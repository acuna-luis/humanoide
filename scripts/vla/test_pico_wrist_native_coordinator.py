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
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent/'runtime'))
import arm_native_lease_bridge as bridge
import pico_wrist_native_coordinator as coordinator
import pico_wrist_pc_heartbeat as pc_heartbeat
import pico_wrist_model_decision as model_decision
import prepare_pico_wrist_native_probe as prep
from test_prepare_pico_wrist_native_probe import state, urdf, transmissions
from test_arm_native_lease_bridge import telemetry
from test_pico_wrist_model_decision import case as model_case, BOOT as MODEL_BOOT

GOAL = '12345678-1234-1234-1234-123456789abc'


class ModelPermissionTests(unittest.TestCase):
    def test_wait_keeps_guard_and_lease_checked_until_matching_permission(self):
        task = 'a'*64
        permit = {'goal_id':GOAL, 'task_sha256':task, 'decision_sha256':'b'*64,
                  'deadline_monotonic_ns':time.monotonic_ns()+2_000_000_000}
        calls = []
        pc = types.SimpleNamespace(begin_model_permit=lambda goal, sha: calls.append((goal, sha)))
        pending = iter([None, None, permit])
        pc.permit_snapshot = lambda: next(pending)
        lease = types.SimpleNamespace(guard_alive=lambda: True, path='/no-io')
        guard = types.SimpleNamespace(failure=None)
        progress = types.SimpleNamespace(beat=lambda: calls.append('beat'))
        with patch.object(coordinator.native, 'check_lease_current') as check, patch.object(coordinator.time, 'sleep'):
            got = coordinator.await_model_permission(pc, lease, guard, progress, GOAL, task,
                                                     time.monotonic()+1)
        self.assertEqual(got, permit)
        self.assertEqual(calls[0], (GOAL, task))
        self.assertEqual(calls.count('beat'), 3)
        self.assertEqual(check.call_count, 3)

    def test_wait_rejects_foreign_or_expired_permit_and_guard_failure(self):
        task = 'a'*64
        lease = types.SimpleNamespace(guard_alive=lambda: True, path='/no-io')
        guard = types.SimpleNamespace(failure=None)
        progress = types.SimpleNamespace(beat=lambda: None)
        for value in (
            {'goal_id':'other', 'task_sha256':task, 'decision_sha256':'b'*64,
             'deadline_monotonic_ns':time.monotonic_ns()+1_000_000_000},
            {'goal_id':GOAL, 'task_sha256':task, 'decision_sha256':'b'*64,
             'deadline_monotonic_ns':time.monotonic_ns()-1},
        ):
            pc = types.SimpleNamespace(begin_model_permit=lambda *_: None,
                                       permit_snapshot=lambda: value)
            with patch.object(coordinator.native, 'check_lease_current'):
                with self.assertRaisesRegex(RuntimeError, 'invalid_or_expired_model_permission'):
                    coordinator.await_model_permission(pc, lease, guard, progress, GOAL, task,
                                                       time.monotonic()+1)
        guard.failure = 'lost'
        pc = types.SimpleNamespace(begin_model_permit=lambda *_: None,
                                   permit_snapshot=lambda: None)
        with self.assertRaisesRegex(RuntimeError, 'guard_lost_waiting_for_model'):
            coordinator.await_model_permission(pc, lease, guard, progress, GOAL, task,
                                               time.monotonic()+1)


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
            bridge.native.check_lease_current(self.lease.path, time.monotonic)
            if self.latest is None or time.monotonic()-self.latest['monotonic'] > bridge.MAX_AGE_S:
                raise RuntimeError('fake_guard_stale')
            return self.latest

    def cancel_goal(self, goal_id):
        self.cancelled.append(goal_id)
        return {'goal_id':goal_id, 'request_sent':True, 'physical_stop_verified':False}

    def prepare_normal_shutdown(self):
        with self.lease.lock:
            if self.failure or self.lease.failed or not self.lease.guard_alive():
                raise RuntimeError('fake_guard_unhealthy_at_shutdown')
            self.stop_event.set()
            self.lease.fail()

    def close(self):
        self.stop_event.set(); self.thread.join(2)


def worker_process(manifest, session, mode):
    candidate = manifest['candidate']
    code = '''import json,sys,time
candidate=json.loads(sys.argv[1]);session=sys.argv[2];mode=sys.argv[3]
def emit(**row):print(json.dumps(row),flush=True)
emit(event='stage_receipt',session_id=session,receipt={
 'status':'STAGED_NOT_LOADED_OR_EXECUTED','runtime_path':candidate['runtime_path'],
 'sha256':candidate['xml_sha256'],'device':1,'inode':2,'movement_commands':0})
req={'event':'uuid_request','session_id':session,'goal_id':%r,'challenge':'c'*32}
emit(**req)
ack=json.loads(sys.stdin.readline())
if mode=='hang_after_model_ack':
 assert all(ack.get(k)==v for k,v in dict(req,event='uuid_ok').items())
 assert set(ack)==set(req)|{'deadline_monotonic_ns','decision_sha256'}
 time.sleep(2);sys.exit(9)
assert ack==dict(req,event='uuid_ok')
if mode=='crash_before_dispatched':sys.exit(9)
emit(event='dispatched',goal_id=req['goal_id'])
if mode=='crash':sys.exit(9)
emit(event='accepted',goal_id=req['goal_id'],accepted=True)
if mode in ('feedback_many','feedback_bad'):
 for i in range(120):
  emit(event='feedback',goal_id=('00000000-0000-0000-0000-000000000000' if mode=='feedback_bad' and i==5 else req['goal_id']),feedback={'n':i})
if mode=='bad_pending':
 emit(event='result_pending',goal_id='00000000-0000-0000-0000-000000000000',status=2,result={});sys.exit(9)
emit(event='result_pending',goal_id=req['goal_id'],status=2,result={})
emit(event='result',goal_id=req['goal_id'],status=4,result={'state':{'state':1101001,'desc':'SUCCEED'}})
if mode=='feedback_after_result':emit(event='feedback',goal_id=req['goal_id'],feedback={'n':1})
emit(event='worker_finished',session_id=session)
emit(event='worker_result',returncode=0)
''' % GOAL
    return subprocess.Popen([sys.executable, '-u', '-c', code, json.dumps(candidate), session, mode],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)


def real_worker_with_fake_transport(manifest, lease_path, intent, uid, session, mode='normal', model=False):
    """Real worker+lease+action state machine; local fake actuator and stage."""
    payload = {'manifest':manifest, 'urdf_text':urdf(), 'transmissions_text':transmissions(),
               'lease_path':str(lease_path), 'session_id':session,
               'intent_path':str(intent), 'intent_uid':uid}
    if model:
        payload['model_mode'] = True
    code = r'''
import hashlib,json,os,socket,subprocess,sys,time,types
sys.path.insert(0, sys.argv[1]);sys.path.insert(0, sys.argv[2]);sys.path.insert(0, sys.argv[3])
import pico_wrist_native_worker as worker
import arm_native_lease_bridge as bridge
payload=json.loads(sys.argv[4]);goal_id=sys.argv[5];mode=sys.argv[6]
os.environ['HW_TYPE']='cruzr_s2_v1_sps'
def forbidden(*args,**kwargs): raise AssertionError('network_or_process_forbidden')
socket.socket.connect=forbidden;socket.create_connection=forbidden;subprocess.Popen=forbidden
real_sha=hashlib.sha256
class FakeHash:
 def hexdigest(self): return payload['manifest']['expected_meta_move_sha256']
worker.hashlib=types.SimpleNamespace(sha256=lambda raw: FakeHash() if raw==b'fake-vendor' else real_sha(raw))
original_read=worker.Path.read_bytes
def read(path):
 values={worker.URDF_PATH:payload['urdf_text'].encode(),worker.SPS_PATH:payload['transmissions_text'].encode(),worker.META_MOVE_PATH:b'fake-vendor'}
 return values[str(path)] if str(path) in values else original_read(path)
worker.Path.read_bytes=read
worker.require_robot_app_can_read_private_task=lambda: os.geteuid()
candidate=payload['manifest']['candidate']
worker.staging.stage_task=lambda *a,**kw: {'status':'STAGED_NOT_LOADED_OR_EXECUTED','runtime_path':candidate['runtime_path'],'sha256':candidate['xml_sha256'],'device':1,'inode':2,'movement_commands':0}
worker.staging.verify_staged=lambda *a,**kw: True
class FakeTransport:
 def __init__(self,lease,exchange,**kwargs): self.lease,self.goal_id,self.rows=lease,None,[]
 def ready(self): return True
 def send(self,goal):
  self.lease.synchronize_uuid(goal_id,None);self.goal_id=goal_id
  self.rows=[] if mode=='hang' else [{'event':'accepted','goal_id':goal_id,'accepted':True},{'event':'result','goal_id':goal_id,'status':4,'result':{'state':{'state':1101001,'desc':'SUCCEED'}}}]
  return goal_id
 def spin(self): time.sleep(.01)
 def drain(self): rows,self.rows=self.rows,[];return rows
 def cancel(self): pass
 def close(self): pass
bridge.GuardedRosaTransport=FakeTransport
channel=worker.WorkerChannel(sys.stdin.fileno(),sys.stdout.fileno(),payload['session_id'],model_mode=payload.get('model_mode',False))
prov=('worker',payload['session_id'],'b'*64,'c'*64)
rc=worker.run(payload,channel,verified_provenance=prov)
channel.emit(event='worker_result',returncode=rc)
raise SystemExit(rc)
'''
    vla = Path(__file__).resolve().parent
    return subprocess.Popen([sys.executable, '-B', '-u', '-c', code, str(vla), str(vla/'runtime'),
                             str(vla.parent/'box_handling'), json.dumps(payload), GOAL, mode],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)


class CoordinatorTests(unittest.TestCase):
    def test_model_ack_starts_short_action_deadline_if_worker_blocks_in_send(self):
        manifest = prep.prepare(state(), urdf(), transmissions())
        with tempfile.TemporaryDirectory() as directory:
            control = Path(directory)/'stable-control'; control.mkdir(mode=0o700)
            lease = bridge.GuardLease(directory, manifest['input']['reference_20d'], lambda: True)
            guard = FakeGuard(lease)
            processes = []
            def spawn(_, intent, uid):
                process = worker_process(manifest, lease.session_id, 'hang_after_model_ack')
                processes.append(process)
                return process
            permit = {'goal_id':GOAL, 'task_sha256':manifest['candidate']['xml_sha256'],
                      'decision_sha256':'b'*64,
                      'deadline_monotonic_ns':time.monotonic_ns()+5_000_000_000}
            pc = types.SimpleNamespace(begin_model_permit=lambda *_: None, permit_snapshot=lambda: permit)
            start = time.monotonic()
            try:
                with patch.object(bridge.arm, 'physical_release_gate'), \
                     patch.object(coordinator, 'GLOBAL_RECEIPT_DIR', control), \
                     patch.object(coordinator, 'MODEL_ACTION_TIMEOUT_S', .2):
                    with self.assertRaisesRegex(RuntimeError, 'worker_terminal_evidence_incomplete'):
                        coordinator.coordinate(lease, guard, manifest, urdf(), transmissions(), spawn,
                                               control, timeout=5, model_permit=pc)
                self.assertLess(time.monotonic()-start, 2)
                self.assertEqual(guard.cancelled, [GOAL])
                records = [json.loads(line) for line in
                           (control/('worker-events-'+lease.session_id+'.jsonl')).read_text().splitlines()]
                self.assertEqual([r['decision_sha256'] for r in records
                                  if r.get('event') == 'model_permission_verified'], ['b'*64])
            finally:
                guard.close()
                for process in processes:
                    if process.poll() is None: process.terminate()
                    process.wait(timeout=3)
                    for stream in (process.stdin,process.stdout,process.stderr): stream.close()

    def test_two_phase_model_decision_reaches_simulated_worker_only_when_fresh(self):
        # Real coordinator, lease, heartbeat and worker IPC; the observation,
        # action transport and actuator are local fakes, not ROS or a robot.
        rows, _ = model_case()
        manifest = prep.prepare(state(), urdf(), transmissions())
        with tempfile.TemporaryDirectory() as directory:
            control = Path(directory)/'stable-control'; control.mkdir(mode=0o700)
            lease = bridge.GuardLease(directory, manifest['input']['reference_20d'], lambda: True)
            guard = FakeGuard(lease)
            read_fd, write_fd = os.pipe()
            decision = [None]
            seen = []
            def permit(request):
                return model_decision.make_dispatch_permission(decision[0], request['goal_id'],
                    request['task_sha256'], boot_id=MODEL_BOOT, now_ns=time.monotonic_ns(),
                    max_state_age_ns=10_000_000_000, max_prediction_age_ns=10_000_000_000)
            pump = pc_heartbeat.PcHeartbeatPump(write_fd, lease.session_id, model_permit=permit)
            def challenge(row):
                pump.submit(row)
                return True
            pc = pc_heartbeat.PcHeartbeat(read_fd, lease.session_id, challenge, model_mode=True)
            processes = []
            def spawn(path, intent, uid):
                process = real_worker_with_fake_transport(manifest, path, intent, uid, lease.session_id,
                                                          model=True)
                processes.append(process)
                return process
            def event(row):
                seen.append(row.get('event'))
                if row.get('event') == 'stage_receipt':
                    now = time.monotonic_ns()
                    rows[1]['paired_state20']['received_monotonic_ns'] = now-1_000_000
                    rows[1]['prediction_received_monotonic_ns'] = now-500_000
                    decision[0] = model_decision.decision_from_stream(rows, manifest,
                                                                       now_ns=now, boot_id=MODEL_BOOT)
                return True
            try:
                pc.await_ready(2)
                with patch.object(bridge.arm, 'physical_release_gate'), \
                     patch.object(coordinator, 'GLOBAL_RECEIPT_DIR', control):
                    result = coordinator.coordinate(lease, guard, manifest, urdf(), transmissions(),
                        spawn, control, timeout=8, model_permit=pc, event_sink=event)
                self.assertEqual(result['status'], 'ACTION_SUCCEEDED_AND_POSTFLIGHT_OBSERVED')
                self.assertIn('stage_receipt', seen)
                self.assertIn('uuid_request', seen)
                self.assertIn('dispatched', seen)
                self.assertIsNotNone(decision[0])
            finally:
                pc.close(); pump.close(); guard.close()
                for fd in (read_fd, write_fd):
                    try: os.close(fd)
                    except OSError: pass
                for process in processes:
                    if process.poll() is None: process.terminate()
                    process.wait(timeout=3)
                    for stream in (process.stdin,process.stdout,process.stderr): stream.close()

    def test_concurrent_guard_event_copy_failure_preserves_first_alert(self):
        class ChangedHistory:
            def __iter__(self):
                raise RuntimeError('deque mutated during iteration')
        def host_failed():
            raise OSError('host status unavailable')
        guard = types.SimpleNamespace(
            failure='guard_reported:OPERATOR_ALERT', channel_failed=False,
            auto_cancel_requested=True, guard_events=ChangedHistory(),
            first_guard_fault={'event':'OPERATOR_ALERT','reason':'source_stale_or_future:body'},
            latest=None, status_diagnostics=host_failed)
        result = coordinator.failure_diagnostics(guard, {'started':True})
        self.assertEqual(result['failure'], 'guard_reported:OPERATOR_ALERT')
        self.assertEqual(result['first_guard_fault']['reason'], 'source_stale_or_future:body')
        self.assertIn('deque mutated', result['guard_events_error'])
        self.assertIn('host status unavailable', result['host_liveness_error'])

    def test_oversized_snapshot_retains_first_guard_cause(self):
        guard = types.SimpleNamespace(
            failure='guard_reported:OPERATOR_ALERT', first_guard_fault={'reason':'unsafe_joint'},
            guard_events=[{'reason':'x'*512} for _ in range(100)], latest=None)
        result = coordinator.failure_diagnostics(guard, {})
        self.assertEqual(result['first_guard_fault']['reason'], 'unsafe_joint')
        self.assertEqual(result['failure'], 'guard_reported:OPERATOR_ALERT')
        self.assertIn('guard_diagnostics_too_large', result['diagnostic_error'])

    def test_operator_notice_fits_even_when_unicode_escapes_expand(self):
        long_unicode = '\U0001f9ef' * 1000
        notice = coordinator.failure_notice({
            'failure':long_unicode, 'reason':long_unicode,
            'first_guard_fault':{'reason':long_unicode},
            'host_liveness':{'pc_heartbeat_failure':long_unicode}})
        self.assertLess(len(json.dumps(notice, separators=(',', ':')).encode('utf-8')), 4096)
        self.assertEqual(notice['guard_reason'], long_unicode[:64])
        self.assertFalse(notice['physical_stop_verified'])

    def test_real_worker_pc_loss_after_dispatch_cancels_exact_uuid(self):
        manifest = prep.prepare(state(), urdf(), transmissions())
        with tempfile.TemporaryDirectory() as directory:
            control = Path(directory)/'stable-control'
            control.mkdir(mode=0o700)
            lease = bridge.GuardLease(directory, manifest['input']['reference_20d'], lambda: True)
            guard = FakeGuard(lease)
            processes = []
            notices = []
            def spawn(path, intent, uid):
                child = real_worker_with_fake_transport(manifest, path, intent, uid, lease.session_id, 'hang')
                processes.append(child)
                return child
            def event_sink(row):
                if row.get('event') == 'dispatched':
                    guard.failure = 'simulated_pc_liveness_lost'
                    guard.first_guard_fault = {'event':'OPERATOR_ALERT',
                        'reason':'source_stale_or_future:body', 'physical_stop_confirmed':False}
                    guard.guard_events = [{'event':'UNRESOLVED_MONITORING','reason':'x'*512}
                                          for _ in range(16)]
                    guard.status_diagnostics = lambda: {'pc_heartbeat_failure':'simulated_failure'}
                if row.get('event') == 'guard_diagnostic_alert':
                    # The safety attempt precedes the nonblocking operator
                    # alert; durable failure records have not yet been written.
                    self.assertEqual(guard.cancelled, [GOAL])
                    journal = control/('worker-events-'+lease.session_id+'.jsonl')
                    self.assertNotIn('coordinator_failure', journal.read_text())
                    notices.append(row)
                return True
            try:
                with patch.object(coordinator, 'GLOBAL_RECEIPT_DIR', control):
                    with self.assertRaisesRegex(RuntimeError, 'guard_lost_during_trial'):
                        coordinator.coordinate(lease, guard, manifest, urdf(), transmissions(),
                            spawn, control, timeout=8, event_sink=event_sink,
                            verified_provenance=('host', lease.session_id, 'b'*64, 'c'*64))
                self.assertEqual(guard.cancelled, [GOAL])
                self.assertTrue(lease.failed)
                rows = [json.loads(line) for line in
                        (control/('worker-events-'+lease.session_id+'.jsonl')).read_text().splitlines()]
                names = [row.get('event') for row in rows]
                self.assertLess(names.index('independent_cancel_requested'), names.index('guard_diagnostics'))
                diagnostic = next(row for row in rows if row.get('event') == 'guard_diagnostics')
                self.assertEqual(diagnostic['failure'], 'simulated_pc_liveness_lost')
                self.assertEqual(diagnostic['first_guard_fault']['reason'], 'source_stale_or_future:body')
                self.assertEqual(diagnostic['host_liveness']['pc_heartbeat_failure'], 'simulated_failure')
                self.assertFalse(diagnostic['physical_stop_verified'])
                self.assertEqual(len(diagnostic['recent_guard_events']), 16)
                self.assertEqual(len(notices), 1)
                self.assertLess(len(json.dumps(notices[0]).encode()), 4096)
                self.assertEqual(notices[0]['guard_reason'], 'source_stale_or_future:body')
            finally:
                guard.close()
                for process in processes:
                    if process.poll() is None: process.terminate()  # Local fake child only.
                    try: process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill()  # This exact local test process has no ROS or robot access.
                        process.wait(timeout=3)
                    for stream in (process.stdin, process.stdout, process.stderr): stream.close()

    def test_real_worker_and_coordinator_share_exact_uuid_with_simulated_guard(self):
        manifest = prep.prepare(state(), urdf(), transmissions())
        with tempfile.TemporaryDirectory() as directory:
            control = Path(directory)/'stable-control'
            control.mkdir(mode=0o700)
            lease = bridge.GuardLease(directory, manifest['input']['reference_20d'], lambda: True)
            guard = FakeGuard(lease)
            processes = []
            def spawn(path, intent, uid):
                child = real_worker_with_fake_transport(manifest, path, intent, uid, lease.session_id)
                processes.append(child)
                return child
            try:
                with patch.object(coordinator, 'GLOBAL_RECEIPT_DIR', control):
                    try:
                        result = coordinator.coordinate(lease, guard, manifest, urdf(), transmissions(),
                            spawn, control, timeout=8,
                            verified_provenance=('host', lease.session_id, 'b'*64, 'c'*64))
                    except Exception as exc:
                        detail = processes[0].stderr.read().decode() if processes and processes[0].poll() is not None else ''
                        raise AssertionError(str(exc)+'; child: '+detail) from exc
                self.assertEqual(result['goal_id'], GOAL)
                self.assertEqual(result['status'], 'ACTION_SUCCEEDED_AND_POSTFLIGHT_OBSERVED')
                rows = [json.loads(line) for line in
                        (control/('worker-events-'+lease.session_id+'.jsonl')).read_text().splitlines()]
                self.assertEqual([row['goal_id'] for row in rows if row['event']=='uuid_request'], [GOAL])
                self.assertEqual([row['goal_id'] for row in rows if row['event']=='dispatched'], [GOAL])
                self.assertEqual(guard.cancelled, [])
            finally:
                guard.close()
                for process in processes:
                    if process.poll() is None: process.terminate()
                    process.wait(timeout=3)
                    for stream in (process.stdin, process.stdout, process.stderr): stream.close()

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

    def test_feedback_is_counted_without_per_message_disk_sync(self):
        manifest = prep.prepare(state(), urdf(), transmissions())
        with tempfile.TemporaryDirectory() as directory:
            control = Path(directory)/'stable-control'
            control.mkdir(mode=0o700)
            lease = bridge.GuardLease(directory, manifest['input']['reference_20d'], lambda: True)
            guard = FakeGuard(lease)
            processes, sync_counts, output = [], [], []
            uuid_committed = threading.Event()
            original_fsync = os.fsync
            def count_sync(fd):
                try: name = os.readlink('/proc/self/fd/' + str(fd))
                except OSError: name = ''
                data = ''
                if '/worker-events-' in name:
                    data = Path(name).read_text()
                    sync_counts.append(len(data.splitlines()))
                result = original_fsync(fd)
                if '"event": "uuid_request"' in data:
                    uuid_committed.set()
                return result
            original_exchange = guard.exchange
            def exchange(request, timeout):
                self.assertTrue(uuid_committed.is_set(), 'UUID handshake preceded durable receipt')
                return original_exchange(request, timeout)
            guard.exchange = exchange
            def spawn(_, intent, uid):
                process = worker_process(manifest, lease.session_id, 'feedback_many')
                processes.append(process)
                return process
            try:
                with patch.object(bridge.arm, 'physical_release_gate'), \
                     patch.object(coordinator, 'GLOBAL_RECEIPT_DIR', control), \
                     patch.object(coordinator.os, 'fsync', side_effect=count_sync):
                    result = coordinator.coordinate(lease, guard, manifest, urdf(), transmissions(),
                        spawn, control, timeout=5, event_sink=lambda row: output.append(row) or True)
                events = [json.loads(line) for line in
                          (control/('worker-events-'+lease.session_id+'.jsonl')).read_text().splitlines()]
                self.assertEqual([e['count'] for e in events if e['event']=='feedback_summary'], [120])
                self.assertNotIn('feedback', [e['event'] for e in events])
                self.assertNotIn('feedback', [e['event'] for e in output])
                self.assertEqual(len(sync_counts), 10)  # eight critical events + two postflight commits
                self.assertEqual(events[1]['event'], 'uuid_request')
                self.assertGreaterEqual(sync_counts[1], 2)
                # The PC consumes only the sink, not the on-disk summaries.
                import run_pico_wrist_native_trial as pc
                evidence = pc.SuccessEvidence(lease.session_id)
                for row in output: evidence.accept(row)
                evidence.accept(result)
                self.assertEqual(evidence.phase, 9)
            finally:
                guard.close()
                for process in processes:
                    if process.poll() is None: process.terminate()
                    process.wait(timeout=3)
                    for stream in (process.stdin, process.stdout, process.stderr): stream.close()

    def test_bad_feedback_still_cancels_exact_goal(self):
        manifest = prep.prepare(state(), urdf(), transmissions())
        with tempfile.TemporaryDirectory() as directory:
            control = Path(directory)/'stable-control'
            control.mkdir(mode=0o700)
            lease = bridge.GuardLease(directory, manifest['input']['reference_20d'], lambda: True)
            guard = FakeGuard(lease)
            processes = []
            def spawn(_, intent, uid):
                process = worker_process(manifest, lease.session_id, 'feedback_bad')
                processes.append(process)
                return process
            try:
                with patch.object(bridge.arm, 'physical_release_gate'), \
                     patch.object(coordinator, 'GLOBAL_RECEIPT_DIR', control):
                    with self.assertRaisesRegex(ValueError, 'foreign_worker_action_event'):
                        coordinator.coordinate(lease, guard, manifest, urdf(), transmissions(),
                                               spawn, control, timeout=5)
                self.assertEqual(guard.cancelled, [GOAL])
                self.assertTrue(lease.failed)
                self.assertTrue((control/'PENDING_OR_UNRESOLVED.json').is_file())
                events = [json.loads(line) for line in
                          (control/('worker-events-'+lease.session_id+'.jsonl')).read_text().splitlines()]
                self.assertEqual([e['count'] for e in events if e['event']=='feedback_summary'], [5])
            finally:
                guard.close()
                for process in processes:
                    if process.poll() is None: process.terminate()
                    process.wait(timeout=3)
                    for stream in (process.stdin, process.stdout, process.stderr): stream.close()

    def test_feedback_after_result_fails_closed(self):
        manifest = prep.prepare(state(), urdf(), transmissions())
        with tempfile.TemporaryDirectory() as directory:
            control = Path(directory)/'stable-control'
            control.mkdir(mode=0o700)
            lease = bridge.GuardLease(directory, manifest['input']['reference_20d'], lambda: True)
            guard = FakeGuard(lease)
            processes = []
            def spawn(_, intent, uid):
                process = worker_process(manifest, lease.session_id, 'feedback_after_result')
                processes.append(process)
                return process
            try:
                with patch.object(bridge.arm, 'physical_release_gate'), \
                     patch.object(coordinator, 'GLOBAL_RECEIPT_DIR', control):
                    with self.assertRaisesRegex(ValueError, 'foreign_worker_action_event'):
                        coordinator.coordinate(lease, guard, manifest, urdf(), transmissions(),
                                               spawn, control, timeout=5)
                self.assertTrue(lease.failed)
                self.assertTrue((control/'PENDING_OR_UNRESOLVED.json').is_file())
            finally:
                guard.close()
                for process in processes:
                    if process.poll() is None: process.terminate()
                    process.wait(timeout=3)
                    for stream in (process.stdin, process.stdout, process.stderr): stream.close()

    def test_guard_failure_during_feedback_cancels_exact_goal(self):
        manifest = prep.prepare(state(), urdf(), transmissions())
        with tempfile.TemporaryDirectory() as directory:
            control = Path(directory)/'stable-control'
            control.mkdir(mode=0o700)
            lease = bridge.GuardLease(directory, manifest['input']['reference_20d'], lambda: True)
            guard = FakeGuard(lease)
            processes, count = [], [0]
            original_decode = coordinator.native.object_json
            def decode(raw):
                row = original_decode(raw)
                if row.get('event') == 'feedback':
                    count[0] += 1
                    if count[0] == 40: guard.failure = 'simulated_guard_fault'
                return row
            def spawn(_, intent, uid):
                process = worker_process(manifest, lease.session_id, 'feedback_many')
                processes.append(process)
                return process
            try:
                with patch.object(bridge.arm, 'physical_release_gate'), \
                     patch.object(coordinator, 'GLOBAL_RECEIPT_DIR', control), \
                     patch.object(coordinator.native, 'object_json', side_effect=decode):
                    with self.assertRaisesRegex(RuntimeError, 'guard_lost_during_trial'):
                        coordinator.coordinate(lease, guard, manifest, urdf(), transmissions(),
                                               spawn, control, timeout=5)
                self.assertEqual(count[0], 40)
                self.assertEqual(guard.cancelled, [GOAL])
                self.assertTrue(lease.failed)
                events = [json.loads(line) for line in
                          (control/('worker-events-'+lease.session_id+'.jsonl')).read_text().splitlines()]
                self.assertEqual([e['count'] for e in events if e['event']=='feedback_summary'], [40])
            finally:
                guard.close()
                for process in processes:
                    if process.poll() is None: process.terminate()
                    process.wait(timeout=3)
                    for stream in (process.stdin, process.stdout, process.stderr): stream.close()

    def test_uuid_disk_failure_prevents_guard_handshake_and_worker_ack(self):
        manifest = prep.prepare(state(), urdf(), transmissions())
        with tempfile.TemporaryDirectory() as directory:
            control = Path(directory)/'stable-control'
            control.mkdir(mode=0o700)
            lease = bridge.GuardLease(directory, manifest['input']['reference_20d'], lambda: True)
            guard = FakeGuard(lease)
            processes = []
            original_fsync = os.fsync
            def fail_uuid_fsync(fd):
                try: name = os.readlink('/proc/self/fd/' + str(fd))
                except OSError: name = ''
                if '/worker-events-' in name and '"event": "uuid_request"' in Path(name).read_text():
                    raise OSError('simulated_uuid_disk_failure')
                return original_fsync(fd)
            def spawn(_, intent, uid):
                process = worker_process(manifest, lease.session_id, 'success')
                processes.append(process)
                return process
            try:
                with patch.object(bridge.arm, 'physical_release_gate'), \
                     patch.object(coordinator, 'GLOBAL_RECEIPT_DIR', control), \
                     patch.object(coordinator.os, 'fsync', side_effect=fail_uuid_fsync):
                    with self.assertRaisesRegex(OSError, 'simulated_uuid_disk_failure'):
                        coordinator.coordinate(lease, guard, manifest, urdf(), transmissions(),
                                               spawn, control, timeout=5)
                self.assertFalse(guard.goal_acknowledged.is_set())
                self.assertIsNone(lease.goal_id)
                self.assertEqual(guard.cancelled, [])
                self.assertTrue((control/'PENDING_OR_UNRESOLVED.json').is_file())
            finally:
                guard.close()
                for process in processes:
                    if process.poll() is None: process.terminate()
                    process.wait(timeout=3)
                    for stream in (process.stdin, process.stdout, process.stderr): stream.close()

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
                                bridge.native.check_lease_current(lease.path, time.monotonic)
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
                    self.assertEqual(events[-2]['event'], 'independent_cancel_requested')
                    self.assertEqual(events[-1]['event'], 'guard_diagnostics')
                    self.assertEqual(guard.cancelled, [GOAL])
                    self.assertFalse(events[-2]['physical_stop_verified'])
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
