#!/usr/bin/env python3
"""Motion-host passive guard/lease check. No ROS goal is ever constructed.

Run in the ROS2 container via the review wrapper; the child guard and lease
consumer must share this Linux host's monotonic clock. A synthetic UUID is
whitelisted but never published to ROS. Killing the child is a software-only
fault injection: it does not measure physical braking or enable VLA control.
"""
import json
import math
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

import arm_from_pico_supervised as arm
import arm_native_lease_bridge as bridge
import pico_wrist_action_client as native


def require_persisted_revocation(lease):
    """Distinguish a written zero deadline from natural expiry or I/O failure."""
    if not lease._async_failure_done.wait(3):
        raise RuntimeError('lease_revocation_not_observed')
    if lease._async_failure_error is not None:
        raise RuntimeError('lease_revocation_write_failed')
    row = native.object_json(Path(lease.path).read_text())
    deadline = row.get('deadline')
    if set(row) != {'deadline'} or type(deadline) not in (int, float) or deadline != 0:
        raise RuntimeError('lease_revocation_not_persisted')


def validate_payload(payload):
    if (not isinstance(payload, dict) or set(payload) != {'session', 'initial', 'guard_source'}
            or not isinstance(payload['session'], dict) or not isinstance(payload['guard_source'], str)):
        raise ValueError('invalid_check_payload')
    session, initial = payload['session'], payload['initial']
    arm.validate_preflight(session, 0, dry_run=True)
    if not isinstance(initial, dict) or set(initial) != set(arm.BODY):
        raise ValueError('invalid_reference_20d')
    values = arm.joint_state({'name': list(initial), 'position': list(initial.values()),
                              'velocity': [0.0]*len(initial)}, arm.BODY)
    arm.check_sps_limits(values)
    if not payload['guard_source'] or len(payload['guard_source']) > 1_000_000:
        raise ValueError('invalid_guard_source')
    return session, initial


def check(payload):
    session, initial = validate_payload(payload)
    compile(payload['guard_source'], '<passive-arm-guard>', 'exec')
    started = time.monotonic()
    age = session['age_at_handoff_s']
    if type(age) not in (int, float) or not math.isfinite(age) or age < 0:
        raise ValueError('invalid_inventory_age')
    child = None
    pipe = None
    # /tmp is temporary and must be independently verified shared before any
    # future cross-container physical use; here both processes use one container.
    with tempfile.TemporaryDirectory(prefix='pico-arm-bridge-check-', dir='/tmp') as directory:
        try:
            sentinel = 'ARM_GUARD_END_' + uuid.uuid4().hex
            if sentinel in payload['guard_source']:
                raise ValueError('guard_source_sentinel_collision')
            bootstrap = ('import sys\nparts=[]\nfor line in sys.stdin:\n'
                         ' if line.rstrip("\\n")=='+repr(sentinel)+': break\n'
                         ' parts.append(line)\n'
                         'else: raise SystemExit("guard source incomplete")\n'
                         'exec(compile("".join(parts),"<arm-guard>","exec"))\n')
            child = subprocess.Popen([sys.executable, '-B', '-u', '-c', bootstrap],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, bufsize=0)
            message = (payload['guard_source'] + '\n' + sentinel + '\n' +
                       json.dumps(session, allow_nan=False) + '\n').encode()
            view = memoryview(message)
            while view:
                count = child.stdin.write(view)
                if type(count) is not int or count <= 0:
                    raise BrokenPipeError('guard_session_write_failed')
                view = view[count:]
            child.stdin.flush()
            lease = bridge.GuardLease(directory, initial, lambda: child.poll() is None,
                                      session_id=session['session_id'])
            pipe = bridge.GuardPipe(child, lease, started-age)
            pipe.await_ready(26)
            # A random synthetic identifier is never passed to an action client.
            synthetic_goal = str(uuid.uuid4())
            lease.synchronize_uuid(synthetic_goal, pipe.exchange)
            keepalive_end = time.monotonic()+.8
            while time.monotonic() < keepalive_end:
                if pipe.failure or child.poll() is not None:
                    raise RuntimeError('guard_failed_during_observation')
                native.check_lease_current(lease.path, time.monotonic)
                time.sleep(.05)
            # There is no action or moving task to interrupt in this check.
            child.terminate()
            child.wait(timeout=3)
            pipe.thread.join(3)
            if pipe.thread.is_alive() or not lease.failed:
                raise RuntimeError('guard_loss_not_observed')
            # The transport revokes asynchronously on loss. Observe its
            # completion before claiming the on-disk lease was revoked.
            require_persisted_revocation(lease)
            try:
                native.check_lease_current(lease.path, time.monotonic)
            except RuntimeError:
                pass
            else:
                raise RuntimeError('lease_not_revoked_on_guard_exit')
            return {'status': 'PASS_PASSIVE_GUARD_UUID_AND_LEASE_REVOCATION',
                    'synthetic_uuid': synthetic_goal, 'movement_commands': 0,
                    'physical_control_qualified': False, 'physical_stop_verified': False,
                    'limits': ['guard process termination is not servo braking',
                               'no action goal was created or sent',
                               'cross-container shared lease path was not tested',
                               'transport transit before session receipt is not measured']}
        finally:
            if pipe is not None:
                pipe.stop()
            if child is not None and child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    child.kill(); child.wait(timeout=3)
            if child is not None:
                for stream in (child.stdin, child.stdout):
                    if stream is not None:
                        stream.close()


if __name__ == '__main__':
    raise SystemExit('Use the passive wrapper; direct execution is disabled.')
