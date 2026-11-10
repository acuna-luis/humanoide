"""Local tests of the passive arm monitor; no ROS or robot access."""
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent / 'runtime'))
import arm_from_pico_supervised as arm
import check_arm_from_pico_supervised as runner


def sample():
    return {'name': list(arm.BODY), 'position': list(arm.BODY.values()),
            'velocity': [0.0] * len(arm.BODY)}


class ArmMonitorTests(unittest.TestCase):
    def test_lowered_head_and_pico_are_required(self):
        row = sample()
        self.assertEqual(arm.check_body(row)['head_pitch_joint'], -.43)
        row['position'][row['name'].index('head_pitch_joint')] = 0
        with self.assertRaisesRegex(ValueError, 'not_pico'):
            arm.check_body(row)

    def test_corridor_detects_other_axis_and_wrist_overshoot(self):
        initial = dict(arm.BODY)
        row = sample()
        row['position'][row['name'].index(arm.ARM_AXIS)] += arm.ARM_STEP
        arm.motion_envelope(row, initial)
        row['position'][row['name'].index(arm.ARM_AXIS)] += .004
        with self.assertRaisesRegex(ValueError, 'outside_trial_corridor'):
            arm.motion_envelope(row, initial)
        row = sample()
        row['position'][row['name'].index('L_elbow_roll_joint')] += .004
        with self.assertRaisesRegex(ValueError, 'non_trial_axis_drift'):
            arm.motion_envelope(row, initial)

    def test_nonfinite_values_and_run_are_rejected_before_ros(self):
        row = sample()
        row['velocity'][0] = math.nan
        with self.assertRaises(ValueError):
            arm.check_body(row)
        with self.assertRaisesRegex(RuntimeError, 'physical_dispatch_blocked'):
            arm.main({}, dry_run=False)
        with patch.object(runner, 'check', side_effect=AssertionError('must not connect')):
            self.assertEqual(runner.main(['--run']), 2)

    def test_remote_source_contains_no_goal_dispatch(self):
        source = (Path(__file__).resolve().parent / 'runtime/arm_from_pico_supervised.py').read_text()
        self.assertNotIn('send_goal_async(', source)
        compile(runner.source_bundle(), '<remote-check>', 'exec')


if __name__ == '__main__':
    unittest.main()
