"""Local tests of the passive arm monitor; no ROS or robot access."""
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent / 'runtime'))
import arm_from_pico_supervised as arm
import check_arm_from_pico_supervised as runner
import test_head_from_pico_supervised as head_tests


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

    def test_remote_source_compiles_and_execution_stays_blocked(self):
        compile(runner.source_bundle(), '<remote-check>', 'exec')
        with self.assertRaisesRegex(RuntimeError, 'physical_dispatch_blocked'):
            arm.physical_release_gate()

    def test_trial_argument_controls_only_right_wrist(self):
        args = arm.build_trial_args(dict(arm.BODY))
        self.assertEqual(args['component_names'], ['right_arm'])
        self.assertEqual(args['goals'][0][-1], arm.ARM_STEP)
        self.assertEqual(args['goals'][0][:-1], [arm.BODY[n] for n in (
            'R_shoulder_pitch_joint', 'R_shoulder_roll_joint', 'R_shoulder_yaw_joint',
            'R_elbow_roll_joint', 'R_elbow_yaw_joint', 'R_wrist_pitch_joint')])
        with self.assertRaises(ValueError):
            arm.build_trial_args(dict(arm.BODY, R_wrist_roll_joint=math.inf))


class FakeArmRun(head_tests.FakeRun):
    def install(self):
        modules = super().install()
        original = modules['rclpy.action'].ActionClient
        fake = self
        class RecordingActionClient(original):
            def send_goal_async(self, goal, goal_uuid):
                fake.request = goal
                return super().send_goal_async(goal, goal_uuid)
        modules['rclpy.action'].ActionClient = RecordingActionClient
        return modules

    def spin(self, node, timeout_sec=0):
        topic = '/mc/whole_joint_states'
        if topic in self.subs and not hasattr(self, 'arm_callback_installed'):
            original = self.subs[topic]
            def arm_callback(message):
                message['position'][message['name'].index('head_pitch_joint')] = -.43
                message['velocity'][message['name'].index('head_pitch_joint')] = 0.0
                if self.scenario == 'success' and self.sent is not None:
                    elapsed = max(0.0, self.now - self.sent)
                    index = message['name'].index(arm.ARM_AXIS)
                    message['position'][index] = arm.ARM_STEP * min(1.0, elapsed / 2.0)
                    message['velocity'][index] = arm.ARM_STEP / 2 if elapsed < 2 else 0.0
                original(message)
            self.subs[topic] = arm_callback
            self.arm_callback_installed = True
        super().spin(node, timeout_sec)


class ArmActionTests(unittest.TestCase):
    def run_fake(self, scenario):
        fake = FakeArmRun(scenario)
        # Only test code replaces the hard physical gate; the live runner has
        # no option or input that grants this release.
        with patch.object(head_tests, 'subject', arm), patch.object(head_tests, 'sample', sample), \
             patch.object(arm, 'physical_release_gate'):
            result = fake.execute()
        return fake, result

    def test_success_requires_one_action_and_endpoint(self):
        fake, result = self.run_fake('success')
        self.assertEqual(result, 0)
        self.assertEqual(fake.send_count, 1)
        self.assertEqual(fake.request.task_name, 'move_components_json')
        import json
        self.assertEqual(json.loads(fake.request.yaml_args), arm.build_trial_args(dict(arm.BODY)))
        self.assertIn('ARM_SUCCEEDED_AND_STATIONARY', [row['event'] for row in fake.emitted])

    def test_stop_during_pending_acceptance_cancels_exact_goal(self):
        fake, result = self.run_fake('estop_pending')
        self.assertEqual(result, 1)
        self.assertEqual(fake.send_count, 1)
        self.assertEqual(fake.cancel_uuid_count, 1)
        events = [row['event'] for row in fake.emitted]
        self.assertLess(events.index('OPERATOR_ALERT'), events.index('cancel_uuid_requested'))


if __name__ == '__main__':
    unittest.main()
