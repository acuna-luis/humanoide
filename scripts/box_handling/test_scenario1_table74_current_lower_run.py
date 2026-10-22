"""Relative lowering proof chain and one-shot IO tests; no robot connections."""
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.box_handling import scenario1_cli as cli
from scripts.box_handling import scenario1_runtime as runtime
from scripts.box_handling import scenario1_table74_current_lower as lower
from scripts.box_handling import scenario1_table74_current_lower_run as run
from scripts.box_handling import scenario1_table74_trial_run as approach
from scripts.box_handling.test_scenario1_table74_current_trial_run import PROFILE, source_checkpoint, bundle as approach_bundle
from scripts.box_handling.test_scenario1_table74_trial import sources
from scripts.box_handling.test_scenario1_table74_trial_run import SUCCESS
from scripts.box_handling.test_resume_pickup_reference import fixture_source


def proof_record(bundle, source_hash, *, parent=None):
    source=source_checkpoint();context=fixture_source()[2]
    uid='80974a9d-f9b2-4322-a2d7-2db41f28766e' if parent is None else 'b765c1be-d570-4aaa-b267-b7af56d6fc25'
    terminal=dict(copy.deepcopy(SUCCESS),goal_id=uid,request_id='1')
    pending=dict(artifact='table74_approach_trial',version=1,bundle_id=bundle['manifest']['id'],source_sha256=source_hash,
        phase='pending',intent_ns=15,finished_ns=None,result=None,error=None,physical_support_confirmed=False,automatic_retry=False)
    succeeded=dict(pending,phase='succeeded',finished_ns=65,result=terminal)
    rows=[dict(event='ready',time_ns=1,context=context),
          dict(event='trial_dependencies',time_ns=2,hashes=bundle['manifest']['robot_files']),
          dict(event='trial',time_ns=20,trial=pending)]
    actions=[dict(event='dispatched',goal_id=uid,request_id='1',endpoint='/mc/manipulation/action'),
             dict(event='accepted',goal_id=uid,request_id='1',accepted=True),terminal,
             dict(event='request_complete',request_id='1',returncode=0)]
    rows += [dict(event='action',time_ns=t,kind='motion',detail=a) for t,a in zip((30,40,50,60),actions)]
    rows += [dict(event='trial',time_ns=70,trial=succeeded),dict(event='stage_complete',time_ns=80,stage=run.STAGE),
             dict(event='session_finishing',time_ns=90,reason='requested')]
    proof={'bundle.json':bundle,'trial.json':succeeded,'source-context.json':approach.context_record(source),
           'context-checkpoint.json':approach.context_record(source),'context.json':context,'events.jsonl':rows}
    if parent is not None:proof['predecessor.json']=parent
    return json.loads(json.dumps(proof))


def predecessor():
    package=approach_bundle()
    return proof_record(package,package['review']['reference']['source_checkpoint_sha256'])


def lowering_bundle(proof=None, stage='precontact'):
    proof=proof or predecessor()
    return lower.build_bundle(dict(version=1,stage=stage,gap_above_surface_m=.19 if stage=='precontact' else .05,
        target_clearance_m=.05 if stage=='precontact' else 0.,surface_height_m=.74,
        predecessor_bundle_id=proof['bundle.json']['manifest']['id'],predecessor_goal_id=proof['trial.json']['result']['goal_id'],
        evidence='Synthetic operator gap confirmation; not sensor measurement',scope='current_post_trial_box_only'),*sources())


def precontact_proof():
    parent=predecessor()
    return proof_record(lowering_bundle(parent),run.digest(parent),parent=parent)


def payload():
    proof=predecessor();bundle=lowering_bundle(proof);info,_=run.validate_entry(proof,PROFILE,bundle)
    return dict(mode='run',profile=copy.deepcopy(PROFILE),checkpoint=info['source'],policy='assume',
        execution_profile='optimistic_v1',cycle=False,resume_source_checkpoint=info['source'],
        resume_plan=info['planned'],resume_context=info['context'],predecessor=proof,trial_bundle=bundle)


class FakeLower(run.LowerRuntime):
    def __init__(self,directory):
        self.events=[];super().__init__(payload(),lambda event,**values:self.events.append(dict(event=event,**values)))
        self.session=Path(directory);self.armed=self.resume_validated=True
    def connected(self): pass
    def discover(self): pass
    def hashes(self): pass
    def health(self,require_home=False):
        if require_home:raise AssertionError('No HOME while held')
    def check_resume_entry(self): pass
    def quick_health(self): pass
    def verify_trial_files(self): pass


class LowerProofTests(unittest.TestCase):
    def test_authentic_approach_and_precontact_chain_authorize_only_the_next_phase(self):
        first=predecessor();info,bundle=run.validate_entry(first,PROFILE,lowering_bundle(first))
        self.assertEqual(info['phase'],'approach_vendor_reference')
        self.assertIs(info['planned']['executable'],False)
        self.assertEqual(info['source'],source_checkpoint())
        self.assertEqual(len(info['chain_bundles']),1)
        second=precontact_proof();info,_=run.validate_entry(second,PROFILE,lowering_bundle(second,'support'))
        self.assertEqual(len(info['chain_bundles']),2)
        self.assertEqual(info['predecessor_sha256'],run.digest(second))
        for proof,stage in ((first,'support'),(second,'precontact')):
            with self.subTest(stage=stage),self.assertRaises(ValueError):
                run.validate_entry(proof,PROFILE,lowering_bundle(proof,stage))
        support=proof_record(lowering_bundle(second,'support'),run.digest(second),parent=second)
        with self.assertRaises(ValueError):run.validate_predecessor(support,PROFILE)

    def test_parent_mutations_fail_closed_before_runtime(self):
        for change in ('missing_file','context','native_terminal','native_uuid','request_rc','nav_after_dispatch',
                       'missing_dependencies','health_error','timestamp','unknown_tail','chain_parent'):
            proof=precontact_proof() if change=='chain_parent' else predecessor()
            rows=proof['events.jsonl']
            if change=='missing_file':proof.pop('source-context.json')
            elif change=='context':proof['context.json']['boot_id']='changed'
            elif change=='native_terminal':proof['trial.json']['result']['status']=6
            elif change=='native_uuid':proof['trial.json']['result']['goal_id']='invalid'
            elif change=='request_rc':next(e for e in rows if e.get('detail',{}).get('event')=='request_complete')['detail']['returncode']=2
            elif change=='nav_after_dispatch':rows.insert(-1,dict(event='action',time_ns=85,kind='navigation',detail={'event':'dispatched'}))
            elif change=='missing_dependencies':rows[:]=[e for e in rows if e['event']!='trial_dependencies']
            elif change=='health_error':rows.insert(2,dict(event='health_worker',time_ns=3,detail={'event':'error','reason':'stale'}))
            elif change=='timestamp':rows[4]['time_ns']=rows[3]['time_ns']-1
            elif change=='unknown_tail':rows.append(dict(event='armed',time_ns=91))
            else:proof['predecessor.json']['bundle.json']['review']['reference']['evidence']='tampered'
            with self.subTest(change=change),self.assertRaises((ValueError,KeyError)):
                run.validate_predecessor(proof,PROFILE)

    def test_only_complete_known_idle_shutdown_tail_is_accepted(self):
        proof=predecessor()
        proof['events.jsonl'] += [dict(event='action',kind='motion',detail=dict(event='error',request_id=None,
            goal_id=None,reason='Lease missing, invalid or expired')),
            dict(event='action',kind='motion',detail=dict(event='worker_closed',returncode=2,physical_stop_verified=False))]
        run.validate_predecessor(proof,PROFILE)
        proof['events.jsonl'].pop()
        with self.assertRaises(ValueError):run.validate_predecessor(proof,PROFILE)

    def test_one_shot_stage_keeps_original_context_and_rejects_retry_or_other_actions(self):
        with tempfile.TemporaryDirectory() as directory:
            machine=FakeLower(directory);before=copy.deepcopy(machine.checkpoint)
            with patch.object(runtime.Runtime,'action',return_value=copy.deepcopy(SUCCESS)) as action:
                machine.stage({'command':'stage','stage':run.STAGE})
                action.assert_called_once_with('motion',{'task_name':machine.trial_bundle['task_name'],'yaml_args':'{}'},45)
                with self.assertRaisesRegex(RuntimeError,'ALREADY_ATTEMPTED'):
                    machine.stage({'command':'stage','stage':run.STAGE})
            self.assertEqual(machine.checkpoint,before)
            self.assertEqual(machine.trial_record['source_sha256'],run.digest(machine.payload['predecessor']))
            self.assertFalse(machine.trial_record['physical_support_confirmed'])
            self.assertFalse((machine.session/'checkpoint.json').exists())
            for kind,goal in [('motion',{'task_name':'cruzr/home','yaml_args':'{}'}),
                              ('navigation',{'command':'navigation_start','arg_json':'{}'})]:
                with self.assertRaises(RuntimeError):machine.action(kind,goal,45)

    def test_failed_fresh_entry_prevents_goal_and_is_not_retryable(self):
        with tempfile.TemporaryDirectory() as directory:
            machine=FakeLower(directory)
            machine.check_resume_entry=Mock(side_effect=RuntimeError('fresh arrival failed'))
            with patch.object(runtime.Runtime,'action') as action,self.assertRaisesRegex(RuntimeError,'fresh arrival'):
                machine.stage({'command':'stage','stage':run.STAGE})
            action.assert_not_called();self.assertEqual(machine.trial_record['phase'],'failed')

    def test_live_hash_readback_covers_every_predecessor_and_current_file(self):
        with tempfile.TemporaryDirectory() as directory:
            machine=FakeLower(directory)
            expected={}
            for b in machine.predecessor['chain_bundles']+[machine.trial_bundle]:expected.update(b['manifest']['robot_files'])
            with patch.object(machine,'native',return_value=json.dumps(expected)):
                run.LowerRuntime.verify_trial_files(machine)
            self.assertTrue(any(e['event']=='lower_chain_dependencies' and e['hashes']==expected for e in machine.events))
            with patch.object(machine,'native',return_value=json.dumps(machine.trial_bundle['manifest']['robot_files'])):
                with self.assertRaisesRegex(RuntimeError,'LOWER_FILES_CHANGED'):run.LowerRuntime.verify_trial_files(machine)

    def test_real_bootstrap_loads_proof_and_never_invokes_the_ordinary_resume_planner(self):
        built=run.make_payload('check',PROFILE,predecessor(),lowering_bundle())
        bootstrap=run.BOOTSTRAP.replace("raise SystemExit(sys.modules['scenario1_table74_current_lower_run'].main(payload))",
            "sys.modules['scenario1_resume'].plan_resume=lambda *a,**k: (_ for _ in ()).throw(AssertionError('ordinary plan'))\n"
            "x=sys.modules['scenario1_table74_current_lower_run'].LowerRuntime(payload)\n"
            "assert x.checkpoint['profile_id']=='scenario1_table74_preparation_v1'\nprint('LOWER_LOADED')")
        result=subprocess.run([sys.executable,'-B','-c',bootstrap],input=json.dumps(built),capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stdout.strip(),'LOWER_LOADED')


class LowerCliTests(unittest.TestCase):
    def files(self,root):
        after=root/'after';after.mkdir();proof=predecessor()
        for name,value in proof.items():
            (after/name).write_text(''.join(json.dumps(e)+'\n' for e in value) if name=='events.jsonl' else json.dumps(value))
        package=root/'bundle.json';package.write_text(json.dumps(lowering_bundle(proof)))
        return after,package

    def test_plan_is_offline_and_check_never_claims_or_arms(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);after,package=self.files(root)
            with patch.object(run,'connection_class',side_effect=AssertionError('No connection')),patch('sys.stdout',io.StringIO()) as output:
                self.assertEqual(run.cli_main(['--after',str(after),'--bundle',str(package)]),0)
            self.assertEqual(json.loads(output.getvalue())['commands_sent'],0)
            connection=Mock();connection.wait.return_value={'context':{}};connection.process.wait.return_value=0
            with patch.object(run,'connection_class',return_value=Mock(return_value=connection)), \
                    patch.object(cli,'claim_resume',side_effect=AssertionError('No claim')), \
                    patch.object(run,'open',side_effect=lambda p,m:open(root/Path(p).name,m),create=True),patch('sys.stdout',io.StringIO()):
                self.assertEqual(run.cli_main(['--check','--after',str(after),'--bundle',str(package),
                                              '--evidence-dir',str(root/'check')]),0)
            connection.send.assert_not_called();self.assertFalse((after/'trial.json.consumed.json').exists())
            self.assertFalse((root/'check/checkpoint.json').exists())

    def test_run_consumes_only_predecessor_journal_before_arm_and_sends_one_trial(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);after,package=self.files(root);evidence=root/'run';messages=[];owner=self
            original={p.name:p.read_bytes() for p in after.iterdir()};data=payload()
            class Connection:
                process=Mock();process.wait.return_value=0
                def send(self,value):
                    if value['command'] in ('arm','stage'):owner.assertTrue((after/'trial.json.consumed.json').is_file())
                    messages.append(value)
                    if value['command']=='stage':
                        cli.atomic_json(evidence/'trial.json',dict(artifact='table74_approach_trial',version=1,
                            bundle_id=data['trial_bundle']['manifest']['id'],source_sha256=run.digest(data['predecessor']),
                            phase='succeeded',intent_ns=1,finished_ns=2,result=SUCCESS,error=None,
                            physical_support_confirmed=False,automatic_retry=False))
                def wait(self,event,timeout=None):return dict(context=data['resume_context'],checkpoint=data['checkpoint'],stage=run.STAGE)
                def close(self):pass
            with patch.object(run,'connection_class',return_value=Mock(return_value=Connection())), \
                    patch.object(run,'open',side_effect=lambda p,m:open(root/Path(p).name,m),create=True), \
                    patch.object(run.subprocess,'run'),patch('sys.stdin.isatty',return_value=True), \
                    patch('builtins.input',return_value='BAJAR74'),patch('sys.stdout',io.StringIO()):
                self.assertEqual(run.cli_main(['--run','--after',str(after),'--bundle',str(package),
                                              '--evidence-dir',str(evidence)]),0)
            self.assertEqual(messages,[{'command':'resume','stop_after':'navigate_put1'},{'command':'arm'},
                {'command':'stage','stage':run.STAGE},{'command':'finish'}])
            self.assertEqual(original,{p.name:p.read_bytes() for p in after.iterdir() if p.name!='trial.json.consumed.json'})
            self.assertFalse((evidence/'checkpoint.json').exists())
            with self.assertRaisesRegex(RuntimeError,'already consumed'):
                run.cli_main(['--after',str(after),'--bundle',str(package)])


if __name__=='__main__':unittest.main()
