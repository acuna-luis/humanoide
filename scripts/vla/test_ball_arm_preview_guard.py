"""Meaningful offline checks for name mapping and fail-closed diagnostics."""
import copy
import math
import unittest

import ball_arm_preview_guard as guard


def example():
    # These are synthetic test values only; they are not robot limits.
    names = list(reversed(guard.BODY_NAMES))
    pos = [0.0] * 20
    vel = [0.0] * 20
    limits = {name: {'min_position_rad': -2.0, 'max_position_rad': 2.0,
                     'max_delta_rad': 0.5, 'max_velocity_rad_s': 1.0,
                     'max_acceleration_rad_s2': 2.0, 'stationary_velocity_rad_s': 0.01}
              for name in guard.MODEL_ORDER}
    return ({'names': names, 'positions': pos, 'velocities': vel,
             'received_monotonic_ns': 999},
            {'names': list(guard.MODEL_ORDER), 'positions': [0.1] * 7,
             'received_monotonic_ns': 998},
            {'max_state_age_ns': 20, 'max_proposal_age_ns': 20,
             'preview_duration_seconds': 2.0, 'joint_limits': limits}, 1000)


class PreviewGuardTests(unittest.TestCase):
    def test_names_not_array_order_and_no_physical_authority(self):
        state, proposal, policy, now = example()
        selected = guard.MODEL_ORDER[0]
        state['positions'][state['names'].index(selected)] = 0.05
        result = guard.review(state, proposal, policy, now)
        self.assertTrue(result['diagnostic_passed'])
        self.assertAlmostEqual(result['joints'][0]['difference_rad'], 0.05)
        self.assertIs(result['physical_control_qualified'], False)
        self.assertEqual(result['physical_commands_generated'], 0)

    def test_stale_future_and_moving_samples_rejected(self):
        state, proposal, policy, now = example()
        state['received_monotonic_ns'] = 979
        proposal['received_monotonic_ns'] = 1001
        state['velocities'][state['names'].index(guard.MODEL_ORDER[0])] = 0.011
        result = guard.review(state, proposal, policy, now)
        self.assertFalse(result['diagnostic_passed'])
        self.assertIn('state_timestamp_future_or_stale', result['reasons'])
        self.assertIn('proposal_timestamp_future_or_stale', result['reasons'])
        self.assertIn(guard.MODEL_ORDER[0] + ':state_not_stationary', result['reasons'])

    def test_large_jump_and_position_rejected(self):
        state, proposal, policy, now = example()
        proposal['positions'][0] = 3.0
        reasons = guard.review(state, proposal, policy, now)['reasons']
        self.assertIn(guard.MODEL_ORDER[0] + ':delta_exceeds_limit', reasons)
        self.assertIn(guard.MODEL_ORDER[0] + ':proposal_outside_limits', reasons)

    def test_minimum_jerk_speed_and_acceleration_bounds(self):
        state, proposal, policy, now = example()
        result = guard.review(state, proposal, policy, now)
        expected = max(1.875 * 0.1, math.sqrt((10 / math.sqrt(3)) * 0.1 / 2))
        self.assertAlmostEqual(result['joints'][0]['minimum_hypothetical_duration_s'], expected)
        policy['preview_duration_seconds'] = expected / 2
        self.assertIn(guard.MODEL_ORDER[0] + ':duration_below_mathematical_bound',
                      guard.review(state, proposal, policy, now)['reasons'])

    def test_missing_limits_duplicate_names_nan_and_booleans_fail(self):
        state, proposal, policy, now = example()
        mutations = []
        p = copy.deepcopy(policy); del p['joint_limits'][guard.MODEL_ORDER[0]]; mutations.append((state, proposal, p, now))
        s = copy.deepcopy(state); s['names'][1] = s['names'][0]; mutations.append((s, proposal, policy, now))
        s = copy.deepcopy(state); s['names'][0] = 'unrelated_joint'; mutations.append((s, proposal, policy, now))
        p = copy.deepcopy(proposal); p['positions'][0] = float('nan'); mutations.append((state, p, policy, now))
        p = copy.deepcopy(proposal); p['positions'][0] = True; mutations.append((state, p, policy, now))
        p = copy.deepcopy(policy); p['joint_limits'][guard.MODEL_ORDER[0]]['max_velocity_rad_s'] = 0; mutations.append((state, proposal, p, now))
        for args in mutations:
            with self.subTest(args=args), self.assertRaises(ValueError):
                guard.review(*args)

    def test_body_names_match_versioned_profile(self):
        import json
        from pathlib import Path
        profile = Path(__file__).parent / 'runtime/cruzr_s2_vla_profile.json'
        names = json.loads(profile.read_text())['joint_names']
        self.assertEqual(list(guard.BODY_NAMES), names)

    def test_other_axes_stationarity_is_explicitly_out_of_scope(self):
        state, proposal, policy, now = example()
        state['velocities'][state['names'].index('head_yaw_joint')] = 0.1
        result = guard.review(state, proposal, policy, now)
        self.assertTrue(result['diagnostic_passed'])
        self.assertTrue(any('other 13' in limitation for limitation in result['limitations']))


if __name__ == '__main__':
    unittest.main()
