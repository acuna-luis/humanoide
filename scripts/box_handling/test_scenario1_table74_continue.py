"""Continue only after an authenticated post-success diagnostic interruption.

Synthetic original files stay failed and byte-identical. All control phases
and transports in orchestration tests are mocked; no robot is contacted.
"""
from contextlib import ExitStack
import copy
import hashlib
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
from scripts.box_handling import scenario1_table74_continue as continuation
from scripts.box_handling import scenario1_table74_cycle as cycle
from scripts.box_handling import scenario1_table74_current_lower_run as lower_run
from scripts.box_handling import scenario1_table74_log_recovery as recovery
from scripts.box_handling.test_scenario1_table74_current_lower_run import PROFILE, predecessor
from scripts.box_handling.test_scenario1_table74_current_lower_run import lowering_bundle
from scripts.box_handling.test_scenario1_table74_trial_run import SUCCESS
from scripts.box_handling.test_scenario1_table74_recipe import RecipeHarness


def source_fixture():
    proof = predecessor()
    failed = dict(proof['trial.json'], phase='failed', error=recovery.ALLOWED_ERROR)
    events = proof['events.jsonl'][:7]
    events.append(dict(event='trial', time_ns=70, trial=copy.deepcopy(failed)))
    events.append(dict(event='error', time_ns=80, reason=recovery.ALLOWED_ERROR, physical_state='unconfirmed'))
    for kind in ('navigation', 'motion', 'health_worker'):
        health = kind == 'health_worker'
        error = dict(event='error', request_id=None,
            reason='RuntimeError: Health worker lease expired or stop requested' if health else 'Lease missing, invalid or expired')
        if not health:
            error['goal_id'] = None
        outer = dict(event='health_worker') if health else dict(event='action', kind=kind)
        events.append(dict(outer, time_ns=90+len(events), detail=error))
        events.append(dict(outer, time_ns=90+len(events), detail=dict(event='worker_closed',
            returncode=78 if health else 2, physical_stop_verified=False)))
    proof['trial.json'], proof['events.jsonl'] = failed, events
    return proof


def write_source(directory):
    directory.mkdir()
    proof = source_fixture()
    for name in lower_run.FILES:
        value = proof[name]
        text = ''.join(json.dumps(row)+'\n' for row in value) if name == 'events.jsonl' else json.dumps(value, indent=2)+'\n'
        (directory/name).write_text(text)
    return proof


def argv(after, *flags):
    return ['--continue-deposit', '--table-height-cm', '74', '--after', str(after), *flags]


class ContinuationEntryTests(unittest.TestCase):
    def test_default_plan_does_not_read_source_create_files_or_contact_controller(self):
        with patch.object(Path, 'read_text', side_effect=AssertionError('No source read for plan')), \
                patch.object(Path, 'read_bytes', side_effect=AssertionError('No source read for plan')), \
                patch.object(Path, 'mkdir', side_effect=AssertionError('No plan artifact')), \
                patch.object(continuation, 'prepare_recovery', side_effect=AssertionError('No recovery copy for plan')), \
                patch.object(cycle, 'run', side_effect=AssertionError('No controller')), patch('sys.stdout', io.StringIO()) as output:
            self.assertEqual(continuation.main(argv('/missing/source')), 0)
        self.assertIsInstance(json.loads(output.getvalue()), dict)

    def test_run_and_check_require_explicit_recovery_flag_before_io(self):
        for mode in ('--run', '--check'):
            with self.subTest(mode=mode),patch.object(continuation, 'prepare_recovery', side_effect=AssertionError('No copy')), \
                    patch.object(Path, 'mkdir', side_effect=AssertionError('No artifact without authorization')), \
                    patch.object(cycle, 'run', side_effect=AssertionError('No controller')), patch('sys.stderr', io.StringIO()):
                try:
                    code = continuation.main(argv('/missing/source', mode))
                except (SystemExit, ValueError):
                    pass
                else:
                    self.assertNotEqual(code, 0)

    def test_prepare_preserves_original_failed_bytes_and_records_typed_assumed_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'original'
            original = write_source(source)
            before = {name:(source/name).read_bytes() for name in lower_run.FILES}
            evidence = root/'entry'; evidence.mkdir()
            copied = continuation.prepare_recovery(source, evidence)
            self.assertEqual(copied, evidence/'recovery-source')
            self.assertEqual({name:(copied/name).read_bytes() for name in lower_run.FILES}, before)
            self.assertEqual({name:(source/name).read_bytes() for name in lower_run.FILES}, before)
            record = json.loads((copied/recovery.AUTHORIZATION_FILE).read_text())
            self.assertEqual(record, dict(version=1, kind='table74_log_only_recovery', next_stage='precontact',
                source_directory=str(source.resolve()), source_sha256={name:hashlib.sha256(raw).hexdigest() for name,raw in before.items()},
                proof_sha256=recovery.digest(original), operator_state_assumed_unchanged=True,
                current_physical_measurement=False))
            self.assertEqual(json.loads((copied/'trial.json').read_text())['phase'], 'failed')
            self.assertFalse((source/'trial.json.consumed.json').exists())
            self.assertFalse((copied/'trial.json.consumed.json').exists())

    def test_bad_source_blocks_before_cycle_and_never_coerces_failed_journal_to_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root/'original';write_source(source)
            failed = json.loads((source/'trial.json').read_text());failed['error'] = 'DectionForceCollision'
            (source/'trial.json').write_text(json.dumps(failed))
            with patch.object(cycle, 'run', side_effect=AssertionError('No controller for physical fault')) as run, \
                    patch('sys.stderr', io.StringIO()):
                try:
                    code = continuation.main(argv(source, '--run', '--recovery-confirmed', '--evidence-dir', str(root/'entry')))
                except (ValueError, RuntimeError):
                    pass
                else:
                    self.assertNotEqual(code, 0)
            run.assert_not_called()
            self.assertEqual(json.loads((source/'trial.json').read_text())['phase'], 'failed')
            self.assertFalse((source/'trial.json.consumed.json').exists())

    def test_entry_passes_recovery_copy_without_ordinary_resume_or_stage_jump(self):
        for mode in ('--run', '--check'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);source=root/'original';write_source(source)
                with patch.object(cycle, 'run', return_value=37) as run:
                    result=continuation.main(argv(source, mode, '--recovery-confirmed', '--evidence-dir', str(root/'entry')))
                self.assertEqual(result, 37)
                selected, stop=run.call_args.args
                self.assertEqual(selected.table74_after, root/'entry/recovery-source')
                self.assertEqual(selected.evidence_dir, root/'entry/continuation')
                self.assertEqual(selected.table_height_cm, 74.)
                self.assertEqual(selected.stop_after, 'cycle')
                self.assertIsNone(selected.resume)
                self.assertIsNone(selected.from_stage)
                self.assertFalse(stop.requested)
                self.assertEqual(bool(selected.run), mode=='--run')
                self.assertEqual(bool(selected.check), mode=='--check')

    def test_optimistic_wrapper_continue_help_is_offline(self):
        process=subprocess.run(['bash',str(cli.ROOT/'scripts/optimistic_scenario1.sh'),
            '--continue-deposit','--help'],text=True,capture_output=True,timeout=10)
        self.assertEqual(process.returncode,0,process.stderr)
        self.assertIn('--continue-deposit',process.stdout)
        self.assertIn('--recovery-confirmed',process.stdout)


class ContinuationCycleTests(unittest.TestCase):
    def setup_recovery(self, root):
        source=root/'original';write_source(source)
        entry=root/'entry';entry.mkdir()
        return continuation.prepare_recovery(source,entry)

    def test_continuation_starts_at_precontact_never_repeats_pickup_or_approach(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);after=self.setup_recovery(root)
            with RecipeHarness(root) as h:
                selected=cli.parser('assume','optimistic_v1').parse_args(['--table-height-cm','74','--run',
                    '--evidence-dir',str(root/'cycle')]);selected.table74_after=after
                self.assertEqual(cycle.run(selected,h.stop),0)
                h.pickup.assert_not_called()
                self.assertEqual([call.args[0] for call in h.phase.call_args_list],['precontact','support'])
                self.assertEqual(h.phase.call_args_list[0].args[1],after)
                self.assertEqual(h.release.call_count,2)
                h.home.assert_called_once()

    def test_precontact_failure_stops_before_support_open_or_home(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);after=self.setup_recovery(root)
            with RecipeHarness(root) as h:
                selected=cli.parser('assume','optimistic_v1').parse_args(['--table-height-cm','74','--run',
                    '--evidence-dir',str(root/'cycle')]);selected.table74_after=after
                h.phase.side_effect=RuntimeError('fresh rest or health failed')
                self.assertEqual(cycle.run(selected,h.stop),78)
                h.pickup.assert_not_called();h.phase.assert_called_once()
                self.assertEqual(h.phase.call_args.args[0],'precontact')
                h.release.assert_not_called();h.home.assert_not_called()

    def test_continuation_check_only_checks_precontact_without_claims_or_movements(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);after=self.setup_recovery(root)
            selected=cli.parser('assume','optimistic_v1').parse_args(['--table-height-cm','74','--check',
                '--evidence-dir',str(root/'check')]);selected.table74_after=after
            with patch.object(cycle.installer,'_lock',return_value=Mock()), \
                    patch.object(cycle,'execute_phase',return_value=55) as phase, \
                    patch.object(cycle,'pickup',side_effect=AssertionError('No pickup')), \
                    patch.object(cycle,'release_phase',side_effect=AssertionError('No opening')), \
                    patch.object(cycle.home,'run',side_effect=AssertionError('No HOME')):
                self.assertEqual(cycle.run(selected,SimpleNamespace(requested=False)),55)
            phase.assert_called_once()
            self.assertEqual(phase.call_args.args[:2],('precontact',after))
            self.assertTrue(phase.call_args.kwargs['check_only'])
            self.assertFalse((after/'trial.json.consumed.json').exists())
            self.assertFalse((root/'original/trial.json.consumed.json').exists())


class RecoveryAdmissionBoundaryTests(unittest.TestCase):
    def copied(self, root):
        source=root/'original';write_source(source)
        evidence=root/'entry';evidence.mkdir()
        after=continuation.prepare_recovery(source,evidence)
        proof,info,_=lower_run.load_predecessor(after,PROFILE)
        return source,after,proof,info

    def test_claim_consumes_original_once_without_modifying_failed_history_or_normal_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source,after,proof,_=self.copied(root)
            before={name:(source/name).read_bytes() for name in lower_run.FILES}
            destination=root/'new-trial.json'
            lower_run.claim_recovery_source(proof,destination)
            marker=source/'trial.json.consumed.json'
            self.assertEqual(json.loads(marker.read_text())['continued_in'],str(destination))
            self.assertEqual({name:(source/name).read_bytes() for name in lower_run.FILES},before)
            self.assertEqual(json.loads((source/'trial.json').read_text())['phase'],'failed')
            with self.assertRaisesRegex(RuntimeError,'consumed'):
                lower_run.claim_recovery_source(proof,root/'second-trial.json')
            with self.assertRaisesRegex(RuntimeError,'consumed'):
                lower_run.load_predecessor(after,PROFILE)
            fresh=root/'second-entry';fresh.mkdir()
            with self.assertRaisesRegex(ValueError,'consumed'):
                continuation.prepare_recovery(source,fresh)
            with patch.object(cli,'claim_resume',side_effect=AssertionError('Normal proof is not a recovery source')):
                lower_run.claim_recovery_source(predecessor(),root/'normal-trial.json')

    def test_copy_loader_rejects_changed_or_consumed_original_before_any_claim(self):
        for mutation in ('changed','consumed'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);source,after,proof,_=self.copied(root)
                if mutation=='changed':
                    original=source/'events.jsonl';original.write_bytes(original.read_bytes()+b'\n')
                else:
                    cli.claim_resume(source/'trial.json',root/'other-trial.json')
                with patch.object(cli,'claim_resume',side_effect=AssertionError('Invalid source must not be consumed')):
                    with self.assertRaises(RuntimeError):lower_run.load_predecessor(after,PROFILE)
                    with self.assertRaises(RuntimeError):lower_run.claim_recovery_source(proof,root/'trial.json')
                self.assertFalse((after/'trial.json.consumed.json').exists())

    def test_real_precontact_payload_loads_recovery_namespace_in_isolated_python_without_sdk(self):
        script='''import json,sys,types
payload=json.loads(sys.stdin.read())
for name,source in payload.pop('modules'):
 module=types.ModuleType(name);sys.modules[name]=module
 exec(compile(source,name+'.py','exec'),module.__dict__)
machine=sys.modules['scenario1_table74_current_lower_run'].LowerRuntime(payload,lambda *a,**k:None)
print(json.dumps(dict(original_phase=machine.payload['predecessor']['trial.json']['phase'],
 next_phase=machine.trial_bundle['review']['reference']['stage'],
 requirements=machine.resume_plan['requirements'],
 recovery_kind=machine.predecessor['recovery_authorization']['kind'],
 executable=machine.resume_plan['executable'])))
'''
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);_,_,proof,_=self.copied(root)
            bundle=lowering_bundle(proof,'precontact')
            payload=lower_run.make_payload('check',PROFILE,proof,bundle)
            process=subprocess.run([sys.executable,'-I','-B','-c',script],input=json.dumps(payload),
                text=True,capture_output=True,timeout=15)
            self.assertEqual(process.returncode,0,process.stderr)
            report=json.loads(process.stdout)
            self.assertEqual(report['original_phase'],'failed')
            self.assertEqual(report['next_phase'],'precontact')
            self.assertEqual(report['requirements']['box_state'],'held')
            self.assertIs(report['requirements']['home'],False)
            self.assertEqual(report['recovery_kind'],'table74_log_only_recovery')
            self.assertIs(report['executable'],False)

    def test_original_claim_follows_ready_and_resume_but_precedes_copy_claim_arm_and_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source,after,proof,info=self.copied(root)
            bundle=lowering_bundle(proof,'precontact');package=root/'bundle.json';package.write_text(json.dumps(bundle))
            evidence=root/'run';order=[];owner=self
            original_claim=cli.claim_resume
            def claim(path,destination):
                order.append('claim-original' if path.parent==source else 'claim-copy')
                original_claim(path,destination)
            class Connection:
                process=Mock();process.wait.return_value=0
                def send(self,message):
                    command=message['command'];order.append('send-'+command)
                    if command in ('arm','stage'):
                        owner.assertTrue((source/'trial.json.consumed.json').exists())
                        owner.assertTrue((after/'trial.json.consumed.json').exists())
                    if command=='stage':
                        cli.atomic_json(evidence/'trial.json',dict(artifact='table74_approach_trial',version=1,
                            bundle_id=bundle['manifest']['id'],source_sha256=info['predecessor_sha256'],
                            phase='succeeded',intent_ns=1,finished_ns=2,result=SUCCESS,error=None,
                            physical_support_confirmed=False,automatic_retry=False))
                def wait(self,event,timeout=None):
                    order.append('wait-'+event)
                    return dict(context=info['context'],checkpoint=info['source'],stage=lower_run.STAGE)
                def close(self):order.append('close')
            with patch.object(lower_run,'connection_class',return_value=Mock(return_value=Connection())), \
                    patch.object(lower_run,'open',side_effect=lambda path,mode:open(root/Path(path).name,mode),create=True), \
                    patch.object(cli,'claim_resume',side_effect=claim), \
                    patch.object(lower_run.subprocess,'run',return_value=Mock(returncode=0)), \
                    patch('sys.stdin.isatty',return_value=True),patch('builtins.input',return_value='BAJAR74'), \
                    patch('sys.stdout',io.StringIO()):
                self.assertEqual(lower_run.cli_main(['--run','--after',str(after),'--bundle',str(package),
                    '--evidence-dir',str(evidence)]),0)
            self.assertLess(order.index('wait-ready'),order.index('claim-original'))
            self.assertLess(order.index('wait-resume_ready'),order.index('claim-original'))
            self.assertLess(order.index('claim-original'),order.index('claim-copy'))
            self.assertLess(order.index('claim-copy'),order.index('send-arm'))
            self.assertLess(order.index('send-arm'),order.index('send-stage'))
            self.assertEqual(order.count('claim-original'),1)
            self.assertEqual(order.count('send-stage'),1)
            self.assertEqual(json.loads((source/'trial.json').read_text())['phase'],'failed')


if __name__ == '__main__':
    unittest.main()
