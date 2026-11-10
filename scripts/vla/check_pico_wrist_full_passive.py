#!/usr/bin/env python3
"""Check PC-to-Motion heartbeat, guard and native worker without robot goals.

The Motion host creates and removes a private temporary lease and marker. This
does not stage a task, change a controller or prove physical stopping. No
``--run`` mode exists. Readiness for a physical test remains separate.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time
import uuid

import check_arm_native_bridge_live as passive
import check_arm_from_pico_supervised as preflight
import pico_wrist_pc_heartbeat as heartbeat
import prepare_pico_wrist_native_probe as probe
import run_head_from_pico_supervised as head
import run_pico_wrist_native_trial as trial

ROOT = Path(__file__).resolve().parents[2]
VLA = ROOT / 'scripts/vla'
RUNTIME = VLA / 'runtime'
BOX = ROOT / 'scripts/box_handling'
EVIDENCE = ROOT.parent / 'Humanoide-vla-evidence' / 'PICO_FULL_PASSIVE_CHECK'


def source_bundle():
    paths = {
        'metamove_head_probe': RUNTIME / 'metamove_head_probe.py',
        'head_from_pico_readonly': RUNTIME / 'head_from_pico_readonly.py',
        'arm_from_pico_supervised': RUNTIME / 'arm_from_pico_supervised.py',
        'scenario1_request_ids': BOX / 'scenario1_request_ids.py',
        'scenario1_action_client': BOX / 'scenario1_action_client.py',
        'prepare_pico_wrist_native_probe': VLA / 'prepare_pico_wrist_native_probe.py',
        'arm_native_lease_bridge': VLA / 'arm_native_lease_bridge.py',
        'pico_wrist_pc_heartbeat': VLA / 'pico_wrist_pc_heartbeat.py',
        'pico_wrist_native_coordinator': RUNTIME / 'pico_wrist_native_coordinator.py',
        'pico_wrist_docker_launcher': RUNTIME / 'pico_wrist_docker_launcher.py',
        'pico_wrist_full_passive_remote': RUNTIME / 'pico_wrist_full_passive_remote.py',
    }
    sources = {name: (path.read_text(encoding='utf-8'), str(path)) for name, path in paths.items()}
    guard = passive.module_code({name: sources[name] for name in
        ('metamove_head_probe', 'head_from_pico_readonly', 'arm_from_pico_supervised')})
    guard += ('import json\nprint(json.dumps({"event":"BRIDGE_READY"}),flush=True)\n'
              'session=json.loads(sys.stdin.readline())\n'
              'raise SystemExit(sys.modules["arm_from_pico_supervised"].main('
              'session,dry_run=True,monitor_only=True))\n')
    # This worker imports the native API for fingerprinting but never creates
    # an action client, calls rosa.init, or constructs/sends an action goal.
    worker = passive.module_code({name: sources[name] for name in
        ('scenario1_request_ids', 'scenario1_action_client')})
    worker += ('import json,time\n'
        'request=json.loads(sys.stdin.readline())\n'
        'from rosa.action_client import ActionClient,ActionClientGoalHandle\n'
        'native=sys.modules["scenario1_action_client"]\n'
        'fingerprints=native.validate_native_sources({"ActionClient":ActionClient,'
        '"ActionClientGoalHandle":ActionClientGoalHandle})\n'
        'native.check_lease(request["lease_path"],time.monotonic())\n'
        'goal_valid=native.validate_goal("motion",json.dumps(request["goal"],allow_nan=False))==request["goal"]\n'
        'print(json.dumps({"event":"NATIVE_READONLY_READY","fingerprints":fingerprints,'
        '"goal_format_valid":goal_valid,"lease_fresh":True,"monotonic":time.monotonic()}),flush=True)\n')
    host = passive.module_code(sources)
    host += ('import json\nprint(json.dumps({"event":"BRIDGE_READY"}),flush=True)\n'
             'payload=json.loads(sys.stdin.readline())\n'
             'print(json.dumps(sys.modules["pico_wrist_full_passive_remote"].check(payload),'
             'allow_nan=False),flush=True)\n')
    hashes = {name: hashlib.sha256(source.encode('utf-8')).hexdigest()
              for name, (source, _) in sources.items()}
    return host, guard, worker, hashes


def drive(process, session_id, preflight_started, outdir):
    selector = selectors.DefaultSelector()
    for stream, name in ((process.stdout, 'stdout'), (process.stderr, 'stderr')):
        os.set_blocking(stream.fileno(), False)
        selector.register(stream, selectors.EVENT_READ, name)
    pump = None
    data = bytearray()
    preflight_ack = heartbeat_ready = False
    result = None
    deadline = time.monotonic() + 55
    try:
        with (outdir / 'stdout.jsonl').open('x', encoding='utf-8') as out, \
             (outdir / 'stderr.log').open('x', encoding='utf-8') as err:
            while selector.get_map():
                if time.monotonic() >= deadline:
                    raise TimeoutError('passive_integration_timeout')
                if pump is not None and pump.failed.is_set():
                    raise RuntimeError('pc_heartbeat_failed:' + str(pump.failure))
                for key, _ in selector.select(.1):
                    block = os.read(key.fileobj.fileno(), 65536)
                    if not block:
                        selector.unregister(key.fileobj)
                        continue
                    target = out if key.data == 'stdout' else err
                    target.write(block.decode('utf-8', 'replace')); target.flush()
                    if key.data == 'stderr':
                        continue
                    data.extend(block)
                    if len(data) > 1_000_000:
                        raise ValueError('remote_output_too_large')
                    while b'\n' in data:
                        line, _, remainder = bytes(data).partition(b'\n')
                        data = bytearray(remainder)
                        row = json.loads(line)
                        if not isinstance(row, dict):
                            raise ValueError('remote_event_not_object')
                        event = row.get('event')
                        if event == 'HOST_PREFLIGHT_READY':
                            challenge = row.get('challenge')
                            if (preflight_ack or row.get('session_id') != session_id or
                                    not isinstance(challenge, str) or len(challenge) != 32 or
                                    any(c not in '0123456789abcdef' for c in challenge)):
                                raise ValueError('invalid_pc_preflight_challenge')
                            ack = {'event': 'pc_preflight_ack', 'session_id': session_id,
                                   'challenge': challenge, 'inventory_age_s': time.monotonic()-preflight_started}
                            trial.docker_launch.write_stream(process.stdin.fileno(),
                                (json.dumps(ack)+'\n').encode(), 1.0)
                            preflight_ack = True
                        elif event == 'HOST_HEARTBEAT_READY':
                            if not preflight_ack or heartbeat_ready or row.get('session_id') != session_id:
                                raise ValueError('invalid_pc_heartbeat_ready')
                            pump = heartbeat.PcHeartbeatPump(process.stdin.fileno(), session_id)
                            heartbeat_ready = True
                        elif event == 'pc_ping':
                            if pump is None:
                                raise ValueError('challenge_before_heartbeat_ready')
                            pump.submit(row)
                        elif row.get('status') == 'PASS_PC_HOST_GUARD_READONLY_NATIVE':
                            if result is not None:
                                raise ValueError('duplicate_result')
                            result = row
            if data.strip():
                raise ValueError('remote_output_truncated')
        rc = process.wait(timeout=3)
        if (rc != 0 or not preflight_ack or not heartbeat_ready or not isinstance(result, dict) or
                result.get('movement_commands') != 0 or result.get('action_goals_created') != 0 or
                result.get('physical_control_qualified') is not False):
            raise RuntimeError('passive_integration_not_confirmed')
        return result
    finally:
        if pump is not None:
            pump.close()
        selector.close()


def check(manifest_path, urdf_path, transmissions_path):
    manifest = json.loads(manifest_path.read_bytes())
    urdf = urdf_path.read_bytes().decode('utf-8')
    transmissions = transmissions_path.read_bytes().decode('utf-8')
    probe.validate(manifest, urdf, transmissions)
    mode, started, _ = preflight.preflight()
    host, guard, worker, hashes = source_bundle()
    token = uuid.uuid4().hex
    session = {'schema': 'cruzr_head_pico_preflight_v1', 'task_sha256': preflight.ARM_TASK_SHA,
               'pico_sha256': head.admission.PICO_SHA, 'work_mode': mode,
               'operator_confirmed': False, 'controller_status_writers_checked': True,
               'age_at_handoff_s': time.monotonic()-started, 'session_id': token, 'mode': 'check'}
    payload = {'session': session, 'manifest': manifest, 'urdf_text': urdf,
               'transmissions_text': transmissions, 'guard_source': guard, 'worker_source': worker}
    sentinel = 'PICO_HOST_END_' + uuid.uuid4().hex
    if sentinel in host:
        raise ValueError('host_source_sentinel_collision')
    EVIDENCE.mkdir(mode=0o700, parents=True, exist_ok=True)
    outdir = EVIDENCE / ('check-' + token)
    outdir.mkdir(mode=0o700)
    print('EVIDENCIA=' + str(outdir), flush=True)
    (outdir / 'sources-sha256.json').write_text(json.dumps(hashes, indent=2)+'\n', encoding='utf-8')
    env = dict(os.environ, CRUZR_INTERNAL_ASKPASS='1',
               SSH_ASKPASS=str(ROOT/'scripts/cruzr_recover_to_home.sh'),
               SSH_ASKPASS_REQUIRE='force', DISPLAY=os.environ.get('DISPLAY', ':0'))
    process = subprocess.Popen(trial.host_command(sentinel), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, env=env, bufsize=0)
    try:
        trial.docker_launch.write_stream(process.stdin.fileno(),
            (host+'\n'+sentinel+'\n'+json.dumps(payload, allow_nan=False)+'\n').encode(), 10)
        result = drive(process, token, started, outdir)
    finally:
        # This check never sends goals; terminate only its own SSH if stuck.
        if process.poll() is None:
            process.terminate()
            try: process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(timeout=3)
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is not None: stream.close()
    print(json.dumps({'status': result['status'], 'evidence': str(outdir),
                      'movement_commands': 0, 'physical_stop_verified': False}, allow_nan=False))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--run', action='store_true')
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--urdf', type=Path)
    parser.add_argument('--transmissions', type=Path)
    args = parser.parse_args(argv)
    if args.run:
        print('BLOCKED: passive check has no physical execution', file=sys.stderr)
        return 2
    try:
        if any(value is None for value in (args.manifest, args.urdf, args.transmissions)):
            raise ValueError('manifest_urdf_and_transmissions_required')
        check(args.manifest, args.urdf, args.transmissions)
        return 0
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, subprocess.SubprocessError) as exc:
        print('FULL_PASSIVE_CHECK_FAILED: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
