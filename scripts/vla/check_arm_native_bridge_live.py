#!/usr/bin/env python3
"""Passive check of real Motion guard, UUID handshake and lease revocation.

No physical run is provided. The check starts an ephemeral ROS2 guard in the
Motion ROS2 container; it does not create or send an action goal. Guard and
lease run on Motion to use the same monotonic clock. A synthetic UUID is not
published. Loss of an idle guard is not a test of physical servo stopping.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

import check_arm_from_pico_supervised as existing
import prepare_pico_wrist_native_probe as probe
import run_head_from_pico_supervised as head

ROOT = Path(__file__).resolve().parents[2]
VLA = ROOT/'scripts/vla'
RUNTIME = VLA/'runtime'
BOX = ROOT/'scripts/box_handling'
EVIDENCE = ROOT.parent/'Humanoide-vla-evidence'/'ARM_NATIVE_BRIDGE_CHECK'


def module_code(sources):
    code = 'import sys,types\n'
    for name, (source, filename) in sources.items():
        compile(source, filename, 'exec')
        code += ('m=types.ModuleType('+repr(name)+')\n'
                 'm.__file__='+repr(filename)+'\n'
                 'sys.modules['+repr(name)+']=m\n'
                 'exec(compile('+repr(source)+','+repr(filename)+',"exec"),m.__dict__)\n')
    return code


def source_bundle():
    paths = {
        'metamove_head_probe': RUNTIME/'metamove_head_probe.py',
        'head_from_pico_readonly': RUNTIME/'head_from_pico_readonly.py',
        'arm_from_pico_supervised': RUNTIME/'arm_from_pico_supervised.py',
        'scenario1_request_ids': BOX/'scenario1_request_ids.py',
        'scenario1_action_client': BOX/'scenario1_action_client.py',
        'prepare_pico_wrist_native_probe': VLA/'prepare_pico_wrist_native_probe.py',
        'arm_native_lease_bridge': VLA/'arm_native_lease_bridge.py',
        'arm_native_bridge_check_remote': RUNTIME/'arm_native_bridge_check_remote.py',
    }
    sources = {name: (path.read_text(encoding='utf-8'), str(path)) for name, path in paths.items()}
    guard_sources = {name: sources[name] for name in
                     ('metamove_head_probe', 'head_from_pico_readonly', 'arm_from_pico_supervised')}
    guard = (module_code(guard_sources) + 'import json\n'
             'print(json.dumps({"event":"BRIDGE_READY"}),flush=True)\n'
             'session=json.loads(sys.stdin.readline())\n'
             'raise SystemExit(sys.modules["arm_from_pico_supervised"].main('
             'session,dry_run=True,monitor_only=True))\n')
    coordinator = (module_code(sources) + 'import json\n'
                   'print(json.dumps({"event":"BRIDGE_READY"}),flush=True)\n'
                   'payload=json.loads(sys.stdin.readline())\n'
                   'print(json.dumps(sys.modules["arm_native_bridge_check_remote"].check(payload),'
                   'allow_nan=False),flush=True)\n')
    hashes = {name: hashlib.sha256(source.encode()).hexdigest()
              for name, (source, _) in sources.items()}
    return coordinator, guard, hashes


def check(manifest_path, urdf_path, transmissions_path):
    manifest = json.loads(manifest_path.read_bytes())
    urdf = urdf_path.read_bytes().decode('utf-8')
    transmissions = transmissions_path.read_bytes().decode('utf-8')
    probe.validate(manifest, urdf, transmissions)
    token = uuid.uuid4().hex
    EVIDENCE.mkdir(mode=0o700, parents=True, exist_ok=True)
    outdir = EVIDENCE / ('check-' + token)
    outdir.mkdir(mode=0o700)
    mode, started, container = existing.preflight()
    coordinator, guard, hashes = source_bundle()
    session = {'schema': 'cruzr_head_pico_preflight_v1', 'task_sha256': existing.ARM_TASK_SHA,
               'pico_sha256': head.admission.PICO_SHA, 'work_mode': mode,
               'operator_confirmed': False, 'controller_status_writers_checked': True,
               'age_at_handoff_s': time.monotonic()-started, 'session_id': token, 'mode': 'check'}
    payload = {'session': session, 'initial': manifest['input']['reference_20d'], 'guard_source': guard}
    sentinel = 'CODE_END_' + uuid.uuid4().hex
    if sentinel in coordinator:
        raise RuntimeError('source_sentinel_collision')
    env = dict(os.environ, CRUZR_INTERNAL_ASKPASS='1',
               SSH_ASKPASS=str(ROOT/'scripts/cruzr_recover_to_home.sh'),
               SSH_ASKPASS_REQUIRE='force', DISPLAY=os.environ.get('DISPLAY', ':0'))
    data = coordinator + '\n' + sentinel + '\n' + json.dumps(payload, allow_nan=False) + '\n'
    (outdir/'sources-sha256.json').write_text(json.dumps(hashes, indent=2)+'\n')
    try:
        result = subprocess.run(head.remote_command(container, sentinel), input=data, text=True,
                                capture_output=True, timeout=55, env=env)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError('passive_check_timeout_guard_process_may_remain') from exc
    (outdir/'stdout.log').write_text(result.stdout)
    (outdir/'stderr.log').write_text(result.stderr)
    rows = []
    for line in result.stdout.splitlines():
        try:
            row = json.loads(line)
            if isinstance(row, dict): rows.append(row)
        except ValueError:
            continue
    finals = [x for x in rows if x.get('status') == 'PASS_PASSIVE_GUARD_UUID_AND_LEASE_REVOCATION']
    if (result.returncode != 0 or len(finals) != 1 or finals[0].get('movement_commands') != 0
            or finals[0].get('physical_control_qualified') is not False):
        raise RuntimeError('passive_bridge_check_failed_evidence:' + str(outdir))
    print(json.dumps({'status': finals[0]['status'], 'evidence': str(outdir),
                      'movement_commands': 0, 'physical_stop_verified': False}))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check', action='store_true')
    group.add_argument('--run', action='store_true')
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--urdf', type=Path)
    parser.add_argument('--transmissions', type=Path)
    args = parser.parse_args(argv)
    if args.run:
        print('BLOCKED: physical execution is not implemented', file=sys.stderr)
        return 2
    try:
        if any(x is None for x in (args.manifest, args.urdf, args.transmissions)):
            raise ValueError('manifest_urdf_and_transmissions_required')
        check(args.manifest, args.urdf, args.transmissions)
        return 0
    except (OSError, RuntimeError, ValueError, TypeError, KeyError, subprocess.SubprocessError) as exc:
        print('PASSIVE_BRIDGE_CHECK_FAILED: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
