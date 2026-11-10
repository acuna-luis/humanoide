"""Local pipe tests; no ROS, SSH, task installation or robot movement."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from unittest.mock import patch

import check_pico_wrist_full_passive as subject
sys.path.insert(0, str(Path(__file__).resolve().parent / 'runtime'))
import pico_wrist_full_passive_remote as remote


class FullPassiveTests(unittest.TestCase):
    def test_run_rejects_before_check_or_network(self):
        with patch.object(subject, 'check', side_effect=AssertionError('must not connect')), \
             contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(subject.main(['--run']), 2)

    def test_sources_compile_and_worker_has_no_top_level_action_dispatch(self):
        import ast
        host, guard, worker, hashes = subject.source_bundle()
        for name, code in (('host', host), ('guard', guard), ('worker', worker)):
            compile(code, '<' + name + '>', 'exec')
        self.assertIn('pico_wrist_full_passive_remote', hashes)
        outer = ast.parse(worker)
        forbidden = {'send_goal_async', 'run_action', 'stage_task', 'call_async'}
        calls = [node.func.attr for node in ast.walk(outer) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Attribute)]
        self.assertFalse(forbidden.intersection(calls))

    def test_heartbeat_uses_exact_bound_guard_bundle(self):
        host, guard, worker, hashes = subject.source_bundle(guard_heartbeat=True)
        _, bound_guard, _ = subject.trial.source_bundle()
        self.assertEqual(guard, bound_guard)
        self.assertIn('guard_can_cancel=True', guard)
        self.assertIn('__pico_verified_stream__', guard)
        for source in (host, guard, worker): compile(source, '<passive-source>', 'exec')

    def test_host_modules_import_without_pc_binding_on_motion(self):
        host, _, _, hashes = subject.source_bundle()
        self.assertIn('pico_wrist_trial_admission', hashes)
        module_code = host.rsplit('import json\nprint(', 1)[0]
        module_code += ('assert "pico_wrist_trial_admission" in sys.modules\n'
                        'assert "pico_wrist_native_coordinator" in sys.modules\n'
                        'assert "pico_wrist_review_binding" not in sys.modules\n')
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, '-I', '-B', '-'], input=module_code,
                                    cwd=directory, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_real_pipes_challenge_response_and_result(self):
        token = 'a' * 32
        child_code = '''import json,sys
token='a'*32
print(json.dumps({'event':'BRIDGE_READY'}),flush=True)
print(json.dumps({'event':'HOST_PREFLIGHT_READY','session_id':token,'challenge':'b'*32}),flush=True)
ack=json.loads(sys.stdin.readline())
assert ack['session_id']==token and ack['challenge']=='b'*32
print(json.dumps({'event':'HOST_HEARTBEAT_READY','session_id':token}),flush=True)
ping={'event':'pc_ping','session_id':token,'sequence':0,'nonce':'c'*32}
print(json.dumps(ping),flush=True)
pong=json.loads(sys.stdin.readline())
assert pong==dict(ping,event='pc_pong')
print(json.dumps({'status':'PASS_PC_HOST_GUARD_READONLY_NATIVE','movement_commands':0,
                  'action_goals_created':0,'physical_control_qualified':False}),flush=True)
'''
        process = subprocess.Popen([sys.executable, '-B', '-u', '-c', child_code],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
        try:
            with tempfile.TemporaryDirectory() as directory:
                result = subject.drive(process, token, time.monotonic(), Path(directory))
                self.assertEqual(result['movement_commands'], 0)
                self.assertEqual(result['action_goals_created'], 0)
        finally:
            if process.poll() is None: process.kill(); process.wait()
            for stream in (process.stdin, process.stdout, process.stderr): stream.close()

    def test_unexpected_session_is_rejected(self):
        code = ('import json;print(json.dumps({"event":"HOST_PREFLIGHT_READY",'
                '"session_id":"bad","challenge":"b"*32}),flush=True)')
        process = subprocess.Popen([sys.executable, '-B', '-u', '-c', code],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
        try:
            with tempfile.TemporaryDirectory() as directory, \
                 self.assertRaisesRegex(ValueError, 'preflight'):
                subject.drive(process, 'a'*32, time.monotonic(), Path(directory))
        finally:
            if process.poll() is None: process.kill(); process.wait()
            for stream in (process.stdin, process.stdout, process.stderr): stream.close()

    def run_fake_host(self, *, bad_worker=False, guard_heartbeat=False, drop_heartbeat=False,
                      model_diagnostic=False):
        token = uuid.uuid4().hex
        arm = remote.arm
        session = {'schema':'cruzr_head_pico_preflight_v1', 'task_sha256':arm.TASK_SHA,
                   'pico_sha256':arm.PICO_SHA, 'work_mode':'joystick',
                   'operator_confirmed':False, 'controller_status_writers_checked':True,
                   'age_at_handoff_s':1.0, 'session_id':token, 'mode':'check'}
        reference = dict(arm.BODY)
        payload = {'session': session, 'manifest':{'input':{'reference_20d':reference},
                   'candidate':{'goal':{'task_name':'synthetic','yaml_args':'{}'},
                                'xml_sha256':'e'*64}},
                   'urdf_text':'', 'transmissions_text':'',
                   'guard_source':'pass', 'worker_source':'pass'}
        if guard_heartbeat:
            payload.update(guard_heartbeat=True,
                           guard_sha256=hashlib.sha256(b'pass').hexdigest())
        if model_diagnostic:
            payload['model_diagnostic'] = True

        class Pc:
            def __init__(self, *args, **kwargs): pass
            def await_ready(self, timeout): pass
            def alive(self): return True
            def close(self): return True
            def begin_model_permit(self, goal_id, task_sha256):
                self.request = {'goal_id':goal_id, 'task_sha256':task_sha256}
            def permit_snapshot(self):
                return dict(self.request, decision_sha256='f'*64,
                            deadline_monotonic_ns=time.monotonic_ns()+1_000_000_000)

        class Output:
            failed = False
            def __init__(self, fd): pass
            def emit(self, row): return True

        guard_source = '''import json,select,sys,time
session=json.loads(sys.argv[1]); pos=json.loads(sys.argv[2]); gid='a'*32
diagnostic=json.loads(sys.argv[3]); drop_heartbeat=json.loads(sys.argv[4]); heartbeat_count=0
def send(event,**fields):
 print(json.dumps(dict(event=event,monotonic=time.monotonic(),goal_uuid=gid,**fields)),flush=True)
def telemetry():
 send('telemetry',position=pos,velocity={x:0 for x in pos},estop=0,servo_stop=0)
telemetry()
send('pre_dispatch_ready',session_id=session['session_id'],challenge='b'*32)
ack=json.loads(sys.stdin.readline())
assert ack['session_id']==session['session_id'] and ack['challenge']=='b'*32
telemetry()
send('ARM_GUARD_READY',session_id=session['session_id'],movement_commands=0,physical_control_qualified=False)
next_sample=time.monotonic()+.1
while True:
 if time.monotonic()>=next_sample:
  telemetry(); next_sample=time.monotonic()+.1
 readable,_,_=select.select([sys.stdin],[],[],0.05)
 if not readable: continue
 line=sys.stdin.readline()
 if not line: break
 command=json.loads(line)
 if command['event']=='supervisor_heartbeat':
  if drop_heartbeat: sys.exit(9)
  assert diagnostic and command['sequence']==heartbeat_count
  heartbeat_count+=1
  continue
 if command['event']=='stop_guard':
  assert not diagnostic or heartbeat_count>=2
  send('ARM_GUARD_STOPPED',movement_commands=0,physical_stop_confirmed=False); break
 assert not diagnostic
 assert command['event']=='prepare_goal_uuid'
 send('goal_uuid_ready',session_id=command['session_id'],guard_id=command['guard_id'],
      goal_id=command['goal_id'],challenge=command['challenge'])
'''
        worker_source = '''import json,sys,time
path=sys.argv[1]; hashes=json.loads(sys.argv[2])
lease=json.load(open(path)); assert time.monotonic()<lease['deadline']
print(json.dumps({'event':'NATIVE_READONLY_READY','fingerprints':hashes,
 'goal_format_valid':True,'lease_fresh':True,'monotonic':time.monotonic()}),flush=True)
'''
        started = []
        def start(container, setup, source, data, *, stderr, verified=None):
            if container == 'ros':
                if guard_heartbeat:
                    assert verified == {'role':'guard', 'session_id':token,
                                        'source_sha256':payload['guard_sha256']}
                command = [sys.executable, '-u', '-c', guard_source,
                           json.dumps(data), json.dumps(reference), json.dumps(guard_heartbeat),
                           json.dumps(drop_heartbeat)]
            else:
                hashes = {} if bad_worker else remote.native.SUPPORTED_NATIVE_CLASSES
                command = [sys.executable, '-u', '-c', worker_source,
                           data['lease_path'], json.dumps(hashes)]
            child = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, bufsize=0)
            started.append(child)
            return child

        try:
            with patch.object(remote.launch, 'HostOutput', Output), \
                 patch.object(remote.launch, 'pc_preflight_handoff'), \
                 patch.object(remote.launch, 'discover_containers', return_value=('app', 'ros')), \
                 patch.object(remote.launch, 'verify_shared_tmp'), \
                 patch.object(remote.launch, 'start_streamed', side_effect=start), \
                 patch.object(remote.heartbeat, 'PcHeartbeat', Pc), \
                 patch.object(remote.probe, 'validate'):
                if bad_worker:
                    with self.assertRaisesRegex(RuntimeError, 'native_worker_check_failed'):
                        remote.check(payload)
                    return None
                return remote.check(payload)
        finally:
            for child in started:
                if child.poll() is None: child.kill(); child.wait()
                for stream in (child.stdin, child.stdout):
                    if stream is not None and not stream.closed: stream.close()

    def test_full_host_guard_and_worker_with_real_local_pipes(self):
        result = self.run_fake_host()
        self.assertEqual(result['status'], 'PASS_PC_HOST_GUARD_READONLY_NATIVE')
        self.assertEqual(result['action_goals_created'], 0)
        self.assertFalse(result['physical_control_qualified'])

    def test_bad_native_fingerprint_fails_before_uuid_handshake(self):
        self.run_fake_host(bad_worker=True)

    def test_cancel_capable_heartbeat_without_uuid_or_cancel(self):
        with patch.object(remote.bridge.GuardLease, 'synchronize_uuid',
                          side_effect=AssertionError('UUID handoff is forbidden')), \
             patch.object(remote.bridge.GuardPipe, 'cancel_goal',
                          side_effect=AssertionError('cancellation is forbidden')):
            result = self.run_fake_host(guard_heartbeat=True)
        self.assertEqual(result['status'], 'PASS_PC_HOST_GUARD_HEARTBEAT_NO_GOAL')
        self.assertGreaterEqual(result['heartbeat_pulses_sent'], 2)
        self.assertEqual(result['uuid_handshakes'], 0)
        self.assertEqual(result['cancel_requests'], 0)
        self.assertFalse(result['physical_control_qualified'])
        self.assertIn('does not reproduce the original trajectory', result['limitations'])

    def test_heartbeat_requires_binding_before_live_preflight(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'input'
            path.write_text('{}')
            with patch.object(subject.probe, 'validate'), \
                 patch.object(subject.preflight, 'preflight', side_effect=AssertionError('must not connect')), \
                 self.assertRaisesRegex(ValueError, 'heartbeat_check_requires_review_binding'):
                subject.check(path, path, path, guard_heartbeat=True)

    def test_heartbeat_guard_failure_cannot_pass(self):
        with self.assertRaises((RuntimeError, TimeoutError)):
            self.run_fake_host(guard_heartbeat=True, drop_heartbeat=True)

    def test_model_permit_with_guard_never_hands_uuid_or_cancels(self):
        with patch.object(remote.bridge.GuardLease, 'synchronize_uuid',
                          side_effect=AssertionError('UUID handoff is forbidden')), \
             patch.object(remote.bridge.GuardPipe, 'cancel_goal',
                          side_effect=AssertionError('cancellation is forbidden')):
            result = self.run_fake_host(guard_heartbeat=True, model_diagnostic=True)
        self.assertEqual(result['status'], 'PASS_PC_MODEL_GUARD_PERMIT_NO_GOAL')
        self.assertTrue(result['model_permit_received'])
        self.assertTrue(result['correlation_id_never_handed_to_guard'])
        self.assertEqual(result['movement_commands'], 0)
        self.assertEqual(result['action_goals_created'], 0)
        self.assertEqual(result['uuid_handshakes'], 0)
        self.assertEqual(result['cancel_requests'], 0)

    def test_model_diagnostic_requires_guard_heartbeat_before_network(self):
        with patch.object(subject.preflight, 'preflight', side_effect=AssertionError('must not connect')), \
             self.assertRaisesRegex(ValueError, 'model_diagnostic_requires_guard_heartbeat'):
            subject.check(Path('/missing'), Path('/missing'), Path('/missing'), model_diagnostic=True)

    def test_model_driver_supplies_permit_only_after_guard_ready(self):
        token = 'a'*32
        child_code = '''import json,sys
token='a'*32
def send(row): print(json.dumps(row),flush=True)
send({'event':'HOST_PREFLIGHT_READY','session_id':token,'challenge':'b'*32})
assert json.loads(sys.stdin.readline())['challenge']=='b'*32
send({'event':'HOST_HEARTBEAT_READY','session_id':token})
send({'event':'PASSIVE_MODEL_INFERENCE_READY','session_id':token})
request={'goal_id':'12345678-1234-1234-1234-123456789abc','task_sha256':'d'*64}
ping={'event':'pc_ping','session_id':token,'sequence':0,'nonce':'c'*32,'model_request':request}
send(ping)
reply=json.loads(sys.stdin.readline())
assert reply['model_permit']==dict(request,decision_sha256='e'*64,budget_ns=1000000000)
send({'status':'PASS_PC_MODEL_GUARD_PERMIT_NO_GOAL','movement_commands':0,
      'action_goals_created':0,'uuid_handshakes':0,'cancel_requests':0,
      'heartbeat_pulses_sent':3,'physical_control_qualified':False,
      'model_permit_received':True,'correlation_id_never_handed_to_guard':True,
      'decision_sha256':'e'*64})
'''
        class Model:
            started = closed = False
            def start(self): self.started = True
            def permit(self, request):
                assert self.started
                return dict(request, decision_sha256='e'*64, budget_ns=1_000_000_000)
            def close(self): self.closed = True
        process = subprocess.Popen([sys.executable, '-B', '-u', '-c', child_code],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
        model=Model()
        try:
            with tempfile.TemporaryDirectory() as directory:
                result=subject.drive(process, token, time.monotonic(), Path(directory),
                                     guard_heartbeat=True, model=model)
            self.assertTrue(model.started)
            self.assertTrue(model.closed)
            self.assertEqual(result['decision_sha256'], 'e'*64)
        finally:
            if process.poll() is None: process.kill(); process.wait()
            for stream in (process.stdin, process.stdout, process.stderr): stream.close()


if __name__ == '__main__':
    unittest.main()
