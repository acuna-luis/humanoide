"""Offline worker IPC and additive staging tests; no robot/network access."""
import json
import os
import hashlib
from pathlib import Path
import tempfile
import threading
import signal
import select
import subprocess
import time
import unittest
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent/'runtime'))
import pico_wrist_native_worker as worker
import pico_wrist_native_stage as stage
import pico_wrist_native_coordinator as coordinator
import prepare_pico_wrist_native_probe as prep
from test_prepare_pico_wrist_native_probe import state, urdf, transmissions
import test_scenario1_action_client as native_tests

GOAL = '12345678-1234-1234-1234-123456789abc'


class WorkerChannelTests(unittest.TestCase):
    def setUp(self):
        self.in_read, self.in_write = os.pipe()
        self.out_read, self.out_write = os.pipe()
        self.channel = worker.WorkerChannel(self.in_read, self.out_write, 'a'*32)

    def tearDown(self):
        for fd in (self.in_read, self.in_write, self.out_read, self.out_write):
            try: os.close(fd)
            except OSError: pass

    def test_final_lease_read_expiring_during_io_blocks_handshake(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'lease.json'
            path.write_text(json.dumps({'deadline': time.monotonic()+10}))
            lease = worker.LeaseProxy(path, {}, self.channel, {})
            lease.stage_receipt = {}
            original = Path.read_text
            reads = []
            def delayed(file, *args, **kwargs):
                if file == path:
                    reads.append(None)
                    if len(reads) == 3:
                        file.write_text(json.dumps({'deadline': time.monotonic()+.05}))
                        time.sleep(.1)
                return original(file, *args, **kwargs)
            with patch.object(Path, 'read_text', delayed), \
                 patch.object(self.channel, 'prepare_uuid', side_effect=lambda _, check_live: check_live()), \
                 patch.object(worker.staging, 'verify_staged'):
                with self.assertRaisesRegex(RuntimeError, 'expired'):
                    lease.synchronize_uuid(GOAL, None)
            self.assertEqual(len(reads), 3)

    def test_uuid_handshake_waits_for_exact_ack(self):
        errors = []
        def send():
            try: self.channel.prepare_uuid(GOAL)
            except BaseException as exc: errors.append(exc)
        thread = threading.Thread(target=send); thread.start()
        request = json.loads(os.read(self.out_read, 4096))
        self.assertEqual(request['goal_id'], GOAL)
        self.assertTrue(thread.is_alive())
        os.write(self.in_write, (json.dumps(dict(request, event='uuid_ok'))+'\n').encode())
        thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])

    def test_native_fd1_logs_cannot_corrupt_uuid_events_or_targeted_cancel(self):
        # One local child, no ROS, network, or robot. Real native-state-machine
        # and WorkerChannel run with a fake transport; raw C-style fd 1 output
        # must go to stderr while events and UUID handshake remain pure JSON.
        vla = Path(__file__).resolve().parent
        code = r'''
import os,sys
sys.path[:0]=[sys.argv[1],sys.argv[2],sys.argv[3]]
import pico_wrist_native_worker as worker
import pico_wrist_action_client as native
import test_scenario1_action_client as fixtures
fd=worker.isolate_event_stdout()
channel=worker.WorkerChannel(sys.stdin.fileno(),fd,'a'*32)
channel.emit(event='stage_receipt',session_id='a'*32)
os.write(1,b'I2026 native ROSA initialization log\n')
clock=fixtures.FakeClock()
class Transport(fixtures.FakeTransport):
 def send(self,goal):
  channel.prepare_uuid(fixtures.GOAL_ID)
  return super().send(goal)
 def spin(self):
  os.write(1,b'I2026 native ROSA progress log\n')
  return super().spin()
transport=Transport(clock,((.25,fixtures.ACCEPT),))
rc=native.run_action(transport,'motion',{},3,lambda **row:channel.emit(**row),
                     interrupted=lambda: 'test_interruption' if transport.sent and clock.value>=.5 else None,
                     clock=clock,cancel_grace=.5)
channel.emit(event='test_complete',returncode=rc,canceled=transport.canceled)
os.close(fd)
'''
        process = subprocess.Popen([sys.executable, '-B', '-u', '-c', code,
                                    str(vla), str(vla/'runtime'), str(vla.parent/'box_handling')],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
        try:
            def read_event():
                self.assertTrue(select.select([process.stdout], [], [], 3)[0], 'event timeout')
                return json.loads(process.stdout.readline())
            self.assertEqual(read_event()['event'], 'stage_receipt')
            request = read_event()
            self.assertEqual(request['event'], 'uuid_request')
            self.assertEqual(request['goal_id'], GOAL)
            process.stdin.write((json.dumps(dict(request,event='uuid_ok'))+'\n').encode())
            process.stdin.flush()
            rows = []
            while True:
                event = read_event()
                rows.append(event)
                if event['event'] == 'test_complete':
                    break
            self.assertEqual(process.wait(timeout=3), 0)
            self.assertEqual(rows[-1]['canceled'], [GOAL])
            self.assertTrue(any(row.get('event') == 'cancel_requested' and row.get('goal_id') == GOAL
                                for row in rows))
            self.assertIn(b'native ROSA initialization log', process.stderr.read())
            self.assertTrue(all(isinstance(row, dict) for row in rows))
        finally:
            if process.poll() is None: process.kill()  # This exact child is local and simulated.
            process.wait(timeout=3)
            for stream in (process.stdin,process.stdout,process.stderr): stream.close()

    def test_mismatched_uuid_fails_before_send(self):
        errors = []
        def send():
            try: self.channel.prepare_uuid(GOAL)
            except BaseException as exc: errors.append(exc)
        thread = threading.Thread(target=send); thread.start()
        request = json.loads(os.read(self.out_read, 4096))
        ack = dict(request, event='uuid_ok', goal_id='00000000-0000-0000-0000-000000000000')
        os.write(self.in_write, (json.dumps(ack)+'\n').encode())
        thread.join(2)
        self.assertTrue(errors and 'coordinator_ack_mismatch' in str(errors[0]))

    def test_model_ack_binds_deadline_and_is_checked_after_staging(self):
        self.channel.model_mode = True
        errors = []
        def send():
            try: self.channel.prepare_uuid(GOAL)
            except BaseException as exc: errors.append(exc)
        thread = threading.Thread(target=send); thread.start()
        request = json.loads(os.read(self.out_read, 4096))
        ack = dict(request, event='uuid_ok', decision_sha256='f'*64,
                   deadline_monotonic_ns=time.monotonic_ns()+1_000_000_000)
        os.write(self.in_write, (json.dumps(ack)+'\n').encode())
        thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(self.channel.model_decision_sha256, 'f'*64)
        with tempfile.TemporaryDirectory() as directory:
            lease = worker.LeaseProxy(Path(directory)/'lease.json', {}, self.channel, {})
            with patch.object(self.channel, 'prepare_uuid'), patch.object(worker.native, 'check_lease_current'), \
                 patch.object(worker.staging, 'verify_staged',
                              side_effect=lambda *_: setattr(self.channel, 'model_deadline_monotonic_ns',
                                                             time.monotonic_ns()-1)):
                with self.assertRaisesRegex(RuntimeError, 'model_permission_missing_or_expired'):
                    lease.synchronize_uuid(GOAL, None)

    def test_model_ack_expired_or_for_other_goal_is_rejected(self):
        for expired in (True, False):
            self.channel.model_mode = True
            errors = []
            def send():
                try: self.channel.prepare_uuid(GOAL)
                except BaseException as exc: errors.append(exc)
            thread = threading.Thread(target=send); thread.start()
            request = json.loads(os.read(self.out_read, 4096))
            ack = dict(request, event='uuid_ok', decision_sha256='a'*64,
                       deadline_monotonic_ns=time.monotonic_ns()+(-1 if expired else 1_000_000_000))
            if not expired:
                ack['goal_id'] = '00000000-0000-0000-0000-000000000000'
            os.write(self.in_write, (json.dumps(ack)+'\n').encode())
            thread.join(2)
            self.assertFalse(thread.is_alive())
            self.assertTrue(errors, 'model ACK must be rejected')

    def test_missing_ack_is_bounded(self):
        started = time.monotonic()
        with self.assertRaisesRegex(TimeoutError, 'coordinator_ack_timeout'):
            self.channel.prepare_uuid(GOAL)
        self.assertLess(time.monotonic()-started, 1.5)

    def test_lease_expiring_during_task_recheck_blocks_send(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'lease.json'
            path.write_text(json.dumps({'deadline': time.monotonic()+.05}))
            lease = worker.LeaseProxy(path, {}, self.channel, {})
            def slow_verify(*args, **kwargs): time.sleep(.08)
            with patch.object(self.channel, 'prepare_uuid'), \
                 patch.object(worker.staging, 'verify_staged', side_effect=slow_verify):
                with self.assertRaisesRegex(RuntimeError, 'expired'):
                    lease.synchronize_uuid(GOAL, None)

    def test_broken_output_sets_interrupt(self):
        os.close(self.out_read); self.out_read = -1
        self.channel.emit(event='test')
        self.assertEqual(self.channel.interrupted(), 'worker_output_unavailable')

    def test_gate_blocks_before_payload_or_rosa(self):
        with self.assertRaisesRegex(RuntimeError, 'physical_dispatch_blocked'):
            worker.run(None, self.channel)

    def test_signal_after_simulated_dispatch_requests_uuid_cancel(self):
        raw = b'fake installed bytes'; digest = hashlib.sha256(raw).hexdigest()
        manifest = {'input': {'reference_20d': dict(prep.BODY), 'urdf_sha256': digest,
                              'transmissions_sha256': digest}, 'expected_meta_move_sha256': digest}
        payload = {'manifest': manifest, 'urdf_text': urdf(), 'transmissions_text': transmissions(),
                   'lease_path': '/tmp/fake-lease.json', 'session_id': 'a'*32,
                   'intent_path': '/tmp/fake-intent.json', 'intent_uid': os.geteuid()}
        clock = native_tests.FakeClock()
        transport = native_tests.FakeTransport(clock, ((.25, native_tests.ACCEPT),))
        original_spin = transport.spin
        def spin():
            original_spin()
            if transport.sent and clock.value >= .5 and self.channel.signal_received is None:
                os.kill(os.getpid(), signal.SIGTERM)
        transport.spin = spin
        rows = []
        def guarded(_lease, _exchange, _manifest, _urdf, _trans, _emit, *, interrupted,
                    after_transport_ready, verified_provenance=None):
            # Simulate rosa.init replacing the worker's handler; the hook must
            # restore it before the fake action is sent.
            signal.signal(signal.SIGTERM, lambda signum, frame: None)
            after_transport_ready()
            return worker.native.run_action(transport, 'motion', {}, 3,
                        lambda **row: rows.append(row), interrupted, clock=clock, cancel_grace=.5)
        with patch.object(worker.arm, 'physical_release_gate'), \
             patch.dict(os.environ, {'HW_TYPE':'cruzr_s2_v1_sps'}), \
             patch.object(worker.Path, 'read_bytes', return_value=raw), \
             patch.object(worker, 'require_robot_app_can_read_private_task'), \
             patch.object(worker.native, 'check_lease_current'), \
             patch.object(worker.staging, 'stage_task', return_value={}), \
             patch.object(worker.bridge, 'run_guarded_once', side_effect=guarded):
            result = worker.run(payload, self.channel)
        self.assertEqual(result, 3)  # no terminal reply in fake transport
        self.assertEqual(transport.canceled, [native_tests.GOAL_ID])
        self.assertEqual(rows[-1]['event'], 'terminal_unknown')
        self.assertFalse(rows[-1]['physical_stop_verified'])


class StageTests(unittest.TestCase):
    def test_private_task_requires_same_effective_uid(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp)
            app = proc/'65'
            app.mkdir()
            (app/'exe').symlink_to(worker.ROBOT_APP_PATH)
            (app/'status').write_text('Name:\trobot_app\nUid:\t10\t20\t20\t20\n')
            self.assertEqual(worker.require_robot_app_can_read_private_task(proc, worker_uid=20), 20)
            with self.assertRaisesRegex(RuntimeError, 'robot_app_cannot_read'):
                worker.require_robot_app_can_read_private_task(proc, worker_uid=0)

    def test_additive_stage_and_no_overwrite(self):
        bundle = prep.prepare(state(), urdf(), transmissions())
        with tempfile.TemporaryDirectory() as directory:
            intent = coordinator.durable_intent(directory, bundle, 'a'*32)
            receipt = stage.stage_task(bundle, urdf(), transmissions(), root=directory,
                                       intent_path=intent, session_id='a'*32, intent_owner_uid=os.geteuid())
            staged = Path(receipt['runtime_path'])
            self.assertTrue(receipt['directory_created'])
            self.assertEqual(staged.read_text(), bundle['candidate']['xml'])
            self.assertEqual(receipt['sha256'], bundle['candidate']['xml_sha256'])
            self.assertEqual(receipt['movement_commands'], 0)
            self.assertTrue(stage.verify_staged(bundle, receipt, root=directory))
            with self.assertRaises(FileExistsError):
                stage.stage_task(bundle, urdf(), transmissions(), root=directory,
                                 intent_path=intent, session_id='a'*32, intent_owner_uid=os.geteuid())
            self.assertEqual(staged.read_text(), bundle['candidate']['xml'])
            staged.write_text('modified')
            with self.assertRaisesRegex(RuntimeError, 'staged_hash_changed'):
                stage.verify_staged(bundle, receipt, root=directory)

    def test_stage_rejects_symlink_directory_and_tampered_bundle(self):
        bundle = prep.prepare(state(), urdf(), transmissions())
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            intent = coordinator.durable_intent(directory, bundle, 'a'*32)
            (Path(directory)/'diagnostics').symlink_to(outside, target_is_directory=True)
            with self.assertRaises(OSError):
                stage.stage_task(bundle, urdf(), transmissions(), root=directory,
                                 intent_path=intent, session_id='a'*32, intent_owner_uid=os.geteuid())
        bundle['candidate']['target_rad'][-1] += .1
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory)/'diagnostics').mkdir()
            intent = coordinator.durable_intent(directory, bundle, 'a'*32)
            with self.assertRaises(ValueError):
                stage.stage_task(bundle, urdf(), transmissions(), root=directory,
                                 intent_path=intent, session_id='a'*32, intent_owner_uid=os.geteuid())
            self.assertEqual(list((Path(directory)/'diagnostics').iterdir()), [])

    def test_staging_needs_preexisting_matching_intent(self):
        bundle = prep.prepare(state(), urdf(), transmissions())
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory)/'PENDING_OR_UNRESOLVED.json'
            with self.assertRaises(FileNotFoundError):
                stage.stage_task(bundle, urdf(), transmissions(), root=directory,
                                 intent_path=missing, session_id='a'*32, intent_owner_uid=os.geteuid())
            self.assertFalse((Path(directory)/'diagnostics').exists())
            intent = coordinator.durable_intent(directory, bundle, 'a'*32)
            with self.assertRaisesRegex(ValueError, 'stage_intent_mismatch'):
                stage.stage_task(bundle, urdf(), transmissions(), root=directory,
                                 intent_path=intent, session_id='b'*32, intent_owner_uid=os.geteuid())
            self.assertFalse((Path(directory)/'diagnostics').exists())

    def test_expected_intent_owner_and_staged_owner_are_enforced(self):
        bundle = prep.prepare(state(), urdf(), transmissions())
        with tempfile.TemporaryDirectory() as directory:
            intent = coordinator.durable_intent(directory, bundle, 'a'*32)
            owner = Path(directory).stat().st_uid
            with self.assertRaisesRegex(ValueError, 'intent_directory_not_private_or_owned'):
                stage.stage_task(bundle, urdf(), transmissions(), root=directory,
                                 intent_path=intent, session_id='a'*32, intent_owner_uid=owner+1)
            self.assertFalse((Path(directory)/'diagnostics').exists())
            result = stage.stage_task(bundle, urdf(), transmissions(), root=directory,
                                      intent_path=intent, session_id='a'*32, intent_owner_uid=owner)
            self.assertTrue(Path(result['runtime_path']).is_file())


if __name__ == '__main__':
    unittest.main()
