"""Offline coverage for bounded main navigation deadlines and supervision."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from scripts.box_handling import scenario1_cli as cli
from scripts.box_handling import scenario1_contract as contract
from scripts.box_handling import scenario1_runtime as runtime
from scripts.box_handling import scenario1_action_client as action
from scripts.box_handling.test_scenario1_action_client import FakeClock, FakeTransport, ACCEPT, GOAL_ID
from scripts.box_handling.test_scenario1_runtime import PROFILE


class NavigationTimeoutTest(unittest.TestCase):
    def test_cli_and_runtime_reject_out_of_range_values(self):
        parser = cli.parser('assume', 'optimistic_v1')
        self.assertEqual(parser.parse_args([]).navigation_timeout_s, 300)
        for value in (180, 300, 600):
            self.assertEqual(parser.parse_args(['--navigation-timeout-s', str(value)]).navigation_timeout_s, value)
            self.assertEqual(contract.validate_navigation_timeout(value), value)
        for value in (0, 179, 601, True, 300.0, float('nan'), '300'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                runtime.Runtime({'checkpoint': contract.new_checkpoint(PROFILE), 'profile': PROFILE,
                                 'navigation_timeout_s': value})
        for value in ('179', '601', 'nan'):
            with self.subTest(value=value), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    parser.parse_args(['--navigation-timeout-s', value])

    def test_main_navigation_uses_selected_timeout_with_arrival_checks(self):
        for point in ('get1', 'put1'):
            with self.subTest(point=point):
                machine = runtime.Runtime({'checkpoint': contract.new_checkpoint(PROFILE), 'profile': PROFILE,
                                           'navigation_timeout_s': 600}, emit=Mock())
                machine.prepare_map = Mock()
                machine.map_points = Mock()
                machine.read_poses = Mock(return_value=([], 0))
                machine.sync_planner_map = Mock()
                machine.points = {point: {'mode': 'logo_nav', 'id': point, '_expected_pose': {}}}
                machine.action = Mock(return_value={'event': 'result', 'status': 4,
                    'result': {'state': {'desc': 'SUCCEED', 'state': 1101001},
                               'dmsg': 'navigation_start SUCCEEDED'}})
                machine.map_state = Mock(return_value=('utars_nav_map', 'FSM_WAITNAVIGATE'))
                machine.arrival_measurements = Mock(return_value=([], []))
                machine.navigate(point)
                self.assertEqual(machine.action.call_args.args[2], 600)
                self.assertEqual(machine.read_poses.call_count, 2)
                machine.arrival_measurements.assert_called_once()

    def test_outer_navigation_budget_exceeds_action_and_other_stages_unchanged(self):
        for timeout in (180, 300, 600):
            for point in ('navigate_get1', 'navigate_put1'):
                self.assertEqual(contract.stage_wait_timeout(point, timeout), timeout + 240)
            self.assertEqual(contract.stage_wait_timeout('grasp', timeout), 420)

    def test_worker_session_waits_beyond_native_timeout(self):
        machine = runtime.Runtime({'checkpoint': contract.new_checkpoint(PROFILE), 'profile': PROFILE})
        machine.session = Path('/unused')
        machine.connected = Mock()
        worker = Mock()
        worker.call.return_value = [{'event': 'result', 'status': 4}]
        machine.action_sessions['navigation'] = worker
        machine.action('navigation', {'command': 'navigation_start', 'arg_json': '{}'}, 600)
        self.assertEqual(worker.call.call_args.kwargs['timeout'], 618)
        self.assertEqual(worker.call.call_args.args[0]['timeout'], 600)

    def test_late_success_and_timeout_cancel_at_new_limit(self):
        success = {'event': 'result', 'status': 4, 'result': {
            'state': {'desc': 'SUCCEED', 'state': 1101001}, 'dmsg': 'navigation_start SUCCEEDED'}}
        cancelled = {'event': 'result', 'status': 5, 'result': {}}
        for schedule, expected, cancelled_expected in (
                (((.25, ACCEPT), (220., success)), 0, []),
                (((.25, ACCEPT),), 2, [GOAL_ID])):
            clock = FakeClock()
            transport = FakeTransport(clock, schedule, ((.25, cancelled),))
            events = []
            status = action.run_action(transport, 'navigation', {'command': 'navigation_start', 'arg_json': '{}'},
                                       300, lambda **row: events.append(row), clock=clock, cancel_grace=1)
            self.assertEqual(status, expected)
            self.assertEqual(transport.canceled, cancelled_expected)
            if expected:
                self.assertEqual(clock(), 300.25)
                self.assertTrue(any(row.get('reason') == 'Action deadline exceeded' for row in events))

    def test_control_lease_still_cancels_before_navigation_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'lease.json'
            path.write_text('{"deadline": 190}')
            clock = FakeClock()
            transport = FakeTransport(clock, ((.25, ACCEPT),))
            events = []
            status = action.run_action(transport, 'navigation', {'command': 'navigation_start', 'arg_json': '{}'},
                300, lambda **row: events.append(row), lease_file=path, clock=clock, cancel_grace=1)
        self.assertEqual(status, 3)
        self.assertEqual(transport.canceled, [GOAL_ID])
        self.assertTrue(any('expired' in row.get('reason', '') for row in events))

    def test_resume_instruction_preserves_selection(self):
        args = cli.parser('assume', 'optimistic_v1').parse_args(['--navigation-timeout-s', '600'])
        cp = contract.new_checkpoint(PROFILE, policy='assume', execution_profile='optimistic_v1')
        with contextlib.redirect_stdout(io.StringIO()) as output:
            cli.report_pause('optimistic_scenario1.sh', Path('/tmp/checkpoint.json'), cp, False, args=args)
        self.assertIn('--navigation-timeout-s 600', output.getvalue())

    def test_plan_reports_limits_without_connecting(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(cli.main(['--plan', '--navigation-timeout-s', '600'],
                                      policy='assume', execution_profile='optimistic_v1'), 0)
        self.assertIn('"navigation_timeout_s": 600', output.getvalue())
        self.assertIn('"session_timeout_s": 900', output.getvalue())


if __name__ == '__main__':
    unittest.main()
