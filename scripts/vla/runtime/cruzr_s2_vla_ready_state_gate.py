#!/usr/bin/env python3
"""Read-only READY-state gate for the Cruzr S2 E6.0 canary.

Consumes one JSON ``sensor_msgs/msg/JointState`` sample from
``/mc/whole_joint_states`` on stdin.  READY belongs to the named ROS joint
coordinate system used by the checkpoint; raw actuator coordinates are not
interchangeable because some motors have a different sign convention.  The
module does not import ROS, open a network connection, or emit a command.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from typing import Any


ARM_NAMES = (
    "L_elbow_roll_joint",
    "L_elbow_yaw_joint",
    "L_shoulder_pitch_joint",
    "L_shoulder_roll_joint",
    "L_shoulder_yaw_joint",
    "L_wrist_pitch_joint",
    "L_wrist_roll_joint",
    "R_elbow_roll_joint",
    "R_elbow_yaw_joint",
    "R_shoulder_pitch_joint",
    "R_shoulder_roll_joint",
    "R_shoulder_yaw_joint",
    "R_wrist_pitch_joint",
    "R_wrist_roll_joint",
)
LOCKED_NAMES = (
    "head_pitch_joint",
    "head_yaw_joint",
    "lifter_pitch_1_joint",
    "lifter_pitch_2_joint",
    "lifter_pitch_3_joint",
    "waist_yaw_joint",
)


def number(item: dict[str, Any], key: str, default: float | None = None) -> float:
    raw = item.get(key, default)
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key}:not_numeric") from exc
    if not math.isfinite(value):
        raise ValueError(f"{key}:non_finite")
    return value


def classify(
    message: dict[str, Any],
    contract: dict[str, Any],
    *,
    ready_tolerance: float,
    velocity_tolerance: float,
) -> list[str]:
    names = message.get("name")
    positions = message.get("position")
    velocities = message.get("velocity")
    if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
        raise ValueError("joint_state:names")
    if len(names) != len(set(names)):
        raise ValueError("joint_state:duplicate_name")
    if not isinstance(positions, list) or len(positions) != len(names):
        raise ValueError("joint_state:positions")
    if not isinstance(velocities, list) or len(velocities) != len(names):
        raise ValueError("joint_state:velocities")
    by_name = {
        name: {
            "position": number({"position": position}, "position"),
            "velocity": number({"velocity": velocity}, "velocity"),
        }
        for name, position, velocity in zip(names, positions, velocities, strict=True)
    }

    expected_names = contract.get("commanded_joint_names")
    expected_positions = contract.get("ready_arm_positions")
    if expected_names != list(ARM_NAMES):
        raise ValueError("contract:commanded_joint_order")
    if contract.get("locked_joint_names") != list(LOCKED_NAMES):
        raise ValueError("contract:locked_joint_order")
    if not isinstance(expected_positions, list) or len(expected_positions) != 14:
        raise ValueError("contract:ready_arm_positions")

    selected: list[tuple[str, dict[str, float], float | None]] = []
    for index, name in enumerate(ARM_NAMES):
        if name not in by_name:
            raise ValueError(f"joint_state:missing:{name}")
        selected.append((name, by_name[name], float(expected_positions[index])))
    for name in LOCKED_NAMES:
        if name not in by_name:
            raise ValueError(f"joint_state:missing:{name}")
        selected.append((name, by_name[name], None))

    maximum_ready_error = 0.0
    maximum_velocity = 0.0
    for _name, item, expected in selected:
        position = number(item, "position")
        velocity = number(item, "velocity")
        maximum_velocity = max(maximum_velocity, abs(velocity))
        if expected is not None:
            maximum_ready_error = max(maximum_ready_error, abs(position - expected))

    measured_ready = (
        maximum_ready_error <= ready_tolerance
        and maximum_velocity <= velocity_tolerance
    )
    return [
        "READY_STATE_SOURCE=/mc/whole_joint_states,named-ros-coordinates",
        "READY_ARM_COUNT=14",
        "READY_LOCKED_AXIS_COUNT=6",
        f"READY_MAX_ABS_ERROR={maximum_ready_error:.6f}",
        f"READY_BODY_MAX_ABS_VELOCITY={maximum_velocity:.6f}",
        f"MEASURED_READY={'1' if measured_ready else '0'}",
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--ready-tolerance", type=float, default=0.01)
    parser.add_argument("--velocity-tolerance", type=float, default=0.01)
    args = parser.parse_args()
    for label in ("ready_tolerance", "velocity_tolerance"):
        value = getattr(args, label)
        if not 0 < value <= 0.02:
            parser.error(f"--{label.replace('_', '-')} debe estar en (0, 0.02]")
    try:
        contract = json.loads(open(args.contract, encoding="utf-8").read())
        message = json.load(sys.stdin)
        if not isinstance(contract, dict) or not isinstance(message, dict):
            raise ValueError("json:not_object")
        output = classify(
            message,
            contract,
            ready_tolerance=args.ready_tolerance,
            velocity_tolerance=args.velocity_tolerance,
        )
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"READY_STATE_ERROR={exc}", file=sys.stderr)
        return 2
    print("\n".join(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
