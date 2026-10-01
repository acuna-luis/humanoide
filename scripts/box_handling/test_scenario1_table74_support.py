"""Pinned support-only geometry and provenance, entirely offline."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

from scripts.box_handling import scenario1_table74_support as support


SNAPSHOT = Path(__file__).resolve().parents[2] / 'vendor/ubtech/cruzr_s2/snapshot_20260916/motion'


def reference():
    return dict(version=1, gap_above_surface_m=.05, surface_height_m=.74,
                predecessor_bundle_id=support.PINNED_APPROACH_BUNDLE_ID,
                predecessor_goal_id=support.PINNED_APPROACH_GOAL_ID,
                evidence='synthetic operator-gap evidence for tests only',
                scope='current_post_approach_box_only')


def sources():
    return ((SNAPSHOT / 'tasks/wrc_cruzr/put_cruzr_wrc_low.xml').read_text(),
            (SNAPSHOT / 'meta_clamp/wrc/put_cruzr_wrc_low.yaml').read_text())


def build(ref=None):
    return support.build_bundle(reference() if ref is None else ref, *sources())


def texts(bundle):
    name = bundle['task_name']
    return bundle['tasks'][support.TASK_ROOT + name + '.xml'], bundle['tasks'][support.META_ROOT + name + '.yaml']


class SupportOnlyTests(unittest.TestCase):
    def test_all_controls_and_original_bytes_outside_trajectory_and_box_size_are_preserved(self):
        _, original = sources()
        _, yaml = texts(build())
        start, end = '  robot_trajectory_data:\n', '  admit_param:\n'
        old_prefix, old_rest = original.split(start)
        old_trajectory, old_suffix = old_rest.split(end)
        new_prefix, new_rest = yaml.split(start)
        new_trajectory, new_suffix = new_rest.split(end)
        self.assertEqual(new_prefix.replace('box_size: [0.603, 0.397, 0.22]',
                                           'box_size: [0.6, 0.4, 0.28]'), old_prefix)
        self.assertEqual(new_suffix, old_suffix)
        self.assertEqual(len(yaml.splitlines()), len(original.splitlines()))
        changes = [(a, b) for a, b in zip(original.splitlines(), yaml.splitlines()) if a != b]
        self.assertEqual(len(changes), 16)
        self.assertIn('  duration: 12.0\n', yaml)
        self.assertIn('  collision_detect: true\n', yaml)
        self.assertEqual(yaml.count('time: [10.0, 10.0, 12.0]'), 2)
        self.assertEqual(yaml.count('collision_force: [0.0, 0.0, 10.0, 0.0, 0.0, 0.0]'), 2)
        self.assertIn('torso: [0.0, 0.0, 0.0, 1.0, 1.0, 1.0]', yaml)

    def test_only_final_two_hand_points_request_five_cm_down_without_rotation_or_xy_motion(self):
        xml, yaml = texts(build())
        section = yaml.split('  robot_trajectory_data:\n')[1].split('  admit_param:\n')[0]
        positions = [ast.literal_eval(x) for x in re.findall(r'^          position: (\[[^\n]*?\])', section, re.M)]
        self.assertEqual(positions, [[0, 0, 0], [0, 0, 0], [0, 0, -.05],
                                    [0, 0, 0], [0, 0, 0], [0, 0, -.05],
                                    [0, 0, 0], [0, 0, 0], [0, 0, 0]])
        self.assertEqual(re.findall(r'timestamp: ([0-9.]+)', section), ['6.0', '10.0', '12.0'] * 3)
        rotations = re.findall(r'orientation: (\[[^\n]*?\])', section)
        self.assertEqual(len(rotations), 9)
        self.assertTrue(all(ast.literal_eval(x) == [1, 0, 0, 0] for x in rotations))
        self.assertEqual(re.findall(r'tranform_mode: "([A-Z_]+)"', section), ['RELATIVE'] * 9)
        self.assertNotIn('ABSOLUTE', section)
        self.assertNotIn('-0.03', section)
        self.assertNotIn('-0.31', section)

    def test_xml_has_one_meta_clamp_and_no_opening_home_navigation_or_second_action(self):
        bundle = build()
        xml, _ = texts(bundle)
        self.assertEqual([(x.tag, x.attrib) for x in ET.fromstring(xml).iter()],
            [('root', {'main_tree_to_execute': 'MainTree'}),
             ('BehaviorTree', {'ID': 'MainTree'}), ('Sequence', {'name': 'root_sequence'}),
             ('Action', {'ID': 'MetaClamp', 'name': bundle['task_name']})])
        for name in ('open_arm', 'home', 'navigate', 'approach'):
            self.assertNotIn(name, xml)

    def test_reference_requires_exact_current_gap_table_and_predecessor(self):
        for key in ('gap_above_surface_m', 'surface_height_m'):
            for value in (float('nan'), float('inf'), float('-inf'), 0, -.05, True, '.05', 10**1000):
                changed = reference(); changed[key] = value
                with self.subTest(key=key, value=str(value)[:24]), self.assertRaises(ValueError):
                    build(changed)
        for key, value in (('gap_above_surface_m', .03), ('gap_above_surface_m', .07),
                           ('surface_height_m', 1.0), ('predecessor_bundle_id', '0'*64),
                           ('predecessor_goal_id', '11111111-1111-4111-8111-111111111111'),
                           ('version', True), ('scope', 'any_successful_approach'),
                           ('evidence', ''), ('evidence', None)):
            changed = reference(); changed[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                build(changed)
        for changed in ({}, dict(reference(), physical_validation=True)):
            with self.assertRaises(ValueError):
                build(changed)

    def test_every_source_byte_is_pinned(self):
        xml, yaml = sources()
        for a, b in ((xml+'\n', yaml), (xml, yaml+'\n'),
                     (xml, yaml.replace('collision_detect: true', 'collision_detect: false'))):
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                support.build_bundle(reference(), a, b)

    def test_manifest_binds_predecessor_provenance_native_library_and_exact_content(self):
        bundle = build()
        manifest = bundle['manifest']
        self.assertEqual(manifest['phase'], 'support_only')
        self.assertEqual(bundle['task_name'], support.NAMESPACE+manifest['id']+'_support')
        self.assertEqual(manifest['dependencies'], support.DEPENDENCIES)
        self.assertEqual(manifest['dependencies'][support.META_CLAMP_PATH], support.BINARY_SHA)
        self.assertEqual(manifest['reference_sha256'], support.sha256(support.canonical(reference())))
        self.assertEqual(set(manifest['robot_files']), set(support.DEPENDENCIES) | set(bundle['tasks']))
        for path, value in bundle['tasks'].items():
            self.assertEqual(manifest['robot_files'][path], hashlib.sha256(value.encode()).hexdigest())
        self.assertEqual(support.validate_bundle(bundle), bundle)
        self.assertNotEqual(build(dict(reference(), evidence='other provenance'))['task_name'], bundle['task_name'])

    def test_no_support_pin_clearance_or_autorun_claim_is_created(self):
        review = build()['review']
        for name in ('automatic_execution_authorized', 'installed', 'integrated_in_optimistic',
                     'absolute_hand_z_calibration_created', 'support_confirmed', 'pin_disengagement_confirmed'):
            self.assertIs(review[name], False)
        self.assertEqual(review['physical_validation'], 'pending')
        self.assertTrue(review['operator_gap_is_approximate'])
        self.assertIsNone(review['bounded_gap_uncertainty_m'])
        self.assertIsNone(review['absolute_hand_motion_z_m'])
        self.assertEqual(review['final_hand_delta_z_m'], -.05)
        self.assertEqual(review['contact_window_s'], [10, 12])
        self.assertIn('pin_release_3cm', review['excluded_phases'])
        self.assertIn('opening', review['excluded_phases'])
        limitations = ' '.join(review['limitations'])
        for text in ('not an autorun', 'do not lock', 'does not prove', 'interpolation is not certified', 'another 5 cm'):
            self.assertIn(text, limitations)

    def test_rehashed_trajectory_control_xml_and_review_tampering_is_rejected(self):
        original = build()
        yaml_path = support.META_ROOT+original['task_name']+'.yaml'
        xml_path = support.TASK_ROOT+original['task_name']+'.xml'
        variants = []
        for old, new in (('collision_detect: true', 'collision_detect: false'),
                         ('time: [10.0, 10.0, 12.0]', 'time: [6.0, 6.0, 12.0]'),
                         ('position: [0.0, 0.0, -0.05]', 'position: [0.0, 0.0, -0.08]'),
                         ('position: [0.0, 0.0, 0.0]', 'position: [0.20, 0.0, 0.0]'),
                         ('orientation: [1.0, 0.0, 0.0, 0.0]', 'orientation: [0.5, 0.5, 0.5, -0.5]'),
                         ('tranform_mode: "RELATIVE"', 'tranform_mode: "ABSOLUTE"')):
            changed = copy.deepcopy(original)
            changed['tasks'][yaml_path] = changed['tasks'][yaml_path].replace(old, new, 1)
            changed['manifest']['robot_files'][yaml_path] = support.sha256(changed['tasks'][yaml_path])
            variants.append(changed)
        changed = copy.deepcopy(original)
        changed['tasks'][xml_path] = changed['tasks'][xml_path].replace('</Sequence>',
            '<Action ID="MetaClamp" name="wrc/open_arm_cruzr" /></Sequence>')
        changed['manifest']['robot_files'][xml_path] = support.sha256(changed['tasks'][xml_path])
        variants.append(changed)
        for field, value in (('physical_validation', 'verified'), ('support_confirmed', True),
                             ('pin_disengagement_confirmed', True), ('automatic_execution_authorized', True)):
            changed = copy.deepcopy(original); changed['review'][field] = value; variants.append(changed)
        changed = copy.deepcopy(original); changed['dependencies'][support.META_CLAMP_PATH] = '0'*64; variants.append(changed)
        for index, changed in enumerate(variants):
            with self.subTest(index=index), self.assertRaises(ValueError):
                support.validate_bundle(changed)

    def test_in_memory_validation_is_pure_and_returns_an_independent_copy(self):
        namespace = {'__name__': 'support_in_memory', '__package__': 'scripts.box_handling'}
        exec(compile(Path(support.__file__).read_text(), 'support_in_memory', 'exec'), namespace)
        self.assertNotIn('__file__', namespace)
        original = build()
        checked = namespace['validate_bundle'](original)
        self.assertEqual(checked, original)
        checked['review']['reference']['evidence'] = 'edited'
        checked['dependencies'].clear()
        self.assertEqual(original, build())

    def test_cli_only_prepares_new_local_artifacts_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ref, output = root/'reference.json', root/'output'
            ref.write_text(json.dumps(reference()))
            args = [sys.executable, '-B', support.__file__, '--reference', str(ref), '--output', str(output)]
            result = subprocess.run(args, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('NO_INSTALLATION_NO_AUTORUN', result.stdout)
            bundle = json.loads((output/'bundle.json').read_text())
            self.assertEqual(support.validate_bundle(bundle), build())
            before = {p.name: p.read_bytes() for p in output.iterdir()}
            self.assertEqual(len(before), 4)
            repeated = subprocess.run(args, capture_output=True, text=True, timeout=10)
            self.assertNotEqual(repeated.returncode, 0)
            self.assertEqual({p.name: p.read_bytes() for p in output.iterdir()}, before)


if __name__ == '__main__':
    unittest.main()
