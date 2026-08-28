#!/usr/bin/env python3
"""Standard-library tests for E3.1 selection and proxy definitions."""

from __future__ import annotations

import importlib.util
import pathlib
import unittest


SCRIPT = pathlib.Path(__file__).parents[1] / "evaluate_vla_ood_e3_1.py"
SPEC = importlib.util.spec_from_file_location("evaluate_vla_ood_e3_1", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class OodProxyDefinitionTests(unittest.TestCase):
    def test_proxy_grid_has_twenty_six_variants(self) -> None:
        per_task = sum(len(axis["values"]) for axis in MODULE.PROXY_AXES)
        self.assertEqual(per_task, 13)
        self.assertEqual(per_task * len(MODULE.TASK_IDS), 26)

    def test_each_axis_has_exactly_one_nominal(self) -> None:
        for axis in MODULE.PROXY_AXES:
            self.assertEqual(axis["values"].count(axis["nominal"]), 1)

    def test_proxy_units_do_not_claim_metric_scene_geometry(self) -> None:
        units = {axis["units"] for axis in MODULE.PROXY_AXES}
        self.assertNotIn("metres", units)
        self.assertNotIn("object_yaw_degrees", units)
        self.assertTrue(all("not" in axis["interpretation"] for axis in MODULE.PROXY_AXES))

    def test_sample_ids_are_unique(self) -> None:
        identifiers = {
            MODULE._sample_id(task_id, axis_index, value_index)
            for task_id in MODULE.TASK_IDS
            for axis_index, axis in enumerate(MODULE.PROXY_AXES)
            for value_index, _ in enumerate(axis["values"])
        }
        self.assertEqual(len(identifiers), 26)


if __name__ == "__main__":
    unittest.main()
