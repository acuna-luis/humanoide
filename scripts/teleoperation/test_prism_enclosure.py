"""Regression tests for conservative prism closure and retained collision gates."""
import unittest

import numpy as np
import trimesh

from general_home.geometry import Shape,solid_distance
from general_home.prism_enclosure import convex_prism_enclosure,component_prism_covers


def wall(polygon=None):
    if polygon is None:
        angle=np.arange(12)*2*np.pi/12
        polygon=np.c_[.1*np.cos(angle),.1*np.sin(angle)]
    polygon=np.asarray(polygon)
    n=len(polygon)
    vertices=np.vstack([np.c_[polygon,np.zeros(n)],np.c_[polygon,np.full(n,.4)]])
    faces=[]
    for i in range(n):
        j=(i+1)%n
        faces.extend([[i,j,n+j],[i,n+j,n+i]])
    return trimesh.Trimesh(vertices=vertices,faces=faces,process=False)


class PrismTests(unittest.TestCase):
    def test_complete_sidewall_covers_interior_and_caps(self):
        source=wall();before=source.triangles.copy()
        hull,certificate=convex_prism_enclosure(source)
        self.assertTrue(hull.is_volume)
        self.assertTrue(hull.contains([[0,0,.2]])[0])
        self.assertTrue(certificate['source_triangles_covered'])
        self.assertTrue(certificate['prism_interior_covered'])
        self.assertFalse(certificate['physical_approval'])
        np.testing.assert_array_equal(source.triangles,before)

    def test_rotation_translation_and_skew_prism(self):
        source=wall();source.vertices[12:,0]+=.07
        source.apply_transform(trimesh.transformations.rotation_matrix(.57,[1,2,3]))
        source.apply_translation([1,-2,3])
        self.assertIsNotNone(convex_prism_enclosure(source))

    def test_concave_end_loop_rejected(self):
        polygon=[[-.1,-.1],[.1,-.1],[.03,0],[.1,.1],[-.1,.1]]
        self.assertIsNone(convex_prism_enclosure(wall(polygon)))

    def test_tapered_or_nonplanar_end_rejected(self):
        tapered=wall();tapered.vertices[12:,:2]*=.9
        self.assertIsNone(convex_prism_enclosure(tapered))
        warped=wall();warped.vertices[-1,2]+=.001
        self.assertIsNone(convex_prism_enclosure(warped))

    def test_missing_or_duplicate_side_face_rejected(self):
        missing=wall();missing.update_faces(np.arange(len(missing.faces)-1))
        self.assertIsNone(convex_prism_enclosure(missing))
        duplicate=wall();duplicate.faces=np.vstack([duplicate.faces,duplicate.faces[0]])
        self.assertIsNone(convex_prism_enclosure(duplicate))

    def test_unrecognized_residual_sheet_preserves_whole_enclosure(self):
        source=wall()
        triangle=trimesh.Trimesh(vertices=[[.5,0,0],[.6,0,0],[.5,.1,0]],faces=[[0,1,2]],process=False)
        assembly=trimesh.util.concatenate([source,triangle])
        self.assertIsNone(component_prism_covers(assembly))
        shape=Shape.from_mesh('residual','residual',assembly)
        self.assertTrue(shape.convex)

    def test_component_union_retains_solids_and_leaves_empty_space(self):
        first=wall();second=wall();second.apply_translation([.6,0,0])
        assembly=trimesh.util.concatenate([first,second])
        before=assembly.triangles.copy()
        shape=Shape.from_mesh('assembly','assembly',assembly)
        self.assertEqual(shape.representation,'closed_components_with_certified_prism_enclosures')
        self.assertEqual(len(shape.enclosure_certificate),2)
        self.assertFalse(shape.convex)
        np.testing.assert_array_equal(assembly.triangles,before)
        probe=trimesh.creation.box(extents=[.02,.02,.02]);probe.apply_translation([.3,0,.2])
        self.assertGreater(solid_distance(shape,Shape.from_mesh('clear','clear',probe)),.18)
        probe.apply_translation([-.3,0,0])
        self.assertEqual(solid_distance(shape,Shape.from_mesh('inside','inside',probe)),0)

    def test_closed_part_is_preserved_in_component_union(self):
        closed=trimesh.creation.box(extents=[.1,.1,.1]);closed.apply_translation([.5,0,0])
        result=component_prism_covers(trimesh.util.concatenate([wall(),closed]))
        self.assertEqual(len(result[0]),2)
        self.assertEqual(len(result[1]),1)
        self.assertAlmostEqual(sum(m.volume for m in result[0]),convex_prism_enclosure(wall())[0].volume+closed.volume)


if __name__=='__main__':
    unittest.main()
