#!/usr/bin/env python3
"""Reconstruct logged first HOME command timing; not actual joint motion."""
import argparse
from collections import defaultdict
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import re

STAMP = re.compile(r'^[IWEF](\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d+)')
MOVE = re.compile(r'Now move (\w+) in joint space to: \[([^]]+)\] within ([\d.]+) s')
LIMIT = re.compile(r"(\w+)'s (\d+)-th position cmd: ([-\d.e+]+) is over of range: \[([-\d.e+]+), ([-\d.e+]+)\]")
FORCE = re.compile(r'Excessive force detected in (\d+)-th dimension of the (\w+) ft sensor: ([-\d.e+]+)')


def analyze(text):
    active = False
    moves, limits, forces = [], defaultdict(list), []
    result = dict(status='NO_COMPLETE_FIRST_HOME_WINDOW', physical_authorized=False,
                  actual_joint_trajectory_reconstructed=False)
    for number, line in enumerate(text.splitlines(),1):
        stamp = STAMP.match(line)
        if not stamp:
            continue
        clock = datetime.fromisoformat(stamp[1])
        record = dict(line=number, robot_log_time=stamp[1],
                      madrid_time=(clock-timedelta(hours=6)).isoformat()+'+02:00')
        if "BTree task:" in line and "is start" in line:
            if active:
                result['interrupted_by_other_task_start'] = record
                break
            if "'cruzr/home'" not in line:
                continue
            active = True
            start = clock
            result['home_start'] = record
        if not active:
            continue
        record['seconds_after_home_start'] = (clock-start).total_seconds()
        if match := MOVE.search(line):
            moves.append(dict(record, group=match[1], target=[float(x) for x in match[2].split()],
                              duration_s=float(match[3])))
        if match := LIMIT.search(line):
            value, low, high = map(float, match.group(3,4,5))
            limits[match[1]+':'+match[2]].append(dict(record, command=value, low=low, high=high,
                                                       excess_rad=max(low-value,value-high,0)))
        if match := FORCE.search(line):
            forces.append(dict(record, dimension_index_as_logged=match[1], side=match[2], value=float(match[3])))
        if 'BTree tick succeeded' in line or 'BTree tick failed' in line:
            result['task_outcome'] = dict(record, outcome='SUCCESS' if 'succeeded' in line else 'FAILURE')
            result['status'] = 'LOGGED_HOME_WINDOW_RECONSTRUCTED_NOT_PHYSICAL_CLEARANCE'
            break
    if moves:
        first = min(m['seconds_after_home_start'] for m in moves)
        for move in moves:
            move['command_start_offset_from_first_group_s'] = move['seconds_after_home_start']-first
        result['logged_command_start_spread_s'] = max(m['command_start_offset_from_first_group_s'] for m in moves)
    result['group_commands'] = moves
    result['range_warnings'] = {key: dict(count=len(values), first=values[0], last=values[-1],
                                         maximum_excess_rad=max(v['excess_rad'] for v in values))
                               for key,values in limits.items()}
    result['force_warnings'] = forces
    result['limitations'] = ['timestamps_are_logged_command_events_not_measured_motion_start',
                            'no_full_initial_20D_state_or_actual_trajectory_derived',
                            'indices_are_vendor_log_indices_not_assigned_ROS_joint_names',
                            'force_warnings_are_not_first_contact_time_or_measured_stop_distance',
                            'Madrid_offset_minus_6_hours_applies_to_these_September_2026_logs_only',
                            'task_success_does_not_demonstrate_absence_of_contact']
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    reports = []
    for path in args.log:
        data = path.read_bytes()
        reports.append(dict(source=str(path), sha256=hashlib.sha256(data).hexdigest(),
                            **analyze(data.decode('utf-8',errors='replace'))))
    result = dict(logs=reports, physical_authorized=False, robot_connections=0, movement_commands=0)
    with args.output.open('x') as out:
        json.dump(result,out,indent=2,allow_nan=False)
        out.write('\n')
    print(args.output)
    return 0 if all(r['status'].startswith('LOGGED_HOME_WINDOW') for r in reports) else 3


if __name__ == '__main__':
    raise SystemExit(main())
