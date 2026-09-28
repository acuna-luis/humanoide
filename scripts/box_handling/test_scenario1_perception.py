"""Pure regression checks; never contact the robot or create files."""
import copy
import math
import unittest

from scripts.box_handling.scenario1_perception import guard_selection, stable_report, validate_pair


def selection(stamp=100, x=.78, y=.10, z=.62, angle_deg=0., index=0, axis='z'):
    orientation = dict(x=0., y=0., z=0., w=math.cos(math.radians(angle_deg) / 2))
    orientation[axis] = math.sin(math.radians(angle_deg) / 2)
    return dict(stamp_ns=stamp, camera_pose=dict(original_measurement=True),
                selection=dict(selected_index=index,
                               selected_pose=dict(position=dict(x=x, y=y, z=z),
                                                  orientation=orientation)))


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
