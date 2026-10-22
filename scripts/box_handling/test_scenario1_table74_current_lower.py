"""Pinned lowering phases: no ROS, network, native loads or execution."""
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from scripts.box_handling import scenario1_deposit
from scripts.box_handling import scenario1_table74_current_lower as lower
from scripts.box_handling import scenario1_table74_support as legacy
from scripts.box_handling.test_scenario1_table74_current_trial import sources


def reference(stage='precontact'):
    gap, target = {'precontact': (.19, .05), 'support': (.05, 0.), 'settle': (.01, 0.)}[stage]
    return dict(version=1, stage=stage, gap_above_surface_m=gap, target_clearance_m=target,
        surface_height_m=.74, predecessor_bundle_id='a'*64,
        predecessor_goal_id='80974a9d-f9b2-4322-a2d7-2db41f28766e',
        evidence='Current operator report: both sides horizontal, stable, over board, no contact.',
        scope='current_post_trial_box_only')


def bundle(stage='precontact'):
    return lower.build_bundle(reference(stage), *sources())


class CurrentRelativeLoweringTests(unittest.TestCase):
    def test_both_exact_pairs_delta_and_no_support_claim(self):
        for stage, delta, target in (('precontact', -.14, .05), ('support', -.05, 0.), ('settle', -.01, 0.)):
            with self.subTest(stage=stage):
                b = bundle(stage); review = b['review']
                self.assertEqual(lower.validate_bundle(b), b)
                self.assertEqual(review['lower_delta_z_m'], delta)
                self.assertEqual(review['nominal_target_clearance_m'], target)
                self.assertEqual(review['phase'], 'current_relative_lowering')
                self.assertEqual(review['physical_validation'], 'pending')
                for key in ('automatic_execution_authorized', 'installed', 'integrated_in_optimistic',
                            'physical_support_confirmed', 'pin_disengagement_confirmed', 'measured_absolute_calibration_created'):
                    self.assertIs(review[key], False)

    def test_source_and_support_trajectory_match_legacy_without_global_mutation(self):
        old = legacy._trajectory(support=True)
        self.assertEqual(lower._trajectory(lowering=False), legacy._trajectory(support=False))
        self.assertEqual(lower._trajectory(lowering=True, delta_z=-.05), old)
        self.assertEqual(lower._trajectory(lowering=True, delta_z=-.14),
                         old.replace('[0.0, 0.0, -0.05]', '[0.0, 0.0, -0.14]'))
        self.assertEqual(legacy._trajectory(support=True), old)

    def test_only_trajectory_and_xml_opening_change_all_controls_unchanged(self):
        xml, yaml = sources()
        for stage, delta in (('precontact', -.14), ('support', -.05), ('settle', -.01)):
            b = bundle(stage); name = b['task_name']; candidate = b['tasks'][lower.META_ROOT+name+'.yaml']
            expected = yaml.replace(legacy._trajectory(support=False), lower._trajectory(lowering=True, delta_z=delta), 1)
            self.assertEqual(candidate, expected)
            self.assertIn('box_size: [0.6, 0.4, 0.28]', candidate)
            self.assertNotIn('tranform_mode: "ABSOLUTE"', candidate)
            self.assertEqual(candidate.count('tranform_mode: "RELATIVE"'), 9)
            self.assertEqual(candidate.count('orientation: [1.0, 0.0, 0.0, 0.0]'), 9)
            self.assertEqual(candidate.count('position: [0.0, 0.0, '+repr(delta)+']'), 2)
            for section in ('collision_data:', 'admit_param:'):
                self.assertIn(section, candidate)
            actions = ET.fromstring(b['tasks'][lower.TASK_ROOT+name+'.xml']).findall('.//Action')
            self.assertEqual([a.attrib for a in actions], [dict(ID='MetaClamp', name=name)])
            self.assertNotIn('open_arm', b['tasks'][lower.TASK_ROOT+name+'.xml'])

    def test_predecessor_and_stage_are_in_content_identity(self):
        first = bundle(); original = reference()
        for field, value in (('predecessor_bundle_id', 'b'*64),
                            ('predecessor_goal_id', '8a15575b-f746-4405-8a1d-c819b092d01f'),
                            ('evidence', 'Another current confirmed gap report')):
            r = copy.deepcopy(original); r[field] = value
            self.assertNotEqual(lower.build_bundle(r, *sources())['task_name'], first['task_name'])
        self.assertNotEqual(bundle('support')['task_name'], first['task_name'])

    def test_settle_is_distinct_residual_gap_correction_and_keeps_all_other_source_controls(self):
        support = bundle('support'); settle = bundle('settle')
        self.assertNotEqual(support['task_name'], settle['task_name'])
        self.assertEqual(settle['review']['stage'], 'settle')
        self.assertEqual(settle['review']['reference']['gap_above_surface_m'], .01)
        self.assertEqual(settle['review']['lower_delta_z_m'], -.01)
        self.assertIs(settle['review']['physical_support_confirmed'], False)
        self.assertEqual(settle['tasks'][lower.META_ROOT+settle['task_name']+'.yaml'],
            support['tasks'][lower.META_ROOT+support['task_name']+'.yaml'].replace(
                'position: [0.0, 0.0, -0.05]', 'position: [0.0, 0.0, -0.01]'))
        for gap in (.05, 0., .011):
            r = reference('settle'); r['gap_above_surface_m'] = gap
            with self.subTest(gap=gap), self.assertRaises(ValueError): lower.build_bundle(r, *sources())
        r = reference('settle'); r['target_clearance_m'] = -.01
        with self.assertRaises(ValueError): lower.build_bundle(r, *sources())

    def test_no_arbitrary_gap_stage_or_malformed_provenance(self):
        for key, value in (('version', True), ('stage', 'release'), ('gap_above_surface_m', .18),
                           ('target_clearance_m', 0.), ('surface_height_m', .695),
                           ('gap_above_surface_m', float('nan')), ('surface_height_m', True),
                           ('scope', 'any_box'), ('predecessor_bundle_id', 'a'*63),
                           ('predecessor_goal_id', '80974A9D-F9B2-4322-A2D7-2DB41F28766E'),
                           ('predecessor_goal_id', '00000000-0000-0000-0000-000000000000'),
                           ('predecessor_goal_id', None), ('evidence', '')):
            r = reference(); r[key] = value
            with self.subTest(key=key,value=value), self.assertRaises(ValueError): lower.build_bundle(r, *sources())
        r = reference('support'); r['target_clearance_m'] = -.03
        with self.assertRaises(ValueError): lower.build_bundle(r, *sources())
        r = reference(); r['physical_support_confirmed'] = True
        with self.assertRaises(ValueError): lower.build_bundle(r, *sources())

    def test_source_pins_and_rehashed_trajectory_controls_claims_rejected(self):
        xml, yaml = sources()
        with self.assertRaises(ValueError): lower.build_bundle(reference(), xml, yaml+'\n')
        for old, new in (('position: [0.0, 0.0, -0.14]', 'position: [0.0, 0.0, -0.19]'),
                         ('position: [0.0, 0.0, 0.0]', 'position: [0.0, 0.0, -0.05]'),
                         ('enable_admit: true', 'enable_admit: false'),
                         ('collision_detect: true', 'collision_detect: false'),
                         ('duration: 12.0', 'duration: 14.0'),
                         ('box_size: [0.6, 0.4, 0.28]', 'box_size: [0.603, 0.397, 0.22]')):
            b = bundle(); path = lower.META_ROOT+b['task_name']+'.yaml'
            self.assertIn(old, b['tasks'][path]); b['tasks'][path] = b['tasks'][path].replace(old, new, 1)
            b['manifest']['robot_files'][path] = lower.sha256(b['tasks'][path])
            with self.subTest(old=old), self.assertRaises(ValueError): lower.validate_bundle(b)
        for key, value in (('physical_support_confirmed', True), ('lower_delta_z_m', -.19),
                           ('physical_validation', 'completed')):
            b = bundle(); b['review'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): lower.validate_bundle(b)

    def test_in_memory_validator_needs_neither_file_nor_native_runtime(self):
        b = bundle()
        namespace = {'__name__': 'current_lowering_in_memory', '__package__': None}
        with patch.dict(sys.modules, {'scenario1_deposit': scenario1_deposit}):
            exec(compile(Path(lower.__file__).read_text(), '<memory-lower>', 'exec'), namespace)
        self.assertEqual(namespace['validate_bundle'](b), b)

    def test_cli_new_directory_outputs_and_overwrite_refusal(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); source = root/'reference.json'; output = root/'lowering'
            source.write_text(json.dumps(reference()))
            with contextlib.redirect_stdout(io.StringIO()) as captured:
                self.assertEqual(lower.main(['--reference', str(source), '--output', str(output)]), 0)
            result = json.loads(captured.getvalue())
            self.assertEqual(result['lower_delta_z_m'], -.14)
            self.assertEqual(result['status'], 'PREPARED_LOCALLY_NOT_INSTALLED_OR_EXECUTED')
            b = json.loads((output/'bundle.json').read_text())
            self.assertEqual(lower.validate_bundle(b), b)
            before = {p.name:p.read_bytes() for p in output.iterdir()}
            with self.assertRaises(FileExistsError): lower.main(['--reference', str(source), '--output', str(output)])
            self.assertEqual(before, {p.name:p.read_bytes() for p in output.iterdir()})


if __name__ == '__main__':
    unittest.main()
