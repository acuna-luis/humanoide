"""Inspect a clamp .motion locally; never connect, publish or replay."""
import argparse
import hashlib
import json
import math
from pathlib import Path


JOINTS = {
    'head': ['head_yaw_joint', 'head_pitch_joint'],
    'left_arm': ['L_'+name+'_joint' for name in (
        'shoulder_pitch', 'shoulder_roll', 'shoulder_yaw', 'elbow_roll',
        'elbow_yaw', 'wrist_pitch', 'wrist_roll')],
    'right_arm': ['R_'+name+'_joint' for name in (
        'shoulder_pitch', 'shoulder_roll', 'shoulder_yaw', 'elbow_roll',
        'elbow_yaw', 'wrist_pitch', 'wrist_roll')],
    'lifter': ['lifter_pitch_1_joint', 'lifter_pitch_2_joint', 'lifter_pitch_3_joint'],
    'waist': ['waist_yaw_joint'],
}


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def inspect(motion, state=None):
    if not isinstance(motion, dict) or motion.get('robot') != 'Utars':
        raise ValueError('This inspector supports only the recorded Utars clamp profile')
    groups = set(motion)-{'robot', 'source'}
    if not groups or groups-set(JOINTS):
        raise ValueError('Missing or unsupported motion groups; do not ignore extra effectors')
    measured = None
    if state is not None:
        names, positions = state['name'], state['position']
        if len(names) != len(positions) or len(set(names)) != len(names):
            raise ValueError('Invalid named joint-state sample')
        if not all(number(q) for q in positions):
            raise ValueError('Nonfinite measured joint position')
        measured = dict(zip(names, positions))
    report = dict(robot=motion['robot'], source=motion.get('source'), groups={},
                  physical_authorized=False, freshness_checked=False,
                  collision_checked=False, limits_checked=False)
    deltas = []
    for group in sorted(groups):
        rows = motion[group]
        if not isinstance(rows, list) or len(rows) < 2:
            raise ValueError('At least two samples required: '+group)
        previous = None
        for row in rows:
            if not isinstance(row, dict) or not number(row.get('t')) or row['t'] < 0:
                raise ValueError('Invalid time: '+group)
            if previous is not None and row['t'] <= previous:
                raise ValueError('Nonadvancing times: '+group)
            q = row.get('q')
            if not isinstance(q, list) or len(q) != len(JOINTS[group]) or not all(number(x) for x in q):
                raise ValueError('Invalid joint vector: '+group)
            previous = row['t']
        vectors = [row['q'] for row in rows]
        ranges = [max(axis)-min(axis) for axis in zip(*vectors)]
        result = dict(samples=len(rows), duration_s=rows[-1]['t']-rows[0]['t'],
                      initial_q=vectors[0], final_q=vectors[-1], range_rad=ranges,
                      movement_recorded=any(x > 1e-9 for x in ranges))
        if measured is not None:
            if set(JOINTS[group])-set(measured):
                raise ValueError('Missing measured joints: '+group)
            differences = [measured[name]-q for name, q in zip(JOINTS[group], vectors[0])]
            result['initial_delta_rad'] = differences
            deltas.extend(abs(x) for x in differences)
        report['groups'][group] = result
    if measured is not None:
        report['max_initial_delta_rad'] = max(deltas)
        report['initial_geometry_matches_002rad'] = max(deltas) < .02
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('motion', type=Path)
    parser.add_argument('--joint-state-json', type=Path,
                        help='Optional sensor_msgs JointState JSON by name, not raw actuator IDs')
    args = parser.parse_args()
    try:
        raw = args.motion.read_bytes()
        state = json.loads(args.joint_state_json.read_text()) if args.joint_state_json else None
        report = inspect(json.loads(raw), state)
        report.update(path=str(args.motion.resolve()), bytes=len(raw),
                      sha256=hashlib.sha256(raw).hexdigest())
        print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(2, 'INSPECTION_FAILED: '+str(error)+'\n')


if __name__ == '__main__':
    main()
