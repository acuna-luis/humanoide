import unittest
import numpy as np
from anchor_entry_scene_to_chassis_gap import front_edge_x_at_centreline


class AnchorTests(unittest.TestCase):
    def test_rotated_edge_uses_centreline_not_midpoint(self):
        table = dict(front_top_midpoint_base_m=[.6, .1, .7],
                     rotation_vector_rad=[0., 0., .2], size_m=[.84, .838, .038])
        self.assertAlmostEqual(front_edge_x_at_centreline(table), .6+.1*np.tan(.2))

    def test_edge_must_cross_centreline(self):
        table = dict(front_top_midpoint_base_m=[.6, 1., .7],
                     rotation_vector_rad=[0., 0., 0.], size_m=[.84, .838, .038])
        with self.assertRaises(ValueError): front_edge_x_at_centreline(table)

    def test_longitudinal_edge_rejected(self):
        table = dict(front_top_midpoint_base_m=[.6, 0., .7],
                     rotation_vector_rad=[0., 0., np.pi/2], size_m=[.84, .838, .038])
        with self.assertRaises(ValueError): front_edge_x_at_centreline(table)


if __name__ == '__main__': unittest.main()
