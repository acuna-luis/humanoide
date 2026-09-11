"""Check boundary-only diagnostics never substitute for solid collision checks."""
import unittest
import fcl
import numpy as np
import trimesh
from audit_home_interfaces import boundary_object,query_boundary
from general_home.geometry import Shape,solid_distance


class InterfaceTests(unittest.TestCase):
    def test_nested_solids_have_separated_boundaries_but_collide(self):
        outer=trimesh.creation.box(extents=[2,2,2])
        inner=trimesh.creation.box(extents=[.2,.2,.2])
        report=query_boundary(boundary_object(outer),boundary_object(inner))
        self.assertFalse(report['surface_intersection'])
        self.assertAlmostEqual(report['boundary_distance_m'],.9)
        self.assertEqual(solid_distance(Shape.from_mesh('a','a',outer),Shape.from_mesh('b','b',inner)),0)

    def test_nearest_points_use_transformed_world_frame(self):
        mesh=trimesh.creation.box(extents=[1,1,1])
        a,b=boundary_object(mesh),boundary_object(mesh)
        a.setTransform(fcl.Transform(np.eye(3),np.array([2.,0,0])))
        b.setTransform(fcl.Transform(np.eye(3),np.array([4.,0,0])))
        report=query_boundary(a,b)
        self.assertAlmostEqual(report['boundary_distance_m'],1)
        np.testing.assert_allclose(np.array(report['nearest_points_m'])[:,0],[2.5,3.5])

    def test_contacts_are_reported_as_witnesses_not_full_overlap_bound(self):
        mesh=trimesh.creation.box(extents=[1,1,1])
        other=mesh.copy();other.apply_translation([.5,0,0])
        report=query_boundary(boundary_object(mesh),boundary_object(other),contact_limit=2)
        self.assertTrue(report['surface_intersection'])
        self.assertEqual(report['contact_witness_count'],2)
        self.assertTrue(report['contact_list_may_be_truncated'])
        self.assertFalse(report['witness_validated_on_both_source_triangles'])

    def test_reconstructed_contacts_follow_both_world_transforms(self):
        mesh=trimesh.creation.box(extents=[1,1,1])
        a,b=boundary_object(mesh),boundary_object(mesh)
        a.setTransform(fcl.Transform(np.eye(3),np.array([2.,0,0])))
        b.setTransform(fcl.Transform(np.eye(3),np.array([2.9,0,0])))
        report=query_boundary(a,b,source_meshes=(mesh,mesh))
        self.assertTrue(report['witness_validated_on_both_source_triangles'])
        points=np.array(report['contact_witnesses_m'])
        self.assertGreater(len(points),0)
        self.assertGreaterEqual(points[:,0].min(),2.4-1e-8)
        self.assertLessEqual(points[:,0].max(),2.5+1e-8)


if __name__=='__main__':unittest.main()
