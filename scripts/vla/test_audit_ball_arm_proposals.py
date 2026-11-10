"""Tests for the offline-only seven-axis proposal audit."""
import contextlib
import io
import unittest
from unittest.mock import patch
from pathlib import Path

import audit_ball_arm_proposals as arm


def rows():
    return [
        {'event': 'model_ready', 'model_sha256': arm.MODEL_SHA256,
         'physical_control_qualified': False, 'movement_commands': 0},
        {'event': 'prediction', 'index': 0, 'image_source_ns': 123,
         'image_sha256': 'a' * 64, 'physical_control_qualified': False,
         'prediction': [10., 20., 30., 40., 50., 60., 70., .8],
         'proposed_minus_observed_rad': [1., 2., 3., 4., 5., 6., 7.]},
        {'event': 'done', 'samples': 1, 'physical_control_qualified': False},
        {'event': 'summary', 'predictions': 1, 'observations_sent': 1,
         'observations_dropped': 0, 'movement_commands': 0},
    ]


class ArmAuditTest(unittest.TestCase):
    def test_mapping_uses_names_and_preserves_recorded_information(self):
        result = arm.audit(rows())
        joints = result['predictions'][0]['joints']
        self.assertEqual(joints['R_elbow_roll_joint']['model_index'], 3)
        self.assertEqual(joints['R_elbow_roll_joint']['historical_sdk_right_arm_index'], 0)
        self.assertEqual(joints['R_elbow_roll_joint']['model_value_rad'], 40.)
        self.assertEqual(joints['R_elbow_roll_joint']['derived_observed_rad'], 36.)
        self.assertEqual(joints['R_shoulder_pitch_joint']['historical_sdk_right_arm_index'], 2)
        self.assertEqual(result['largest_recorded_difference']['joint'], 'R_wrist_roll_joint')
        self.assertIs(result['physical_control_qualified'], False)
        self.assertEqual(result['movement_commands'], 0)

    def test_bad_data_is_rejected_without_partial_report(self):
        for change in ('nan', 'bad_index', 'qualified', 'wrong_model', 'incomplete', 'bad_counts'):
            data = rows()
            if change == 'nan': data[1]['prediction'][0] = float('nan')
            if change == 'bad_index': data[1]['index'] = 2
            if change == 'qualified': data[1]['physical_control_qualified'] = True
            if change == 'wrong_model': data[0]['model_sha256'] = '0' * 64
            if change == 'incomplete': data.pop()
            if change == 'bad_counts': data[2]['samples'] = 7
            with self.subTest(change=change), self.assertRaises(ValueError):
                arm.audit(data)

    def test_run_is_blocked_before_reading_files(self):
        with (patch.object(Path, 'open', side_effect=AssertionError('file read')),
              contextlib.redirect_stderr(io.StringIO())):
            self.assertEqual(arm.main(['--run']), 2)


if __name__ == '__main__':
    unittest.main()
