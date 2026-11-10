import math
import unittest

from audit_ball_arm_proposals import MODEL_ORDER
from ball_arm_preview_guard import BODY_NAMES
from ball_arm_trajectory_preview import preview


def example():
    # Synthetic limits and state only; not limits of the robot.
    return {
        'state': {'names': list(reversed(BODY_NAMES)), 'positions': [0.0] * 20,
                  'velocities': [0.0] * 20, 'received_monotonic_ns': 100},
        'proposal': {'names': list(MODEL_ORDER),
                     'positions': [0.1, -0.1, 0.05, 0.0, 0.05, 0.0, -0.05],
                     'received_monotonic_ns': 105},
        'policy': {'max_state_age_ns': 20, 'max_proposal_age_ns': 20,
                   'preview_duration_seconds': 3.0,
                   'joint_limits': {name: {'min_position_rad': -1.0,
                                           'max_position_rad': 1.0,
                                           'max_delta_rad': 0.2,
                                           'max_velocity_rad_s': 0.3,
                                           'max_acceleration_rad_s2': 0.3,
                                           'stationary_velocity_rad_s': 0.01}
                                    for name in MODEL_ORDER}},
        'now_ns': 110, 'sample_count': 11, 'locked_stationary_velocity_rad_s': 0.01,
    }


class PreviewTests(unittest.TestCase):
    def test_coupled_segment_and_other_axes_fixed_by_name(self):
        source = example()
        result = preview(source)
        self.assertTrue(result['preview_generated'])
        self.assertFalse(result['physical_control_qualified'])
        self.assertEqual(result['physical_commands_generated'], 0)
        self.assertEqual(len(result['samples']), 11)
        names = result['joint_names']
        for row in result['samples']:
            for name in BODY_NAMES:
                actual = row['positions_rad'][names.index(name)]
                if name not in MODEL_ORDER:
                    self.assertEqual(actual, 0.0)
                else:
                    target = source['proposal']['positions'][MODEL_ORDER.index(name)]
                    self.assertGreaterEqual(actual, min(0.0, target))
                    self.assertLessEqual(actual, max(0.0, target))
        last = result['samples'][-1]
        self.assertEqual(last['relative_time_s'], 3.0)
        for name, target in zip(MODEL_ORDER, source['proposal']['positions'], strict=True):
            self.assertAlmostEqual(last['positions_rad'][names.index(name)], target)

    def test_rejects_large_model_delta_without_clamping(self):
        source = example()
        source['proposal']['positions'][0] = 0.9
        result = preview(source)
        self.assertFalse(result['preview_generated'])
        self.assertEqual(result['samples'], [])
        self.assertIn('R_shoulder_pitch_joint:delta_exceeds_limit', result['reasons'])

    def test_rejects_state_and_proposal_staleness(self):
        source = example()
        source['now_ns'] = 1000
        result = preview(source)
        self.assertEqual(result['samples'], [])
        self.assertIn('state_timestamp_future_or_stale', result['reasons'])
        self.assertIn('proposal_timestamp_future_or_stale', result['reasons'])

    def test_rejects_movement_of_other_arm(self):
        source = example()
        name = 'L_elbow_roll_joint'
        source['state']['velocities'][source['state']['names'].index(name)] = 0.02
        result = preview(source)
        self.assertEqual(result['samples'], [])
        self.assertIn(name + ':locked_state_not_stationary', result['reasons'])

    def test_invalid_counts_and_nan_are_errors(self):
        for bad in (True, 1, 1002):
            source = example()
            source['sample_count'] = bad
            with self.assertRaises(ValueError):
                preview(source)
        source = example()
        source['proposal']['positions'][0] = math.nan
        with self.assertRaises(ValueError):
            preview(source)

    def test_rejects_too_short_motion_time(self):
        source = example()
        source['policy']['preview_duration_seconds'] = 0.1
        result = preview(source)
        self.assertEqual(result['samples'], [])
        self.assertTrue(any(reason.endswith('duration_below_mathematical_bound')
                            for reason in result['reasons']))


if __name__ == '__main__':
    unittest.main()
