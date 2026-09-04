#!/usr/bin/env python3
"""Fail-closed 20D state gate for E6.1C READY and ENTRY endpoints."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
import time
from typing import Any


EXPECTED_SCHEMA = "cruzr-s2-vla-ready-entry-transition-e6.1c-v1"


def object_from(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def vector(value: Any, length: int, label: str) -> list[float]:
    if not isinstance(value, list) or len(value) != length:
        raise ValueError(f"{label}: expected {length} values")
    result = [float(item) for item in value]
    if not all(math.isfinite(item) for item in result):
        raise ValueError(f"{label}: non-finite value")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--state-json", type=Path, required=True)
    parser.add_argument("--expect", choices=("ready", "entry"), required=True)
    parser.add_argument("--require-fresh", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    contract = object_from(args.contract)
    state = object_from(args.state_json)
    if contract.get("schema") != EXPECTED_SCHEMA:
        raise ValueError("unexpected E6.1C contract")
    if contract.get("physical_execution_authorized") is not False:
        raise ValueError("contract unexpectedly authorizes movement")
    order = contract["joint_order"]
    if state.get("names") != order:
        raise ValueError("state joint order is not exact")
    positions = vector(state.get("positions"), 20, "state.positions")
    velocities = vector(state.get("velocities"), 20, "state.velocities")
    reference_key = (
        "observed_ready_reference_20d_rad"
        if args.expect == "ready"
        else "frozen_dataset_entry_20d_rad"
    )
    reference = vector(contract[reference_key], 20, reference_key)
    deltas = [abs(value - expected) for value, expected in zip(positions, reference, strict=True)]
    maximum_index = max(range(20), key=deltas.__getitem__)
    maximum_velocity = max(abs(value) for value in velocities)
    gate = contract["state_gate"]
    reasons = []
    if deltas[maximum_index] > float(gate["maximum_chebyshev_distance_rad"]):
        reasons.append(f"state_not_{args.expect}")
    if maximum_velocity > float(gate["maximum_absolute_velocity_rad_s"]):
        reasons.append("state_not_stationary")
    observed_at = float(state.get("observed_at_unix"))
    if not math.isfinite(observed_at):
        raise ValueError("observed_at_unix is not finite")
    age = time.time() - observed_at
    if args.require_fresh and (age < -1.0 or age > float(gate["maximum_state_age_seconds"])):
        reasons.append("state_not_fresh")
    result = {
        "schema": "cruzr-s2-vla-ready-entry-state-gate-e6.1c-v1",
        "expected_endpoint": args.expect,
        "qualified": not reasons,
        "maximum_chebyshev_distance_rad": deltas[maximum_index],
        "maximum_distance_joint": order[maximum_index],
        "maximum_absolute_velocity_rad_s": maximum_velocity,
        "state_age_seconds": age,
        "rejection_reasons": reasons,
        "physical_execution_authorized": False,
        "physical_publisher_count": 0,
    }
    rendered = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if not reasons else 3


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
