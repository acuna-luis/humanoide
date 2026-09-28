"""Offline regressions from sanitized camera/TF evidence; no robot access."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import Mock

from scripts.box_handling.front_sps_contract import SelectionTransaction, select_report
from scripts.box_handling.probe_front_box import transform_poses
from scripts.box_handling.scenario1_perception import stable_report
from scripts.box_handling.select_front_box import select_front_box


FIXTURE = Path(__file__).with_name('fixtures') / 'front_box_20260928.json'


def stamp_ns(report):
    stamp = report['vision_result']['trans_outputs']['box_pose']['header']['stamp']
    return stamp['sec'] * 1_000_000_000 + stamp['nanosec']


def detection(report):
    return {'frame_id': 'base_link', 'poses': transform_poses(
        report['vision_result']['trans_outputs']['box_pose']['poses'],
        report['tf_at_detection']['transform'])}


class IncidentSelectionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads(FIXTURE.read_text())['cases']

    def test_first_three_real_selections_preserve_original_camera_pose(self):
        self.assertEqual(len(self.cases), 4)
        for case in self.cases[:3]:
            with self.subTest(session=case['id']):
                report = copy.deepcopy(case['reports'][0])
                before = copy.deepcopy(report)
                expected = case['expected_selected_index']
                diagnostic = select_front_box(detection(report))
                self.assertEqual(diagnostic['selected_index'], expected)
                pending = select_report(report, case['selection_time_ns'])
                self.assertEqual(pending['selection']['selected_index'], expected)
                self.assertEqual(pending['camera_pose'],
                                 report['vision_result']['trans_outputs']['box_pose']['poses'][expected])
                self.assertIn('position_gate', pending['selection'])
                self.assertFalse(pending['selection']['reachability_checked'])
                self.assertFalse(pending['selection']['motion_authorized'])
                self.assertEqual(report, before)

    def test_last_two_real_captures_select_near_box_and_keep_diagnostic_scope(self):
        case = self.cases[-1]
        self.assertEqual(case['recorded_selected_index'], 5)
        self.assertEqual(case['expected_selected_index'], 4)
        self.assertEqual(len(case['reports']), 2)
        for report in case['reports']:
            with self.subTest(stamp=stamp_ns(report)):
                candidates = detection(report)
                near, far = candidates['poses'][4:6]
                # Both were in the same lateral band at almost the same height;
                # the rear box's smaller bearing must not make it the target.
                self.assertLess(abs(near['position']['y'] - far['position']['y']), .08)
                self.assertLess(abs(near['position']['z'] - far['position']['z']), .04)
                result = select_front_box(candidates)
                self.assertEqual(result['selected_index'], 4)
                self.assertEqual(result['selected_pose'], near)
                self.assertGreater(near['position']['x'], .79)
                self.assertLess(near['position']['x'], .8)
                self.assertGreater(far['position']['x'], 1.19)
                self.assertFalse(result['reachability_checked'])
                self.assertFalse(result['motion_authorized'])

    def test_last_two_captures_rejected_by_position_margin_before_delivery(self):
        for report in self.cases[-1]['reports']:
            with self.subTest(stamp=stamp_ns(report)):
                with self.assertRaisesRegex(ValueError, 'BOX_POSITION_REJECTED'):
                    select_report(report, stamp_ns(report) + 200_000_000)

    def test_far_box_alone_is_rejected_without_a_fallback(self):
        report = copy.deepcopy(self.cases[-1]['reports'][-1])
        poses = report['vision_result']['trans_outputs']['box_pose']['poses']
        poses[:] = [poses[5]]
        selected = select_front_box(detection(report))
        self.assertEqual(selected['selected_index'], 0)
        self.assertGreater(selected['selected_pose']['position']['x'], 1.19)
        with self.assertRaisesRegex(ValueError, 'BOX_POSITION_REJECTED'):
            select_report(report, stamp_ns(report) + 200_000_000)

    def test_rejected_detection_latches_transaction_and_cannot_be_selected(self):
        rejected = self.cases[-1]['reports'][0]
        transaction = SelectionTransaction()
        with self.assertRaisesRegex(ValueError, 'BOX_POSITION_REJECTED'):
            transaction.detect(rejected, stamp_ns(rejected) + 200_000_000)
        self.assertTrue(transaction.failed)
        self.assertIsNone(transaction.pending)
        with self.assertRaises(ValueError):
            transaction.select(stamp_ns(rejected) + 300_000_000)
        allowed = self.cases[0]['reports'][0]
        with self.assertRaises(ValueError):
            transaction.detect(allowed, self.cases[0]['selection_time_ns'])
        self.assertIsNone(transaction.pending)

    def test_stable_report_rejects_first_real_capture_without_another_capture(self):
        previous, current = self.cases[-1]['reports']
        capture = Mock(return_value=current)
        clock = Mock(return_value=stamp_ns(current) + 200_000_000)
        with self.assertRaisesRegex(ValueError, 'BOX_POSITION_REJECTED'):
            stable_report(previous, stamp_ns(previous) + 200_000_000,
                          select_report, capture, clock)
        capture.assert_not_called()
        clock.assert_not_called()

    def test_stable_report_does_not_deliver_a_rejected_second_capture(self):
        previous, current = copy.deepcopy(self.cases[-1]['reports'])
        # Explicitly synthetic first TF: move its near box 1 cm into the gate.
        # The second report is the untouched incident capture outside the gate.
        previous['tf_at_detection']['transform']['translation']['x'] -= .01
        first = select_report(previous, stamp_ns(previous) + 200_000_000)
        self.assertEqual(first['selection']['selected_index'], 4)
        capture = Mock(return_value=current)
        with self.assertRaisesRegex(ValueError, 'BOX_POSITION_REJECTED'):
            stable_report(previous, stamp_ns(previous) + 200_000_000,
                          select_report, capture, lambda: stamp_ns(current) + 200_000_000)
        capture.assert_called_once_with()

    def test_vertical_stack_in_real_success_keeps_its_top(self):
        report = self.cases[1]['reports'][0]
        selected = select_front_box(detection(report))
        self.assertEqual(selected['selected_index'], 0)
        self.assertEqual(selected['selected_stack_indices_bottom_to_top'], [3, 1, 0])

    def test_different_height_behind_front_box_remains_ambiguous(self):
        candidates = detection(self.cases[-1]['reports'][-1])
        candidates['poses'] = candidates['poses'][4:6]
        candidates['poses'][1]['position']['z'] += .1
        with self.assertRaisesRegex(ValueError, '[Aa]mbiguous'):
            select_front_box(candidates)


if __name__ == '__main__':
    unittest.main()
