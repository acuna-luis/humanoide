"""Read-only resume odometry tests; no ROSA, robot or network access."""
import copy
import io
import json
import math
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from scripts.box_handling import scenario1_resume_worker as worker


START = 10_000_000_000
MS = 1_000_000


def odometry(stamp, *, x=0., yaw=0., linear=(0., 0., 0.), angular=(0., 0., 0.)):
    return {'header': {'stamp': {'sec': stamp//10**9, 'nanosec': stamp % 10**9}, 'frame_id': 'odom'},
            'child_frame_id': 'base_link',
            'pose': {'pose': {'position': dict(x=x, y=0., z=0.),
                             'orientation': dict(x=0., y=0., z=math.sin(yaw/2), w=math.cos(yaw/2))},
                     'covariance': [0.]*36},
            'twist': {'twist': {'linear': dict(zip('xyz', linear)), 'angular': dict(zip('xyz', angular))},
                      'covariance': [0.]*36}}


def warm():
    acquisition = worker.Acquisition(START)
    for offset in (100, 200):
        acquisition.add(odometry(START+offset*MS), START+(offset+1)*MS)
    return acquisition


class AcquisitionTests(unittest.TestCase):
    def test_success_requires_two_new_samples_and_one_publisher(self):
        acquisition = worker.Acquisition(START)
        self.assertIsNone(acquisition.complete(START+MS, 1))
        acquisition.add(odometry(START+100*MS), START+101*MS)
        self.assertIsNone(acquisition.complete(START+102*MS, 1))
        acquisition.add(odometry(START+200*MS), START+201*MS)
        self.assertIsNone(acquisition.complete(START+202*MS, 0))
        result = acquisition.complete(START+203*MS, 1)
        self.assertEqual(result['event'], 'resume_base_check')
        self.assertEqual(result['requested_ns'], START)
        self.assertEqual(result['completed_ns'], START+203*MS)
        self.assertEqual(result['frames'], {'frame_id': 'odom', 'child_frame_id': 'base_link'})
        self.assertTrue(result['stationary'])
        self.assertEqual(len(result['samples']), 2)
        self.assertEqual(result['publishers'], 1)

    def test_exact_duplicate_does_not_count_or_renew_receipt(self):
        acquisition = worker.Acquisition(START)
        first = odometry(START+100*MS)
        acquisition.add(first, START+101*MS)
        acquisition.add(copy.deepcopy(first), START+200*MS)
        self.assertEqual(len(acquisition.samples), 1)
        self.assertEqual(acquisition.samples[-1]['received_ns'], START+101*MS)
        self.assertIsNone(acquisition.complete(START+201*MS, 1))
        acquisition.add(odometry(START+300*MS), START+301*MS)
        result = acquisition.complete(START+302*MS, 1)
        self.assertEqual(result['duplicates_ignored'], 1)
        self.assertEqual([row['header']['stamp']['nanosec'] for row in result['samples']], [100*MS, 300*MS])

    def test_frozen_duplicate_stream_becomes_stale(self):
        acquisition = worker.Acquisition(START)
        message = odometry(START+100*MS)
        acquisition.add(message, START+101*MS)
        acquisition.add(message, START+500*MS)
        with self.assertRaisesRegex(ValueError, 'Stale'):
            acquisition.add(message, START+601*MS)
        with self.assertRaises(ValueError):
            acquisition.add(odometry(START+700*MS), START+701*MS)

    def test_same_stamp_changed_content_is_fatal(self):
        for field in ('position', 'frame', 'covariance'):
            acquisition = worker.Acquisition(START)
            message = odometry(START+100*MS)
            acquisition.add(message, START+101*MS)
            if field == 'position':
                message['pose']['pose']['position']['x'] = .001
            elif field == 'frame':
                message['header']['frame_id'] = 'other'
            else:
                message['pose']['covariance'][0] = 1.
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'Conflicting'):
                acquisition.add(message, START+102*MS)

    def test_regression_is_fatal_even_when_older_message_was_seen(self):
        acquisition = warm()
        with self.assertRaisesRegex(ValueError, 'Regressing'):
            acquisition.add(odometry(START+100*MS), START+300*MS)

    def test_pre_request_queue_is_ignored_only_before_first_new_sample(self):
        acquisition = worker.Acquisition(START)
        acquisition.add(odometry(START-10**9, linear=(.2, 0., 0.)), START+MS)
        acquisition.add(odometry(START), START+2*MS)
        self.assertEqual(len(acquisition.samples), 0)
        acquisition.add(odometry(START+100*MS), START+101*MS)
        with self.assertRaisesRegex(ValueError, 'newer'):
            acquisition.add(odometry(START), START+102*MS)

    def test_source_future_and_old_receipt_are_rejected(self):
        for stamp, receipt in ((START+100*MS, START+99*MS), (START+MS, START+502*MS)):
            with self.subTest(stamp=stamp), self.assertRaisesRegex(ValueError, 'Stale or future'):
                worker.Acquisition(START).add(odometry(stamp), receipt)

    def test_cached_samples_cannot_satisfy_later_complete(self):
        with self.assertRaisesRegex(ValueError, 'Stale'):
            warm().complete(START+701*MS, 1)

    def test_invalid_or_changed_frames_fail(self):
        for field in ('frame_id', 'child_frame_id'):
            acquisition = warm()
            message = odometry(START+300*MS)
            destination = message['header'] if field == 'frame_id' else message
            destination[field] = 'new_frame'
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'frame changed'):
                acquisition.add(message, START+301*MS)
            for value in ('', ' ', 123):
                destination[field] = value
                with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, 'nonempty'):
                    worker.Acquisition(START).add(message, START+301*MS)

    def test_all_velocity_components_and_vector_norm_are_checked(self):
        for kind, values in (('linear', (0., .004, 0.)), ('linear', (0., 0., .004)),
                             ('linear', (.0025, .0025, 0.)), ('angular', (.011, 0., 0.)),
                             ('angular', (0., .011, 0.)), ('angular', (0., 0., .011))):
            with self.subTest(kind=kind, values=values), self.assertRaisesRegex(ValueError, 'moving'):
                worker.Acquisition(START).add(odometry(START+MS, **{kind: values}), START+2*MS)

    def test_quaternion_and_nonfinite_payload_rejected(self):
        messages = [odometry(START+MS) for _ in range(4)]
        messages[0]['pose']['pose']['orientation']['w'] = 0.
        messages[1]['pose']['pose']['position']['x'] = float('nan')
        messages[2]['twist']['twist']['angular']['y'] = float('inf')
        messages[3]['pose']['covariance'][0] = float('nan')
        for message in messages:
            with self.subTest(message=repr(message)), self.assertRaises(ValueError):
                worker.Acquisition(START).add(message, START+2*MS)

    def test_stability_uses_relative_pose_and_wrapped_yaw(self):
        acquisition = worker.Acquisition(START)
        acquisition.add(odometry(START+100*MS, x=40., yaw=math.radians(179.6)), START+101*MS)
        acquisition.add(odometry(START+200*MS, x=40.005, yaw=math.radians(-179.4)), START+201*MS)
        self.assertTrue(acquisition.complete(START+202*MS, 1)['stationary'])
        for x, yaw in ((.0051, 0.), (0., math.radians(1.01))):
            acquisition = worker.Acquisition(START)
            acquisition.add(odometry(START+100*MS), START+101*MS)
            acquisition.add(odometry(START+200*MS, x=x, yaw=yaw), START+201*MS)
            with self.subTest(x=x, yaw=yaw), self.assertRaisesRegex(ValueError, 'not stable'):
                acquisition.complete(START+202*MS, 1)

    def test_multiple_or_invalid_publishers_cannot_pass(self):
        for publishers in (2, -1, True, '1'):
            with self.subTest(publishers=publishers), self.assertRaisesRegex(ValueError, 'one'):
                warm().complete(START+202*MS, publishers)

    def test_results_and_inputs_are_independent_copies(self):
        acquisition = warm()
        first = acquisition.complete(START+202*MS, 1)
        first['samples'][0]['pose']['pose']['position']['x'] = 999
        second = acquisition.complete(START+203*MS, 1)
        self.assertEqual(second['samples'][0]['pose']['pose']['position']['x'], 0.)

    def test_duplicate_json_keys_and_bad_stamp_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            worker.object_json('{"header":1,"header":2}')
        for field, value in (('sec', True), ('sec', -1), ('nanosec', 10**9), ('nanosec', .5)):
            message = odometry(START+MS)
            message['header']['stamp'][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                worker.Acquisition(START).add(message, START+2*MS)


class CollectionTests(unittest.TestCase):
    def reader(self, emit_samples=True, publishers=1):
        clock = NS(now=0.)
        native = NS(acquisition=None, publisher_count=lambda: publishers)
        def spin():
            clock.now += .125
            if emit_samples:
                stamp = START+round(clock.now*1e9)
                native.acquisition.add(odometry(stamp), stamp)
        native.spin = spin
        return native, clock

    def collect(self, native, clock, deadline=100.):
        with tempfile.TemporaryDirectory() as directory:
            lease = Path(directory)/'lease.json'
            lease.write_text(json.dumps({'deadline': deadline}))
            return worker.collect(native, lease, clock=lambda: clock.now,
                                  wall=lambda: START+round(clock.now*1e9))

    def test_two_samples_produce_result_and_collector_is_detached(self):
        native, clock = self.reader()
        result = self.collect(native, clock)
        self.assertTrue(result['stationary'])
        self.assertEqual(clock.now, .25)
        self.assertIsNone(native.acquisition)

    def test_missing_stream_or_publisher_times_out_at_five_seconds(self):
        for emit_samples, publishers in ((False, 1), (False, 0)):
            native, clock = self.reader(emit_samples, publishers)
            with self.subTest(publishers=publishers), self.assertRaisesRegex(TimeoutError, 'deadline'):
                self.collect(native, clock)
            self.assertEqual(clock.now, 5.)
            self.assertIsNone(native.acquisition)

    def test_lease_expiry_before_and_during_acquisition_blocks_success(self):
        for deadline in (0., .2):
            native, clock = self.reader()
            with self.subTest(deadline=deadline), self.assertRaisesRegex(RuntimeError, 'expired'):
                self.collect(native, clock, deadline)
            self.assertIsNone(native.acquisition)

    def test_multiple_publishers_fail_before_acquisition(self):
        native, clock = self.reader(publishers=2)
        with self.assertRaisesRegex(ValueError, 'one'):
            self.collect(native, clock)
        self.assertEqual(clock.now, 0.)

    def test_missing_and_malformed_lease_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'lease.json'
            with self.assertRaises(FileNotFoundError):
                worker.check_lease(path, 0.)
            for value in ({}, {'deadline': True}, {'deadline': float('nan')}):
                path.write_text(json.dumps(value))
                with self.subTest(value=value), self.assertRaises(ValueError):
                    worker.check_lease(path, 0.)

    def test_required_lease_argument_checked_before_native_import(self):
        with patch.object(worker, 'NativeReader', side_effect=AssertionError('No native import')), \
                patch('sys.stderr', io.StringIO()), self.assertRaises(SystemExit) as error:
            worker.main([])
        self.assertEqual(error.exception.code, 2)

    def test_expired_lease_main_emits_one_error_without_creating_reader(self):
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'lease.json'
            path.write_text('{"deadline":0}')
            with patch.object(worker, 'NativeReader', side_effect=AssertionError('No native import')), \
                    patch('sys.stdout', output):
                code = worker.main(['--lease-file', str(path)])
        self.assertEqual(code, 78)
        rows = output.getvalue().splitlines()
        self.assertEqual(len(rows), 1)
        self.assertEqual(json.loads(rows[0])['event'], 'error')


if __name__ == '__main__':
    unittest.main()
