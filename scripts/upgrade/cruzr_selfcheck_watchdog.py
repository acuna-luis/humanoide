#!/usr/bin/env python3
"""Vision host: recover an initial boot stuck in SelfChecking after a monitor crash.

Signature (all required, 2026-09-18 incident): initial-boot Control Center in
SelfChecking for STUCK_S, no self-check result, StartMotion never started, and
walker-system.self_check_monitor-1 restarted after SelfChecking began.

Recovery: ask by voice for the main E-stop, wait until it is measured pressed,
restart only the Control Center container, wait for the new process to reach
the initial WaitEStopRelease and announce it. At most once per host boot.
It never releases an E-stop, calls StartMotion, changes modes or sends motion.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import time

import cruzr_boot_voice as voice
import cruzr_cc_start_when_ready as gate

CC = voice.CC
MONITOR = 'walker-system.self_check_monitor-1'
CC_LOG = Path('/etc/walker/log/system/cc_main.latest.log')
BOOT_RECORD = Path('/etc/walker/boot/selfcheck_watchdog_boot_id')
STUCK_S = 120.0
WATCH_S = 3 * 3600.0
ESTOP_WAIT_S = 1800.0
RESTART_WAIT_S = 480.0
POLL_S = 5.0
ALLOWED_STATES = {'TmpState', 'waitBootReady', 'Recover', 'WaitEStopRelease',
                  'EnterWorkMode', 'SelfChecking'}
PRESS_TEXT = ('Self check was interrupted. Press the emergency stop '
              'to restart the control center.')
READY_TEXT = 'Control center restarted. Ready to release the emergency stop.'
LINE = re.compile(r'^\w (\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d+) .*?sm state changed: .*?-> (\w+)')


def log(message):
    print('CRUZR_SELFCHECK_WATCHDOG '+message, flush=True)


def selfcheck_entry(text):
    """Local time of the last transition into SelfChecking, or None."""
    entry = None
    for line in text.splitlines():
        match = LINE.match(line)
        if match:
            entry = (datetime.strptime(match[1], '%Y-%m-%d %H:%M:%S.%f').astimezone()
                     if match[2] == 'SelfChecking' else None)
    return entry


def assess(snapshot, text, monitor_started, now):
    """Pure classification; returns (stuck, reason)."""
    if not snapshot or not snapshot[1]:
        return False, 'control_center_unreadable'
    states = snapshot[1]
    if states[-1] != 'SelfChecking':
        return False, 'state='+states[-1]
    if not set(states) <= ALLOWED_STATES:
        return False, 'not_initial_boot_path'
    entry = selfcheck_entry(text)
    if entry is None:
        return False, 'selfcheck_entry_not_found'
    tail = text[text.rfind('-> SelfChecking'):]
    if 'selfcheck result' in tail:
        return False, 'selfcheck_result_present'
    if 'StartMotion' in tail:
        return False, 'startmotion_started'
    if (now-entry).total_seconds() < STUCK_S:
        return False, 'selfchecking_for_%ds' % (now-entry).total_seconds()
    if monitor_started is None or monitor_started <= entry:
        return False, 'monitor_not_restarted_after_selfcheck'
    return True, 'selfcheck_monitor_restarted_result_lost'


def read_log():
    try:
        data = CC_LOG.read_bytes()[-2000000:]
        return re.sub(r'\x1b\[[0-9;]*m', '', data.decode('utf-8', errors='replace'))
    except OSError:
        return ''


def monitor_started():
    try:
        value = subprocess.run(['docker', 'inspect', '--format', '{{.State.StartedAt}}', MONITOR],
                               capture_output=True, text=True, timeout=10).stdout.strip()
        match = re.fullmatch(r'(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(\.\d+)?Z', value)
        if match:
            micro = (match[2] or '.0')[:7]
            return datetime.strptime(match[1]+micro, '%Y-%m-%dT%H:%M:%S.%f').replace(tzinfo=timezone.utc)
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def observe():
    snapshot = voice.snapshot()
    return snapshot, assess(snapshot, read_log(), monitor_started(), datetime.now().astimezone())


def safety():
    topics = ('/emb/estop_key_state', '/emb/servo_estop_key_state', '/emb/chrg_input_status')
    values = [voice.safety_sample(t, 10.0) for t in topics]
    return [v.get('data') if isinstance(v, dict) else None for v in values]


def speak(text):
    goal = {'type': 1, 'is_break': True, 'file_path': '', 'text': text,
            'speaker': '', 'speed': 50, 'volume': 80, 'pitch': 50,
            'language': 'en', 'format': 'wav', 'need_save': False}
    try:
        result = voice.native(['rosa', 'action', 'send_goal', gate.VOICE_ACTION,
                               'sys_task_msgs/action/Tts', json.dumps(goal)], 20)
        ok = voice.speech_result_ok(result.returncode, result.stdout)
    except (OSError, subprocess.TimeoutExpired):
        ok = False
    log('VOICE=' + ('succeeded' if ok else 'failed') + '; text=' + json.dumps(text))
    return ok


def claim_boot():
    try:
        boot_id = gate.BOOT_ID.read_text().strip()
        with BOOT_RECORD.open('a+') as record:
            fcntl.flock(record, fcntl.LOCK_EX)
            record.seek(0)
            if record.read().strip() == boot_id:
                return False
            record.seek(0)
            record.truncate()
            record.write(boot_id+'\n')
            record.flush()
            os.fsync(record.fileno())
        return True
    except OSError as error:
        log('DISABLED=boot_record_unavailable; '+type(error).__name__)
        return False


def wait_pressed(stuck_snapshot):
    deadline = time.monotonic()+ESTOP_WAIT_S
    confirmed = 0
    while time.monotonic() < deadline:
        snapshot, (stuck, reason) = observe()
        if snapshot != stuck_snapshot or not stuck:
            log('ABORT=control_center_changed_while_waiting; reason='+reason)
            return False
        measured = safety()
        # Main E-stop pressed and charger disconnected, twice in a row.
        confirmed = confirmed+1 if measured[0] == 1 and measured[2] == 0 else 0
        log('WAITING_ESTOP=' + json.dumps(measured) + '; confirmations=%d/2' % confirmed)
        if confirmed == 2:
            return True
        time.sleep(POLL_S)
    log('ABORT=estop_not_pressed_in_time; no_restart')
    return False


def restart_and_wait(stuck_snapshot):
    # Re-verify immediately before the only mutating call.
    snapshot, (stuck, reason) = observe()
    measured = safety()
    if snapshot != stuck_snapshot or not stuck or measured[0] != 1 or measured[2] != 0:
        log('ABORT=precondition_changed; reason=%s; safety=%s' % (reason, json.dumps(measured)))
        return False
    log('RESTARTING=%s; movement_commands=0' % CC)
    result = subprocess.run(['docker', 'restart', '--time', '10', CC],
                            capture_output=True, text=True, timeout=60)
    if result.returncode:
        log('RESTART_FAILED=' + json.dumps(result.stderr[-500:]))
        return False
    deadline = time.monotonic()+RESTART_WAIT_S
    while time.monotonic() < deadline:
        current = voice.snapshot()
        if current and current[0] != stuck_snapshot[0] and gate.initial_release_state(current):
            if gate.release_ready(read_snapshot=voice.snapshot, read_sample=voice.safety_sample):
                log('RECOVERED=new_control_center_in_WaitEStopRelease')
                speak(READY_TEXT)
                return True
        elif current and current[1] and not set(current[1]) <= ALLOWED_STATES - {'EnterWorkMode', 'SelfChecking'}:
            log('ATTENTION=new_control_center_left_initial_wait; state='+current[1][-1])
            return False
        time.sleep(POLL_S)
    log('ATTENTION=new_control_center_not_ready_in_time; keep_estop_pressed; full_power_cycle')
    return False


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--watch', action='store_true', help='Once per host boot, detect and recover')
    mode.add_argument('--check', action='store_true', help='Read-only classification')
    args = parser.parse_args(argv)
    if socket.gethostname() != 'vision':
        log('BLOCKED=not_vision_host')
        return 78
    if args.check:
        snapshot, (stuck, reason) = observe()
        log('STATE=%s; STUCK=%d; REASON=%s; safety=%s; movement=none restart=none' % (
            snapshot[1][-1] if snapshot and snapshot[1] else 'unknown',
            stuck, reason, json.dumps(safety())))
        return 0
    if not claim_boot():
        log('SKIPPED=already_ran_this_host_boot')
        return 0
    deadline = time.monotonic()+WATCH_S
    while time.monotonic() < deadline:
        snapshot, (stuck, reason) = observe()
        if stuck:
            break
        if snapshot and snapshot[1] and not set(snapshot[1]) <= ALLOWED_STATES:
            log('DONE=control_center_left_initial_boot; state=%s' % snapshot[1][-1])
            return 0
        time.sleep(POLL_S)
    else:
        log('DONE=watch_window_elapsed')
        return 0
    log('DETECTED=' + reason + '; no_startmotion; movement_commands=0')
    speak(PRESS_TEXT)
    if not wait_pressed(snapshot):
        return 75
    return 0 if restart_and_wait(snapshot) else 75


if __name__ == '__main__':
    raise SystemExit(main())
