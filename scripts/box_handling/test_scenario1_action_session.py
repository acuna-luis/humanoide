#!/usr/bin/env python3
"""Persistent native action session tests; no ROSA import or robot connection."""

import io
import json
from pathlib import Path
import queue
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

if __package__:
    from . import scenario1_action_client as action
else:
    import scenario1_action_client as action


SUCCESS = {'state': {'desc': 'SUCCEED', 'state': 1101001}}
GOAL = {'task_name': 'example', 'yaml_args': '{}'}


def request(number, goal=GOAL, timeout=2):
    return json.dumps({'request_id': 'request-' + str(number), 'goal': goal, 'timeout': timeout})


class FakeClock:
    def __init__(self):
        self.value = 0.

    def __call__(self):
        return self.value


class FakeTransport:
    def __init__(self, clock, results=None):
        self.clock = clock
        self.goal_id = None
        self.sent = []
        self.canceled = []
        self.completed = []
        self.events = []
        self.results = results or [SUCCESS]
        self.on_spin = lambda: None
        self.cancel_result = True
        self.produce_result = True

    def ready(self):
        return True

    def send(self, goal):
        self.sent.append(goal)
        self.goal_id = 'uuid-' + str(len(self.sent))
        self.events.append({'event': 'accepted', 'goal_id': self.goal_id, 'accepted': True})
        if self.produce_result:
            result = self.results[min(len(self.sent)-1, len(self.results)-1)]
            self.events.append({'event': 'result', 'goal_id': self.goal_id, 'status': 4, 'result': result})
        return self.goal_id

    def spin(self):
        self.clock.value += .25
        self.on_spin()

    def drain(self):
        rows, self.events = self.events, []
        return rows

    def cancel(self):
        self.canceled.append(self.goal_id)
        if self.cancel_result:
            self.events.append({'event': 'result', 'goal_id': self.goal_id, 'status': 5, 'result': {}})

    def finish_successful_request(self):
        self.completed.append(self.goal_id)
        self.goal_id = None


def inbox():
    return NS(requests=queue.Queue(), reason=None, eof=False)


class SessionTests(unittest.TestCase):
    def run_requests(self, requests, results=None, kind='motion', configure=lambda *args: None):
        clock = FakeClock()
        transport = FakeTransport(clock, results)
        source = inbox()
        pending = list(requests)
        source.requests.put(pending.pop(0))
        rows = []

        def emit(**row):
            rows.append(row)
            if row['event'] == 'request_complete' and row['returncode'] == 0:
                if pending:
                    source.requests.put(pending.pop(0))
                else:
                    source.eof = True
                    source.reason = 'Request input pipe disconnected'

        configure(transport, source, clock)
        code = action.run_session(transport, kind, source, emit, clock=clock)
        return code, rows, transport

    def test_two_successes_reuse_one_transport_and_distinct_uuid(self):
        code, rows, transport = self.run_requests([request(1), request(2)])
        self.assertEqual(code, 0)
        self.assertEqual(len(transport.sent), 2)
        self.assertEqual(transport.completed, ['uuid-1', 'uuid-2'])
        self.assertEqual(transport.canceled, [])
        for number in (1, 2):
            correlated = [row for row in rows if row.get('request_id') == f'request-{number}']
            self.assertEqual([row['event'] for row in correlated],
                             ['dispatched', 'accepted', 'result', 'request_complete'])
            self.assertEqual(correlated[0]['goal_id'], f'uuid-{number}')

    def test_motion_application_failure_exits_without_second_goal(self):
        code, rows, transport = self.run_requests([request(1), request(2)],
                                                  [{'state': {'desc': 'FAIL', 'state': 1101001}}])
        self.assertEqual(code, 2)
        self.assertEqual(len(transport.sent), 1)
        self.assertEqual(transport.completed, [])
        self.assertEqual(rows[-1], {'event': 'request_complete', 'request_id': 'request-1', 'returncode': 2})

    def test_navigation_application_failure_is_sticky_even_status_four(self):
        nav = {'command': 'check_state', 'arg_json': '{}'}
        bad = {'state': {'desc': 'FAIL'}, 'dmsg': 'FSM_WAITNAVIGATE'}
        code, _, transport = self.run_requests([request(1, nav), request(2, nav)], [bad], 'navigation')
        self.assertEqual(code, 2)
        self.assertEqual(len(transport.sent), 1)
        self.assertEqual(transport.completed, [])

    def test_duplicate_request_id_never_redispatched(self):
        code, _, transport = self.run_requests([request(1), request(1)])
        self.assertEqual(code, 2)
        self.assertEqual(len(transport.sent), 1)

    def test_malformed_goal_never_dispatches(self):
        code, _, transport = self.run_requests([request(1, {'task_name': 'wrong'})])
        self.assertEqual(code, 2)
        self.assertEqual(transport.sent, [])

    def test_eof_during_action_cancels_own_uuid_and_exits(self):
        def configure(transport, source, clock):
            transport.produce_result = False
            def disconnect():
                source.eof = True
                source.reason = 'Request input pipe disconnected'
            transport.on_spin = disconnect
        code, rows, transport = self.run_requests([request(1), request(2)], configure=configure)
        self.assertEqual(code, 2)
        self.assertEqual(transport.canceled, ['uuid-1'])
        self.assertEqual(len(transport.sent), 1)
        self.assertTrue(any(row['event'] == 'interrupted_terminal' for row in rows))

    def test_timeout_unknown_terminal_poisoned_session(self):
        def configure(transport, source, clock):
            transport.produce_result = False
            transport.cancel_result = False
        code, rows, transport = self.run_requests([request(1), request(2)], configure=configure)
        self.assertEqual(code, 3)
        self.assertEqual(transport.canceled, ['uuid-1'])
        self.assertEqual(len(transport.sent), 1)
        self.assertEqual(rows[-1]['returncode'], 3)

    def test_expired_lease_during_idle_never_dispatches(self):
        clock = FakeClock()
        transport = FakeTransport(clock)
        source = inbox()
        source.requests.put(request(1))
        rows = []
        with tempfile.TemporaryDirectory() as directory:
            lease = Path(directory)/'lease.json'
            lease.write_text('{"deadline":0}')
            code = action.run_session(transport, 'motion', source, lambda **r: rows.append(r),
                                      lease_file=lease, clock=clock)
        self.assertEqual(code, 2)
        self.assertEqual(transport.sent, [])

    def test_signal_cancels_active_request(self):
        clock = FakeClock()
        transport = FakeTransport(clock)
        transport.produce_result = False
        source = inbox()
        source.requests.put(request(1))
        rows = []
        code = action.run_session(transport, 'motion', source, lambda **r: rows.append(r),
                                  interrupted=lambda: 'Signal 2' if clock() >= .25 else None, clock=clock)
        self.assertEqual(code, 2)
        self.assertEqual(transport.canceled, ['uuid-1'])

    def test_terminal_success_after_input_disconnect_stays_failure(self):
        def configure(transport, source, clock):
            transport.on_spin = lambda: setattr(source, 'reason', 'Input disconnected')
        code, _, transport = self.run_requests([request(1), request(2)], configure=configure)
        self.assertEqual(code, 2)
        self.assertEqual(transport.completed, [])
        self.assertEqual(len(transport.sent), 1)


class CanceledRecoverySessionTests(unittest.TestCase):
    def run_parked(self, after_complete, *, interrupted=lambda: None, lease_file=None):
        from scripts.box_handling.test_scenario1_action_client import NoProgressTransport
        clock = FakeClock()
        transport = NoProgressTransport(clock)
        source = inbox()
        correction = transport.correction_guard.spec
        goal = dict(command='navigation_start', arg_json=json.dumps(dict(target_point=dict(
            map_name='utars_nav_map', mode='free_nav', **correction['target']))))
        value = dict(request_id='first', goal=goal, timeout=30., correction=correction,
                     allow_correction_recovery=True)
        source.requests.put(json.dumps(value))
        rows = []
        def emit(**row):
            rows.append(row)
            if row['event'] == 'request_complete' and row['returncode'] == 4:
                after_complete(source, transport, value)
        code = action.run_session(transport, 'navigation', source, emit, clock=clock,
                                  interrupted=interrupted, lease_file=lease_file)
        return code, rows, transport

    def test_canceled_worker_stays_retired_and_eof_closes_cleanly(self):
        def close(source, transport, value):
            source.eof = True
            source.reason = 'Request input pipe disconnected'
        code, rows, transport = self.run_parked(close)
        self.assertEqual(code, 0)
        self.assertEqual(transport.sent, 1)
        self.assertEqual(transport.canceled, [transport.goal_id])
        self.assertIsNotNone(transport.correction_guard.failure)
        self.assertEqual([row['returncode'] for row in rows if row['event'] == 'request_complete'], [4])
        self.assertEqual(rows[-1]['event'], 'session_closed')

    def test_canceled_client_rejects_any_further_request_without_dispatch(self):
        def queue_next(source, transport, value):
            source.requests.put(json.dumps(dict(value, request_id='second')))
        code, rows, transport = self.run_parked(queue_next)
        self.assertEqual(code, 2)
        self.assertEqual(transport.sent, 1)
        self.assertTrue(any('retired' in row.get('reason', '') for row in rows))
        self.assertIsNotNone(transport.correction_guard.failure)

    def test_late_transport_error_poisoned_parked_worker(self):
        def extra_error(source, transport, value):
            transport.pending.append(dict(event='error', goal_id=transport.goal_id, reason='late DDS failure'))
        code, rows, transport = self.run_parked(extra_error)
        self.assertEqual(code, 2)
        self.assertEqual(transport.sent, 1)
        self.assertTrue(any('Unexpected evidence after canceled' in row.get('reason', '') for row in rows))

    def test_late_contradictory_or_malformed_status_poisoned_parked_worker(self):
        for status in (4, 6, 0, True, False, 5., '5', None):
            def extra_status(source, transport, value):
                transport.pending.append(dict(event='status', goal_id=transport.goal_id, status=status))
            with self.subTest(status=status):
                code, rows, transport = self.run_parked(extra_status)
                self.assertEqual(code, 2)
                self.assertEqual(transport.sent, 1)
                self.assertIsNotNone(transport.correction_guard.failure)
                self.assertTrue(any('Contradictory status after canceled' in row.get('reason', '')
                                    for row in rows))

    def test_eof_does_not_discard_late_errors_or_contradictory_terminal_status(self):
        for evidence in (dict(event='error', reason='late DDS failure'),
                         dict(event='status', status=4), dict(event='status', status=6)):
            def close_with_evidence(source, transport, value):
                transport.pending.append(dict(goal_id=transport.goal_id, **evidence))
                source.eof = True
                source.reason = 'Request input pipe disconnected'
            with self.subTest(evidence=evidence):
                code, rows, transport = self.run_parked(close_with_evidence)
                self.assertEqual(code, 2)
                self.assertEqual(transport.sent, 1)
                self.assertFalse(any(row['event'] == 'session_closed' for row in rows))

    def test_late_valid_status_does_not_reopen_canceled_worker(self):
        for status in (1, 2, 3, 5):
            closed = [False]
            def extra_status(source, transport, value):
                transport.pending.append(dict(event='status', goal_id=transport.goal_id, status=status))
                original_spin = transport.spin
                def spin_and_close():
                    original_spin()
                    if closed[0]:
                        source.eof = True
                        source.reason = 'Request input pipe disconnected'
                    closed[0] = True
                transport.spin = spin_and_close
            with self.subTest(status=status):
                code, rows, transport = self.run_parked(extra_status)
                self.assertEqual(code, 0)
                self.assertEqual(transport.sent, 1)
                self.assertIsNotNone(transport.correction_guard.failure)
                self.assertEqual([row['returncode'] for row in rows if row['event'] == 'request_complete'], [4])

    def test_parked_worker_preserves_signal_and_lease_checks(self):
        stop = [None]
        def signal(source, transport, value):
            stop[0] = 'Signal 2'
        code, rows, transport = self.run_parked(signal, interrupted=lambda: stop[0])
        self.assertEqual(code, 2)
        self.assertEqual(transport.sent, 1)
        self.assertTrue(any(row.get('reason') == 'Signal 2' for row in rows))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'lease.json'
            path.write_text('{"deadline":0.8}')
            code, rows, transport = self.run_parked(lambda *args: None, lease_file=path)
        self.assertEqual(code, 2)
        self.assertEqual(transport.sent, 1)
        self.assertTrue(any('Lease missing' in row.get('reason', '') for row in rows))

    def test_bare_recovery_return_code_cannot_park_without_validated_evidence(self):
        from scripts.box_handling import scenario1_nav_correction as nav
        clock = FakeClock()
        transport = FakeTransport(clock)
        transport.configure_correction = lambda candidate: None
        candidate = nav.make_spec(dict(point_x=0., point_y=0., point_yaw=0.),
                                  dict(x=.03, y=0., yaw=0., stamp_ns=1), 1, point='box_pickup')
        goal = dict(command='navigation_start', arg_json=json.dumps(dict(target_point=dict(
            map_name='utars_nav_map', mode='free_nav', **candidate['target']))))
        source = inbox()
        source.requests.put(json.dumps(dict(request_id='bad', goal=goal, timeout=30.,
            correction=candidate, allow_correction_recovery=True)))
        rows = []
        code = action.run_session(transport, 'navigation', source, lambda **row: rows.append(row),
                                  clock=clock, run_one=lambda *args, **kwargs: 4)
        self.assertEqual(code, 2)
        self.assertEqual(transport.sent, [])
        self.assertEqual(transport.completed, [])
        self.assertFalse(any(row['event'] == 'request_complete' and row['returncode'] == 4 for row in rows))


class InputTests(unittest.TestCase):
    def test_recovery_flag_requires_explicit_visual_pickup_correction(self):
        from scripts.box_handling import scenario1_nav_correction as nav
        candidate = nav.make_spec(dict(point_x=0., point_y=0., point_yaw=0.),
                                  dict(x=.03, y=0., yaw=0., stamp_ns=1), 1, point='box_pickup')
        goal = dict(command='navigation_start', arg_json=json.dumps(dict(target_point=dict(
            map_name='utars_nav_map', mode='free_nav', **candidate['target']))))
        value = dict(request_id='r', goal=goal, timeout=30., correction=candidate,
                     allow_correction_recovery=True)
        action.validate_session_request('navigation', json.dumps(value), set())
        for invalid in (dict(value, allow_correction_recovery=False),
                        dict(value, allow_correction_recovery=1),
                        dict(value, correction=dict(candidate, point='get1')),
                        {key: item for key, item in value.items() if key != 'correction'}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                action.validate_session_request('navigation', json.dumps(invalid), set())

    def test_exact_request_fields_and_timeout_required(self):
        for raw in (request(1, timeout=True), request(1, timeout=0), request(1, timeout=-1),
                    request(1, timeout=float('inf')), '{}',
                    '{"request_id":"x","goal":{},"timeout":1,"extra":1}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                action.validate_session_request('motion', raw, set())

    def test_unreviewed_navigation_command_rejected_before_dispatch(self):
        with self.assertRaisesRegex(ValueError, 'reviewed'):
            action.validate_session_request('navigation', request(1, {'command': 'unknown', 'arg_json': '{}'}), set())

    def test_session_limit_and_request_ids_bounded(self):
        with self.assertRaisesRegex(ValueError, 'limit'):
            action.validate_session_request('motion', request(999), {str(x) for x in range(256)})
        for value in ('', 'x'*129, 'with spaces', 123):
            raw = json.dumps({'request_id': value, 'goal': GOAL, 'timeout': 2})
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'request_id'):
                action.validate_session_request('motion', raw, set())

    def test_reader_reports_eof_without_blocking_active_loop(self):
        source = action.SessionInput(io.StringIO(request(1)+'\n'))
        source.thread.join(timeout=1)
        self.assertTrue(source.eof)
        self.assertIsNotNone(source.reason)

    def test_reader_refuses_unbounded_queue(self):
        source = action.SessionInput(io.StringIO(request(1)+'\n'+request(2)+'\n'))
        source.thread.join(timeout=1)
        self.assertIn('Too many queued', source.reason)
        self.assertEqual(source.requests.qsize(), 1)

    def test_reader_refuses_unterminated_or_oversized_request(self):
        for value in (request(1), 'x'*(1024*1024+1)):
            source = action.SessionInput(io.StringIO(value))
            source.thread.join(timeout=1)
            self.assertIn('Oversized or incomplete', source.reason)

    def test_serve_requires_lease_and_excludes_oneshot_options_before_import(self):
        for args in (['--serve', '--kind', 'motion'],
                     ['--serve', '--kind', 'motion', '--lease-file', '/unused', '--timeout', '2']):
            with patch('sys.stderr', io.StringIO()), self.assertRaises(SystemExit) as error:
                action.main(args)
            self.assertEqual(error.exception.code, 2)


class AdapterReuseTests(unittest.TestCase):
    def build(self):
        client = action.native_client_class(object, str)()
        rows = []
        client.configure_observer(lambda event, **r: rows.append(dict(event=event, **r)))
        client.observed_goal_id = 'old'
        client.accepted = True
        client.terminal = True
        for key in ('_goal_handles', '_goal_futures', '_result_futures', '_goal_options'):
            setattr(client, key, {'old': object()})
        return client, rows

    def test_reuse_clears_completed_native_storage_and_state(self):
        client, _ = self.build()
        client.retire_successful_goal()
        self.assertIsNone(client.observed_goal_id)
        self.assertFalse(client.accepted)
        self.assertFalse(client.terminal)
        self.assertEqual(client.retired_goal_ids, {'old'})
        for key in ('_goal_handles', '_goal_futures', '_result_futures', '_goal_options'):
            self.assertEqual(getattr(client, key), {})

    def test_late_old_result_and_acceptance_do_not_poison_new_goal(self):
        client, rows = self.build()
        client.retire_successful_goal()
        client.observed_goal_id = 'new'
        client.handle_goal_response_async(NS(goal_id=NS(uuid='old')))
        client.handel_result_async(NS(goal_id=NS(uuid='old')))
        self.assertEqual(rows, [])
        self.assertFalse(client.accepted)
        self.assertFalse(client.terminal)

    def test_unknown_uuid_is_still_an_error(self):
        client, rows = self.build()
        client.retire_successful_goal()
        client.observed_goal_id = 'new'
        client.handel_result_async(NS(goal_id=NS(uuid='unrelated')))
        self.assertEqual(rows[-1]['event'], 'error')
        self.assertFalse(client.terminal)

    def test_incomplete_or_canceled_goal_cannot_be_reused(self):
        for field, value in (('accepted', False), ('terminal', False),
                             ('result_pending', True), ('cancel_future', object())):
            client, _ = self.build()
            setattr(client, field, value)
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                client.retire_successful_goal()

    def test_duplicate_generated_uuid_refused_before_service_dispatch(self):
        class Base:
            def create_goal_request(self, goal, options):
                return object(), 'old'
        client = action.native_client_class(Base, str)()
        client.configure_observer(lambda *args, **kwargs: None)
        client.retired_goal_ids.add('old')
        with self.assertRaisesRegex(RuntimeError, 'UUID reused'):
            client.create_goal_request(object())

    def test_persistent_storage_checked_before_dispatch(self):
        transport = object.__new__(action.RosaTransport)
        transport.client = NS(_goal_handles={}, _goal_futures={}, _result_futures={}, _goal_options={})
        transport.validate_session_api()
        transport.client._goal_options = None
        with self.assertRaisesRegex(RuntimeError, 'persistent goal storage'):
            transport.validate_session_api()


class NavigationContractTests(unittest.TestCase):
    def validate(self, command, result):
        action.validate_session_result('navigation', {'command': command, 'arg_json': '{}'},
                                       {'status': 4, 'result': result})

    def test_reviewed_navigation_results(self):
        for command, result in (
                ('get_map_name', {'state': {'desc': 'SUCCESS'}, 'result_json': '{"map_name":"utars_nav_map"}'}),
                ('check_state', {'state': {'desc': '等待导航'}, 'dmsg': '当前FSM: FSM_WAITNAVIGATE'}),
                ('map_set', {'state': {'desc': 'VSLAM_LOAD_MAP_FINISHED'}}),
                ('relocation_start', {'state': {'desc': 'NAVIGATION_READY'}}),
                ('navigation_start', {'state': {'desc': 'VSLAM_LOCATION_LOST'},
                                      'dmsg': 'navigation_start SUCCEEDED ,change to FSM_WaitNavigate'})):
            with self.subTest(command=command):
                self.validate(command, result)

    def test_empty_map_name_allows_preflight_and_later_map_preparation(self):
        self.validate('get_map_name', {'state': {'desc': 'SUCCESS'},
                                       'result_json': '{"map_name":""}'})

    def test_missing_or_contradictory_navigation_result_fails(self):
        for command, result in (
                ('get_map_name', {'state': {'desc': 'SUCCESS'}, 'result_json': '{}'}),
                ('check_state', {'state': {'desc': 'SUCCESS'}, 'dmsg': 'FSM_NAVIGATING'}),
                ('navigation_start', {'state': {'desc': 'VSLAM_LOCATION_LOST'}, 'dmsg': ''}),
                ('map_set', {'state': {'desc': 'BUSY'}}),
                ('relocation_start', {'state': {'desc': 'BUSY'}})):
            with self.subTest(command=command), self.assertRaises(ValueError):
                self.validate(command, result)


if __name__ == '__main__':
    unittest.main()
