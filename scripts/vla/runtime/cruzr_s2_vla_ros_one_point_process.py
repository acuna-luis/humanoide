#!/usr/bin/env python3
"""Explicit ROS process for the E6.0 one-point runtime.

The checked-in activation template is disabled.  ``--run`` validates a
run-specific grant and its caller-supplied SHA-256 *before* importing rclpy.
The SDK command publisher is constructed lazily only after READY state and one
valid checkpoint chunk have passed the pure runtime core.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import pathlib
import sys
import time
from typing import Any


def load_module(path: pathlib.Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"json:not_object:{path}")
    return value


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--activation", type=pathlib.Path, required=True)
    parser.add_argument("--expected-activation-sha256")
    parser.add_argument("--runtime", type=pathlib.Path, required=True)
    parser.add_argument("--monitor", type=pathlib.Path, required=True)
    parser.add_argument("--transport", type=pathlib.Path, required=True)
    parser.add_argument("--ros-backend", type=pathlib.Path, required=True)
    parser.add_argument("--monitor-contract", type=pathlib.Path, required=True)
    parser.add_argument("--transport-contract", type=pathlib.Path, required=True)
    parser.add_argument("--limits", type=pathlib.Path, required=True)
    parser.add_argument("--profile", type=pathlib.Path, required=True)
    args = parser.parse_args()
    if args.check == args.run:
        parser.error("indique exactamente uno de --check o --run")
    return args


def normalize_state(message: Any, received: float) -> dict[str, Any]:
    return {
        "schema": "cruzr-s2-vla-normalized-joint-state-e6.0u-v1",
        "source_topic": "/mc/whole_joint_states",
        "sample_time_seconds": received,
        "received_time_seconds": received,
        "joint_names": list(message.name),
        "positions": list(message.position),
        "velocities": list(message.velocity),
    }


def normalize_chunk(message: Any, received: float) -> dict[str, Any]:
    points = []
    for point in message.chunk_points:
        duration = float(point.time_from_start.sec) + float(
            point.time_from_start.nanosec
        ) * 1e-9
        points.append({
            "positions": list(point.positions),
            "time_from_start_seconds": duration,
        })
    return {
        "schema": "cruzr-s2-vla-normalized-checkpoint-chunk-e6.0w-v1",
        "source_topic": "/vla_inference_result",
        "chunk_id": int(message.chunk_id),
        "status_code": int(message.status_code),
        "inference_time_seconds": float(message.inference_time_sec),
        "received_time_seconds": received,
        "points": points,
    }


def main() -> int:
    args = parse_args()
    activation = load_json(args.activation)
    runtime_module = load_module(args.runtime, "e6_0w_process_runtime")
    monitor_module = load_module(args.monitor, "e6_0w_process_monitor")
    transport_module = load_module(args.transport, "e6_0w_process_transport")
    activation = runtime_module.validate_activation_template(activation)
    monitor_contract = monitor_module.load_monitor_contract(args.monitor_contract)
    transport_contract = transport_module.load_transport_contract(args.transport_contract)
    limits = transport_module.load_engineering_limits(args.limits)
    profile = load_json(args.profile)

    if args.check:
        if runtime_module.activation_is_enabled(activation):
            raise SystemExit("ERROR: --check exige una plantilla desactivada")
        print("E6.0W_ROS_PROCESS_CHECK_OK=lazy-publisher,explicit-grant,template-disabled")
        print("E6.0W_SELECTED_STATE_TOPIC=/mc/whole_joint_states")
        print("E6.0W_COMMAND_TOPIC=/mc/sdk/robot_command")
        print("E6.0W_ACTIVE_LAUNCHER_ENABLED=0")
        print("E6.0W_PHYSICAL_AUTHORIZED=0")
        return 0

    # Everything below this point is unreachable with the versioned template.
    # Reject before importing ROS or constructing subscriptions/publishers.
    if not runtime_module.activation_is_enabled(activation):
        print("E6.0W_ACTIVE_LAUNCHER_ENABLED=0", file=sys.stderr)
        print("E6.0W_PHYSICAL_AUTHORIZED=0", file=sys.stderr)
        print("ERROR: falta grant físico run-specific completo", file=sys.stderr)
        return 3
    if not args.expected_activation_sha256:
        print("ERROR: --run exige --expected-activation-sha256", file=sys.stderr)
        return 3
    actual_activation_sha = sha256(args.activation)
    if actual_activation_sha != args.expected_activation_sha256:
        print("ERROR: hash del grant de activación no coincide", file=sys.stderr)
        return 3

    import rclpy
    from rclpy.node import Node
    from rclpy.qos import (
        DurabilityPolicy,
        HistoryPolicy,
        QoSProfile,
        ReliabilityPolicy,
    )
    from sensor_msgs.msg import JointState
    from vla_msgs.msg import Gr00tMotionChunk

    ros_backend_module = load_module(args.ros_backend, "e6_0w_process_ros_backend")

    class CanaryNode(Node):
        def __init__(self) -> None:
            super().__init__("cruzr_s2_vla_e6_0_one_point")
            self.done = False
            self.result_state = "STARTING"
            self.runtime = runtime_module.OnePointCanaryRuntime(
                activation=activation,
                monitor_contract=monitor_contract,
                transport_contract=transport_contract,
                limits=limits,
                profile=profile,
                monitor_type=monitor_module,
                transport_type=transport_module,
                backend_factory=lambda: ros_backend_module.RosSdkRobotCommandBackend(self),
            )
            state_qos = QoSProfile(
                reliability=ReliabilityPolicy.RELIABLE,
                history=HistoryPolicy.KEEP_LAST,
                depth=4,
                durability=DurabilityPolicy.VOLATILE,
            )
            chunk_qos = QoSProfile(
                reliability=ReliabilityPolicy.BEST_EFFORT,
                history=HistoryPolicy.KEEP_LAST,
                depth=10,
                durability=DurabilityPolicy.VOLATILE,
            )
            self.state_subscription = self.create_subscription(
                JointState,
                activation["selected_state_topic"],
                self.state_callback,
                state_qos,
            )
            self.chunk_subscription = self.create_subscription(
                Gr00tMotionChunk,
                activation["chunk_topic"],
                self.chunk_callback,
                chunk_qos,
            )
            self.timer = self.create_timer(
                float(limits["sample_period_seconds"]), self.timer_callback
            )
            self.get_logger().info(
                "E6.0W activo: esperando READY fresco y un solo chunk task 0"
            )

        def record(self, decision: Any) -> None:
            payload = json.dumps(decision.as_dict(), sort_keys=True)
            if decision.accepted:
                self.get_logger().info(payload)
            else:
                self.get_logger().error(payload)
            if decision.state in {"FAULTED", "COMPLETED", "STOPPED"}:
                self.result_state = decision.state
                self.done = True

        def state_callback(self, message: Any) -> None:
            now = time.monotonic()
            self.record(self.runtime.receive_state(
                normalize_state(message, now), now_seconds=now
            ))

        def chunk_callback(self, message: Any) -> None:
            now = time.monotonic()
            self.record(self.runtime.receive_chunk(
                normalize_chunk(message, now), now_seconds=now
            ))

        def timer_callback(self) -> None:
            if self.runtime.state == "DISPATCHING_ONE_POINT":
                self.record(self.runtime.tick(now_seconds=time.monotonic()))

        def stop_runtime(self) -> None:
            terminal_result = self.result_state
            decision = self.runtime.stop()
            if terminal_result not in {"COMPLETED", "FAULTED"}:
                self.result_state = decision.state
            self.done = True

    rclpy.init(args=None)
    node = CanaryNode()
    exit_code = 1
    try:
        while rclpy.ok() and not node.done:
            rclpy.spin_once(node, timeout_sec=0.05)
        exit_code = 0 if node.result_state == "COMPLETED" else 1
    except KeyboardInterrupt:
        node.stop_runtime()
        exit_code = 130
    finally:
        node.stop_runtime()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    print(f"E6.0W_FINAL_STATE={node.result_state}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
