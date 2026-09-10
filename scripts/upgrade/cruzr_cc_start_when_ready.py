#!/usr/bin/env python3
"""Start the unchanged v0.2.0 Control Center after Motion and cameras answer.

Runs inside the Control Center container, after the normal Walker entrypoint.
Does not publish motion, change E-stops, restart containers or skip self-check.
Control Center retains its normal boot behaviour, including internal HOME.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import fcntl
import hashlib
import json
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
CAMERA_TOPICS = (
    '/sensor/camera/waist_front_rgbd/color/raw',
    '/sensor/camera/stereo_left/image/raw',
    '/sensor/camera/stereo_right/image/raw',
    '/sensor/camera/chassis_front_rgbd/color/raw',
    '/sensor/camera/fisheye_left/image/raw',
    '/sensor/camera/fisheye_right/image/raw',
)
CC_LOG = Path('/etc/walker/log/system/cc_main.latest.log')
BOOT_ID = Path('/proc/sys/kernel/random/boot_id')
VOICE_BOOT_RECORD = Path('/etc/walker/boot/cc_ready_voice_boot_id')
VOICE_TEXT = 'Ready to release the emergency stop.'
VOICE_ACTION = '/sys/speech/tts'


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
        result = subprocess.run(['timeout', '--kill-after=1', str(max(0.1, timeout_s-1)), *PROBE],
                                capture_output=True, text=True, timeout=timeout_s+1)
        return response_ok(result.returncode, result.stdout)
    except (OSError, subprocess.TimeoutExpired):
        return False


def sample(topic, timeout_s):
    """New volatile subscription; no cached daemon and no motion publication."""
    try:
        result = subprocess.run(
            ['timeout', '--kill-after=1', str(max(0.1, timeout_s-1)),
             'rosa', 'topic', 'echo', '--once', '--no-daemon',
             '--qos-durability', 'volatile', topic],
            capture_output=True, text=True, timeout=timeout_s+1)
        if result.returncode == 0:
            return json.loads(result.stdout)
    except (OSError, subprocess.TimeoutExpired, ValueError):
        pass
    return None


def camera_stamp(message):
    try:
        stamp = message['header']['stamp']
        sec, nano = stamp['sec'], stamp['nanosec']
        if (type(sec) is int and sec > 0 and type(nano) is int
                and 0 <= nano < 1000000000
                and message['width'] > 0 and message['height'] > 0):
            return sec * 1000000000 + nano
    except (TypeError, KeyError):
        pass
    return None


def camera_round(timeout_s):
    with ThreadPoolExecutor(max_workers=len(CAMERA_TOPICS)) as pool:
        messages = list(pool.map(lambda topic: sample(topic, timeout_s), CAMERA_TOPICS))
    return {topic: camera_stamp(message) for topic, message in zip(CAMERA_TOPICS, messages)}


def wait_cameras(max_wait=MAX_WAIT_S, check=camera_round, clock=time.monotonic,
                 pause=time.sleep, emit=log):
    deadline = clock() + max_wait
    previous = None
    while clock() < deadline:
        current = check(min(8.0, deadline-clock()))
        if clock() >= deadline:
            break
        complete = (set(current) == set(CAMERA_TOPICS)
                    and all(type(value) is int and value > 0 for value in current.values()))
        if complete and previous and all(current[t] > previous[t] for t in CAMERA_TOPICS):
            emit('CAMERA_RESPONSES=2/2; topics=6; advancing_timestamps=1')
            return True
        previous = current if complete else None
        emit('CAMERA_RESPONSES=' + ('1/2' if complete else '0/2'))
        pause(min(5.0, max(0, deadline-clock())))
    emit('BLOCKED=cameras_not_ready; Control Center not started; no movement command')
    return False


def current_control_log():
    """Require the log to be open by the currently running vendor process.

    cc_main.latest.log alone may still refer to the PREVIOUS power cycle while
    the startup gate is waiting. Do not qualify that stale WaitEStopRelease.
    """
    try:
        target = CC_LOG.resolve(strict=True)
        owners = []
        for process in Path('/proc').glob('[0-9]*'):
            try:
                if (process/'exe').resolve() == BINARY and any(
                        fd.resolve() == target for fd in (process/'fd').iterdir()):
                    owners.append((process.name, (process/'stat').read_text().rsplit(')', 1)[1].split()[19]))
            except OSError:
                continue
        if len(owners) != 1:
            return None
        with target.open('rb') as stream:
            # Never approve using a suffix that could hide an earlier operating mode.
            data = stream.read(2000001)
        if len(data) > 2000000:
            return None
        text = re.sub(r'\x1b\[[0-9;]*m', '', data.decode('utf-8', errors='replace'))
        states = re.findall(r'sm state changed: .*?-> (\w+)', text)
        return (owners[0], str(target)), states
    except (OSError, ValueError, IndexError):
        return None


def initial_release_state(snapshot):
    if not snapshot or not snapshot[1] or snapshot[1][-1] != 'WaitEStopRelease':
        return False
    # This is an INITIAL boot aid, never recovery after teleoperation or contact.
    return all(state in {'TmpState', 'waitBootReady', 'Recover', 'WaitEStopRelease'}
               for state in snapshot[1])


def release_ready(*, read_snapshot, read_sample):
    before = read_snapshot()
    if not initial_release_state(before):
        log('NOT_READY=control_center_not_in_initial_WaitEStopRelease')
        return False
    topics = ('/emb/estop_key_state', '/emb/servo_estop_key_state', '/emb/chrg_input_status')
    with ThreadPoolExecutor(max_workers=3) as pool:
        messages = list(pool.map(lambda topic: read_sample(topic, 10.0), topics))
    states = [m.get('data') if isinstance(m, dict) else None for m in messages]
    if states != [1, 0, 0] or not all(type(value) is int for value in states):
        log('NOT_READY=estop_servo_charger; measured=' + json.dumps(states))
        return False
    after = read_snapshot()
    if after != before or not initial_release_state(after):
        log('NOT_READY=control_center_changed_during_check')
        return False
    return True


def claim_boot_voice():
    """Only the first CC startup in this host boot may schedule the prompt.

    Record BEFORE waiting. A subsequent CC/container restart is a recovery,
    not another routine power-on, even if it creates a new vendor log.
    """
    try:
        boot_id = BOOT_ID.read_text().strip()
        if not re.fullmatch(r'[a-f0-9-]{36}', boot_id):
            raise ValueError('invalid boot id')
        with VOICE_BOOT_RECORD.open('a+') as record:
            fcntl.flock(record, fcntl.LOCK_EX)
            record.seek(0)
            if record.read().strip() == boot_id:
                return False
            record.seek(0)
            record.truncate()
            record.write(boot_id + '\n')
            record.flush()
            os.fsync(record.fileno())
        return True
    except (OSError, ValueError) as error:
        log('VOICE_DISABLED=boot_record_unavailable; ' + type(error).__name__)
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
    group.add_argument('--control-snapshot', action='store_true',
                       help='Print current vendor process and initial boot state as JSON')
    parser.add_argument('--timeout', type=float, default=MAX_WAIT_S)
    args = parser.parse_args(argv)
    if not 20 <= args.timeout <= MAX_WAIT_S:
        parser.error('--timeout must be between 20 and 420 seconds')
    deadline = time.monotonic() + args.timeout
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
    if args.control_snapshot:
        print(json.dumps(current_control_log()))
        return 0
    if not wait_ready(max_wait=max(0, deadline-time.monotonic())):
        return 75
    log('MOTION_READY=1')
    if not wait_cameras(max_wait=max(0, deadline-time.monotonic())):
        return 75
    if deadline-time.monotonic() <= 0 or not probe(min(12, deadline-time.monotonic())):
        log('BLOCKED=motion_lost_after_camera_check')
        return 75
    if time.monotonic() >= deadline:
        log('BLOCKED=readiness_deadline_exceeded')
        return 75
    if not args.start:
        log('CHECK_ONLY=1; vendor_process_not_started; movement_commands=0')
        return 0
    log('STARTING_VENDOR_CONTROL_CENTER=1; vendor_selfcheck_and_estop_logic_unchanged')
    os.execvp(COMMAND[0], COMMAND)


if __name__ == '__main__':
    raise SystemExit(main())
