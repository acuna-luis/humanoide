"""Historical reconstruction must preserve source data and remain offline-only."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

from live_ball_observation_adapter import PROFILE, RIGHT_HAND
from prepare_ball_historical_shadow_input import prepare


def png():
    def chunk(kind, data):
        return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data) & 0xffffffff)
    pixels = (b'\0' + b'\x12\x34\x56' * 960) * 576
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', 960, 576, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(pixels)) + chunk(b'IEND', b''))


def capture(root):
    names = json.loads(PROFILE.read_text())['joint_names']
    (root / 'rgb').mkdir()
    raw = png()
    (root / 'rgb/000000.png').write_bytes(raw)
    manifest = {'schema': 'cruzr-passive-episode-v1', 'training_ready': False, 'joint_names': names}
    quality = {'capture_checks_passed': True, 'training_ready': False,
               'hands': {'hand_right': {'capture_checks_passed': True}}}
    (root / 'manifest.json').write_text(json.dumps(manifest))
    (root / 'quality.json').write_text(json.dumps(quality))
    (root / 'aligned.jsonl').write_text('')
    rows = [
        {'kind': 'start', 'movement_commands': 0},
        {'kind': 'joints', 'source_ns': 1000000000, 'received_monotonic_ns': 2000000000,
         'message': {'name': names, 'position': [float(i) for i in range(20)]}},
        {'kind': 'hand_right', 'source_ns': 1000000000, 'received_monotonic_ns': 2000000000,
         'message': {'name': RIGHT_HAND, 'position': [0.1] * 7}},
        {'kind': 'ready'},
        {'kind': 'rgb', 'source_ns': 1000000001, 'received_monotonic_ns': 2000000001,
         'png_file': 'rgb/000000.png', 'png_sha256': hashlib.sha256(raw).hexdigest()},
    ]
    (root / 'samples.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in rows))
    files = ['manifest.json', 'quality.json', 'aligned.jsonl', 'samples.jsonl', 'rgb/000000.png']
    sums = ''.join(hashlib.sha256((root / name).read_bytes()).hexdigest() + '  ' + name + '\n' for name in files)
    (root / 'SHA256SUMS').write_text(sums)
    return raw, hashlib.sha256(sums.encode()).hexdigest()


class HistoricalInputTests(unittest.TestCase):
    def test_reconstructs_source_and_marks_as_historical(self):
        import base64
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'capture'; root.mkdir()
            raw, checksum = capture(root)
            out = Path(d) / 'one.jsonl'
            prepare(root, out, checksum)
            row = json.loads(out.read_text())
            self.assertEqual(base64.b64decode(row['png_b64']), raw)
            self.assertEqual(row['image_source_ns'], 1000000001)
            self.assertEqual(row['joint_source_ns'], 1000000000)
            self.assertEqual(row['received_monotonic_ns']['image'], 2000000001)
            self.assertEqual(row['state27'], [float(i) for i in range(20)] + [0.1] * 7)
            self.assertEqual(row['source_status'], 'historical_recording_not_live')
            self.assertNotIn('pc_received_monotonic_ns', row)
            self.assertIs(row['physical_control_qualified'], False)

    def test_bad_checksum_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'capture'; root.mkdir(); capture(root)
            out = Path(d) / 'one.jsonl'
            with self.assertRaises(ValueError): prepare(root, out, '0' * 64)
            self.assertFalse(out.exists())

    def test_corrupted_image_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'capture'; root.mkdir(); _, checksum = capture(root)
            (root / 'rgb/000000.png').write_bytes(b'corrupt')
            out = Path(d) / 'one.jsonl'
            with self.assertRaises(ValueError): prepare(root, out, checksum)
            self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
