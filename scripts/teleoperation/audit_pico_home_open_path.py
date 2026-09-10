#!/usr/bin/env python3
"""Reproducible offline clamp sweep for open_v2; never connects to a robot."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"vla"))
import analyze_vla_fixture_collision_e4_1c as fk
from check_pico_home_geometry_offline import obb, separation
from cruzr_pico_home_open_path import waypoints, DURATIONS_S, REVISION
from cruzr_pico_to_home_owner_gate import JOINT_ORDER, PICO_VARIANTS


def audit(snapshot, samples, *, path=waypoints, durations=DURATIONS_S,
          revision=REVISION, variants=PICO_VARIANTS):
    if not 101 <= samples <= 2001:
        raise ValueError("samples must be 101..2001")
    joints, boxes, meshes = fk.load_robot(snapshot/'runtime.urdf', snapshot/'runtime-meshes.zip')
    archived = json.loads(json.loads((snapshot/'joints.json').read_text())['stdout'])
    initial = dict(zip(archived['name'], archived['position']))
    geometry = json.loads((snapshot/'geometry-check-1001.json').read_text())
    tool = geometry['tool_bounds_in_sensor_m']  # Full archived bounds, 2 mm inflation, 0..40 mm axial.
    targets = geometry['tested_robot_links']
    reach = sum(np.linalg.norm(j['origin'][:3, 3]) for j in joints)
    reach += max(max(np.linalg.norm(fk.corners(*b), axis=1)) for b in list(boxes.values())+list(tool.values()))
    limits = {j.get('name'): [float(j.find('limit').get(k)) for k in ('lower', 'upper')]
              for j in ET.parse(snapshot/'runtime.urdf').getroot().findall('joint')
              if j.get('name') in JOINT_ORDER}
    report = {'revision': revision, 'movement_commands': 0, 'physical_approval': False,
              'scope': 'clamp-robot and clamp-clamp; archived geometry, monotone joint segments',
              'limitations': ['Not a physical safety certificate; prior contact invalidated direct HOME.',
                             'Actual interpolation, tracking, braking and external scene not verified.',
                             'Own attachment pairs remain reported; no new collision exemptions.'],
              'samples_per_segment': samples, 'variants': {},
              'source_sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                  [snapshot/'runtime.urdf', snapshot/'runtime-meshes.zip', snapshot/'geometry-check-1001.json',
                   Path(__file__), Path(__file__).with_name('cruzr_pico_home_open_path.py')]}}
    for variant, start in variants.items():
        records = []
        points = path(start)
        if len(points) != len(durations)+1 or any(d <= 0 for d in durations):
            raise ValueError('Each segment needs a positive duration')
        for point in points:
            if any(not limits[n][0] <= q <= limits[n][1] for n, q in zip(JOINT_ORDER, point)):
                raise ValueError('Target exceeds URDF limits')
        for i, (a, z) in enumerate(zip(points, points[1:])):
            a, z = np.array(a), np.array(z)
            minima = {}
            # Covers unsampled positions only under a common, monotone joint interpolation.
            travel_pair = reach*float(np.abs(z-a).sum())/(samples-1)
            for alpha in np.linspace(0, 1, samples):
                poses = fk.forward_kinematics(joints, dict(initial, **dict(zip(JOINT_ORDER, a+alpha*(z-a)))))
                tb = {s: obb(poses[s+'_sixforce_link'], tool[s]) for s in ('L', 'R')}
                pairs = [(s+':'+n, separation(*tb[s], *obb(poses[n], boxes[n])))
                         for s in ('L', 'R') for n in targets]
                pairs.append(('L:R_clamp', separation(*tb['L'], *tb['R'])))
                for key, gap in pairs:
                    if gap < minima.get(key, {}).get('gap_m', float('inf')):
                        minima[key] = {'gap_m': gap, 'fraction': float(alpha)}
            local_pairs = {s+':'+s+'_'+n+'_link' for s in ('L', 'R')
                           for n in ('sixforce', 'wrist_roll', 'wrist_pitch')}
            body_pairs = {k: v for k, v in minima.items() if k not in local_pairs}
            worst = min(body_pairs, key=lambda k: body_pairs[k]['gap_m'])
            record = {'segment': i, 'duration_s': durations[i], 'minimum_by_pair': minima,
                      'sampling_pair_travel_bound_m': travel_pair,
                      'nonattachment_minimum_pair': worst,
                      'nonattachment_sample_min_m': body_pairs[worst]['gap_m'],
                      'nonattachment_conditional_lower_bound_m': body_pairs[worst]['gap_m']-travel_pair,
                      'quintic_vmax_rad_s': float(1.875*np.max(np.abs(z-a))/durations[i])}
            records.append(record)
            print(variant, i, worst, record['nonattachment_conditional_lower_bound_m'], flush=True)
        report['variants'][variant] = records
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--samples', type=int, default=501)
    args = parser.parse_args()
    result = audit(args.snapshot_dir, args.samples)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
