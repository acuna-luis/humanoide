"""Fault injection for supervision/checkpoint boundaries. No robot or network."""
import copy
import io
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

from scripts.box_handling import scenario1_cli as cli
from scripts.box_handling import scenario1_contract as contract
from scripts.box_handling import scenario1_runtime as runtime


PROFILE = json.loads((Path(__file__).with_name('scenario1_current_geometry.json')).read_text())


class SimulatedRuntime(runtime.Runtime):
    def __init__(self, directory, stop_after='verify_home'):
        self.events = []
        cp = contract.new_checkpoint(PROFILE, stop_after=stop_after)
        super().__init__({'checkpoint': cp, 'profile': PROFILE},
                         lambda event, **values: self.events.append(dict(event=event, **values)))
        self.session = Path(directory)
        self.armed = True
        self.calls = []
        self.fail_health_at = None
        self.failure_task = None

    def discover(self):
        self.connected()

    def hashes(self):
        pass

    def health(self, require_home=False):
        if self.checkpoint['in_flight'] == self.fail_health_at:
            raise RuntimeError('Health check failed')
        if require_home:
            self.calls.append('home_measured')

    def navigate(self, point):
        self.assert_persisted()
        self.calls.append(point)

    def action(self, kind, goal, timeout):
        self.assert_persisted()
        task = goal['task_name']
        self.calls.append(task)
        return dict(event='result', status=4 if task != self.failure_task else 6,
                    result={'state': {'desc': 'SUCCEED', 'state': 1101001}})

    def assert_persisted(self):
        stored = json.loads((self.session/'checkpoint.json').read_text())
        if not stored['in_flight'] or stored != self.checkpoint:
            raise AssertionError('Physical command preceded durable intent')


def advance(machine, stop='verify_home'):
    for stage in contract.STAGES:
        message = dict(command='stage', stage=stage)
        if stage == 'verify_held':
            message['confirmed_box'] = 'held'
        if stage == 'verify_released':
            message['confirmed_box'] = 'released'
        machine.stage(message)
        if stage == stop:
            break


class RuntimeTest(unittest.TestCase):
    def test_full_cycle_exact_geometry_and_measured_home(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = SimulatedRuntime(directory)
            advance(machine)
            self.assertEqual(machine.calls, ['get1', 'vision/enable_transport_vision_switch',
                'local_front_box/separate_right_cruzr', 'cruzr/mobot_back_20', 'put1',
                'wrc_cruzr/put_cruzr_wrc_low', 'cruzr/home', 'home_measured'])
            self.assertIsNone(contract.next_stage(machine.checkpoint))

    def test_grasp_stop_never_reverses_transports_deposits_or_homes(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = SimulatedRuntime(directory, 'verify_held')
            advance(machine, 'verify_held')
            self.assertEqual(machine.checkpoint['box_state'], 'held')
            self.assertEqual(len(machine.calls), 3)
            with self.assertRaises(ValueError):
                machine.stage(dict(stage='retreat'))
            self.assertEqual(len(machine.calls), 3)

    def test_health_failure_invalidates_prior_clean_held_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = SimulatedRuntime(directory)
            advance(machine, 'verify_held')
            machine.fail_health_at = 'retreat'
            with self.assertRaisesRegex(RuntimeError, 'Health'):
                machine.stage(dict(stage='retreat'))
            stored = json.loads((Path(directory)/'checkpoint.json').read_text())
            self.assertEqual(stored['box_state'], 'unknown')
            self.assertEqual(stored['failure']['stage'], 'retreat')
            self.assertNotIn('cruzr/mobot_back_20', machine.calls)
            with self.assertRaises(ValueError):
                contract.resume_checkpoint(stored, PROFILE, confirmed_box='held', state_reconfirmed=True)

    def test_deposit_failure_never_homes_or_retries(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = SimulatedRuntime(directory)
            machine.failure_task = 'wrc_cruzr/put_cruzr_wrc_low'
            with self.assertRaises(ValueError):
                advance(machine)
            self.assertEqual(machine.calls.count(machine.failure_task), 1)
            self.assertNotIn('cruzr/home', machine.calls)
            self.assertEqual(machine.checkpoint['box_state'], 'unknown')

    def test_successful_home_action_is_insufficient(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = SimulatedRuntime(directory)
            machine.fail_health_at = 'verify_home'
            with self.assertRaises(RuntimeError):
                advance(machine)
            self.assertIn('cruzr/home', machine.calls)
            self.assertNotIn('verify_home', machine.checkpoint['completed'])
            self.assertFalse(any(e.get('stage') == 'verify_home' and e['event'] == 'stage_complete' for e in machine.events))

    def test_heartbeat_loss_blocks_next_action_and_records_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = SimulatedRuntime(directory)
            machine.last_heartbeat = time.monotonic()-20
            with self.assertRaisesRegex(RuntimeError, 'HEARTBEAT'):
                machine.stage(dict(stage='navigate_get1'))
            self.assertEqual(machine.calls, [])
            self.assertIsNotNone(machine.checkpoint['failure'])

    def test_revoked_lease_never_renews_under_concurrent_writers(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = SimulatedRuntime(directory)
            writers = [threading.Thread(target=lambda: [machine.write_lease() for _ in range(20)]) for _ in range(3)]
            for thread in writers:
                thread.start()
            machine.stop.set()
            machine.write_lease()
            for thread in writers:
                thread.join()
            self.assertEqual(json.loads((Path(directory)/'control-lease.json').read_text()), {'deadline': 0})

    def test_watchdog_write_error_latches_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = SimulatedRuntime(directory)
            with patch.object(machine, 'write_lease', side_effect=OSError('disk failed')):
                with self.assertRaises(OSError):
                    machine.watchdog()
            self.assertTrue(machine.stop.is_set())

    def test_arm_and_unarmed_stage_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = SimulatedRuntime(directory)
            machine.armed = False
            with self.assertRaisesRegex(RuntimeError, 'NOT_ARMED'):
                machine.stage(dict(stage='navigate_get1'))
            self.assertEqual(machine.calls, [])

    def test_home_telemetry_uses_best_effort_and_rejects_old_samples(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = runtime.Runtime({'checkpoint': contract.new_checkpoint(PROFILE)})
            machine.native_container = 'fake'
            machine.ros_container = 'fake-ros'
            controllers = "Response(controller=[{'name':'manipulation_controller','state':'running'}, {'name':'sdk_controller','state':'initialized'}, {'name':'vla_sdk_controller','state':'initialized'}])"
            calls = []
            def native(args, timeout=12):
                calls.append(args)
                if 'list_controllers' in ' '.join(args):
                    return controllers
                return json.dumps({'header': {'stamp': {'sec': 1, 'nanosec': 0}}})
            machine.native = native
            machine.topic = lambda topic: 'status_list: []' if topic.endswith('/status') else (
                'batteries:\n- batsoc: 90\n- batsoc: 90' if topic.endswith('battery_state') else 'data: 0')
            with self.assertRaisesRegex(RuntimeError, 'antigua'):
                machine.health()
            telemetry = calls[-1]
            self.assertEqual(telemetry[telemetry.index('--qos-reliability')+1], 'best_effort')
            self.assertEqual(telemetry[telemetry.index('--qos-durability')+1], 'volatile')

    def test_duplicate_results_or_failure_return_code_never_advance(self):
        result = json.dumps(dict(event='result', status=4, result={'state': {'desc':'SUCCEED','state':1101001}}))+'\n'
        for output, rc in ((result+result, 0), (result, 2), ('Goal rejected\n', 0)):
            machine = runtime.Runtime({'action_client': '# unused', 'checkpoint': contract.new_checkpoint(PROFILE)}, lambda *args, **kwargs: None)
            machine.native_container = 'fake'
            process = Mock(stdout=io.StringIO(output))
            process.wait.return_value = rc
            process.poll.return_value = rc
            with patch.object(runtime.subprocess, 'Popen', return_value=process), self.assertRaises(RuntimeError):
                machine.action('motion', {'task_name':'cruzr/home','yaml_args':'{}'}, 1)


class CliTest(unittest.TestCase):
    def held_checkpoint(self):
        cp = contract.new_checkpoint(PROFILE, stop_after='verify_held')
        for stage in contract.STAGES[:4]:
            cp = contract.begin_stage(cp, stage)
            cp = contract.complete_stage(cp, stage, confirmed_box='held' if stage == 'verify_held' else None)
        return cp

    def test_default_is_check_and_modes_are_exclusive(self):
        args = cli.parser().parse_args([])
        self.assertFalse(args.run or args.resume or args.plan)
        with self.assertRaises(SystemExit), patch('sys.stderr', io.StringIO()):
            cli.parser().parse_args(['--run', '--check'])

    def test_plan_is_offline_and_no_changes(self):
        with patch.object(cli.subprocess, 'Popen', side_effect=AssertionError('No network')), \
                patch('sys.stdout', io.StringIO()) as output:
            self.assertEqual(cli.main(['--plan']), 0)
        self.assertIn('operator_assumed_existing', output.getvalue())

    def test_resume_source_consumed_once_even_after_new_run_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/'checkpoint.json'
            source.write_text('{}')
            target = Path(directory)/'next-checkpoint.json'
            cli.claim_resume(source, target)
            target.write_text('{"failure":"retreat interrupted"}')
            with self.assertRaises(FileExistsError):
                cli.claim_resume(source, target)
            with self.assertRaisesRegex(RuntimeError, 'consumido'):
                cli.main(['--resume', str(source)])

    def test_noninteractive_run_fails_before_network(self):
        with patch('sys.stdin.isatty', return_value=False), patch.object(cli.subprocess, 'Popen', side_effect=AssertionError('No network')):
            with self.assertRaisesRegex(RuntimeError, 'terminal'):
                cli.main(['--run'])

    def test_no_confirmation_does_not_proceed(self):
        with patch('builtins.input', return_value=''), patch('sys.stdout', io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, 'Confirmación'):
                cli.confirm('Test', 'CONTINUAR')

    def test_cancel_before_arming_resume_does_not_clone_clean_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            origin = root/'checkpoint.json'
            origin.write_text(json.dumps(self.held_checkpoint()))
            (root/'context.json').write_text('{}')
            evidence = root/'new-run'
            connection = Mock()
            connection.wait.return_value = dict(map_name='utars_nav_map', nav_state='FSM_WAITNAVIGATE', context={})
            with patch('sys.stdin.isatty', return_value=True), \
                    patch.object(cli, 'Connection', return_value=connection), \
                    patch.object(cli.subprocess, 'run'), patch.object(cli, 'confirm', side_effect=RuntimeError('operator stopped')), \
                    patch.object(cli, 'open', side_effect=lambda name, mode: open(root/Path(name).name, mode), create=True), \
                    patch('sys.stdout', io.StringIO()):
                with self.assertRaisesRegex(RuntimeError, 'operator stopped'):
                    cli.main(['--resume', str(origin), '--evidence-dir', str(evidence)])
            self.assertFalse((evidence/'checkpoint.json').exists())
            self.assertFalse(origin.with_name(origin.name+'.consumed.json').exists())
            self.assertEqual(json.loads(origin.read_text()), self.held_checkpoint())
            connection.send.assert_not_called()

    def test_noop_resume_cannot_clone_held_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            origin = Path(directory)/'checkpoint.json'
            origin.write_text(json.dumps(self.held_checkpoint()))
            with patch.object(cli, 'Connection', side_effect=AssertionError('No network')):
                with self.assertRaisesRegex(RuntimeError, 'no tiene etapas'):
                    cli.main(['--resume', str(origin), '--stop-after', 'grasp'])


if __name__ == '__main__':
    unittest.main()
