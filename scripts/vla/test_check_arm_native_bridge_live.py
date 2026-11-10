"""Passive bridge-check tests with local simulated subprocesses only."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent/'runtime'))
import arm_from_pico_supervised as arm
import arm_native_bridge_check_remote as remote
import check_arm_native_bridge_live as wrapper
import test_head_from_pico_supervised as head_tests


def simulated_guard_source():
    body = json.dumps(arm.BODY)
    return '''import json,select,sys,time
session=json.loads(sys.stdin.readline())
session_id=session['session_id']
guard='a'*32
body=json.loads(%r)
def emit(event,**kw):
 print(json.dumps(dict(event=event,goal_uuid=guard,monotonic=time.monotonic(),**kw)),flush=True)
def telemetry():
 emit('telemetry',position=body,velocity={n:0.0 for n in body},estop=0,servo_stop=0)
emit('BRIDGE_READY')
telemetry()
emit('pre_dispatch_ready',session_id=session_id,challenge='c'*32)
ack=json.loads(sys.stdin.readline())
assert ack['session_id']==session_id
telemetry()
emit('ARM_GUARD_READY',session_id=session_id,movement_commands=0,physical_control_qualified=False)
while True:
 ready,_,_=select.select([sys.stdin],[],[],.05)
 if ready:
  line=sys.stdin.readline()
  if not line:break
  cmd=json.loads(line)
  if cmd['event']=='stop_guard':
   emit('ARM_GUARD_STOPPED',movement_commands=0,physical_stop_confirmed=False);break
  if cmd['event']=='prepare_goal_uuid':
   cmd['event']='goal_uuid_ready';emit(**cmd)
 telemetry()
''' % body


def payload():
    with patch.object(head_tests, 'subject', arm):
        session = head_tests.proof()
    session['mode'] = 'check'; session['operator_confirmed'] = False
    return {'session': session, 'initial': dict(arm.BODY), 'guard_source': simulated_guard_source()}


class PassiveCheckTests(unittest.TestCase):
    def test_revocation_receipt_rejects_write_error_and_natural_expiry(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'lease.json'
            done = threading.Event(); done.set()
            lease = SimpleNamespace(path=path, _async_failure_done=done,
                                    _async_failure_error='OSError: disk')
            path.write_text('{"deadline":0}')
            with self.assertRaisesRegex(RuntimeError, 'write_failed'):
                remote.require_persisted_revocation(lease)
            lease._async_failure_error = None
            path.write_text('{"deadline":0.001}')
            with self.assertRaisesRegex(RuntimeError, 'not_persisted'):
                remote.require_persisted_revocation(lease)
            path.write_text('{"deadline":0}')
            remote.require_persisted_revocation(lease)

    def test_simulated_child_handshake_and_loss_without_goal(self):
        result = remote.check(payload())
        self.assertEqual(result['status'], 'PASS_PASSIVE_GUARD_UUID_AND_LEASE_REVOCATION')
        self.assertEqual(result['movement_commands'], 0)
        self.assertFalse(result['physical_stop_verified'])

    def test_reference_mismatch_is_rejected_without_starting_child(self):
        row = payload(); row['initial']['R_elbow_yaw_joint'] = -4.0
        with patch.object(remote.subprocess, 'Popen', side_effect=AssertionError('no child')):
            with self.assertRaises(ValueError): remote.check(row)

    def test_run_rejected_without_read_or_preflight(self):
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('must not read')):
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(wrapper.main(['--run']), 2)

    def test_streamed_sources_compile(self):
        coordinator, guard, hashes = wrapper.source_bundle()
        compile(coordinator, '<coordinator>', 'exec')
        compile(guard, '<guard>', 'exec')
        self.assertEqual(len(hashes), 8)
        self.assertIn('monitor_only=True', guard)

    def test_streamed_modules_load_before_invalid_payload_is_rejected(self):
        coordinator, _, _ = wrapper.source_bundle()
        sentinel = 'TEST_SOURCE_END'
        bootstrap = ('import sys\nparts=[]\nfor line in sys.stdin:\n'
                     ' if line.rstrip("\\n")=='+repr(sentinel)+': break\n'
                     ' parts.append(line)\n'
                     'exec(compile("".join(parts),"<coordinator>","exec"))\n')
        child = subprocess.run([sys.executable, '-B', '-c', bootstrap],
                               input=coordinator+'\n'+sentinel+'\n{}\n',
                               text=True, capture_output=True, timeout=8)
        self.assertNotEqual(child.returncode, 0)
        self.assertIn('BRIDGE_READY', child.stdout)
        self.assertIn('invalid_check_payload', child.stderr)


if __name__ == '__main__':
    unittest.main()
