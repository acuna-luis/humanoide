#!/usr/bin/env python3

import importlib.util
import ast
import pathlib
import sys
import unittest


HERE = pathlib.Path(__file__).resolve().parent
MODULE_PATH = HERE / "cruzr_s2_shadow_validator.py"
SPEC = importlib.util.spec_from_file_location("shadow_validator", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ShadowValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = MODULE.load_profile(HERE / "cruzr_s2_vla_profile.json")

    def valid_points(self):
        midpoint = [
            (low + high) / 2.0
            for low, high in zip(self.profile["lower_boundary"], self.profile["upper_boundary"])
        ]
        return [
            {
                "positions": midpoint,
                "velocities": [0.0] * 20,
                "accelerations": [0.0] * 20,
                "effort": [0.0] * 20,
                "time_from_start": index * 0.08,
            }
            for index in range(10)
        ], midpoint

    def test_valid_chunk_is_accepted(self):
        points, state = self.valid_points()
        result = MODULE.validate_chunk_data(
            self.profile,
            chunk_id=1,
            status_code=1,
            inference_time_sec=0.4,
            points=points,
            state_positions=state,
        )
        self.assertTrue(result.accepted, result.reasons)

    def test_wrong_dimension_is_rejected(self):
        points, state = self.valid_points()
        points[3]["positions"] = points[3]["positions"][:-1]
        result = MODULE.validate_chunk_data(
            self.profile,
            chunk_id=2,
            status_code=1,
            inference_time_sec=0.4,
            points=points,
            state_positions=state,
        )
        self.assertFalse(result.accepted)
        self.assertTrue(any("dimension" in reason for reason in result.reasons))

    def test_jump_and_range_are_rejected(self):
        points, state = self.valid_points()
        points[1]["positions"] = list(points[1]["positions"])
        points[1]["positions"][0] = self.profile["upper_boundary"][0] + 1.0
        result = MODULE.validate_chunk_data(
            self.profile,
            chunk_id=3,
            status_code=1,
            inference_time_sec=0.4,
            points=points,
            state_positions=state,
        )
        self.assertFalse(result.accepted)
        self.assertTrue(any("range_violations" in reason for reason in result.reasons))
        self.assertTrue(any("speed_violations" in reason for reason in result.reasons))

    def test_source_has_no_command_publisher(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_names = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        called_attributes = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertNotIn("RobotCommand", imported_names)
        self.assertNotIn("create_publisher", called_attributes)

    def test_inference_adapter_has_no_command_path(self):
        source = (HERE / "cruzr_s2_inference_shadow.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_names = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertNotIn("RobotCommand", imported_names)
        self.assertNotIn("/mc/sdk/robot_command", source)


if __name__ == "__main__":
    unittest.main()
