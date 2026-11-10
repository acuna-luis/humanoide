#!/usr/bin/env python3
"""Motion-host integration check: PC heartbeat, real guard and read-only worker.

Never starts the wrist coordinator, stages a task, constructs an action goal or
calls an action server. Ordinary mode hands a synthetic UUID to the guard;
heartbeat mode hands over no UUID and never requests cancellation. Neither
mode proves physical braking or qualifies VLA control.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import select
import subprocess
import sys
import tempfile
import time
import uuid

import arm_from_pico_supervised as arm
import arm_native_lease_bridge as bridge
import pico_wrist_docker_launcher as launch
import pico_wrist_pc_heartbeat as heartbeat
import prepare_pico_wrist_native_probe as probe
import scenario1_action_client as native


def _worker_line(process, timeout):
    deadline = time.monotonic() + timeout
    fd = process.stdout.fileno()
    os.set_blocking(fd, False)
    data = bytearray()
    while time.monotonic() < deadline:
        readable, _, _ = select.select([fd], [], [], max(0, deadline-time.monotonic()))
        if not readable:
            break
        try:
            block = os.read(fd, 4097)
        except BlockingIOError:
            continue
        if not block:
            raise RuntimeError('readonly_worker_closed_without_result')
        data.extend(block)
        if len(data) > 4096:
            raise ValueError('readonly_worker_output_too_large')
        if b'\n' in data:
            line, _, rest = bytes(data).partition(b'\n')
            if rest:
                raise ValueError('readonly_worker_extra_output')
            return native.object_json(line.decode('utf-8'))
    raise TimeoutError('readonly_worker_timeout')


def check(payload):
    required = {'session', 'manifest', 'urdf_text', 'transmissions_text', 'guard_source', 'worker_source'}
    diagnostic = isinstance(payload, dict) and set(payload) in (
        required | {'guard_heartbeat', 'guard_sha256'},
        required | {'guard_heartbeat', 'guard_sha256', 'model_diagnostic'})
    model_diagnostic = diagnostic and payload.get('model_diagnostic') is True
    if not isinstance(payload, dict) or (set(payload) != required and not diagnostic):
        raise ValueError('invalid_passive_payload')
    if diagnostic and (payload['guard_heartbeat'] is not True or
                       not isinstance(payload['guard_source'], str) or
                       not isinstance(payload['guard_sha256'], str) or
                       hashlib.sha256(payload['guard_source'].encode('utf-8')).hexdigest() != payload['guard_sha256']):
        raise ValueError('passive_guard_digest_mismatch')
    if diagnostic and 'model_diagnostic' in payload and not model_diagnostic:
        raise ValueError('invalid_passive_model_diagnostic')
    session = payload['session']
    arm.validate_preflight(session, 0, dry_run=True)
    manifest = payload['manifest']
    probe.validate(manifest, payload['urdf_text'], payload['transmissions_text'])
    for key in ('guard_source', 'worker_source'):
        source = payload[key]
        if not isinstance(source, str) or not 0 < len(source) < 1_000_000:
            raise ValueError('invalid_' + key)
        compile(source, '<passive-check-source>', 'exec')

    output = launch.HostOutput(sys.stdout.fileno())
    pc = guard = worker = pipe = lease = None
    launch.pc_preflight_handoff(session, output, sys.stdin.fileno())
    if not output.emit({'event': 'HOST_HEARTBEAT_READY', 'session_id': session['session_id']}):
        raise RuntimeError('operator_output_unavailable')
    if model_diagnostic:
        pc = heartbeat.PcHeartbeat(sys.stdin.fileno(), session['session_id'], output.emit,
                                   model_mode=True)
    else:
        pc = heartbeat.PcHeartbeat(sys.stdin.fileno(), session['session_id'], output.emit)
    try:
        pc.await_ready(3)
        app, ros = launch.discover_containers()
        with tempfile.TemporaryDirectory(prefix='pico-full-passive-', dir='/tmp') as directory:
            try:
                launch.verify_shared_tmp(directory, app)
                scope = ({'role':'guard', 'session_id':session['session_id'],
                          'source_sha256':payload['guard_sha256']} if diagnostic else None)
                try:
                    if diagnostic:
                        guard = launch.start_streamed(ros, '/opt/ros/humble/setup.bash',
                            payload['guard_source'], session, stderr=subprocess.DEVNULL, verified=scope)
                    else:
                        guard = launch.start_streamed(ros, '/opt/ros/humble/setup.bash',
                            payload['guard_source'], session, stderr=subprocess.DEVNULL)
                except launch.StreamStartUncertain as exc:
                    # This process has never received a UUID. Preserve its
                    # handle for best-effort cleanup; uncertain delivery is
                    # still an error, not proof of remote termination.
                    guard = exc.process
                    raise
                lease = bridge.GuardLease(directory, manifest['input']['reference_20d'],
                    lambda: guard.poll() is None and pc.alive() and not output.failed,
                    session_id=session['session_id'])
                pipe = bridge.GuardPipe(guard, lease, time.monotonic()-session['age_at_handoff_s'],
                                        enable_guard_heartbeat=diagnostic)
                pipe.await_ready(26)
                request = {'lease_path': str(lease.path), 'goal': manifest['candidate']['goal']}
                worker = launch.start_streamed(app, '/opt/walker/setup.bash',
                    payload['worker_source'], request, stderr=subprocess.DEVNULL)
                result = _worker_line(worker, 8)
                expected_keys = {'event', 'fingerprints', 'goal_format_valid', 'lease_fresh', 'monotonic'}
                if (set(result) != expected_keys or result['event'] != 'NATIVE_READONLY_READY' or
                        result['fingerprints'] != native.SUPPORTED_NATIVE_CLASSES or
                        result['goal_format_valid'] is not True or result['lease_fresh'] is not True or
                        type(result['monotonic']) not in (int, float) or
                        not math.isfinite(result['monotonic']) or
                        not 0 <= time.monotonic()-result['monotonic'] <= 1.0):
                    raise RuntimeError('native_worker_check_failed')
                if worker.wait(timeout=2) != 0:
                    raise RuntimeError('native_readonly_worker_failed')
                model_permit = None
                if model_diagnostic:
                    # This identifier is *only* a correlation token on the PC
                    # heartbeat. Never hand it to the guard or any ROS client.
                    correlation_id = str(uuid.uuid4())
                    if not output.emit({'event':'PASSIVE_MODEL_INFERENCE_READY',
                                        'session_id':session['session_id']}):
                        raise RuntimeError('passive_model_start_delivery_failed')
                    pc.begin_model_permit(correlation_id, manifest['candidate']['xml_sha256'])
                    initial_sequence = pipe.heartbeat_sequence
                    end = time.monotonic() + 140.0
                    while time.monotonic() < end:
                        if lease.goal_id is not None or not pc.alive() or output.failed:
                            raise RuntimeError('passive_model_guard_state_changed')
                        pipe.checked_snapshot()
                        model_permit = pc.permit_snapshot()
                        if model_permit is not None:
                            if (model_permit.get('goal_id') != correlation_id or
                                    model_permit.get('task_sha256') != manifest['candidate']['xml_sha256']):
                                raise ValueError('passive_model_permit_identity_mismatch')
                            if pipe.heartbeat_sequence - initial_sequence >= 2:
                                break
                        time.sleep(.05)
                    if model_permit is None:
                        raise TimeoutError('passive_model_permit_timeout')
                    pulses = pipe.heartbeat_sequence - initial_sequence
                    if pulses < 2 or lease.goal_id is not None:
                        raise RuntimeError('passive_model_guard_not_sustained')
                    pipe.checked_snapshot()
                elif diagnostic:
                    # No UUID is handed off: even a fault has no goal that the
                    # guard could cancel. The heartbeat timeout is only enforced
                    # after a UUID, so this is not a watchdog-expiry test.
                    initial_sequence = pipe.heartbeat_sequence
                    end = time.monotonic() + 3.0
                    while time.monotonic() < end:
                        if lease.goal_id is not None or not pc.alive() or output.failed:
                            raise RuntimeError('passive_heartbeat_state_changed')
                        pipe.checked_snapshot()
                        time.sleep(.05)
                    pulses = pipe.heartbeat_sequence - initial_sequence
                    if pulses < 2 or lease.goal_id is not None:
                        raise RuntimeError('passive_heartbeat_not_sustained')
                else:
                    # The ordinary passive mode exercises only a synthetic
                    # guard handshake; it is never passed to ROS.
                    synthetic = str(uuid.uuid4())
                    lease.synchronize_uuid(synthetic, pipe.exchange)
                if not pc.alive() or not lease.guard_alive() or output.failed:
                    raise RuntimeError('passive_connection_not_live')
                native.check_lease(lease.path, time.monotonic())
                stop_clean = pipe.stop()
                guard.wait(timeout=4)
                pipe.thread.join(3)
                if not stop_clean or pipe.thread.is_alive() or guard.returncode != 0 or not lease.failed:
                    raise RuntimeError('guard_did_not_stop_cleanly')
                try:
                    native.check_lease(lease.path, time.monotonic())
                except RuntimeError:
                    pass
                else:
                    raise RuntimeError('lease_not_revoked')
                if diagnostic:
                    report = {'status': ('PASS_PC_MODEL_GUARD_PERMIT_NO_GOAL' if model_diagnostic else
                                         'PASS_PC_HOST_GUARD_HEARTBEAT_NO_GOAL'),
                            'movement_commands': 0, 'action_goals_created': 0,
                            'uuid_handshakes': 0, 'cancel_requests': 0,
                            'heartbeat_pulses_sent': pulses, 'physical_control_qualified': False,
                            'physical_stop_verified': False,
                            'limitations': ['no per-heartbeat acknowledgement',
                                'heartbeat expiry enforcement requires a handed-off UUID',
                                'no cancellation, action goal or physical movement',
                                'does not reproduce the original trajectory']}
                    if model_diagnostic:
                        report.update(decision_sha256=model_permit['decision_sha256'],
                                      model_permit_received=True,
                                      correlation_id_never_handed_to_guard=True)
                        report['limitations'].extend(['no model command is sent to an action server',
                            'Vision to PC image age is not measured',
                            'no real ROS goal, UUID handoff, cancellation or braking'])
                    return report
                return {'status': 'PASS_PC_HOST_GUARD_READONLY_NATIVE',
                        'movement_commands': 0, 'action_goals_created': 0,
                        'physical_control_qualified': False,
                        'physical_stop_verified': False,
                        'limitations': ['no real action client or goal',
                            'no staging or physical motion',
                            'no cross-container cancellation or braking test']}
            finally:
                if pipe is not None:
                    try: pipe.stop()
                    except Exception: pass
                for child in (worker, guard):
                    if child is not None:
                        if child.poll() is None:
                            child.terminate()
                            try: child.wait(timeout=3)
                            except subprocess.TimeoutExpired:
                                child.kill(); child.wait(timeout=3)
                        for stream in (child.stdin, child.stdout):
                            if stream is not None:
                                stream.close()
    finally:
        pc.close()


if __name__ == '__main__':
    raise SystemExit('Use the passive wrapper; no physical run exists.')
