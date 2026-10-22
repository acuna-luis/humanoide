"""Current held put1 trial boundaries; local fixtures and fake transports only."""
import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.box_handling import scenario1_contract as contract
from scripts.box_handling import scenario1_resume as resume
from scripts.box_handling import scenario1_runtime as runtime
from scripts.box_handling import scenario1_cli as cli
from scripts.box_handling import scenario1_table74_current_trial as trial
from scripts.box_handling import scenario1_table74_current_trial_run as run
from scripts.box_handling import scenario1_table74_trial_run as approach
from scripts.box_handling.test_resume_pickup_reference import fixture_source
from scripts.box_handling.test_scenario1_table74_trial import sources
from scripts.box_handling.test_scenario1_table74_trial_run import SUCCESS


PROFILE = json.loads(Path(run.__file__).with_name('scenario1_table74_preparation.json').read_text())


def source_checkpoint():
    _, held, _, _ = fixture_source()
    cp = resume.plan_resume(held, PROFILE, stop_after='navigate_put1', policy='assume',
                            execution_profile='optimistic_v1', box_state='held')['checkpoint']
    for stage in ('retreat', 'navigate_put1'):
        cp = contract.complete_stage(contract.begin_stage(cp, stage), stage)
    return cp


def bundle(source=None):
    source = source or source_checkpoint()
    digest = hashlib.sha256(json.dumps(source, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return trial.build_bundle(dict(version=1, mode='operator_assumed_vendor45',
        source_checkpoint_sha256=digest, surface_height_m=.74, reference_surface_height_m=.45,
        scope='current_held_put1_only', evidence='Synthetic operator assumption; no physical calibration'), *sources())


def payload(mode='run'):
    source = source_checkpoint()
    _, plan = run.prepare_entry(source, PROFILE, bundle(source))
    return dict(mode=mode, profile=copy.deepcopy(PROFILE), checkpoint=copy.deepcopy(source),
        policy='assume', execution_profile='optimistic_v1', cycle=False,
        resume_source_checkpoint=source, resume_plan=plan, trial_bundle=bundle(source))


class FakeRuntime(run.CurrentTrialRuntime):
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
    def connected(self): self.gate('connected')
    def discover(self): self.gate('discover')
    def hashes(self): self.gate('hashes')
    def health(self, require_home=False):
        if require_home: raise AssertionError('Held box is not HOME')
        self.gate('health')
    def check_resume_entry(self): self.gate('entry')
    def quick_health(self): self.gate('stationary')
    def verify_trial_files(self): self.gate('trial_hashes')


class CurrentEntryTests(unittest.TestCase):
    def test_inherited_runtime_runs_original_checkpoint_refresh_and_one_trial_without_sps(self):
        with tempfile.TemporaryDirectory() as directory:
            root, events = Path(directory), []
            machine = run.CurrentTrialRuntime(payload(), lambda event, **values: events.append(dict(event=event, **values)))
            original = copy.deepcopy(machine.checkpoint)
            machine.native_container = 'fake-native'
            for message in ({'command':'resume','stop_after':'navigate_put1'}, {'command':'arm'},
                            {'command':'stage','stage':run.STAGE}, {'command':'finish'}):
                machine.commands.put(message)
            def entry(**kwargs): machine.resume_validated = True
            def create():
                machine.session=root/'session'; machine.session.mkdir(exist_ok=True)
            with patch.object(runtime.threading,'Thread'),patch.object(runtime.signal,'signal'), \
                    patch.object(runtime,'open',side_effect=lambda p,m:open(root/'runtime.lock',m),create=True), \
                    patch.object(runtime,'check_sps_discovery'), \
                    patch.object(runtime.Runtime,'action',return_value=copy.deepcopy(SUCCESS)) as action, \
                    patch.object(runtime.subprocess,'Popen',side_effect=AssertionError('No processes')), \
                    patch.multiple(machine,discover=Mock(),hashes=Mock(),health=Mock(),start_live_monitor=Mock(),
                        map_points=Mock(return_value={}),map_state=Mock(return_value=('utars_nav_map','FSM_WAITNAVIGATE')),
                        read_poses=Mock(),check_resume_entry=Mock(side_effect=entry),quick_health=Mock(),
                        verify_trial_files=Mock(),create_session=Mock(side_effect=create),
                        start_adapters=Mock(side_effect=AssertionError('No SPS'))):
                self.assertEqual(machine.run(),0,events)
                action.assert_called_once_with('motion',
                    {'task_name':machine.trial_bundle['task_name'],'yaml_args':'{}'},45)
                machine.check_resume_entry.assert_any_call(refresh_health=True)
                machine.health.assert_any_call(require_home=False)
            self.assertEqual(machine.checkpoint,original)
            self.assertEqual([e['stage'] for e in events if e['event']=='stage_complete'],[run.STAGE])
            self.assertFalse(any(e['event']=='checkpoint' for e in events))
            self.assertFalse((machine.session/'checkpoint.json').exists())
            self.assertEqual(json.loads((machine.session/'trial.json').read_text())['phase'],'succeeded')

    def test_pending_profile_and_original_checkpoint_survive_without_ordinary_resume_plan(self):
        data = payload(); before = copy.deepcopy(data)
        with patch.object(resume, 'plan_resume', side_effect=AssertionError('No ordinary plan')):
            machine = run.CurrentTrialRuntime(data)
        self.assertEqual(data, before)
        self.assertEqual(machine.checkpoint, data['resume_source_checkpoint'])
        self.assertEqual(machine.checkpoint['completed'], ['retreat', 'navigate_put1'])
        self.assertEqual(machine.checkpoint['stop_after'], 'navigate_put1')
        self.assertEqual(machine.payload['profile']['deposit']['compatibility'], 'pending')
        self.assertIs(machine.resume_plan['executable'], False)
        self.assertEqual(machine.resume_plan['requirements'],
            dict(box_state='held', home=False, waypoint='put1', vision_prep=False))

    def test_other_checkpoint_profile_mode_and_bundle_source_are_rejected(self):
        for change in ('failure', 'not_held', 'missing_put1', 'standard', 'source_hash', 'profile'):
            data = payload()
            if change == 'failure': data['resume_source_checkpoint']['failure'] = {'stage': 'navigate_put1', 'reason': 'unknown'}
            elif change == 'not_held': data['resume_source_checkpoint']['box_state'] = 'unknown'
            elif change == 'missing_put1': data['resume_source_checkpoint']['completed'].pop()
            elif change == 'standard': data['resume_source_checkpoint']['execution_profile'] = 'standard_v1'
            elif change == 'source_hash':
                other = copy.deepcopy(data['resume_source_checkpoint']); other['origin']['explicit_state'] = False
                data['trial_bundle'] = bundle(other)
            else: data['profile']['deposit']['compatibility'] = 'verified'
            with self.subTest(change=change), self.assertRaises(ValueError): run.CurrentTrialRuntime(data)

    def test_single_dispatch_has_durable_pending_journal_and_no_checkpoint_promotion(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = FakeRuntime(directory)
            original = copy.deepcopy(machine.checkpoint)
            def dispatch(kind, goal, timeout):
                self.assertEqual((kind, goal, timeout), ('motion',
                    {'task_name': machine.trial_bundle['task_name'], 'yaml_args': '{}'}, 45))
                self.assertEqual(json.loads((machine.session/'trial.json').read_text())['phase'], 'pending')
                return copy.deepcopy(SUCCESS)
            with patch.object(runtime.Runtime, 'action', side_effect=dispatch) as action:
                machine.stage({'command': 'stage', 'stage': run.STAGE})
            action.assert_called_once()
            self.assertEqual(machine.checkpoint, original)
            self.assertEqual(json.loads((machine.session/'trial.json').read_text())['phase'], 'succeeded')
            self.assertFalse((machine.session/'checkpoint.json').exists())
            machine.save()
            self.assertIs(json.loads((machine.session/'context-checkpoint.json').read_text())['executable'], False)
            with self.assertRaisesRegex(RuntimeError, 'ALREADY_ATTEMPTED'):
                machine.stage({'command': 'stage', 'stage': run.STAGE})

    def test_every_failed_preflight_blocks_dispatch_and_stays_failed_without_retry(self):
        for gate in ('discover', 'hashes', 'health', 'entry', 'stationary', 'trial_hashes'):
            with tempfile.TemporaryDirectory() as directory:
                machine = FakeRuntime(directory); machine.fail_at = gate
                with self.subTest(gate=gate), patch.object(runtime.Runtime, 'action') as action:
                    with self.assertRaisesRegex(RuntimeError, gate):
                        machine.stage({'command': 'stage', 'stage': run.STAGE})
                    action.assert_not_called()
                    self.assertEqual(machine.trial_record['phase'], 'failed')
                    with self.assertRaisesRegex(RuntimeError, 'ALREADY_ATTEMPTED'):
                        machine.stage({'command': 'stage', 'stage': run.STAGE})

    def test_other_actions_and_stages_are_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            machine = FakeRuntime(directory)
            with patch.object(runtime.Runtime, 'action') as action:
                for stage in contract.STAGES:
                    with self.subTest(stage=stage), self.assertRaises(RuntimeError):
                        machine.stage({'command': 'stage', 'stage': stage})
                for kind, goal in [('motion', {'task_name': 'cruzr/home', 'yaml_args': '{}'}),
                    ('motion', {'task_name': machine.trial_bundle['task_name'], 'yaml_args': '{}'}),
                    ('navigation', {'command': 'navigation_start', 'arg_json': '{}'})]:
                    with self.assertRaises(RuntimeError): machine.action(kind, goal, 45)
                action.assert_not_called()

    def test_bootstrap_uses_real_sources_and_constructs_without_ordinary_planner(self):
        built = run.make_payload('check', PROFILE, source_checkpoint(), bundle())
        self.assertEqual(dict(built['modules'])['scenario1_runtime'], Path(runtime.__file__).read_text())
        self.assertEqual(dict(built['modules'])['scenario1_table74_trial_run'], Path(approach.__file__).read_text())
        bootstrap = run.BOOTSTRAP.replace(
            "raise SystemExit(sys.modules['scenario1_table74_current_trial_run'].main(payload))",
            "sys.modules['scenario1_resume'].plan_resume=lambda *a,**k: (_ for _ in ()).throw(AssertionError('ordinary plan'))\n"
            "instance=sys.modules['scenario1_table74_current_trial_run'].CurrentTrialRuntime(payload)\n"
            "assert instance.checkpoint['stop_after']=='navigate_put1'\nprint('CURRENT_BOOTSTRAP_LOADED')")
        result = subprocess.run([sys.executable, '-B', '-c', bootstrap], input=json.dumps(built),
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'CURRENT_BOOTSTRAP_LOADED')


class CurrentCliTests(unittest.TestCase):
    def files(self, root):
        source, package = root/'checkpoint.json', root/'bundle.json'
        source.write_text(json.dumps(source_checkpoint()))
        package.write_text(json.dumps(bundle()))
        (root/'context.json').write_text('{}')
        return source, package

    def test_default_plan_is_offline_and_source_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source, package = self.files(root)
            before = {p.name:p.read_bytes() for p in root.iterdir()}
            with patch.object(run, 'connection_class', side_effect=AssertionError('No connection')), \
                    patch.object(cli, 'claim_resume', side_effect=AssertionError('No claim')), \
                    patch('sys.stdout', io.StringIO()) as output:
                self.assertEqual(run.cli_main(['--resume', str(source), '--bundle', str(package)]), 0)
            report = json.loads(output.getvalue())
            self.assertEqual(report['commands_sent'], 0)
            self.assertFalse(report['ordinary_deposit_authorized'])
            self.assertFalse(report['context']['executable'])
            self.assertEqual(before, {p.name:p.read_bytes() for p in root.iterdir()})

    def test_check_never_claims_or_sends_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source, package=self.files(root)
            connection=Mock(); connection.wait.return_value={'context':{}}; connection.process.wait.return_value=0
            with patch.object(run, 'connection_class', return_value=Mock(return_value=connection)), \
                    patch.object(cli, 'claim_resume', side_effect=AssertionError('No claim')), \
                    patch.object(run, 'open', side_effect=lambda p,m:open(root/Path(p).name,m), create=True), \
                    patch('builtins.input', side_effect=AssertionError('No prompt')), patch('sys.stdout', io.StringIO()):
                self.assertEqual(run.cli_main(['--check','--resume',str(source),'--bundle',str(package),
                                              '--evidence-dir',str(root/'check')]),0)
            connection.send.assert_not_called()
            self.assertFalse(source.with_name(source.name+'.consumed.json').exists())
            self.assertFalse((root/'check/checkpoint.json').exists())

    def test_run_consumes_before_arm_and_only_refreshes_then_sends_one_trial(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source, package=self.files(root); evidence=root/'run'
            before=source.read_bytes(); messages=[]; data=payload(); owner=self
            class Connection:
                process=Mock(); process.wait.return_value=0
                def send(self, value):
                    if value['command'] in ('arm','stage'):
                        owner.assertTrue(source.with_name(source.name+'.consumed.json').is_file())
                    messages.append(value)
                    if value['command']=='stage':
                        cli.atomic_json(evidence/'trial.json', dict(artifact='table74_approach_trial', version=1,
                            bundle_id=data['trial_bundle']['manifest']['id'], source_sha256=data['resume_plan']['source_sha256'],
                            phase='succeeded',intent_ns=1,finished_ns=2,result=SUCCESS,error=None,
                            physical_support_confirmed=False,automatic_retry=False))
                def wait(self, event, timeout=None): return dict(context={},checkpoint=data['checkpoint'],stage=run.STAGE)
                def close(self): pass
            with patch.object(run,'connection_class',return_value=Mock(return_value=Connection())), \
                    patch.object(run,'open',side_effect=lambda p,m:open(root/Path(p).name,m),create=True), \
                    patch.object(run.subprocess,'run') as command,patch('sys.stdin.isatty',return_value=True), \
                    patch('builtins.input',return_value='APROXIMAR74') as token,patch('sys.stdout',io.StringIO()):
                self.assertEqual(run.cli_main(['--run','--resume',str(source),'--bundle',str(package),
                                              '--evidence-dir',str(evidence)]),0)
            self.assertEqual(messages,[{'command':'resume','stop_after':'navigate_put1'}, {'command':'arm'},
                {'command':'stage','stage':run.STAGE},{'command':'finish'}])
            token.assert_called_once(); command.assert_called_once()
            self.assertEqual(source.read_bytes(),before)
            self.assertFalse((evidence/'checkpoint.json').exists())
            with self.assertRaisesRegex(RuntimeError,'already consumed'):
                run.cli_main(['--resume',str(source),'--bundle',str(package)])


if __name__=='__main__': unittest.main()
