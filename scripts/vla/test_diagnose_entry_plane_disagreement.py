import unittest
import numpy as np
from scipy.spatial.transform import Rotation
from diagnose_entry_plane_disagreement import intersect_rays


class RayPlaneTests(unittest.TestCase):
    def test_known_plane_and_common_rigid_transform(self):
        pixels = np.array([[0., 0.], [1., 0.], [0., 1.]])
        origin = np.array([0., 0., 2.]); normal = np.array([0., 0., 1.])
        expected = np.array([[0., 0., 2.], [2., 0., 2.], [0., 2., 2.]])
        np.testing.assert_allclose(intersect_rays(pixels, np.eye(3), np.eye(4), origin, normal), expected)
        camera = np.eye(4)
        camera[:3, :3] = Rotation.from_euler('xyz', [.3, -.5, .7]).as_matrix()
        camera[:3, 3] = [.2, .4, -.9]
        actual = intersect_rays(pixels, np.eye(3), camera,
                                camera[:3, :3] @ origin+camera[:3, 3], camera[:3, :3] @ normal)
        np.testing.assert_allclose(actual, expected @ camera[:3, :3].T+camera[:3, 3], atol=1e-14)

    def test_parallel_and_behind_rejected(self):
        for normal, origin in (([1., 0., 0.], [1., 0., 0.]), ([0., 0., 1.], [0., 0., -1.])):
            with self.assertRaises(ValueError):
                intersect_rays(np.zeros((1, 2)), np.eye(3), np.eye(4), np.array(origin), np.array(normal))


if __name__ == '__main__': unittest.main()
