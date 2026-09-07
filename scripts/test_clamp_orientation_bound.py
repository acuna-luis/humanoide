import itertools
import json
import math
import unittest

from audit_clamp_orientation_bound import ROOT, audit, radius_about_origin


class OrientationBoundTests(unittest.TestCase):
    def test_nominal_radius_and_no_physical_transform(self):
        c = json.loads((ROOT/'config/clamp_mount_requalification.json').read_text())
        result = audit(c)
        self.assertAlmostEqual(result['nominal_radius_m'], math.hypot(.047, .055, .095))
        for key in ('center_in_L_sixforce_link_m', 'center_in_R_sixforce_link_m', 'safe_radius_m'):
            self.assertIsNone(result[key])
        self.assertFalse(result['physical_authorized'])
        self.assertEqual(result['trajectories_evaluated'], [])

    def test_rotated_corners_remain_in_sphere(self):
        bounds = [[-.035, -.055, -.035], [.047, .045, .095]]
        radius, _ = radius_about_origin(bounds)
        for p in itertools.product(*zip(*bounds)):
            for angle in range(0, 360, 7):
                a = math.radians(angle)
                x, y, z = p
                x, y = x*math.cos(a)-y*math.sin(a), x*math.sin(a)+y*math.cos(a)
                y, z = y*math.cos(a)-z*math.sin(a), y*math.sin(a)+z*math.cos(a)
                self.assertLessEqual(math.hypot(x, y, z), radius+1e-14)

    def test_invalid_bounds(self):
        for bounds in (None, [[0,0,0],[0,1,1]], [[0,0,0],[True,1,1]],
                       [[0,0,0],[1,1,float('nan')]]):
            with self.assertRaises(ValueError):
                radius_about_origin(bounds)


if __name__ == '__main__':
    unittest.main()
