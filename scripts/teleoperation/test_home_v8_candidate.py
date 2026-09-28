"""Offline candidate checks; no robot connection or motion."""
import unittest
from review_home_v8_early_roll import check_structure, path_for
from cruzr_pico_to_home_owner_gate import PICO_REFERENCE


class CandidateTest(unittest.TestCase):
    def test_timing_and_only_first_opening_split_changes(self):
        check_structure()

    def test_recorded_out_of_limit_shoulder_enters_interval(self):
        q=[0.0]*20
        q[3]=.11687016127703728
        q[0]=-.0709466114397109
        first=path_for('arms_first')(q)[1]
        self.assertLess(first[3],.0987266)
        self.assertAlmostEqual(first[3],.06687016127703728)
        self.assertAlmostEqual(first[0],q[0]-.03)
        self.assertEqual(first[14:],q[14:])

    def test_opened_and_final_targets_match_v7(self):
        for q in ([0.0]*20,list(PICO_REFERENCE)):
            for order in ('body_first','arms_first'):
                points=path_for(order)(q)
                both=points[3]
                for i in range(14):
                    delta=-.2 if i in (3,10) else -.03 if i in (0,7) else 0
                    self.assertAlmostEqual(both[i],q[i]+delta)
                self.assertEqual(both[14:],[0.0]*6)
                self.assertEqual(points[-1],[0.0]*20)


if __name__=='__main__':unittest.main()
