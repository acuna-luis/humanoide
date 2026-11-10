"""Local tests of the passive arm monitor; no ROS or robot access."""
import math
import json
from pathlib import Path
import sys
import time
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent / 'runtime'))
import arm_from_pico_supervised as arm
import check_arm_from_pico_supervised as runner
import test_head_from_pico_supervised as head_tests
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'box_handling'))
import scenario1_action_client as box_client


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

    def test_codo_early_warning_before_sps_limit(self):
        initial = dict(arm.BODY, L_elbow_yaw_joint=2.8793, R_elbow_yaw_joint=-2.8787)
        row = sample()
        row['position'] = [initial[n] for n in row['name']]
        arm.motion_envelope(row, initial)
        row['position'][row['name'].index('L_elbow_yaw_joint')] = 2.8797
        with self.assertRaisesRegex(ValueError, 'approaching_nominal_sps_limit'):
            arm.motion_envelope(row, initial)
        row['position'][row['name'].index('L_elbow_yaw_joint')] = 2.8801
        with self.assertRaisesRegex(ValueError, 'outside_nominal_sps_limit'):
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

    def test_native_box_client_accepts_arm_goal_format(self):
        goal = {'task_name': arm.TASK, 'yaml_args': json.dumps(arm.build_trial_args(dict(arm.BODY)))}
        self.assertEqual(box_client.validate_goal('motion', json.dumps(goal)), goal)
        args = json.loads(goal['yaml_args'])
        self.assertEqual(args['component_names'], ['right_arm'])
        self.assertEqual(len(args['goals'][0]), 7)

    def test_native_box_terminal_success_contract(self):
        def result(status, code, desc):
            return types.SimpleNamespace(status=status,
                result=types.SimpleNamespace(state=types.SimpleNamespace(state=code, desc=desc)))
        for status, code, desc in ((4, 1101001, 'SUCCEED'), (4, 0, 'SUCCEED'),
                                   (5, 1101001, 'SUCCEED'), (4, 1101001, 'FAILED')):
            expected = box_client.result_succeeded('motion', status,
                         {'state': {'state': code, 'desc': desc}})
            self.assertEqual(arm.motion_result_ok(result(status, code, desc)), expected)

    def test_preflight_requires_sps_profile_and_exact_transmissions(self):
        names = 'walker-motion.manipulation_robot_app-1\nwalker-ros.ros2-1\nwalker-motion.hw-1\n'
        def execute(host, command):
            if command[:2] == ['docker', 'ps']:
                return {'returncode': 0, 'stdout': names}
            if command[-1] == 'HW_TYPE':
                return {'returncode': 0, 'stdout': 'cruzr_s2_v1_sps\n'}
            digest = runner.SPS_SHA if command[-1] == runner.SPS_TRANSMISSIONS else runner.ARM_TASK_SHA
            return {'returncode': 0, 'stdout': digest + '  path\n'}
        with patch.object(runner.head, 'preflight', return_value=('joystick', time.monotonic(), 'walker-ros.ros2-1')), \
             patch.object(runner, 'execute', side_effect=execute):
            self.assertEqual(runner.preflight()[0], 'joystick')
        def bad_profile(host, command):
            if command[-1] == 'HW_TYPE':
                return {'returncode': 0, 'stdout': 'cruzr_s2_v1\n'}
            return execute(host, command)
        with patch.object(runner.head, 'preflight', return_value=('joystick', time.monotonic(), 'walker-ros.ros2-1')), \
             patch.object(runner, 'execute', side_effect=bad_profile):
            with self.assertRaisesRegex(RuntimeError, 'sps_profile'):
                runner.preflight()


class FakeArmRun(head_tests.FakeRun):
    def install(self):
        modules = super().install()
        original = modules['rclpy.action'].ActionClient
        fake = self
        class RecordingActionClient(original):
            def send_goal_async(self, goal, goal_uuid):
                fake.request = goal
                future = super().send_goal_async(goal, goal_uuid)
                class FutureProxy:
                    def done(self): return future.done()
                    def result(self):
                        handle = future.result()
                        class HandleProxy:
                            accepted = handle.accepted
                            def cancel_goal_async(self): return handle.cancel_goal_async()
                            def get_result_async(self):
                                result_future = handle.get_result_async()
                                class ResultProxy:
                                    def done(self): return result_future.done()
                                    def result(self):
                                        response = result_future.result()
                                        response.result.state.state = 1101001 if response.status == 4 else 0
                                        return response
                                return ResultProxy()
                        return HandleProxy()
                return FutureProxy()
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
        self.assertEqual(json.loads(fake.request.yaml_args), arm.build_trial_args(dict(arm.BODY)))
        self.assertIn('ARM_SUCCEEDED_AND_STATIONARY', [row['event'] for row in fake.emitted])

    def test_stop_during_pending_acceptance_cancels_exact_goal(self):
        fake, result = self.run_fake('estop_pending')
        self.assertEqual(result, 1)
        self.assertEqual(fake.send_count, 1)
        self.assertEqual(fake.cancel_uuid_count, 1)
        events = [row['event'] for row in fake.emitted]
        self.assertLess(events.index('OPERATOR_ALERT'), events.index('cancel_uuid_requested'))


class ContinuousGuardTests(unittest.TestCase):
    def simulate_guard(self, scenario):
        fake = FakeArmRun('success')
        original_spin = fake.spin
        def spin(node, timeout_sec=0):
            original_spin(node, timeout_sec)
            if scenario == 'foreign' and any(x['event'] == 'goal_uuid_ready' for x in fake.emitted):
                status = types.SimpleNamespace(status=2, goal_info=types.SimpleNamespace(
                    goal_id=types.SimpleNamespace(uuid=list(b'z'*16))))
                fake.subs['/mc/manipulation/action/_action/status'](types.SimpleNamespace(status_list=[status]))
        fake.spin = spin
        read_count = 0
        def write(fd, data): fake.emitted.append(json.loads(data)); return len(data)
        def read(fd, size):
            nonlocal read_count
            read_count += 1
            if read_count == 1:
                ready = next(x for x in reversed(fake.emitted) if x['event'] == 'pre_dispatch_ready')
                return (json.dumps({'schema': 'cruzr_head_pico_handoff_v1', 'session_id': 'a'*32,
                                    'challenge': ready['challenge'], 'inventory_age_s': 3.0})+'\n').encode()
            guard = next(x for x in reversed(fake.emitted) if x['event'] == 'ARM_GUARD_READY')
            command = {'event': 'prepare_goal_uuid', 'session_id': 'a'*32,
                       'guard_id': guard['goal_uuid'], 'goal_id': '12345678-1234-1234-1234-123456789abc',
                       'challenge': 'c'*32}
            if read_count == 2 or scenario == 'duplicate':
                return (json.dumps(command)+'\n').encode()
            return (json.dumps({'event':'stop_guard', 'session_id':'a'*32})+'\n').encode()
        with patch.object(head_tests, 'subject', arm):
            session = head_tests.proof()
        session['mode'] = 'check'; session['operator_confirmed'] = False
        with patch.object(head_tests, 'sample', sample), patch.dict(sys.modules, fake.install()), \
             patch.object(arm.time, 'monotonic', side_effect=lambda: fake.now), \
             patch.object(arm.os, 'set_blocking'), patch.object(arm.os, 'write', side_effect=write), \
             patch.object(arm.os, 'read', side_effect=read), \
             patch.object(arm.select, 'select', side_effect=lambda r,w,x,timeout:(r,[],[])):
            if scenario == 'success':
                self.assertEqual(arm.main(session, dry_run=True, monitor_only=True), 0)
            elif scenario == 'duplicate':
                with self.assertRaisesRegex(ValueError, 'invalid_guard_uuid_handshake'):
                    arm.main(session, dry_run=True, monitor_only=True)
            else:
                with self.assertRaisesRegex(ValueError, 'foreign_action_active'):
                    arm.main(session, dry_run=True, monitor_only=True)
        self.assertEqual(fake.send_count, 0)
        return fake.emitted

    def test_guard_whitelists_one_uuid_then_stops_without_dispatch(self):
        events = self.simulate_guard('success')
        self.assertIn('goal_uuid_ready', [row['event'] for row in events])
        self.assertIn('ARM_GUARD_STOPPED', [row['event'] for row in events])

    def test_second_uuid_request_is_rejected(self):
        self.simulate_guard('duplicate')

    def test_foreign_action_remains_blocked_after_uuid_ack(self):
        self.simulate_guard('foreign')


if __name__ == '__main__':
    unittest.main()
