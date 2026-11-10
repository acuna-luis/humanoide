"""PC relay/permission integration with local fake subprocesses only."""
import json
from pathlib import Path
import tempfile
import threading
import time
import types
import unittest
from unittest.mock import Mock, patch

import run_pico_wrist_native_trial as launcher
from test_pico_wrist_model_decision import case, GOAL


class LiveModelPermissionTests(unittest.TestCase):
    def prepared(self, directory, *, stale=False):
        rows, manifest = case()
        now = time.monotonic_ns()
        rows[1]['paired_state20']['received_monotonic_ns'] = now-(11_000_000_000 if stale else 1_000_000)
        rows[1]['prediction_received_monotonic_ns'] = now-500_000
        raw = ''.join(json.dumps(row)+'\n' for row in rows).encode()
        provider = launcher.LiveModelPermission(manifest, {}, Path(directory))
        return provider, raw, manifest

    def test_complete_relay_is_retained_before_permission(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider, raw, manifest = self.prepared(tmp)
            request = {'goal_id':GOAL, 'task_sha256':manifest['candidate']['xml_sha256']}
            self.assertIsNone(provider.permit(request))
            result = Mock(returncode=0)
            result.communicate.return_value = (raw, b'')
            with patch.object(provider, '_verify_sources') as verify, \
                 patch.object(launcher.subprocess, 'Popen', return_value=result) as run:
                provider._capture()
            self.assertEqual(verify.call_count, 2)
            command = run.call_args.args[0]
            self.assertIn('--one-shot', command)
            self.assertEqual(command[command.index('--max-samples')+1], '1')
            self.assertEqual((Path(tmp)/'model-shadow.jsonl').read_bytes(), raw)
            decision = json.loads((Path(tmp)/'model-decision.json').read_bytes())
            self.assertEqual(provider.permit(request)['decision_sha256'], decision['decision_sha256'])
            self.assertTrue(provider.close())
            with self.assertRaisesRegex(RuntimeError, 'model_capture_closed'):
                provider.permit(request)

    def test_failed_or_incomplete_relay_cannot_issue_permission(self):
        for result in (types.SimpleNamespace(returncode=1, stdout=b'', stderr=b'failure'),
                       types.SimpleNamespace(returncode=0, stdout=b'{"event":"model_ready"}\n', stderr=b'')):
            with tempfile.TemporaryDirectory() as tmp:
                provider, _, manifest = self.prepared(tmp)
                request = {'goal_id':GOAL, 'task_sha256':manifest['candidate']['xml_sha256']}
                process = Mock(returncode=result.returncode)
                process.communicate.return_value = (result.stdout, result.stderr)
                with patch.object(provider, '_verify_sources'), \
                     patch.object(launcher.subprocess, 'Popen', return_value=process):
                    provider._capture()
                with self.assertRaisesRegex(RuntimeError, 'model_capture_failed'):
                    provider.permit(request)
                self.assertFalse((Path(tmp)/'model-decision.json').exists())
                failure = json.loads((Path(tmp)/'model-failure.json').read_text())
                self.assertEqual(failure['relay_returncode'], result.returncode)
                self.assertEqual(failure['stderr_tail'], result.stderr.decode())
                self.assertFalse(failure['remote_cleanup_verified'])

    def test_expired_decision_cannot_issue_permission(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider, raw, manifest = self.prepared(tmp, stale=True)
            result = Mock(returncode=0)
            result.communicate.return_value = (raw, b'')
            with patch.object(provider, '_verify_sources'), \
                 patch.object(launcher.subprocess, 'Popen', return_value=result):
                provider._capture()
            with self.assertRaisesRegex(ValueError, 'expired'):
                provider.permit({'goal_id':GOAL, 'task_sha256':manifest['candidate']['xml_sha256']})

    def test_close_interrupts_local_relay_without_issuing_permission(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider, raw, manifest = self.prepared(tmp)
            started = threading.Event(); stopped = threading.Event()
            class Relay:
                returncode = None
                def poll(self): return self.returncode
                def terminate(self):
                    self.returncode = -15
                    stopped.set()
                def communicate(self, timeout):
                    started.set()
                    if not stopped.wait(timeout): raise TimeoutError('test_relay_did_not_stop')
                    return raw, b''
            process = Relay()
            with patch.object(provider, '_verify_sources'), \
                 patch.object(launcher.subprocess, 'Popen', return_value=process):
                provider.start()
                self.assertTrue(started.wait(2))
                self.assertTrue(provider.close())
            self.assertTrue(stopped.is_set())
            self.assertIsNone(provider.decision)
            with self.assertRaisesRegex(RuntimeError, 'model_capture_closed'):
                provider.permit({'goal_id':GOAL, 'task_sha256':manifest['candidate']['xml_sha256']})


if __name__ == '__main__':
    unittest.main()
