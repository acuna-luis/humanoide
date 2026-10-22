"""Final-deposit supervisor: real proofs/builders, fake installer and transport."""
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch

from scripts.box_handling import scenario1_table74_finish as finish
from scripts.box_handling.test_scenario1_table74_current_release_run import support_proof,relief_proof


def write_proof(directory,proof):
    directory.mkdir()
    for name,value in proof.items():
        (directory/name).write_text(''.join(json.dumps(e)+'\n'for e in value)if name=='events.jsonl'else json.dumps(value))


def args(after,*,phase='pin-relief',mode=None,complete=True,evidence=None):
    values=['--finish-deposit','--table-height-cm','74','--phase',phase,'--after',str(after)]
    if mode:values.append('--'+mode)
    if complete:
        values+=['--supported','--tool-clearance-cm','4','--pin-exit-cm','3','--path-clear']
        if phase=='open':values.append('--pins-free')
    if evidence:values+=['--evidence-dir',str(evidence)]
    return values


def capture_plan(arguments):
    with patch('sys.stdout',io.StringIO())as output:
        code=finish.main(arguments)
    return code,json.loads(output.getvalue())


class FinishPlanTests(unittest.TestCase):
    def test_missing_current_declarations_remain_false_and_offline_without_artifacts(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);after=root/'after';write_proof(after,support_proof())
            before={p.name:p.read_bytes()for p in after.iterdir()}
            with patch.object(finish,'installer_call',side_effect=AssertionError('No installer')), \
                    patch.object(finish.runner,'cli_main',side_effect=AssertionError('No runtime')), \
                    patch.object(finish.cli,'atomic_json',side_effect=AssertionError('No writes')):
                code,report=capture_plan(args(after,complete=False))
            self.assertEqual(code,0);self.assertFalse(report['operator_reference_complete'])
            self.assertFalse(report['declarations']['supported']);self.assertFalse(report['reference_created'])
            self.assertIsNone(report['task_name']);self.assertFalse(report['health_ready'])
            self.assertEqual(report['requirements_missing'],['--supported','--tool-clearance-cm','--pin-exit-cm','--path-clear'])
            self.assertEqual(before,{p.name:p.read_bytes()for p in after.iterdir()})
            self.assertEqual([p.name for p in root.iterdir()],['after'])

    def test_complete_explicit_flags_build_a_deterministic_offline_candidate_only(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);after=root/'after';write_proof(after,support_proof())
            with patch.object(finish,'installer_call',side_effect=AssertionError('No connection')):
                first=capture_plan(args(after))[1];second=capture_plan(args(after))[1]
            self.assertEqual(first['bundle_id'],second['bundle_id'])
            self.assertTrue(first['operator_reference_complete']);self.assertFalse(first['reference_created'])
            self.assertFalse(first['ordinary_deposit_authorized']);self.assertFalse(first['next_phase_automatic'])
            self.assertEqual([p.name for p in root.iterdir()],['after'])

    def test_operator_note_is_literal_deterministic_provenance_without_plan_artifacts(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);after=root/'after';write_proof(after,support_proof())
            note='  Caja ajustada manualmente; apoyo completo.\nComprobación actual: "libre".  '
            arguments=args(after)+['--operator-note',note]
            with patch.object(finish.time,'time_ns',side_effect=AssertionError('No plan timestamp')):
                first=capture_plan(arguments)[1];second=capture_plan(arguments)[1]
            self.assertEqual(first['bundle_id'],second['bundle_id']);self.assertEqual(first['operator_note'],note)
            parsed=finish.parser().parse_args(arguments)
            _,info,_=finish.runner.load_predecessor(after,json.loads(finish.PROFILE.read_text()))
            reference,_,_=finish.reference_for(parsed,info)
            self.assertTrue(reference['evidence'].endswith('; operator_note='+note))
            self.assertNotEqual(first['bundle_id'],capture_plan(args(after)+['--operator-note',note+'x'])[1]['bundle_id'])
            self.assertEqual([p.name for p in root.iterdir()],['after'])

    def test_operator_note_limit_is_1500_characters_and_blank_notes_are_rejected(self):
        with tempfile.TemporaryDirectory()as directory:
            after=Path(directory)/'after';write_proof(after,support_proof())
            self.assertTrue(capture_plan(args(after)+['--operator-note','á'*1500])[1]['operator_reference_complete'])
            for note in ('x'*1501,'  \n '):
                with self.subTest(length=len(note)),self.assertRaisesRegex(ValueError,'operator-note'):
                    capture_plan(args(after)+['--operator-note',note])

    def test_open_requires_authentic_relief_and_a_new_pins_free_declaration(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);supported=root/'supported';relieved=root/'relieved'
            write_proof(supported,support_proof());write_proof(relieved,relief_proof())
            with self.assertRaisesRegex(ValueError,'PHASE_MISMATCH'):
                capture_plan(args(supported,phase='open'))
            arguments=args(relieved,phase='open');arguments.remove('--pins-free')
            code,report=capture_plan(arguments)
            self.assertEqual(code,0);self.assertIn('--pins-free',report['requirements_missing'])
            self.assertIsNone(report['task_name'])
            self.assertTrue(capture_plan(args(relieved,phase='open'))[1]['operator_reference_complete'])
            with self.assertRaises(ValueError):capture_plan(args(supported)+['--pins-free'])

    def test_incompatible_normal_scenario_flags_are_rejected_before_reading_source(self):
        extras=[['--cycle'],['--resume','old.json'],['--from-stage','grasp'],['--stop-after','cycle'],['--box-state','held']]
        with patch.object(finish.runner,'load_predecessor',side_effect=AssertionError('No reads')),patch('sys.stderr',io.StringIO()):
            for flags in extras:
                with self.subTest(flags=flags),self.assertRaises(SystemExit):finish.main(args('unused')+flags)

    def test_invalid_clearance_and_pin_measurements_never_create_a_candidate(self):
        with tempfile.TemporaryDirectory()as directory:
            after=Path(directory)/'after';write_proof(after,support_proof())
            for flag,value in (('--tool-clearance-cm','3.99'),('--tool-clearance-cm','nan'),
                               ('--pin-exit-cm','3.001'),('--pin-exit-cm','0')):
                arguments=args(after);arguments[arguments.index(flag)+1]=value
                with self.subTest(flag=flag,value=value),self.assertRaises(ValueError):capture_plan(arguments)


class FinishExecutionTests(unittest.TestCase):
    def test_receipt_records_note_and_time_separately_from_the_deterministic_bundle(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);after=root/'after';write_proof(after,support_proof());evidence=root/'check'
            note='Ajustada manualmente; apoyo completo y holguras revisadas ahora.'
            plan=capture_plan(args(after)+['--operator-note',note])[1]
            with patch.object(finish,'installer_call',return_value={'installed':True}), \
                    patch.object(finish.time,'time_ns',return_value=1234567890),patch('sys.stdout',io.StringIO()):
                self.assertEqual(finish.main(args(after,mode='check',evidence=evidence)+['--operator-note',note]),0)
            receipt=json.loads((evidence/'supervisor.json').read_text())
            self.assertEqual(receipt['operator_note'],note)
            self.assertEqual(receipt['created_ns'],1234567890)
            self.assertEqual(receipt['declarations_recorded_ns'],1234567890)
            self.assertFalse(receipt['recording_timestamp_verifies_physical_state'])
            candidate=json.loads((evidence/'bundle.json').read_text())
            self.assertEqual(candidate['manifest']['id'],plan['bundle_id'])
            self.assertTrue(candidate['review']['reference']['evidence'].endswith(note))

    def test_check_only_checks_files_and_reports_pending_without_install_or_health(self):
        for installed in (False,True):
            with tempfile.TemporaryDirectory()as directory:
                root=Path(directory);after=root/'after';write_proof(after,support_proof());evidence=root/'check'
                with patch.object(finish,'installer_call',return_value={'installed':installed})as install, \
                        patch.object(finish.runner,'cli_main',side_effect=AssertionError('No health/runtime')), \
                        patch('sys.stdout',io.StringIO()):
                    result=finish.main(args(after,mode='check',evidence=evidence))
                self.assertEqual(result,0 if installed else 55)
                self.assertEqual(install.call_args.args[1],'check');install.assert_called_once()
                receipt=json.loads((evidence/'supervisor.json').read_text())
                self.assertFalse(receipt['health_ready']);self.assertEqual(receipt['movement_commands_sent'],0)
                self.assertEqual(receipt['status'],'FILES_VERIFIED'if installed else'INSTALLATION_PENDING')
                self.assertFalse((after/'trial.json.consumed.json').exists())

    def test_missing_declarations_or_nontty_block_before_writes_and_installer(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);after=root/'after';write_proof(after,support_proof());evidence=root/'run'
            with patch.object(finish,'installer_call',side_effect=AssertionError('No installer')), \
                    patch('sys.stdout',io.StringIO()):
                self.assertEqual(finish.main(args(after,mode='run',complete=False,evidence=evidence)),78)
                with patch('sys.stdin.isatty',return_value=False),self.assertRaisesRegex(RuntimeError,'TTY'):
                    finish.main(args(after,mode='run',evidence=evidence))
            self.assertFalse(evidence.exists())

    def test_run_installs_then_checks_then_runs_exactly_one_phase_and_consumes_no_checkpoint(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);after=root/'after';write_proof(after,support_proof());evidence=root/'run';calls=[]
            original={p.name:p.read_bytes()for p in after.iterdir()}
            def install(*values):calls.append(('installer',values[1]));return {'status':'installed'}
            def phase(arguments):
                calls.append(('phase',arguments[0]))
                self.assertEqual(Path(arguments[arguments.index('--after')+1]),after)
                if arguments[0]=='--run':
                    self.assertEqual(calls,[('installer','install'),('phase','--check'),('phase','--run')])
                    (after/'trial.json.consumed.json').write_text('{}')
                return 0
            with patch.object(finish,'installer_call',side_effect=install),patch.object(finish.runner,'cli_main',side_effect=phase), \
                    patch('sys.stdin.isatty',return_value=True),patch('sys.stdout',io.StringIO()):
                self.assertEqual(finish.main(args(after,mode='run',evidence=evidence)),0)
            self.assertEqual(calls,[('installer','install'),('phase','--check'),('phase','--run')])
            report=json.loads((evidence/'supervisor.json').read_text())
            self.assertEqual(report['status'],'phase_completed');self.assertEqual(report['movement_commands_sent'],1)
            self.assertFalse((evidence/'checkpoint.json').exists())
            self.assertEqual(original,{p.name:p.read_bytes()for p in after.iterdir()if p.name!='trial.json.consumed.json'})
            with patch.object(finish,'installer_call',side_effect=AssertionError('No repeated install')),self.assertRaisesRegex(RuntimeError,'already consumed'):
                finish.main(args(after,mode='run',evidence=root/'again'))

    def test_failed_installer_or_live_preflight_prevents_run_and_does_not_consume(self):
        for point in ('installer','live_check'):
            with tempfile.TemporaryDirectory()as directory:
                root=Path(directory);after=root/'after';write_proof(after,support_proof());evidence=root/'run'
                install=Mock(side_effect=RuntimeError('install failed'))if point=='installer'else Mock(return_value={})
                phase=Mock(return_value=78)
                with patch.object(finish,'installer_call',install),patch.object(finish.runner,'cli_main',phase), \
                        patch('sys.stdin.isatty',return_value=True),patch('sys.stdout',io.StringIO()),self.assertRaises(RuntimeError):
                    finish.main(args(after,mode='run',evidence=evidence))
                self.assertEqual(phase.call_count,0 if point=='installer'else 1)
                self.assertFalse((after/'trial.json.consumed.json').exists())
                self.assertEqual(json.loads((evidence/'supervisor.json').read_text())['status'],'interrupted')

    def test_error_after_claim_records_uncertain_motion_and_never_starts_the_other_phase(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);after=root/'after';write_proof(after,support_proof());evidence=root/'run'
            def phase(arguments):
                if arguments[0]=='--check':return 0
                (after/'trial.json.consumed.json').write_text('{}');raise RuntimeError('lost terminal')
            with patch.object(finish,'installer_call',return_value={}),patch.object(finish.runner,'cli_main',side_effect=phase)as phases, \
                    patch('sys.stdin.isatty',return_value=True),patch('sys.stdout',io.StringIO()),self.assertRaisesRegex(RuntimeError,'lost terminal'):
                finish.main(args(after,mode='run',evidence=evidence))
            self.assertEqual(phases.call_count,2)
            report=json.loads((evidence/'supervisor.json').read_text())
            self.assertIsNone(report['movement_commands_sent']);self.assertFalse(report['health_ready'])


class InstallerReceiptTests(unittest.TestCase):
    def test_exact_zero_motion_receipt_required_even_when_subprocess_returns_zero(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);after=root/'after';write_proof(after,support_proof())
            parsed=finish.parser().parse_args(args(after))
            proof,info,_=finish.runner.load_predecessor(after,json.loads(finish.PROFILE.read_text()))
            reference,_,_=finish.reference_for(parsed,info);package=finish.build_bundle(reference)
            valid=dict(status='checked',id=package['manifest']['id'],phase=finish.release.PHASE,
                       movement_commands=0,restarts=0,installed=False)
            for field,value in ((None,None),('id','f'*64),('movement_commands',False),('restarts',1),('installed','false')):
                receipt=copy.deepcopy(valid)
                if field:receipt[field]=value
                result=subprocess.CompletedProcess([],0,json.dumps(receipt),'')
                with patch.object(finish.subprocess,'run',return_value=result)as command:
                    if field:
                        with self.subTest(field=field),self.assertRaisesRegex(RuntimeError,'MISMATCH'):
                            finish.installer_call(root/'bundle.json','check',root,package)
                    else:self.assertFalse(finish.installer_call(root/'bundle.json','check',root,package)['installed'])
                self.assertIn('--check',command.call_args.args[0])


class WrapperDispatchTests(unittest.TestCase):
    def test_real_wrapper_finish_plan_and_normal_preparation_plan_remain_offline(self):
        wrapper=finish.ROOT/'scripts/optimistic_scenario1.sh'
        with tempfile.TemporaryDirectory()as directory:
            after=Path(directory)/'after';write_proof(after,support_proof())
            result=subprocess.run(['bash',str(wrapper),*args(after,complete=False)],capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertFalse(json.loads(result.stdout)['operator_reference_complete'])
        result=subprocess.run(['bash',str(wrapper),'--table-height-cm','74','--stop-after','grasp','--plan'],
                              capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        report=json.loads(result.stdout[result.stdout.index('{'):])
        self.assertEqual(report['profile']['deposit']['compatibility'],'pending')
        self.assertEqual(report['stages'],['navigate_get1','enable_vision','grasp','verify_held'])


if __name__=='__main__':unittest.main()
