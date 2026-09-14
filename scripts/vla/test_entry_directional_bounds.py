import unittest
import numpy as np
from scipy.spatial.transform import Rotation

from entry_directional_bounds import remainder_bound


class DirectionalTaylorTests(unittest.TestCase):
    def test_two_joint_chain_finite_box(self):
        rng = np.random.default_rng(199)
        lengths = [.7, .3]
        def point(q):
            return np.array([.7*np.cos(q[0])+.3*np.cos(q.sum()), .7*np.sin(q[0])+.3*np.sin(q.sum())])
        for _ in range(80):
            q = rng.uniform(-2, 2, 2); h = rng.uniform(.001, .3, 2)
            direction = rng.normal(size=2); direction /= np.linalg.norm(direction)
            p = point(q); joint = .7*np.array([np.cos(q[0]), np.sin(q[0])])
            gradient = np.array([np.array([-p[1], p[0]])@direction,
                                 np.array([-(p-joint)[1], (p-joint)[0]])@direction])
            error = remainder_bound([sum(lengths), lengths[1]], [0, 1], h)
            upper = p@direction + np.abs(gradient)@h + error
            for _ in range(40): self.assertLessEqual(point(q+rng.uniform(-h, h))@direction, upper+1e-12)

    def test_depth_order_is_not_joint_array_order(self):
        a = remainder_bound([1., .3], [0, 1], [.2, .1])
        b = remainder_bound([.3, 1.], [1, 0], [.1, .2])
        self.assertAlmostEqual(a, b)
        self.assertAlmostEqual(a, .5*(1*.2**2 + 2*.3*.2*.1 + .3*.1**2))

    def test_nonparallel_axes_three_dimensional_chain(self):
        rng = np.random.default_rng(24)
        def state(q):
            first = Rotation.from_rotvec([0, 0, q[0]])
            second = Rotation.from_rotvec([0, q[1], 0])
            origin = first.apply([.7, 0, 0])
            return origin+first.apply(second.apply([.3, 0, 0])), origin, first.apply([0, 1, 0])
        for _ in range(80):
            q = rng.uniform(-2, 2, 2); h = rng.uniform(.001, .3, 2)
            normal = rng.normal(size=3); normal /= np.linalg.norm(normal)
            point, origin, axis = state(q)
            gradient = np.array([np.cross([0, 0, 1], point)@normal,
                                 np.cross(axis, point-origin)@normal])
            upper = point@normal+np.abs(gradient)@h+remainder_bound([1., .3], [0, 1], h)
            for _ in range(30): self.assertLessEqual(state(q+rng.uniform(-h, h))[0]@normal, upper+1e-12)

    def test_invalid_radius_or_width_rejected(self):
        for radii, widths in [([-1], [1]), ([1], [-1]), ([np.nan], [1])]:
            with self.assertRaises(ValueError): remainder_bound(radii, [0], widths)


if __name__ == '__main__': unittest.main()
