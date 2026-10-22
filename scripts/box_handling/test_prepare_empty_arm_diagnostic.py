"""Offline tests of small SDK candidate construction; no robot, ROS or SDK."""
import copy
import hashlib
import io
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from scripts.box_handling import prepare_empty_arm_diagnostic as builder


def state():
    names = list(reversed(builder.REQUIRED_JOINTS))+['driving_wheel_left_joint', 'driving_wheel_right_joint']
    return dict(header=dict(frame_id='whole_state_controller', stamp=dict(sec=100, nanosec=123)),
                name=names, position=[(index-10)*.0001 for index in range(20)]+[1.2, -2.3],
                velocity=[0.]*22, effort=[0.]*22)


def urdf():
    root = ET.Element('robot', name='native_test')
    for name in builder.REQUIRED_JOINTS:
        joint = ET.SubElement(root, 'joint', name=name, type='revolute')
        ET.SubElement(joint, 'limit', lower='-2', upper='2', velocity='1', effort='10')
    return ET.tostring(root, encoding='unicode')


class EmptyArmCandidateTests(unittest.TestCase):
    def test_each_arm_has_exact_return_scaled_native_direction_and_only_seven_moving_axes(self):
        source = state()
        original = copy.deepcopy(source)
        by_name = dict(zip(source['name'], source['position']))
        for arm in ('right', 'left'):
            with self.subTest(arm=arm):
                motion, review = builder.prepare(source, arm, urdf_text=urdf())
                self.assertEqual(set(motion), {'robot', 'source', *builder.JOINTS})
                self.assertEqual((motion['robot'], motion['source']), ('Utars', 'utars_teleop'))
                self.assertEqual(len(review['candidate']['moving_joints']), 7)
                self.assertEqual(len(review['candidate']['unchanged_joints']), 13)
                scale = math.radians(2)/1.910
                changed = []
                for group, names in builder.JOINTS.items():
                    frames = motion[group]
                    expected_start = [by_name[name] for name in names]
                    self.assertEqual(len(frames), 11001)
                    self.assertEqual(frames[0], dict(t=0., q=expected_start))
                    self.assertEqual(frames[-1], dict(t=22., q=expected_start))
                    self.assertEqual(frames[1000]['q'], expected_start)
                    self.assertEqual(frames[10000]['q'], expected_start)
                    self.assertTrue(all(len(frame['q']) == len(names) for frame in frames))
                    self.assertTrue(all(b['t'] > a['t'] for a, b in zip(frames, frames[1:])))
                    self.assertEqual(frames[5000]['q'], frames[6000]['q'])
                    for index, name in enumerate(names):
                        if group == arm+'_arm':
                            changed.append(name)
                            delta = scale*builder.NATIVE_PREPARATION[arm][index]
                            self.assertAlmostEqual(frames[5000]['q'][index]-by_name[name], delta)
                        else:
                            self.assertTrue(all(frame['q'][index] == by_name[name] for frame in frames))
                self.assertEqual(changed, list(builder.JOINTS[arm+'_arm']))
                self.assertAlmostEqual(max(abs(value) for value in review['candidate']['relative_scaled_vector_rad']), math.radians(2))
                self.assertTrue(review['urdf']['checked'])
                self.assertFalse(review['source']['freshness_verified'])
                self.assertEqual(source, original)

    def test_outward_and_return_ramps_are_monotone_symmetric_and_velocity_bounded(self):
        motion, review = builder.prepare(state(), 'right', 1.)
        frames = motion['right_arm']
        q0 = frames[0]['q']
        delta = review['candidate']['relative_scaled_vector_rad']
        for index, change in enumerate(delta):
            values = [frame['q'][index] for frame in frames[1000:5001]]
            self.assertTrue(all((b-a)*change >= -1e-18 for a, b in zip(values, values[1:])))
            for offset in (0, 1, 500, 2000, 3999, 4000):
                self.assertAlmostEqual(frames[1000+offset]['q'][index]-q0[index],
                                       frames[10000-offset]['q'][index]-q0[index])
        largest = max(abs(a-b) for first, second in zip(frames, frames[1:]) for a, b in zip(first['q'], second['q']))
        bound = 1.875*math.radians(1)/8
        self.assertLessEqual(largest*500, bound+1e-12)
        self.assertAlmostEqual(review['candidate']['largest_sample_step_rad'], largest)
        self.assertFalse(review['urdf']['checked'])

    def test_no_zero_fill_acceptance_or_raw_motor_axis_substitution(self):
        for name in builder.REQUIRED_JOINTS:
            source = state()
            index = source['name'].index(name)
            for field in ('name', 'position', 'velocity', 'effort'):
                source[field].pop(index)
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'Missing canonical 20D'):
                builder.prepare(source, 'right')
        source = state()
        source['name'][0] = 'head_yaw_motor'
        with self.assertRaisesRegex(ValueError, 'Missing canonical 20D'):
            builder.prepare(source, 'right')

    def test_home_and_rest_limits_are_strict_and_no_motion_is_prepared_on_failure(self):
        for field, value in (('position', .02), ('position', -.02), ('velocity', .002), ('velocity', -.002)):
            source = state()
            source[field][0] = value
            with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, 'HOME|rest'):
                builder.prepare(source, 'left')
        source = state()
        source['velocity'][-1] = .002
        with self.assertRaisesRegex(ValueError, 'rest'):
            builder.prepare(source, 'right')

    def test_malformed_incomplete_nonnumeric_and_nonfinite_sources_rejected(self):
        changes = (lambda s: s['position'].pop(), lambda s: s.update(velocity=[]),
                   lambda s: s['name'].__setitem__(0, s['name'][1]),
                   lambda s: s['position'].__setitem__(0, True),
                   lambda s: s['position'].__setitem__(0, math.nan),
                   lambda s: s['velocity'].__setitem__(0, math.inf),
                   lambda s: s['effort'].__setitem__(0, '0'),
                   lambda s: s['position'].__setitem__(0, 10**400),
                   lambda s: s['header']['stamp'].update(sec=True),
                   lambda s: s['header']['stamp'].update(nanosec=10**9),
                   lambda s: s.pop('header'))
        for mutate in changes:
            source = state()
            mutate(source)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                builder.prepare(source, 'right')
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON key'):
            builder.json_object('{"name":[],"name":[]}')

    def test_arm_and_amplitude_cannot_expand_authorized_envelope(self):
        for amplitude in (0, -1, 2.000001, 90., True, '2', math.nan, math.inf):
            with self.subTest(amplitude=amplitude), self.assertRaises(ValueError):
                builder.prepare(state(), 'right', amplitude)
        with self.assertRaisesRegex(ValueError, 'Arm'):
            builder.prepare(state(), 'both')

    def test_urdf_requires_every_named_axis_and_checks_position_and_velocity(self):
        cases = []
        missing = ET.fromstring(urdf())
        missing.remove(missing.find("joint[@name='R_shoulder_pitch_joint']"))
        cases.append(missing)
        duplicate = ET.fromstring(urdf())
        duplicate.append(copy.deepcopy(duplicate.find('joint')))
        cases.append(duplicate)
        bad_position = ET.fromstring(urdf())
        bad_position.find("joint[@name='R_shoulder_yaw_joint']/limit").set('upper', '.02')
        cases.append(bad_position)
        bad_velocity = ET.fromstring(urdf())
        bad_velocity.find("joint[@name='R_shoulder_yaw_joint']/limit").set('velocity', '.001')
        cases.append(bad_velocity)
        for root in cases:
            with self.subTest(xml=ET.tostring(root)), self.assertRaises(ValueError):
                builder.prepare(state(), 'right', urdf_text=ET.tostring(root, encoding='unicode'))

    def test_native_manipulation_urdf_can_omit_only_explicitly_unchanged_head_axes(self):
        root = ET.fromstring(urdf())
        for name in builder.JOINTS['head']:
            root.remove(root.find("joint[@name='"+name+"']"))
        motion, review = builder.prepare(state(), 'right', urdf_text=ET.tostring(root, encoding='unicode'))
        self.assertEqual(review['urdf']['checked_joint_count'], 18)
        self.assertEqual(review['urdf']['unmodelled_unchanged_joints'], list(builder.JOINTS['head']))
        self.assertTrue(all(frame['q'] == motion['head'][0]['q'] for frame in motion['head']))
        root.remove(root.find("joint[@name='waist_yaw_joint']"))
        with self.assertRaisesRegex(ValueError, 'waist_yaw_joint'):
            builder.prepare(state(), 'right', urdf_text=ET.tostring(root, encoding='unicode'))

    def test_local_artifact_hashes_record_provenance_and_preserve_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'state.json'
            source.write_text(json.dumps(state()))
            model = root/'native.urdf'
            model.write_text(urdf())
            output = root/'new-candidate'
            review = builder.build(source, 'right', output, urdf_path=model)
            raw = (output/'empty_arm_right.motion').read_bytes()
            self.assertEqual(review['candidate']['sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(review['source']['sha256'], hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertEqual(review['urdf']['sha256'], hashlib.sha256(model.read_bytes()).hexdigest())
            self.assertEqual(json.loads((output/'review.json').read_text()), review)
            self.assertEqual(set(p.name for p in output.iterdir()), {'empty_arm_right.motion', 'review.json'})
            self.assertEqual(output.stat().st_mode & 0o777, 0o700)
            self.assertFalse(review['physical_approval'])
            self.assertEqual(review['movement_commands'], 0)
            with self.assertRaisesRegex(ValueError, 'new'):
                builder.build(source, 'left', output)
            self.assertEqual((output/'empty_arm_right.motion').read_bytes(), raw)

    def test_invalid_input_does_not_create_output_and_cli_has_no_execution_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'state.json'
            source.write_text('{}')
            output = root/'never-created'
            with self.assertRaises(ValueError):
                builder.build(source, 'right', output)
            self.assertFalse(output.exists())
            with patch('sys.stderr', io.StringIO()), self.assertRaises(SystemExit):
                builder.main(['--state', str(source), '--arm', 'right', '--output', str(output), '--run'])
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
