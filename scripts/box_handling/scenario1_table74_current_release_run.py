#!/usr/bin/env python3
"""One supervised pin relief or lateral opening after authenticated support.

Each phase consumes its predecessor trial journal, retains the original
pending-profile checkpoint as context only and sends exactly one immutable
task. Operator support/clearance declarations remain explicit assumptions,
never sensor measurements. No HOME, retry or ordinary deposit is authorized.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
import uuid

if __name__=='__main__' and not __package__:
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
    __package__='scripts.box_handling'

if __package__:
    from . import scenario1_contract as contract
    from . import scenario1_table74_current_lower as lower
    from . import scenario1_table74_current_lower_run as lowering
    from . import scenario1_table74_current_release as release
    from . import scenario1_table74_support_run as proof_tools
    from . import scenario1_table74_trial_run as approach
    from .scenario1_runtime import Runtime
else:
    import scenario1_contract as contract
    import scenario1_table74_current_lower as lower
    import scenario1_table74_current_lower_run as lowering
    import scenario1_table74_current_release as release
    import scenario1_table74_support_run as proof_tools
    import scenario1_table74_trial_run as approach
    from scenario1_runtime import Runtime


STAGE=approach.STAGE
FILES=lowering.FILES
digest=lowering.digest
BOOTSTRAP=lowering.BOOTSTRAP.replace("sys.modules['scenario1_table74_current_lower_run'].main(payload)",
                                    "sys.modules['scenario1_table74_current_release_run'].main(payload)")


def _completed_trial(proof,profile,bundle,builder,parent):
    """Validate native completion without widening the lowering predecessor API."""
    def entry(source,selected,checked):
        source=contract.validate_checkpoint(source,selected)
        if source!=parent['source']:
            raise ValueError('Release predecessor changed the original pending checkpoint')
        return source,{},lowering.entry_context(source,parent['predecessor_sha256'])
    events=proof.get('events.jsonl')
    if not isinstance(events,list) or not 1<=len(events)<=20000:
        raise ValueError('Release predecessor events are missing or unbounded')
    finishes=[i for i,e in enumerate(events) if isinstance(e,dict) and e.get('event')=='session_finishing']
    if len(finishes)!=1:raise ValueError('Release predecessor has no unique finish boundary')
    active=events[:finishes[0]+1]
    stamps=[e.get('time_ns') for e in active if isinstance(e,dict)]
    if (len(stamps)!=len(active) or any(type(t)is not int or t<=0 for t in stamps) or stamps!=sorted(stamps)):
        raise ValueError('Release predecessor timestamps are missing, invalid or regressed')
    if any(e.get('event')=='error' or e.get('detail',{}).get('event') in
           ('error','terminal_unknown','worker_exit_unconfirmed','cancel_requested','cancel_response','interrupted_terminal')
           for e in active):
        raise ValueError('Release predecessor contains an error or unconfirmed interruption')
    result=proof.get('trial.json',{}).get('result',{});goal=result.get('goal_id')
    try:
        if str(uuid.UUID(goal))!=goal or uuid.UUID(goal).int==0:raise ValueError('noncanonical')
    except (ValueError,TypeError,AttributeError):raise ValueError('Release predecessor UUID invalid')
    if type(result.get('request_id'))is not str or not result['request_id']:
        raise ValueError('Release predecessor request identity missing')
    info=proof_tools.validate_predecessor({name:proof[name] for name in FILES},profile,
        bundle_validator=builder,entry_builder=entry,pinned_bundle_id=bundle['manifest']['id'],pinned_goal_id=goal)
    journal=proof['trial.json'];journals=[e for e in active if e.get('event')=='trial']
    motion=[e for e in active if e.get('event')=='action' and e.get('kind')=='motion']
    ordered=[next(e for e in motion if e['detail']['event']==name)
             for name in ('dispatched','accepted','result','request_complete')]
    if not (journal['intent_ns']<=journals[0]['time_ns']<ordered[0]['time_ns']<ordered[1]['time_ns']<
            ordered[2]['time_ns']<ordered[3]['time_ns']<=journal['finished_ns']<=journals[-1]['time_ns']<active[-1]['time_ns']):
        raise ValueError('Release predecessor native/journal timestamps differ')
    if info['context']!=parent['context']:
        raise ValueError('Release predecessor changed boot/container/map/dependency context')
    return info,goal


def validate_predecessor(proof,profile,*,_depth=0):
    """Accept supported/settled -> relief only; at most five completed tasks."""
    if (_depth>1 or not isinstance(proof,dict) or set(proof)!=set(FILES)|{'predecessor.json'}):
        raise ValueError('Release predecessor requires its complete bounded proof chain')
    bundle=proof['bundle.json']
    phase=bundle.get('manifest',{}).get('phase') if isinstance(bundle,dict) else None
    if phase=='current_relative_lowering':
        bundle=lower.validate_bundle(bundle)
        predecessor_stage=bundle['review']['reference']['stage']
        if predecessor_stage not in ('support','settle'):
            raise ValueError('Release requires completed support or its one-centimetre settle')
        parent=lowering.validate_predecessor(proof['predecessor.json'],profile)
        expected_parent='precontact' if predecessor_stage=='support' else 'support'
        if parent['completed_stage']!=expected_parent:
            raise ValueError('Support/settle phase order differs from its authenticated predecessor')
        builder=lower.validate_bundle
    elif phase=='current_pin_release' and _depth==0:
        bundle=release.validate_bundle(bundle)
        if bundle['review']['reference']['stage']!='pin_relief':
            raise ValueError('Completed lateral opening cannot authorize another release')
        parent=validate_predecessor(proof['predecessor.json'],profile,_depth=1)
        builder=release.validate_bundle
    else:
        raise ValueError('Only completed support or its pin relief can precede release')
    ref=bundle['review']['reference']
    if ref['predecessor_bundle_id']!=parent['bundle_id'] or ref['predecessor_goal_id']!=parent['goal_id']:
        raise ValueError('Release predecessor reference identifies another action')
    info,goal=_completed_trial(proof,profile,bundle,builder,parent)
    chain=parent['chain_bundles']+[bundle]
    if len(chain)>5:raise ValueError('Release predecessor chain exceeds five completed tasks')
    info.update(predecessor_sha256=digest(proof),bundle_id=bundle['manifest']['id'],goal_id=goal,
        phase=phase,completed_stage=ref['stage'],chain_bundles=chain)
    info['planned']=lowering.entry_context(info['source'],info['predecessor_sha256'])
    return info


def validate_entry(proof,profile,bundle):
    info=validate_predecessor(proof,profile);bundle=release.validate_bundle(bundle)
    ref=bundle['review']['reference']
    expected=('support','settle') if ref['stage']=='pin_relief' else ('pin_relief',)
    if (info['completed_stage']not in expected or ref['predecessor_bundle_id']!=info['bundle_id'] or
            ref['predecessor_goal_id']!=info['goal_id']):
        raise ValueError('Release stage does not follow its authenticated predecessor')
    return info,bundle


def load_predecessor(directory,profile):
    directory=Path(directory)
    if (directory/'trial.json.consumed.json').exists():
        raise RuntimeError('Predecessor journal already consumed; no release retry')
    raw={name:(directory/name).read_bytes() for name in (*FILES,'predecessor.json')}
    if any(len(v)>16*1024*1024 for v in raw.values()) or sum(map(len,raw.values()))>32*1024*1024:
        raise ValueError('Release predecessor files exceed proof bounds')
    proof={name:([json.loads(line) for line in value.decode().splitlines() if line.strip()]
        if name=='events.jsonl' else json.loads(value)) for name,value in raw.items()}
    info=validate_predecessor(proof,profile)
    return proof,info,{name:hashlib.sha256(value).hexdigest() for name,value in raw.items()}


class ReleaseRuntime(lowering.LowerRuntime):
    def __init__(self,payload,emit=None):
        self.predecessor,self.trial_bundle=validate_entry(payload['predecessor'],payload['profile'],payload['trial_bundle'])
        info=self.predecessor
        if (payload.get('checkpoint')!=info['source'] or payload.get('resume_source_checkpoint')!=info['source'] or
                payload.get('resume_plan')!=info['planned'] or payload.get('resume_context')!=info['context'] or
                payload.get('cycle',False)is not False or payload.get('resume_options')is not None or
                payload.get('resume_pickup_reference')is not None):
            raise ValueError('Release technical context differs from its authenticated predecessor')
        base=dict(payload);base.pop('resume_plan',None);Runtime.__init__(self,base,emit)
        self.payload=payload;self.resume_plan=info['planned'];self.trial_record=None;self._trial_dispatch=False


def main(payload):return ReleaseRuntime(payload).run()


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
         'scenario1_table74_support','scenario1_table74_support_run','scenario1_table74_current_lower',
         'scenario1_table74_current_lower_run','scenario1_table74_current_release','scenario1_table74_current_release_run')]
    return payload


def connection_class(cli):return approach.connection_class(cli,bootstrap=BOOTSTRAP)


def parser():
    p=argparse.ArgumentParser(description=__doc__);m=p.add_mutually_exclusive_group()
    m.add_argument('--plan',action='store_true');m.add_argument('--check',action='store_true');m.add_argument('--run',action='store_true')
    p.add_argument('--after',type=Path,required=True);p.add_argument('--bundle',type=Path,required=True)
    p.add_argument('--profile',type=Path,default=Path(__file__).with_name('scenario1_table74_preparation.json'))
    p.add_argument('--evidence-dir',type=Path);p.add_argument('--wifi',action='store_true')
    return p


def cli_main(argv=None):
    from . import scenario1_table74_current_phase_cli as phase_cli
    args=parser().parse_args(argv);profile=json.loads(args.profile.read_text())
    proof,info,hashes=load_predecessor(args.after,profile)
    bundle=release.validate_bundle(json.loads(args.bundle.read_text()));info,bundle=validate_entry(proof,profile,bundle)
    ref=bundle['review']['reference']
    text=('Ensayo único '+('descenso de3cm para aliviar pines' if ref['stage']=='pin_relief' else
            'apertura lateral de10cm por lado con pines ya libres')+
          '. Confirme apoyo real estable de toda la caja, misma postura y agarre, holgura herramienta-tablero '
          'de almenos4cm, salida requerida de pines no mayor3cm, corredor lateral libre. Manos/cinta retiradas, '
          'cargador desconectado, paros liberados, otros mandos detenidos y persona junto al paro. '
          'Las confirmaciones son del operador; el resultado técnico no verifica apoyo ni pines libres.')
    return phase_cli.execute(args,profile,proof,info,hashes,bundle,make_payload=make_payload,
        load_predecessor=load_predecessor,validate_bundle=release.validate_bundle,connection_class=connection_class,
        confirmation_text=text,confirmation_token='LIBERAR74',evidence_tag='TABLE74_CURRENT_RELEASE',
        status_prefix='RELEASE',lock_reason='table74-current-release')


if __name__=='__main__':raise SystemExit(cli_main())
