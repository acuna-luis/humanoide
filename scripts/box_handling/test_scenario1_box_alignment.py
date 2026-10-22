"""Pure visual-alignment regressions; no clients, processes or robot access."""
import copy
import math
import unittest

from scripts.box_handling import front_sps_contract as sps
from scripts.box_handling import scenario1_box_alignment as alignment
from scripts.box_handling.scenario1_perception import validate_pair


def selection(stamp=100_000_000_000, x=.78, y=.1, z=.62, yaw=0.):
    return dict(stamp_ns=stamp, selection=dict(selected_index=0,
        selected_pose=dict(position=dict(x=x, y=y, z=z),
            orientation=dict(x=0., y=0., z=math.sin(yaw/2), w=math.cos(yaw/2)))))


def detection_report():
    def pose(x, y, z):
        return dict(position=dict(x=x, y=y, z=z), orientation=dict(x=0., y=0., z=0., w=1.))
    header = dict(frame_id='stereo_left_rectified_optical_frame', stamp=dict(sec=100, nanosec=0))
    return dict(status=4, request_ns=99_900_000_000,
        vision_result=dict(ok=True, trans_outputs=dict(camera_name='head', object_name='workbin',
            box_pose=dict(header=header, poses=[pose(.55, .7, 1.3), pose(.5909, .02, .4)]))),
        tf_at_detection=dict(header=dict(frame_id='base_link', stamp=copy.deepcopy(header['stamp'])),
            child_frame_id=header['frame_id'], transform=dict(translation=dict(x=.2, y=0., z=0.),
                rotation=dict(x=0., y=0., z=0., w=1.))))


def odometry(stamp, x=1., y=2., yaw=0.):
    return dict(header=dict(stamp=dict(sec=stamp//10**9, nanosec=stamp % 10**9), frame_id='odom'),
        child_frame_id='base_link', pose=dict(pose=dict(position=dict(x=x, y=y, z=0.),
            orientation=dict(x=0., y=0., z=math.sin(yaw/2), w=math.cos(yaw/2)))),
        twist=dict(twist=dict(linear=dict(x=0., y=0., z=0.), angular=dict(x=0., y=0., z=0.))))


def base_report(completed, x=1., y=2., yaw=0.):
    return dict(stationary=True, publishers=1, requested_ns=completed-100_000_000,
        completed_ns=completed, samples=[odometry(completed-n, x, y, yaw) for n in (80_000_000, 20_000_000)])


class PolicyTests(unittest.TestCase):
    def test_count_zero_to_seven_only_and_fixed_budgets(self):
        for count in range(8):
            policy = alignment.make_policy(count)
            self.assertEqual(policy['max_corrections'], count)
            self.assertEqual({k: v for k, v in policy.items() if k != 'max_corrections'},
                             {k: v for k, v in alignment.POLICY.items() if k != 'max_corrections'})
            with self.assertRaises(TypeError):
                policy['max_step_m'] = 1.
        self.assertEqual(alignment.make_policy()['max_corrections'], 7)
        self.assertEqual(alignment.POLICY['max_corrections'], 7)
        self.assertEqual(alignment.POLICY['max_step_m'], .05)
        self.assertEqual(alignment.POLICY['max_total_m'], .1)
        self.assertEqual(alignment.POLICY['total_budget_s'], 120.)
        self.assertNotIn('max_recoveries', alignment.POLICY)

    def test_noninteger_unbounded_or_negative_count_rejected(self):
        for count in (-1, 8, 10**100, 7., True, False, None, '7', math.nan, math.inf):
            with self.subTest(count=count), self.assertRaisesRegex(ValueError, 'INVALID_MAX_CORRECTIONS'):
                alignment.make_policy(count)


class ObservationTests(unittest.TestCase):
    def test_outside_gate_is_observation_only_and_original_detection_unchanged(self):
        report = detection_report()
        original = copy.deepcopy(report)
        observed = alignment.observe(report, 100_100_000_000)
        self.assertAlmostEqual(observed['selection']['selected_pose']['position']['x'], .7909)
        self.assertFalse(observed['selection']['motion_authorized'])
        self.assertEqual(observed['detection'], report)
        self.assertEqual(report, original)
        with self.assertRaisesRegex(ValueError, 'BOX_POSITION_REJECTED'):
            sps.select_report(report, 100_100_000_000)

    def test_detection_requires_freshness_success_and_exact_tf(self):
        changes = (lambda r: r.update(status=6),
                   lambda r: r['vision_result'].update(ok=False),
                   lambda r: r['tf_at_detection']['header']['stamp'].update(sec=99),
                   lambda r: r['tf_at_detection']['header'].update(frame_id='map'),
                   lambda r: r['tf_at_detection'].update(child_frame_id='other'),
                   lambda r: r.update(request_ns=101_000_000_000))
        for mutate in changes:
            report = detection_report()
            mutate(report)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                alignment.observe(report, 100_100_000_000)
        for now in (99_999_999_999, 102_000_000_001):
            with self.subTest(now=now), self.assertRaises(ValueError):
                alignment.observe(detection_report(), now)

    def test_unchosen_alternative_never_substitutes_selected_out_of_gate_box(self):
        report = detection_report()
        observed = alignment.observe(report, 100_100_000_000)
        self.assertEqual(observed['selection']['selected_index'], 1)
        delta = alignment.displacement(observed)
        self.assertAlmostEqual(delta['x'], .0209)
        self.assertEqual(observed['selection']['selected_index'], 1)


class GeometryTests(unittest.TestCase):
    def test_native_gate_and_ten_mm_reserve_remain_unchanged(self):
        self.assertEqual(sps.POSITION_MARGIN_M, .01)
        self.assertEqual(sps.POSITION_BOUNDS_M, dict(x=(.41, .79), y=(-.39, .39), z=(.01, 1.49)))
        for x in (.41, .79):
            sps.validate_position(selection(x=x)['selection']['selected_pose'])
        for x in (.409999999, .790000001):
            with self.subTest(x=x), self.assertRaisesRegex(ValueError, 'BOX_POSITION_REJECTED'):
                sps.validate_position(selection(x=x)['selection']['selected_pose'])

    def test_inner_margin_exact_limits_never_request_chassis_motion(self):
        for x in (.43, .6, .77):
            for y in (-.37, 0., .37):
                with self.subTest(x=x, y=y):
                    self.assertEqual(alignment.displacement(selection(x=x, y=y)), dict(x=0., y=0.))
                    self.assertEqual(alignment.violation(selection(x=x, y=y)), 0.)

    def test_both_axes_signs_and_original_pose_preserved(self):
        for x, y, expected in ((.405, 0., dict(x=-.025, y=0.)),
                              (.8, 0., dict(x=.03, y=0.)),
                              (.6, -.395, dict(x=0., y=-.025)),
                              (.6, .395, dict(x=0., y=.025)),
                              (.8, .395, dict(x=.03, y=.025))):
            pending = selection(x=x, y=y)
            before = copy.deepcopy(pending)
            delta = alignment.displacement(pending)
            for axis in 'xy':
                self.assertAlmostEqual(delta[axis], expected[axis])
            self.assertEqual(pending, before)

    def test_near_edge_correction_includes_arrival_residual_and_improvement(self):
        # The box is natively admissible but lies outside the preparation margin.
        pending = selection(x=.7805179438290441)
        sps.validate_position(pending['selection']['selected_pose'])
        delta = alignment.displacement(pending)
        self.assertAlmostEqual(delta['x'], .0245179438290441)
        self.assertGreater(delta['x'], alignment.POLICY['max_arrival_distance_m'])
        worst = pending['selection']['selected_pose']['position']['x']-(delta['x']-.012)
        self.assertAlmostEqual(worst, .768)

    def test_tiny_both_axis_goals_have_meaningful_distance_and_stay_in_gate(self):
        for x, y in ((.779, 0.), (.421, 0.), (.6, .379), (.6, -.379), (.779, .379)):
            pending = selection(x=x, y=y)
            delta = alignment.displacement(pending)
            self.assertLessEqual(math.hypot(*delta.values()), .05)
            projected = copy.deepcopy(pending['selection']['selected_pose'])
            for axis in 'xy':
                projected['position'][axis] -= delta[axis]
                if delta[axis]:
                    self.assertGreater(abs(delta[axis]), .012)
            sps.validate_position(projected)

    def test_z_and_excessive_xy_requests_are_not_planar_recoverable(self):
        for pending in (selection(z=0.), selection(z=1.5), selection(x=.821),
                        selection(x=.82, y=.395), selection(x=.1), selection(y=1.)):
            with self.subTest(pending=pending), self.assertRaises(ValueError):
                alignment.displacement(pending)
        self.assertAlmostEqual(alignment.displacement(selection(x=.82))['x'], .05)

    def test_base_delta_rotates_into_map_without_changing_final_yaw(self):
        reference = dict(x=1., y=2., yaw=math.pi/2)
        target = alignment.target(reference, dict(x=.02, y=-.01))
        self.assertAlmostEqual(target['point_x'], 1.01)
        self.assertAlmostEqual(target['point_y'], 2.02)
        self.assertEqual(target['point_yaw'], reference['yaw'])

    def test_comparison_transform_does_not_rewrite_pickup_measurement(self):
        previous = selection(x=.7909)
        current = selection(stamp=100_100_000_000, x=.77)
        original = copy.deepcopy((previous, current))
        first = alignment.in_map(previous, dict(x=1., y=2., yaw=0.))
        second = alignment.in_map(current, dict(x=1.0209, y=2., yaw=0.))
        self.assertAlmostEqual(validate_pair(first, second)['translation_m'], 0.)
        self.assertEqual((previous, current), original)


class ArrivalAndTimeTests(unittest.TestCase):
    def test_arrival_two_stable_new_measurements_twelve_mm_two_degrees(self):
        target = dict(point_x=0., point_y=0., point_yaw=0.)
        rows = [dict(x=.012, y=0., yaw=math.radians(2.))]*2
        result = alignment.validate_arrival(rows, target)
        self.assertEqual(result[0]['distance_tolerance_m'], .012)
        for x, yaw in ((.012000001, 0.), (0., math.radians(2.000001))):
            with self.subTest(x=x, yaw=yaw), self.assertRaisesRegex(ValueError, 'ARRIVAL_NOT_CONFIRMED'):
                alignment.validate_arrival([dict(x=x, y=0., yaw=yaw)]*2, target)

    def test_arrival_rejects_count_bad_numbers_and_base_instability(self):
        target = dict(point_x=0., point_y=0., point_yaw=0.)
        good = dict(x=0., y=0., yaw=0.)
        for rows in ([], [good], [good]*3, [dict(good, x=math.nan)]*2, [dict(good, x=True)]*2):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                alignment.validate_arrival(rows, target)
        with self.assertRaisesRegex(ValueError, 'BASE_UNSTABLE'):
            alignment.validate_arrival([dict(good, x=-.004), dict(good, x=.004)], target)

    def test_arrival_yaw_uses_shortest_wrap(self):
        rows = [dict(x=0., y=0., yaw=-math.pi+math.radians(.1))]*2
        result = alignment.validate_arrival(rows, dict(point_x=0., point_y=0., point_yaw=math.pi))
        self.assertAlmostEqual(result[0]['yaw_error_deg'], .1)

    def test_image_pairs_use_near_source_times_despite_processing_delay(self):
        history = [dict(x=1., y=2., yaw=0., stamp_ns=stamp) for stamp in
                   (99_900_000_000, 100_100_000_000, 101_400_000_000, 101_500_000_000)]
        result = alignment.match_pose_time(selection(), history)
        self.assertEqual(result['max_delta_ns'], 100_000_000)
        self.assertEqual([r['stamp_ns'] for r in result['poses']], [99_900_000_000, 100_100_000_000])

    def test_time_pairing_rejects_missing_far_duplicate_or_regressing_samples(self):
        for stamps in ([], [100_000_000_000], [98_000_000_000, 98_100_000_000],
                       [99_499_999_999, 100_500_000_001], [100_000_000_000]*2,
                       [100_100_000_000, 100_000_000_000]):
            with self.subTest(stamps=stamps), self.assertRaises(ValueError):
                alignment.match_pose_time(selection(), [dict(x=1., y=2., yaw=0., stamp_ns=s) for s in stamps])

    def test_history_cannot_hide_intermediate_motion_by_returning_to_origin(self):
        history = [dict(x=x, y=2., yaw=0., stamp_ns=stamp) for x, stamp in
                   ((1., 99_900_000_000), (1.006, 100_000_000_000), (1., 100_100_000_000))]
        with self.assertRaisesRegex(ValueError, 'BASE_UNSTABLE'):
            alignment.match_pose_time(selection(), history)


class AssociationTests(unittest.TestCase):
    def observation(self, *, x=.60, stamp=100_000_000_000, base_x=1.):
        return (selection(stamp=stamp, x=x), selection(stamp=stamp+100_000_000, x=x+.01),
                base_report(stamp-100_000_000, x=base_x), base_report(stamp+300_000_000, x=base_x))

    def test_two_coherent_poses_are_averaged_for_comparison_only(self):
        data = self.observation()
        original = copy.deepcopy(data)
        result = alignment.association_observation(*data)
        self.assertAlmostEqual(result['observation']['selection']['selected_pose']['position']['x'], 1.605)
        self.assertTrue(result['comparison_only'])
        self.assertEqual(result['image_stamps_ns'], [100_000_000_000, 100_100_000_000])
        self.assertEqual(data, original)

    def test_equivalent_quaternion_signs_are_averaged_correctly(self):
        data = self.observation()
        data[1]['selection']['selected_pose']['orientation']['w'] = -1.
        result = alignment.association_observation(*data)
        self.assertAlmostEqual(result['observation']['selection']['selected_pose']['orientation']['w'], 1.)

    def test_box_matches_across_chassis_motion_in_local_odom(self):
        previous = alignment.association_observation(*self.observation())
        current = alignment.association_observation(*self.observation(x=.57, stamp=101_000_000_000, base_x=1.03))
        comparison = alignment.validate_association(previous, current)
        self.assertAlmostEqual(comparison['translation_m'], 0.)
        self.assertEqual(comparison['max_translation_m'], .02)
        self.assertEqual(comparison['max_rotation_deg'], 3.)

    def test_averaging_cannot_hide_inconsistent_pair(self):
        data = self.observation()
        data[1]['selection']['selected_pose']['position']['x'] += .02
        with self.assertRaises(ValueError):
            alignment.association_observation(*data)

    def test_different_box_translation_rotation_or_odom_frame_rejected(self):
        previous = alignment.association_observation(*self.observation())
        for kind in ('translation', 'rotation', 'frame'):
            current = copy.deepcopy(previous)
            current['observation']['stamp_ns'] += 1
            if kind == 'translation':
                current['observation']['selection']['selected_pose']['position']['x'] += .020001
            elif kind == 'rotation':
                yaw = math.radians(3.001)
                current['observation']['selection']['selected_pose']['orientation'].update(z=math.sin(yaw/2), w=math.cos(yaw/2))
            else:
                current['frames']['frame_id'] = 'reset_odom'
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                alignment.validate_association(previous, current)
        with self.assertRaisesRegex(ValueError, 'ASSOCIATION_REQUIRED'):
            alignment.validate_association(None, None)

    def test_odom_evidence_requires_fresh_stationary_unique_publisher_and_valid_frames(self):
        changes = (lambda r: r.update(publishers=2), lambda r: r.update(publishers=True),
                   lambda r: r.update(stationary=False), lambda r: r['samples'].pop(),
                   lambda r: r.update(completed_ns=1),
                   lambda r: r['samples'][1].update(header=copy.deepcopy(r['samples'][0]['header'])),
                   lambda r: r['samples'][1]['twist']['twist']['linear'].update(x=.003001),
                   lambda r: r['samples'][1].update(child_frame_id='other'),
                   lambda r: [s.update(child_frame_id='camera_frame') for s in r['samples']],
                   lambda r: r['samples'][1]['pose']['pose']['position'].update(x=1.006))
        for mutate in changes:
            data = list(self.observation())
            mutate(data[3])
            with self.subTest(mutate=mutate), self.assertRaises((ValueError, KeyError)):
                alignment.association_observation(*data)

    def test_odom_must_bracket_images_in_same_stationary_frame(self):
        for kind in ('bracket', 'frame', 'moving', 'stale'):
            first, second, before, after = self.observation()
            if kind == 'bracket':
                first['stamp_ns'] = before['completed_ns']-1
            elif kind == 'frame':
                for row in after['samples']:
                    row['header']['frame_id'] = 'reset_odom'
            elif kind == 'moving':
                for row in after['samples']:
                    row['pose']['pose']['position']['x'] += .006
            else:
                after['completed_ns'] += 500_000_001
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                alignment.association_observation(first, second, before, after)


class PostureTests(unittest.TestCase):
    def report(self, *, body=0., head=-.43):
        ids = (1001, 1002, 2001, 2002, 2003, 3001, 11001, 11002, 11003, 11004,
               *range(4001, 4008), *range(5001, 5008))
        return dict(actuator=[dict(act_item=[dict(id=i, position=head if i == 1002 else body) for i in ids])]*2)

    def test_preparation_requires_body_home_and_observation_requires_lowered_head(self):
        alignment.pickup_posture(self.report(head=0.), observation=False)
        alignment.pickup_posture(self.report())
        for report in (self.report(body=.03), self.report(head=0.)):
            with self.subTest(report=report), self.assertRaisesRegex(ValueError, 'POSTURE_REQUIRED'):
                alignment.pickup_posture(report)


if __name__ == '__main__':
    unittest.main()
