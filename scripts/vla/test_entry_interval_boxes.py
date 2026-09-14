import math
import unittest
import numpy as np

from entry_interval_boxes import multiply, poses_interval, trig_range
from test_entry_local_displacement_bounds import geometry
from prepare_vla_entry_bundle import common


class IntervalBoxTests(unittest.TestCase):
    def test_trigonometric_extrema_and_full_turn(self):
        lo,hi=trig_range(1.,2.)
        self.assertLessEqual(lo,min(math.sin(1),math.sin(2)))
        self.assertGreaterEqual(hi,1.)
        self.assertEqual(trig_range(-4,4),(-1.,1.))
        lo,hi=trig_range(2,4,True);self.assertLessEqual(lo,-1.)

    def test_interval_matrix_product_contains_signed_products(self):
        rng=np.random.default_rng(711)
        a=rng.normal(size=(4,4));b=rng.normal(size=(4,8))
        lo,hi=multiply((a-.2,a+.2),(b-.3,b+.3))
        for _ in range(100):
            p=(a+rng.uniform(-.2,.2,a.shape))@(b+rng.uniform(-.3,.3,b.shape))
            self.assertTrue((p>=lo-1e-14).all() and (p<=hi+1e-14).all())

    def test_three_dimensional_fk_is_enclosed_at_all_tested_corners(self):
        g=geometry(True);rng=np.random.default_rng(44)
        for _ in range(50):
            q=rng.uniform(-2,2,2);h=rng.uniform(.01,.2,2)
            result=poses_interval(g.joints,dict(zip(['a','b'],q)),dict(zip(['a','b'],h)))
            for delta in [[-h[0],-h[1]],[-h[0],h[1]],[h[0],-h[1]],[h[0],h[1]],[0,0]]:
                poses=common.fk.forward_kinematics(g.joints,dict(zip(['a','b'],q+delta)))
                for link in poses:
                    lo,hi=result[link]
                    self.assertTrue((poses[link]>=lo-1e-14).all())
                    self.assertTrue((poses[link]<=hi+1e-14).all())

    def test_invalid_angle_intervals_are_rejected(self):
        for a,b in [(2,1),(float('nan'),1),(0,float('inf'))]:
            with self.assertRaises(ValueError):trig_range(a,b)


if __name__=='__main__':unittest.main()
