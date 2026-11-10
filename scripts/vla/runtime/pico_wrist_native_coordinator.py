#!/usr/bin/env python3
"""Candidate coordinator for one staged wrist probe; physical gate is closed.

Dependencies are passed explicitly; the real docker launcher is not implemented.
No retries, HOME or automatic cleanup. A worker crash after dispatch is an
uncertain physical state, not a stopped robot. The pre-stage receipt is fsynced
before the worker is created so a partial task write is never silently lost.
"""
import json
import fcntl
import math
import os
from pathlib import Path
import re
import select
import stat
import time

import arm_from_pico_supervised as arm
import arm_native_lease_bridge as bridge
import scenario1_action_client as native
import prepare_pico_wrist_native_probe as probe

MAX_LINE = 65536
GOAL_ID = re.compile(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\Z')
# One stable host directory across sessions. /tmp is used only for the lease
# and a mirror visible to the native container; it is not the durable record.
GLOBAL_RECEIPT_DIR = Path('/var/tmp/cruzr-pico-v4-wrist-control')


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


def acquire_trial_lock():
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
        if marker.exists() or marker.is_symlink():
            raise RuntimeError('previous_trial_requires_manual_review')
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


def coordinate(lease, guard_pipe, manifest, urdf_text, transmissions_text,
               start_worker, evidence_dir, *, timeout=20.0, held_lock_fd=None,
               event_sink=lambda row: True):
    """Run one worker under guard; unreachable with the current release gate.

    start_worker must start the reviewed native-container worker and supply its
    payload. The caller must separately perform the physical and hardware
    preflight and attest source/containers. This function never grants those.
    """
    arm.physical_release_gate()
    if Path(evidence_dir) != GLOBAL_RECEIPT_DIR:
        raise ValueError('must_use_stable_global_receipt_directory')
    owns_lock = held_lock_fd is None
    if owns_lock:
        lock_fd = acquire_trial_lock()
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
        if marker.exists() or marker.is_symlink():
            raise RuntimeError('previous_trial_requires_manual_review')
    try:
        return _coordinate_locked(lease, guard_pipe, manifest, urdf_text, transmissions_text,
                                  start_worker, timeout=timeout, event_sink=event_sink)
    finally:
        if owns_lock:
            os.close(lock_fd)


def _coordinate_locked(lease, guard_pipe, manifest, urdf_text, transmissions_text,
                       start_worker, *, timeout, event_sink):
    arm.physical_release_gate()
    if type(timeout) not in (float, int) or not math.isfinite(timeout) or not 0 < timeout <= 20:
        raise ValueError('invalid_coordinator_timeout')
    probe.validate(manifest, urdf_text, transmissions_text)
    if manifest['input']['reference_20d'] != lease.initial:
        raise ValueError('reference_mismatch')
    guard_pipe.await_ready(3)
    native.check_lease(lease.path, time.monotonic())
    marker = durable_intent(GLOBAL_RECEIPT_DIR, manifest, lease.session_id)
    mirror = mirror_intent(marker, lease)
    journal_path = GLOBAL_RECEIPT_DIR/('worker-events-' + lease.session_id + '.jsonl')
    # If worker creation or evidence opening fails, marker remains.
    journal = journal_path.open('x', encoding='utf-8')
    process = None
    stage_seen = dispatched = accepted = result_ok = finished = worker_result = False
    goal_id = None
    failure = None
    deadline = time.monotonic()+timeout
    buffer = bytearray()
    try:
        process = start_worker(lease.path, mirror, os.geteuid())
        if process.stdin is None or process.stdout is None:
            raise RuntimeError('worker_pipes_unavailable')
        os.set_blocking(process.stdout.fileno(), False)
        while time.monotonic() < deadline:
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
                line, _, rest = bytes(buffer).partition(b'\n')
                buffer = bytearray(rest)
                row = native.object_json(line.decode('utf-8'))
                event = row.get('event')
                journal.write(json.dumps(row, allow_nan=False)+'\n'); journal.flush(); os.fsync(journal.fileno())
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
                    # The XML specifies all seven joints. Compare its six
                    # nominally stationary targets with fresh telemetry
                    # before ACK allows the worker to send anything.
                    check_stationary_targets(manifest, guard_pipe.checked_snapshot(), lease.initial)
                    goal_id = row['goal_id']
                    lease.synchronize_uuid(goal_id, guard_pipe.exchange)
                    write_ack(process, dict(row, event='uuid_ok'), bridge.HANDSHAKE_S)
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
                elif event in ('feedback', 'status'):
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
        # Recheck after the durable write; another thread may have observed a
        # guard or lease failure while storage was flushing.
        final = guard_pipe.checked_snapshot()
        if (abs(final['position'][arm.ARM_AXIS]-endpoint) > arm.ARM_CORRIDOR_TOLERANCE or
                abs(final['velocity'][arm.ARM_AXIS]) > .01):
            raise RuntimeError('postflight_changed_before_return')
        journal.write(json.dumps({'event': 'postflight_settled', 'physical_stop_verified': False})+'\n')
        journal.flush(); os.fsync(journal.fileno())
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
        failure = type(exc).__name__ + ': ' + str(exc)
        records = [{'event': 'coordinator_failure', 'reason': failure,
                    'physical_state': 'UNKNOWN_IF_DISPATCH_ATTEMPTED', 'no_retry': True}]
        try:
            lease.fail()
        except Exception as revoke_error:
            records.append({'event': 'lease_revocation_failed', 'reason': str(revoke_error)})
        # Neither a failed lease write nor failed journal storage can prevent
        # the independent guard from attempting the exact UUID cancellation.
        if goal_id is not None and lease.goal_id == goal_id and not result_ok:
            try:
                canceled = guard_pipe.cancel_goal(goal_id)
                records.append({'event': 'independent_cancel_requested', **canceled})
            except Exception as cancel_error:
                records.append({'event': 'independent_cancel_unconfirmed',
                    'reason': str(cancel_error), 'physical_stop_verified': False})
        try:
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
