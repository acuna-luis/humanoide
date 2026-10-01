"""Exercise Ctrl+C and repeated cycles through the real CLI, without ROS/SSH."""
import copy
from contextlib import ExitStack
import io
import json
from pathlib import Path
import signal
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from scripts.box_handling import scenario1_cli as cli
from scripts.box_handling import scenario1_contract as contract
from scripts.box_handling import scenario1_resume as resume
from scripts.box_handling.test_scenario1_runtime import PROFILE, SimulatedRuntime


class CycleCliTest(unittest.TestCase):
    def exercise(self, root, *, stop_stage=None, stop_cycle=1, stop_at_ready=False,
                 cycle=True, failure=None, source=None, during_lock=None):
        instances = []
        evidence = root/'run'
        command_calls = []

        class Connection:
            def __init__(self, payload, wifi, location, *, console=None):
                instances.append(self)
                self.sent = []
                self.waits = []
                self.location = location
                self.process = Mock()
                self.process.wait.return_value = 0
                self.close = Mock()
                remote = root/'remote'
                remote.mkdir()
                self.machine = SimulatedRuntime(remote)
                self.machine.payload = payload
                self.machine.checkpoint = copy.deepcopy(payload['checkpoint'])
                self.machine.execution_profile = 'optimistic_v1'
                self.machine.policy = 'assume'
                self.machine.cycle = payload['cycle']
                self.machine.session_deadline = time.monotonic()+900
                self.machine.quick_health = Mock()
                self.machine.failure_task = failure

            def send(self, value):
                self.sent.append(value)

            def wait(self, desired, timeout=None):
                self.waits.append(desired)
                if desired == 'ready':
                    if stop_at_ready:
                        signal.raise_signal(signal.SIGINT)
                    return dict(context={}, map_name='utars_nav_map', nav_state='FSM_WAITNAVIGATE')
                if desired in ('armed', 'resume_ready'):
                    cli.atomic_json(self.location/'checkpoint.json', self.machine.checkpoint)
                    return dict(checkpoint=self.machine.checkpoint)
                if desired == 'stage_complete':
                    message = self.sent[-1]
                    if message['stage'] == stop_stage and self.machine.cycle_number == stop_cycle:
                        # Deliver SIGINT while the physical stage is still in flight.
                        signal.raise_signal(signal.SIGINT)
                        signal.raise_signal(signal.SIGINT)
                        self.assert_no_finish()
                    try:
                        self.machine.stage(message)
                    finally:
                        cli.atomic_json(self.location/'checkpoint.json', self.machine.checkpoint)
                    return dict(stage=message['stage'])
                if desired == 'cycle_ready':
                    self.machine.next_cycle(self.sent[-1]['cycle_number'])
                    cli.atomic_json(self.location/'checkpoint.json', self.machine.checkpoint)
                    return dict(cycle_number=self.machine.cycle_number, checkpoint=self.machine.checkpoint)
                raise AssertionError(desired)

            def assert_no_finish(self):
                if any(row['command'] == 'finish' for row in self.sent):
                    raise AssertionError('Closed connection during stage')

        def make_payload(mode, profile, checkpoint):
            return dict(mode=mode, profile=profile, checkpoint=checkpoint, modules=[], action_client='',
                        perception_guard='', sensor_worker='', health_worker='', resume_worker='')

        def contact_lock(*args, **kwargs):
            command_calls.append((args, kwargs))
            if during_lock and args[0][-1] == 'improved-scenario1:'+during_lock:
                signal.raise_signal(signal.SIGINT)

        flags = ['--cycle'] if cycle else ['--run']
        if source:
            flags += ['--resume', str(source)]
        with ExitStack() as stack:
            stack.enter_context(patch.object(cli, 'Connection', Connection))
            stack.enter_context(patch.object(cli, 'make_payload', side_effect=make_payload))
            stack.enter_context(patch.object(cli.subprocess, 'run', side_effect=contact_lock))
            stack.enter_context(patch.object(cli, 'open', side_effect=lambda name, mode: open(root/Path(name).name, mode), create=True))
            output = stack.enter_context(patch('sys.stdout', io.StringIO()))
            stack.enter_context(patch('sys.stderr', io.StringIO()))
            rc = cli.entrypoint(flags+['--evidence-dir', str(evidence)], policy='assume', execution_profile='optimistic_v1')
        self.assertTrue(all(kwargs['start_new_session'] for _, kwargs in command_calls))
        connection = instances[0]
        connection.close.assert_called_once()
        return rc, connection, evidence, output.getvalue()

    def test_two_cycles_one_connection_and_pause_after_grasp_closes_held_ledger(self):
        with tempfile.TemporaryDirectory() as directory:
            rc, conn, folder, output = self.exercise(Path(directory), stop_stage='grasp', stop_cycle=2)
            self.assertEqual(rc, 0)
            self.assertEqual(conn.waits.count('ready'), 1)
            self.assertEqual(conn.waits.count('armed'), 1)
            stages = [row['stage'] for row in conn.sent if row['command'] == 'stage']
            self.assertEqual(stages, list(contract.STAGES)+list(contract.STAGES[:4]))
            cp = json.loads((folder/'checkpoint.json').read_text())
            self.assertEqual(resume.plan_resume(cp, PROFILE, policy='assume', execution_profile='optimistic_v1')['stage'], 'retreat')
            archive = json.loads((folder/'cycle-000001.json').read_text())
            with self.assertRaises(ValueError):
                contract.validate_checkpoint(archive)
            self.assertIn('--cycle --resume', output)
            self.assertEqual(conn.sent[-1], {'command': 'finish'})

    def test_every_ctrl_c_boundary_finishes_only_current_action_and_its_verification(self):
        expected = {'navigate_get1': 'enable_vision', 'enable_vision': 'grasp', 'grasp': 'retreat',
                    'verify_held': 'retreat', 'retreat': 'navigate_put1', 'navigate_put1': 'deposit',
                    'deposit': 'home', 'verify_released': 'home', 'home': 'navigate_get1',
                    'verify_home': 'navigate_get1'}
        previous = signal.getsignal(signal.SIGINT)
        for stage, following in expected.items():
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as directory:
                rc, conn, folder, output = self.exercise(Path(directory), stop_stage=stage)
                self.assertEqual(rc, 0)
                cp = json.loads((folder/'checkpoint.json').read_text())
                self.assertEqual(contract.next_stage(cp), following)
                self.assertIsNone(cp['in_flight'])
                self.assertIsNone(cp['failure'])
                plan = resume.plan_resume(cp, PROFILE, policy='assume', execution_profile='optimistic_v1')
                self.assertEqual(plan['stage'], following)
                self.assertEqual(signal.getsignal(signal.SIGINT), previous)

    def test_signal_during_interstage_lock_does_not_send_next_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            rc, conn, folder, _ = self.exercise(Path(directory), during_lock='grasp')
            self.assertEqual(rc, 0)
            self.assertEqual([v['stage'] for v in conn.sent if v['command'] == 'stage'],
                             ['navigate_get1', 'enable_vision'])
            self.assertEqual(contract.next_stage(json.loads((folder/'checkpoint.json').read_text())), 'grasp')

    def test_signal_during_initial_checks_never_arms(self):
        with tempfile.TemporaryDirectory() as directory:
            rc, conn, folder, output = self.exercise(Path(directory), stop_at_ready=True)
            self.assertEqual(rc, 0)
            self.assertEqual(conn.sent, [{'command': 'finish'}])
            self.assertEqual(contract.next_stage(json.loads((folder/'checkpoint.json').read_text())), 'navigate_get1')

    def test_signal_during_resume_checks_keeps_source_unconsumed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_dir = root/'source'; source_dir.mkdir()
            cp = contract.new_checkpoint(PROFILE, policy='assume', execution_profile='optimistic_v1')
            cp = contract.complete_stage(contract.begin_stage(cp, 'navigate_get1'), 'navigate_get1')
            source = source_dir/'checkpoint.json'; source.write_text(json.dumps(cp))
            (source_dir/'context.json').write_text('{}')
            rc, conn, _, output = self.exercise(root, stop_at_ready=True, source=source)
            self.assertEqual(rc, 0)
            self.assertFalse(source.with_name(source.name+'.consumed.json').exists())
            self.assertEqual(conn.sent, [{'command': 'finish'}])
            self.assertIn(str(source.resolve()), output)

    def test_failure_during_requested_pause_is_still_failure_not_a_clean_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            rc, conn, folder, output = self.exercise(Path(directory), stop_stage='grasp',
                                                      failure='local_front_box/separate_right_cruzr')
            self.assertEqual(rc, 78)
            self.assertNotIn('PAUSA_COMPLETADA', output)
            self.assertNotIn({'command': 'finish'}, conn.sent)
            cp = json.loads((folder/'checkpoint.json').read_text())
            with self.assertRaises(ValueError):
                resume.plan_resume(cp, PROFILE, policy='assume', execution_profile='optimistic_v1')

    def test_single_run_also_has_graceful_stop_without_enabling_cycle(self):
        with tempfile.TemporaryDirectory() as directory:
            rc, conn, folder, output = self.exercise(Path(directory), stop_stage='deposit', cycle=False)
            self.assertEqual(rc, 0)
            self.assertEqual(contract.next_stage(json.loads((folder/'checkpoint.json').read_text())), 'home')
            self.assertNotIn('--cycle --resume', output)

    def test_unconsumed_failed_source_pause_keeps_explicit_recovery_options(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/'checkpoint.json'
            cp = contract.new_checkpoint(PROFILE, policy='assume', execution_profile='optimistic_v1')
            cp = contract.fail_stage(contract.begin_stage(cp, 'navigate_get1'), 'navigate_get1', 'test fault')
            source.write_text(json.dumps(cp))
            args = cli.parser('assume', 'optimistic_v1').parse_args([
                '--cycle', '--resume', str(source), '--from-stage', 'home',
                '--box-state', 'released', '--recovery-confirmed', '--wifi'])
            plan = resume.plan_resume(cp, PROFILE, stage='home', box_state='released',
                                      recovery_confirmed=True, policy='assume', execution_profile='optimistic_v1')
            with patch('sys.stdout', io.StringIO()) as output:
                cli.report_pause('optimistic_scenario1.sh', source, cp, True, args=args, resume_plan=plan)
            self.assertIn('siguiente=home', output.getvalue())
            self.assertIn('--from-stage home --box-state released --recovery-confirmed', output.getvalue())
            self.assertIn('--wifi', output.getvalue())
            self.assertEqual(json.loads(source.read_text()), cp)

    def test_next_cycle_clears_console_history_without_hiding_active_cycle_events(self):
        reporter = cli.ConsoleReporter()
        for name in ('last_feedback', 'shown_box_measurements', 'shown_box_rejections'):
            collection = getattr(reporter, name)
            if isinstance(collection, dict):
                collection['old'] = 'value'
            else:
                collection.add('old')
        self.assertEqual(reporter.render(dict(event='cycle_ready')), [])
        for name in ('last_feedback', 'shown_box_measurements', 'shown_box_rejections'):
            self.assertFalse(getattr(reporter, name))

    def test_cycle_check_and_plan_are_read_only_and_partial_cycle_is_rejected(self):
        for mode in ('--check', '--plan'):
            self.assertFalse(cli.is_moving(cli.parser('assume', 'optimistic_v1').parse_args(['--cycle', mode])))
        self.assertTrue(cli.is_moving(cli.parser('assume', 'optimistic_v1').parse_args(['--cycle'])))
        with patch.object(cli, 'Connection', side_effect=AssertionError('No connection')), patch('sys.stdout', io.StringIO()):
            self.assertEqual(cli.main(['--cycle', '--plan'], policy='assume', execution_profile='optimistic_v1'), 0)
            for ending in ('get1', 'grasp', 'put1'):
                with self.assertRaisesRegex(ValueError, 'ciclo completo'):
                    cli.main(['--cycle', '--stop-after', ending], policy='assume', execution_profile='optimistic_v1')


if __name__ == '__main__':
    unittest.main()
