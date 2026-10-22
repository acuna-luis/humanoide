"""Authenticated support/relief release phases; entirely synthetic IO."""
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch

from scripts.box_handling import scenario1_cli as cli
from scripts.box_handling import scenario1_runtime as runtime
from scripts.box_handling import scenario1_table74_current_lower_run as lowering
from scripts.box_handling import scenario1_table74_current_release as release
from scripts.box_handling import scenario1_table74_current_release_run as run
from scripts.box_handling import scenario1_table74_current_phase_cli as phase_cli
from scripts.box_handling.test_scenario1_table74_current_lower_run import (
    PROFILE,precontact_proof,lowering_bundle,proof_record,FakeLower)
from scripts.box_handling.test_scenario1_table74_trial import SNAPSHOT,sources
from scripts.box_handling.test_scenario1_table74_trial_run import SUCCESS


def set_goal(proof,goal):
    proof=copy.deepcopy(proof);proof['trial.json']['result']['goal_id']=goal
    for event in proof['events.jsonl']:
        if event.get('event')=='trial' and event['trial'].get('result')is not None:
            event['trial']['result']['goal_id']=goal
        if event.get('event')=='action' and event.get('kind')=='motion' and 'goal_id'in event['detail']:
            event['detail']['goal_id']=goal
    return proof


def support_proof():
    parent=precontact_proof()
    proof=proof_record(lowering_bundle(parent,'support'),lowering.digest(parent),parent=parent)
    return set_goal(proof,'1100702d-2081-47ca-8776-d1fc4ea52a6f')


def bundle(proof=None,stage='pin_relief',version=2):
    proof=proof or support_proof()
    ref=dict(version=version,stage=stage,surface_height_m=.74,
        predecessor_bundle_id=proof['bundle.json']['manifest']['id'],predecessor_goal_id=proof['trial.json']['result']['goal_id'],
        operator_support_confirmed=True,tool_table_clearance_m=(.05 if version==2 and stage=='pin_relief' else .04),
        required_pin_exit_m=.04 if version==2 else .03,
        operator_pins_free=stage=='lateral_open',lateral_path_clear=True,
        evidence='Synthetic direct operator support and clearance confirmation; not sensor data',
        scope='current_supported_box_only')
    return release.build_bundle(ref,sources()[0],(SNAPSHOT/'meta_clamp/wrc/open_arm_cruzr.yaml').read_text())


def relief_proof():
    parent=support_proof()
    proof=proof_record(bundle(parent),lowering.digest(parent),parent=parent)
    return set_goal(proof,'b6379c08-1aae-4827-b0f5-a1193589324c')


def settled_proof():
    parent=support_proof()
    proof=proof_record(lowering_bundle(parent,'settle'),lowering.digest(parent),parent=parent)
    return set_goal(proof,'a06f07b1-a4ed-4c02-81d7-95c8a962bd72')


def payload():
    proof=support_proof();package=bundle(proof);info,_=run.validate_entry(proof,PROFILE,package)
    return dict(mode='run',profile=copy.deepcopy(PROFILE),checkpoint=info['source'],policy='assume',
        execution_profile='optimistic_v1',cycle=False,resume_source_checkpoint=info['source'],
        resume_plan=info['planned'],resume_context=info['context'],predecessor=proof,trial_bundle=package)


class FakeRelease(run.ReleaseRuntime):
    def __init__(self,directory):
        self.events=[];super().__init__(payload(),lambda event,**values:self.events.append(dict(event=event,**values)))
        self.session=Path(directory);self.armed=self.resume_validated=True
    connected,discover,hashes,health=FakeLower.connected,FakeLower.discover,FakeLower.hashes,FakeLower.health
    check_resume_entry,quick_health,verify_trial_files=FakeLower.check_resume_entry,FakeLower.quick_health,FakeLower.verify_trial_files


class ReleaseProofTests(unittest.TestCase):
    def test_support_relief_open_chain_is_bounded_and_preserves_pending_context(self):
        first=support_proof();info,_=run.validate_entry(first,PROFILE,bundle(first))
        self.assertEqual(info['completed_stage'],'support');self.assertEqual(len(info['chain_bundles']),3)
        second=relief_proof();info,_=run.validate_entry(second,PROFILE,bundle(second,'lateral_open'))
        self.assertEqual(info['completed_stage'],'pin_relief');self.assertEqual(len(info['chain_bundles']),4)
        self.assertEqual(info['source']['profile_id'],'scenario1_table74_preparation_v1')
        self.assertEqual(info['source']['stop_after'],'navigate_put1')
        self.assertFalse(info['planned']['executable'])
        for proof,stage in ((first,'lateral_open'),(second,'pin_relief')):
            with self.subTest(stage=stage),self.assertRaises(ValueError):run.validate_entry(proof,PROFILE,bundle(proof,stage))
        opened=proof_record(bundle(second,'lateral_open'),run.digest(second),parent=second)
        with self.assertRaises(ValueError):run.validate_predecessor(opened,PROFILE)
        # A new explicit one-centimetre settle may now follow support; this
        # does not turn either native result into physical support evidence.
        self.assertEqual(lowering.validate_predecessor(first,PROFILE)['completed_stage'],'support')

    def test_unconfirmed_support_pins_or_clearance_cannot_authorize_either_action(self):
        for field,value in (('operator_support_confirmed',False),('tool_table_clearance_m',.049999),
                            ('required_pin_exit_m',.040001),('lateral_path_clear',False),('operator_pins_free',True)):
            package=bundle();package['review']['reference'][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):run.validate_entry(support_proof(),PROFILE,package)
        package=bundle(relief_proof(),'lateral_open');package['review']['reference']['operator_pins_free']=False
        with self.assertRaises(ValueError):run.validate_entry(relief_proof(),PROFILE,package)

    def test_legacy_bundle_cannot_be_newly_dispatched_but_its_authentic_proof_can_precede_v2_open(self):
        supported=support_proof();historical=bundle(supported,version=1)
        with self.assertRaisesRegex(ValueError,'(?i)historical|regenerate'):
            run.validate_entry(supported,PROFILE,historical)
        old_relief=proof_record(historical,run.digest(supported),parent=supported)
        old_relief=set_goal(old_relief,'3d58dbd8-9bfe-4b83-82e7-7a2f828ddbeb')
        info=run.validate_predecessor(old_relief,PROFILE)
        self.assertEqual(info['completed_stage'],'pin_relief')
        current=bundle(old_relief,'lateral_open',version=2)
        self.assertEqual(run.validate_entry(old_relief,PROFILE,current)[1],current)

    def test_completed_settle_is_authenticated_but_still_requires_operator_support(self):
        settled=settled_proof();info,_=run.validate_entry(settled,PROFILE,bundle(settled))
        self.assertEqual(info['completed_stage'],'settle');self.assertEqual(len(info['chain_bundles']),4)
        package=bundle(settled);package['review']['reference']['operator_support_confirmed']=False
        with self.assertRaises(ValueError):run.validate_entry(settled,PROFILE,package)
        relief=proof_record(bundle(settled),run.digest(settled),parent=settled)
        relief=set_goal(relief,'17e27d39-b07f-47f9-96a1-ce91777dbf7d')
        info,_=run.validate_entry(relief,PROFILE,bundle(relief,'lateral_open'))
        self.assertEqual(len(info['chain_bundles']),5)
        with self.assertRaises(ValueError):lowering.validate_predecessor(settled,PROFILE)

    def test_predecessor_tamper_error_missing_hash_nav_and_context_changes_are_rejected(self):
        for change in ('context','unknown_result','nav','health','hash','timestamp','parent','source','tail'):
            proof=support_proof();events=proof['events.jsonl']
            if change=='context':proof['context.json']['boot_id']='another-boot'
            elif change=='unknown_result':proof['trial.json']['result']['status']=5
            elif change=='nav':events.insert(-1,dict(event='action',time_ns=85,kind='navigation',detail={'event':'dispatched'}))
            elif change=='health':events.insert(2,dict(event='health_worker',time_ns=3,detail={'event':'error','reason':'stale'}))
            elif change=='hash':events[1]['hashes']={}
            elif change=='timestamp':events[5]['time_ns']=1
            elif change=='parent':proof['predecessor.json']['trial.json']['result']['goal_id']='not-a-uuid'
            elif change=='source':proof['source-context.json']['checkpoint']['completed'].pop()
            else:events.append(dict(event='armed',time_ns=100))
            with self.subTest(change=change),self.assertRaises((ValueError,KeyError)):
                run.validate_predecessor(proof,PROFILE)

    def test_runtime_revalidates_chain_and_only_sends_one_release_task(self):
        with tempfile.TemporaryDirectory() as directory:
            machine=FakeRelease(directory);original=copy.deepcopy(machine.checkpoint)
            with patch.object(runtime.Runtime,'action',return_value=copy.deepcopy(SUCCESS)) as action:
                machine.stage({'command':'stage','stage':run.STAGE})
                action.assert_called_once_with('motion',{'task_name':machine.trial_bundle['task_name'],'yaml_args':'{}'},45)
                with self.assertRaisesRegex(RuntimeError,'ALREADY_ATTEMPTED'):machine.stage({'command':'stage','stage':run.STAGE})
            self.assertEqual(machine.checkpoint,original)
            self.assertFalse((machine.session/'checkpoint.json').exists())
            self.assertFalse(machine.trial_record['physical_support_confirmed'])
            for task in ('cruzr/home','wrc/open_arm_cruzr'):
                with self.assertRaises(RuntimeError):machine.action('motion',{'task_name':task,'yaml_args':'{}'},45)
        bad=payload();bad['predecessor']['context.json']['boot_id']='tampered'
        with self.assertRaises(ValueError):run.ReleaseRuntime(bad)

    def test_failed_fresh_health_prevents_dispatch(self):
        with tempfile.TemporaryDirectory() as directory:
            machine=FakeRelease(directory);machine.health=Mock(side_effect=RuntimeError('health failed'))
            with patch.object(runtime.Runtime,'action') as action,self.assertRaisesRegex(RuntimeError,'health failed'):
                machine.stage({'command':'stage','stage':run.STAGE})
            action.assert_not_called();self.assertEqual(machine.trial_record['phase'],'failed')

    def test_real_bootstrap_contains_unchanged_lowering_and_loads_without_ordinary_plan(self):
        built=run.make_payload('check',PROFILE,support_proof(),bundle())
        self.assertEqual(dict(built['modules'])['scenario1_table74_current_lower_run'],Path(lowering.__file__).read_text())
        code=run.BOOTSTRAP.replace("raise SystemExit(sys.modules['scenario1_table74_current_release_run'].main(payload))",
            "sys.modules['scenario1_resume'].plan_resume=lambda *a,**k: (_ for _ in ()).throw(AssertionError('ordinary'))\n"
            "x=sys.modules['scenario1_table74_current_release_run'].ReleaseRuntime(payload)\n"
            "assert x.payload['profile']['deposit']['compatibility']=='pending'\nprint('RELEASE_LOADED')")
        result=subprocess.run([sys.executable,'-B','-c',code],input=json.dumps(built),capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stdout.strip(),'RELEASE_LOADED')


class ReleaseCliTests(unittest.TestCase):
    def files(self,root):
        after=root/'after';after.mkdir();proof=support_proof()
        for name,value in proof.items():
            (after/name).write_text(''.join(json.dumps(e)+'\n'for e in value)if name=='events.jsonl'else json.dumps(value))
        package=root/'bundle.json';package.write_text(json.dumps(bundle(proof)))
        return after,package

    def test_plan_and_check_never_consume_or_dispatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);after,package=self.files(root)
            with patch.object(run,'connection_class',side_effect=AssertionError('No connection')),patch('sys.stdout',io.StringIO())as output:
                self.assertEqual(run.cli_main(['--after',str(after),'--bundle',str(package)]),0)
            self.assertEqual(json.loads(output.getvalue())['commands_sent'],0)
            connection=Mock();connection.wait.return_value={'context':{}};connection.process.wait.return_value=0
            with patch.object(run,'connection_class',return_value=Mock(return_value=connection)), \
                    patch.object(cli,'claim_resume',side_effect=AssertionError('No claim')), \
                    patch.object(phase_cli,'open',side_effect=lambda p,m:open(root/Path(p).name,m),create=True),patch('sys.stdout',io.StringIO()):
                self.assertEqual(run.cli_main(['--check','--after',str(after),'--bundle',str(package),
                                              '--evidence-dir',str(root/'check')]),0)
            connection.send.assert_not_called();self.assertFalse((after/'trial.json.consumed.json').exists())
            self.assertFalse((root/'check/checkpoint.json').exists())

    def test_run_claims_journal_before_arm_and_sends_only_one_bound_phase(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);after,package=self.files(root);evidence=root/'run';messages=[];owner=self;data=payload()
            class Connection:
                process=Mock();process.wait.return_value=0
                def send(self,message):
                    if message['command']in('arm','stage'):owner.assertTrue((after/'trial.json.consumed.json').is_file())
                    messages.append(message)
                    if message['command']=='stage':
                        cli.atomic_json(evidence/'trial.json',dict(artifact='table74_approach_trial',version=1,
                            bundle_id=data['trial_bundle']['manifest']['id'],source_sha256=run.digest(data['predecessor']),
                            phase='succeeded',intent_ns=1,finished_ns=2,result=SUCCESS,error=None,
                            physical_support_confirmed=False,automatic_retry=False))
                def wait(self,event,timeout=None):return dict(context=data['resume_context'],checkpoint=data['checkpoint'],stage=run.STAGE)
                def close(self):pass
            with patch.object(run,'connection_class',return_value=Mock(return_value=Connection())), \
                    patch.object(phase_cli,'open',side_effect=lambda p,m:open(root/Path(p).name,m),create=True), \
                    patch.object(phase_cli.subprocess,'run'),patch('sys.stdin.isatty',return_value=True), \
                    patch('builtins.input',return_value='LIBERAR74'),patch('sys.stdout',io.StringIO()):
                self.assertEqual(run.cli_main(['--run','--after',str(after),'--bundle',str(package),
                                              '--evidence-dir',str(evidence)]),0)
            self.assertEqual(messages,[{'command':'resume','stop_after':'navigate_put1'},{'command':'arm'},
                {'command':'stage','stage':run.STAGE},{'command':'finish'}])
            self.assertFalse((evidence/'checkpoint.json').exists())
            with self.assertRaisesRegex(RuntimeError,'already consumed'):
                run.cli_main(['--after',str(after),'--bundle',str(package)])


if __name__=='__main__':unittest.main()
