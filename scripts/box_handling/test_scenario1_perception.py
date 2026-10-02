"""Offline perception regressions; only temporary files, no robot or network."""
import copy
from contextlib import contextmanager
import json
import math
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.box_handling import front_sps_contract as sps
from scripts.box_handling.scenario1_perception import (
    SelectionConsistencyError, guard_selection, observe_position_rejection, stable_report, validate_pair)
from scripts.box_handling.scenario1_runtime import guarded_adapter_source
from scripts.box_handling.test_front_sps import report


def selection(stamp=100, x=.78, y=.10, z=.62, angle_deg=0., index=0, axis='z'):
    orientation = dict(x=0., y=0., z=0., w=math.cos(math.radians(angle_deg) / 2))
    orientation[axis] = math.sin(math.radians(angle_deg) / 2)
    return dict(stamp_ns=stamp, camera_pose=dict(original_measurement=True),
                selection=dict(selected_index=index,
                               selected_pose=dict(position=dict(x=x, y=y, z=z),
                                                  orientation=orientation)))


class PositionRejectionObservationTest(unittest.TestCase):
    def test_success_retains_original_result_without_extra_diagnostic(self):
        result = object()
        validator = Mock(return_value=result)
        log = Mock()
        pose = dict(position=dict(x=.75, y=.1, z=.2))
        self.assertIs(observe_position_rejection(validator, pose, sps.POSITION_BOUNDS_M, log), result)
        validator.assert_called_once_with(pose)
        log.assert_not_called()

    def test_failure_preserves_same_exception_and_observes_all_axes_and_actual_bounds(self):
        error = ValueError('original gate failure')
        pose = dict(position=dict(x=.8173, y=.10, z=.20))
        bounds = copy.deepcopy(sps.POSITION_BOUNDS_M)
        before = copy.deepcopy((pose, bounds))
        log = Mock()
        with self.assertRaises(ValueError) as raised:
            observe_position_rejection(Mock(side_effect=error), pose, bounds, log)
        self.assertIs(raised.exception, error)
        detail = log.call_args.args[0]
        self.assertEqual(detail['event'], 'position_rejected')
        self.assertEqual(detail['frame_id'], 'base_link')
        self.assertEqual(detail['position'], pose['position'])
        self.assertEqual(detail['bounds_m'], bounds)
        self.assertEqual(detail['reason'], str(error))
        detail['position']['x'] = 0
        detail['bounds_m']['x'] = (0, 20)
        self.assertEqual((pose, bounds), before)

    def test_invalid_axis_is_null_without_discarding_other_axes_or_masking_rejection(self):
        for value in (math.nan, math.inf, True, None, '0.5', 10**400):
            pose = dict(position=dict(x=value, y=.1, z=.2))
            log = Mock()
            error = ValueError('invalid x')
            with self.subTest(value=value), self.assertRaises(ValueError) as raised:
                observe_position_rejection(Mock(side_effect=error), pose, sps.POSITION_BOUNDS_M, log)
            self.assertIs(raised.exception, error)
            detail = log.call_args.args[0]
            self.assertEqual(detail['position'], dict(x=None, y=.1, z=.2))
            json.dumps(detail, allow_nan=False)

    def test_log_failure_never_replaces_gate_rejection(self):
        error = ValueError('BOX_POSITION_REJECTED: original')
        for log_error in (OSError('disk unavailable'), ValueError('serialization failed')):
            with self.subTest(error=log_error), self.assertRaises(ValueError) as raised:
                observe_position_rejection(Mock(side_effect=error), dict(position={}), {},
                                           Mock(side_effect=log_error))
            self.assertIs(raised.exception, error)

    @contextmanager
    def transient_adapter(self, directory):
        source = Path(__file__).with_name('scenario1_perception.py').read_text()
        generated = guarded_adapter_source('/not-installed-for-test', directory, source)
        with patch.dict(sys.modules, {'front_sps_contract': sps}), \
                patch.object(sps, 'validate_position', sps.validate_position), \
                patch.object(sps, 'select_report', sps.select_report), \
                patch.object(sys, 'path', list(sys.path)), patch.object(sys, 'argv', list(sys.argv)), \
                patch.object(runpy, 'run_path'):
            namespace = {}
            exec(compile(generated, 'test-transient-adapter', 'exec'), namespace)
            yield namespace

    def test_generated_adapter_logs_first_rejection_and_transaction_still_latches(self):
        with tempfile.TemporaryDirectory() as directory, self.transient_adapter(directory) as namespace:
            capture = Mock(side_effect=AssertionError('No extra capture after rejection'))
            namespace['capture'] = capture
            transaction = sps.SelectionTransaction()
            captured = report()
            captured['vision_result']['trans_outputs']['box_pose']['poses'][1]['position']['x'] = .6173
            with self.assertRaisesRegex(ValueError, 'BOX_POSITION_REJECTED.*x=0.8173'):
                transaction.detect(captured, 100_100_000_000)
            capture.assert_not_called()
            self.assertTrue(transaction.failed)
            self.assertIsNone(transaction.pending)
            rows = (Path(directory)/'selection.jsonl').read_text().splitlines()
            self.assertEqual(len(rows), 1)
            detail = json.loads(rows[0])
            self.assertAlmostEqual(detail['position']['x'], .8173)
            self.assertEqual(set(detail['position']), set('xyz'))
            self.assertEqual(detail['bounds_m']['x'], [.41, .79])

    def test_rejection_of_second_capture_is_visible_without_returning_a_selection(self):
        with tempfile.TemporaryDirectory() as directory, self.transient_adapter(directory) as namespace:
            captured = report()
            captured['vision_result']['trans_outputs']['box_pose']['poses'][1]['position']['x'] = .6173
            capture = Mock(return_value=captured)
            with self.assertRaisesRegex(ValueError, 'BOX_POSITION_REJECTED'):
                stable_report(report(), 100_100_000_000, namespace['original'],
                              capture, lambda: 100_200_000_000)
            capture.assert_called_once()
            self.assertEqual(len((Path(directory)/'selection.jsonl').read_text().splitlines()), 1)

    def test_valid_selection_and_final_reply_still_preserve_camera_pose_without_extra_records(self):
        with tempfile.TemporaryDirectory() as directory, self.transient_adapter(directory) as namespace:
            captured = report()
            pending = namespace['original'](captured, 100_100_000_000)
            reply = sps.SelectionTransaction.result(pending)
            self.assertEqual(reply['sps_outputs']['poses'], [pending['camera_pose']])
            self.assertTrue(reply['ok'])
            self.assertFalse((Path(directory)/'selection.jsonl').exists())


class SelectionConsistencyTest(unittest.TestCase):
    def test_distinct_stamps_and_changed_indices_preserve_original_reference(self):
        previous = selection(index=4)
        current = selection(stamp=200, x=.79, index=1)
        original = copy.deepcopy((previous, current))
        result = validate_pair(previous, current)
        self.assertAlmostEqual(result['translation_m'], .01)
        self.assertEqual(result['reference'], current)
        self.assertIsNot(result['reference'], current)
        self.assertEqual((previous, current), original)
        self.assertFalse(result['reachability_checked'])
        result['reference']['camera_pose']['original_measurement'] = False
        self.assertTrue(current['camera_pose']['original_measurement'])

    def test_same_index_does_not_hide_a_different_position(self):
        with self.assertRaises(ValueError):
            validate_pair(selection(index=2), selection(stamp=200, x=.9, index=2))

    def test_repeated_old_invalid_and_missing_timestamps_rejected(self):
        for stamp in (100, 99, 0, -1, True, 200.0, '200', None):
            with self.subTest(stamp=stamp), self.assertRaises(ValueError):
                validate_pair(selection(), selection(stamp=stamp))
        current = selection(stamp=200); del current['stamp_ns']
        with self.assertRaises(ValueError):
            validate_pair(selection(), current)

    def test_translation_is_three_dimensional_and_does_not_average(self):
        current = selection(stamp=200, x=.79, y=.11, z=.63)
        result = validate_pair(selection(), current)
        self.assertAlmostEqual(result['translation_m'], math.sqrt(3) * .01)
        self.assertEqual(result['reference']['selection']['selected_pose'], current['selection']['selected_pose'])
        with self.assertRaises(ValueError):
            validate_pair(selection(), selection(stamp=200, x=.795, y=.115))

    def test_exact_thresholds_accepted_and_excesses_rejected(self):
        result = validate_pair(selection(), selection(stamp=200, x=.80, angle_deg=3.))
        self.assertAlmostEqual(result['rotation_deg'], 3.)
        for current in (selection(stamp=200, x=.800001), selection(stamp=200, angle_deg=3.000001)):
            with self.subTest(current=current), self.assertRaises(ValueError):
                validate_pair(selection(), current)

    def test_rejection_reports_measured_translation_and_full_rotation_without_returning_pose(self):
        for x, angle in ((.805, 1.), (.785, 5.5), (.805, 5.5)):
            with self.subTest(x=x, angle=angle), self.assertRaises(SelectionConsistencyError) as raised:
                validate_pair(selection(), selection(stamp=200, x=x, angle_deg=angle))
            measurement = raised.exception.measurement
            self.assertAlmostEqual(measurement['translation_m'], abs(x-.78))
            self.assertAlmostEqual(measurement['rotation_deg'], angle)
            self.assertEqual(measurement['max_translation_m'], .02)
            self.assertEqual(measurement['max_rotation_deg'], 3.)
            self.assertFalse(measurement['reachability_checked'])
            self.assertNotIn('reference', measurement)
            self.assertIn('translation=', str(raised.exception))
            self.assertIn('rotation=', str(raised.exception))

    def test_overflowing_distance_rejects_and_diagnostic_remains_json_serializable(self):
        with self.assertRaises(SelectionConsistencyError) as raised:
            validate_pair(selection(x=-1e308), selection(stamp=200, x=1e308))
        self.assertIsNone(raised.exception.measurement['translation_m'])
        json.dumps(raised.exception.measurement, allow_nan=False)

    def test_sign_flipped_quaternion_has_zero_rotation_difference(self):
        previous = selection(angle_deg=30.)
        current = selection(stamp=200, angle_deg=30.)
        orientation = current['selection']['selected_pose']['orientation']
        current['selection']['selected_pose']['orientation'] = {key: -value for key, value in orientation.items()}
        self.assertAlmostEqual(validate_pair(previous, current)['rotation_deg'], 0.)

    def test_full_rotation_detects_pitch_and_roll_changes(self):
        for axis in ('x', 'y', 'z'):
            with self.subTest(axis=axis):
                result = validate_pair(selection(), selection(stamp=200, angle_deg=2.5, axis=axis))
                self.assertAlmostEqual(result['rotation_deg'], 2.5)
                with self.assertRaises(ValueError):
                    validate_pair(selection(), selection(stamp=200, angle_deg=3.1, axis=axis))

    def test_wraparound_uses_shortest_rotational_angle(self):
        result = validate_pair(selection(angle_deg=179), selection(stamp=200, angle_deg=-179))
        self.assertAlmostEqual(result['rotation_deg'], 2.)

    def test_nonfinite_nonunit_and_malformed_poses_rejected(self):
        cases = [selection(stamp=200, x=float('nan')), selection(stamp=200, x=True),
                 selection(stamp=200, y=float('inf')), {}, {'stamp_ns': 200}]
        nonunit = selection(stamp=200)
        nonunit['selection']['selected_pose']['orientation']['w'] = .5
        cases.append(nonunit)
        for current in cases:
            with self.subTest(current=current), self.assertRaises(ValueError):
                validate_pair(selection(), current)

    def test_grasp_guard_uses_original_reference_and_leaves_pending_unchanged(self):
        result = validate_pair(selection(), selection(stamp=200))
        reference = result['reference']
        pending = selection(stamp=300, z=.63, index=5)
        original = copy.deepcopy(pending)
        report = guard_selection(pending, reference)
        self.assertEqual(report['previous_stamp_ns'], 200)
        self.assertEqual(report['stamp_ns'], 300)
        self.assertEqual(pending, original)
        self.assertNotIn('reference', report)
        for rejected in (selection(stamp=200), selection(stamp=300, z=.65)):
            with self.assertRaises(ValueError):
                guard_selection(rejected, reference)


class StableReportTest(unittest.TestCase):
    def test_capture_and_clock_order_with_unmodified_second_camera_pose(self):
        calls = []
        first_report = dict(name='first', full_evidence=dict(value=1))
        second_report = dict(name='second')
        first_pending = selection(stamp=100, index=3)
        second_pending = selection(stamp=200, x=.79, index=0)
        second_pending['camera_pose'] = dict(position=dict(x=-.015, y=.321, z=.765),
                                            orientation=dict(x=.01, y=.03, z=.02, w=.999))
        second_original = copy.deepcopy(second_pending)
        def original(report, now):
            calls.append(('select', report['name'], now))
            return first_pending if report is first_report else second_pending
        def capture():
            calls.append(('capture',))
            return second_report
        def clock():
            calls.append(('clock',))
            return 250
        result = stable_report(first_report, 150, original, capture, clock)
        self.assertEqual(calls, [('select', 'first', 150), ('capture',), ('clock',),
                                 ('select', 'second', 250)])
        self.assertEqual(result['camera_pose'], second_original['camera_pose'])
        self.assertEqual(result['selection'], second_original['selection'])
        self.assertEqual(second_pending, second_original)
        self.assertEqual(result['previous_detection'], first_report)
        self.assertIsNot(result['previous_detection'], first_report)
        self.assertAlmostEqual(result['stability']['translation_m'], .01)
        self.assertNotIn('reference', result['stability'])
        self.assertEqual(result['stamp_ns'], 200)

    def test_failed_first_contract_does_not_capture(self):
        def reject(_report, _now):
            raise ValueError('First contract rejected')
        def forbidden_capture():
            self.fail('Capture must not follow invalid first report')
        with self.assertRaisesRegex(ValueError, 'First contract'):
            stable_report({}, 150, reject, forbidden_capture, lambda: 250)

    def test_failed_second_contract_never_returns_selection(self):
        first_report = object()
        def original(report, _now):
            if report is first_report:
                return selection(stamp=100)
            raise ValueError('Second report stale')
        with self.assertRaisesRegex(ValueError, 'Second report stale'):
            stable_report(first_report, 150, original, lambda: {}, lambda: 250)

    def test_same_stamp_or_changed_box_never_returns_selection(self):
        for second_pending in (selection(stamp=100), selection(stamp=200, x=.9),
                               selection(stamp=200, angle_deg=4)):
            first_report = object()
            def original(report, _now):
                return selection(stamp=100) if report is first_report else second_pending
            with self.subTest(second_pending=second_pending), self.assertRaises(ValueError):
                stable_report(first_report, 150, original, lambda: {}, lambda: 250)

    def test_capture_deadline_failure_propagates_without_second_contract(self):
        calls = []
        def original(_report, _now):
            calls.append('contract')
            return selection(stamp=100)
        def timeout_capture():
            raise TimeoutError('Remaining native result deadline exceeded')
        with self.assertRaises(TimeoutError):
            stable_report({}, 150, original, timeout_capture, lambda: 250)
        self.assertEqual(calls, ['contract'])


if __name__ == '__main__':
    unittest.main()
