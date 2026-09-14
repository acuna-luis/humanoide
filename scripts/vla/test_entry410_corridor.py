import unittest
import math
from runtime.entry410_single_stage_remote import check_segment_corridor
from entry410_stage_contract import check_position_tolerances


class CorridorTests(unittest.TestCase):
    def setUp(self):
        self.stage=dict(joint_order=['a','b','fixed'], start=[0.,1.,.1], end=[1.,-1.,.1])

    def check(self, a, b, fixed=.1):
        return check_segment_corridor(self.stage, dict(a=[a,0],b=[b,0],fixed=[fixed,0]),.01,.005)

    def test_synchronized_opposite_directions(self):
        lo,hi=self.check(.5,0);self.assertLessEqual(lo,.5);self.assertGreaterEqual(hi,.5)

    def test_inside_joint_boxes_but_off_path_rejected(self):
        with self.assertRaises(RuntimeError):self.check(.1,-.8)

    def test_tracking_noise_with_common_progress(self):
        self.check(.505,-.004)

    def test_stationary_deviation_rejected(self):
        with self.assertRaises(RuntimeError):self.check(.5,0,.11)

    def test_endpoints_and_overshoot(self):
        self.check(0,1);self.check(1,-1)
        with self.assertRaises(RuntimeError):self.check(1.02,-1.04)

    def test_nonfinite_rejected(self):
        with self.assertRaises(RuntimeError):self.check(float('nan'),0)
        with self.assertRaises(ValueError):check_segment_corridor(self.stage,{},float('nan'),.005)

    def test_tolerances_cannot_exceed_geometry(self):
        stage=dict(geometry_joint_error_rad=math.pi/180)
        record=dict(position_tolerance_rad=.01,stationary_joint_tolerance_rad=.005)
        check_position_tolerances(record,stage)
        for key in record:
            bad=dict(record);bad[key]=.02
            with self.assertRaises(ValueError):check_position_tolerances(bad,stage)
        with self.assertRaises(ValueError):check_position_tolerances(record,{})


if __name__=='__main__':unittest.main()
