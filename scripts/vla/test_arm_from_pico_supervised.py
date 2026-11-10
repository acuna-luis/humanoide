"""Local tests of the passive arm monitor; no ROS or robot access."""
import math
import json
from pathlib import Path
import sys
import time
import types
import unittest
import uuid
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
    def test_wrist_guard_requires_matching_bootstrap_role_and_session(self):
        good = ('guard', 'a'*32, 'b'*64, 'c'*64)
        arm.require_verified_stream(good, 'guard', 'a'*32)
        for evidence in (None, ('worker', 'a'*32, 'b'*64, 'c'*64),
                         ('guard', 'd'*32, 'b'*64, 'c'*64),
                         ('guard', 'a'*32, 'bad', 'c'*64)):
            with self.assertRaisesRegex(RuntimeError, 'physical_dispatch_blocked'):
                arm.require_verified_stream(evidence, 'guard', 'a'*32)
        with self.assertRaisesRegex(RuntimeError, 'physical_dispatch_blocked'):
            arm.main({'session_id':'a'*32}, dry_run=False, verified_provenance=good)

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
    def test_heartbeat_scope_sequence_and_expiry(self):
        guard = arm.SupervisorHeartbeat('a'*32, 'b'*32)
        with self.assertRaisesRegex(ValueError, 'expired'):
            guard.require_fresh(1.0)
        row = {'event':'supervisor_heartbeat', 'session_id':'a'*32,
               'guard_id':'b'*32, 'sequence':0}
        guard.accept(row, 1.0)
        guard.require_fresh(1.1)
        with self.assertRaisesRegex(ValueError, 'invalid_supervisor'):
            guard.accept(row, 1.2)
        with self.assertRaisesRegex(ValueError, 'invalid_supervisor'):
            guard.accept(dict(row, session_id='c'*32, sequence=1), 1.2)
        guard.accept(dict(row, sequence=1), 1.2)
        with self.assertRaisesRegex(ValueError, 'expired'):
            guard.require_fresh(1.2 + arm.SUPERVISOR_HEARTBEAT_TIMEOUT_S + .01)

    def simulate_guard(self, scenario):
        fake = FakeArmRun('success')
        faults = ('guard_estop', 'guard_stale', 'guard_stdout', 'guard_eof', 'guard_badjson', 'guard_ros_error', 'cancel_unknown_then_active', 'cancel_repeated_active', 'supervisor_timeout', 'guard_stop_early')
        if scenario in ('cancel', 'cancel_disabled') + faults:
            fake.goal_id = list(uuid.UUID('12345678-1234-1234-1234-123456789abc').bytes)
        original_spin = fake.spin
        def spin(node, timeout_sec=0):
            if (scenario == 'guard_ros_error' and not getattr(fake, 'ros_error_given', False)
                    and any(x['event'] == 'goal_uuid_ready' for x in fake.emitted)):
                fake.ros_error_given = True
                raise OSError('simulated ROS failure')
            original_spin(node, timeout_sec)
            acknowledged = any(x['event'] == 'goal_uuid_ready' for x in fake.emitted)
            if acknowledged and scenario == 'guard_estop':
                fake.subs['/emb/estop_key_state']({'data': 1})
            if acknowledged and scenario == 'guard_stale' and not fake.cancelled:
                if not hasattr(fake, 'saved_body_callback'):
                    fake.saved_body_callback = fake.subs['/mc/whole_joint_states']
                    fake.subs['/mc/whole_joint_states'] = lambda message: None
            if fake.cancelled and hasattr(fake, 'saved_body_callback'):
                fake.subs['/mc/whole_joint_states'] = fake.saved_body_callback
            if fake.cancelled and scenario in faults + ('cancel',):
                # Simulate a goal delivered after the first cancellation:
                # it stays active across two retries before becoming terminal.
                value = 2 if scenario == 'cancel_repeated_active' and fake.cancel_uuid_count < 3 else 5
                status = types.SimpleNamespace(status=value, goal_info=types.SimpleNamespace(
                    goal_id=types.SimpleNamespace(uuid=fake.goal_id)))
                fake.subs['/mc/manipulation/action/_action/status'](types.SimpleNamespace(status_list=[status]))
            if (scenario == 'cancel_unknown_then_active' and fake.cancel_uuid_count == 1
                    and any(x['event'] == 'guard_cancel_response' for x in fake.emitted)):
                status = types.SimpleNamespace(status=2, goal_info=types.SimpleNamespace(
                    goal_id=types.SimpleNamespace(uuid=fake.goal_id)))
                fake.subs['/mc/manipulation/action/_action/status'](types.SimpleNamespace(status_list=[status]))
            if scenario == 'foreign' and any(x['event'] == 'goal_uuid_ready' for x in fake.emitted):
                status = types.SimpleNamespace(status=2, goal_info=types.SimpleNamespace(
                    goal_id=types.SimpleNamespace(uuid=list(b'z'*16))))
                fake.subs['/mc/manipulation/action/_action/status'](types.SimpleNamespace(status_list=[status]))
        fake.spin = spin
        read_count = 0
        def write(fd, data):
            if scenario == 'guard_stdout' and any(x['event'] == 'goal_uuid_ready' for x in fake.emitted):
                raise BlockingIOError('fake broken observer')
            fake.emitted.append(json.loads(data)); return len(data)
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
                if read_count == 2 and scenario in ('cancel',) + faults:
                    heartbeat = {'event':'supervisor_heartbeat', 'session_id':'a'*32,
                                 'guard_id':guard['goal_uuid'], 'sequence':0}
                    return (json.dumps(heartbeat)+'\n'+json.dumps(command)+'\n').encode()
                return (json.dumps(command)+'\n').encode()
            if read_count == 3 and scenario in ('guard_eof', 'cancel_unknown_then_active', 'cancel_repeated_active'): return b''
            if read_count == 3 and scenario == 'guard_badjson': return b'{bad json}\n'
            if read_count == 3 and scenario in ('cancel', 'cancel_disabled'):
                return (json.dumps({'event':'cancel_goal_uuid', 'session_id':'a'*32,
                        'goal_id':command['goal_id'], 'challenge':'e'*32})+'\n').encode()
            return (json.dumps({'event':'stop_guard', 'session_id':'a'*32})+'\n').encode()
        def select_input(r, w, x, timeout):
            if (scenario in ('guard_stale', 'guard_stdout', 'guard_estop', 'guard_ros_error', 'supervisor_timeout')
                    and any(e['event'] == 'goal_uuid_ready' for e in fake.emitted)):
                return ([], [], [])
            return (r, [], [])
        with patch.object(head_tests, 'subject', arm):
            session = head_tests.proof()
        session['mode'] = 'check'; session['operator_confirmed'] = False
        modules = fake.install()
        if scenario in ('cancel_service_missing', 'cancel_service_lost_before_ack', 'cancel_unknown_then_active'):
            create_node = modules['rclpy'].create_node
            def new_node(*args, **kwargs):
                node = create_node(*args, **kwargs)
                create_client = node.create_client
                def new_client(*args, **kwargs):
                    client = create_client(*args, **kwargs)
                    if scenario != 'cancel_unknown_then_active':
                        client.service_is_ready = lambda: (scenario != 'cancel_service_missing' and read_count < 2)
                    else:
                        call = client.call_async
                        def first_unknown(request):
                            if fake.cancel_uuid_count == 0:
                                self.assertEqual(bytes(request.goal_info.goal_id.uuid), bytes(fake.goal_id))
                                fake.cancel_uuid_count += 1
                                return types.SimpleNamespace(done=lambda: True,
                                    result=lambda: types.SimpleNamespace(return_code=2))
                            return call(request)
                        client.call_async = first_unknown
                    return client
                node.create_client = new_client
                return node
            modules['rclpy'].create_node = new_node
        with patch.object(head_tests, 'sample', sample), patch.dict(sys.modules, modules), \
             patch.object(arm, 'physical_release_gate'), \
             patch.object(arm.time, 'monotonic', side_effect=lambda: fake.now), \
             patch.object(arm.os, 'set_blocking'), patch.object(arm.os, 'write', side_effect=write), \
             patch.object(arm.os, 'read', side_effect=read), \
             patch.object(arm.select, 'select', side_effect=select_input):
            if scenario == 'cancel_service_missing':
                self.assertEqual(arm.main(session, dry_run=True, monitor_only=True, guard_can_cancel=True), 1)
                self.assertTrue(any(x.get('reason') == 'cancel_service_unavailable' for x in fake.emitted))
            elif scenario == 'cancel_service_lost_before_ack':
                with self.assertRaisesRegex(ValueError, 'cancel_service_unavailable'):
                    arm.main(session, dry_run=True, monitor_only=True, guard_can_cancel=True)
            elif scenario == 'success':
                self.assertEqual(arm.main(session, dry_run=True, monitor_only=True,
                                          guard_can_cancel=False), 0)
            elif scenario == 'cancel':
                self.assertEqual(arm.main(session, dry_run=True, monitor_only=True,
                                          guard_can_cancel=True), 1)
            elif scenario in faults:
                self.assertEqual(arm.main(session, dry_run=True, monitor_only=True,
                                          guard_can_cancel=True), 1)
                expected = 3 if scenario == 'cancel_repeated_active' else 2 if scenario == 'cancel_unknown_then_active' else 1
                self.assertEqual(fake.cancel_uuid_count, expected)
            elif scenario == 'cancel_disabled':
                with self.assertRaisesRegex(ValueError, 'invalid_guard_cancel_request'):
                    arm.main(session, dry_run=True, monitor_only=True)
            elif scenario == 'duplicate':
                with self.assertRaisesRegex(ValueError, 'invalid_guard_uuid_handshake'):
                    arm.main(session, dry_run=True, monitor_only=True)
            else:
                with self.assertRaisesRegex(ValueError, 'foreign_action_active'):
                    arm.main(session, dry_run=True, monitor_only=True)
        self.assertEqual(fake.send_count, 0)
        return fake.emitted

    def test_supervisor_timeout_cancels_exact_handshaken_uuid(self):
        events = self.simulate_guard('supervisor_timeout')
        alert = next(row for row in events if row['event'] == 'OPERATOR_ALERT')
        self.assertIn('supervisor_heartbeat_expired', alert['reason'])
        self.assertTrue(any(row['event'] == 'guard_auto_cancel_requested' for row in events))
        self.assertFalse(alert['physical_stop_confirmed'])

    def test_guard_refuses_stop_before_terminal_and_still(self):
        events = self.simulate_guard('guard_stop_early')
        alert = next(row for row in events if row['event'] == 'OPERATOR_ALERT')
        self.assertIn('guard_stop_without_terminal_and_still', alert['reason'])
        self.assertTrue(any(row['event'] == 'guard_auto_cancel_requested' for row in events))

    def test_guard_whitelists_one_uuid_then_stops_without_dispatch(self):
        events = self.simulate_guard('success')
        self.assertIn('goal_uuid_ready', [row['event'] for row in events])
        self.assertIn('ARM_GUARD_STOPPED', [row['event'] for row in events])

    def test_second_uuid_request_is_rejected(self):
        self.simulate_guard('duplicate')

    def test_foreign_action_remains_blocked_after_uuid_ack(self):
        self.simulate_guard('foreign')

    def test_guard_requests_exact_uuid_cancel_without_claiming_stop(self):
        events = self.simulate_guard('cancel')
        request = next(x for x in events if x['event'] == 'guard_cancel_requested')
        self.assertEqual(request['goal_id'], '12345678-1234-1234-1234-123456789abc')
        self.assertFalse(request['physical_stop_confirmed'])

    def test_missing_cancel_service_blocks_preflight(self):
        events = self.simulate_guard('cancel_service_missing')
        self.assertNotIn('ARM_GUARD_READY', [row['event'] for row in events])

    def test_cancel_service_lost_before_ack_blocks_uuid(self):
        events = self.simulate_guard('cancel_service_lost_before_ack')
        self.assertNotIn('goal_uuid_ready', [row['event'] for row in events])

    def test_passive_check_cannot_cancel(self):
        self.simulate_guard('cancel_disabled')

    def test_guard_faults_cancel_own_uuid_and_keep_observing(self):
        for scenario in ('guard_estop', 'guard_stale', 'guard_stdout', 'guard_eof', 'guard_badjson', 'guard_ros_error'):
            with self.subTest(scenario=scenario):
                self.simulate_guard(scenario)

    def test_unknown_cancel_followed_by_own_active_retries_once(self):
        events = self.simulate_guard('cancel_unknown_then_active')
        self.assertTrue(any(x.get('event') == 'guard_cancel_response' and x.get('return_code') == 2
                            for x in events))
        retry = [x for x in events if x.get('attempt') == 2]
        self.assertEqual(len(retry), 1)
        self.assertFalse(retry[0]['physical_stop_confirmed'])

    def test_delayed_active_goal_is_retried_until_terminal(self):
        events = self.simulate_guard('cancel_repeated_active')
        retries = [x for x in events if x.get('event') == 'guard_auto_cancel_requested'
                   and x.get('reason') == 'own_uuid_active_after_cancel']
        self.assertEqual([x['attempt'] for x in retries], [2, 3])
        self.assertGreaterEqual(retries[1]['monotonic'] - retries[0]['monotonic'], arm.GUARD_CANCEL_RETRY_S)
        self.assertTrue(any(x['event'] == 'guard_terminal_observed' and x['status'] == 5 for x in events))
        self.assertFalse(any(x.get('physical_stop_confirmed') is True for x in events))


if __name__ == '__main__':
    unittest.main()
