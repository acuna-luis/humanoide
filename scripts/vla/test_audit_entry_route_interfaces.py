import unittest
import numpy as np
from audit_entry_route_interfaces import interface_domain


class InterfaceDomainTests(unittest.TestCase):
    def test_route_and_error_included_with_joint_limit_intersection(self):
        lo,hi=interface_domain([[.2,-.4],[.8,.6]],[1,0],[-1,-1],[1,1],.3)
        np.testing.assert_allclose(lo,[-.7,-.1])
        np.testing.assert_allclose(hi,[.9,1.])

    def test_reject_bad_route_or_error(self):
        for path,error in [([[np.nan]],0),([[2]],0),([[0]],-1)]:
            with self.assertRaises(ValueError):interface_domain(path,[0],[-1],[1],error)


if __name__=='__main__':unittest.main()
