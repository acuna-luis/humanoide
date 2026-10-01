"""Approach-only artifact contracts; all generated tasks remain offline."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

from scripts.box_handling import scenario1_table74_trial as trial


SNAPSHOT = Path(__file__).resolve().parents[2] / 'vendor/ubtech/cruzr_s2/snapshot_20260916/motion'


def reference():
    return dict(version=1, box_bottom_above_floor_m=1.10, surface_height_m=.74,
                precontact_clearance_m=.05, evidence='synthetic-test-reference',
                scope='current_post_grasp_box_only')


def sources():
    return ((SNAPSHOT / 'tasks/wrc_cruzr/put_cruzr_wrc_low.xml').read_text(),
            (SNAPSHOT / 'meta_clamp/wrc/put_cruzr_wrc_low.yaml').read_text())


def build(ref=None):
    return trial.build_bundle(ref or reference(), *sources())


def task_texts(bundle):
    name = bundle['task_name']
    return bundle['tasks'][trial.TASK_ROOT + name + '.xml'], bundle['tasks'][trial.META_ROOT + name + '.yaml']


class Table74ApproachTrialTests(unittest.TestCase):
    def test_exact_yaml_edit_whitelist_preserves_controls_times_and_torso_approach(self):
        original_xml, original_yaml = sources()
        xml, yaml = task_texts(build())
        changes = [(old, new) for old, new in zip(original_yaml.splitlines(), yaml.splitlines())
                   if old != new]
        self.assertEqual(len(original_yaml.splitlines()), len(yaml.splitlines()))
        self.assertEqual(len(changes), 8)
        self.assertEqual(sum('Z_REL_XYRPY_ABSOLUTE' in new for _, new in changes), 2)
        self.assertEqual(sum('position: [0.75,' in new and ', -0.31]' in new for _, new in changes), 2)
        self.assertEqual(sum('position: [0.0, 0.0, 0.0]' in new for _, new in changes), 3)
        self.assertEqual(sum('box_size' in new for _, new in changes), 1)
        restored = yaml
        # Restore entire first-point blocks to avoid replacing torso ABSOLUTE modes.
        for y in ('0.285', '-0.285'):
            restored = restored.replace(
                'position: [0.75, ' + y + ', -0.31] # x y z\n'
                '          orientation: [0.5, 0.5, 0.5, -0.5] # w x y z\n'
                '          tranform_mode: "Z_REL_XYRPY_ABSOLUTE"',
                'position: [0.75, ' + y + ', 0.65] # x y z\n'
                '          orientation: [0.5, 0.5, 0.5, -0.5] # w x y z\n'
                '          tranform_mode: "ABSOLUTE"')
        restored = restored.replace('position: [0.0, 0.0, 0.0]', 'position: [0.0, 0.0, -0.20]').replace(
            'box_size: [0.603, 0.397, 0.22]', 'box_size: [0.6, 0.4, 0.28]')
        self.assertEqual(restored, original_yaml)
        self.assertIn('collision_detect: true', yaml)
        self.assertEqual(yaml.count('time: [10.0, 10.0, 12.0]'), 2)

    def test_single_xml_action_and_no_final_descent_opening_or_relative_rotation(self):
        bundle = build()
        xml, yaml = task_texts(bundle)
        self.assertEqual([node.attrib for node in ET.fromstring(xml).iter('Action')],
                         [{'ID': 'MetaClamp', 'name': bundle['task_name']}])
        self.assertNotIn('open_arm', xml)
        self.assertNotIn('home', xml)
        trajectories = yaml.split('  robot_trajectory_data:', 1)[1].split('  admit_param:', 1)[0]
        positions = [ast.literal_eval(value) for value in re.findall(
            r'^          position: (\[[^\n]*?\])', trajectories, re.M)]
        self.assertEqual(positions, [[.75, .285, -.31], [.2, 0, 0], [0, 0, 0],
                                    [.75, -.285, -.31], [.2, 0, 0], [0, 0, 0],
                                    [0, 0, 1.2], [.30, 0, 1.2], [0, 0, 0]])
        for orientation, mode in re.findall(
                r'orientation: (\[[^\n]*\]).*?\n\s+tranform_mode: "([A-Z_]+)"', trajectories):
            if mode == 'RELATIVE':
                self.assertEqual(ast.literal_eval(orientation), [1, 0, 0, 0])
        self.assertEqual(re.findall(r'timestamp: ([0-9.]+)', trajectories),
                         ['6.0', '10.0', '12.0'] * 3)

    def test_manifest_pins_both_sources_native_mode_library_and_generated_bytes(self):
        bundle = build()
        manifest = bundle['manifest']
        identity = manifest['id']
        self.assertRegex(identity, r'^[0-9a-f]{64}$')
        self.assertEqual(bundle['task_name'], trial.NAMESPACE + identity + '_approach')
        self.assertEqual(bundle['dependencies'], trial.DEPENDENCIES)
        self.assertEqual(manifest['dependencies'][trial.META_CLAMP_PATH], trial.BINARY_SHA)
        self.assertEqual(set(manifest['robot_files']), set(trial.DEPENDENCIES) | set(bundle['tasks']))
        for path, text in bundle['tasks'].items():
            self.assertEqual(manifest['robot_files'][path], hashlib.sha256(text.encode()).hexdigest())
        self.assertEqual(trial.validate_bundle(bundle), bundle)

    def test_height_difference_is_relative_and_review_does_not_claim_execution_or_calibration(self):
        bundle = build()
        report = bundle['review']
        self.assertEqual(report['first_hand_delta_z_m'], -.31)
        self.assertEqual(report['nominal_target_box_bottom_above_floor_m'], .79)
        self.assertIsNone(report['absolute_hand_motion_z_m'])
        self.assertFalse(report['absolute_hand_z_calibration_created'])
        self.assertTrue(report['operator_box_height_is_approximate'])
        self.assertIsNone(report['bounded_height_uncertainty_m'])
        self.assertEqual(report['physical_validation'], 'pending')
        self.assertFalse(report['automatic_execution_authorized'])
        self.assertFalse(report['installed'])
        self.assertFalse(report['integrated_in_optimistic'])
        self.assertIn('final_5cm_lowering', report['excluded_phases'])
        self.assertIn('pin_release_3cm', report['excluded_phases'])
        self.assertTrue(report['assumptions_not_verified'])
        self.assertIn('not an autorun', ' '.join(report['limitations']))

    def test_every_source_byte_is_pinned(self):
        xml, yaml = sources()
        for changed in ((xml + '\n', yaml), (xml, yaml + '\n'),
                        (xml, yaml.replace('collision_detect: true', 'collision_detect: false'))):
            with self.subTest(source=changed[0][-10:]), self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                trial.build_bundle(reference(), *changed)

    def test_nonfinite_nonpositive_and_wrong_scope_inputs_are_rejected(self):
        for key in ('box_bottom_above_floor_m', 'surface_height_m', 'precontact_clearance_m'):
            for value in (float('nan'), float('inf'), float('-inf'), 0, -.1, True, '1.10', 10**1000):
                ref = reference()
                ref[key] = value
                with self.subTest(key=key, value=str(value)[:24]), self.assertRaises(ValueError):
                    build(ref)
        for key, value in (('surface_height_m', .75), ('precontact_clearance_m', .20),
                           ('version', True), ('scope', 'all_future_cycles'), ('evidence', ''),
                           ('evidence', None)):
            ref = reference()
            ref[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                build(ref)
        ref = reference()
        ref['calibration_verified'] = True
        with self.assertRaises(ValueError):
            build(ref)

    def test_height_pin_is_trial_scope_not_an_invented_physical_reach_envelope(self):
        # Another otherwise finite height requires review, not extrapolation
        # from the sole operator measurement associated with this trial.
        for height in (.10, .79, 1.11, 1.20, 1.50):
            ref = reference()
            ref['box_bottom_above_floor_m'] = height
            with self.subTest(height=height), self.assertRaisesRegex(ValueError, 'requires a new review'):
                build(ref)
        bundle = build()
        self.assertFalse(bundle['review']['automatic_execution_authorized'])
        self.assertEqual(bundle['review']['physical_validation'], 'pending')
        self.assertEqual(trial.validate_bundle(bundle), bundle)

    def test_reference_provenance_and_generated_content_are_immutable_and_independent(self):
        ref = reference()
        original = copy.deepcopy(ref)
        first = build(ref)
        self.assertEqual(build(dict(reversed(list(ref.items())))), first)
        modified = dict(ref, evidence='other-measurement')
        self.assertNotEqual(build(modified)['task_name'], first['task_name'])
        verified = trial.validate_bundle(first)
        verified['review']['reference']['evidence'] = 'changed'
        verified['dependencies'].clear()
        self.assertEqual(first['review']['reference']['evidence'], original['evidence'])
        self.assertEqual(first['dependencies'], trial.DEPENDENCIES)
        self.assertEqual(ref, original)

    def test_rehashed_additional_motion_and_false_validation_claims_are_rejected(self):
        original = build()
        yaml_path = trial.META_ROOT + original['task_name'] + '.yaml'
        xml_path = trial.TASK_ROOT + original['task_name'] + '.xml'
        variants = []
        for old, new in (('collision_detect: true', 'collision_detect: false'),
                         ('position: [0.0, 0.0, 0.0]', 'position: [0.0, 0.0, -0.05]'),
                         ('position: [0.75, 0.285, -0.31]', 'position: [0.90, 0.285, -0.31]'),
                         ('Z_REL_XYRPY_ABSOLUTE', 'RELATIVE')):
            changed = copy.deepcopy(original)
            changed['tasks'][yaml_path] = changed['tasks'][yaml_path].replace(old, new, 1)
            changed['manifest']['robot_files'][yaml_path] = trial.sha256(changed['tasks'][yaml_path])
            variants.append(changed)
        changed = copy.deepcopy(original)
        changed['tasks'][xml_path] = changed['tasks'][xml_path].replace('</Sequence>',
            '<Action ID="MetaClamp" name="wrc/open_arm_cruzr" /></Sequence>')
        changed['manifest']['robot_files'][xml_path] = trial.sha256(changed['tasks'][xml_path])
        variants.append(changed)
        for field, value in (('automatic_execution_authorized', True), ('physical_validation', 'verified')):
            changed = copy.deepcopy(original)
            changed['review'][field] = value
            variants.append(changed)
        changed = copy.deepcopy(original)
        changed['dependencies'][trial.META_CLAMP_PATH] = '0' * 64
        variants.append(changed)
        for index, changed in enumerate(variants):
            with self.subTest(index=index), self.assertRaises(ValueError):
                trial.validate_bundle(changed)

    def test_validator_runs_in_memory_without_filesystem_or_module_file(self):
        namespace = {'__name__': 'table74_trial_in_memory', '__package__': 'scripts.box_handling'}
        exec(compile(Path(trial.__file__).read_text(), 'table74_trial_in_memory', 'exec'), namespace)
        self.assertNotIn('__file__', namespace)
        self.assertEqual(namespace['validate_bundle'](build()), build())


if __name__ == '__main__':
    unittest.main()
