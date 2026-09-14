import unittest
from runtime.metamove_head_probe import check_envelope, check_stop_cadence


class HeadProbeTests(unittest.TestCase):
    def test_single_stop_sample_does_not_qualify(self):
        self.assertFalse(check_stop_cadence([100.]))

    def test_five_second_cadence_accepted(self):
        self.assertTrue(check_stop_cadence([100.,105.]))

    def test_compatible_cadence(self):
        self.assertTrue(check_stop_cadence([100.,101.,102.]))

    def setUp(self):
        self.initial={'head_yaw_joint':0.,'head_pitch_joint':0.,'L_shoulder_roll_joint':0.}

    def test_only_reviewed_head_motion(self):
        q=dict(self.initial,head_pitch_joint=-.43)
        check_envelope(q,self.initial,self.initial)

    def test_unexpected_arm_motion(self):
        with self.assertRaises(RuntimeError):
            check_envelope(dict(self.initial,L_shoulder_roll_joint=.03),self.initial,self.initial)

    def test_wrong_head_axis_and_overshoot(self):
        for changes in ({'head_yaw_joint':-.43},{'head_pitch_joint':-.46},{'head_pitch_joint':float('nan')}):
            with self.assertRaises(RuntimeError):check_envelope(dict(self.initial,**changes),self.initial,self.initial)


if __name__=='__main__':unittest.main()
