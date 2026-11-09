import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from prepare_ball_current_observations import prepare
from prepare_ball_observations import RIGHT_HAND, TASK
from prepare_ball_candidate_targets import JOINTS


class CurrentObservationsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.capture = self.root / 'capture'
        self.capture.mkdir()
        (self.capture / 'rgb').mkdir()
        self.names = JOINTS + [f'joint_{i}' for i in range(13)]
        self.state = [float(i) for i in range(20)]
        self.fingers = [float(i) for i in range(7)]
        self.manifest = {'schema': 'cruzr-passive-episode-v1', 'training_ready': False,
                         'joint_names': self.names}
        self.quality = {'capture_checks_passed': True, 'training_ready': False,
                        'hands': {'hand_right': {'status': 'complete', 'capture_checks_passed': True}}}
        self.joint = {'kind': 'joints', 'source_ns': 100_000_000, 'received_monotonic_ns': 190_000_000,
                      'message': {'name': self.names, 'position': self.state}}
        self.hand = {'kind': 'hand_right', 'source_ns': 110_000_000, 'received_monotonic_ns': 195_000_000,
                     'message': {'name': RIGHT_HAND, 'position': self.fingers}}
        self.rgb = {'kind': 'rgb', 'source_ns': 120_000_000, 'received_monotonic_ns': 200_000_000,
                    'png_file': 'rgb/000001.png',
                    'png_sha256': hashlib.sha256(b'example image').hexdigest()}
        self.row = {'png_file': 'rgb/000001.png', 'image_source_ns': 120_000_000,
                    'state20': self.state, 'hand_right': {'name': RIGHT_HAND, 'position': self.fingers},
                    'source_delta_ms': {'joints': -20.0, 'hand_right': -10.0},
                    'reception_delta_ms': {'joints': -25.0, 'hand_right': -15.0},
                    'source_lines': {'joints': 1, 'hand_right': 2}}
        (self.capture / 'rgb/000001.png').write_bytes(b'example image')
        self.write_capture()

    def write_capture(self):
        for name, value in (('manifest.json', self.manifest), ('quality.json', self.quality)):
            (self.capture / name).write_text(json.dumps(value))
        (self.capture / 'aligned.jsonl').write_text(json.dumps(self.row) + '\n')
        (self.capture / 'samples.jsonl').write_text(json.dumps(self.joint) + '\n' + json.dumps(self.hand) + '\n' + json.dumps(self.rgb) + '\n')
        paths = ['manifest.json', 'quality.json', 'aligned.jsonl', 'samples.jsonl', 'rgb/000001.png']
        (self.capture / 'SHA256SUMS').write_text(''.join(
            hashlib.sha256((self.capture / path).read_bytes()).hexdigest() + '  ' + path + '\n'
            for path in paths))

    def test_exports_no_actions_and_checks_raw_states(self):
        result = prepare(self.capture, self.root / 'out')
        self.assertEqual(result['task'], TASK)
        self.assertFalse(result['has_action_column'])
        self.assertFalse(result['physical_control_qualified'])
        self.assertEqual(result['state_names'], self.names + RIGHT_HAND)
        self.assertEqual(result['records'][0]['state27'], self.state + self.fingers)
        self.assertEqual(result['records'][0]['status'], 'unreviewed')
        self.assertNotIn('action', result['records'][0])

    def test_rejects_bad_image_hash(self):
        (self.capture / 'rgb/000001.png').write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError, 'image integrity'):
            prepare(self.capture, self.root / 'out')

    def test_rejects_incomplete_hand(self):
        self.quality['hands']['hand_right']['status'] = 'partial'
        self.write_capture()
        with self.assertRaisesRegex(ValueError, 'quality'):
            prepare(self.capture, self.root / 'out')

    def test_rejects_nominal_future_state(self):
        self.row['source_delta_ms']['hand_right'] = 1.0
        self.write_capture()
        with self.assertRaisesRegex(ValueError, 'no nominally causal'):
            prepare(self.capture, self.root / 'out')

    def test_rejects_raw_state_disagreement(self):
        self.hand['message']['position'] = [0.0] * 7
        self.write_capture()
        with self.assertRaisesRegex(ValueError, 'aligned and raw state differ'):
            prepare(self.capture, self.root / 'out')

    def test_rejects_future_received_state(self):
        self.hand['received_monotonic_ns'] = self.rgb['received_monotonic_ns'] + 1
        self.write_capture()
        with self.assertRaisesRegex(ValueError, 'not received before image'):
            prepare(self.capture, self.root / 'out')

    def test_rejects_raw_image_timestamp_mismatch(self):
        self.rgb['source_ns'] += 1
        self.write_capture()
        with self.assertRaisesRegex(ValueError, 'raw image reference mismatch'):
            prepare(self.capture, self.root / 'out')

    def test_does_not_overwrite(self):
        out = self.root / 'out'
        out.mkdir()
        with self.assertRaisesRegex(ValueError, 'output must be new'):
            prepare(self.capture, out)


if __name__ == '__main__':
    unittest.main()
