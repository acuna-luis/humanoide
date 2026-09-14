import unittest
import numpy as np
from scipy.spatial.transform import Rotation

from fit_entry_fixture_pose import rectangle, project, fit


class PoseFitTests(unittest.TestCase):
    def test_recovers_metric_pose_from_synthetic_pixels(self):
        camera = np.eye(4)
        camera[:3, :3] = Rotation.from_euler('xyz', [-2.1, 0., -1.55]).as_matrix()
        camera[:3, 3] = [.16, .04, 1.5]
        k = np.array([[383., 0, 476.], [0, 383., 193.], [0, 0, 1.]])
        corners = rectangle(.84, .838)
        truth = np.array([.015, -.02, .03, .55, -.04, .66])
        pixels = project(corners, truth, camera, k)
        recovered, predicted = fit(corners, pixels, camera, k, [0, 0, 0, .6, 0, .65])
        np.testing.assert_allclose(predicted, pixels, atol=1e-6)
        np.testing.assert_allclose(recovered, truth, atol=1e-6)

    def test_rejects_bad_dimensions_and_pixels(self):
        for size in [(0, 1), (-1, 1), (float('nan'), 1)]:
            with self.assertRaises(ValueError): rectangle(*size)
        with self.assertRaises(ValueError):
            fit(rectangle(1, 1), np.zeros((3, 2)), np.eye(4), np.eye(3), np.zeros(6))


if __name__ == '__main__':
    unittest.main()
