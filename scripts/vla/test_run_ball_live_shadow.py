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
            row = {'schema':'cruzr_ball_live_observation_v1', 'image_sha256':'a'*64, 'image_source_ns':123}
            source = ('import sys,time,json; sys.stdin.buffer.read(); row=' + repr(row) + '; '
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


if __name__ == '__main__':
    unittest.main()
