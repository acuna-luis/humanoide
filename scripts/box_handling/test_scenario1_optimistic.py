"""Optimistic execution boundaries; fake transports only, no robot access."""
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.box_handling import scenario1_cli as cli
from scripts.box_handling import scenario1_contract as contract
from scripts.box_handling import scenario1_runtime as runtime
from scripts.box_handling.test_scenario1_runtime import PROFILE, SimulatedRuntime


def optimistic_machine(directory):
    machine = SimulatedRuntime(directory)
    machine.policy = 'assume'
    machine.execution_profile = 'optimistic_v1'
    machine.checkpoint = contract.new_checkpoint(PROFILE, policy='assume',
                                                 execution_profile='optimistic_v1')
    machine.quick_health = Mock()
    # Exercise transition policy independently of the visual planner/transport.
    # The planner and its real stage entry are covered in test_scenario1_box_alignment.
    machine.align_box_for_pickup = Mock()
    return machine


class OptimisticStagesTest(unittest.TestCase):
    def test_replaces_seven_full_acquisitions_and_keeps_final_measured_home(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = optimistic_machine(directory)
            machine.health = Mock(wraps=machine.health)
            machine.discover = Mock(wraps=machine.discover)
            machine.hashes = Mock(wraps=machine.hashes)
            for stage in contract.STAGES:
                machine.stage({'stage': stage})
            self.assertEqual(machine.quick_health.call_count, 7)
            machine.health.assert_called_once_with(require_home=True)
            self.assertEqual(machine.discover.call_count, 8)
            self.assertEqual(machine.hashes.call_count, 8)
            self.assertIn('home_measured', machine.calls)
            self.assertEqual(machine.checkpoint['completed'], list(contract.STAGES))
            self.assertTrue(all(v['source'] == 'assumed'
                                for v in machine.checkpoint['confirmations'].values()))

    def test_grasp_failure_still_prevents_retreat_deposit_and_home(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = optimistic_machine(directory)
            machine.failure_task = 'local_front_box/separate_right_cruzr'
            with self.assertRaises(ValueError):
                for stage in contract.STAGES:
                    machine.stage({'stage': stage})
            self.assertEqual(machine.checkpoint['box_state'], 'unknown')
            self.assertNotIn('cruzr/mobot_back_20', machine.calls)
            self.assertNotIn('wrc_cruzr/put_cruzr_wrc_low', machine.calls)
            self.assertNotIn('cruzr/home', machine.calls)

    def test_live_fault_after_assumed_grasp_prevents_retreat(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = optimistic_machine(directory)
            for stage in contract.STAGES[:4]:
                machine.stage({'stage': stage})
            machine.quick_health.side_effect = RuntimeError('LIVE_HEALTH: stale actuator')
            with self.assertRaisesRegex(RuntimeError, 'stale actuator'):
                machine.stage({'stage': 'retreat'})
            self.assertNotIn('cruzr/mobot_back_20', machine.calls)
            self.assertEqual(machine.checkpoint['box_state'], 'unknown')

    def test_home_cannot_be_assumed_from_a_successful_action(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = optimistic_machine(directory)
            machine.fail_health_at = 'verify_home'
            with self.assertRaisesRegex(RuntimeError, 'Health'):
                for stage in contract.STAGES:
                    machine.stage({'stage': stage})
            self.assertNotIn('verify_home', machine.checkpoint['completed'])
            self.assertFalse(any(e['event'] == 'stage_complete' and e.get('stage') == 'verify_home'
                                 for e in machine.events))


class LiveRuntimeTest(unittest.TestCase):
    def machine(self):
        cp = contract.new_checkpoint(PROFILE, policy='assume', execution_profile='optimistic_v1')
        return runtime.Runtime(dict(checkpoint=cp, execution_profile='optimistic_v1',
                                    policy='assume'), emit=Mock())

    def test_wrong_payload_profile_is_rejected_remotely(self):
        cp = contract.new_checkpoint(PROFILE, policy='assume', execution_profile='optimistic_v1')
        with self.assertRaisesRegex(ValueError, 'execution profile'):
            runtime.Runtime(dict(checkpoint=cp, execution_profile='standard_v1'))
        cp = contract.new_checkpoint(PROFILE, policy='assume')
        with self.assertRaisesRegex(ValueError, 'execution profile'):
            runtime.Runtime(dict(checkpoint=cp, execution_profile='optimistic_v1'))

    def test_readonly_benchmark_compares_acquisition_with_live_transition(self):
        machine = self.machine()
        machine.payload['mode'] = 'check'
        for method in ('connected', 'discover', 'hashes', 'health', 'quick_health', 'read_poses'):
            setattr(machine, method, Mock())
        expected = ('utars_nav_map', 'FSM_WAITNAVIGATE')
        machine.map_state = Mock(return_value=expected)
        machine.action = Mock(side_effect=AssertionError('No physical action'))
        machine.benchmark_checks(1, expected)
        machine.health.assert_called_once_with(require_home=True)
        machine.quick_health.assert_called_once_with()
        machine.action.assert_not_called()

    def test_fast_health_never_falls_back_to_a_previous_ok(self):
        machine = self.machine()
        machine.health = Mock(side_effect=AssertionError('No fallback acquisition'))
        with self.assertRaisesRegex(RuntimeError, 'NOT_ARMED'):
            machine.quick_health()
        machine.live_monitor_enabled = True
        machine.connected = Mock()
        machine.check_live_health = Mock(side_effect=ValueError('latched E-stop'))
        with patch.object(runtime.time, 'sleep', side_effect=AssertionError('Do not wait after fault')):
            with self.assertRaisesRegex(ValueError, 'latched E-stop'):
                machine.quick_health()

    def test_transition_waits_only_for_post_result_actuators(self):
        machine = self.machine()
        machine.live_monitor_enabled = True
        machine.last_action_end_ns = 900
        machine.connected = Mock()
        machine.check_live_health = Mock(side_effect=[runtime.live_health.LiveHealthPending('settling'), {}])
        with patch.object(runtime.time, 'sleep') as wait:
            machine.quick_health()
        wait.assert_called_once_with(.01)
        self.assertEqual(machine.check_live_health.call_count, 2)
        machine.check_live_health.assert_called_with(stationary=True, after_ns=900)

    def test_watchdog_revokes_live_control_lease_during_a_fault(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = self.machine()
            machine.session = Path(directory)
            machine.live_monitor_enabled = True
            machine.check_live_health = Mock(side_effect=ValueError('controller changed'))
            with patch.object(machine.stop, 'wait', return_value=False):
                machine.watchdog()
            self.assertTrue(machine.stop.is_set())
            self.assertEqual(json.loads((machine.session/'control-lease.json').read_text())['deadline'], 0)
            self.assertTrue((machine.session/'stop').exists())


class OptimisticCliTest(unittest.TestCase):
    def test_plan_has_own_profile_and_name_without_connections_or_prompts(self):
        with patch.object(cli, 'Connection', side_effect=AssertionError('No network')), \
                patch.object(cli.subprocess, 'run', side_effect=AssertionError('No commands')), \
                patch('builtins.input', side_effect=AssertionError('No prompts')), \
                patch('sys.stdout', io.StringIO()) as output:
            self.assertEqual(cli.main(['--plan'], policy='assume', execution_profile='optimistic_v1'), 0)
        plan = json.loads(output.getvalue()[output.getvalue().index('{'):])
        self.assertEqual(plan['execution_profile'], 'optimistic_v1')
        self.assertEqual(plan['policy'], 'assume')
        self.assertEqual(plan['stages'], list(contract.STAGES))
        self.assertEqual(cli.parser('assume', 'optimistic_v1').prog, 'optimistic_scenario1.sh')
        for policy in ('ask', 'sensors'):
            with self.assertRaises(ValueError):
                cli.parser(policy, 'optimistic_v1')

    def test_resume_from_standard_is_rejected_before_any_connection(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'checkpoint.json'
            original = contract.new_checkpoint(PROFILE, policy='assume')
            path.write_text(json.dumps(original))
            before = path.read_bytes()
            with patch.object(cli, 'Connection', side_effect=AssertionError('No network')), \
                    patch('sys.stdout', io.StringIO()):
                with self.assertRaisesRegex(ValueError, '[Ee]xecution profile'):
                    cli.main(['--resume', str(path), '--plan', '--profile',
                              str(cli.HERE/'scenario1_current_geometry.json')], policy='assume',
                             execution_profile='optimistic_v1')
            self.assertEqual(path.read_bytes(), before)
            self.assertFalse(path.with_name(path.name+'.consumed.json').exists())

    def test_transmitted_health_source_loads_pure_validators_in_dependency_order(self):
        checkpoint = contract.new_checkpoint(PROFILE, policy='assume', execution_profile='optimistic_v1')
        payload = cli.make_payload('check', PROFILE, checkpoint)
        compile(payload['health_worker'], 'health-worker-payload', 'exec')
        names = [name for name, _ in payload['modules']]
        self.assertLess(names.index('scenario1_checks'), names.index('scenario1_live_health'))
        self.assertLess(names.index('scenario1_live_health'), names.index('scenario1_runtime'))
        self.assertIn('scenario1_live_health', payload['health_worker'])


if __name__ == '__main__':
    unittest.main()
