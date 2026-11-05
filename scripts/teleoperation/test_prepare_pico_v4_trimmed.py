"""Offline checks for v4 motion trim; no ROS or robot access."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.teleoperation import prepare_pico_v4_trimmed as prepare


class PrepareTrimmedTests(unittest.TestCase):
    def fixture(self, directory, mutate=None):
        base = Path(directory)
        motion = {'robot': 'Utars', 'source': 'utars_teleop'}
        for group, names in prepare.ORDER.items():
            times = [0.0, 1.0, 2.0, 4.0] if group == 'head' else [0.0, 0.5, 1.5, 4.0]
            motion[group] = [{'t': x, 'q': [float(i)]*len(names)} for i, x in enumerate(times)]
        if mutate:
            mutate(motion)
        source = base/'normal.motion'
        source.write_text(json.dumps(motion))
        sha = prepare.digest_file(source)
        receipt = base/'result.json'
        receipt.write_text(json.dumps({'output_sha256': sha, 'source_bag_sha256': 'a'*64,
                                       'time_scale': 1.0, 'duration_s': 4.0}))
        return source, receipt, sha, motion

    def test_common_cut_preserves_groups_and_timing(self):
        with tempfile.TemporaryDirectory() as directory:
            source, receipt, sha, old = self.fixture(directory)
            output = Path(directory)/'trimmed.motion'
            result = prepare.trim(source, receipt, output, sha, 'a'*64, 1.0)
            new = json.loads(output.read_text())
            self.assertEqual(new['robot'], 'Utars')
            self.assertEqual(new['source'], 'utars_teleop')
            self.assertEqual(result['duration_s'], 3.0)
            self.assertFalse(result['trajectory_validated'])
            self.assertFalse(result['playback_started'])
            self.assertFalse(result['vendor_interpolation_equivalence_validated'])
            for group in prepare.ORDER:
                prior = [r for r in old[group] if r['t'] <= 1.0][-1]
                later = [r for r in old[group] if r['t'] > 1.0]
                self.assertEqual(new[group][0], {'t': 0.0, 'q': prior['q']})
                self.assertEqual(new[group][1:], [{'t': r['t']-1.0, 'q': r['q']} for r in later])
                self.assertEqual(new[group][-1]['t'], 3.0)
                self.assertEqual(result['groups'][group]['held_sample_original_time_s'], prior['t'])
                self.assertEqual(result['groups'][group]['first_following_delay_s'], later[0]['t']-1.0)
            self.assertEqual(result['groups']['head']['held_sample_age_s'], 0.0)
            self.assertEqual(result['groups']['left_hand']['held_sample_age_s'], 0.5)

    def test_cut_on_and_between_samples_has_no_duplicate_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            source, receipt, sha, _ = self.fixture(directory)
            for cut in (1.0, 1.25):
                output = Path(directory)/('trimmed'+str(cut))
                prepare.trim(source, receipt, output, sha, 'a'*64, cut)
                for group in prepare.ORDER:
                    times = [r['t'] for r in json.loads(output.read_text())[group]]
                    self.assertEqual(times[0], 0.0)
                    self.assertTrue(all(a < b for a, b in zip(times, times[1:])))

    def test_existing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            source, receipt, sha, _ = self.fixture(directory)
            output = Path(directory)/'existing.motion'
            output.write_text('preserve')
            with self.assertRaises(FileExistsError):
                prepare.trim(source, receipt, output, sha, 'a'*64, 1.0)
            self.assertEqual(output.read_text(), 'preserve')

    def test_rejects_source_or_bag_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            source, receipt, sha, _ = self.fixture(directory)
            output = Path(directory)/'trimmed.motion'
            for bad_sha, bad_bag in [('b'*64, 'a'*64), (sha, 'b'*64)]:
                with self.subTest(bad_sha=bad_sha, bad_bag=bad_bag), self.assertRaises(ValueError):
                    prepare.trim(source, receipt, output, bad_sha, bad_bag, 1.0)
                self.assertFalse(output.exists())

    def test_rejects_invalid_cut(self):
        with tempfile.TemporaryDirectory() as directory:
            source, receipt, sha, _ = self.fixture(directory)
            output = Path(directory)/'trimmed.motion'
            for cut in (-1.0, 0.0, 4.0, 4.1, float('nan'), float('inf')):
                with self.subTest(cut=cut), self.assertRaises(ValueError):
                    prepare.trim(source, receipt, output, sha, 'a'*64, cut)
                self.assertFalse(output.exists())

    def test_rejects_invalid_time_or_positions(self):
        for fault in ('duplicate', 'nan', 'dimension', 'end'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as directory:
                def mutate(motion):
                    if fault == 'duplicate': motion['right_hand'][1]['t'] = 0.0
                    elif fault == 'nan': motion['right_hand'][1]['q'][0] = float('nan')
                    elif fault == 'dimension': motion['right_hand'][1]['q'] = [0.0]
                    elif fault == 'end': motion['right_hand'][-1]['t'] = 3.5
                source, receipt, sha, _ = self.fixture(directory, mutate)
                output = Path(directory)/'trimmed.motion'
                with self.assertRaises(ValueError):
                    prepare.trim(source, receipt, output, sha, 'a'*64, 1.0)
                self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
