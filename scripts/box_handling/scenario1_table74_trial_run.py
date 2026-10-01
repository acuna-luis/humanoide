#!/usr/bin/env python3
"""One supervised table-74 approach from a clean held-box put1 checkpoint.

Default --plan is offline. --check retains the ordinary read-only preflight.
--run consumes the source checkpoint and sends one immutable approach task.
No opening, final lowering, HOME, navigation goal or automatic retry exists.
Successful action completion does not establish support or physical clearance.
"""
import argparse
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import queue
import shlex
import subprocess
import sys
import threading
import time

if __name__ == '__main__' and not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = 'scripts.box_handling'

if __package__:
    from . import scenario1_contract as contract, scenario1_resume as resume
    from . import scenario1_table74_trial as trial
    from .scenario1_runtime import Runtime, atomic_json, code_command
else:
    import scenario1_contract as contract
    import scenario1_resume as resume
    import scenario1_table74_trial as trial
    from scenario1_runtime import Runtime, atomic_json, code_command


STAGE = 'approach_trial'
TIMEOUT = 45
BOOTSTRAP = '''import json,sys,types
payload=json.loads(sys.stdin.readline())
for name,source in payload.pop('modules'):
 module=types.ModuleType(name);sys.modules[name]=module
 exec(compile(source,name+'.py','exec'),module.__dict__)
raise SystemExit(sys.modules['scenario1_table74_trial_run'].main(payload))
'''


def validate_bundle(bundle):
    bundle = trial.validate_bundle(bundle)
    reference = bundle['review']['reference']
    if (reference['box_bottom_above_floor_m'] != 1.10 or
            bundle['review']['first_hand_delta_z_m'] != -.31 or
            bundle['review']['nominal_target_box_bottom_above_floor_m'] != .79):
        raise ValueError('Trial runner requires the measured 1.10 m reference and 0.31 m approach')
    return bundle


def prepare_entry(source, profile):
    source = contract.validate_checkpoint(source, profile)
    if (source['in_flight'] is not None or source['failure'] is not None or
            source['box_state'] != 'held' or not source['completed'] or
            source['completed'][-1] != 'navigate_put1' or
            source.get('policy') != 'assume' or
            contract.execution_profile(source) != 'optimistic_v1'):
        raise ValueError('Trial requires a clean optimistic held-box checkpoint immediately after put1')
    options = dict(policy='assume', execution_profile='optimistic_v1', stop_after='verify_home')
    planned = resume.plan_resume(source, profile, **options)
    if planned['stage'] != 'deposit' or planned['requirements']['waypoint'] != 'put1':
        raise ValueError('Trial entry must retain the ordinary deposit entry checks')
    return source, options, planned


def context_record(checkpoint):
    return dict(artifact='table74_trial_context_only', executable=False,
                checkpoint=copy.deepcopy(checkpoint))


def validate_journal(record, bundle_id, source_sha256):
    fields = {'artifact', 'version', 'bundle_id', 'source_sha256', 'phase', 'intent_ns',
              'finished_ns', 'result', 'error', 'physical_support_confirmed', 'automatic_retry'}
    if (not isinstance(record, dict) or set(record) != fields or
            record['artifact'] != 'table74_approach_trial' or type(record['version']) is not int or
            record['version'] != 1 or record['bundle_id'] != bundle_id or
            record['source_sha256'] != source_sha256 or record['physical_support_confirmed'] is not False or
            record['automatic_retry'] is not False or type(record['intent_ns']) is not int or record['intent_ns'] <= 0):
        raise ValueError('Malformed trial journal identity')
    json.dumps(record, allow_nan=False)
    if record['phase'] == 'pending':
        if any(record[key] is not None for key in ('finished_ns', 'result', 'error')):
            raise ValueError('Malformed pending trial')
    elif record['phase'] in ('succeeded', 'failed'):
        if type(record['finished_ns']) is not int or record['finished_ns'] < record['intent_ns']:
            raise ValueError('Malformed trial completion timestamp')
        if record['phase'] == 'succeeded':
            contract.validate_motion_result(record['result'])
            if record['error'] is not None or not isinstance(record['result'].get('goal_id'), str) or not record['result']['goal_id']:
                raise ValueError('Unidentified successful trial result')
        elif not isinstance(record['error'], str) or not record['error']:
            raise ValueError('Missing trial failure reason')
    else:
        raise ValueError('Unknown trial phase')
    return copy.deepcopy(record)


class TrialRuntime(Runtime):
    """Keep the existing safety machinery; authorize only this extra task."""
    def __init__(self, payload, emit=None):
        self.trial_bundle = validate_bundle(payload['trial_bundle'])
        source, options, planned = prepare_entry(payload['resume_source_checkpoint'], payload['profile'])
        if (payload.get('resume_plan') != planned or payload.get('resume_options') != options or
                payload.get('checkpoint') != planned['checkpoint'] or payload.get('cycle', False) is not False):
            raise ValueError('Trial source or entry plan changed')
        super().__init__(payload, emit)
        self.trial_record = None
        self._trial_dispatch = False

    def save(self):
        record = context_record(self.checkpoint)
        atomic_json(self.session/'context-checkpoint.json', record)
        self.emit('scenario_context', context=record)

    def verify_trial_files(self):
        self.connected()
        expected = self.trial_bundle['manifest']['robot_files']
        code = '''import hashlib,json,pathlib,sys
paths=json.loads(sys.argv[1])
print(json.dumps({p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() for p in paths},sort_keys=True))
'''
        observed = json.loads(self.native(code_command(code, [json.dumps(list(expected))]), timeout=20))
        if observed != expected:
            raise RuntimeError('TRIAL_FILES_CHANGED: task, parameters or pinned dependencies differ')
        self.emit('trial_dependencies', bundle_id=self.trial_bundle['manifest']['id'], hashes=observed)

    def hashes(self):
        super().hashes()
        self.verify_trial_files()

    def action(self, kind, goal, timeout, *, correction=None, allow_home_retry=False):
        query = (kind == 'navigation' and isinstance(goal, dict) and
                 set(goal) == {'command', 'arg_json'} and
                 goal['command'] in ('get_map_name', 'check_state') and goal['arg_json'] == '{}')
        approach = (self._trial_dispatch and self.armed and kind == 'motion' and
                    goal == {'task_name': self.trial_bundle['task_name'], 'yaml_args': '{}'} and
                    self.trial_record is not None and self.trial_record['phase'] == 'pending')
        if correction is not None or allow_home_retry is not False or not (query or approach):
            raise RuntimeError('TRIAL_ACTION_NOT_AUTHORIZED')
        return super().action(kind, goal, timeout)

    def save_trial(self):
        validate_journal(self.trial_record, self.trial_bundle['manifest']['id'], self.resume_plan['source_sha256'])
        atomic_json(self.session/'trial.json', self.trial_record)
        self.emit('trial', trial=copy.deepcopy(self.trial_record))

    def stage(self, message):
        if message != {'command': 'stage', 'stage': STAGE}:
            raise RuntimeError('TRIAL_STAGE_NOT_AUTHORIZED')
        if not self.armed or not self.resume_validated or self.session is None:
            raise RuntimeError('TRIAL_NOT_ARMED')
        if self.trial_record is not None or (self.session/'trial.json').exists():
            raise RuntimeError('TRIAL_ALREADY_ATTEMPTED: physical review required; no retry')
        self.trial_record = dict(artifact='table74_approach_trial', version=1,
            bundle_id=self.trial_bundle['manifest']['id'], source_sha256=self.resume_plan['source_sha256'],
            phase='pending', intent_ns=time.time_ns(), finished_ns=None, result=None, error=None,
            physical_support_confirmed=False, automatic_retry=False)
        self.save_trial()  # Durable intent before gates and before any dispatch.
        started = time.monotonic()
        try:
            self.connected()
            self.timed('trial_containers', self.discover)
            self.timed('trial_dependencies', self.hashes)
            self.timed('trial_health', self.health, require_home=False)
            self.check_resume_entry()
            self.timed('trial_stationary', self.quick_health)
            self.verify_trial_files()
            self.connected()
            self._trial_dispatch = True
            try:
                result = self.action('motion', {'task_name': self.trial_bundle['task_name'], 'yaml_args': '{}'}, TIMEOUT)
            finally:
                self._trial_dispatch = False
            self.trial_record['result'] = copy.deepcopy(result)
            contract.validate_motion_result(result)
            self.connected()
            self.timed('trial_post_stationary', self.quick_health)
            self.trial_record.update(phase='succeeded', finished_ns=time.time_ns())
            self.save_trial()
            self.emit('stage_complete', stage=STAGE, elapsed_s=round(time.monotonic()-started, 3),
                      physical_support_confirmed=False)
        except BaseException as exc:
            self._trial_dispatch = False
            self.trial_record.update(phase='failed', finished_ns=time.time_ns(), error=str(exc) or type(exc).__name__)
            self.save_trial()
            raise


def main(payload):
    return TrialRuntime(payload).run()


def local_cli():
    if __package__:
        from . import scenario1_cli
    else:
        import scenario1_cli
    return scenario1_cli


def make_payload(mode, profile, source, bundle):
    cli = local_cli()
    source, options, planned = prepare_entry(source, profile)
    payload = cli.make_payload(mode, profile, planned['checkpoint'])
    payload.update(policy='assume', execution_profile='optimistic_v1', cycle=False,
                   resume_source_checkpoint=source, resume_options=options,
                   resume_plan=planned, trial_bundle=validate_bundle(bundle))
    here = Path(__file__).resolve().parent
    payload['modules'] += [(name, (here/(name+'.py')).read_text()) for name in
        ('scenario1_deposit', 'scenario1_table74_trial', 'scenario1_table74_trial_run')]
    return payload


def connection_class(cli):
    class TrialConnection(cli.Connection):
        def __init__(self, payload, wifi, evidence, *, console=None):
            self.evidence = evidence
            self.bundle_id = payload['trial_bundle']['manifest']['id']
            self.source_sha256 = payload['resume_plan']['source_sha256']
            self.console = console if console is not None else cli.ConsoleReporter()
            self.events = queue.Queue()
            self.write_lock = threading.Lock()
            self.closed = threading.Event()
            env = dict(os.environ, CRUZR_INTERNAL_ASKPASS='1',
                SSH_ASKPASS=str(cli.ROOT/'scripts/cruzr_recover_to_home.sh'),
                SSH_ASKPASS_REQUIRE='force', DISPLAY=os.environ.get('DISPLAY', ':0'))
            command = cli.ssh_command(wifi)
            code = 'import base64;exec(base64.b64decode(%r))' % base64.b64encode(BOOTSTRAP.encode()).decode()
            command[-1] = shlex.join(['python3', '-u', '-B', '-c', code])
            self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, env=env, start_new_session=True, bufsize=1)
            self.send(payload)
            self.threads = [threading.Thread(target=self.read, daemon=True),
                            threading.Thread(target=self.errors, daemon=True),
                            threading.Thread(target=self.heartbeat, daemon=True)]
            for thread in self.threads:
                thread.start()

        def read(self):
            try:
                with (self.evidence/'events.jsonl').open('a') as log:
                    for line in self.process.stdout:
                        log.write(line)
                        log.flush()
                        try:
                            event = json.loads(line)
                            if not isinstance(event, dict) or not isinstance(event.get('event'), str):
                                raise ValueError('Malformed trial event')
                            if event['event'] == 'checkpoint':
                                raise ValueError('Trial must not publish an executable scenario checkpoint')
                            if event['event'] == 'scenario_context':
                                record = event['context']
                                if record != context_record(contract.validate_checkpoint(record['checkpoint'])):
                                    raise ValueError('Malformed non-executable context')
                                cli.atomic_json(self.evidence/'context-checkpoint.json', record)
                            if event['event'] == 'trial':
                                record = validate_journal(event['trial'], self.bundle_id, self.source_sha256)
                                cli.atomic_json(self.evidence/'trial.json', record)
                            self.present(event)
                            self.events.put(event)
                        except (ValueError, KeyError, TypeError) as exc:
                            error = dict(event='error', reason='Trial protocol: '+str(exc))
                            self.present(error)
                            self.events.put(error)
            finally:
                self.events.put(dict(event='eof'))
    return TrialConnection


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    mode = result.add_mutually_exclusive_group()
    mode.add_argument('--plan', action='store_true', help='Plan offline; default')
    mode.add_argument('--check', action='store_true', help='Read-only technical checks')
    mode.add_argument('--run', action='store_true', help='One approach after a physical confirmation token')
    result.add_argument('--resume', type=Path, required=True, help='Clean held-box checkpoint after put1')
    result.add_argument('--bundle', type=Path, required=True, help='Immutable approach bundle.json')
    result.add_argument('--profile', type=Path, default=Path(__file__).with_name('scenario1_current_geometry.json'))
    result.add_argument('--evidence-dir', type=Path)
    result.add_argument('--wifi', action='store_true')
    return result


def cli_main(argv=None):
    cli = local_cli()
    args = parser().parse_args(argv)
    source_bytes = args.resume.read_bytes()
    if args.resume.with_name(args.resume.name+'.consumed.json').exists():
        raise RuntimeError('Source checkpoint already consumed; trial repetition is forbidden')
    profile = json.loads(args.profile.read_text())
    source, options, planned = prepare_entry(json.loads(source_bytes), profile)
    bundle = validate_bundle(json.loads(args.bundle.read_text()))
    if not args.run and not args.check:
        print(json.dumps(dict(mode='plan', stage=STAGE, task_name=bundle['task_name'],
            source_sha256=planned['source_sha256'], resume=planned, review=bundle['review'],
            commands_sent=0, source_consumed=False, automatic_retries=0), indent=2, ensure_ascii=False))
        return 0
    if args.run and not sys.stdin.isatty():
        raise RuntimeError('A physical operator and TTY confirmation are required')
    context = json.loads((args.resume.parent/'context.json').read_text())
    payload = make_payload('run' if args.run else 'check', profile, source, bundle)
    payload['resume_context'] = context
    evidence = args.evidence_dir or cli.ROOT.parent/'Humanoide-vla-evidence'/(
        time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())+'_TABLE74_APPROACH_TRIAL_'+str(os.getpid()))
    evidence.mkdir(parents=True, exist_ok=False)
    os.chmod(evidence, 0o700)
    cli.atomic_json(evidence/'source-context.json', context_record(source))
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
                    raise RuntimeError('Trial technical check failed')
                print('TRIAL_CHECK_OK; source unchanged, no approach sent.')
                return 0
            cli.confirm('Ensayo único: misma caja sujeta y postura de la medida de base 1,10 m; '
                'mesa de 0,74 m, referencia conservada tras transporte, en put1. '
                'Cinta métrica y manos retiradas del robot, de la caja y de todo el recorrido. '
                'Compruebe montaje, estabilidad, recorrido completo libre de manos/caja/cuerpo y '
                'avance de 20 cm; batería suficiente, cargador desconectado, paros liberados, '
                'ruedas en navegación, modo automático, ningún otro mando y persona junto al paro. '
                'La aproximación nominal termina 5 cm sobre la mesa; no confirma apoyo ni abre abrazaderas.', 'APROXIMAR')
            if args.resume.read_bytes() != source_bytes or validate_bundle(json.loads(args.bundle.read_text())) != bundle:
                raise RuntimeError('Trial source or bundle changed after preflight')
            connection.send({'command': 'resume', 'stop_after': 'verify_home'})
            received = connection.wait('resume_ready')['checkpoint']
            if received != planned['checkpoint']:
                raise RuntimeError('Trial resume context changed')
            subprocess.run(['bash', str(cli.ROOT/'scripts/lib/cruzr_contact_motion_lock.sh'),
                            'table74-approach-trial'], check=True, start_new_session=True)
            cli.atomic_json(evidence/'trial-intent.json', dict(artifact='table74_trial_intent',
                source_sha256=planned['source_sha256'], bundle_id=bundle['manifest']['id'],
                phase='pending', automatic_retry=False, time_ns=time.time_ns()))
            cli.claim_resume(args.resume, evidence/'trial.json')
            connection.send({'command': 'arm'})
            connection.wait('armed')
            connection.send({'command': 'stage', 'stage': STAGE})
            completed = connection.wait('stage_complete', timeout=120)
            if completed.get('stage') != STAGE:
                raise RuntimeError('Unexpected trial completion')
            journal = validate_journal(json.loads((evidence/'trial.json').read_text()),
                                       bundle['manifest']['id'], planned['source_sha256'])
            if journal['phase'] != 'succeeded':
                raise RuntimeError('Trial completion lacks its confirmed terminal result')
            cli.finish_connection(connection)
            print('APPROACH_COMPLETED; caja aún sujeta, apoyo y separación pendientes de comprobación física. '
                  'Sin apertura ni HOME; no repetir desde esta posición.')
            return 0
        finally:
            if connection:
                connection.close()


if __name__ == '__main__':
    raise SystemExit(cli_main())
