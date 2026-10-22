"""Common-height cycle tests; no network, installation on a robot or movement."""
import contextlib
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from scripts.box_handling import scenario1_cli as cli
from scripts.box_handling import scenario1_contract as contract
from scripts.box_handling import scenario1_height_deposit as height
from scripts.box_handling import scenario1_runtime as runtime
from scripts.box_handling import scenario1_table74_trial_install as installer
from scripts.box_handling.test_scenario1_runtime import SimulatedRuntime, advance
from scripts.box_handling.test_scenario1_table74_trial_install import FakeDocker


def sources():
    return [(cli.SNAPSHOT/p).read_text() for p in (
        'tasks/wrc_cruzr/put_cruzr_wrc_low.xml', 'meta_clamp/wrc/put_cruzr_wrc_low.yaml',
        'meta_clamp/wrc/open_arm_cruzr.yaml')]


def bundle(cm=74):
    return height.build_bundle(height.RECIPES[cm], *sources())


def payload(cm=74, trial=True):
    profile = height.profile(cm)
    cp = contract.new_checkpoint(profile)
    return dict(profile=profile, checkpoint=cp, mode='run', deposit_bundle=bundle(cm),
                extra_hashes=bundle(cm)['manifest']['robot_files'], height_trial_authorized=trial)


class HeightBundleTests(unittest.TestCase):
    def test_both_heights_are_deterministic_and_no_uuid_or_checkpoint_changes_identity(self):
        for cm in (74, 90):
            b = bundle(cm)
            self.assertEqual(b, height.validate_bundle(b))
            self.assertEqual(b, bundle(cm))
            self.assertEqual(b['task_name'], height.profile(cm)['deposit']['task'])
            self.assertEqual(height.profile_height(contract.validate_profile(height.profile(cm))), cm)

    def test_74_has_one_support_descent_then_separate_relief_and_open(self):
        b = bundle()
        xml = b['tasks'][height.TASK_ROOT+b['task_name']+'.xml']
        actions = ET.fromstring(xml).findall('.//Action')
        self.assertEqual([a.attrib['name'] for a in actions],
                         [b['task_name'], b['task_name']+'_relief', b['task_name']+'_open'])
        native = b['tasks'][height.META_ROOT+b['task_name']+'.yaml']
        self.assertEqual(native.count('position: [0.0, 0.0, -0.19]'), 2)
        self.assertEqual(native.count('position: [0.75, 0.285, 0.94]'), 1)
        self.assertIn('timestamp: 12.0\n          position: [0.0, 0.0, 0.0]', native)
        relief = b['tasks'][height.META_ROOT+b['task_name']+'_relief.yaml']
        opening = b['tasks'][height.META_ROOT+b['task_name']+'_open.yaml']
        self.assertEqual(relief.count('position: [0.0, 0.0, -0.04]'), 2)
        self.assertIn('position: [0.0, 0.1, 0.0]', opening)
        self.assertIn('position: [0.0, -0.1, 0.0]', opening)
        self.assertFalse(b['review']['current_support_measured'])
        self.assertIn('pending', b['review']['physical_validation'])

    def test_90_retains_historical_native_descent_torso_and_external_open(self):
        b = bundle(90)
        native = b['tasks'][height.META_ROOT+b['task_name']+'.yaml']
        expected = sources()[1]
        for y in ('0.285', '-0.285'):
            expected = expected.replace('position: [0.75, '+y+', 0.65]', 'position: [0.75, '+y+', 1.10]')
        self.assertEqual(native, expected)
        actions = ET.fromstring(b['tasks'][height.TASK_ROOT+b['task_name']+'.xml']).findall('.//Action')
        self.assertEqual(actions[-1].attrib['name'], 'wrc/open_arm_cruzr')

    def test_tampered_force_even_with_updated_manifest_is_rejected(self):
        b = bundle()
        p = height.META_ROOT+b['task_name']+'.yaml'
        b['tasks'][p] = b['tasks'][p].replace('frequency: 500', 'frequency: 100')
        b['manifest']['robot_files'][p] = height.sha(b['tasks'][p])
        with self.assertRaises(ValueError):
            height.validate_bundle(b)

    def test_swapped_height_release_or_source_pin_is_rejected(self):
        for field in ('reference', 'release', 'pin'):
            b = bundle()
            if field == 'reference': b['review']['reference']['height_cm'] = 90
            elif field == 'release': b['tasks'][height.META_ROOT+b['task_name']+'_open.yaml'] += '\n'
            else: b['manifest']['robot_files'][height.SOURCE_YAML_PATH] = '0'*64
            with self.assertRaises(ValueError): height.validate_bundle(b)

    def test_arbitrary_height_profile_or_changed_grasp_cannot_borrow_contract(self):
        with self.assertRaises(ValueError): height.profile(75)
        p = height.profile(74); p['grasp']['task'] = 'other/grasp'
        with self.assertRaises(ValueError): contract.validate_profile(p)
        p = height.profile(74); p['id'] += '_forged'
        with self.assertRaises(ValueError): contract.validate_profile(p)


class HeightRuntimeTests(unittest.TestCase):
    def test_trial_and_live_dependency_pins_are_enforced_remotely(self):
        with self.assertRaisesRegex(ValueError, 'HEIGHT_TRIAL_PENDING'):
            runtime.Runtime(payload(trial=False))
        p = payload(); del p['extra_hashes'][height.SOURCE_YAML_PATH]
        with self.assertRaisesRegex(ValueError, 'dependencies'): runtime.Runtime(p)
        p = payload(); p['deposit_bundle'] = bundle(90)
        with self.assertRaisesRegex(ValueError, 'mismatch'): runtime.Runtime(p)
        runtime.Runtime(dict(payload(trial=False), mode='check'))
        partial = payload(trial=False)
        partial['checkpoint'] = contract.new_checkpoint(height.profile(74), stop_after='verify_held')
        runtime.Runtime(partial)  # No deposit reachable, no fictitious trial permission.

    def test_shared_runtime_dispatches_one_native_deposit_and_then_home(self):
        for cm in (74, 90):
            with tempfile.TemporaryDirectory() as directory:
                # Keep the existing fault-injection runtime and durable stage checks.
                with patch('scripts.box_handling.test_scenario1_runtime.PROFILE', height.profile(cm)):
                    # The simulated legacy initializer does not send the height bundle.
                    original_init = runtime.Runtime.__init__
                    def initialize(machine, p, emit=None):
                        original_init(machine, dict(p, **{k:v for k,v in payload(cm).items() if k != 'checkpoint'}), emit)
                    with patch.object(runtime.Runtime, '__init__', initialize):
                        machine = SimulatedRuntime(directory)
                advance(machine)
                self.assertEqual(machine.calls.count(height.profile(cm)['deposit']['task']), 1)
                self.assertNotIn('wrc_cruzr/put_cruzr_wrc_low', machine.calls)
                self.assertEqual(machine.calls[-2:], ['cruzr/home', 'home_measured'])

    def test_failed_deposit_cannot_reach_home_or_released_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = SimulatedRuntime(directory)
            p = height.profile(74)
            machine.payload.update(payload())
            machine.checkpoint = contract.new_checkpoint(p)
            machine.failure_task = p['deposit']['task']
            with self.assertRaises(Exception): advance(machine)
            self.assertNotIn('cruzr/home', machine.calls)
            self.assertNotIn('verify_released', machine.checkpoint['completed'])

    def test_payload_bootstrap_loads_common_module_in_isolation(self):
        p = cli.make_payload('check', height.profile(74), contract.new_checkpoint(height.profile(74)))
        names = [name for name, _ in p['modules']]
        self.assertLess(names.index('scenario1_height_deposit'), names.index('scenario1_contract'))
        source = cli.BOOTSTRAP.replace("raise SystemExit(sys.modules['scenario1_runtime'].main(payload))", "print('LOADED')")
        result = subprocess.run([sys.executable, '-I', '-B', '-c', source], input=json.dumps(p)+'\n',
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'LOADED')


class HeightCliTests(unittest.TestCase):
    def args(self, *values):
        return cli.parser('assume', 'optimistic_v1').parse_args(list(values))

    def test_plan_uses_one_common_session_without_installation_connection_or_questions(self):
        for cm in ('74', '90'):
            with patch.object(cli, 'Connection', side_effect=AssertionError('network')), \
                 patch.object(cli, 'prepare_height_installation', side_effect=AssertionError('install')), \
                 patch('builtins.input', side_effect=AssertionError('prompt')), contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(cli.run_args(self.args('--table-height-cm', cm, '--plan')), 0)
            self.assertIn('"sessions": 1', output.getvalue())

    def test_full_run_without_trial_is_blocked_before_contact_or_install(self):
        with patch.object(cli.subprocess, 'run', side_effect=AssertionError('command')):
            with self.assertRaisesRegex(ValueError, 'HEIGHT_TRIAL_PENDING'):
                cli.run_args(self.args('--table-height-cm', '74', '--run'))

    def test_complete_cli_uses_one_connection_and_one_file_preparation(self):
        messages, connections = [], []
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            class Connection:
                def __init__(self, p, wifi, evidence, **kwargs):
                    connections.append(p)
                    self.cp, self.evidence = p['checkpoint'], evidence
                    from unittest.mock import Mock
                    self.process = Mock(); self.process.wait.return_value = 0
                def send(self, message):
                    messages.append(message)
                    if message['command'] == 'stage':
                        stage = message['stage']
                        options = ({'confirmed_box': {'verify_held':'held', 'verify_released':'released'}[stage],
                                    'verification_source':'assumed'} if stage in ('verify_held','verify_released') else {})
                        if stage == 'verify_home': options['home_verified'] = True
                        self.cp = contract.complete_stage(contract.begin_stage(self.cp, stage), stage, **options)
                        cli.atomic_json(self.evidence/'checkpoint.json', self.cp)
                def wait(self, desired, timeout=None):
                    return dict(checkpoint=self.cp, context={}, map_name='utars_nav_map', nav_state='FSM_WAITNAVIGATE')
                def close(self): pass
            with patch.object(cli, 'Connection', Connection), patch.object(cli, 'prepare_height_installation') as install, \
                 patch.object(cli.subprocess, 'run'), patch('builtins.input', side_effect=AssertionError('prompt')), \
                 patch.object(cli, 'open', side_effect=lambda name, mode: open(root/Path(name).name, mode), create=True), \
                 contextlib.redirect_stdout(io.StringIO()):
                rc = cli.run_args(self.args('--table-height-cm', '74', '--height-deposit-trial', '--run',
                                           '--evidence-dir', str(root/'run')))
            self.assertEqual(rc, 0)
            self.assertEqual(len(connections), 1)
            self.assertEqual(install.call_count, 1)
            self.assertEqual([m['stage'] for m in messages if m['command'] == 'stage'], list(contract.STAGES))
            self.assertTrue(connections[0]['height_trial_authorized'])

    def test_pause_command_retains_90_cm_and_trial_choice(self):
        args = self.args('--table-height-cm', '90', '--height-deposit-trial')
        cp = contract.new_checkpoint(height.profile(90))
        with contextlib.redirect_stdout(io.StringIO()) as output:
            cli.report_pause('optimistic_scenario1.sh', Path('/tmp/new-checkpoint.json'), cp, False, args=args)
        self.assertIn('--table-height-cm 90', output.getvalue())
        self.assertIn('--height-deposit-trial', output.getvalue())

    def test_supervised_legacy_profile_is_preserved(self):
        p, legacy = cli.selected_profile(self.args('--table-height-cm', '74', '--table74-supervised'), 'verify_home')
        self.assertTrue(legacy)
        self.assertEqual(p['id'], cli.TABLE74_PREPARATION_ID)

    def test_check_never_installs_missing_bundle(self):
        with tempfile.TemporaryDirectory() as d:
            from scripts.box_handling import scenario1_table74_cycle as existing
            with patch.object(existing, 'installer_call', return_value={'installed':False}) as call, \
                 patch.object(existing, 'archive_installation') as archive:
                with self.assertRaisesRegex(ValueError, 'NOT_INSTALLED'):
                    cli.prepare_height_installation(bundle(), Path(d), False)
                self.assertEqual([c.args[1] for c in call.call_args_list], ['check'])
                archive.assert_not_called()


class HeightInstallerTests(unittest.TestCase):
    def test_extended_installer_checks_all_pins_installs_once_and_rolls_back_only_new_files(self):
        docker = FakeDocker()
        docker.files.update(dict(zip(height.TEXT_SOURCES, sources())))
        original = docker.__call__
        def run(args, *, data=None, timeout=20):
            if len(args) > 6 and args[6] == installer.READ_SOURCE:
                q = json.loads(data)
                return json.dumps(dict(dependencies={p:dict(sha256=height.DEPENDENCIES[p],
                    **({'text':docker.files[p]} if p in q['text_sources'] else {})) for p in q['dependencies']},
                    targets={p:height.sha(docker.files[p]) if p in docker.files else None for p in q['targets']}))
            return original(args, data=data, timeout=timeout)
        with tempfile.TemporaryDirectory() as directory:
            opts = dict(run=run, evidence_root=Path(directory)/'evidence', lock_path=Path(directory)/'lock')
            b = bundle()
            self.assertFalse(installer.operate(b, operation='check', **opts)['installed'])
            installer.operate(b, operation='install', **opts)
            writes = len(docker.writes)
            self.assertEqual(writes, 4)
            self.assertTrue(docker.writes[-1].endswith('.xml'))
            installed_files = dict(docker.files)
            installer.operate(b, operation='install', **opts)
            self.assertEqual(docker.files, installed_files)
            self.assertTrue(installer.operate(b, operation='check', **opts)['installed'])
            installer.operate(b, operation='rollback', **opts)
            self.assertEqual(len(docker.removes), 4)
            self.assertTrue(all(p in docker.files for p in height.TEXT_SOURCES))


if __name__ == '__main__':
    unittest.main()
