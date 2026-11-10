"""Local-only tests: no robot connections, publishers or action clients."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_head_from_pico_supervised as runner


class WrapperTests(unittest.TestCase):
    SUCCESS = ['pre_dispatch_ready', 'dispatch', 'acceptance', 'action_result', 'HEAD_SUCCEEDED_AND_STATIONARY']
    def test_confirmation_rejected_before_files_or_preflight(self):
        with tempfile.TemporaryDirectory() as parent:
            root = Path(parent)/'new'
            with patch.object(runner, 'EVIDENCE_ROOT', root), \
                 patch.object(runner, 'preflight', side_effect=AssertionError('must not connect')):
                with self.assertRaisesRegex(RuntimeError, 'physical_confirmation'):
                    runner.run_once(False)
                self.assertFalse(root.exists())

    def test_preflight_checks_local_and_current_mode_twice(self):
        with patch.object(runner, 'local_exclusivity') as local, \
             patch.object(runner, 'current_mode', return_value='joystick') as mode, \
             patch.object(runner.admission, 'inventory', return_value=('motion','walker-ros.ros2-1')) as check:
            result, started, container = runner.preflight()
            self.assertEqual(result, 'joystick')
            self.assertEqual(container, 'walker-ros.ros2-1')
            self.assertLessEqual(started, time.monotonic())
            self.assertEqual(local.call_count, 2)
            self.assertEqual(mode.call_count, 2)
            check.assert_called_once()

    def test_preflight_output_is_tee_d_without_closing_console(self):
        def sample():
            print('result observed', flush=True)
            print('diagnostic', file=sys.stderr, flush=True)
            return ('joystick', time.monotonic(), 'walker-ros.ros2-1')
        with tempfile.TemporaryDirectory() as parent:
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), \
                 patch.object(runner, 'preflight', side_effect=sample):
                runner.recorded_preflight(Path(parent))
                print('console remains open')
            self.assertIn('result observed', out.getvalue())
            self.assertIn('console remains open', out.getvalue())
            self.assertIn('diagnostic', err.getvalue())
            self.assertIn('result observed', (Path(parent)/'preflight-stdout.log').read_text())
            self.assertIn('diagnostic', (Path(parent)/'preflight-stderr.log').read_text())

    def test_bad_mode_fails_without_admission(self):
        with patch.object(runner, 'cc_call', return_value={'result':{'workMode':'teleop'}}):
            with self.assertRaisesRegex(RuntimeError, 'not_in_joystick'):
                runner.current_mode()

    def execute_fake_run(self, directory, rc, events):
        root = Path(directory)/'evidence'
        sources = {'metamove_head_probe':'pass\n', 'head_from_pico_readonly':'pass\n',
                   'head_from_pico_supervised':'pass\n'}
        with patch.object(runner, 'EVIDENCE_ROOT', root), \
             patch.object(runner, 'preflight', side_effect=lambda: ('joystick', time.monotonic(), 'walker-ros.ros2-1')), \
             patch.object(runner, 'source_bundle', return_value=(sources, 'pass\n')), \
             patch.object(runner, 'stream_remote', return_value=(rc, events)) as stream:
            if rc == 0 and events == self.SUCCESS:
                self.assertEqual(runner.run_once(True), 0)
            else:
                with self.assertRaisesRegex(RuntimeError, 'uncertain_or_unsuccessful'):
                    runner.run_once(True)
            stream.assert_called_once()
            return root

    def test_success_removes_only_own_marker_and_records_source(self):
        with tempfile.TemporaryDirectory() as parent:
            root = self.execute_fake_run(parent, 0, self.SUCCESS)
            self.assertFalse((root/'PENDING_OR_UNRESOLVED.json').exists())
            evidence = [p for p in root.iterdir() if p.is_dir()]
            self.assertEqual(len(evidence), 1)
            self.assertTrue(json.loads((evidence[0]/'result.json').read_text())['success'])
            self.assertTrue((evidence[0]/'head_from_pico_supervised.py').exists())

    def test_failure_keeps_marker_and_forbids_another_attempt(self):
        with tempfile.TemporaryDirectory() as parent:
            root = self.execute_fake_run(parent, 1, ['UNRESOLVED_MONITORING'])
            self.assertTrue((root/'PENDING_OR_UNRESOLVED.json').is_file())
            with patch.object(runner, 'EVIDENCE_ROOT', root), \
                 patch.object(runner, 'preflight', side_effect=AssertionError('must not connect')):
                with self.assertRaisesRegex(RuntimeError, 'manual_review'):
                    runner.run_once(True)

    def test_alert_blocks_success_even_with_success_event(self):
        with tempfile.TemporaryDirectory() as parent:
            root = self.execute_fake_run(parent, 0, ['pre_dispatch_ready', 'dispatch', 'acceptance', 'action_result',
                                                      'OPERATOR_ALERT', 'HEAD_SUCCEEDED_AND_STATIONARY'])
            self.assertTrue((root/'PENDING_OR_UNRESOLVED.json').exists())

    def test_stream_persists_telemetry_and_immediately_displays_alerts(self):
        sentinel = 'CODE_END_' + 'a'*32
        code = ("import sys,json;"
                "exec(\"for line in sys.stdin:\\n if line.strip() == '"+sentinel+"': break\");"
                "print(json.dumps({'event':'BRIDGE_READY'}),flush=True);s=json.loads(sys.stdin.readline());u='a'*32;"
                "print(json.dumps({'event':'telemetry','goal_uuid':u,'private':'joint_data'}),flush=True);"
                "print(json.dumps({'event':'OPERATOR_ALERT','goal_uuid':u,'reason':'sample'}),flush=True);"
                "print(json.dumps({'event':'UNRESOLVED_MONITORING','goal_uuid':u}),flush=True)")
        with tempfile.TemporaryDirectory() as parent:
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc, events = runner.stream_remote([sys.executable,'-B','-u','-c',code],
                                                  'unused input', sentinel, {'session_id':'b'*32},
                                                  time.monotonic(), Path(parent))
            self.assertEqual(rc, 0)
            self.assertIn('OPERATOR_ALERT', out.getvalue())
            self.assertIn('ALERTA', err.getvalue())
            self.assertNotIn('joint_data', out.getvalue())
            self.assertIn('joint_data', (Path(parent)/'remote-stdout.jsonl').read_text())
            self.assertIn('UNRESOLVED_MONITORING', events)

    def test_two_phase_handoff_and_silence_warning_before_dispatch(self):
        sentinel = 'CODE_END_' + 'c'*32
        child = f'''import sys,json,time
for line in sys.stdin:
 if line.strip()=={sentinel!r}: break
print(json.dumps({{'event':'BRIDGE_READY'}}),flush=True)
session=json.loads(sys.stdin.readline()); goal='d'*32; challenge='e'*32
print(json.dumps({{'event':'pre_dispatch_ready','goal_uuid':goal,'session_id':session['session_id'],'challenge':challenge}}),flush=True)
handoff=json.loads(sys.stdin.readline())
assert handoff['session_id']==session['session_id'] and handoff['challenge']==challenge
assert handoff['schema']=='cruzr_head_pico_handoff_v1' and handoff['inventory_age_s']>=0
time.sleep(1.4)
print(json.dumps({{'event':'dispatch','goal_uuid':goal,'task':'cruzr/move_head_lower'}}),flush=True)
print(json.dumps({{'event':'acceptance','goal_uuid':goal,'accepted':True}}),flush=True)
print(json.dumps({{'event':'action_result','goal_uuid':goal,'status':4,'desc':'SUCCEED'}}),flush=True)
print(json.dumps({{'event':'HEAD_SUCCEEDED_AND_STATIONARY','goal_uuid':goal}}),flush=True)
'''
        with tempfile.TemporaryDirectory() as parent:
            out, err = io.StringIO(), io.StringIO()
            session = {'session_id':'b'*32, 'age_at_handoff_s':0.0}
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc, events = runner.stream_remote([sys.executable,'-B','-u','-c',child],
                    'unused source', sentinel, session, time.monotonic(), Path(parent))
            self.assertEqual(rc, 0)
            self.assertIn('LOCAL_COMMUNICATION_ALERT', events)
            self.assertIn('falta telemetría', err.getvalue())
            handoff = json.loads((Path(parent)/'pre-dispatch-handoff.json').read_text())
            self.assertEqual(handoff['session_id'], 'b'*32)
            self.assertEqual(handoff['challenge'], 'e'*32)

    def test_invalid_goal_identity_never_receives_handoff(self):
        sentinel = 'CODE_END_' + 'c'*32
        child = f'''import sys,json
for line in sys.stdin:
 if line.strip()=={sentinel!r}: break
print(json.dumps({{'event':'BRIDGE_READY'}}),flush=True)
session=json.loads(sys.stdin.readline())
print(json.dumps({{'event':'telemetry','goal_uuid':'d'*32}}),flush=True)
print(json.dumps({{'event':'pre_dispatch_ready','goal_uuid':'f'*32,
 'session_id':session['session_id'],'challenge':'e'*32}}),flush=True)
assert sys.stdin.readline()==''
'''
        with tempfile.TemporaryDirectory() as parent:
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc, events = runner.stream_remote([sys.executable,'-B','-u','-c',child],
                    'unused source', sentinel, {'session_id':'b'*32},
                    time.monotonic(), Path(parent))
            self.assertEqual(rc, 0)
            self.assertIn('OUTPUT_INVALID', events)
            self.assertFalse((Path(parent)/'pre-dispatch-handoff.json').exists())

    def test_source_writer_handles_partial_writes(self):
        class Partial:
            def __init__(self): self.data = bytearray()
            def write(self, block):
                part = bytes(block[:2]); self.data.extend(part); return len(part)
            def flush(self): pass
        stream = Partial()
        runner.write_all(stream, b'1234567')
        self.assertEqual(stream.data, b'1234567')

    def test_remote_command_never_adds_process_killing_timeout(self):
        text = ' '.join(runner.remote_command('walker-ros.ros2-1', 'CODE_END_'+'a'*32))
        self.assertNotIn('timeout ', text)
        self.assertNotIn('ServerAliveInterval', text)
        with self.assertRaises(RuntimeError):
            runner.remote_command('other-container', 'CODE_END_'+'a'*32)

    def test_bundle_hands_actual_session_to_main_without_direct_entry(self):
        import subprocess
        with tempfile.TemporaryDirectory() as parent:
            root = Path(parent)
            sources = {}
            for name, source in {
                'metamove_head_probe': 'if __name__ == "__main__": raise SystemExit(99)\n',
                'head_from_pico_readonly': 'if __name__ == "__main__": raise SystemExit(98)\n',
                'head_from_pico_supervised': 'import json\ndef main(session,*,dry_run):\n print(json.dumps({"session":session,"dry_run":dry_run})); return 0\nif __name__ == "__main__": raise SystemExit(97)\n',
            }.items():
                path = root/(name+'.py'); path.write_text(source); sources[name] = path
            session = {'schema':'cruzr_head_pico_preflight_v1', 'session_id':'a'*32,
                       'age_at_handoff_s':1.25, 'operator_confirmed':True}
            with patch.object(runner, 'SOURCES', sources):
                _, code = runner.source_bundle(dry_run=True)
            result = subprocess.run([sys.executable, '-B', '-c', code],
                                    input=json.dumps(session)+'\n', capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            lines = result.stdout.splitlines()
            self.assertEqual(json.loads(lines[0])['event'], 'BRIDGE_READY')
            self.assertEqual(json.loads(lines[1]), {'session':session,'dry_run':True})

    def test_check_hands_false_operator_confirmation_to_same_runtime(self):
        with tempfile.TemporaryDirectory() as parent, \
             patch.object(runner, 'EVIDENCE_ROOT', Path(parent)/'evidence'), \
             patch.object(runner, 'preflight', side_effect=lambda: ('joystick', time.monotonic(), 'walker-ros.ros2-1')), \
             patch.object(runner, 'source_bundle', return_value=({}, 'source')) as bundle, \
             patch.object(runner, 'stream_remote', return_value=(0, ['pre_dispatch_ready',
                       'PICO_HEAD_SUPERVISED_DRY_RUN_PASSED'])) as stream:
            self.assertEqual(runner.check_full(), 0)
            bundle.assert_called_once_with(dry_run=True)
            session = stream.call_args.args[3]
            self.assertIs(session['operator_confirmed'], False)
            self.assertEqual(session['mode'], 'check')

    def test_check_rejects_any_dispatch_even_if_dry_event_present(self):
        with tempfile.TemporaryDirectory() as parent, \
             patch.object(runner, 'EVIDENCE_ROOT', Path(parent)/'evidence'), \
             patch.object(runner, 'preflight', side_effect=lambda: ('joystick', time.monotonic(), 'walker-ros.ros2-1')), \
             patch.object(runner, 'source_bundle', return_value=({}, 'source')), \
             patch.object(runner, 'stream_remote', return_value=(0, ['pre_dispatch_ready','dispatch',
                       'PICO_HEAD_SUPERVISED_DRY_RUN_PASSED'])):
            with self.assertRaisesRegex(RuntimeError, 'dry_run_failed'):
                runner.check_full()


if __name__ == '__main__':
    unittest.main()
