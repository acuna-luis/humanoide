import math
import unittest
from build_home_offline_candidate import build, segment, evaluate, check_position_limits, NAMES


class CandidateTests(unittest.TestCase):
    def test_outbound_separately_parameterized(self):
        source = {'arm_path_checkpoint_order': {k: [v]*14 for k, v in
                  [('ready_b', 1), ('waypoint_a', .5), ('staging_preposition', .1)]}}
        out = build(source, direction='outbound')
        back = build(source)
        self.assertEqual(out['segments'][0]['start_rad'], [0]*14)
        self.assertEqual(out['segments'][-1]['end_rad'], [1]*14)
        self.assertAlmostEqual(out['total_duration_s'], back['total_duration_s'])
        self.assertFalse(out['collision_validated'])
        with self.assertRaises(ValueError):
            build(source, direction='invalid')

    def test_position_check_rejects_missing_and_violations(self):
        source = {'arm_path_checkpoint_order': {k: [.5]*14 for k in
                  ('ready_b', 'waypoint_a', 'staging_preposition')}}
        candidate = build(source)
        xml = '<robot>'+''.join(f'<joint name="{n}" type="revolute"><limit lower="-1" upper="1"/></joint>'
                                for n in NAMES)+'</robot>'
        self.assertEqual(check_position_limits(candidate, xml)['status'], 'URDF_POSITION_BOUNDS_PASS_ONLY')
        self.assertEqual(len(check_position_limits(candidate, '<robot/>')['missing_or_invalid_limits']), 14)
        candidate['segments'][0]['start_rad'] = [2]*14
        self.assertEqual(len(check_position_limits(candidate, xml)['violations']), 14)
        candidate['interpolation'] = 'unknown'
        with self.assertRaises(ValueError):
            check_position_limits(candidate, xml)

    def test_endpoints_and_derivatives(self):
        row = segment([-.7]*14, [.9]*14, .15, .5)
        for u, expected in ((0, -.7), (1, .9)):
            q, v, a = evaluate(row, u)
            for x in q:
                self.assertAlmostEqual(x, expected)
            self.assertEqual(v, [0]*14)
            self.assertEqual(a, [0]*14)

    def test_analytic_extrema(self):
        for distance in (.00001, .01, .5, 3):
            row = segment([0]*14, [distance]*14, .15, .5)
            self.assertLessEqual(max(map(abs, evaluate(row, .5)[1])), .15)
            for u in ((3-math.sqrt(3))/6, (3+math.sqrt(3))/6):
                self.assertLessEqual(max(map(abs, evaluate(row, u)[2])), .5)
            self.assertLessEqual(row['max_velocity_rad_s'], .15)
            self.assertLessEqual(row['max_acceleration_rad_s2'], .5)

    def test_stationary(self):
        row = segment([1]*14, [1]*14, .15, .5)
        self.assertGreater(row['duration_s'], 0)
        self.assertEqual(evaluate(row, .3), ([1]*14, [0]*14, [0]*14))

    def test_reject_invalid(self):
        for bad in (True, 0, -1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                segment([0]*14, [1]*14, bad, .5)
            with self.assertRaises(ValueError):
                segment([0]*14, [1]*14, .15, bad)
        for bad in ([0]*13, [True]*14, [float('nan')]*14):
            with self.assertRaises(ValueError):
                segment(bad, [0]*14, .15, .5)
        with self.assertRaises(ValueError):
            segment([-1e308]*14, [1e308]*14, .15, .5)

    def test_never_exports_executable_or_fakes_other_axes(self):
        source = {'arm_path_checkpoint_order': {k: [v]*14 for k, v in
                  [('ready_b', 1), ('waypoint_a', .5), ('staging_preposition', .1)]}}
        result = build(source)
        self.assertFalse(result['physical_authorized'])
        self.assertFalse(result['executable'])
        self.assertFalse(result['collision_validated'])
        self.assertIsNone(result['non_arm_state'])
        self.assertEqual(result['joint_names'][0], 'L_elbow_roll_joint')
        self.assertEqual(len(result['segments']), 3)


if __name__ == '__main__':
    unittest.main()
