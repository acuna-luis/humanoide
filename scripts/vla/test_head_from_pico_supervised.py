"""Offline tests. Fake ROS only: these tests cannot publish robot commands."""
import json
import math
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'runtime'))
import head_from_pico_supervised as subject
from head_from_pico_readonly import BODY, ACTUATOR_IDS, HAND_SUFFIXES


def proof():
    return {'schema': 'cruzr_head_pico_preflight_v1', 'task_sha256': subject.TASK_SHA,
            'pico_sha256': subject.PICO_SHA, 'work_mode': 'joystick',
            'operator_confirmed': True, 'controller_status_writers_checked': True,
            'age_at_handoff_s': 1.0, 'session_id': 'a' * 32, 'mode': 'run'}


def sample():
    return {'name': list(BODY), 'position': list(BODY.values()),
            'velocity': [0.0] * len(BODY)}


class EnvelopeTests(unittest.TestCase):
    def test_session_and_stale_handoff(self):
        subject.validate_preflight(proof(), 10)
        with self.assertRaises(ValueError):
            subject.validate_preflight(proof(), 30)
        row = proof(); row['operator_confirmed'] = 1
        with self.assertRaises(ValueError):
            subject.validate_preflight(row, 0)
        row = proof(); row['mode'] = 'check'; row['operator_confirmed'] = False
        subject.validate_preflight(row, 0, dry_run=True)
        with self.assertRaises(ValueError):
            subject.validate_preflight(row, 0, dry_run=False)

    def test_locked_axes_and_declared_pico_limits(self):
        row = sample(); initial = dict(BODY)
        row['position'][row['name'].index('head_pitch_joint')] = -.43
        values = subject.motion_envelope(row, initial)
        self.assertTrue(subject.standstill(values, target=True))
        row['position'][row['name'].index('R_elbow_yaw_joint')] = -2.889
        with self.assertRaisesRegex(ValueError, 'outside_declared'):
            subject.motion_envelope(row, initial)
        row = sample(); row['position'][row['name'].index('R_elbow_yaw_joint')] += .003
        with self.assertRaisesRegex(ValueError, 'axis_drift'):
            subject.motion_envelope(row, initial)
        row = sample(); row['velocity'][row['name'].index('head_pitch_joint')] = .501
        with self.assertRaisesRegex(ValueError, 'head_pitch_speed_observation_threshold'):
            subject.motion_envelope(row, initial)

    def test_foreign_and_unknown_action_states(self):
        make = lambda ident, status: types.SimpleNamespace(
            status=status, goal_info=types.SimpleNamespace(
                goal_id=types.SimpleNamespace(uuid=list(ident))))
        own, foreign = b'a'*16, b'b'*16
        self.assertEqual(subject.foreign_active([make(own, 2)], own), [])
        self.assertEqual(subject.foreign_active([make(foreign, 2)], own), [foreign.hex()])
        with self.assertRaises(ValueError):
            subject.foreign_active([make(foreign, 0)], own)


class FakeRun:
    def __init__(self, scenario):
        self.scenario = scenario
        self.now = 0.0
        self.subs = {}
        self.sent = None
        self.goal_id = None
        self.send_count = 0
        self.cancel_count = 0
        self.cancel_uuid_count = 0
        self.cancelled = False
        self.emitted = []
        self.spins = 0
        self.spin_error_given = False
        self.future_error_given = False

    def action_status(self):
        if self.sent is None or self.now-self.sent < (6 if self.scenario == 'late' else 1):
            return []
        return [types.SimpleNamespace(status=5 if self.cancelled else 2,
                goal_info=types.SimpleNamespace(goal_id=types.SimpleNamespace(uuid=self.goal_id)))]

    def spin(self, node, timeout_sec=0):
        self.now += .1
        self.spins += 1
        if self.scenario == 'spin_error' and self.sent is not None and not self.spin_error_given:
            self.spin_error_given = True
            raise RuntimeError('fake executor spin failure')
        if self.scenario == 'broken' and self.sent is not None and self.now-self.sent > 8:
            raise KeyboardInterrupt('fake operator interrupt after broken transport')
        if self.spins > 1500:
            raise AssertionError('fake runner did not terminate')
        sec = 1000 + int(self.now)
        ns = int((self.now-int(self.now))*1_000_000_000)
        stamp = {'header': {'stamp': {'sec': sec, 'nanosec': ns}}}
        body = sample(); body.update(stamp)
        if self.scenario == 'success' and self.sent is not None:
            elapsed = max(0.0, self.now-self.sent)
            i = body['name'].index('head_pitch_joint')
            body['position'][i] = -.43 * min(1.0, elapsed / 2.0)
            body['velocity'][i] = -.215 if elapsed < 2.0 else 0.0
        actuators = dict(stamp, act_item=[{'id': n, 'status': 4663, 'error_code': 0}
                                           for n in ACTUATOR_IDS])
        def hand(side):
            return dict(stamp, name=[side+'_'+s for s in HAND_SUFFIXES],
                        position=[0.0]*7, velocity=[0.0]*7)
        messages = {'/mc/whole_joint_states': body, '/mc/actuator_state': actuators,
                    '/mc/left_hand/joint_states': hand('left'),
                    '/mc/right_hand/joint_states': hand('right'),
                    '/emb/estop_key_state': {'data': int(
                        self.scenario in ('estop_pending', 'estop_stays') and self.sent is not None
                        and self.now-self.sent >= 1 and (not self.cancelled or self.scenario == 'estop_stays'))},
                    '/emb/servo_estop_key_state': {'data': 0},
                    '/emb/chrg_input_status': {'data': 0},
                    '/emb/battery_state': {'batteries_states': [{'batsoc': 77}, {'batsoc': 79}]},
                    '/mc/manipulation/action/_action/status':
                        types.SimpleNamespace(status_list=self.action_status())}
        for name, callback in list(self.subs.items()):
            callback(messages[name])

    def install(self):
        run = self
        class Clock:
            def now(self):
                return types.SimpleNamespace(nanoseconds=1_000_000_000_000 + int(run.now*1e9))
        class CancelFuture:
            def done(self): return True
            def result(self): return types.SimpleNamespace(return_code=0)
        class CancelClient:
            def service_is_ready(self): return True
            def call_async(self, request):
                if bytes(request.goal_info.goal_id.uuid) != bytes(run.goal_id):
                    raise AssertionError('cancelled a different goal')
                run.cancel_uuid_count += 1; run.cancelled = True
                return CancelFuture()
        class Node:
            def get_topic_names_and_types(self):
                names = ('/mc/whole_joint_states', '/mc/actuator_state',
                         '/mc/left_hand/joint_states', '/mc/right_hand/joint_states',
                         '/emb/estop_key_state', '/emb/servo_estop_key_state',
                         '/emb/chrg_input_status', '/emb/battery_state')
                return [(n, ['fake/msg/Type']) for n in names]
            def create_subscription(self, typ, topic, callback, qos):
                run.subs[topic] = callback; return callback
            def count_publishers(self, topic): return 0
            def get_clock(self): return Clock()
            def create_client(self, typ, topic): return CancelClient()
            def destroy_node(self): pass
        class Goal:
            accepted = True
            def get_result_async(self):
                if run.scenario == 'result_error': raise RuntimeError('fake result error')
                class ResultFuture:
                    def done(self):
                        return run.cancelled or (run.scenario == 'success' and run.now-run.sent >= 2.2)
                    def result(self):
                        if run.scenario == 'success' and not run.cancelled:
                            return types.SimpleNamespace(status=4,
                                result=types.SimpleNamespace(state=types.SimpleNamespace(desc='SUCCEED')))
                        return types.SimpleNamespace(status=5,
                            result=types.SimpleNamespace(state=types.SimpleNamespace(desc='CANCELED')))
                return ResultFuture()
            def cancel_goal_async(self):
                run.cancel_count += 1; run.cancelled = True
                return CancelFuture()
        class GoalFuture:
            def done(self):
                if run.scenario == 'future_error' and not run.future_error_given:
                    run.future_error_given = True
                    raise RuntimeError('fake future exception')
                delay = 6 if run.scenario in ('late', 'estop_pending', 'estop_stays') else .2
                return run.now-run.sent >= delay
            def result(self): return Goal()
        class ActionClient:
            def __init__(self, node, typ, name): pass
            def server_is_ready(self): return True
            def send_goal_async(self, goal, goal_uuid):
                run.send_count += 1; run.sent = run.now; run.goal_id = goal_uuid.uuid
                if run.scenario == 'send_error':
                    raise RuntimeError('fake failure after send')
                return GoalFuture()
        class UUID:
            def __init__(self, uuid): self.uuid = uuid
        class CancelGoal:
            class Request:
                def __init__(self):
                    self.goal_info = types.SimpleNamespace(goal_id=types.SimpleNamespace(uuid=None))
        class ArmTask:
            class Goal: pass
        def module(name, **values):
            mod = types.ModuleType(name); mod.__dict__.update(values); return mod
        rclpy = module('rclpy', init=lambda: None, shutdown=lambda: None,
                       create_node=lambda *a, **kw: Node(), spin_once=run.spin)
        qos = module('rclpy.qos', QoSProfile=lambda **kw: None,
                     ReliabilityPolicy=types.SimpleNamespace(RELIABLE=1),
                     DurabilityPolicy=types.SimpleNamespace(TRANSIENT_LOCAL=1),
                     qos_profile_sensor_data=None)
        return {
            'rclpy': rclpy, 'rclpy.action': module('rclpy.action', ActionClient=ActionClient),
            'rclpy.qos': qos, 'rosidl_runtime_py': module('rosidl_runtime_py'),
            'rosidl_runtime_py.utilities': module('rosidl_runtime_py.utilities', get_message=lambda x: None),
            'rosidl_runtime_py.convert': module('rosidl_runtime_py.convert', message_to_ordereddict=lambda x: x),
            'unique_identifier_msgs': module('unique_identifier_msgs'),
            'unique_identifier_msgs.msg': module('unique_identifier_msgs.msg', UUID=UUID),
            'action_msgs': module('action_msgs'),
            'action_msgs.msg': module('action_msgs.msg', GoalStatusArray=object),
            'action_msgs.srv': module('action_msgs.srv', CancelGoal=CancelGoal),
            'mc_task_msgs': module('mc_task_msgs'),
            'mc_task_msgs.action': module('mc_task_msgs.action', ArmTask=ArmTask),
        }

    def execute(self, *, dry_run=False):
        def write(fd, data):
            if self.scenario == 'broken' and self.sent is not None:
                raise BrokenPipeError('fake observer link loss')
            self.emitted.append(json.loads(data)); return len(data)
        def read(fd, size):
            ready = next(x for x in reversed(self.emitted) if x['event'] == 'pre_dispatch_ready')
            value = {'schema': 'cruzr_head_pico_handoff_v1', 'session_id': 'a'*32,
                     'challenge': ready['challenge'], 'inventory_age_s': 3.0}
            return (json.dumps(value)+'\n').encode()
        with patch.dict(sys.modules, self.install()), \
             patch.object(subject.time, 'monotonic', side_effect=lambda: self.now), \
             patch.object(subject.os, 'set_blocking'), patch.object(subject.os, 'write', side_effect=write), \
             patch.object(subject.os, 'read', side_effect=read), \
             patch.object(subject.select, 'select', side_effect=lambda r, w, x, timeout: (r, [], [])):
            session = proof()
            if dry_run:
                session['mode'] = 'check'; session['operator_confirmed'] = False
            return subject.main(session, dry_run=dry_run)


class ActionRaceTests(unittest.TestCase):
    def test_full_dry_run_reaches_handoff_without_goal(self):
        run = FakeRun('success')
        self.assertEqual(run.execute(dry_run=True), 0)
        events = [x['event'] for x in run.emitted]
        self.assertIn('pre_dispatch_ready', events)
        self.assertIn('PICO_HEAD_SUPERVISED_DRY_RUN_PASSED', events)
        self.assertEqual(run.send_count, 0)
        self.assertNotIn('dispatch', events)

    def test_normal_success_moves_only_fake_head_and_waits_stable(self):
        run = FakeRun('success')
        self.assertEqual(run.execute(), 0)
        events = [x['event'] for x in run.emitted]
        self.assertEqual(run.send_count, 1)
        self.assertEqual(run.cancel_count + run.cancel_uuid_count, 0)
        self.assertEqual(events.count('action_result'), 1)
        self.assertIn('HEAD_SUCCEEDED_AND_STATIONARY', events)
        telemetry = [x for x in run.emitted if x['event'] == 'telemetry']
        self.assertTrue(any(x['velocity']['head_pitch_joint'] < 0 for x in telemetry))
        self.assertTrue(any(abs(x['position']['head_pitch_joint']+.43) < .001 for x in telemetry))

    def test_estop_during_pending_acceptance_alerts_then_cancels(self):
        run = FakeRun('estop_pending')
        self.assertEqual(run.execute(), 1)
        events = [x['event'] for x in run.emitted]
        self.assertEqual(run.send_count, 1)
        self.assertEqual(run.cancel_uuid_count, 1)
        self.assertLess(events.index('OPERATOR_ALERT'), events.index('cancel_uuid_requested'))
        self.assertIn('terminal_status_and_standstill_observed', events)

    def test_standstill_observed_without_releasing_estop(self):
        run = FakeRun('estop_stays')
        self.assertEqual(run.execute(), 1)
        self.assertEqual(run.send_count, 1)
        self.assertEqual(run.cancel_uuid_count, 1)
        self.assertIn('terminal_status_and_standstill_observed',
                      [x['event'] for x in run.emitted])

    def test_executor_spin_error_alerts_and_keeps_monitoring(self):
        run = FakeRun('spin_error')
        self.assertEqual(run.execute(), 1)
        self.assertEqual(run.send_count, 1)
        self.assertEqual(run.cancel_count, 1)
        events = [x['event'] for x in run.emitted]
        self.assertIn('OPERATOR_ALERT', events)
        self.assertIn('fault_and_standstill_observed', events)

    def test_unexpected_future_exception_enters_fallback_until_terminal(self):
        run = FakeRun('future_error')
        self.assertEqual(run.execute(), 1)
        self.assertEqual(run.send_count, 1)
        self.assertEqual(run.cancel_count, 1)
        events = [x['event'] for x in run.emitted]
        self.assertIn('UNRESOLVED', events)
        self.assertIn('terminal_status_and_standstill_observed', events)
        self.assertNotIn('HEAD_SUCCEEDED_AND_STATIONARY', events)

    def test_broken_output_still_cancels_and_does_not_declare_success(self):
        run = FakeRun('broken')
        self.assertEqual(run.execute(), 1)
        self.assertEqual(run.send_count, 1)
        self.assertEqual(run.cancel_count, 1)
        self.assertNotIn('HEAD_SUCCEEDED_AND_STATIONARY', [x['event'] for x in run.emitted])

    def test_send_exception_after_request_uses_uuid_no_retry(self):
        run = FakeRun('send_error')
        self.assertEqual(run.execute(), 1)
        events = [x['event'] for x in run.emitted]
        self.assertEqual(run.send_count, 1)
        self.assertEqual(run.cancel_uuid_count, 1)
        self.assertIn('OPERATOR_ALERT', events)
        self.assertIn('cancel_uuid_requested', events)
        self.assertIn('terminal_status_and_standstill_observed', events)
        self.assertNotIn('HEAD_SUCCEEDED_AND_STATIONARY', events)
        self.assertFalse(any(x.get('movement_commands') == 0 for x in run.emitted
                             if x['event'] == 'preflight_failed'))

    def test_late_acceptance_cancels_and_waits_for_standstill(self):
        run = FakeRun('late')
        self.assertEqual(run.execute(), 1)
        events = [x['event'] for x in run.emitted]
        self.assertEqual(run.send_count, 1)
        self.assertEqual(run.cancel_count, 1)
        self.assertLess(events.index('OPERATOR_ALERT'), events.index('acceptance'))
        self.assertLess(events.index('acceptance'), events.index('cancel_requested'))
        self.assertIn('fault_and_standstill_observed', events)

    def test_result_request_exception_keeps_observing_and_cancels(self):
        run = FakeRun('result_error')
        self.assertEqual(run.execute(), 1)
        events = [x['event'] for x in run.emitted]
        self.assertEqual(run.send_count, 1)
        self.assertEqual(run.cancel_count, 1)
        self.assertIn('OPERATOR_ALERT', events)
        self.assertIn('terminal_status_and_standstill_observed', events)
        self.assertNotIn('HEAD_SUCCEEDED_AND_STATIONARY', events)


if __name__ == '__main__':
    unittest.main()
