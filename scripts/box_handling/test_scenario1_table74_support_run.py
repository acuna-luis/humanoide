"""Journal-authorized support continuation; local fixtures, no robot or network."""
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.box_handling import scenario1_table74_support_run as run
from scripts.box_handling import scenario1_table74_trial_run as approach
from scripts.box_handling import scenario1_cli as cli
from scripts.box_handling import scenario1_contract as contract
from scripts.box_handling import scenario1_runtime as runtime
from scripts.box_handling.test_scenario1_table74_support import build
from scripts.box_handling.test_scenario1_table74_trial_run import PROFILE, SUCCESS, source_checkpoint, FakeRuntime

ROOT = Path(__file__).resolve().parents[2]


def predecessor():
    bundle = json.loads((ROOT/'config/box_handling/scenario1_table74/approach_trial/bundle.json').read_text())
    source, options, planned = approach.prepare_entry(source_checkpoint(), PROFILE)
    context = dict(boot_id='synthetic', containers={}, dependencies={}, points={}, execution_profile='optimistic_v1')
    terminal = dict(copy.deepcopy(SUCCESS), goal_id=run.support.PINNED_APPROACH_GOAL_ID, request_id='1')
    pending = dict(artifact='table74_approach_trial', version=1, bundle_id=bundle['manifest']['id'],
        source_sha256=planned['source_sha256'], phase='pending', intent_ns=100, finished_ns=None,
        result=None, error=None, physical_support_confirmed=False, automatic_retry=False)
    succeeded = dict(pending, phase='succeeded', finished_ns=200, result=terminal)
    rows = [dict(event='dispatched', request_id='1', goal_id=terminal['goal_id'], endpoint='/mc/manipulation/action'),
            dict(event='accepted', request_id='1', goal_id=terminal['goal_id'], accepted=True), terminal,
            dict(event='request_complete', request_id='1', returncode=0)]
    events = [dict(event='ready', context=context), dict(event='trial_dependencies', hashes=bundle['manifest']['robot_files']),
              dict(event='trial', trial=pending)]
    events += [dict(event='action', kind='motion', detail=row) for row in rows]
    events += [dict(event='trial', trial=succeeded), dict(event='stage_complete', stage='approach_trial'),
               dict(event='session_finishing', reason='requested')]
    return json.loads(json.dumps({'bundle.json': bundle, 'trial.json': succeeded, 'context.json': context,
            'source-context.json': approach.context_record(source),
            'context-checkpoint.json': approach.context_record(planned['checkpoint']), 'events.jsonl': events}))


def payload():
    proof = predecessor()
    info = run.validate_predecessor(proof, PROFILE)
    return dict(mode='run', profile=PROFILE, checkpoint=info['planned']['checkpoint'], policy='assume',
        execution_profile='optimistic_v1', cycle=False, resume_source_checkpoint=info['source'],
        resume_options=info['options'], resume_plan=info['planned'], resume_context=info['context'],
        predecessor=proof, trial_bundle=build())


class FakeSupport(run.SupportRuntime):
    def __init__(self, directory):
        self.events, self.gates = [], []
        super().__init__(payload(), lambda event, **values: self.events.append(dict(event=event, **values)))
        self.session = Path(directory)
        self.armed = self.resume_validated = True
        self.fail_at = None

    gate, connected = FakeRuntime.gate, FakeRuntime.connected
    discover, hashes, health = FakeRuntime.discover, FakeRuntime.hashes, FakeRuntime.health
    check_resume_entry, quick_health = FakeRuntime.check_resume_entry, FakeRuntime.quick_health
    verify_trial_files = FakeRuntime.verify_trial_files


class SupportProofTests(unittest.TestCase):
    def test_only_confirmed_idle_worker_closures_are_allowed_after_finish(self):
        proof = predecessor()
        for kind in ('navigation', 'motion', 'health_worker'):
            def wrap(detail):
                return dict(event='health_worker', detail=detail) if kind == 'health_worker' else dict(event='action', kind=kind, detail=detail)
            error = dict(event='error', request_id=None,
                reason='RuntimeError: Health worker lease expired or stop requested' if kind == 'health_worker' else 'Lease missing, invalid or expired')
            if kind != 'health_worker': error['goal_id'] = None
            proof['events.jsonl'].extend([wrap(error), wrap(dict(event='worker_closed',
                returncode=78 if kind == 'health_worker' else 2, physical_stop_verified=False))])
        run.validate_predecessor(proof, PROFILE)
        invalid = []
        for kind in ('motion', 'navigation'):
            invalid.append(dict(event='action', kind=kind,
                detail=dict(event='dispatched', request_id='2', goal_id='another', endpoint='/mc/manipulation/action')))
            invalid.append(dict(event='action', kind=kind,
                detail=dict(event='error', request_id='2', goal_id='another', reason='Lease missing, invalid or expired')))
        invalid += [dict(event='armed'), dict(event='stage_complete', stage='deposit'),
                    dict(event='trial', trial=copy.deepcopy(proof['trial.json'])),
                    dict(event='stage', stage='home'), dict(event='error', reason='unknown')]
        for event in invalid:
            changed = copy.deepcopy(proof); changed['events.jsonl'].append(event)
            with self.subTest(event=event), self.assertRaises(ValueError):
                run.validate_predecessor(changed, PROFILE)

    def test_exact_successful_predecessor_is_independent_and_semantically_hashed(self):
        proof = predecessor(); before = copy.deepcopy(proof)
        info = run.validate_predecessor(proof, PROFILE)
        self.assertEqual(info['goal_id'], run.support.PINNED_APPROACH_GOAL_ID)
        self.assertEqual(info['planned']['stage'], 'deposit')
        self.assertEqual(info['predecessor_sha256'], run.digest(proof))
        self.assertEqual(proof, before)

    def test_missing_failed_duplicate_cancelled_or_unpinned_evidence_is_rejected(self):
        mutations = []
        for key in run.FILES:
            proof = predecessor(); proof.pop(key); mutations.append(proof)
        proof = predecessor(); proof['trial.json']['phase'] = 'pending'; mutations.append(proof)
        proof = predecessor(); proof['trial.json']['automatic_retry'] = True; mutations.append(proof)
        proof = predecessor(); proof['trial.json']['result']['goal_id'] = 'other'; mutations.append(proof)
        proof = predecessor(); proof['context.json']['boot_id'] = 'different'; mutations.append(proof)
        proof = predecessor(); proof['context-checkpoint.json']['checkpoint']['box_state'] = 'released'; mutations.append(proof)
        for event in ('accepted', 'result', 'cancel_requested', 'error'):
            proof = predecessor()
            detail = next(e['detail'] for e in proof['events.jsonl'] if e.get('event') == 'action' and e['detail']['event'] == 'accepted')
            if event == 'result':
                detail = copy.deepcopy(proof['trial.json']['result'])
            else:
                detail = dict(detail, event=event)
            proof['events.jsonl'].insert(-1, dict(event='action', kind='motion', detail=detail))
            mutations.append(proof)
        proof = predecessor(); proof['events.jsonl'].pop(1); mutations.append(proof)
        for proof in mutations:
            with self.subTest(keys=list(proof)), self.assertRaises((ValueError, KeyError)):
                run.validate_predecessor(proof, PROFILE)

    def test_stage_complete_before_terminal_result_is_not_a_success(self):
        proof = predecessor()
        stage = proof['events.jsonl'].pop(-2)
        proof['events.jsonl'].insert(3, stage)
        with self.assertRaises(ValueError): run.validate_predecessor(proof, PROFILE)

    def test_navigation_after_approach_and_unreviewed_action_kinds_are_rejected(self):
        for kind in ('navigation', 'planning', 'unknown'):
            proof = predecessor()
            proof['events.jsonl'].insert(-1, dict(event='action', kind=kind,
                detail=dict(event='dispatched', request_id='99', goal_id='new-goal', endpoint='/vnav/task/command')))
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                run.validate_predecessor(proof, PROFILE)

    def test_real_full_bootstrap_loads_subclass_without_running_or_changing_baseline(self):
        built = run.make_payload('check', PROFILE, predecessor(), build())
        self.assertEqual(dict(built['modules'])['scenario1_runtime'], Path(runtime.__file__).read_text())
        self.assertEqual(dict(built['modules'])['scenario1_table74_trial_run'], Path(approach.__file__).read_text())
        bootstrap = run.BOOTSTRAP.replace(
            "raise SystemExit(sys.modules['scenario1_table74_support_run'].main(payload))",
            "instance=sys.modules['scenario1_table74_support_run'].SupportRuntime(payload)\n"
            "assert isinstance(instance,sys.modules['scenario1_runtime'].Runtime)\nprint('SUPPORT_BOOTSTRAP_LOADED')")
        result = subprocess.run([sys.executable, '-B', '-c', bootstrap], input=json.dumps(built),
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'SUPPORT_BOOTSTRAP_LOADED')


class SupportRuntimeTests(unittest.TestCase):
    def test_single_support_has_durable_intent_and_no_ordinary_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = FakeSupport(directory)
            before = copy.deepcopy(machine.checkpoint)
            machine.save()
            def dispatch(kind, goal, timeout):
                self.assertEqual(kind, 'motion')
                self.assertEqual(goal, {'task_name': machine.trial_bundle['task_name'], 'yaml_args': '{}'})
                self.assertEqual(json.loads((machine.session/'support.json').read_text())['phase'], 'pending')
                return copy.deepcopy(SUCCESS)
            with patch.object(runtime.Runtime, 'action', side_effect=dispatch) as action:
                machine.stage({'command': 'stage', 'stage': run.STAGE})
                with self.assertRaisesRegex(RuntimeError, 'ALREADY_ATTEMPTED'):
                    machine.stage({'command': 'stage', 'stage': run.STAGE})
                action.assert_called_once()
            self.assertEqual(machine.checkpoint, before)
            self.assertEqual(machine.trial_record['phase'], 'succeeded')
            self.assertFalse(machine.trial_record['physical_support_confirmed'])
            self.assertFalse((machine.session/'checkpoint.json').exists())
            self.assertFalse((machine.session/'trial.json').exists())
            with self.assertRaises(ValueError):
                contract.validate_checkpoint(json.loads((machine.session/'context-checkpoint.json').read_text()))
            self.assertFalse(any(e['event'] in ('checkpoint', 'trial') for e in machine.events))

    def test_gates_stop_timeout_and_failed_result_do_not_authorize_repetition(self):
        for gate in ('connected', 'discover', 'hashes', 'health', 'entry', 'stationary', 'trial_hashes', 'stop'):
            with self.subTest(gate=gate), tempfile.TemporaryDirectory() as directory:
                machine = FakeSupport(directory)
                if gate == 'stop': machine.stop.set()
                else: machine.fail_at = gate
                with patch.object(runtime.Runtime, 'action') as action:
                    with self.assertRaises(RuntimeError): machine.stage({'command': 'stage', 'stage': run.STAGE})
                    action.assert_not_called()
                    self.assertEqual(machine.trial_record['phase'], 'failed')
                    with self.assertRaisesRegex(RuntimeError, 'ALREADY_ATTEMPTED'):
                        machine.stage({'command': 'stage', 'stage': run.STAGE})
        for result in (TimeoutError('unknown'), dict(SUCCESS, status=6)):
            with tempfile.TemporaryDirectory() as directory:
                machine = FakeSupport(directory)
                with patch.object(runtime.Runtime, 'action', return_value=result,
                                  side_effect=result if isinstance(result, Exception) else None) as action:
                    with self.assertRaises((ValueError, TimeoutError)):
                        machine.stage({'command': 'stage', 'stage': run.STAGE})
                    action.assert_called_once()
                    self.assertEqual(machine.trial_record['phase'], 'failed')

    def test_no_baseline_stage_approach_navigation_home_or_opening_is_admitted(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = FakeSupport(directory)
            with patch.object(runtime.Runtime, 'action') as action:
                for stage in (*contract.STAGES, 'approach_trial'):
                    with self.assertRaises(RuntimeError): machine.stage({'command': 'stage', 'stage': stage})
                for goal in ({'task_name': 'cruzr/home', 'yaml_args': '{}'},
                             {'task_name': machine.payload['predecessor']['bundle.json']['task_name'], 'yaml_args': '{}'},
                             {'task_name': machine.trial_bundle['task_name'], 'yaml_args': '{}'}):
                    with self.assertRaises(RuntimeError): machine.action('motion', goal, 45)
                with self.assertRaises(RuntimeError):
                    machine.action('navigation', {'command': 'navigation_start', 'arg_json': '{}'}, 45)
                action.assert_not_called()


class SupportCliTests(unittest.TestCase):
    def files(self, root):
        after = root/'approach'; after.mkdir()
        for name, value in predecessor().items():
            (after/name).write_text('\n'.join(json.dumps(e) for e in value)+'\n' if name == 'events.jsonl' else json.dumps(value))
        bundle = root/'bundle.json'; bundle.write_text(json.dumps(build()))
        return after, bundle

    def test_default_plan_is_offline_and_never_claims_previous_journal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); after, bundle = self.files(root)
            before = {p.name:p.read_bytes() for p in after.iterdir()}
            with patch.object(run, 'connection_class', side_effect=AssertionError('No network')), \
                    patch.object(cli, 'claim_resume', side_effect=AssertionError('No claim')), patch('sys.stdout', io.StringIO()) as output:
                self.assertEqual(run.cli_main(['--after', str(after), '--bundle', str(bundle)]), 0)
            self.assertEqual(json.loads(output.getvalue())['stage'], run.STAGE)
            self.assertEqual(before, {p.name:p.read_bytes() for p in after.iterdir()})

    def test_check_sends_no_commands_and_does_not_create_executable_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); after, bundle = self.files(root)
            connection = Mock(); connection.wait.return_value = dict(context={}); connection.process.wait.return_value = 0
            with patch.object(run, 'connection_class', return_value=Mock(return_value=connection)), \
                    patch.object(cli, 'claim_resume', side_effect=AssertionError('No claim')), \
                    patch.object(run, 'open', side_effect=lambda name, mode: open(root/Path(name).name, mode), create=True), \
                    patch('builtins.input', side_effect=AssertionError('No prompts')), patch('sys.stdout', io.StringIO()):
                self.assertEqual(run.cli_main(['--check', '--after', str(after), '--bundle', str(bundle),
                                              '--evidence-dir', str(root/'check')]), 0)
            connection.send.assert_not_called()
            self.assertFalse((after/'trial.json.consumed.json').exists())
            self.assertFalse((root/'check/checkpoint.json').exists())

    def test_run_claims_only_trial_journal_before_arm_and_sends_one_support(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); after, bundle = self.files(root)
            evidence, messages = root/'run', []
            data = payload(); info = run.validate_predecessor(data['predecessor'], PROFILE)
            self_test = self
            class Connection:
                process = Mock(); process.wait.return_value = 0
                def send(self, value):
                    if value['command'] in ('arm','stage'):
                        self_test.assertTrue((after/'trial.json.consumed.json').is_file())
                    messages.append(value)
                    if value['command'] == 'stage':
                        cli.atomic_json(evidence/'support.json', dict(artifact='table74_support_trial', version=1,
                            bundle_id=data['trial_bundle']['manifest']['id'], source_sha256=info['predecessor_sha256'],
                            phase='succeeded', intent_ns=1, finished_ns=2, result=SUCCESS, error=None,
                            physical_support_confirmed=False, automatic_retry=False))
                def wait(self, desired, timeout=None): return dict(context={}, checkpoint=data['checkpoint'], stage=run.STAGE)
                def close(self): pass
            with patch.object(run, 'connection_class', return_value=Mock(return_value=Connection())), \
                    patch.object(run, 'open', side_effect=lambda name, mode: open(root/Path(name).name, mode), create=True), \
                    patch.object(run.subprocess, 'run'), patch('sys.stdin.isatty', return_value=True), \
                    patch('builtins.input', return_value='APOYAR'), patch('sys.stdout', io.StringIO()) as output:
                self.assertEqual(run.cli_main(['--run', '--after', str(after), '--bundle', str(bundle),
                                              '--evidence-dir', str(evidence)]), 0)
            self.assertEqual(messages, [{'command':'resume','stop_after':'verify_home'}, {'command':'arm'},
                                        {'command':'stage','stage':run.STAGE}, {'command':'finish'}])
            self.assertIn('Cinta métrica y manos fuera', output.getvalue())
            self.assertNotIn('checkpoint.json.consumed.json', [p.name for p in after.iterdir()])
            self.assertFalse((evidence/'checkpoint.json').exists())
            with self.assertRaisesRegex(RuntimeError, 'already consumed'):
                run.cli_main(['--after', str(after), '--bundle', str(bundle)])


if __name__ == '__main__': unittest.main()
