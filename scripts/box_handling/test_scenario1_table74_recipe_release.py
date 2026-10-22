"""Recorded release assumptions are explicit; all transport here is synthetic."""
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts.box_handling import scenario1_table74_current_release as release
from scripts.box_handling import scenario1_table74_finish as finish
from scripts.box_handling import scenario1_table74_recipe as recipe
from scripts.box_handling.test_scenario1_table74_current_release import sources
from scripts.box_handling.test_scenario1_table74_current_release_run import support_proof, relief_proof


def write_proof(directory, proof):
    directory.mkdir()
    for name, value in proof.items():
        (directory/name).write_text(''.join(json.dumps(event)+'\n' for event in value)
                                  if name == 'events.jsonl' else json.dumps(value))


def arguments(after, phase='pin-relief', mode=None, evidence=None):
    result = ['--finish-deposit', '--table-height-cm', '74', '--phase', phase, '--after', str(after)]
    if mode:
        result.append('--'+mode)
    if evidence:
        result += ['--evidence-dir', str(evidence)]
    return result


def reference(stage='pin_relief'):
    policy = recipe.RecipePolicy.from_default()
    parsed = finish.parser().parse_args(arguments('unused', 'pin-relief' if stage == 'pin_relief' else 'open'))
    info = dict(completed_stage='support' if stage == 'pin_relief' else 'pin_relief',
                predecessor_sha256='b'*64, bundle_id='a'*64,
                goal_id='80974a9d-f9b2-4322-a2d7-2db41f28766e')
    return finish.reference_for(parsed, info, policy)[0]


class RecipeReleaseContractTests(unittest.TestCase):
    def test_v3_uses_exact_same_motion_as_v2_and_keeps_operator_fields_false(self):
        for stage in ('pin_relief', 'lateral_open'):
            recorded = reference(stage)
            self.assertEqual(recorded['version'], 3)
            self.assertFalse(recorded['operator_support_confirmed'])
            self.assertFalse(recorded['operator_pins_free'])
            self.assertFalse(recorded['lateral_path_clear'])
            self.assertFalse(recorded['assumption_provenance']['current_physical_measurement'])
            manual = {name: copy.deepcopy(value) for name, value in recorded.items()
                      if name != 'assumption_provenance'}
            manual.update(version=2, scope='current_supported_box_only', operator_support_confirmed=True,
                          operator_pins_free=stage == 'lateral_open', lateral_path_clear=True)
            automatic = release.build_bundle(recorded, *sources())
            supervised = release.build_bundle(manual, *sources())
            self.assertEqual(release.validate_bundle(automatic), automatic)
            self.assertEqual(automatic['tasks'][release.META_ROOT+automatic['task_name']+'.yaml'],
                             supervised['tasks'][release.META_ROOT+supervised['task_name']+'.yaml'])
            self.assertNotEqual(automatic['manifest']['id'], supervised['manifest']['id'])
            review = automatic['review']
            for key in ('current_operator_support_confirmed', 'current_operator_pins_free',
                        'current_physical_measurement', 'physical_support_sensor_verified',
                        'pin_disengagement_sensor_verified', 'release_physically_qualified',
                        'automatic_execution_authorized'):
                self.assertIs(review[key], False)

    def test_recorded_dimensions_are_exact_and_native_source_checks_remain(self):
        for stage, clearance in (('pin_relief', .08), ('lateral_open', .05)):
            ref = reference(stage)
            self.assertEqual(ref['tool_table_clearance_m'], clearance)
            self.assertEqual(ref['required_pin_exit_m'], .02)
            bundle = release.build_bundle(ref, *sources())
            self.assertEqual(bundle['review']['left_hand_delta_m'], [0., 0., -.04] if stage == 'pin_relief' else [0., .1, 0.])
            self.assertTrue(bundle['review']['native_controls_preserved'])
            xml, yaml = sources()
            with self.assertRaisesRegex(ValueError, 'checksum'):
                release.build_bundle(ref, xml, yaml+'\n')

    def test_edited_provenance_measurements_or_operator_claims_are_rejected(self):
        changes = (
            ('operator_support_confirmed', True), ('operator_pins_free', True),
            ('lateral_path_clear', True), ('scope', 'current_supported_box_only'),
            ('tool_table_clearance_m', .081), ('required_pin_exit_m', .03),
        )
        for field, value in changes:
            ref = reference(); ref[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                release.build_bundle(ref, *sources())
        for field, value in (('recipe_sha256', 'f'*64), ('current_physical_measurement', True)):
            ref = reference(); ref['assumption_provenance'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                release.build_bundle(ref, *sources())
        for field, value in (('support_assumed', False), ('pins_free_assumed', False),
                             ('tool_clearance_after_relief_cm', 6)):
            ref = reference('lateral_open'); ref['assumption_provenance']['recipe']['facts'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                release.build_bundle(ref, *sources())

    def test_v3_provenance_is_required_only_in_version3(self):
        ref = reference(); del ref['assumption_provenance']
        with self.assertRaises(ValueError):
            release.validate_reference(ref)
        ref = reference(); ref['version'] = 2
        with self.assertRaises(ValueError):
            release.validate_reference(ref)

    def test_remote_installer_reproduces_v3_without_local_repository_access(self):
        automatic = release.build_bundle(reference(), *sources())
        code = finish.installer.remote_source()
        code += '\nassert sys.modules["scenario1_table74_current_release"].validate_bundle('+repr(automatic)+') == '+repr(automatic)+'\n'
        result = subprocess.run([sys.executable, '-I', '-'], input=code, text=True,
                                capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)


class RecipeFinishTests(unittest.TestCase):
    def test_invalid_policy_rejected_before_predecessor_or_transport(self):
        with patch.object(finish.runner, 'load_predecessor', side_effect=AssertionError('No source reads')):
            with self.assertRaises((ValueError, TypeError)):
                finish.main(arguments('unused'), execution_policy={'kind': 'recorded_recipe_assumption'})

    def test_recipe_plan_is_offline_and_not_an_operator_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); after = root/'after'; write_proof(after, support_proof())
            with patch.object(finish, 'installer_call', side_effect=AssertionError('No installer')), \
                    patch.object(finish.runner, 'cli_main', side_effect=AssertionError('No runtime')), \
                    patch.object(finish.cli, 'atomic_json', side_effect=AssertionError('No writes')), \
                    patch('sys.stdout', io.StringIO()) as output:
                self.assertEqual(finish.main(arguments(after), execution_policy=recipe.RecipePolicy.from_default()), 0)
            report = json.loads(output.getvalue())
            self.assertTrue(report['recipe_reference_complete'])
            self.assertFalse(report['operator_reference_complete'])
            self.assertFalse(report['current_physical_measurement'])
            self.assertFalse(report['declarations']['supported'])
            self.assertFalse(report['reference_created'])
            self.assertEqual([path.name for path in root.iterdir()], ['after'])

    def test_recipe_run_has_one_runner_with_its_own_preflight_and_no_tty_or_input(self):
        for phase, proof in (('pin-relief', support_proof()), ('open', relief_proof())):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as directory:
                root = Path(directory); after = root/'after'; write_proof(after, proof)
                evidence = root/'run'; policy = recipe.RecipePolicy.from_default(); calls = []
                def install(*values):
                    calls.append(('install', values[1])); return {'status': 'installed'}
                def execute(argv, *, execution_policy=None):
                    self.assertIs(execution_policy, policy)
                    self.assertEqual(argv[0], '--run')
                    calls.append(('runner', argv[0]))
                    (after/'trial.json.consumed.json').write_text('{}')
                    return 0
                with patch.object(finish, 'installer_call', side_effect=install), \
                        patch.object(finish.runner, 'cli_main', side_effect=execute), \
                        patch('sys.stdin.isatty', side_effect=AssertionError('No TTY test')), \
                        patch('builtins.input', side_effect=AssertionError('No input')), \
                        patch('sys.stdout', io.StringIO()):
                    self.assertEqual(finish.main(arguments(after, phase, 'run', evidence), execution_policy=policy), 0)
                self.assertEqual(calls, [('install', 'install'), ('runner', '--run')])
                report = json.loads((evidence/'supervisor.json').read_text())
                self.assertEqual(report['status'], 'phase_completed')
                self.assertEqual(report['movement_commands_sent'], 1)
                self.assertTrue(report['health_ready'])
                self.assertTrue(report['duplicate_standalone_live_check_omitted'])
                self.assertEqual(report['declarations_kind'], 'historical_recipe_assumptions_not_current_operator_state')
                self.assertIsNone(report['declarations_recorded_ns'])
                self.assertFalse(report['physical_release_measured'])
                self.assertFalse(report['next_phase_automatic'])
                self.assertFalse((evidence/'technical-check').exists())
                recorded = json.loads((evidence/'reference.json').read_text())
                self.assertEqual(recorded['version'], 3)
                self.assertFalse(recorded['operator_support_confirmed'])

    def test_failed_native_runner_stops_without_claiming_success_or_healthy_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); after = root/'after'; write_proof(after, support_proof()); evidence = root/'failed'
            with patch.object(finish, 'installer_call', return_value={}), \
                    patch.object(finish.runner, 'cli_main', return_value=78) as execute, \
                    patch('builtins.input', side_effect=AssertionError('No input')), \
                    patch('sys.stdout', io.StringIO()), self.assertRaisesRegex(RuntimeError, 'FINISH_PHASE_FAILED'):
                finish.main(arguments(after, mode='run', evidence=evidence), execution_policy=recipe.RecipePolicy.from_default())
            execute.assert_called_once()
            report = json.loads((evidence/'supervisor.json').read_text())
            self.assertEqual(report['status'], 'interrupted')
            self.assertFalse(report['health_ready'])
            self.assertEqual(report['movement_commands_sent'], 0)
            self.assertFalse(report['source_journal_consumed'])

    def test_recipe_does_not_accept_current_operator_declarations_or_other_dimensions(self):
        with tempfile.TemporaryDirectory() as directory:
            after = Path(directory)/'after'; write_proof(after, support_proof())
            for flags in (['--supported'], ['--path-clear'], ['--operator-note', 'Current measurement'],
                          ['--tool-clearance-cm', '5'], ['--pin-exit-cm', '4']):
                with self.subTest(flags=flags), self.assertRaises(ValueError):
                    finish.main(arguments(after)+flags, execution_policy=recipe.RecipePolicy.from_default())


if __name__ == '__main__':
    unittest.main()
