import unittest
import numpy as np
from entry_orbit_bounds import triangle_bounds, separation, prove_boxes, refine_triangle_pair


class OrbitBoundsTests(unittest.TestCase):
    def test_triangle_interior_and_rotational_uncertainty_are_enclosed(self):
        rng = np.random.default_rng(610)
        t = rng.uniform(-1, 1, (100, 3, 3))
        bounds = triangle_bounds(t, (-.8, .2), .015)
        weights = rng.dirichlet([1, 1, 1], (50, 100))
        p = np.einsum('sni,nij->snj', weights, t)
        drift = rng.normal(size=p.shape)
        drift *= .015*rng.random((50, 100, 1))/np.linalg.norm(drift, axis=2)[:, :, None]
        p += drift
        theta = rng.uniform(-.8, .2, (50, 100))
        x, y = p[:, :, 0].copy(), p[:, :, 1].copy()
        p[:, :, 0] = x*np.cos(theta)-y*np.sin(theta)
        p[:, :, 1] = x*np.sin(theta)+y*np.cos(theta)
        r, angle = np.linalg.norm(p[:, :, :2], axis=2), np.arctan2(p[:, :, 1], p[:, :, 0])
        self.assertTrue((r >= bounds[:, 0]).all() and (r <= bounds[:, 1]).all())
        self.assertTrue((p[:, :, 2] >= bounds[:, 2]).all() and (p[:, :, 2] <= bounds[:, 3]).all())
        center = (bounds[:, 4]+bounds[:, 5])/2
        self.assertTrue((np.abs((angle-center+np.pi) % (2*np.pi)-np.pi) <= (bounds[:, 5]-bounds[:, 4])/2+1e-12).all())

    def test_origin_inside_projected_triangle_and_branch_cut(self):
        t = np.array([[[-1, -1, 0], [1, -1, 0], [0, 1, 0]],
                      [[-1, -.1, 1], [-1, .1, 1], [-2, 0, 1]]])
        b = triangle_bounds(t)
        self.assertEqual(b[0, 0], 0)
        self.assertGreaterEqual(b[1, 5]-b[1, 4], 2*np.pi)

    def test_lower_bound_does_not_exceed_sampled_distances(self):
        rng = np.random.default_rng(82)
        for _ in range(100):
            a, b = rng.normal(size=(2, 3, 3))
            ba, bb = triangle_bounds(a[None], (-.2, .3))[0], triangle_bounds(b[None], (-.1, .1))[0]
            lower = separation(ba, bb)
            pa = rng.dirichlet([1, 1, 1], 30)@a
            pb = rng.dirichlet([1, 1, 1], 30)@b
            for points, limits in ((pa, (-.2, .3)), (pb, (-.1, .1))):
                angles = rng.uniform(*limits, 30)
                xy = points[:, :2].copy()
                points[:, 0] = xy[:, 0]*np.cos(angles)-xy[:, 1]*np.sin(angles)
                points[:, 1] = xy[:, 0]*np.sin(angles)+xy[:, 1]*np.cos(angles)
            self.assertLessEqual(lower, np.linalg.norm(pa[:, None]-pb, axis=2).min()+1e-12)

    def test_tree_proves_disjoint_slabs_and_preserves_overlap(self):
        rng = np.random.default_rng(4)
        a = rng.uniform([.1, -.1, 0], [.2, .1, .1], (35, 3, 3))
        b = a+[0, 0, .3]
        result = prove_boxes(triangle_bounds(a), triangle_bounds(b), a, b)
        self.assertTrue(result['proved'])
        self.assertFalse(prove_boxes(triangle_bounds(a), triangle_bounds(a), a, a)['proved'])

    def test_refinement_preserves_all_children_and_budget_failure(self):
        a = np.array([[1., 0, 0], [2, 0, 0], [1, 1, 0]])
        b = a+[0, 0, .01]
        self.assertTrue(refine_triangle_pair(a, b, triangle_bounds)['proved'])
        self.assertFalse(refine_triangle_pair(a, a, triangle_bounds, max_nodes=17)['proved'])


if __name__ == '__main__':
    unittest.main()
