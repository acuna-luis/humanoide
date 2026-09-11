#!/usr/bin/env python3
"""Prepare a HOME recovery from live joints, without requiring teleoperation.

Read-only robot access. This is a preparation tool, NOT a motion executor.
No --run, installation, task dispatch, controller reset or mode change exists.
"""
import argparse
import concurrent.futures
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from collect_estop_available_readonly import execute, ros
from cruzr_pico_to_home_owner_gate import JOINT_ORDER
from general_home.trace_analysis import analyze, strict_json, stamp_ns


def one_document(text):
    documents = [d for d in yaml.safe_load_all(text) if d is not None]
    if len(documents) != 1 or not isinstance(documents[0], dict):
        raise ValueError('Expected exactly one ROS document')
    return documents[0]


def idle_gate(reads):
    for key in ('commands', 'action', 'locks'):
        if reads.get(key, {}).get('returncode') != 0:
            raise ValueError('Control state unavailable: ' + key)
    if not re.search(r'^Writer count:\s*0\s*$', reads['commands']['stdout'], re.M):
        raise ValueError('An external joint-command writer exists or its count is unknown')
    action = one_document(reads['action']['stdout'])
    statuses = action.get('status_list')
    if not isinstance(statuses, list):
        raise ValueError('Missing action status list')
    if any(not isinstance(s, dict) or type(s.get('status')) is not int or
           s['status'] not in (4, 5, 6) for s in statuses):
        raise ValueError('Action still active or unknown')
    locks = one_document(reads['locks']['stdout'])
    if locks.get('locked') is not False or locks.get('module_name') != '':
        raise ValueError('A module is locked or its state is unknown')


def joint_values(sample):
    names = sample.get('name')
    positions, velocities = sample.get('position'), sample.get('velocity')
    if not all(isinstance(x, list) for x in (names, positions, velocities)):
        raise ValueError('Incomplete canonical JointState')
    if not all(isinstance(n, str) for n in names) or len(set(names)) != len(names):
        raise ValueError('Invalid/duplicate canonical joint names')
    if len(names) != len(positions) or len(names) != len(velocities) or not set(JOINT_ORDER) <= set(names):
        raise ValueError('Missing canonical joints')
    if any(type(x) not in (float, int) or not math.isfinite(x) for x in positions + velocities):
        raise ValueError('Nonfinite/invalid canonical joint value')
    values = {n: (p, v) for n, p, v in zip(names, positions, velocities)}
    if max(abs(values[n][1]) for n in JOINT_ORDER) > .002:
        raise ValueError('Canonical JointState is moving')
    return stamp_ns(sample.get('header', {}).get('stamp')), values


def state_from_trace(records, *, empty_clamps, captured_at, joint_samples):
    if empty_clamps is not True:
        raise ValueError('Empty clamps must be explicitly established')
    quality = analyze(records)
    if quality['issues']:
        raise ValueError('Invalid capture: ' + '; '.join(quality['issues']))
    if quality['stop_observations'] or any(quality['last_observed_stops'].values()):
        raise ValueError('Stop active or changed during capture; use stop recovery')
    # Do not reduce the declared geometry/tracking uncertainty from this sample.
    for name, joint in quality['joints'].items():
        if joint['fault_samples'] or joint['disabled_samples']:
            raise ValueError('Actuator unhealthy: ' + name)
        if joint['max_abs_velocity_rad_s'] > .002 or joint['observed_position_span_rad'] > .002:
            raise ValueError('Posture not stationary over the capture: ' + name)
        if joint['max_abs_requested_command_error_rad'] > .01:
            raise ValueError('Latent command or excessive following error: ' + name)
    # Actuator positions have motor-axis signs, distinct from the URDF joints.
    # Never turn raw actuator positions into planning coordinates. Two advancing
    # canonical JointStates are required; no inferred sign table or zero fill.
    if len(joint_samples) != 2:
        raise ValueError('Two canonical JointState samples are required')
    (stamp0, initial), (stamp1, joints) = map(joint_values, joint_samples)
    if stamp1 <= stamp0 or any(abs(joints[n][0] - initial[n][0]) > .002 for n in JOINT_ORDER):
        raise ValueError('Canonical JointState stale or posture changed')
    return dict(schema='cruzr-general-home-state-v1', captured_at=captured_at,
                source='canonical /mc/whole_joint_states with independent raw actuator health capture; no absolute clock synchronization',
                empty_clamps=True, actuators_healthy=True, controller_idle=True,
                joint_state=dict(name=JOINT_ORDER,
                                 position=[joints[n][0] for n in JOINT_ORDER],
                                 velocity=[joints[n][1] for n in JOINT_ORDER])), quality


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Read and prepare only (default)')
    parser.add_argument('--empty-clamps', action='store_true', required=True,
                        help='Operator has established empty clamps; never inferred from a photo')
    parser.add_argument('--scene', type=Path, help='Measured scene JSON; omitted = self-collision analysis only')
    parser.add_argument('--output-dir', type=Path, required=True, help='New private evidence directory')
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error('Output directory already exists')
    if args.scene is not None and not args.scene.is_file():
        parser.error('Scene file unavailable')
    args.output_dir.mkdir(parents=True, mode=0o700)
    out = args.output_dir
    report = dict(schema='cruzr-live-recovery-preparation-v1', status='PREPARING',
                  movement_commands=0, remote_mutations=0, physical_approval=False,
                  installable=False, teleoperation_required=False,
                  started_at=datetime.now(timezone.utc).isoformat())
    try:
        # Bounded passive recording validates advancing source timestamps, both
        # stops, actuator health, stationarity and preserved asymmetric values.
        with (out / 'capture.log').open('x') as log:
            capture = subprocess.run([sys.executable, str(Path(__file__).with_name('capture_home_motion_trace.py')),
                                      '--seconds', '5', '--output-dir', str(out / 'capture')],
                                     stdout=log, stderr=subprocess.STDOUT, timeout=40)
        if capture.returncode:
            raise ValueError('Passive capture unavailable; see capture.log')
        meta = json.loads((out / 'capture/capture.json').read_text())
        m, r = meta['container'], meta['ros_container']
        queries = {
            'commands': ('motion', ros(m, 'rosa topic info /mc/sdk/robot_command', True)),
            'action': ('motion', ros(r, 'ros2 topic echo --once --no-daemon /mc/manipulation/action/_action/status')),
            'locks': ('motion', ros(r, 'ros2 topic echo --once --no-daemon /sys/state/module_lock_info')),
        }
        reads = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            jobs = {pool.submit(execute, host, command): key for key, (host, command) in queries.items()}
            for job in concurrent.futures.as_completed(jobs):
                reads[jobs[job]] = job.result()
        save(out / 'control-reads.json', reads)
        idle_gate(reads)
        joint_samples = []
        for i in range(2):
            reading = execute('motion', ros(m, 'rosa topic echo --once --no-daemon /mc/whole_joint_states', True))
            save(out / f'canonical-joints-{i}.json', reading)
            if reading.get('returncode') != 0:
                raise ValueError('Canonical JointState unavailable; raw motor signs cannot substitute it')
            joint_samples.append(one_document(reading['stdout']))
        records = [strict_json(line) for line in (out / 'capture/trace.jsonl').read_text().splitlines() if line.strip()]
        state, quality = state_from_trace(records, empty_clamps=args.empty_clamps,
                                          captured_at=datetime.now(timezone.utc).isoformat(),
                                          joint_samples=joint_samples)
        save(out / 'state.json', state)
        save(out / 'capture-analysis.json', quality)
        if args.scene is None:
            scene = dict(schema='cruzr-general-home-scene-v1', frame_id='base_link', complete=True,
                         captured_at=meta['finished_at'], objects=[],
                         source='SYNTHETIC_EMPTY_SCENE_FOR_SELF_COLLISION_ONLY_NOT_PHYSICAL_CLEARANCE')
            save(out / 'scene.json', scene)
            report['scene_scope'] = 'self_collision_only; external environment NOT qualified'
        else:
            (out / 'scene.json').write_bytes(args.scene.read_bytes())
            report['scene_scope'] = 'operator_supplied_scene; not independently measured by this tool'
        planner = ROOT / 'scripts/teleoperation/cruzr_plan_home.py'
        with (out / 'planner.log').open('x') as log:
            process = subprocess.run([sys.executable, str(planner), '--plan', '--state', str(out / 'state.json'),
                                      '--scene', str(out / 'scene.json'), '--timeout', '20',
                                      '--timing-law', 'cubic-rest', '--output', str(out / 'plan.json')],
                                     stdout=log, stderr=subprocess.STDOUT, timeout=180)
        report['planner_exit_code'] = process.returncode
        if not (out / 'plan.json').is_file():
            raise ValueError('Planner did not produce a report; see planner.log')
        plan = json.loads((out / 'plan.json').read_text())
        report.update(status='CANDIDATE_NOT_EXECUTABLE' if process.returncode == 0 else 'MODEL_REJECTED',
                      planner_status=plan['status'], activation_blockers=plan['activation_blockers'],
                      rejected_pairs=len(plan.get('conflicts', [])))
        # A candidate is never a physical permit, even with no geometric conflict.
        return 3
    except (ValueError, OSError, KeyError, TypeError, yaml.YAMLError, subprocess.TimeoutExpired) as exc:
        report.update(status='PREPARATION_REJECTED', error=str(exc))
        return 2
    finally:
        report['finished_at'] = datetime.now(timezone.utc).isoformat()
        save(out / 'result.json', report)
        (out / 'preparer.py').write_bytes(Path(__file__).read_bytes())
        (out / 'SHA256SUMS').write_text(''.join(
            hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + str(p.relative_to(out)) + '\n'
            for p in sorted(out.rglob('*')) if p.is_file() and p != out / 'SHA256SUMS'))
        print(json.dumps(report, ensure_ascii=False))
        print('EVIDENCE=' + str(out))


if __name__ == '__main__':
    raise SystemExit(main())
