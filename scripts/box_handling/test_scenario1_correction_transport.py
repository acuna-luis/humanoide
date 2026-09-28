#!/usr/bin/env python3
"""Correction transport fault injection; no native SDK, network or robot."""

import json
import queue
import sys
from types import SimpleNamespace as NS
from types import ModuleType
import unittest
from unittest.mock import Mock, patch

if __package__:
    from . import scenario1_action_client as action
else:
    import scenario1_action_client as action


NAV = {'command': 'navigation_start', 'arg_json': '{}'}
RESULT = {'state': {'desc': 'SUCCESS'}, 'dmsg': 'navigation_start SUCCEEDED'}


class Clock:
    def __init__(self):
        self.value = 0.

    def __call__(self):
        return self.value


class GuardTransport:
    """Preparation requires spinning even when the action server is ready."""
    def __init__(self, clock):
        self.clock = clock
        self.goal_id = None
        self.correction_guard = object()
        self.prepared_at = .5
        self.armed_at = None
        self.failed_at = None
        self.failure = None
        self.sent = []
        self.canceled = []
        self.events = []
        self.finished = []
        self.result_delay = .5
        self.cancel_status = 5
        self.settle_started = None
        self.settle_delay = .25
        self.on_spin = lambda: None

    def ready(self):
        return True

    def check_correction(self):
        if self.failed_at is not None and self.clock() >= self.failed_at:
            self.failure = 'Correction telemetry stale or outside envelope'
        if self.failure:
            raise ValueError(self.failure)

    def correction_ready(self):
        self.check_correction()
        return self.clock() >= self.prepared_at

    def arm_correction(self):
        if not self.correction_ready():
            raise ValueError('Not ready')
        self.armed_at = self.clock()

    def correction_snapshot(self):
        return {'armed': self.armed_at is not None, 'failure': self.failure}

    def begin_correction_settle(self):
        self.settle_started = self.clock()

    def correction_settled(self):
        return self.clock() >= self.settle_started + self.settle_delay

    def send(self, goal):
        if self.armed_at is None:
            raise AssertionError('Dispatch before fresh stationary telemetry')
        self.goal_id = 'correction-uuid'
        self.sent.append((self.clock(), goal))
        self.events.append({'event': 'accepted', 'goal_id': self.goal_id})
        return self.goal_id

    def spin(self):
        self.clock.value += .125
        self.on_spin()
        if (self.sent and self.result_delay is not None
                and self.clock() >= self.sent[0][0] + self.result_delay):
            self.events.append({'event': 'result', 'goal_id': self.goal_id,
                                'status': 4, 'result': RESULT})
            self.result_delay = None

    def drain(self):
        result, self.events = self.events, []
        return result

    def cancel(self):
        self.canceled.append(self.goal_id)
        if self.cancel_status is not None:
            self.events.append({'event': 'result', 'goal_id': self.goal_id,
                                'status': self.cancel_status, 'result': RESULT})

    def finish_successful_request(self):
        self.finished.append(self.goal_id)
        self.correction_guard = None
        self.goal_id = None


class CorrectionLifecycleTests(unittest.TestCase):
    def exercise(self, configure=lambda t: None, interrupted=lambda: None, timeout=10.):
        clock = Clock()
        transport = GuardTransport(clock)
        configure(transport)
        rows = []
        code = action.run_action(transport, 'navigation', NAV, timeout,
                                 lambda **row: rows.append(row), interrupted=interrupted,
                                 clock=clock, cancel_grace=.5)
        return code, transport, rows

    def test_ready_server_still_waits_and_arms_before_dispatch(self):
        code, transport, rows = self.exercise()
        self.assertEqual(code, 0)
        self.assertEqual(transport.sent[0][0], .5)
        self.assertEqual(transport.armed_at, .5)
        self.assertEqual(transport.canceled, [])
        guards = [r for r in rows if r['event'] == 'correction_guard']
        self.assertEqual([r['phase'] for r in guards[:2]], ['preparing', 'armed'])
        self.assertIsNone(guards[1]['goal_id'])
        self.assertEqual(guards[-1]['phase'], 'terminal')
        self.assertEqual(guards[-1]['goal_id'], 'correction-uuid')

    def test_no_telemetry_times_out_before_any_dispatch_or_cancel(self):
        code, transport, rows = self.exercise(lambda t: setattr(t, 'prepared_at', 100.))
        self.assertEqual(code, 2)
        self.assertEqual(transport.sent, [])
        self.assertEqual(transport.canceled, [])
        self.assertEqual(transport.clock(), 5.)
        self.assertTrue(any('stationary telemetry' in r.get('reason', '') for r in rows))

    def test_malformed_or_stale_preparation_never_dispatches(self):
        code, transport, _ = self.exercise(lambda t: setattr(t, 'failed_at', .25))
        self.assertEqual(code, 2)
        self.assertEqual(transport.sent, [])
        self.assertEqual(transport.canceled, [])

    def test_guard_failure_cancels_only_active_uuid_and_observes_terminal(self):
        def configure(transport):
            transport.failed_at = .75
            transport.result_delay = None
        code, transport, rows = self.exercise(configure)
        self.assertEqual(code, 2)
        self.assertEqual(transport.canceled, ['correction-uuid'])
        self.assertEqual(rows[-1]['event'], 'interrupted_terminal')
        self.assertFalse(rows[-1]['physical_stop_verified'])

    def test_late_success_after_guard_cancel_is_still_failure(self):
        def configure(transport):
            transport.failed_at = .75
            transport.result_delay = None
            transport.cancel_status = 4
        code, transport, rows = self.exercise(configure)
        self.assertEqual(code, 2)
        self.assertEqual(transport.canceled, ['correction-uuid'])
        self.assertEqual(rows[-1]['status'], 4)

    def test_guard_failure_and_success_same_spin_never_authorize_continuation(self):
        code, transport, rows = self.exercise(lambda t: setattr(t, 'failed_at', 1.))
        self.assertEqual(code, 2)
        self.assertEqual(transport.canceled, [])
        self.assertEqual(rows[-1]['event'], 'interrupted_terminal')

    def test_guard_fault_does_not_prevent_bounded_unknown_terminal_report(self):
        def configure(transport):
            transport.failed_at = .75
            transport.result_delay = None
            transport.cancel_status = None
        code, transport, rows = self.exercise(configure)
        self.assertEqual(code, 3)
        self.assertEqual(rows[-1]['event'], 'terminal_unknown')
        self.assertEqual(transport.clock(), 1.25)

    def test_signal_during_preparation_never_sends(self):
        holder = {}
        code, transport, _ = self.exercise(lambda t: holder.update(transport=t),
            interrupted=lambda: 'Signal 2' if holder['transport'].clock() >= .25 else None)
        self.assertEqual(code, 2)
        self.assertEqual(transport.sent, [])

    def test_motion_with_guard_is_rejected_even_if_configured_accidentally(self):
        clock = Clock()
        transport = GuardTransport(clock)
        rows = []
        code = action.run_action(transport, 'motion', {'task_name': 'x', 'yaml_args': '{}'},
                                 10., lambda **row: rows.append(row), clock=clock)
        self.assertEqual(code, 2)
        self.assertEqual(transport.sent, [])

    def test_success_waits_for_new_stationary_evidence(self):
        code, transport, rows = self.exercise()
        self.assertEqual(code, 0)
        self.assertEqual(transport.settle_started, 1.)
        self.assertEqual(transport.clock(), 1.25)
        self.assertEqual(transport.canceled, [])
        self.assertTrue(any(row.get('phase') == 'settled' for row in rows))

    def test_terminal_success_with_continued_motion_fails_without_second_cancel(self):
        code, transport, rows = self.exercise(lambda t: setattr(t, 'settle_delay', 20.))
        self.assertEqual(code, 2)
        self.assertEqual(transport.clock(), 2.5)
        self.assertEqual(transport.canceled, [])
        self.assertEqual(rows[-1]['event'], 'interrupted_terminal')
        self.assertFalse(any(row.get('phase') == 'settled' for row in rows))

    def test_settling_never_extends_action_deadline(self):
        code, transport, rows = self.exercise(lambda t: setattr(t, 'settle_delay', 20.), timeout=1.5)
        self.assertEqual(code, 2)
        self.assertEqual(transport.clock(), 1.5)
        self.assertEqual(transport.canceled, [])
        self.assertTrue(any('deadline' in row.get('reason', '') for row in rows))

    def test_interrupt_during_settling_never_returns_success(self):
        holder = {}
        code, transport, rows = self.exercise(lambda t: holder.update(transport=t),
            interrupted=lambda: 'Lost lease or signal' if holder['transport'].clock() >= 1.125 else None)
        self.assertEqual(code, 2)
        self.assertEqual(transport.canceled, [])
        self.assertFalse(any(row.get('phase') == 'settled' for row in rows))


class CorrectionAdapterTests(unittest.TestCase):
    def transport(self):
        value = action.RosaTransport.__new__(action.RosaTransport)
        value.kind = 'navigation'
        value.correction_guard = NS(add=lambda *args: None, check=lambda now: None,
                                    summary=lambda: {'ok': True})
        value.correction_failure = None
        value.correction_armed = True
        value.correction_readers = {}
        value.events = queue.Queue()
        value.client = NS(observed_goal_id='goal', retire_successful_goal=lambda: None)
        return value

    def test_callback_annotation_json_delivery_and_no_action_events(self):
        transport = self.transport()
        calls = []
        transport.correction_guard.add = lambda *args: calls.append(args)
        receive = transport.correction_callback('odom')
        self.assertIs(receive.__annotations__['raw'], str)
        with patch.object(action.time, 'time_ns', return_value=1234):
            receive('{"header":{"frame_id":"odom"}}')
        self.assertEqual(calls, [('odom', {'header': {'frame_id': 'odom'}}, 1234)])
        self.assertTrue(transport.events.empty())

    def test_malformed_callback_latches_error_without_throwing_through_spin(self):
        transport = self.transport()
        receive = transport.correction_callback('map')
        receive('{"x":1,"x":2}')
        self.assertIn('Duplicate JSON', transport.correction_failure)
        receive('{}')  # Fault must remain sticky.
        with self.assertRaisesRegex(RuntimeError, 'telemetry failed'):
            transport.check_correction()
        self.assertTrue(transport.events.empty())

    def test_success_clears_guard_and_idle_callbacks_do_not_poison_next_request(self):
        transport = self.transport()
        transport.finish_successful_request()
        self.assertIsNone(transport.correction_guard)
        self.assertFalse(transport.correction_armed)
        transport.correction_callback('map')('invalid json while inactive')
        self.assertIsNone(transport.correction_failure)

    def test_failed_guard_is_not_cleared_by_finish(self):
        transport = self.transport()
        transport.correction_failure = 'outside envelope'
        with self.assertRaises(RuntimeError):
            transport.finish_successful_request()
        self.assertIsNotNone(transport.correction_guard)

    def test_native_readers_use_reviewed_apis_and_reuse_without_old_guard_samples(self):
        transport = self.transport()
        transport.correction_guard = None
        transport.client.observed_goal_id = None
        calls, guards = [], []

        class QoS:
            def __init__(self):
                self.settings = []
            def bestEffort(self):
                self.settings.append('best_effort')
            def durabilityVolatile(self):
                self.settings.append('volatile')
            def keepLast(self, count):
                self.settings.append(('depth', count))

        def create_reader(message_type, topic, callback, qos):
            calls.append((message_type, topic, callback, qos.settings))
            return NS(getWriterCount=lambda: 2 if topic == '/nav/robot_pose' else 1)

        def new_guard(spec, requested_ns):
            received = []
            guard = NS(add=lambda *args: received.append(args), received=received,
                       check=lambda now: None, ready=lambda now: True,
                       arm=lambda now: None, summary=lambda: {'request': requested_ns})
            guards.append(guard)
            return guard

        transport.node = NS(create_reader=create_reader)
        qos_module, utils_module = ModuleType('rosa.base._QoS'), ModuleType('rosa.utils')
        qos_module.SensorDataQoS = QoS
        utils_module.resolve_message_type = lambda name: 'resolved:' + name
        modules = {'rosa': ModuleType('rosa'), 'rosa.base': ModuleType('rosa.base'),
                   'rosa.base._QoS': qos_module, 'rosa.utils': utils_module}
        with patch.dict('sys.modules', modules), patch.object(action, 'correction_module',
                return_value=NS(Guard=new_guard)), patch.object(action.time, 'time_ns', return_value=1000):
            transport.configure_correction({'first': True})
            self.assertTrue(transport.correction_ready())
            transport.arm_correction()
            calls[0][2]('{}')
            self.assertEqual(len(guards[0].received), 1)
            transport.finish_successful_request()
            calls[0][2]('{}')  # No active request: must not populate an old/new baseline.
            transport.configure_correction({'second': True})
            calls[1][2]('{}')
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(guards), 2)
        self.assertEqual(len(guards[0].received), 1)
        self.assertEqual(guards[1].received, [('odom', {}, 1000)])
        self.assertEqual([row[0] for row in calls],
                         ['resolved:geometry_msgs/msg/PoseStamped', 'resolved:nav_msgs/msg/Odometry'])
        self.assertTrue(all(row[3] == ['best_effort', 'volatile', ('depth', 5)] for row in calls))
        self.assertTrue(transport.events.empty())

    def test_new_correction_cannot_replace_an_active_or_failed_guard(self):
        transport = self.transport()
        with self.assertRaisesRegex(RuntimeError, 'idle navigation'):
            transport.configure_correction({})


class CorrectionProtocolTests(unittest.TestCase):
    def request(self, goal=NAV):
        return {'request_id': 'correction-1', 'goal': goal, 'timeout': 10,
                'correction': {'test': 'spec'}}

    def test_optional_field_validated_against_exact_goal_and_triple_preserved(self):
        calls = []
        module = NS(validate_spec=lambda spec, goal: calls.append((spec, goal)))
        with patch.object(action, 'correction_module', return_value=module):
            result = action.validate_session_request('navigation', json.dumps(self.request()), set())
        self.assertEqual(result, ('correction-1', NAV, 10))
        self.assertEqual(calls, [({'test': 'spec'}, NAV)])

    def test_correction_rejected_for_motion_and_nonmovement_navigation_queries(self):
        for kind, goal in [('motion', {'task_name': 'x', 'yaml_args': '{}'}),
                           ('navigation', {'command': 'check_state', 'arg_json': '{}'})]:
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'navigation_start'):
                action.validate_session_request(kind, json.dumps(self.request(goal)), set())

    def test_invalid_correction_rejected_before_configure_or_dispatch(self):
        def reject(spec, goal):
            raise ValueError('Correction target mismatch')
        source = NS(requests=queue.Queue(), reason=None, eof=False)
        source.requests.put(json.dumps(self.request()))
        transport = GuardTransport(Clock())
        rows = []
        with patch.object(action, 'correction_module', return_value=NS(validate_spec=reject)):
            code = action.run_session(transport, 'navigation', source, lambda **row: rows.append(row),
                                      clock=transport.clock)
        self.assertEqual(code, 2)
        self.assertEqual(transport.sent, [])
        self.assertEqual(rows[-1]['request_id'], 'correction-1')

    def test_session_configures_guard_and_correlates_evidence(self):
        source = NS(requests=queue.Queue(), reason=None, eof=False)
        source.requests.put(json.dumps(self.request()))
        transport = GuardTransport(Clock())
        configured = []
        transport.configure_correction = lambda spec: configured.append(spec)
        rows = []
        def emit(**row):
            rows.append(row)
            if row['event'] == 'request_complete':
                source.eof = True
                source.reason = 'EOF'
        with patch.object(action, 'correction_module', return_value=NS(
                validate_spec=lambda *a, **k: None,
                require_motion_qualified=action.correction_module().require_motion_qualified)):
            code = action.run_session(transport, 'navigation', source, emit, clock=transport.clock)
        self.assertEqual(code, 0)
        self.assertEqual(configured, [{'test': 'spec'}])
        guards = [row for row in rows if row['event'] == 'correction_guard']
        self.assertTrue(guards)
        self.assertTrue(all(row['request_id'] == 'correction-1' for row in guards))
        self.assertEqual(transport.finished, ['correction-uuid'])

    def test_guard_failure_poisons_session_and_queued_request_is_not_dispatched(self):
        source = NS(requests=queue.Queue(), reason=None, eof=False)
        source.requests.put(json.dumps(self.request()))
        second = self.request()
        second['request_id'] = 'correction-2'
        source.requests.put(json.dumps(second))
        transport = GuardTransport(Clock())
        transport.configure_correction = lambda spec: None
        transport.failed_at = .75
        transport.result_delay = None
        rows = []
        with patch.object(action, 'correction_module', return_value=NS(
                validate_spec=lambda *a, **k: None,
                require_motion_qualified=action.correction_module().require_motion_qualified)):
            code = action.run_session(transport, 'navigation', source, lambda **row: rows.append(row),
                                      clock=transport.clock)
        self.assertEqual(code, 2)
        self.assertEqual(len(transport.sent), 1)
        self.assertEqual(transport.canceled, ['correction-uuid'])
        self.assertEqual(transport.finished, [])
        self.assertEqual(source.requests.qsize(), 1)
        self.assertEqual(rows[-1]['request_id'], 'correction-1')


class RealGuardIntegrationTests(unittest.TestCase):
    def spec_and_goal(self):
        module = action.correction_module()
        target = {'point_x': .03, 'point_y': 0., 'point_yaw': 0.}
        reference = {'x': 0., 'y': 0., 'yaw': 0., 'stamp_ns': 9_000_000_000}
        spec = module.make_spec(target, reference, 1)
        goal = {'command': 'navigation_start', 'arg_json': json.dumps({'target_point': {
            'mode': 'free_nav', 'map_name': 'utars_nav_map', **target}})}
        return module, spec, goal

    def test_actual_spec_must_match_dispatched_coordinates(self):
        _, spec, goal = self.spec_and_goal()
        request = {'request_id': 'x', 'goal': goal, 'timeout': 15, 'correction': spec}
        self.assertEqual(action.validate_session_request('navigation', json.dumps(request), set())[1], goal)
        request['goal']['arg_json'] = goal['arg_json'].replace('0.03', '0.04')
        with self.assertRaisesRegex(ValueError, 'differs'):
            action.validate_session_request('navigation', json.dumps(request), set())

    def native_run(self, speed_after_send, result_delay, *, angular_after_send=0.,
                   close_after_send=False, quiet_after_result=False):
        module, spec, goal = self.spec_and_goal()
        clock = Clock()
        transport = GuardTransport(clock)
        transport.correction_guard = module.Guard(spec, requested_ns=10_000_000_000)
        transport.correction_failure = None
        transport.correction_armed = False
        transport.correction_readers = {key: NS(getWriterCount=lambda: 1) for key in ('map', 'odom')}
        transport.result_delay = result_delay
        for method in ('check_correction', 'correction_ready', 'correction_snapshot',
                       'begin_correction_settle', 'correction_settled'):
            setattr(transport, method, getattr(action.RosaTransport, method).__get__(transport))
        def arm():
            action.RosaTransport.arm_correction(transport)
            transport.armed_at = clock()
        transport.arm_correction = arm
        callbacks = {key: action.RosaTransport.correction_callback(transport, key) for key in ('map', 'odom')}
        now_ns = lambda: 10_000_000_000 + round(clock() * 1e9)
        def telemetry():
            stamp = now_ns()
            position = .03 if transport.sent and close_after_send else 0.
            pose = {'position': dict(x=position, y=0., z=0.), 'orientation': dict(x=0., y=0., z=0., w=1.)}
            header = {'stamp': {'sec': stamp // 10**9, 'nanosec': stamp % 10**9}, 'frame_id': 'map'}
            callbacks['map'](json.dumps({'header': header, 'pose': pose}))
            header = dict(header, frame_id='odom')
            linear = speed_after_send if transport.sent else 0.
            angular = (angular_after_send(clock() - transport.sent[0][0])
                       if callable(angular_after_send) else angular_after_send) if transport.sent else 0.
            if quiet_after_result and transport.correction_guard.summary()['settle_started_ns'] is not None:
                linear = angular = 0.
            callbacks['odom'](json.dumps({'header': header, 'child_frame_id': 'base_link',
                'pose': {'pose': pose}, 'twist': {'twist': {
                    'linear': dict(x=linear, y=0., z=0.),
                    'angular': dict(x=0., y=0., z=angular)}}}))
        transport.on_spin = telemetry
        rows = []
        with patch.object(action.time, 'time_ns', side_effect=now_ns):
            code = action.run_action(transport, 'navigation', goal, 15., lambda **row: rows.append(row),
                                     clock=clock, cancel_grace=.5)
        return code, transport, rows

    def test_real_velocity_violation_through_native_callback_cancels_and_collects_terminal(self):
        code, transport, rows = self.native_run(.11, None)
        self.assertEqual(code, 2)
        self.assertEqual(transport.sent[0][0], .25)
        self.assertEqual(transport.canceled, ['correction-uuid'])
        self.assertIn('velocity', transport.correction_failure)
        self.assertEqual(rows[-1]['event'], 'interrupted_terminal')

    def test_real_guard_requires_new_quiet_samples_after_success(self):
        code, transport, rows = self.native_run(0., .5)
        self.assertEqual(code, 0)
        self.assertEqual(transport.clock(), 1.)  # Result at .75; two samples at .875/1.
        self.assertEqual(transport.canceled, [])
        self.assertTrue(any(row.get('phase') == 'settled' for row in rows))

    def test_real_guard_rejects_motion_after_success_even_below_active_speed_limit(self):
        code, transport, rows = self.native_run(.005, .5)
        self.assertEqual(code, 2)
        self.assertLessEqual(transport.clock(), 2.25)
        self.assertEqual(transport.canceled, [])
        self.assertEqual(rows[-1]['event'], 'interrupted_terminal')
        self.assertFalse(any(row.get('phase') == 'settled' for row in rows))

    def test_authorized_approach_angular_speeds_pass_callbacks_then_require_rest(self):
        for speed in (.26143, .5, .6):
            with self.subTest(speed=speed):
                code, transport, rows = self.native_run(0., .5,
                    angular_after_send=speed, quiet_after_result=True)
                self.assertEqual(code, 0)
                self.assertEqual(transport.canceled, [])
                self.assertEqual(transport.correction_guard.summary()['max_angular_speed_rad_s'], speed)
                self.assertTrue(transport.correction_guard.summary()['settled'])
                self.assertTrue(any(row.get('phase') == 'settled' for row in rows))

    def test_angular_speed_above_approach_limit_cancels_before_target(self):
        for speed in (.600001, 1.2):
            with self.subTest(speed=speed):
                code, transport, rows = self.native_run(0., None, angular_after_send=speed)
                self.assertEqual(code, 2)
                self.assertEqual(transport.canceled, ['correction-uuid'])
                violation = transport.correction_guard.summary()['velocity_violation']
                self.assertEqual(violation['angular_limit_rad_s'], .6)
                self.assertEqual(violation['exceeded'], ['angular'])
                self.assertEqual(rows[-1]['event'], 'interrupted_terminal')

    def test_final_alignment_allows_1_2_only_after_two_close_map_samples(self):
        # First post-goal map sample is close; the preceding sample is still
        # 3 cm away. Higher speed becomes eligible on the second close sample.
        code, transport, rows = self.native_run(.02, .5,
            angular_after_send=lambda elapsed: .5 if elapsed < .25 else 1.2,
            close_after_send=True, quiet_after_result=True)
        self.assertEqual(code, 0)
        self.assertEqual(transport.canceled, [])
        self.assertEqual(transport.correction_guard.summary()['max_angular_speed_rad_s'], 1.2)
        self.assertTrue(transport.correction_guard.summary()['settled'])
        self.assertTrue(any(row.get('phase') == 'settled' for row in rows))
        code, transport, _ = self.native_run(0., None, angular_after_send=1.2, close_after_send=True)
        self.assertEqual(code, 2)
        self.assertEqual(transport.canceled, ['correction-uuid'])
        self.assertEqual(transport.correction_guard.summary()['velocity_violation']['angular_limit_rad_s'], .6)

    def test_alignment_limit_and_translation_condition_still_cancel_excess(self):
        for linear, angular, limit in ((0., 1.200001, 1.2), (.020001, 1.2, .6)):
            with self.subTest(linear=linear, angular=angular):
                code, transport, _ = self.native_run(linear, None,
                    angular_after_send=lambda elapsed: .5 if elapsed < .25 else angular,
                    close_after_send=True)
                self.assertEqual(code, 2)
                self.assertEqual(transport.canceled, ['correction-uuid'])
                self.assertEqual(transport.correction_guard.summary()['velocity_violation']['angular_limit_rad_s'], limit)

    def test_authorized_angular_motion_must_still_stop_after_terminal_success(self):
        code, transport, rows = self.native_run(0., .5, angular_after_send=.5)
        self.assertEqual(code, 2)
        self.assertEqual(transport.canceled, [])
        self.assertEqual(rows[-1]['event'], 'interrupted_terminal')
        self.assertFalse(any(row.get('phase') == 'settled' for row in rows))


class QualificationBlockTests(unittest.TestCase):
    def test_revoked_permission_prevents_readiness_arm_dispatch_and_cancel(self):
        clock = Clock()
        transport = GuardTransport(clock)
        for method in ('ready', 'correction_ready', 'arm_correction', 'send', 'spin', 'cancel'):
            setattr(transport, method, Mock(side_effect=AssertionError('Blocked correction called '+method)))
        rows = []
        report = dict(action.correction_module().qualification_report(), motion_enabled=False,
                      status='blocked', reason_code='GET1_CORRECTION_UNQUALIFIED', reason='synthetic revocation')
        with patch.object(action.correction_module(), 'qualification_report', return_value=report):
            code = action.run_action(transport, 'navigation', NAV, 15,
                                     lambda **row: rows.append(row), clock=clock)
        self.assertEqual(code, 2)
        self.assertTrue(any('GET1_CORRECTION_UNQUALIFIED' in row.get('reason', '') for row in rows))
        for method in ('ready', 'correction_ready', 'arm_correction', 'send', 'spin', 'cancel'):
            getattr(transport, method).assert_not_called()
        self.assertIsNone(transport.goal_id)
        self.assertEqual(clock(), 0.)
        self.assertFalse(any(row.get('phase') in ('armed', 'settling', 'settled', 'terminal') for row in rows))


class RemotePayloadTests(unittest.TestCase):
    def test_make_payload_embeds_guard_for_separate_native_process(self):
        from scripts.box_handling import scenario1_cli as cli
        payload = cli.make_payload('check', {}, {})
        namespace = {'__name__': 'scenario1_native_payload_test', '__package__': None}
        with patch.dict(sys.modules):
            # The native process cannot rely on the supervisor's package import.
            sys.modules.pop('scenario1_nav_correction', None)
            sys.modules.pop('scripts.box_handling.scenario1_nav_correction', None)
            exec(compile(payload['action_client'], '<native-action-payload>', 'exec'), namespace)
            module = namespace['correction_module']()
            self.assertIs(module, sys.modules['scenario1_nav_correction'])
            self.assertFalse(hasattr(module, '__file__'))  # It came from the payload, not the PC filesystem.
            target = dict(point_x=.03, point_y=0., point_yaw=0.)
            spec = module.make_spec(target, dict(x=0., y=0., yaw=0., stamp_ns=10**9), 1)
            goal = {'command': 'navigation_start', 'arg_json': json.dumps({'target_point': {
                'map_name': 'utars_nav_map', 'mode': 'free_nav', **target}})}
            request = {'request_id': 'remote-correction', 'goal': goal, 'timeout': 15, 'correction': spec}
            checked = namespace['validate_session_request']('navigation', json.dumps(request), set())
            self.assertEqual(checked, ('remote-correction', goal, 15))
            goal['arg_json'] = goal['arg_json'].replace('0.03', '0.04')
            with self.assertRaisesRegex(ValueError, 'differs'):
                namespace['validate_session_request']('navigation', json.dumps(request), set())


if __name__ == '__main__':
    unittest.main()
