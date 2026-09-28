"""Offline synthetic geometry only; no measured reference or robot execution."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from scripts.box_handling import scenario1_deposit as deposit


ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / 'vendor/ubtech/cruzr_s2/snapshot_20260916/motion'


def pending():
    return json.loads((ROOT / 'config/box_handling/scenario1_put1.json').read_text())


def complete():
    # Deliberately synthetic values, not a calibration or recommendation.
    profile = pending()
    profile.update(calibration_mode='measured_hand_reference',
                   reference_box_bottom_above_floor_m=0.90,
                   reference_left_hand_motion_z_m=0.84,
                   reference_right_hand_motion_z_m=0.85,
                   horizontal_alignment_verified=True,
                   release_clearance_verified=True,
                   evidence='synthetic unit-test fixture; not physical evidence')
    return profile


def complete_vendor():
    # A fictitious reviewed endpoint, not a measured robot reference.
    profile = pending()
    profile.update(reference_vendor_box_bottom_above_floor_m=.62,
                   reference_vendor_position_reached_verified=True,
                   horizontal_alignment_verified=True,
                   release_clearance_verified=True,
                   evidence='synthetic reached WRC endpoint with box held; no robot')
    return profile


def sources():
    return ((SNAPSHOT / 'tasks/wrc_cruzr/put_cruzr_wrc_low.xml').read_text(),
            (SNAPSHOT / 'meta_clamp/wrc/put_cruzr_wrc_low.yaml').read_text(),
            (SNAPSHOT / 'meta_clamp/wrc/open_arm_cruzr.yaml').read_text())


class DepositProfileTests(unittest.TestCase):
    def test_shipped_profile_has_no_calibration(self):
        profile = pending()
        self.assertEqual(profile['surface_height_m'], .74)
        self.assertEqual(profile['surface_pitch_deg'], 0)
        self.assertEqual(profile['calibration_mode'], 'vendor_final_reference')
        report = deposit.review(profile)
        self.assertFalse(report['ready'])
        self.assertIsNone(report['targets'])
        self.assertEqual(set(report['missing']), {
            'reference_vendor_box_bottom_above_floor_m',
            'reference_vendor_position_reached_verified', 'horizontal_alignment_verified',
            'release_clearance_verified', 'evidence'})
        self.assertEqual(report['physical_validation'], 'pending')

    def test_pending_never_builds_executable(self):
        with self.assertRaises(deposit.DepositGeometryPending) as caught:
            deposit.build_bundle(pending(), *sources())
        self.assertIn('reference_vendor_box_bottom_above_floor_m', caught.exception.missing)

    def test_each_required_record_independently_blocks(self):
        for name in deposit._REFERENCES + deposit._VERIFICATIONS + ('evidence',):
            with self.subTest(name=name):
                profile = complete()
                profile[name] = False if name in deposit._VERIFICATIONS else None
                report = deposit.review(profile)
                self.assertEqual(report['missing'], [name])
                with self.assertRaises(deposit.DepositGeometryPending):
                    deposit.build_bundle(profile, *sources())

    def test_validation_returns_detached_data(self):
        profile = complete()
        normalized = deposit.validate_profile(profile)
        normalized['box_size_m'][0] = 999
        self.assertEqual(profile['box_size_m'][0], .603)
        report = deposit.review(profile)
        report['config']['box_size_m'][0] = 999
        self.assertEqual(profile['box_size_m'][0], .603)

    def test_nominal_targets_use_explicit_asymmetric_measured_references(self):
        report = deposit.review(complete())
        self.assertTrue(report['ready'])
        self.assertEqual(report['targets'], {
            'left_hand': {'contact_z_m': .68, 'approach_z_m': .88},
            'right_hand': {'contact_z_m': .69, 'approach_z_m': .89}})
        self.assertEqual(report['physical_validation'], 'pending')

    def test_nonfinite_wrong_types_and_unknown_fields_rejected(self):
        for key in ('surface_height_m', 'surface_pitch_deg') + deposit._REFERENCES:
            for value in (float('nan'), float('inf'), float('-inf'), True, '0.74', 10**1000):
                with self.subTest(key=key, value=repr(value)[:30]):
                    profile = complete()
                    profile[key] = value
                    with self.assertRaises(ValueError):
                        deposit.review(profile)
        profile = complete()
        profile['height_override'] = .74
        with self.assertRaises(ValueError):
            deposit.review(profile)
        del profile['height_override']
        del profile['evidence']
        with self.assertRaises(ValueError):
            deposit.review(profile)

    def test_non_horizontal_wrong_box_and_bad_metadata_rejected(self):
        cases = [('surface_pitch_deg', .001), ('surface_pitch_deg', -10),
                 ('surface_height_m', 0), ('surface_height_m', -1),
                 ('reference_box_bottom_above_floor_m', 0),
                 ('reference_box_bottom_above_floor_m', -1),
                 ('box_size_m', [.6, .4, .28]), ('box_size_m', [.603, .397]),
                 ('box_size_m', [.603, .397, float('nan')]),
                 ('version', True), ('version', 2), ('id', '../escape'),
                 ('evidence', ''), ('evidence', {}),
                 ('release_clearance_verified', 1), ('horizontal_alignment_verified', 'true')]
        for key, value in cases:
            with self.subTest(key=key, value=value):
                profile = complete()
                profile[key] = value
                with self.assertRaises(ValueError):
                    deposit.review(profile)

    def test_finite_inputs_with_nonfinite_derived_target_rejected(self):
        profile = complete()
        profile.update(surface_height_m=1e308, reference_left_hand_motion_z_m=1e308)
        with self.assertRaises(ValueError):
            deposit.review(profile)

    def test_legacy_unmeasured_offset_schema_is_rejected(self):
        profile = complete()
        for name in deposit._REFERENCES:
            del profile[name]
        profile.update(motion_origin_above_floor_m=.14,
                       left_hand_above_box_bottom_m=.08,
                       right_hand_above_box_bottom_m=.09)
        with self.assertRaisesRegex(ValueError, 'missing or unknown fields'):
            deposit.review(profile)

    def test_reference_height_change_compensates_both_measured_hands(self):
        profile = complete()
        first = deposit.review(profile)
        # Another synthetic observation of the same grasp translated vertically.
        profile['reference_box_bottom_above_floor_m'] += .10
        profile['reference_left_hand_motion_z_m'] += .10
        profile['reference_right_hand_motion_z_m'] += .10
        second = deposit.review(profile)
        for hand in ('left_hand', 'right_hand'):
            for coordinate in ('contact_z_m', 'approach_z_m'):
                self.assertAlmostEqual(first['targets'][hand][coordinate],
                                       second['targets'][hand][coordinate], places=14)

    def test_vendor_reference_formula_and_remaining_physical_limit(self):
        report = deposit.review(complete_vendor())
        self.assertTrue(report['ready'])
        self.assertEqual(report['targets'], {
            'left_hand': {'contact_z_m': .57, 'approach_z_m': .77},
            'right_hand': {'contact_z_m': .57, 'approach_z_m': .77}})
        self.assertEqual(report['physical_validation'], 'pending')

    def test_vendor_endpoint_must_be_explicitly_verified_and_cited(self):
        for field, value in ((deposit._VENDOR_VERIFIED, False), ('evidence', None)):
            with self.subTest(field=field):
                profile = complete_vendor()
                profile[field] = value
                report = deposit.review(profile)
                self.assertFalse(report['ready'])
                self.assertIn(field, report['missing'])
                self.assertIsNone(report['targets'])
                with self.assertRaises(deposit.DepositGeometryPending):
                    deposit.build_bundle(profile, *sources())

    def test_vendor_measurement_alone_or_success_text_does_not_qualify(self):
        profile = complete_vendor()
        profile[deposit._VENDOR_VERIFIED] = False
        profile['evidence'] = 'SUCCEED result, no reached endpoint evidence'
        report = deposit.review(profile)
        self.assertFalse(report['ready'])
        self.assertIsNone(report['targets'])

    def test_calibration_modes_are_exclusive(self):
        for profile, field, value in (
                (complete_vendor(), 'reference_left_hand_motion_z_m', .84),
                (complete(), deposit._VENDOR_REFERENCE, .62),
                (complete(), deposit._VENDOR_VERIFIED, True)):
            with self.subTest(field=field):
                profile[field] = value
                with self.assertRaisesRegex(ValueError, 'exclusive'):
                    deposit.review(profile)

    def test_vendor_fields_and_mode_are_strict(self):
        cases = [(deposit._VENDOR_REFERENCE, value) for value in
                 (0, -.1, float('nan'), float('inf'), True, '.62', 10**1000)]
        cases += [(deposit._VENDOR_VERIFIED, value) for value in (1, 'true', None)]
        cases += [('calibration_mode', value) for value in ('auto', None, True)]
        for field, value in cases:
            with self.subTest(field=field, value=repr(value)[:30]):
                profile = complete_vendor()
                profile[field] = value
                with self.assertRaises(ValueError):
                    deposit.review(profile)
        profile = complete_vendor()
        del profile[deposit._VENDOR_VERIFIED]
        with self.assertRaisesRegex(ValueError, 'missing or unknown fields'):
            deposit.review(profile)

    def test_original_measured_reference_schema_still_normalizes(self):
        extended = complete()
        legacy = {name: value for name, value in extended.items()
                  if name in deposit._LEGACY_PROFILE_KEYS}
        self.assertEqual(deposit.validate_profile(legacy), deposit.validate_profile(extended))
        self.assertEqual(deposit.build_bundle(legacy, *sources()),
                         deposit.build_bundle(extended, *sources()))


class DepositBundleTests(unittest.TestCase):
    def test_only_three_yaml_lines_change(self):
        xml, yaml, opening = sources()
        bundle = deposit.build_bundle(complete(), xml, yaml, opening)
        changed = bundle['tasks'][deposit.META_ROOT + bundle['task_name'] + '.yaml']
        before_lines, after_lines = yaml.splitlines(), changed.splitlines()
        self.assertEqual(len(before_lines), len(after_lines))
        differences = [(old, new) for old, new in zip(before_lines, after_lines) if old != new]
        self.assertEqual(differences, [
            ('  box_size: [0.6, 0.4, 0.28]', '  box_size: [0.603, 0.397, 0.22]'),
            ('          position: [0.75, 0.285, 0.65] # x y z',
             '          position: [0.75, 0.285, 0.88] # x y z'),
            ('          position: [0.75, -0.285, 0.65] # x y z',
             '          position: [0.75, -0.285, 0.89] # x y z')])
        # All force/collision windows, torso, XY, rotations, descent and durations
        # remain exact source bytes outside the three whitelisted replacements.
        restored = changed
        for old, new in differences:
            restored = restored.replace(new, old, 1)
        self.assertEqual(restored, yaml)
        self.assertEqual(bundle['dependencies'][deposit.SOURCE_OPEN_PATH],
                         hashlib.sha256(opening.encode()).hexdigest())

    def test_74_to_75_cm_moves_both_targets_and_changes_immutable_id(self):
        profile = complete()
        first = deposit.build_bundle(profile, *sources())
        profile['surface_height_m'] = .75
        second = deposit.build_bundle(profile, *sources())
        self.assertNotEqual(first['manifest']['id'], second['manifest']['id'])
        self.assertNotEqual(first['task_name'], second['task_name'])
        self.assertNotEqual(first['manifest']['config_sha256'], second['manifest']['config_sha256'])
        for hand in ('left_hand', 'right_hand'):
            for coordinate in ('contact_z_m', 'approach_z_m'):
                self.assertAlmostEqual(second['review']['targets'][hand][coordinate] -
                                       first['review']['targets'][hand][coordinate], .01, places=14)

    def test_height_change_alone_does_not_complete_pending_calibration(self):
        profile = pending()
        profile['surface_height_m'] = .75
        report = deposit.review(profile)
        self.assertFalse(report['ready'])
        self.assertIsNone(report['targets'])
        self.assertEqual(report['physical_validation'], 'pending')
        with self.assertRaises(deposit.DepositGeometryPending):
            deposit.build_bundle(profile, *sources())

    def test_vendor_reference_74_to_75_changes_only_hand_z(self):
        profile = complete_vendor()
        first = deposit.build_bundle(profile, *sources())
        profile['surface_height_m'] = .75
        second = deposit.build_bundle(profile, *sources())
        self.assertNotEqual(first['manifest']['id'], second['manifest']['id'])
        first_yaml = next(text for path, text in first['tasks'].items() if path.endswith('.yaml'))
        second_yaml = next(text for path, text in second['tasks'].items() if path.endswith('.yaml'))
        self.assertEqual(second_yaml, first_yaml.replace(', 0.77] # x y z', ', 0.78] # x y z'))
        for side in ('left_hand', 'right_hand'):
            self.assertEqual(second['review']['targets'][side], {'contact_z_m': .58, 'approach_z_m': .78})
        # Pin audit still covers the untouched opening and all original sources.
        self.assertEqual(first['dependencies'], second['dependencies'])

    def test_paths_xml_dependencies_and_hashes(self):
        bundle = deposit.build_bundle(complete(), *sources())
        manifest = bundle['manifest']
        self.assertRegex(manifest['id'], r'^[a-f0-9]{64}$')
        name = 'local_scenario1_deposit/' + manifest['id']
        self.assertEqual(bundle['task_name'], name)
        self.assertEqual(list(bundle['tasks']), [deposit.META_ROOT + name + '.yaml',
                                               deposit.TASK_ROOT + name + '.xml'])
        tree = ET.fromstring(bundle['tasks'][deposit.TASK_ROOT + name + '.xml'])
        self.assertEqual([node.attrib for node in tree.iter('Action')], [
            {'ID': 'MetaClamp', 'name': name},
            {'ID': 'MetaClamp', 'name': 'wrc/open_arm_cruzr'}])
        self.assertEqual(bundle['dependencies'], deposit.SOURCE_HASHES)
        self.assertEqual(manifest['dependencies'], bundle['dependencies'])
        for path, content in bundle['tasks'].items():
            self.assertEqual(manifest['robot_files'][path], hashlib.sha256(content.encode()).hexdigest())
        self.assertEqual(len(manifest['robot_files']), 5)
        self.assertEqual(manifest['physical_validation'], 'pending')

    def test_source_changes_including_controls_or_opening_fail(self):
        original = sources()
        replacements = [(0, original[0] + '\n'),
                        (1, original[1].replace('collision_detect: true', 'collision_detect: false')),
                        (1, original[1].replace('45, 45, 45', '90, 90, 90')),
                        (2, original[2].replace('-0.05', '-0.06'))]
        for index, changed in replacements:
            with self.subTest(index=index):
                inputs = list(original)
                inputs[index] = changed
                with self.assertRaisesRegex(ValueError, 'source hash mismatch'):
                    deposit.build_bundle(complete(), *inputs)

    def test_build_is_deterministic_and_does_not_mutate_profile(self):
        profile = complete()
        before = copy.deepcopy(profile)
        first = deposit.build_bundle(profile, *sources())
        second = deposit.build_bundle(dict(reversed(list(profile.items()))), *sources())
        self.assertEqual(first, second)
        self.assertEqual(profile, before)
        first['dependencies'].clear()
        self.assertEqual(len(deposit.SOURCE_HASHES), 3)
        self.assertEqual(len(first['manifest']['dependencies']), 3)


if __name__ == '__main__':
    unittest.main()
