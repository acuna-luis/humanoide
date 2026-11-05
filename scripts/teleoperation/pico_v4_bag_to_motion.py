#!/usr/bin/env python3
"""Offline geometric conversion for the vendor player, never publishes commands.

Arms/head use recorded position commands; hands use measured joint positions.
Current/effort control is NOT reproduced. Original bag remains unchanged.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sqlite3

HAND_SUFFIXES = ('thumb_swing', 'thumb_mcp', 'thumb_pip', 'index_mcp',
                 'middle_mcp', 'ring_mcp', 'little_mcp')
ARM_SUFFIXES = ('shoulder_pitch_joint', 'shoulder_roll_joint', 'shoulder_yaw_joint',
                'elbow_roll_joint', 'elbow_yaw_joint', 'wrist_pitch_joint', 'wrist_roll_joint')
ORDER = {'head': ['head_yaw_joint', 'head_pitch_joint'],
         'left_arm': ['L_' + x for x in ARM_SUFFIXES],
         'right_arm': ['R_' + x for x in ARM_SUFFIXES],
         'left_hand': ['left_' + x for x in HAND_SUFFIXES],
         'right_hand': ['right_' + x for x in HAND_SUFFIXES]}
TOPICS = {'head': '/mc/head/joint_command',
          'left_arm': '/mc/left_arm/joint_command',
          'right_arm': '/mc/right_arm/joint_command',
          'left_hand': '/mc/left_hand/joint_states',
          'right_hand': '/mc/right_hand/joint_states'}


def convert(database, output, time_scale, expected_sha256):
    from rclpy.serialization import deserialize_message
    from rosidl_runtime_py.utilities import get_message

    if not math.isfinite(time_scale) or time_scale < 1:
        raise ValueError('Time scale must be >=1; acceleration is not supported')
    database, output = Path(database).resolve(), Path(output).resolve()
    digest = hashlib.sha256()
    with database.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    if digest.hexdigest() != expected_sha256:
        raise ValueError('Source bag checksum mismatch')
    frames = {}
    with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as connection:
        if connection.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise ValueError('SQLite integrity check failed')
        for group, topic in TOPICS.items():
            topic_id, type_name = connection.execute(
                'SELECT id,type FROM topics WHERE name=?', (topic,)).fetchone()
            cls = get_message(type_name)
            values = []
            for data, in connection.execute(
                    'SELECT data FROM messages WHERE topic_id=? ORDER BY id', (topic_id,)):
                msg = deserialize_message(data, cls)
                if group.endswith('hand'):
                    positions = dict(zip(msg.name, msg.position))
                    if len(msg.name) != 7 or len(msg.position) != 7:
                        raise ValueError('Incomplete hand frame')
                else:
                    positions = {item.name: item.position for item in msg.joint_cmd}
                if set(positions) != set(ORDER[group]):
                    raise ValueError('Unexpected joint names in ' + group)
                q = [float(positions[name]) for name in ORDER[group]]
                if not all(math.isfinite(x) for x in q):
                    raise ValueError('Non-finite joint value')
                stamp = msg.header.stamp.sec * 1_000_000_000 + msg.header.stamp.nanosec
                if stamp <= 0 or (values and stamp <= values[-1][0]):
                    raise ValueError('Invalid/non-increasing header time in ' + group)
                values.append((stamp, q))
            if len(values) < 2:
                raise ValueError('Missing trajectory in ' + group)
            frames[group] = values
    origin = min(values[0][0] for values in frames.values())
    end = max(values[-1][0] for values in frames.values())
    motion = {'robot': 'Utars', 'source': 'utars_teleop'}
    report = {'source_sha256': digest.hexdigest(), 'time_scale': time_scale,
              'duration_s': (end - origin) / 1e9 * time_scale,
              'hands_source': 'measured position; original effort/modes not replayed',
              'groups': {}}
    for group, values in frames.items():
        rows = [{'t': (stamp - origin) / 1e9 * time_scale, 'q': q} for stamp, q in values]
        if rows[0]['t'] > 0:
            rows.insert(0, {'t': 0., 'q': rows[0]['q'][:]})
        if rows[-1]['t'] < report['duration_s']:
            rows.append({'t': report['duration_s'], 'q': rows[-1]['q'][:]})
        motion[group] = rows
        report['groups'][group] = {'samples': len(rows), 'names': ORDER[group],
            'initial_q': rows[0]['q'], 'final_q': rows[-1]['q'],
            'largest_step_rad': max(max(abs(x-y) for x,y in zip(a['q'], b['q']))
                                    for a,b in zip(rows, rows[1:]))}
    # Exclusive creation: preserve every original/previous derivative.
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as stream:
        json.dump(motion, stream, allow_nan=False, separators=(',', ':'))
    report['output'] = str(output)
    report['output_sha256'] = hashlib.sha256(output.read_bytes()).hexdigest()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('database', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--time-scale', type=float, default=2.)
    parser.add_argument('--expected-sha256', required=True)
    args = parser.parse_args()
    print(json.dumps(convert(args.database, args.output, args.time_scale,
                             args.expected_sha256), indent=2))


if __name__ == '__main__':
    main()
