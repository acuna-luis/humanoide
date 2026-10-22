#!/usr/bin/env python3
"""One supervised current table-74 approach; no ordinary deposit authorization.

The operator-assumed vendor-45 reference is not a measured hand calibration.
The source checkpoint/profile stay unchanged and retain their pending deposit.
This runner only sends the immutable approach task, never support, opening,
navigation, grasp, HOME or retry. Default --plan is entirely offline.
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

if __name__ == '__main__' and not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = 'scripts.box_handling'

if __package__:
    from . import scenario1_contract as contract
    from . import scenario1_table74_current_trial as trial
    from . import scenario1_table74_trial_run as approach
    from .scenario1_runtime import Runtime
else:
    import scenario1_contract as contract
    import scenario1_table74_current_trial as trial
    import scenario1_table74_trial_run as approach
    from scenario1_runtime import Runtime


STAGE = approach.STAGE
PROFILE_ID = 'scenario1_table74_preparation_v1'
PROFILE_SHA256 = '28dc98bbebf0ce1e8d18b0ad05bce42adcf3c01510dbba88d9d14daf928acc7c'
BOOTSTRAP = approach.BOOTSTRAP.replace("sys.modules['scenario1_table74_trial_run'].main(payload)",
                                    "sys.modules['scenario1_table74_current_trial_run'].main(payload)")


def validate_bundle(bundle):
    checked = trial.validate_bundle(bundle)
    if checked['manifest']['phase'] != 'approach_vendor_reference':
        raise ValueError('Current trial requires the vendor-reference approach phase')
    return checked


def prepare_entry(source, profile, bundle):
    """Build non-executable context; never promote the pending deposit profile."""
    source = contract.validate_checkpoint(source, profile)
    if (source['profile_id'] != PROFILE_ID or source['profile_sha256'] != PROFILE_SHA256 or
            source['stop_after'] != 'navigate_put1' or source['in_flight'] is not None or
            source['failure'] is not None or source['box_state'] != 'held' or
            not source['completed'] or source['completed'][-1] != 'navigate_put1' or
            contract.progress_index(source) != contract.STAGES.index('deposit') or
            source.get('policy') != 'assume' or contract.execution_profile(source) != 'optimistic_v1'):
        raise ValueError('Current trial requires the exact pending table74 profile and clean optimistic held put1 boundary')
    bundle = validate_bundle(bundle)
    digest = hashlib.sha256(json.dumps(source, sort_keys=True, separators=(',', ':'),
                                      allow_nan=False).encode()).hexdigest()
    if bundle['review']['reference']['source_checkpoint_sha256'] != digest:
        raise ValueError('Current trial reference belongs to another source checkpoint')
    planned = dict(artifact='table74_current_trial_context', executable=False,
        checkpoint=copy.deepcopy(source), stage=STAGE, source_sha256=digest,
        requirements=dict(box_state='held', home=False, waypoint='put1', vision_prep=False))
    return source, planned


class CurrentTrialRuntime(approach.TrialRuntime):
    def __init__(self, payload, emit=None):
        self.trial_bundle = validate_bundle(payload['trial_bundle'])
        source, planned = prepare_entry(payload['resume_source_checkpoint'], payload['profile'], self.trial_bundle)
        if (payload.get('checkpoint') != source or payload.get('resume_plan') != planned or
                payload.get('cycle', False) is not False or payload.get('resume_pickup_reference') is not None or
                payload.get('resume_options') is not None):
            raise ValueError('Current trial source/context changed or ordinary resume options supplied')
        # Runtime's ordinary resume planner would authorize a complete scenario.
        # Initialize against the original pending checkpoint, then attach only
        # our non-executable, task-specific read-only entry requirements.
        base = dict(payload)
        base.pop('resume_plan', None)
        Runtime.__init__(self, base, emit)
        self.payload = payload
        self.resume_plan = planned
        self.trial_record = None
        self._trial_dispatch = False


def main(payload):
    return CurrentTrialRuntime(payload).run()


def make_payload(mode, profile, source, bundle):
    cli = approach.local_cli()
    source, planned = prepare_entry(source, profile, bundle)
    payload = cli.make_payload(mode, profile, source)
    payload.update(policy='assume', execution_profile='optimistic_v1', cycle=False,
                   box_alignment_attempts=0, resume_source_checkpoint=source,
                   resume_plan=planned, trial_bundle=validate_bundle(bundle))
    here = Path(__file__).resolve().parent
    payload['modules'] += [(name, (here/(name+'.py')).read_text()) for name in
        ('scenario1_deposit', 'scenario1_table74_recipe', 'scenario1_table74_native_completion', 'scenario1_table74_trial', 'scenario1_table74_trial_run',
         'scenario1_table74_current_trial', 'scenario1_table74_current_trial_run')]
    return payload


def connection_class(cli):
    return approach.connection_class(cli, bootstrap=BOOTSTRAP)


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    mode = result.add_mutually_exclusive_group()
    mode.add_argument('--plan', action='store_true', help='Offline default')
    mode.add_argument('--check', action='store_true', help='Read-only technical preflight')
    mode.add_argument('--run', action='store_true', help='One supervised approach only')
    result.add_argument('--resume', type=Path, required=True)
    result.add_argument('--bundle', type=Path, required=True)
    result.add_argument('--profile', type=Path, default=Path(__file__).with_name('scenario1_table74_preparation.json'))
    result.add_argument('--evidence-dir', type=Path)
    result.add_argument('--wifi', action='store_true')
    return result


def cli_main(argv=None, *, execution_policy=None):
    if execution_policy is not None:
        from .scenario1_table74_recipe import assert_policy
        assert_policy(execution_policy)
    cli = approach.local_cli()
    args = parser().parse_args(argv)
    source_bytes = args.resume.read_bytes()
    if args.resume.with_name(args.resume.name+'.consumed.json').exists():
        raise RuntimeError('Source checkpoint already consumed; trial repetition is forbidden')
    profile = json.loads(args.profile.read_text())
    bundle = validate_bundle(json.loads(args.bundle.read_text()))
    source, planned = prepare_entry(json.loads(source_bytes), profile, bundle)
    if not args.run and not args.check:
        print(json.dumps(dict(mode='plan', stage=STAGE, task_name=bundle['task_name'],
            source_sha256=planned['source_sha256'], context=planned, review=bundle['review'],
            commands_sent=0, source_consumed=False, automatic_retries=0,
            ordinary_deposit_authorized=False), indent=2, ensure_ascii=False))
        return 0
    if args.run and execution_policy is None and not sys.stdin.isatty():
        raise RuntimeError('A physical operator and TTY confirmation are required')
    source_context_bytes = (args.resume.parent/'context.json').read_bytes()
    context = json.loads(source_context_bytes)
    payload = make_payload('run' if args.run else 'check', profile, source, bundle)
    if execution_policy is not None:
        payload['recipe_provenance'] = execution_policy.as_dict()
    payload['resume_context'] = context
    evidence = args.evidence_dir or cli.ROOT.parent/'Humanoide-vla-evidence'/(
        time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())+'_TABLE74_CURRENT_APPROACH_'+str(os.getpid()))
    evidence.mkdir(parents=True, exist_ok=False)
    os.chmod(evidence, 0o700)
    cli.atomic_json(evidence/'source-context.json', approach.context_record(source))
    cli.atomic_json(evidence/'bundle.json', bundle)
    cli.atomic_json(evidence/'source-sha256.json', {name: hashlib.sha256(code.encode()).hexdigest()
        for name, code in payload['modules']} | {name: hashlib.sha256(payload[name].encode()).hexdigest()
        for name in ('action_client', 'health_worker', 'resume_worker', 'perception_guard', 'sensor_worker')})
    print('Evidencia: '+str(evidence), flush=True)
    from contextlib import ExitStack
    import fcntl
    connection = None
    with ExitStack() as stack:
        for path in ('/tmp/cruzr_blue_workbin_cycle.lock', '/tmp/cruzr-improved-scenario1.lock'):
            lock = stack.enter_context(open(path, 'a'))
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            connection = connection_class(cli)(payload, args.wifi, evidence)
            ready = connection.wait('ready')
            cli.atomic_json(evidence/'context.json', ready['context'])
            if args.check:
                if connection.process.wait(timeout=15) != 0:
                    raise RuntimeError('Current approach technical check failed')
                print('CURRENT_TRIAL_CHECK_OK; source unchanged, no motion sent.')
                return 0
            if execution_policy is not None:
                execution_policy.authorize('APROXIMAR74', evidence)
            else:
                cli.confirm('Ensayo único mesa74 desde la caja actualmente sujeta en put1. '
                'Se usa la referencia vendor45 asumida por el operador, sin calibración medida de manos. '
                'Compruebe estabilidad, trayectoria completa de brazos/torso/caja y avance de20cm despejados; '
                'cargador desconectado, paros liberados, ruedas en navegación, modo automático, '
                'otros mandos detenidos y persona junto al paro. No confirma apoyo ni abre abrazaderas.', 'APROXIMAR74')
            def unchanged():
                if (args.resume.read_bytes() != source_bytes or
                        (args.resume.parent/'context.json').read_bytes() != source_context_bytes or
                        validate_bundle(json.loads(args.bundle.read_text())) != bundle):
                    raise RuntimeError('Current trial source, context or bundle changed after preflight')
            unchanged()
            # Runtime's existing message only refreshes entry health/arrival;
            # no plan_resume call, new checkpoint or physical task occurs here.
            connection.send({'command': 'resume', 'stop_after': source['stop_after']})
            if connection.wait('resume_ready')['checkpoint'] != source:
                raise RuntimeError('Current trial entry context changed')
            unchanged()
            subprocess.run(['bash', str(cli.ROOT/'scripts/lib/cruzr_contact_motion_lock.sh'),
                            'table74-current-approach'], check=True, start_new_session=True)
            cli.atomic_json(evidence/'trial-intent.json', dict(artifact='table74_current_trial_intent',
                source_sha256=planned['source_sha256'], bundle_id=bundle['manifest']['id'],
                phase='pending', automatic_retry=False, time_ns=time.time_ns()))
            cli.claim_resume(args.resume, evidence/'trial.json')
            connection.send({'command': 'arm'})
            connection.wait('armed')
            connection.send({'command': 'stage', 'stage': STAGE})
            if connection.wait('stage_complete', timeout=120).get('stage') != STAGE:
                raise RuntimeError('Unexpected current approach completion')
            journal = approach.validate_journal(json.loads((evidence/'trial.json').read_text()),
                                                bundle['manifest']['id'], planned['source_sha256'])
            if journal['phase'] != 'succeeded':
                raise RuntimeError('Current approach lacks its confirmed terminal result')
            cli.finish_connection(connection)
            print('CURRENT_APPROACH_COMPLETED; caja sujeta, apoyo y desenganche pendientes; sin apertura ni HOME.')
            return 0
        finally:
            if connection:
                connection.close()


if __name__ == '__main__':
    raise SystemExit(cli_main())
