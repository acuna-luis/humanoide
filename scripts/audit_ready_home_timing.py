#!/usr/bin/env python3
"""Necessary average-speed test of local staging XML, not runtime validation."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    files = [ROOT/'scripts/vla/runtime/tasks/s2_vla_e6_0_ready_s2.xml',
             ROOT/'scripts/vla/runtime/tasks/s2_vla_e6_0_exact_recovery.xml']
    trees = [ET.parse(f) for f in files]
    staging = {}
    rows = []
    for action in trees[0].findall('.//Action'):
        if action.get('type') == 'arm':
            staging[action.get('location')] = [float(x) for x in action.get('joint_angles').split(';')]
    for direction, tree in zip(('HOME_TO_READY_STAGING', 'RECOVERY_STAGING_TO_HOME'), trees):
        for action in tree.findall('.//Action'):
            if action.get('type') != 'arm':
                continue
            side = action.get('location')
            target = [float(x) for x in action.get('joint_angles').split(';')]
            start = [0.]*7 if direction == 'HOME_TO_READY_STAGING' else staging[side]
            duration = float(action.get('duration'))
            if len(start) != 7 or len(target) != 7 or duration <= 0:
                raise ValueError('invalid_XML_stage')
            d = max(abs(b-a) for a, b in zip(start, target))
            rows.append(dict(direction=direction, side=side, duration_s=duration,
                maximum_joint_displacement_rad=d, necessary_peak_speed_lower_bound_rad_s=d/duration,
                provisional_arm_speed_limit_rad_s=.15, necessary_condition_pass=d/duration <= .15))
    result = dict(status='LOCAL_XML_NECESSARY_SPEED_CHECK', rows=rows,
        basis='integral(abs(velocity),0,T)>=abs(delta_q); peak_speed>=abs(delta_q)/T',
        initial_postures_assumed=['numeric_zero_HOME','recovery_reaches_declared_staging'],
        assumptions=['duration_means_completion_time; no_vendor_time_rescaling'],
        complete_paths_validated=False, installed_runtime_equivalence_verified=False,
        physical_authorized=False, robot_connections=0, movement_commands=0,
        source_sha256={str(f): hashlib.sha256(f.read_bytes()).hexdigest() for f in files+[Path(__file__)]})
    with args.output.open('x') as out:
        json.dump(result, out, indent=2, allow_nan=False)
        out.write('\n')
    print(json.dumps(rows))


if __name__ == '__main__':
    main()
