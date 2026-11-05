#!/usr/bin/env python3
"""Read a closed SQLite ROS bag; no ROS node, publishers, services or replay.

Run in the ROS environment providing rclpy and the recorded message types.
Reports capture coverage and numerical validity, not permission to replay.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sqlite3


def inspect(directory):
    from rclpy.serialization import deserialize_message
    from rosidl_runtime_py.utilities import get_message

    directory = Path(directory).resolve()
    if not (directory / 'metadata.yaml').is_file():
        raise ValueError('Missing metadata.yaml; recording may not be closed')
    databases = sorted(directory.glob('*.db3'))
    if len(databases) != 1:
        raise ValueError('This inspector requires one unsplit SQLite database')
    database = databases[0]
    before = database.stat()
    selected = {
        '/mc/whole_joint_states', '/mc/left_hand/joint_states',
        '/mc/right_hand/joint_states', '/mc/left_hand/command',
        '/mc/right_hand/command', '/mc/head/joint_command',
        '/mc/left_arm/joint_command', '/mc/right_arm/joint_command',
    }
    report = {'database': str(database), 'bytes': before.st_size, 'topics': {}}
    with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as connection:
        if connection.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise ValueError('SQLite integrity check failed')
        for topic_id, name, type_name in connection.execute('SELECT id,name,type FROM topics'):
            count = connection.execute('SELECT COUNT(*) FROM messages WHERE topic_id=?',
                                       (topic_id,)).fetchone()[0]
            entry = {'type': type_name, 'count': count}
            report['topics'][name] = entry
            if name not in selected or count == 0:
                continue
            cls = get_message(type_name)
            ranges = {}
            previous_time = None
            first_time = None
            previous_stamp = None
            bad_values = backward_times = backward_stamps = 0
            duplicates = 0
            max_gap = 0
            modes = set()
            for timestamp, data in connection.execute(
                    'SELECT timestamp,data FROM messages WHERE topic_id=? ORDER BY id', (topic_id,)):
                msg = deserialize_message(data, cls)
                if first_time is None:
                    first_time = timestamp
                if previous_time is not None:
                    gap = timestamp - previous_time
                    backward_times += gap < 0
                    max_gap = max(max_gap, gap)
                previous_time = timestamp
                stamp = msg.header.stamp.sec * 1_000_000_000 + msg.header.stamp.nanosec
                if previous_stamp is not None:
                    backward_stamps += stamp < previous_stamp
                    duplicates += stamp == previous_stamp
                previous_stamp = stamp
                if hasattr(msg, 'joint_cmd'):
                    names = [x.name for x in msg.joint_cmd]
                    values = {'position': [x.position for x in msg.joint_cmd],
                              'velocity': [x.velocity for x in msg.joint_cmd],
                              'effort': [x.effort for x in msg.joint_cmd]}
                    modes.add(tuple(x.control_mode for x in msg.joint_cmd))
                else:
                    names = list(msg.name if hasattr(msg, 'name') else msg.names)
                    values = {key: list(getattr(msg, key)) for key in
                              ('position', 'velocity', 'effort', 'torque', 'acceleration', 'kp', 'kd')
                              if hasattr(msg, key)}
                    if hasattr(msg, 'mode'):
                        modes.add(tuple(msg.mode))
                if not names or len(set(names)) != len(names):
                    bad_values += 1
                for field, numbers in values.items():
                    if not numbers and field != 'position':
                        continue
                    if len(numbers) != len(names) or not all(math.isfinite(x) for x in numbers):
                        bad_values += 1
                        continue
                    field_ranges = ranges.setdefault(field, {})
                    for joint, value in zip(names, numbers):
                        limits = field_ranges.setdefault(joint, [value, value])
                        limits[0] = min(limits[0], value)
                        limits[1] = max(limits[1], value)
            entry.update(duration_s=(previous_time - first_time) / 1e9,
                         largest_receive_gap_s=max_gap / 1e9,
                         backward_receive_times=backward_times,
                         backward_header_times=backward_stamps,
                         repeated_header_times=duplicates,
                         invalid_values_or_dimensions=bad_values,
                         modes=[list(x) for x in sorted(modes)], ranges=ranges)
    after = database.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError('Database changed during inspection; stop recording first')
    digest = hashlib.sha256()
    with database.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    report['sha256'] = digest.hexdigest()
    report['replay_validated'] = False
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    print(json.dumps(inspect(args.directory), indent=2))


if __name__ == '__main__':
    main()
