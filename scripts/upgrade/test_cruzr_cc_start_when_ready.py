import importlib.util
import os
from pathlib import Path
import unittest
import tempfile
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('gate', Path(__file__).with_name('cruzr_cc_start_when_ready.py'))
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
import cruzr_boot_voice as voice
import cruzr_boot_visual as visual
voice.gate = gate


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
             patch.object(gate, 'wait_cameras', return_value=True), \
             patch.object(gate, 'probe', return_value=True), \
             patch.object(gate, 'claim_boot_voice', return_value=False), \
             patch.object(gate.os, 'execvp') as execute:
            self.assertEqual(gate.main([]), 0)
            execute.assert_not_called()
            gate.main(['--start'])
            execute.assert_called_once_with('rosa', gate.COMMAND)
            self.assertEqual(gate.COMMAND[1:4], ['run','control_center','control_center'])

    def test_cameras_require_all_six_and_two_advancing_rounds(self):
        def run(rounds):
            elapsed = [0]
            def pause(seconds): elapsed[0] += seconds
            answers = iter(rounds)
            return gate.wait_cameras(max_wait=11, check=lambda _: next(answers),
                                     clock=lambda: elapsed[0], pause=pause, emit=lambda _: None)
        frame = {topic: 100 for topic in gate.CAMERA_TOPICS}
        next_frame = {topic: 200 for topic in gate.CAMERA_TOPICS}
        missing = dict(next_frame); missing[gate.CAMERA_TOPICS[0]] = None
        self.assertTrue(run([frame, next_frame]))
        self.assertFalse(run([frame, frame, frame]))
        self.assertFalse(run([frame, missing, next_frame]))
        self.assertIsNone(gate.camera_stamp(None))
        self.assertIsNone(gate.camera_stamp({'header': {'stamp': {'sec': 0, 'nanosec': 0}}, 'width': 1, 'height': 1}))

    def test_release_rejects_recovery_old_log_missing_stop_and_process_change(self):
        good = (('184', '/current'), ['TmpState', 'WaitEStopRelease'])
        bad = (('184', '/current'), ['AutoTaskMode', 'WaitEStopRelease'])
        self.assertFalse(gate.initial_release_state(None))
        self.assertFalse(gate.initial_release_state(bad))
        self.assertTrue(gate.initial_release_state(good))
        with patch.object(gate, 'current_control_log', return_value=good), \
             patch.object(gate, 'sample', side_effect=[{'data': 1}, {'data': 0}, {'data': 0}]):
            self.assertTrue(gate.release_ready(read_snapshot=gate.current_control_log, read_sample=gate.sample))
        for samples in ([{'data': 0}, {'data': 0}, {'data': 0}],
                        [None, {'data': 0}, {'data': 0}]):
            with patch.object(gate, 'current_control_log', return_value=good), \
                 patch.object(gate, 'sample', side_effect=samples):
                self.assertFalse(gate.release_ready(read_snapshot=gate.current_control_log, read_sample=gate.sample))
        with patch.object(gate, 'current_control_log', side_effect=[good, bad]), \
             patch.object(gate, 'sample', side_effect=[{'data': 1}, {'data': 0}, {'data': 0}]):
            self.assertFalse(gate.release_ready(read_snapshot=gate.current_control_log, read_sample=gate.sample))

    def test_voice_once_per_host_boot_not_each_container_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            boot = Path(directory)/'boot'; record = Path(directory)/'record'
            boot.write_text('11111111-1111-1111-1111-111111111111')
            with patch.object(gate, 'BOOT_ID', boot), patch.object(gate, 'VOICE_BOOT_RECORD', record):
                self.assertTrue(gate.claim_boot_voice())
                self.assertFalse(gate.claim_boot_voice())
                boot.write_text('22222222-2222-2222-2222-222222222222')
                self.assertTrue(gate.claim_boot_voice())
                self.assertFalse(gate.claim_boot_voice())

    def test_voice_only_uses_tts_and_only_with_fresh_release_readiness(self):
        info = gate.subprocess.CompletedProcess([], 0,
            'Action: sys_task_msgs/action/Tts\nAction server count: 1\n')
        with patch.object(voice, 'native', return_value=info) as native, \
             patch.object(voice, 'motion_probe', return_value=True), \
             patch.object(voice, 'release_ready', return_value=False):
            self.assertFalse(voice.announce())
            native.assert_called_once_with(['rosa', 'action', 'info', '/sys/speech/tts'], 5)
        done = gate.subprocess.CompletedProcess([], 0,
            "Result: result={'result': {'desc': 'Success', 'state': 1001000, "
            "'msg_type': 'sys_state_msgs::msg::SpeechState'}}, status=4\n")
        with patch.object(voice, 'native', side_effect=[info, done]) as native, \
             patch.object(voice, 'motion_probe', return_value=True), \
             patch.object(voice, 'release_ready', return_value=True):
            self.assertTrue(voice.announce())
            command = native.call_args.args[0]
            self.assertEqual(command[:5], ['rosa', 'action', 'send_goal', '/sys/speech/tts', 'sys_task_msgs/action/Tts'])
            goal = gate.json.loads(command[5])
            self.assertEqual(goal['text'], 'Ready to release the emergency stop.')
            self.assertEqual(goal['language'], 'en')

    def test_tts_result_requires_real_success_not_goal_acceptance(self):
        good = ("Result: result={'result': {'desc': 'Success', 'state': 1001000, "
                "'msg_type': 'sys_state_msgs::msg::SpeechState'}}, status=4\n")
        self.assertTrue(voice.speech_result_ok(0, good))
        for rc, output in [(1, good), (0, good.replace('status=4', 'status=6')),
                           (0, good.replace('Success', 'Failure')),
                           (0, good+good), (0, 'Goal accepted with ID: abc'),
                           (0, good.replace('1001000', '0'))]:
            self.assertFalse(voice.speech_result_ok(rc, output))

    def test_watcher_rejects_operating_mode_and_never_reannounces_same_boot(self):
        with patch.object(voice.socket, 'gethostname', return_value='vision'), \
             patch.object(gate, 'claim_boot_voice', return_value=False), \
             patch.object(voice, 'snapshot') as snapshot, \
             patch.object(voice, 'announce') as announce:
            self.assertEqual(voice.main(['--watch']), 0)
            snapshot.assert_not_called()
            announce.assert_not_called()
        with patch.object(voice.socket, 'gethostname', return_value='vision'), \
             patch.object(voice, 'snapshot', return_value=[['1', '/current'], ['AutoTaskMode']]), \
             patch.object(voice, 'announce') as announce:
            self.assertEqual(voice.main(['--check', '--announce']), 75)
            announce.assert_not_called()

    def test_plain_check_never_speaks_and_successful_watcher_does_once(self):
        initial = [['1', '/current'], ['TmpState', 'WaitEStopRelease']]
        with patch.object(voice.socket, 'gethostname', return_value='vision'), \
             patch.object(gate, 'claim_boot_voice', return_value=True), \
             patch.object(voice, 'snapshot', return_value=initial), \
             patch.object(voice, 'check_ready', return_value=True), \
             patch.object(visual, 'prepare', return_value=True), \
             patch.object(visual, 'hold', return_value=True) as hold, \
             patch.object(voice, 'announce', return_value=True) as announce:
            self.assertEqual(voice.main(['--check']), 0)
            announce.assert_not_called()
            hold.assert_not_called()
            self.assertEqual(voice.main(['--watch']), 0)
            announce.assert_called_once_with()
            hold.assert_called_once()

    def test_motion_lost_after_cameras_rejects_release(self):
        with patch.object(gate, 'wait_ready', return_value=True), \
             patch.object(gate, 'wait_cameras', return_value=True), \
             patch.object(voice, 'motion_probe', return_value=False), \
             patch.object(voice, 'release_ready') as release:
            self.assertFalse(voice.check_ready(voice.time.monotonic()+60))
            release.assert_not_called()

    def test_readiness_failure_and_changed_binary_block_start(self):
        with patch.dict(os.environ, HW_TYPE='cruzr_s2_v1'), \
             patch.object(gate.Path, 'read_bytes', return_value=b'vendor'), \
             patch.object(gate, 'wait_ready', return_value=False) as ready, \
             patch.object(gate, 'claim_boot_voice', return_value=False), \
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
