#!/usr/bin/env python3
"""Regresión de visión MESAS2; ejecuta sólo validadores Python, sin ROS/SSH."""
import math
from pathlib import Path
import re
import subprocess
import sys
import unittest


SOURCE = Path(__file__).with_name("cruzr_blue_workbin_cycle.sh").read_text()
# Consulta perceptiva 2026-09-09, caja visible en detector_segment.png.
OBSERVED = (0.164391, 0.050471, 1.730504,
            0.8516812476, -0.0132420061, 0.0081721306, 0.5238290924)


def validate(function, samples):
    match = re.search(r"^" + function + r"\(\) \{\n  python3 .*?<<'PY'\n(.*?)\nPY\n\}",
                      SOURCE, re.MULTILINE | re.DOTALL)
    if match is None:
        raise AssertionError("No se encontró el validador " + function)
    return subprocess.run([sys.executable, "-c", match[1],
                           *(" ".join(map(str, sample)) for sample in samples)],
                          capture_output=True, text=True, timeout=3)


def pose(**changes):
    values = dict(zip(("x", "y", "z", "qx", "qy", "qz", "qw"), OBSERVED))
    values.update(changes)
    return tuple(values.values())


class ApproachWindowTests(unittest.TestCase):
    def approach(self, sample, accepted):
        result = validate("validate_approach_samples", [sample, sample])
        self.assertEqual(result.returncode == 0, accepted, result.stderr)

    def test_observed_mesas2_pair_is_admitted_for_approach(self):
        self.approach(OBSERVED, True)

    def test_far_window_remains_bounded(self):
        for changes, accepted in [({"y": 0}, True), ({"y": -0.001}, False),
                                  ({"y": 1.101}, False), ({"z": 1.801}, False),
                                  ({"x": 0.551}, False)]:
            with self.subTest(changes=changes):
                self.approach(pose(**changes), accepted)

    def test_near_window_keeps_previous_minimum(self):
        for changes, accepted in [({"z": 1.15}, False),
                                  ({"z": 1.15, "y": 0.10}, True),
                                  ({"z": 0.966, "y": 0.099}, False),
                                  ({"z": 0.649, "y": 0.3}, False)]:
            with self.subTest(changes=changes):
                self.approach(pose(**changes), accepted)

    def test_nonfinite_pose_is_rejected(self):
        for name in ("x", "y", "z", "qx", "qy", "qz", "qw"):
            for value in (math.nan, math.inf, -math.inf):
                with self.subTest(name=name, value=value):
                    self.approach(pose(**{name: value}), False)

    def test_unstable_pair_still_rejected(self):
        result = validate("validate_approach_samples", [OBSERVED, pose(x=0.20)])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("inestable", result.stderr)

    def test_invalid_quaternion_still_rejected(self):
        self.approach(pose(qw=2), False)

    def test_approach_admission_does_not_authorize_grasp(self):
        for sample in (OBSERVED, pose(x=0, z=0.966)):
            result = validate("validate_detection_samples", [sample, sample])
            self.assertNotEqual(result.returncode, 0)

    def test_previous_grasp_window_still_works(self):
        sample = pose(x=0, y=0.3, z=0.966)
        result = validate("validate_detection_samples", [sample, sample])
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
