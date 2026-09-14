import unittest
import numpy as np
import trimesh
from explain_entry_fixture_witness import ordered_surface_points


class NearestPointOrderTests(unittest.TestCase):
    def setUp(self):
        self.a = trimesh.creation.box(extents=[1,1,1])
        self.b = self.a.copy(); self.b.apply_translation([2,0,0])
        self.points = np.array([[.5,0,0],[1.5,0,0]])

    def test_preserves_correct_order(self):
        points, swapped = ordered_surface_points(self.a,self.b,self.points)
        np.testing.assert_array_equal(points,self.points)
        self.assertFalse(swapped)

    def test_corrects_reversed_bvh_order(self):
        points, swapped = ordered_surface_points(self.a,self.b,self.points[::-1])
        np.testing.assert_array_equal(points,self.points)
        self.assertTrue(swapped)

    def test_rejects_points_off_both_surfaces(self):
        with self.assertRaises(ValueError):
            ordered_surface_points(self.a,self.b,[[0,0,4],[0,0,5]])


if __name__ == '__main__': unittest.main()
