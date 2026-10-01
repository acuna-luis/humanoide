#!/usr/bin/env python3
"""Offline fault-injection tests; no ROSA import, network or robot access."""

import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

if __package__:
    from . import scenario1_action_client as action
else:
    import scenario1_action_client as action


GOAL_ID = '12345678-1234-1234-1234-123456789abc'
SUCCESS = {'state': {'desc': 'SUCCEED', 'state': 1101001}}


class FakeClock:
    def __init__(self):
        self.value = 0.

    def __call__(self):
        return self.value


class FakeTransport:
    def __init__(self, clock, schedule=(), cancel_schedule=()):
        self.clock = clock
        self.schedule = list(schedule)
        self.cancel_schedule = list(cancel_schedule)
        self.goal_id = None
        self.pending = []
        self.sent = 0
        self.canceled = []
        self.available = True

    def ready(self):
        return self.available

    def send(self, goal):
        self.sent += 1
        self.goal_id = GOAL_ID
        return self.goal_id

    def spin(self):
        self.clock.value += .25
        remaining = []
        for when, row in self.schedule:
            if self.clock() >= when:
                self.pending.append(dict(goal_id=GOAL_ID, **row))
            else:
                remaining.append((when, row))
        self.schedule = remaining

    def drain(self):
        rows, self.pending = self.pending, []
        return rows

    def cancel(self):
        self.canceled.append(self.goal_id)
        self.schedule.extend((self.clock() + delay, row) for delay, row in self.cancel_schedule)


ACCEPT = {'event': 'accepted', 'accepted': True}
RESULT = {'event': 'result', 'status': 4, 'result': SUCCESS}


class LifecycleTests(unittest.TestCase):
    def run_case(self, schedule=(), cancel_schedule=(), timeout=2., interrupt=lambda: None,
                 lease_file=None, available=True):
        clock = FakeClock()
        transport = FakeTransport(clock, schedule, cancel_schedule)
        transport.available = available
        rows = []
        code = action.run_action(transport, 'motion', {'task_name': 'example', 'yaml_args': '{}'},
                                 timeout, lambda **row: rows.append(row), interrupt,
                                 lease_file, clock, cancel_grace=1.)
        return code, rows, transport, clock

    def test_only_real_accepted_success_returns_zero(self):
        code, rows, transport, _ = self.run_case(((.25, ACCEPT), (.5, RESULT)))
        self.assertEqual(code, 0)
        self.assertEqual(transport.sent, 1)
        self.assertEqual(transport.canceled, [])
        self.assertEqual([r['event'] for r in rows], ['dispatched', 'accepted', 'result'])

    def test_rejection_never_retries_or_cancels(self):
        code, _, transport, _ = self.run_case(((.25, {'event': 'rejected', 'accepted': False}),))
        self.assertEqual(code, 2)
        self.assertEqual(transport.sent, 1)
        self.assertEqual(transport.canceled, [])

    def test_motion_status_four_is_not_enough(self):
        bad = dict(RESULT, result={'state': {'desc': 'FAILED', 'state': 1101001}})
        code, _, transport, _ = self.run_case(((.25, ACCEPT), (.5, bad)))
        self.assertEqual(code, 2)
        self.assertEqual(transport.canceled, [])

    def test_deadline_cancels_exact_goal_and_observes_terminal(self):
        canceled = {'event': 'result', 'status': 5, 'result': {}}
        code, rows, transport, clock = self.run_case(((.25, ACCEPT),), ((.25, canceled),))
        self.assertEqual(code, 2)
        self.assertEqual(transport.canceled, [GOAL_ID])
        self.assertEqual(rows[-1]['event'], 'interrupted_terminal')
        self.assertFalse(rows[-1]['physical_stop_verified'])
        self.assertLessEqual(clock(), 3.)

    def test_cancel_ack_without_terminal_stays_unknown(self):
        ack = {'event': 'cancel_response', 'response': {'return_code': 0}}
        code, rows, transport, clock = self.run_case(((.25, ACCEPT),), ((.25, ack),))
        self.assertEqual(code, 3)
        self.assertEqual(rows[-1]['event'], 'terminal_unknown')
        self.assertEqual(transport.sent, 1)
        self.assertEqual(clock(), 3.)

    def test_late_success_after_cancel_does_not_continue_cycle(self):
        code, rows, _, _ = self.run_case(((.25, ACCEPT),), ((.25, RESULT),))
        self.assertEqual(code, 2)
        self.assertEqual(rows[-1]['event'], 'interrupted_terminal')
        self.assertEqual(rows[-1]['status'], 4)

    def test_unknown_acceptance_still_targets_generated_uuid(self):
        code, rows, transport, _ = self.run_case(timeout=8.)
        self.assertEqual(code, 3)
        self.assertEqual(transport.sent, 1)
        self.assertEqual(transport.canceled, [GOAL_ID])
        self.assertTrue(any('Acceptance unknown' in r.get('reason', '') for r in rows))

    def test_late_acceptance_after_timeout_is_observed_until_terminal(self):
        canceled = {'event': 'result', 'status': 5, 'result': {}}
        code, rows, transport, _ = self.run_case(cancel_schedule=((.25, ACCEPT), (.5, canceled)))
        self.assertEqual(code, 2)
        self.assertEqual(transport.canceled, [GOAL_ID])
        self.assertEqual(rows[-1]['event'], 'interrupted_terminal')

    def test_interruption_before_dispatch_sends_nothing(self):
        code, _, transport, _ = self.run_case(interrupt=lambda: 'Signal 2')
        self.assertEqual(code, 2)
        self.assertEqual(transport.sent, 0)

    def test_interruption_after_dispatch_cancels(self):
        clock = FakeClock()
        transport = FakeTransport(clock, ((.25, ACCEPT),))
        rows = []
        code = action.run_action(transport, 'motion', {}, 5., lambda **r: rows.append(r),
                                 lambda: 'Signal 2' if clock() >= .5 else None,
                                 clock=clock, cancel_grace=1.)
        self.assertEqual(code, 3)
        self.assertEqual(transport.canceled, [GOAL_ID])

    def test_absent_server_has_no_dispatch_or_cancel(self):
        code, _, transport, _ = self.run_case(available=False)
        self.assertEqual(code, 2)
        self.assertEqual((transport.sent, transport.canceled), (0, []))

    def test_expired_lease_never_dispatches(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'lease.json'
            path.write_text('{"deadline":0}')
            code, _, transport, _ = self.run_case(lease_file=path)
        self.assertEqual(code, 2)
        self.assertEqual(transport.sent, 0)

    def test_lease_expiration_cancels_active_goal(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'lease.json'
            path.write_text('{"deadline":0.6}')
            code, rows, transport, _ = self.run_case(((.25, ACCEPT),), lease_file=path)
        self.assertEqual(code, 3)
        self.assertEqual(transport.canceled, [GOAL_ID])
        self.assertTrue(any('expired' in r.get('reason', '') for r in rows))

    def test_nonterminal_get_result_is_never_success(self):
        row = {'event': 'result_pending', 'status': 2, 'result': SUCCESS}
        code, _, transport, _ = self.run_case(((.25, ACCEPT), (.5, row)))
        self.assertEqual(code, 3)
        self.assertEqual(transport.canceled, [GOAL_ID])

    def test_cancel_response_error_still_waits_for_terminal(self):
        bad_ack = {'event': 'error', 'reason': 'Malformed cancel response'}
        canceled = {'event': 'result', 'status': 5, 'result': {}}
        code, rows, _, _ = self.run_case(((.25, ACCEPT),), ((.25, bad_ack), (.5, canceled)))
        self.assertEqual(code, 2)
        self.assertEqual(rows[-1]['event'], 'interrupted_terminal')

    def test_callback_error_does_not_discard_terminal_in_same_batch(self):
        bad_feedback = {'event': 'error', 'reason': 'Malformed feedback'}
        code, rows, transport, _ = self.run_case(((.25, ACCEPT), (.5, bad_feedback), (.5, RESULT)))
        self.assertEqual(code, 2)
        self.assertEqual(transport.canceled, [])
        self.assertEqual(rows[-1]['event'], 'interrupted_terminal')


class JsonHelper:
    @staticmethod
    def msg_to_json(message):
        return json.dumps(message)


MESSAGE_TYPE = NS(getTypeHelper=lambda: JsonHelper())


class FakePort:
    def __init__(self, response):
        self.response = response
        self.requests = []

    def get_result(self, future):
        return self.response

    def call_async(self, request, callback):
        self.requests.append(request)
        self.callback = callback
        return 'future'


class NativeAdapterTests(unittest.TestCase):
    def build(self):
        cls = action.native_client_class(object, str)
        client = cls()
        rows = []
        client.configure_observer(lambda event, **data: rows.append(dict(event=event, **data)))
        client.observed_goal_id = GOAL_ID
        client.SendGoalService = NS(Response=MESSAGE_TYPE)
        client.CancelResponse = MESSAGE_TYPE
        client.Result = MESSAGE_TYPE
        client._goal_futures = {GOAL_ID: 'future'}
        client._result_futures = {GOAL_ID: 'future'}
        client._goal_handles = {GOAL_ID: NS(get_goal_uuid=lambda: GOAL_ID)}
        return client, rows

    def test_acceptance_uses_service_flag_not_default_handle_status(self):
        client, rows = self.build()
        client._goal_client = FakePort({'accepted': False})
        client.handle_goal_response_async(NS(goal_id=NS(uuid=GOAL_ID)))
        self.assertFalse(client.accepted)
        self.assertEqual(rows, [{'event': 'rejected', 'goal_id': GOAL_ID, 'accepted': False}])

    def test_non_boolean_acceptance_is_error(self):
        client, rows = self.build()
        client._goal_client = FakePort({'accepted': 1})
        client.handle_goal_response_async(NS(goal_id=NS(uuid=GOAL_ID)))
        self.assertFalse(client.accepted)
        self.assertEqual(rows[-1]['event'], 'error')

    def test_cancel_copies_exact_uuid_and_preserves_handle(self):
        client, rows = self.build()
        client.CancelRequest = lambda: NS(goal_info=NS(goal_id=NS(uuid=None)))
        client._cancel_client = FakePort({'return_code': 0, 'goals_canceling': []})
        client.cancel_own_goal()
        self.assertEqual(client._cancel_client.requests[0].goal_info.goal_id.uuid, GOAL_ID)
        self.assertEqual(client._goal_handles[GOAL_ID].get_goal_uuid(), GOAL_ID)
        client._cancel_client.callback()
        self.assertEqual(rows[-1]['event'], 'cancel_response')
        self.assertFalse(rows[-1]['physical_stop_verified'])

    def test_native_executing_response_does_not_mark_terminal(self):
        client, rows = self.build()
        client._result_client = FakePort(NS(status=2, result=SUCCESS))
        client.result_pending = True
        client.handel_result_async(NS(goal_id=NS(uuid=GOAL_ID)))
        self.assertFalse(client.terminal)
        self.assertFalse(client.result_pending)
        self.assertEqual(rows[-1]['event'], 'result_pending')

    def test_unrelated_result_is_not_accepted(self):
        client, rows = self.build()
        client._result_client = FakePort(NS(status=4, result=SUCCESS))
        client.handel_result_async(NS(goal_id=NS(uuid='another-goal')))
        self.assertFalse(client.terminal)
        self.assertEqual(rows[-1]['event'], 'error')


class InputTests(unittest.TestCase):
    def test_invalid_json_and_nonfinite_lease_rejected(self):
        for raw in ('[]', '{"a":1,"a":2}', '{"a":NaN}', '{"a":1e999}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                action.object_json(raw)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'lease.json'
            for raw in ('{"deadline":true}', '{"deadline":"200"}', '{}'):
                path.write_text(raw)
                with self.subTest(raw=raw), self.assertRaises(RuntimeError):
                    action.check_lease(path, 0)

    def test_goal_requires_exact_typed_fields_and_json_arguments(self):
        for raw in ('{"task_name":"home"}', '{"task_name":"home","yaml_args":"[]"}',
                    '{"task_name":"home","yaml_args":"{}","extra":true}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                action.validate_goal('motion', raw)

    def test_navigation_application_result_left_to_caller(self):
        self.assertTrue(action.result_succeeded('navigation', 4, {'result_json': '{}'}))
        self.assertFalse(action.result_succeeded('navigation', 6, {'result_json': '{}'}))


class CompatibilityTests(unittest.TestCase):
    def test_native_source_pin_ignores_comments_but_not_behavior(self):
        source = 'class Example:\n    def send(self, x):\n        return x\n'
        cosmetic = 'class Example:  # comment\n\n    def send( self, x ):\n        return x\n'
        changed = 'class Example:\n    def send(self, x):\n        return None\n'
        fingerprint = action.class_fingerprint(source, 'Example')
        self.assertEqual(fingerprint, action.class_fingerprint(cosmetic, 'Example'))
        observed = action.validate_native_sources({'Example': object()}, {'Example': fingerprint},
                                                   source_reader=lambda _: cosmetic)
        self.assertEqual(observed, {'Example': fingerprint})
        with self.assertRaisesRegex(RuntimeError, 'NATIVE_API_UNREVIEWED'):
            action.validate_native_sources({'Example': object()}, {'Example': fingerprint},
                                           source_reader=lambda _: changed)

    def test_uninspectable_native_source_fails_before_initialization(self):
        def missing(_):
            raise OSError('No source file')
        with self.assertRaisesRegex(RuntimeError, 'cannot inspect'):
            action.validate_native_sources({'ActionClient': object()}, source_reader=missing)

    def test_missing_native_binding_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'NATIVE_API_UNSUPPORTED'):
            action.require_callables(NS(init=lambda: None, spin_once=None), ('init', 'spin_once'), 'rosa')

    def test_generated_native_messages_and_cancel_layout_required(self):
        helper = NS(msg_from_json=lambda value: value, msg_to_json=json.dumps)
        message = NS(getTypeHelper=lambda: helper)
        port = NS(call_async=lambda *args: None, get_result=lambda *args: None,
                  getServiceCount=lambda: 1)
        client = NS(send_goal_async=lambda *args: None, send_result_request_async=lambda *args: None,
                    is_action_server_ready=lambda: True, _goal_client=port, _result_client=port,
                    _cancel_client=port, _feedback_reader=NS(getWriterCount=lambda: 1),
                    _status_reader=NS(getWriterCount=lambda: 1), Goal=message, Result=message,
                    Feedback=message, CancelResponse=message, SendGoalService=NS(Response=message),
                    CancelRequest=lambda: NS(goal_info=NS(goal_id=NS(uuid=GOAL_ID))),
                    _goal_handles={}, _goal_futures={})
        action.validate_native_client(client)
        client.CancelRequest = lambda: NS(goal_id=GOAL_ID)
        with self.assertRaisesRegex(RuntimeError, 'cancel request/goal storage layout'):
            action.validate_native_client(client)

    def test_duplicate_action_server_fails_before_dispatch(self):
        transport = object.__new__(action.RosaTransport)
        port = NS(getServiceCount=lambda: 2)
        transport.client = NS(_goal_client=port, _result_client=port, _cancel_client=port,
                              is_action_server_ready=lambda: True)
        with self.assertRaisesRegex(RuntimeError, 'Ambiguous'):
            transport.ready()

    def test_discovery_spins_until_server_ready(self):
        class Discovering(FakeTransport):
            def ready(self):
                return self.clock() >= .5

        clock = FakeClock()
        transport = Discovering(clock, ((.75, ACCEPT), (1., RESULT)))
        code = action.run_action(transport, 'motion', {}, 2., lambda **row: None, clock=clock)
        self.assertEqual(code, 0)
        self.assertEqual(transport.sent, 1)


class PlanningTests(unittest.TestCase):
    def run_case(self, goal=None, status=4, result=None, lease_file=None, interrupt=lambda: None):
        clock = FakeClock()
        result = {'state': {'desc': 'READY', 'state': 0}} if result is None else result
        terminal = dict(event='result', status=status, result=result)
        transport = FakeTransport(clock, ((.25, ACCEPT), (.5, terminal)))
        rows = []
        goal = dict(command='set_map', map_name='utars_nav_map') if goal is None else goal
        code = action.run_action(transport, 'planning', goal, 2., lambda **row: rows.append(row),
            interrupted=interrupt, lease_file=lease_file, clock=clock, cancel_grace=1.)
        return code, rows, transport

    def test_reviewed_map_refresh_and_state_query_require_ready_result(self):
        for command in ('set_map', 'check_state'):
            goal = dict(command=command, map_name='utars_nav_map')
            with self.subTest(command=command):
                self.assertEqual(action.validate_goal('planning', json.dumps(goal)), goal)
                code, rows, transport = self.run_case(goal)
                self.assertEqual(code, 0)
                self.assertEqual(transport.sent, 1)
                self.assertEqual(transport.canceled, [])
                self.assertEqual(rows[0]['endpoint'], '/vnav/action/planning')

    def test_finished_is_idle_only_for_state_query_not_map_refresh(self):
        finished = {'state': {'desc': 'FINISH', 'state': 0}}
        for command, expected_code in (('check_state', 0), ('set_map', 2)):
            with self.subTest(command=command):
                code, rows, transport = self.run_case(
                    dict(command=command, map_name='utars_nav_map'), result=finished)
                self.assertEqual(code, expected_code)
                self.assertEqual(transport.sent, 1)
                self.assertEqual(transport.canceled, [])
                if command == 'set_map':
                    self.assertTrue(any('did not confirm READY' in row.get('reason', '') for row in rows))

    def test_other_commands_targets_fields_or_maps_never_dispatch(self):
        base = dict(command='set_map', map_name='utars_nav_map')
        goals = [dict(base, command=name) for name in ('start_planning', 'navigation_start',
                 'map_set', 'stop', '', True, ['set_map'])]
        goals += [dict(base, map_name=value) for value in ('another_map', '', None, True)]
        goals += [dict(base, **{field: value}) for field, value in (
            ('target_point', {}), ('arg_json', '{}'), ('allow_backward', ''),
            ('marker_operator', ''), ('marker_changename', ''))]
        goals += [{}, {'command': 'set_map'}, {'map_name': 'utars_nav_map'}]
        for goal in goals:
            with self.subTest(goal=goal):
                with self.assertRaises(ValueError):
                    action.validate_goal('planning', json.dumps(goal))
                code, rows, transport = self.run_case(goal)
                self.assertEqual(code, 2)
                self.assertEqual(transport.sent, 0)
                self.assertEqual(transport.canceled, [])

    def test_planning_terminal_status_four_without_ready_is_failure(self):
        results = [{'state': {'desc': desc, 'state': 0}}
                   for desc in ('SUCCESS', 'SUCCEED', 'RUNNING', 'GOAL_OUTCOSTMAP', '', None)]
        results += [{}, {'state': None}, {'state': []}, {'state': 'READY'}]
        for result in results:
            with self.subTest(result=result):
                self.assertFalse(action.result_succeeded('planning', 4, result))
                code, rows, transport = self.run_case(result=result)
                self.assertEqual(code, 2)
                self.assertEqual(transport.sent, 1)
                self.assertEqual(transport.canceled, [])

    def test_ready_cannot_mask_canceled_aborted_or_nonterminal_status(self):
        for status in (0, 2, 5, 6, True, 4.0, '4'):
            with self.subTest(status=status):
                self.assertFalse(action.result_succeeded('planning', status,
                    {'state': {'desc': 'READY', 'state': 0}}))
        for status in (5, 6):
            with self.subTest(status=status):
                code, rows, transport = self.run_case(status=status)
                self.assertEqual(code, 2)
                self.assertEqual(transport.sent, 1)

    def test_expired_lease_or_interruption_prevents_map_refresh(self):
        with tempfile.TemporaryDirectory() as directory:
            lease = Path(directory) / 'lease.json'
            lease.write_text('{"deadline":0}')
            code, rows, transport = self.run_case(lease_file=lease)
            self.assertEqual((code, transport.sent), (2, 0))
        code, rows, transport = self.run_case(interrupt=lambda: 'Signal 2')
        self.assertEqual((code, transport.sent), (2, 0))

    def test_planning_transport_uses_observed_native_type_and_endpoint(self):
        native_action = object()
        base_client = NS(SendGoalOptions=lambda: object())
        rosa = NS(init=Mock(), Node=Mock(return_value='node'), spin_once=Mock(),
                  ok=Mock(return_value=True), shutdown=Mock())
        client = NS(configure_observer=Mock())
        constructor = Mock(return_value=client)
        modules = {'rosa': rosa,
            'rosa.action_client': NS(ActionClient=base_client, ActionClientGoalHandle=object()),
            'rosa.base._ActionType': NS(to_string=str),
            'vnav_task_msgs.action': NS(VnavCommand=native_action)}
        with patch.dict('sys.modules', modules), \
                patch.object(action, 'validate_native_sources', return_value={}) as pin, \
                patch.object(action, 'validate_native_client') as validate, \
                patch.object(action, 'native_client_class', return_value=constructor):
            transport = action.RosaTransport('planning')
            constructor.assert_called_once_with('node', '/vnav/action/planning', native_action)
            pin.assert_called_once()
            validate.assert_called_once_with(client)
            client.configure_observer.assert_called_once()
            transport.close()
            rosa.shutdown.assert_called_once()


if __name__ == '__main__':
    unittest.main()
