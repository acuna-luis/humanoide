#!/usr/bin/env python3
"""Candidate guard-to-ROSA lease bridge; no live runner or robot dispatch.

This module supplies an expiry-only lease and a pre-send UUID handshake for a
future independent guard. The current PICO monitor is not yet such a guard.
Never interpret a lease, cancel ACK or terminal status as physical stopping.
"""
import json
import math
import os
from pathlib import Path
import queue
import re
import select
import stat
import sys
import tempfile
import threading
import time
import uuid

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'runtime'))
sys.path.insert(0, str(HERE.parent / 'box_handling'))
import arm_from_pico_supervised as arm
import scenario1_action_client as native
import prepare_pico_wrist_native_probe as probe

MAX_AGE_S = .5
LEASE_S = .5
HANDSHAKE_S = .4
MAX_LINE_BYTES = 65536
UUID = re.compile(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\Z')


class GuardLease:
    """Advance a native lease only on a fresh, validated guard observation.

    Caller must connect `guard_alive` and `exchange` to the *same pinned guard
    subprocess* and deliver its events. The current monitor does not implement
    the UUID handshake; no code here enables it or bypasses its release gate.
    One host monotonic clock is required for guard, bridge and action client.
    """
    def __init__(self, private_dir, initial, guard_alive, *, clock=time.monotonic, session_id=None):
        self.directory = Path(private_dir)
        info = self.directory.lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or
                stat.S_IMODE(info.st_mode) & 0o077):
            raise ValueError('lease_directory_not_private')
        if not isinstance(initial, dict) or set(initial) != set(arm.BODY):
            raise ValueError('reference_20d_required')
        row = {'name': list(initial), 'position': list(initial.values()),
               'velocity': [0.0] * len(initial)}
        values = arm.joint_state(row, arm.BODY)
        arm.check_sps_limits(values)
        self.initial = dict(initial)
        self.guard_alive = guard_alive
        self.clock = clock
        self.lock = threading.RLock()
        if session_id is not None and (not isinstance(session_id, str) or
                                        not re.fullmatch('[0-9a-f]{32}', session_id)):
            raise ValueError('invalid_guard_session_id')
        self.session_id = session_id or uuid.uuid4().hex
        self.guard_id = None
        self.goal_id = None
        self.last_stamp = None
        self.failed = False
        self.path = self.directory / ('arm-lease-' + self.session_id + '.json')
        # A zero deadline is fail-closed until valid telemetry arrives.
        self._write(0.0)

    def _write(self, deadline):
        if not math.isfinite(deadline) or deadline < 0:
            raise ValueError('invalid_lease_deadline')
        fd, name = tempfile.mkstemp(prefix='.arm-lease-', dir=self.directory)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as out:
                json.dump({'deadline': deadline}, out, allow_nan=False)
                out.write('\n')
                out.flush()
                os.fsync(out.fileno())
            os.replace(name, self.path)
        except BaseException:
            try:
                os.unlink(name)
            except FileNotFoundError:
                pass
            raise

    def fail(self):
        with self.lock:
            self.failed = True
            self._write(0.0)

    def heartbeat(self, event):
        with self.lock:
            self._heartbeat_locked(event)

    def _heartbeat_locked(self, event):
        try:
            if self.failed or not self.guard_alive():
                raise RuntimeError('guard_not_alive')
            if not isinstance(event, dict) or event.get('event') != 'telemetry':
                raise ValueError('invalid_guard_event')
            guard_id = event.get('goal_uuid')
            if not isinstance(guard_id, str) or not re.fullmatch('[0-9a-f]{32}', guard_id):
                raise ValueError('invalid_guard_identity')
            if self.guard_id is not None and guard_id != self.guard_id:
                raise ValueError('guard_identity_changed')
            stamp, now = event.get('monotonic'), self.clock()
            if (type(stamp) not in (int, float) or not math.isfinite(stamp) or
                    not math.isfinite(now) or not 0 <= now-stamp <= MAX_AGE_S or
                    (self.last_stamp is not None and stamp <= self.last_stamp)):
                raise ValueError('guard_event_stale_or_regressed')
            if any(type(event.get(k)) is not int or event[k] != 0 for k in ('estop', 'servo_stop')):
                raise ValueError('guard_reports_stop')
            positions, velocities = event.get('position'), event.get('velocity')
            if not isinstance(positions, dict) or not isinstance(velocities, dict):
                raise ValueError('missing_guard_joint_values')
            if set(positions) != set(arm.BODY) or set(velocities) != set(arm.BODY):
                raise ValueError('guard_joint_set_mismatch')
            names = list(arm.BODY)
            msg = {'name': names, 'position': [positions[n] for n in names],
                   'velocity': [velocities[n] for n in names]}
            arm.motion_envelope(msg, self.initial)
            self.guard_id, self.last_stamp = guard_id, stamp
            self._write(now + LEASE_S)
        except Exception:
            self.fail()
            raise

    def synchronize_uuid(self, goal_id, exchange):
        """Ask the guard to whitelist exactly this UUID before network send."""
        try:
            with self.lock:
                if self.failed or not self.guard_alive() or self.guard_id is None:
                    raise RuntimeError('guard_not_ready')
                if self.goal_id is not None or not isinstance(goal_id, str) or not UUID.fullmatch(goal_id):
                    raise ValueError('invalid_or_duplicate_goal_id')
                native.check_lease(self.path, self.clock())
                challenge = uuid.uuid4().hex
                request = {'event': 'prepare_goal_uuid', 'session_id': self.session_id,
                           'guard_id': self.guard_id, 'goal_id': goal_id, 'challenge': challenge}
                began = self.clock()
            ack = exchange(request, HANDSHAKE_S)
            with self.lock:
                elapsed = self.clock()-began
                expected = dict(request, event='goal_uuid_ready')
                if (not isinstance(ack, dict) or set(ack) != set(expected) | {'goal_uuid', 'monotonic'}
                        or {k: ack[k] for k in expected} != expected
                        or ack['goal_uuid'] != self.guard_id
                        or type(ack['monotonic']) not in (int, float)
                        or not math.isfinite(ack['monotonic'])
                        or not 0 <= self.clock()-ack['monotonic'] <= MAX_AGE_S):
                    raise RuntimeError('uuid_handshake_invalid_ack')
                if (self.failed or not math.isfinite(elapsed) or
                        not 0 <= elapsed <= HANDSHAKE_S or not self.guard_alive()):
                    raise RuntimeError('uuid_handshake_failed')
                # Waiting for ACK must not extend a stale guard lease. The caller
                # must deliver independently verified fresh telemetry as needed.
                native.check_lease(self.path, self.clock())
                self.goal_id = goal_id
        except Exception:
            self.fail()
            raise


class GuardPipe:
    """Connect a pinned guard subprocess's line protocol to a GuardLease.

    Caller must launch the reviewed source and give it the matching preflight
    first; this class does not launch or attest a process by itself. It keeps
    stdin open after the preflight challenge, feeds only post-ready telemetry,
    and puts a hard wall-clock timeout on the UUID ACK exchange. Any failure
    expires the lease permanently. A shared Motion monotonic clock is required.
    """
    def __init__(self, process, lease, inventory_started, *, clock=time.monotonic,
                 enable_guard_heartbeat=False):
        if process.stdin is None or process.stdout is None:
            raise ValueError('guard_pipes_required')
        if lease.guard_alive() is not True:
            raise ValueError('guard_process_not_alive')
        self.process, self.lease = process, lease
        # Nonblocking writes are mandatory: even sending the handshake must
        # be bounded when the guard stops reading its pipe.
        os.set_blocking(self.process.stdin.fileno(), False)
        self.clock, self.inventory_started = clock, inventory_started
        self.acks = queue.Queue(maxsize=1)
        self.ready = threading.Event()
        self.write_lock = threading.Lock()
        self.failure = None
        self.channel_failed = False
        self.auto_cancel_requested = False
        self.stopping = False
        self.stop_ack = False
        self.latest = None
        self.handoff = False
        self.guard_id = None
        if type(enable_guard_heartbeat) is not bool:
            raise ValueError('guard_heartbeat_mode_invalid')
        self.enable_guard_heartbeat = enable_guard_heartbeat
        self.heartbeat_sequence = 0
        self.thread = threading.Thread(target=self._reader, daemon=True)
        self.thread.start()

    def _send(self, row, deadline):
        data = (json.dumps(row, separators=(',', ':'), allow_nan=False) + '\n').encode()
        if len(data) > 4096:
            raise ValueError('guard_command_too_large')
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not self.write_lock.acquire(timeout=remaining):
            raise TimeoutError('guard_write_lock_timeout')
        try:
            view = memoryview(data)
            while view:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('guard_write_timeout')
                _, writable, _ = select.select([], [self.process.stdin.fileno()], [], remaining)
                if not writable:
                    raise TimeoutError('guard_write_timeout')
                try:
                    count = os.write(self.process.stdin.fileno(), view)
                except BlockingIOError:
                    continue
                if type(count) is not int or count <= 0:
                    raise BrokenPipeError('short_guard_write')
                view = view[count:]
        finally:
            self.write_lock.release()

    def _reader(self):
        try:
            while True:
                raw = self.process.stdout.readline(MAX_LINE_BYTES + 1)
                if not raw:
                    raise RuntimeError('guard_output_closed')
                if len(raw) > MAX_LINE_BYTES or not raw.endswith(b'\n'):
                    raise ValueError('guard_output_excessive_or_truncated')
                row = native.object_json(raw.decode('utf-8'))
                event = row.get('event')
                if event == 'BRIDGE_READY':
                    continue
                if event == 'telemetry':
                    if self.ready.is_set() and not self.stopping and not self.lease.failed:
                        if not self.lease.guard_alive():
                            # PC liveness can fail while the independent guard
                            # process is still alive. Revoke authority but keep
                            # its pipe available for exact-UUID cancellation.
                            with self.lease.lock:
                                self.failure = 'guard_or_pc_liveness_lost'
                                try: self.lease.fail()
                                except Exception as exc:
                                    self.failure += ':lease_revocation_failed:' + str(exc)
                            continue
                        # Publish the sample only after it has been validated;
                        # postflight readers use this same lock.
                        with self.lease.lock:
                            try:
                                self.lease.heartbeat(row)
                            except Exception as exc:
                                # The observation is unsafe, but the guard
                                # channel may still cancel the exact UUID.
                                self.failure = 'guard_telemetry_invalid:' + str(exc)
                            else:
                                self.latest = row
                                if self.enable_guard_heartbeat:
                                    self._send_guard_heartbeat()
                    elif not self.ready.is_set():
                        self.latest = row
                elif event == 'pre_dispatch_ready':
                    challenge, guard_id = row.get('challenge'), row.get('goal_uuid')
                    age = self.clock()-self.inventory_started
                    if (self.handoff or row.get('session_id') != self.lease.session_id
                            or not isinstance(challenge, str) or not re.fullmatch('[0-9a-f]{32}', challenge)
                            or not isinstance(guard_id, str) or not re.fullmatch('[0-9a-f]{32}', guard_id)
                            or not math.isfinite(age) or not 0 <= age <= 27):
                        raise ValueError('invalid_guard_preflight_handoff')
                    self.guard_id, self.handoff = guard_id, True
                    self._send({'schema': 'cruzr_head_pico_handoff_v1',
                                'session_id': self.lease.session_id,
                                'challenge': challenge, 'inventory_age_s': age}, time.monotonic()+2.0)
                elif event == 'ARM_GUARD_READY':
                    if (not self.handoff or self.ready.is_set() or self.latest is None
                            or row.get('session_id') != self.lease.session_id
                            or row.get('goal_uuid') != self.guard_id
                            or self.latest.get('goal_uuid') != self.guard_id
                            or type(row.get('movement_commands')) is not int
                            or row.get('movement_commands') != 0
                            or row.get('physical_control_qualified') is not False):
                        raise ValueError('invalid_guard_ready')
                    # The staged target must be based on this exact reference,
                    # within the same observation tolerance as the monitor.
                    positions, velocities = self.latest.get('position'), self.latest.get('velocity')
                    if (not isinstance(positions, dict) or not isinstance(velocities, dict)
                            or set(positions) != set(arm.BODY) or set(velocities) != set(arm.BODY)
                            or any(type(positions[n]) not in (int, float) or
                                   abs(positions[n]-self.lease.initial[n]) > arm.LOCKED_DRIFT_RAD
                                   for n in arm.BODY)
                            or any(type(velocities[n]) not in (int, float) or
                                   abs(velocities[n]) > .001 for n in arm.BODY)):
                        raise ValueError('guard_reference_changed')
                    self.lease.heartbeat(self.latest)
                    if self.enable_guard_heartbeat:
                        self._send_guard_heartbeat()
                    self.ready.set()
                elif event in ('goal_uuid_ready', 'guard_cancel_requested'):
                    if not self.ready.is_set():
                        raise ValueError('guard_ack_before_ready')
                    self.acks.put_nowait(row)
                elif event in ('guard_cancel_response', 'guard_terminal_observed'):
                    # These are observations only. They do not revive a lease or
                    # establish physical stopping; caller can journal them.
                    continue
                elif event in ('OPERATOR_ALERT', 'UNRESOLVED_MONITORING',
                               'guard_auto_cancel_requested', 'guard_auto_cancel_delivery_unknown',
                               'guard_cancel_response_unknown', 'guard_fault_terminal_and_still'):
                    with self.lease.lock:
                        self.failure = self.failure or ('guard_reported:' + event)
                        try: self.lease.fail()
                        except Exception as exc:
                            self.failure += ':lease_revocation_failed:' + str(exc)
                        if event == 'guard_auto_cancel_requested':
                            self.auto_cancel_requested = True
                elif event == 'ARM_GUARD_STOPPED' and self.stopping:
                    if (row.get('goal_uuid') != self.guard_id or row.get('movement_commands') != 0
                            or row.get('physical_stop_confirmed') is not False):
                        raise ValueError('invalid_guard_stop_ack')
                    self.stop_ack = True
                    return
                else:
                    raise ValueError('unexpected_guard_event:' + str(event))
        except BaseException as exc:
            with self.lease.lock:
                self.channel_failed = True
                self.failure = str(exc)
                try:
                    self.lease.fail()
                except Exception as revoke_error:
                    self.failure += ':lease_revocation_failed:' + str(revoke_error)
                finally:
                    self.ready.set()  # wake waiters; they must inspect failure

    def _send_guard_heartbeat(self):
        """Pulse only after validated telemetry and live PC/coordinator lease."""
        if not self.lease.guard_alive() or self.lease.failed or self.guard_id is None:
            raise RuntimeError('guard_heartbeat_requires_live_supervisor')
        self._send({'event': 'supervisor_heartbeat', 'session_id': self.lease.session_id,
                    'guard_id': self.guard_id, 'sequence': self.heartbeat_sequence},
                   time.monotonic() + .1)
        self.heartbeat_sequence += 1

    def checked_snapshot(self):
        """Atomically return only a fresh, successfully checked sample."""
        with self.lease.lock:
            if self.failure or self.lease.failed or not self.ready.is_set() or not self.lease.guard_alive():
                raise RuntimeError('guard_not_healthy_for_snapshot')
            native.check_lease(self.lease.path, self.clock())
            sample = self.latest
            if (not isinstance(sample, dict) or type(sample.get('monotonic')) not in (int, float)
                    or not math.isfinite(sample['monotonic'])
                    or not 0 <= self.clock()-sample['monotonic'] <= MAX_AGE_S):
                raise RuntimeError('postflight_telemetry_stale')
            # Return independent containers so callers cannot alter the sample.
            return dict(sample, position=dict(sample['position']), velocity=dict(sample['velocity']))

    def await_ready(self, timeout):
        if not self.ready.wait(timeout) or self.failure or not self.lease.guard_alive():
            self.lease.fail()
            raise RuntimeError('continuous_guard_not_ready:' + str(self.failure))
        native.check_lease(self.lease.path, self.clock())

    def exchange(self, request, timeout):
        if self.failure or not self.ready.is_set() or not self.lease.guard_alive():
            raise RuntimeError('continuous_guard_unavailable')
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= HANDSHAKE_S:
            raise ValueError('invalid_handshake_timeout')
        deadline = time.monotonic() + timeout
        try:
            self._send(request, deadline)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('guard_ack_timeout')
            return self.acks.get(timeout=remaining)
        except (queue.Empty, TimeoutError) as exc:
            self.lease.fail()
            raise TimeoutError('guard_ack_timeout') from exc
        except (OSError, ValueError):
            self.lease.fail()
            raise

    def stop(self, timeout=2.0):
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 5:
            raise ValueError('invalid_guard_stop_timeout')
        self.stopping = True
        try:
            self.lease.fail()
        except Exception:
            pass  # Still stop the passive guard; do not claim lease revocation.
        try:
            self._send({'event': 'stop_guard', 'session_id': self.lease.session_id}, time.monotonic()+timeout)
        except (OSError, ValueError, TimeoutError):
            pass
        self.thread.join(timeout)
        return self.stop_ack and not self.thread.is_alive() and not self.channel_failed and not self.failure

    def prepare_normal_shutdown(self):
        """End renewal atomically after postflight, before progress is stopped."""
        with self.lease.lock:
            if self.failure or self.lease.failed or not self.ready.is_set() or not self.lease.guard_alive():
                raise RuntimeError('guard_unhealthy_at_shutdown')
            native.check_lease(self.lease.path, self.clock())
            self.stopping = True
            self.lease.fail()

    def cancel_goal(self, goal_id):
        """Ask independent guard to cancel only the handshaken UUID once.

        Call only after the worker received, or might have received, its ACK.
        A request, response or unknown UUID never proves physical stopping.
        """
        if self.channel_failed or self.process.poll() is not None or self.lease.goal_id != goal_id:
            raise RuntimeError('guard_cancel_identity_unavailable')
        if self.auto_cancel_requested:
            return {'goal_id': goal_id, 'request_sent': True, 'automatic': True,
                    'physical_stop_verified': False}
        revocation_error = None
        try:
            self.lease.fail()
        except Exception as exc:
            # A disk/fsync failure must not suppress the independent cancel.
            revocation_error = type(exc).__name__ + ':' + str(exc)
        request = {'event': 'cancel_goal_uuid', 'session_id': self.lease.session_id,
                   'goal_id': goal_id, 'challenge': uuid.uuid4().hex}
        deadline = time.monotonic()+1.0
        self._send(request, deadline)
        remaining = deadline-time.monotonic()
        if remaining <= 0: raise TimeoutError('guard_cancel_request_timeout')
        try: ack = self.acks.get(timeout=remaining)
        except queue.Empty as exc: raise TimeoutError('guard_cancel_request_timeout') from exc
        expected = dict(request, event='guard_cancel_requested', physical_stop_confirmed=False)
        if (not isinstance(ack, dict) or set(ack) != set(expected) | {'goal_uuid','monotonic'}
                or {k:ack[k] for k in expected} != expected or ack['goal_uuid'] != self.guard_id):
            raise RuntimeError('guard_cancel_ack_invalid')
        return {'goal_id': goal_id, 'request_sent': True, 'physical_stop_verified': False,
                'lease_revocation_error': revocation_error}


def synchronized_client_class(base, to_string, handshake):
    """Bind ROSA-generated UUID before its goal request is sent.

    The pinned SDK calls virtual create_goal_request immediately before
    _goal_client.call_async. The added handshake is local; no vendor file is
    modified. Failure clears the unsent local handle and leaves no UUID for
    run_action to cancel. Only the separately reviewed ROSA source is allowed
    at runtime by RosaTransport's existing fingerprint checks.
    """
    observed = native.native_client_class(base, to_string)
    class Synchronized(observed):
        def create_goal_request(self, goal, options=None):
            request, goal_id = super().create_goal_request(goal, options)
            try:
                handshake(goal_id)
            except BaseException:
                self.observed_goal_id = None
                self._goal_handles.pop(goal_id, None)
                raise
            return request, goal_id
    return Synchronized


class GuardedRosaTransport(native.RosaTransport):
    """Same pinned ROSA transport as boxes with a pre-send UUID handshake.

    The release gate is checked before importing or initializing ROSA. The
    current gate always rejects; tests replace it only with fake ROSA modules.
    """
    def __init__(self, lease, exchange):
        arm.physical_release_gate()
        import rosa
        from rosa.action_client import ActionClient, ActionClientGoalHandle
        from rosa.base._ActionType import to_string
        from mc_task_msgs.action import ArmTask
        self.rosa = rosa
        self.kind = 'motion'
        self.correction_guard = None
        self.correction_failure = None
        self.correction_armed = False
        self.correction_readers = {}
        self.events = queue.Queue()
        native.require_callables(rosa, ('init', 'Node', 'spin_once', 'ok', 'shutdown'), 'rosa')
        self.api_fingerprints = native.validate_native_sources({
            'ActionClient': ActionClient, 'ActionClientGoalHandle': ActionClientGoalHandle})
        rosa.init()
        try:
            self.node = rosa.Node('pico_wrist_guarded_action')
            cls = synchronized_client_class(ActionClient, to_string,
                lambda ident: lease.synchronize_uuid(ident, exchange))
            self.client = cls(self.node, native.ENDPOINTS['motion'], ArmTask)
            native.validate_native_client(self.client)
            self.client.configure_observer(lambda event, **data: self.events.put(dict(event=event, **data)))
            self.options = ActionClient.SendGoalOptions()
        except BaseException:
            rosa.shutdown()
            raise


def run_guarded_once(lease, exchange, manifest, urdf_text, transmissions_text, emit, *,
                     timeout=15.0, interrupted=lambda: None, after_transport_ready=lambda: None):
    """Use native action state machine under lease; current gate blocks ROSA.

    The caller must feed fresh guard events concurrently, use a private path
    visible identically from both processes on the same Motion host and permit
    exactly the validated staged task. These requirements are not implemented
    by the current PC launcher. No retry or automatic HOME is introduced.
    """
    arm.physical_release_gate()
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 15:
        raise ValueError('invalid_single_trial_timeout')
    probe.validate(manifest, urdf_text, transmissions_text)
    if manifest['input']['reference_20d'] != lease.initial:
        raise ValueError('guard_reference_does_not_match_candidate')
    goal = manifest['candidate']['goal']
    checked_goal = native.validate_goal('motion', json.dumps(goal, allow_nan=False))
    if checked_goal != goal:
        raise ValueError('invalid_goal')
    transport = GuardedRosaTransport(lease, exchange)
    try:
        # ROSA initialization may overwrite process signal handlers. The worker
        # reinstalls its callbacks here before the native client can send.
        after_transport_ready()
        return native.run_action(transport, 'motion', goal, timeout, emit,
                                 interrupted=interrupted, lease_file=lease.path)
    finally:
        lease.fail()
        transport.close()


def main():
    print('BLOCKED: no independent live guard/UUID handshake or physical run is enabled', file=sys.stderr)
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
