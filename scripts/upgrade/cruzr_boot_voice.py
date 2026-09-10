#!/usr/bin/env python3
"""Vision host: initial-boot announcement only; no restart, mode or motion calls."""
import argparse
import ast
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import shlex
import socket
import subprocess
import time

import cruzr_cc_start_when_ready as gate

CC = 'walker-system.control_center-1'
ROS = 'walker-ros.ros2-1'
GATE_PATH = '/etc/walker/boot/cruzr_cc_start_when_ready.py'


def native(command, timeout):
    return subprocess.run(['docker', 'exec', CC, 'bash', '-lc',
        'source /opt/walker/setup.bash && export ROS2CLI_DISABLE_DAEMON=1 && ' +
        shlex.join(['timeout', '--kill-after=1', str(max(0.1, timeout-1)), *command])],
        capture_output=True, text=True, timeout=timeout+2)


def snapshot():
    try:
        # This mode reads /proc and the log only. Sourcing the ROS environment
        # repeatedly adds seconds to each observation without providing data.
        result = subprocess.run(['docker', 'exec', CC, 'python3', GATE_PATH,
                                 '--control-snapshot'], capture_output=True,
                                text=True, timeout=5)
        if result.returncode == 0:
            return json.loads(result.stdout)
    except (OSError, subprocess.TimeoutExpired, ValueError):
        pass
    return None


def motion_probe(timeout):
    try:
        result = native(gate.PROBE, timeout)
        return gate.response_ok(result.returncode, result.stdout)
    except (OSError, subprocess.TimeoutExpired):
        return False


def safety_sample(topic, timeout):
    # The native ROSA CLI in v0.2.0 crashes decoding std_msgs/UInt8.
    # Read the three embedded topics in the installed ROS 2 container instead.
    if topic not in {'/emb/estop_key_state', '/emb/servo_estop_key_state', '/emb/chrg_input_status'}:
        return None
    try:
        command = ['ros2', 'topic', 'echo', '--once', '--no-daemon',
                   '--qos-durability', 'volatile', topic]
        result = subprocess.run(['docker', 'exec', ROS, 'bash', '-lc',
            'source /opt/ros/humble/setup.bash && export ROS2CLI_DISABLE_DAEMON=1 && ' +
            shlex.join(['timeout', '--kill-after=1', str(max(0.1, timeout-2)), *command])],
            capture_output=True, text=True, timeout=timeout+1)
        match = re.fullmatch(r'\s*data: ([01])\s*\n---\s*', result.stdout)
        if result.returncode == 0 and match:
            return {'data': int(match[1])}
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def cameras(timeout):
    def read(topic):
        try:
            result = native(['rosa', 'topic', 'echo', '--once', '--no-daemon',
                             '--qos-durability', 'volatile', topic], timeout)
            if result.returncode == 0:
                return gate.camera_stamp(json.loads(result.stdout))
        except (OSError, subprocess.TimeoutExpired, ValueError):
            pass
        return None
    with ThreadPoolExecutor(max_workers=6) as pool:
        return dict(zip(gate.CAMERA_TOPICS, pool.map(read, gate.CAMERA_TOPICS)))


def release_ready():
    return gate.release_ready(read_snapshot=snapshot, read_sample=safety_sample)


def speech_result_ok(returncode, output):
    # Exact result observed on this v0.2.0 TTS server: "Success", not "SUCCEED".
    replies = re.findall(r'^Result: result=(.+), status=(\d+)$', output, re.M)
    if returncode != 0 or len(replies) != 1 or replies[0][1] != '4':
        return False
    try:
        result = ast.literal_eval(replies[0][0])['result']
        return (result['desc'] == 'Success' and result['state'] == 1001000
                and result['msg_type'] == 'sys_state_msgs::msg::SpeechState')
    except (ValueError, SyntaxError, TypeError, KeyError):
        return False


def announce():
    try:
        info = native(['rosa', 'action', 'info', gate.VOICE_ACTION], 5)
        if (info.returncode != 0
                or re.findall(r'^Action: (.*)$', info.stdout, re.M) != ['sys_task_msgs/action/Tts']
                or re.findall(r'^Action server count: (\d+)$', info.stdout, re.M) != ['1']):
            return False
        if not motion_probe(8) or not release_ready():
            return False
        goal = {'type': 1, 'is_break': True, 'file_path': '', 'text': gate.VOICE_TEXT,
                'speaker': '', 'speed': 50, 'volume': 80, 'pitch': 50,
                'language': 'en', 'format': 'wav', 'need_save': False}
        result = native(['rosa', 'action', 'send_goal', gate.VOICE_ACTION,
                         'sys_task_msgs/action/Tts', json.dumps(goal)], 15)
        gate.log('VOICE_COMMAND_RC=' + str(result.returncode))
        gate.log('VOICE_COMMAND_RESULT=' + json.dumps(result.stdout[-2000:]))
        ok = speech_result_ok(result.returncode, result.stdout)
    except (OSError, subprocess.TimeoutExpired):
        ok = False
    gate.log('VOICE_RESULT=' + ('succeeded' if ok else 'failed_no_retry'))
    return ok


def check_ready(deadline):
    if not gate.wait_ready(check=motion_probe, max_wait=max(0, deadline-time.monotonic())):
        return False
    if not gate.wait_cameras(check=cameras, max_wait=max(0, deadline-time.monotonic())):
        return False
    if time.monotonic() >= deadline or not motion_probe(min(8, deadline-time.monotonic())):
        return False
    if not release_ready():
        return False
    return time.monotonic() < deadline


def visual_ready_checker():
    # Keep the initial process identity; a container restart must not inherit
    # a screen permission from the previous startup.
    initial = snapshot()
    previous = {}

    def ready():
        if not gate.initial_release_state(initial) or snapshot() != initial:
            return False
        # Independent read-only probes run together so a healthy refresh does not
        # spend three successive CLI startup delays with the screen lease aging.
        with ThreadPoolExecutor(max_workers=3) as pool:
            camera_future = pool.submit(cameras, 6)
            motion_future = pool.submit(motion_probe, 6)
            release_future = pool.submit(release_ready)
            current = camera_future.result()
            motion_ok = motion_future.result()
            release_ok = release_future.result()
        if not all(type(current.get(t)) is int and current[t] > previous.get(t, 0)
                   for t in gate.CAMERA_TOPICS):
            return False
        previous.update(current)
        return motion_ok and release_ok and snapshot() == initial
    return ready


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--watch', action='store_true', help='Once per host boot, wait and announce')
    mode.add_argument('--check', action='store_true', help='Read-only check, no sound by default')
    mode.add_argument('--prepare-display', action='store_true', help='Install the known screen addition only')
    parser.add_argument('--announce', action='store_true', help='With --check: one explicit voice test')
    parser.add_argument('--visual', action='store_true', help='With --check: show readiness until release (no motion)')
    args = parser.parse_args(argv)
    if args.announce and not args.check:
        parser.error('--announce requires --check')
    if args.visual and not args.check:
        parser.error('--visual requires --check')
    if socket.gethostname() != 'vision':
        gate.log('BLOCKED=not_vision_host')
        return 78
    if args.prepare_display:
        import cruzr_boot_visual as visual
        ok = visual.prepare()
        gate.log('VISUAL_INSTALL=' + ('verified' if ok else 'failed'))
        return 0 if ok else 78
    if args.watch and not gate.claim_boot_voice():
        gate.log('VOICE_SKIPPED=already_attempted_this_host_boot')
        return 0
    deadline = time.monotonic() + 420
    while time.monotonic() < deadline:
        current = snapshot()
        if gate.initial_release_state(current):
            break
        if current and current[1] and current[1][-1] not in {'TmpState', 'waitBootReady', 'Recover'}:
            gate.log('NOT_READY=not_initial_boot_release; no_recovery_attempt')
            return 75
        gate.log('WAITING=initial_Control_Center_boot')
        time.sleep(3)
    else:
        gate.log('NOT_READY=initial_boot_timeout')
        return 75
    if not check_ready(deadline):
        return 75
    gate.log('RELEASE_TECHNICAL_CHECK=passed; movement_commands=0')
    if (args.watch or args.announce) and not announce():
        return 75
    if args.watch or args.visual:
        import cruzr_boot_visual as visual
        if not visual.prepare():
            gate.log('VISUAL_UNAVAILABLE; voice_readiness_unchanged')
            return 75
        return 0 if visual.hold(visual_ready_checker()) else 75
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
