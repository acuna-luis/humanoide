"""Offline bootstrap failure tests. No Docker, ROS or robot access."""
from pathlib import Path
import shlex
import subprocess
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent / 'runtime'))
import pico_wrist_docker_launcher as launcher


def child_process():
    child = MagicMock()
    child.stdin.fileno.return_value = 71
    child.wait.return_value = 0
    return child


class StreamStartTests(unittest.TestCase):
    def test_success_streams_source_sentinel_and_payload_separately(self):
        child = child_process()
        with patch.object(launcher.subprocess, 'Popen', return_value=child) as spawn, \
             patch.object(launcher, 'write_stream') as write, \
             patch.object(launcher.uuid, 'uuid4') as token:
            token.return_value.hex = 'a'*32
            self.assertIs(launcher.start_streamed('app', '/opt/walker/setup.bash',
                                                 'print(1)', {'x': 1}, stderr=None), child)
        self.assertEqual(write.call_count, 3)
        self.assertEqual(write.call_args_list[0].args[1], b'print(1)\n')
        self.assertEqual(write.call_args_list[1].args[1], b'PICO_SOURCE_END_'+b'a'*32+b'\n')
        self.assertTrue(write.call_args_list[2].args[1].endswith(b'\n'))
        bootstrap = spawn.call_args.args[0][-1]
        self.assertIn('if line==', bootstrap)
        self.assertNotIn('line.rstrip', bootstrap)

    def test_source_failure_is_before_any_sentinel_attempt(self):
        child = child_process()
        with patch.object(launcher.subprocess, 'Popen', return_value=child), \
             patch.object(launcher, 'write_stream', side_effect=TimeoutError('source')) as write:
            with self.assertRaises(launcher.StreamStartUncertain) as observed:
                launcher.start_streamed('app', '/opt/walker/setup.bash', 'pass', {}, stderr=None)
        self.assertEqual(write.call_count, 1)
        self.assertIs(observed.exception.process, child)
        self.assertFalse(observed.exception.source_may_have_executed)
        self.assertTrue(observed.exception.local_cleanup_observed)
        self.assertEqual(observed.exception.phase, 'source')
        child.stdin.close.assert_called_once()
        child.wait.assert_called_once_with(timeout=1)
        child.terminate.assert_not_called()
        child.kill.assert_not_called()

    def test_interrupt_after_sentinel_delivery_preserves_potentially_active_child(self):
        child = child_process()
        delivered = []
        def write(_fd, data, _timeout):
            delivered.append(data)
            if len(delivered) == 2:
                # Models SIGINT after the entire sentinel was sent, but before
                # the caller saw a successful return from write_stream.
                raise KeyboardInterrupt('after delivery')
        with patch.object(launcher.subprocess, 'Popen', return_value=child), \
             patch.object(launcher, 'write_stream', side_effect=write):
            with self.assertRaises(launcher.StreamStartUncertain) as observed:
                launcher.start_streamed('app', '/opt/walker/setup.bash', 'pass', {}, stderr=None)
        self.assertTrue(delivered[1].endswith(b'\n'))
        self.assertIs(observed.exception.process, child)
        self.assertTrue(observed.exception.source_may_have_executed)
        self.assertEqual(observed.exception.phase, 'sentinel')
        child.stdin.close.assert_not_called()
        child.wait.assert_not_called()
        child.terminate.assert_not_called()
        child.kill.assert_not_called()

    def test_payload_failure_keeps_handle_and_never_signals_or_closes(self):
        child = child_process()
        with patch.object(launcher.subprocess, 'Popen', return_value=child), \
             patch.object(launcher, 'write_stream', side_effect=[None, None, TimeoutError('payload')]):
            with self.assertRaises(launcher.StreamStartUncertain) as observed:
                launcher.start_streamed('app', '/opt/walker/setup.bash', 'pass', {}, stderr=None)
        self.assertIs(observed.exception.process, child)
        self.assertTrue(observed.exception.source_may_have_executed)
        self.assertEqual(observed.exception.phase, 'payload')
        child.stdin.close.assert_not_called()
        child.wait.assert_not_called()
        child.terminate.assert_not_called()
        child.kill.assert_not_called()

    def test_inert_bootstrap_can_be_terminated_after_its_stdin_closes(self):
        child = child_process()
        child.wait.side_effect = [subprocess.TimeoutExpired('docker', 1), 0]
        with patch.object(launcher.subprocess, 'Popen', return_value=child), \
             patch.object(launcher, 'write_stream', side_effect=TimeoutError('source')):
            with self.assertRaises(launcher.StreamStartUncertain):
                launcher.start_streamed('app', '/opt/walker/setup.bash', 'pass', {}, stderr=None)
        child.stdin.close.assert_called_once()
        child.terminate.assert_called_once()
        child.kill.assert_not_called()

    def test_bad_json_rejected_before_starting_process(self):
        with patch.object(launcher.subprocess, 'Popen') as spawn:
            with self.assertRaises(ValueError):
                launcher.start_streamed('app', '/opt/walker/setup.bash', 'pass', {'x': float('nan')}, stderr=None)
            spawn.assert_not_called()

    def test_launcher_retains_uncertain_worker_and_reports_no_stop(self):
        child = child_process()
        output = MagicMock()
        uncertain = []
        error = launcher.StreamStartUncertain(child, 'payload', TimeoutError('payload'),
                                              source_may_have_executed=True)
        with patch.object(launcher, 'start_streamed', side_effect=error):
            with self.assertRaises(launcher.StreamStartUncertain) as raised:
                launcher._track_stream_start('worker', uncertain, output,
                                             'app', '/opt/walker/setup.bash', 'pass', {}, stderr=None)
        self.assertIs(raised.exception, error)
        self.assertEqual(uncertain, [('worker', 'payload', child)])
        row = output.emit.call_args.args[0]
        self.assertEqual(row['event'], 'OPERATOR_ALERT')
        self.assertFalse(row['physical_stop_confirmed'])
        self.assertTrue(row['no_retry'])
        child.stdin.close.assert_not_called()
        child.terminate.assert_not_called()
        child.kill.assert_not_called()

    def test_launcher_retains_inert_child_if_cleanup_cannot_be_confirmed(self):
        child = child_process()
        output = MagicMock()
        uncertain = []
        error = launcher.StreamStartUncertain(child, 'source', OSError('cleanup'),
                                              source_may_have_executed=False,
                                              local_cleanup_observed=False)
        with patch.object(launcher, 'start_streamed', side_effect=error):
            with self.assertRaises(launcher.StreamStartUncertain):
                launcher._track_stream_start('guard', uncertain, output,
                                             'ros', '/opt/ros/humble/setup.bash', 'pass', {}, stderr=None)
        self.assertEqual(uncertain, [('guard', 'source', child)])
        row = output.emit.call_args.args[0]
        self.assertFalse(row['source_may_have_executed'])
        self.assertFalse(row['local_cleanup_observed'])
        self.assertFalse(row['physical_stop_confirmed'])

    def test_uncertain_child_is_observed_to_local_exit_without_signals(self):
        child = child_process()
        child.stdout = None
        child.poll.side_effect = [None, 7]
        output = MagicMock()
        with patch.object(launcher.time, 'sleep'):
            self.assertEqual(launcher._observe_uncertain_child(child, output, 'worker', 'payload'), 7)
        rows = [call.args[0] for call in output.emit.call_args_list]
        self.assertEqual([row['event'] for row in rows],
                         ['UNRESOLVED_MONITORING', 'uncertain_child_exit_observed'])
        self.assertTrue(all(row['physical_stop_confirmed'] is False for row in rows))
        self.assertTrue(all(row['no_retry'] for row in rows))
        child.stdin.close.assert_not_called()
        child.terminate.assert_not_called()
        child.kill.assert_not_called()

    def test_launch_revokes_lease_and_retains_worker_on_bootstrap_failure(self):
        import os
        child = child_process()
        child.stdout = None
        guard = child_process()
        error = launcher.StreamStartUncertain(child, 'payload', TimeoutError('payload'),
                                              source_may_have_executed=True)
        output = MagicMock()
        output.emit.return_value = True
        output.failed = False
        pc = MagicMock()
        pc.alive.return_value = True
        lease = MagicMock()
        lease.path = Path('/tmp/lease.json')
        pipe = MagicMock()
        lock_fd = os.open('/dev/null', os.O_RDONLY)
        session = {'session_id': 'a'*32, 'age_at_handoff_s': 0.0}
        payload = {'session': session, 'manifest': {'input': {'reference_20d': {}}},
                   'urdf_text': '', 'transmissions_text': '',
                   'guard_source': 'pass', 'worker_source': 'pass', 'operator_confirmed': True}
        def coordinate(_lease, _pipe, _manifest, _urdf, _sps, start_worker, *_args, **_kwargs):
            return start_worker(lease.path, Path('/tmp/intent.json'), 1000)
        with patch.object(launcher.arm, 'physical_release_gate'), \
             patch.object(launcher, 'validate_payload', return_value=session), \
             patch.object(launcher.coordinator, 'ensure_control_root'), \
             patch.object(launcher.coordinator, 'acquire_trial_lock', return_value=lock_fd), \
             patch.object(launcher, 'HostOutput', return_value=output), \
             patch.object(launcher, 'pc_preflight_handoff'), \
             patch.object(launcher.heartbeat, 'PcHeartbeat', return_value=pc), \
             patch.object(launcher, 'discover_containers', return_value=('app', 'ros')), \
             patch.object(launcher.tempfile, 'mkdtemp', return_value='/tmp/fake'), \
             patch.object(launcher, 'verify_shared_tmp'), \
             patch.object(launcher.bridge, 'GuardLease', return_value=lease), \
             patch.object(launcher.bridge, 'GuardPipe', return_value=pipe), \
             patch.object(launcher.coordinator, 'GLOBAL_RECEIPT_DIR', Path('/tmp')), \
             patch('pathlib.Path.open', new_callable=MagicMock), \
             patch.object(launcher, 'start_streamed', side_effect=[guard, error]), \
             patch.object(launcher.coordinator, 'coordinate', side_effect=coordinate), \
             patch.object(launcher, '_observe_uncertain_child', return_value=1) as observe:
            with self.assertRaises(launcher.StreamStartUncertain):
                launcher.launch(payload)
        lease.fail.assert_called_once()
        observe.assert_called_once_with(child, output, 'worker', 'payload')
        pc.close.assert_called_once()
        child.stdin.close.assert_not_called()
        child.terminate.assert_not_called()
        child.kill.assert_not_called()

    def test_bootstrap_refuses_sentinel_without_terminating_newline(self):
        child = child_process()
        with patch.object(launcher.subprocess, 'Popen', return_value=child) as spawn, \
             patch.object(launcher, 'write_stream'), \
             patch.object(launcher.uuid, 'uuid4') as token:
            token.return_value.hex = 'a'*32
            launcher.start_streamed('app', '/opt/walker/setup.bash',
                                    'print("SOURCE_EXECUTED")', {}, stderr=None)
        command = shlex.split(spawn.call_args.args[0][-1])
        bootstrap = command[command.index('-c')+1]
        result = subprocess.run([sys.executable, '-B', '-c', bootstrap],
            input='print("SOURCE_EXECUTED")\nPICO_SOURCE_END_'+'a'*32,
            capture_output=True, text=True, timeout=3)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('SOURCE_EXECUTED', result.stdout)
        self.assertIn('incomplete source', result.stderr)


if __name__ == '__main__':
    unittest.main()
