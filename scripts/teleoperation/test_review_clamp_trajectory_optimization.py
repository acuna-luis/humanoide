import math
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import review_clamp_trajectory_optimization as review
from check_pico_home_geometry_offline import separation


class ReviewTests(unittest.TestCase):
    def test_batched_gap_matches_existing_scalar_sat(self):
        rng = np.random.default_rng(17)
        def boxes():
            centers = rng.normal(size=(40, 3))
            rotations = np.array([review.fk.rotation_rpy(x) for x in rng.normal(size=(40, 3))])
            return centers, rotations, np.array([.1, .2, .3])
        a, b = boxes(), boxes()
        expected = [separation(a[0][i], a[1][i], a[2], b[0][i], b[1][i], b[2]) for i in range(40)]
        np.testing.assert_allclose(review.batch_gap(a, b), expected, atol=1e-12)

    def test_batch_fk_matches_scalar_and_common_ancestors_cancel(self):
        joints = [dict(name=review.JOINT_ORDER[0], type='revolute', parent='base_link',
                       child='shared', origin=np.eye(4), axis=np.array([0., 0., 1.])),
                  dict(name=review.JOINT_ORDER[1], type='revolute', parent='shared',
                       child='tool', origin=review.fk.transform([.5, 0, 0]), axis=np.array([0., 1., 0.])),
                  dict(name='fixed', type='fixed', parent='shared', child='obstacle',
                       origin=review.fk.transform([0, .5, 0]), axis=np.array([0., 0., 1.]))]
        q = np.zeros((20, 20)); q[:, :2] = np.random.default_rng(19).normal(size=(20, 2))
        poses = review.batch_fk(joints, q)
        for i in range(len(q)):
            expected = review.fk.forward_kinematics(joints, dict(zip(review.JOINT_ORDER, q[i])))
            for name in expected:
                np.testing.assert_allclose(poses[name][i], expected[name], atol=1e-12)
        bounds = np.array([[-.1, -.1, -.1], [.1, .1, .1]])
        radii = review.pair_radii(joints, 'tool', bounds, 'obstacle', bounds)
        self.assertEqual(radii[0], 0)
        self.assertAlmostEqual(radii[1], math.sqrt(.03))
        self.assertEqual(np.count_nonzero(radii), 1)

    def test_skip_requires_exact_equality_not_endpoint_tolerance(self):
        zero = np.zeros(20)
        end = zero.copy(); end[14] = .001
        hold = review.Stage('hold', zero, zero, np.full(20, 3.75))
        small_move = review.Stage('small', zero, end, np.full(20, 3.75))
        self.assertEqual(review.remove_exact_holds([hold, small_move]), [small_move])

    def test_radius_bounds_cover_continuous_motion_and_finite_angle_error(self):
        joint = dict(name=review.JOINT_ORDER[0], type='revolute', parent='base_link',
                     child='hinge', origin=np.eye(4), axis=np.array([0., 0., 1.]))
        fixed = dict(name='fixed', type='fixed', parent='hinge', child='point',
                     origin=review.fk.transform([.7, 0, 0]), axis=np.array([0., 0., 1.]))
        joints = [joint, fixed]
        zero_bounds = np.zeros((2, 3))
        obstacle = np.array([[1.1, .3, 0], [1.1, .3, 0]])
        weights = review.pair_radii(joints, 'point', zero_bounds, 'base_link', obstacle)
        stage = review.Stage('arc', np.r_[-.5, np.zeros(19)], np.r_[.5, np.zeros(19)], np.ones(20))
        _, q = stage.samples(11)
        poses = review.batch_fk(joints, q)
        gaps = review.batch_gap(review.batch_obb(poses['point'], zero_bounds),
                                review.batch_obb(poses['base_link'], obstacle))
        bound = np.min(np.minimum(gaps[:-1], gaps[1:])-abs(np.diff(q, axis=0))@weights/2)
        _, dense = stage.samples(2001)
        nominal = review.batch_fk(joints, dense)['point'][:, :3, 3]
        self.assertGreaterEqual(float(np.linalg.norm(nominal-obstacle[0], axis=1).min()), bound)
        perturbed = dense.copy(); perturbed[:, 0] += math.radians(5)
        actual = review.batch_fk(joints, perturbed)['point'][:, :3, 3]
        displacement = float(np.linalg.norm(actual-nominal, axis=1).max())
        self.assertLessEqual(displacement, 2*math.sin(math.radians(5)/2)*weights.sum()+1e-12)

    def test_short_component_finishes_before_long_component_without_jump(self):
        stage = review.Stage('parallel', np.zeros(20), np.ones(20),
                             np.r_[np.full(14, 10), np.full(6, 3.75)])
        t, q = stage.samples(101)
        index = int(np.flatnonzero(t == 3.75)[0])
        np.testing.assert_array_equal(q[index, 14:], np.ones(6))
        self.assertTrue((q[index, :14] < 1).all())
        np.testing.assert_array_equal(q[-1], np.ones(20))

    def test_candidates_continuous_and_retimed_peaks_do_not_increase(self):
        for variant, start in review.PICO_VARIANTS.items():
            candidates = review.candidates(start, 'pico')
            caps = review.peak_caps(candidates['baseline_20s'])
            for name, stages in candidates.items():
                np.testing.assert_array_equal(stages[0].start, start)
                np.testing.assert_array_equal(stages[-1].end, np.zeros(20))
                for a, b in zip(stages, stages[1:]):
                    np.testing.assert_array_equal(a.end, b.start)
                for kind, values in review.peak_caps(stages).items():
                    self.assertTrue((values <= caps[kind]+1e-12).all(), (variant, name, kind))
            expected = 16.25 if variant == 'pico_body_zero' else 20.
            self.assertAlmostEqual(sum(s.duration for s in candidates['omit_exact_holds']), expected)

    def test_analytical_peaks_bound_dense_polynomial_derivatives(self):
        s = np.linspace(0, 1, 100001)
        derivatives = {'velocity':30*s**2*(1-s)**2,
                       'acceleration':60*s-180*s**2+120*s**3,
                       'jerk':60-360*s+360*s**2}
        stage = review.Stage('test', np.zeros(20), np.full(20, .7), np.full(20, 2.3))
        for power, (name, values) in enumerate(derivatives.items(), 1):
            numerical = .7/2.3**power*np.abs(values).max()
            self.assertAlmostEqual(stage.peaks()[name][0], numerical, places=8)

    def test_bad_duration_or_new_joint_without_budget_rejected(self):
        with self.assertRaises(ValueError):
            review.Stage('bad', np.zeros(20), np.ones(20), np.zeros(20))
        points = [np.zeros(20) for _ in range(5)]
        reference = review.make_stages(points, (1, 1, 1, 1))
        points[1] = np.ones(20)
        with self.assertRaises(ValueError):
            review.retime_to_same_joint_peaks(points, reference)


if __name__ == '__main__':
    unittest.main()
