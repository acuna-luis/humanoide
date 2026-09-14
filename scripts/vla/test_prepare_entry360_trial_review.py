import unittest
import numpy as np
from prepare_entry360_trial_review import cubic_proposal


class CubicProposalTests(unittest.TestCase):
    def test_actual_large_lifter_change_obeys_design_caps(self):
        a=np.zeros(20);b=a.copy();b[17]=2.1556265354156494
        proposal=cubic_proposal(a,b)
        self.assertEqual(proposal['duration_seconds'],65)
        # Differentiate the polynomial across its whole normalized interval.
        u=np.linspace(0,1,10001);duration=proposal['duration_seconds']
        self.assertLessEqual(np.max(abs(b[17]*(6*u-6*u*u)/duration)),.05)
        self.assertLessEqual(np.max(abs(b[17]*(6-12*u)/duration**2)),.05)
        self.assertFalse(proposal['installable'])
        self.assertIsNone(proposal['global_jerk_bound'])

    def test_stationary_and_invalid_inputs(self):
        self.assertEqual(cubic_proposal(np.zeros(20),np.zeros(20))['duration_seconds'],0)
        for bad in [np.zeros(19),np.full(20,np.nan)]:
            with self.assertRaises(ValueError):cubic_proposal(np.zeros(20),bad)


if __name__=='__main__':unittest.main()
