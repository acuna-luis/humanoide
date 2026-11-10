"""Coordinator integration with fake processes only; no ROS or robot access."""
import json
import contextlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent/'runtime'))
import arm_native_lease_bridge as bridge
import pico_wrist_native_coordinator as coordinator
import prepare_pico_wrist_native_probe as prep
from test_prepare_pico_wrist_native_probe import state, urdf, transmissions
from test_arm_native_lease_bridge import telemetry

GOAL = '12345678-1234-1234-1234-123456789abc'


class FakeGuard:
    def __init__(self, lease):
        self.lease, self.failure, self.latest = lease, None, None
        self.ready_timeout = None
        self.cancelled = []
        self.goal_acknowledged = threading.Event()
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.pump)
        self.thread.start()

    def pump(self):
        while not self.stop_event.wait(.03):
            row = telemetry(time.monotonic(), self.lease.initial)
            if self.goal_acknowledged.is_set():
                row['position'][bridge.arm.ARM_AXIS] += bridge.arm.ARM_STEP
            try:
                self.lease.heartbeat(row)
                self.latest = row
            except Exception as exc:
                self.failure = str(exc); return

    def await_ready(self, timeout):
        self.ready_timeout = timeout
        deadline = time.monotonic()+timeout
        while self.latest is None and time.monotonic() < deadline: time.sleep(.01)
        if self.latest is None: raise RuntimeError('fake_guard_not_ready')

    def exchange(self, request, timeout):
        self.goal_acknowledged.set()
        return dict(request, event='goal_uuid_ready', goal_uuid=request['guard_id'],
                    monotonic=time.monotonic())

    def checked_snapshot(self):
        with self.lease.lock:
            if self.failure or self.lease.failed:
                raise RuntimeError('fake_guard_not_healthy')
            bridge.native.check_lease(self.lease.path, time.monotonic())
            if self.latest is None or time.monotonic()-self.latest['monotonic'] > bridge.MAX_AGE_S:
                raise RuntimeError('fake_guard_stale')
            return self.latest

    def cancel_goal(self, goal_id):
        self.cancelled.append(goal_id)
        return {'goal_id':goal_id, 'request_sent':True, 'physical_stop_verified':False}

    def close(self):
        self.stop_event.set(); self.thread.join(2)


def worker_process(manifest, session, mode):
    candidate = manifest['candidate']
    code = '''import json,sys
candidate=json.loads(sys.argv[1]);session=sys.argv[2];mode=sys.argv[3]
def emit(**row):print(json.dumps(row),flush=True)
emit(event='stage_receipt',session_id=session,receipt={
 'status':'STAGED_NOT_LOADED_OR_EXECUTED','runtime_path':candidate['runtime_path'],
 'sha256':candidate['xml_sha256'],'device':1,'inode':2,'movement_commands':0})
req={'event':'uuid_request','session_id':session,'goal_id':%r,'challenge':'c'*32}
emit(**req)
ack=json.loads(sys.stdin.readline());assert ack==dict(req,event='uuid_ok')
if mode=='crash_before_dispatched':sys.exit(9)
emit(event='dispatched',goal_id=req['goal_id'])
if mode=='crash':sys.exit(9)
emit(event='accepted',goal_id=req['goal_id'],accepted=True)
if mode=='bad_pending':
 emit(event='result_pending',goal_id='00000000-0000-0000-0000-000000000000',status=2,result={});sys.exit(9)
emit(event='result_pending',goal_id=req['goal_id'],status=2,result={})
emit(event='result',goal_id=req['goal_id'],status=4,result={'state':{'state':1101001,'desc':'SUCCEED'}})
emit(event='worker_finished',session_id=session)
emit(event='worker_result',returncode=0)
''' % GOAL
    return subprocess.Popen([sys.executable, '-u', '-c', code, json.dumps(candidate), session, mode],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)


class CoordinatorTests(unittest.TestCase):
    def test_progress_timeout_cannot_rearm(self):
        now = [10.0]
        monitor = coordinator.CoordinatorProgress(clock=lambda: now[0])
        self.assertTrue(monitor.alive())
        monitor.start()
        now[0] += coordinator.COORDINATOR_PROGRESS_TIMEOUT_S + .01
        self.assertFalse(monitor.alive())
        now[0] -= .01
        with self.assertRaisesRegex(RuntimeError, 'coordinator_progress_expired'):
            monitor.beat()
        self.assertFalse(monitor.alive())

    def test_guard_ready_timeout_covers_observed_stop_topic_cadence(self):
        # Its internal preflight/handoff still enforces the separate 30 s TTL.
        self.assertEqual(coordinator.GUARD_READY_TIMEOUT_S, 26.0)
        self.assertLess(coordinator.GUARD_READY_TIMEOUT_S, 30.0)

    def test_blocked_journal_fsync_expires_lease_and_keeps_receipt(self):
        manifest = prep.prepare(state(), urdf(), transmissions())
        with tempfile.TemporaryDirectory() as directory:
            control = Path(directory)/'stable-control'
            control.mkdir(mode=0o700)
            lease = bridge.GuardLease(directory, manifest['input']['reference_20d'], lambda: True)
            guard = FakeGuard(lease)
            processes, errors = [], []
            stalled, release = threading.Event(), threading.Event()
            original_fsync = os.fsync
            journal_calls = [0]

            def delayed_fsync(fd):
                try: name = os.readlink('/proc/self/fd/' + str(fd))
                except OSError: name = ''
                if '/worker-events-' in name:
                    journal_calls[0] += 1
                    # stage receipt, UUID request, then dispatched event.
                    if journal_calls[0] == 3:
                        stalled.set()
                        if not release.wait(4):
                            raise TimeoutError('test_stall_not_released')
                return original_fsync(fd)

            def spawn(_, intent, uid):
                process = worker_process(manifest, lease.session_id, 'success')
                processes.append(process)
                return process

            def invoke():
                try:
                    coordinator.coordinate(lease, guard, manifest, urdf(),
                                           transmissions(), spawn, control, timeout=5)
                except BaseException as exc:
                    errors.append(exc)

            try:
                with patch.object(bridge.arm, 'physical_release_gate'), \
                     patch.object(coordinator, 'GLOBAL_RECEIPT_DIR', control), \
                     patch.object(coordinator, 'COORDINATOR_PROGRESS_TIMEOUT_S', .2), \
                     patch.object(coordinator.os, 'fsync', side_effect=delayed_fsync):
                    thread = threading.Thread(target=invoke)
                    thread.start()
                    try:
                        self.assertTrue(stalled.wait(3), 'journal fsync was not reached')
                        limit = time.monotonic()+2
                        # ``failed`` is set before the zero deadline is fsynced
                        # and replaced; observe the consumer's actual verdict.
                        # Natural expiry is also valid.
                        rejected = False
                        while time.monotonic() < limit:
                            try:
                                bridge.native.check_lease(lease.path, time.monotonic())
                            except (RuntimeError, OSError, ValueError):
                                rejected = True
                                break
                            time.sleep(.02)
                        self.assertTrue(rejected, 'lease remained valid after coordinator stalled')
                    finally:
                        # Always release/join before removing the fake gate and
                        # temporary paths, even if a test assertion fails.
                        release.set()
                        thread.join(3)
                    self.assertFalse(thread.is_alive())
                    self.assertTrue(errors)
                    self.assertIn('coordinator_progress_expired', str(errors[0]))
                    self.assertTrue((control/'PENDING_OR_UNRESOLVED.json').is_file())
                    self.assertEqual(guard.cancelled, [GOAL])
            finally:
                release.set()
                guard.close()
                for process in processes:
                    if process.poll() is None: process.terminate()
                    process.wait(timeout=3)
                    for stream in (process.stdin, process.stdout, process.stderr): stream.close()

    def test_gate_blocks_before_receipt_or_worker(self):
        with self.assertRaisesRegex(RuntimeError, 'physical_dispatch_blocked'):
            coordinator.coordinate(None, None, None, None, None, None, None)

    def test_moving_before_uuid_ack_is_rejected_without_ack(self):
        manifest = prep.prepare(state(), urdf(), transmissions())
        with tempfile.TemporaryDirectory() as directory:
            control = Path(directory)/'stable-control'
            control.mkdir(mode=0o700)
            lease = bridge.GuardLease(directory, manifest['input']['reference_20d'], lambda: True)
            guard = FakeGuard(lease)
            processes = []
            def spawn(_, intent, uid):
                process = worker_process(manifest, lease.session_id, 'success')
                processes.append(process)
                return process
            def moving_snapshot():
                row = telemetry(time.monotonic(), lease.initial)
                row['velocity'][bridge.arm.ARM_AXIS] = .002
                return row
            try:
                with patch.object(bridge.arm, 'physical_release_gate'), \
                     patch.object(coordinator, 'GLOBAL_RECEIPT_DIR', control), \
                     patch.object(guard, 'checked_snapshot', side_effect=moving_snapshot), \
                     patch.object(lease, 'synchronize_uuid') as sync:
                    with self.assertRaisesRegex(ValueError, 'guard_sample_not_stationary_at_reference'):
                        coordinator.coordinate(lease, guard, manifest, urdf(),
                                               transmissions(), spawn, control, timeout=5)
                    sync.assert_not_called()
                self.assertFalse(guard.goal_acknowledged.is_set())
                self.assertTrue(lease.failed)
                events = [json.loads(line) for line in
                          (control/('worker-events-'+lease.session_id+'.jsonl')).read_text().splitlines()]
                self.assertNotIn('dispatched', [row['event'] for row in events])
            finally:
                guard.close()
                for process in processes:
                    if process.poll() is None: process.terminate()
                    process.wait(timeout=3)
                    for stream in (process.stdin, process.stdout, process.stderr): stream.close()

    def exercise(self, mode):
        manifest = prep.prepare(state(), urdf(), transmissions())
        with tempfile.TemporaryDirectory() as directory:
            control = Path(directory)/'stable-control'
            control.mkdir(mode=0o700)
            lease = bridge.GuardLease(directory, manifest['input']['reference_20d'], lambda: True)
            guard = FakeGuard(lease)
            processes = []
            def spawn(_, intent, uid):
                self.assertTrue(Path(intent).is_file())
                process = worker_process(manifest, lease.session_id, 'crash' if mode == 'crash_disk' else mode)
                processes.append(process)
                return process
            def fail_disk():
                lease.failed = True
                raise OSError('simulated lease disk failure')
            try:
                with patch.object(bridge.arm, 'physical_release_gate'), \
                     patch.object(coordinator, 'GLOBAL_RECEIPT_DIR', control), \
                     (patch.object(lease, 'fail', side_effect=fail_disk) if mode == 'crash_disk'
                      else contextlib.nullcontext()):
                    if mode == 'success':
                        result = coordinator.coordinate(lease, guard, manifest, urdf(),
                                                        transmissions(), spawn, control, timeout=5)
                        self.assertEqual(result['status'], 'ACTION_SUCCEEDED_AND_POSTFLIGHT_OBSERVED')
                        self.assertEqual(guard.ready_timeout, coordinator.GUARD_READY_TIMEOUT_S)
                        self.assertFalse(result['physical_stop_verified'])
                    else:
                        if mode == 'bad_pending':
                            with self.assertRaisesRegex(ValueError, 'invalid_pending_result'):
                                coordinator.coordinate(lease, guard, manifest, urdf(),
                                                       transmissions(), spawn, control, timeout=5)
                        else:
                            with self.assertRaisesRegex(RuntimeError, 'worker_terminal_evidence_incomplete'):
                                coordinator.coordinate(lease, guard, manifest, urdf(),
                                                       transmissions(), spawn, control, timeout=5)
                        self.assertTrue(lease.failed)
                self.assertTrue((control/'PENDING_OR_UNRESOLVED.json').is_file())
                events = [json.loads(line) for line in (control/('worker-events-'+lease.session_id+'.jsonl')).read_text().splitlines()]
                self.assertEqual(sum(x.get('event') == 'dispatched' for x in events),
                                 0 if mode == 'crash_before_dispatched' else 1)
                if mode == 'success':
                    self.assertEqual(events[-1]['event'], 'postflight_settled')
                    self.assertEqual(guard.cancelled, [])
                else:
                    self.assertIn('coordinator_failure', [x['event'] for x in events])
                    self.assertEqual(events[-1]['event'], 'independent_cancel_requested')
                    self.assertEqual(guard.cancelled, [GOAL])
                    self.assertFalse(events[-1]['physical_stop_verified'])
                    if mode == 'crash_disk':
                        self.assertIn('lease_revocation_failed', [x['event'] for x in events])
            finally:
                guard.close()
                for process in processes:
                    if process.poll() is None: process.terminate()
                    process.wait(timeout=3)
                    for stream in (process.stdin, process.stdout, process.stderr): stream.close()

    def test_success_requires_native_result_and_observed_settle(self):
        self.exercise('success')

    def test_client_exit_after_dispatch_is_uncertain_and_keeps_receipt(self):
        self.exercise('crash')

    def test_lease_disk_error_does_not_suppress_cancel_after_worker_loss(self):
        self.exercise('crash_disk')

    def test_stationary_elbow_goal_near_boundary_fails_despite_small_drift(self):
        manifest = prep.prepare(state(), urdf(), transmissions())
        initial = manifest['input']['reference_20d']
        sample = telemetry(time.monotonic(), initial)
        sample['position']['R_elbow_yaw_joint'] += .001
        with self.assertRaisesRegex(ValueError, 'stationary_target_outside_guard_sps_warning:R_elbow_yaw_joint'):
            coordinator.check_stationary_targets(manifest, sample, initial)

    def test_foreign_pending_result_is_rejected(self):
        self.exercise('bad_pending')

    def test_worker_loss_after_uuid_ack_before_dispatch_event_is_uncertain(self):
        self.exercise('crash_before_dispatched')

    def test_existing_intent_blocks_without_overwrite(self):
        manifest = prep.prepare(state(), urdf(), transmissions())
        with tempfile.TemporaryDirectory() as directory:
            first = coordinator.durable_intent(directory, manifest, 'a'*32)
            before = first.read_bytes()
            with self.assertRaises(FileExistsError):
                coordinator.durable_intent(directory, manifest, 'b'*32)
            self.assertEqual(first.read_bytes(), before)

    def test_global_receipt_blocks_a_different_session_before_guard_or_worker(self):
        manifest = prep.prepare(state(), urdf(), transmissions())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)/'stable-control'; root.mkdir(mode=0o700)
            coordinator.durable_intent(root, manifest, 'a'*32)
            with patch.object(bridge.arm, 'physical_release_gate'), \
                 patch.object(coordinator, 'GLOBAL_RECEIPT_DIR', root):
                with self.assertRaisesRegex(RuntimeError, 'previous_trial_requires_manual_review'):
                    coordinator.coordinate(None, None, manifest, urdf(), transmissions(), None, root)

    def test_control_root_creation_is_receipted_and_rechecked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)/'stable-control'
            with patch.object(coordinator, 'GLOBAL_RECEIPT_DIR', root):
                receipt = coordinator.ensure_control_root()
                self.assertEqual(receipt['mode'], '0700')
                self.assertTrue((root/'CONTROL_DIRECTORY_CREATED.json').is_file())
                self.assertTrue((root.parent/'.stable-control.create-intent.json').is_file())
                self.assertEqual(coordinator.ensure_control_root(), receipt)
                (root/'CONTROL_DIRECTORY_CREATED.json').write_text('{}')
                with self.assertRaisesRegex(ValueError, 'receipt_mismatch'):
                    coordinator.ensure_control_root()

    def test_interrupted_control_root_creation_retains_intent_and_blocks_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)/'stable-control'
            real_mkdir = coordinator.os.mkdir
            def interrupted(path, mode=0o777, *, dir_fd=None):
                real_mkdir(path, mode, dir_fd=dir_fd)
                raise OSError('simulated interruption after mkdir')
            with patch.object(coordinator, 'GLOBAL_RECEIPT_DIR', root):
                with patch.object(coordinator.os, 'mkdir', side_effect=interrupted):
                    with self.assertRaises(OSError): coordinator.ensure_control_root()
                self.assertTrue(root.is_dir())
                self.assertTrue((root.parent/'.stable-control.create-intent.json').is_file())
                with self.assertRaises(FileNotFoundError): coordinator.ensure_control_root()


if __name__ == '__main__':
    unittest.main()
