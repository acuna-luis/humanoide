"""Execute transient lease runners locally, without ROS, network or a robot."""
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

from scripts.box_handling.scenario1_cycle_lease import adapter_runner_source


ADAPTER = '''\
import argparse
import json
from pathlib import Path
import sys
import time
from front_sps_contract import select_report
from cycle_test_bridge import started, iteration, cleaned

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--session', required=True, type=Path)
    args = parser.parse_args()
    started(__name__, __file__, list(sys.argv), select_report)
    deadline = json.loads((args.session/'lease.json').read_text())['deadline']
    try:
        while time.monotonic() < deadline and not (args.session/'stop').exists():
            iteration()
    finally:
        cleaned()

if __name__ == '__main__':
    main()
'''


class CycleLeaseTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='cycle_lease_')
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.session = self.root/'session'
        self.session.mkdir()
        self.script = self.root/'front_sps_native.py'
        self.script.write_text(ADAPTER)
        self.now = 100.
        self.lease(102.)
        self.bridge = types.ModuleType('cycle_test_bridge')
        self.bridge.started = Mock()
        self.bridge.iteration = Mock()
        self.bridge.cleaned = Mock()
        self.contract = types.ModuleType('front_sps_contract')
        self.contract.select_report = object()

    def lease(self, deadline):
        (self.session/'lease.json').write_text(json.dumps(dict(deadline=deadline)))

    def execute(self):
        source = adapter_runner_source(self.script, self.session)
        with patch.dict(sys.modules, {'front_sps_contract': self.contract,
                                      'cycle_test_bridge': self.bridge}), \
                patch.object(sys, 'path', list(sys.path)), \
                patch.object(sys, 'argv', [str(self.script), '--session', str(self.session)]), \
                patch('time.monotonic', side_effect=lambda: self.now):
            exec(compile(source, 'cycle-runner', 'exec'), {})

    def test_deadline_renewal_extends_original_deadline_without_changing_script(self):
        before = self.script.read_bytes()

        def iteration():
            self.now += 1
            if self.now == 101:
                self.lease(104.)

        self.bridge.iteration.side_effect = iteration
        self.execute()
        self.assertEqual(self.bridge.iteration.call_count, 4)
        self.bridge.cleaned.assert_called_once_with()
        self.assertEqual(self.script.read_bytes(), before)

    def test_wrapper_argv_main_file_and_contract_monkeypatch_survive(self):
        self.bridge.iteration.side_effect = lambda: setattr(self, 'now', 102.)
        self.execute()
        self.bridge.started.assert_called_once_with(
            '__main__', str(self.script),
            [str(self.script), '--session', str(self.session)],
            self.contract.select_report)

    def test_expiry_performs_original_cleanup_without_an_iteration(self):
        for deadline in (100., 99., 0.):
            with self.subTest(deadline=deadline):
                self.bridge.cleaned.reset_mock()
                self.lease(deadline)
                self.execute()
                self.bridge.iteration.assert_not_called()
                self.bridge.cleaned.assert_called_once_with()

    def test_stop_ends_loop_even_if_lease_is_renewed(self):
        def iteration():
            (self.session/'stop').touch()
            self.lease(1000.)

        self.bridge.iteration.side_effect = iteration
        self.execute()
        self.bridge.iteration.assert_called_once_with()
        self.bridge.cleaned.assert_called_once_with()

    def test_expiry_cannot_be_revived_within_adapter_process(self):
        # Expose the predicate only in this fake adapter to exercise its latch.
        self.script.write_text(ADAPTER + '\nfrom cycle_test_bridge import predicate\n'
                               'predicate(_scenario1_cycle_lease_valid)\n')
        self.bridge.predicate = Mock()
        self.bridge.iteration.side_effect = lambda: setattr(self, 'now', 102.)
        self.execute()
        predicate = self.bridge.predicate.call_args.args[0]
        self.lease(1000.)
        with patch('time.monotonic', return_value=102.):
            self.assertFalse(predicate())

    def test_invalid_lease_cannot_be_revived_after_exception_is_caught(self):
        self.script.write_text(ADAPTER.replace(
            '        cleaned()',
            '        from cycle_test_bridge import predicate\n'
            '        predicate(_scenario1_cycle_lease_valid)\n'
            '        cleaned()'))
        self.bridge.predicate = Mock()
        self.bridge.iteration.side_effect = lambda: self.lease(True)
        with self.assertRaisesRegex(RuntimeError, 'SPS_SESSION_LEASE_INVALID'):
            self.execute()
        predicate = self.bridge.predicate.call_args.args[0]
        self.lease(1000.)
        with patch('time.monotonic', return_value=100.):
            self.assertFalse(predicate())

    def test_invalid_lease_during_run_fails_and_runs_original_cleanup(self):
        invalid = [True, False, None, '105', {}, [], float('nan'), float('inf'),
                   float('-inf'), 10**400, 1000.5001]
        for deadline in invalid:
            with self.subTest(deadline=deadline):
                self.lease(102.)
                self.bridge.iteration.reset_mock()
                self.bridge.cleaned.reset_mock()
                self.bridge.iteration.side_effect = lambda value=deadline: self.lease(value)
                with self.assertRaisesRegex(RuntimeError, 'SPS_SESSION_LEASE_INVALID'):
                    self.execute()
                self.bridge.iteration.assert_called_once_with()
                self.bridge.cleaned.assert_called_once_with()

    def test_corrupt_or_missing_lease_fails_closed(self):
        path = self.session/'lease.json'
        for contents in ('not JSON', '[]', '{}', '{"deadline":105,"extra":1}', None):
            with self.subTest(contents=contents):
                self.lease(102.)
                self.bridge.iteration.reset_mock()
                self.bridge.cleaned.reset_mock()

                def corrupt(value=contents):
                    if value is None:
                        path.unlink()
                    else:
                        path.write_text(value)

                self.bridge.iteration.side_effect = corrupt
                with self.assertRaisesRegex(RuntimeError, 'SPS_SESSION_LEASE_INVALID'):
                    self.execute()
                self.bridge.iteration.assert_called_once_with()
                self.bridge.cleaned.assert_called_once_with()

    def test_future_deadline_is_bounded_with_only_half_second_tolerance(self):
        self.lease(1000.5)
        self.bridge.iteration.side_effect = lambda: (self.session/'stop').touch()
        self.execute()
        self.bridge.iteration.assert_called_once_with()

    def test_unexpected_script_rejected_before_running_any_adapter_code(self):
        for source in (
                ADAPTER.replace('time.monotonic() < deadline', 'True'),
                ADAPTER + '\n# time.monotonic() < deadline\n',
                '# time.monotonic() < deadline\n',
                'if time.monotonic() < deadline:\n    pass\n',
                'while True:\n    ready = time.monotonic() < deadline\n    break\n'):
            with self.subTest(source=source):
                self.script.write_text(source)
                with self.assertRaisesRegex(RuntimeError, 'SPS_CYCLE_ADAPTER_SOURCE_CHANGED'):
                    self.execute()
                self.bridge.started.assert_not_called()

    def test_adapter_directory_is_available_for_import_without_replacing_existing_modules(self):
        (self.root/'cycle_sibling.py').write_text('VALUE = 7\n')
        self.script.write_text(ADAPTER + '\nfrom cycle_sibling import VALUE\nassert VALUE == 7\n')
        self.bridge.iteration.side_effect = lambda: setattr(self, 'now', 102.)
        try:
            self.execute()
        finally:
            sys.modules.pop('cycle_sibling', None)

    def test_generated_source_handles_quotes_and_template_names_in_paths(self):
        self.script = self.root/"SCRIPT_PATH ' SESSION_PATH.py"
        self.script.write_text(ADAPTER)
        self.bridge.iteration.side_effect = lambda: setattr(self, 'now', 102.)
        self.execute()
        self.assertEqual(self.bridge.started.call_args.args[1], str(self.script))

    def test_real_adapter_sources_each_have_one_outer_lease_condition(self):
        # This is a compatibility assertion, never an import or ROS execution.
        import ast
        for name in ('front_sps_worker.py', 'front_sps_native.py'):
            with self.subTest(name=name):
                source = Path(__file__).with_name(name).read_text()
                self.assertEqual(source.count('time.monotonic() < deadline'), 1)
                changed = source.replace('time.monotonic() < deadline',
                                         '_scenario1_cycle_lease_valid()', 1)
                ast.parse(changed)
                self.assertIn("args.session/'stop'", changed)


if __name__ == '__main__':
    unittest.main()
