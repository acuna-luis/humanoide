"""Table 69.5 cm behavior: local sources, temporary files and fake transports."""
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

import yaml

from scripts.box_handling import prepare_scenario1_table695 as prepare
from scripts.box_handling import scenario1_cli as cli
from scripts.box_handling import scenario1_contract as contract
from scripts.box_handling import scenario1_deposit_profiles as profiles
from scripts.box_handling import scenario1_resume as resume
from scripts.box_handling import scenario1_runtime as runtime
from scripts.box_handling import scenario1_table695 as table695
from scripts.box_handling import scenario1_table695_install as installer
from scripts.box_handling import scenario1_table90 as table90


def profile():
    return json.loads((cli.ROOT / 'config/box_handling/scenario1_table695_geometry.json').read_text())


def bundle():
    return json.loads(prepare.candidate()['bundle.json'])


def payload(mode='check', *, trial=False, stop_after='deposit'):
    geometry = profile()
    checkpoint = contract.new_checkpoint(geometry, stop_after=stop_after,
        policy='assume', execution_profile='optimistic_v1')
    value = cli.make_payload(mode, geometry, checkpoint)
    value.update(policy='assume', execution_profile='optimistic_v1', deposit_trial=trial)
    return value


def plan(*extra):
    args = cli.parser('assume', 'optimistic_v1').parse_args(['--plan', *extra])
    output = io.StringIO()
    with patch('sys.stdout', output), patch.object(cli, 'Connection', side_effect=AssertionError('No SSH')):
        result = cli._main(args)
    if result != 0:
        raise AssertionError('Local plan did not succeed')
    text = output.getvalue()
    return text, json.loads(text[text.index('{'):])


class Table695Tests(unittest.TestCase):
    def test_only_absolute_hand_height_changes_and_twenty_cm_descent_remains(self):
        original = yaml.safe_load((prepare.SNAPSHOT / 'meta_clamp/wrc/put_cruzr_wrc_low.yaml').read_text())
        changed = yaml.safe_load(bundle()['tasks'][table695.META_ROOT + table695.TASK_NAME + '.yaml'])
        hands = []
        for item in changed['request']['robot_trajectory_data']:
            if item['body_name'] in ('left_hand', 'right_hand'):
                hands.append(item['body_name'])
                self.assertAlmostEqual(item['data'][0]['position'][2], .895)
                self.assertAlmostEqual(item['data'][2]['position'][2], -.20)
                self.assertAlmostEqual(item['data'][0]['position'][2] + item['data'][2]['position'][2], .695)
                item['data'][0]['position'][2] = .65
        self.assertCountEqual(hands, ['left_hand', 'right_hand'])
        self.assertEqual(changed, original)

    def test_new_task_and_profile_cannot_borrow_table90_physical_qualification(self):
        geometry = profile()
        self.assertNotEqual(table695.TASK_NAME, table90.TASK_NAME)
        self.assertNotEqual(table695.PROFILE_ID, table90.PROFILE_ID)
        self.assertIsNone(table695.PHYSICAL_QUALIFICATION)
        self.assertFalse(table695.motion_qualified(geometry))
        value = bundle()
        self.assertEqual(value['manifest']['physical_validation'], 'pending')
        self.assertEqual(value['review']['physical_validation'], 'pending')
        self.assertIs(value['review']['executable'], False)
        report = json.loads(prepare.candidate()['review.json'])
        self.assertIs(report['executable'], False)
        self.assertIsNone(report['physical_qualification'])

    def test_registry_selects_exact_tasks_and_original_remains_native(self):
        geometry90 = json.loads((cli.ROOT / 'config/box_handling/scenario1_table90_geometry.json').read_text())
        original = json.loads((cli.HERE / 'scenario1_current_geometry.json').read_text())
        self.assertIs(profiles.select(profile()), table695)
        self.assertIs(profiles.select(geometry90), table90)
        self.assertIsNone(profiles.select(original))
        changed = profile()
        changed['deposit']['task'] += '_unrecognized'
        with self.assertRaises(ValueError):
            contract.validate_profile(changed)

    def test_force_torso_height_and_claimed_validation_tampering_are_rejected(self):
        original = bundle()
        path = table695.META_ROOT + table695.TASK_NAME + '.yaml'
        for field in ('force', 'torso', 'height'):
            changed = copy.deepcopy(original)
            text = changed['tasks'][path]
            if field == 'force':
                self.assertIn('collision_detect: true', text)
                text = text.replace('collision_detect: true', 'collision_detect: false', 1)
            elif field == 'torso':
                self.assertIn('torso: [0.0', text)
                text = text.replace('torso: [0.0', 'torso: [1.0', 1)
            else:
                data = yaml.safe_load(text)
                hand = next(item for item in data['request']['robot_trajectory_data'] if item['body_name'] == 'left_hand')
                hand['data'][0]['position'][2] += .01
                text = yaml.safe_dump(data)
            changed['tasks'][path] = text
            changed['manifest']['robot_files'][path] = table695.sha(text)
            with self.subTest(field=field), self.assertRaises(ValueError):
                table695.validate_bundle(changed)
        for part, key, value in (('review', 'executable', True),
                                 ('review', 'physical_validation', 'completed_operator_confirmed'),
                                 ('manifest', 'physical_validation', 'verified')):
            changed = copy.deepcopy(original)
            changed[part][key] = value
            with self.subTest(part=part, key=key), self.assertRaises(ValueError):
                table695.validate_bundle(changed)

    def test_false_verified_profile_labels_are_rejected(self):
        geometry = profile()
        geometry['deposit']['compatibility'] = 'verified'
        with self.assertRaises(ValueError):
            contract.validate_profile(geometry)

    def test_checkpoints_from_45_695_and_90_cannot_be_cross_resumed(self):
        geometries = [json.loads((cli.HERE / 'scenario1_current_geometry.json').read_text()),
                      profile(),
                      json.loads((cli.ROOT / 'config/box_handling/scenario1_table90_geometry.json').read_text())]
        for source in geometries:
            checkpoint = contract.new_checkpoint(source, stop_after='deposit',
                policy='assume', execution_profile='optimistic_v1')
            for target in geometries:
                if source['id'] == target['id']:
                    contract.validate_checkpoint(checkpoint, target)
                else:
                    with self.subTest(source=source['id'], target=target['id']), self.assertRaises(ValueError):
                        resume.plan_resume(checkpoint, target, stop_after='deposit',
                            policy='assume', execution_profile='optimistic_v1')

    def test_trial_authorizes_only_deposit_boundary_and_keeps_home_pending(self):
        geometry = profile()
        table695.require_motion_ready(geometry, 'verify_held')
        for stop_after in ('deposit', 'verify_home'):
            with self.subTest(stop_after=stop_after), self.assertRaises(ValueError):
                table695.require_motion_ready(geometry, stop_after)
        table695.require_motion_ready(geometry, 'deposit', deposit_trial=True)
        table695.require_motion_ready(geometry, 'deposit', 'deposit', deposit_trial=True)
        with self.assertRaises(ValueError):
            table695.require_motion_ready(geometry, 'verify_home', deposit_trial=True)
        checkpoint = contract.new_checkpoint(geometry, stop_after='deposit',
            policy='assume', execution_profile='optimistic_v1')
        for stage in contract.STAGES[:contract.STAGES.index('deposit') + 1]:
            checkpoint = contract.begin_stage(checkpoint, stage)
            checkpoint = contract.complete_stage(checkpoint, stage,
                confirmed_box='held' if stage == 'verify_held' else None,
                verification_source='assumed' if stage == 'verify_held' else 'operator')
        self.assertIsNone(contract.next_stage(checkpoint))
        self.assertEqual(checkpoint['box_state'], 'unknown')
        self.assertNotIn('verify_released', checkpoint['completed'])
        self.assertNotIn('home', checkpoint['completed'])
        self.assertFalse(table695.motion_qualified(geometry))

    def test_runtime_rechecks_trial_and_rejects_full_cycle_even_with_flag(self):
        runtime.Runtime(payload('check'))
        with self.assertRaises(ValueError):
            runtime.Runtime(payload('run'))
        runtime.Runtime(payload('run', trial=True))
        with self.assertRaises(ValueError):
            runtime.Runtime(payload('run', trial=True, stop_after='verify_home'))

    def test_runtime_check_rejects_nonboolean_trial_and_wrong_trial_scope(self):
        for trial in ('true', 'false', 1, 0, None, []):
            with self.subTest(trial=trial), self.assertRaisesRegex(ValueError, 'DEPOSIT_TRIAL_INVALID'):
                runtime.Runtime(payload('check', trial=trial))
        with self.assertRaisesRegex(ValueError, 'DEPOSIT_TRIAL_INVALID'):
            runtime.Runtime(payload('check', trial=True, stop_after='verify_home'))
        for geometry in (json.loads((cli.HERE / 'scenario1_current_geometry.json').read_text()),
                         json.loads((cli.ROOT / 'config/box_handling/scenario1_table90_geometry.json').read_text())):
            checkpoint = contract.new_checkpoint(geometry, stop_after='deposit',
                policy='assume', execution_profile='optimistic_v1')
            value = cli.make_payload('check', geometry, checkpoint)
            value.update(policy='assume', execution_profile='optimistic_v1', deposit_trial=True)
            with self.subTest(profile=geometry['id']), self.assertRaisesRegex(ValueError, 'DEPOSIT_TRIAL_INVALID'):
                runtime.Runtime(value)

    def test_actual_deposit_stage_dispatches_695_once_only_with_trial_and_never_homes(self):
        for trial in (False, True):
            with self.subTest(trial=trial), tempfile.TemporaryDirectory() as directory:
                value = payload('check', trial=trial)
                checkpoint = value['checkpoint']
                for stage in contract.STAGES[:contract.STAGES.index('deposit')]:
                    checkpoint = contract.begin_stage(checkpoint, stage)
                    checkpoint = contract.complete_stage(checkpoint, stage,
                        confirmed_box='held' if stage == 'verify_held' else None,
                        verification_source='assumed' if stage == 'verify_held' else 'operator')
                value['checkpoint'] = checkpoint
                machine = runtime.Runtime(value, lambda *args, **kwargs: None)
                machine.session = Path(directory)
                machine.armed = True
                machine.connected = Mock()
                machine.discover = Mock()
                machine.hashes = Mock()
                machine.quick_health = Mock()

                def action(kind, goal, timeout):
                    stored = json.loads((Path(directory) / 'checkpoint.json').read_text())
                    self.assertEqual(stored, machine.checkpoint)
                    self.assertEqual(stored['in_flight'], 'deposit')
                    self.assertEqual(kind, 'motion')
                    self.assertEqual(goal['task_name'], table695.TASK_NAME)
                    return dict(event='result', status=4,
                        result={'state': {'desc': 'SUCCEED', 'state': 1101001}})

                machine.action = Mock(side_effect=action)
                if not trial:
                    with self.assertRaises(ValueError):
                        machine.stage(dict(stage='deposit'))
                    machine.action.assert_not_called()
                    self.assertEqual(machine.checkpoint['failure']['stage'], 'deposit')
                else:
                    machine.stage(dict(stage='deposit'))
                    machine.action.assert_called_once()
                    self.assertIsNone(contract.next_stage(machine.checkpoint))
                    self.assertEqual(machine.checkpoint['box_state'], 'unknown')
                    for forbidden in ('verify_released', 'home', 'verify_home'):
                        with self.assertRaises(ValueError):
                            machine.stage(dict(stage=forbidden))
                    machine.action.assert_called_once()

    def test_explicit_resume_to_deposit_keeps_selected_profile_and_trial_boundary(self):
        geometry = profile()
        checkpoint = contract.new_checkpoint(geometry, stop_after='verify_held',
            policy='assume', execution_profile='optimistic_v1')
        for stage in contract.STAGES[:contract.STAGES.index('verify_held') + 1]:
            checkpoint = contract.begin_stage(checkpoint, stage)
            checkpoint = contract.complete_stage(checkpoint, stage,
                confirmed_box='held' if stage == 'verify_held' else None,
                verification_source='assumed' if stage == 'verify_held' else 'operator')
        result = resume.plan_resume(checkpoint, geometry, stage='deposit', box_state='held',
            recovery_confirmed=True, stop_after='deposit', policy='assume', execution_profile='optimistic_v1')
        self.assertEqual(result['stage'], 'deposit')
        self.assertEqual(result['requirements']['waypoint'], 'put1')
        self.assertEqual(result['checkpoint']['profile_id'], table695.PROFILE_ID)
        self.assertEqual(result['checkpoint']['stop_after'], 'deposit')
        self.assertEqual(result['checkpoint']['completed'], [])
        self.assertEqual(result['checkpoint']['origin']['skipped_stages'], ['retreat', 'navigate_put1'])
        with self.assertRaises(ValueError):
            table695.require_motion_ready(geometry, 'deposit', result['stage'])
        table695.require_motion_ready(geometry, 'deposit', result['stage'], deposit_trial=True)

    def test_payload_pins_bundle_models_home_and_survives_remote_bootstrap(self):
        value = payload()
        _, hashes = table695.validate_bundle(value['deposit_bundle'])
        for path, digest in dict(hashes, **table695.CURRENT_MODEL_PINS).items():
            self.assertEqual(value['extra_hashes'][path], digest)
        self.assertEqual(value['extra_hashes'][table695.TASK_ROOT + 'cruzr/home.xml'],
            'd9e9462792b41300d352604b53ea2a4890a9382e942321990708f6ded2e26ccb')
        names = [name for name, _ in value['modules']]
        self.assertLess(names.index('scenario1_table90'), names.index('scenario1_table695'))
        self.assertLess(names.index('scenario1_table695'), names.index('scenario1_deposit_profiles'))
        self.assertLess(names.index('scenario1_deposit_profiles'), names.index('scenario1_contract'))
        with patch.dict(sys.modules):
            for name, source in value['modules']:
                module = types.ModuleType(name)
                sys.modules[name] = module
                exec(compile(source, name + '.py', 'exec'), module.__dict__)
            sys.modules['scenario1_runtime'].Runtime(value)
        for path in (next(iter(hashes)), next(iter(table695.CURRENT_MODEL_PINS))):
            changed = copy.deepcopy(value)
            changed['extra_hashes'].pop(path)
            with self.subTest(path=path), self.assertRaises(ValueError):
                runtime.Runtime(changed)

    def test_plan_selects_695_without_connecting_or_claiming_physical_success(self):
        text, value = plan('--table-height-cm', '69.5')
        self.assertEqual(value['profile']['deposit']['task'], table695.TASK_NAME)
        self.assertEqual(value['physical_validation'], 'pending')
        calculation = value['deposit_calculation']
        self.assertAlmostEqual(calculation['surface_height_m'], .695)
        self.assertAlmostEqual(calculation['approach_hand_z_m'], .895)
        self.assertAlmostEqual(calculation['final_hand_z_m'], .695)
        self.assertIs(calculation['executable'], False)
        self.assertIsNone(calculation['physical_qualification'])
        self.assertNotIn('ensayo físico y HOME completados', text)

    def test_default_and_explicit_90_preserve_original_tested_profile(self):
        for arguments in ((), ('--table-height-cm', '90')):
            with self.subTest(arguments=arguments):
                _, value = plan(*arguments)
                self.assertEqual(value['profile']['deposit']['task'], table90.TASK_NAME)
                self.assertAlmostEqual(value['deposit_calculation']['approach_hand_z_m'], 1.10)
                self.assertAlmostEqual(value['deposit_calculation']['final_hand_z_m'], .90)
                self.assertEqual(value['physical_validation'], 'completed_operator_confirmed')
        _, native = plan('--table-height-cm', '45')
        self.assertEqual(native['profile']['deposit']['task'], 'wrc_cruzr/put_cruzr_wrc_low')

    def test_full_695_cycle_fails_before_ssh_or_evidence_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / 'not-created'
            args = cli.parser('assume', 'optimistic_v1').parse_args([
                '--run', '--table-height-cm', '69.5', '--evidence-dir', str(destination)])
            with patch.object(cli, 'Connection', side_effect=AssertionError('No SSH')):
                with self.assertRaises(ValueError):
                    cli._main(args)
            self.assertFalse(destination.exists())

    def test_unsupported_heights_and_explicit_profile_conflicts_fail_locally(self):
        for height in ('0', '70', '-1', 'nan', 'inf', '69,5'):
            with self.subTest(height=height), patch('sys.stderr', io.StringIO()):
                with self.assertRaises((SystemExit, ValueError)):
                    args = cli.parser('assume', 'optimistic_v1').parse_args([
                        '--plan', '--table-height-cm', height])
                    cli._main(args)
        with patch('sys.stderr', io.StringIO()), self.assertRaises((SystemExit, ValueError)):
            args = cli.parser('assume', 'optimistic_v1').parse_args([
                '--plan', '--table-height-cm', '69.5', '--profile',
                str(cli.ROOT / 'config/box_handling/scenario1_table695_geometry.json')])
            cli._main(args)

    def test_trial_option_rejects_check_plan_and_non_deposit_stop(self):
        for options in (['--plan'], ['--check'], ['--run'], ['--run', '--stop-after', 'grasp']):
            with self.subTest(options=options), patch('sys.stderr', io.StringIO()):
                with patch.object(cli, 'Connection', side_effect=AssertionError('No SSH')):
                    with self.assertRaises((SystemExit, ValueError)):
                        args = cli.parser('assume', 'optimistic_v1').parse_args([
                            '--table-height-cm', '69.5', '--deposit-trial', *options])
                        cli._main(args)

    def test_trial_option_cannot_be_applied_to_native_45_or_qualified_90(self):
        for height in ('45', '90'):
            args = cli.parser('assume', 'optimistic_v1').parse_args([
                '--run', '--table-height-cm', height, '--deposit-trial', '--stop-after', 'deposit'])
            with self.subTest(height=height), patch.object(cli, 'Connection', side_effect=AssertionError('No SSH')):
                with self.assertRaises(ValueError):
                    cli._main(args)

    def test_exported_installer_uses_only_additive_file_operations_with_fake_docker(self):
        from scripts.box_handling.test_scenario1_deposit_install import FakeDocker
        source = installer.remote_source().rsplit("raise SystemExit(_files['main']())", 1)[0]
        scope = {}
        exec(compile(source, 'table695-export', 'exec'), scope)
        install = scope['_files']['install_bundle']
        fake = FakeDocker()
        with tempfile.TemporaryDirectory() as directory:
            receipt = install(bundle(), run=fake, evidence_root=Path(directory) / 'evidence',
                              lock_path=Path(directory) / 'lock')
        self.assertEqual(receipt['status'], 'installed')
        self.assertEqual(receipt['movement_commands'], 0)
        self.assertEqual(receipt['restarts'], 0)
        self.assertEqual(receipt['loaded'], 'not_verified')
        self.assertEqual(len(receipt['created_files']), 2)
        self.assertEqual(set(fake.writes), set(bundle()['tasks']))
        self.assertTrue(fake.writes[0].endswith('.yaml'))
        self.assertTrue(fake.writes[1].endswith('.xml'))
        fake = FakeDocker()
        fake.files[table695.META_ROOT + table695.TASK_NAME + '.yaml'] = 'existing conflicting task'
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(RuntimeError):
                install(bundle(), run=fake, evidence_root=Path(directory) / 'evidence',
                        lock_path=Path(directory) / 'lock')
        self.assertEqual(fake.writes, [])

    def test_local_installer_export_never_contacts_robot_or_launches_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bundle.json'
            path.write_text(json.dumps(bundle()))
            destination = Path(directory) / 'remote-program.py'
            output = io.StringIO()
            with patch.object(sys, 'argv', ['table695-installer', '--bundle', str(path),
                                          '--remote-program', str(destination)]):
                with patch('sys.stdout', output), patch.object(installer.subprocess, 'run',
                        side_effect=AssertionError('No SSH or other command execution')):
                    installer.main()
            status = json.loads(output.getvalue())
            self.assertEqual(status['remote_operations'], 0)
            self.assertEqual(status['movement_commands'], 0)
            self.assertEqual(status['physical_validation'], 'pending')
            self.assertEqual(status['loaded'], 'not_verified')
            self.assertEqual(destination.read_text(), installer.remote_source())


if __name__ == '__main__':
    unittest.main()
