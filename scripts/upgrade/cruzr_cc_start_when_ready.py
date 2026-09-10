#!/usr/bin/env python3
"""Start the unchanged v0.2.0 Control Center only after Motion answers.

Runs inside the Control Center container, after the normal Walker entrypoint.
Does not publish motion, change E-stops, restart containers or skip self-check.
Control Center retains its normal boot behaviour, including internal HOME.
"""
import argparse
import hashlib
import os
from pathlib import Path
import re
import subprocess
import time

BINARY = Path('/opt/walker/control_center/lib/control_center/control_center')
EXPECTED_SHA256 = '465b1a440875992b1a2562cde2ff452cc26b5d78bf06daa4e05460f8d9dccdf5'
COMMAND = ['rosa', 'run', 'control_center', 'control_center', '--', '--tbox-args',
           '--config', 'config/base.conf', '--config', 'config/cc.conf']
PROBE = ['rosa', 'service', 'call', '/self_check/x86/file_presence_check',
         'sys_task_msgs/srv/SelfCheckTask', '{"param":"{}"}']
MAX_WAIT_S = 420.0
PROBE_INTERVAL_S = 10.0
REQUIRED_RESPONSES = 3


def log(message):
    print('CRUZR_CC_READY_GATE '+message, flush=True)


def response_ok(returncode, output):
    # Fixed no-parameter readiness request: current vendor output, empty reasons.
    # A service name advertised in DDS, or passed=True inside diagnostic text,
    # does not count as a successful reply.
    replies = re.findall(r'^response: (.*)$', output, flags=re.M)
    return returncode == 0 and replies == [
        'sys_task_msgs.srv.SelfCheckTask.Response(passed=True, reason=[])']


def probe(timeout_s):
    try:
        result = subprocess.run(PROBE, capture_output=True, text=True, timeout=timeout_s)
        return response_ok(result.returncode, result.stdout)
    except (OSError, subprocess.TimeoutExpired):
        return False


def wait_ready(check=probe, clock=time.monotonic, pause=time.sleep, emit=log,
               max_wait=MAX_WAIT_S, interval=PROBE_INTERVAL_S):
    deadline = clock()+max_wait
    consecutive = 0
    while clock() < deadline:
        answered = check(min(12.0, deadline-clock()))
        # A late reply must not turn an expired readiness window into success.
        if clock() >= deadline:
            break
        consecutive = consecutive+1 if answered else 0
        emit(f'MOTION_RESPONSES={consecutive}/{REQUIRED_RESPONSES}')
        if consecutive == REQUIRED_RESPONSES:
            return True
        pause(min(interval, max(0, deadline-clock())))
    emit('BLOCKED=motion_not_ready; Control Center not started; no movement command')
    return False


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--check', action='store_true')
    group.add_argument('--start', action='store_true')
    args = parser.parse_args(argv)
    if os.environ.get('HW_TYPE') != 'cruzr_s2_v1':
        log('BLOCKED=unexpected_hardware')
        return 78
    try:
        actual = hashlib.sha256(BINARY.read_bytes()).hexdigest()
    except OSError:
        actual = ''
    if actual != EXPECTED_SHA256:
        log('BLOCKED=unreviewed_control_center_binary; review after software update')
        return 78
    if not wait_ready():
        return 75
    log('MOTION_READY=1')
    if not args.start:
        log('CHECK_ONLY=1; vendor_process_not_started; movement_commands=0')
        return 0
    log('STARTING_VENDOR_CONTROL_CENTER=1; vendor_selfcheck_and_estop_logic_unchanged')
    os.execvp(COMMAND[0], COMMAND)


if __name__ == '__main__':
    raise SystemExit(main())
