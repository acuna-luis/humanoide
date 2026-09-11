"""Offline tests; optional pinned archive exercises constructor interception."""
import json
import os
from pathlib import Path
import tempfile
import unittest

import numpy as np

from audit_native_collision_geometry import vertex_coverage
from general_home.native_geometry import InitializerArguments


class GeometryTests(unittest.TestCase):
    def test_solid_interior_is_not_reported_outside(self):
        cube = np.array([[x,y,z] for x in (-1,1) for y in (-1,1) for z in (-1,1)])
        report = vertex_coverage([[0,0,0], [1.05,0,0]], cube, .1)
        self.assertTrue(report['all_vertices_contained'])

    def test_rounding_is_not_an_expanded_bounding_box(self):
        cube = np.array([[x,y,z] for x in (-1,1) for y in (-1,1) for z in (-1,1)])
        report = vertex_coverage([[1.09,1.09,1.09]], cube, .1)
        self.assertEqual(report['outside_vertices'], 1)
        self.assertAlmostEqual(report['maximum_vertex_excess_m'], np.sqrt(3)*.09-.1)

    def test_bad_inputs_rejected(self):
        cube = [[x,y,z] for x in (-1,1) for y in (-1,1) for z in (-1,1)]
        for vertices, radius in (([], .1), ([[np.nan,0,0]], .1), ([[0,0,0]], -1)):
            with self.assertRaises(ValueError):
                vertex_coverage(vertices, cube, radius)

    def test_unknown_binary_rejected_before_interpretation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'unreviewed.so'
            path.write_bytes(b'not executable')
            with self.assertRaisesRegex(ValueError, 'hash'):
                InitializerArguments(path, 'arm')

    @unittest.skipUnless(os.environ.get('CRUZR_GEOMETRY_ARCHIVE'), 'Set private offline archive explicitly')
    def test_pinned_defaults_and_guard(self):
        root = Path(os.environ['CRUZR_GEOMETRY_ARCHIVE'])
        results = {}
        for part, count in (('arm',7), ('head',2), ('leg',6)):
            obj = InitializerArguments(root/'opt/walker/manipulation_kinematics/lib'/f'libs2_{part}_kinematics.so', part)
            results[part] = obj.extract()
            self.assertEqual(len(results[part]['component_primitives']), count)
            self.assertFalse(results[part]['physical_approval'])
            self.assertEqual(results[part]['host_native_calls'], 0)
            with self.assertRaisesRegex(ValueError, 'fresh'):
                obj.extract()
        # Compare known SI dimensions independently read from the disassembly.
        arm = results['arm']['component_primitives']
        self.assertEqual(arm[1]['points'], [[0,0,0], [0,0,.296]])
        self.assertEqual(arm[1]['scalar_arguments'], [.055])
        self.assertEqual(results['head']['component_primitives'][1]['dimensions_argument'], [.11,.13,.085])
        clamp_sets = [[(x['points'], x['scalar_arguments']) for x in r['all_constructor_calls']
            if x.get('name') == 'S2Clamp'] for r in results.values()]
        self.assertTrue(all(x == clamp_sets[0] for x in clamp_sets))
        path = root/'opt/walker/manipulation_kinematics/lib/libs2_arm_kinematics.so'
        obj = InitializerArguments(path, 'arm')
        obj.build = dict(obj.build, start=obj.build['start']-1)
        with self.assertRaises(Exception):
            obj.extract()


if __name__ == '__main__':
    unittest.main()
