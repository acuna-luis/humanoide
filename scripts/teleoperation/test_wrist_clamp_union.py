"""Coverage regressions and optional pinned native FK arithmetic tests."""
import os
from pathlib import Path
import tempfile
import unittest

import numpy as np
import trimesh

from general_home.native_arm_frames import NativeArmFrames,dh_poses
from general_home.union_coverage import Capsule,RoundedHull,build_cover,certify_boundary,convex_mesh


class UnionTests(unittest.TestCase):
    def test_nearby_hull_vertices_preserve_closed_topology(self):
        cube = trimesh.creation.box(extents=[.1,.1,.1]).vertices
        vertices = np.vstack([cube,cube[-1]+[5e-9,-5e-9,-5e-9]])
        hull = convex_mesh(vertices)
        self.assertTrue(hull.is_volume)
        self.assertEqual(len(hull.vertices),9)
        self.assertEqual(len(hull.faces),14)
        self.assertGreater(hull.volume,.001)

    def test_vertices_in_different_members_do_not_certify_faces(self):
        vertices = np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,1]],dtype=float)
        members = [Capsule(str(i),[[0,0,0],point],.1) for i,point in enumerate(vertices[1:])]
        self.assertTrue((np.min([m.score(vertices) for m in members],axis=0)<0).all())
        before,_ = certify_boundary(trimesh.convex.convex_hull(vertices),members,[0,0,0])
        self.assertFalse(before['volume_covered'])
        derived,after,_,_,patch = build_cover(vertices,members,[0,0,0])
        self.assertTrue(after['volume_covered'])
        self.assertIsNotNone(patch)
        self.assertTrue((patch.score([[.5,.5,0],[1/3,1/3,1/3]])<0).all())
        self.assertEqual(len(derived),4)

    def test_surface_coverage_without_common_anchor_is_rejected(self):
        hull = trimesh.creation.box(extents=[2,2,2])
        members = [Capsule('left',[[-1,0,0],[-1,0,0]],.25),
            Capsule('right',[[1,0,0],[1,0,0]],.25)]
        with self.assertRaisesRegex(ValueError,'anchor'):
            certify_boundary(hull,members,[0,0,0])

    def test_already_covered_solid_needs_no_supplement(self):
        cube = trimesh.creation.box(extents=[.2,.2,.2])
        members = [Capsule('sphere',[[0,0,0],[0,0,0]],1)]
        derived,report,_,_,patch = build_cover(cube.vertices,members,[0,0,0])
        self.assertIsNone(patch)
        self.assertEqual(len(derived),1)
        self.assertTrue(report['volume_covered'])
        self.assertFalse(report['physical_approval'])

    def test_radial_padding_does_not_fill_box_corners(self):
        cube = trimesh.creation.box(extents=[2,2,2])
        shape = RoundedHull('rounded',cube.vertices,.1)
        self.assertLess(shape.score([[1.05,0,0]])[0],0)
        self.assertGreater(shape.score([[1.09,1.09,1.09]])[0],0)

    def test_nonfinite_geometry_rejected(self):
        for value in ([[np.nan,0,0],[0,0,0]], [[0,0],[1,1]]):
            with self.assertRaises(ValueError):
                Capsule('bad',value,.1)

    def test_unknown_native_binary_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'bad.so';path.write_bytes(b'invalid')
            with self.assertRaisesRegex(ValueError,'hash'):
                NativeArmFrames(path)

    @unittest.skipUnless(os.environ.get('CRUZR_GEOMETRY_ARCHIVE'),'Set explicit private library archive')
    def test_native_fk_and_capsule_attachment(self):
        path = Path(os.environ['CRUZR_GEOMETRY_ARCHIVE'])/'opt/walker/manipulation_kinematics/lib/libs2_arm_kinematics.so'
        frames = NativeArmFrames(path)
        for q in np.vstack([np.zeros(7),np.random.default_rng(81).uniform(-2,2,(24,7))]):
            fk,placed = frames.evaluate(q)
            np.testing.assert_allclose(fk,dh_poses(frames.geometry,q),atol=1e-13,rtol=0)
            np.testing.assert_allclose(placed[6],fk[-1],atol=1e-13,rtol=0)
            self.assertEqual(set(placed),{1,3,5,6})
        for q in ([0]*6,[0]*8,[np.nan]*7):
            with self.assertRaises(ValueError):
                frames.evaluate(q)


if __name__ == '__main__':
    unittest.main()
