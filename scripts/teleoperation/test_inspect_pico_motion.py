import copy
import unittest

from scripts.teleoperation.inspect_pico_motion import inspect


class MotionInspectionTests(unittest.TestCase):
    def motion(self):
        return dict(robot='Utars', source='utars_teleop',
                    head=[dict(q=[0., 0.], t=0.), dict(q=[.1, -.2], t=1.)])

    def test_describes_motion_without_modifying_or_authorizing(self):
        data = self.motion()
        original = copy.deepcopy(data)
        result = inspect(data)
        self.assertEqual(result['groups']['head']['range_rad'], [.1, .2])
        self.assertEqual(result['groups']['head']['duration_s'], 1.)
        self.assertFalse(result['physical_authorized'])
        self.assertFalse(result['freshness_checked'])
        self.assertEqual(data, original)

    def test_compares_joint_names_despite_reordered_state(self):
        state = dict(name=['head_pitch_joint', 'head_yaw_joint'], position=[.002, .001])
        result = inspect(self.motion(), state)
        self.assertTrue(result['initial_geometry_matches_002rad'])
        self.assertEqual(result['max_initial_delta_rad'], .002)
        state['position'][0] = .021
        self.assertFalse(inspect(self.motion(), state)['initial_geometry_matches_002rad'])

    def test_rejects_bad_recording_and_extra_channels(self):
        for fault in ('nan', 'time', 'dimension', 'short', 'unknown', 'robot'):
            data = self.motion()
            if fault == 'nan': data['head'][1]['q'][0] = float('nan')
            if fault == 'time': data['head'][1]['t'] = 0.
            if fault == 'dimension': data['head'][1]['q'].append(0.)
            if fault == 'short': data['head'].pop()
            if fault == 'unknown': data['fingers'] = []
            if fault == 'robot': data['robot'] = 'Other'
            with self.subTest(fault=fault), self.assertRaises(ValueError):
                inspect(data)

    def test_rejects_missing_duplicate_and_invalid_measured_joints(self):
        for state in (dict(name=['head_yaw_joint'], position=[0.]),
                      dict(name=['head_yaw_joint']*2, position=[0., 0.]),
                      dict(name=['head_yaw_joint', 'head_pitch_joint'], position=[0.]),
                      dict(name=['head_yaw_joint', 'head_pitch_joint'], position=[0., float('inf')])):
            with self.subTest(state=state), self.assertRaises(ValueError):
                inspect(self.motion(), state)


if __name__ == '__main__':
    unittest.main()
