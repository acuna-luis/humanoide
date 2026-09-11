#!/usr/bin/env python3
"""Rank archived, coherent task entries by torso tilt. Offline analysis only.

Uses the frozen E6.0Z report, not a motor-state sample. No trajectories,
installation files, ROS, networking, model inference or motion are generated.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np

import analyze_vla_fixture_collision_e4_1c as fk


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_joints(path):
    joints = []
    for element in ET.parse(path).getroot().findall('joint'):
        axis = element.find('axis')
        limit = element.find('limit')
        joints.append(dict(
            name=element.get('name'), type=element.get('type'),
            parent=element.find('parent').get('link'),
            child=element.find('child').get('link'),
            origin=fk.origin_transform(element.find('origin')),
            axis=fk.xyz(axis.get('xyz') if axis is not None else None, (1, 0, 0)),
            limit=None if limit is None else (
                float(limit.get('lower', '-inf')), float(limit.get('upper', 'inf')))))
    return joints


def validate_records(report, contract):
    names = report['joint_names']
    if names != contract['joint_order'] or len(names) != 20 or len(set(names)) != 20:
        raise ValueError('Expected exact canonical 20D order')
    if report.get('schema') != 'cruzr-s2-vla-dataset-entry-states-v1':
        raise ValueError('Unknown archive schema')
    records = report['frame_zero_records']
    if len(records) != report['episode_count'] or not records:
        raise ValueError('Incomplete archive')
    seen = set()
    for record in records:
        if record['episode'] in seen:
            raise ValueError('Duplicate episode')
        seen.add(record['episode'])
        if type(record['task']) is not int:
            raise ValueError('Invalid task ID')
        for field in ('state', 'action'):
            values = record[field]
            if (len(values) != 20 or any(type(v) not in (int, float) for v in values)
                    or not np.isfinite(values).all()):
                raise ValueError('Invalid canonical vector')
    return records


def torso_metrics(joints, state):
    poses = fk.forward_kinematics(joints, state)
    # Define upright in the zero-body model, without assuming torso's local +Z
    # is base +Z. Yaw about the vertical alone must not count as torso tilt.
    zero = fk.forward_kinematics(joints, {})['torso_link'][:3, :3]
    local_up = zero.T @ np.array([0., 0., 1.])
    up = poses['torso_link'][:3, :3] @ local_up
    tilt = math.degrees(math.atan2(float(np.linalg.norm(up[:2])), float(up[2])))
    return tilt, poses


def analyze(report, contract, joints, upright_degrees=5.0):
    if not math.isfinite(upright_degrees) or not 0 <= upright_degrees <= 90:
        raise ValueError('Invalid exploratory tilt threshold')
    records = validate_records(report, contract)
    names = report['joint_names']
    limits = {j['name']: j['limit'] for j in joints if j['type'] != 'fixed'}
    if not set(names) <= set(limits):
        raise ValueError('Canonical joints absent from model')
    baseline_id = contract['candidate']['episode']
    baseline = next(r for r in records if r['episode'] == baseline_id)
    if baseline['task'] != contract['task_id']:
        raise ValueError('Baseline belongs to a different task')
    rows = []
    for record in records:
        if record['task'] != contract['task_id']:
            continue
        q = dict(zip(names, record['state'], strict=True))
        tilt, poses = torso_metrics(joints, q)
        violations = [name for name, value in q.items()
                      if limits[name] is not None and not limits[name][0] <= value <= limits[name][1]]
        delta = np.asarray(record['action']) - record['state']
        rows.append(dict(
            episode=record['episode'], task=record['task'], frame=0,
            state=record['state'], action=record['action'],
            torso_tilt_from_zero_body_degrees=tilt,
            maximum_change_from_previous_entry_rad=float(np.max(abs(
                np.asarray(record['state']) - baseline['state']))),
            dataset_action_minus_state_max_rad=float(np.max(abs(delta))),
            # These are dataset labels, NOT a prediction of checkpoint-40000.
            within_exploratory_tilt_threshold=tilt <= upright_degrees,
            joint_limit_violations=violations,
            lifter_rad=[q[f'lifter_pitch_{i}_joint'] for i in (1, 2, 3)],
            sensor_origins_base_m={side: poses[f'{side}_sixforce_link'][:3, 3].tolist()
                                   for side in ('L', 'R')},
            torso_origin_base_m=poses['torso_link'][:3, 3].tolist()))
    candidates = sorted((r for r in rows if r['within_exploratory_tilt_threshold']
                         and not r['joint_limit_violations']), key=lambda r: (
        r['maximum_change_from_previous_entry_rad'], r['torso_tilt_from_zero_body_degrees'], r['episode']))
    return dict(
        schema='cruzr-vla-entry-posture-review-v1',
        status='OFFLINE_CANDIDATES_ONLY', physical_execution_authorized=False,
        task_id=contract['task_id'], joint_order=names,
        source_episode_count=len(records), task_episode_count=len(rows),
        exploratory_tilt_threshold_degrees=upright_degrees,
        candidate_count=len(candidates),
        baseline=next(r for r in rows if r['episode'] == baseline_id),
        shortlist=candidates[:10], all_task_entries=rows,
        limitations=[
            'Tilt is FK relative to upright zero-body URDF, not a measured floor angle.',
            'Threshold is an exploratory ranking preference, not a safety limit.',
            'Complete archived frame-zero 20D vectors preserved; no mixed or clipped poses.',
            'Sensor origins are not pad centers or table height.',
            'Dataset action continuity is not checkpoint prediction continuity.',
            'No transition, collisions, stability, fixture, stopping or physical execution validated.',
            'Frozen ENTRY contract, XML and shadow configuration remain unchanged.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset-report', type=Path, required=True)
    parser.add_argument('--entry-contract', type=Path, required=True)
    parser.add_argument('--urdf', type=Path, required=True)
    parser.add_argument('--upright-degrees', type=float, default=5.)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    contract = json.loads(args.entry_contract.read_text())
    if digest(args.dataset_report) != contract['candidate']['dataset_entry_report_sha256']:
        raise ValueError('Archived dataset report differs from frozen contract hash')
    result = analyze(json.loads(args.dataset_report.read_text()), contract,
                     load_joints(args.urdf), args.upright_degrees)
    result['sources_sha256'] = {str(p.resolve()): digest(p) for p in (
        args.dataset_report, args.entry_contract, args.urdf, Path(__file__), Path(fk.__file__))}
    # Never overwrite an earlier review or any runtime artifact.
    args.output_dir.mkdir(parents=True, exist_ok=False)
    (args.output_dir / 'entry-postures.json').write_text(
        json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: result[k] for k in (
        'status', 'task_episode_count', 'candidate_count', 'physical_execution_authorized')}))
    for row in result['shortlist'][:5]:
        print(f"{row['episode']}: tilt={row['torso_tilt_from_zero_body_degrees']:.3f} deg; "
              f"change={row['maximum_change_from_previous_entry_rad']:.6f} rad")


if __name__ == '__main__':
    main()
