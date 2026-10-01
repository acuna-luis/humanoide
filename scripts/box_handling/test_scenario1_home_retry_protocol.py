"""Known HOME failure handoff; synthetic workers only, never ROS or robot IO."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.box_handling import scenario1_action_client as action
from scripts.box_handling import scenario1_session as session
from scripts.box_handling import test_scenario1_action_session as fixtures


FAILURE = {'state': {'desc': 'MoveToGoalFailed', 'state': 7104050}}


def request(number=1, *, opt=True, goal=None):
    result = dict(request_id=str(number), goal=goal or dict(action.HOME_GOAL), timeout=2)
    if opt:
        result['allow_home_retry'] = True
    return result


def trace(goal_id='uuid-1', request_id=None):
    rows = [dict(event='dispatched', goal_id=goal_id, endpoint=action.ENDPOINTS['motion']),
            dict(event='accepted', goal_id=goal_id, accepted=True),
            dict(event='result', goal_id=goal_id, status=6, result=copy.deepcopy(FAILURE)),
            dict(event='error', goal_id=goal_id, reason=action.UNSUCCESSFUL_TERMINAL)]
    if request_id is not None:
        for row in rows:
            row['request_id'] = request_id
    return rows


class HomeTransport(fixtures.FakeTransport):
    def __init__(self, clock, outcomes=None):
        super().__init__(clock)
        self.outcomes = outcomes or [dict(status=6, result=copy.deepcopy(FAILURE))]
        self.failed_retirements = []
        self.modify = lambda rows: None

    def send(self, goal):
        goal_id = super().send(goal)
        if self.produce_result:
            self.events[-1].update(copy.deepcopy(self.outcomes[min(len(self.sent)-1, len(self.outcomes)-1)]))
        self.modify(self.events)
        return goal_id

    def finish_recoverable_home_failure(self, terminal):
        if not action.known_home_failure(terminal) or terminal['goal_id'] != self.goal_id:
            raise AssertionError('Invalid synthetic failure retirement')
        self.failed_retirements.append(self.goal_id)
        self.goal_id = None


class HomeFailureWorkerTests(unittest.TestCase):
    def run_requests(self, requests, *, outcomes=None, configure=lambda *args: None):
        clock = fixtures.FakeClock()
        transport = HomeTransport(clock, outcomes)
        source = fixtures.inbox()
        pending = list(requests)
        source.requests.put(json.dumps(pending.pop(0)))
        rows = []

        def emit(**row):
            rows.append(row)
            if row['event'] == 'request_complete' and (
                    row['returncode'] == 0 or row.get('recoverable_home_failure') is True):
                if pending:
                    source.requests.put(json.dumps(pending.pop(0)))
                else:
                    source.eof = True
                    source.reason = 'Request input pipe disconnected'

        configure(transport, source, clock)
        code = action.run_session(transport, 'motion', source, emit, clock=clock)
        return code, rows, transport

    def test_known_failure_is_returned_unchanged_without_worker_retry_or_cancellation(self):
        code, rows, transport = self.run_requests([request()])
        self.assertEqual(code, 0)  # Session ends normally only after synthetic supervisor EOF.
        self.assertEqual(transport.sent, [action.HOME_GOAL])
        self.assertEqual(transport.canceled, [])
        self.assertEqual(transport.completed, [])
        self.assertEqual(transport.failed_retirements, ['uuid-1'])
        result = [row for row in rows if row['event'] == 'result']
        self.assertEqual(result, [dict(event='result', request_id='1', goal_id='uuid-1',
                                      status=6, result=FAILURE)])
        receipt = [row for row in rows if row['event'] == 'request_complete']
        self.assertEqual(receipt, [dict(event='request_complete', request_id='1', returncode=2,
                                       recoverable_home_failure=True, goal_id='uuid-1')])

    def test_supervisor_must_request_second_home_with_new_uuid(self):
        success = dict(status=4, result=fixtures.SUCCESS)
        code, rows, transport = self.run_requests([request(), request(2, opt=False)],
                                                outcomes=[dict(status=6, result=FAILURE), success])
        self.assertEqual(code, 0)
        self.assertEqual(transport.sent, [action.HOME_GOAL, action.HOME_GOAL])
        self.assertEqual(transport.failed_retirements, ['uuid-1'])
        self.assertEqual(transport.completed, ['uuid-2'])
        self.assertEqual([row['returncode'] for row in rows if row['event'] == 'request_complete'], [2, 0])

    def test_second_home_without_optin_remains_permanent_failure(self):
        code, rows, transport = self.run_requests([request(), request(2, opt=False), request(3)])
        self.assertEqual(code, 2)
        self.assertEqual(len(transport.sent), 2)
        self.assertEqual(transport.failed_retirements, ['uuid-1'])
        self.assertNotIn('recoverable_home_failure', rows[-1])

    def test_failure_without_optin_is_not_recoverable(self):
        code, rows, transport = self.run_requests([request(opt=False), request(2)])
        self.assertEqual(code, 2)
        self.assertEqual(len(transport.sent), 1)
        self.assertEqual(transport.failed_retirements, [])

    def test_unknown_code_description_status_or_uuid_is_not_recoverable(self):
        outcomes = [dict(status=6, result={'state': {'desc': 'OtherFault', 'state': 7104050}}),
                    dict(status=6, result={'state': {'desc': 'MoveToGoalFailed', 'state': 7104051}}),
                    dict(status=6, result={'state': {'desc': 'MoveToGoalFailed', 'state': '7104050'}}),
                    dict(status=5, result=FAILURE), dict(status=4, result=FAILURE),
                    dict(status=6, result=FAILURE, goal_id=None)]
        for outcome in outcomes:
            with self.subTest(outcome=outcome):
                code, rows, transport = self.run_requests([request(), request(2)], outcomes=[outcome])
                self.assertEqual(code, 2)
                self.assertEqual(len(transport.sent), 1)
                self.assertEqual(transport.failed_retirements, [])
                self.assertFalse(any(row.get('recoverable_home_failure') for row in rows))

    def test_duplicate_result_missing_acceptance_or_extra_transport_error_poison(self):
        def duplicate(rows): rows.append(copy.deepcopy(rows[-1]))
        def no_acceptance(rows): rows.pop(0)
        def extra_error(rows): rows.append(dict(event='error', goal_id='uuid-1', reason='callback fault'))
        def canceled_status(rows): rows.append(dict(event='status', goal_id='uuid-1', status=5))
        def canceling_pending(rows): rows.append(dict(event='result_pending', goal_id='uuid-1', status=3))
        for modify in (duplicate, no_acceptance, extra_error, canceled_status, canceling_pending):
            def configure(transport, source, clock): transport.modify = modify
            with self.subTest(modify=modify.__name__):
                code, rows, transport = self.run_requests([request(), request(2)], configure=configure)
                self.assertEqual(code, 2)
                self.assertEqual(len(transport.sent), 1)
                self.assertEqual(transport.failed_retirements, [])
                self.assertFalse(any(row.get('recoverable_home_failure') for row in rows))

    def test_disconnect_or_timeout_cannot_be_reclassified_even_with_matching_terminal(self):
        for failure in ('disconnect', 'timeout'):
            def configure(transport, source, clock):
                if failure == 'disconnect':
                    transport.on_spin = lambda: setattr(source, 'reason', 'Lost supervisor')
                else:
                    transport.on_spin = lambda: setattr(clock, 'value', 10.)
            with self.subTest(failure=failure):
                code, rows, transport = self.run_requests([request(), request(2)], configure=configure)
                self.assertEqual(code, 2)
                self.assertEqual(transport.failed_retirements, [])
                self.assertFalse(any(row.get('recoverable_home_failure') for row in rows))

    def test_lease_expiry_during_retirement_poisoned_before_recoverable_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'lease.json'
            path.write_text('{"deadline":50}')
            clock = fixtures.FakeClock()
            transport = HomeTransport(clock)
            source = fixtures.inbox()
            source.requests.put(json.dumps(request()))
            rows = []
            original = transport.finish_recoverable_home_failure

            def retire(terminal):
                original(terminal)
                path.write_text('{"deadline":0}')

            transport.finish_recoverable_home_failure = retire
            code = action.run_session(transport, 'motion', source, lambda **row: rows.append(row),
                                      clock=clock, lease_file=path)
            self.assertEqual(code, 2)
            self.assertEqual(len(transport.sent), 1)
            self.assertFalse(any(row.get('recoverable_home_failure') for row in rows))

    def test_optin_rejects_other_actions_or_nonempty_home_arguments_before_dispatch(self):
        candidates = [request(goal={'task_name': 'cruzr/ready', 'yaml_args': '{}'}),
                      request(goal={'task_name': 'cruzr/home', 'yaml_args': '{"a":1}'}),
                      request(goal={'task_name': 'cruzr/home', 'yaml_args': '{ }'})]
        for value in (False, 1, 'true', None):
            candidate = request(); candidate['allow_home_retry'] = value; candidates.append(candidate)
        for candidate in candidates:
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                action.validate_session_request('motion', json.dumps(candidate), set())
        for kind in ('navigation', 'planning'):
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                action.validate_session_request(kind, json.dumps(request()), set())


class HomeFailureReceiptTests(unittest.TestCase):
    def test_parent_independently_requires_optin_exact_trace_and_terminal_identity(self):
        receipt = dict(event='request_complete', request_id='1', returncode=2,
                       recoverable_home_failure=True, goal_id='uuid-1')
        goal_request = request(); goal_request.pop('request_id')
        rows = trace(request_id='1')
        self.assertTrue(session.recoverable_home_receipt(goal_request, '1', receipt, rows))
        for key, value in [('recoverable_home_failure', False), ('goal_id', 'wrong'),
                           ('request_id', 'wrong'), ('returncode', 0), ('returncode', True)]:
            malformed = dict(receipt, **{key: value})
            with self.subTest(key=key, value=value):
                self.assertFalse(session.recoverable_home_receipt(goal_request, '1', malformed, rows))
        no_optin = dict(goal_request); no_optin.pop('allow_home_retry')
        self.assertFalse(session.recoverable_home_receipt(no_optin, '1', receipt, rows))
        for bad_rows in (rows+rows[2:3], rows[1:], rows[:1]+rows[2:],
                         rows+[dict(event='cancel_requested', request_id='1', goal_id='uuid-1')],
                         rows+[dict(event='result_pending', request_id='1', goal_id='uuid-1', status=3)]):
            self.assertFalse(session.recoverable_home_receipt(goal_request, '1', receipt, bad_rows))

    def test_real_local_pipe_keeps_worker_alive_and_returns_original_failed_result(self):
        worker = '''import json,sys
print(json.dumps({'event':'session_ready','request_id':None}),flush=True)
for line in sys.stdin:
 r=json.loads(line); rid=r['request_id']; uid='uuid-'+rid
 for event in TRACE:
  event=dict(event,request_id=rid,goal_id=uid)
  print(json.dumps(event),flush=True)
 print(json.dumps(dict(event='request_complete',request_id=rid,goal_id=uid,returncode=2,recoverable_home_failure=True)),flush=True)
'''.replace('TRACE', repr(trace()))
        events = []
        channel = session.ProcessSession([sys.executable, '-u', '-B', '-c', worker], events.append)
        try:
            goal_request = request(); goal_request.pop('request_id')
            first = channel.call(goal_request, timeout=2)
            self.assertFalse(channel.failed)
            self.assertIsNone(channel.process.poll())
            self.assertEqual([row['status'] for row in first if row['event'] == 'result'], [6])
            second = channel.call(goal_request, timeout=2)
            self.assertEqual([row['goal_id'] for row in second if row['event'] == 'result'], ['uuid-2'])
            self.assertEqual(channel.sequence, 2)
        finally:
            channel.close()

    def test_native_retirement_still_rejects_bad_result_or_queued_duplicate(self):
        transport = object.__new__(action.RosaTransport)
        transport.client = Mock()
        transport.client.observed_goal_id = 'uuid-1'
        transport.correction_guard = None
        transport.drain = Mock(return_value=[trace()[2]])
        with self.assertRaisesRegex(RuntimeError, 'Unexpected evidence'):
            transport.finish_recoverable_home_failure(trace()[2])
        transport.client.retire_successful_goal.assert_not_called()
        with self.assertRaisesRegex(RuntimeError, 'Unconfirmed HOME'):
            transport.finish_recoverable_home_failure(dict(trace()[2], status=4))
        transport.client.retire_successful_goal.assert_not_called()


if __name__ == '__main__':
    unittest.main()
