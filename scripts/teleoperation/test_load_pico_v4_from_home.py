"""Simulated preflight and RPC cases; never connect to the robot."""
from contextlib import ExitStack
import itertools
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from scripts.teleoperation import load_pico_v4_from_home as m


class FakeTransport:
    def __init__(self, evidence): self.ros_container='fake-ros'
    def run(self, host, command, timeout=120): return m.SHA+'  config'

class FakeMonitor:
    def __init__(self,*args): self.faults=[]; self.processes=[]
    def check(self): pass
    def close(self): pass

class LoadModeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.stack=ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(m,'ROOT',Path(self.tmp.name)/'repo'))
        item={'State':{'Running':True},'RestartCount':0,'Id':'test',
              'Config':{'Env':['HW_TYPE=cruzr_s2_v1_sps','TELE_DEVICE=pico','transmit=local']}}
        snap={'motion':{'containers':{'motion.manipulation_robot_app':item,'motion.hw':item},'active_session':None},
              'vision':{'containers':{'system.control_center':item},'active_session':None}}
        self.stack.enter_context(patch.object(m,'Transport',FakeTransport))
        self.stack.enter_context(patch.object(m,'snapshots',return_value=snap))
        self.stack.enter_context(patch.object(m,'loaded',return_value=True))
        self.safe=self.stack.enter_context(patch.object(m,'safety'))
        self.battery=self.stack.enter_context(patch.object(m,'battery',return_value=[80,80]))
        self.stack.enter_context(patch.object(m,'pose',side_effect=lambda *a: (['MEASURED_HOME=1'],next(self.stamps))))
        self.stamps=itertools.count(100)
        self.topic=self.stack.enter_context(patch.object(m,'read_topic',side_effect=lambda t,n:
            'locked: false' if 'module_lock' in n else 'status_list: []\n'))
        self.hands=self.stack.enter_context(patch.object(m,'hands'))
        self.stack.enter_context(patch.object(m,'run_local',return_value='OK'))
        self.stack.enter_context(patch.object(m,'Monitor',FakeMonitor))
        self.stack.enter_context(patch.object(m,'sample_still',side_effect=[(['stable'],200),(['stable'],201)]))
        self.stack.enter_context(patch.object(m.time,'sleep'))
        clock=itertools.count(0,20)
        self.stack.enter_context(patch.object(m.time,'monotonic',side_effect=lambda:next(clock)))
        self.stack.enter_context(patch.object(m.subprocess,'run',side_effect=lambda args,**kwargs:
            SimpleNamespace(returncode=0 if 'probar_pico_v4.sh' in ' '.join(args) else
                            (3 if args[0]=='systemctl' else 1),stdout='ok',stderr='')))
        self.calls=[]
        self.switch_error=None
        def call(method,params):
            self.calls.append(method)
            if method=='cc.api.work_mode.switch':
                if self.switch_error: raise self.switch_error
                return {'result':{}}
            if method=='cc.api.status.get':
                return {'result':{'workMode':'teleop' if 'cc.api.work_mode.switch' in self.calls else 'joystick'}}
            raise AssertionError(method)
        self.stack.enter_context(patch.object(m,'call',side_effect=call))

    def run_mode(self,*args):
        with patch.object(sys,'argv',['mode',*args]): return m.main()

    def test_run_without_physical_confirmation_rejects_before_preflight(self):
        with self.assertRaises(SystemExit): self.run_mode('--run')
        self.assertEqual(self.calls,[])
        self.safe.assert_not_called()

    def test_check_never_switches(self):
        self.assertEqual(self.run_mode('--check'),0)
        self.assertNotIn('cc.api.work_mode.switch',self.calls)

    def test_failed_preflight_does_not_switch(self):
        self.battery.return_value=[29,80]
        self.assertEqual(self.run_mode('--run','--physical-confirmation',
                         'MANOS VACIAS HOME ZONA LIBRE PAROS PERSONA'),1)
        self.assertNotIn('cc.api.work_mode.switch',self.calls)

    def test_switch_occurs_only_once(self):
        self.assertEqual(self.run_mode('--run','--physical-confirmation',
                         'MANOS VACIAS HOME ZONA LIBRE PAROS PERSONA'),0)
        self.assertEqual(self.calls.count('cc.api.work_mode.switch'),1)

    def test_uncertain_rpc_failure_does_not_retry(self):
        self.switch_error=TimeoutError('injected timeout')
        self.assertEqual(self.run_mode('--run','--physical-confirmation',
                         'MANOS VACIAS HOME ZONA LIBRE PAROS PERSONA'),1)
        self.assertEqual(self.calls.count('cc.api.work_mode.switch'),1)

    def test_action_message_requires_valid_idle_structure(self):
        for text in ('', 'status_list:', 'status_list: []\nstatus: 2',
                     'status_list:\n- goal_info:\n  status: 1\n',
                     'status_list:\n- goal_info:\n  status: 0\n',
                     'status_list: []\n- goal_info:\n  status: 4\n'):
            with self.subTest(text=text),self.assertRaises(RuntimeError): m.action_idle(text)
        m.action_idle('status_list: []\n')
        m.action_idle('status_list:\n- goal_info:\n  status: 4\n')

if __name__=='__main__': unittest.main()
