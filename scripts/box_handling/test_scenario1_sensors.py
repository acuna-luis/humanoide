"""Synthetic sensor-envelope tests; no telemetry acquisition or robot access."""
import copy
import json
import math
from pathlib import Path
import unittest

from scripts.box_handling.scenario1_sensors import NON_POSTURE_JOINTS, evaluate, inspect, validate_profile


NOW = 10_000_000_000
GEOMETRY = 'scenario1_current_geometry_v1'


def wrist_profile(side, state):
    return dict(frame_id=side + '_wrist', force_min=[-1., -1., 8. if state == 'held' else -1.],
                force_max=[1., 1., 12. if state == 'held' else 1.],
                torque_min=[-.2, -.2, -.2], torque_max=[.2, .2, .2],
                max_force_span_n=.5, max_torque_span_nm=.05)


def profile():
    stages = {}
    for state, positions in (('held', [.4, -.2]), ('released', [.1, 0.])):
        stages[state] = dict(pose=dict(joint_names=['joint_a', 'joint_b'],
                                      position_rad=dict(zip(['joint_a', 'joint_b'], positions))),
                             max_pose_error_rad=.02,
                             left=wrist_profile('left', state), right=wrist_profile('right', state))
    return dict(version=1, id='synthetic_test_profile', geometry_id=GEOMETRY,
                qualification='qualified', evidence_reference='synthetic-positive-and-negative-fixture',
                stages=stages)


def snapshot(state='held'):
    ft = {'left': [], 'right': []}
    joints = []
    for index in range(6):
        stamp = NOW - 300_000_000 + index * 50_000_000
        for side in ft:
            ft[side].append(dict(stamp_ns=stamp, received_ns=stamp+10_000_000,
                                 frame_id=side+'_wrist', force=[0., 0., 10. if state == 'held' else 0.],
                                 torque=[0., 0., 0.]))
        joints.append(dict(stamp_ns=stamp, received_ns=stamp+10_000_000,
                           names=['joint_a', 'joint_b'], position=[.4, -.2] if state == 'held' else [.1, 0.],
                           velocity=[0., 0.]))
    return dict(version=1, written_ns=NOW-1_000_000, ft=ft, joints=joints)


class ProfileTest(unittest.TestCase):
    def test_shipped_template_has_no_calibration_and_cannot_authorize_sensor_execution(self):
        pending = json.loads(Path(__file__).with_name('scenario1_sensor_profile.json').read_text())
        self.assertEqual(pending['qualification'], 'pending')
        self.assertEqual(pending['stages'], {'held': None, 'released': None})
        self.assertIsNone(pending['evidence_reference'])
        self.assertEqual(validate_profile(pending, GEOMETRY), pending)
        with self.assertRaisesRegex(ValueError, 'pending'):
            validate_profile(pending, GEOMETRY, require_qualified=True)
        with self.assertRaisesRegex(ValueError, 'pending'):
            evaluate(snapshot(), pending, 'held', NOW)

    def test_valid_profile_is_independent_and_requires_evidence_and_matching_geometry(self):
        original = profile()
        result = validate_profile(original, GEOMETRY, True)
        result['stages']['held']['left']['force_max'][0] = 90
        self.assertEqual(original['stages']['held']['left']['force_max'][0], 1.)
        with self.assertRaises(ValueError):
            validate_profile(original, 'other_geometry')
        for evidence in (None, '', '  ', True, {}):
            changed = profile(); changed['evidence_reference'] = evidence
            with self.subTest(evidence=evidence), self.assertRaises(ValueError):
                validate_profile(changed, GEOMETRY)

    def test_unknown_schema_and_fake_pending_bounds_fail(self):
        changed = profile(); changed['unexpected'] = 1
        with self.assertRaises(ValueError):
            validate_profile(changed, GEOMETRY)
        changed = profile(); changed['qualification'] = 'pending'
        with self.assertRaises(ValueError):
            validate_profile(changed, GEOMETRY)
        changed = profile(); changed['version'] = True
        with self.assertRaises(ValueError):
            validate_profile(changed, GEOMETRY)

    def test_calibration_requires_names_positions_frames_tolerances_and_finite_bounds(self):
        variants = []
        item = profile(); item['stages']['held']['pose']['joint_names'].append('joint_a'); variants.append(item)
        item = profile(); del item['stages']['held']['pose']['position_rad']['joint_a']; variants.append(item)
        item = profile(); item['stages']['held']['left']['frame_id'] = ''; variants.append(item)
        item = profile(); item['stages']['held']['max_pose_error_rad'] = .031; variants.append(item)
        item = profile(); item['stages']['held']['max_pose_error_rad'] = 0; variants.append(item)
        item = profile(); item['stages']['held']['left']['max_force_span_n'] = 0; variants.append(item)
        item = profile(); item['stages']['held']['right']['max_torque_span_nm'] = -1; variants.append(item)
        item = profile(); item['stages']['held']['left']['force_min'][0] = math.nan; variants.append(item)
        item = profile(); item['stages']['held']['left']['torque_max'][1] = math.inf; variants.append(item)
        item = profile(); item['stages']['held']['left']['force_max'][2] = 7; variants.append(item)
        item = profile(); item['stages']['held']['left']['force_max'] = [1, 2]; variants.append(item)
        for item in variants:
            with self.subTest(profile=item), self.assertRaises(ValueError):
                validate_profile(item, GEOMETRY)

    def test_indistinguishable_loads_fail_only_at_overlapping_posture_regions(self):
        item = profile()
        item['stages']['released'] = copy.deepcopy(item['stages']['held'])
        with self.assertRaisesRegex(ValueError, 'overlap'):
            validate_profile(item, GEOMETRY)
        # Different post-task poses have different gravity effects and therefore
        # cannot be required to have disjoint force ranges by this parser.
        item['stages']['released']['pose']['position_rad']['joint_a'] = .1
        self.assertEqual(validate_profile(item, GEOMETRY)['qualification'], 'qualified')
        item = profile(); item['stages']['released']['pose'] = copy.deepcopy(item['stages']['held']['pose'])
        self.assertEqual(validate_profile(item, GEOMETRY)['qualification'], 'qualified')


class TelemetryTest(unittest.TestCase):
    def test_inspection_is_not_a_box_classification_and_preserves_input(self):
        sample = snapshot(); original = copy.deepcopy(sample)
        result = inspect(sample, NOW)
        self.assertFalse(result['box_state_evaluated'])
        self.assertNotIn('state', result)
        self.assertEqual(result['measurements']['left']['count'], 6)
        self.assertEqual(result['measurements']['right']['force_n']['max'], [0., 0., 10.])
        self.assertEqual(sample, original)

    def test_old_buffer_is_not_counted_as_fresh_evidence(self):
        sample = snapshot()
        for stream in (sample['ft']['left'], sample['ft']['right'], sample['joints']):
            old = copy.deepcopy(stream[0]); old['stamp_ns'] = NOW-1_000_000_000
            old['received_ns'] = old['stamp_ns']+10_000_000; stream.insert(0, old)
        self.assertEqual(inspect(sample, NOW)['measurements']['left']['count'], 6)
        with self.assertRaises(ValueError):
            inspect(sample, NOW, min_stamp_ns=NOW-250_000_000)

    def test_requires_both_wrists_joints_and_five_samples_per_stream(self):
        for path in ('left', 'right', 'joints'):
            sample = snapshot()
            container = sample if path == 'joints' else sample['ft']
            container[path] = container[path][-4:]
            with self.subTest(path=path), self.assertRaises(ValueError):
                inspect(sample, NOW)
        sample = snapshot(); del sample['ft']['right']
        with self.assertRaises(ValueError):
            inspect(sample, NOW)

    def test_samples_must_span_point_two_seconds_without_long_gaps(self):
        sample = snapshot()
        for stream in (sample['ft']['left'], sample['ft']['right'], sample['joints']):
            for index, item in enumerate(stream):
                item['stamp_ns'] = NOW-60_000_000 + index*5_000_000
                item['received_ns'] = item['stamp_ns']+1_000_000
        with self.assertRaisesRegex(ValueError, 'span'):
            inspect(sample, NOW)
        sample = snapshot()
        sample['ft']['left'][0]['stamp_ns'] -= 100_000_000
        sample['ft']['left'][0]['received_ns'] -= 100_000_000
        with self.assertRaisesRegex(ValueError, 'gap'):
            inspect(sample, NOW)

    def test_stale_snapshot_future_or_delayed_data_and_invalid_clock_fail(self):
        variants = []
        item = snapshot(); item['written_ns'] = NOW-600_000_000; variants.append(item)
        item = snapshot(); item['written_ns'] = NOW+1; variants.append(item)
        item = snapshot(); item['ft']['left'][-1]['stamp_ns'] = NOW+1; variants.append(item)
        item = snapshot(); item['ft']['left'][0]['received_ns'] = item['ft']['left'][0]['stamp_ns']-1; variants.append(item)
        item = snapshot(); item['joints'][0]['stamp_ns'] -= 600_000_000; variants.append(item)
        item = snapshot(); item['joints'][0]['stamp_ns'] = True; variants.append(item)
        for sample in variants:
            with self.subTest(snapshot=sample), self.assertRaises(ValueError):
                inspect(sample, NOW)
        with self.assertRaises(ValueError):
            inspect(snapshot(), NOW, min_stamp_ns=NOW+1)

    def test_timestamps_cannot_repeat_or_move_backwards(self):
        for path in ('left', 'right', 'joints'):
            for delta in (0, -1):
                sample = snapshot(); stream = sample[path] if path == 'joints' else sample['ft'][path]
                stream[2]['stamp_ns'] = stream[1]['stamp_ns'] + delta
                with self.subTest(path=path, delta=delta), self.assertRaises(ValueError):
                    inspect(sample, NOW)

    def test_latest_left_right_samples_must_be_aligned(self):
        sample = snapshot()
        for item in sample['ft']['right']:
            item['stamp_ns'] -= 150_000_000; item['received_ns'] -= 150_000_000
        with self.assertRaisesRegex(ValueError, 'skew'):
            inspect(sample, NOW)

    def test_all_stream_values_and_frames_must_be_valid_and_consistent(self):
        variants = []
        item = snapshot(); item['ft']['left'][0]['force'][0] = math.nan; variants.append(item)
        item = snapshot(); item['ft']['right'][0]['torque'][1] = math.inf; variants.append(item)
        item = snapshot(); item['ft']['right'][2]['frame_id'] = 'different_frame'; variants.append(item)
        item = snapshot(); item['joints'][0]['position'][0] = True; variants.append(item)
        item = snapshot(); item['joints'][0]['velocity'] = []; variants.append(item)
        item = snapshot(); item['joints'][0]['names'] = ['joint_a', 'joint_a']; variants.append(item)
        item = snapshot(); item['joints'][2]['names'][0] = 'different_joint'; variants.append(item)
        for sample in variants:
            with self.subTest(snapshot=sample), self.assertRaises(ValueError):
                inspect(sample, NOW)

    def test_joint_motion_is_rejected_even_if_final_velocity_is_zero(self):
        sample = snapshot(); sample['joints'][1]['velocity'][0] = .0201
        with self.assertRaisesRegex(ValueError, 'velocity'):
            inspect(sample, NOW)


class EnvelopeTest(unittest.TestCase):
    def test_held_and_released_use_their_own_empirical_pose_and_loads(self):
        for state in ('held', 'released'):
            sample = snapshot(state); original = copy.deepcopy(sample)
            result = evaluate(sample, profile(), state, NOW)
            self.assertEqual(result['state'], state)
            self.assertEqual(result['source'], 'wrist_ft_pose_envelope')
            self.assertEqual(result['profile_id'], 'synthetic_test_profile')
            self.assertIn('box_identity', result['not_directly_measured'])
            self.assertIn('separation_from_another_box', result['not_directly_measured'])
            self.assertIn('destination_support', result['not_directly_measured'])
            self.assertEqual(sample, original)
            json.dumps(result, allow_nan=False)

    def test_pose_matches_by_name_without_assuming_home_or_array_order(self):
        sample = snapshot()
        for item in sample['joints']:
            item['names'].reverse(); item['position'].reverse(); item['velocity'].reverse()
        result = evaluate(sample, profile(), 'held', NOW)
        self.assertEqual(result['measurements']['joints']['max_calibration_pose_error_rad'], 0.)
        for item in sample['joints']:
            item['position'] = [0., 0.]
        with self.assertRaisesRegex(ValueError, 'posture'):
            evaluate(sample, profile(), 'held', NOW)

    def test_all_calibrated_joints_and_exact_wrist_frames_are_required(self):
        item = profile()
        for stage in item['stages'].values():
            stage['pose']['joint_names'] = ['joint_a']
            del stage['pose']['position_rad']['joint_b']
        with self.assertRaisesRegex(ValueError, 'exactly'):
            evaluate(snapshot(), item, 'held', NOW)
        item = profile(); item['stages']['held']['left']['frame_id'] = 'other_frame'
        with self.assertRaisesRegex(ValueError, 'frame'):
            evaluate(snapshot(), item, 'held', NOW)

    def test_either_wrist_force_or_torque_outside_envelope_rejects(self):
        for side in ('left', 'right'):
            for field, axis, value in (('force', 2, 12.1), ('torque', 0, .21)):
                sample = snapshot(); sample['ft'][side][2][field][axis] = value
                with self.subTest(side=side, field=field), self.assertRaisesRegex(ValueError, 'envelope'):
                    evaluate(sample, profile(), 'held', NOW)

    def test_unstable_force_and_torque_fail_inside_broad_envelopes(self):
        for side, field, axis, value in (('left', 'force', 2, 10.6), ('right', 'torque', 1, .06)):
            sample = snapshot(); sample['ft'][side][2][field][axis] = value
            with self.subTest(side=side, field=field), self.assertRaisesRegex(ValueError, 'unstable'):
                evaluate(sample, profile(), 'held', NOW)

    def test_any_pose_sample_outside_calibration_or_unknown_state_rejects(self):
        sample = snapshot(); sample['joints'][0]['position'][0] += .021
        with self.assertRaisesRegex(ValueError, 'posture'):
            evaluate(sample, profile(), 'held', NOW)
        with self.assertRaises(ValueError):
            evaluate(snapshot(), profile(), 'unknown', NOW)

    def test_driving_wheel_positions_after_translation_do_not_change_body_posture(self):
        sample = snapshot()
        wheel_names = sorted(NON_POSTURE_JOINTS)
        for item in sample['joints']:
            item['names'] += wheel_names
            item['position'] += [7.06, .46]
            item['velocity'] += [0., 0.]
        before = evaluate(sample, profile(), 'held', NOW)
        for item in sample['joints']:
            item['position'][-2:] = [12.34, 9.87]
        after = evaluate(sample, profile(), 'held', NOW)
        self.assertEqual(before['measurements']['joints']['max_calibration_pose_error_rad'], 0.)
        self.assertEqual(after['measurements']['joints']['max_calibration_pose_error_rad'], 0.)
        self.assertEqual(after['measurements']['joints']['posture_excluded_joint_names'], wheel_names)
        self.assertEqual(after['measurements']['joints']['excluded_wheel_positions_rad'],
                         dict(zip(wheel_names, [12.34, 9.87])))
        self.assertEqual(inspect(sample, NOW)['measurements']['joints']['posture_excluded_joint_names'], wheel_names)

    def test_wheel_velocities_still_reject_nonstationary_samples(self):
        for wheel_name in NON_POSTURE_JOINTS:
            sample = snapshot()
            for item in sample['joints']:
                item['names'].append(wheel_name)
                item['position'].append(7.06)
                item['velocity'].append(0.)
            sample['joints'][1]['velocity'][-1] = .021
            with self.subTest(wheel=wheel_name), self.assertRaisesRegex(ValueError, 'velocity'):
                evaluate(sample, profile(), 'held', NOW)

    def test_wheel_positions_cannot_be_added_to_calibration(self):
        for wheel_name in NON_POSTURE_JOINTS:
            item = profile()
            for stage in item['stages'].values():
                stage['pose']['joint_names'].append(wheel_name)
                stage['pose']['position_rad'][wheel_name] = 7.06
            with self.subTest(wheel=wheel_name), self.assertRaisesRegex(ValueError, 'wheel positions'):
                validate_profile(item, GEOMETRY)

    def test_only_exact_driving_wheel_names_are_excluded_not_body_or_unknown_joints(self):
        for missing_name in ('waist_yaw_joint', 'head_pitch_joint', 'other_joint', 'driving_wheel_left'):
            sample = snapshot()
            for item in sample['joints']:
                item['names'].append(missing_name)
                item['position'].append(.1)
                item['velocity'].append(0.)
            with self.subTest(name=missing_name), self.assertRaisesRegex(ValueError, 'non-wheel joints'):
                evaluate(sample, profile(), 'held', NOW)


if __name__ == '__main__':
    unittest.main()
