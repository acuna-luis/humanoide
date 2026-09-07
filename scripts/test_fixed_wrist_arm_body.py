import unittest
from audit_fixed_wrist_arm_body import gap


class GapTests(unittest.TestCase):
    def test_separated(self):
        self.assertEqual(gap(([0,0,0], [1,1,1]), ([4,1,1], [5,2,2])), 3)

    def test_touch_overlap(self):
        for b in (([1,0,0], [2,1,1]), ([.5,.5,.5], [2,2,2])):
            self.assertEqual(gap(([0,0,0], [1,1,1]), b), 0)

    def test_invalid(self):
        for a in (([2,0,0], [1,1,1]), ([float('nan'),0,0], [1,1,1])):
            with self.assertRaises(ValueError):
                gap(a, ([0,0,0], [1,1,1]))


if __name__ == '__main__':
    unittest.main()
