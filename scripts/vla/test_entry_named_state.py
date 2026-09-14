import copy
import unittest
from unittest.mock import patch
from runtime.entry410_single_stage_remote import named_values
from prepare_home_ready_access import JOINT_ORDER, measured_named_start


class NamedStateTests(unittest.TestCase):
    def message(self):
        return dict(name=list(JOINT_ORDER), position=[i*.01 for i in range(20)], velocity=[0.]*20)

    def test_order_is_by_name(self):
        m=self.message(); expected=named_values(m,JOINT_ORDER)
        for field in ('name','position','velocity'):m[field].reverse()
        self.assertEqual(named_values(m,JOINT_ORDER),expected)

    def test_missing_duplicate_nonfinite_and_lengths(self):
        for kind in ('missing','duplicate','nan','length'):
            m=self.message()
            if kind=='missing':m['name'][0]='unknown'
            if kind=='duplicate':m['name'][0]=m['name'][1]
            if kind=='nan':m['position'][0]=float('nan')
            if kind=='length':m['velocity'].pop()
            with self.subTest(kind=kind),self.assertRaises(ValueError):named_values(m,JOINT_ORDER)

    def test_motor_positions_do_not_define_geometry(self):
        samples=[]
        for i in range(2):
            m=self.message();m['header']={'stamp':{'sec':10,'nanosec':i*100_000_000}}
            samples.append(dict(received_monotonic=10+i*.1,messages={
                '/mc/whole_joint_states':m,'/mc/actuator_state':{'header':copy.deepcopy(m['header'])}}))
        capture=dict(schema='cruzr-entry-named-state-capture-v1',robot_commands=0,samples=samples)
        health={n:dict(position=-100.,velocity=0.,error_code=0,status=7) for n in JOINT_ORDER}
        with patch('prepare_home_ready_access.decode_actuators',return_value=(None,health)):
            self.assertEqual(measured_named_start(capture),self.message()['position'])
            health[JOINT_ORDER[0]]['status']=0
            with self.assertRaises(ValueError):measured_named_start(capture)


if __name__=='__main__':unittest.main()
