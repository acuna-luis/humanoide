#!/usr/bin/env python3

import ast
import importlib.util
import pathlib
import sys
import unittest


HERE = pathlib.Path(__file__).resolve().parent
MODULE_PATH = HERE / "vla_executor_sink.py"
SPEC = importlib.util.spec_from_file_location("vla_executor_sink_tested", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class VlaExecutorSinkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = MODULE.load_profile(HERE / "cruzr_s2_vla_profile.json")

    def sink(self, axis_profile="P20_AHLW"):
        sink = MODULE.VlaExecutorSink(
            profile=self.profile,
            axis_profile=axis_profile,
            fixture="low",
            runtime_id="test-runtime",
            checkpoint_id="test-checkpoint",
        )
        self.assertTrue(sink.acquire_client("test-client").accepted)
        self.assertTrue(sink.refresh_deadman("test-client", 100.0).accepted)
        return sink

    def test_valid_chunk_and_all_axis_profile_sizes(self):
        for name in MODULE.AXIS_PROFILES:
            with self.subTest(name=name):
                sink = self.sink(name)
                expected = int(name[1:3])
                self.assertEqual(len(sink.enabled), expected)
                message = MODULE.valid_message(sink, chunk_id=1, now=100.0)
                result = sink.submit(message, now=100.0)
                self.assertTrue(result.accepted, result.reasons)
                self.assertEqual(len(result.command["effective_points"]), 10)
                self.assertEqual(len(result.command["effective_points"][0]), 20)
                self.assertEqual(result.command["physical_publisher_count"], 0)

    def test_locked_axes_hold_nonzero_fixture_pose(self):
        sink = self.sink("P14_A")
        message = MODULE.valid_message(sink, chunk_id=1, now=100.0)
        for point in message["points"]:
            point["positions"][0] += 0.01
            point["positions"][14] += 0.01
        result = sink.submit(message, now=100.0)
        self.assertTrue(result.accepted, result.reasons)
        self.assertAlmostEqual(result.command["effective_points"][0][0], sink.hold_state[0] + 0.01)
        self.assertAlmostEqual(result.command["effective_points"][0][14], sink.hold_state[14])
        self.assertNotEqual(sink.hold_state[14], 0.0)

    def test_invalid_chunk_does_not_consume_sequence_id(self):
        sink = self.sink()
        invalid = MODULE.valid_message(sink, chunk_id=1, now=100.0)
        invalid["runtime_id"] = "wrong"
        self.assertFalse(sink.submit(invalid, now=100.0).accepted)
        valid = MODULE.valid_message(sink, chunk_id=1, now=100.0)
        self.assertTrue(sink.submit(valid, now=100.0).accepted)

    def test_nan_and_wrong_order_are_rejected(self):
        sink = self.sink()
        message = MODULE.valid_message(sink, chunk_id=1, now=100.0)
        message["points"][0]["positions"][0] = float("nan")
        message["joint_names"][0:2] = reversed(message["joint_names"][0:2])
        result = sink.submit(message, now=100.0)
        self.assertFalse(result.accepted)
        self.assertTrue(any("non_finite" in reason for reason in result.reasons))
        self.assertIn("joint_names:order_or_membership_mismatch", result.reasons)

    def test_duplicate_regressive_and_second_client_are_rejected(self):
        sink = self.sink()
        self.assertFalse(sink.acquire_client("second").accepted)
        self.assertTrue(sink.submit(MODULE.valid_message(sink, chunk_id=5, now=100.0), now=100.0).accepted)
        self.assertFalse(sink.submit(MODULE.valid_message(sink, chunk_id=5, now=100.0), now=100.0).accepted)
        self.assertFalse(sink.submit(MODULE.valid_message(sink, chunk_id=4, now=100.0), now=100.0).accepted)

    def test_cancel_and_stop_are_idempotent_and_latched(self):
        canceled = self.sink()
        self.assertTrue(canceled.cancel("test-client").accepted)
        self.assertTrue(canceled.cancel("test-client").accepted)
        self.assertFalse(
            canceled.submit(MODULE.valid_message(canceled, chunk_id=1, now=100.0), now=100.0).accepted
        )
        stopped = self.sink()
        self.assertTrue(stopped.stop().accepted)
        self.assertTrue(stopped.stop().accepted)
        self.assertFalse(
            stopped.submit(MODULE.valid_message(stopped, chunk_id=1, now=100.0), now=100.0).accepted
        )

    def test_deadman_timeout_latches_stop(self):
        sink = self.sink()
        decision = sink.poll(100.51)
        self.assertFalse(decision.accepted)
        self.assertTrue(sink.stopped)
        self.assertEqual(decision.reasons, ["deadman:timeout_stop_latched"])

    def test_source_has_no_ros_network_or_publisher_api(self):
        tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
        imports = set()
        called = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                called.add(node.func.attr)
        self.assertFalse(imports & {"rclpy", "rosa", "socket", "requests", "subprocess", "urllib"})
        self.assertFalse(called & {"create_publisher", "publish", "send_goal_async"})
        self.assertNotIn("/mc/sdk/robot_command", MODULE_PATH.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
