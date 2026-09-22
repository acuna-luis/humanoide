import math
import unittest
import subprocess
import sys
from pathlib import Path
from scripts.box_handling.front_nudge import target_for, displacement, check_corridor

class NudgeTest(unittest.TestCase):
    def test_known_failed_route_cannot_be_retried(self):
        result=subprocess.run([sys.executable,str(Path(__file__).with_name('front_nudge.py')),
                               '--run','--physical-confirmed'],capture_output=True,text=True)
        self.assertEqual(result.returncode,2)
        self.assertIn('Run blocked after reverse-motion trial',result.stderr)
    def test_target_is_five_cm_in_current_heading(self):
        for a in (0, math.pi/2, -3.08):
            p=dict(position=dict(x=1.,y=2.),orientation=dict(x=0.,y=0.,z=math.sin(a/2),w=math.cos(a/2)))
            t=target_for(p)
            d=displacement((1.,2.,a),(t['point_x'],t['point_y'],t['point_yaw']))
            self.assertAlmostEqual(d[0],.05);self.assertAlmostEqual(d[1],0);self.assertAlmostEqual(d[2],0)
            check_corridor(d)
    def test_nonfinite_invalid_orientation_and_detours_fail(self):
        for d in ((.061,0,0),(0,.013,0),(0,0,math.radians(2.1)),(-.006,0,0),(math.nan,0,0)):
            with self.assertRaises(ValueError):check_corridor(d)
        for q in (dict(x=0,y=0,z=0,w=0),dict(x=math.nan,y=0,z=0,w=1)):
            with self.assertRaises(ValueError):target_for(dict(position=dict(x=0,y=0),orientation=q))
