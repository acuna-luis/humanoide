"""Synthetic guard regressions only: no ROS imports, connections or commands."""
import json
import math
from pathlib import Path
import unittest

from scripts.box_handling import scenario1_nav_correction as correction


NS = 1_000_000_000
START = 100 * NS


def spec(attempt=1, x=.03, yaw=0.):
    return correction.make_spec({'point_x': 0., 'point_y': 0., 'point_yaw': 0.},
                                {'x': x, 'y': 0., 'yaw': yaw, 'stamp_ns': START - 1}, attempt)


def sample(kind, stamp_ns, *, x=None, y=0., yaw=0., linear=0., angular=0.):
    if x is None:
        x = .03 if kind == 'map' else 1000.
    pose = {'position': {'x': x, 'y': y, 'z': 0.},
            'orientation': {'x': 0., 'y': 0., 'z': math.sin(yaw / 2), 'w': math.cos(yaw / 2)}}
    result = {'header': {'stamp': {'sec': stamp_ns // NS, 'nanosec': stamp_ns % NS},
                         'frame_id': 'map' if kind == 'map' else 'unit_odom'},
              'pose': pose}
    if kind == 'odom':
        result.update(child_frame_id='robot_base', pose={'pose': pose},
                      twist={'twist': {'linear': {'x': linear, 'y': 0., 'z': 0.},
                                       'angular': {'x': 0., 'y': 0., 'z': angular}}})
    return result


def warm(guard=None, yaw=0.):
    guard = guard or correction.Guard(spec(yaw=yaw), requested_ns=START)
    for offset in (.1, .2):
        when = START + int(offset * NS)
        guard.add('map', sample('map', when, yaw=yaw), when)
        guard.add('odom', sample('odom', when), when)
    return guard


def armed(yaw=0.):
    guard = warm(yaw=yaw)
    guard.arm(START + 200_000_000)
    return guard


def tick(guard, offset, *, map_x=.03, map_y=0., map_yaw=0., odom_x=1000., odom_yaw=0., linear=0., angular=0.):
    when = START + int(offset * NS)
    guard.add('map', sample('map', when, x=map_x, y=map_y, yaw=map_yaw), when)
    guard.add('odom', sample('odom', when, x=odom_x, yaw=odom_yaw, linear=linear, angular=angular), when)
    return guard.check(when)


class SpecificationTest(unittest.TestCase):
    def goal(self):
        return {'command': 'navigation_start', 'arg_json': json.dumps({'target_point': {
            'map_name': 'utars_nav_map', 'mode': 'free_nav', **spec()['target']}})}

    def test_normalizes_without_mutating_and_policy_is_immutable(self):
        original = spec()
        normalized = correction.validate_spec(original, self.goal())
        normalized['reference']['x'] = 123.
        self.assertEqual(original['reference']['x'], .03)
        with self.assertRaises(TypeError):
            correction.POLICY['max_corrections'] = 9

    def test_strict_schema_and_attempts(self):
        for key, value in [('version', True), ('version', 2), ('point', 'put1'),
                           ('attempt', 0), ('attempt', 3), ('attempt', True), ('policy', {})]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                candidate = spec()
                candidate[key] = value
                correction.validate_spec(candidate)
        for key in ('target', 'reference'):
            candidate = spec()
            candidate[key]['extra'] = 1
            with self.assertRaises(ValueError):
                correction.validate_spec(candidate)

    def test_initial_envelope_inclusive(self):
        correction.validate_spec(spec(x=.05, yaw=math.radians(5)))
        for x, yaw in ((.050001, 0.), (.03, math.radians(5.001))):
            with self.subTest(x=x, yaw=yaw), self.assertRaisesRegex(ValueError, 'initial'):
                spec(x=x, yaw=yaw)

    def test_finite_coordinates_and_integer_reference_stamp_required(self):
        for section, key in (('target', 'point_x'), ('reference', 'x')):
            for bad in (float('nan'), float('inf'), True, '0'):
                candidate = spec()
                candidate[section][key] = bad
                with self.subTest(section=section, bad=bad), self.assertRaises(ValueError):
                    correction.validate_spec(candidate)
        for bad in (0, -1, True, 100.):
            candidate = spec()
            candidate['reference']['stamp_ns'] = bad
            with self.assertRaises(ValueError):
                correction.validate_spec(candidate)

    def test_only_same_explicit_native_goal_is_accepted(self):
        for field, value in (('mode', 'logo_nav'), ('map_name', 'other'), ('point_x', .001), ('point_yaw', .001)):
            goal = self.goal()
            args = json.loads(goal['arg_json'])
            args['target_point'][field] = value
            goal['arg_json'] = json.dumps(args)
            with self.subTest(field=field), self.assertRaises(ValueError):
                correction.validate_spec(spec(), goal)
        for goal in ({}, {'command': 'navigation_stop', 'arg_json': '{}'},
                     {'command': 'navigation_start', 'arg_json': 'bad'},
                     {'command': 'navigation_start', 'arg_json': '[]'}):
            with self.assertRaises(ValueError):
                correction.validate_spec(spec(), goal)


class PreparationTest(unittest.TestCase):
    def test_two_samples_from_both_streams_are_required(self):
        guard = correction.Guard(spec(), requested_ns=START)
        self.assertFalse(guard.ready(START))
        for kind in ('map', 'odom'):
            guard.add(kind, sample(kind, START + 1), START + 1)
        self.assertFalse(guard.ready(START + 1))
        for kind in ('map', 'odom'):
            guard.add(kind, sample(kind, START + 2), START + 2)
        self.assertTrue(guard.ready(START + 2))
        guard.arm(START + 2)
        self.assertTrue(guard.check(START + 2)['armed'])
        self.assertFalse(guard.summary()['arrival_verified'])

    def test_premature_arm_and_double_arm_fail_sticky(self):
        for guard in (correction.Guard(spec(), START), armed()):
            with self.assertRaises(ValueError):
                guard.arm(START + 300_000_000)
            self.assertIsNotNone(guard.summary()['failure'])

    def test_stale_first_sample_cannot_satisfy_two_fresh_samples(self):
        guard = warm()
        with self.assertRaisesRegex(ValueError, 'stale'):
            guard.ready(START + 650_000_001)

    def test_reference_must_match_new_pose(self):
        for x, yaw in ((.035001, 0.), (.03, math.radians(1.001))):
            guard = correction.Guard(spec(), START)
            with self.subTest(x=x, yaw=yaw), self.assertRaisesRegex(ValueError, 'reference differs'):
                guard.add('map', sample('map', START+1, x=x, yaw=yaw), START+1)

    def test_fresh_initial_pose_must_also_be_inside_envelope(self):
        guard = correction.Guard(spec(x=.05), START)
        with self.assertRaisesRegex(ValueError, 'initial envelope'):
            guard.add('map', sample('map', START+1, x=.051), START+1)

    def test_stationary_preparation_uses_all_velocity_components(self):
        for axis, field, value in (('x', 'linear', .003001), ('z', 'linear', .003001),
                                   ('y', 'angular', .010001)):
            guard = correction.Guard(spec(), START)
            payload = sample('odom', START+1)
            payload['twist']['twist'][field][axis] = value
            with self.subTest(axis=axis, field=field), self.assertRaisesRegex(ValueError, 'velocity'):
                guard.add('odom', payload, START+1)

    def test_frame_ids_are_recorded_without_assuming_map_equals_odom(self):
        guard = armed()
        report = tick(guard, .3, map_x=.027, odom_x=999.997, linear=.03)
        self.assertEqual(report['frames']['odom'], {'frame_id': 'unit_odom', 'child_frame_id': 'robot_base'})
        self.assertAlmostEqual(report['path_m']['map'], .003)
        self.assertAlmostEqual(report['path_m']['odom'], .003)
        json.dumps(report, allow_nan=False)


class MalformedTelemetryTest(unittest.TestCase):
    def test_rejects_stale_future_frozen_and_unrequested_stamps(self):
        cases = [(START+2, START+1), (START+1, START+NS), (START+1, START-1)]
        for stamp, received in cases:
            guard = correction.Guard(spec(), START)
            with self.subTest(stamp=stamp, received=received), self.assertRaises(ValueError):
                guard.add('map', sample('map', stamp), received)
        guard = warm()
        with self.assertRaisesRegex(ValueError, 'advance'):
            guard.add('map', sample('map', START+200_000_000), START+300_000_000)

    def test_persistent_reader_backlog_never_counts_as_new_telemetry(self):
        guard = correction.Guard(spec(attempt=2), START)
        for offset in (-NS, 0):
            for kind in ('map', 'odom'):
                guard.add(kind, sample(kind, START+offset), START+1)
        self.assertFalse(guard.ready(START+1))
        self.assertEqual(guard.summary()['samples'], {'map': 0, 'odom': 0})
        self.assertEqual(guard.summary()['frames'], {})
        for kind in ('map', 'odom'):
            guard.add(kind, sample(kind, START+2), START+2)
        self.assertFalse(guard.ready(START+2))
        for kind in ('map', 'odom'):
            guard.add(kind, sample(kind, START+3), START+3)
        self.assertTrue(guard.ready(START+3))

    def test_pre_request_sample_after_first_new_sample_is_a_failure(self):
        guard = correction.Guard(spec(), START)
        guard.add('map', sample('map', START+1), START+1)
        with self.assertRaisesRegex(ValueError, 'newer than request'):
            guard.add('map', sample('map', START), START+2)

    def test_invalid_quaternion_position_stamp_and_frames(self):
        changes = [lambda p: p['header'].update(frame_id='odom'),
                   lambda p: p['header']['stamp'].update(nanosec=NS),
                   lambda p: p['header']['stamp'].update(sec=True),
                   lambda p: p['pose']['position'].update(x=float('nan')),
                   lambda p: p['pose']['orientation'].update(w=0.),
                   lambda p: p['pose']['orientation'].update(w=float('inf'))]
        for mutate in changes:
            guard = correction.Guard(spec(), START)
            payload = sample('map', START+1)
            mutate(payload)
            with self.assertRaises(ValueError):
                guard.add('map', payload, START+1)
        for field in ('frame_id', 'child_frame_id'):
            for value in ('', 'new_frame'):
                guard = warm()
                payload = sample('odom', START+300_000_000)
                (payload['header'] if field == 'frame_id' else payload)[field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    guard.add('odom', payload, START+300_000_000)

    def test_malformed_payload_latches_failure(self):
        for payload in ('bad JSON', '[]', {}, {'header': None}):
            guard = correction.Guard(spec(), START)
            with self.assertRaises(ValueError) as raised:
                guard.add('map', payload, START+1)
            with self.assertRaisesRegex(ValueError, '.*') as repeated:
                guard.ready(START+2)
            self.assertEqual(str(raised.exception), str(repeated.exception))

    def test_native_json_payload_is_accepted(self):
        guard = correction.Guard(spec(), START)
        guard.add('map', json.dumps(sample('map', START+1)), START+1)
        self.assertEqual(guard.summary()['samples']['map'], 1)

    def test_clock_regression_and_check_before_arm_fail(self):
        guard = warm()
        guard.ready(START+200_000_000)
        with self.assertRaisesRegex(ValueError, 'backwards'):
            guard.ready(START+100_000_000)
        with self.assertRaisesRegex(ValueError, 'not been armed'):
            warm().check(START+200_000_000)


class ActiveLimitsTest(unittest.TestCase):
    def test_angular_violation_keeps_exact_sample_and_active_phase(self):
        guard = armed()
        when = START + 300_000_000
        payload = sample('odom', when, linear=.007283258968572332,
                         angular=-.60143092940150614)
        with self.assertRaisesRegex(ValueError, r'active limit.*angular=0\.601430929'):
            guard.add('odom', payload, when + 1)
        report = guard.summary()
        violation = report['velocity_violation']
        self.assertEqual(violation['phase'], 'active')
        self.assertEqual(violation['exceeded'], ['angular'])
        self.assertEqual(violation['stamp_ns'], when)
        self.assertEqual(violation['received_ns'], when + 1)
        self.assertEqual(violation['angular_limit_rad_s'], .60)
        self.assertEqual(violation['sample']['twist']['twist']['angular']['z'], -.60143092940150614)
        self.assertLess(report['last_stamp_ns']['odom'], when)
        payload['twist']['twist']['angular']['z'] = 0.
        violation['sample']['twist']['twist']['angular']['z'] = 123.
        self.assertEqual(guard.summary()['velocity_violation']['sample']['twist']['twist']['angular']['z'],
                         -.60143092940150614)

    def test_velocity_report_distinguishes_preparation_and_settling(self):
        for phase, guard, speed, limit in (('preparing', warm(), .011, .01),
                                          ('settling', armed(), .601, .60)):
            if phase == 'settling':
                guard.begin_settle(START + 200_000_000)
            payload = sample('odom', START + 300_000_000, angular=speed)
            with self.subTest(phase=phase), self.assertRaisesRegex(ValueError, phase + ' limit'):
                guard.add('odom', json.dumps(payload), START + 300_000_001)
            self.assertEqual(guard.summary()['velocity_violation']['angular_limit_rad_s'], limit)
            self.assertEqual(guard.summary()['velocity_violation']['sample'], payload)

    def test_active_velocity_limits_are_inclusive(self):
        guard = armed()
        report = tick(guard, .3, linear=.1, angular=.60)
        self.assertIsNone(report['velocity_violation'])
        with self.assertRaisesRegex(ValueError, 'velocity'):
            tick(guard, .4, angular=.600001)

    def test_source_and_receive_watchdog_fail_without_new_samples(self):
        guard = armed()
        with self.assertRaisesRegex(ValueError, 'stale'):
            guard.check(START+700_000_001)

    def test_speed_limits_are_checked_before_accepting_sample(self):
        for kwargs in ({'linear': .100001}, {'angular': .600001}):
            guard = armed()
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(ValueError, 'velocity'):
                tick(guard, .3, **kwargs)
            with self.assertRaisesRegex(ValueError, 'velocity'):
                guard.add('odom', sample('odom', START+400_000_000), START+400_000_000)

    def test_distance_worsening_is_relative_to_best_so_far(self):
        guard = armed()
        tick(guard, .3, map_x=.024)
        with self.assertRaisesRegex(ValueError, 'worsened'):
            tick(guard, .4, map_x=.039001)

    def test_independent_odometry_excursion_and_yaw_limit(self):
        for kwargs, message in (({'odom_x': 1000.080001}, 'excursion'),
                                ({'odom_yaw': math.radians(15.001)}, 'yaw excursion')):
            guard = armed()
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(ValueError, message):
                tick(guard, .3, **kwargs)

    def test_accumulated_path_rejects_back_and_forth_motion(self):
        guard = armed()
        tick(guard, .3, odom_x=1000.04)
        tick(guard, .4, odom_x=1000.)
        tick(guard, .5, odom_x=1000.04)
        with self.assertRaisesRegex(ValueError, 'path budget'):
            tick(guard, .6, odom_x=1000.03)

    def test_no_progress_fails_despite_continuing_fresh_samples(self):
        guard = armed()
        for index in range(3, 42):
            tick(guard, index / 10)
        with self.assertRaisesRegex(ValueError, 'no significant progress'):
            tick(guard, 4.2)

    def test_significant_distance_or_yaw_progress_resets_watchdog(self):
        for progress in ({'map_x': .027}, {'map_yaw': math.radians(3.7)}):
            guard = armed(yaw=math.radians(4.))
            for index in range(3, 42):
                tick(guard, index/10, map_yaw=math.radians(4.))
            options = {'map_x': .03, 'map_yaw': math.radians(4.)}
            options.update(progress)
            tick(guard, 4.2, **options)

    def test_yaw_wrap_uses_shortest_angle(self):
        initial = spec()
        initial['target']['point_yaw'] = math.pi
        initial['reference']['yaw'] = -math.pi + math.radians(.2)
        guard = correction.Guard(initial, START)
        for offset in (.1, .2):
            when = START + int(offset*NS)
            guard.add('map', sample('map', when, yaw=math.pi-math.radians(.2)), when)
            guard.add('odom', sample('odom', when, yaw=math.pi-math.radians(.2)), when)
        guard.arm(START+200_000_000)
        tick(guard, .3, map_yaw=-math.pi+math.radians(.2), odom_yaw=-math.pi+math.radians(.2))
        self.assertAlmostEqual(guard.summary()['max_yaw_excursion_deg']['odom'], .4)

    def test_arrival_still_requires_parent_two_sample_confirmation(self):
        guard = armed()
        for index in range(3, 60):
            report = tick(guard, index/10, map_x=.019)
        self.assertFalse(report['arrival_verified'])
        self.assertIsNone(report['failure'])

    def test_action_deadline_even_if_already_within_tolerance(self):
        guard = armed()
        for index in range(3, 303):
            tick(guard, index/10, map_x=.019)
        with self.assertRaisesRegex(ValueError, 'time budget'):
            tick(guard, 30.3, map_x=.019)


class NativeManeuverTest(unittest.TestCase):
    def lateral_guard(self):
        target = dict(point_x=.016656, point_y=.023698, point_yaw=math.radians(.351558))
        reference = dict(x=0., y=0., yaw=0., stamp_ns=START-1)
        guard = correction.Guard(correction.make_spec(target, reference, 1), START)
        for offset in (.1, .2):
            when = START+round(offset*NS)
            guard.add('map', sample('map', when, x=0.), when)
            guard.add('odom', sample('odom', when), when)
        guard.arm(START+200_000_000)
        return guard

    def lateral_tick(self, guard, offset, x=0., y=0., yaw_deg=0., angular=0., linear=0.):
        when = START+round(offset*NS)
        for kind in ('map', 'odom'):
            guard.add(kind, sample(kind, when, x=x+(1000. if kind == 'odom' else 0.), y=y,
                                  yaw=math.radians(yaw_deg), angular=angular, linear=linear), when)
        return guard.check(when)

    def test_observed_angular_peak_and_documented_arc_ceiling_are_permitted(self):
        guard = armed()
        for offset, angular in ((.3, .26143092940150614), (.4, .5), (.5, .6)):
            self.assertIsNone(tick(guard, offset, angular=angular)['failure'])
        with self.assertRaisesRegex(ValueError, 'velocity'):
            tick(guard, .6, angular=.600001)

    def test_transient_reverse_is_bounded_against_best_distance(self):
        guard = armed()
        tick(guard, .3, map_x=.037503, odom_x=1000.007503, linear=.04)
        tick(guard, .4, map_x=.045, odom_x=1000.015, linear=.04)
        with self.assertRaisesRegex(ValueError, 'worsened'):
            tick(guard, .5, map_x=.045001, odom_x=1000.015001)

    def test_final_turn_allowance_requires_two_close_fresh_poses_and_little_translation(self):
        guard = armed()
        tick(guard, .3, map_x=.019, angular=.5)
        # Only one close pose cannot unlock the faster final turn.
        payload = sample('odom', START+310_000_000, angular=.61)
        self.assertEqual(guard.angular_limit(correction._sample('odom', payload, START+310_000_000)), .6)
        tick(guard, .4, map_x=.019, linear=.02, angular=1.2)
        self.assertIsNone(guard.summary()['velocity_violation'])
        for when, linear, expected in ((START+410_000_000, .020001, .6),
                                      (START+910_000_000, 0., .6)):
            payload = sample('odom', when, linear=linear)
            self.assertEqual(guard.angular_limit(correction._sample('odom', payload, when)), expected)
        with self.assertRaisesRegex(ValueError, 'velocity'):
            tick(guard, .5, map_x=.019, angular=1.200001)

    def test_exiting_position_window_restores_approach_speed_limit(self):
        guard = armed()
        tick(guard, .3, map_x=.019)
        tick(guard, .4, map_x=.019, angular=1.1)
        with self.assertRaisesRegex(ValueError, r'limit=0\.600000000'):
            tick(guard, .5, map_x=.021, angular=.61)

    def test_lateral_goal_can_turn_approach_and_turn_back_without_false_stall(self):
        guard = self.lateral_guard()
        self.assertAlmostEqual(guard.summary()['yaw_limits']['excursion_deg'], 125.15, places=1)
        # Six seconds of useful initial rotation, with no improvement in XY or final yaw.
        for index in range(3, 63):
            self.lateral_tick(guard, index/10, yaw_deg=(index-2)*55/60, angular=.16)
        report = self.lateral_tick(guard, 6.3, x=.011, y=.016, yaw_deg=55., linear=.03)
        self.assertEqual(report['progress_phase'], 'final_alignment')
        for index in range(64, 124):
            self.lateral_tick(guard, index/10, x=.011, y=.016,
                              yaw_deg=55.-(index-63)*54.648442/60, angular=.16)
        self.lateral_tick(guard, 12.4, x=.011, y=.016, yaw_deg=.351558)
        guard.begin_settle(START+12_400_000_000)
        for index in (125, 126):
            report = self.lateral_tick(guard, index/10, x=.011, y=.016, yaw_deg=.351558)
        self.assertTrue(guard.settled(START+12_600_000_000))
        self.assertLess(report['distance_m'], .02)
        self.assertLess(report['yaw_error_deg'], 2.)
        self.assertFalse(report['arrival_verified'])  # Supervisor still validates its own new pair.

    def test_wrong_way_rotation_does_not_count_as_progress(self):
        guard = self.lateral_guard()
        for index in range(3, 42):
            self.lateral_tick(guard, index/10, yaw_deg=-(index-2)*.4, angular=.07)
        with self.assertRaisesRegex(ValueError, 'no significant progress'):
            self.lateral_tick(guard, 4.2, yaw_deg=-16., angular=.07)

    def test_geometry_limits_rotation_and_accumulated_oscillation(self):
        guard = self.lateral_guard()
        with self.assertRaisesRegex(ValueError, 'yaw excursion'):
            self.lateral_tick(guard, .3, yaw_deg=guard.summary()['yaw_limits']['excursion_deg']+.001)
        # Small repeated oscillations inside excursion still consume total turn budget.
        guard = self.lateral_guard()
        for index, angle in enumerate((50., 0., 50., 0., 50.), 3):
            self.lateral_tick(guard, index/10, yaw_deg=angle)
        with self.assertRaisesRegex(ValueError, 'accumulated yaw'):
            self.lateral_tick(guard, .8, yaw_deg=0.)

    def test_tangent_arc_for_observed_residual_then_final_rotation_is_allowed(self):
        guard = self.lateral_guard()
        target = guard.spec['target']
        bearing = math.atan2(target['point_y'], target['point_x'])
        radius = math.hypot(target['point_x'], target['point_y'])/(2*math.sin(bearing))
        for index in range(1, 61):
            angle = 2*bearing*index/60
            self.lateral_tick(guard, .2+index/10, x=radius*math.sin(angle),
                              y=radius*(1-math.cos(angle)), yaw_deg=math.degrees(angle),
                              angular=2*bearing/6, linear=radius*2*bearing/6)
        # A slower final return must count as progress even before beating the
        # yaw recorded on first crossing 2 cm halfway through the initial arc.
        for index in range(1, 121):
            yaw = 2*bearing+(target['point_yaw']-2*bearing)*index/120
            report = self.lateral_tick(guard, 6.2+index/10,
                x=target['point_x'], y=target['point_y'], yaw_deg=math.degrees(yaw), angular=.16)
        self.assertLess(report['path_m']['map'], .04)
        self.assertGreater(report['max_yaw_excursion_deg']['map'], 100.)
        self.assertLess(report['yaw_error_deg'], .001)
        self.assertIsNone(report['failure'])

    def test_future_close_poses_do_not_authorize_earlier_fast_odometry(self):
        guard = armed()
        for offset in (.4, .5):
            when = START+round(offset*NS)
            guard.add('map', sample('map', when, x=.019), when)
        with self.assertRaisesRegex(ValueError, r'limit=0\.600000000'):
            guard.add('odom', sample('odom', START+300_000_000, angular=1.), START+500_000_000)

    def test_two_causal_close_poses_allow_delayed_odometry_despite_newer_map_pose(self):
        guard = armed()
        for offset in (.3, .4, .5):
            when = START+round(offset*NS)
            guard.add('map', sample('map', when, x=.019), when)
        guard.add('odom', sample('odom', START+450_000_000, angular=1.), START+500_000_000)
        self.assertIsNone(guard.check(START+500_000_000)['failure'])

    def test_excursion_remains_enforced_past_pi_with_unwrapped_heading(self):
        target = dict(point_x=0., point_y=.03, point_yaw=0.)
        reference = dict(x=0., y=0., yaw=0., stamp_ns=START-1)
        guard = correction.Guard(correction.make_spec(target, reference, 1), START)
        for offset in (.1, .2):
            when = START+round(offset*NS)
            guard.add('map', sample('map', when, x=0.), when)
            guard.add('odom', sample('odom', when), when)
        guard.arm(START+200_000_000)
        for index, yaw in enumerate((90., 179., -170.), 3):
            self.lateral_tick(guard, index/10, yaw_deg=yaw)
        self.assertAlmostEqual(guard.summary()['max_yaw_excursion_deg']['map'], 190.)
        with self.assertRaisesRegex(ValueError, 'yaw excursion'):
            self.lateral_tick(guard, .6, yaw_deg=-160.)

    def test_repeated_position_window_crossings_cannot_reset_progress_timer(self):
        guard = armed()
        tick(guard, .3, map_x=.019)
        for index in range(4, 43):
            tick(guard, index/10, map_x=.021 if index%2==0 else .019)
        with self.assertRaisesRegex(ValueError, 'no significant progress'):
            tick(guard, 4.3, map_x=.021)


class TerminalSettlingTest(unittest.TestCase):
    def machine(self):
        guard = armed()
        tick(guard, .3, map_x=.019)
        guard.begin_settle(START+300_000_000)
        return guard

    def test_success_requires_two_post_result_samples_from_both_streams(self):
        guard = self.machine()
        self.assertFalse(guard.settled(START+300_000_000))
        tick(guard, .4, map_x=.019)
        self.assertFalse(guard.settled(START+400_000_000))
        guard.add('map', sample('map', START+500_000_000, x=.019), START+500_000_000)
        self.assertFalse(guard.settled(START+500_000_000))
        guard.add('odom', sample('odom', START+500_000_000), START+500_000_000)
        self.assertTrue(guard.settled(START+500_000_000))
        summary = guard.summary()
        self.assertTrue(summary['settled'])
        self.assertEqual(summary['settled_ns'], START+500_000_000)
        self.assertFalse(summary['arrival_verified'])

    def test_delayed_pre_result_sources_never_satisfy_settling(self):
        guard = armed()
        guard.begin_settle(START+300_000_000)
        for offset in (250_000_000, 300_000_000):
            for kind in ('map', 'odom'):
                guard.add(kind, sample(kind, START+offset), START+offset+100_000_000)
        self.assertFalse(guard.settled(START+400_000_000))

    def test_deceleration_is_allowed_but_last_two_odometry_must_be_quiet(self):
        guard = self.machine()
        for offset, velocity in ((.4, .09), (.5, .02), (.6, .003)):
            tick(guard, offset, map_x=.019, linear=velocity)
            self.assertFalse(guard.settled(START+int(offset*NS)))
        tick(guard, .7, map_x=.019, linear=.003, angular=.01)
        self.assertTrue(guard.settled(START+700_000_000))

    def test_angular_motion_also_requires_two_quiet_samples(self):
        guard = self.machine()
        tick(guard, .4, map_x=.019, angular=.010001)
        tick(guard, .5, map_x=.019)
        self.assertFalse(guard.settled(START+500_000_000))
        tick(guard, .6, map_x=.019)
        self.assertTrue(guard.settled(START+600_000_000))

    def test_map_pair_must_be_stable_in_position_and_yaw(self):
        for kwargs in ({'map_x': .011}, {'map_x': .019, 'map_yaw': math.radians(1.001)}):
            guard = self.machine()
            tick(guard, .4, map_x=.019)
            tick(guard, .5, **kwargs)
            self.assertFalse(guard.settled(START+500_000_000))
            tick(guard, .6, **kwargs)
            self.assertTrue(guard.settled(START+600_000_000))

    def test_settling_timeout_does_not_reset_the_action_deadline(self):
        guard = self.machine()
        for index in range(4, 19):
            tick(guard, index/10, map_x=.019, linear=.02)
            self.assertFalse(guard.settled(START+int(index/10*NS)))
        with self.assertRaisesRegex(ValueError, 'settling time budget'):
            tick(guard, 1.9, map_x=.019, linear=.02)
        other = armed()
        for index in range(3, 302):
            tick(other, index/10, map_x=.019)
        other.begin_settle(START+30_100_000_000)
        with self.assertRaisesRegex(ValueError, 'action time budget'):
            tick(other, 30.3, map_x=.019)

    def test_active_guards_and_freshness_remain_in_force(self):
        guard = self.machine()
        with self.assertRaisesRegex(ValueError, 'velocity'):
            tick(guard, .4, map_x=.019, linear=.100001)
        other = self.machine()
        with self.assertRaisesRegex(ValueError, 'stale'):
            other.settled(START+800_000_001)

    def test_lifecycle_cannot_reset_or_skip_terminal_observation(self):
        guard = self.machine()
        with self.assertRaisesRegex(ValueError, 'already started'):
            guard.begin_settle(START+300_000_000)
        with self.assertRaisesRegex(ValueError, 'has not started'):
            armed().settled(START+200_000_000)
        with self.assertRaisesRegex(ValueError, 'not been armed'):
            warm().begin_settle(START+200_000_000)


class PickupRecoveryTest(unittest.TestCase):
    def machine(self, distance=.03, point='box_pickup'):
        candidate = spec(x=distance)
        candidate['point'] = point
        guard = correction.Guard(candidate, START)
        for offset in (.1, .2):
            when = START + int(offset * NS)
            guard.add('map', sample('map', when, x=distance), when)
            guard.add('odom', sample('odom', when), when)
        guard.arm(START + 200_000_000)
        return guard

    def recover(self):
        guard = self.machine()
        tick(guard, .4, map_x=.036)
        tick(guard, .7, map_x=.033)
        return guard

    def test_recorded_distance_trace_survives_initial_recovery_without_claiming_arrival(self):
        fixture = json.loads((Path(__file__).parent / 'fixtures' /
                              'box_alignment_progress_20261002.json').read_text())
        guard = self.machine(fixture['initial_distance_m'])
        for row in fixture['samples']:
            report = tick(guard, .2 + row['elapsed_s'], map_x=row['distance_m'],
                          odom_x=1000. + fixture['initial_distance_m'] - row['distance_m'])
        self.assertIsNotNone(report['pickup_recovery']['used_ns'])
        self.assertAlmostEqual(report['progress_distance_m'], fixture['initial_distance_m'])
        self.assertGreater(report['distance_m'], .005)
        self.assertFalse(report['arrival_verified'])
        self.assertFalse(report['settled'])
        # This is a projection of recorded distances, not archived raw poses.
        # Holding at the last position must still cancel four seconds after
        # that single recovery, without requiring a native terminal response.
        when = .2 + fixture['samples'][-1]['elapsed_s']
        deadline = (report['pickup_recovery']['used_ns'] - START) / NS + 4.
        while when + .1 < deadline:
            when += .1
            tick(guard, when, map_x=report['distance_m'])
        with self.assertRaisesRegex(ValueError, 'no significant progress'):
            tick(guard, deadline, map_x=report['distance_m'])

    def test_stationary_pickup_retains_four_second_watchdog(self):
        guard = self.machine()
        for index in range(3, 42):
            tick(guard, index / 10)
        with self.assertRaisesRegex(ValueError, 'no significant progress'):
            tick(guard, 4.2)
        self.assertIsNone(guard.summary()['pickup_recovery']['used_ns'])

    def test_away_motion_alone_does_not_renew_watchdog(self):
        guard = self.machine()
        for index in range(3, 42):
            tick(guard, index / 10, map_x=.03 + (index - 2) * .0001)
        with self.assertRaisesRegex(ValueError, 'no significant progress'):
            tick(guard, 4.2, map_x=.034)

    def test_repeated_retreats_cannot_renew_recovery(self):
        guard = self.recover()
        first = guard.summary()['pickup_recovery']['used_ns']
        for index in range(8, 47):
            tick(guard, index / 10, map_x=.036 if (index // 5) % 2 else .033)
        self.assertEqual(guard.summary()['progress_ns'], first)
        with self.assertRaisesRegex(ValueError, 'no significant progress'):
            tick(guard, 4.7, map_x=.033)

    def test_subthreshold_return_and_retreat_do_not_count(self):
        for peak, returned in ((.0319, .030), (.036, .0341)):
            with self.subTest(peak=peak, returned=returned):
                guard = self.machine()
                tick(guard, .4, map_x=peak)
                tick(guard, .7, map_x=returned)
                self.assertIsNone(guard.summary()['pickup_recovery']['used_ns'])

    def test_return_after_net_progress_is_not_initial_recovery(self):
        guard = self.machine()
        tick(guard, .3, map_x=.027)
        tick(guard, .4, map_x=.034)
        report = tick(guard, .7, map_x=.031)
        self.assertIsNone(report['pickup_recovery']['used_ns'])
        self.assertEqual(report['progress_ns'], START + 300_000_000)

    def test_get1_retains_previous_best_distance_watchdog(self):
        guard = self.machine(point='get1')
        for index in range(3, 42):
            tick(guard, index / 10, map_x=.036 if index < 20 else .033)
        with self.assertRaisesRegex(ValueError, 'no significant progress'):
            tick(guard, 4.2, map_x=.033)

    def test_worsening_speed_excursion_and_staleness_still_abort_after_recovery(self):
        cases = (({'map_x': .045001}, 'worsened'),
                 ({'linear': .100001}, 'velocity'),
                 ({'odom_x': 1000.080001}, 'excursion'))
        for options, reason in cases:
            with self.subTest(reason=reason), self.assertRaisesRegex(ValueError, reason):
                tick(self.recover(), .8, **options)
        guard = self.recover()
        with self.assertRaisesRegex(ValueError, 'stale'):
            guard.check(START + 1_200_000_001)

    def test_normal_net_progress_continues_after_recovery(self):
        guard = self.recover()
        report = tick(guard, .8, map_x=.027)
        self.assertEqual(report['progress_ns'], START + 800_000_000)
        self.assertAlmostEqual(report['progress_distance_m'], .027)
        self.assertEqual(report['pickup_recovery']['used_ns'], START + 700_000_000)


if __name__ == '__main__':
    unittest.main()
