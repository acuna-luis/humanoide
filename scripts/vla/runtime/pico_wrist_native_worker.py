#!/usr/bin/env python3
"""ROSA worker for one verified native wrist goal.

It delegates the UUID handshake and lease ownership to the Motion-host
coordinator. Its output pipe is nonblocking; broken communication becomes an
interruption, not a success. A lease or cancel response is not physical STOP.
"""
import json
import hashlib
import math
import os
from pathlib import Path
import re
import select
import signal
import sys
import time
import uuid

import arm_from_pico_supervised as arm
import arm_native_lease_bridge as bridge
import pico_wrist_action_client as native
import pico_wrist_native_stage as staging

MAX_LINE = 4096
ID = re.compile(r'[0-9a-f]{32}\Z')
URDF_PATH = '/opt/walker/manipulation_platforms/share/manipulation_platforms/config/urdf/cruzr_s2.urdf'
SPS_PATH = '/opt/walker/config_mc_cruzr_s2_v1_sps/share/config_mc_cruzr_s2_v1_sps/config/ecat_hardware/transmissions.yaml'
META_MOVE_PATH = '/opt/walker/manipulation_meta_tasks/lib/libmeta_move.so'
ROBOT_APP_PATH = '/opt/walker/manipulation_task_manager/lib/manipulation_task_manager/robot_app'


def require_robot_app_can_read_private_task(proc_root=Path('/proc'), *, worker_uid=None):
    """Check the staged 0600 XML can be read by the running robot_app.

    The executing worker checks vendor files with its own effective UID before
    staging. This check addresses the separate reader process, not its future
    execution, capabilities, mount changes or physical safety.
    """
    uid = os.geteuid() if worker_uid is None else worker_uid
    matches = []
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            if os.readlink(entry/'exe') != ROBOT_APP_PATH:
                continue
            status = (entry/'status').read_text(encoding='utf-8')
            lines = [line for line in status.splitlines() if line.startswith('Uid:')]
            if len(lines) != 1 or len(lines[0].split()) != 5:
                raise ValueError('robot_app_uid_not_available')
            matches.append(int(lines[0].split()[2]))
        except (FileNotFoundError, ProcessLookupError):
            continue
        except PermissionError as exc:
            raise RuntimeError('robot_app_uid_not_observable') from exc
    if len(matches) != 1 or matches[0] != uid:
        raise RuntimeError('robot_app_cannot_read_private_task_or_not_unique')
    return matches[0]


def isolate_event_stdout():
    """Keep the JSON pipe on a private fd and route native fd 1 to stderr.

    Call before importing or initializing ROSA. Native libraries may write to
    fd 1 directly, so Python-only stdout redirection is insufficient. This
    changes only this worker's descriptors and never discards a log line.
    """
    output = sys.stdout.fileno()
    error = sys.stderr.fileno()
    if output != 1 or error != 2:
        raise RuntimeError('worker_standard_descriptors_unexpected')
    sys.stdout.flush()
    event_fd = os.dup(output)
    try:
        os.dup2(error, output)
    except BaseException:
        os.close(event_fd)
        raise
    return event_fd


class WorkerChannel:
    def __init__(self, input_fd, output_fd, session_id, *, model_mode=False):
        if not isinstance(session_id, str) or not ID.fullmatch(session_id):
            raise ValueError('invalid_worker_session')
        if type(model_mode) is not bool:
            raise ValueError('invalid_worker_model_mode')
        self.input_fd, self.output_fd, self.session_id = input_fd, output_fd, session_id
        self.model_mode = model_mode
        self.model_deadline_monotonic_ns = None
        self.model_decision_sha256 = None
        self.failed = False
        self.signal_received = None
        os.set_blocking(input_fd, False)
        os.set_blocking(output_fd, False)

    def emit(self, **row):
        data = (json.dumps(row, separators=(',', ':'), allow_nan=False)+'\n').encode()
        try:
            if len(data) > MAX_LINE or os.write(self.output_fd, data) != len(data):
                self.failed = True
        except (OSError, BlockingIOError):
            self.failed = True

    def interrupted(self):
        if self.signal_received is not None:
            return 'worker_signal_' + str(self.signal_received)
        return 'worker_output_unavailable' if self.failed else None

    def check_model_permit(self):
        if self.model_mode and (type(self.model_deadline_monotonic_ns) is not int or
                                time.monotonic_ns() >= self.model_deadline_monotonic_ns or
                                not isinstance(self.model_decision_sha256, str) or
                                not re.fullmatch('[0-9a-f]{64}', self.model_decision_sha256)):
            raise RuntimeError('model_permission_missing_or_expired')

    def prepare_uuid(self, goal_id, *, check_live=None):
        if self.interrupted():
            raise RuntimeError(self.interrupted())
        nonce = uuid.uuid4().hex
        request = {'event': 'uuid_request', 'session_id': self.session_id,
                   'goal_id': goal_id, 'challenge': nonce}
        self.emit(**request)
        if self.failed:
            raise RuntimeError('uuid_request_not_delivered')
        # The model may need to start on Ada after the guard is already live.
        # The lease is checked during this wait; it does not extend the lease.
        deadline = time.monotonic()+(150.0 if self.model_mode else bridge.HANDSHAKE_S)
        buffer = bytearray()
        while time.monotonic() < deadline:
            if self.interrupted():
                raise RuntimeError(self.interrupted())
            if check_live is not None:
                check_live()
            readable, _, _ = select.select([self.input_fd], [], [], min(.1, deadline-time.monotonic()))
            if not readable:
                continue
            try:
                data = os.read(self.input_fd, MAX_LINE+1)
            except BlockingIOError:
                continue
            if not data:
                raise RuntimeError('coordinator_disconnected_before_goal')
            buffer.extend(data)
            if len(buffer) > MAX_LINE:
                raise ValueError('coordinator_ack_too_long')
            if b'\n' in buffer:
                line, extra = bytes(buffer).split(b'\n', 1)
                if extra:
                    raise ValueError('coordinator_ack_extra_data')
                ack = native.object_json(line.decode('utf-8'))
                expected = dict(request, event='uuid_ok')
                if self.model_mode:
                    if (not isinstance(ack, dict) or set(ack) != set(expected) |
                            {'deadline_monotonic_ns', 'decision_sha256'} or
                            any(ack.get(k) != v for k, v in expected.items()) or
                            type(ack.get('deadline_monotonic_ns')) is not int or
                            not isinstance(ack.get('decision_sha256'), str) or
                            not re.fullmatch('[0-9a-f]{64}', ack['decision_sha256'])):
                        raise ValueError('coordinator_model_ack_mismatch')
                    self.model_deadline_monotonic_ns = ack['deadline_monotonic_ns']
                    self.model_decision_sha256 = ack['decision_sha256']
                    self.check_model_permit()
                elif ack != expected:
                    raise ValueError('coordinator_ack_mismatch')
                if self.interrupted():
                    raise RuntimeError(self.interrupted())
                return
        raise TimeoutError('coordinator_ack_timeout')


class LeaseProxy:
    """The host remains sole owner of the shared lease file."""
    def __init__(self, path, initial, channel, manifest):
        self.path = Path(path)
        if (not self.path.is_absolute() or self.path.parts[:2] != ('/', 'tmp') or
                '..' in self.path.parts or self.path.suffix != '.json'):
            raise ValueError('invalid_shared_lease_path')
        self.initial, self.channel, self.manifest = initial, channel, manifest
        self.stage_receipt = None

    def synchronize_uuid(self, goal_id, _exchange):
        self.channel.prepare_uuid(goal_id, check_live=lambda: native.check_lease_current(self.path, time.monotonic))
        native.check_lease_current(self.path, time.monotonic)
        if self.channel.interrupted(): raise RuntimeError(self.channel.interrupted())
        staging.verify_staged(self.manifest, self.stage_receipt)
        # File read can block while the guard dies; require a still-current
        # lease and an uninterrupted channel immediately before returning to
        # create_goal_request. This does not make a later wire send atomic.
        if self.channel.interrupted(): raise RuntimeError(self.channel.interrupted())
        native.check_lease_current(self.path, time.monotonic)
        # Same Motion clock is already required by the shared lease. This
        # checks immediately before returning to ROSA; wire delivery is not
        # atomic with this check and stopping is not certified.
        self.channel.check_model_permit()

    def fail(self):
        # Do not write the host's lease: that could race with its renewer. The
        # host expires the lease on this event or when this worker disappears.
        self.channel.emit(event='worker_finished', session_id=self.channel.session_id)


def run(payload, channel, *, verified_provenance=None):
    # Check before reading a candidate, importing ROSA or sending anything.
    if verified_provenance is None:
        arm.physical_release_gate()
    else:
        arm.require_verified_stream(verified_provenance, 'worker', channel.session_id)
    fields = {'manifest', 'urdf_text', 'transmissions_text', 'lease_path',
              'session_id', 'intent_path', 'intent_uid'}
    if (not isinstance(payload, dict) or set(payload) not in (fields, fields | {'model_mode'}) or
            payload.get('model_mode', False) is not channel.model_mode or
            ('model_mode' in payload and payload['model_mode'] is not True)):
        raise ValueError('invalid_worker_payload')
    if payload['session_id'] != channel.session_id:
        raise ValueError('worker_session_mismatch')
    previous = {}
    def note_signal(signum, _frame):
        channel.signal_received = signum
    def install_handlers():
        for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            signal.signal(signum, note_signal)
    try:
        for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            previous[signum] = signal.getsignal(signum)
        install_handlers()
        manifest = payload['manifest']
        lease = LeaseProxy(payload['lease_path'], manifest['input']['reference_20d'], channel, manifest)
        if os.environ.get('HW_TYPE') != 'cruzr_s2_v1_sps':
            raise RuntimeError('worker_hardware_profile_mismatch')
        expected = {URDF_PATH: manifest['input']['urdf_sha256'],
                    SPS_PATH: manifest['input']['transmissions_sha256'],
                    META_MOVE_PATH: manifest['expected_meta_move_sha256']}
        for path, digest in expected.items():
            if hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest:
                raise RuntimeError('worker_installed_hash_mismatch:' + path)
        require_robot_app_can_read_private_task()
        if channel.interrupted(): raise RuntimeError(channel.interrupted())
        native.check_lease_current(lease.path, time.monotonic)
        receipt = staging.stage_task(manifest, payload['urdf_text'], payload['transmissions_text'],
                                     intent_path=payload['intent_path'], session_id=channel.session_id,
                                     intent_owner_uid=payload['intent_uid'])
        lease.stage_receipt = receipt
        channel.emit(event='stage_receipt', session_id=channel.session_id, receipt=receipt)
        if channel.interrupted():
            raise RuntimeError('stage_receipt_or_signal_no_goal:' + channel.interrupted())
        native.check_lease_current(lease.path, time.monotonic)
        # Uses the reviewed native box transport, source fingerprints, acceptance,
        # UUID targeted cancel and expiry checks; no auto retry or HOME.
        return bridge.run_guarded_once(lease, None, manifest, payload['urdf_text'],
                                       payload['transmissions_text'], channel.emit,
                                       interrupted=channel.interrupted,
                                       after_transport_ready=install_handlers,
                                       verified_provenance=verified_provenance)
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


def main():
    print('BLOCKED: native worker requires physical review; no goal sent', file=sys.stderr)
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
