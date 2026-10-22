"""Recorded-recipe execution uses assumptions, never invented observations.

Only local JSON fixtures and mocked phase boundaries are used. No transport,
native library, ROS publisher or robot control process is reached.
"""
from contextlib import ExitStack
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.box_handling import scenario1_cli as cli
from scripts.box_handling import scenario1_table74_cycle as cycle
from scripts.box_handling import scenario1_table74_recipe as recipe
from scripts.box_handling import scenario1_table74_current_release_run as release_run
from scripts.box_handling import scenario1_table74_finish as finish
from scripts.box_handling.test_scenario1_table74_current_trial_run import source_checkpoint
from scripts.box_handling.test_scenario1_table74_current_release_run import PROFILE, support_proof
from scripts.box_handling.test_scenario1_table74_current_release_run import payload as supervised_release_payload
from scripts.box_handling.test_scenario1_table74_trial_run import SUCCESS


ISOLATED_LOADER = '''import json,sys,types
query=json.loads(sys.stdin.read());payload=query['payload']
for name,source in payload.pop('modules'):
 module=types.ModuleType(name);sys.modules[name]=module
 exec(compile(source,name+'.py','exec'),module.__dict__)
module=sys.modules['scenario1_table74_current_release_run']
machine=module.ReleaseRuntime(payload,lambda *args,**kwargs:None)
print(json.dumps(dict(builder_version=machine.trial_bundle['manifest']['builder_version'],
 recipe=sys.modules['scenario1_table74_recipe'].validate_record(payload['recipe_provenance']),
 checkpoint_unchanged=machine.checkpoint==payload['resume_source_checkpoint'],
 ordinary_plan_executable=machine.resume_plan['executable'],
 native_scope=sys.modules['scenario1_table74_native_completion'].__name__)))
'''

ISOLATED_REJECTIONS = '''import json,sys,types
query=json.loads(sys.stdin.read())
for name,source in query['modules']:
 module=types.ModuleType(name);sys.modules[name]=module
 exec(compile(source,name+'.py','exec'),module.__dict__)
errors=[]
for payload in query['cases']:
 try:
  sys.modules['scenario1_table74_current_release_run'].ReleaseRuntime(payload,lambda *a,**k:None)
 except ValueError as exc:errors.append(str(exc))
 else:raise AssertionError('Release runtime admitted incompatible recipe provenance')
print(json.dumps(errors))
'''


def recorded_release_payload():
    policy = recipe.RecipePolicy.from_default()
    proof = support_proof()
    info = release_run.validate_predecessor(proof, PROFILE)
    selected = finish.parser().parse_args(['--finish-deposit', '--table-height-cm', '74',
        '--phase', 'pin-relief', '--after', '/unused-local-fixture'])
    reference, missing, _ = finish.reference_for(selected, info, execution_policy=policy)
    if missing:
        raise AssertionError('Recorded reference unexpectedly incomplete')
    bundle = finish.build_bundle(reference)
    payload = release_run.make_payload('run', PROFILE, proof, bundle)
    payload['recipe_provenance'] = policy.as_dict()
    return payload


def arguments(*flags):
    return cli.parser('assume', 'optimistic_v1').parse_args(['--table-height-cm', '74', *flags])


class RecipeHarness:
    """Real recipe policy; replace only already-tested native phase boundaries."""
    def __init__(self, root):
        self.root = root
        self.stop = SimpleNamespace(requested=False)
        self.calls = []
        self.source = root/'checkpoint.json'
        self.source.write_text(json.dumps(source_checkpoint()))
        self.stack = ExitStack()

    def __enter__(self):
        def pickup(args, stop, evidence):
            self.calls.append(('pickup', args.box_alignment_attempts))
            return self.source
        def phase(kind, after, source, evidence, wifi=False, **kwargs):
            self.calls.append(('phase', kind))
            self.check_policy(kwargs)
            return evidence/'physical-run'
        def release(after, evidence, stage, clearance, pin_exit, pins_free=False, **kwargs):
            self.calls.append(('release', stage, clearance, pin_exit, pins_free))
            self.check_policy(kwargs)
            return evidence/'physical-run'
        def home(**kwargs):
            self.calls.append(('home',))
            self.check_policy(kwargs)
            return dict(phase='succeeded', measured_home=True)
        entries = [patch.object(cycle.installer, '_lock', return_value=Mock()),
            patch.object(cycle.sys.stdin, 'isatty', return_value=False),
            patch('builtins.input', side_effect=AssertionError('Recipe execution must not prompt')),
            patch.object(cycle, 'pickup', side_effect=pickup),
            patch.object(cycle, 'execute_phase', side_effect=phase),
            patch.object(cycle, 'release_phase', side_effect=release),
            patch.object(cycle.home, 'run', side_effect=home),
            patch.object(cycle.subprocess, 'run', side_effect=AssertionError('No test transport')),
            patch.object(recipe.RecipePolicy, 'validate_completion', return_value=None),
            patch('sys.stdout', io.StringIO()), patch('sys.stderr', io.StringIO())]
        mocks = [self.stack.enter_context(entry) for entry in entries]
        self.pickup, self.phase, self.release, self.home = mocks[3:7]
        self.completion = mocks[8]
        return self

    @staticmethod
    def check_policy(kwargs):
        if type(kwargs.get('execution_policy')) is not recipe.RecipePolicy:
            raise AssertionError('Native boundary lost its explicit recorded-recipe policy')

    def __exit__(self, *exc):
        return self.stack.__exit__(*exc)

    def run(self, *extra):
        return cycle.run(arguments('--run', '--evidence-dir', str(self.root/'cycle'), *extra), self.stop)

    def journal(self):
        return json.loads((self.root/'cycle/cycle.json').read_text())


class RecipePolicyTests(unittest.TestCase):
    def test_versioned_recipe_json_matches_the_pinned_runtime_recipe(self):
        source = Path(recipe.__file__).with_suffix('.json')
        self.assertEqual(json.loads(source.read_text()), recipe.RecipePolicy.from_default().as_dict()['recipe'])

    def test_default_is_explicit_recorded_assumption_and_returns_defensive_copies(self):
        policy = recipe.RecipePolicy.from_default()
        record = policy.as_dict()
        self.assertIn('recorded_recipe_assumption', json.dumps(record))
        before = copy.deepcopy(record)
        record.clear()
        self.assertEqual(policy.as_dict(), before)
        facts = policy.facts()
        snapshot = copy.deepcopy(facts)
        self.assertEqual(snapshot, dict(gap_after_approach_cm=19, gap_after_precontact_cm=5,
            support_assumed=True, tool_clearance_before_relief_cm=8, required_pin_exit_cm=2,
            tool_clearance_after_relief_cm=5, pins_free_assumed=True,
            lateral_path_assumed_clear=True, empty_tools_after_open_assumed=True))
        self.assertIs(before['current_physical_measurement'], False)
        facts.clear()
        self.assertEqual(policy.facts(), snapshot)

    def test_authorization_has_provenance_without_input_or_claiming_sensor_support(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            policy = recipe.RecipePolicy.from_default()
            with patch('builtins.input', side_effect=AssertionError('No question')):
                policy.authorize('HOME74', root)
            artifacts = [json.loads(path.read_text()) for path in root.rglob('*.json')]
            # Exact receipt layout belongs to the policy. Its persistent record
            # must still expose the crucial distinction from physical sensing.
            encoded = json.dumps(artifacts)
            self.assertIn('recorded_recipe_assumption', encoded)
            self.assertIn('HOME74', encoded)
            self.assertIn('"current_physical_measurement": false', encoded)
            self.assertNotIn('"physical_support_measured": true', encoded)
            self.assertNotIn('"sensor_verified": true', encoded)

    def test_unknown_token_is_not_a_general_yes_bypass(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises((ValueError, RuntimeError)):
                recipe.RecipePolicy.from_default().authorize('DISABLE_ESTOP', Path(directory))

    def test_changed_geometry_provenance_or_boolean_representation_is_rejected(self):
        for mutation in ('height', 'source', 'hash', 'bool'):
            record = recipe.RecipePolicy.from_default().as_dict()
            if mutation == 'height':
                record['recipe']['surface_height_cm'] = 69.5
            elif mutation == 'source':
                record['source_evidence'] = 'unverified-other-run'
            elif mutation == 'hash':
                record['recipe_sha256'] = '0'*64
            else:
                record['recipe']['facts']['support_assumed'] = 1
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                recipe.RecipePolicy(record)

    def test_fake_policy_or_mutated_authenticated_policy_does_not_skip_physical_token(self):
        class Fake:
            def as_dict(self):
                return recipe.RecipePolicy.from_default().as_dict()
        with self.assertRaises(ValueError):
            recipe.assert_policy(Fake())
        policy = recipe.RecipePolicy.from_default()
        policy._record['current_physical_measurement'] = True
        with self.assertRaises(ValueError):
            recipe.assert_policy(policy)

    def test_native_completion_requires_unique_verified_event_matching_finished_action(self):
        policy = recipe.RecipePolicy.from_default()
        check = dict(event='table74_native_completion', verified=True, goal_id='native-goal', bundle_id='bundle')
        journal = dict(phase='succeeded', bundle_id='bundle', result=dict(goal_id='native-goal'))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def put(rows, record):
                (root/'events.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
                (root/'trial.json').write_text(json.dumps(record))
            put([check], journal)
            self.assertEqual(policy.validate_completion(root, root), check)
            cases = [([], journal), ([check, check], journal),
                ([dict(check, verified=False)], journal), ([dict(check, verified=1)], journal),
                ([dict(check, goal_id='other')], journal), ([dict(check, bundle_id='other')], journal),
                ([check], dict(journal, phase='pending'))]
            for rows, record in cases:
                put(rows, record)
                with self.subTest(rows=rows, phase=record['phase']), self.assertRaises(RuntimeError):
                    policy.validate_completion(root, root)

    def test_version3_release_payload_loads_all_sources_in_isolated_remote_namespace(self):
        payload = recorded_release_payload()
        result = subprocess.run([sys.executable, '-I', '-B', '-c', ISOLATED_LOADER],
            input=json.dumps(dict(payload=payload)), text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        observed = json.loads(result.stdout)
        self.assertEqual(observed['builder_version'], 3)
        self.assertEqual(observed['recipe'], recipe.RecipePolicy.from_default().as_dict())
        self.assertTrue(observed['checkpoint_unchanged'])
        self.assertFalse(observed['ordinary_plan_executable'])
        self.assertEqual(observed['native_scope'], 'scenario1_table74_native_completion')

    def test_isolated_release_runtime_rejects_missing_false_tampered_or_wrong_version_policy(self):
        valid = recorded_release_payload()
        modules = valid.pop('modules')
        cases = []
        for mutation in ('missing', 'none', 'false', 'changed'):
            payload = copy.deepcopy(valid)
            if mutation == 'missing':
                payload.pop('recipe_provenance')
            elif mutation == 'none':
                payload['recipe_provenance'] = None
            elif mutation == 'false':
                payload['recipe_provenance'] = False
            else:
                payload['recipe_provenance']['recipe']['facts']['support_assumed'] = 1
            cases.append(payload)
        supervised = supervised_release_payload()
        supervised['recipe_provenance'] = recipe.RecipePolicy.from_default().as_dict()
        cases.append(supervised)
        result = subprocess.run([sys.executable, '-I', '-B', '-c', ISOLATED_REJECTIONS],
            input=json.dumps(dict(modules=modules, cases=cases)), text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        errors = json.loads(result.stdout)
        self.assertEqual(len(errors), 5)
        self.assertTrue(all('recipe' in error.lower() for error in errors))


class RecipeCycleTests(unittest.TestCase):
    def test_real_trial_stage_marks_failed_after_vendor_success_when_native_guard_rejects(self):
        source = source_checkpoint()
        bundle = cycle.build_approach(source)
        payload = cycle.approach_run.make_payload('run', PROFILE, source, bundle)
        payload['recipe_provenance'] = recipe.RecipePolicy.from_default().as_dict()
        events = []
        machine = cycle.approach_run.CurrentTrialRuntime(payload,
            lambda event, **values: events.append(dict(event=event, **values)))
        with tempfile.TemporaryDirectory() as directory:
            machine.session = Path(directory)
            machine.armed = machine.resume_validated = True
            gates = {name: Mock() for name in ('connected', 'discover', 'hashes', 'health',
                'check_resume_entry', 'quick_health', 'verify_trial_files')}
            with patch.multiple(machine, **gates), \
                    patch.object(machine, 'action', return_value=copy.deepcopy(SUCCESS)) as action, \
                    patch.object(machine, 'audit_native_completion', side_effect=RuntimeError('DectionForceCollision')) as audit, \
                    patch.object(cycle.subprocess, 'run', side_effect=AssertionError('No test transport')):
                with self.assertRaisesRegex(RuntimeError, 'DectionForceCollision'):
                    machine.stage(dict(command='stage', stage=cycle.approach_run.STAGE))
            action.assert_called_once()
            audit.assert_called_once()
            journal = json.loads((machine.session/'trial.json').read_text())
            self.assertEqual(journal['phase'], 'failed')
            self.assertEqual(journal['result']['status'], 4)
            self.assertIs(journal['physical_support_confirmed'], False)
            self.assertIs(journal['automatic_retry'], False)
            self.assertFalse(machine._trial_dispatch)
            self.assertFalse(any(event['event'] == 'stage_complete' for event in events))

    def test_recipe_phase_uses_one_run_with_its_own_preflight_instead_of_a_second_check_session(self):
        policy = recipe.RecipePolicy.from_default()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'checkpoint.json'
            source.write_text(json.dumps(source_checkpoint()))
            with patch.object(cycle, 'installer_call', return_value=dict(installed=True)), \
                    patch.object(cycle, 'archive_installation'), \
                    patch.object(cycle, 'completed', return_value={}), \
                    patch.object(policy, 'validate_completion'), \
                    patch.object(cycle.approach_run, 'cli_main', return_value=0) as runner, \
                    patch('builtins.input', side_effect=AssertionError('No recipe prompt')):
                result = cycle.execute_phase('approach', None, source, root/'approach', execution_policy=policy)
            self.assertEqual(result, root/'approach/physical-run')
            runner.assert_called_once()
            self.assertIn('--run', runner.call_args.args[0])
            self.assertNotIn('--check', runner.call_args.args[0])
            self.assertIs(runner.call_args.kwargs['execution_policy'], policy)

    def test_default_full_recipe_needs_no_input_preserves_alignment_and_one_exact_phase_sequence(self):
        with tempfile.TemporaryDirectory() as directory, RecipeHarness(Path(directory)) as h:
            profile = cycle.PROFILE.read_bytes()
            self.assertEqual(h.run('--box-alignment-attempts', '7'), 0)
            self.assertEqual(h.calls, [('pickup', 7), ('phase', 'approach'), ('phase', 'precontact'),
                ('phase', 'support'), ('release', 'pin-relief', 8., 2., False),
                ('release', 'open', 5., 2., True), ('home',)])
            self.assertEqual(h.journal()['status'], 'succeeded')
            self.assertIs(h.journal()['physical_support_measured'], False)
            self.assertIs(h.journal()['ordinary_profile_qualified'], False)
            self.assertEqual(cycle.PROFILE.read_bytes(), profile)
            self.assertIn('recorded_recipe_assumption', json.dumps(h.journal()))

    def test_clean_held_put1_source_does_not_repeat_pickup_or_modify_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory, RecipeHarness(Path(directory)) as h:
            before = h.source.read_bytes()
            self.assertEqual(h.run('--resume', str(h.source), '--box-state', 'held'), 0)
            h.pickup.assert_not_called()
            self.assertEqual(h.calls[0], ('phase', 'approach'))
            self.assertEqual(h.source.read_bytes(), before)

    def test_pickup_failure_stops_without_approach_release_or_home(self):
        with tempfile.TemporaryDirectory() as directory, RecipeHarness(Path(directory)) as h:
            h.pickup.side_effect = RuntimeError('health lease expired')
            self.assertEqual(h.run(), 78)
            h.phase.assert_not_called()
            h.release.assert_not_called()
            h.home.assert_not_called()

    def test_each_native_phase_failure_is_sticky_and_never_triggers_extra_lowering_or_home(self):
        for index in range(3):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as directory, RecipeHarness(Path(directory)) as h:
                h.phase.side_effect = [h.root/'completed' for _ in range(index)] + [RuntimeError('native aborted')]
                self.assertEqual(h.run(), 78)
                self.assertEqual(h.phase.call_count, index+1)
                h.release.assert_not_called()
                h.home.assert_not_called()
                self.assertNotEqual(h.journal()['status'], 'succeeded')

    def test_relief_or_open_failure_never_homes_or_retries(self):
        for failure_at in (0, 1):
            with self.subTest(failure_at=failure_at), tempfile.TemporaryDirectory() as directory, RecipeHarness(Path(directory)) as h:
                h.release.side_effect = [h.root/'relief' for _ in range(failure_at)] + [RuntimeError('cancelled')]
                self.assertEqual(h.run(), 78)
                self.assertEqual(h.release.call_count, failure_at+1)
                h.home.assert_not_called()

    def test_stop_or_keyboard_interrupt_prevents_all_following_recipe_steps(self):
        for interrupt in (False, True):
            with self.subTest(interrupt=interrupt), tempfile.TemporaryDirectory() as directory, RecipeHarness(Path(directory)) as h:
                def phase(*args, **kwargs):
                    if interrupt:
                        raise KeyboardInterrupt()
                    h.stop.requested = True
                    return h.root/'approach/physical-run'
                h.phase.side_effect = phase
                self.assertEqual(h.run(), 130 if interrupt else 55)
                self.assertEqual(h.phase.call_count, 1)
                h.release.assert_not_called()
                h.home.assert_not_called()

    def test_home_still_requires_measured_success(self):
        for result in (None, dict(phase='succeeded', measured_home=False), dict(phase='failed', measured_home=True)):
            with self.subTest(result=result), tempfile.TemporaryDirectory() as directory, RecipeHarness(Path(directory)) as h:
                h.home.side_effect = None
                h.home.return_value = result
                self.assertEqual(h.run(), 78)
                self.assertNotEqual(h.journal()['status'], 'succeeded')

    def test_native_completion_guard_failure_never_reaches_next_recipe_phase(self):
        policy = recipe.RecipePolicy.from_default()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'checkpoint.json'
            source.write_text(json.dumps(source_checkpoint()))
            with patch.object(cycle, 'installer_call', return_value=dict(installed=True)), \
                    patch.object(cycle, 'archive_installation'), patch.object(cycle, 'completed', return_value={}), \
                    patch.object(cycle.approach_run, 'cli_main', return_value=0) as runner, \
                    patch.object(policy, 'validate_completion', side_effect=RuntimeError('native force collision; SUCCEED is insufficient')):
                with self.assertRaisesRegex(RuntimeError, 'native force collision'):
                    cycle.execute_phase('approach', None, source, root/'approach', execution_policy=policy)
            runner.assert_called_once()

    def test_readonly_default_check_never_authorizes_recipe_or_installs(self):
        with tempfile.TemporaryDirectory() as directory:
            selected = arguments('--evidence-dir', str(Path(directory)/'check'))
            with patch.object(cycle.installer, '_lock', return_value=Mock()), \
                    patch.object(cli, '_main', return_value=0) as child, \
                    patch.object(recipe.RecipePolicy, 'authorize', side_effect=AssertionError('Read-only check cannot authorize action')), \
                    patch.object(cycle, 'execute_phase', side_effect=AssertionError('No deposit')):
                self.assertEqual(cycle.run(selected, SimpleNamespace(requested=False)), 0)
            self.assertTrue(child.call_args.args[0].check)
            self.assertFalse(child.call_args.args[0].run)
            self.assertEqual(child.call_args.args[0].stop_after, 'put1')


if __name__ == '__main__':
    unittest.main()
