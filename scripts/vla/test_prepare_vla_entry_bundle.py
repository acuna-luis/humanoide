"""Analytic counterexamples for the offline interval reviewer, without robot IO."""
import unittest
import numpy as np

from prepare_vla_entry_bundle import certify_pairs, rim_height, routes, validate_first_record, empty_recovery_waypoints


class AnalyticGeometry:
    lower = np.array([-2.])
    upper = np.array([2.])
    labels = [['a', 'b'], ['c', 'd']]
    weights = np.array([[1.], [1.]])

    def __init__(self, collision=False, uncertain=False):
        self.collision = collision
        self.uncertain = uncertain

    def distances(self, q):
        # Lipschitz constant 1. A narrow off-centre minimum must be checked,
        # even though endpoints and the root midpoint are separated.
        first = abs(q[0] - .25) if self.collision else .15
        second = .0020000011 if self.uncertain else .5
        return np.array([first, second])


class IntervalTests(unittest.TestCase):
    def test_interior_contact_is_found(self):
        result = certify_pairs(AnalyticGeometry(collision=True), [[0.], [1.]])
        self.assertEqual(result['pairs'][0]['status'], 'MODEL_MARGIN_VIOLATION')
        self.assertFalse(result['all_pairs_certified'])
        self.assertFalse(result['physical_approval'])

    def test_clear_path_and_reverse_have_same_certificate(self):
        for path in ([[0.], [1.]], [[1.], [0.]]):
            result = certify_pairs(AnalyticGeometry(), path)
            self.assertTrue(result['all_pairs_certified'])
            self.assertEqual(len(result['pairs']), 2)
            self.assertTrue(all(not row['exempted'] for row in result['pairs']))
            self.assertFalse(result['physical_approval'])

    def test_depth_exhaustion_does_not_pass_clear_samples(self):
        result = certify_pairs(AnalyticGeometry(uncertain=True), [[0.], [1.]], max_depth=2)
        self.assertEqual(result['pairs'][1]['status'], 'UNRESOLVED')
        self.assertFalse(result['all_pairs_certified'])

    def test_unresolved_pair_is_not_repeated_in_sibling_subtrees(self):
        geometry = AnalyticGeometry(uncertain=True)
        # The nearly-tangent pair needs more than the allowed depth everywhere.
        # One unresolved leaf already prevents its whole-route certificate.
        result = certify_pairs(geometry, [[0.], [1.]], max_depth=12)
        self.assertLess(result['distance_queries'], 40)
        self.assertFalse(result['timed_out'])
        self.assertEqual(result['pairs'][1]['status'], 'UNRESOLVED')
        self.assertEqual(result['pairs'][1]['uncertainty_witness']['reason'],
                         'SUBDIVISION_RESOLUTION_EXHAUSTED')
        self.assertFalse(result['all_pairs_certified'])
        self.assertFalse(result['physical_approval'])

    def test_error_scenario_is_uncertainty_not_reported_contact(self):
        result = certify_pairs(AnalyticGeometry(), [[0.], [1.]], joint_error_rad=.2)
        self.assertEqual(result['pairs'][0]['status'], 'UNRESOLVED')

    def test_start_violation_retained_after_clear_segments(self):
        result = certify_pairs(AnalyticGeometry(collision=True), [[.25], [1.], [1.5]])
        self.assertEqual(result['pairs'][0]['status'], 'MODEL_MARGIN_VIOLATION')
        self.assertEqual(result['pairs'][0]['witness']['fraction'], 0)

    def test_invalid_budget_vectors_limits_and_error(self):
        for kwargs in ({'seconds': 0}, {'seconds': float('nan')},
                       {'max_depth': 0}, {'joint_error_rad': -1}):
            with self.assertRaises(ValueError):
                certify_pairs(AnalyticGeometry(), [[0.], [1.]], **kwargs)
        for path in ([[0.], [float('nan')]], [[0.], [3.]], [[0.]]):
            with self.assertRaises(ValueError):
                certify_pairs(AnalyticGeometry(), path)

    def test_routes_preserve_asymmetric_start_and_exact_entry(self):
        start = np.linspace(-.2, .2, 20)
        entry = np.linspace(.1, -.1, 20)
        ready = np.full(20, -.3)
        original = start.copy()
        for path in routes(start, ready, entry).values():
            np.testing.assert_array_equal(path[0], original)
            np.testing.assert_array_equal(path[-1], entry)
        np.testing.assert_array_equal(start, original)

    def test_recovery_completes_observation_head_to_true_home(self):
        start = np.zeros(20)
        start[14] = -.43
        entry = np.full(20, .1)
        result = empty_recovery_waypoints([start, entry])
        np.testing.assert_array_equal(result[0], entry)
        np.testing.assert_array_equal(result[-2], start)
        np.testing.assert_array_equal(result[-1], np.zeros(20))
        self.assertEqual(len(empty_recovery_waypoints([np.zeros(20), entry])), 2)

    def test_height_reconstruction_on_synthetic_camera(self):
        pose = np.diag([1., -1., -1., 1.])
        pose[2, 3] = 2.
        # Unit focal length, width .6 at depth 1 -> surface 2-1-.2+.15=.95.
        self.assertAlmostEqual(rim_height(pose, np.eye(3), [[-.3, 0], [.3, 0]], .6, .2, .15), .95)
        with self.assertRaises(ValueError):
            rim_height(np.eye(4), np.eye(3), [[-.3, 0], [.3, 0]], .6, .2, .15)
        with self.assertRaises(ValueError):
            rim_height(pose, np.eye(3), [[0, 0], [0, 0]], .6, .2, .15)

    def test_dataset_identity_and_state_cannot_be_substituted(self):
        row = dict(episode_index=46, task_index=0, timestamp=0.)
        row['observation.state'] = [0.] * 32
        np.testing.assert_array_equal(validate_first_record(row, 46, [0.] * 20), np.zeros(20))
        for field, value in [('episode_index', 44), ('task_index', 1),
                             ('timestamp', .1), ('timestamp', float('nan')), ('frame_index', 1)]:
            changed = dict(row, **{field: value})
            with self.assertRaises(ValueError):
                validate_first_record(changed, 46, [0.] * 20)
        with self.assertRaises(ValueError):
            validate_first_record(row, 46, [.1] * 20)


if __name__ == '__main__':
    unittest.main()
