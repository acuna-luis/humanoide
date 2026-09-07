import unittest
from audit_shoulder_between_samples import lower_bound


class BoundTests(unittest.TestCase):
    def test_known_bound(self):
        rows = [{'angle_rad': a, 'surface_distance_m': .01} for a in (0, -.01, -.02)]
        self.assertAlmostEqual(lower_bound(rows, .2)['conditional_surface_lower_bound_m'], .009)

    def test_irregular_grid_uses_largest_interval(self):
        rows = [{'angle_rad': a, 'surface_distance_m': .01} for a in (0, -.01, -.05)]
        self.assertAlmostEqual(lower_bound(rows, 1)['conditional_surface_lower_bound_m'], -.01)

    def test_rejects_bad_input(self):
        for rows in ([], [{'angle_rad': 0, 'surface_distance_m': .01}]*2,
                     [{'angle_rad': 0, 'surface_distance_m': .01},
                      {'angle_rad': -.1, 'surface_distance_m': float('nan')}]):
            with self.assertRaises(ValueError):
                lower_bound(rows, 1)


if __name__ == '__main__':
    unittest.main()
