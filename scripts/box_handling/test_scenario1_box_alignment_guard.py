"""Pickup-only guard extensions preserve existing GET1 limits and goal checks."""
import copy
import json
import unittest

from scripts.box_handling import scenario1_nav_correction as nav
from scripts.box_handling.test_scenario1_nav_correction import START, NS, sample


# Exact policy from pre-port blob 0c2d7c69497d6e53d2a6d0a307e4970421e929d9.
GET1_POLICY = dict(max_corrections=2, max_initial_distance_m=.05, max_initial_yaw_deg=5.,
    action_timeout_s=30., total_budget_s=70., max_excursion_m=.08, max_path_m=.12,
    max_worsening_m=.015, max_linear_speed_m_s=.10, max_approach_angular_speed_rad_s=.60,
    max_angular_speed_rad_s=1.20, alignment_linear_speed_m_s=.02, max_yaw_excursion_deg=195.,
    yaw_excursion_margin_deg=15., max_yaw_path_deg=400., source_age_s=.5, receive_age_s=.5,
    no_progress_s=4., settle_timeout_s=1.5)


def spec(point='box_pickup', attempt=1):
    return nav.make_spec(dict(point_x=0., point_y=0., point_yaw=0.),
        dict(x=.03, y=0., yaw=0., stamp_ns=START-1), attempt, point=point)


class AlignmentGuardTests(unittest.TestCase):
    def test_get1_policy_matches_baseline_exactly(self):
        self.assertEqual(dict(nav.POLICY), GET1_POLICY)
        with self.assertRaises(TypeError):
            nav.POLICY['max_corrections'] = 7

    def test_pickup_accepts_seven_but_get1_retains_two(self):
        for attempt in range(1, 8):
            self.assertEqual(nav.validate_spec(spec(attempt=attempt))['attempt'], attempt)
        for point, attempts in (('box_pickup', (0, 8, True, 1.)), ('get1', (0, 3, 7, True, 1.))):
            for attempt in attempts:
                with self.subTest(point=point, attempt=attempt), self.assertRaises(ValueError):
                    spec(point, attempt)
        self.assertEqual(spec('get1', 2)['attempt'], 2)

    def test_each_point_keeps_its_monitoring_threshold(self):
        pickup = nav.Guard(spec(), START)
        get1 = nav.Guard(spec('get1'), START)
        self.assertEqual(pickup.distance_tolerance_m, .005)
        self.assertEqual(get1.distance_tolerance_m, .02)
        self.assertEqual(pickup.summary()['point'], 'box_pickup')
        self.assertEqual(get1.summary()['point'], 'get1')

    def test_fast_final_turn_requires_pickup_within_five_mm_but_get1_twenty_mm(self):
        for point, distance, limit in (('box_pickup', .005, 1.2), ('box_pickup', .005001, .6),
                                       ('get1', .02, 1.2), ('get1', .020001, .6)):
            guard = nav.Guard(spec(point), START)
            for offset in (.1, .2):
                when = START+round(offset*NS)
                guard.add('map', sample('map', when), when)
                guard.add('odom', sample('odom', when), when)
            guard.arm(START+200_000_000)
            for offset in (.3, .4):
                when = START+round(offset*NS)
                guard.add('map', sample('map', when, x=distance), when)
                guard.add('odom', sample('odom', when), when)
            when = START+400_000_000
            value = nav._sample('odom', sample('odom', when, linear=.01), when)
            with self.subTest(point=point, distance=distance):
                self.assertEqual(guard.angular_limit(value), limit)

    def test_pickup_goal_must_match_measured_target_and_supported_map_mode(self):
        correction = spec()
        target = dict(correction['target'], map_name='utars_nav_map', mode='free_nav')
        good = dict(command='navigation_start', arg_json=json.dumps(dict(target_point=target)))
        self.assertEqual(nav.validate_spec(correction, good), correction)
        for key, value in (('point_x', .001), ('point_y', .001), ('point_yaw', .001),
                           ('map_name', 'other_map'), ('mode', 'logo_nav')):
            bad = dict(good, arg_json=json.dumps(dict(target_point=dict(target, **{key: value}))))
            with self.subTest(key=key), self.assertRaises(ValueError):
                nav.validate_spec(correction, bad)
        with self.assertRaises(ValueError):
            nav.validate_spec(correction, dict(good, command='navigation_cancel'))

    def test_pickup_does_not_widen_schema_position_yaw_or_timestamp_envelopes(self):
        original = spec()
        bad_specs = [dict(original, point='put1'), dict(original, version=True),
                     dict(original, extra='policy'), dict(original, target=dict(original['target'], extra=1)),
                     dict(original, reference=dict(original['reference'], x=.050001)),
                     dict(original, reference=dict(original['reference'], yaw=.1)),
                     dict(original, reference=dict(original['reference'], stamp_ns=True))]
        for bad in bad_specs:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                nav.validate_spec(bad)
        snapshot = copy.deepcopy(original)
        checked = nav.validate_spec(original)
        checked['reference']['x'] = .04
        self.assertEqual(original, snapshot)


if __name__ == '__main__':
    unittest.main()
