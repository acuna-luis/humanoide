"""Native selected-arm preparation contracts; local files only, no robot/SDK."""
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from scripts.box_handling import prepare_native_arm_preparation as builder
from scripts.box_handling.prepare_empty_arm_diagnostic import JOINTS
from scripts.box_handling.test_prepare_empty_arm_diagnostic import state, urdf


SOURCE = builder.SOURCE_XML.read_text()


class NativePreparationTests(unittest.TestCase):
    def test_outbound_action_is_exact_copy_and_return_uses_measured_named_reference(self):
        sample = state()
        original = copy.deepcopy(sample)
        values = dict(zip(sample['name'], sample['position']))
        native = ET.fromstring(SOURCE)
        for arm in ('right', 'left'):
            with self.subTest(arm=arm):
                xml, manifest = builder.prepare(sample, arm, SOURCE, urdf())
                generated = ET.fromstring(xml)
                actions = generated.findall('./BehaviorTree/Sequence/Action')
                source_action = next(a for a in native.findall('./BehaviorTree/Sequence/Parallel/Action') if a.get('location') == arm)
                self.assertEqual(len(actions), 2)
                self.assertEqual(actions[0].attrib, source_action.attrib)
                self.assertEqual(actions[1].get('duration'), '6')
                self.assertEqual(actions[1].get('location'), arm)
                actual = [float(q.strip()) for q in actions[1].get('joint_angles').split(';')]
                self.assertEqual(actual, [values[n] for n in JOINTS[arm+'_arm']])
                self.assertEqual(manifest['candidate']['outbound_duration_s'], 3.)
                self.assertEqual(manifest['candidate']['return_duration_s'], 6.)
                self.assertEqual(manifest['candidate']['total_nominal_duration_s'], 9.)
                self.assertEqual(manifest['source']['initial_joint_reference_20d'], {n: values[n] for n in builder.REQUIRED_JOINTS})
                self.assertEqual(manifest['source']['canonical_joint_state'], sample)
                self.assertEqual(manifest['xml'], xml)
                self.assertEqual(sample, original)

    def test_no_other_arm_head_torso_perception_grasp_or_global_home_commands(self):
        for arm in ('right', 'left'):
            xml, manifest = builder.prepare(state(), arm, SOURCE, urdf())
            root = ET.fromstring(xml)
            self.assertIsNone(root.find('.//Parallel'))
            self.assertEqual(len(root.findall('.//Action')), 2)
            self.assertTrue(all(a.get('ID') == 'MetaMove' and a.get('type') == 'arm' and a.get('location') == arm
                                for a in root.findall('.//Action')))
            self.assertNotIn('MetaClamp', xml)
            self.assertNotIn('MetaLook', xml)
            self.assertNotIn('cruzr/home', xml)
            self.assertFalse(manifest['candidate']['commands_head_lifter_waist'])
            self.assertFalse(manifest['candidate']['has_global_home'])

    def test_changed_native_source_or_invalid_arm_cannot_generate(self):
        for source in (SOURCE+'\n', SOURCE.replace('duration="3"', 'duration="2"')):
            with self.assertRaisesRegex(ValueError, 'SHA256_MISMATCH'):
                builder.prepare(state(), 'right', source, urdf())
        with self.assertRaisesRegex(ValueError, 'Arm'):
            builder.prepare(state(), 'both', SOURCE, urdf())

    def test_non_home_moving_missing_axis_or_duplicate_source_cannot_generate(self):
        for change in (lambda s: s['position'].__setitem__(0, .02),
                       lambda s: s['velocity'].__setitem__(0, .002),
                       lambda s: s['name'].__setitem__(0, 'raw_motor'),
                       lambda s: s['name'].__setitem__(0, s['name'][1])):
            sample = state()
            change(sample)
            with self.subTest(change=change), self.assertRaises(ValueError):
                builder.prepare(sample, 'right', SOURCE, urdf())

    def test_urdf_position_interval_and_necessary_average_speed_fail_closed(self):
        for field, value, error in (('upper', '1.9', 'position interval'), ('velocity', '.5', 'average speed')):
            root = ET.fromstring(urdf())
            root.find("joint[@name='R_shoulder_yaw_joint']/limit").set(field, value)
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, error):
                builder.prepare(state(), 'right', SOURCE, ET.tostring(root, encoding='unicode'))

    def test_average_limit_is_necessary_condition_never_certified_peak_interpolation(self):
        xml, manifest = builder.prepare(state(), 'right', SOURCE, urdf())
        yaw = manifest['urdf']['limits']['R_shoulder_yaw_joint']
        initial = manifest['source']['initial_joint_reference_20d']['R_shoulder_yaw_joint']
        self.assertAlmostEqual(yaw['outbound_average_required_rad_s'], abs(1.910-initial)/3.)
        self.assertAlmostEqual(yaw['return_average_required_rad_s'], abs(1.910-initial)/6.)
        self.assertEqual(manifest['urdf']['velocity_check'], 'NECESSARY_AVERAGE_ONLY')
        self.assertFalse(manifest['urdf']['native_peak_velocity_verified'])
        self.assertFalse(manifest['urdf']['native_interpolation_verified'])
        self.assertFalse(manifest['urdf']['collision_checked'])

    def test_only_unchanged_missing_head_axes_are_allowed_in_native_model(self):
        root = ET.fromstring(urdf())
        for name in JOINTS['head']:
            root.remove(root.find("joint[@name='"+name+"']"))
        _, manifest = builder.prepare(state(), 'right', SOURCE, ET.tostring(root, encoding='unicode'))
        self.assertEqual(manifest['urdf']['checked_joint_count'], 18)
        self.assertEqual(manifest['urdf']['unmodelled_unchanged_joints'], list(JOINTS['head']))
        root.remove(root.find("joint[@name='L_elbow_roll_joint']"))
        with self.assertRaisesRegex(ValueError, 'L_elbow_roll_joint'):
            builder.prepare(state(), 'right', SOURCE, ET.tostring(root, encoding='unicode'))

    def test_task_identity_changes_with_real_return_reference_and_preserves_full_amplitude(self):
        first = state()
        _, a = builder.prepare(first, 'right', SOURCE, urdf())
        second = copy.deepcopy(first)
        second['position'][second['name'].index('R_elbow_roll_joint')] += .001
        _, b = builder.prepare(second, 'right', SOURCE, urdf())
        self.assertNotEqual(a['candidate']['task_name'], b['candidate']['task_name'])
        self.assertEqual(a['candidate']['outbound_joint_target_rad'], [.315, -.484, 1.910, -1.503, .697, .362, .142])

    def test_local_output_hash_namespace_provenance_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'state.json'; source.write_text(json.dumps(state()))
            model = root/'native.urdf'; model.write_text(urdf())
            output = root/'new-task'
            manifest = builder.build(source, 'left', output, model)
            raw = (output/'task.xml').read_bytes()
            sha = hashlib.sha256(raw).hexdigest()
            self.assertEqual(manifest['candidate']['xml_sha256'], sha)
            self.assertEqual(manifest['xml'].encode(), raw)
            self.assertEqual(manifest['candidate']['task_name'], 'diagnostics/native_arm_preparation_left_'+sha[:16])
            self.assertEqual(manifest['candidate']['runtime_path'], builder.TASK_ROOT+manifest['candidate']['task_name']+'.xml')
            self.assertEqual(manifest['source']['canonical_sha256'], hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertEqual(json.loads((output/'manifest.json').read_text()), manifest)
            self.assertEqual(output.stat().st_mode & 0o777, 0o700)
            self.assertEqual(set(p.name for p in output.iterdir()), {'task.xml', 'manifest.json'})
            self.assertEqual(manifest['remote_writes'], 0)
            self.assertEqual(manifest['movement_commands'], 0)
            with self.assertRaisesRegex(ValueError, 'new'):
                builder.build(source, 'right', output, model)
            self.assertEqual((output/'task.xml').read_bytes(), raw)

    def test_invalid_source_leaves_no_output_and_no_run_flag_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'state.json'; source.write_text('{}')
            model = root/'native.urdf'; model.write_text(urdf())
            output = root/'none'
            with self.assertRaises(ValueError):
                builder.build(source, 'right', output, model)
            self.assertFalse(output.exists())
            with patch('sys.stderr', io.StringIO()), self.assertRaises(SystemExit):
                builder.main(['--state', str(source), '--urdf', str(model), '--arm', 'right', '--output', str(output), '--run'])
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
