"""Single approach authorization and journals, using local synthetic IO only."""
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.box_handling import scenario1_table74_trial_run as run
from scripts.box_handling import scenario1_cli as cli
from scripts.box_handling import scenario1_contract as contract
from scripts.box_handling import scenario1_runtime as runtime
from scripts.box_handling.test_scenario1_table74_trial import build, reference

PROFILE = json.loads(Path(__file__).with_name('scenario1_current_geometry.json').read_text())
SUCCESS = dict(event='result', goal_id='11111111-1111-4111-8111-111111111111', status=4,
               result={'state': {'desc': 'SUCCEED', 'state': 1101001}})


def source_checkpoint():
    cp = contract.new_checkpoint(PROFILE, stop_after='navigate_put1', policy='assume',
                                 execution_profile='optimistic_v1')
    for stage in contract.STAGES[:6]:
        options = dict(confirmed_box='held', verification_source='assumed') if stage == 'verify_held' else {}
        cp = contract.complete_stage(contract.begin_stage(cp, stage), stage, **options)
    return cp


def payload():
    source, options, plan = run.prepare_entry(source_checkpoint(), PROFILE)
    return dict(mode='run', profile=PROFILE, checkpoint=plan['checkpoint'], policy='assume',
                execution_profile='optimistic_v1', cycle=False, resume_source_checkpoint=source,
                resume_options=options, resume_plan=plan, trial_bundle=build())


class FakeRuntime(run.TrialRuntime):
    def __init__(self, directory):
        self.events, self.gates = [], []
        super().__init__(payload(), lambda event, **values: self.events.append(dict(event=event, **values)))
        self.session = Path(directory)
        self.armed = self.resume_validated = True
        self.fail_at = None

    def gate(self, name):
        self.gates.append(name)
        if self.fail_at == name:
            raise RuntimeError(name+' failed')

    def connected(self):
        if self.stop.is_set():
            raise RuntimeError('STOP remains latched')
        self.gate('connected')

    def discover(self): self.gate('discover')
    def hashes(self): self.gate('hashes')
    def health(self, require_home=False):
        if require_home:
            raise AssertionError('Held box is not HOME')
        self.gate('health')
    def check_resume_entry(self): self.gate('entry')
    def quick_health(self): self.gate('stationary')
    def verify_trial_files(self): self.gate('trial_hashes')


class TrialRuntimeTest(unittest.TestCase):
    def test_inherited_run_finishes_trial_without_sps_or_normal_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root, events = Path(directory), []
            machine = run.TrialRuntime(payload(), lambda event, **values: events.append(dict(event=event, **values)))
            machine.native_container = 'fake-native'
            for message in ({'command': 'resume', 'stop_after': 'verify_home'}, {'command': 'arm'},
                            {'command': 'stage', 'stage': run.STAGE}, {'command': 'finish'}):
                machine.commands.put(message)

            def entry(**unused): machine.resume_validated = True
            def create():
                machine.session = root/'session'
                machine.session.mkdir(exist_ok=True)

            with patch.object(runtime.threading, 'Thread'), patch.object(runtime.signal, 'signal'), \
                    patch.object(runtime, 'open', side_effect=lambda name, mode: open(root/'runtime.lock', mode), create=True), \
                    patch.object(runtime, 'check_sps_discovery'), \
                    patch.object(runtime.Runtime, 'action', return_value=copy.deepcopy(SUCCESS)) as action, \
                    patch.object(runtime.subprocess, 'Popen', side_effect=AssertionError('No processes')), \
                    patch.multiple(machine, discover=Mock(), hashes=Mock(), health=Mock(),
                        start_live_monitor=Mock(), map_points=Mock(return_value={}),
                        map_state=Mock(return_value=('utars_nav_map', 'FSM_WAITNAVIGATE')),
                        read_poses=Mock(), check_resume_entry=Mock(side_effect=entry),
                        quick_health=Mock(), verify_trial_files=Mock(), create_session=Mock(side_effect=create),
                        start_adapters=Mock(side_effect=AssertionError('No SPS'))):
                self.assertEqual(machine.run(), 0, events)
                action.assert_called_once_with('motion',
                    {'task_name': machine.trial_bundle['task_name'], 'yaml_args': '{}'}, 45)
            self.assertFalse((machine.session/'checkpoint.json').exists())
            self.assertTrue((machine.session/'context-checkpoint.json').is_file())
            self.assertEqual(json.loads((machine.session/'trial.json').read_text())['phase'], 'succeeded')
            self.assertEqual(json.loads((machine.session/'control-lease.json').read_text())['deadline'], 0)
            self.assertEqual([e['stage'] for e in events if e['event'] == 'stage_complete'], [run.STAGE])
            self.assertFalse(any(e['event'] == 'checkpoint' for e in events))

    def test_one_dispatch_follows_pending_journal_and_preserves_scenario_context(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = FakeRuntime(directory)
            original = copy.deepcopy(machine.checkpoint)
            machine.save()

            def dispatch(kind, goal, timeout):
                self.assertEqual(kind, 'motion')
                self.assertEqual(goal, {'task_name': machine.trial_bundle['task_name'], 'yaml_args': '{}'})
                self.assertEqual(timeout, 45)
                self.assertEqual(json.loads((machine.session/'trial.json').read_text())['phase'], 'pending')
                self.assertEqual(machine.gates, ['connected', 'discover', 'hashes', 'health', 'entry',
                                                'stationary', 'trial_hashes', 'connected'])
                return copy.deepcopy(SUCCESS)

            with patch.object(runtime.Runtime, 'action', side_effect=dispatch) as action:
                machine.stage({'command': 'stage', 'stage': run.STAGE})
                action.assert_called_once()
                with self.assertRaisesRegex(RuntimeError, 'ALREADY_ATTEMPTED'):
                    machine.stage({'command': 'stage', 'stage': run.STAGE})
                action.assert_called_once()
            self.assertEqual(machine.checkpoint, original)
            self.assertFalse((machine.session/'checkpoint.json').exists())
            context = json.loads((machine.session/'context-checkpoint.json').read_text())
            with self.assertRaises(ValueError): contract.validate_checkpoint(context)
            self.assertEqual(machine.trial_record['phase'], 'succeeded')
            self.assertFalse(machine.trial_record['physical_support_confirmed'])
            self.assertFalse(any(e['event'] == 'checkpoint' for e in machine.events))

    def test_safety_gate_faults_or_stop_never_dispatch_and_cannot_be_retried(self):
        for gate in ('connected', 'discover', 'hashes', 'health', 'entry', 'stationary', 'trial_hashes', 'stop'):
            with self.subTest(gate=gate), tempfile.TemporaryDirectory() as directory:
                machine = FakeRuntime(directory)
                if gate == 'stop': machine.stop.set()
                else: machine.fail_at = gate
                with patch.object(runtime.Runtime, 'action') as action:
                    with self.assertRaises(RuntimeError): machine.stage({'command': 'stage', 'stage': run.STAGE})
                    self.assertEqual(machine.trial_record['phase'], 'failed')
                    with self.assertRaisesRegex(RuntimeError, 'ALREADY_ATTEMPTED'):
                        machine.stage({'command': 'stage', 'stage': run.STAGE})
                    action.assert_not_called()

    def test_action_failures_timeout_and_posture_failure_remain_terminal(self):
        failed = copy.deepcopy(SUCCESS)
        failed.update(status=6, result={'state': {'desc': 'MoveToGoalFailed', 'state': 7104050}})
        for outcome in (failed, TimeoutError('Unknown result')):
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as directory:
                machine = FakeRuntime(directory)
                with patch.object(runtime.Runtime, 'action', side_effect=outcome if isinstance(outcome, Exception) else None,
                                  return_value=outcome) as action:
                    with self.assertRaises((ValueError, TimeoutError)):
                        machine.stage({'command': 'stage', 'stage': run.STAGE})
                    self.assertEqual(machine.trial_record['phase'], 'failed')
                    self.assertFalse(any(e['event'] == 'stage_complete' for e in machine.events))
                    self.assertEqual(action.call_count, 1)
        with tempfile.TemporaryDirectory() as directory:
            machine = FakeRuntime(directory)
            with patch.object(runtime.Runtime, 'action', return_value=SUCCESS), \
                    patch.object(machine, 'quick_health', side_effect=[None, RuntimeError('moving')]):
                with self.assertRaisesRegex(RuntimeError, 'moving'):
                    machine.stage({'command': 'stage', 'stage': run.STAGE})
            self.assertEqual(machine.trial_record['phase'], 'failed')

    def test_stages_and_actions_outside_trial_are_rejected_without_dispatch(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = FakeRuntime(directory)
            with patch.object(runtime.Runtime, 'action') as action:
                for stage in (*contract.STAGES, 'retry', ''):
                    with self.subTest(stage=stage), self.assertRaises(RuntimeError):
                        machine.stage({'command': 'stage', 'stage': stage})
                with self.assertRaises(RuntimeError):
                    machine.stage({'command': 'stage', 'stage': run.STAGE, 'extra': True})
                for kind, goal in [('motion', {'task_name': 'cruzr/home', 'yaml_args': '{}'}),
                                   ('motion', {'task_name': machine.trial_bundle['task_name'], 'yaml_args': '{}'}),
                                   ('navigation', {'command': 'navigation_start', 'arg_json': '{}'})]:
                    with self.assertRaises(RuntimeError): machine.action(kind, goal, 45)
                action.assert_not_called()
            self.assertIsNone(machine.trial_record)

    def test_existing_pending_ledger_blocks_a_fresh_instance(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = FakeRuntime(directory)
            (machine.session/'trial.json').write_text('{"phase":"pending"}')
            with self.assertRaisesRegex(RuntimeError, 'ALREADY_ATTEMPTED'):
                machine.stage({'command': 'stage', 'stage': run.STAGE})

    def test_bundle_readback_requires_all_files_and_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = FakeRuntime(directory)
            expected = machine.trial_bundle['manifest']['robot_files']
            for actual in (expected, {}, dict(expected, **{next(iter(expected)): '0'*64})):
                with patch.object(machine, 'native', return_value=json.dumps(actual)):
                    if actual == expected:
                        run.TrialRuntime.verify_trial_files(machine)
                    else:
                        with self.assertRaisesRegex(RuntimeError, 'TRIAL_FILES_CHANGED'):
                            run.TrialRuntime.verify_trial_files(machine)


class TrialEntryTest(unittest.TestCase):
    def test_only_clean_held_put1_and_exact_measurement_are_admitted(self):
        original = source_checkpoint()
        for changes in ({'box_state': 'unknown'}, {'in_flight': 'deposit'},
                        {'completed': original['completed'][:-1]}, {'execution_profile': 'standard_v1'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                run.prepare_entry(dict(original, **changes), PROFILE)
        ref = reference(); ref['box_bottom_above_floor_m'] = 1.20
        with self.assertRaisesRegex(ValueError, '1.10'):
            run.validate_bundle(build(ref))

    def test_payload_bootstrap_loads_only_new_entry_without_patching_baseline(self):
        built = run.make_payload('check', PROFILE, source_checkpoint(), build())
        sources = dict(built['modules'])
        self.assertEqual(sources['scenario1_runtime'], Path(runtime.__file__).read_text())
        self.assertEqual(built['modules'][-1][0], 'scenario1_table74_trial_run')
        self.assertIn("sys.modules['scenario1_table74_trial_run'].main(payload)", run.BOOTSTRAP)
        self.assertEqual(runtime.TASKS['deposit'], ('wrc_cruzr/put_cruzr_wrc_low', 120))
        self.assertEqual(built['resume_plan']['requirements']['waypoint'], 'put1')
        # Load exactly the production module sequence in an isolated local
        # interpreter; instantiate only, without run(), ROS imports or IO.
        bootstrap = run.BOOTSTRAP.replace(
            "raise SystemExit(sys.modules['scenario1_table74_trial_run'].main(payload))",
            "instance=sys.modules['scenario1_table74_trial_run'].TrialRuntime(payload)\n"
            "assert isinstance(instance,sys.modules['scenario1_runtime'].Runtime)\n"
            "print('TRIAL_BOOTSTRAP_LOADED')")
        result = subprocess.run([sys.executable, '-B', '-c', bootstrap], input=json.dumps(built),
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'TRIAL_BOOTSTRAP_LOADED')


class TrialCliTest(unittest.TestCase):
    def files(self, root):
        source, bundle = root/'checkpoint.json', root/'bundle.json'
        source.write_text(json.dumps(source_checkpoint()))
        bundle.write_text(json.dumps(build()))
        (root/'context.json').write_text('{}')
        return source, bundle

    def test_default_plan_is_offline_does_not_consume_or_create_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source, bundle = self.files(root)
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            with patch.object(run, 'connection_class', side_effect=AssertionError('No network')), \
                    patch.object(cli, 'claim_resume', side_effect=AssertionError('No claim')), \
                    patch('sys.stdout', io.StringIO()) as output:
                self.assertEqual(run.cli_main(['--resume', str(source), '--bundle', str(bundle)]), 0)
            report = json.loads(output.getvalue())
            self.assertEqual(report['stage'], run.STAGE)
            self.assertEqual(report['commands_sent'], 0)
            self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir()})

    def test_check_never_claims_arms_or_dispatches(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source, bundle = self.files(root)
            connection = Mock()
            connection.wait.return_value = {'context': {}}
            connection.process.wait.return_value = 0
            with patch.object(run, 'connection_class', return_value=Mock(return_value=connection)), \
                    patch.object(cli, 'claim_resume', side_effect=AssertionError('No claim')), \
                    patch.object(run, 'open', side_effect=lambda name, mode: open(root/Path(name).name, mode), create=True), \
                    patch('builtins.input', side_effect=AssertionError('No prompt')), patch('sys.stdout', io.StringIO()):
                self.assertEqual(run.cli_main(['--check', '--resume', str(source), '--bundle', str(bundle),
                                              '--evidence-dir', str(root/'check')]), 0)
            connection.send.assert_not_called()
            self.assertFalse((root/'check/checkpoint.json').exists())
            self.assertFalse(source.with_name(source.name+'.consumed.json').exists())

    def test_run_requires_token_and_consumes_before_arm_then_sends_only_trial(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source, bundle = self.files(root)
            evidence, messages = root/'run', []
            source_before = source.read_bytes()
            data = payload()

            class Connection:
                process = Mock()
                process.wait.return_value = 0
                def send(self, value):
                    if value['command'] in ('arm', 'stage'):
                        self_test.assertTrue(source.with_name(source.name+'.consumed.json').is_file())
                    messages.append(value)
                    if value['command'] == 'stage':
                        journal = dict(artifact='table74_approach_trial', version=1,
                            bundle_id=data['trial_bundle']['manifest']['id'],
                            source_sha256=data['resume_plan']['source_sha256'], phase='succeeded',
                            intent_ns=1, finished_ns=2, result=SUCCESS, error=None,
                            physical_support_confirmed=False, automatic_retry=False)
                        cli.atomic_json(evidence/'trial.json', journal)
                def wait(self, desired, timeout=None):
                    return dict(context={}, checkpoint=data['checkpoint'], stage=run.STAGE)
                def close(self): pass

            self_test = self
            with patch.object(run, 'connection_class', return_value=Mock(return_value=Connection())), \
                    patch.object(run, 'open', side_effect=lambda name, mode: open(root/Path(name).name, mode), create=True), \
                    patch.object(run.subprocess, 'run') as commands, patch('sys.stdin.isatty', return_value=True), \
                    patch('builtins.input', return_value='APROXIMAR') as token, patch('sys.stdout', io.StringIO()):
                self.assertEqual(run.cli_main(['--run', '--resume', str(source), '--bundle', str(bundle),
                                              '--evidence-dir', str(evidence)]), 0)
            self.assertEqual(messages, [{'command': 'resume', 'stop_after': 'verify_home'}, {'command': 'arm'},
                                        {'command': 'stage', 'stage': run.STAGE}, {'command': 'finish'}])
            token.assert_called_once()
            commands.assert_called_once()
            self.assertEqual(source.read_bytes(), source_before)
            self.assertFalse((evidence/'checkpoint.json').exists())
            with self.assertRaisesRegex(RuntimeError, 'already consumed'):
                run.cli_main(['--resume', str(source), '--bundle', str(bundle)])


if __name__ == '__main__':
    unittest.main()
