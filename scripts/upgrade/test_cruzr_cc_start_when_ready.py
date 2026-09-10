import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('gate', Path(__file__).with_name('cruzr_cc_start_when_ready.py'))
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class GateTests(unittest.TestCase):
    def test_compose_patch_preserves_other_services_and_rejects_changed_command(self):
        patch_spec = importlib.util.spec_from_file_location('compose_patch',
            Path(__file__).with_name('patch_cc_readiness_compose.py'))
        module = importlib.util.module_from_spec(patch_spec)
        patch_spec.loader.exec_module(module)
        text = ('services:\n  other:\n    command: [keep, me]\n'
                '  system.control_center:\n    extends: other\n    command:\n      - '+module.ORIGINAL+'\n')
        result = module.rewrite(text)
        self.assertEqual(result.replace(module.GATED,module.ORIGINAL), text)
        self.assertEqual(module.rewrite(result), result)
        with self.assertRaises(ValueError):
            module.rewrite(text.replace(module.ORIGINAL, 'another command'))

    def run_sequence(self, answers, max_wait=90):
        elapsed = [0.0]
        calls = []
        def check(timeout):
            calls.append(timeout)
            return answers[len(calls)-1] if len(calls) <= len(answers) else False
        def pause(seconds):
            elapsed[0] += seconds
        result = gate.wait_ready(check, lambda: elapsed[0], pause, lambda s: None,
                                 max_wait=max_wait, interval=10)
        return result, calls, elapsed[0]

    def test_waits_for_three_consecutive_real_responses(self):
        result, calls, elapsed = self.run_sequence([False, True, True, False, True, True, True])
        self.assertTrue(result)
        self.assertEqual(len(calls), 7)
        self.assertEqual(elapsed, 60)

    def test_deadline_is_bounded_and_failure_never_starts_vendor(self):
        result, calls, elapsed = self.run_sequence([], max_wait=25)
        self.assertFalse(result)
        self.assertEqual(elapsed, 25)
        self.assertEqual(calls, [12, 12, 5])

    def test_third_response_after_deadline_does_not_qualify(self):
        elapsed = [0.0]
        calls = [0]
        def check(timeout):
            calls[0] += 1
            if calls[0] == 3:
                elapsed[0] += 7
            return True
        def pause(seconds):
            elapsed[0] += seconds
        self.assertFalse(gate.wait_ready(check, lambda: elapsed[0], pause,
                                         lambda s: None, max_wait=25, interval=10))
        self.assertEqual(calls[0], 3)

    def test_rejects_advertised_failed_ambiguous_or_fake_response(self):
        good = 'response: sys_task_msgs.srv.SelfCheckTask.Response(passed=True, reason=[])\n'
        self.assertTrue(gate.response_ok(0, good))
        for code, text in [(1, good), (0, good+good), (0, '/self_check/x86/file_presence_check'),
                           (0, good.replace('True','False')), (0, 'error '+good),
                           (0, good.replace('reason=[]','reason=[failed]'))]:
            self.assertFalse(gate.response_ok(code, text))

    def test_default_check_never_executes_vendor_and_start_preserves_command(self):
        with patch.dict(os.environ, HW_TYPE='cruzr_s2_v1'), \
             patch.object(gate.Path, 'read_bytes', return_value=b'vendor'), \
             patch.object(gate, 'EXPECTED_SHA256', gate.hashlib.sha256(b'vendor').hexdigest()), \
             patch.object(gate, 'wait_ready', return_value=True), \
             patch.object(gate.os, 'execvp') as execute:
            self.assertEqual(gate.main([]), 0)
            execute.assert_not_called()
            gate.main(['--start'])
            execute.assert_called_once_with('rosa', gate.COMMAND)
            self.assertEqual(gate.COMMAND[1:4], ['run','control_center','control_center'])

    def test_readiness_failure_and_changed_binary_block_start(self):
        with patch.dict(os.environ, HW_TYPE='cruzr_s2_v1'), \
             patch.object(gate.Path, 'read_bytes', return_value=b'vendor'), \
             patch.object(gate, 'wait_ready', return_value=False) as ready, \
             patch.object(gate.os, 'execvp') as execute:
            self.assertEqual(gate.main(['--start']), 78)
            ready.assert_not_called()
            with patch.object(gate, 'EXPECTED_SHA256', gate.hashlib.sha256(b'vendor').hexdigest()):
                self.assertEqual(gate.main(['--start']), 75)
            execute.assert_not_called()

    def test_unreviewed_hardware_never_probes_or_starts_vendor(self):
        with patch.dict(os.environ, HW_TYPE='another_robot'), \
             patch.object(gate, 'wait_ready') as ready, \
             patch.object(gate.os, 'execvp') as execute:
            self.assertEqual(gate.main(['--start']), 78)
            ready.assert_not_called()
            execute.assert_not_called()


if __name__ == '__main__':
    unittest.main()
