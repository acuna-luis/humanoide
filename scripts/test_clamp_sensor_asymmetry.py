#!/usr/bin/env python3
import math
import unittest
from audit_clamp_sensor_asymmetry import bounds_witness


class BoundsWitnessTests(unittest.TestCase):
    def test_rectangle_witness(self):
        points = [(x,y,0) for x in (-2,2) for y in (-1,1)]
        self.assertAlmostEqual(bounds_witness(points,90)['outside_bound_mm'],1)
        self.assertTrue(bounds_witness(points,90)['non_symmetry_witness'])

    def test_zero_does_not_assert_symmetry(self):
        points = [(-1,-1,0),(1,-1,0),(1,1,0),(-1,1,0),(.2,.3,0)]
        r = bounds_witness(points,90)
        self.assertAlmostEqual(r['outside_bound_mm'],0)
        self.assertTrue(r['zero_is_not_proof_of_symmetry'])
        self.assertFalse(r['non_symmetry_witness'])

    def test_invalid(self):
        for points, angle in [([],0), ([(0,0,math.nan)],0), ([(0,0,0)],math.inf)]:
            with self.assertRaises(ValueError):
                bounds_witness(points,angle)


if __name__ == '__main__':
    unittest.main()
