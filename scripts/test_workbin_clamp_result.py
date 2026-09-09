#!/usr/bin/env python3
"""Prueba offline: medidas plausibles no convierten FAILURE en agarre válido."""
from pathlib import Path
import re
import subprocess
import sys
import unittest

SOURCE = Path(__file__).with_name("cruzr_blue_workbin_cycle.sh").read_text()
FUNCTION = SOURCE.split("verify_clamp_log() {", 1)[1].split("\nconfirm_once()", 1)[0]
MATCH = re.search(r"  python3 -c '\n(.*?)\n' <<<\"\$log_excerpt\"", FUNCTION, re.S)
assert MATCH, "No se encontró el verificador"
CODE = MATCH[1]
# Medidas del fallo real de 2026-09-09, que el verificador anterior aceptaba.
MEASUREMENTS = """__CRUZR_CLAMP_LOG_SEGMENT__
BTree task: 'cruzr/blue_workbin_clamp_only' is start
left_force_base : 4.90499 21.5192 1.5233
left-right-arm tool's distance on base: 0.0380927 0.580225 0.00546197
"""


def ending(result):
    return ("End MetaClamp: clamp_cruzr_byd_large\n"
            "W [meta_node.cpp:97:TickEnd]: meta_name: MetaClamp\n"
            "    action_name: clamp_cruzr_byd_large\n"
            "    result: " + result + "\n" +
            ("BTree tick succeeded\n" if result == "SUCCESS" else ""))


def verify(log):
    return subprocess.run([sys.executable, "-c", CODE], input=log,
                          capture_output=True, text=True, timeout=3)


class ClampResultTests(unittest.TestCase):
    def test_real_failure_with_plausible_measurements_is_rejected(self):
        log = (MEASUREMENTS + "distance_on_float_base.y: 0.581279 > "
               "box size.outside_len: 0.578\nclamp_status: ClampBoxImperfect\n"
               + ending("FAILURE"))
        result = verify(log)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Motion rechazó", result.stderr)

    def test_explicit_failure_is_rejected_even_without_imperfect_marker(self):
        self.assertNotEqual(verify(MEASUREMENTS + ending("FAILURE")).returncode, 0)

    def test_missing_or_unfinished_result_is_rejected(self):
        for tail in ("", ending("RUNNING"), ending("UNKNOWN"),
                     "End MetaClamp: clamp_cruzr_byd_large\n"):
            with self.subTest(tail=tail):
                self.assertNotEqual(verify(MEASUREMENTS + tail).returncode, 0)

    def test_synthetic_complete_success_remains_accepted(self):
        result = verify(MEASUREMENTS + ending("SUCCESS"))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_later_release_invalidates_grasp(self):
        result = verify(MEASUREMENTS + ending("SUCCESS") +
                        "Start MetaClamp: byd/open_arm_cruzr\n")
        self.assertNotEqual(result.returncode, 0)

    def test_failed_latest_clamp_not_replaced_by_earlier_success(self):
        self.assertNotEqual(verify(MEASUREMENTS + ending("SUCCESS") +
                                   ending("FAILURE")).returncode, 0)

    def test_later_unknown_task_or_teleop_invalidates_grasp(self):
        for task in ['unknown', 'teleoperation/cruzr_clamp_pico_teleoperation']:
            log = MEASUREMENTS + ending('SUCCESS') + "BTree task: '%s' is start\n" % task
            self.assertNotEqual(verify(log).returncode, 0)

    def test_success_without_completed_tree_is_rejected(self):
        self.assertNotEqual(verify(MEASUREMENTS + ending('SUCCESS').replace(
            'BTree tick succeeded\n', '')).returncode, 0)

    def test_fault_or_cancellation_after_success_is_rejected(self):
        for event in ['Operation disabled unexpected', 'Self collision between links', 'goal canceled']:
            self.assertNotEqual(verify(MEASUREMENTS + ending('SUCCESS') + event).returncode, 0)

    def test_nonfinite_force_is_rejected(self):
        self.assertNotEqual(verify(MEASUREMENTS.replace('4.90499', '1e999') + ending('SUCCESS')).returncode, 0)


if __name__ == "__main__":
    unittest.main()
