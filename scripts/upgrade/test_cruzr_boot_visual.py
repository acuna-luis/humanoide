import hashlib
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

import cruzr_boot_visual as visual
import cruzr_boot_voice as voice


class VisualTests(unittest.TestCase):
    def test_snapshot_stays_a_direct_read_of_current_process_and_log(self):
        expected = [['pid', 'log'], ['TmpState', 'WaitEStopRelease']]
        response = subprocess.CompletedProcess([], 0, json.dumps(expected))
        with patch.object(voice.subprocess, 'run', return_value=response) as run:
            self.assertEqual(voice.snapshot(), expected)
        self.assertEqual(run.call_args.args[0], ['docker', 'exec', voice.CC,
                         'python3', voice.GATE_PATH, '--control-snapshot'])

    def test_hold_clears_after_release_without_second_permission(self):
        elapsed = [0]
        with patch.object(visual, 'container_write', return_value=True) as write:
            ready = iter([True, True, False])
            self.assertTrue(visual.hold(lambda: next(ready), clock=lambda: elapsed[0],
                                       pause=lambda t: elapsed.__setitem__(0, elapsed[0]+t)))
        payloads = [json.loads(c.args[1]) for c in write.call_args_list]
        self.assertEqual([p['ready'] for p in payloads], [True, True, False])
        self.assertNotEqual(payloads[0]['sequence'], payloads[1]['sequence'])

    def test_unknown_state_and_late_check_never_publish_ready(self):
        for checker in (lambda: False, lambda: True):
            with patch.object(visual, 'container_write', return_value=True) as write:
                times = iter([0, 0, 3])
                visual.hold(checker, max_wait=2, clock=lambda: next(times))
            self.assertTrue(all(not json.loads(c.args[1])['ready'] for c in write.call_args_list))

    def test_cleanup_on_exception_and_finite_lease(self):
        with patch.object(visual, 'container_write', return_value=True) as write:
            self.assertFalse(visual.hold(lambda: (_ for _ in ()).throw(OSError())))
        self.assertFalse(json.loads(write.call_args.args[1])['ready'])
        payload = json.loads(visual.status_payload(True, 'test', clock=lambda: 100))
        self.assertEqual(payload['expires_at_ms'], 112000)

    def test_page_patch_is_exact_idempotent_and_preserves_vendor_code(self):
        page = '<head>\n  </head>\n<body><div id="root"></div></body>\n'
        with patch.object(visual, 'ORIGINAL_INDEX_SHA', hashlib.sha256(page.encode()).hexdigest()):
            result = visual.patched_index(page)
            self.assertEqual(result.replace(visual.TAG, ''), page)
            self.assertEqual(visual.patched_index(result), result)
            for bad in (page+'changed', result.replace(visual.TAG, visual.TAG*2)):
                with self.assertRaises(ValueError): visual.patched_index(bad)

    def test_live_monitor_rejects_frozen_cameras_and_changed_process(self):
        initial = [['pid', 'log'], ['TmpState', 'WaitEStopRelease']]
        frame = {t: 100 for t in voice.gate.CAMERA_TOPICS}
        with patch.object(voice, 'snapshot', return_value=initial), \
             patch.object(voice, 'cameras', return_value=frame), \
             patch.object(voice, 'motion_probe', return_value=True), \
             patch.object(voice, 'release_ready', return_value=True):
            ready = voice.visual_ready_checker()
            self.assertTrue(ready())
            self.assertFalse(ready())
            with patch.object(voice, 'snapshot', return_value=[['new', 'log'], initial[1]]):
                self.assertFalse(ready())

    def test_visual_test_never_announces_and_plain_check_never_installs(self):
        initial = [['pid', 'log'], ['TmpState', 'WaitEStopRelease']]
        with patch.object(voice.socket, 'gethostname', return_value='vision'), \
             patch.object(voice, 'snapshot', return_value=initial), \
             patch.object(voice, 'check_ready', return_value=True), \
             patch.object(voice, 'announce') as announce, \
             patch.object(visual, 'prepare', return_value=True) as prepare, \
             patch.object(visual, 'hold', return_value=True) as hold:
            self.assertEqual(voice.main(['--check']), 0)
            prepare.assert_not_called()
            self.assertEqual(voice.main(['--check', '--visual']), 0)
            announce.assert_not_called()
            hold.assert_called_once()


if __name__ == '__main__':
    unittest.main()
