#!/usr/bin/env python3
"""One supervised 5 cm support trial after the pinned successful approach.

Authorization comes from the approach journal, never from reusing its consumed
scenario checkpoint. Default --plan is offline. There is no opening, navigation
goal, HOME, disengagement or retry. SUCCEED alone does not prove physical support.
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
    from . import scenario1_contract as contract
    from . import scenario1_table74_trial_run as approach
    from . import scenario1_table74_support as support
    from .scenario1_runtime import Runtime, atomic_json, code_command
else:
    import scenario1_contract as contract
    import scenario1_table74_trial_run as approach
    import scenario1_table74_support as support
    from scenario1_runtime import Runtime, atomic_json, code_command


STAGE = 'support_trial'
TIMEOUT = 45
FILES = ('bundle.json', 'trial.json', 'source-context.json', 'context-checkpoint.json', 'context.json', 'events.jsonl')
BOOTSTRAP = approach.BOOTSTRAP.replace("sys.modules['scenario1_table74_trial_run'].main(payload)",
                                       "sys.modules['scenario1_table74_support_run'].main(payload)")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def validate_shutdown_tail(events):
    """Only known idle worker closures may follow the finished approach."""
    states = {}
    for event in events:
        name = event.get('event')
        kind = event.get('kind') if name == 'action' else 'health_worker' if name == 'health_worker' else None
        detail = event.get('detail')
        if kind not in ('motion', 'navigation', 'health_worker') or not isinstance(detail, dict):
            raise ValueError('Unexpected activity after approach session finish')
        if detail.get('event') == 'error':
            reason = ('RuntimeError: Health worker lease expired or stop requested' if kind == 'health_worker'
                      else 'Lease missing, invalid or expired')
            if (kind in states or 'request_id' not in detail or detail['request_id'] is not None or
                    detail.get('goal_id') is not None or
                    kind != 'health_worker' and 'goal_id' not in detail or detail.get('reason') != reason or
                    set(detail) - {'event', 'request_id', 'goal_id', 'reason', 'time_ns'}):
                raise ValueError('Non-idle or unknown failure after approach session finish')
            states[kind] = 'idle_error'
        elif detail.get('event') == 'worker_closed':
            expected = (78 if kind == 'health_worker' else 2) if states.get(kind) == 'idle_error' else 0
            if (states.get(kind) == 'closed' or type(detail.get('returncode')) is not int or
                    detail['returncode'] != expected or detail.get('physical_stop_verified') is not False or
                    set(detail) - {'event', 'returncode', 'physical_stop_verified', 'time_ns'}):
                raise ValueError('Unconfirmed worker closure after approach session finish')
            states[kind] = 'closed'
        else:
            raise ValueError('Executable or unknown event after approach session finish')
    if any(state != 'closed' for state in states.values()):
        raise ValueError('Approach shutdown evidence is incomplete')


def validate_predecessor(proof, profile):
    """Verify the exact successful approach and its non-executable context."""
    if not isinstance(proof, dict) or set(proof) != set(FILES):
        raise ValueError('Incomplete approach predecessor evidence')
    bundle = approach.validate_bundle(proof['bundle.json'])
    if bundle['manifest']['id'] != support.PINNED_APPROACH_BUNDLE_ID:
        raise ValueError('Support trial requires the pinned approach bundle')
    source_record = proof['source-context.json']
    source, options, planned = approach.prepare_entry(source_record.get('checkpoint'), profile)
    if source_record != approach.context_record(source):
        raise ValueError('Malformed approach source context')
    if proof['context-checkpoint.json'] != approach.context_record(planned['checkpoint']):
        raise ValueError('Approach technical checkpoint does not match its source')
    journal = approach.validate_journal(proof['trial.json'], bundle['manifest']['id'], planned['source_sha256'])
    if journal['phase'] != 'succeeded' or journal['result']['goal_id'] != support.PINNED_APPROACH_GOAL_ID:
        raise ValueError('The pinned approach must have a confirmed successful result')
    context = proof['context.json']
    if (not isinstance(context, dict) or set(context) != {'boot_id', 'containers', 'dependencies', 'points', 'execution_profile'}
            or context.get('execution_profile') != 'optimistic_v1'):
        raise ValueError('Missing approach runtime context')
    events = proof['events.jsonl']
    if not isinstance(events, list) or any(not isinstance(e, dict) for e in events):
        raise ValueError('Malformed approach event log')
    finishes = [i for i, e in enumerate(events) if e.get('event') == 'session_finishing' and e.get('reason') == 'requested']
    if len(finishes) != 1:
        raise ValueError('Approach session did not close at a confirmed boundary')
    validate_shutdown_tail(events[finishes[0]+1:])
    active = events[:finishes[0]]
    if any(e.get('event') == 'error' for e in active):
        raise ValueError('Approach contains a supervisor failure')
    ready = [e for e in active if e.get('event') == 'ready']
    stages = [e for e in active if e.get('event') == 'stage_complete']
    journals = [e.get('trial') for e in active if e.get('event') == 'trial']
    if (len(ready) != 1 or ready[0].get('context') != context or len(stages) != 1 or
            stages[0].get('stage') != approach.STAGE or len(journals) != 2 or
            journals[-1] != journal or journals[0].get('phase') != 'pending'):
        raise ValueError('Approach completion, context or journal is ambiguous')
    approach.validate_journal(journals[0], bundle['manifest']['id'], planned['source_sha256'])
    if journals[0]['intent_ns'] != journal['intent_ns']:
        raise ValueError('Approach has more than one intent')
    if not (active.index(next(e for e in active if e.get('event') == 'trial')) <
            active.index(next(e for e in active if e.get('event') == 'trial' and e.get('trial') == journal)) <
            active.index(stages[0])):
        raise ValueError('Approach journal ordering is invalid')
    motion_events = [e for e in active if e.get('event') == 'action' and e.get('kind') == 'motion']
    rows = [e.get('detail') for e in motion_events]
    startup = {'session_ready', 'native_api', 'worker_log'}
    allowed = {'dispatched', 'status', 'accepted', 'feedback', 'result_pending', 'result', 'request_complete'} | startup
    if any(not isinstance(row, dict) or row.get('event') not in allowed for row in rows):
        raise ValueError('Approach action contains an interruption or unknown outcome')
    first_dispatch = next((i for i, r in enumerate(rows) if r['event'] == 'dispatched'), -1)
    if first_dispatch < 0 or any(r['event'] in startup for r in rows[first_dispatch:]):
        raise ValueError('Unexpected action startup after dispatch')
    rows = [r for r in rows if r['event'] not in startup]
    uid, rid = journal['result']['goal_id'], journal['result']['request_id']
    if any(r.get('request_id') != rid or (r['event'] != 'request_complete' and r.get('goal_id') != uid) for r in rows):
        raise ValueError('Approach action identity is not unique')
    by_name = {name: [r for r in rows if r['event'] == name] for name in ('dispatched', 'accepted', 'result', 'request_complete')}
    if (any(len(v) != 1 for v in by_name.values()) or by_name['accepted'][0].get('accepted') is not True or
            by_name['dispatched'][0].get('endpoint') != '/mc/manipulation/action' or
            by_name['result'][0] != journal['result'] or
            type(by_name['request_complete'][0].get('returncode')) is not int or
            by_name['request_complete'][0]['returncode'] != 0):
        raise ValueError('Approach lacks its unique accepted successful terminal result')
    positions = [rows.index(by_name[name][0]) for name in ('dispatched', 'accepted', 'result', 'request_complete')]
    if positions != sorted(positions):
        raise ValueError('Approach action ordering is invalid')
    pending_index = next(i for i, e in enumerate(active) if e.get('event') == 'trial')
    successful_index = next(i for i, e in enumerate(active) if e.get('event') == 'trial' and e.get('trial') == journal)
    action_indexes = [next(i for i, e in enumerate(active) if e in motion_events and e.get('detail') == by_name[name][0])
                      for name in ('dispatched', 'accepted', 'result', 'request_complete')]
    if not (pending_index < action_indexes[0] < action_indexes[1] < action_indexes[2] < action_indexes[3] <
            successful_index < active.index(stages[0])):
        raise ValueError('Approach terminal evidence does not precede completion')
    for index, event in enumerate(active):
        if event.get('event') == 'action':
            if event.get('kind') not in ('motion', 'navigation'):
                raise ValueError('Unreviewed action endpoint in approach evidence')
            # Older logs omit navigation command/arguments. They cannot prove
            # which queries preceded approach, but no navigation event at all
            # is expected once the approach goal has been dispatched.
            if event['kind'] == 'navigation' and index >= action_indexes[0]:
                raise ValueError('Navigation activity after approach dispatch')
    if any(type(r.get('status')) is not int or r['status'] not in (1, 2, 4) for r in rows if r['event'] == 'status'):
        raise ValueError('Approach action status contains cancellation or failure')
    if any(type(r.get('status')) is not int or r['status'] not in (0, 1, 2) for r in rows if r['event'] == 'result_pending'):
        raise ValueError('Approach pending result is invalid')
    observed_hashes = [e.get('hashes') for e in active if e.get('event') == 'trial_dependencies']
    if not observed_hashes or any(h != bundle['manifest']['robot_files'] for h in observed_hashes):
        raise ValueError('Approach installed-file evidence is missing or inconsistent')
    return dict(source=source, options=options, planned=planned, context=copy.deepcopy(context),
                predecessor_sha256=digest(proof), bundle_id=bundle['manifest']['id'], goal_id=uid)


def load_predecessor(directory, profile):
    directory = Path(directory)
    if (directory/'trial.json.consumed.json').exists():
        raise RuntimeError('Approach journal already consumed; no support retry')
    raw = {name: (directory/name).read_bytes() for name in FILES}
    proof = {name: ([json.loads(line) for line in content.decode().splitlines() if line.strip()]
                    if name == 'events.jsonl' else json.loads(content)) for name, content in raw.items()}
    validated = validate_predecessor(proof, profile)
    return proof, validated, {name: hashlib.sha256(content).hexdigest() for name, content in raw.items()}


def context_record(checkpoint):
    return dict(artifact='table74_support_context_only', executable=False, checkpoint=copy.deepcopy(checkpoint))


def validate_journal(record, bundle_id, predecessor_sha256):
    if not isinstance(record, dict) or record.get('artifact') != 'table74_support_trial':
        raise ValueError('Malformed support journal')
    adapted = dict(record, artifact='table74_approach_trial')
    approach.validate_journal(adapted, bundle_id, predecessor_sha256)
    return copy.deepcopy(record)


class SupportRuntime(approach.TrialRuntime):
    def __init__(self, payload, emit=None):
        self.trial_bundle = support.validate_bundle(payload['trial_bundle'])
        self.predecessor = validate_predecessor(payload['predecessor'], payload['profile'])
        expected = self.predecessor
        if (payload.get('checkpoint') != expected['planned']['checkpoint'] or
                payload.get('resume_source_checkpoint') != expected['source'] or
                payload.get('resume_plan') != expected['planned'] or payload.get('resume_options') != expected['options'] or
                payload.get('resume_context') != expected['context'] or payload.get('cycle', False) is not False):
            raise ValueError('Support technical entry differs from its successful predecessor')
        Runtime.__init__(self, payload, emit)
        self.trial_record = None
        self._trial_dispatch = False

    def save(self):
        record = context_record(self.checkpoint)
        atomic_json(self.session/'context-checkpoint.json', record)
        self.emit('scenario_context', context=record)

    def verify_trial_files(self):
        self.connected()
        expected = dict(self.payload['predecessor']['bundle.json']['manifest']['robot_files'])
        expected.update(self.trial_bundle['manifest']['robot_files'])
        code = '''import hashlib,json,pathlib,sys
print(json.dumps({p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() for p in json.loads(sys.argv[1])}))
'''
        observed = json.loads(self.native(code_command(code, [json.dumps(list(expected))]), timeout=20))
        if observed != expected:
            raise RuntimeError('SUPPORT_FILES_CHANGED: predecessor, support or dependencies differ')
        self.emit('support_dependencies', bundle_id=self.trial_bundle['manifest']['id'], hashes=observed)

    def save_trial(self):
        validate_journal(self.trial_record, self.trial_bundle['manifest']['id'], self.predecessor['predecessor_sha256'])
        atomic_json(self.session/'support.json', self.trial_record)
        self.emit('support', support=copy.deepcopy(self.trial_record))

    def stage(self, message):
        if message != {'command': 'stage', 'stage': STAGE}:
            raise RuntimeError('SUPPORT_STAGE_NOT_AUTHORIZED')
        if not self.armed or not self.resume_validated or self.session is None:
            raise RuntimeError('SUPPORT_NOT_ARMED')
        if self.trial_record is not None or (self.session/'support.json').exists():
            raise RuntimeError('SUPPORT_ALREADY_ATTEMPTED: no retry')
        self.trial_record = dict(artifact='table74_support_trial', version=1,
            bundle_id=self.trial_bundle['manifest']['id'], source_sha256=self.predecessor['predecessor_sha256'],
            phase='pending', intent_ns=time.time_ns(), finished_ns=None, result=None, error=None,
            physical_support_confirmed=False, automatic_retry=False)
        self.save_trial()
        started = time.monotonic()
        try:
            self.connected()
            self.timed('support_containers', self.discover)
            self.timed('support_dependencies', self.hashes)
            self.timed('support_health', self.health, require_home=False)
            self.check_resume_entry()
            self.timed('support_stationary', self.quick_health)
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
            self.timed('support_post_stationary', self.quick_health)
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
    return SupportRuntime(payload).run()


def make_payload(mode, profile, proof, bundle):
    cli = approach.local_cli()
    predecessor = validate_predecessor(proof, profile)
    bundle = support.validate_bundle(bundle)
    payload = cli.make_payload(mode, profile, predecessor['planned']['checkpoint'])
    payload.update(policy='assume', execution_profile='optimistic_v1', cycle=False,
        resume_source_checkpoint=predecessor['source'], resume_options=predecessor['options'],
        resume_plan=predecessor['planned'], resume_context=predecessor['context'],
        predecessor=copy.deepcopy(proof), trial_bundle=bundle)
    here = Path(__file__).resolve().parent
    payload['modules'] += [(name, (here/(name+'.py')).read_text()) for name in
        ('scenario1_deposit', 'scenario1_table74_trial', 'scenario1_table74_trial_run',
         'scenario1_table74_support', 'scenario1_table74_support_run')]
    return payload


def connection_class(cli):
    class SupportConnection(cli.Connection):
        def __init__(self, payload, wifi, evidence, *, console=None):
            self.evidence = evidence
            self.bundle_id = payload['trial_bundle']['manifest']['id']
            self.predecessor_sha256 = digest(payload['predecessor'])
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
            for thread in self.threads: thread.start()

        def present(self, event):
            if event.get('event') == 'resume_checked':
                print('  Entrada técnica comprobada en put1; ensayo de apoyo pendiente, caja aún sujeta.', flush=True)
            elif event.get('event') == 'stage_complete' and event.get('stage') == STAGE:
                print('  Ensayo de apoyo terminado; falta confirmar apoyo físico. Abrazaderas sin abrir.', flush=True)
            else:
                super().present(event)

        def read(self):
            try:
                with (self.evidence/'events.jsonl').open('a') as log:
                    for line in self.process.stdout:
                        log.write(line); log.flush()
                        try:
                            event = json.loads(line)
                            if not isinstance(event, dict) or not isinstance(event.get('event'), str):
                                raise ValueError('Malformed support event')
                            if event['event'] in ('checkpoint', 'trial'):
                                raise ValueError('Support must not publish baseline or approach continuation')
                            if event['event'] == 'scenario_context':
                                record = event['context']
                                if record != context_record(contract.validate_checkpoint(record['checkpoint'])):
                                    raise ValueError('Malformed non-executable support context')
                                cli.atomic_json(self.evidence/'context-checkpoint.json', record)
                            if event['event'] == 'support':
                                record = validate_journal(event['support'], self.bundle_id, self.predecessor_sha256)
                                cli.atomic_json(self.evidence/'support.json', record)
                            self.present(event); self.events.put(event)
                        except (ValueError, KeyError, TypeError) as exc:
                            error = dict(event='error', reason='Support protocol: '+str(exc))
                            self.present(error); self.events.put(error)
            finally:
                self.events.put(dict(event='eof'))
    return SupportConnection


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    mode = result.add_mutually_exclusive_group()
    mode.add_argument('--plan', action='store_true')
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--run', action='store_true')
    result.add_argument('--after', type=Path, required=True, help='Evidence directory of the pinned successful approach')
    result.add_argument('--bundle', type=Path, required=True)
    result.add_argument('--profile', type=Path, default=Path(__file__).with_name('scenario1_current_geometry.json'))
    result.add_argument('--evidence-dir', type=Path)
    result.add_argument('--wifi', action='store_true')
    return result


def cli_main(argv=None):
    cli = approach.local_cli()
    args = parser().parse_args(argv)
    profile = json.loads(args.profile.read_text())
    proof, predecessor, source_hashes = load_predecessor(args.after, profile)
    bundle = support.validate_bundle(json.loads(args.bundle.read_text()))
    if not args.run and not args.check:
        print(json.dumps(dict(mode='plan', stage=STAGE, task_name=bundle['task_name'],
            predecessor=predecessor, predecessor_file_sha256=source_hashes, review=bundle['review'],
            commands_sent=0, predecessor_consumed=False, automatic_retries=0), indent=2, ensure_ascii=False))
        return 0
    if args.run and not sys.stdin.isatty():
        raise RuntimeError('A physical operator and APOYAR token in a TTY are required')
    payload = make_payload('run' if args.run else 'check', profile, proof, bundle)
    evidence = args.evidence_dir or cli.ROOT.parent/'Humanoide-vla-evidence'/(
        time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())+'_TABLE74_SUPPORT_TRIAL_'+str(os.getpid()))
    evidence.mkdir(parents=True, exist_ok=False); os.chmod(evidence, 0o700)
    cli.atomic_json(evidence/'predecessor.json', dict(artifact='support_predecessor_evidence', proof=proof,
        file_sha256=source_hashes, semantic_sha256=predecessor['predecessor_sha256'], source=str(args.after.resolve())))
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
            lock = stack.enter_context(open(path, 'a')); fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            connection = connection_class(cli)(payload, args.wifi, evidence)
            ready = connection.wait('ready'); cli.atomic_json(evidence/'context.json', ready['context'])
            if args.check:
                if connection.process.wait(timeout=15) != 0: raise RuntimeError('Support check failed')
                print('SUPPORT_CHECK_OK; journal anterior sin consumir, ningún apoyo enviado.')
                return 0
            cli.confirm('Ensayo APOYAR: misma caja y posición del approach, hueco actual confirmado de 5 cm; '
                'caja plenamente alineada sobre mesa horizontal de 74 cm, agarre cerrado y estable, efector instalado. '
                'Cinta métrica y manos fuera del robot, caja y recorrido; zona libre, batería suficiente, '
                'cargador desconectado, paros liberados, ruedas en navegación, modo automático, '
                'ningún otro mando y persona junto al paro. Sólo bajar 5 cm; sin desenganche, apertura ni HOME.', 'APOYAR')
            current, _, current_hashes = load_predecessor(args.after, profile)
            if current != proof or current_hashes != source_hashes or support.validate_bundle(json.loads(args.bundle.read_text())) != bundle:
                raise RuntimeError('Support predecessor or bundle changed after review')
            connection.send({'command': 'resume', 'stop_after': 'verify_home'})
            if connection.wait('resume_ready')['checkpoint'] != predecessor['planned']['checkpoint']:
                raise RuntimeError('Support technical entry changed')
            subprocess.run(['bash', str(cli.ROOT/'scripts/lib/cruzr_contact_motion_lock.sh'),
                            'table74-support-trial'], check=True, start_new_session=True)
            cli.atomic_json(evidence/'support-intent.json', dict(artifact='table74_support_intent',
                predecessor_sha256=predecessor['predecessor_sha256'], bundle_id=bundle['manifest']['id'],
                phase='pending', automatic_retry=False, time_ns=time.time_ns()))
            cli.claim_resume(args.after/'trial.json', evidence/'support.json')
            connection.send({'command': 'arm'}); connection.wait('armed')
            connection.send({'command': 'stage', 'stage': STAGE})
            completed = connection.wait('stage_complete', timeout=120)
            journal = validate_journal(json.loads((evidence/'support.json').read_text()),
                                       bundle['manifest']['id'], predecessor['predecessor_sha256'])
            if completed.get('stage') != STAGE or journal['phase'] != 'succeeded':
                raise RuntimeError('Support completion not confirmed')
            cli.finish_connection(connection)
            print('SUPPORT_COMPLETED; compruebe apoyo físico. Abrazaderas cerradas; sin desenganche ni HOME. No repetir.')
            return 0
        finally:
            if connection: connection.close()


if __name__ == '__main__':
    raise SystemExit(cli_main())
