#!/usr/bin/env python3
"""One relative lowering from authenticated current table74 trial evidence.

Default --plan is offline. The predecessor journal is consumed before arm;
the original pending-profile checkpoint is context only. No opening, pin
disengagement, navigation, grasp, HOME or retry is authorized. A successful
support lowering still needs direct physical confirmation of actual support.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

if __name__ == '__main__' and not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = 'scripts.box_handling'

if __package__:
    from . import scenario1_contract as contract
    from . import scenario1_table74_current_trial_run as current
    from . import scenario1_table74_current_lower as lower
    from . import scenario1_table74_support_run as proof_tools
    from . import scenario1_table74_trial_run as approach
    from .scenario1_runtime import Runtime, code_command
else:
    import scenario1_contract as contract
    import scenario1_table74_current_trial_run as current
    import scenario1_table74_current_lower as lower
    import scenario1_table74_support_run as proof_tools
    import scenario1_table74_trial_run as approach
    from scenario1_runtime import Runtime, code_command


STAGE = approach.STAGE
FILES = proof_tools.FILES
BOOTSTRAP = current.BOOTSTRAP.replace("sys.modules['scenario1_table74_current_trial_run'].main(payload)",
                                    "sys.modules['scenario1_table74_current_lower_run'].main(payload)")
digest = proof_tools.digest


def entry_context(source, source_hash):
    return dict(artifact='table74_current_trial_context', executable=False,
        checkpoint=copy.deepcopy(source), stage=STAGE, source_sha256=source_hash,
        requirements=dict(box_state='held', home=False, waypoint='put1', vision_prep=False))


def validate_predecessor(proof, profile, *, _depth=0):
    """Bounded authentic approach -> precontact -> support evidence chain."""
    if _depth > 1 or not isinstance(proof, dict) or 'bundle.json' not in proof:
        raise ValueError('Lowering predecessor proof is missing or too deep')
    bundle = proof['bundle.json']
    phase = bundle.get('manifest', {}).get('phase') if isinstance(bundle, dict) else None
    parent = None
    if phase == 'approach_vendor_reference':
        if set(proof) != set(FILES):
            raise ValueError('Current approach requires exactly its six proof files')
        bundle = current.validate_bundle(bundle)
        def entry(source, selected, checked):
            source, planned = current.prepare_entry(source, selected, checked)
            return source, {}, planned
        builder = current.validate_bundle
    elif phase == 'current_relative_lowering' and _depth == 0:
        if set(proof) != set(FILES)|{'predecessor.json'}:
            raise ValueError('Precontact predecessor requires its original predecessor proof')
        bundle = lower.validate_bundle(bundle)
        if bundle['review']['reference']['stage'] != 'precontact':
            raise ValueError('A completed support phase cannot authorize another lowering')
        parent = validate_predecessor(proof['predecessor.json'], profile, _depth=1)
        ref = bundle['review']['reference']
        if (ref['predecessor_bundle_id'] != parent['bundle_id'] or ref['predecessor_goal_id'] != parent['goal_id']):
            raise ValueError('Precontact reference does not identify its original approach')
        def entry(source, selected, checked):
            source = contract.validate_checkpoint(source, selected)
            if source != parent['source']:
                raise ValueError('Lowering predecessor changed the original checkpoint')
            return source, {}, entry_context(source, parent['predecessor_sha256'])
        builder = lower.validate_bundle
    else:
        raise ValueError('Only a current approach or its first precontact lowering can precede this trial')
    events = proof.get('events.jsonl')
    if not isinstance(events, list) or not 1 <= len(events) <= 20000:
        raise ValueError('Predecessor events are missing or exceed the bounded proof size')
    finish = [i for i,e in enumerate(events) if isinstance(e,dict) and e.get('event')=='session_finishing']
    if len(finish) != 1:
        raise ValueError('Predecessor has no unique finish boundary')
    active = events[:finish[0]+1]
    stamps = [e.get('time_ns') for e in active if isinstance(e,dict)]
    if (len(stamps)!=len(active) or any(type(t)is not int or t<=0 for t in stamps) or
            stamps != sorted(stamps)):
        raise ValueError('Predecessor source timestamps are missing, invalid or regressed')
    if any(e.get('event')=='error' or e.get('detail',{}).get('event') in
           ('error','terminal_unknown','worker_exit_unconfirmed','cancel_requested','cancel_response','interrupted_terminal')
           for e in active):
        raise ValueError('Predecessor contains an error or unconfirmed interruption')
    result = proof.get('trial.json',{}).get('result',{})
    goal = result.get('goal_id')
    try:
        if str(uuid.UUID(goal))!=goal or uuid.UUID(goal).int==0: raise ValueError('noncanonical')
    except (ValueError,TypeError,AttributeError):
        raise ValueError('Predecessor goal UUID is invalid')
    if type(result.get('request_id')) is not str or not result['request_id']:
        raise ValueError('Predecessor native request identity is absent')
    info = proof_tools.validate_predecessor({name:proof[name] for name in FILES},profile,
        bundle_validator=builder,entry_builder=entry,pinned_bundle_id=bundle['manifest']['id'],pinned_goal_id=goal)
    journal = proof['trial.json']
    journal_events = [e for e in active if e.get('event')=='trial']
    motion = [e for e in active if e.get('event')=='action' and e.get('kind')=='motion']
    relevant = [next(e for e in motion if e['detail']['event']==name)
                for name in ('dispatched','accepted','result','request_complete')]
    if not (journal['intent_ns'] <= journal_events[0]['time_ns'] < relevant[0]['time_ns'] <
            relevant[1]['time_ns'] < relevant[2]['time_ns'] < relevant[3]['time_ns'] <=
            journal['finished_ns'] <= journal_events[-1]['time_ns'] < active[-1]['time_ns']):
        raise ValueError('Predecessor journal/native source timestamp order differs')
    if parent is not None and info['context'] != parent['context']:
        raise ValueError('Lowering predecessor changed robot/map/dependency context')
    info.update(predecessor_sha256=digest(proof),bundle_id=bundle['manifest']['id'],goal_id=goal,
                phase=phase,source=info['source'],
                chain_bundles=(parent['chain_bundles'] if parent else [])+[bundle])
    info['planned']=entry_context(info['source'],info['predecessor_sha256'])
    return info


def validate_entry(proof, profile, bundle):
    info = validate_predecessor(proof,profile)
    bundle = lower.validate_bundle(bundle)
    ref = bundle['review']['reference']
    expected = 'approach_vendor_reference' if ref['stage']=='precontact' else 'current_relative_lowering'
    if (info['phase']!=expected or ref['predecessor_bundle_id']!=info['bundle_id'] or
            ref['predecessor_goal_id']!=info['goal_id']):
        raise ValueError('Lowering stage does not match its authenticated predecessor')
    return info, bundle


def load_predecessor(directory, profile):
    directory=Path(directory)
    if (directory/'trial.json.consumed.json').exists():
        raise RuntimeError('Predecessor journal already consumed; no lowering retry')
    names=list(FILES)+(['predecessor.json'] if (directory/'predecessor.json').exists() else [])
    raw={name:(directory/name).read_bytes() for name in names}
    if any(len(value)>16*1024*1024 for value in raw.values()) or sum(map(len,raw.values()))>32*1024*1024:
        raise ValueError('Predecessor files exceed proof bounds')
    proof={name:([json.loads(line) for line in value.decode().splitlines() if line.strip()]
                 if name=='events.jsonl' else json.loads(value)) for name,value in raw.items()}
    info=validate_predecessor(proof,profile)
    return proof,info,{name:hashlib.sha256(value).hexdigest() for name,value in raw.items()}


class LowerRuntime(current.CurrentTrialRuntime):
    def __init__(self,payload,emit=None):
        self.predecessor,self.trial_bundle=validate_entry(payload['predecessor'],payload['profile'],payload['trial_bundle'])
        info=self.predecessor
        if (payload.get('checkpoint')!=info['source'] or payload.get('resume_source_checkpoint')!=info['source'] or
                payload.get('resume_plan')!=info['planned'] or payload.get('resume_context')!=info['context'] or
                payload.get('cycle',False)is not False or payload.get('resume_options')is not None or
                payload.get('resume_pickup_reference')is not None):
            raise ValueError('Lowering technical context differs from its authenticated predecessor')
        base=dict(payload);base.pop('resume_plan',None)
        Runtime.__init__(self,base,emit)
        self.payload=payload;self.resume_plan=info['planned']
        self.trial_record=None;self._trial_dispatch=False

    def verify_trial_files(self):
        self.connected()
        expected={}
        for bundle in self.predecessor['chain_bundles']+[self.trial_bundle]:
            for path,value in bundle['manifest']['robot_files'].items():
                if path in expected and expected[path]!=value: raise ValueError('Conflicting predecessor dependency pin')
                expected[path]=value
        code='''import hashlib,json,pathlib,sys
print(json.dumps({p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() for p in json.loads(sys.argv[1])}))
'''
        observed=json.loads(self.native(code_command(code,[json.dumps(list(expected))]),timeout=20))
        if observed!=expected: raise RuntimeError('LOWER_FILES_CHANGED: predecessor, lowering or dependencies differ')
        # Keep each trial's own manifest identity in historical proof; live
        # readback additionally verifies every earlier task in the chain.
        self.emit('trial_dependencies',bundle_id=self.trial_bundle['manifest']['id'],
                  hashes={p:observed[p] for p in self.trial_bundle['manifest']['robot_files']})
        self.emit('lower_chain_dependencies',hashes=observed)


def main(payload): return LowerRuntime(payload).run()


def make_payload(mode,profile,proof,bundle):
    cli=approach.local_cli();info,bundle=validate_entry(proof,profile,bundle)
    payload=cli.make_payload(mode,profile,info['source'])
    payload.update(policy='assume',execution_profile='optimistic_v1',cycle=False,box_alignment_attempts=0,
        resume_source_checkpoint=info['source'],resume_plan=info['planned'],resume_context=info['context'],
        predecessor=copy.deepcopy(proof),trial_bundle=bundle)
    here=Path(__file__).resolve().parent
    payload['modules'] += [(name,(here/(name+'.py')).read_text()) for name in
        ('scenario1_deposit','scenario1_table74_trial','scenario1_table74_trial_run',
         'scenario1_table74_current_trial','scenario1_table74_current_trial_run',
         'scenario1_table74_support','scenario1_table74_support_run',
         'scenario1_table74_current_lower','scenario1_table74_current_lower_run')]
    return payload


def connection_class(cli): return approach.connection_class(cli,bootstrap=BOOTSTRAP)


def parser():
    p=argparse.ArgumentParser(description=__doc__);m=p.add_mutually_exclusive_group()
    m.add_argument('--plan',action='store_true');m.add_argument('--check',action='store_true');m.add_argument('--run',action='store_true')
    p.add_argument('--after',type=Path,required=True);p.add_argument('--bundle',type=Path,required=True)
    p.add_argument('--profile',type=Path,default=Path(__file__).with_name('scenario1_table74_preparation.json'))
    p.add_argument('--evidence-dir',type=Path);p.add_argument('--wifi',action='store_true')
    return p


def cli_main(argv=None):
    cli=approach.local_cli();args=parser().parse_args(argv)
    profile=json.loads(args.profile.read_text())
    proof,info,hashes=load_predecessor(args.after,profile)
    bundle=lower.validate_bundle(json.loads(args.bundle.read_text()))
    info,bundle=validate_entry(proof,profile,bundle)
    if not args.run and not args.check:
        print(json.dumps(dict(mode='plan',stage=STAGE,task_name=bundle['task_name'],context=info['planned'],
            review=bundle['review'],predecessor_sha256=info['predecessor_sha256'],commands_sent=0,
            predecessor_consumed=False,automatic_retries=0,ordinary_deposit_authorized=False),indent=2,ensure_ascii=False))
        return 0
    if args.run and not sys.stdin.isatty(): raise RuntimeError('A physical operator and TTY confirmation are required')
    payload=make_payload('run' if args.run else 'check',profile,proof,bundle)
    evidence=args.evidence_dir or cli.ROOT.parent/'Humanoide-vla-evidence'/(
        time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'_TABLE74_CURRENT_LOWER_'+str(os.getpid()))
    evidence.mkdir(parents=True,exist_ok=False);os.chmod(evidence,0o700)
    for name,value in (('source-context.json',approach.context_record(info['source'])),
                       ('predecessor.json',proof),('bundle.json',bundle)):
        cli.atomic_json(evidence/name,value)
    cli.atomic_json(evidence/'source-sha256.json',{name:hashlib.sha256(code.encode()).hexdigest()
        for name,code in payload['modules']}|{name:hashlib.sha256(payload[name].encode()).hexdigest()
        for name in ('action_client','health_worker','resume_worker','perception_guard','sensor_worker')})
    print('Evidencia: '+str(evidence),flush=True)
    from contextlib import ExitStack
    import fcntl
    connection=None
    with ExitStack() as stack:
        for path in ('/tmp/cruzr_blue_workbin_cycle.lock','/tmp/cruzr-improved-scenario1.lock'):
            lock=stack.enter_context(open(path,'a'));fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            connection=connection_class(cli)(payload,args.wifi,evidence)
            ready=connection.wait('ready');cli.atomic_json(evidence/'context.json',ready['context'])
            if args.check:
                if connection.process.wait(timeout=15)!=0: raise RuntimeError('Lowering technical check failed')
                print('LOWER_CHECK_OK; predecessor unchanged, no motion sent.');return 0
            ref=bundle['review']['reference']
            cli.confirm('Descenso único '+str(round((ref['gap_above_surface_m']-ref['target_clearance_m'])*100))+
                'cm; misma caja y agarre estables, hueco actual comprobado en ambos lados, caja entera sobre tablero. '
                'Manos/cinta fuera, recorrido libre, cargador desconectado, paros liberados, ruedas en navegación, '
                'otros mandos detenidos y persona junto al paro. No abre ni desengancha; SUCCEED no confirma apoyo.', 'BAJAR74')
            def unchanged():
                new,_,fresh=load_predecessor(args.after,profile)
                if new!=proof or fresh!=hashes or lower.validate_bundle(json.loads(args.bundle.read_text()))!=bundle:
                    raise RuntimeError('Lowering source proof or bundle changed after preflight')
            unchanged();connection.send({'command':'resume','stop_after':info['source']['stop_after']})
            if connection.wait('resume_ready')['checkpoint']!=info['source']: raise RuntimeError('Lowering entry context changed')
            unchanged()
            subprocess.run(['bash',str(cli.ROOT/'scripts/lib/cruzr_contact_motion_lock.sh'),'table74-current-lower'],
                           check=True,start_new_session=True)
            cli.atomic_json(evidence/'trial-intent.json',dict(artifact='table74_current_lower_intent',
                predecessor_sha256=info['predecessor_sha256'],bundle_id=bundle['manifest']['id'],
                phase='pending',automatic_retry=False,time_ns=time.time_ns()))
            cli.claim_resume(args.after/'trial.json',evidence/'trial.json')
            connection.send({'command':'arm'});connection.wait('armed')
            connection.send({'command':'stage','stage':STAGE})
            if connection.wait('stage_complete',timeout=120).get('stage')!=STAGE: raise RuntimeError('Unexpected lowering completion')
            journal=approach.validate_journal(json.loads((evidence/'trial.json').read_text()),
                bundle['manifest']['id'],info['predecessor_sha256'])
            if journal['phase']!='succeeded': raise RuntimeError('Lowering lacks confirmed terminal result')
            cli.finish_connection(connection)
            print('LOWER_COMPLETED; comprobar hueco/apoyo físico; sin apertura, desenganche ni HOME.');return 0
        finally:
            if connection: connection.close()


if __name__=='__main__': raise SystemExit(cli_main())
