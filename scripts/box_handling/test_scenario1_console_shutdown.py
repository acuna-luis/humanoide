"""Clean finish diagnostics cannot mask faults while a goal is active."""
import copy
import json
import unittest

from scripts.box_handling.scenario1_console import ConsoleReporter


FINISH = {'event': 'session_finishing', 'reason': 'requested'}


def idle_error(kind='motion'):
    detail = {'event': 'error', 'request_id': None,
              'reason': 'Lease missing, invalid or expired'}
    if kind == 'health_worker':
        detail['reason'] = 'RuntimeError: Health worker lease expired or stop requested'
        return {'event': 'health_worker', 'detail': detail}
    detail['goal_id'] = None
    return {'event': 'action', 'kind': kind, 'detail': detail}


def closed(kind='motion', code=2):
    event = idle_error(kind)
    event['detail'] = {'event': 'worker_closed', 'returncode': code,
                       'physical_stop_verified': False}
    return event


class ShutdownPresentationTests(unittest.TestCase):
    def test_explicit_finish_then_exact_idle_revocations_are_presented_as_closure(self):
        reporter = ConsoleReporter()
        self.assertIn('Cierre solicitado', '\n'.join(reporter.render(FINISH)))
        for kind in ('motion', 'navigation', 'planning', 'health_worker'):
            with self.subTest(kind=kind):
                original = idle_error(kind)
                snapshot = copy.deepcopy(original)
                self.assertEqual(reporter.render(original), [])
                self.assertEqual(original, snapshot)
                self.assertEqual(reporter.render(closed(kind, 78 if kind == 'health_worker' else 2)), [])

    def test_same_idle_errors_and_exit_codes_before_finish_still_report_errors(self):
        reporter = ConsoleReporter()
        for kind in ('motion', 'navigation', 'planning', 'health_worker'):
            self.assertIn('ERROR', '\n'.join(reporter.render(idle_error(kind))))
            self.assertIn('ERROR', '\n'.join(reporter.render(closed(kind))))

    def test_other_finishing_reason_does_not_authorize_reclassification(self):
        reporter = ConsoleReporter()
        reporter.render({'event': 'session_finishing', 'reason': 'fault'})
        self.assertIn('ERROR', '\n'.join(reporter.render(idle_error())))

    def test_active_request_or_goal_lease_error_stays_visible_after_finish(self):
        for key in ('request_id', 'goal_id'):
            reporter = ConsoleReporter()
            reporter.render(FINISH)
            event = idle_error()
            event['detail'][key] = 'active-uuid'
            with self.subTest(key=key):
                self.assertIn('ERROR', '\n'.join(reporter.render(event)))
                self.assertIn('ERROR', '\n'.join(reporter.render(closed())))

    def test_health_request_and_unknown_or_malformed_errors_stay_visible(self):
        variants = []
        health = idle_error('health_worker')
        health['detail']['request_id'] = 'health-1'
        variants.append(health)
        health_goal = idle_error('health_worker')
        health_goal['detail']['goal_id'] = 'unexpected-active-uuid'
        variants.append(health_goal)
        for kind in ('motion', 'health_worker'):
            event = idle_error(kind)
            event['detail']['reason'] += ' unexpected suffix'
            variants.append(event)
        event = idle_error('other')
        variants.append(event)
        for key in ('request_id', 'goal_id'):
            event = idle_error()
            del event['detail'][key]
            variants.append(event)
        for event in variants:
            reporter = ConsoleReporter()
            reporter.render(FINISH)
            with self.subTest(event=event):
                self.assertIn('ERROR', '\n'.join(reporter.render(event)))

    def test_close_code_requires_preceding_exact_idle_error_for_same_worker(self):
        reporter = ConsoleReporter()
        reporter.render(FINISH)
        self.assertIn('ERROR', '\n'.join(reporter.render(closed())))
        reporter.render(idle_error('motion'))
        self.assertIn('ERROR', '\n'.join(reporter.render(closed('navigation'))))
        self.assertIn('ERROR', '\n'.join(reporter.render(closed('motion', 78))))
        self.assertIn('ERROR', '\n'.join(reporter.render(closed('motion', 2))))

    def test_unexpected_error_revokes_expected_close_classification(self):
        reporter = ConsoleReporter()
        reporter.render(FINISH)
        reporter.render(idle_error())
        bad = idle_error()
        bad['detail']['reason'] = 'Unexpected callback with active goal'
        self.assertIn('ERROR', '\n'.join(reporter.render(bad)))
        self.assertIn('ERROR', '\n'.join(reporter.render(closed())))

    def test_late_cancellation_and_terminal_uncertainty_remain_visible(self):
        reporter = ConsoleReporter()
        reporter.render(FINISH)
        for name in ('cancel_requested', 'cancel_response', 'terminal_unknown',
                     'interrupted_terminal', 'worker_exit_unconfirmed'):
            event = idle_error()
            event['detail'] = {'event': name, 'request_id': 'req-1', 'goal_id': 'goal-1'}
            self.assertTrue(reporter.render(event), name)

    def test_verbose_keeps_every_original_event_unchanged(self):
        reporter = ConsoleReporter(verbose=True)
        for event in (FINISH, idle_error(), closed()):
            self.assertEqual(json.loads(reporter.render(event)[0]), event)


if __name__ == '__main__':
    unittest.main()
