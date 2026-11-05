"""Offline tests for the non-moving normal-speed derivative."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.teleoperation import prepare_pico_v4_normal_speed as prepare


class PrepareNormalTests(unittest.TestCase):
    def fixture(self, directory, mutate=None):
        base = Path(directory)
        original = {'robot': 'Utars', 'source': 'utars_teleop'}
        groups = {}
        for group, names in prepare.ORDER.items():
            q0, q1 = [0.0]*len(names), [0.25]*len(names)
            original[group] = [{'t': 0.0, 'q': q0}, {'t': 4.0, 'q': q1}]
            groups[group] = {'names': names, 'samples': 2, 'initial_q': q0, 'final_q': q1}
        if mutate:
            mutate(original, groups)
        source = base/'slow.motion'
        source.write_text(json.dumps(original))
        slow_sha = hashlib.sha256(source.read_bytes()).hexdigest()
        receipt = base/'conversion.json'
        receipt.write_text(json.dumps({'source_sha256': 'a'*64, 'output_sha256': slow_sha,
                                       'time_scale': 2, 'duration_s': 4.0, 'groups': groups}))
        return source, receipt, slow_sha, original

    def test_time_is_halved_without_changing_positions_and_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            slow, receipt, sha, original = self.fixture(directory)
            output = Path(directory)/'normal.motion'
            result = prepare.convert(slow, receipt, output, sha, 'a'*64)
            motion = json.loads(output.read_text())
            self.assertEqual(result['duration_s'], 2.0)
            self.assertEqual(result['time_scale'], 1.0)
            self.assertFalse(result['playback_started'])
            for group in prepare.ORDER:
                self.assertEqual([row['t'] for row in motion[group]], [0.0, 2.0])
                self.assertEqual([row['q'] for row in motion[group]],
                                 [row['q'] for row in original[group]])
            prior = output.read_bytes()
            with self.assertRaises(FileExistsError):
                prepare.convert(slow, receipt, output, sha, 'a'*64)
            self.assertEqual(output.read_bytes(), prior)

    def test_source_mismatch_never_writes_output(self):
        with tempfile.TemporaryDirectory() as directory:
            slow, receipt, sha, _ = self.fixture(directory)
            output = Path(directory)/'normal.motion'
            for slow_sha, bag_sha in [('b'*64, 'a'*64), (sha, 'b'*64)]:
                with self.subTest(slow_sha=slow_sha, bag_sha=bag_sha), self.assertRaises(ValueError):
                    prepare.convert(slow, receipt, output, slow_sha, bag_sha)
                self.assertFalse(output.exists())

    def test_non_increasing_time_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            def mutate(motion, _groups):
                motion['right_hand'][1]['t'] = 0.0
            slow, receipt, sha, _ = self.fixture(directory, mutate)
            output = Path(directory)/'normal.motion'
            with self.assertRaises(ValueError):
                prepare.convert(slow, receipt, output, sha, 'a'*64)
            self.assertFalse(output.exists())

    def test_non_finite_position_and_wrong_joint_count_are_rejected(self):
        for invalid in (float('nan'), [0.0]):
            with self.subTest(invalid=invalid), tempfile.TemporaryDirectory() as directory:
                def mutate(motion, _groups):
                    if isinstance(invalid, list):
                        motion['right_hand'][1]['q'] = invalid
                    else:
                        motion['right_hand'][1]['q'][0] = invalid
                slow, receipt, sha, _ = self.fixture(directory, mutate)
                with self.assertRaises(ValueError):
                    prepare.convert(slow, receipt, Path(directory)/'normal.motion', sha, 'a'*64)


if __name__ == '__main__':
    unittest.main()
