import unittest
import math
from prepare_ready_head_hardware_limit import choose_pitch


class HeadHardwareTargetTests(unittest.TestCase):
    def test_retains_one_degree_enclosure(self):
        error=math.radians(1)
        target=choose_pitch(-.6510789706582119,-.65,.51,error)
        self.assertEqual(target,-.63)
        self.assertGreaterEqual(target-error,-.65)
        self.assertEqual(choose_pitch(-.43,-.65,.51,error),-.43)

    def test_upper_bound_rounds_inward(self):
        self.assertEqual(choose_pitch(.52,-.65,.51,math.radians(1)),.49)

    def test_invalid_or_impossible_domain(self):
        for args in ((0.,-.01,.01,.02),(float('nan'),-.65,.51,.01),
                     (0.,-.65,.51,-.01),(0.,1.,-1.,.01)):
            with self.assertRaises(ValueError):choose_pitch(*args)


if __name__=='__main__':unittest.main()
