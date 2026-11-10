#!/usr/bin/env python3
"""Coordinator for one supervised staged wrist probe.

Dependencies are passed explicitly by the verified docker launcher.
No retries, HOME or automatic cleanup. A worker crash after dispatch is an
uncertain physical state, not a stopped robot. The pre-stage receipt is fsynced
before the worker is created so a partial task write is never silently lost.
"""
import json
import hashlib
import fcntl
import math
import os
from pathlib import Path
import re
import select
import stat
import threading
import time

import arm_from_pico_supervised as arm
import arm_native_lease_bridge as bridge
import scenario1_action_client as native
import prepare_pico_wrist_native_probe as probe
import pico_wrist_trial_admission as admission
import archive_canceled_pico_wrist_731084 as incident

MAX_LINE = 65536
# Application liveness threshold, not a physical stopping-time bound.
COORDINATOR_PROGRESS_TIMEOUT_S = 2.0
# The guard needs two samples from event-driven E-stop topics. It continues to
# enforce the existing 30 s preflight handoff deadline independently.
GUARD_READY_TIMEOUT_S = 26.0
MODEL_ACTION_TIMEOUT_S = 20.0
GOAL_ID = re.compile(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\Z')
# One stable host directory across sessions. /tmp is used only for the lease
# and a mirror visible to the native container; it is not the durable record.
GLOBAL_RECEIPT_DIR = Path('/var/tmp/cruzr-pico-v4-wrist-control')


class CoordinatorProgress:
    """Permanently invalidate liveness if the coordinator loop stops advancing.

    GuardLease checks this liveness while consuming telemetry. If the loop is
    blocked in I/O, it stops renewing its lease; any last on-disk deadline then
    expires. Neither expiry nor a cancellation request proves physical braking.
    """
    def __init__(self, *, clock=time.monotonic):
        self.clock = clock
        self.lock = threading.Lock()
        self.started = False
        self.failed = False
        self.last = None

    def start(self):
        with self.lock:
            if self.started or self.failed:
                raise RuntimeError('coordinator_progress_not_startable')
            now = self.clock()
            if not math.isfinite(now):
                raise ValueError('coordinator_clock_invalid')
            self.last, self.started = now, True

    def _alive_locked(self, now):
        if self.failed:
            return False
        if not self.started:
            return True
        if not math.isfinite(now) or not 0 <= now-self.last <= COORDINATOR_PROGRESS_TIMEOUT_S:
            self.failed = True
            return False
        return True

    def alive(self):
        with self.lock:
            return self._alive_locked(self.clock())

    def beat(self):
        with self.lock:
            now = self.clock()
            if not self.started or not self._alive_locked(now):
                raise RuntimeError('coordinator_progress_expired')
            self.last = now

    def stop(self):
        with self.lock:
            self.failed = True


def ensure_control_root():
    """Create the stable private control directory additively, with receipts.

    A sibling intent is fsynced *before* mkdir. On interruption it remains and
    forces manual inspection; no automatic rollback or unrelated deletion.
    """
    root = GLOBAL_RECEIPT_DIR
    parent = root.parent
    if not root.is_absolute() or parent.resolve() != parent or root.name in ('', '.', '..'):
        raise ValueError('invalid_global_receipt_path')
    flags_dir = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | getattr(os, 'O_NOFOLLOW', 0)
    parent_fd = os.open(parent, flags_dir)
    intent_name = '.'+root.name+'.create-intent.json'
    try:
        try:
            info = os.stat(root.name, dir_fd=parent_fd, follow_symlinks=False)
            exists = True
        except FileNotFoundError:
            exists = False
        if not exists:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | getattr(os, 'O_NOFOLLOW', 0)
            intent_fd = os.open(intent_name, flags, 0o600, dir_fd=parent_fd)
            with os.fdopen(intent_fd, 'w', encoding='utf-8') as stream:
                json.dump({'state':'intent_before_control_directory_creation',
                           'path':str(root), 'owner_uid':os.geteuid()}, stream)
                stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
            os.fsync(parent_fd)
            os.mkdir(root.name, 0o700, dir_fd=parent_fd)
            os.fsync(parent_fd)
            info = os.stat(root.name, dir_fd=parent_fd, follow_symlinks=False)
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or
                stat.S_IMODE(info.st_mode) != 0o700):
            raise ValueError('global_receipt_directory_not_private')
        root_fd = os.open(root.name, flags_dir, dir_fd=parent_fd)
        try:
            actual = os.fstat(root_fd)
            if (actual.st_dev, actual.st_ino) != (info.st_dev, info.st_ino):
                raise RuntimeError('global_receipt_directory_identity_changed')
            receipt = {'path':str(root), 'owner_uid':actual.st_uid,
                       'device':actual.st_dev, 'inode':actual.st_ino,
                       'mode':'0700', 'automatic_cleanup':False}
            name = 'CONTROL_DIRECTORY_CREATED.json'
            if not exists:
                flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | getattr(os, 'O_NOFOLLOW', 0)
                fd = os.open(name, flags, 0o600, dir_fd=root_fd)
                with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                    json.dump(receipt, stream); stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
                os.fsync(root_fd)
            else:
                fd = os.open(name, os.O_RDONLY | os.O_CLOEXEC | getattr(os, 'O_NOFOLLOW', 0), dir_fd=root_fd)
                with os.fdopen(fd, 'r', encoding='utf-8') as stream:
                    if json.load(stream) != receipt:
                        raise ValueError('global_directory_receipt_mismatch')
            return receipt
        finally:
            os.close(root_fd)
    finally:
        os.close(parent_fd)


def require_no_pending_recovery(root):
    """Incomplete archive intents remain a durable block even without marker."""
    for path in root.iterdir():
        # Check the name even for symlinks or unreadable/nonregular files.
        if re.fullmatch(r'RECOVERY-[0-9a-f]{32}-intent\.json', path.name):
            raise RuntimeError('recovery_requires_manual_review')


def _incident_status(raw):
    """Check the pinned historical UUID status, not current physical stop."""
    if (not isinstance(raw, bytes) or len(raw) > 65536 or
            hashlib.sha256(raw).hexdigest() != incident.TERMINAL_EVIDENCE_SHA):
        raise ValueError('incident_terminal_evidence_hash_mismatch')
    value = json.loads(raw)['status']
    if value.get('returncode') != 0 or value.get('stderr') != '':
        raise ValueError('incident_terminal_observation_failed')
    text = value['stdout']
    lines = text.splitlines()
    ids = [int(match.group(1)) for line in lines
           if (match := re.fullmatch(r'      - (\d+)', line))]
    if (lines.count('status_list:') != 1 or lines.count('  status: 5') != 1 or
            len(re.findall(r'^  status:', text, flags=re.M)) != 1 or
            ids != list(bytes.fromhex(incident.GOAL.replace('-', '')))):
        raise ValueError('incident_terminal_uuid_or_status_mismatch')


def _incident_static(evidence, *, allow_new_session=None):
    """Recheck original marker, journal, revoked lease and exact staged XML."""
    _incident_status(evidence)
    root = GLOBAL_RECEIPT_DIR
    for directory in (root, incident.LEASE_DIR):
        info = directory.lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or
                stat.S_IMODE(info.st_mode) & 0o077 or directory.resolve() != directory):
            raise ValueError('incident_directory_not_private_or_canonical')
    pending = sorted(p.name for p in root.iterdir()
                     if re.fullmatch(r'RECOVERY-[0-9a-f]{32}-intent\.json', p.name))
    expected = [] if allow_new_session is None else ['RECOVERY-'+allow_new_session+'-intent.json']
    if pending != expected:
        raise RuntimeError('incident_recovery_intent_set_changed')
    incident.validate_record(root, incident.LEASE_DIR)
    incident.container_task('check')


def acquire_trial_lock(*, incident_evidence=None):
    root = GLOBAL_RECEIPT_DIR
    info = root.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) & 0o077 or root.resolve() != root):
        raise ValueError('global_receipt_directory_not_private')
    flags = os.O_CREAT | os.O_RDWR | os.O_CLOEXEC | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(root/'.trial.lock', flags, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        marker = root/'PENDING_OR_UNRESOLVED.json'
        if incident_evidence is None:
            if marker.exists() or marker.is_symlink():
                raise RuntimeError('previous_trial_requires_manual_review')
            require_no_pending_recovery(root)
        else:
            # Exact, historical 731084 only; no existing marker is removed.
            # Admit only the specifically verified ROS CLI daemon; process
            # inventory and its reported graph are point observations, not
            # authentication or distributed exclusivity proofs.
            _incident_static(incident_evidence)
            incident.no_observed_activity(allow_ros_daemon=True)
        return fd
    except BaseException:
        os.close(fd)
        raise


def mirror_intent(marker, lease):
    """Mirror the fsynced global intent into the private shared /tmp lease dir."""
    path = lease.directory/('intent-' + lease.session_id + '.json')
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(path, flags, 0o600)
    try:
        raw = marker.read_bytes()
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        directory_fd = os.open(lease.directory, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(directory_fd)
        finally: os.close(directory_fd)
    except BaseException:
        # The durable global receipt survives all mirror failures.
        raise
    return path


def durable_intent(directory, manifest, session_id):
    """Fail if any earlier intent exists; never erase or overwrite a receipt."""
    root = Path(directory)
    info = root.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or
            stat.S_IMODE(info.st_mode) & 0o077):
        raise ValueError('evidence_directory_not_private')
    path = root/'PENDING_OR_UNRESOLVED.json'
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump({'session_id': session_id, 'task_path': manifest['candidate']['runtime_path'],
                       'task_sha256': manifest['candidate']['xml_sha256'],
                       'state': 'intent_before_stage_or_send'}, stream, allow_nan=False)
            stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        dirfd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(dirfd)
        finally: os.close(dirfd)
    except BaseException:
        # Any incomplete file is deliberately retained for manual review.
        raise
    return path


def durable_incident_intent(directory, manifest, session_id, evidence):
    """Create a separate durable intent while retaining incident 731084."""
    if (not isinstance(session_id, str) or not re.fullmatch('[0-9a-f]{32}', session_id)
            or session_id == incident.SESSION):
        raise ValueError('invalid_new_incident_trial_session')
    candidate = manifest['candidate']
    if (candidate['runtime_path'] == incident.TASK_PATH or
            candidate['xml_sha256'] == incident.TASK_SHA):
        raise ValueError('incident_trial_must_use_new_task')
    _incident_static(evidence)
    root = Path(directory)
    if root != GLOBAL_RECEIPT_DIR:
        raise ValueError('incident_intent_requires_global_directory')
    path = root/('RECOVERY-' + session_id + '-intent.json')
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump({'session_id': session_id, 'task_path': candidate['runtime_path'],
                       'task_sha256': candidate['xml_sha256'],
                       'state': 'intent_before_stage_or_send'}, stream, allow_nan=False)
            stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        directory_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(directory_fd)
        finally: os.close(directory_fd)
        # The mirror has the stage worker's existing strict schema. A
        # separate durable binding retains the predecessor relationship.
        incident.durable_new(root/('RECOVERY-' + session_id + '-incident-binding.json'),
                             _incident_binding(session_id, candidate))
    except BaseException:
        # Existing marker and any partial new intent remain as blockers.
        raise
    return path


def _incident_binding(session_id, candidate):
    return {'schema': 'pico_wrist_731084_successor_v1',
            'new_session_id': session_id, 'predecessor_session_id': incident.SESSION,
            'predecessor_goal_id': incident.GOAL, 'predecessor_marker_sha256': incident.MARKER_SHA,
            'predecessor_journal_sha256': incident.JOURNAL_SHA,
            'historical_status_evidence_sha256': incident.TERMINAL_EVIDENCE_SHA,
            'new_task_sha256': candidate['xml_sha256'], 'physical_control_qualified': False}


def write_ack(process, row, timeout):
    """Bound the entire write; partial or undelivered ACK is not a send."""
    raw = (json.dumps(row, separators=(',', ':'), allow_nan=False)+'\n').encode()
    if len(raw) > 4096:
        raise ValueError('worker_ack_too_large')
    fd = process.stdin.fileno()
    os.set_blocking(fd, False)
    deadline = time.monotonic()+timeout
    view = memoryview(raw)
    while view:
        remaining = deadline-time.monotonic()
        if remaining <= 0: raise TimeoutError('worker_ack_write_timeout')
        _, writable, _ = select.select([], [fd], [], remaining)
        if not writable: raise TimeoutError('worker_ack_write_timeout')
        try: count = os.write(fd, view)
        except BlockingIOError: continue
        if count <= 0: raise BrokenPipeError('worker_ack_write_failed')
        view = view[count:]


def check_stationary_targets(manifest, sample, reference):
    """Check all non-wrist commanded endpoints against both guard envelopes.

    A linear interval is checked; an actual controller may overshoot, so this
    is not a validated braking-distance or physical safety guarantee.
    """
    positions = sample['position']
    candidate = manifest['candidate']
    for name, target in zip(candidate['arm_joint_order'], candidate['target_rad']):
        if name == arm.ARM_AXIS:
            continue
        current, initial = positions[name], reference[name]
        lo, hi = arm.SPS_LIMITS[name]
        if (abs(target-initial) > arm.LOCKED_DRIFT_RAD or
                not (lo+initial)/2 <= target <= (hi+initial)/2 or
                not (lo+current)/2 <= target <= (hi+current)/2):
            raise ValueError('stationary_target_outside_guard_sps_warning:' + name)


def failure_diagnostics(guard_pipe, progress_state):
    """Take a bounded best-effort snapshot after cancellation was requested.

    This never calls ROS or waits for the guard. Fields are observations, not
    evidence that the actuator stopped or that an absent event did not occur.
    """
    result = {'event': 'guard_diagnostics', 'physical_stop_verified': False,
              'progress_before_stop': progress_state}
    try:
        reason = getattr(guard_pipe, 'failure', None)
        result['failure'] = None if reason is None else str(reason)[:512]
        result['channel_failed'] = getattr(guard_pipe, 'channel_failed', None)
        result['auto_cancel_requested'] = getattr(guard_pipe, 'auto_cancel_requested', None)
        result['first_guard_fault'] = getattr(guard_pipe, 'first_guard_fault', None)
    except Exception as exc:
        result['guard_identity_error'] = type(exc).__name__ + ':' + str(exc)[:256]
    try:
        result['recent_guard_events'] = list(getattr(guard_pipe, 'guard_events', ()))
    except Exception as exc:
        # A concurrent append can invalidate deque iteration. Preserve the
        # first alert and other already captured information in that case.
        result['guard_events_error'] = type(exc).__name__ + ':' + str(exc)[:256]
    try:
        sample = getattr(guard_pipe, 'latest', None)
        if isinstance(sample, dict):
            result['last_guard_sample'] = {k: sample.get(k) for k in
                ('monotonic', 'position', 'velocity', 'estop', 'servo_stop') if k in sample}
    except Exception as exc:
        result['guard_sample_error'] = type(exc).__name__ + ':' + str(exc)[:256]
    try:
        diagnostics = getattr(guard_pipe, 'status_diagnostics', None)
        if callable(diagnostics):
            result['host_liveness'] = diagnostics()
    except Exception as exc:
        result['host_liveness_error'] = type(exc).__name__ + ':' + str(exc)[:256]
    try:
        # Check serializability and cap overall evidence; never let a damaged
        # diagnostic prevent retention of the cancellation outcome.
        raw = json.dumps(result, allow_nan=False, separators=(',', ':'))
        if len(raw.encode('utf-8')) > 32768:
            raise ValueError('guard_diagnostics_too_large')
    except Exception as exc:
        # Keep small string evidence even if one auxiliary field is damaged.
        fault = result.get('first_guard_fault')
        fault_reason = fault.get('reason') if isinstance(fault, dict) else None
        return {'event': 'guard_diagnostics',
                'failure': result.get('failure') if isinstance(result.get('failure'), str) else None,
                'first_guard_fault': {'reason': fault_reason[:512]} if isinstance(fault_reason, str) else None,
                'diagnostic_error': type(exc).__name__ + ':' + str(exc)[:256],
                'physical_stop_verified': False}
    return result


def failure_notice(diagnostics):
    """Small operator alert for the host's nonblocking 4096-byte channel."""
    fault = diagnostics.get('first_guard_fault')
    fault = fault if isinstance(fault, dict) else {}
    host = diagnostics.get('host_liveness')
    host = host if isinstance(host, dict) else {}
    def bounded(value):
        # HostOutput uses JSON's ASCII escaping: a non-BMP code point can
        # expand to 12 bytes. Four 64-character fields plus envelope remain
        # below its 4096-byte limit even for such input.
        return value[:64] if isinstance(value, str) else None
    notice = {'event': 'guard_diagnostic_alert',
            'failure': bounded(diagnostics.get('failure')),
            'guard_reason': bounded(fault.get('reason')),
            'pc_heartbeat_failure': bounded(host.get('pc_heartbeat_failure')),
            'diagnostic_error': bounded(diagnostics.get('diagnostic_error')),
            'no_retry': True, 'physical_stop_verified': False}
    # Measure the same ensure_ascii encoding as HostOutput, with headroom.
    encoded = json.dumps(notice, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    if len(encoded) > 3500:
        return {'event': 'guard_diagnostic_alert', 'reason': 'diagnostic_notice_oversize',
                'no_retry': True, 'physical_stop_verified': False}
    return notice


def coordinate(lease, guard_pipe, manifest, urdf_text, transmissions_text,
               start_worker, evidence_dir, *, timeout=20.0, held_lock_fd=None,
               event_sink=lambda row: True, verified_provenance=None, model_permit=None,
               incident_evidence=None):
    """Run one worker under guard for a verified wrist-trial bootstrap.

    start_worker must start the reviewed native-container worker and supply its
    payload. The caller must separately perform the physical and hardware
    preflight and attest source/containers. This function never grants those.
    """
    if verified_provenance is None:
        arm.physical_release_gate()
    else:
        arm.require_verified_stream(verified_provenance, 'host', lease.session_id)
    if Path(evidence_dir) != GLOBAL_RECEIPT_DIR:
        raise ValueError('must_use_stable_global_receipt_directory')
    if incident_evidence is not None and model_permit is None:
        raise ValueError('incident_admission_requires_model_mode')
    owns_lock = held_lock_fd is None
    if owns_lock:
        lock_fd = (acquire_trial_lock() if incident_evidence is None else
                   acquire_trial_lock(incident_evidence=incident_evidence))
    else:
        lock_fd = held_lock_fd
        if type(lock_fd) is not int:
            raise ValueError('invalid_held_trial_lock')
        expected = os.stat(GLOBAL_RECEIPT_DIR/'.trial.lock', follow_symlinks=False)
        actual = os.fstat(lock_fd)
        if (not stat.S_ISREG(actual.st_mode) or
                (actual.st_dev, actual.st_ino) != (expected.st_dev, expected.st_ino)):
            raise ValueError('held_trial_lock_identity_mismatch')
        # Reassert non-blockingly on the exact shared open file description.
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        marker = GLOBAL_RECEIPT_DIR/'PENDING_OR_UNRESOLVED.json'
        if incident_evidence is None:
            if marker.exists() or marker.is_symlink():
                raise RuntimeError('previous_trial_requires_manual_review')
            require_no_pending_recovery(GLOBAL_RECEIPT_DIR)
        else:
            _incident_static(incident_evidence)
    # The guard's existing lease renewer also checks that this coordinator is
    # making progress. This remains permanently fail-closed after a stall.
    progress = CoordinatorProgress()
    previous_guard_alive = lease.guard_alive
    lease.guard_alive = lambda: previous_guard_alive() and progress.alive()
    try:
        result = _coordinate_locked(lease, guard_pipe, manifest, urdf_text, transmissions_text,
                                    start_worker, timeout=timeout, event_sink=event_sink,
                                    progress=progress, verified_provenance=verified_provenance,
                                    model_permit=model_permit, incident_evidence=incident_evidence)
        # The reader and progress watchdog share this transition: a telemetry
        # sample after progress.stop() must not be mistaken for a runtime fault.
        guard_pipe.prepare_normal_shutdown()
        return result
    finally:
        progress.stop()
        if owns_lock:
            os.close(lock_fd)


def await_model_permission(pc, lease, guard_pipe, progress, goal_id, task_sha256, deadline):
    """Wait for a fresh model permit while the existing guard remains live.

    PC receipt freshness does not measure Vision-to-PC delay. The host and
    worker must use the same monotonic clock, as required by the shared lease.
    A permit never authorizes a physical run on its own.
    """
    pc.begin_model_permit(goal_id, task_sha256)
    while time.monotonic() < deadline:
        progress.beat()
        if guard_pipe.failure or not lease.guard_alive():
            raise RuntimeError('guard_lost_waiting_for_model')
        native.check_lease(lease.path, time.monotonic())
        permit = pc.permit_snapshot()
        if permit is not None:
            if (not isinstance(permit, dict) or set(permit) !=
                    {'goal_id', 'task_sha256', 'decision_sha256', 'deadline_monotonic_ns'} or
                    permit['goal_id'] != goal_id or permit['task_sha256'] != task_sha256 or
                    not isinstance(permit['decision_sha256'], str) or
                    not re.fullmatch('[0-9a-f]{64}', permit['decision_sha256']) or
                    type(permit['deadline_monotonic_ns']) is not int or
                    permit['deadline_monotonic_ns'] <= time.monotonic_ns()):
                raise RuntimeError('invalid_or_expired_model_permission')
            return permit
        time.sleep(.05)
    raise TimeoutError('model_permission_timeout')


def _coordinate_locked(lease, guard_pipe, manifest, urdf_text, transmissions_text,
                       start_worker, *, timeout, event_sink, progress, verified_provenance=None,
                       model_permit=None, incident_evidence=None):
    if verified_provenance is None:
        arm.physical_release_gate()
    else:
        arm.require_verified_stream(verified_provenance, 'host', lease.session_id)
    maximum = 150 if model_permit is not None else 20
    if type(timeout) not in (float, int) or not math.isfinite(timeout) or not 0 < timeout <= maximum:
        raise ValueError('invalid_coordinator_timeout')
    probe.validate(manifest, urdf_text, transmissions_text)
    if manifest['input']['reference_20d'] != lease.initial:
        raise ValueError('reference_mismatch')
    guard_pipe.await_ready(GUARD_READY_TIMEOUT_S)
    native.check_lease(lease.path, time.monotonic())
    progress.start()
    if incident_evidence is None:
        marker = durable_intent(GLOBAL_RECEIPT_DIR, manifest, lease.session_id)
    else:
        marker = durable_incident_intent(GLOBAL_RECEIPT_DIR, manifest, lease.session_id, incident_evidence)
    progress.beat()
    mirror = mirror_intent(marker, lease)
    progress.beat()
    journal_path = GLOBAL_RECEIPT_DIR/('worker-events-' + lease.session_id + '.jsonl')
    # If worker creation or evidence opening fails, marker remains.
    journal = journal_path.open('x', encoding='utf-8')
    process = None
    stage_seen = dispatched = accepted = result_ok = finished = worker_result = False
    goal_id = None
    failure = None
    feedback_count = 0
    deadline = time.monotonic()+timeout
    buffer = bytearray()
    try:
        process = start_worker(lease.path, mirror, os.geteuid())
        progress.beat()
        if process.stdin is None or process.stdout is None:
            raise RuntimeError('worker_pipes_unavailable')
        os.set_blocking(process.stdout.fileno(), False)
        while time.monotonic() < deadline:
            progress.beat()
            if guard_pipe.failure or not lease.guard_alive():
                raise RuntimeError('guard_lost_during_trial')
            native.check_lease(lease.path, time.monotonic())
            ready, _, _ = select.select([process.stdout.fileno()], [], [], .05)
            if not ready:
                if process.poll() is not None: break
                continue
            chunk = os.read(process.stdout.fileno(), MAX_LINE+1)
            if not chunk: break
            buffer.extend(chunk)
            if len(buffer) > MAX_LINE: raise ValueError('worker_output_excessive')
            while b'\n' in buffer:
                progress.beat()
                if guard_pipe.failure or not lease.guard_alive():
                    raise RuntimeError('guard_lost_during_trial')
                native.check_lease(lease.path, time.monotonic())
                line, _, rest = bytes(buffer).partition(b'\n')
                buffer = bytearray(rest)
                row = native.object_json(line.decode('utf-8'))
                event = row.get('event')
                if event == 'feedback':
                    # Retain a count, not a high-rate disk/console write. The
                    # independent guard and the lease are still checked for
                    # every message, and bad UUIDs still fail closed.
                    if not dispatched or result_ok or row.get('goal_id') != goal_id:
                        raise ValueError('foreign_worker_action_event')
                    feedback_count += 1
                    continue
                if feedback_count:
                    journal.write(json.dumps({'event': 'feedback_summary', 'goal_id': goal_id,
                                              'count': feedback_count})+'\n')
                    feedback_count = 0
                journal.write(json.dumps(row, allow_nan=False)+'\n'); journal.flush(); os.fsync(journal.fileno())
                progress.beat()
                if event_sink(row) is not True:
                    raise RuntimeError('operator_output_unavailable')
                if event == 'BRIDGE_READY':
                    continue
                if event == 'stage_receipt':
                    receipt = row.get('receipt')
                    candidate = manifest['candidate']
                    if (stage_seen or row.get('session_id') != lease.session_id or not isinstance(receipt, dict)
                            or receipt.get('runtime_path') != candidate['runtime_path']
                            or receipt.get('sha256') != candidate['xml_sha256']
                            or receipt.get('status') != 'STAGED_NOT_LOADED_OR_EXECUTED'
                            or type(receipt.get('device')) is not int or type(receipt.get('inode')) is not int
                            or type(receipt.get('movement_commands')) is not int or receipt['movement_commands'] != 0):
                        raise ValueError('invalid_stage_receipt')
                    stage_seen = True
                elif event == 'uuid_request':
                    if (not stage_seen or goal_id is not None or row.get('session_id') != lease.session_id
                            or not isinstance(row.get('goal_id'), str) or not GOAL_ID.fullmatch(row['goal_id'])
                            or not isinstance(row.get('challenge'), str) or not re.fullmatch('[0-9a-f]{32}', row['challenge'])
                            or set(row) != {'event', 'session_id', 'goal_id', 'challenge'}):
                        raise ValueError('invalid_worker_uuid_request')
                    permit = None
                    if model_permit is not None:
                        permit = await_model_permission(model_permit, lease, guard_pipe, progress,
                                                        row['goal_id'], manifest['candidate']['xml_sha256'],
                                                        min(deadline, time.monotonic()+120.0))
                        permit_event = {'event':'model_permission_verified', 'session_id':lease.session_id,
                                        'goal_id':row['goal_id'], 'task_sha256':permit['task_sha256'],
                                        'decision_sha256':permit['decision_sha256'],
                                        'deadline_monotonic_ns':permit['deadline_monotonic_ns'],
                                        'physical_stop_verified':False}
                        journal.write(json.dumps(permit_event, allow_nan=False)+'\n')
                        journal.flush(); os.fsync(journal.fileno())
                        progress.beat()
                        if event_sink(permit_event) is not True:
                            raise RuntimeError('operator_output_unavailable')
                        if permit['deadline_monotonic_ns'] <= time.monotonic_ns():
                            raise RuntimeError('model_permission_expired_after_journal')
                    if incident_evidence is not None:
                        _incident_static(incident_evidence, allow_new_session=lease.session_id)
                        raw, _ = incident.read_regular(marker)
                        if json.loads(raw) != {'session_id': lease.session_id,
                                'task_path': manifest['candidate']['runtime_path'],
                                'task_sha256': manifest['candidate']['xml_sha256'],
                                'state': 'intent_before_stage_or_send'}:
                            raise RuntimeError('new_incident_intent_changed')
                        binding_raw, _ = incident.read_regular(GLOBAL_RECEIPT_DIR/
                            ('RECOVERY-' + lease.session_id + '-incident-binding.json'))
                        if json.loads(binding_raw) != _incident_binding(lease.session_id, manifest['candidate']):
                            raise RuntimeError('incident_predecessor_binding_changed')
                    if permit is not None and permit['deadline_monotonic_ns'] <= time.monotonic_ns():
                        raise RuntimeError('model_permission_expired_after_incident_check')
                    # The incident recheck can block on filesystem or docker
                    # I/O. Take the guarded stationary sample only afterward,
                    # immediately before the UUID handshake and model permit.
                    admission.check_guard_before_dispatch(manifest, lease, guard_pipe)
                    if permit is not None and permit['deadline_monotonic_ns'] <= time.monotonic_ns():
                        raise RuntimeError('model_permission_expired_before_handshake')
                    goal_id = row['goal_id']
                    lease.synchronize_uuid(goal_id, guard_pipe.exchange)
                    ack = dict(row, event='uuid_ok')
                    if permit is not None:
                        if permit['deadline_monotonic_ns'] <= time.monotonic_ns():
                            raise RuntimeError('model_permission_expired_before_ack')
                        ack.update(deadline_monotonic_ns=permit['deadline_monotonic_ns'],
                                   decision_sha256=permit['decision_sha256'])
                        # Bound the entire post-ACK interval, including an SDK
                        # send that blocks before the worker can start its own
                        # action timer. This is not a physical stopping bound.
                        deadline = min(deadline, time.monotonic()+MODEL_ACTION_TIMEOUT_S)
                    write_ack(process, ack, bridge.HANDSHAKE_S)
                elif event == 'dispatched':
                    if dispatched or goal_id is None or row.get('goal_id') != goal_id:
                        raise ValueError('unexpected_dispatch')
                    dispatched = True
                elif event == 'accepted':
                    if not dispatched or accepted or row.get('goal_id') != goal_id or row.get('accepted') is not True:
                        raise ValueError('invalid_acceptance')
                    accepted = True
                elif event == 'result':
                    if (not accepted or result_ok or row.get('goal_id') != goal_id or
                            not native.result_succeeded('motion', row.get('status'), row.get('result'))):
                        raise ValueError('invalid_action_result')
                    result_ok = True
                elif event == 'result_pending':
                    if (not accepted or row.get('goal_id') != goal_id or
                            type(row.get('status')) is not int or row['status'] not in (0, 1, 2)):
                        raise ValueError('invalid_pending_result')
                elif event == 'status':
                    if not dispatched or row.get('goal_id') != goal_id:
                        raise ValueError('foreign_worker_action_event')
                elif event == 'worker_finished':
                    if finished or row.get('session_id') != lease.session_id: raise ValueError('worker_session_mismatch')
                    finished = True
                elif event == 'worker_result':
                    if worker_result or type(row.get('returncode')) is not int or row['returncode'] != 0:
                        raise RuntimeError('worker_action_failed')
                    worker_result = True
                else:
                    raise RuntimeError('worker_failure_or_unknown_event:' + str(event))
        if buffer or not (stage_seen and dispatched and accepted and result_ok and finished and worker_result):
            raise RuntimeError('worker_terminal_evidence_incomplete')
        try:
            exit_code = process.wait(timeout=1)
        except Exception as exc:
            raise RuntimeError('worker_exit_unconfirmed') from exc
        if exit_code != 0:
            raise RuntimeError('worker_exit_unconfirmed')
        # Check arrival and rest through the continuously validated guard.
        endpoint = manifest['candidate']['target_rad'][-1]
        since = None
        while time.monotonic() < deadline:
            progress.beat()
            sample = guard_pipe.checked_snapshot()
            q = sample['position'][arm.ARM_AXIS]
            v = sample['velocity'][arm.ARM_AXIS]
            if abs(q-endpoint) <= arm.ARM_CORRIDOR_TOLERANCE and abs(v) <= .01:
                since = since or time.monotonic()
                if time.monotonic()-since >= 1: break
            else:
                since = None
            time.sleep(.02)
        else:
            raise RuntimeError('endpoint_not_settled')
        journal.write(json.dumps({'event': 'postflight_candidate', 'physical_stop_verified': False})+'\n')
        journal.flush(); os.fsync(journal.fileno())
        progress.beat()
        # Recheck after the durable write; another thread may have observed a
        # guard or lease failure while storage was flushing.
        final = guard_pipe.checked_snapshot()
        if (abs(final['position'][arm.ARM_AXIS]-endpoint) > arm.ARM_CORRIDOR_TOLERANCE or
                abs(final['velocity'][arm.ARM_AXIS]) > .01):
            raise RuntimeError('postflight_changed_before_return')
        journal.write(json.dumps({'event': 'postflight_settled', 'physical_stop_verified': False})+'\n')
        journal.flush(); os.fsync(journal.fileno())
        progress.beat()
        if event_sink({'event': 'postflight_settled', 'physical_stop_verified': False}) is not True:
            raise RuntimeError('operator_output_unavailable')
        final = guard_pipe.checked_snapshot()
        if (abs(final['position'][arm.ARM_AXIS]-endpoint) > arm.ARM_CORRIDOR_TOLERANCE or
                abs(final['velocity'][arm.ARM_AXIS]) > .01):
            raise RuntimeError('postflight_changed_after_journal')
        # Marker intentionally remains even on success until a reviewed caller
        # records the robot modification and removes exactly this receipt.
        return {'status': 'ACTION_SUCCEEDED_AND_POSTFLIGHT_OBSERVED',
                'goal_id': goal_id, 'intent_receipt': str(marker),
                'physical_stop_verified': False, 'automatic_cleanup': False}
    except BaseException as exc:
        # Snapshot plain in-memory progress fields before stop changes them;
        # no filesystem or ROS work may precede revocation/cancellation.
        progress_state = {'started': progress.started, 'failed': progress.failed,
                          'last_monotonic': progress.last}
        progress.stop()
        failure = type(exc).__name__ + ': ' + str(exc)
        records = [{'event': 'coordinator_failure', 'reason': failure,
                    'physical_state': 'UNKNOWN_IF_DISPATCH_ATTEMPTED', 'no_retry': True}]
        persisted = None
        try:
            # Revoke renewal in memory immediately, but never wait for the
            # filesystem before asking the independent guard to cancel. An
            # already in-flight write or goal remains a distinct uncertainty.
            persisted = lease.fail_async()
            records.append({'event': 'lease_revocation_started',
                            'durable_write_completed': persisted.is_set()})
        except Exception as revoke_error:
            records.append({'event': 'lease_revocation_failed', 'reason': str(revoke_error)})
        # Neither a failed lease write nor failed journal storage can prevent
        # the independent guard from attempting the exact UUID cancellation.
        cancel_records = []
        if goal_id is not None and lease.goal_id == goal_id and not result_ok:
            try:
                canceled = guard_pipe.cancel_goal(goal_id)
                cancel_records.append({'event': 'independent_cancel_requested', **canceled})
            except Exception as cancel_error:
                cancel_records.append({'event': 'independent_cancel_unconfirmed',
                    'reason': str(cancel_error), 'physical_stop_verified': False})
        # Cancellation was attempted before this bounded observation. A
        # still-pending revocation is not a durable receipt, and must not be
        # silently reported as successful if the storage write stays blocked.
        if persisted is not None:
            persisted.wait(.05)
            if persisted.is_set() and getattr(lease, '_async_failure_error', None):
                records.append({'event': 'lease_revocation_failed',
                                'reason': lease._async_failure_error})
        records.extend(cancel_records)
        records.append(failure_diagnostics(guard_pipe, progress_state))
        # Operator output is best effort and occurs after cancellation was
        # attempted but before durable storage, which may block indefinitely.
        try:
            event_sink(failure_notice(records[-1]))
        except Exception:
            pass
        try:
            if feedback_count:
                journal.write(json.dumps({'event': 'feedback_summary', 'goal_id': goal_id,
                                          'count': feedback_count})+'\n')
            for row in records:
                journal.write(json.dumps(row)+'\n')
            journal.flush(); os.fsync(journal.fileno())
        except Exception:
            pass
        # Do not kill a potentially active worker or claim that expiring its
        # lease stopped the servo. Leave the intent and operator warning.
        raise
    finally:
        journal.close()


if __name__ == '__main__':
    raise SystemExit('No direct execution. A reviewed docker/PC launcher is still required.')
