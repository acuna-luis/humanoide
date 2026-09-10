import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
import plan_clamp_home_adaptive as adaptive


class AdaptiveHomeTests(unittest.TestCase):
    def plan(self,q,v=None):
        return adaptive.plan(q,[0.]*20 if v is None else v)

    def test_pico_opens_less_and_preserves_non_roll_positions(self):
        q=adaptive.PICO_REFERENCE[:14]+[0.]*6
        p=self.plan(q)
        self.assertEqual(p['steps'][0]['name'],'open_only_missing_clearance')
        opened=p['steps'][0]['end']
        for i in range(20):
            self.assertEqual(opened[i],-.5 if i in adaptive.ROLLS else q[i])
        self.assertLess(p['nominal_seconds'],16.)
        self.assertFalse(p['physical_approval'])
        self.assertFalse(p['installable'])

    def test_asymmetric_opening_never_adds_delta_to_already_open_arm(self):
        q=adaptive.PICO_REFERENCE[:14]+[0.]*6
        q[3],q[10]=-.6,-.3
        steps=self.plan(q)['steps']
        self.assertEqual(steps[0]['end'][3],-.6)
        self.assertEqual(steps[0]['end'][10],-.5)
        for s in steps[:-1]:
            self.assertEqual(s['end'][3],-.6)
            self.assertEqual(s['end'][10],-.5)

    def test_already_open_pico_skips_opening_and_retains_each_roll(self):
        q=adaptive.PICO_REFERENCE[:14]+[0.]*6
        q[3],q[10]=-.55,-.62
        steps=self.plan(q)['steps']
        self.assertEqual(steps[0]['name'],'lower_with_opening_preserved')
        self.assertEqual(steps[0]['end'][3],q[3])
        self.assertEqual(steps[0]['end'][10],q[10])

    def test_home_is_noop_and_down_arms_do_not_rise_to_pico(self):
        self.assertEqual(self.plan([0.]*20)['steps'],[])
        q=[0.]*20;q[3],q[10]=-.5,-.6
        steps=self.plan(q)['steps']
        self.assertEqual([s['name'] for s in steps],['close_only_lowered_arms'])
        for s in steps:
            self.assertTrue(all(s['end'][i]==0 for i in adaptive.ARM_SHAPE_INDICES))

    def test_flexed_body_opens_before_reset_and_closes_last(self):
        q=[0.]*14+adaptive.PICO_REFERENCE[14:]
        p=self.plan(q)
        self.assertEqual([s['name'] for s in p['steps']],
                         ['open_only_missing_clearance','body_home_with_arm_posture_preserved','close_only_lowered_arms'])
        self.assertEqual(p['steps'][0]['end'][14:],q[14:])
        self.assertEqual(p['steps'][1]['end'][3],-.5)
        self.assertEqual(p['steps'][1]['end'][10],-.5)

    def test_tiny_body_error_is_corrected_not_declared_exact_home(self):
        q=adaptive.PICO_REFERENCE[:14]+[0.]*6;q[14]=-.003
        stages=self.plan(q)['steps']
        body=[s for s in stages if s['name']=='body_home_with_arm_posture_preserved']
        self.assertEqual(len(body),1)
        self.assertGreaterEqual(body[0]['seconds'],1.)
        self.assertEqual(body[0]['end'][14:],[0.]*6)

    def test_each_step_continuous_and_caps_hold_for_boundary_postures(self):
        for arm in (adaptive.PICO_REFERENCE[:14],[0.]*14):
            for body in ([0.]*6,adaptive.PICO_REFERENCE[14:]):
                for left,right in [(0.02,0.02),(-.65,-.65),(-.25,-.6)]:
                    q=arm+body;q[3],q[10]=left,right
                    p=self.plan(q); last=q
                    for s in p['steps']:
                        self.assertEqual(s['start'],last)
                        peaks=adaptive.Step(**s).stage().peaks()
                        for key,limit in adaptive.CAPS.items():
                            self.assertLessEqual(float(peaks[key].max()),limit+1e-12)
                        last=s['end']
                    self.assertEqual(last,[0.]*20)

    def test_unknown_nonfinite_asymmetric_and_moving_states_rejected(self):
        q=adaptive.PICO_REFERENCE[:14]+[0.]*6
        for i,x in [(0,0.),(7,0.),(17,.25),(3,-.7),(3,.021),
                    (5,float('nan')),(5,float('inf')),(5,True)]:
            changed=q.copy();changed[i]=x
            with self.assertRaises(ValueError):self.plan(changed)
        v=[0.]*20;v[3]=.0021
        with self.assertRaises(ValueError):self.plan(q,v)
        with self.assertRaises(ValueError):self.plan(q[:-1])


if __name__=='__main__':unittest.main()
