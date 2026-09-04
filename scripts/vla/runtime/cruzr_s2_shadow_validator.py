#!/usr/bin/env python3
"""Read-only validator for the UBTECH Cruzr S2 GR00T motion chunks.

This process deliberately does not import RobotCommand, create a publisher, or
send an action goal.  It can therefore inspect VLA output while leaving the
physical command path absent.  Active control belongs in a separate, reviewed
program after shadow validation has passed.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence


COMMAND_TOPIC = "/mc/sdk/robot_command"
CHUNK_TOPIC = "/vla_inference_result"
STATE_TOPIC = "/mc/sdk/robot_state"
STATE_FALLBACK_TOPIC = "/mc/whole_joint_states"
DEFAULT_PROFILE = pathlib.Path(__file__).with_name("cruzr_s2_vla_profile.json")


@dataclass
class ValidationResult:
    accepted: bool
    chunk_id: int
    reasons: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "chunk_id": self.chunk_id,
            "reasons": self.reasons,
            "metrics": self.metrics,
        }


def load_profile(path: os.PathLike[str] | str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as profile_file:
        profile = json.load(profile_file)
    dim = int(profile["action_dim"])
    vector_keys = (
        "joint_names",
        "lower_boundary",
        "upper_boundary",
        "max_interpoint_speed",
        "max_first_point_delta",
    )
    for key in vector_keys:
        if len(profile[key]) != dim:
            raise ValueError(f"{key} has {len(profile[key])} entries; expected {dim}")
    if len(set(profile["joint_names"])) != dim:
        raise ValueError("joint_names contains duplicates")
    joint_names = set(profile["joint_names"])
    commanded = set(profile["commanded_joint_names"])
    locked = set(profile["locked_joint_names"])
    if commanded & locked or commanded | locked != joint_names:
        raise ValueError("commanded_joint_names and locked_joint_names must partition joint_names")
    return profile


def _finite_vector(values: Iterable[Any], expected: int, label: str, reasons: list[str]) -> list[float]:
    try:
        vector = [float(value) for value in values]
    except (TypeError, ValueError) as exc:
        reasons.append(f"{label}:non_numeric:{exc}")
        return []
    if len(vector) != expected:
        reasons.append(f"{label}:dimension:{len(vector)}!=expected:{expected}")
        return vector
    if not all(math.isfinite(value) for value in vector):
        reasons.append(f"{label}:non_finite")
    return vector


def state_vector_from_names(
    profile: Mapping[str, Any],
    names: Sequence[str],
    positions: Sequence[float],
) -> tuple[list[float], list[str]]:
    if len(names) != len(positions):
        raise ValueError(f"robot state names/positions mismatch: {len(names)} != {len(positions)}")
    by_name = dict(zip(names, positions))
    defaults = profile.get("state_defaults", {})
    result: list[float] = []
    defaulted: list[str] = []
    for name in profile["joint_names"]:
        if name in by_name:
            result.append(float(by_name[name]))
        elif name in defaults:
            result.append(float(defaults[name]))
            defaulted.append(name)
        else:
            raise ValueError(f"robot state is missing required joint: {name}")
    return result, defaulted


def validate_chunk_data(
    profile: Mapping[str, Any],
    *,
    chunk_id: int,
    status_code: int,
    inference_time_sec: float,
    points: Sequence[Mapping[str, Any]],
    state_positions: Sequence[float] | None,
) -> ValidationResult:
    reasons: list[str] = []
    metrics: dict[str, Any] = {}
    dim = int(profile["action_dim"])
    horizon = int(profile["action_horizon"])
    expected_dt = float(profile["point_dt_seconds"])
    dt_tolerance = float(profile["point_dt_tolerance_seconds"])

    if int(status_code) != 1:
        reasons.append(f"status_code:{status_code}")
    if not math.isfinite(float(inference_time_sec)) or float(inference_time_sec) < 0:
        reasons.append("inference_time:invalid")
    if len(points) != horizon:
        reasons.append(f"horizon:{len(points)}!=expected:{horizon}")

    position_rows: list[list[float]] = []
    times: list[float] = []
    for index, point in enumerate(points):
        row = _finite_vector(point.get("positions", []), dim, f"point:{index}:positions", reasons)
        position_rows.append(row)
        for key in ("velocities", "accelerations", "effort"):
            values = point.get(key, [])
            if values:
                _finite_vector(values, dim, f"point:{index}:{key}", reasons)
        try:
            point_time = float(point["time_from_start"])
        except (KeyError, TypeError, ValueError):
            reasons.append(f"point:{index}:time_from_start:invalid")
            point_time = math.nan
        times.append(point_time)

    if len(position_rows) == horizon and all(len(row) == dim for row in position_rows):
        lower = [float(value) for value in profile["lower_boundary"]]
        upper = [float(value) for value in profile["upper_boundary"]]
        tolerance = float(profile["range_tolerance"])
        range_violations: list[dict[str, Any]] = []
        for point_index, row in enumerate(position_rows):
            for joint_index, value in enumerate(row):
                if value < lower[joint_index] - tolerance or value > upper[joint_index] + tolerance:
                    range_violations.append(
                        {
                            "point": point_index,
                            "joint": profile["joint_names"][joint_index],
                            "value": value,
                            "lower": lower[joint_index],
                            "upper": upper[joint_index],
                        }
                    )
        if range_violations:
            reasons.append(f"range_violations:{len(range_violations)}")
            metrics["range_violation_examples"] = range_violations[:8]

        speed_limits = [float(value) for value in profile["max_interpoint_speed"]]
        commanded_names = set(profile["commanded_joint_names"])
        max_speeds = [0.0] * dim
        speed_violations: list[dict[str, Any]] = []
        for point_index in range(1, len(position_rows)):
            dt = times[point_index] - times[point_index - 1]
            if not math.isfinite(dt) or dt <= 0:
                continue
            for joint_index in range(dim):
                speed = abs(position_rows[point_index][joint_index] - position_rows[point_index - 1][joint_index]) / dt
                max_speeds[joint_index] = max(max_speeds[joint_index], speed)
                if speed > speed_limits[joint_index] and profile["joint_names"][joint_index] in commanded_names:
                    speed_violations.append(
                        {
                            "point": point_index,
                            "joint": profile["joint_names"][joint_index],
                            "speed": speed,
                            "limit": speed_limits[joint_index],
                        }
                    )
        metrics["max_interpoint_speed"] = dict(zip(profile["joint_names"], max_speeds))
        if speed_violations:
            reasons.append(f"speed_violations:{len(speed_violations)}")
            metrics["speed_violation_examples"] = speed_violations[:8]

        if state_positions is None:
            reasons.append("robot_state:unavailable")
        else:
            state = _finite_vector(state_positions, dim, "robot_state", reasons)
            if len(state) == dim:
                delta_limits = [float(value) for value in profile["max_first_point_delta"]]
                signed_deltas = [position_rows[0][i] - state[i] for i in range(dim)]
                deltas = [abs(value) for value in signed_deltas]
                metrics["state_positions"] = dict(zip(profile["joint_names"], state))
                metrics["first_point_positions"] = dict(
                    zip(profile["joint_names"], position_rows[0])
                )
                metrics["first_point_signed_delta"] = dict(
                    zip(profile["joint_names"], signed_deltas)
                )
                metrics["first_point_delta"] = dict(zip(profile["joint_names"], deltas))
                commanded_indices = [
                    index
                    for index, name in enumerate(profile["joint_names"])
                    if name in commanded_names
                ]
                maximum_index = max(commanded_indices, key=lambda index: deltas[index])
                metrics["maximum_commanded_first_point_delta"] = {
                    "joint_index": maximum_index,
                    "joint": profile["joint_names"][maximum_index],
                    "signed_delta": signed_deltas[maximum_index],
                    "absolute_delta": deltas[maximum_index],
                    "limit": delta_limits[maximum_index],
                }
                violations = [
                    {
                        "joint": profile["joint_names"][i],
                        "delta": deltas[i],
                        "limit": delta_limits[i],
                    }
                    for i in range(dim)
                    if deltas[i] > delta_limits[i] and profile["joint_names"][i] in commanded_names
                ]
                if violations:
                    reasons.append(f"first_point_delta_violations:{len(violations)}")
                    metrics["first_point_delta_violation_examples"] = violations[:8]

    if len(times) == horizon and all(math.isfinite(value) for value in times):
        for index, value in enumerate(times):
            expected = index * expected_dt
            if abs(value - expected) > dt_tolerance:
                reasons.append(f"point:{index}:time:{value:.6f}!=expected:{expected:.6f}")
    metrics["inference_time_sec"] = float(inference_time_sec)
    return ValidationResult(not reasons, int(chunk_id), reasons, metrics)


def _message_points(message: Any) -> list[dict[str, Any]]:
    return [
        {
            "positions": list(point.positions),
            "velocities": list(point.velocities),
            "accelerations": list(point.accelerations),
            "effort": list(point.effort),
            "time_from_start": float(point.time_from_start.sec)
            + float(point.time_from_start.nanosec) * 1e-9,
        }
        for point in message.chunk_points
    ]


def run_ros_validator(args: argparse.Namespace) -> int:
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
    from mc_state_msgs.msg import RobotState
    from sensor_msgs.msg import JointState
    from vla_msgs.msg import Gr00tMotionChunk

    profile = load_profile(args.profile)
    log_path = pathlib.Path(args.log)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    qos = QoSProfile(
        reliability=ReliabilityPolicy.BEST_EFFORT,
        history=HistoryPolicy.KEEP_LAST,
        depth=10,
        durability=DurabilityPolicy.VOLATILE,
    )

    class ShadowNode(Node):
        def __init__(self) -> None:
            super().__init__("cruzr_s2_vla_shadow_validator")
            self.latest_state: list[float] | None = None
            self.latest_state_monotonic = 0.0
            self.defaulted_joints: list[str] = []
            self.state_messages = 0
            self.state_source = "none"
            self.accepted = 0
            self.rejected = 0
            self.seen = 0
            self.last_chunk_id: int | None = None
            self.fatal_reason = ""
            self.create_subscription(RobotState, STATE_TOPIC, self.on_state, qos)
            self.create_subscription(JointState, STATE_FALLBACK_TOPIC, self.on_joint_state, qos)
            self.create_subscription(Gr00tMotionChunk, CHUNK_TOPIC, self.on_chunk, qos)

        def command_publishers(self) -> int:
            return len(self.get_publishers_info_by_topic(COMMAND_TOPIC))

        def assert_command_path_absent(self) -> bool:
            count = self.command_publishers()
            if count:
                self.fatal_reason = f"command_publishers_detected:{count}"
                self.get_logger().error(self.fatal_reason)
                return False
            return True

        def accept_state(self, names: Sequence[str], positions: Sequence[float], source: str) -> None:
            try:
                self.latest_state, self.defaulted_joints = state_vector_from_names(
                    profile,
                    list(names),
                    list(positions),
                )
                self.latest_state_monotonic = time.monotonic()
                self.state_messages += 1
                self.state_source = source
                if self.state_messages == 1:
                    self.get_logger().info(
                        f"SHADOW_STATE_READY=joints:{len(self.latest_state)},"
                        f"defaulted:{','.join(self.defaulted_joints) or 'none'},source:{source}"
                    )
            except (TypeError, ValueError) as exc:
                self.latest_state = None
                self.get_logger().error(f"robot_state_rejected:{exc}")

        def on_state(self, message: Any) -> None:
            self.accept_state(message.joint_states.name, message.joint_states.position, STATE_TOPIC)

        def on_joint_state(self, message: Any) -> None:
            self.accept_state(message.name, message.position, STATE_FALLBACK_TOPIC)

        def on_chunk(self, message: Any) -> None:
            if not self.assert_command_path_absent():
                return
            self.seen += 1
            reasons_before: list[str] = []
            if self.last_chunk_id is not None and int(message.chunk_id) <= self.last_chunk_id:
                reasons_before.append(f"chunk_id_not_increasing:{message.chunk_id}<={self.last_chunk_id}")
            self.last_chunk_id = int(message.chunk_id)
            state = self.latest_state
            state_age = None
            if state is not None:
                state_age = time.monotonic() - self.latest_state_monotonic
                if state_age > float(profile["max_state_age_seconds"]):
                    reasons_before.append(f"robot_state_stale:{state_age:.3f}s")
                    state = None
            result = validate_chunk_data(
                profile,
                chunk_id=message.chunk_id,
                status_code=message.status_code,
                inference_time_sec=message.inference_time_sec,
                points=_message_points(message),
                state_positions=state,
            )
            result.reasons[:0] = reasons_before
            result.accepted = not result.reasons
            result.metrics["state_age_sec"] = state_age
            result.metrics["state_defaulted_joints"] = self.defaulted_joints
            result.metrics["state_source"] = self.state_source
            result.metrics["observed_at_unix"] = time.time()
            if result.accepted:
                self.accepted += 1
                level = self.get_logger().info
                label = "SHADOW_CHUNK_ACCEPTED"
            else:
                self.rejected += 1
                level = self.get_logger().warning
                label = "SHADOW_CHUNK_REJECTED"
            with log_path.open("a", encoding="utf-8") as output:
                output.write(json.dumps(result.as_dict(), sort_keys=True) + "\n")
            level(f"{label}=id:{result.chunk_id},reasons:{','.join(result.reasons) or 'none'}")

    rclpy.init(args=None)
    node = ShadowNode()
    started = time.monotonic()
    exit_code = 0
    try:
        if not node.assert_command_path_absent():
            return 3
        node.get_logger().info(
            f"SHADOW_READY=profile:{profile['profile']},dim:{profile['action_dim']},"
            f"horizon:{profile['action_horizon']},publisher:none"
        )
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.1)
            if node.fatal_reason:
                exit_code = 3
                break
            if args.max_chunks and node.seen >= args.max_chunks:
                break
            if args.duration and time.monotonic() - started >= args.duration:
                break
            if not node.assert_command_path_absent():
                exit_code = 3
                break
        if exit_code == 0 and node.seen == 0 and not args.allow_no_chunks:
            exit_code = 2
        elif exit_code == 0 and node.rejected:
            exit_code = 1
        print(
            f"SHADOW_SUMMARY=seen:{node.seen},accepted:{node.accepted},"
            f"rejected:{node.rejected},command_publishers:{node.command_publishers()},exit:{exit_code}",
            flush=True,
        )
    finally:
        node.destroy_node()
        rclpy.shutdown()
    return exit_code


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default=str(DEFAULT_PROFILE))
    parser.add_argument("--log", default="/tmp/cruzr_s2_vla_shadow.jsonl")
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--max-chunks", type=int, default=0)
    parser.add_argument("--allow-no-chunks", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    return run_ros_validator(parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
