"""Guard lease and native handshake tests, offline with simulated processes."""
import json
import io
import os
import select
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import types
from pathlib import Path
from unittest.mock import patch

import arm_native_lease_bridge as bridge
import test_scenario1_action_client as box_tests


def telemetry(now, initial=None):
    initial = dict(bridge.arm.BODY) if initial is None else dict(initial)
    return {'event': 'telemetry', 'goal_uuid': 'a' * 32, 'monotonic': now,
            'position': initial, 'velocity': {n: 0.0 for n in initial},
            'estop': 0, 'servo_stop': 0}


class LeaseTests(unittest.TestCase):
    def test_uuid_ack_can_expire_while_waiting_for_lease_lock(self):
        # Reproduce the current fail-closed limitation without a fake clock:
        # the ACK is fresh when returned by the transport, but an ongoing
        # lease operation can hold the lock until that ACK is too old.
        with tempfile.TemporaryDirectory() as directory:
            lease = bridge.GuardLease(directory, dict(bridge.arm.BODY), lambda: True)
            lease.heartbeat(telemetry(time.monotonic()))
            exchange_started = threading.Event(); return_ack = threading.Event()
            ack_returned = threading.Event()
            response = {}
            def exchange(request, timeout):
                exchange_started.set()
                if not return_ack.wait(2): raise TimeoutError('test_ack_not_released')
                ack = dict(request, event='goal_uuid_ready', goal_uuid='a'*32,
                           monotonic=time.monotonic())
                response['returned_at'] = time.monotonic()
                ack_returned.set()
                return ack
            def handshake():
                try:
                    lease.synchronize_uuid(box_tests.GOAL_ID, exchange)
                except Exception as exc:
                    response['error'] = exc
            thread = threading.Thread(target=handshake)
            thread.start()
            try:
                self.assertTrue(exchange_started.wait(2))
                with lease.lock:
                    return_ack.set()
                    self.assertTrue(ack_returned.wait(2))
                    self.assertLess(time.monotonic()-response['returned_at'], .2)
                    time.sleep(bridge.MAX_AGE_S + .1)
                    self.assertTrue(thread.is_alive())
            finally:
                return_ack.set()
                thread.join(3)
            self.assertFalse(thread.is_alive())
            self.assertIsInstance(response.get('error'), RuntimeError)
            self.assertEqual(str(response['error']), 'uuid_handshake_invalid_ack')
            self.assertTrue(lease.failed)
            self.assertIsNone(lease.goal_id)

    def test_guard_heartbeat_is_required_and_fault_is_permanent(self):
        clock = box_tests.FakeClock(); clock.value = 1.0
        with tempfile.TemporaryDirectory() as directory:
            gate = bridge.GuardLease(directory, dict(bridge.arm.BODY), lambda: True, clock=clock)
            with self.assertRaises(RuntimeError):
                bridge.native.check_lease_current(gate.path, clock)
            gate.heartbeat(telemetry(clock()))
            bridge.native.check_lease_current(gate.path, clock)
            clock.value += .1
            bad = telemetry(clock()); bad['position']['L_elbow_yaw_joint'] += .003
            with self.assertRaises(ValueError):
                gate.heartbeat(bad)
            with self.assertRaises(RuntimeError):
                bridge.native.check_lease_current(gate.path, clock)
            with self.assertRaises(RuntimeError):
                gate.heartbeat(telemetry(clock()))

    def test_stale_duplicate_guard_id_and_stops_fail_closed(self):
        for change in ('stale', 'duplicate', 'guard_id', 'estop'):
            clock = box_tests.FakeClock(); clock.value = 5.0
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                gate = bridge.GuardLease(directory, dict(bridge.arm.BODY), lambda: True, clock=clock)
                gate.heartbeat(telemetry(clock()))
                clock.value += .1
                event = telemetry(clock())
                if change == 'stale': event['monotonic'] -= 1
                if change == 'duplicate': event['monotonic'] -= .1
                if change == 'guard_id': event['goal_uuid'] = 'b' * 32
                if change == 'estop': event['estop'] = 1
                with self.assertRaises(ValueError): gate.heartbeat(event)
                self.assertTrue(gate.failed)
                self.assertEqual(json.loads(gate.path.read_text())['deadline'], 0)

    def test_lost_simulated_guard_process_expires_lease(self):
        event = telemetry(time.monotonic())
        child = subprocess.Popen([sys.executable, '-u', '-c',
            'import json,time;print(' + repr(json.dumps(event)) + ',flush=True);time.sleep(20)'],
            stdout=subprocess.PIPE, text=True)
        try:
            with tempfile.TemporaryDirectory() as directory:
                gate = bridge.GuardLease(directory, dict(bridge.arm.BODY),
                                         lambda: child.poll() is None)
                gate.heartbeat(json.loads(child.stdout.readline()))
                child.terminate(); child.wait(timeout=3)
                time.sleep(bridge.LEASE_S + .1)
                with self.assertRaises(RuntimeError):
                    bridge.native.check_lease_current(gate.path, time.monotonic)
        finally:
            if child.poll() is None: child.kill()
            child.wait(timeout=3)
            child.stdout.close()

    def test_concurrent_fault_cannot_be_overwritten_by_heartbeat(self):
        clock = box_tests.FakeClock(); clock.value = 2.0
        with tempfile.TemporaryDirectory() as directory:
            gate = bridge.GuardLease(directory, dict(bridge.arm.BODY), lambda: True, clock=clock)
            started, release = threading.Event(), threading.Event()
            original = gate._write
            def delayed(deadline):
                if deadline > 0:
                    started.set()
                    if not release.wait(2): raise RuntimeError('test timed out')
                original(deadline)
            with patch.object(gate, '_write', side_effect=delayed):
                heartbeat = threading.Thread(target=gate.heartbeat, args=(telemetry(clock()),))
                fault = threading.Thread(target=gate.fail)
                heartbeat.start(); self.assertTrue(started.wait(2))
                fault.start(); release.set()
                heartbeat.join(2); fault.join(2)
            self.assertFalse(heartbeat.is_alive() or fault.is_alive())
            self.assertTrue(gate.failed)
            self.assertEqual(json.loads(gate.path.read_text())['deadline'], 0)

    def test_async_revocation_stops_renewal_even_if_write_is_in_flight(self):
        clock = box_tests.FakeClock(); clock.value = 2.0
        with tempfile.TemporaryDirectory() as directory:
            gate = bridge.GuardLease(directory, dict(bridge.arm.BODY), lambda: True, clock=clock)
            began, release = threading.Event(), threading.Event()
            original = gate._write
            def delayed(deadline):
                if deadline > 0:
                    began.set()
                    if not release.wait(2): raise RuntimeError('test timed out')
                original(deadline)
            with patch.object(gate, '_write', side_effect=delayed):
                writer = threading.Thread(target=gate.heartbeat, args=(telemetry(clock()),))
                writer.start(); self.assertTrue(began.wait(2))
                done = gate.fail_async()
                self.assertTrue(gate.failed)
                self.assertFalse(done.is_set())
                self.assertIs(done, gate.fail_async())
                release.set(); writer.join(2)
                self.assertTrue(done.wait(2))
            self.assertEqual(json.loads(gate.path.read_text())['deadline'], 0)
            with self.assertRaises(RuntimeError): gate.heartbeat(telemetry(clock()))

    def test_invalid_sample_is_never_published_as_latest(self):
        child = simulated_guard('d'*32, 'bad_observation')
        try:
            with tempfile.TemporaryDirectory() as directory:
                lease = bridge.GuardLease(directory, dict(bridge.arm.BODY),
                                          lambda: child.poll() is None, session_id='d'*32)
                pipe = bridge.GuardPipe(child, lease, time.monotonic())
                pipe.await_ready(3)
                lease.synchronize_uuid(box_tests.GOAL_ID, pipe.exchange)
                deadline = time.monotonic()+2
                while not lease.failed and time.monotonic()<deadline: time.sleep(.01)
                self.assertTrue(lease.failed)
                self.assertEqual(pipe.latest['position'], dict(bridge.arm.BODY))
                with self.assertRaisesRegex(RuntimeError, 'guard_not_healthy'):
                    pipe.checked_snapshot()
        finally:
            if child.poll() is None: child.terminate()
            child.wait(timeout=3)
            for stream in (child.stdin, child.stdout, child.stderr): stream.close()

    def test_expired_lease_cancels_exact_simulated_native_goal(self):
        clock = box_tests.FakeClock(); clock.value = 1.0
        with tempfile.TemporaryDirectory() as directory:
            gate = bridge.GuardLease(directory, dict(bridge.arm.BODY), lambda: True, clock=clock)
            gate.heartbeat(telemetry(clock()))
            transport = box_tests.FakeTransport(clock, ((1.25, box_tests.ACCEPT),))
            rows = []
            result = bridge.native.run_action(transport, 'motion', {'task_name': 'probe', 'yaml_args': '{}'},
                3.0, lambda **row: rows.append(row), lease_file=gate.path, clock=clock, cancel_grace=.5)
            self.assertEqual(result, 3)
            self.assertEqual(transport.sent, 1)
            self.assertEqual(transport.canceled, [box_tests.GOAL_ID])
            self.assertEqual(rows[-1]['event'], 'terminal_unknown')
            self.assertFalse(rows[-1]['physical_stop_verified'])


class HandshakeTests(unittest.TestCase):
    def gate(self, directory, clock):
        gate = bridge.GuardLease(directory, dict(bridge.arm.BODY), lambda: True, clock=clock)
        gate.heartbeat(telemetry(clock()))
        return gate

    def test_exact_uuid_ack_required_and_lease_not_extended(self):
        clock = box_tests.FakeClock(); clock.value = 10.0
        with tempfile.TemporaryDirectory() as directory:
            gate = self.gate(directory, clock)
            def exchange(request, timeout):
                self.assertEqual(timeout, bridge.HANDSHAKE_S)
                return dict(request, event='goal_uuid_ready', goal_uuid=request['guard_id'], monotonic=clock())
            gate.synchronize_uuid(box_tests.GOAL_ID, exchange)
            self.assertEqual(gate.goal_id, box_tests.GOAL_ID)
            clock.value += bridge.LEASE_S + .01
            with self.assertRaises(RuntimeError):
                bridge.native.check_lease_current(gate.path, clock)

    def test_mismatched_and_late_ack_fail_closed(self):
        for kind in ('mismatch', 'late'):
            clock = box_tests.FakeClock(); clock.value = 10.0
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                gate = self.gate(directory, clock)
                def exchange(request, timeout):
                    if kind == 'late': clock.value += timeout + .01
                    ack = dict(request, event='goal_uuid_ready', goal_uuid=request['guard_id'], monotonic=clock())
                    if kind == 'mismatch': ack['goal_id'] = 'b' * 36
                    return ack
                with self.assertRaises(RuntimeError):
                    gate.synchronize_uuid(box_tests.GOAL_ID, exchange)
                self.assertTrue(gate.failed)
                self.assertIsNone(gate.goal_id)

    def test_pc_or_coordinator_loss_during_ack_never_grants_send(self):
        for failed in ('pc', 'coordinator'):
            clock = box_tests.FakeClock(); clock.value = 10.0
            live = {'pc': True, 'coordinator': True}
            with self.subTest(failed=failed), tempfile.TemporaryDirectory() as directory:
                gate = bridge.GuardLease(directory, dict(bridge.arm.BODY),
                                         lambda: live['pc'] and live['coordinator'], clock=clock)
                gate.heartbeat(telemetry(clock()))
                def exchange(request, timeout):
                    live[failed] = False
                    return dict(request, event='goal_uuid_ready', goal_uuid=request['guard_id'], monotonic=clock())
                with self.assertRaisesRegex(RuntimeError, 'uuid_handshake_failed'):
                    gate.synchronize_uuid(box_tests.GOAL_ID, exchange)
                self.assertTrue(gate.failed)
                self.assertIsNone(gate.goal_id)

    def test_supervisor_pulse_requires_live_pc_and_coordinator(self):
        for failed in ('pc', 'coordinator'):
            live = {'pc': True, 'coordinator': True}
            pipe = object.__new__(bridge.GuardPipe)
            pipe.lease = types.SimpleNamespace(session_id='a'*32, failed=False,
                                               guard_alive=lambda: live['pc'] and live['coordinator'])
            pipe.guard_id = 'b'*32
            pipe.heartbeat_sequence = 0
            rows = []
            pipe._send = lambda row, deadline: rows.append(row)
            pipe._send_guard_heartbeat()
            self.assertEqual(rows[0]['sequence'], 0)
            live[failed] = False
            with self.assertRaisesRegex(RuntimeError, 'guard_heartbeat_requires_live_supervisor'):
                pipe._send_guard_heartbeat()
            self.assertEqual(len(rows), 1)

    def test_ack_happens_before_native_request_can_be_sent(self):
        events = []
        class FakeBase:
            def __init__(self): self._goal_handles = {}
            def create_goal_request(self, goal, options=None):
                events.append('created')
                self._goal_handles[box_tests.GOAL_ID] = object()
                return object(), box_tests.GOAL_ID
            def send_goal_async(self, goal, options=None):
                request, ident = self.create_goal_request(goal, options)
                events.append('wire_send')
                return ident
        def handshake(ident):
            self.assertEqual(ident, box_tests.GOAL_ID)
            self.assertEqual(events, ['created'])
            events.append('guard_ack')
        cls = bridge.synchronized_client_class(FakeBase, lambda x: x, handshake)
        client = cls(); client.configure_observer(lambda *a, **kw: None)
        client.send_goal_async({})
        self.assertEqual(events, ['created', 'guard_ack', 'wire_send'])

    def test_failed_handshake_has_no_send_or_cancel_identity(self):
        events = []
        class FakeBase:
            def __init__(self): self._goal_handles = {}
            def create_goal_request(self, goal, options=None):
                self._goal_handles[box_tests.GOAL_ID] = object()
                return object(), box_tests.GOAL_ID
            def send_goal_async(self, goal, options=None):
                self.create_goal_request(goal, options)
                events.append('wire_send')
        def fail(_): raise TimeoutError('no guard ACK')
        cls = bridge.synchronized_client_class(FakeBase, lambda x: x, fail)
        client = cls(); client.configure_observer(lambda *a, **kw: None)
        with self.assertRaises(TimeoutError): client.send_goal_async({})
        self.assertEqual(events, [])
        self.assertIsNone(client.observed_goal_id)
        self.assertEqual(client._goal_handles, {})

    def test_cli_never_runs(self):
        with patch('sys.stderr'):
            self.assertEqual(bridge.main(), 2)

    def test_real_transport_remains_blocked_before_rosa_import(self):
        with self.assertRaisesRegex(RuntimeError, 'physical_dispatch_blocked'):
            bridge.GuardedRosaTransport(None, None)
        with self.assertRaisesRegex(RuntimeError, 'physical_dispatch_blocked'):
            bridge.run_guarded_once(None, None, None, None, None, lambda **row: None)

    def test_model_mode_starts_action_timeout_after_permit_and_send(self):
        manifest = {'candidate': {'goal': {'task_name':'probe', 'yaml_args':'{}'}},
                    'input': {'reference_20d':dict(bridge.arm.BODY)}}
        for model_mode in (False, True):
            channel = types.SimpleNamespace(session_id='a'*32, model_mode=model_mode)
            lease = types.SimpleNamespace(channel=channel, manifest=manifest,
                                          initial=dict(bridge.arm.BODY), path='/tmp/lease',
                                          fail=lambda:None)
            transport = types.SimpleNamespace(close=lambda:None)
            with self.subTest(model_mode=model_mode), \
                 patch.object(bridge.probe, 'validate'), \
                 patch.object(bridge.native, 'validate_goal', return_value=manifest['candidate']['goal']), \
                 patch.object(bridge, 'GuardedRosaTransport', return_value=transport), \
                 patch.object(bridge.native, 'run_action', return_value=0) as run:
                bridge.run_guarded_once(lease, None, manifest, '', '', lambda **row:None,
                    verified_provenance=('worker','a'*32,'b'*64,'c'*64))
                self.assertEqual(run.call_args.kwargs.get('deadline_after_send', False), model_mode)

    def test_fake_lease_cannot_construct_native_transport(self):
        from types import SimpleNamespace
        provenance = ('worker', 'a'*32, 'b'*64, 'c'*64)
        fake = SimpleNamespace(channel=SimpleNamespace(session_id='a'*32), path=None,
                               stage_receipt={})
        with self.assertRaisesRegex(ValueError, 'worker_lease_or_stage_missing'):
            bridge.GuardedRosaTransport(fake, None, verified_provenance=provenance,
                                        session_id='a'*32)

    def test_transport_rejects_goal_not_equal_to_staged_task_before_rosa(self):
        import pico_wrist_native_worker as worker
        import pico_wrist_native_stage as stage
        in_read, in_write = os.pipe()
        out_read, out_write = os.pipe()
        try:
            channel = worker.WorkerChannel(in_read, out_write, 'a'*32)
            manifest = {'candidate':{'task_name':'diagnostics/pico_v4_wrist_'+'1'*16,
                                     'goal':{'task_name':'cruzr/home','yaml_args':'{}'}}}
            lease = worker.LeaseProxy('/tmp/lease.json', {}, channel, manifest)
            lease.stage_receipt = {'placeholder':True}
            with patch.object(stage, 'verify_staged'), patch.object(bridge.probe, 'validate'):
                with self.assertRaisesRegex(ValueError, 'worker_goal_not_staged_task'):
                    bridge.GuardedRosaTransport(lease, None,
                        verified_provenance=('worker','a'*32,'b'*64,'c'*64), session_id='a'*32)
        finally:
            for fd in (in_read,in_write,out_read,out_write): os.close(fd)

    def test_only_staged_goal_may_be_attempted_once_even_after_uncertain_send(self):
        from types import SimpleNamespace
        import pico_wrist_native_stage as stage
        goal = {'task_name':'diagnostics/wrist', 'yaml_args':'{}'}
        lease = SimpleNamespace(manifest={'candidate':{'goal':goal}}, stage_receipt={},
                                path='/tmp/fake.json', channel=SimpleNamespace(interrupted=lambda: None))
        transport = object.__new__(bridge.GuardedRosaTransport)
        transport._wrist_lease, transport._wrist_goal, transport._wrist_attempted = lease, goal, False
        with patch.object(stage, 'verify_staged'), patch.object(bridge.native, 'check_lease_current'), \
             patch.object(bridge.native.RosaTransport, 'send', side_effect=OSError('delivery_unknown')) as send:
            with self.assertRaisesRegex(ValueError, 'unexpected_or_repeated_wrist_goal'):
                transport.send({'task_name':'cruzr/home', 'yaml_args':'{}'})
            send.assert_not_called()
            with self.assertRaisesRegex(OSError, 'delivery_unknown'):
                transport.send(dict(goal))
            with self.assertRaisesRegex(ValueError, 'unexpected_or_repeated_wrist_goal'):
                transport.send(dict(goal))
            send.assert_called_once()


def simulated_guard(session, mode):
    """Child uses real pipes and monotonic clock but never imports ROS."""
    code = '''import json,select,sys,time
session,mode=sys.argv[1:3]
guard='a'*32
body=json.loads(sys.argv[3])
def emit(event,**kwargs):
 print(json.dumps(dict(event=event,goal_uuid=guard,monotonic=time.monotonic(),**kwargs)),flush=True)
def telemetry():
 emit('telemetry',position=body,velocity={n:0.0 for n in body},estop=0,servo_stop=0)
emit('BRIDGE_READY')
telemetry()
emit('pre_dispatch_ready',session_id=session,challenge='c'*32)
ack=json.loads(sys.stdin.readline())
assert ack['session_id']==session and ack['challenge']=='c'*32
telemetry()
emit('ARM_GUARD_READY',session_id=session,movement_commands=0,physical_control_qualified=False)
injected=False
next_sample=time.monotonic()+.1
while True:
 ready,_,_=select.select([sys.stdin],[],[],.05)
 if ready:
  line=sys.stdin.readline()
  if not line: break
  cmd=json.loads(line)
  if cmd['event']=='stop_guard':
   if mode=='bad_stop_ack':
    emit('ARM_GUARD_STOPPED',movement_commands=0,physical_stop_confirmed=True)
   else:
    emit('ARM_GUARD_STOPPED',movement_commands=0,physical_stop_confirmed=False)
   break
  if cmd['event']=='prepare_goal_uuid' and mode!='no_ack':
   cmd['event']='goal_uuid_ready'
   if mode=='bad_ack':cmd['goal_id']='00000000-0000-0000-0000-000000000000'
   emit(**cmd)
   if mode=='guard_fault':
    emit('OPERATOR_ALERT',reason='outside_nominal_sps_limit:R_elbow_yaw_joint',no_retry=True,physical_stop_confirmed=False)
    break
   if mode=='bad_observation' and not injected:
    time.sleep(.1)
    bad=dict(body);bad['L_elbow_yaw_joint']+=.003
    emit('telemetry',position=bad,velocity={n:0.0 for n in body},estop=0,servo_stop=0);injected=True
  if cmd['event']=='cancel_goal_uuid':
   cmd['event']='guard_cancel_requested';cmd['physical_stop_confirmed']=False;emit(**cmd)
 if mode!='cancel' or time.monotonic()>=next_sample:
  telemetry();next_sample=time.monotonic()+.1
'''
    return subprocess.Popen([sys.executable, '-u', '-c', code, session, mode,
                             json.dumps(bridge.arm.BODY)], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)


class GuardPipeProcessTests(unittest.TestCase):
    def test_initial_renewal_that_expires_never_advertises_readiness(self):
        child = simulated_guard('d'*32, 'success')
        release = threading.Event()
        try:
            with tempfile.TemporaryDirectory() as directory:
                lease = bridge.GuardLease(directory, dict(bridge.arm.BODY),
                                          lambda: child.poll() is None, session_id='d'*32)
                began = threading.Event(); original = lease._write
                def stalled(deadline):
                    if deadline > 0:
                        began.set()
                        if not release.wait(4): raise RuntimeError('test_stall_not_released')
                    original(deadline)
                with patch.object(lease, '_write', side_effect=stalled):
                    pipe = bridge.GuardPipe(child, lease, time.monotonic(), enable_guard_heartbeat=True)
                    self.assertTrue(began.wait(2))
                    time.sleep(bridge.LEASE_S+.05)
                    release.set()
                    with self.assertRaisesRegex(RuntimeError, 'continuous_guard_not_ready'):
                        pipe.await_ready(3)
                    self.assertEqual(pipe.heartbeat_sequence, 0)
                    self.assertTrue(lease.failed)
                    self.assertTrue(lease._async_failure_done.wait(2))
                    self.assertEqual(json.loads(lease.path.read_text())['deadline'], 0)
        finally:
            release.set()
            if child.poll() is None: child.terminate()
            child.wait(timeout=3)
            for stream in (child.stdin, child.stdout, child.stderr): stream.close()

    def test_stop_ack_is_processed_before_immediate_eof(self):
        for valid in (True, False):
            with self.subTest(valid=valid), tempfile.TemporaryDirectory() as directory:
                lease = bridge.GuardLease(directory, dict(bridge.arm.BODY), lambda: True,
                                          session_id='d'*32)
                row = {'event':'ARM_GUARD_STOPPED', 'goal_uuid':'a'*32,
                       'movement_commands':0, 'physical_stop_confirmed':not valid}
                pipe = object.__new__(bridge.GuardPipe)
                pipe.process = types.SimpleNamespace(stdout=io.BytesIO((json.dumps(row)+'\n').encode()))
                pipe.lease = lease; pipe.stopping = True; pipe.stop_ack = False
                pipe.channel_failed = False; pipe.failure = None; pipe.guard_id = 'a'*32
                pipe.ready = threading.Event(); pipe.ready.set()
                pipe._guard_input = bridge.queue.Queue(maxsize=2)
                pipe._guard_transport_done = threading.Event(); pipe._normal_queue_failed = False
                pipe._read_transport()
                self.assertFalse(pipe.channel_failed)
                pipe._reader()
                self.assertEqual(pipe.stop_ack, valid)
                self.assertEqual(pipe.channel_failed, not valid)
                if not valid: self.assertTrue(lease._async_failure_done.wait(2))

    def test_stalled_renewal_does_not_block_exact_cancel_ack(self):
        child = simulated_guard('d'*32, 'cancel')
        release = threading.Event()
        try:
            with tempfile.TemporaryDirectory() as directory:
                lease = bridge.GuardLease(directory, dict(bridge.arm.BODY),
                                          lambda: child.poll() is None, session_id='d'*32)
                pipe = bridge.GuardPipe(child, lease, time.monotonic(), enable_guard_heartbeat=True)
                try:
                    pipe.await_ready(3)
                    lease.synchronize_uuid(box_tests.GOAL_ID, pipe.exchange)
                    began = threading.Event(); original = lease._write
                    def stalled(deadline):
                        if deadline > 0:
                            began.set()
                            if not release.wait(4): raise RuntimeError('test_stall_not_released')
                        original(deadline)
                    with patch.object(lease, '_write', side_effect=stalled):
                        self.assertTrue(began.wait(2))
                        old = pipe.latest; sequence = pipe.heartbeat_sequence
                        started = time.monotonic()
                        result = pipe.cancel_goal(box_tests.GOAL_ID)
                        self.assertTrue(result['request_sent'])
                        self.assertTrue(result['lease_revocation_pending'])
                        self.assertFalse(result['physical_stop_verified'])
                        self.assertLess(time.monotonic()-started, 1)
                        # Returning a late positive write cannot publish the
                        # observation or rearm a failed lease/heartbeat.
                        time.sleep(bridge.LEASE_S+.05)
                        release.set()
                        self.assertTrue(lease._async_failure_done.wait(2))
                        self.assertEqual(json.loads(lease.path.read_text())['deadline'], 0)
                        self.assertIs(pipe.latest, old)
                        self.assertEqual(pipe.heartbeat_sequence, sequence)
                        self.assertTrue(lease.failed)
                finally:
                    # Failure during handshake can still start asynchronous
                    # revocation, which must finish before deleting its dir.
                    release.set()
                    if child.poll() is None: child.terminate()
                    child.wait(timeout=3)
                    pipe.transport_thread.join(3)
                    pipe.thread.join(3)
                    if lease._async_failure_thread is not None:
                        self.assertTrue(lease._async_failure_done.wait(3))
        finally:
            release.set()
            if child.poll() is None: child.terminate()
            child.wait(timeout=3)
            for stream in (child.stdin, child.stdout, child.stderr): stream.close()

    def test_full_event_queue_fails_closed_but_retains_cancel_channel(self):
        child = simulated_guard('d'*32, 'cancel')
        release = threading.Event()
        try:
            with patch.object(bridge, 'MAX_GUARD_EVENTS', 2), tempfile.TemporaryDirectory() as directory:
                lease = bridge.GuardLease(directory, dict(bridge.arm.BODY),
                                          lambda: child.poll() is None, session_id='d'*32)
                pipe = bridge.GuardPipe(child, lease, time.monotonic())
                pipe.await_ready(3)
                lease.synchronize_uuid(box_tests.GOAL_ID, pipe.exchange)
                began = threading.Event(); original = lease._write
                def stalled(deadline):
                    if deadline > 0:
                        began.set()
                        if not release.wait(4): raise RuntimeError('test_stall_not_released')
                    original(deadline)
                with patch.object(lease, '_write', side_effect=stalled):
                    self.assertTrue(began.wait(2))
                    deadline = time.monotonic()+2
                    while not pipe._normal_queue_failed and time.monotonic()<deadline:
                        time.sleep(.01)
                    self.assertEqual(pipe.failure, 'guard_event_queue_saturated')
                    self.assertTrue(lease.failed)
                    self.assertFalse(pipe.channel_failed)
                    self.assertTrue(pipe.cancel_goal(box_tests.GOAL_ID)['request_sent'])
                    release.set()
                    self.assertTrue(lease._async_failure_done.wait(2))
        finally:
            release.set()
            if child.poll() is None: child.terminate()
            child.wait(timeout=3)
            for stream in (child.stdin, child.stdout, child.stderr): stream.close()

    def test_renewal_stall_keeps_watchdog_cancel_observable(self):
        # Real GuardPipe and SupervisorHeartbeat over process pipes; ROS and
        # physical movement are simulated. This observes a different fault
        # from the zero-deadline fsync test below: the renewal thread blocks in
        # an in-flight positive lease write while the transport reader remains
        # able to report the independent simulated watchdog cancellation.
        code = r'''import json,os,select,sys,time
sys.path.insert(0, sys.argv[1])
from arm_from_pico_supervised import SupervisorHeartbeat
session=sys.argv[2]; body=json.loads(sys.argv[3]); guard='a'*32
watchdog=SupervisorHeartbeat(session,guard); own=None; fault=False; buf=b''
os.set_blocking(1,False)
def emit(event,**fields):
 data=(json.dumps(dict(event=event,goal_uuid=guard,monotonic=time.monotonic(),**fields))+'\n').encode()
 try: os.write(1,data)
 except BlockingIOError: pass
def telemetry(): emit('telemetry',position=body,velocity={n:0.0 for n in body},estop=0,servo_stop=0)
emit('BRIDGE_READY'); telemetry(); emit('pre_dispatch_ready',session_id=session,challenge='c'*32)
ack=json.loads(sys.stdin.readline()); assert ack['session_id']==session
telemetry(); emit('ARM_GUARD_READY',session_id=session,movement_commands=0,physical_control_qualified=False)
next_sample=time.monotonic()
while True:
 now=time.monotonic()
 if own is not None and not fault:
  try: watchdog.require_fresh(now)
  except ValueError:
   fault=True
   os.write(2,('simulated_watchdog_cancel:'+own+'\n').encode())
   emit('guard_auto_cancel_requested',reason='supervisor_heartbeat_expired',physical_stop_confirmed=False)
 if not fault and now>=next_sample:
  telemetry(); next_sample=now+.1
 readable,_,_=select.select([0],[],[],.01)
 if readable:
  block=os.read(0,4096)
  if not block: break
  buf+=block
  while b'\n' in buf:
   line,buf=buf.split(b'\n',1); row=json.loads(line)
   if fault: continue
   if row['event']=='supervisor_heartbeat': watchdog.accept(row,time.monotonic())
   elif row['event']=='prepare_goal_uuid':
    watchdog.require_fresh(time.monotonic()); own=row['goal_id']
    row['event']='goal_uuid_ready'; emit(**row)
'''
        session = 'd' * 32
        child = subprocess.Popen([sys.executable, '-B', '-u', '-c', code,
                                  str(Path(__file__).resolve().parent/'runtime'),
                                  session, json.dumps(bridge.arm.BODY)],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, bufsize=0)
        pipe = None
        release = threading.Event()
        try:
            with tempfile.TemporaryDirectory() as directory:
                lease = bridge.GuardLease(directory, dict(bridge.arm.BODY),
                                          lambda: child.poll() is None, session_id=session)
                pipe = bridge.GuardPipe(child, lease, time.monotonic(), enable_guard_heartbeat=True)
                pipe.await_ready(3)
                lease.synchronize_uuid(box_tests.GOAL_ID, pipe.exchange)
                began = threading.Event()
                original = lease._write
                def stalled_renewal(deadline):
                    if deadline > 0:
                        began.set()
                        if not release.wait(4): raise RuntimeError('test_stall_not_released')
                    original(deadline)
                try:
                    with patch.object(lease, '_write', side_effect=stalled_renewal):
                        self.assertTrue(began.wait(2), 'reader did not enter lease renewal')
                        readable, _, _ = select.select([child.stderr], [], [], 3)
                        self.assertTrue(readable, 'independent simulated watchdog did not fire')
                        marker = child.stderr.readline().decode().strip()
                        self.assertEqual(marker, 'simulated_watchdog_cancel:'+box_tests.GOAL_ID)
                        deadline = time.monotonic()+1
                        while not pipe.auto_cancel_requested and time.monotonic()<deadline:
                            time.sleep(.01)
                        self.assertTrue(pipe.auto_cancel_requested)
                        result = pipe.cancel_goal(box_tests.GOAL_ID)
                        self.assertTrue(result['automatic'])
                        self.assertTrue(result['request_sent'])
                        self.assertTrue(result['lease_revocation_pending'])
                        self.assertFalse(result['physical_stop_verified'])
                finally:
                    release.set()
                    if child.poll() is None: child.terminate()
                    child.wait(timeout=3)
                    pipe.transport_thread.join(3)
                    pipe.thread.join(3)
                    # The transport's EOF and the simulated fault both start
                    # an asynchronous lease revocation. It must finish before
                    # TemporaryDirectory begins removing its files.
                    if lease._async_failure_thread is not None:
                        self.assertTrue(lease._async_failure_done.wait(3),
                                        'lease revocation did not finish before cleanup')
        finally:
            release.set()
            if child.poll() is None: child.kill()
            child.wait(timeout=3)
            for stream in (child.stdin, child.stdout, child.stderr): stream.close()

    def test_blocked_lease_fsync_does_not_delay_cancel_request(self):
        child = simulated_guard('d'*32, 'cancel')
        try:
            with tempfile.TemporaryDirectory() as directory:
                lease = bridge.GuardLease(directory, dict(bridge.arm.BODY),
                                          lambda: child.poll() is None, session_id='d'*32)
                pipe = bridge.GuardPipe(child, lease, time.monotonic())
                pipe.await_ready(3)
                lease.synchronize_uuid(box_tests.GOAL_ID, pipe.exchange)
                began, release = threading.Event(), threading.Event()
                original = lease._write
                def blocked(deadline):
                    if deadline == 0:
                        began.set()
                        if not release.wait(3): raise RuntimeError('test timed out')
                    original(deadline)
                try:
                    with patch.object(lease, '_write', side_effect=blocked):
                        started = time.monotonic()
                        result = pipe.cancel_goal(box_tests.GOAL_ID)
                        self.assertTrue(began.wait(1))
                        self.assertTrue(result['request_sent'])
                        self.assertTrue(result['lease_revocation_pending'])
                        self.assertLess(time.monotonic()-started, 1)
                        self.assertFalse(result['physical_stop_verified'])
                        release.set()
                        self.assertTrue(lease._async_failure_done.wait(2))
                finally:
                    release.set()
                self.assertEqual(json.loads(lease.path.read_text())['deadline'], 0)
                pipe.stop()
        finally:
            if child.poll() is None: child.terminate()
            child.wait(timeout=3)
            for stream in (child.stdin, child.stdout, child.stderr): stream.close()

    def test_guard_fault_reason_survives_later_pipe_close(self):
        child = simulated_guard('d'*32, 'guard_fault')
        try:
            with tempfile.TemporaryDirectory() as directory:
                lease = bridge.GuardLease(directory, dict(bridge.arm.BODY),
                                          lambda: child.poll() is None, session_id='d'*32)
                pipe = bridge.GuardPipe(child, lease, time.monotonic())
                pipe.await_ready(3)
                # The ACK may arrive just as the simulated process exits;
                # the observed alert itself must survive subsequent EOF.
                try:
                    lease.synchronize_uuid(box_tests.GOAL_ID, pipe.exchange)
                except (RuntimeError, TimeoutError, OSError, ValueError):
                    pass
                child.wait(timeout=3)
                pipe.transport_thread.join(3)
                pipe.thread.join(3)
                if lease._async_failure_thread is not None:
                    self.assertTrue(lease._async_failure_done.wait(3),
                                    'lease revocation did not finish before cleanup')
                self.assertEqual(pipe.first_guard_fault['reason'],
                                 'outside_nominal_sps_limit:R_elbow_yaw_joint')
                self.assertEqual(pipe.first_guard_fault['event'], 'OPERATOR_ALERT')
                self.assertEqual(pipe.failure, 'guard_reported:OPERATOR_ALERT')
                self.assertTrue(lease.failed)
        finally:
            if child.poll() is None: child.terminate()
            child.wait(timeout=3)
            for stream in (child.stdin, child.stdout, child.stderr): stream.close()

    def test_normal_shutdown_precedes_coordinator_progress_end(self):
        child = simulated_guard('d'*32, 'success')
        progress = {'alive': True}
        try:
            with tempfile.TemporaryDirectory() as directory:
                lease = bridge.GuardLease(directory, dict(bridge.arm.BODY),
                    lambda: child.poll() is None and progress['alive'], session_id='d'*32)
                pipe = bridge.GuardPipe(child, lease, time.monotonic())
                pipe.await_ready(3)
                pipe.prepare_normal_shutdown()
                progress['alive'] = False
                time.sleep(.15)
                self.assertIsNone(pipe.failure)
                self.assertTrue(pipe.stop())
                self.assertEqual(child.wait(timeout=3), 0)
        finally:
            if child.poll() is None: child.terminate()
            child.wait(timeout=3)
            for stream in (child.stdin, child.stdout, child.stderr): stream.close()

    def test_stop_without_exact_ack_is_not_success(self):
        child = simulated_guard('d'*32, 'bad_stop_ack')
        try:
            with tempfile.TemporaryDirectory() as directory:
                lease = bridge.GuardLease(directory, dict(bridge.arm.BODY),
                                          lambda: child.poll() is None, session_id='d'*32)
                pipe = bridge.GuardPipe(child, lease, time.monotonic())
                pipe.await_ready(3)
                self.assertFalse(pipe.stop())
                self.assertFalse(pipe.stop_ack)
                self.assertTrue(pipe.channel_failed)
        finally:
            if child.poll() is None: child.terminate()
            child.wait(timeout=3)
            for stream in (child.stdin, child.stdout, child.stderr): stream.close()

    def exercise(self, mode):
        session = 'd'*32
        child = simulated_guard(session, mode)
        liveness = {'pc': True}
        try:
            with tempfile.TemporaryDirectory() as directory:
                lease = bridge.GuardLease(directory, dict(bridge.arm.BODY),
                                          lambda: child.poll() is None and liveness['pc'], session_id=session)
                pipe = bridge.GuardPipe(child, lease, time.monotonic())
                pipe.await_ready(3)
                if mode == 'success':
                    lease.synchronize_uuid(box_tests.GOAL_ID, pipe.exchange)
                    self.assertEqual(lease.goal_id, box_tests.GOAL_ID)
                elif mode == 'cancel':
                    lease.synchronize_uuid(box_tests.GOAL_ID, pipe.exchange)
                    result = pipe.cancel_goal(box_tests.GOAL_ID)
                    self.assertEqual(result['goal_id'], box_tests.GOAL_ID)
                    self.assertFalse(result['physical_stop_verified'])
                elif mode == 'disk_fail_cancel':
                    lease.synchronize_uuid(box_tests.GOAL_ID, pipe.exchange)
                    def fail_disk():
                        lease.failed = True
                        raise OSError('simulated disk failure')
                    with patch.object(lease, 'fail', side_effect=fail_disk):
                        result = pipe.cancel_goal(box_tests.GOAL_ID)
                    self.assertTrue(result['request_sent'])
                    self.assertIn('OSError', result['lease_revocation_error'])
                    self.assertFalse(result['physical_stop_verified'])
                elif mode == 'pc_lost':
                    lease.synchronize_uuid(box_tests.GOAL_ID, pipe.exchange)
                    liveness['pc'] = False
                    deadline = time.monotonic()+2
                    while not lease.failed and time.monotonic()<deadline: time.sleep(.01)
                    self.assertTrue(lease.failed)
                    self.assertFalse(pipe.channel_failed)
                    result = pipe.cancel_goal(box_tests.GOAL_ID)
                    self.assertTrue(result['request_sent'])
                    self.assertFalse(result['physical_stop_verified'])
                elif mode == 'bad_observation':
                    lease.synchronize_uuid(box_tests.GOAL_ID, pipe.exchange)
                    deadline = time.monotonic()+2
                    while not lease.failed and time.monotonic()<deadline: time.sleep(.01)
                    self.assertTrue(lease.failed)
                    self.assertFalse(pipe.channel_failed)
                    result = pipe.cancel_goal(box_tests.GOAL_ID)
                    self.assertTrue(result['request_sent'])
                    self.assertFalse(result['physical_stop_verified'])
                elif mode == 'no_ack':
                    started = time.monotonic()
                    with self.assertRaisesRegex(TimeoutError, 'guard_ack_timeout'):
                        lease.synchronize_uuid(box_tests.GOAL_ID, pipe.exchange)
                    self.assertLess(time.monotonic() - started, 1.5)
                    self.assertTrue(lease.failed)
                elif mode == 'bad_ack':
                    with self.assertRaises(RuntimeError):
                        lease.synchronize_uuid(box_tests.GOAL_ID, pipe.exchange)
                    self.assertTrue(lease.failed)
                elif mode == 'dead':
                    child.terminate(); child.wait(timeout=3)
                    pipe.thread.join(3)
                    self.assertTrue(lease.failed)
                    self.assertTrue(lease._async_failure_done.wait(2))
                    self.assertEqual(json.loads(lease.path.read_text())['deadline'], 0)
                pipe.stop()
        finally:
            if child.poll() is None: child.terminate()
            child.wait(timeout=3)
            for stream in (child.stdin, child.stdout, child.stderr):
                if stream is not None: stream.close()

    def test_fresh_guard_and_exact_uuid_ack_over_real_pipes(self):
        self.exercise('success')

    def test_guard_that_does_not_ack_is_bounded_and_revokes(self):
        self.exercise('no_ack')

    def test_wrong_uuid_ack_revokes(self):
        self.exercise('bad_ack')

    def test_independent_exact_uuid_cancel_does_not_claim_stop(self):
        self.exercise('cancel')

    def test_disk_error_does_not_block_independent_cancel(self):
        self.exercise('disk_fail_cancel')

    def test_pc_liveness_loss_still_allows_independent_exact_cancel(self):
        self.exercise('pc_lost')

    def test_invalid_guard_sample_revokes_but_channel_can_cancel(self):
        self.exercise('bad_observation')

    def test_guard_death_revokes(self):
        self.exercise('dead')

    def test_session_mismatch_fails_before_guard_ready(self):
        child = simulated_guard('e'*32, 'success')
        try:
            with tempfile.TemporaryDirectory() as directory:
                lease = bridge.GuardLease(directory, dict(bridge.arm.BODY),
                                          lambda: child.poll() is None, session_id='d'*32)
                pipe = bridge.GuardPipe(child, lease, time.monotonic())
                with self.assertRaisesRegex(RuntimeError, 'continuous_guard_not_ready'):
                    pipe.await_ready(2)
                self.assertTrue(lease.failed)
                pipe.stop()
        finally:
            if child.poll() is None: child.terminate()
            child.wait(timeout=3)
            for stream in (child.stdin, child.stdout, child.stderr):
                if stream is not None: stream.close()

    def test_full_input_pipe_has_bounded_write_and_revokes(self):
        child = subprocess.Popen([sys.executable, '-u', '-c', 'import time;time.sleep(10)'],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0)
        try:
            with tempfile.TemporaryDirectory() as directory:
                lease = bridge.GuardLease(directory, dict(bridge.arm.BODY),
                                          lambda: child.poll() is None, session_id='d'*32)
                pipe = bridge.GuardPipe(child, lease, time.monotonic())
                # Fill the nonblocking OS pipe so _send itself must time out.
                while True:
                    try:
                        os.write(child.stdin.fileno(), b'x' * 4096)
                    except BlockingIOError:
                        break
                pipe.ready.set()  # fake ready; this test exercises write handling only
                started = time.monotonic()
                with self.assertRaisesRegex(TimeoutError, 'guard_ack_timeout'):
                    pipe.exchange({'event': 'prepare_goal_uuid'}, .2)
                self.assertLess(time.monotonic()-started, 1.0)
                self.assertTrue(lease.failed)
                child.terminate(); child.wait(timeout=3); pipe.thread.join(3)
        finally:
            if child.poll() is None: child.terminate()
            child.wait(timeout=3)
            for stream in (child.stdin, child.stdout, child.stderr):
                if stream is not None: stream.close()


if __name__ == '__main__':
    unittest.main()
