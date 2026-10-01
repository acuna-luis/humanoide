"""Table90 regression checks, using local files and fake transports only."""
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yaml

from scripts.box_handling import scenario1_cli as cli
from scripts.box_handling import scenario1_contract as contract
from scripts.box_handling import scenario1_runtime as runtime
from scripts.box_handling import scenario1_table90 as table90
from scripts.box_handling import prepare_scenario1_table90 as prepare
from scripts.box_handling import scenario1_table90_install as installer


def profile():
    return json.loads((prepare.ROOT/'config/box_handling/scenario1_table90_geometry.json').read_text())


def bundle():
    return json.loads(prepare.candidate()['bundle.json'])


class Table90Tests(unittest.TestCase):
    def test_deposit_trial_stops_before_release_and_home(self):
        p = profile()
        cp = contract.new_checkpoint(p, stop_after='deposit', policy='assume', execution_profile='optimistic_v1')
        table90.require_motion_ready(p, 'deposit')
        for stage in contract.STAGES[:contract.STAGES.index('deposit')+1]:
            cp = contract.begin_stage(cp, stage)
            cp = contract.complete_stage(cp, stage, confirmed_box='held' if stage == 'verify_held' else None,
                                         verification_source='assumed' if stage == 'verify_held' else 'operator')
        self.assertIsNone(contract.next_stage(cp))
        self.assertNotIn('verify_released', cp['completed'])
        self.assertNotIn('home', cp['completed'])
        with patch.object(table90, 'PHYSICAL_QUALIFICATION', None):
            with self.assertRaisesRegex(ValueError, 'TABLE90_MOTION_PENDING'):
                table90.require_motion_ready(p, 'verify_home', 'deposit')

    def test_qualification_applies_only_to_tested_profile_and_pins_home(self):
        p = profile()
        self.assertTrue(table90.motion_qualified(p))
        table90.require_motion_ready(p, 'verify_home')
        changed = copy.deepcopy(p)
        changed['box_size_m'][0] += .01
        self.assertFalse(table90.motion_qualified(changed))
        with self.assertRaisesRegex(ValueError, 'TABLE90_MOTION_PENDING'):
            table90.require_motion_ready(changed, 'verify_home')
        cp = contract.new_checkpoint(p, policy='assume', execution_profile='optimistic_v1')
        payload = cli.make_payload('run', p, cp)
        payload.update(execution_profile='optimistic_v1', policy='assume')
        runtime.Runtime(payload)
        self.assertEqual(payload['extra_hashes'][table90.TASK_ROOT+'cruzr/home.xml'],
                         'd9e9462792b41300d352604b53ea2a4890a9382e942321990708f6ded2e26ccb')

    def test_exported_installer_adds_files_only_and_refuses_conflicts(self):
        from scripts.box_handling.test_scenario1_deposit_install import FakeDocker
        code = installer.remote_source().rsplit("raise SystemExit(_files['main']())", 1)[0]
        scope = {}
        exec(compile(code, 'table90-export', 'exec'), scope)
        install = scope['_files']['install_bundle']
        fake = FakeDocker()
        with tempfile.TemporaryDirectory() as directory:
            receipt = install(bundle(), run=fake, evidence_root=Path(directory)/'evidence',
                              lock_path=Path(directory)/'lock')
            self.assertEqual(receipt['status'], 'installed')
            self.assertEqual(receipt['movement_commands'], 0)
            self.assertEqual(receipt['restarts'], 0)
            self.assertEqual(receipt['loaded'], 'not_verified')
            self.assertEqual(len(receipt['created_files']), 2)
            self.assertTrue(fake.writes[0].endswith('.yaml'))
            self.assertTrue(fake.writes[1].endswith('.xml'))
        fake = FakeDocker()
        fake.files[table90.META_ROOT+table90.TASK_NAME+'.yaml'] = 'conflicting existing task'
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, 'Destination conflict'):
                install(bundle(), run=fake, evidence_root=Path(directory)/'evidence',
                        lock_path=Path(directory)/'lock')
            self.assertEqual(fake.writes, [])

    def test_only_hand_absolute_z_changes_and_descent_is_retained(self):
        source = yaml.safe_load((prepare.SNAPSHOT/'meta_clamp/wrc/put_cruzr_wrc_low.yaml').read_text())
        changed = yaml.safe_load(bundle()['tasks'][table90.META_ROOT+table90.TASK_NAME+'.yaml'])
        for item in changed['request']['robot_trajectory_data']:
            if item['body_name'] in ('left_hand', 'right_hand'):
                self.assertEqual(item['data'][0]['position'][2], 1.1)
                self.assertAlmostEqual(item['data'][0]['position'][2]+item['data'][2]['position'][2], .9)
                item['data'][0]['position'][2] = .65
        self.assertEqual(changed, source)

    def test_changed_torso_force_and_manifest_cannot_pass_validation(self):
        original = bundle()
        path = table90.META_ROOT+table90.TASK_NAME+'.yaml'
        for old, new in (('torso: [0.0', 'torso: [1.0'), ('collision_detect: true', 'collision_detect: false'),
                         ('position: [0.75, 0.285, 1.10]', 'position: [0.75, 0.285, 1.20]')):
            changed = copy.deepcopy(original)
            self.assertIn(old, changed['tasks'][path])
            changed['tasks'][path] = changed['tasks'][path].replace(old, new, 1)
            with self.assertRaises(ValueError):
                table90.validate_bundle(changed)
        changed = copy.deepcopy(original); changed['review']['executable'] = True
        with self.assertRaises(ValueError):
            table90.validate_bundle(changed)

    def test_payload_pins_new_tasks_and_remote_module_order(self):
        p = profile(); cp = contract.new_checkpoint(p, policy='assume', execution_profile='optimistic_v1')
        payload = cli.make_payload('check', p, cp)
        payload.update(execution_profile='optimistic_v1', policy='assume')
        _, hashes = table90.validate_bundle(payload['deposit_bundle'])
        for path, digest in hashes.items():
            self.assertEqual(payload['extra_hashes'][path], digest)
        names = [name for name, _ in payload['modules']]
        self.assertLess(names.index('scenario1_table90'), names.index('scenario1_contract'))
        # Exercise the actual standalone module namespace used by the bootstrap.
        import sys, types
        with patch.dict(sys.modules):
            for name, source in payload['modules']:
                module = types.ModuleType(name); sys.modules[name] = module
                exec(compile(source, name+'.py', 'exec'), module.__dict__)
        runtime.Runtime(payload)
        payload['extra_hashes'].pop(next(iter(hashes)))
        with self.assertRaisesRegex(ValueError, 'dependency pins'):
            runtime.Runtime(payload)

    def test_old_checkpoints_and_false_verified_labels_are_rejected(self):
        p = profile(); original = json.loads((cli.HERE/'scenario1_current_geometry.json').read_text())
        cp = contract.new_checkpoint(original, policy='assume', execution_profile='optimistic_v1')
        with self.assertRaises(ValueError):
            contract.validate_checkpoint(cp, p)
        p['deposit']['compatibility'] = 'verified'
        with self.assertRaisesRegex(ValueError, 'calculated profile'):
            contract.validate_profile(p)

    def test_pending_cycle_fails_before_transport_or_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            args = cli.parser('assume', 'optimistic_v1').parse_args(['--run', '--evidence-dir', directory+'/new'])
            with patch.object(table90, 'PHYSICAL_QUALIFICATION', None), patch.object(cli, 'Connection', side_effect=AssertionError('No SSH')):
                with self.assertRaisesRegex(ValueError, 'TABLE90_MOTION_PENDING'):
                    cli._main(args)
            self.assertFalse(Path(directory, 'new').exists())
        p = profile(); cp = contract.new_checkpoint(p, policy='assume', execution_profile='optimistic_v1')
        payload = cli.make_payload('run', p, cp)
        with patch.object(table90, 'PHYSICAL_QUALIFICATION', None):
            with self.assertRaisesRegex(ValueError, 'TABLE90_MOTION_PENDING'):
                runtime.Runtime(payload)

    def test_default_optimistic_plan_selects90_standard_keeps_original(self):
        args = cli.parser('assume', 'optimistic_v1').parse_args(['--plan'])
        with patch('sys.stdout', new_callable=io.StringIO) as output:
            self.assertEqual(cli._main(args), 0)
        self.assertIn(table90.TASK_NAME, output.getvalue())
        self.assertIn('"approach_hand_z_m": 1.1', output.getvalue())
        standard = cli.parser('assume').parse_args(['--plan'])
        self.assertEqual(standard.profile, cli.HERE/'scenario1_current_geometry.json')


if __name__ == '__main__':
    unittest.main()
