"""Optional Docker diagnostics never replace native terminals or live guards."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.box_handling import scenario1_console as console
from scripts.box_handling import scenario1_table74_recipe as recipe
from scripts.box_handling import scenario1_table74_trial_run as trial
from scripts.box_handling.test_scenario1_table74_current_lower import bundle
from scripts.box_handling.test_scenario1_table74_native_completion import log


def success():
    return dict(event='result', goal_id='48339049-920e-4c9b-9762-7774f92c3621',
        status=4, result=dict(state=dict(desc='SUCCEED', state=1101001)))


class FeriaLogAuditTests(unittest.TestCase):
    def machine(self, root):
        runtime = trial.TrialRuntime.__new__(trial.TrialRuntime)
        runtime.session = root
        runtime.native_container = 'pinned-test-container'
        runtime.trial_bundle = bundle()
        runtime.emit = Mock()
        runtime.connected = Mock()
        return runtime

    def test_real_docker_json_log_reader_error_is_archived_and_inconclusive(self):
        text = "Error grabbing logs: invalid character '\\x00' looking for beginning of value\n"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); runtime = self.machine(root)
            response = Mock(returncode=0, stdout=text)
            with patch.object(trial.subprocess, 'run', return_value=response) as command:
                runtime.audit_native_completion(1000000001, success())
            command.assert_called_once()
            self.assertEqual(command.call_args.kwargs['timeout'], 2)
            self.assertEqual(command.call_args.args[0][-1], 'pinned-test-container')
            capture = json.loads((root/'native-log-capture.json').read_text())
            self.assertEqual(capture['log'], text)
            calls = runtime.emit.call_args_list
            self.assertEqual(calls[0].args, ('table74_native_log_capture',))
            report = calls[-1].kwargs
            self.assertEqual(calls[-1].args, ('table74_native_completion',))
            self.assertIs(report['verified'], False)
            self.assertEqual(report['diagnostic_status'], 'unavailable')
            self.assertIs(report['execution_result_validated'], True)
            self.assertEqual(report['goal_id'], success()['goal_id'])
            runtime.connected.assert_called_once()

    def test_timeout_is_bounded_diagnostic_and_preserves_partial_text(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); runtime = self.machine(root)
            with patch.object(trial.subprocess, 'run', side_effect=subprocess.TimeoutExpired('docker', 2, output=b'partial log')):
                runtime.audit_native_completion(1, success())
            self.assertEqual(json.loads((root/'native-log-capture.json').read_text())['log'], 'partial log')
            self.assertIs(runtime.emit.call_args.kwargs['verified'], False)

    def test_force_failure_is_archived_before_rejection_and_never_becomes_a_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); runtime = self.machine(root)
            text = log(runtime.trial_bundle)+'\nDectionForceCollision\n'
            with patch.object(trial.subprocess, 'run', return_value=Mock(returncode=0, stdout=text)):
                with self.assertRaisesRegex(ValueError, 'NATIVE_FAULT'):
                    runtime.audit_native_completion(1, success())
            self.assertEqual(json.loads((root/'native-log-capture.json').read_text())['log'], text)
            self.assertFalse(any(call.args == ('table74_native_completion',) for call in runtime.emit.call_args_list))

    def test_programming_errors_are_not_reclassified_as_an_optional_log(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = self.machine(Path(directory))
            with patch.object(trial.subprocess, 'run', side_effect=TypeError('programming error')):
                with self.assertRaisesRegex(TypeError, 'programming error'):
                    runtime.audit_native_completion(1, success())


class FeriaCompletionPolicyTests(unittest.TestCase):
    def test_identified_success_with_explicit_inconclusive_audit_is_accepted_honestly(self):
        event = dict(event='table74_native_completion', verified=False, diagnostic_status='unavailable',
            guard_policy='feria_native_terminal_v1', critical_fault_observed=False,
            execution_result_validated=True, goal_id=success()['goal_id'], bundle_id='bundle')
        journal = dict(phase='succeeded', bundle_id='bundle', result=success())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def put(row, record):
                (root/'events.jsonl').write_text(json.dumps(row)+'\n')
                (root/'trial.json').write_text(json.dumps(record))
            put(event, journal)
            self.assertIs(recipe.RecipePolicy.from_default().validate_completion(root, root)['verified'], False)
            for mutation in ('fault', 'status', 'state', 'uuid', 'policy', 'result_checked'):
                row, record = copy.deepcopy(event), copy.deepcopy(journal)
                if mutation == 'fault': row['critical_fault_observed'] = True
                elif mutation == 'status': record['result']['status'] = 6
                elif mutation == 'state': record['result']['result']['state']['state'] = 7104050
                elif mutation == 'uuid': row['goal_id'] = 'another-goal'
                elif mutation == 'policy': row['guard_policy'] = 'ignore-all-faults'
                else: row['execution_result_validated'] = False
                put(row, record)
                with self.subTest(mutation=mutation), self.assertRaises((ValueError, RuntimeError)):
                    recipe.RecipePolicy.from_default().validate_completion(root, root)

    def test_optional_diagnostic_is_presented_without_hiding_other_errors(self):
        reporter = console.ConsoleReporter()
        event = dict(event='table74_native_completion', verified=False, diagnostic_status='inconclusive')
        line = reporter.render(event)
        self.assertTrue(any('Registro Docker no concluyente' in item for item in line))
        self.assertTrue(any('ERROR' in item for item in reporter.render(dict(event='error', reason='force fault'))))


if __name__ == '__main__':
    unittest.main()
