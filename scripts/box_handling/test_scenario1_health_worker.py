"""Offline freshness/protocol tests; the native ROSA imports remain lazy."""
import json
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

try:
    from . import scenario1_health_worker as worker
except ImportError:
    import scenario1_health_worker as worker


START = 10_000_000_000


def stamped(stamp):
    sec, nanosec = divmod(stamp, 10**9)
    return {'header': {'stamp': {'sec': sec, 'nanosec': nanosec}}, 'value': [1, 2]}


def acquisition(command='health'):
    return worker.Acquisition({'request_id': 'request-1', 'command': command}, START, 100)


def fill_health(collector):
    for key in worker.SAFETY:
        collector.add(key, {'data': 0}, START+1, 101)
    collector.add('actuator', stamped(START+1), START+1, 101)
    collector.add('actuator', stamped(START+2), START+2, 102)


class ProtocolTests(unittest.TestCase):
    def test_only_named_readonly_commands_are_allowed(self):
        for command in ('health', 'pose'):
            self.assertEqual(worker.validate_request({'request_id': 'a.1', 'command': command})['command'], command)
        for command in ('navigate', 'home', 'publish', '', None):
            with self.subTest(command=command), self.assertRaises(ValueError):
                worker.validate_request({'request_id': 'r', 'command': command})

    def test_unknown_fields_id_and_invalid_timeout_rejected(self):
        valid = {'request_id': 'r', 'command': 'health'}
        changes = ({'extra': True}, {'request_id': '../bad'}, {'request_id': 2},
                   {'timeout': True}, {'timeout': float('nan')}, {'timeout': 13},
                   {'timeout': 0}, {'require_home': 1})
        for changed in changes:
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                worker.validate_request(dict(valid, **changed))

    def test_duplicate_keys_and_nonfinite_messages_rejected(self):
        for value in ('{"data":0,"data":1}', '{"data":NaN}', '[]', 'null'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                worker.object_json(value)

    def test_source_stamp_requires_exact_nonzero_integer_fields(self):
        for stamp in ({'sec': 0, 'nanosec': 0}, {'sec': -1, 'nanosec': 0},
                      {'sec': True, 'nanosec': 1}, {'sec': 1, 'nanosec': 10**9},
                      {'sec': 1, 'nanosec': 0.1}):
            with self.subTest(stamp=stamp), self.assertRaises(ValueError):
                worker.source_stamp_ns({'header': {'stamp': stamp}})


class AcquisitionTests(unittest.TestCase):
    def test_health_needs_new_four_safety_two_actuators_and_controller(self):
        collector = acquisition()
        self.assertIsNone(collector.complete(START+10, {}, {}))
        fill_health(collector)
        self.assertIsNone(collector.complete(START+10, None, {}))
        self.assertIsNone(collector.complete(START+10, {}, None))
        result = collector.complete(START+10, {'controller': []}, {'status_list': []})
        self.assertEqual(result['event'], 'health_result')
        self.assertEqual(result['request_id'], 'request-1')
        self.assertEqual(result['requested_ns'], START)
        self.assertEqual(result['completed_ns'], START+10)
        self.assertTrue(result['status_retained'])
        self.assertEqual(len(result['actuator']), 2)
        self.assertEqual(set(result['safety']), set(worker.SAFETY))
        self.assertEqual(result['actuator_duplicates_ignored'], 0)

    def test_pre_request_receipts_cannot_satisfy_health(self):
        collector = acquisition()
        for key in worker.SAFETY:
            collector.add(key, {'data': 0}, START+1, 99)
        collector.add('actuator', stamped(START+1), START+1, 99)
        collector.add('actuator', stamped(START+2), START+2, 100)
        self.assertIsNone(collector.complete(START+10, {}, {}))
        self.assertEqual(collector.safety, {})
        self.assertEqual(len(collector.samples), 0)

    def test_queued_old_source_cannot_satisfy_new_pose_request(self):
        collector = acquisition('pose')
        collector.add('pose', stamped(START-10), START+1, 101)
        collector.add('pose', stamped(START-5), START+2, 102)
        self.assertIsNone(collector.complete(START+10))

    def test_pose_result_requires_two_advancing_current_sources(self):
        collector = acquisition('pose')
        collector.add('pose', stamped(START+1), START+2, 101)
        self.assertIsNone(collector.complete(START+3))
        collector.add('pose', stamped(START+3), START+4, 102)
        result = collector.complete(START+5)
        self.assertEqual(result['event'], 'pose_result')
        self.assertEqual(len(result['poses']), 2)
        self.assertNotIn('controller', result)

    def test_regressing_source_fails_even_before_request_after_new_sample(self):
        for key, command in (('actuator', 'health'), ('pose', 'pose')):
            for second in (START+1, START-1):
                collector = acquisition(command)
                collector.add(key, stamped(START+2), START+2, 101)
                with self.subTest(key=key, second=second), self.assertRaisesRegex(ValueError, 'Nonadvancing'):
                    collector.add(key, stamped(second), START+3, 102)

    def test_same_pose_timestamp_still_fails_even_with_identical_content(self):
        collector = acquisition('pose')
        collector.add('pose', stamped(START+1), START+1, 101)
        with self.assertRaisesRegex(ValueError, 'Nonadvancing pose source timestamp'):
            collector.add('pose', stamped(START+1), START+2, 102)

    def test_identical_actuator_duplicate_does_not_refresh_sample_or_receipt(self):
        collector = acquisition()
        fill_health(collector)
        samples = list(collector.samples)
        receipts = dict(collector.receipts)
        # Object order/JSON whitespace differ; all fields and their types agree.
        duplicate = {'value': [1, 2], 'header': {'stamp': {'nanosec': 2, 'sec': 10}}}
        collector.add('actuator', json.dumps(duplicate, indent=2), START+100, 200)
        self.assertEqual(list(collector.samples), samples)
        self.assertEqual(collector.receipts, receipts)
        self.assertEqual(collector.last_stamp, START+2)
        self.assertEqual(collector.duplicates_ignored, 1)
        self.assertEqual(collector.complete(START+101, {}, {})['actuator_duplicates_ignored'], 1)

    def test_duplicates_never_substitute_for_a_second_new_source(self):
        collector = acquisition()
        for key in worker.SAFETY:
            collector.add(key, {'data': 0}, START+1, 101)
        collector.add('actuator', stamped(START+1), START+1, 101)
        for offset in range(2, 102):
            collector.add('actuator', stamped(START+1), START+offset, 100+offset)
            self.assertIsNone(collector.complete(START+offset, {}, {}))
        self.assertEqual(len(collector.samples), 1)
        self.assertEqual(collector.duplicates_ignored, 100)
        collector.add('actuator', stamped(START+102), START+102, 202)
        result = collector.complete(START+103, {}, {})
        self.assertEqual([worker.source_stamp_ns(row) for row in result['actuator']], [START+1, START+102])
        self.assertEqual(result['actuator_duplicates_ignored'], 100)

    def test_same_actuator_stamp_with_different_payload_is_a_conflict(self):
        # Python's True == 1 and 1.0 == 1 must not hide changed field types.
        for changed in ([1, 3], [True, 2], [1.0, 2], [2, 1]):
            collector = acquisition()
            collector.add('actuator', stamped(START+1), START+1, 101)
            duplicate = stamped(START+1)
            duplicate['value'] = changed
            with self.subTest(changed=changed), self.assertRaisesRegex(ValueError, 'Conflicting actuator samples'):
                collector.add('actuator', duplicate, START+2, 102)
            self.assertEqual(collector.duplicates_ignored, 0)

    def test_stale_duplicate_is_rejected_before_it_can_be_ignored(self):
        collector = acquisition()
        collector.add('actuator', stamped(START+1), START+1, 101)
        with self.assertRaisesRegex(ValueError, 'Stale or future actuator source timestamp'):
            collector.add('actuator', stamped(START+1), START+worker.MAX_AGE_NS+2, 102)
        self.assertEqual(collector.duplicates_ignored, 0)

    def test_two_frozen_sources_cannot_pass_when_controller_is_slow(self):
        for controller in (None, {'controller': []}):
            collector = acquisition()
            fill_health(collector)
            collector.add('actuator', stamped(START+2), START+worker.MAX_AGE_NS, 1000)
            now = START+worker.MAX_AGE_NS+3
            for key in worker.SAFETY:
                collector.add(key, {'data': 0}, now, 1001)
            with self.subTest(controller=controller), self.assertRaisesRegex(ValueError, 'source samples became stale'):
                collector.complete(now, controller, {'status_list': []})
            self.assertEqual(collector.receipts['actuator'], START+2)

    def test_initial_queued_actuator_data_does_not_count_as_a_duplicate(self):
        collector = acquisition()
        for offset in (-2, -1):
            collector.add('actuator', stamped(START+offset), START+1, 101)
        self.assertEqual(len(collector.samples), 0)
        self.assertEqual(collector.duplicates_ignored, 0)
        self.assertIsNone(collector.last_stamp)

    def test_stale_and_future_sources_fail(self):
        for source, receipt in ((START+1, START+worker.MAX_AGE_NS+2), (START+5, START+1)):
            with self.subTest(source=source), self.assertRaises(ValueError):
                acquisition('pose').add('pose', stamped(source), receipt, 101)

    def test_two_latest_samples_are_kept_if_controller_is_slow(self):
        collector = acquisition()
        fill_health(collector)
        for offset in range(3, 100):
            collector.add('actuator', stamped(START+offset), START+offset, 100+offset)
        rows = collector.complete(START+100, {}, {})['actuator']
        self.assertEqual([worker.source_stamp_ns(row) for row in rows], [START+98, START+99])

    def test_advancing_stream_survives_controller_delay_longer_than_source_age(self):
        collector = acquisition()
        for step in range(1, 13):
            now = START+step*250_000_000
            for key in worker.SAFETY:
                collector.add(key, {'data': 0}, now, 100+step)
            collector.add('actuator', stamped(now), now, 100+step)
            self.assertIsNone(collector.complete(now, None, {'status_list': []}))
        rows = collector.complete(now, {}, {})['actuator']
        self.assertEqual([worker.source_stamp_ns(row) for row in rows],
                         [START+2_750_000_000, START+3_000_000_000])

    def test_stale_safety_cannot_be_hidden_by_new_actuators(self):
        collector = acquisition()
        fill_health(collector)
        now = START+worker.MAX_AGE_NS+10
        collector.add('actuator', stamped(now-1), now-1, 1000)
        collector.add('actuator', stamped(now), now, 1001)
        with self.assertRaisesRegex(ValueError, 'safety'):
            collector.complete(now, {}, {})

    def test_acquired_samples_cannot_be_mutated_by_caller(self):
        collector = acquisition('pose')
        message = stamped(START+1)
        collector.add('pose', message, START+1, 101)
        message['value'][0] = 900
        collector.add('pose', stamped(START+2), START+2, 102)
        first = collector.complete(START+3)
        first['poses'][0]['value'][0] = 800
        self.assertEqual(collector.complete(START+3)['poses'][0]['value'], [1, 2])

    def test_unrelated_stream_does_not_satisfy_acquisition(self):
        collector = acquisition('pose')
        fill_health(collector)
        self.assertIsNone(collector.complete(START+10))


class LeaseTests(unittest.TestCase):
    def test_control_and_general_lease_are_both_required(self):
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory)
            for name in ('lease.json', 'control-lease.json'):
                (session/name).write_text('{"deadline":200}')
            self.assertTrue(worker.session_active(session, 100))
            self.assertFalse(worker.session_active(session, 200))
            (session/'control-lease.json').write_text('{"deadline":0}')
            self.assertFalse(worker.session_active(session, 100))
            (session/'control-lease.json').unlink()
            with self.assertRaises(FileNotFoundError):
                worker.session_active(session, 100)
            (session/'stop').touch()
            self.assertFalse(worker.session_active(session, 100))

    def test_expired_session_exits_without_importing_rosa(self):
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory)
            (session/'lease.json').write_text('{"deadline":0}')
            (session/'control-lease.json').write_text('{"deadline":0}')
            self.assertEqual(worker.main(['--session', directory]), 0)


class NativeHandshakeTests(unittest.TestCase):
    def make_native(self):
        native = worker.NativeReader.__new__(worker.NativeReader)
        native.acquisition = None
        native.controller = None
        native.status = {'status_list': []}
        native.response_ready = threading.Event()
        calls = []

        class Client:
            ready = False

            def getServiceCount(self):
                return 1

            def wait_service(self, timeout):
                calls.append(('wait', timeout))
                self.ready = True
                return True

            def call_async(self, request, callback):
                if not self.ready:
                    raise RuntimeError('Service not ready: missing waitForService')
                calls.append(('call', request))
                callback()
                return object()

            def get_result(self, future, json_format):
                return '{"controller":[]}'

        native.client = Client()
        native.readers = {key: SimpleNamespace(getWriterCount=lambda: 1) for key in worker.TOPICS}

        def spin():
            now, arrival = time.time_ns(), time.monotonic_ns()
            for key in worker.SAFETY:
                native.acquisition.add(key, {'data': 0}, now, arrival)
            key = 'actuator' if native.acquisition.request['command'] == 'health' else 'pose'
            native.acquisition.add(key, stamped(now), now, arrival)
            native.acquisition.add(key, stamped(now+1), now+1, arrival+1)
        native.spin = spin
        return native, calls

    def test_native_service_requires_explicit_bounded_wait_before_call(self):
        native, calls = self.make_native()
        request = worker.validate_request({'request_id': 'native-1', 'command': 'health'})
        result = native.acquire(request, lambda: None)
        self.assertEqual(calls, [('wait', 0), ('call', '{}')])
        self.assertEqual(result['event'], 'health_result')
        self.assertIsNone(native.acquisition)

    def test_lease_revoked_during_readiness_prevents_service_call(self):
        native, calls = self.make_native()
        checks = 0

        def guard():
            nonlocal checks
            checks += 1
            if checks > 1:
                raise RuntimeError('Lease expired')
        request = worker.validate_request({'request_id': 'native-2', 'command': 'health'})
        with self.assertRaisesRegex(RuntimeError, 'Lease expired'):
            native.acquire(request, guard)
        self.assertEqual(calls, [('wait', 0)])

    def test_two_pose_publishers_with_new_samples_preserve_previous_ros2_contract(self):
        native, calls = self.make_native()
        native.readers['pose'] = SimpleNamespace(getWriterCount=lambda: 2)
        request = worker.validate_request({'request_id': 'pose-1', 'command': 'pose'})
        result = native.acquire(request, lambda: None)
        self.assertEqual(result['publisher_count'], 2)
        self.assertEqual(len(result['poses']), 2)
        self.assertGreater(worker.source_stamp_ns(result['poses'][0]), result['requested_ns'])
        self.assertGreater(worker.source_stamp_ns(result['poses'][1]), worker.source_stamp_ns(result['poses'][0]))
        self.assertEqual(calls, [])

    def test_two_publishers_do_not_relax_health_uniqueness(self):
        native, _ = self.make_native()
        native.readers['actuator'] = SimpleNamespace(getWriterCount=lambda: 2)
        request = worker.validate_request({'request_id': 'health-two', 'command': 'health', 'timeout': .005})
        with self.assertRaisesRegex(TimeoutError, '"actuator": 2'):
            native.acquire(request, lambda: None)

    def test_two_pose_publishers_with_only_old_samples_fail_with_diagnostic(self):
        native, _ = self.make_native()
        native.readers['pose'] = SimpleNamespace(getWriterCount=lambda: 2)
        def spin():
            old = native.acquisition.requested_ns-1
            native.acquisition.add('pose', stamped(old), time.time_ns(), time.monotonic_ns())
        native.spin = spin
        request = worker.validate_request({'request_id': 'pose-old', 'command': 'pose', 'timeout': .005})
        with self.assertRaisesRegex(TimeoutError, '"fresh_samples": 0.*"pose": 2'):
            native.acquire(request, lambda: None)

    def test_no_pose_callbacks_fail_even_when_publishers_are_discovered(self):
        native, _ = self.make_native()
        native.readers['pose'] = SimpleNamespace(getWriterCount=lambda: 2)
        native.spin = lambda: None
        request = worker.validate_request({'request_id': 'pose-empty', 'command': 'pose', 'timeout': .005})
        with self.assertRaisesRegex(TimeoutError, '"fresh_samples": 0.*"pose": 2'):
            native.acquire(request, lambda: None)

    def test_frozen_single_source_then_silence_times_out_within_twelve_seconds(self):
        native, calls = self.make_native()
        elapsed = {'ns': 0}
        collectors, checks = [], []
        clock = SimpleNamespace(time_ns=lambda: START+elapsed['ns'],
                                monotonic_ns=lambda: 100+elapsed['ns'],
                                monotonic=lambda: elapsed['ns']/1e9)

        def spin():
            elapsed['ns'] += 250_000_000
            current = native.acquisition
            collectors.append(current)
            now = clock.time_ns()
            for key in worker.SAFETY:
                current.add(key, {'data': 0}, now, clock.monotonic_ns())
            if elapsed['ns'] <= 1_000_000_000:
                current.add('actuator', stamped(START+250_000_000), now, clock.monotonic_ns())

        native.spin = spin
        request = worker.validate_request({'request_id': 'frozen-source', 'command': 'health', 'timeout': 12})
        with patch.object(worker, 'time', clock):
            with self.assertRaisesRegex(TimeoutError, '"fresh_samples": 1'):
                native.acquire(request, lambda: checks.append(clock.monotonic()))
        self.assertEqual(elapsed['ns'], 12_000_000_000)
        self.assertEqual(collectors[-1].duplicates_ignored, 3)
        self.assertEqual(len(collectors[-1].samples), 1)
        self.assertEqual(calls, [('wait', 0), ('call', '{}')])
        self.assertGreater(len(checks), 1)
        self.assertTrue(all(instant <= 12 for instant in checks))
        self.assertIsNone(native.acquisition)


if __name__ == '__main__':
    unittest.main()
