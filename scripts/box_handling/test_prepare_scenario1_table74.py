"""Offline candidate review; all reference measurements below are synthetic."""
import copy
import json
import ast
import re
import unittest

from scripts.box_handling import prepare_scenario1_table74 as candidate
from scripts.box_handling.test_scenario1_deposit import pending, complete, sources


class Table74CandidateTests(unittest.TestCase):
    def test_missing_reference_remains_unrendered_and_uninstallable(self):
        files = candidate.prepare(pending(), *sources())
        self.assertIn('put_table74.yaml.in', files)
        self.assertNotIn('put_table74.candidate.yaml', files)
        self.assertFalse(any(name.endswith('.xml') for name in files))
        self.assertIn('${LEFT_HAND_APPROACH_Z_M}', files['put_table74.yaml.in'])
        self.assertIn('${RIGHT_HAND_APPROACH_Z_M}', files['put_table74.yaml.in'])
        review = json.loads(files['review.json'])
        self.assertFalse(review['can_install'])
        self.assertFalse(review['integrated_in_optimistic'])
        self.assertEqual(review['opening']['status'], 'operator_proposed_unverified')
        self.assertIsNone(review['release_review']['required_relative_hand_drop_after_support_m'])
        self.assertEqual(review['release_review']['proposed_relative_hand_drop_after_support_m'], .03)
        self.assertEqual(review['release_review']['operator_max_drop_after_support_m'], .03)
        self.assertEqual(review['nominal_hand_drop_from_precontact_through_release_m'], .08)
        self.assertEqual(review['hand_formula']['after_release_z_m'], 'contact_z_m - 0.03')
        self.assertNotIn('open_horizontal.candidate.yaml', files)
        self.assertIsNone(review['geometry_review']['targets'])
        self.assertEqual(review['nominal_box_on_table_floor_m'],
                         dict(bottom=.74, center=.85, top=.96))

    def test_opening_separates_three_cm_relief_from_lateral_release_preserving_controls(self):
        files = candidate.prepare(pending(), *sources())
        original = sources()[2]
        changed = files['release_under_rim.candidate.yaml'].split('\n', 1)[1]
        header = changed.split('  robot_trajectory_data:', 1)[0]
        self.assertEqual(header.replace('duration: 4.0', 'duration: 2.0').replace(
            'box_size: [0.603, 0.397, 0.22]', 'box_size: [0.6, 0.4, 0.28]'),
            original.split('  robot_trajectory_data:', 1)[0])
        positions = [ast.literal_eval(v) for v in re.findall(r'^          position: (\[[^\n]*?\])', changed, re.M)]
        self.assertEqual(positions, [[0, 0, -.03], [0, .1, 0],
                                    [0, 0, -.03], [0, -.1, 0], [0, 0, 0]])
        self.assertEqual(re.findall(r'timestamp: ([0-9.]+)', changed), ['2.0', '4.0', '2.0', '4.0', '4.0'])
        self.assertEqual(changed.count('tranform_mode: "RELATIVE"'), 5)
        self.assertIn('position: [0, 0.1, 0.0]', changed)
        self.assertIn('position: [0, -0.1, 0.0]', changed)
        self.assertEqual(changed.count('          orientation: [1.0, 0.0, 0.0, 0.0]'), 5)

    def test_final_descent_is_five_cm_and_all_other_contact_force_torso_bytes_preserved(self):
        xml, original, opening = sources()
        changed = candidate.prepare(pending(), xml, original, opening)['put_table74.yaml.in'].split('\n', 1)[1]
        restored = changed.replace('${LEFT_HAND_APPROACH_Z_M}', '0.65').replace(
            '${RIGHT_HAND_APPROACH_Z_M}', '0.65').replace(
            'box_size: [0.603, 0.397, 0.22]', 'box_size: [0.6, 0.4, 0.28]').replace(
            'position: [0.0, 0.0, -0.05]', 'position: [0.0, 0.0, -0.20]')
        self.assertEqual(restored, original)
        self.assertEqual(changed.count('position: [0.0, 0.0, -0.05]'), 3)

    def test_complete_synthetic_reference_uses_both_hand_offsets_not_box_center(self):
        profile = complete()
        before = copy.deepcopy(profile)
        files = candidate.prepare(profile, *sources())
        self.assertIn('put_table74.candidate.yaml', files)
        self.assertNotIn('${', files['put_table74.candidate.yaml'])
        self.assertIn('position: [0.75, 0.285, 0.73]', files['put_table74.candidate.yaml'])
        self.assertIn('position: [0.75, -0.285, 0.74]', files['put_table74.candidate.yaml'])
        review = json.loads(files['review.json'])
        for hand in ('left_hand', 'right_hand'):
            target = review['geometry_review']['targets'][hand]
            self.assertAlmostEqual(target['approach_z_m']-.05, target['contact_z_m'])
        self.assertEqual(review['opening']['separation']['left_delta_m'][2], 0)
        self.assertEqual(review['opening']['separation']['right_delta_m'][2], 0)
        self.assertEqual(review['opening']['lowering']['both_hand_delta_m'][2], -.03)
        self.assertFalse(json.loads(files['review.json'])['can_install'])
        self.assertEqual(profile, before)

    def test_wrong_height_nonhorizontal_and_changed_sources_rejected(self):
        for key, value in [('surface_height_m', .75), ('surface_pitch_deg', 1.0)]:
            profile = pending()
            profile[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                candidate.prepare(profile, *sources())
        for index in range(3):
            changed = list(sources())
            changed[index] += '\n'
            with self.subTest(source=index), self.assertRaises(ValueError):
                candidate.prepare(pending(), *changed)


if __name__ == '__main__':
    unittest.main()
