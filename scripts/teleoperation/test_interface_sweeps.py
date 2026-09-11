import unittest
import numpy as np
import fcl
import trimesh

from audit_home_interface_sweeps import reference_overlap_box, outside_all_boxes, validated_surface_contacts
from audit_home_interfaces import boundary_object, query_boundary
from general_home.contact_witnesses import triangle_pair_witnesses


class InterfaceSweepTests(unittest.TestCase):
    def test_triangle_contacts_and_disjoint_faces(self):
        a = np.array([[[0., 0, 0], [2, 0, 0], [0, 2, 0]]])
        b = np.array([[[.5, .5, -1], [.5, .5, 1], [2, 2, 1]]])
        points = triangle_pair_witnesses(a, b)
        self.assertGreater(len(points), 0)
        self.assertLess(abs(points[:, 2]).max(), 1e-8)
        self.assertEqual(len(triangle_pair_witnesses(a, b+[0, 0, 5])), 0)
        self.assertEqual(len(triangle_pair_witnesses(a, np.zeros((1, 3, 3)))), 0)

    def test_coplanar_edge_crossings_without_contained_vertex(self):
        a = np.array([[[-2., -1, 0], [2, -1, 0], [0, 2, 0]]])
        b = np.array([[[-2., 1, 0], [2, 1, 0], [0, -2, 0]]])
        points = triangle_pair_witnesses(a, b)
        self.assertGreaterEqual(len(points), 6)
        for triangle in (a, b):
            residual = np.linalg.norm(trimesh.triangles.closest_point(np.repeat(triangle, len(points), axis=0), points)-points, axis=1)
            self.assertLess(residual.max(), 1e-8)

    def test_reference_bound_contains_overlap_and_margin(self):
        a = [[0, 0, 0], [1, 1, 1]]
        b = [[.5, .2, -.5], [2, .8, .5]]
        box = reference_overlap_box(a, b, .01)
        np.testing.assert_allclose(box, [[.49, .19, -.01], [1.01, .81, .51]])
        self.assertEqual(len(outside_all_boxes([[.5, .4, 0]], [box])), 0)
        self.assertEqual(len(outside_all_boxes([[0, .4, 0]], [box])), 1)

    def test_union_of_reference_boxes_not_their_convex_hull(self):
        boxes = [[[0, 0, 0], [1, 1, 1]], [[2, 0, 0], [3, 1, 1]]]
        np.testing.assert_allclose(outside_all_boxes([[.5, .5, .5], [1.5, .5, .5], [2.5, .5, .5]], boxes), [[1.5, .5, .5]])

    def test_separated_reference_and_box_boundary(self):
        box = reference_overlap_box([[0, 0, 0], [1, 1, 1]], [[2, 2, 2], [3, 3, 3]], 0)
        self.assertIsNone(box)
        self.assertEqual(len(outside_all_boxes([[1, 1, 1]], [None])), 1)
        self.assertEqual(len(outside_all_boxes([[1+5e-10, 1, 1]], [[[0, 0, 0], [1, 1, 1]]])), 0)

    def test_bad_inputs_rejected(self):
        with self.assertRaises(ValueError):
            reference_overlap_box([[np.nan, 0, 0]], [[0, 0, 0]])
        with self.assertRaises(ValueError):
            outside_all_boxes([[0, 0, 0]], [[[1, 0, 0], [0, 1, 1]]])

    def test_real_surface_witness_leaves_reference_contact_region(self):
        mesh = trimesh.creation.box(extents=[1., 1., 1.])
        a, b = boundary_object(mesh), boundary_object(mesh)
        reference = reference_overlap_box(mesh.vertices, mesh.vertices+[.9, 0, 0])
        pose = np.eye(4); pose[0, 3] = .9
        b.setTransform(fcl.Transform(pose[:3, :3], pose[:3, 3]))
        initial = query_boundary(a, b)
        self.assertTrue(initial['surface_intersection'])
        points, stats = validated_surface_contacts(mesh, mesh, pose, a, b)
        self.assertGreater(stats['discarded'], 0)  # FCL reports invalid coplanar witnesses.
        self.assertGreater(len(points), 0)
        self.assertEqual(len(outside_all_boxes(points, [reference])), 0)
        pose[0, 3] = -.9
        b.setTransform(fcl.Transform(pose[:3, :3], pose[:3, 3]))
        points, stats = validated_surface_contacts(mesh, mesh, pose, a, b)
        self.assertGreater(len(outside_all_boxes(points, [reference])), 0)


if __name__ == '__main__':
    unittest.main()
