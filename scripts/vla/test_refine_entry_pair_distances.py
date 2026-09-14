import unittest
import copy
import numpy as np

from refine_entry_pair_distances import RefinedPairDistances, refinement_indices
from prepare_vla_entry_bundle import certify_pairs


class Geometry:
    labels = [['a', 'b'], ['c', 'd']]
    pairs = [(0, 1), (2, 3)]
    shapes = [0, 1, 2, 3]
    weights = np.array([[.1], [.1]])
    lower = np.array([-1.])
    upper = np.array([1.])

    def distances(self, q):
        self.last_q = q.copy()
        return np.array([.05, .001])


class RefinementTests(unittest.TestCase):
    def test_prior_report_cannot_change_scenario_route_model_or_pairs(self):
        prior = dict(candidate='c', route='r', model_sources={'m': 'hash'}, sources_sha256={'f': 'hash'},
            audit=dict(timed_out=False, base_margin_m=.002, joint_error_scenario_rad=.01,
                pairs=[dict(pair=['a','b'], exempted=False, status='UNRESOLVED')]))
        kwargs=dict(candidate='c', route='r', model_sources={'m':'hash'}, sources={'f':'hash'}, error_rad=.01)
        self.assertEqual(refinement_indices(prior, [['a','b']], **kwargs), [0])
        for mode in ('candidate', 'route', 'model', 'source', 'margin', 'error', 'timeout', 'pair', 'exempt'):
            p=copy.deepcopy(prior)
            if mode in ('candidate','route'): p[mode]='other'
            if mode=='model': p['model_sources']={}
            if mode=='source': p['sources_sha256']={}
            if mode=='margin': p['audit']['base_margin_m']=.001
            if mode=='error': p['audit']['joint_error_scenario_rad']=.005
            if mode=='timeout': p['audit']['timed_out']=True
            if mode=='pair': p['audit']['pairs'][0]['pair']=['b','a']
            if mode=='exempt': p['audit']['pairs'][0]['exempted']=True
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                refinement_indices(p, [['a','b']], **kwargs)

    def test_refinement_retains_collision_and_all_pairs(self):
        g = RefinedPairDistances(Geometry(), [0], lambda a, b: .2)
        report = certify_pairs(g, [[0.], [.1]], joint_error_rad=.6)
        self.assertEqual(report['pairs'][0]['status'], 'CERTIFIED_AFFINE_INTERVALS')
        self.assertEqual(report['pairs'][1]['status'], 'MODEL_MARGIN_VIOLATION')
        self.assertFalse(report['all_pairs_certified'])
        self.assertFalse(report['physical_approval'])
        self.assertTrue(all(not p['exempted'] for p in report['pairs']))

    def test_base_geometry_is_updated_before_solid_query(self):
        base = Geometry()
        g = RefinedPairDistances(base, [0], lambda a, b: .1 + base.last_q[0])
        np.testing.assert_allclose(g.distances(np.array([.2])), [.3, .001])
        np.testing.assert_allclose(g.distances(np.array([.3])), [.4, .001])

    def test_invalid_or_conflicting_refinement_is_rejected(self):
        for value in (float('nan'), float('inf'), -.1, .001):
            with self.subTest(value=value), self.assertRaises(ValueError):
                RefinedPairDistances(Geometry(), [0], lambda a, b: value).distances([0.])

    def test_unrefined_result_cannot_be_dropped(self):
        g = RefinedPairDistances(Geometry(), [], lambda a, b: .2)
        np.testing.assert_allclose(g.distances([0.]), [.05, .001])
        self.assertEqual(g.solid_queries, 0)
        with self.assertRaises(ValueError):
            RefinedPairDistances(Geometry(), [2], lambda a, b: .2)


if __name__ == '__main__':
    unittest.main()
