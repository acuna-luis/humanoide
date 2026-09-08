import unittest
import numpy as np
from audit_clamp_continuous_routes import fractions, travel_bound
from audit_clamp_orientation_bound import radius_about_origin


class ContinuousBoundsTests(unittest.TestCase):
    def test_schedule_breakpoints(self):
        self.assertEqual(fractions(.5, 'left_first'), [1, 0])
        self.assertEqual(fractions(.5, 'right_first'), [0, 1])
        for s in ('simultaneous', 'left_first', 'right_first'):
            self.assertEqual(fractions(0, s), [0, 0])
            self.assertEqual(fractions(1, s), [1, 1])

    def test_angular_and_prismatic_travel(self):
        joints = [dict(name='r', type='revolute'),
                  dict(name='p', type='prismatic', axis=np.array([0, 0, 1]))]
        self.assertAlmostEqual(travel_bound({'r': -.2, 'p': .03}, joints, 2), .43)

    def test_rotating_point_containment(self):
        joints = [dict(name='r', type='revolute')]
        for angle in np.linspace(-3, 3, 101):
            chord = np.linalg.norm([2*np.cos(angle)-2, 2*np.sin(angle)])
            self.assertLessEqual(chord, travel_bound({'r': angle}, joints, 2)+1e-12)

    def test_reported_tool_radius(self):
        radius, _ = radius_about_origin([[-.035, -.055, -.035], [.047, .045, .095]])
        self.assertAlmostEqual(radius, np.linalg.norm([.047, .055, .095]))


if __name__ == '__main__':
    unittest.main()
