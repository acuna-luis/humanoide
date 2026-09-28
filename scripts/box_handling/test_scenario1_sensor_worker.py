"""Offline contract checks for the read-only sensor collector (no ROS imports)."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

try:
    from . import scenario1_sensor_worker as worker
except ImportError:
    import scenario1_sensor_worker as worker


def header(sec=12, nanosec=345, frame='force_torque_sensor_controller'):
    return NS(stamp=NS(sec=sec, nanosec=nanosec), frame_id=frame)


def wrench():
    return NS(header=header(), wrench=NS(force=NS(x=1, y=-2, z=3.5),
                                        torque=NS(x=-0.1, y=0.2, z=0)))


def joints():
    return NS(header=header(frame=''), name=['left_joint', 'right_joint'],
              position=[0.3, -0.4], velocity=[0, 0.01])


def leases(session, control=200, general=300):
    (session/'control-lease.json').write_text(json.dumps({'deadline': control}))
    (session/'lease.json').write_text(json.dumps({'deadline': general}))


class SerializationTests(unittest.TestCase):
    def test_wrench_preserves_raw_axes_frame_and_exact_source_stamp(self):
        sample = worker.wrench_sample(wrench(), 12_000_001_000)
        self.assertEqual(sample, {
            'stamp_ns': 12_000_000_345, 'received_ns': 12_000_001_000,
            'frame_id': 'force_torque_sensor_controller',
            'force': [1.0, -2.0, 3.5], 'torque': [-0.1, 0.2, 0.0],
        })

    def test_rejects_missing_frame_and_malformed_message(self):
        message = wrench()
        message.header.frame_id = ''
        with self.assertRaises(ValueError):
            worker.wrench_sample(message, 1)
        with self.assertRaises(ValueError):
            worker.wrench_sample(NS(), 1)

    def test_rejects_nonfinite_and_boolean_force(self):
        for value in (float('nan'), float('inf'), -float('inf'), True, '1'):
            with self.subTest(value=value):
                message = wrench()
                message.wrench.force.y = value
                with self.assertRaises(ValueError):
                    worker.wrench_sample(message, 1)

    def test_requires_valid_nonzero_source_stamp(self):
        for sec, nanosec in ((0, 0), (-1, 0), (1, -1), (1, 1_000_000_000),
                             (True, 0), (1, 0.5)):
            with self.subTest(sec=sec, nanosec=nanosec):
                with self.assertRaises(ValueError):
                    worker.stamp_ns(header(sec, nanosec))

    def test_requires_positive_integer_receipt_stamp(self):
        for receipt in (0, -1, True, 1.5):
            with self.subTest(receipt=receipt), self.assertRaises(ValueError):
                worker.wrench_sample(wrench(), receipt)

    def test_frozen_or_reversing_source_clock_is_rejected(self):
        previous = worker.advance_source_stamp(None, 100)
        self.assertEqual(worker.advance_source_stamp(previous, 101), 101)
        for current in (100, 99, 0, -1, True):
            with self.subTest(current=current), self.assertRaises(ValueError):
                worker.advance_source_stamp(previous, current)

    def test_joint_positions_velocities_and_names_are_retained(self):
        sample = worker.joint_sample(joints(), 12_000_001_000)
        self.assertEqual(sample, {
            'stamp_ns': 12_000_000_345, 'received_ns': 12_000_001_000,
            'names': ['left_joint', 'right_joint'], 'position': [0.3, -0.4],
            'velocity': [0.0, 0.01],
        })

    def test_incomplete_or_duplicate_joints_do_not_become_readiness(self):
        for field, value in (('name', []), ('name', ['same', 'same']),
                             ('name', ['left', '']), ('velocity', []),
                             ('position', [0]), ('velocity', [0, float('nan')])):
            with self.subTest(field=field, value=value):
                message = joints()
                setattr(message, field, value)
                with self.assertRaises(ValueError):
                    worker.joint_sample(message, 1)


class BufferTests(unittest.TestCase):
    def test_streams_are_independent_and_ready_requires_all_three(self):
        buffer = worker.SensorBuffer()
        self.assertFalse(buffer.ready(0))
        for stream in ('left', 'right'):
            self.assertTrue(buffer.add(stream, {'raw': [1]}, 0))
            self.assertFalse(buffer.ready(0))
        buffer.add('joints', {'raw': [2]}, 0)
        self.assertTrue(buffer.ready(0))
        self.assertFalse(buffer.ready(worker.WINDOW_NS))

    def test_arrival_rate_is_capped_at_100_hz(self):
        buffer = worker.SensorBuffer()
        self.assertTrue(buffer.add('left', {'n': 1}, 0))
        self.assertFalse(buffer.add('left', {'n': 2}, 9_999_999))
        self.assertTrue(buffer.add('left', {'n': 3}, 10_000_000))
        self.assertEqual(buffer.snapshot(1, 10_000_000)['ft']['left'],
                         [{'n': 1}, {'n': 3}])

    def test_storage_is_bounded_to_two_arrival_seconds(self):
        buffer = worker.SensorBuffer()
        for number in range(301):
            buffer.add('left', {'n': number}, number*10_000_000)
        rows = buffer.snapshot(1, 3_000_000_000)['ft']['left']
        self.assertEqual(len(rows), 200)
        self.assertEqual((rows[0]['n'], rows[-1]['n']), (101, 300))
        self.assertEqual(buffer.snapshot(1, 5_000_000_000)['ft']['left'], [])

    def test_no_sample_can_be_changed_through_aliases(self):
        buffer = worker.SensorBuffer()
        sample = {'force': [1, 2, 3]}
        buffer.add('left', sample, 0)
        sample['force'][0] = 900
        first = buffer.snapshot(1, 0)
        first['ft']['left'][0]['force'][1] = 900
        self.assertEqual(buffer.snapshot(1, 0)['ft']['left'][0]['force'], [1, 2, 3])

    def test_backwards_arrival_clock_is_rejected(self):
        buffer = worker.SensorBuffer()
        buffer.add('right', {}, 10)
        with self.assertRaises(ValueError):
            buffer.add('left', {}, 9)
        with self.assertRaises(ValueError):
            buffer.snapshot(1, 9)

    def test_malformed_sample_is_rejected_even_within_rate_limit(self):
        buffer = worker.SensorBuffer()
        buffer.add('left', {}, 0)
        with self.assertRaises(ValueError):
            buffer.add('left', {'force': [float('nan')]}, 1)
        with self.assertRaises(ValueError):
            buffer.add('unknown', {}, 1)

    def test_snapshot_write_is_complete_and_replaces_previous_snapshot(self):
        buffer = worker.SensorBuffer()
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory)
            (session/'sensors.json').write_text('previous')
            result = worker.write_snapshot(session, buffer, 12, 0)
            self.assertEqual(result, {'version': 1, 'written_ns': 12,
                                     'ft': {'left': [], 'right': []}, 'joints': []})
            self.assertEqual(json.loads((session/'sensors.json').read_text()), result)
            self.assertEqual([p.name for p in session.iterdir()], ['sensors.json'])


class LeaseTests(unittest.TestCase):
    def test_both_leases_must_be_current(self):
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory)
            leases(session)
            self.assertTrue(worker.session_active(session, 100))
            self.assertFalse(worker.session_active(session, 200))
            leases(session, control=300, general=150)
            self.assertFalse(worker.session_active(session, 150))

    def test_stop_wins_even_if_leases_are_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory)
            (session/'stop').touch()
            self.assertFalse(worker.session_active(session, 100))

    def test_missing_or_malformed_lease_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory)
            with self.assertRaises(FileNotFoundError):
                worker.session_active(session, 100)
            leases(session)
            for bad in ('broken', '[]', '{}', '{"deadline":true}',
                        '{"deadline":"200"}', '{"deadline":NaN}'):
                with self.subTest(bad=bad):
                    (session/'control-lease.json').write_text(bad)
                    with self.assertRaises(ValueError):
                        worker.session_active(session, 100)

    def test_expired_main_exits_without_ros_or_fake_readiness(self):
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory)
            leases(session, control=0)
            (session/'sensors.ready').write_text('stale')
            with patch.object(worker.time, 'monotonic', return_value=100):
                self.assertEqual(worker.main(['--session', directory]), 0)
            self.assertFalse((session/'sensors.ready').exists())
            self.assertFalse((session/'sensors.json').exists())
            self.assertFalse((session/'sensors.error').exists())

    def test_main_records_invalid_session_lease_without_ready_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory)
            (session/'sensors.ready').touch()
            self.assertEqual(worker.main(['--session', directory]), 78)
            self.assertIn('FileNotFoundError', (session/'sensors.error').read_text())
            self.assertFalse((session/'sensors.ready').exists())


if __name__ == '__main__':
    unittest.main()
