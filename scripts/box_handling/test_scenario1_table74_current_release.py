"""Pure opening-phase tests: no native runtime, network or robot movement."""
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

from scripts.box_handling import scenario1_deposit as deposit
from scripts.box_handling import scenario1_table74_current_release as release


def reference(stage='pin_relief',version=2):
    return dict(version=version, stage=stage, surface_height_m=.74,
        predecessor_bundle_id='a'*64, predecessor_goal_id='80974a9d-f9b2-4322-a2d7-2db41f28766e',
        operator_support_confirmed=True, tool_table_clearance_m=(.05 if version==2 and stage=='pin_relief' else .04),
        required_pin_exit_m=(.04 if version==2 else .03),
        operator_pins_free=stage == 'lateral_open', lateral_path_clear=True,
        evidence='SYNTHETIC TEST ONLY: operator confirms supported box, current clearance and pin state.',
        scope='current_supported_box_only')


def sources():
    root = Path(__file__).resolve().parents[2]/'vendor/ubtech/cruzr_s2/snapshot_20260916/motion'
    return ((root/'tasks/wrc_cruzr/put_cruzr_wrc_low.xml').read_text(),
            (root/'meta_clamp/wrc/open_arm_cruzr.yaml').read_text())


def bundle(stage='pin_relief',version=2):
    return release.build_bundle(reference(stage,version), *sources())


class CurrentReleaseTests(unittest.TestCase):
    def test_two_separate_exact_phases_without_roll_or_combined_movement(self):
        for stage, left, right in (('pin_relief', [0., 0., -.04], [0., 0., -.04]),
                                    ('lateral_open', [0., .1, 0.], [0., -.1, 0.])):
            with self.subTest(stage=stage):
                b = bundle(stage); review = b['review']; name = b['task_name']
                self.assertEqual(release.validate_bundle(b), b)
                self.assertEqual(review['stage'], stage)
                self.assertEqual(review['left_hand_delta_m'], left)
                self.assertEqual(review['right_hand_delta_m'], right)
                self.assertEqual(review['torso_delta_m'], [0., 0., 0.])
                self.assertEqual(review['relative_quaternion_wxyz'], [1., 0., 0., 0.])
                yaml = b['tasks'][release.META_ROOT+name+'.yaml']
                self.assertEqual(yaml.count('timestamp: 2.0'), 3)
                self.assertEqual(yaml.count('orientation: [1.0, 0.0, 0.0, 0.0]'), 3)
                self.assertEqual(yaml.count('tranform_mode: "RELATIVE"'), 3)
                self.assertNotIn('0.7933533', yaml)
                self.assertNotIn('-0.05', yaml)
                actions = ET.fromstring(b['tasks'][release.TASK_ROOT+name+'.xml']).findall('.//Action')
                self.assertEqual([a.attrib for a in actions], [dict(ID='MetaClamp', name=name)])

    def test_all_other_vendor_parameters_byte_preserved_including_five_value_limit(self):
        xml, yaml = sources()
        self.assertEqual(release.DEPENDENCIES[release.SOURCE_YAML_PATH],
                         'c41bd1d88379c2012ee44639142fb5b55c1d58decd6a75851c8e17763778e37b')
        self.assertEqual(release.SOURCE_YAML_PATH, deposit.SOURCE_OPEN_PATH)
        self.assertEqual(set(release.DEPENDENCIES), {release.SOURCE_XML_PATH, release.SOURCE_YAML_PATH, release.META_CLAMP_PATH})
        for stage in ('pin_relief', 'lateral_open'):
            b = bundle(stage); name = b['task_name']; candidate = b['tasks'][release.META_ROOT+name+'.yaml']
            self.assertEqual(candidate, yaml.replace(release._SOURCE_TRAJECTORY, release._trajectory(stage), 1))
            self.assertIn('position_rotation_limit_up: [1.0, 0.1, 0.0, 0.5, 0.4]', candidate)
            self.assertIn('box_size: [0.6, 0.4, 0.28]', candidate)
            self.assertIn('duration: 2.0', candidate)
            self.assertIn('task_stack: task_stack_cruzr_clamp_manipulability.yaml', candidate)

    def test_current_declarations_never_create_sensor_or_physical_qualification_claim(self):
        review = bundle()['review']
        self.assertIs(review['reference']['operator_support_confirmed'], True)
        for key in ('physical_support_sensor_verified', 'pin_disengagement_sensor_verified',
                    'release_physically_qualified', 'measured_absolute_calibration_created',
                    'automatic_execution_authorized', 'installed', 'integrated_in_optimistic'):
            self.assertIs(review[key], False)
        self.assertEqual(review['physical_validation'], 'pending')

    def test_stage_predecessor_and_current_evidence_change_immutable_identity(self):
        original = bundle()
        for key, value in (('predecessor_bundle_id', 'b'*64),
                           ('predecessor_goal_id', '8a15575b-f746-4405-8a1d-c819b092d01f'),
                           ('tool_table_clearance_m', .06), ('required_pin_exit_m', .02),
                           ('evidence', 'Another synthetic current report')):
            r = reference(); r[key] = value
            self.assertNotEqual(release.build_bundle(r, *sources())['task_name'], original['task_name'])
        self.assertNotEqual(bundle('lateral_open')['task_name'], original['task_name'])

    def test_missing_support_unknown_pin_state_and_insufficient_clearance_rejected(self):
        for key, value in (('operator_support_confirmed', False), ('operator_support_confirmed', 1),
                ('lateral_path_clear', False), ('lateral_path_clear', 1), ('operator_pins_free', True),
                ('operator_pins_free', 0), ('tool_table_clearance_m', .04999), ('tool_table_clearance_m', True),
                ('required_pin_exit_m', 0), ('required_pin_exit_m', -.01), ('required_pin_exit_m', .04001),
                ('required_pin_exit_m', True), ('tool_table_clearance_m', float('inf')),
                ('required_pin_exit_m', float('nan')), ('tool_table_clearance_m', 10**400),
                ('surface_height_m', .695), ('version', True), ('stage', 'combined'), ('scope', 'any_box'),
                ('predecessor_bundle_id', 'a'*63), ('predecessor_goal_id', None),
                ('predecessor_goal_id', '00000000-0000-0000-0000-000000000000'), ('evidence', ' ')):
            r = reference(); r[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError): release.build_bundle(r, *sources())
        for value in (False, None, 1):
            r = reference('lateral_open'); r['operator_pins_free'] = value
            with self.subTest(pins_free=value), self.assertRaises(ValueError): release.build_bundle(r, *sources())
        for modifier in ('extra', 'missing'):
            r = reference()
            if modifier == 'extra': r['physical_validation'] = 'complete'
            else: del r['lateral_path_clear']
            with self.assertRaises(ValueError): release.build_bundle(r, *sources())

    def test_source_changes_and_rehashed_unsafe_candidate_changes_rejected(self):
        xml, yaml = sources()
        for changed_xml, changed_yaml in ((xml+'\n', yaml), (xml, yaml+'\n')):
            with self.assertRaises(ValueError): release.build_bundle(reference(), changed_xml, changed_yaml)
        for old, new in (('position: [0.0, 0.0, -0.04]', 'position: [0.0, 0.0, -0.05]'),
                ('orientation: [1.0, 0.0, 0.0, 0.0]', 'orientation: [0.7933533, 0.6087614, 0.0, 0.0]'),
                ('duration: 2.0', 'duration: 1.0'),
                ('position_rotation_limit_up: [1.0, 0.1, 0.0, 0.5, 0.4]',
                 'position_rotation_limit_up: [1.0, 0.1, 0.0, 0.5, 0.4, 0.4]'),
                ('box_size: [0.6, 0.4, 0.28]', 'box_size: [0.603, 0.397, 0.22]')):
            b = bundle(); path = release.META_ROOT+b['task_name']+'.yaml'
            self.assertIn(old, b['tasks'][path]); b['tasks'][path] = b['tasks'][path].replace(old, new, 1)
            b['manifest']['robot_files'][path] = release.sha256(b['tasks'][path])
            with self.subTest(old=old), self.assertRaises(ValueError): release.validate_bundle(b)
        for key, value in (('physical_validation', 'complete'), ('release_physically_qualified', True),
                           ('left_hand_delta_m', [0., .1, -.04])):
            b = bundle(); b['review'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): release.validate_bundle(b)

    def test_checked_in_three_cm_bundle_remains_byte_exact_and_historically_valid(self):
        path=Path(__file__).resolve().parents[2]/'config/box_handling/scenario1_table74/current_trial_20261022/pin-relief-bundle/bundle.json'
        historical=json.loads(path.read_text())
        self.assertEqual(historical['manifest']['id'],'9621edaa01540251414915ada2781d194e7fffa277a028163c244b3348d30f04')
        self.assertEqual(historical['review']['reference']['version'],1)
        self.assertEqual(release.validate_bundle(historical),historical)
        self.assertEqual(release.build_bundle(historical['review']['reference'],*sources()),historical)
        self.assertEqual(historical['review']['left_hand_delta_m'],[0.,0.,-.03])

    def test_versioned_three_and_four_cm_contracts_have_distinct_exact_displacements(self):
        legacy=reference(version=1);legacy['tool_table_clearance_m']=.05
        current=dict(legacy,version=2)
        first=release.build_bundle(legacy,*sources());second=release.build_bundle(current,*sources())
        self.assertNotEqual(first['manifest']['id'],second['manifest']['id'])
        self.assertEqual(first['manifest']['builder_version'],1)
        self.assertEqual(second['manifest']['builder_version'],2)
        for value,distance in ((first,-.03),(second,-.04)):
            self.assertEqual(release.validate_bundle(value),value)
            self.assertEqual(value['review']['left_hand_delta_m'],[0.,0.,distance])
            self.assertEqual(value['review']['right_hand_delta_m'],[0.,0.,distance])
            self.assertEqual(value['review']['torso_delta_m'],[0.,0.,0.])

    def test_v2_requires_five_cm_before_relief_and_four_cm_before_zero_z_opening(self):
        for stage,minimum in (('pin_relief',.05),('lateral_open',.04)):
            r=reference(stage);r['tool_table_clearance_m']=minimum
            self.assertEqual(release.validate_reference(r)['tool_table_clearance_m'],minimum)
            r['tool_table_clearance_m']=minimum-.00001
            with self.subTest(stage=stage),self.assertRaises(ValueError):release.validate_reference(r)
        legacy=reference(version=1)
        self.assertEqual(release.validate_reference(legacy)['tool_table_clearance_m'],.04)
        legacy['required_pin_exit_m']=.04
        with self.assertRaises(ValueError):release.validate_reference(legacy)

    def test_validator_pure_in_memory_without_file_or_native_runtime(self):
        b = bundle(); namespace = {'__name__': 'current_release_in_memory', '__package__': None}
        with patch.dict(sys.modules, {'scenario1_deposit': deposit}):
            exec(compile(Path(release.__file__).read_text(), '<release-memory>', 'exec'), namespace)
        self.assertEqual(namespace['validate_bundle'](b), b)

    def test_cli_outputs_new_directory_only_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); path = root/'reference.json'; output = root/'release'
            path.write_text(json.dumps(reference()))
            with contextlib.redirect_stdout(io.StringIO()) as captured:
                self.assertEqual(release.main(['--reference', str(path), '--output', str(output)]), 0)
            self.assertEqual(json.loads(captured.getvalue())['status'], 'PREPARED_LOCALLY_NOT_INSTALLED_OR_EXECUTED')
            b = json.loads((output/'bundle.json').read_text()); self.assertEqual(release.validate_bundle(b), b)
            before = {p.name:p.read_bytes() for p in output.iterdir()}
            with self.assertRaises(FileExistsError): release.main(['--reference', str(path), '--output', str(output)])
            self.assertEqual(before, {p.name:p.read_bytes() for p in output.iterdir()})


if __name__ == '__main__':
    unittest.main()
