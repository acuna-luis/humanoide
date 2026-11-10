"""Candidate launcher source and closed-gate tests; no SSH or robot actions."""
import contextlib
import hashlib
import io
import json
import os
import shlex
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import run_pico_wrist_native_trial as launcher
import pico_wrist_review_binding as binding
import check_pico_wrist_full_passive as full_passive


def execute_streamed(source, payload):
    sentinel = 'FAKE_SOURCE_END'
    bootstrap = ('import sys\nparts=[]\nfor line in sys.stdin:\n'
                 ' if line.rstrip("\\n")=='+repr(sentinel)+': break\n'
                 ' parts.append(line)\n'
                 'exec(compile("".join(parts),"<source>","exec"))\n')
    return subprocess.run([sys.executable,'-B','-c',bootstrap],
        input=source+'\n'+sentinel+'\n'+json.dumps(payload)+'\n',
        text=True,capture_output=True,timeout=10)


class LauncherTests(unittest.TestCase):
    def test_verified_host_bootstrap_checks_source_before_execution(self):
        sentinel = 'PICO_HOST_END_' + 'b'*32
        payload = {'session': {'session_id': 'a'*32}}
        source = ('import json,sys\n'
                  'print(json.loads(sys.stdin.readline())["session"]["session_id"], flush=True)\n')
        raw = source.encode()
        payload_raw = json.dumps(payload, allow_nan=False).encode()
        verified = {'source_size':len(raw), 'source_sha256':hashlib.sha256(raw).hexdigest(),
                    'payload_sha256':hashlib.sha256(payload_raw).hexdigest(), 'session_id':'a'*32}
        command = shlex.split(launcher.host_command(sentinel, verified=verified)[-1])
        child = launcher.start_host_streamed(command, source, sentinel, payload, dict(os.environ))
        try:
            self.assertEqual(child.stdout.readline(), b'a'*32+b'\n')
            self.assertEqual(child.wait(timeout=3), 0)
        finally:
            for stream in (child.stdin, child.stdout, child.stderr): stream.close()
        verified['source_sha256'] = '0'*64
        command = shlex.split(launcher.host_command(sentinel, verified=verified)[-1])
        child = launcher.start_host_streamed(command, source, sentinel, payload, dict(os.environ))
        try:
            self.assertEqual(child.stdout.read(), b'')
            self.assertNotEqual(child.wait(timeout=3), 0)
            self.assertIn(b'source_digest_mismatch', child.stderr.read())
        finally:
            for stream in (child.stdin, child.stdout, child.stderr): stream.close()

    def test_controlled_pc_sources_exist_and_are_readable(self):
        sources = launcher.controlled_pc_sources()
        self.assertIn('estop_reader', sources)
        self.assertIn('review_binding', sources)
        self.assertTrue(all(isinstance(raw, bytes) and raw for raw, _ in sources.values()))

    def test_run_blocked_before_file_or_network(self):
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('must not read')), \
             patch.object(launcher.subprocess, 'Popen', side_effect=AssertionError('must not connect')):
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(launcher.main(['--run', '--physical-confirmed']), 2)

    def test_sentinel_delivered_then_interrupt_preserves_live_child(self):
        sentinel = 'LOCAL_TEST_SENTINEL'
        bootstrap = ('import sys\nparts=[]\nfor line in sys.stdin:\n'
                     ' if line=='+repr(sentinel+'\n')+': break\n'
                     ' parts.append(line)\n'
                     'else: raise SystemExit("incomplete")\n'
                     'exec(compile("".join(parts),"<local-test>","exec"))\n')
        source = 'import sys\nprint("SOURCE_EXECUTED",flush=True)\nsys.stdin.readline()\n'
        original = launcher.docker_launch.write_stream
        calls = []
        def write_then_interrupt(fd, data, timeout):
            calls.append(data)
            original(fd, data, timeout)
            if len(calls) == 2:
                raise KeyboardInterrupt('after complete sentinel')
        child = None
        try:
            with patch.object(launcher.docker_launch, 'write_stream', side_effect=write_then_interrupt):
                with self.assertRaises(launcher.HostStartUncertain) as raised:
                    launcher.start_host_streamed([sys.executable, '-B', '-u', '-c', bootstrap],
                        source, sentinel, {}, dict(os.environ))
            child = raised.exception.process
            self.assertEqual(raised.exception.phase, 'sentinel')
            self.assertTrue(raised.exception.source_may_have_executed)
            self.assertFalse(raised.exception.local_cleanup_observed)
            self.assertEqual(child.stdout.readline(), b'SOURCE_EXECUTED\n')
            self.assertIsNone(child.poll())
            self.assertFalse(child.stdin.closed)
        finally:
            # This is a local fake bootstrap with no robot access or goal.
            if child is not None:
                child.stdin.close()
                child.wait(timeout=3)
                child.stdout.close(); child.stderr.close()

    def test_source_failure_reaps_only_before_sentinel(self):
        child = unittest.mock.MagicMock()
        child.stdin.fileno.return_value = 123
        with patch.object(launcher.subprocess, 'Popen', return_value=child), \
             patch.object(launcher.docker_launch, 'write_stream', side_effect=BrokenPipeError('before sentinel')), \
             patch.object(launcher.docker_launch, '_reap_unstarted_bootstrap') as reap:
            with self.assertRaises(launcher.HostStartUncertain) as raised:
                launcher.start_host_streamed(['fake'], 'source', 'sentinel', {}, {})
        self.assertEqual(raised.exception.phase, 'source')
        self.assertFalse(raised.exception.source_may_have_executed)
        self.assertTrue(raised.exception.local_cleanup_observed)
        reap.assert_called_once_with(child)

    def test_bad_output_after_dispatch_keeps_observing_without_killing(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp)/'local-child-completed'
            code = ('import json,pathlib,sys,time\n'
                    'print(json.dumps({"event":"dispatched","goal_id":"fake"}),flush=True)\n'
                    'print("not-json",flush=True)\n'
                    'time.sleep(.3)\n'
                    'pathlib.Path(sys.argv[1]).write_text("completed")\n')
            child = subprocess.Popen([sys.executable, '-B', '-u', '-c', code, str(marker)],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, bufsize=0)
            try:
                with contextlib.redirect_stdout(io.StringIO()), \
                     contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaisesRegex(RuntimeError, 'host_delivery_uncertain'):
                        launcher.supervise_started_host(child, 'a'*32, time.monotonic(), Path(tmp))
                self.assertEqual(child.returncode, 0)
                self.assertEqual(marker.read_text(), 'completed')
            finally:
                if child.poll() is None:
                    child.kill()  # Local fake process only; no robot.
                child.wait(timeout=3)
                child.stdin.close(); child.stdout.close(); child.stderr.close()

    def test_selector_setup_failure_preserves_same_host_handle(self):
        child = unittest.mock.MagicMock()
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(launcher.selectors, 'DefaultSelector', side_effect=OSError('no selector')), \
             patch.object(launcher, 'observe_uncertain_host', side_effect=RuntimeError('observed')) as observe, \
             contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, 'observed'):
                launcher.supervise_started_host(child, 'a'*32, time.monotonic(), Path(tmp))
        observe.assert_called_once_with(child, Path(tmp), 'runtime')
        child.kill.assert_not_called(); child.terminate.assert_not_called()

    def test_selector_close_failure_does_not_abandon_host(self):
        child = unittest.mock.MagicMock()
        selector = unittest.mock.MagicMock()
        selector.register.side_effect = OSError('register failed')
        selector.close.side_effect = OSError('close failed')
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(launcher.selectors, 'DefaultSelector', return_value=selector), \
             patch.object(launcher.os, 'set_blocking'), \
             patch.object(launcher, 'observe_uncertain_host', side_effect=RuntimeError('observed')) as observe, \
             contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, 'observed'):
                launcher.supervise_started_host(child, 'a'*32, time.monotonic(), Path(tmp))
        observe.assert_called_once_with(child, Path(tmp), 'runtime')
        child.kill.assert_not_called(); child.terminate.assert_not_called()

    def test_uncertain_observation_survives_failed_logs_and_selector(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp)/'local-child-completed'
            code = ('import pathlib,sys,time\n'
                    'print("still-running",flush=True)\n'
                    'time.sleep(.2)\n'
                    'pathlib.Path(sys.argv[1]).write_text("completed")\n')
            child = subprocess.Popen([sys.executable, '-B', '-u', '-c', code, str(marker)],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, bufsize=0)
            original_open = Path.open
            def fail_log_open(path, *args, **kwargs):
                if path.name.startswith('uncertain-host-'):
                    raise OSError('simulated log failure')
                return original_open(path, *args, **kwargs)
            try:
                with patch.object(Path, 'open', fail_log_open), \
                     patch.object(launcher.selectors, 'DefaultSelector', side_effect=OSError('no selector')), \
                     contextlib.redirect_stderr(io.StringIO()) as stderr:
                    with self.assertRaisesRegex(RuntimeError, 'host_delivery_uncertain'):
                        launcher.observe_uncertain_host(child, Path(tmp), 'runtime')
                self.assertIn('observación continúa', stderr.getvalue())
                self.assertEqual(child.returncode, 0)
                self.assertEqual(marker.read_text(), 'completed')
                self.assertFalse(child.stdin.closed)
            finally:
                if child.poll() is None:
                    child.kill()  # Local fake process only; no robot.
                child.wait(timeout=3)
                child.stdin.close(); child.stdout.close(); child.stderr.close()

    def test_uncertain_observation_survives_poll_and_stderr_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            child = subprocess.Popen([sys.executable, '-B', '-c', 'import time; time.sleep(.2)'],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            original_poll = child.poll
            polls = []
            def flaky_poll():
                polls.append(1)
                if len(polls) == 1: raise OSError('poll failed')
                return original_poll()
            broken_stderr = unittest.mock.MagicMock()
            broken_stderr.write.side_effect = BrokenPipeError('stderr closed')
            try:
                with patch.object(child, 'poll', side_effect=flaky_poll), \
                     patch.object(sys, 'stderr', broken_stderr):
                    with self.assertRaisesRegex(RuntimeError, 'host_delivery_uncertain'):
                        launcher.observe_uncertain_host(child, Path(tmp), 'runtime')
                self.assertEqual(child.returncode, 0)
                self.assertFalse(child.stdin.closed)
            finally:
                if child.poll() is None: child.kill()
                child.wait(timeout=3)
                child.stdin.close(); child.stdout.close(); child.stderr.close()

    def test_uncertain_observation_survives_setup_interrupt_and_close_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp)/'local-child-completed'
            code = 'import pathlib,sys,time; time.sleep(.2); pathlib.Path(sys.argv[1]).write_text("done")'
            child = subprocess.Popen([sys.executable, '-B', '-c', code, str(marker)],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            real_set_blocking = os.set_blocking
            real_open = Path.open
            calls = {'stream': 0, 'log': 0}
            def flaky_set_blocking(*args):
                calls['stream'] += 1
                if calls['stream'] == 1: raise KeyboardInterrupt()
                return real_set_blocking(*args)
            class FailingClose:
                def __init__(self, wrapped): self.wrapped = wrapped
                def write(self, value): return self.wrapped.write(value)
                def flush(self): return self.wrapped.flush()
                def close(self):
                    self.wrapped.close()
                    raise OSError('simulated close failure')
            def flaky_open(path, *args, **kwargs):
                if path.name.startswith('uncertain-host-'):
                    calls['log'] += 1
                    if calls['log'] == 1: raise KeyboardInterrupt()
                    return FailingClose(real_open(path, *args, **kwargs))
                return real_open(path, *args, **kwargs)
            try:
                with patch.object(launcher.os, 'set_blocking', side_effect=flaky_set_blocking), \
                     patch.object(Path, 'open', flaky_open), contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaisesRegex(RuntimeError, 'host_delivery_uncertain'):
                        launcher.observe_uncertain_host(child, Path(tmp), 'runtime')
                self.assertEqual(child.returncode, 0)
                self.assertEqual(marker.read_text(), 'done')
                self.assertFalse(child.stdin.closed)
            finally:
                if child.poll() is None: child.kill()
                child.wait(timeout=3)
                child.stdin.close(); child.stdout.close(); child.stderr.close()

    def test_success_evidence_requires_order_and_matching_identities(self):
        session = 'a'*32
        goal = '01234567-89ab-cdef-0123-456789abcdef'
        rows = [
            {'event':'stage_receipt','session_id':session},
            {'event':'uuid_request','session_id':session,'goal_id':goal},
            {'event':'dispatched','goal_id':goal},
            {'event':'accepted','goal_id':goal,'accepted':True},
            {'event':'result','goal_id':goal,'status':4,'result':{'state':{'desc':'SUCCEED','state':1101001}}},
            {'event':'worker_finished','session_id':session},
            {'event':'worker_result','returncode':0},
            {'event':'postflight_settled','physical_stop_verified':False},
            {'status':'ACTION_SUCCEEDED_AND_POSTFLIGHT_OBSERVED','goal_id':goal,'physical_stop_verified':False},
        ]
        good = launcher.SuccessEvidence(session)
        for row in rows: good.accept(row)
        self.assertEqual(good.phase, 9)
        for bad_rows in (rows[:4]+rows[5:], rows[:3]+[rows[2]]+rows[3:],
                         rows[:3]+[dict(rows[3], goal_id='f'*36)]+rows[4:],
                         rows[:8]+[dict(rows[8], goal_id='f'*36)],
                         [dict(rows[0],session_id='b'*32)]+rows[1:]):
            with self.subTest(rows=bad_rows), self.assertRaises(RuntimeError):
                evidence = launcher.SuccessEvidence(session)
                for row in bad_rows: evidence.accept(row)

    def test_binding_is_checked_before_passive_robot_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root/'manifest.json'; manifest.write_bytes(b'{}')
            urdf = root/'robot.urdf'; urdf.write_bytes(b'<robot/>\r\n')
            transmissions = root/'sps.yaml'; transmissions.write_bytes(b'transmissions: {}\n')
            review = root/'review.txt'; review.write_text('Technical review; no motion approval.\n')
            retained = root/'binding'
            with patch.object(binding.probe, 'validate', return_value={}):
                result = binding.create(retained, manifest, urdf, transmissions, review)
            args = ['--check', '--binding', str(retained), '--binding-sha256', result['binding_sha256'],
                    '--manifest', str(manifest), '--urdf', str(urdf), '--transmissions', str(transmissions)]
            with patch.object(full_passive, 'main', return_value=0) as passive, \
                 contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(launcher.main(args), 0)
                passive.assert_called_once()
                self.assertIn('BINDING_BYTES_MATCH', output.getvalue())
            urdf.write_bytes(b'<robot/>\n')  # Same logical XML, different bytes.
            with patch.object(full_passive, 'main', side_effect=AssertionError('must not connect')), \
                 contextlib.redirect_stderr(io.StringIO()) as error:
                self.assertEqual(launcher.main(args), 1)
                self.assertIn('candidate_input_changed', error.getvalue())
            with patch.object(full_passive, 'main', side_effect=AssertionError('must not connect')), \
                 contextlib.redirect_stderr(io.StringIO()) as error:
                self.assertEqual(launcher.main(['--check', '--binding', str(retained)]), 1)
                self.assertIn('binding_digest_and_all_candidate_inputs_required', error.getvalue())

    def test_future_run_path_rejects_changed_binding_before_preflight_or_ssh(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root/'manifest.json'; manifest.write_bytes(b'{}')
            urdf = root/'robot.urdf'; urdf.write_bytes(b'<robot/>')
            transmissions = root/'sps.yaml'; transmissions.write_bytes(b'transmissions: {}')
            review = root/'review.txt'; review.write_text('Review with unresolved physical gates.\n')
            retained = root/'binding'
            with patch.object(binding.probe, 'validate', return_value={}):
                result = binding.create(retained, manifest, urdf, transmissions, review)
                manifest.write_bytes(b'{ }')  # Still JSON, but not the reviewed bytes.
                with patch.object(launcher.arm, 'physical_release_gate'), \
                     patch.object(launcher.passive.existing, 'preflight', side_effect=AssertionError('must not connect')), \
                     patch.object(launcher.subprocess, 'Popen', side_effect=AssertionError('must not connect')):
                    with self.assertRaisesRegex(ValueError, 'candidate_input_changed:manifest.json'):
                        launcher.run_candidate(manifest, urdf, transmissions, True,
                            binding_path=retained, binding_sha256=result['binding_sha256'])

    def test_bundles_compile_and_guard_has_independent_cancel_mode(self):
        host, guard, worker = launcher.source_bundle()
        for name, source in (('host',host),('guard',guard),('worker',worker)):
            compile(source, '<'+name+'>', 'exec')
        self.assertIn('guard_can_cancel=True', guard)

    def test_evidence_retains_exact_bundles_inputs_and_rejects_overwrite(self):
        host, guard, worker, sources = launcher.source_bundle(include_sources=True)
        with tempfile.TemporaryDirectory() as tmp:
            outdir = Path(tmp)
            digest = launcher.retain_bundle_evidence(outdir, sources, host, guard, worker,
                                                     b'{"a":1}\n', b'URDF\r\n', b'YAML\n')
            raw = (outdir/'bundle-evidence.json').read_bytes()
            index = json.loads(raw)
            self.assertEqual(digest, hashlib.sha256(raw).hexdigest())
            self.assertEqual(index['review_status'], 'not_reviewed')
            self.assertEqual((outdir/'robot.urdf').read_bytes(), b'URDF\r\n')
            for name, expected in index['sha256'].items():
                self.assertEqual(hashlib.sha256((outdir/name).read_bytes()).hexdigest(), expected)
            self.assertEqual((outdir/'bundle-host.py').read_text(), host)
            launcher.verify_bundle_evidence(outdir, digest)
            (outdir/'bundle-guard.py').write_text('changed')
            with self.assertRaisesRegex(RuntimeError, 'bundle_evidence_changed'):
                launcher.verify_bundle_evidence(outdir, digest)
            with self.assertRaises(FileExistsError):
                launcher.retain_bundle_evidence(outdir, sources, host, guard, worker,
                                                b'other', b'other', b'other')

    def test_host_stream_rejects_before_docker(self):
        host, _, _ = launcher.source_bundle()
        child = execute_streamed(host, {})
        self.assertNotEqual(child.returncode,0)
        self.assertIn('BRIDGE_READY',child.stdout)
        self.assertIn('physical_dispatch_blocked',child.stderr)

    def test_worker_stream_reports_blocked_result_without_goal(self):
        _, _, worker = launcher.source_bundle()
        child = execute_streamed(worker, {'session_id':'a'*32})
        rows=[json.loads(line) for line in child.stdout.splitlines()]
        self.assertEqual(child.returncode,2)
        self.assertIn('worker_error',[x.get('event') for x in rows])
        self.assertEqual(rows[-1],{'event':'worker_result','returncode':2})
        self.assertNotIn('dispatched',[x.get('event') for x in rows])


if __name__ == '__main__':
    unittest.main()
