import copy
import unittest
from plan_pico_home_offline import build
from cruzr_home_posture_gate import BODY_ACTUATOR_ALIASES

class PlanTests(unittest.TestCase):
    def setUp(self):
        self.names=['joint_'+str(i) for i in range(20)]
        self.joints=dict(name=self.names,position=[.3]*20,velocity=[0.]*20)
        self.act=dict(act_item=[dict(id=aliases[0],error_code=0,status=7,position=.3,velocity=0,cmd_pos=.3) for _,aliases in BODY_ACTUATOR_ALIASES])
        self.urdf='<robot>'+''.join(f'<joint name="{n}" type="revolute"><limit lower="-1" upper="1"/></joint>' for n in self.names)+'</robot>'
    def test_holds_body_during_arm_phase(self):
        r=build(self.joints,self.act,self.names,self.urdf)
        self.assertEqual(r['segments'][0]['end_rad'][14:],[.3]*6)
        self.assertFalse(r['executable'])
        for s in r['segments']:
            self.assertLessEqual(s['analytic_vmax_rad_s'],.15)
            self.assertLessEqual(s['analytic_amax_rad_s2'],.5)
    def test_rejects_bad_state(self):
        for change in ('moving','missing','nan','fault'):
            j=copy.deepcopy(self.joints);a=copy.deepcopy(self.act)
            if change=='moving':j['velocity'][0]=.2
            if change=='missing':j['position'].pop()
            if change=='nan':j['position'][0]=float('nan')
            if change=='fault':a['act_item'][0]['error_code']=1
            with self.subTest(change=change),self.assertRaises(ValueError):build(j,a,self.names,self.urdf)
    def test_rejects_outside_limits(self):
        self.joints['position'][0]=1.1
        with self.assertRaises(ValueError):build(self.joints,self.act,self.names,self.urdf)

if __name__=='__main__':unittest.main()
