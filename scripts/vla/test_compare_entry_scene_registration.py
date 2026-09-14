import unittest
import numpy as np
from compare_entry_scene_registration import signed_plane_residual


class PlaneComparisonTests(unittest.TestCase):
    def test_different_points_on_same_tilted_plane_are_not_height_error(self):
        points=np.array([[1.,0,1],[2,0,2],[3,2,3]])
        np.testing.assert_allclose(signed_plane_residual(points,[0,0,0],[-1,0,1]),0,atol=1e-15)

    def test_parallel_plane_signed_offset_and_normal_normalization(self):
        np.testing.assert_allclose(signed_plane_residual([[0,0,.03],[1,2,.03]], [0,0,0],[0,0,2]),.03)

    def test_invalid_normal_rejected(self):
        with self.assertRaises(ValueError):signed_plane_residual([[0,0,0]],[0,0,0],[0,0,0])


if __name__=='__main__':unittest.main()
