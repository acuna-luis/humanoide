#!/usr/bin/env python3
"""Read-only native odometry gate for scenario resumption.

Stdout contains one JSON result; native diagnostics are redirected to stderr.
No action clients, services, command publishers or robot configuration changes.
"""
import argparse
from collections import deque
from contextlib import contextmanager
import copy
import json
import math
import os
from pathlib import Path
import sys
import time


TOPIC = '/mc/odom'
TYPE = 'nav_msgs/msg/Odometry'
MAX_AGE_NS = 500_000_000


def object_json(value):
    def pairs(items):
        result = {}
        for key, item in items:
            if key in result:
                raise ValueError('Duplicate JSON key: ' + key)
            result[key] = item
        return result
    if isinstance(value, str):
        value = json.loads(value, object_pairs_hook=pairs)
    if not isinstance(value, dict):
        raise ValueError('Expected a JSON object')
    json.dumps(value, allow_nan=False)
    return copy.deepcopy(value)


def number(value, label):
    if type(value) not in (int, float):
        raise ValueError('Invalid numeric ' + label)
    try:
        value = float(value)
    except OverflowError as error:
        raise ValueError('Nonfinite ' + label) from error
    if not math.isfinite(value):
        raise ValueError('Nonfinite ' + label)
    return value


def nanoseconds(value, label):
    if type(value) is not int or value <= 0:
        raise ValueError('Invalid ' + label)
    return value


def sample(payload, received_ns):
    raw = object_json(payload)
    received_ns = nanoseconds(received_ns, 'receipt timestamp')
    try:
        header = raw['header']
        stamp = header['stamp']
        sec, ns = stamp['sec'], stamp['nanosec']
        if type(sec) is not int or sec < 0 or type(ns) is not int or not 0 <= ns < 10**9:
            raise ValueError('Invalid odometry source timestamp')
        stamp_ns = nanoseconds(sec * 10**9 + ns, 'source timestamp')
        frames = dict(frame_id=header['frame_id'], child_frame_id=raw['child_frame_id'])
        if any(not isinstance(value, str) or not value.strip() or value != value.strip()
               for value in frames.values()):
            raise ValueError('Odometry frame and child frame must be nonempty')
        pose = raw['pose']['pose']
        position = [number(pose['position'][axis], 'position') for axis in 'xyz']
        q = {axis: number(pose['orientation'][axis], 'quaternion') for axis in 'xyzw'}
        norm = math.hypot(*q.values())
        if abs(norm - 1.) > .01:
            raise ValueError('Invalid odometry quaternion')
        q = {axis: value / norm for axis, value in q.items()}
        yaw = math.atan2(2 * (q['w']*q['z'] + q['x']*q['y']),
                         1 - 2 * (q['y']**2 + q['z']**2))
        twist = raw['twist']['twist']
        velocities = {kind: math.hypot(*(number(twist[kind][axis], kind + ' velocity')
                                       for axis in 'xyz')) for kind in ('linear', 'angular')}
    except (KeyError, TypeError) as error:
        raise ValueError('Malformed odometry sample') from error
    return dict(raw=raw, stamp_ns=stamp_ns, received_ns=received_ns, frames=frames,
                position=position, yaw=yaw, **velocities)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


class Acquisition:
    def __init__(self, requested_ns):
        self.requested_ns = nanoseconds(requested_ns, 'request timestamp')
        self.samples = deque(maxlen=2)
        self.failure = None
        self.duplicates_ignored = 0

    def healthy(self):
        if self.failure is not None:
            raise ValueError(self.failure)

    @staticmethod
    def fresh(value, now_ns):
        for key in ('stamp_ns', 'received_ns'):
            if not 0 <= now_ns - value[key] <= MAX_AGE_NS:
                raise ValueError('Stale or future odometry ' + key)

    def add(self, payload, received_ns):
        self.healthy()
        try:
            value = sample(payload, received_ns)
            stamp = value['stamp_ns']
            if not self.samples and stamp <= self.requested_ns:
                return  # Queued pre-request data cannot count toward readiness.
            if stamp <= self.requested_ns or received_ns <= self.requested_ns:
                raise ValueError('Odometry must be newer than the request')
            self.fresh(value, received_ns)
            if self.samples:
                previous = self.samples[-1]
                if stamp < previous['stamp_ns']:
                    raise ValueError('Regressing odometry source timestamp')
                if stamp == previous['stamp_ns']:
                    if canonical(value['raw']) != canonical(previous['raw']):
                        raise ValueError('Conflicting odometry payload at the same source timestamp')
                    self.duplicates_ignored += 1
                    return  # Do not refresh receipts or supply a second sample.
                if received_ns <= previous['received_ns']:
                    raise ValueError('Nonadvancing odometry receipt timestamp')
                if value['frames'] != previous['frames']:
                    raise ValueError('Odometry frame changed')
            if value['linear'] > .003 + 1e-12 or value['angular'] > .01 + 1e-12:
                raise ValueError('Base is moving: odometry velocity exceeds stationary limit')
            self.samples.append(value)
        except (ValueError, TypeError, OverflowError) as error:
            self.failure = str(error)
            raise ValueError(self.failure) from error

    def complete(self, now_ns, publishers):
        self.healthy()
        try:
            now_ns = nanoseconds(now_ns, 'completion timestamp')
            if now_ns < self.requested_ns:
                raise ValueError('Clock moved backwards during resume check')
            if type(publishers) is not int or publishers < 0 or publishers > 1:
                raise ValueError('Exactly one odometry publisher is required')
            for value in self.samples:
                self.fresh(value, now_ns)
            if publishers != 1 or len(self.samples) != 2:
                return None
            first, last = self.samples
            distance = math.hypot(*(b-a for a, b in zip(first['position'], last['position'])))
            yaw = abs(math.atan2(math.sin(last['yaw']-first['yaw']),
                                 math.cos(last['yaw']-first['yaw'])))
            if distance > .005 + 1e-12 or yaw > math.radians(1) + 1e-12:
                raise ValueError('Base pose is not stable across the two odometry samples')
            return dict(event='resume_base_check', requested_ns=self.requested_ns,
                        completed_ns=now_ns, samples=[copy.deepcopy(value['raw']) for value in self.samples],
                        publishers=publishers, stationary=True, frames=dict(last['frames']),
                        duplicates_ignored=self.duplicates_ignored)
        except (ValueError, TypeError, OverflowError) as error:
            self.failure = str(error)
            raise ValueError(self.failure) from error


def check_lease(path, now):
    lease = object_json(Path(path).read_text())
    deadline = number(lease.get('deadline'), 'control lease deadline')
    if not math.isfinite(now) or now >= deadline:
        raise RuntimeError('Control lease expired')


class NativeReader:
    def __init__(self):
        import rosa
        from rosa.base._QoS import SensorDataQoS
        from rosa.utils import resolve_message_type
        self.rosa = rosa
        self.acquisition = None
        self.failure = None
        rosa.init()
        try:
            self.node = rosa.Node('scenario1_resume_base_readonly')
            qos = SensorDataQoS()
            qos.bestEffort()
            qos.durabilityVolatile()
            qos.keepLast(5)
            def receive(raw: str):
                if self.acquisition is not None and self.failure is None:
                    try:
                        self.acquisition.add(raw, time.time_ns())
                    except Exception as error:
                        self.failure = error
            self.reader = self.node.create_reader(resolve_message_type(TYPE), TOPIC, receive, qos=qos)
        except BaseException:
            rosa.shutdown()
            raise

    def publisher_count(self):
        return self.reader.getWriterCount()

    def spin(self):
        if self.failure is not None:
            raise self.failure
        if not self.rosa.ok():
            raise RuntimeError('ROSA context stopped')
        self.rosa.spin_once(self.node, 20)
        if self.failure is not None:
            raise self.failure

    def close(self):
        self.rosa.shutdown()


def collect(native, lease_file, *, clock=time.monotonic, wall=time.time_ns, timeout=5.):
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 5:
        raise ValueError('Resume telemetry timeout must be within five seconds')
    deadline = clock() + timeout
    native.acquisition = Acquisition(wall())
    try:
        while clock() < deadline:
            check_lease(lease_file, clock())
            count = native.publisher_count()
            if type(count) is not int or count > 1 or count < 0:
                raise ValueError('Exactly one odometry publisher is required')
            native.spin()
            check_lease(lease_file, clock())
            result = native.acquisition.complete(wall(), native.publisher_count())
            if clock() >= deadline:
                break
            if result is not None:
                return result
        raise TimeoutError('Fresh stationary odometry unavailable within resume check deadline')
    finally:
        native.acquisition = None


@contextmanager
def native_stdout_to_stderr():
    """Keep Python and native diagnostics away from the single JSON stdout line."""
    sys.stdout.flush()
    original = os.dup(1)
    try:
        os.dup2(2, 1)
        yield
    finally:
        sys.stdout.flush()
        os.dup2(original, 1)
        os.close(original)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lease-file', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        check_lease(args.lease_file, time.monotonic())
        deadline = time.monotonic() + 5.
        with native_stdout_to_stderr():
            native = NativeReader()
            try:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('Resume reader initialization exceeded five seconds')
                result = collect(native, args.lease_file, timeout=remaining)
            finally:
                native.close()
        code = 0
    except Exception as error:
        result = dict(event='error', reason=type(error).__name__ + ': ' + str(error))
        code = 78
        print(result['reason'], file=sys.stderr)
    print(json.dumps(result, allow_nan=False), flush=True)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
