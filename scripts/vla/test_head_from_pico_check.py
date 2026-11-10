import importlib.util
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / 'runtime'))
import head_from_pico_check as wrapper
import head_from_pico_readonly as monitor
import head_from_pico_candidate as candidate


def sample():
    return {'name': list(monitor.BODY), 'position': list(monitor.BODY.values()),
            'velocity': [0.0] * len(monitor.BODY)}


class HeadFromPicoCheckTests(unittest.TestCase):
    def test_run_rejected_before_remote_or_files(self):
        with patch.object(wrapper, 'check', side_effect=AssertionError('must not connect')):
            with patch('sys.stderr', new_callable=io.StringIO) as err:
                self.assertEqual(wrapper.main(['--run']), 2)
                self.assertIn('BLOQUEADO', err.getvalue())

    def test_candidate_blocked_before_creating_action_client(self):
        with self.assertRaisesRegex(RuntimeError, 'PHYSICAL_CONTROL_BLOCKED'):
            candidate.dispatch_after_qualification(None, None, None, None, None)

    def test_v4_posture_and_declared_pico_limits(self):
        row = sample()
        self.assertEqual(monitor.check_body(row)['R_elbow_yaw_joint'], -2.88)
        i = row['name'].index('R_elbow_yaw_joint')
        row['position'][i] = -2.89  # within 0.02 of the nominal but past declared -2.88872
        with self.assertRaisesRegex(ValueError, 'outside_declared'):
            monitor.check_body(row)
        row = sample()
        row['velocity'][0] = .002
        with self.assertRaisesRegex(ValueError, 'not_stationary'):
            monitor.check_body(row)

    def test_malformed_and_nonfinite_samples_fail_closed(self):
        row = sample()
        row['position'][0] = float('nan')
        with self.assertRaises(ValueError):
            monitor.check_body(row)
        row = sample()
        row['name'][1] = row['name'][0]
        with self.assertRaises(ValueError):
            monitor.check_body(row)
        with self.assertRaises(ValueError):
            monitor.check_hand({'name': [], 'position': [], 'velocity': []}, 'right')

    def test_fault_and_low_battery_rejected(self):
        actuators = {'act_item': [{'id': i, 'status': 4663, 'error_code': 0}
                                  for i in monitor.ACTUATOR_IDS]}
        monitor.check_actuators(actuators)
        actuators['act_item'][0]['error_code'] = 1
        with self.assertRaisesRegex(ValueError, 'actuator_fault'):
            monitor.check_actuators(actuators)
        monitor.check_battery({'batteries_states': [{'batsoc': 77}, {'batsoc': 79}]})
        with self.assertRaisesRegex(ValueError, 'battery_invalid'):
            monitor.check_battery({'batteries_states': [{'batsoc': 29}, {'batsoc': 79}]})

    def test_actions_active_are_not_idle(self):
        wrapper.action_status('status_list:\n- status: 5\n---\n')
        with self.assertRaisesRegex(ValueError, 'action_active'):
            wrapper.action_status('status_list:\n- status: 2\n---\n')

    def test_controller_states_fail_closed(self):
        good = "response: X.Response(controller=[{'name':'manipulation_controller','state':'running'}, {'name':'dexterous_hand_controller','state':'running'}, {'name':'vla_sdk_controller','state':'initialized'}, {'name':'sdk_controller','state':'initialized'}])"
        wrapper.controller_states(good)
        with self.assertRaisesRegex(ValueError, 'controller_not_expected'):
            wrapper.controller_states(good.replace("'initialized'", "'running'", 1))


if __name__ == '__main__':
    unittest.main()
