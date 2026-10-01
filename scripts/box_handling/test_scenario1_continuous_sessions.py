"""Long-lived request sessions and replay rejection; no ROS or robot."""
import json
import queue
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.box_handling import scenario1_action_client as action
from scripts.box_handling import scenario1_health_worker as health
from scripts.box_handling.scenario1_request_ids import RequestIds
from scripts.box_handling import test_scenario1_action_session as fixtures


def motion_request(number, **changes):
    return json.dumps(dict(request_id=str(number), goal=fixtures.GOAL,
                          timeout=2, **changes))


class RequestIdTests(unittest.TestCase):
    def test_ten_thousand_requests_keep_only_high_water_mark(self):
        ids = RequestIds(legacy_limit=256)
        for number in range(1, 10001):
            ids.validate(str(number))
            ids.add(str(number))
        self.assertEqual(ids.last_sequence, 10000)
        self.assertEqual(ids.legacy_ids, set())
        self.assertEqual(ids.mode, 'sequential')
        for number in (1, 256, 9999, 10000):
            with self.subTest(number=number), self.assertRaisesRegex(ValueError, 'Repeated'):
                ids.add(str(number))
        self.assertEqual(ids.last_sequence, 10000)

    def test_first_sequence_must_be_one_and_no_gaps_allowed(self):
        ids = RequestIds(legacy_limit=256)
        for number in ('2', '1000'):
            with self.assertRaisesRegex(ValueError, 'Out-of-order'):
                ids.add(number)
        ids.add('1')
        with self.assertRaisesRegex(ValueError, 'Out-of-order'):
            ids.add('3')
        ids.add('2')

    def test_legacy_ids_preserve_limit_and_replay_rejection(self):
        ids = RequestIds(legacy_limit=3)
        for value in ('alpha', 'beta', 'gamma'):
            ids.add(value)
        with self.assertRaisesRegex(ValueError, 'Repeated'):
            ids.add('alpha')
        with self.assertRaisesRegex(ValueError, 'limit'):
            ids.add('delta')
        self.assertEqual(ids.last_sequence, 0)
        self.assertEqual(len(ids.legacy_ids), 3)

    def test_mode_cannot_change_to_erase_replay_history(self):
        for first, second in (('1', 'legacy-1'), ('legacy-1', '1'), ('1', '01'),
                              ('1', '0'), ('1', '+2'), ('1', '\u0662')):
            ids = RequestIds(legacy_limit=256)
            ids.add(first)
            with self.subTest(first=first, second=second), self.assertRaisesRegex(ValueError, 'mix'):
                ids.add(second)


class ActionSessionTests(unittest.TestCase):
    def run_requests(self, values):
        return fixtures.SessionTests().run_requests(values)

    def test_more_than_old_limit_remain_sequential_and_close_cleanly(self):
        code, rows, transport = self.run_requests([motion_request(n) for n in range(1, 301)])
        self.assertEqual(code, 0)
        self.assertEqual(len(transport.sent), 300)
        self.assertEqual(len(transport.completed), 300)
        self.assertEqual(transport.canceled, [])
        self.assertEqual(rows[-1]['event'], 'session_closed')

    def test_replay_of_old_request_never_dispatches_after_old_limit(self):
        code, rows, transport = self.run_requests(
            [motion_request(n) for n in range(1, 301)] + [motion_request(1), motion_request(301)])
        self.assertEqual(code, 2)
        self.assertEqual(len(transport.sent), 300)
        self.assertEqual(rows[-1]['request_id'], '1')
        self.assertTrue(any('Repeated request_id' in row.get('reason', '') for row in rows))

    def test_skipped_sequence_does_not_dispatch(self):
        code, rows, transport = self.run_requests([motion_request(1), motion_request(3)])
        self.assertEqual(code, 2)
        self.assertEqual(len(transport.sent), 1)
        self.assertTrue(any('Out-of-order' in row.get('reason', '') for row in rows))

    def test_malformed_goal_does_not_consume_sequence(self):
        ids = RequestIds(legacy_limit=256)
        malformed = json.loads(motion_request(1))
        malformed['goal'] = {}
        with self.assertRaises(ValueError):
            action.validate_session_request('motion', json.dumps(malformed), ids)
        self.assertEqual(ids.last_sequence, 0)
        self.assertEqual(action.validate_session_request('motion', motion_request(1), ids)[0], '1')


class HealthSessionTests(unittest.TestCase):
    def run_requests(self, numbers):
        pending = iter(numbers)
        commands = queue.Queue(maxsize=16)
        active = True
        rows = []
        acquired = []

        def enqueue():
            nonlocal active
            number = next(pending, None)
            if number is None:
                active = False  # End the lease once the synthetic workload ends.
            else:
                commands.put_nowait(health.validate_request(
                    dict(request_id=str(number), command='health')))

        def emit(**row):
            rows.append(row)
            if row['event'] == 'request_complete' and row['returncode'] == 0:
                enqueue()

        def acquire(request, guard):
            guard()
            acquired.append(request['request_id'])
            return dict(event='health_result', request_id=request['request_id'])

        reader = SimpleNamespace(spin=lambda: None, acquire=acquire, close=lambda: None)
        enqueue()
        with patch.object(health.queue, 'Queue', return_value=commands), \
                patch.object(health.threading, 'Thread'), \
                patch.object(health, 'NativeReader', return_value=reader), \
                patch.object(health, 'session_active', side_effect=lambda *args: active), \
                patch.object(health, 'emit', side_effect=emit):
            code = health.main(['--session', '/unused-test-session'])
        return code, rows, acquired

    def test_five_thousand_requests_do_not_hit_old_health_limit(self):
        code, rows, acquired = self.run_requests(range(1, 5001))
        self.assertEqual(len(acquired), 5000)
        completed = [row for row in rows if row['event'] == 'request_complete']
        self.assertEqual(len(completed), 5000)
        self.assertTrue(all(row['returncode'] == 0 for row in completed))
        self.assertEqual(code, 78)  # Explicit synthetic lease expiry still ends it.
        self.assertIn('lease expired', rows[-1]['reason'])

    def test_health_rejects_replay_after_more_than_4096_requests(self):
        code, rows, acquired = self.run_requests([*range(1, 4201), 1, 4201])
        self.assertEqual(code, 78)
        self.assertEqual(len(acquired), 4200)
        self.assertEqual(rows[-1], dict(event='request_complete', request_id='1', returncode=78))
        self.assertIn('Repeated request_id', rows[-2]['reason'])


if __name__ == '__main__':
    unittest.main()
