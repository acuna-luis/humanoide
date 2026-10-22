"""CLI/payload tests for visual alignment; no SSH, ROS or native main calls."""
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

from scripts.box_handling import scenario1_box_alignment as alignment
from scripts.box_handling import scenario1_cli as cli
from scripts.box_handling import scenario1_contract as contract


PROFILE = json.loads((Path(__file__).with_name('scenario1_current_geometry.json')).read_text())


class AlignmentCliTests(unittest.TestCase):
    def plan(self, flags):
        with patch.object(cli, 'Connection', side_effect=AssertionError('No SSH')), \
                patch.object(cli.subprocess, 'run', side_effect=AssertionError('No commands')), \
                patch.object(cli.subprocess, 'Popen', side_effect=AssertionError('No processes')), \
                patch('sys.stdout', io.StringIO()) as output:
            rc = cli.main(['--plan', *flags], policy='assume', execution_profile='optimistic_v1')
        self.assertEqual(rc, 0)
        text = output.getvalue()
        return json.loads(text[text.index('{'):])

    def test_flag_default_seven_and_only_zero_to_seven_are_allowed(self):
        parser = cli.parser('assume', 'optimistic_v1')
        self.assertEqual(parser.parse_args([]).box_alignment_attempts, 7)
        for count in range(8):
            self.assertEqual(parser.parse_args(['--box-alignment-attempts', str(count)]).box_alignment_attempts, count)
        for value in ('-1', '8', '1000000', '3.0', 'nan', 'inf', 'True'):
            with self.subTest(value=value), patch('sys.stderr', io.StringIO()), self.assertRaises(SystemExit):
                parser.parse_args(['--box-alignment-attempts', value])

    def test_other_entrypoints_keep_their_original_default_without_alignment(self):
        for policy in ('ask', 'assume', 'sensors'):
            parser = cli.parser(policy, 'standard_v1')
            self.assertEqual(parser.parse_args([]).box_alignment_attempts, 0)
            self.assertEqual(parser.parse_args(['--box-alignment-attempts', '2']).box_alignment_attempts, 2)

    def test_each_plan_reports_exact_policy_without_connection_or_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            for count in range(8):
                path = Path(directory)/str(count)
                report = self.plan(['--stop-after', 'grasp', '--box-alignment-attempts', str(count),
                                    '--evidence-dir', str(path)])
                detail = report['box_alignment']
                self.assertEqual(detail['enabled'], count > 0)
                self.assertEqual(detail['policy'], dict(alignment.make_policy(count)))
                self.assertTrue(detail['before_native_grasp'])
                self.assertTrue(detail['arm_task_unchanged'])
                self.assertEqual(report['profile']['grasp']['task'], 'local_front_box/separate_right_cruzr')
                self.assertFalse(path.exists())

    def test_pending_table74_full_plan_also_exposes_policy_without_activating_deposit(self):
        report = self.plan(['--table-height-cm', '74', '--box-alignment-attempts', '4'])
        self.assertEqual(report['box_alignment']['policy'], dict(alignment.make_policy(4)))
        self.assertFalse(report['execution_allowed'])
        self.assertFalse(report['table_preparation']['deposit_executable'])
        self.assertEqual(report['profile']['deposit']['compatibility'], 'pending')

    def test_pause_resume_command_keeps_selected_count_including_zero(self):
        checkpoint = contract.new_checkpoint(PROFILE, stop_after='verify_held', policy='assume',
                                              execution_profile='optimistic_v1')
        for count in (0, 3, 7):
            args = cli.parser('assume', 'optimistic_v1').parse_args(
                ['--stop-after', 'grasp', '--box-alignment-attempts', str(count)])
            with self.subTest(count=count), patch('sys.stdout', io.StringIO()) as output:
                cli.report_pause('optimistic_scenario1.sh', Path('/tmp/example.json'), checkpoint, False, args=args)
            self.assertIn('--box-alignment-attempts '+str(count), output.getvalue())

    def test_actual_check_payload_and_evidence_keep_requested_count_without_processes(self):
        for count in (0, 3, 7):
            with self.subTest(count=count), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                evidence = root/'run'
                captured = []
                class FakeConnection:
                    def __init__(self, payload, wifi, location, *, console=None):
                        captured.append(copy.deepcopy(payload))
                        self.process = Mock()
                        self.process.wait.return_value = 0
                    def wait(self, desired):
                        if desired != 'ready':
                            raise AssertionError('Read-only check requested physical stage')
                        return dict(context={}, map_name='utars_nav_map', nav_state='FSM_WAITNAVIGATE')
                    def close(self):
                        pass
                with patch.object(cli, 'Connection', FakeConnection), \
                        patch.object(cli.subprocess, 'run', side_effect=AssertionError('No commands')), \
                        patch.object(cli.subprocess, 'Popen', side_effect=AssertionError('No processes')), \
                        patch.object(cli, 'open', side_effect=lambda name, mode: open(root/Path(name).name, mode), create=True), \
                        patch('sys.stdout', io.StringIO()):
                    rc = cli.main(['--check', '--stop-after', 'grasp', '--box-alignment-attempts', str(count),
                                   '--evidence-dir', str(evidence)], policy='assume', execution_profile='optimistic_v1')
                self.assertEqual(rc, 0)
                self.assertEqual(len(captured), 1)
                self.assertEqual(captured[0]['mode'], 'check')
                self.assertEqual(captured[0]['box_alignment_attempts'], count)
                policy = json.loads((evidence/'box-alignment-policy.json').read_text())
                self.assertEqual(policy['policy'], dict(alignment.make_policy(count)))
                self.assertEqual(dict(captured[0]['modules'])['scenario1_box_alignment'],
                                 cli.HERE.joinpath('scenario1_box_alignment.py').read_text())

    def test_exact_bootstrap_loads_modules_and_embedded_action_guard_without_running_main(self):
        checkpoint = contract.new_checkpoint(PROFILE, policy='assume', execution_profile='optimistic_v1')
        with patch.object(cli.subprocess, 'run', side_effect=AssertionError('No commands')), \
                patch.object(cli.subprocess, 'Popen', side_effect=AssertionError('No processes')):
            payload = cli.make_payload('check', PROFILE, checkpoint)
            # Execute the original loader, stopping before its sole physical entry.
            loader, physical_entry = cli.BOOTSTRAP.split('raise SystemExit', 1)
            self.assertIn("sys.modules['scenario1_runtime'].main(payload)", physical_entry)
            with patch.dict(sys.modules), patch('sys.stdin', io.StringIO(json.dumps({'modules': payload['modules']})+'\n')):
                exec(compile(loader, 'scenario1-bootstrap-loader-only', 'exec'), {})
                embedded_alignment = sys.modules['scenario1_box_alignment']
                embedded_runtime = sys.modules['scenario1_runtime']
                self.assertIs(embedded_runtime.box_alignment, embedded_alignment)
                self.assertEqual(embedded_alignment.make_policy(3)['max_corrections'], 3)
                action = types.ModuleType('alignment_test_action_client')
                exec(compile(payload['action_client'], 'embedded-action-client-without-main', 'exec'), action.__dict__)
                guard = sys.modules['scenario1_nav_correction']
                spec = guard.make_spec(dict(point_x=.03, point_y=0., point_yaw=0.),
                    dict(x=0., y=0., yaw=0., stamp_ns=100), 7, point='box_pickup')
                self.assertEqual(spec['attempt'], 7)
                self.assertEqual(guard.Guard(spec, 101).distance_tolerance_m, .005)
                with self.assertRaises(ValueError):
                    guard.validate_spec(dict(spec, attempt=8))
                with self.assertRaises(ValueError):
                    guard.validate_spec(dict(spec, point='get1', attempt=3))


if __name__ == '__main__':
    unittest.main()
