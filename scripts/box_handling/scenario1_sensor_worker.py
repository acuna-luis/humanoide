#!/usr/bin/env python3
"""Read-only ROS2 sensor collector; no commands, publishers or calibration.

Snapshot readiness means that all three streams were received, not that their
frames, calibration, contact or physical condition have been validated. Buffer
age/rate use a monotonic arrival clock; source and receipt stamps are preserved.
"""
import argparse
from collections import deque
import copy
import json
import math
import os
from pathlib import Path
import tempfile
import time


FT_TOPICS = {'left': '/mc/ft_states/L_hand_ft', 'right': '/mc/ft_states/R_hand_ft'}
JOINT_TOPIC = '/mc/whole_joint_states'
WINDOW_NS = 2_000_000_000
MIN_INTERVAL_NS = 10_000_000
SNAPSHOT_PERIOD_NS = 100_000_000


def _integer(value, label, *, positive=False):
    if type(value) is not int or value < (1 if positive else 0):
        raise ValueError(label + ' must be a valid integer timestamp')
    return value


def stamp_ns(header):
    try:
        sec = _integer(header.stamp.sec, 'stamp.sec')
        nanosec = _integer(header.stamp.nanosec, 'stamp.nanosec')
    except AttributeError as exc:
        raise ValueError('Sensor header has no timestamp') from exc
    if nanosec >= 1_000_000_000:
        raise ValueError('Invalid stamp.nanosec')
    return _integer(sec * 1_000_000_000 + nanosec, 'stamp_ns', positive=True)


def advance_source_stamp(previous, current):
    """Fail closed if a stream repeats or reverses its source timestamp."""
    _integer(current, 'stamp_ns', positive=True)
    if previous is not None and current <= previous:
        raise ValueError('Sensor source timestamp froze or moved backwards')
    return current


def _numbers(values):
    result = []
    for value in values:
        if type(value) not in (int, float):
            raise ValueError('Nonnumeric sensor value')
        try:
            value = float(value)
        except OverflowError as exc:
            raise ValueError('Nonfinite sensor value') from exc
        if not math.isfinite(value):
            raise ValueError('Nonfinite sensor value')
        result.append(value)
    return result


def wrench_sample(message, received_ns):
    """Serialize WrenchStamped verbatim; frame_id is not a frame calibration."""
    try:
        frame = message.header.frame_id
        if type(frame) is not str or not frame:
            raise ValueError('Missing wrench frame_id')
        force = _numbers([getattr(message.wrench.force, axis) for axis in 'xyz'])
        torque = _numbers([getattr(message.wrench.torque, axis) for axis in 'xyz'])
        return dict(stamp_ns=stamp_ns(message.header),
                    received_ns=_integer(received_ns, 'received_ns', positive=True),
                    frame_id=frame, force=force, torque=torque)
    except AttributeError as exc:
        raise ValueError('Malformed WrenchStamped') from exc


def joint_sample(message, received_ns):
    """Serialize named measured joints, requiring positions and velocities."""
    try:
        names = list(message.name)
        position, velocity = _numbers(message.position), _numbers(message.velocity)
        if (not names or any(type(name) is not str or not name for name in names) or
                len(set(names)) != len(names) or len(position) != len(names) or
                len(velocity) != len(names)):
            raise ValueError('Incomplete or duplicate measured joints')
        return dict(stamp_ns=stamp_ns(message.header),
                    received_ns=_integer(received_ns, 'received_ns', positive=True),
                    names=names, position=position, velocity=velocity)
    except (AttributeError, TypeError) as exc:
        raise ValueError('Malformed JointState') from exc


class SensorBuffer:
    """Independent bounded streams: last two arrival seconds, at most 100 Hz."""
    STREAMS = ('left', 'right', 'joints')

    def __init__(self):
        self.samples = {name: deque(maxlen=WINDOW_NS // MIN_INTERVAL_NS)
                        for name in self.STREAMS}
        self.last_kept = {name: None for name in self.STREAMS}
        self.last_arrival = {name: None for name in self.STREAMS}

    def _prune(self, monotonic_ns):
        _integer(monotonic_ns, 'monotonic_ns')
        for stream, rows in self.samples.items():
            if self.last_arrival[stream] is not None and monotonic_ns < self.last_arrival[stream]:
                raise ValueError('Arrival clock moved backwards')
            while rows and rows[0][0] <= monotonic_ns - WINDOW_NS:
                rows.popleft()

    def add(self, stream, sample, monotonic_ns):
        if stream not in self.samples:
            raise ValueError('Unknown sensor stream')
        self._prune(monotonic_ns)
        if not isinstance(sample, dict):
            raise ValueError('Invalid sensor sample')
        # Check serialization even for samples dropped by the rate limit.
        json.dumps(sample, allow_nan=False)
        self.last_arrival[stream] = monotonic_ns
        previous = self.last_kept[stream]
        if previous is not None and monotonic_ns - previous < MIN_INTERVAL_NS:
            return False
        self.samples[stream].append((monotonic_ns, copy.deepcopy(sample)))
        self.last_kept[stream] = monotonic_ns
        return True

    def ready(self, monotonic_ns):
        self._prune(monotonic_ns)
        return all(self.samples.values())

    def snapshot(self, written_ns, monotonic_ns):
        self._prune(monotonic_ns)
        data = {name: [copy.deepcopy(sample) for _, sample in rows]
                for name, rows in self.samples.items()}
        return dict(version=1, written_ns=_integer(written_ns, 'written_ns', positive=True),
                    ft={'left': data['left'], 'right': data['right']}, joints=data['joints'])


def session_active(session, now_monotonic):
    """Both leases must be present and valid; malformed/missing leases fail closed."""
    if type(now_monotonic) not in (int, float) or not math.isfinite(now_monotonic):
        raise ValueError('Invalid monotonic time')
    session = Path(session)
    if (session/'stop').exists():
        return False
    for filename in ('control-lease.json', 'lease.json'):
        lease = json.loads((session/filename).read_text())
        deadline = lease.get('deadline') if isinstance(lease, dict) else None
        if type(deadline) not in (int, float) or not math.isfinite(deadline):
            raise ValueError('Invalid ' + filename)
        if now_monotonic >= deadline:
            return False
    return True


def atomic_text(path, text):
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', dir=path.parent,
                                         prefix=path.name+'.', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
        descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def write_snapshot(session, buffer, written_ns, monotonic_ns):
    snapshot = buffer.snapshot(written_ns, monotonic_ns)
    atomic_text(Path(session)/'sensors.json', json.dumps(snapshot, allow_nan=False)+'\n')
    return snapshot


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True, type=Path)
    args = parser.parse_args(argv)
    session = args.session.resolve()
    node, ros = None, None
    ready_path = session/'sensors.ready'
    try:
        if not session.is_dir():
            raise ValueError('Sensor session directory does not exist')
        ready_path.unlink(missing_ok=True)
        (session/'sensors.error').unlink(missing_ok=True)
        if not session_active(session, time.monotonic()):
            return 0
        import rclpy
        from geometry_msgs.msg import WrenchStamped
        from sensor_msgs.msg import JointState
        from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy

        ros = rclpy
        ros.init(args=[])
        node = ros.create_node('scenario1_sensor_worker')
        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT,
                         durability=DurabilityPolicy.VOLATILE)
        buffer = SensorBuffer()
        source_stamps = dict.fromkeys(buffer.STREAMS)

        def receive(stream, message):
            received = time.time_ns()
            sample = (joint_sample(message, received) if stream == 'joints'
                      else wrench_sample(message, received))
            # Check every callback, including arrivals discarded by the rate cap.
            source_stamps[stream] = advance_source_stamp(source_stamps[stream], sample['stamp_ns'])
            buffer.add(stream, sample, time.monotonic_ns())

        subscriptions = [node.create_subscription(WrenchStamped, topic,
                         lambda message, side=side: receive(side, message), qos)
                         for side, topic in FT_TOPICS.items()]
        subscriptions.append(node.create_subscription(JointState, JOINT_TOPIC,
                             lambda message: receive('joints', message), qos))
        next_write = 0
        while ros.ok() and session_active(session, time.monotonic()):
            ros.spin_once(node, timeout_sec=0.02)
            now = time.monotonic_ns()
            if now >= next_write:
                write_snapshot(session, buffer, time.time_ns(), now)
                if buffer.ready(now):
                    if not ready_path.exists():
                        atomic_text(ready_path, 'ready\n')
                else:
                    ready_path.unlink(missing_ok=True)
                next_write = now + SNAPSHOT_PERIOD_NS
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        if session.is_dir():
            atomic_text(session/'sensors.error', type(exc).__name__ + ': ' + str(exc) + '\n')
        return 78
    finally:
        ready_path.unlink(missing_ok=True)
        if node is not None:
            node.destroy_node()
        if ros is not None and ros.ok():
            ros.shutdown()


if __name__ == '__main__':
    raise SystemExit(main())
