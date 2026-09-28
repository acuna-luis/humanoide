"""Offline SPS position-gate regressions; no clients, processes or robot I/O."""
import copy
import math
import unittest
from unittest.mock import patch

from scripts.box_handling import front_sps_contract as contract
from scripts.box_handling.probe_front_box import transform_poses
from scripts.box_handling.select_front_box import select_front_box
from scripts.box_handling.test_front_sps import report


DETECT_NS = 100_100_000_000
SELECT_NS = 100_200_000_000
BOUNDS = {'x': (.41, .79), 'y': (-.39, .39), 'z': (.01, 1.49)}


def base_pose(**coordinates):
    position = dict(x=.75, y=.02, z=.4)
    position.update(coordinates)
    return dict(position=position, orientation=dict(x=0., y=0., z=0., w=1.))


def consistent_pending_at_x(pending, x):
    """Alter all cached representations; retain the earlier 'passed' marker."""
    index = pending['selection']['selected_index']
    captured = pending['detection']
    transform = captured['tf_at_detection']['transform']
    camera_pose = captured['vision_result']['trans_outputs']['box_pose']['poses'][index]
    camera_pose['position']['x'] = x - transform['translation']['x']
    pending['camera_pose'] = copy.deepcopy(camera_pose)
    pending['selection']['selected_pose'] = transform_poses([camera_pose], transform)[0]
    assert pending['selection']['position_gate']['passed'] is True
    return pending


class PositionEnvelopeTest(unittest.TestCase):
    def test_all_six_bounds_are_inclusive(self):
        for axis, bounds in BOUNDS.items():
            for value in bounds:
                with self.subTest(axis=axis, value=value):
                    pose = base_pose(**{axis: value})
                    before = copy.deepcopy(pose)
                    checked = contract.validate_position(pose)
                    self.assertTrue(checked['passed'])
                    self.assertEqual(pose, before)

    def test_next_float_outside_each_bound_is_rejected_without_epsilon(self):
        for axis, (low, high) in BOUNDS.items():
            for value in (math.nextafter(low, -math.inf), math.nextafter(high, math.inf)):
                with self.subTest(axis=axis, value=value):
                    with self.assertRaisesRegex(ValueError, 'BOX_POSITION_REJECTED.*'+axis):
                        contract.validate_position(base_pose(**{axis: value}))

    def test_nonfinite_boolean_and_nonnumeric_coordinates_are_rejected(self):
        for axis in BOUNDS:
            for value in (math.nan, math.inf, -math.inf, True, False, None, '.5'):
                with self.subTest(axis=axis, value=value):
                    with self.assertRaisesRegex(ValueError, 'BOX_POSITION_REJECTED: invalid'):
                        contract.validate_position(base_pose(**{axis: value}))

    def test_missing_coordinates_are_rejected(self):
        for axis in BOUNDS:
            pose = base_pose()
            del pose['position'][axis]
            with self.subTest(axis=axis), self.assertRaisesRegex(ValueError, 'BOX_POSITION_REJECTED'):
                contract.validate_position(pose)

    def test_metadata_reports_a_position_reserve_without_certifying_reach(self):
        checked = contract.validate_position(base_pose())
        self.assertEqual(checked['frame_id'], 'base_link')
        self.assertEqual(checked['bounds_m'], BOUNDS)
        self.assertEqual(checked['margin_m'], .01)
        self.assertEqual(checked['policy'], contract.POSITION_GATE_ID)
        self.assertIs(checked['reachability_checked'], False)
        checked['bounds_m']['x'] = (0., 10.)
        self.assertEqual(contract.validate_position(base_pose())['bounds_m'], BOUNDS)


class PositionGateTransactionTest(unittest.TestCase):
    def assert_failed_and_unusable(self, transaction):
        self.assertIs(transaction.failed, True)
        self.assertIsNone(transaction.pending)
        with self.assertRaises(ValueError):
            transaction.select(SELECT_NS)
        with self.assertRaises(ValueError):
            transaction.detect(report(), DETECT_NS)

    def test_both_replies_preserve_exact_original_camera_pose_and_timestamped_tf(self):
        captured = report()
        before = copy.deepcopy(captured)
        original = captured['vision_result']['trans_outputs']['box_pose']['poses'][1]
        transaction = contract.SelectionTransaction()
        detected = transaction.detect(captured, DETECT_NS)
        selected, pending = transaction.select(SELECT_NS)
        for result in (detected, selected):
            self.assertEqual(result, dict(ok=True, sps_outputs=dict(poses=[original], is_empty=False)))
        self.assertEqual(pending['camera_pose'], original)
        self.assertEqual(pending['detection'], before)
        self.assertEqual(pending['stamp_ns'], 100_000_000_000)
        self.assertEqual(pending['selection']['selected_pose']['position']['x'], .75)
        self.assertNotEqual(pending['selection']['selected_pose'], original)
        self.assertTrue(pending['selection']['position_gate']['passed'])
        self.assertFalse(pending['selection']['reachability_checked'])
        self.assertEqual(captured, before)

    def test_modifying_detection_reply_cannot_modify_the_pending_camera_pose(self):
        transaction = contract.SelectionTransaction()
        detected = transaction.detect(report(), DETECT_NS)
        original = copy.deepcopy(detected)
        detected['sps_outputs']['poses'][0]['position']['x'] = 50.
        selected, pending = transaction.select(SELECT_NS)
        self.assertEqual(selected, original)
        self.assertEqual(pending['camera_pose'], original['sps_outputs']['poses'][0])

    def test_detect_rejects_selected_out_of_bounds_box_and_latches_failure(self):
        captured = report()
        captured['vision_result']['trans_outputs']['box_pose']['poses'][1]['position']['x'] = 1.
        transaction = contract.SelectionTransaction()
        with self.assertRaisesRegex(ValueError, 'BOX_POSITION_REJECTED.*x=1.2000'):
            transaction.detect(captured, DETECT_NS)
        self.assert_failed_and_unusable(transaction)

    def test_unreachable_front_is_not_replaced_by_a_reachable_lateral_box(self):
        captured = report()
        captured['vision_result']['trans_outputs']['box_pose']['poses'] = [
            base_pose(x=1., y=.01, z=.4),  # After TF: X=1.2, Y=.01.
            base_pose(x=.5, y=.15, z=.7),  # After TF: X=.7, Y=.15.
        ]
        candidates = transform_poses(captured['vision_result']['trans_outputs']['box_pose']['poses'],
                                     captured['tf_at_detection']['transform'])
        self.assertEqual(select_front_box(dict(frame_id='base_link', poses=candidates))['selected_index'], 0)
        self.assertTrue(contract.validate_position(candidates[1])['passed'])
        transaction = contract.SelectionTransaction()
        with self.assertRaisesRegex(ValueError, 'BOX_POSITION_REJECTED.*no other box substituted'):
            transaction.detect(captured, DETECT_NS)
        self.assert_failed_and_unusable(transaction)

    def test_detect_response_rechecks_position_even_if_selection_claims_passed(self):
        pending = contract.select_report(report(), DETECT_NS)
        consistent_pending_at_x(pending, 1.2)
        transaction = contract.SelectionTransaction()
        with patch.object(contract, 'select_report', return_value=pending):
            with self.assertRaisesRegex(ValueError, 'BOX_POSITION_REJECTED.*x=1.2000'):
                transaction.detect(report(), DETECT_NS)
        self.assert_failed_and_unusable(transaction)

    def test_select_response_rechecks_consistently_altered_pending_despite_passed_flag(self):
        transaction = contract.SelectionTransaction()
        transaction.detect(report(), DETECT_NS)
        consistent_pending_at_x(transaction.pending, 1.2)
        with self.assertRaisesRegex(ValueError, 'BOX_POSITION_REJECTED.*x=1.2000'):
            transaction.select(SELECT_NS)
        self.assert_failed_and_unusable(transaction)

    def test_select_rejects_camera_pose_that_no_longer_matches_detection(self):
        transaction = contract.SelectionTransaction()
        transaction.detect(report(), DETECT_NS)
        transaction.pending['camera_pose']['position']['x'] += .01
        with self.assertRaisesRegex(ValueError, 'camera pose no longer matches'):
            transaction.select(SELECT_NS)
        self.assert_failed_and_unusable(transaction)

    def test_select_rejects_base_pose_that_no_longer_matches_exact_transform(self):
        transaction = contract.SelectionTransaction()
        transaction.detect(report(), DETECT_NS)
        transaction.pending['selection']['selected_pose']['position']['x'] += .01
        with self.assertRaisesRegex(ValueError, 'selected pose no longer matches exact-time TF'):
            transaction.select(SELECT_NS)
        self.assert_failed_and_unusable(transaction)

    def test_wrong_transform_frame_or_timestamp_cannot_reach_first_success(self):
        for part, key, value in (
                ('header', 'frame_id', 'map'), ('header', 'stamp', dict(sec=100, nanosec=1)),
                (None, 'child_frame_id', 'different_camera')):
            captured = report()
            transform = captured['tf_at_detection']
            (transform[part] if part else transform)[key] = value
            transaction = contract.SelectionTransaction()
            with self.subTest(part=part, key=key), self.assertRaisesRegex(ValueError, 'TF must match'):
                transaction.detect(captured, DETECT_NS)
            self.assert_failed_and_unusable(transaction)

    def test_x_and_z_bounds_pass_both_replies_without_clamping_camera_values(self):
        for x in BOUNDS['x']:
            for z in BOUNDS['z']:
                captured = report()
                captured['tf_at_detection']['transform']['translation']['x'] = 0.
                captured['vision_result']['trans_outputs']['box_pose']['poses'] = [base_pose(x=x, z=z)]
                before = copy.deepcopy(captured)
                transaction = contract.SelectionTransaction()
                with self.subTest(x=x, z=z):
                    detected = transaction.detect(captured, DETECT_NS)
                    selected, pending = transaction.select(SELECT_NS)
                    self.assertEqual(detected, selected)
                    self.assertEqual(selected['sps_outputs']['poses'],
                                     before['vision_result']['trans_outputs']['box_pose']['poses'])
                    self.assertEqual(pending['detection'], before)
                    self.assertEqual(captured, before)


if __name__ == '__main__':
    unittest.main()
