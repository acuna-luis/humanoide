#!/usr/bin/env python3
"""Offline tests of the standalone release command and its dispatch guards."""
from pathlib import Path
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS / "lib"))
from cruzr_open_only_gate import classify_context


class OpenOnlyTests(unittest.TestCase):
    def context(self, **changes):
        data = dict(writers=0, unsafe_event=False,
                    last_task="cruzr/blue_workbin_clamp_only")
        data.update(changes)
        return data

    def test_workbin_context_does_not_require_successful_grip(self):
        self.assertEqual(classify_context(self.context()), "clamp")

    def test_already_attempted_release_is_not_repeated(self):
        self.assertEqual(classify_context(self.context(
            last_task="cruzr/blue_workbin_open_only")), "already_attempted")

    def test_unknown_home_and_pico_contexts_are_rejected(self):
        for task in (None, "", "cruzr/home", "teleoperation/cruzr_clamp_pico_teleoperation"):
            with self.subTest(task=task), self.assertRaises(ValueError):
                classify_context(self.context(last_task=task))

    def test_concurrent_or_unknown_writers_are_rejected(self):
        for writers in (1, None, "0", False):
            with self.subTest(writers=writers), self.assertRaises(ValueError):
                classify_context(self.context(writers=writers))

    def test_unsafe_and_unknown_event_status_are_rejected(self):
        for value in (True, None, 0):
            with self.subTest(value=value), self.assertRaises(ValueError):
                classify_context(self.context(unsafe_event=value))

    def test_missing_fields_are_rejected(self):
        for field in self.context():
            data = self.context()
            del data[field]
            with self.subTest(field=field), self.assertRaises(ValueError):
                classify_context(data)

    def test_template_only_opens(self):
        root = ET.parse(SCRIPTS / "custom_tasks/test_blue_workbin_factory_open_only.xml")
        self.assertEqual([a.attrib for a in root.iter("Action")],
                         [{"ID": "MetaClamp", "name": "byd/open_arm_cruzr"}])

    def test_docker_timestamp_is_normalized_for_robot_python(self):
        import datetime
        import re
        from types import SimpleNamespace
        source = (SCRIPTS / "cruzr_blue_workbin_cycle.sh").read_text()
        snippet = re.search(r"^stamp = re.sub.*\nstarted = .*", source, re.M)[0]
        env = dict(datetime=datetime, re=re,
                   sys=SimpleNamespace(argv=["-", "2026-09-09T05:21:42.186913053Z"]))
        exec(snippet, env)
        self.assertEqual(env["stamp"], "2026-09-09T05:21:42.186913Z")
        self.assertAlmostEqual(env["started"], 1788931302.186913, places=5)

    def test_cli_rejects_bypass_flags_without_connecting(self):
        for script, args in (
            ("cruzr_blue_workbin_open_only.sh", ["--yes"]),
            ("cruzr_blue_workbin_open_only.sh", ["--run", "--fast"]),
            ("cruzr_blue_workbin_cycle.sh", ["--open-only", "--yes"]),
            ("cruzr_blue_workbin_cycle.sh", ["--check-open-only", "--fast"]),
        ):
            result = subprocess.run([str(SCRIPTS / script), *args],
                                    capture_output=True, text=True, timeout=3)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("Conexión:", result.stdout)

    def test_noninteractive_run_is_rejected_without_connecting(self):
        result = subprocess.run([str(SCRIPTS / "cruzr_blue_workbin_open_only.sh"), "--run"],
                                input="ABRIR ABRAZADERAS\n", capture_output=True,
                                text=True, timeout=3)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("terminal interactiva", result.stderr)
        self.assertNotIn("Conexión:", result.stdout)

    def run_dispatch(self, context, mode, execution=False, fail_goal=False,
                     fail_refresh=False, answer="ABRIR ABRAZADERAS\n"):
        # Parse the real functions, replacing only the final entry point.
        # All network, installers and physical-action functions become mocks.
        source = (SCRIPTS / "cruzr_blue_workbin_cycle.sh").read_text()
        prefix, last = source.rsplit("\nmain\n", 1)
        self.assertEqual(last, "")
        mocks = """
check_open_only_actuators() { echo MOCK_ACTUATORS; }
open_only_context() { echo "$TEST_CONTEXT"; }
remote_preflight() { echo MOCK_PREFLIGHT; }
install_one_template() { echo UNEXPECTED_INSTALL; exit 91; }
run_motion_task() { echo UNEXPECTED_MOTION; exit 92; }
"""
        if execution:
            mocks += """
install_one_template() { echo MOCK_INSTALL; }
remote_preflight() { echo MOCK_REFRESH; if [[ "$TEST_FAIL_REFRESH" == 1 ]]; then exit 93; fi; }
run_motion_task() { echo "MOCK_GOAL=$1"; [[ "$TEST_FAIL_GOAL" != 1 ]]; }
"""
        mocks += """
MODE="$TEST_MODE"
run_open_only
"""
        import os
        env = dict(os.environ, TEST_CONTEXT=context, TEST_MODE=mode,
                   TEST_FAIL_GOAL=str(int(fail_goal)),
                   TEST_FAIL_REFRESH=str(int(fail_refresh)))
        return subprocess.run(["bash", "-c", prefix + mocks,
                               str(SCRIPTS / "cruzr_blue_workbin_cycle.sh")],
                              env=env, input=answer, capture_output=True, text=True, timeout=3)

    def test_check_does_not_install_or_move(self):
        result = self.run_dispatch("clamp", "check-open-only")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("OPEN_ONLY_CHECK_OK", result.stdout)
        self.assertNotIn("UNEXPECTED_", result.stdout)

    def test_run_does_not_repeat_prior_open_attempt(self):
        result = self.run_dispatch("already_attempted", "open-only")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("OPEN_ONLY_NO_ACTION", result.stdout)
        self.assertNotIn("UNEXPECTED_", result.stdout)

    def test_confirmed_run_dispatches_only_one_open_goal(self):
        result = self.run_dispatch("clamp", "open-only", execution=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        goals = [s for s in result.stdout.splitlines() if s.startswith("MOCK_GOAL=")]
        self.assertEqual(goals, ["MOCK_GOAL=cruzr/blue_workbin_open_only"])
        self.assertIn("OPEN_ONLY_SUCCEEDED", result.stdout)

    def test_failed_goal_is_not_retried(self):
        result = self.run_dispatch("clamp", "open-only", execution=True, fail_goal=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout.count("MOCK_GOAL="), 1)
        self.assertNotIn("OPEN_ONLY_SUCCEEDED", result.stdout)

    def test_changed_health_blocks_dispatch_after_confirmation(self):
        result = self.run_dispatch("clamp", "open-only", execution=True, fail_refresh=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("MOCK_GOAL=", result.stdout)

    def test_cancelled_confirmation_does_not_dispatch(self):
        result = self.run_dispatch("clamp", "open-only", execution=True, answer="no\n")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("MOCK_GOAL=", result.stdout)


if __name__ == "__main__":
    unittest.main()
