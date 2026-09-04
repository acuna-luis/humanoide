#!/usr/bin/env python3
"""Normalize one read-only ROS JointState sample to the frozen E6.1B 20D order."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import time
from typing import Any

import yaml


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    contract = load_object(args.contract)
    if contract.get("schema") != "cruzr-s2-vla-task0-entry-recovery-e6.1b-v1":
        raise ValueError("unexpected E6.1B contract")
    documents = [item for item in yaml.safe_load_all(args.input.read_text(encoding="utf-8")) if item]
    if len(documents) != 1 or not isinstance(documents[0], dict):
        raise ValueError("input must contain exactly one JointState mapping")
    sample = documents[0]
    names = sample.get("name")
    positions = sample.get("position")
    velocities = sample.get("velocity")
    if not all(isinstance(item, list) for item in (names, positions, velocities)):
        raise ValueError("JointState must contain name, position and velocity lists")
    if len(names) != len(positions) or len(names) != len(velocities):
        raise ValueError("JointState name/position/velocity lengths differ")
    if len(set(names)) != len(names):
        raise ValueError("JointState contains duplicate names")
    by_name = {
        name: (float(position), float(velocity))
        for name, position, velocity in zip(names, positions, velocities, strict=True)
    }
    order = contract["candidate"]["joint_order"]
    missing = [name for name in order if name not in by_name]
    if missing:
        raise ValueError(f"JointState is missing required joints: {missing}")
    normalized_positions = [by_name[name][0] for name in order]
    normalized_velocities = [by_name[name][1] for name in order]
    if not all(math.isfinite(value) for value in normalized_positions + normalized_velocities):
        raise ValueError("JointState contains non-finite values")

    stamp = sample.get("header", {}).get("stamp", {})
    output = {
        "schema": "cruzr-s2-vla-live-joint-state-e6.1b-v1",
        "source_topic": "/mc/whole_joint_states",
        "source_header": {
            "sec": int(stamp.get("sec", 0)),
            "nanosec": int(stamp.get("nanosec", 0)),
            "frame_id": sample.get("header", {}).get("frame_id", ""),
        },
        "observed_at_unix": time.time(),
        "names": order,
        "positions": normalized_positions,
        "velocities": normalized_velocities,
        "physical_command_publisher_created": False,
        "physical_movement_commanded": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(f"E6.1B_STATE_20D_OK={args.output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}", file=__import__("sys").stderr)
        raise SystemExit(2) from exc
