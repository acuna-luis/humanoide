"""Persistent odometry requests reuse the existing strict resume gate offline."""
import copy
import json
import math
import sys
import threading
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from scripts.box_handling import scenario1_health_worker as worker


START = 10_000_000_000
MS = 1_000_000


def odometry(stamp, *, x=0., yaw=0., speed=0., turn=0.):
    return dict(header=dict(frame_id='odom', stamp=dict(sec=stamp//10**9, nanosec=stamp % 10**9)),
                child_frame_id='base_link',
                pose=dict(pose=dict(position=dict(x=x, y=0., z=0.),
                                    orientation=dict(x=0., y=0., z=math.sin(yaw/2), w=math.cos(yaw/2)))),
                twist=dict(twist=dict(linear=dict(x=speed, y=0., z=0.),
                                      angular=dict(x=0., y=0., z=turn))))


def acquisition():
    return worker.Acquisition(dict(request_id='base-1', command='base'), START, 100)


def warm():
    result = acquisition()
    for offset in (100, 200):
        result.add('odom', odometry(START+offset*MS), START+(offset+1)*MS, 100+offset)
    return result


class BaseRequestTests(unittest.TestCase):
    def test_base_default_and_timeout_are_bounded_by_five_seconds(self):
        self.assertEqual(worker.validate_request(dict(request_id='b', command='base'))['timeout'], 5.)
        for timeout in (0, -1, 5.001, True, float('nan'), float('inf')):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                worker.validate_request(dict(request_id='b', command='base', timeout=timeout))
        self.assertEqual(worker.validate_request(dict(request_id='b', command='base', timeout=.2))['timeout'], .2)
        with self.assertRaisesRegex(ValueError, 'require_home'):
            worker.validate_request(dict(request_id='b', command='base', require_home=True))
        self.assertEqual(worker.validate_request(dict(request_id='h', command='health'))['timeout'], 12.)
        self.assertEqual(worker.validate_request(dict(request_id='p', command='pose'))['timeout'], 12.)

    def test_two_new_stationary_samples_emit_base_schema_without_controller(self):
        result = warm().complete(START+203*MS, publishers=1)
        self.assertEqual(result['event'], 'base_result')
        self.assertEqual(result['request_id'], 'base-1')
        self.assertEqual(result['requested_ns'], START)
        self.assertEqual(result['completed_ns'], START+203*MS)
        self.assertTrue(result['stationary'])
        self.assertEqual(result['publishers'], 1)
        self.assertEqual(result['frames'], dict(frame_id='odom', child_frame_id='base_link'))
        self.assertEqual(len(result['samples']), 2)
        self.assertNotIn('controller', result)
        self.assertNotIn('status', result)

    def test_queued_sources_and_pre_request_receipts_cannot_satisfy_request(self):
        result = acquisition()
        for offset in (-2, -1, 0):
            result.add('odom', odometry(START+offset), START+MS, 101)
        result.add('odom', odometry(START+MS), START+MS, 100)
        self.assertEqual(len(result.base.samples), 0)
        self.assertIsNone(result.complete(START+2*MS, publishers=1))

    def test_unrelated_streams_cannot_satisfy_base_request(self):
        result = acquisition()
        for name in ('pose', 'actuator', *worker.SAFETY):
            result.add(name, {}, START+MS, 101)
        self.assertIsNone(result.complete(START+2*MS, publishers=1))

    def test_duplicate_does_not_supply_second_sample_or_renew_receipt(self):
        result = acquisition()
        message = odometry(START+100*MS)
        result.add('odom', message, START+101*MS, 101)
        result.add('odom', copy.deepcopy(message), START+200*MS, 102)
        self.assertEqual(len(result.base.samples), 1)
        self.assertEqual(result.base.samples[-1]['received_ns'], START+101*MS)
        self.assertEqual(result.base.duplicates_ignored, 1)
        self.assertIsNone(result.complete(START+201*MS, publishers=1))
        result.add('odom', odometry(START+300*MS), START+301*MS, 103)
        self.assertEqual(result.complete(START+302*MS, publishers=1)['duplicates_ignored'], 1)

    def test_conflicting_duplicate_regression_and_frame_change_latch_failure(self):
        for problem in ('conflict', 'regression', 'frame'):
            result = acquisition()
            result.add('odom', odometry(START+100*MS), START+101*MS, 101)
            stamp = START+(99 if problem == 'regression' else 100 if problem == 'conflict' else 200)*MS
            second = odometry(stamp, x=.001 if problem == 'conflict' else 0.)
            if problem == 'frame':
                second['header']['frame_id'] = 'changed'
            with self.subTest(problem=problem), self.assertRaises(ValueError):
                result.add('odom', second, START+201*MS, 102)
            with self.assertRaises(ValueError):
                result.complete(START+202*MS, publishers=1)

    def test_stale_future_and_nonfinite_sources_are_rejected(self):
        for message, received in ((odometry(START+MS), START+502*MS),
                                  (odometry(START+2*MS), START+MS),
                                  (odometry(START+MS, x=float('nan')), START+MS)):
            with self.subTest(message=message), self.assertRaises(ValueError):
                acquisition().add('odom', message, received, 101)
        with self.assertRaisesRegex(ValueError, 'Stale'):
            warm().complete(START+701*MS, publishers=1)

    def test_motion_and_pose_drift_are_rejected_without_weakening_resume_limits(self):
        for change in (dict(speed=.003001), dict(turn=.010001)):
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'Base is moving'):
                acquisition().add('odom', odometry(START+MS, **change), START+2*MS, 101)
        for change in (dict(x=.005001), dict(yaw=math.radians(1.001))):
            result = acquisition()
            result.add('odom', odometry(START+100*MS), START+101*MS, 101)
            result.add('odom', odometry(START+200*MS, **change), START+201*MS, 102)
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'not stable'):
                result.complete(START+202*MS, publishers=1)

    def test_exactly_one_typed_publisher_is_required(self):
        self.assertIsNone(warm().complete(START+203*MS, publishers=0))
        for count in (2, -1, True, 1., None):
            with self.subTest(count=count), self.assertRaises(ValueError):
                warm().complete(START+203*MS, publishers=count)

    def test_results_do_not_alias_native_samples(self):
        result = warm()
        report = result.complete(START+203*MS, publishers=1)
        report['samples'][0]['pose']['pose']['position']['x'] = 100
        self.assertEqual(result.complete(START+203*MS, publishers=1)['samples'][0]['pose']['pose']['position']['x'], 0)


class NativeBaseTests(unittest.TestCase):
    def make_native(self, publishers=1, *, step_ms=100):
        native = worker.NativeReader.__new__(worker.NativeReader)
        native.acquisition = None
        native.controller = None
        native.status = None
        native.response_ready = threading.Event()
        native.client = Mock(side_effect=AssertionError('No controller request for odometry'))
        native.ensure_base_reader = Mock()
        native.readers = dict(odom=SimpleNamespace(getWriterCount=lambda: publishers))
        elapsed = {'ns': 0}
        clock = SimpleNamespace(time_ns=lambda: START+elapsed['ns'],
                                monotonic_ns=lambda: 100+elapsed['ns'],
                                monotonic=lambda: elapsed['ns']/1e9)
        def spin():
            elapsed['ns'] += step_ms*MS
            native.acquisition.add('odom', odometry(clock.time_ns()), clock.time_ns(), clock.monotonic_ns())
        native.spin = spin
        return native, clock, elapsed

    def test_persistent_acquire_returns_fresh_base_and_preserves_request_identity(self):
        native, clock, _ = self.make_native()
        request = worker.validate_request(dict(request_id='seq-4-1', command='base', timeout=5))
        guard = Mock()
        with patch.object(worker, 'time', clock):
            result = native.acquire(request, guard)
        self.assertEqual(result['request_id'], 'seq-4-1')
        self.assertEqual(result['event'], 'base_result')
        self.assertEqual(result['publishers'], 1)
        self.assertGreater(worker.source_stamp_ns(result['samples'][0]), result['requested_ns'])
        self.assertIsNone(native.acquisition)
        self.assertFalse(native.client.method_calls)
        self.assertGreaterEqual(guard.call_count, 4)

    def test_ambiguous_or_invalid_publisher_count_fails_without_waiting(self):
        for count in (2, -1, True, 1.):
            native, clock, elapsed = self.make_native(count)
            request = worker.validate_request(dict(request_id='base', command='base'))
            with self.subTest(count=count), patch.object(worker, 'time', clock), self.assertRaisesRegex(ValueError, 'Exactly one'):
                native.acquire(request, lambda: None)
            self.assertLess(elapsed['ns'], 5*10**9)
            self.assertIsNone(native.acquisition)

    def test_missing_publisher_times_out_and_releases_acquisition(self):
        native, clock, elapsed = self.make_native(0)
        request = worker.validate_request(dict(request_id='base', command='base', timeout=.3))
        with patch.object(worker, 'time', clock), self.assertRaisesRegex(TimeoutError, '"odom": 0'):
            native.acquire(request, lambda: None)
        self.assertEqual(elapsed['ns'], 300*MS)
        self.assertIsNone(native.acquisition)

    def test_no_result_is_returned_after_request_deadline(self):
        native, clock, elapsed = self.make_native(step_ms=3000)
        request = worker.validate_request(dict(request_id='base', command='base'))
        with patch.object(worker, 'time', clock), self.assertRaises(TimeoutError):
            native.acquire(request, lambda: None)
        self.assertEqual(elapsed['ns'], 6*10**9)
        self.assertIsNone(native.acquisition)

    def test_guard_failure_after_spin_is_not_masked_by_fresh_samples(self):
        native, clock, _ = self.make_native()
        checks = {'count': 0}
        def guard():
            checks['count'] += 1
            if checks['count'] == 6:
                raise RuntimeError('lease expired')
        request = worker.validate_request(dict(request_id='base', command='base'))
        with patch.object(worker, 'time', clock), self.assertRaisesRegex(RuntimeError, 'lease expired'):
            native.acquire(request, guard)
        self.assertIsNone(native.acquisition)

    def test_odometry_callback_does_not_pollute_live_safety_cache(self):
        native, clock, elapsed = self.make_native()
        native.fatal = None
        native.live_cache = Mock()
        native.acquisition = acquisition()
        elapsed['ns'] = 100*MS
        with patch.object(worker, 'time', clock):
            native.callback('odom')(json.dumps(odometry(clock.time_ns())))
        native.live_cache.add.assert_not_called()
        self.assertIsNone(native.fatal)
        self.assertEqual(len(native.acquisition.base.samples), 1)

    def test_one_lazy_passive_reader_is_reused(self):
        native = worker.NativeReader.__new__(worker.NativeReader)
        native.readers = {}
        native.node = SimpleNamespace(create_reader=Mock(return_value=object()))
        qos = Mock()
        modules = {name: ModuleType(name) for name in ('rosa', 'rosa.base', 'rosa.base._QoS', 'rosa.utils')}
        modules['rosa.base._QoS'].SensorDataQoS = Mock(return_value=qos)
        modules['rosa.utils'].resolve_message_type = lambda name: name
        with patch.dict(sys.modules, modules):
            native.ensure_base_reader()
            native.ensure_base_reader()
        native.node.create_reader.assert_called_once()
        args, kwargs = native.node.create_reader.call_args
        self.assertEqual(args[:2], ('nav_msgs/msg/Odometry', '/mc/odom'))
        self.assertTrue(callable(args[2]))
        self.assertIs(kwargs['qos'], qos)
        qos.bestEffort.assert_called_once_with()
        qos.durabilityVolatile.assert_called_once_with()
        qos.keepLast.assert_called_once_with(5)


if __name__ == '__main__':
    unittest.main()
