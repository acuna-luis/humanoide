import unittest
import numpy as np

from inspect_entry_table_observation import inside_polygon, fit_visible_plane


class VisiblePlaneTests(unittest.TestCase):
    def test_polygon_and_exclusion(self):
        p = [[0, 0], [4, 0], [4, 4], [0, 4]]
        q = [[1, 1], [3, 1], [3, 3], [1, 3]]
        uv = [[.5, .5], [2, 2], [5, 2], [-1, -1]]
        np.testing.assert_array_equal(inside_polygon(uv, p) & ~inside_polygon(uv, q), [1, 0, 0, 0])

    def test_recovers_plane_with_outliers(self):
        rng = np.random.default_rng(23)
        xy = rng.uniform(-.4, .4, (150, 2))
        z = .66 + .04*xy[:, 0] + rng.normal(0, .0004, 150)
        pts = np.vstack([np.column_stack([xy, z]), rng.uniform([-.4, -.4, .2], [.4, .4, .9], (40, 3))])
        centre, normal, mask, residual = fit_visible_plane(pts)
        self.assertGreater(mask.sum(), 145)
        self.assertLess(abs(centre[2]-.04*centre[0]-.66), .001)
        expected = np.array([-.04, 0, 1]); expected /= np.linalg.norm(expected)
        self.assertGreater(normal@expected, .999)
        self.assertLess(np.quantile(residual[mask], .95), .002)

    def test_degenerate_and_nonfinite_rejected(self):
        for pts in (np.zeros((29, 3)), np.zeros((40, 3)), np.full((40, 3), np.nan)):
            with self.assertRaises(ValueError): fit_visible_plane(pts)
        with self.assertRaises(ValueError): inside_polygon([[np.nan, 0]], [[0, 0], [1, 0], [0, 1]])


if __name__ == '__main__':
    unittest.main()
