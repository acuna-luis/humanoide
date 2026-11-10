#!/usr/bin/env python3
"""Motion-host launcher for a supervised single-wrist candidate.

Starts a guard in ROS2 and a worker in the native app container only after
verified bootstrap and preflight. No command-line release switch exists. This
code has not been exercised on hardware and is not a certified stop mechanism.
"""
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import select
import shlex
import subprocess
import sys
import tempfile
import time
import uuid

import arm_from_pico_supervised as arm
import arm_native_lease_bridge as bridge
import pico_wrist_native_coordinator as coordinator
import pico_wrist_pc_heartbeat as heartbeat
import prepare_pico_wrist_native_probe as probe
import pico_wrist_action_client as native


def validate_payload(payload):
    required = {'session', 'manifest', 'urdf_text', 'transmissions_text',
                'guard_source', 'worker_source', 'source_digests', 'operator_confirmed'}
    if (not isinstance(payload, dict) or set(payload) not in
            (required, required | {'model_mode'}, required | {'model_mode', 'incident_evidence_b64'}) or
            ('model_mode' in payload and payload['model_mode'] is not True)):
        raise ValueError('invalid_launcher_payload')
    if 'incident_evidence_b64' in payload:
        value = payload['incident_evidence_b64']
        if not isinstance(value, str) or len(value) > 100000:
            raise ValueError('invalid_incident_evidence')
        try:
            evidence = base64.b64decode(value, validate=True)
        except (ValueError, TypeError) as exc:
            raise ValueError('invalid_incident_evidence') from exc
        coordinator._incident_status(evidence)
    if payload['operator_confirmed'] is not True:
        raise ValueError('current_operator_confirmation_required')
    session = payload['session']
    arm.validate_preflight(session, 0, dry_run=True)
    probe.validate(payload['manifest'], payload['urdf_text'], payload['transmissions_text'])
    digests = payload['source_digests']
    if not isinstance(digests, dict) or set(digests) != {'guard', 'worker'}:
        raise ValueError('invalid_reviewed_source_digests')
    for role in ('guard', 'worker'):
        key = role + '_source'
        if not isinstance(payload[key], str) or not 0 < len(payload[key]) <= 1_000_000:
            raise ValueError('invalid_' + key)
        digest = digests[role]
        if (not isinstance(digest, str) or len(digest) != 64
                or any(char not in '0123456789abcdef' for char in digest)
                or hashlib.sha256(payload[key].encode('utf-8')).hexdigest() != digest):
            raise ValueError('reviewed_source_digest_mismatch:' + role)
        compile(payload[key], '<'+key+'>', 'exec')
    return session


def discover_containers():
    result = subprocess.run(['docker', 'ps', '--format', '{{.Names}}'], capture_output=True, text=True, timeout=5)
    if result.returncode:
        raise RuntimeError('container_discovery_failed')
    names = result.stdout.splitlines()
    app = [x for x in names if x == 'walker-motion.manipulation_robot_app-1']
    ros = [x for x in names if x == 'walker-ros.ros2-1']
    if len(app) != 1 or len(ros) != 1:
        raise RuntimeError('motion_containers_not_unique')
    return app[0], ros[0]


def write_stream(fd, data, timeout):
    os.set_blocking(fd, False)
    deadline = time.monotonic()+timeout
    view = memoryview(data)
    while view:
        remaining = deadline-time.monotonic()
        if remaining <= 0: raise TimeoutError('bootstrap_write_timeout')
        _, writable, _ = select.select([], [fd], [], remaining)
        if not writable: raise TimeoutError('bootstrap_write_timeout')
        try: count = os.write(fd, view)
        except BlockingIOError: continue
        if count <= 0: raise BrokenPipeError('bootstrap_write_failed')
        view = view[count:]


class StreamStartUncertain(RuntimeError):
    """A child exists but its source or payload delivery did not complete.

    If source_may_have_executed, retain the process, revoke its lease, and
    treat the outcome as uncertain. Do not kill a potentially active worker.
    """
    def __init__(self, process, phase, cause, *, source_may_have_executed,
                 local_cleanup_observed=False):
        self.process = process
        self.phase = phase
        self.source_may_have_executed = source_may_have_executed
        self.local_cleanup_observed = local_cleanup_observed
        super().__init__('stream_start_uncertain:' + phase + ':' + type(cause).__name__ + ':' + str(cause))


def _reap_unstarted_bootstrap(child):
    """Stop only a bootstrap that cannot have executed its task source.

    The local docker-exec process is controlled here; its completion alone
    does not prove remote process cleanup or physical stopping.
    """
    if child.stdin is not None:
        try: child.stdin.close()
        except OSError: pass
    try:
        child.wait(timeout=1)
    except subprocess.TimeoutExpired:
        child.terminate()
        try: child.wait(timeout=1)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=1)


def start_streamed(container, setup, source, payload, *, stderr, verified=None):
    sentinel = 'PICO_SOURCE_END_' + uuid.uuid4().hex
    if sentinel in source:
        raise ValueError('source_sentinel_collision')
    encoded_payload = json.dumps(payload, allow_nan=False).encode('utf-8')
    source_bytes = source.encode('utf-8')
    if verified is None:
        # Existing passive checks do not dispatch goals and retain the old
        # framing. Physical callers must provide the binding-derived scope.
        bootstrap = ('import sys\nparts=[]\nfor line in sys.stdin:\n'
                     ' if line=='+repr(sentinel+'\n')+': break\n'
                     ' parts.append(line)\n'
                     'else: raise SystemExit("incomplete source")\n'
                     'exec(compile("".join(parts),"<pico-streamed-source>","exec"))\n')
    else:
        if (not isinstance(verified, dict) or
                set(verified) != {'role', 'source_sha256', 'session_id'} or
                verified['role'] not in ('guard', 'worker')):
            raise ValueError('invalid_verified_stream_scope')
        # Expected source digest is supplied by the PC's previously verified
        # binding. The dynamic per-child payload is constructed by this host;
        # its wire digest protects that exact payload and session in transit.
        if hashlib.sha256(source_bytes).hexdigest() != verified['source_sha256']:
            raise ValueError('reviewed_source_digest_mismatch:' + verified['role'])
        import pico_wrist_verified_stream as stream_verifier
        bootstrap = stream_verifier.build_bootstrap(
            len(source_bytes), sentinel, verified['source_sha256'],
            hashlib.sha256(encoded_payload).hexdigest(), verified['session_id'],
            role=verified['role'])
    command = ('source '+setup+'; export ROS2CLI_DISABLE_DAEMON=1; '
               'exec python3 -B -u -c '+shlex.quote(bootstrap))
    child = subprocess.Popen(['docker', 'exec', '-i', container, 'bash', '-lc', command],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr, bufsize=0)
    try:
        # Before attempting any sentinel, source cannot be executed even if
        # the full source write completed immediately before an interrupt.
        write_stream(child.stdin.fileno(), source_bytes+b'\n', 10.0)
    except BaseException as exc:
        reaped = False
        try:
            _reap_unstarted_bootstrap(child)
            reaped = True
        except BaseException:
            pass  # Preserve handle; remote cleanup unknown.
        raise StreamStartUncertain(child, 'source', exc,
                                   source_may_have_executed=False,
                                   local_cleanup_observed=reaped) from exc
    try:
        # An interrupt can arrive after the complete sentinel reached the
        # child but before write_stream returned; treat any exception here as
        # potentially executed, even when a partial line would be harmless.
        write_stream(child.stdin.fileno(), (sentinel+'\n').encode(), 10.0)
    except BaseException as exc:
        raise StreamStartUncertain(child, 'sentinel', exc,
                                   source_may_have_executed=True) from exc
    try:
        write_stream(child.stdin.fileno(), encoded_payload+b'\n', 10.0)
    except BaseException as exc:
        # Once sentinel is accepted, the source may run and EOF might turn a
        # partial last line into valid JSON. Preserve the handle; no signal,
        # stdin close, retry, or physical-stop claim is permitted here.
        raise StreamStartUncertain(child, 'payload', exc,
                                   source_may_have_executed=True) from exc
    return child


def verify_shared_tmp(directory, app):
    """Check one newly-created private file is readable in the app container."""
    token = uuid.uuid4().hex
    path = Path(directory)/('shared-' + token)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(token); f.flush(); os.fsync(f.fileno())
        code = 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).read_text())'
        result = subprocess.run(['docker', 'exec', app, 'python3', '-B', '-c', code, str(path)],
                                capture_output=True, text=True, timeout=5)
        if result.returncode != 0 or result.stdout.strip() != token:
            raise RuntimeError('shared_tmp_not_verified')
    finally:
        # Remove only the locally created marker; no task or lease cleanup.
        path.unlink(missing_ok=True)


class HostOutput:
    """Nonblocking operator output: a lost reader revokes future leases."""
    def __init__(self, fd):
        self.fd, self.failed = fd, False
        os.set_blocking(fd, False)

    def emit(self, row):
        try:
            data = (json.dumps(row, separators=(',', ':'), allow_nan=False)+'\n').encode()
            if len(data) > 4096 or os.write(self.fd, data) != len(data):
                self.failed = True
        except (OSError, BlockingIOError):
            self.failed = True
        return not self.failed


def _track_stream_start(role, uncertain_children, output, *args, **kwargs):
    """Retain a child if bootstrap delivery is uncertain; never resend."""
    try:
        return start_streamed(*args, **kwargs)
    except StreamStartUncertain as exc:
        # Preserve the handle in launch's scope even as the coordinator
        # journals and propagates the error. The durable worker intent already
        # exists before start_worker is called.
        if exc.source_may_have_executed or not exc.local_cleanup_observed:
            uncertain_children.append((role, exc.phase, exc.process))
        output.emit({'event': 'OPERATOR_ALERT', 'reason': 'bootstrap_delivery_uncertain',
                     'role': role, 'phase': exc.phase,
                     'source_may_have_executed': exc.source_may_have_executed,
                     'local_cleanup_observed': exc.local_cleanup_observed,
                     'no_retry': True, 'physical_stop_confirmed': False,
                     'instruction': 'Supervise el robot; no reintente ni envíe HOME.'})
        raise


def _observe_uncertain_child(child, output, role, phase):
    """Keep a possibly active child under observation without signalling it.

    EOF, a process exit or a cancellation request never establish physical
    stopping. If the child remains alive, keep the host alive and warn rather
    than silently abandoning its process handle. No commands are sent to it.
    """
    stream = child.stdout
    if stream is not None:
        try:
            os.set_blocking(stream.fileno(), False)
        except (OSError, ValueError):
            stream = None  # Continue observing process; channel state unknown.
    last_notice = float('-inf')
    while True:
        try:
            status = child.poll()
            if status is not None:
                output.emit({'event': 'uncertain_child_exit_observed', 'role': role,
                             'phase': phase, 'returncode': status, 'no_retry': True,
                             'physical_stop_confirmed': False})
                return status
            now = time.monotonic()
            if now-last_notice >= 5:
                output.emit({'event': 'UNRESOLVED_MONITORING', 'role': role, 'phase': phase,
                             'no_retry': True, 'physical_stop_confirmed': False,
                             'instruction': 'Supervise el robot; no reintente ni envíe HOME.'})
                last_notice = now
            if stream is None:
                time.sleep(.1)
                continue
            try:
                readable, _, _ = select.select([stream.fileno()], [], [], .1)
            except (OSError, ValueError):
                stream = None
                continue
            if readable:
                try: data = os.read(stream.fileno(), 400)
                except BlockingIOError: continue
                except OSError:
                    stream = None
                    continue
                if not data:
                    stream = None
                else:
                    # Drain the pipe so a worker cannot remain blocked on a
                    # full buffer; forward it without treating it as a result.
                    output.emit({'event': 'uncertain_child_output', 'role': role,
                                 'text': data.decode('utf-8', 'replace'),
                                 'physical_stop_confirmed': False})
        except KeyboardInterrupt:
            output.emit({'event': 'OPERATOR_ALERT', 'reason': 'uncertain_child_still_monitored',
                         'role': role, 'no_retry': True, 'physical_stop_confirmed': False})
        except OSError as exc:
            # A failure to query the local process is not evidence of exit.
            output.emit({'event': 'OPERATOR_ALERT', 'reason': 'uncertain_child_poll_failed:' + str(exc),
                         'role': role, 'no_retry': True, 'physical_stop_confirmed': False})
            time.sleep(.1)


def _observe_uncertain_guard_exit(child, output):
    """Keep the process alive on uncertain guard shutdown; its reader owns stdout."""
    notice = float('-inf')
    while True:
        try:
            rc = child.poll()
            if rc is not None:
                return rc
            now = time.monotonic()
            if now - notice >= 5:
                output.emit({'event':'UNRESOLVED_MONITORING', 'role':'guard',
                             'reason':'guard_shutdown_unconfirmed', 'no_retry':True,
                             'physical_stop_confirmed':False})
                notice = now
            time.sleep(.1)
        except (KeyboardInterrupt, OSError):
            output.emit({'event':'OPERATOR_ALERT', 'reason':'guard_shutdown_unconfirmed',
                         'no_retry':True, 'physical_stop_confirmed':False})


def pc_preflight_handoff(session, output, input_fd):
    """Bound PC-to-Motion preflight age without comparing host clocks."""
    challenge = uuid.uuid4().hex
    if not output.emit({'event':'HOST_PREFLIGHT_READY', 'session_id':session['session_id'],
                        'challenge':challenge}):
        raise RuntimeError('operator_output_unavailable')
    os.set_blocking(input_fd, False)
    deadline = time.monotonic()+3.0
    buffer = bytearray()
    while time.monotonic() < deadline:
        readable, _, _ = select.select([input_fd], [], [], max(0.0, deadline-time.monotonic()))
        if not readable: break
        try: data = os.read(input_fd, 4097)
        except BlockingIOError: continue
        if not data: raise RuntimeError('pc_preflight_disconnected')
        buffer.extend(data)
        if len(buffer) > 4096: raise ValueError('pc_preflight_ack_oversize')
        if b'\n' in buffer:
            line, extra = bytes(buffer).split(b'\n', 1)
            if extra: raise ValueError('pc_preflight_ack_extra_data')
            ack = native.object_json(line.decode('utf-8'))
            if (set(ack) != {'event', 'session_id', 'challenge', 'inventory_age_s'} or
                    ack['event'] != 'pc_preflight_ack' or ack['session_id'] != session['session_id'] or
                    ack['challenge'] != challenge or type(ack['inventory_age_s']) not in (int, float) or
                    not math.isfinite(ack['inventory_age_s']) or ack['inventory_age_s'] < 0 or
                    ack['inventory_age_s']+3.0 > 30 or time.monotonic() > deadline):
                raise ValueError('pc_preflight_ack_invalid_or_stale')
            # The maximum remaining preflight RTT is conservatively included.
            session['age_at_handoff_s'] = ack['inventory_age_s'] + 3.0
            return
    raise TimeoutError('pc_preflight_ack_timeout')


def launch(payload, *, verified_provenance=None):
    # Bootstrap verified source, payload and session before executing us.
    if verified_provenance is None:
        arm.physical_release_gate()
    session = validate_payload(payload)
    if verified_provenance is not None:
        arm.require_verified_stream(verified_provenance, 'host', session['session_id'])
    # This creates only a private, receipted control directory if absent. No
    # automatic rollback; an interrupted creation requires manual review.
    coordinator.ensure_control_root()
    # Acquired before either guard or worker is started; retained until return.
    incident_evidence = (base64.b64decode(payload['incident_evidence_b64'], validate=True)
                         if 'incident_evidence_b64' in payload else None)
    lock_fd = (coordinator.acquire_trial_lock() if incident_evidence is None else
               coordinator.acquire_trial_lock(incident_evidence=incident_evidence))
    child = pipe = lease = pc = None
    worker_holder = []
    uncertain_children = []
    directory = None
    completed = False
    try:
        output = HostOutput(sys.stdout.fileno())
        pc_preflight_handoff(session, output, sys.stdin.fileno())
        if not output.emit({'event':'HOST_HEARTBEAT_READY', 'session_id':session['session_id']}):
            raise RuntimeError('operator_output_unavailable')
        if payload.get('model_mode', False):
            pc = heartbeat.PcHeartbeat(sys.stdin.fileno(), session['session_id'], output.emit, model_mode=True)
        else:
            pc = heartbeat.PcHeartbeat(sys.stdin.fileno(), session['session_id'], output.emit)
        pc.await_ready(3.0)
        app, ros = discover_containers()
        directory = tempfile.mkdtemp(prefix='pico-wrist-live-', dir='/tmp')
        verify_shared_tmp(directory, app)
        # Do not attach stderr to potentially blocking storage. Structured
        # guard fault events are retained by GuardPipe; native stderr remains
        # unavailable until an independently safe drain exists.
        child = _track_stream_start('guard', uncertain_children, output,
            ros, '/opt/ros/humble/setup.bash', payload['guard_source'], session,
            stderr=subprocess.DEVNULL,
            verified={'role': 'guard', 'source_sha256': payload['source_digests']['guard'],
                      'session_id': session['session_id']})
        lease = bridge.GuardLease(directory, payload['manifest']['input']['reference_20d'],
                                  lambda: child.poll() is None and pc.alive() and not output.failed,
                                  session_id=session['session_id'])
        now = time.monotonic()
        pipe = bridge.GuardPipe(child, lease, now-session['age_at_handoff_s'],
                                enable_guard_heartbeat=True)
        # Read only plain process/heartbeat state when the coordinator records
        # a failure after attempting cancellation. Never perform ROS I/O here.
        pipe.status_diagnostics = lambda: {
            'guard_process_returncode': child.poll(),
            'pc_heartbeat_failure': pc.failure,
            'pc_heartbeat_last_monotonic': pc.last,
            'operator_output_failed': output.failed,
        }
        def start_worker(lease_path, intent_path, intent_uid):
            request = {'manifest': payload['manifest'], 'urdf_text': payload['urdf_text'],
                       'transmissions_text': payload['transmissions_text'], 'lease_path': str(lease_path),
                       'session_id': session['session_id'], 'intent_path': str(intent_path),
                       'intent_uid': intent_uid}
            if payload.get('model_mode', False):
                request['model_mode'] = True
            error_log = coordinator.GLOBAL_RECEIPT_DIR/('worker-stderr-'+session['session_id']+'.log')
            with error_log.open('x', encoding='utf-8') as errors:
                worker = _track_stream_start('worker', uncertain_children, output,
                    app, '/opt/walker/setup.bash', payload['worker_source'], request, stderr=errors,
                    verified={'role': 'worker', 'source_sha256': payload['source_digests']['worker'],
                              'session_id': session['session_id']})
            worker_holder.append(worker)
            return worker
        model_options = ({'timeout':150.0, 'model_permit':pc} if payload.get('model_mode', False) else {})
        if incident_evidence is not None:
            model_options['incident_evidence'] = incident_evidence
        result = coordinator.coordinate(lease, pipe, payload['manifest'], payload['urdf_text'],
                                        payload['transmissions_text'], start_worker,
                                        coordinator.GLOBAL_RECEIPT_DIR, held_lock_fd=lock_fd,
                                        event_sink=output.emit, verified_provenance=verified_provenance,
                                        **model_options)
        completed = True
        return result
    finally:
        # On uncertainty, preserve shared files and do not claim cancellation.
        # The operator must monitor the robot; no HOME or retry is issued.
        if lease is not None:
            try: lease.fail()
            except Exception as exc:
                output.emit({'event':'lease_revocation_failed', 'reason':str(exc),
                             'physical_stop_verified':False})
        # A failed bootstrap after the sentinel may have reached executable
        # code. Keep the host and the exact child handles alive until exit;
        # do not signal a worker, resend, or mistake exit for physical stop.
        for role, phase, uncertain_child in uncertain_children:
            _observe_uncertain_child(uncertain_child, output, role, phase)
        shutdown_failure = None
        try:
            if completed and pipe is not None and not pipe.stop():
                output.emit({'event':'OPERATOR_ALERT', 'reason':'guard_stop_unconfirmed',
                             'no_retry':True, 'physical_stop_confirmed':False})
                _observe_uncertain_guard_exit(child, output)
                shutdown_failure = 'guard_stop_unconfirmed'
            if completed and child is not None and shutdown_failure is None:
                try: rc = child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    output.emit({'event':'OPERATOR_ALERT', 'reason':'guard_exit_unconfirmed',
                                 'no_retry':True, 'physical_stop_confirmed':False})
                    _observe_uncertain_guard_exit(child, output)
                    shutdown_failure = 'guard_exit_unconfirmed'
                else:
                    if rc != 0:
                        shutdown_failure = 'guard_exit_failed'
        finally:
            if pc is not None:
                pc.close()
            os.close(lock_fd)
        if shutdown_failure:
            raise RuntimeError(shutdown_failure)


if __name__ == '__main__':
    raise SystemExit('Physical launcher remains blocked; no direct execution.')
