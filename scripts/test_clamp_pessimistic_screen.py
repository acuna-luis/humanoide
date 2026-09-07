import unittest
from audit_clamp_pessimistic_screen import point_aabb_distance


class DistanceTests(unittest.TestCase):
    def test_inside_is_zero(self):
        self.assertEqual(point_aabb_distance([0,0,0], [-1,-1,-1], [1,1,1]), 0)

    def test_outside_distance(self):
        self.assertEqual(point_aabb_distance([4,5,1], [-1,-1,-1], [1,1,1]), 5)

    def test_invalid_is_not_separation(self):
        with self.assertRaises(ValueError):
            point_aabb_distance([float('nan'),0,0], [-1,-1,-1], [1,1,1])
        with self.assertRaises(ValueError):
            point_aabb_distance([0,0,0], [1,1,1], [-1,-1,-1])


if __name__ == '__main__':
    unittest.main()
