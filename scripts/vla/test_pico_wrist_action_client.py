"""Offline checks of isolated VLA lease time and client provenance."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import pico_wrist_action_client as action
import run_pico_wrist_native_trial as trial
import check_pico_wrist_full_passive as passive
import check_arm_native_bridge_live as bridge_check
import verified_pico_wrist_pc_loader as loader


class LeaseFreshnessTests(unittest.TestCase):
    def test_clock_is_sampled_after_read_and_at_expiry_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'lease.json'
            path.write_text('{"deadline":1}')
            now = [0.0]
            original = Path.read_text
            def delayed_read(file, *args, **kwargs):
                raw = original(file, *args, **kwargs)
                if file == path: now[0] = 1.0
                return raw
            with patch.object(Path, 'read_text', delayed_read):
                with self.assertRaisesRegex(RuntimeError, 'expired'):
                    action.check_lease_current(path, lambda: now[0])
            now[0] = .5
            action.check_lease_current(path, lambda: now[0])

    def test_invalid_clock_and_deadline_and_missing_file_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'lease.json'
            path.write_text('{"deadline":2}')
            for value in (True, float('nan'), float('inf'), '1'):
                with self.subTest(value=value), self.assertRaises(RuntimeError):
                    action.check_lease_current(path, lambda: value)
            with self.assertRaises(ValueError):
                action.check_lease_current(path, 1)
            for raw in ('{"deadline":true}', '{"deadline":"2"}', '{}'):
                path.write_text(raw)
                with self.subTest(raw=raw), self.assertRaises(RuntimeError):
                    action.check_lease_current(path, lambda: 1)
            path.unlink()
            with self.assertRaises(FileNotFoundError):
                action.check_lease_current(path, lambda: 1)
            action.check_lease_current(None, lambda: 1)

    def test_client_direct_execution_has_no_dispatch(self):
        process = subprocess.run([sys.executable, '-B', str(Path(action.__file__))],
                                 text=True, capture_output=True, timeout=3)
        self.assertEqual(process.returncode, 2)
        self.assertIn('BLOCKED', process.stderr)


class SourceIsolationTests(unittest.TestCase):
    def test_host_worker_and_passive_sources_use_exact_vla_client(self):
        host, guard, worker, sources = trial.source_bundle(include_sources=True)
        source, path = sources['pico_wrist_action_client']
        self.assertEqual(Path(path), Path(action.__file__))
        self.assertEqual(source, Path(action.__file__).read_text())
        self.assertNotIn('scenario1_action_client', sources)
        self.assertIn(repr(source), host)
        self.assertIn(repr(source), worker)
        self.assertEqual(loader.BUNDLE_PATHS['pico_wrist_action_client'],
                         'scripts/vla/pico_wrist_action_client.py')
        self.assertNotIn('scenario1_action_client', loader.BUNDLE_PATHS)
        self.assertIn('pico_wrist_action_client', passive.source_bundle()[3])
        self.assertIn('pico_wrist_action_client', bridge_check.source_bundle()[2])

    def test_original_client_suite_against_vla_fork(self):
        import test_scenario1_action_client as fixtures
        prior = fixtures.action
        try:
            fixtures.action = action
            suite = unittest.defaultTestLoader.loadTestsFromModule(fixtures)
            result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
            self.assertEqual(result.testsRun, 38)
            self.assertTrue(result.wasSuccessful(), result.errors + result.failures)
        finally:
            fixtures.action = prior

    def test_remote_bundle_imports_isolated_client_without_network(self):
        _, _, _, sources = trial.source_bundle(include_sources=True)
        script = bridge_check.module_code(sources) + '''
assert 'scenario1_action_client' not in sys.modules
client = sys.modules['pico_wrist_action_client']
assert sys.modules['arm_native_lease_bridge'].native is client
assert sys.modules['pico_wrist_native_worker'].native is client
assert sys.modules['pico_wrist_native_coordinator'].native is client
assert sys.modules['pico_wrist_docker_launcher'].native is client
print('VLA_MODULES_ISOLATED')
'''
        result = subprocess.run([sys.executable, '-I', '-B', '-'], input=script,
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('VLA_MODULES_ISOLATED', result.stdout)


if __name__ == '__main__':
    unittest.main()
