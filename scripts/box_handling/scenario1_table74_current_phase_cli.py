"""PC-only one-shot trial IO, with explicit phase validators and transports.

No robot connection exists until a caller selects --check or --run. The phase
runner supplies its bounded predecessor validator, immutable bundle validator,
payload and connection classes. This helper never constructs ordinary plans.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def execute(args, profile, proof, info, hashes, bundle, *, make_payload,
            load_predecessor, validate_bundle, connection_class, confirmation_text,
            confirmation_token, evidence_tag, status_prefix, lock_reason):
    from . import scenario1_table74_trial_run as approach
    cli=approach.local_cli()
    if not args.run and not args.check:
        print(json.dumps(dict(mode='plan',stage=approach.STAGE,task_name=bundle['task_name'],
            context=info['planned'],review=bundle['review'],predecessor_sha256=info['predecessor_sha256'],
            commands_sent=0,predecessor_consumed=False,automatic_retries=0,ordinary_deposit_authorized=False),
            indent=2,ensure_ascii=False))
        return 0
    if args.run and not sys.stdin.isatty():
        raise RuntimeError('A physical operator and TTY confirmation are required')
    payload=make_payload('run' if args.run else 'check',profile,proof,bundle)
    evidence=args.evidence_dir or cli.ROOT.parent/'Humanoide-vla-evidence'/(
        time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'_'+evidence_tag+'_'+str(os.getpid()))
    evidence.mkdir(parents=True,exist_ok=False);os.chmod(evidence,0o700)
    for name,value in (('source-context.json',approach.context_record(info['source'])),
                       ('predecessor.json',proof),('bundle.json',bundle)):
        cli.atomic_json(evidence/name,value)
    cli.atomic_json(evidence/'source-sha256.json',{name:hashlib.sha256(code.encode()).hexdigest()
        for name,code in payload['modules']}|{name:hashlib.sha256(payload[name].encode()).hexdigest()
        for name in ('action_client','health_worker','resume_worker','perception_guard','sensor_worker')}|
        {'phase_cli':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
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
                if connection.process.wait(timeout=15)!=0:
                    raise RuntimeError(status_prefix+' technical check failed')
                print(status_prefix+'_CHECK_OK; predecessor unchanged, no motion sent.')
                return 0
            cli.confirm(confirmation_text,confirmation_token)
            def unchanged():
                new,_,fresh=load_predecessor(args.after,profile)
                if new!=proof or fresh!=hashes or validate_bundle(json.loads(args.bundle.read_text()))!=bundle:
                    raise RuntimeError('Phase source proof or bundle changed after preflight')
            unchanged()
            connection.send({'command':'resume','stop_after':info['source']['stop_after']})
            if connection.wait('resume_ready')['checkpoint']!=info['source']:
                raise RuntimeError('Phase entry context changed')
            unchanged()
            subprocess.run(['bash',str(cli.ROOT/'scripts/lib/cruzr_contact_motion_lock.sh'),lock_reason],
                           check=True,start_new_session=True)
            cli.atomic_json(evidence/'trial-intent.json',dict(artifact='table74_current_phase_intent',
                predecessor_sha256=info['predecessor_sha256'],bundle_id=bundle['manifest']['id'],
                phase='pending',automatic_retry=False,time_ns=time.time_ns()))
            cli.claim_resume(args.after/'trial.json',evidence/'trial.json')
            connection.send({'command':'arm'});connection.wait('armed')
            connection.send({'command':'stage','stage':approach.STAGE})
            if connection.wait('stage_complete',timeout=120).get('stage')!=approach.STAGE:
                raise RuntimeError('Unexpected phase completion')
            journal=approach.validate_journal(json.loads((evidence/'trial.json').read_text()),
                bundle['manifest']['id'],info['predecessor_sha256'])
            if journal['phase']!='succeeded':
                raise RuntimeError('Phase lacks its confirmed successful terminal result')
            cli.finish_connection(connection)
            print(status_prefix+'_COMPLETED; comprobar estado físico antes de continuar; sin HOME ni reintento.')
            return 0
        finally:
            if connection:connection.close()
