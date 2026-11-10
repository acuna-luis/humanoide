"""Local relay tests using synthetic processes only; never connects to ROS."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

SCRIPT = Path(__file__).with_name('run_ball_live_shadow.py')
spec = importlib.util.spec_from_file_location('ball_live_relay', SCRIPT)
relay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(relay)


class RelayTests(unittest.TestCase):
    def test_old_observations_without_new_metadata_remain_shadow_compatible(self):
        old = {'state_names': list(relay.BODY_NAMES) + ['hand_'+str(i) for i in range(7)],
               'state27': [0.0]*27}
        self.assertIsNone(relay.observation_state(old))
        partial = dict(old, state20_velocity_rad_s=[0.0]*20)
        with self.assertRaisesRegex(ValueError, 'metadata_incomplete'):
            relay.observation_state(partial)

    def test_duplicate_image_identity_is_rejected_before_pending_replacement(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / 'passive_episode_remote.py').write_text('# synthetic source\n')
            (directory / 'live_ball_observation_adapter.py').write_text(
                'import sys\nfor line in sys.stdin: print(line, end="", flush=True)\n')
            server = ('import json,sys\n'
                      'print(json.dumps({"event":"ready","schema":"cruzr_ball_live_shadow_v1",'
                      '"physical_control_qualified":False,"model_sha256":'
                      + repr(relay.MODEL_SHA256) + '}),flush=True)\n'
                      'for line in sys.stdin: pass\n')
            row = {'schema':'cruzr_ball_live_observation_v1', 'image_sha256':'a'*64, 'image_source_ns':123}
            source = ('import sys,time,json; sys.stdin.buffer.read(); row='+repr(row)+'; '
                      'row["pc_received_monotonic_ns"]=time.monotonic_ns(); '
                      'print(json.dumps(row),flush=True); print(json.dumps(row),flush=True)')
            args = SimpleNamespace(startup_timeout=5, seconds=2, fps=.5)
            with (patch.object(relay, 'HERE', directory),
                  patch.object(relay, 'discover_vision', return_value='fake'),
                  patch.object(relay, 'collector_command', return_value=[sys.executable,'-u','-c',source]),
                  patch.object(relay, 'server_command', return_value=[sys.executable,'-u','-c',server]),
                  contextlib.redirect_stdout(io.StringIO()),
                  self.assertRaisesRegex(ValueError, 'duplicate_or_non_increasing_observation_identity')):
                relay.run(args)

    def test_stream_bounds_and_fragmentation(self):
        buffers = {}
        self.assertEqual(relay.line_buffer(buffers, 'x', b'{"a":'), [])
        self.assertEqual(relay.line_buffer(buffers, 'x', b'1}\n{}\n'), [b'{"a":1}', b'{}'])
        with patch.object(relay, 'MAX_LINE', 3):
            with self.assertRaises(ValueError):
                relay.line_buffer({}, 'x', b'1234')

    def test_server_shell_arguments_are_quoted_and_bad_host_rejected(self):
        args = SimpleNamespace(host='user@server', port=2649, runner='/tmp/a b',
            train='/tmp/train', volume='ok.volume', checkpoint='/tmp/model',
            device='cpu', seed=1, max_samples=100)
        command = relay.server_command(args)
        self.assertIn("'/tmp/a b'", command[-1])
        args.host = 'x@host;rm'
        with self.assertRaises(ValueError):
            relay.server_command(args)

    def test_ready_precedes_capture_and_prediction_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / 'passive_episode_remote.py').write_text('# synthetic source\n')
            (directory / 'live_ball_observation_adapter.py').write_text(
                'import sys\nfor line in sys.stdin: print(line, end="", flush=True)\n')
            server = '''import json,sys
print(json.dumps({"event":"ready","schema":"cruzr_ball_live_shadow_v1","physical_control_qualified":False,"model_sha256":"e707eea07b58e14b979e78463b94ba75a52b1c18abf8076aebc8aa34ac77f8da"}),flush=True)
count=0
for line in sys.stdin:
    row=json.loads(line)
    count+=1
    print(json.dumps({"event":"prediction","physical_control_qualified":False,"prediction":[0.0]*8,"proposed_minus_observed_rad":[0.0]*7,"image_sha256":row["image_sha256"],"image_source_ns":row["image_source_ns"]}),flush=True)
print(json.dumps({"event":"done","physical_control_qualified":False,"samples":count}),flush=True)
'''
            row = {'schema':'cruzr_ball_live_observation_v1', 'image_sha256':'a'*64, 'image_source_ns':123,
                   'state_names':list(relay.BODY_NAMES)+['hand_'+str(i) for i in range(7)],
                   'state27':[0.0]*27, 'state20_velocity_rad_s':[0.0]*20}
            source = ('import sys,time,json; sys.stdin.buffer.read(); row=' + repr(row) + '; '
                      'row["pc_joint_received_monotonic_ns"]=time.monotonic_ns(); '
                      'row["pc_received_monotonic_ns"]=time.monotonic_ns(); print(json.dumps(row), flush=True)')
            args = SimpleNamespace(startup_timeout=5, seconds=2, fps=.5)
            with (patch.object(relay, 'HERE', directory),
                  patch.object(relay, 'discover_vision', return_value='fake'),
                  patch.object(relay, 'collector_command', return_value=[sys.executable, '-u', '-c', source]),
                  patch.object(relay, 'server_command', return_value=[sys.executable, '-u', '-c', server]),
                  contextlib.redirect_stdout(io.StringIO()) as output):
                relay.run(args)
            events = [json.loads(line) for line in output.getvalue().splitlines()]
            self.assertEqual([e['event'] for e in events], ['model_ready', 'prediction', 'done', 'summary'])
            self.assertGreaterEqual(events[1]['pc_adapter_to_prediction_seconds'], 0)
            self.assertEqual(events[1]['paired_state20']['names'], list(relay.BODY_NAMES))
            self.assertEqual(events[1]['paired_state20']['velocities'], [0.0]*20)
            self.assertLessEqual(events[1]['paired_state20']['received_monotonic_ns'],
                                 events[1]['prediction_received_monotonic_ns'])
            self.assertEqual(events[-1]['observations_sent'], 1)
            self.assertEqual(events[-1]['movement_commands'], 0)

    def test_stalled_collector_upload_has_bounded_timeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / 'passive_episode_remote.py').write_bytes(b'x' * (2 * 1024 * 1024))
            (directory / 'live_ball_observation_adapter.py').write_text('import sys; sys.stdin.buffer.read()')
            ready = {'event': 'ready', 'schema': 'cruzr_ball_live_shadow_v1',
                     'physical_control_qualified': False, 'model_sha256': relay.MODEL_SHA256}
            server = 'import time; print(' + repr(json.dumps(ready)) + ',flush=True); time.sleep(5)'
            args = SimpleNamespace(startup_timeout=5, seconds=2, fps=.5)
            with (patch.object(relay, 'HERE', directory),
                  patch.object(relay, 'MAX_COLLECTOR_UPLOAD_SECONDS', .2),
                  patch.object(relay, 'discover_vision', return_value='fake'),
                  patch.object(relay, 'collector_command', return_value=[sys.executable, '-c', 'import time; time.sleep(5)']),
                  patch.object(relay, 'server_command', return_value=[sys.executable, '-u', '-c', server]),
                  contextlib.redirect_stdout(io.StringIO()),
                  self.assertRaisesRegex(TimeoutError, 'collector source upload stalled')):
                relay.run(args)

    def test_one_shot_drains_later_observations_after_server_exits(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / 'passive_episode_remote.py').write_text('# synthetic source\n')
            (directory / 'live_ball_observation_adapter.py').write_text(
                'import sys\nfor line in sys.stdin: print(line, end="", flush=True)\n')
            ready = {'event':'ready', 'schema':'cruzr_ball_live_shadow_v1',
                     'physical_control_qualified':False, 'model_sha256':relay.MODEL_SHA256}
            server = '''import json,sys
print(json.dumps(READY),flush=True)
row=json.loads(sys.stdin.readline())
print(json.dumps({'event':'prediction','physical_control_qualified':False,'prediction':[0.0]*8,'proposed_minus_observed_rad':[0.0]*7,'image_sha256':row['image_sha256'],'image_source_ns':row['image_source_ns']}),flush=True)
print(json.dumps({'event':'done','physical_control_qualified':False,'samples':1}),flush=True)
'''.replace('READY', repr(ready))
            source = '''import json,sys,time
sys.stdin.buffer.read()
for i in range(3):
    if i: time.sleep(.15)
    row={'schema':'cruzr_ball_live_observation_v1','image_sha256':'a'*64,'image_source_ns':123+i,'pc_received_monotonic_ns':time.monotonic_ns()}
    print(json.dumps(row),flush=True)
'''
            args = SimpleNamespace(startup_timeout=5, seconds=2, fps=.5, one_shot=True)
            with (patch.object(relay, 'HERE', directory),
                  patch.object(relay, 'discover_vision', return_value='fake'),
                  patch.object(relay, 'collector_command', return_value=[sys.executable, '-u', '-c', source]),
                  patch.object(relay, 'server_command', return_value=[sys.executable, '-u', '-c', server]),
                  contextlib.redirect_stdout(io.StringIO()) as output):
                relay.run(args)
            events = [json.loads(line) for line in output.getvalue().splitlines()]
            self.assertEqual([e['event'] for e in events], ['model_ready', 'prediction', 'done', 'summary'])
            self.assertEqual(events[-1]['observations_sent'], 1)
            self.assertEqual(events[-1]['observations_dropped'], 2)
            self.assertEqual(events[-1]['predictions'], 1)

    def test_one_shot_parameters_allow_exactly_one_sample(self):
        required = ['relay', '--host', 'user@host', '--runner', '/runner', '--train', '/train',
                    '--volume', 'vol', '--checkpoint', '/checkpoint', '--one-shot', '--max-samples', '1']
        with patch.object(sys, 'argv', required), patch.object(relay, 'run') as run:
            self.assertEqual(relay.main(), 0)
            self.assertTrue(run.call_args.args[0].one_shot)
        with patch.object(sys, 'argv', required[:-1] + ['2']), \
             contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            relay.main()


if __name__ == '__main__':
    unittest.main()
