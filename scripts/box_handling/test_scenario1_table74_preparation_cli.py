"""Table74 intent/continuity regressions; all transports and commands are fake."""
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.box_handling import scenario1_cli as cli
from scripts.box_handling import scenario1_contract as contract


LEGACY = json.loads((cli.HERE/'scenario1_current_geometry.json').read_text())
TABLE74 = json.loads(cli.TABLE74_PREPARATION_PROFILE.read_text())


def checkpoint(profile, *, at_put1=False):
    cp = contract.new_checkpoint(profile, stop_after='navigate_put1' if at_put1 else 'verify_held',
                                policy='assume', execution_profile='optimistic_v1')
    end = contract.STAGES.index('navigate_put1' if at_put1 else 'verify_held')+1
    for stage in contract.STAGES[:end]:
        options = dict(confirmed_box='held', verification_source='assumed') if stage == 'verify_held' else {}
        cp = contract.complete_stage(contract.begin_stage(cp, stage), stage, **options)
    return cp


def read_report(output):
    text = output.getvalue()
    return json.loads(text[text.index('{'):])


class Table74PreparationCliTests(unittest.TestCase):
    def run_plan(self, arguments):
        output = io.StringIO()
        with patch.object(cli, 'Connection', side_effect=AssertionError('No network')), \
                patch.object(cli.subprocess, 'run', side_effect=AssertionError('No commands')), \
                patch.object(cli.subprocess, 'Popen', side_effect=AssertionError('No processes')), \
                patch('sys.stdout', output):
            result = cli.main(arguments, policy='assume', execution_profile='optimistic_v1')
        self.assertEqual(result, 0)
        return read_report(output)

    def test_only_74_is_accepted_and_profile_selection_is_exclusive(self):
        parser = cli.parser('assume', 'optimistic_v1')
        self.assertEqual(parser.parse_args(['--table-height-cm', '74']).table_height_cm, 74.)
        for args in (['--table-height-cm', value] for value in ('73', '69.5', 'nan', 'inf')):
            with self.subTest(args=args), patch('sys.stderr', io.StringIO()), self.assertRaises(SystemExit):
                parser.parse_args(args)
        with patch('sys.stderr', io.StringIO()), self.assertRaises(SystemExit):
            parser.parse_args(['--table-height-cm', '74', '--profile', str(cli.HERE/'scenario1_current_geometry.json')])

    def test_legacy_default_profile_and_plan_remain_unchanged(self):
        report = self.run_plan(['--plan'])
        self.assertEqual(report['profile'], LEGACY)
        self.assertEqual(report['stages'], list(contract.STAGES))
        self.assertNotIn('table_preparation', report)
        self.assertEqual(report['profile']['deposit']['compatibility'], 'operator_assumed_existing')

    def test_full_plan_routes_to_supervised_coordinator_without_promoting_pending_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            evidence = Path(directory)/'not-created'
            with patch('scripts.box_handling.scenario1_table74_cycle.run', return_value=43) as coordinator, \
                    patch.object(cli, 'Connection', side_effect=AssertionError('Coordinator owns transport')), \
                    patch.object(contract, 'new_checkpoint', side_effect=AssertionError('No full pending checkpoint')):
                result = cli.main(['--plan', '--table-height-cm', '74', '--box-alignment-attempts', '7',
                                   '--evidence-dir', str(evidence)],
                                  policy='assume', execution_profile='optimistic_v1')
            self.assertEqual(result, 43)
            self.assertTrue(coordinator.call_args.args[0].plan)
            self.assertEqual(coordinator.call_args.args[0].box_alignment_attempts, 7)
            self.assertFalse(evidence.exists())
        self.assertEqual(json.loads(cli.TABLE74_PREPARATION_PROFILE.read_text()), TABLE74)
        self.assertEqual(TABLE74['deposit']['compatibility'], 'pending')

    def test_full_run_check_and_implicit_check_delegate_explicit_mode_unchanged(self):
        for mode in (['--run'], ['--check'], [], ['--cycle']):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                evidence = Path(directory)/'not-created'
                with patch('scripts.box_handling.scenario1_table74_cycle.run', return_value=0) as coordinator, \
                        patch.object(cli, 'Connection', side_effect=AssertionError('No direct transport')):
                    result = cli.main([*mode, '--table-height-cm', '74', '--evidence-dir', str(evidence)],
                                      policy='assume', execution_profile='optimistic_v1')
                self.assertEqual(result, 0)
                selected = coordinator.call_args.args[0]
                self.assertEqual(cli.is_moving(selected), '--run' in mode or '--cycle' in mode)
                self.assertFalse(evidence.exists())

    def test_other_confirmation_policies_do_not_silently_acquire_supervised_route(self):
        with patch.object(cli, 'Connection', side_effect=AssertionError('No network')), \
                patch('sys.stderr', io.StringIO()) as output:
            result = cli.entrypoint(['--run', '--table-height-cm', '74'], policy='ask')
        self.assertEqual(result, 78)
        self.assertIn('MESA74_PREPARACION_PENDIENTE', output.getvalue())
        self.assertIn('antes de conectar', output.getvalue())
        self.assertNotIn('ESCENARIO_INTERRUMPIDO', output.getvalue())

    def test_predeposit_plans_keep_pending_profile_and_exact_stage_boundaries(self):
        for flag, last in (('get1', 'navigate_get1'), ('grasp', 'verify_held'), ('put1', 'navigate_put1')):
            with self.subTest(flag=flag):
                report = self.run_plan(['--plan', '--table-height-cm', '74', '--stop-after', flag])
                self.assertEqual(report['stages'], list(contract.STAGES[:contract.STAGES.index(last)+1]))
                self.assertEqual(report['profile'], TABLE74)
                self.assertEqual(report['profile']['deposit']['compatibility'], 'pending')
                self.assertFalse(report['table_preparation']['deposit_executable'])
                self.assertNotIn('deposit', report['stages'])
                self.assertEqual(report['automatic_retries'], 0)

    def test_pending_profile_cannot_be_selected_through_generic_profile_flag(self):
        with patch.object(cli, 'Connection', side_effect=AssertionError('No network')), \
                self.assertRaisesRegex(ValueError, 'requiere --table-height-cm 74'):
            cli.main(['--plan', '--profile', str(cli.TABLE74_PREPARATION_PROFILE)],
                     policy='assume', execution_profile='optimistic_v1')

    def test_editing_preparation_profile_cannot_promote_deposit_to_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'modified-profile.json'
            modified = copy.deepcopy(TABLE74)
            modified['deposit']['compatibility'] = 'verified'
            path.write_text(json.dumps(modified))
            with patch.object(cli, 'TABLE74_PREPARATION_PROFILE', path), \
                    patch.object(cli, 'Connection', side_effect=AssertionError('No network')), \
                    self.assertRaisesRegex(ValueError, 'TABLE74_PREPARATION_PROFILE_CHANGED'):
                cli.main(['--run', '--table-height-cm', '74', '--stop-after', 'grasp'],
                         policy='assume', execution_profile='optimistic_v1')

    def test_resume_requires_same_selection_and_profile_hash_without_consuming_source(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/'checkpoint.json'
            raw = json.dumps(checkpoint(TABLE74))
            source.write_text(raw)
            report = self.run_plan(['--plan', '--table-height-cm', '74', '--resume', str(source),
                                    '--stop-after', 'put1'])
            self.assertEqual(report['stages'], ['retreat', 'navigate_put1'])
            self.assertEqual(report['resume']['checkpoint']['profile_sha256'], contract._profile_hash(TABLE74))
            self.assertEqual(source.read_text(), raw)
            self.assertFalse(source.with_name('checkpoint.json.consumed.json').exists())
            with patch.object(cli, 'Connection', side_effect=AssertionError('No network')), \
                    self.assertRaises(ValueError):
                cli.main(['--run', '--resume', str(source), '--stop-after', 'put1'],
                         policy='assume', execution_profile='optimistic_v1')
            altered = json.loads(raw)
            altered['profile_sha256'] = 'f'*64
            source.write_text(json.dumps(altered))
            with self.assertRaises(ValueError):
                self.run_plan(['--plan', '--table-height-cm', '74', '--resume', str(source), '--stop-after', 'put1'])

    def test_legacy_checkpoint_is_not_silently_migrated_into_table74(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/'checkpoint.json'
            original = json.dumps(checkpoint(LEGACY))
            source.write_text(original)
            with self.assertRaises(ValueError):
                self.run_plan(['--plan', '--table-height-cm', '74', '--resume', str(source), '--stop-after', 'put1'])
            self.assertEqual(source.read_text(), original)
            self.assertFalse(source.with_name('checkpoint.json.consumed.json').exists())

    def test_full_resume_routes_genuine_source_without_modifying_or_consuming_it(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/'checkpoint.json'
            raw = json.dumps(checkpoint(TABLE74, at_put1=True))
            source.write_text(raw)
            with patch('scripts.box_handling.scenario1_table74_cycle.run', return_value=0) as coordinator:
                result = cli.main(['--plan', '--table-height-cm', '74', '--resume', str(source)],
                                  policy='assume', execution_profile='optimistic_v1')
            self.assertEqual(result, 0)
            self.assertEqual(coordinator.call_args.args[0].resume, source)
            self.assertEqual(source.read_text(), raw)
            self.assertFalse(source.with_name('checkpoint.json.consumed.json').exists())

    def test_pause_command_preserves_explicit_table_selection(self):
        args = cli.parser('assume', 'optimistic_v1').parse_args(
            ['--table-height-cm', '74', '--stop-after', 'grasp'])
        cp = contract.new_checkpoint(TABLE74, stop_after='verify_held', policy='assume',
                                     execution_profile='optimistic_v1')
        with patch('sys.stdout', io.StringIO()) as output:
            cli.report_pause('optimistic_scenario1.sh', Path('/tmp/example-checkpoint.json'), cp, False, args=args)
        self.assertIn('--table-height-cm 74', output.getvalue())
        self.assertNotIn('--profile', output.getvalue())

    def test_fake_pickup_run_dispatches_no_deposit_and_persists_intent_in_profile_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root/'run'
            messages = []

            class FakeConnection:
                def __init__(self, payload, wifi, location, *, console=None):
                    if payload['profile'] != TABLE74:
                        raise AssertionError('Wrong execution profile')
                    self.checkpoint = copy.deepcopy(payload['checkpoint'])
                    self.evidence = location
                    self.process = Mock()
                    self.process.wait.return_value = 0

                def send(self, message):
                    messages.append(copy.deepcopy(message))
                    if message['command'] == 'stage':
                        stage = message['stage']
                        if stage not in ('navigate_get1', 'enable_vision', 'grasp', 'verify_held'):
                            raise AssertionError('Unexpected post-pickup command')
                        options = dict(confirmed_box='held', verification_source='assumed') if stage == 'verify_held' else {}
                        self.checkpoint = contract.complete_stage(
                            contract.begin_stage(self.checkpoint, stage), stage, **options)
                        cli.atomic_json(self.evidence/'checkpoint.json', self.checkpoint)

                def wait(self, desired, timeout=None):
                    return dict(checkpoint=self.checkpoint, context={}, map_name='utars_nav_map',
                                nav_state='FSM_WAITNAVIGATE')

                def close(self):
                    pass

            with patch.object(cli, 'Connection', FakeConnection), \
                    patch.object(cli.subprocess, 'run'), \
                    patch.object(cli.subprocess, 'Popen', side_effect=AssertionError('No processes')), \
                    patch('builtins.input', side_effect=AssertionError('No prompts')), \
                    patch.object(cli, 'open', side_effect=lambda name, mode: open(root/Path(name).name, mode), create=True), \
                    patch('sys.stdout', io.StringIO()):
                result = cli.main(['--run', '--table-height-cm', '74', '--stop-after', 'grasp',
                                   '--evidence-dir', str(evidence)],
                                  policy='assume', execution_profile='optimistic_v1')
            self.assertEqual(result, 0)
            self.assertEqual([m['stage'] for m in messages if m['command'] == 'stage'],
                             ['navigate_get1', 'enable_vision', 'grasp', 'verify_held'])
            self.assertEqual(messages[-1], {'command': 'finish'})
            saved = json.loads((evidence/'checkpoint.json').read_text())
            self.assertEqual(saved['profile_id'], cli.TABLE74_PREPARATION_ID)
            self.assertEqual(saved['profile_sha256'], contract._profile_hash(TABLE74))
            self.assertEqual(saved['box_state'], 'held')
            self.assertEqual(json.loads((evidence/'profile.json').read_text()), TABLE74)
            intent = json.loads((evidence/'table-preparation.json').read_text())
            self.assertFalse(intent['deposit_executable'])
            self.assertEqual(intent['profile_sha256'], saved['profile_sha256'])


if __name__ == '__main__':
    unittest.main()
