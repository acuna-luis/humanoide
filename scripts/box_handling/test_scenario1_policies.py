"""Offline policy integration: no prompts, no fake sensing, unchanged commands."""
import copy
import io
import json
import queue
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.box_handling import scenario1_cli as cli
from scripts.box_handling import scenario1_contract as contract
from scripts.box_handling import scenario1_runtime as runtime
from scripts.box_handling.test_scenario1_runtime import PROFILE, SimulatedRuntime, advance
from scripts.box_handling.test_scenario1_sensors import profile as sensor_fixture, snapshot as sensor_snapshot, NOW


class PolicyRuntimeTest(unittest.TestCase):
    def machine(self, directory, policy):
        machine = SimulatedRuntime(directory)
        machine.policy = policy
        machine.checkpoint = contract.new_checkpoint(PROFILE, policy=policy)
        return machine

    def test_assume_runs_same_cycle_and_records_assumptions(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = self.machine(directory, 'assume')
            for stage in contract.STAGES:
                machine.stage({'stage': stage})
            self.assertEqual(machine.checkpoint['box_state'], 'released')
            self.assertTrue(all(record['source'] == 'assumed' and record['sensor_evidence'] is None
                                for record in machine.checkpoint['confirmations'].values()))
            self.assertIn('home_measured', machine.calls)

    def test_assume_never_overrides_explicit_action_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = self.machine(directory, 'assume')
            machine.failure_task = 'local_front_box/separate_right_cruzr'
            with self.assertRaises(ValueError):
                advance(machine)
            self.assertEqual(machine.checkpoint['box_state'], 'unknown')
            self.assertNotIn('cruzr/mobot_back_20', machine.calls)
            self.assertNotIn('cruzr/home', machine.calls)

    def test_sensor_gate_uses_runtime_measurement_not_pc_assertion(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = self.machine(directory, 'sensors')
            machine.sensor_stream_alive = Mock()
            machine.verify_sensors = Mock(side_effect=ValueError('actual load contradicts held'))
            for stage in contract.STAGES[:3]:
                machine.stage({'stage': stage})
            with self.assertRaisesRegex(ValueError, 'contradicts'):
                machine.stage({'stage': 'verify_held', 'confirmed_box': 'held',
                               'sensor_evidence': {'forged': True}})
            self.assertEqual(machine.checkpoint['box_state'], 'unknown')
            self.assertEqual(machine.checkpoint['confirmations'], {})
            self.assertNotIn('cruzr/mobot_back_20', machine.calls)

    def test_sensor_policy_rechecks_load_before_transport_and_home(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = self.machine(directory, 'sensors')
            machine.sensor_stream_alive = Mock()
            machine.verify_sensors = Mock(side_effect=lambda state: {'state': state, 'measured': True})
            advance(machine)
            self.assertEqual([call.args[0] for call in machine.verify_sensors.call_args_list],
                             ['held', 'held', 'held', 'held', 'released', 'released'])
            self.assertTrue(all(record['source'] == 'sensors'
                                for record in machine.checkpoint['confirmations'].values()))

    def test_lost_sensor_process_blocks_commands(self):
        machine = runtime.Runtime({'checkpoint': contract.new_checkpoint(PROFILE, policy='sensors')})
        machine.armed = True
        with self.assertRaisesRegex(RuntimeError, 'SENSOR_WORKER_LOST'):
            machine.connected()

    def test_contradictory_sensor_window_is_not_retried(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = self.machine(directory, 'sensors')
            machine.payload['sensor_profile'] = sensor_fixture()
            sample = sensor_snapshot()
            sample['ft']['left'][-1]['force'][2] = 900.
            (Path(directory)/'sensors.json').write_text(json.dumps(sample))
            machine.sensor_stream_alive = Mock()
            with patch.object(runtime.time, 'time_ns', return_value=NOW), \
                    patch.object(runtime.time, 'sleep', side_effect=AssertionError('No retry after contradiction')):
                with self.assertRaisesRegex(ValueError, 'outside'):
                    machine.verify_sensors('held')

    def test_sensor_window_waits_only_for_fresh_acquisition(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = self.machine(directory, 'sensors')
            machine.payload['sensor_profile'] = sensor_fixture()
            sample = sensor_snapshot()
            target = Path(directory)/'sensors.json'
            partial = copy.deepcopy(sample)
            partial['ft']['left'] = partial['ft']['left'][-2:]
            target.write_text(json.dumps(partial))
            machine.sensor_stream_alive = Mock()
            with patch.object(runtime.time, 'time_ns', return_value=NOW), \
                    patch.object(runtime.time, 'sleep', side_effect=lambda _: target.write_text(json.dumps(sample))) as wait:
                report = machine.verify_sensors('held')
                self.assertEqual(report['state'], 'held')
                wait.assert_called_once_with(.025)


class AutomaticCliTest(unittest.TestCase):
    def test_blocked_correction_without_attempt_displays_residual_and_preserves_error(self):
        connection = cli.Connection.__new__(cli.Connection)
        connection.events = queue.Queue()
        revoked = dict(runtime.nav_correction.qualification_report(), motion_enabled=False,
                       status='blocked', reason_code='GET1_CORRECTION_UNQUALIFIED', reason='synthetic revocation')
        connection.events.put(dict(event='get1_correction', phase='blocked_before_dispatch',
            qualification=revoked,
            measurements=[dict(distance_m=.027319, yaw_error_deg=.385),
                          dict(distance_m=.027318, yaw_error_deg=.387)]))
        connection.events.put(dict(event='error', reason='GET1_CORRECTION_UNQUALIFIED: test'))
        with patch('sys.stdout', io.StringIO()) as output, \
                self.assertRaisesRegex(RuntimeError, 'GET1_CORRECTION_UNQUALIFIED'):
            connection.wait('stage_complete', timeout=1)
        self.assertIn('Ajuste get1 no enviado', output.getvalue())
        self.assertIn('27.32 mm / 0.387 grados', output.getvalue())
        self.assertIn('Agarre no iniciado', output.getvalue())

    def test_pending_sensor_calibration_stops_before_any_network_or_motion(self):
        with patch.object(cli, 'Connection') as connection, patch.object(cli.subprocess, 'run') as command, \
                patch('builtins.input', side_effect=AssertionError('Unexpected prompt')):
            with self.assertRaisesRegex(ValueError, 'qualification is pending'):
                cli.main(['--run'], policy='sensors')
            connection.assert_not_called()
            command.assert_not_called()

    def test_each_plan_reports_fixed_policy_without_network_or_prompts(self):
        for policy in ('ask', 'assume', 'sensors'):
            with self.subTest(policy=policy), patch('builtins.input', side_effect=AssertionError('prompt')), \
                    patch.object(cli, 'Connection', side_effect=AssertionError('network')), \
                    patch('sys.stdout', io.StringIO()) as output:
                self.assertEqual(cli.main(['--plan'], policy=policy), 0)
                self.assertIn('"policy": "'+policy+'"', output.getvalue())
                report = json.loads(output.getvalue()[output.getvalue().index('{'):])
                correction = report['get1_correction']
                self.assertIs(correction['motion_enabled'], True)
                self.assertEqual(correction['status'], 'enabled_for_validation')
                self.assertEqual(correction['physical_validation'], 'pending')
                self.assertEqual(correction['policy']['action_timeout_s'], 30)
                self.assertEqual(correction['policy']['total_budget_s'], 70)
                self.assertEqual(correction['policy']['max_approach_angular_speed_rad_s'], .6)
                self.assertEqual(correction['policy']['max_angular_speed_rad_s'], 1.2)

    def simulate_automatic_cli(self, policy):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root/'run'
            sensor_path = root/'synthetic-sensors.json'
            sensor_path.write_text(json.dumps(sensor_fixture()))

            class OfflineConnection:
                def __init__(self, payload, wifi, location):
                    self.checkpoint = copy.deepcopy(payload['checkpoint'])
                    self.evidence = location
                    self.stage = None
                    self.process = Mock()
                    self.process.wait.return_value = 0

                def send(self, message):
                    if message['command'] == 'stage':
                        stage = self.stage = message['stage']
                        cp = contract.begin_stage(self.checkpoint, stage)
                        verification = {}
                        if stage in ('verify_held', 'verify_released'):
                            verification = dict(confirmed_box='held' if stage == 'verify_held' else 'released',
                                                verification_source='assumed' if policy == 'assume' else 'sensors')
                            if policy == 'sensors':
                                verification['sensor_evidence'] = {'synthetic_test_report': True}
                        self.checkpoint = contract.complete_stage(cp, stage, home_verified=stage == 'verify_home',
                                                                 **verification)
                        cli.atomic_json(self.evidence/'checkpoint.json', self.checkpoint)

                def wait(self, desired, timeout=None):
                    return dict(context={}, map_name='utars_nav_map', nav_state='FSM_WAITNAVIGATE')

                def close(self):
                    pass

            with patch('builtins.input', side_effect=AssertionError('Unexpected prompt')), \
                    patch('sys.stdin.isatty', return_value=False), \
                    patch.object(cli, 'Connection', OfflineConnection), patch.object(cli.subprocess, 'run'), \
                    patch.object(cli, 'open', side_effect=lambda name, mode: open(root/Path(name).name, mode), create=True), \
                    patch('sys.stdout', io.StringIO()):
                arguments = ['--run', '--evidence-dir', str(evidence)]
                if policy == 'sensors':
                    arguments += ['--sensor-profile', str(sensor_path)]
                self.assertEqual(cli.main(arguments, policy=policy), 0)
            checkpoint = json.loads((evidence/'checkpoint.json').read_text())
            self.assertEqual(checkpoint['completed'], list(contract.STAGES))
            self.assertEqual(checkpoint['confirmations']['verify_held']['source'],
                             'assumed' if policy == 'assume' else 'sensors')

    def test_force_without_tty_runs_all_stages_without_input(self):
        self.simulate_automatic_cli('assume')

    def test_qualified_autocheck_without_tty_runs_all_stages_without_input(self):
        self.simulate_automatic_cli('sensors')


if __name__ == '__main__':
    unittest.main()
