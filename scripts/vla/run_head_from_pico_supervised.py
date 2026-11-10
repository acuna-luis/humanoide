#!/usr/bin/env python3
"""Supervised, single fixed head task from the PICO v4 posture.

--check performs only status reads and passive subscriptions. --run executes one
fixed task only after those checks and an operator's physical confirmation.
Cancellation requests and a telemetry sample are not a certified physical stop.
On lost communication the result is uncertain: do not retry or send HOME.
"""
import argparse
import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shlex
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'scripts/vla'))
sys.path.insert(0, str(ROOT / 'scripts/teleoperation'))

import head_from_pico_check as admission
from pico_cc_mode import call as cc_call

RUNTIME = ROOT / 'scripts/vla/runtime'
EVIDENCE_ROOT = ROOT.parent / 'Humanoide-vla-evidence' / 'HEAD_PICO_SUPERVISED'
SOURCES = {
    'metamove_head_probe': RUNTIME / 'metamove_head_probe.py',
    'head_from_pico_readonly': RUNTIME / 'head_from_pico_readonly.py',
    'head_from_pico_supervised': RUNTIME / 'head_from_pico_supervised.py',
}


def local_exclusivity():
    """Read PC processes and sockets. This is not a distributed control lock."""
    p = subprocess.run(['pgrep', '-x', 'pico_control'], capture_output=True, text=True, timeout=5)
    if p.returncode != 1:
        raise RuntimeError('pico_control_active_or_unknown')
    s = subprocess.run(['systemctl', '--user', 'is-active', '--quiet', 'ubt-remote-control.service'],
                       capture_output=True, text=True, timeout=5)
    if s.returncode != 3:
        raise RuntimeError('controller_ui_active_or_unknown')
    sockets = subprocess.run(['ss', '-ntp', 'state', 'established',
                              '( sport = :8082 or dport = :8082 )'],
                             capture_output=True, text=True, timeout=5)
    if sockets.returncode != 0 or len(sockets.stdout.splitlines()) != 1:
        raise RuntimeError('controller_socket_active_or_unknown')


def current_mode():
    response = cc_call('cc.api.status.get', {'list': ['workMode']})
    if response.get('error') or response.get('result', {}).get('workMode') != 'joystick':
        raise RuntimeError('control_center_not_in_joystick_or_unknown')
    return 'joystick'


def preflight():
    started = time.monotonic()
    local_exclusivity()
    mode = current_mode()
    _, container = admission.inventory()
    local_exclusivity()
    if current_mode() != mode:
        raise RuntimeError('mode_changed_during_preflight')
    return mode, started, container


class Tee:
    """Mirror messages without closing the caller's console streams."""
    def __init__(self, console, log):
        self.console, self.log = console, log

    def write(self, value):
        self.console.write(value)
        self.log.write(value)
        self.console.flush()
        self.log.flush()
        return len(value)

    def flush(self):
        self.console.flush()
        self.log.flush()

    def __getattr__(self, name):
        return getattr(self.console, name)


def recorded_preflight(outdir):
    with (outdir/'preflight-stdout.log').open('x', encoding='utf-8') as stdout_log, \
         (outdir/'preflight-stderr.log').open('x', encoding='utf-8') as stderr_log:
        with contextlib.redirect_stdout(Tee(sys.stdout, stdout_log)), \
             contextlib.redirect_stderr(Tee(sys.stderr, stderr_log)):
            try:
                return preflight()
            except BaseException as exc:
                print('PREFLIGHT_FAILED: '+str(exc), file=sys.stderr, flush=True)
                raise


def evidence_dir(prefix, token):
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    name = prefix + '-' + dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ') + '-' + token[:8]
    outdir = EVIDENCE_ROOT/name
    outdir.mkdir(mode=0o700)
    print('EVIDENCIA=' + str(outdir), flush=True)
    return outdir


def source_bundle(*, dry_run):
    if type(dry_run) is not bool:
        raise ValueError('dry_run_must_be_boolean')
    data = {key: path.read_text(encoding='utf-8') for key, path in SOURCES.items()}
    for value in data.values():
        compile(value, '<reviewed-source>', 'exec')
    code = 'import sys,types\n'
    for name in ('metamove_head_probe', 'head_from_pico_readonly'):
        code += ('m=types.ModuleType(' + repr(name) + ')\n'
                 'exec(' + repr(data[name]) + ',m.__dict__)\n'
                 'sys.modules[' + repr(name) + ']=m\n')
    code += ('import json\n'
             'm=types.ModuleType("head_from_pico_supervised")\n'
             'exec(' + repr(data['head_from_pico_supervised']) + ',m.__dict__)\n'
             'sys.modules["head_from_pico_supervised"]=m\n'
             'print(json.dumps({"event":"BRIDGE_READY"}),flush=True)\n'
             'session=json.loads(sys.stdin.readline())\n'
             'raise SystemExit(m.main(session,dry_run=' + repr(dry_run) + '))\n')
    return data, code


def remote_command(container, sentinel):
    if container != 'walker-ros.ros2-1':
        raise RuntimeError('unexpected_ros_container')
    if not re.fullmatch('CODE_END_[0-9a-f]{32}', sentinel):
        raise RuntimeError('invalid_source_sentinel')
    bootstrap = ('import sys\n'
                 'parts=[]\n'
                 'for line in sys.stdin:\n'
                 ' if line.rstrip("\\n")=='+repr(sentinel)+': break\n'
                 ' parts.append(line)\n'
                 'else: raise SystemExit("source incomplete")\n'
                 'exec(compile("".join(parts),"<head-pico-supervisor>","exec"))\n')
    shell = ('source /opt/ros/humble/setup.bash; export ROS2CLI_DISABLE_DAEMON=1; '
             'exec python3 -B -u -c ' + shlex.quote(bootstrap))
    remote = ['docker', 'exec', '-i', container, 'bash', '-lc', shell]
    return ['setsid', '-w', 'ssh', '-T', '-o', 'StrictHostKeyChecking=yes',
            '-o', 'ConnectTimeout=5', '-o', 'TCPKeepAlive=yes',
            '-o', 'PreferredAuthentications=password',
            '-o', 'PubkeyAuthentication=no', '-o', 'NumberOfPasswordPrompts=1',
            'walker@192.168.11.2', shlex.join(remote)]


def write_all(stream, data):
    remaining = memoryview(data)
    while remaining:
        written = stream.write(remaining)
        if type(written) is not int or written <= 0:
            raise BrokenPipeError('incomplete_remote_input')
        remaining = remaining[written:]
    stream.flush()


def stream_remote(command, code, sentinel, session, preflight_started, outdir):
    """Forward and persist output; a local timeout never kills the monitor."""
    env = dict(os.environ, CRUZR_INTERNAL_ASKPASS='1',
               SSH_ASKPASS=str(ROOT/'scripts/cruzr_recover_to_home.sh'),
               SSH_ASKPASS_REQUIRE='force', DISPLAY=os.environ.get('DISPLAY', ':0'))
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, env=env, bufsize=0)
    try:
        if sentinel in code:
            raise RuntimeError('source_sentinel_collision')
        write_all(process.stdin, (code+'\n'+sentinel+'\n').encode('utf-8'))
    except (OSError, BrokenPipeError):
        print('ALERTA: enlace interrumpido; resultado incierto. No reintentar ni enviar HOME.',
              file=sys.stderr, flush=True)
        raise
    events = []
    buffer = b''
    observed_uuid = None
    bridge_ready = False
    handoff_done = False
    silence_alerted = False
    last_event_at = time.monotonic()

    def invalid_output():
        if 'OUTPUT_INVALID' not in events:
            events.append('OUTPUT_INVALID')
    selector = selectors.DefaultSelector()
    for stream, name in ((process.stdout, 'stdout'), (process.stderr, 'stderr')):
        os.set_blocking(stream.fileno(), False)
        selector.register(stream, selectors.EVENT_READ, name)
    deadline = time.monotonic() + 90
    with (outdir/'remote-stdout.jsonl').open('x', encoding='utf-8') as out, \
         (outdir/'remote-stderr.log').open('x', encoding='utf-8') as err:
        while selector.get_map():
            try:
                ready = selector.select(timeout=.25)
            except KeyboardInterrupt:
                print('ALERTA: supervisión aún activa; no se termina el monitor. '
                      'Si procede, actúe sobre el paro físico.', file=sys.stderr, flush=True)
                continue
            now = time.monotonic()
            if handoff_done and not silence_alerted and now - last_event_at > 1.0:
                silence_alerted = True
                events.append('LOCAL_COMMUNICATION_ALERT')
                print('ALERTA: falta telemetría del supervisor durante más de 1 s; '
                      'el resultado es incierto. Supervise el robot y actúe sobre '
                      'el paro físico si es necesario. No reintente ni envíe HOME.',
                      file=sys.stderr, flush=True)
            if not ready and now >= deadline:
                print('ALERTA: sin conclusión en el plazo previsto; estado incierto. '
                      'No reintentar ni enviar HOME. El monitor continúa.', file=sys.stderr, flush=True)
                deadline = time.monotonic() + 30
            for key, _ in ready:
                data = os.read(key.fd, 65536)
                if not data:
                    selector.unregister(key.fileobj)
                    continue
                text = data.decode('utf-8', 'replace')
                target = out if key.data == 'stdout' else err
                target.write(text); target.flush()
                if key.data == 'stderr':
                    sys.stderr.write(text); sys.stderr.flush()
                if key.data == 'stdout':
                    buffer += data
                    while b'\n' in buffer:
                        line, buffer = buffer.split(b'\n', 1)
                        try:
                            row = json.loads(line)
                            if isinstance(row, dict):
                                last_event_at = time.monotonic()
                                event = row.get('event')
                                if event == 'BRIDGE_READY':
                                    if bridge_ready:
                                        invalid_output()
                                        print('ALERTA: señal de handoff duplicada.', file=sys.stderr, flush=True)
                                        continue
                                    bridge_ready = True
                                    session['age_at_handoff_s'] = time.monotonic() - preflight_started
                                    (outdir/'handoff.json').write_text(json.dumps(session, indent=2)+'\n', encoding='utf-8')
                                    write_all(process.stdin, (json.dumps(session)+'\n').encode('utf-8'))
                                    print('Supervisor remoto listo; edad previa al handoff: '
                                          f"{session['age_at_handoff_s']:.3f} s.", flush=True)
                                    continue
                                goal_id = row.get('goal_uuid')
                                valid_id = isinstance(goal_id, str) and re.fullmatch('[0-9a-f]{32}', goal_id)
                                if not isinstance(event, str) or not valid_id or (observed_uuid and observed_uuid != goal_id):
                                    invalid_output()
                                    print('ALERTA: identidad o evento remoto inválido.', file=sys.stderr, flush=True)
                                elif observed_uuid is None:
                                    observed_uuid = goal_id
                                if event == 'dispatch' and row.get('task') != 'cruzr/move_head_lower':
                                    invalid_output()
                                if event == 'acceptance' and row.get('accepted') is not True:
                                    invalid_output()
                                if event == 'action_result' and (row.get('status') != 4 or row.get('desc') != 'SUCCEED'):
                                    invalid_output()
                                if event == 'pre_dispatch_ready':
                                    challenge = row.get('challenge')
                                    if (not bridge_ready or handoff_done or 'OUTPUT_INVALID' in events or
                                            row.get('session_id') != session['session_id'] or
                                            not isinstance(challenge, str) or not re.fullmatch('[0-9a-f]{32}', challenge)):
                                        invalid_output()
                                        print('ALERTA: desafío previo a orden inválido.', file=sys.stderr, flush=True)
                                        process.stdin.close()
                                    else:
                                        handoff_done = True
                                        handoff = {'schema':'cruzr_head_pico_handoff_v1',
                                                   'session_id':session['session_id'],
                                                   'challenge':challenge,
                                                   'inventory_age_s':time.monotonic()-preflight_started}
                                        (outdir/'pre-dispatch-handoff.json').write_text(
                                            json.dumps(handoff, indent=2)+'\n', encoding='utf-8')
                                        write_all(process.stdin, (json.dumps(handoff)+'\n').encode('utf-8'))
                                        process.stdin.close()
                                        last_event_at = time.monotonic()
                                if event == 'dispatch':
                                    if not handoff_done:
                                        invalid_output()
                                        print('ALERTA: despacho detectado sin handoff válido; '
                                              'supervise el robot y actúe sobre el paro si es necesario.',
                                              file=sys.stderr, flush=True)
                                if event != 'telemetry' and len(events) < 1000:
                                    events.append(event)
                                elif len(events) >= 1000 and 'OUTPUT_INVALID' not in events:
                                    invalid_output()
                                if row.get('event') in ('OPERATOR_ALERT', 'UNRESOLVED', 'UNRESOLVED_MONITORING'):
                                    print('ALERTA: supervise el robot y actúe sobre el paro físico '
                                          'si es necesario; no reintente ni envíe HOME.',
                                          file=sys.stderr, flush=True)
                                if row.get('event') != 'telemetry':
                                    print(line.decode('utf-8', 'replace'), flush=True)
                            else:
                                invalid_output()
                                print('ALERTA: evento remoto inválido.', file=sys.stderr, flush=True)
                        except (ValueError, UnicodeDecodeError):
                            invalid_output()
                            print('ALERTA: línea remota no interpretable: ' +
                                  line.decode('utf-8', 'replace')[:1000], file=sys.stderr, flush=True)
                    if len(buffer) > 1_000_000:
                        invalid_output()
                        buffer = buffer[-1_000_000:]
                        print('ALERTA: salida remota excesiva; la supervisión continúa.',
                              file=sys.stderr, flush=True)
    if buffer.strip():
        invalid_output()
        print('ALERTA: salida remota truncada; resultado incierto.', file=sys.stderr, flush=True)
    rc = process.wait()
    return rc, events


def run_once(physical_confirmed):
    if not physical_confirmed:
        raise RuntimeError('physical_confirmation_required')
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock_path = EVIDENCE_ROOT / '.head-pico-supervised.lock'
    flags = os.O_CREAT | os.O_RDWR | os.O_CLOEXEC | getattr(os, 'O_NOFOLLOW', 0)
    lock_fd = os.open(lock_path, flags, 0o600)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        marker = EVIDENCE_ROOT / 'PENDING_OR_UNRESOLVED.json'
        if marker.exists() or marker.is_symlink():
            raise RuntimeError('prior_result_requires_manual_review')
        token = uuid.uuid4().hex
        outdir = evidence_dir('run', token)
        mode, preflight_started, container = recorded_preflight(outdir)
        # Read and validate sources once; bind the session to those exact bytes.
        provisional = {'schema':'cruzr_head_pico_preflight_v1',
                       'task_sha256':admission.TASK_SHA, 'pico_sha256':admission.PICO_SHA,
                       'work_mode':mode, 'operator_confirmed':True,
                       'controller_status_writers_checked':True,
                       'age_at_handoff_s':0.0, 'session_id':token, 'mode':'run'}
        sources, _ = source_bundle(dry_run=False)
        for name, source in sources.items():
            (outdir/(name+'.py')).write_text(source, encoding='utf-8')
        hashes = {name: hashlib.sha256(source.encode()).hexdigest() for name, source in sources.items()}
        intent = {'token':token, 'task':'cruzr/move_head_lower', 'mode':mode,
                  'physical_confirmed':True, 'source_sha256':hashes, 'no_retry':True}
        (outdir/'intent.json').write_text(json.dumps(intent, indent=2)+'\n', encoding='utf-8')
        fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_CLOEXEC |
                     getattr(os, 'O_NOFOLLOW', 0), 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as pending:
            json.dump({'token':token,'evidence':str(outdir),'state':'pending_or_unresolved'}, pending)
            pending.write('\n'); pending.flush(); os.fsync(pending.fileno())
        dir_fd = os.open(EVIDENCE_ROOT, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
        print('ORDEN ÚNICA: cabeza; mantener supervisión y paro accesible.', flush=True)
        try:
            # The session is sent only after the remote bootstrap is ready.
            # Each host uses its own monotonic clock; the final network delay
            # remains unbounded and is not claimed to be measured.
            renewed, code = source_bundle(dry_run=False)
            if renewed != sources:
                raise RuntimeError('supervisor_source_changed_before_dispatch')
            sentinel = 'CODE_END_' + uuid.uuid4().hex
            rc, events = stream_remote(remote_command(container, sentinel), code, sentinel,
                                       provisional, preflight_started, outdir)
        except BaseException:
            print('ALERTA: resultado incierto; no reintentar ni enviar HOME. '
                  'El recibo pendiente se conserva.', file=sys.stderr, flush=True)
            raise
        success = (rc == 0 and events.count('pre_dispatch_ready') == 1 and
                   events.count('dispatch') == 1 and events.count('acceptance') == 1 and
                   'action_result' in events and events.count('HEAD_SUCCEEDED_AND_STATIONARY') == 1 and
                   events.index('pre_dispatch_ready') < events.index('dispatch') <
                   events.index('acceptance') < events.index('action_result') <
                   events.index('HEAD_SUCCEEDED_AND_STATIONARY') and
                   not any(x in events for x in ('UNRESOLVED', 'UNRESOLVED_MONITORING',
                                                  'OPERATOR_ALERT', 'LOCAL_COMMUNICATION_ALERT', 'OUTPUT_INVALID')))
        result = {'returncode':rc,'events':events,'success':success,
                  'physical_stop_certified':False,'no_retry':True}
        (outdir/'result.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
        if not success:
            raise RuntimeError('outcome_uncertain_or_unsuccessful_do_not_retry')
        # Remove only the exact marker just created, never a different receipt.
        existing = json.loads(marker.read_text(encoding='utf-8'))
        if existing.get('token') != token:
            raise RuntimeError('pending_receipt_changed_do_not_remove')
        marker.unlink()
        print('HEAD_SUCCEEDED_AND_STATIONARY; paro físico no certificado.', flush=True)
        return 0
    finally:
        os.close(lock_fd)


def check_full():
    """Use the same remote monitor and handshakes, with dispatch unreachable."""
    token = uuid.uuid4().hex
    outdir = evidence_dir('check', token)
    mode, started, container = recorded_preflight(outdir)
    _, code = source_bundle(dry_run=True)
    session = {'schema':'cruzr_head_pico_preflight_v1',
               'task_sha256':admission.TASK_SHA, 'pico_sha256':admission.PICO_SHA,
               'work_mode':mode, 'operator_confirmed':False,
               'controller_status_writers_checked':True,
               'age_at_handoff_s':0.0, 'session_id':token, 'mode':'check'}
    sentinel = 'CODE_END_' + uuid.uuid4().hex
    rc, events = stream_remote(remote_command(container, sentinel), code, sentinel,
                               session, started, outdir)
    no_motion = rc == 0 and 'dispatch' not in events and 'PICO_HEAD_SUPERVISED_DRY_RUN_PASSED' in events
    (outdir/'result.json').write_text(json.dumps({'returncode':rc,'events':events,
        'movement_commands':0 if no_motion else None,'physical_control_qualified':False},
        indent=2)+'\n', encoding='utf-8')
    if (rc != 0 or events.count('pre_dispatch_ready') != 1 or
            events.count('PICO_HEAD_SUPERVISED_DRY_RUN_PASSED') != 1 or
            any(x in events for x in ('dispatch', 'UNRESOLVED', 'UNRESOLVED_MONITORING',
                                      'OPERATOR_ALERT', 'LOCAL_COMMUNICATION_ALERT', 'OUTPUT_INVALID'))):
        raise RuntimeError('supervised_dry_run_failed_no_motion_authorized')
    print('CHECK_PASSED; no autoriza movimiento ni comprueba parada física.', flush=True)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--run', action='store_true')
    parser.add_argument('--physical-confirmed', action='store_true',
                        help='constancia de condiciones físicas actuales confirmadas por el operador')
    args = parser.parse_args(argv)
    try:
        if args.check:
            if args.physical_confirmed:
                parser.error('--physical-confirmed sólo se usa con --run')
            return check_full()
        return run_once(args.physical_confirmed)
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        print('ERROR: '+str(exc), file=sys.stderr, flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
