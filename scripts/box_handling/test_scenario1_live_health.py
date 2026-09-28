"""Offline continuous-health regressions, including the optional worker path."""
import copy
import json
from pathlib import Path
import stat
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from scripts.box_handling import scenario1_health_worker as worker
from scripts.box_handling import scenario1_live_health as live
from scripts.lib.cruzr_home_posture_gate import BODY_ACTUATOR_ALIASES


NOW = 10_000_000_000
MONO = 20_000_000_000


def actuator(stamp, *, velocity=0., position=0., command=None):
    sec, nanosec = divmod(stamp, 10**9)
    return dict(header=dict(stamp=dict(sec=sec, nanosec=nanosec)), act_item=[
        dict(id=aliases[0], name=name, error_code=0, status=7, position=position,
             velocity=velocity, cmd_pos=position if command is None else command)
        for name, aliases in BODY_ACTUATOR_ALIASES])


def controllers():
    return dict(controller=[dict(name=name, state=state) for name, state in (
        ('manipulation_controller', 'running'), ('sdk_controller', 'initialized'),
        ('vla_sdk_controller', 'initialized'))])


def cache():
    value = live.LiveHealthCache()
    for key in ('estop', 'servo', 'charger'):
        value.add(key, {'data': 0}, NOW, MONO)
    value.add('battery', {'packs': [{'batsoc': 55.}, {'batsoc': 56.}]}, NOW, MONO)
    value.add('status', {'status_list': []}, NOW, MONO)
    value.add('controller', controllers(), NOW, MONO)
    value.add('actuator', actuator(NOW-30_000_000), NOW-20_000_000, MONO-20_000_000)
    value.add('actuator', actuator(NOW-10_000_000), NOW, MONO)
    value.set_publishers(dict.fromkeys(live.PUBLISHERS, 1))
    return value


def check(value, *, offset=0, **kwargs):
    snapshot = value.snapshot(NOW+offset, MONO+offset)
    return live.validate_snapshot(snapshot, now_ns=NOW+offset, now_monotonic_ns=MONO+offset, **kwargs)


class ContinuousCacheTests(unittest.TestCase):
    def test_startup_pending_is_not_a_healthy_report(self):
        value = live.LiveHealthCache()
        value.set_publishers(dict.fromkeys(live.PUBLISHERS, 0))
        with self.assertRaises(live.LiveHealthPending):
            check(value)
        self.assertIsNone(value.error)

    def test_complete_snapshot_preserves_values_and_does_not_claim_box_measurement(self):
        value = cache()
        before = value.snapshot(NOW, MONO)
        report = check(value)
        self.assertEqual(report['safety']['battery_soc'], [55., 56.])
        self.assertFalse(report['stationary_checked'])
        self.assertFalse(report['box_state_measured'])
        self.assertEqual(value.snapshot(NOW, MONO), before)
        before['safety']['estop']['message']['data'] = 1
        self.assertEqual(value.safety['estop']['message']['data'], 0)

    def test_brief_estop_servo_and_charger_faults_latch_before_later_clear(self):
        for key in ('estop', 'servo', 'charger'):
            value = cache()
            with self.subTest(key=key), self.assertRaises(ValueError):
                value.add(key, {'data': 1}, NOW+1, MONO+1)
            fault = value.error
            with self.assertRaisesRegex(ValueError, 'LIVE_HEALTH_FAILED'):
                value.add(key, {'data': 0}, NOW+2, MONO+2)
            self.assertEqual(value.error, fault)
            with self.assertRaisesRegex(ValueError, 'LIVE_HEALTH_FAILED'):
                check(value, offset=3)

    def test_invalid_battery_cannot_wait_for_other_startup_streams(self):
        for battery in ({'packs': [{'batsoc': 55.}, {'batsoc': 1.}]},
                        {'packs': [{'batsoc': 55.}]},
                        {'packs': [{'batsoc': True}, {'batsoc': 55.}]}):
            value = live.LiveHealthCache()
            with self.subTest(battery=battery), self.assertRaises(ValueError):
                value.add('battery', battery, NOW, MONO)
            self.assertIsNotNone(value.error)

    def test_transient_actuator_fault_disabled_and_incomplete_20d_latch(self):
        for kind in ('error', 'fault', 'disabled', 'missing', 'duplicate', 'nonfinite', 'boolean'):
            value = cache()
            message = actuator(NOW+1)
            if kind == 'error': message['act_item'][0]['error_code'] = 1
            if kind == 'fault': message['act_item'][0]['status'] = 15
            if kind == 'disabled': message['act_item'][0]['status'] = 0
            if kind == 'missing': message['act_item'].pop()
            if kind == 'duplicate': message['act_item'].append(copy.deepcopy(message['act_item'][0]))
            if kind == 'nonfinite': message['act_item'][0]['velocity'] = float('inf')
            if kind == 'boolean': message['act_item'][0]['position'] = False
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                value.add('actuator', message, NOW+2, MONO+2)
            with self.assertRaisesRegex(ValueError, 'LIVE_HEALTH_FAILED'):
                value.add('actuator', actuator(NOW+3), NOW+4, MONO+4)

    def test_moving_measurements_are_not_rewritten_or_rejected_as_stationary(self):
        value = cache()
        for delta in (10_000_000, 20_000_000):
            value.add('actuator', actuator(NOW+delta, velocity=.3, position=.4, command=.5),
                      NOW+delta+1, MONO+delta+1)
        before = copy.deepcopy(list(value.actuator))
        report = check(value, offset=30_000_000)
        self.assertEqual(report['posture'][0]['max_abs_velocity'], .3)
        self.assertEqual(list(value.actuator), before)
        with self.assertRaisesRegex(live.LiveHealthPending, 'SETTLING'):
            check(value, offset=30_000_000, stationary=True)
        self.assertIsNone(value.error)  # Rest can be reached; no technical fault occurred.

    def test_identical_duplicate_keeps_original_receipt_and_cannot_prevent_expiry(self):
        value = cache()
        before = copy.deepcopy(list(value.actuator))
        duplicate = json.loads(json.dumps(before[-1]['message'], sort_keys=True))
        value.add('actuator', duplicate, NOW+900_000_000, MONO+900_000_000)
        self.assertEqual(list(value.actuator), before)
        self.assertEqual(value.duplicates_ignored, 1)
        # A newly written snapshot and new delivery cannot freshen frozen source stamps.
        with self.assertRaisesRegex(ValueError, 'STALE'):
            check(value, offset=2_000_000_001)
        with self.assertRaisesRegex(ValueError, 'STALE'):
            value.add('actuator', duplicate, NOW+2_000_000_001, MONO+2_000_000_001)

    def test_conflicting_duplicate_or_regression_is_a_latched_failure(self):
        for conflict in (True, False):
            value = cache()
            message = copy.deepcopy(value.actuator[-1]['message'])
            if conflict:
                message['act_item'][0]['position'] = .001
            else:
                message['header']['stamp']['nanosec'] -= 1
            with self.subTest(conflict=conflict), self.assertRaisesRegex(ValueError, 'nonadvancing'):
                value.add('actuator', message, NOW+1, MONO+1)
            self.assertIsNotNone(value.error)

    def test_status_active_is_allowed_only_during_motion_and_unknown_always_fails(self):
        value = cache()
        value.add('status', {'status_list': [{'status': 2}]}, NOW+1, MONO+1)
        self.assertEqual(check(value, offset=2)['status'], [2])
        with self.assertRaisesRegex(live.LiveHealthPending, 'terminal action status pending'):
            check(value, offset=2, stationary=True)
        with self.assertRaisesRegex(ValueError, 'STATUS'):
            value.add('status', {'status_list': [{'status': 0}]}, NOW+3, MONO+3)

    def test_controller_state_change_latches_even_if_following_reply_is_healthy(self):
        value = cache()
        changed = controllers()
        changed['controller'][0]['state'] = 'initialized'
        with self.assertRaisesRegex(ValueError, 'exclusive manipulation'):
            value.add('controller', changed, NOW+1, MONO+1)
        with self.assertRaisesRegex(ValueError, 'LIVE_HEALTH_FAILED'):
            value.add('controller', controllers(), NOW+2, MONO+2)

    def test_publisher_disappearance_ambiguity_and_boolean_counts_fail(self):
        for key in live.PUBLISHERS:
            for count in (0, 2, True):
                value = cache()
                changed = dict.fromkeys(live.PUBLISHERS, 1)
                changed[key] = count
                with self.subTest(key=key, count=count), self.assertRaisesRegex(ValueError, 'PUBLISHERS'):
                    value.set_publishers(changed)
                self.assertIsNotNone(value.error)

    def test_missing_startup_record_does_not_hide_an_existing_stale_record(self):
        value = cache()
        del value.safety['battery']
        with self.assertRaisesRegex(ValueError, 'STALE'):
            check(value, offset=2_000_000_001)


class SnapshotValidationTests(unittest.TestCase):
    def test_writer_stall_and_either_clock_regression_fail(self):
        snapshot = cache().snapshot(NOW, MONO)
        for wall, mono in ((NOW+1_000_000_001, MONO+1_000_000_001),
                           (NOW-1, MONO), (NOW, MONO-1)):
            with self.subTest(wall=wall, mono=mono), self.assertRaisesRegex(ValueError, 'STALE'):
                live.validate_snapshot(snapshot, now_ns=wall, now_monotonic_ns=mono)

    def test_each_dynamic_record_requires_fresh_wall_and_monotonic_receipt(self):
        paths = [('safety', key) for key in live.SAFETY]+[('actuator', 0), ('controller', None)]
        for parent, key in paths:
            for clock in ('received_ns', 'received_monotonic_ns'):
                snapshot = cache().snapshot(NOW, MONO)
                record = snapshot[parent] if key is None else snapshot[parent][key]
                maximum = 5_000_000_000 if parent == 'safety' and key in ('estop', 'servo') else 2_000_000_000
                record[clock] -= maximum+1
                with self.subTest(parent=parent, key=key, clock=clock), self.assertRaisesRegex(ValueError, 'STALE'):
                    live.validate_snapshot(snapshot, now_ns=NOW, now_monotonic_ns=MONO)

    def test_stop_receipts_remain_unchanged_and_report_real_age_through_five_seconds(self):
        value = cache()
        original = {key: copy.deepcopy(value.safety[key]) for key in ('estop', 'servo')}
        # Other continuously published streams advance; only the observed slow
        # stop streams retain their original, unaltered receipt timestamps.
        for offset in (0, 2_000_000_001, 4_492_012_000, 5_000_000_000):
            if offset:
                value.add('charger', {'data': 0}, NOW+offset, MONO+offset)
                value.add('battery', {'packs': [{'batsoc': 55.}, {'batsoc': 56.}]}, NOW+offset, MONO+offset)
                value.add('controller', controllers(), NOW+offset, MONO+offset)
                for delta in (offset-20_000_000, offset-10_000_000):
                    value.add('actuator', actuator(NOW+delta), NOW+delta, MONO+delta)
            result = check(value, offset=offset, stationary=True)
            for key in ('estop', 'servo'):
                self.assertEqual(value.safety[key], original[key])
                self.assertEqual(result['safety_receipts'][key],
                                 dict(age_ns=offset, monotonic_age_ns=offset, max_age_ns=5_000_000_000))
            for key in ('charger', 'battery'):
                self.assertEqual(result['safety_receipts'][key]['max_age_ns'], 2_000_000_000)
        # Merely taking or validating a new snapshot never freshens the stops.
        for key in ('estop', 'servo'):
            snapshot = value.snapshot(NOW+5_000_000_001, MONO+5_000_000_001)
            other = 'servo' if key == 'estop' else 'estop'
            snapshot['safety'][other]['received_ns'] = NOW+5_000_000_001
            snapshot['safety'][other]['received_monotonic_ns'] = MONO+5_000_000_001
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'STALE: '+key+' receipt'):
                live.validate_snapshot(snapshot, now_ns=NOW+5_000_000_001,
                                       now_monotonic_ns=MONO+5_000_000_001)

    def test_two_second_limits_for_battery_controller_and_actuators_are_not_widened(self):
        for parent, key in (('safety', 'battery'), ('safety', 'charger'),
                            ('controller', None), ('actuator', 0)):
            snapshot = cache().snapshot(NOW, MONO)
            row = snapshot[parent] if key is None else snapshot[parent][key]
            row['received_ns'] = NOW-2_000_000_001
            row['received_monotonic_ns'] = MONO-2_000_000_001
            with self.subTest(parent=parent, key=key), self.assertRaisesRegex(ValueError, 'STALE'):
                live.validate_snapshot(snapshot, now_ns=NOW, now_monotonic_ns=MONO)
        value = cache()
        duplicate = copy.deepcopy(value.actuator[-1]['message'])
        original = copy.deepcopy(list(value.actuator))
        with self.assertRaisesRegex(ValueError, 'STALE: actuator source at receipt'):
            value.add('actuator', duplicate, NOW+2_000_000_001, MONO+2_000_000_001)
        self.assertEqual(list(value.actuator), original)

    def test_status_is_explicitly_retained_but_future_receipts_are_rejected(self):
        snapshot = cache().snapshot(NOW, MONO)
        for clock in ('received_ns', 'received_monotonic_ns'):
            snapshot['status'][clock] -= 3_000_000_000
        self.assertEqual(live.validate_snapshot(snapshot, now_ns=NOW,
                         now_monotonic_ns=MONO, stationary=True)['status'], [])
        snapshot['status']['received_ns'] = NOW+1
        with self.assertRaisesRegex(ValueError, 'STALE'):
            live.validate_snapshot(snapshot, now_ns=NOW, now_monotonic_ns=MONO)

    def test_two_new_post_result_samples_required_even_when_earlier_samples_are_healthy(self):
        value = cache()
        with self.assertRaisesRegex(live.LiveHealthPending, 'after the action'):
            check(value, stationary=True, after_ns=NOW)
        value.add('actuator', actuator(NOW+10_000_000), NOW+10_000_001, MONO+10_000_001)
        with self.assertRaises(live.LiveHealthPending):
            check(value, offset=20_000_000, stationary=True, after_ns=NOW)
        value.add('actuator', actuator(NOW+30_000_000), NOW+30_000_001, MONO+30_000_001)
        result = check(value, offset=40_000_000, stationary=True, after_ns=NOW, require_home=True)
        self.assertTrue(result['stationary_checked'])
        self.assertTrue(result['home_required'])
        self.assertTrue(all(row['MEASURED_HOME'] == '1' for row in result['posture']))

    def test_home_is_measured_with_original_classifier_and_wrong_home_is_not_pending(self):
        value = cache()
        for delta in (1, 2):
            value.add('actuator', actuator(NOW+delta, position=.04), NOW+delta, MONO+delta)
        result = check(value, offset=3, stationary=True)
        self.assertTrue(all(row['MEASURED_HOME'] == '0' for row in result['posture']))
        with self.assertRaisesRegex(ValueError, 'HOME_NOT_MEASURED'):
            check(value, offset=3, stationary=True, require_home=True)

    def test_late_terminal_status_needs_actual_update_and_never_renews_telemetry(self):
        value = cache()
        value.add('status', {'status_list': [{'status': 2}]}, NOW+1, MONO+1)
        for delta in (10_000_000, 20_000_000):
            value.add('actuator', actuator(NOW+delta), NOW+delta+1, MONO+delta+1)
        with self.assertRaisesRegex(live.LiveHealthPending, 'terminal action status pending'):
            check(value, offset=30_000_000, stationary=True, after_ns=NOW)
        original = copy.deepcopy(list(value.actuator))
        value.add('status', {'status_list': [{'status': 4}]}, NOW+40_000_000, MONO+40_000_000)
        self.assertTrue(check(value, offset=50_000_000, stationary=True, after_ns=NOW)['stationary_checked'])
        self.assertEqual(list(value.actuator), original)
        with self.assertRaisesRegex(ValueError, 'STALE'):
            check(value, offset=3_000_000_000, stationary=True, after_ns=NOW)

    def test_source_freshness_cannot_be_replaced_by_new_receipt_or_snapshot(self):
        for mutation in ('old', 'future', 'same', 'reverse'):
            snapshot = cache().snapshot(NOW, MONO)
            if mutation in ('old', 'future'):
                stamp = NOW-3_000_000_000 if mutation == 'old' else NOW+1
                snapshot['actuator'][-1]['message'] = actuator(stamp)
            else:
                stamp = NOW-30_000_000 if mutation == 'same' else NOW-40_000_000
                snapshot['actuator'][-1]['message'] = actuator(stamp)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                live.validate_snapshot(snapshot, now_ns=NOW, now_monotonic_ns=MONO)

    def test_command_disagreement_waits_for_rest_without_claiming_home(self):
        value = cache()
        for delta in (1, 2):
            value.add('actuator', actuator(NOW+delta, command=.02), NOW+delta, MONO+delta)
        with self.assertRaisesRegex(live.LiveHealthPending, 'SETTLING'):
            check(value, offset=3, stationary=True, require_home=True)

    def test_snapshot_schema_flags_and_source_types_are_strict(self):
        for field, content in (('version', True), ('written_ns', True),
                               ('actuator_duplicates_ignored', True), ('error', False)):
            snapshot = cache().snapshot(NOW, MONO)
            snapshot[field] = content
            with self.subTest(field=field), self.assertRaises(ValueError):
                live.validate_snapshot(snapshot, now_ns=NOW, now_monotonic_ns=MONO)
        for kwargs in ({'stationary': 1}, {'require_home': True}, {'after_ns': True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                check(cache(), **kwargs)
        snapshot = cache().snapshot(NOW, MONO)
        snapshot['actuator'][0]['message']['header']['stamp']['sec'] = True
        with self.assertRaises(ValueError):
            live.validate_snapshot(snapshot, now_ns=NOW, now_monotonic_ns=MONO)


class OptionalWorkerTests(unittest.TestCase):
    def reader(self, directory):
        reader = worker.NativeReader.__new__(worker.NativeReader)
        reader.live_cache = cache()
        reader.live_module = live
        reader.live_session = Path(directory)
        reader.live_future = None
        reader.live_response_ready = threading.Event()
        reader.live_next_controller = 0.
        reader.live_last_write = 0.
        reader.readers = {key: SimpleNamespace(getWriterCount=lambda: 1)
                          for key in (*live.SAFETY, 'actuator', 'status')}
        reader.acquisition = None
        reader.status = None
        reader.fatal = None
        reader.client = object()  # Ordinary acquire() client must remain untouched.
        def call(raw, callback):
            callback()
            return 'live-future'
        reader.live_client = SimpleNamespace(getServiceCount=lambda: 1,
            wait_service=Mock(return_value=True), call_async=Mock(side_effect=call),
            get_result=Mock(return_value=controllers()))
        return reader

    def test_background_tick_uses_separate_client_and_writes_complete_atomic_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            reader = self.reader(directory)
            ordinary = reader.client
            with patch.object(worker.time, 'time_ns', return_value=NOW), \
                    patch.object(worker.time, 'monotonic_ns', return_value=MONO), \
                    patch.object(worker.time, 'monotonic', return_value=20.):
                reader._live_tick()
            self.assertEqual(reader.live_client.call_async.call_count, 1)
            reader.live_client.wait_service.assert_called_once_with(0)
            with patch.object(worker.time, 'time_ns', return_value=NOW+150_000_000), \
                    patch.object(worker.time, 'monotonic_ns', return_value=MONO+150_000_000), \
                    patch.object(worker.time, 'monotonic', return_value=20.15):
                reader._live_tick()
            snapshot = json.loads((Path(directory)/'live-health.json').read_text())
            live.validate_snapshot(snapshot, now_ns=NOW+150_000_000, now_monotonic_ns=MONO+150_000_000)
            self.assertEqual(list(Path(directory).iterdir()), [Path(directory)/'live-health.json'])
            self.assertIs(reader.client, ordinary)
            with patch.object(worker.time, 'time_ns', return_value=NOW+1_050_000_000), \
                    patch.object(worker.time, 'monotonic_ns', return_value=MONO+1_050_000_000), \
                    patch.object(worker.time, 'monotonic', return_value=21.05):
                reader._live_tick()
            self.assertEqual(reader.live_client.call_async.call_count, 2)

    def test_callback_fault_between_requests_is_persisted_and_fatal(self):
        with tempfile.TemporaryDirectory() as directory:
            reader = self.reader(directory)
            with patch.object(worker.time, 'time_ns', return_value=NOW+1), \
                    patch.object(worker.time, 'monotonic_ns', return_value=MONO+1):
                reader.callback('estop')('{"data":1}')
                reader.callback('estop')('{"data":0}')
            self.assertIsNotNone(reader.fatal)
            snapshot = json.loads((Path(directory)/'live-health.json').read_text())
            with self.assertRaisesRegex(ValueError, 'LIVE_HEALTH_FAILED'):
                live.validate_snapshot(snapshot, now_ns=NOW+2, now_monotonic_ns=MONO+2)

    def test_each_atomic_snapshot_is_host_readable_inside_private_session(self):
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory)
            session.chmod(0o700)
            reader = self.reader(directory)
            path = session/'live-health.json'
            for offset in (0, 1):
                with patch.object(worker.time, 'time_ns', return_value=NOW+offset), \
                        patch.object(worker.time, 'monotonic_ns', return_value=MONO+offset):
                    reader._write_live()
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o644)
                self.assertEqual(stat.S_IMODE(session.stat().st_mode), 0o700)
                self.assertEqual(json.loads(path.read_text())['written_ns'], NOW+offset)
                self.assertEqual(list(session.iterdir()), [path])
                # Replacement must reset file mode even if the old snapshot
                # came from the former root-owned 0600 writer.
                if offset == 0:
                    path.chmod(0o600)

    def test_frozen_stream_tick_persists_failure_instead_of_publishing_new_healthy_time(self):
        with tempfile.TemporaryDirectory() as directory:
            reader = self.reader(directory)
            with patch.object(worker.time, 'time_ns', return_value=NOW+2_100_000_000), \
                    patch.object(worker.time, 'monotonic_ns', return_value=MONO+2_100_000_000), \
                    patch.object(worker.time, 'monotonic', return_value=22.1):
                with self.assertRaisesRegex(ValueError, 'STALE'):
                    reader._live_tick()
            snapshot = json.loads((Path(directory)/'live-health.json').read_text())
            self.assertIsNotNone(snapshot['error'])
            with self.assertRaisesRegex(ValueError, 'LIVE_HEALTH_FAILED'):
                live.validate_snapshot(snapshot, now_ns=NOW+2_100_000_000,
                                       now_monotonic_ns=MONO+2_100_000_000)


if __name__ == '__main__':
    unittest.main()
