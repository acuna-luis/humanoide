"""Console presentation cannot alter durable evidence or supervisor control."""
import copy
import io
import json
from pathlib import Path
import queue
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from scripts.box_handling import scenario1_cli as cli
from scripts.box_handling import scenario1_contract as contract
from scripts.box_handling.scenario1_console import ConsoleReporter, stage_label
from scripts.box_handling.test_scenario1_contract import profile


def feedback(*, goal='goal-1', request='request-1', kind='navigation', state='NAVIGATING'):
    return {'event': 'action', 'kind': kind, 'time_ns': 1790580012123456789,
            'detail': {'event': 'feedback', 'goal_id': goal, 'request_id': request,
                       'feedback': {'state': {'desc': state, 'state': 1101000},
                                    'dmsg': 'normal progress'}}}


class ReporterTests(unittest.TestCase):
    def reporter(self, verbose=False):
        clock = SimpleNamespace(now=0.)
        return ConsoleReporter(verbose=verbose, clock=lambda: clock.now), clock

    def test_fifty_hertz_feedback_prints_at_most_twice_in_one_second(self):
        reporter, clock = self.reporter()
        lines = []
        for index in range(51):
            clock.now = index / 50
            event = feedback()
            event['time_ns'] += index
            lines.extend(reporter.render(event))
        self.assertGreaterEqual(len(lines), 1)
        self.assertLessEqual(len(lines), 2)
        self.assertTrue(all(isinstance(line, str) for line in lines))
        self.assertNotIn('{', '\n'.join(lines))
        self.assertNotIn('1790580012123456789', '\n'.join(lines))

    def test_new_goal_has_its_own_immediate_first_feedback(self):
        reporter, clock = self.reporter()
        self.assertTrue(reporter.render(feedback()))
        clock.now = .01
        self.assertEqual(reporter.render(feedback()), [])
        self.assertTrue(reporter.render(feedback(goal='goal-2', request='request-2')))

    def test_request_without_goal_and_other_endpoint_do_not_share_throttle(self):
        reporter, clock = self.reporter()
        self.assertTrue(reporter.render(feedback(goal=None, request='query-1')))
        clock.now = .01
        self.assertTrue(reporter.render(feedback(goal=None, request='query-2')))
        self.assertTrue(reporter.render(feedback(goal=None, request='query-2', kind='motion')))

    def test_feedback_state_change_is_visible_before_interval_expires(self):
        reporter, clock = self.reporter()
        reporter.render(feedback())
        clock.now = .01
        changed = reporter.render(feedback(state='ARRIVING'))
        self.assertTrue(changed)
        self.assertIn('ARRIVING', '\n'.join(changed))
        self.assertEqual(reporter.render(feedback(state='ARRIVING')), [])

    def test_alerts_and_repeated_lost_reports_are_never_throttled(self):
        reporter, clock = self.reporter()
        reporter.render(feedback())
        clock.now = .01
        alerts = [feedback(state='VSLAM_LOCATION_LOST'), {'event': 'error', 'reason': 'CONTROL_ERROR'}]
        for name in ('error', 'rejected', 'cancel_requested', 'terminal_unknown'):
            alerts.append({'event': 'action', 'kind': 'navigation', 'detail': {
                'event': name, 'goal_id': 'goal-1', 'request_id': 'request-1', 'reason': 'detail_'+name}})
        for event in alerts:
            with self.subTest(event=event):
                self.assertTrue(reporter.render(event))
                self.assertTrue(reporter.render(event))

    def test_repeated_obstacle_reports_always_warn_and_preserve_provider_detail(self):
        reporter, clock = self.reporter()
        reporter.render(feedback())
        clock.now = .01
        event = feedback(state='OBSTACLE')
        event['detail']['feedback']['dmsg'] = 'Obstáculo frontal a 0,4 m'
        for _ in range(3):
            output = '\n'.join(reporter.render(event))
            self.assertIn('AVISO', output)
            self.assertIn('OBSTACLE', output)
            self.assertIn('Obstáculo frontal a 0,4 m', output)

    def test_health_timing_after_error_does_not_claim_a_successful_check(self):
        reporter, _ = self.reporter()
        self.assertTrue(reporter.render({'event': 'error', 'reason': 'Fallo leyendo estado técnico'}))
        output = '\n'.join(reporter.render({'event': 'timing', 'operation': 'health',
                                           'stage': 'retreat', 'elapsed_s': 1.2345}))
        self.assertIn('Comprobación de estado técnico', output)
        self.assertRegex(output, r'1[.,]2\s*s')
        for unsupported_success in ('comprobado', 'completada', 'correcto'):
            self.assertNotIn(unsupported_success, output.lower())

    def test_transport_success_with_location_lost_does_not_complete_stage(self):
        reporter, _ = self.reporter()
        event = {'event': 'action', 'kind': 'navigation', 'detail': {
            'event': 'result', 'status': 4, 'goal_id': 'goal-1', 'request_id': 'request-1',
            'result': {'state': {'desc': 'VSLAM_LOCATION_LOST', 'state': 0},
                       'dmsg': 'navigation_start SUCCEEDED'}}}
        output = '\n'.join(reporter.render(event))
        self.assertIn('VSLAM_LOCATION_LOST', output)
        self.assertNotIn('etapa completada', output.lower())
        self.assertNotIn('agarre completado', output.lower())

    def test_only_stage_complete_announces_completion_with_assumption_label(self):
        reporter, _ = self.reporter()
        lines = reporter.render({'event': 'stage_complete', 'stage': 'verify_held',
                                 'elapsed_s': 1.23456789, 'logical_assumption': True})
        output = '\n'.join(lines)
        self.assertIn('complet', output.lower())
        self.assertIn('asum', output.lower())
        self.assertRegex(output, r'1[.,]2\s*s')
        self.assertNotIn('1.23456789', output)
        self.assertNotIn('{', output)

    def test_labels_and_elapsed_time_are_readable_without_raw_event_dump(self):
        reporter, _ = self.reporter()
        for stage in contract.STAGES:
            with self.subTest(stage=stage):
                self.assertIsInstance(stage_label(stage), str)
                self.assertTrue(stage_label(stage).strip())
        output = '\n'.join(reporter.render({'event': 'timing', 'operation': 'health',
                                           'stage': 'retreat', 'elapsed_s': 2.3456789,
                                           'time_ns': 1790580012123456789}))
        self.assertRegex(output, r'2[.,]3\s*s')
        self.assertNotIn('2.3456789', output)
        self.assertNotIn('1790580012123456789', output)
        self.assertNotIn('{', output)

    def test_checkpoint_keeps_assumption_label_after_full_technical_entry_checks(self):
        reporter, _ = self.reporter()
        cp = contract.new_checkpoint(profile(), policy='assume')
        for stage in contract.STAGES[:4]:
            arguments = dict(confirmed_box='held', verification_source='assumed') if stage == 'verify_held' else {}
            cp = contract.complete_stage(contract.begin_stage(cp, stage), stage, **arguments)
        self.assertEqual(reporter.render({'event': 'checkpoint', 'checkpoint': cp}), [])
        # First resumed verification runs full health checks, hence this flag
        # can be false even though the actual box evidence remains assumed.
        output = '\n'.join(reporter.render({'event': 'stage_complete', 'stage': 'verify_held',
                                           'elapsed_s': 1.5, 'logical_assumption': False}))
        self.assertIn('asum', output.lower())

    def test_malformed_optional_presentation_data_never_raises(self):
        reporter, _ = self.reporter()
        malformed = [None, [], {}, {'event': None}, {'event': 'action', 'detail': None},
                     {'event': 'action', 'detail': {'event': 'feedback', 'feedback': []}},
                     {'event': 'stage_complete', 'stage': 'retreat', 'elapsed_s': 'bad'},
                     {'event': 'arrival', 'point': 'get1', 'measurement': None},
                     {'event': 'timing', 'elapsed_s': float('nan')},
                     {'event': 'get1_correction', 'measurements': 'bad', 'phase': 'measured'}]
        for event in malformed:
            with self.subTest(event=event):
                result = reporter.render(event)
                self.assertIsInstance(result, list)
                self.assertTrue(all(isinstance(line, str) for line in result))

    def test_verbose_preserves_entire_event_without_throttling_or_mutation(self):
        reporter, clock = self.reporter(verbose=True)
        event = feedback()
        event['extra'] = {'unicode': 'posición', 'nested': [1, False, None]}
        original = copy.deepcopy(event)
        for _ in range(3):
            lines = reporter.render(event)
            self.assertEqual(len(lines), 1)
            self.assertEqual(json.loads(lines[0]), original)
            clock.now += .001
        self.assertEqual(event, original)


class ConnectionPresentationTests(unittest.TestCase):
    def connection(self, evidence, raw, console):
        connection = cli.Connection.__new__(cli.Connection)
        connection.evidence = evidence
        connection.events = queue.Queue()
        connection.process = SimpleNamespace(stdout=io.StringIO(raw))
        connection.console = console
        return connection

    def test_raw_log_is_exact_and_written_before_presentation_and_control_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint = contract.new_checkpoint(profile(), policy='assume')
            rows = [dict(event='checkpoint', checkpoint=checkpoint), feedback(),
                    dict(event='error', reason='CONTROL_ERROR posición')]
            raw_lines = [json.dumps(row, ensure_ascii=False, separators=(', ', ': '))+'\n' for row in rows]
            raw = ''.join(raw_lines)
            observed = []

            class ObservingConsole(ConsoleReporter):
                def render(self, event):
                    index = len(observed)
                    self_test.assertEqual((root/'events.jsonl').read_bytes(), ''.join(raw_lines[:index+1]).encode())
                    observed.append(copy.deepcopy(event))
                    return super().render(event)

            self_test = self
            connection = self.connection(root, raw, ObservingConsole(clock=lambda: 0.))
            with patch('sys.stdout', io.StringIO()) as shown:
                connection.read()
            self.assertIn('CONTROL_ERROR', shown.getvalue())  # Reader, without wait(), presents errors.
            self.assertEqual((root/'events.jsonl').read_bytes(), raw.encode())
            self.assertEqual(observed, rows)
            self.assertEqual(json.loads((root/'checkpoint.json').read_text()), checkpoint)
            with patch('sys.stdout', io.StringIO()) as later, self.assertRaisesRegex(RuntimeError, 'CONTROL_ERROR'):
                connection.wait('stage_complete', timeout=1)
            self.assertEqual(later.getvalue(), '')  # wait() performs control only, no duplicate output.

    def test_formatter_failure_cannot_lose_checkpoint_or_suppress_control_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint = contract.new_checkpoint(profile(), policy='assume')
            raw = json.dumps(dict(event='checkpoint', checkpoint=checkpoint))+'\n'
            raw += json.dumps(dict(event='error', reason='CONTROL_STILL_REQUIRED'))+'\n'

            class BrokenConsole:
                def __init__(self):
                    self.calls = []

                def render(self, event):
                    self.calls.append(event['event'])
                    raise ValueError('Synthetic presentation failure')

            console = BrokenConsole()
            connection = self.connection(root, raw, console)
            with patch('sys.stdout', io.StringIO()), patch('sys.stderr', io.StringIO()):
                connection.read()
            self.assertEqual((root/'events.jsonl').read_bytes(), raw.encode())
            self.assertEqual(json.loads((root/'checkpoint.json').read_text()), checkpoint)
            self.assertEqual(console.calls, ['checkpoint', 'error'])
            with self.assertRaisesRegex(RuntimeError, 'CONTROL_STILL_REQUIRED'):
                connection.wait('stage_complete', timeout=1)

    def test_late_cancellation_and_unknown_terminal_are_displayed_during_close(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            events = [{'event': 'action', 'kind': 'navigation', 'detail': {
                'event': name, 'goal_id': 'late-goal', 'request_id': 'late-request',
                'reason': 'LATE_'+name, 'physical_stop_verified': False}}
                for name in ('cancel_requested', 'terminal_unknown')]
            raw = ''.join(json.dumps(event)+'\n' for event in events)
            connection = self.connection(root, raw, ConsoleReporter(clock=lambda: 0.))
            connection.closed = threading.Event()
            connection.write_lock = threading.Lock()
            connection.process.stdin = io.StringIO()
            # Emulate reader delivery while close waits for process shutdown.
            # No wait(event) call is made to trigger presentation.
            connection.process.wait = Mock(side_effect=lambda timeout: connection.read())
            connection.threads = [SimpleNamespace(join=Mock()), SimpleNamespace(join=Mock())]
            with patch('sys.stdout', io.StringIO()) as shown:
                connection.close()
            output = shown.getvalue()
            self.assertIn('LATE_cancel_requested', output)
            self.assertIn('LATE_terminal_unknown', output)
            self.assertIn('parada física no confirmada', output)
            self.assertNotIn('etapa completada', output.lower())
            self.assertEqual((root/'events.jsonl').read_bytes(), raw.encode())
            self.assertEqual([connection.events.get_nowait() for _ in range(2)], events)
            self.assertEqual(connection.events.get_nowait(), {'event': 'eof'})
            self.assertTrue(connection.closed.is_set())
            connection.process.wait.assert_called_once_with(timeout=15)


if __name__ == '__main__':
    unittest.main()
