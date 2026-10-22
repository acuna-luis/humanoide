"""Supervised cycle contracts using synthetic state and mocked phase runners.

No SSH, ROS, native library, action server or physical command is reached.
Each real phase runner's own proof/terminal checks are covered separately.
"""
from contextlib import ExitStack
import copy
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.box_handling import scenario1_cli as cli
from scripts.box_handling import scenario1_contract as contract
from scripts.box_handling import scenario1_table74_cycle as cycle
from scripts.box_handling.test_scenario1_table74_current_trial_run import source_checkpoint


ANSWERS = ['CONTINUAR74','HUECO19','HUECO5','APOYADA','5','4',
           'DESPEJADO10','PINES_LIBRES','4','DESPEJADO10','LIBRE']


def args(*flags):
    return cli.parser('assume','optimistic_v1').parse_args(['--table-height-cm','74','--table74-supervised',*flags])


def checkpoint(root, *, held_only=False):
    value=source_checkpoint()
    if held_only:
        value=contract.new_checkpoint(json.loads(cycle.PROFILE.read_text()),stop_after='verify_held',
            policy='assume',execution_profile='optimistic_v1')
        for stage in contract.STAGES[:4]:
            extra=dict(confirmed_box='held',verification_source='assumed')if stage=='verify_held'else{}
            value=contract.complete_stage(contract.begin_stage(value,stage),stage,**extra)
    path=root/'checkpoint.json';path.write_text(json.dumps(value));return path


class Harness:
    def __init__(self,test,root,*,answers=None,stop=None):
        self.test,self.root=test,root;self.source=checkpoint(root);self.calls=[]
        self.stop=stop or SimpleNamespace(requested=False)
        self.answers=iter(ANSWERS if answers is None else answers)
        self.lock=Mock();self.stack=ExitStack()

    def __enter__(self):
        def observe(message,stop):
            cycle.guard(stop);answer=next(self.answers);self.calls.append(('answer',answer));return answer
        def pickup(selected,stop,evidence):
            self.calls.append(('pickup',copy.deepcopy(selected)));return self.source
        def phase(kind,after,source,evidence,wifi=False,**extra):
            self.calls.append(('phase',kind,after,source,wifi,extra));return evidence/'physical-run'
        def release(after,evidence,stage,clearance,pin_exit,pins_free=False):
            self.calls.append(('release',stage,clearance,pin_exit,pins_free));return evidence/'physical-run'
        def home(**kwargs):
            self.calls.append(('home',kwargs));return dict(phase='succeeded',measured_home=True)
        replacements=[patch.object(cycle.installer,'_lock',return_value=self.lock),
            patch.object(cycle.sys.stdin,'isatty',return_value=True),
            patch.object(cycle,'observe',side_effect=observe),patch.object(cycle,'pickup',side_effect=pickup),
            patch.object(cycle,'execute_phase',side_effect=phase),patch.object(cycle,'release_phase',side_effect=release),
            patch.object(cycle.home,'run',side_effect=home),
            patch.object(cycle.subprocess,'run',side_effect=AssertionError('Unexpected command')),
            patch('sys.stdout',io.StringIO()),patch('sys.stderr',io.StringIO())]
        self.mocks=[self.stack.enter_context(p) for p in replacements]
        self.pickup=self.mocks[3];self.phase=self.mocks[4];self.release=self.mocks[5];self.home=self.mocks[6]
        return self

    def __exit__(self,*exc):return self.stack.__exit__(*exc)

    def run(self,*flags):
        return cycle.run(args('--run','--evidence-dir',str(self.root/'cycle'),*flags),self.stop)

    def journal(self):return json.loads((self.root/'cycle/cycle.json').read_text())


class Table74CyclePlanTests(unittest.TestCase):
    def test_plan_has_no_files_reads_commands_or_connections_and_no_qualification_claim(self):
        selected=args('--plan','--resume','/not-read/checkpoint.json','--box-alignment-attempts','7')
        with patch.object(Path,'read_text',side_effect=AssertionError('No plan reads')), \
                patch.object(Path,'mkdir',side_effect=AssertionError('No plan directory')), \
                patch.object(cycle.installer,'_lock',side_effect=AssertionError('No plan lock')), \
                patch.object(cycle.subprocess,'run',side_effect=AssertionError('No command')),patch('sys.stdout',io.StringIO())as output:
            self.assertEqual(cycle.run(selected,SimpleNamespace(requested=False)),0)
        report=json.loads(output.getvalue())
        self.assertEqual(report['commands_sent'],0);self.assertEqual(report['files_created'],0)
        self.assertIs(report['ordinary_deposit_profile_qualified'],False)
        self.assertIs(report['native_success_does_not_prove_support'],True)
        self.assertIs(report['resume_source_validated'],False)
        self.assertEqual(report['box_alignment_attempts'],7);self.assertTrue(report['arm_task_unchanged'])

    def test_full_wifi_and_repeating_cycle_fail_before_reads_or_transport(self):
        for flag in ('--wifi','--cycle'):
            with self.subTest(flag=flag),patch.object(Path,'read_text',side_effect=AssertionError('No files')), \
                    patch.object(cycle.installer,'_lock',side_effect=AssertionError('No connection')),self.assertRaises(ValueError):
                cycle.run(args('--run',flag),SimpleNamespace(requested=False))

    def test_default_check_ends_at_put1_preserves_alignment_seven_and_never_installs(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);selected=args('--evidence-dir',str(root/'check'),'--box-alignment-attempts','7')
            lock=Mock()
            with patch.object(cycle.installer,'_lock',return_value=lock),patch.object(cli,'_main',return_value=0)as child, \
                    patch.object(cycle,'execute_phase',side_effect=AssertionError('No deposit for initial check')), \
                    patch.object(cycle,'release_phase',side_effect=AssertionError('No release')), \
                    patch.object(cycle.home,'run',side_effect=AssertionError('No HOME')), \
                    patch.object(cycle.subprocess,'run',side_effect=AssertionError('No commands')):
                self.assertEqual(cycle.run(selected,SimpleNamespace(requested=False)),0)
            passed=child.call_args.args[0]
            self.assertEqual(passed.stop_after,'put1');self.assertEqual(passed.box_alignment_attempts,7)
            self.assertTrue(passed.check);self.assertFalse(passed.run);self.assertFalse(passed.cycle)
            self.assertEqual(selected.stop_after,'cycle');lock.close.assert_called_once()

    def test_root_cli_routes_pending_profile_without_manufacturing_full_checkpoint(self):
        original=cycle.PROFILE.read_bytes()
        with patch.object(cycle,'run',return_value=43)as coordinator, \
                patch.object(cli,'Connection',side_effect=AssertionError('No direct connection')), \
                patch.object(contract,'new_checkpoint',side_effect=AssertionError('No full pending checkpoint')):
            self.assertEqual(cli.main(['--plan','--table-height-cm','74','--box-alignment-attempts','7'],
                policy='assume',execution_profile='optimistic_v1'),43)
        self.assertEqual(coordinator.call_args.args[0].box_alignment_attempts,7)
        self.assertEqual(cycle.PROFILE.read_bytes(),original)
        self.assertEqual(json.loads(original)['deposit']['compatibility'],'pending')

    def test_put1_readonly_check_preserves_missing_installed_file_code55(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);source=checkpoint(root);before=source.read_bytes()
            selected=args('--check','--resume',str(source),'--evidence-dir',str(root/'check'))
            with patch.object(cycle.installer,'_lock',return_value=Mock()), \
                    patch.object(cycle,'pickup',side_effect=AssertionError('No repeated pickup')), \
                    patch.object(cycle,'execute_phase',return_value=55)as phase, \
                    patch.object(cycle.home,'run',side_effect=AssertionError('No HOME')):
                self.assertEqual(cycle.run(selected,SimpleNamespace(requested=False)),55)
            self.assertEqual(phase.call_args.args[:3],('approach',None,source))
            self.assertEqual(phase.call_args.kwargs,{'check_only':True})
            self.assertEqual(source.read_bytes(),before);self.assertFalse(source.with_name('checkpoint.json.consumed.json').exists())
            pending=json.loads((root/'check/cycle.json').read_text())
            self.assertEqual(pending['status'],'installation_pending');self.assertIs(pending['health_ready'],False)

    def test_approach_check_missing_installation_does_not_install_or_run(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);source=checkpoint(root);evidence=root/'phase-check'
            with patch.object(cycle,'installer_call',return_value={'installed':False})as installer, \
                    patch.object(cycle.approach_run,'cli_main',side_effect=AssertionError('No live check without installation')), \
                    patch('sys.stdout',io.StringIO()):
                self.assertEqual(cycle.execute_phase('approach',None,source,evidence,check_only=True),55)
            self.assertEqual(installer.call_count,1);self.assertEqual(installer.call_args.args[1],'check')
            self.assertTrue((evidence/'bundle.json').exists())
            self.assertFalse(source.with_name(source.name+'.consumed.json').exists())

    def test_installation_without_verified_external_backup_never_reaches_native_phase_runner(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);source=checkpoint(root)
            with patch.object(cycle,'installer_call',return_value={'installed':True}), \
                    patch.object(cycle,'archive_installation',side_effect=ValueError('backup differs'))as backup, \
                    patch.object(cycle.approach_run,'cli_main',side_effect=AssertionError('No phase after failed backup'))as runner:
                with self.assertRaisesRegex(ValueError,'backup differs'):
                    cycle.execute_phase('approach',None,source,root/'attempt')
            backup.assert_called_once();runner.assert_not_called()
            self.assertFalse(source.with_name(source.name+'.consumed.json').exists())

    def test_release_backup_failure_prevents_finish_runner_and_any_opening(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory)
            with patch.object(cycle,'stage_release',side_effect=ValueError('release backup differs'))as stage, \
                    patch.object(cycle.finish,'main',side_effect=AssertionError('No release before verified backup'))as finish:
                with self.assertRaisesRegex(ValueError,'release backup differs'):
                    cycle.release_phase(root/'after',root/'release','pin-relief',5.,4.)
            stage.assert_called_once();finish.assert_not_called()

    def test_external_backup_requires_exact_package_receipt_and_original_source_hashes(self):
        package=cycle.build_approach(source_checkpoint())
        originals={path:{'sha256':value}for path,value in package['dependencies'].items()}
        xml_path=cycle.approach.SOURCE_XML_PATH
        originals[xml_path]['text']=(cycle.SNAPSHOT/'tasks/wrc_cruzr/put_cruzr_wrc_low.xml').read_text()
        receipt=dict(status='installed',id=package['manifest']['id'],phase=package['manifest']['phase'],
            package=str(cycle.installer.EVIDENCE_ROOT/package['manifest']['id']),
            originals_overwritten=False,movement_commands=0,restarts=0)
        objects={'bundle.json':package,'manifest.json':package['manifest'],
                 'originals.json':originals,'install-receipt.json':receipt}
        def response(values):return dict(start_ns=100,finished_ns=200,
            stdout=json.dumps({name:json.dumps(value)for name,value in values.items()}))
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);valid=root/'valid';valid.mkdir()
            with patch.object(cycle.home,'execute',return_value=response(objects))as transport:
                cycle.archive_installation(package,valid)
            transport.assert_called_once()
            copied=valid/'robot-installation-backup'
            self.assertEqual(json.loads((copied/'install-receipt.json').read_text()),receipt)
            copied_receipt=json.loads((copied/'copy-receipt.json').read_text())
            self.assertIs(copied_receipt['verified'],True)
            self.assertEqual(set(copied_receipt['sha256']),set(objects))
            for mutation in ('text','hash','receipt','missing'):
                altered=copy.deepcopy(objects)
                if mutation=='text':altered['originals.json'][xml_path]['text']='changed source'
                elif mutation=='hash':altered['originals.json'][xml_path]['sha256']='0'*64
                elif mutation=='receipt':altered['install-receipt.json']['originals_overwritten']=True
                else:altered['receipt.json']=altered.pop('install-receipt.json')
                output=root/mutation;output.mkdir()
                with self.subTest(mutation=mutation),patch.object(cycle.home,'execute',return_value=response(altered)), \
                        self.assertRaises(ValueError):cycle.archive_installation(package,output)
                self.assertFalse((output/'robot-installation-backup').exists())


class Table74CycleOrchestrationTests(unittest.TestCase):
    def test_full_order_requires_current_support_pins_and_empty_path_before_home(self):
        with tempfile.TemporaryDirectory()as directory,Harness(self,Path(directory))as h:
            original=cycle.PROFILE.read_bytes();self.assertEqual(h.run('--box-alignment-attempts','7'),0)
            self.assertEqual([c[1]for c in h.calls if c[0]=='phase'],['approach','precontact','support'])
            releases=[c for c in h.calls if c[0]=='release']
            self.assertEqual(releases,[('release','pin-relief',5.,4.,False),('release','open',4.,4.,True)])
            self.assertLess(h.calls.index(('answer','APOYADA')),h.calls.index(releases[0]))
            self.assertLess(h.calls.index(('answer','PINES_LIBRES')),h.calls.index(releases[1]))
            self.assertEqual(h.calls[-2],('answer','LIBRE'));self.assertEqual(h.calls[-1][0],'home')
            self.assertFalse(h.calls[-1][1]['wifi']);self.assertTrue(all(not c[4]for c in h.calls if c[0]=='phase'))
            self.assertEqual(h.pickup.call_args.args[0].box_alignment_attempts,7)
            self.assertEqual(h.journal()['status'],'succeeded');self.assertEqual(h.journal()['phase_boundary'],'measured_home')
            self.assertFalse(h.journal()['ordinary_profile_qualified']);self.assertEqual(cycle.PROFILE.read_bytes(),original)

    def test_only_one_uniform_residual_gap_correction_then_requires_new_complete_support(self):
        observations=ANSWERS[:3]+['HUECO1','APOYADA']+ANSWERS[4:]
        with tempfile.TemporaryDirectory()as directory,Harness(self,Path(directory),answers=observations)as h:
            self.assertEqual(h.run(),0)
            self.assertEqual([c[1]for c in h.calls if c[0]=='phase'],['approach','precontact','support','settle'])
            self.assertEqual(h.release.call_count,2);self.assertEqual(h.home.call_count,1)
        observations=ANSWERS[:3]+['HUECO1','HUECO1']
        with tempfile.TemporaryDirectory()as directory,Harness(self,Path(directory),answers=observations)as h:
            self.assertEqual(h.run(),55)
            self.assertEqual([c[1]for c in h.calls if c[0]=='phase'].count('settle'),1)
            h.release.assert_not_called();h.home.assert_not_called()

    def test_partial_or_native_success_alone_never_releases_or_homes(self):
        for state in ('PARCIAL','SUCCEED','APOYO UNA ESQUINA',''):
            with self.subTest(state=state),tempfile.TemporaryDirectory()as directory, \
                    Harness(self,Path(directory),answers=ANSWERS[:3]+[state])as h:
                self.assertEqual(h.run(),55);h.release.assert_not_called();h.home.assert_not_called()
                self.assertEqual(h.journal()['phase_boundary'],'support')
                self.assertEqual(h.journal()['operator_support_observation'],state)

    def test_no_free_pins_no_current_clearance_or_no_empty_path_stops_before_next_action(self):
        cases=[(ANSWERS[:7]+['NO_LIBRES'],1,0),
               (ANSWERS[:8]+['3'],1,0),
               (ANSWERS[:-1]+['NO_LIBRE'],2,0),
               (ANSWERS[:4]+['4'],0,0),
               (ANSWERS[:5]+['5'],0,0)]
        for observations,releases,homes in cases:
            with self.subTest(observations=observations),tempfile.TemporaryDirectory()as directory, \
                    Harness(self,Path(directory),answers=observations)as h:
                self.assertEqual(h.run(),55)
                self.assertEqual(h.release.call_count,releases);self.assertEqual(h.home.call_count,homes)

    def test_pickup_failure_never_runs_any_deposit_or_home(self):
        with tempfile.TemporaryDirectory()as directory,Harness(self,Path(directory))as h:
            h.pickup.side_effect=RuntimeError('grasp failed')
            self.assertEqual(h.run(),78);h.phase.assert_not_called();h.release.assert_not_called();h.home.assert_not_called()
            self.assertEqual(h.journal()['in_flight'],'pickup_to_put1')

    def test_phase_failure_or_keyboard_interrupt_never_advances_or_sends_home(self):
        for failure,code in ((RuntimeError('native interrupted'),78),(KeyboardInterrupt(),130)):
            with self.subTest(failure=type(failure).__name__),tempfile.TemporaryDirectory()as directory, \
                    Harness(self,Path(directory))as h:
                h.phase.side_effect=[h.root/'approach/physical-run',failure]
                self.assertEqual(h.run(),code);self.assertEqual(h.phase.call_count,2)
                h.release.assert_not_called();h.home.assert_not_called()
                self.assertEqual(h.journal()['phase_boundary'],'approach')
                self.assertEqual(h.journal()['in_flight'],'precontact')

    def test_stop_after_phase_finishes_does_not_start_any_later_phase(self):
        with tempfile.TemporaryDirectory()as directory,Harness(self,Path(directory))as h:
            def phase(*a,**k):h.stop.requested=True;return h.root/'approach/physical-run'
            h.phase.side_effect=phase
            self.assertEqual(h.run(),55);self.assertEqual(h.phase.call_count,1)
            h.release.assert_not_called();h.home.assert_not_called()

    def test_clean_put1_resume_never_repeats_pickup_or_edits_source(self):
        with tempfile.TemporaryDirectory()as directory,Harness(self,Path(directory))as h:
            before=h.source.read_bytes();self.assertEqual(h.run('--resume',str(h.source),'--box-state','held'),0)
            h.pickup.assert_not_called();self.assertEqual(h.phase.call_args_list[0].args[2],h.source)
            self.assertEqual(h.source.read_bytes(),before)
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);source=checkpoint(root);document=json.loads(source.read_text());document['failure']='fault'
            source.write_text(json.dumps(document))
            with patch.object(cycle.sys.stdin,'isatty',return_value=True), \
                    patch.object(cycle.installer,'_lock',side_effect=AssertionError('No transport for invalid source')), \
                    self.assertRaises(ValueError):
                cycle.run(args('--run','--resume',str(source),'--evidence-dir',str(root/'cycle')),SimpleNamespace(requested=False))

    def test_resume_implicit_movement_reaches_child_run_without_mutating_original_args(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);source=checkpoint(root,held_only=True)
            selected=args('--resume',str(source),'--box-alignment-attempts','7')
            with patch.object(cli,'_main',return_value=0)as child:
                self.assertEqual(cycle.pickup(selected,SimpleNamespace(requested=False),root/'child'),root/'child/checkpoint.json')
            passed=child.call_args.args[0]
            self.assertTrue(passed.run);self.assertFalse(passed.check);self.assertEqual(passed.resume,source)
            self.assertEqual(passed.stop_after,'put1');self.assertEqual(passed.box_alignment_attempts,7)
            self.assertFalse(selected.run);self.assertEqual(selected.stop_after,'cycle')

    def test_existing_evidence_and_failed_home_do_not_claim_cycle_completion(self):
        with tempfile.TemporaryDirectory()as directory,Harness(self,Path(directory))as h:
            target=h.root/'cycle';target.mkdir();journal=target/'cycle.json';journal.write_text('USER EXISTING FILE')
            self.assertEqual(h.run(),78);self.assertEqual(journal.read_text(),'USER EXISTING FILE')
            h.pickup.assert_not_called();h.phase.assert_not_called();h.home.assert_not_called()
        for result in ({'phase':'succeeded','measured_home':False},{'phase':'failed','measured_home':True},None):
            with self.subTest(result=result),tempfile.TemporaryDirectory()as directory,Harness(self,Path(directory))as h:
                h.home.side_effect=None;h.home.return_value=result
                self.assertEqual(h.run(),78);self.assertNotEqual(h.journal()['status'],'succeeded')
                self.assertEqual(h.release.call_count,2);self.assertEqual(h.home.call_count,1)


if __name__=='__main__':unittest.main()
