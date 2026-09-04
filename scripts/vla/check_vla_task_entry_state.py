#!/usr/bin/env python3
"""Fail-closed task/scene/20D entry check for the supplied Cruzr S2 VLA.

This program is standard-library only.  It consumes the read-only report made
by ``analyze_vla_dataset_entry_states.py`` and cannot import ROS or publish a
robot command.  A PASS qualifies only a subsequent fresh shadow run.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


def load_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_positions(path: pathlib.Path) -> list[float]:
    value = load_json(path)
    if isinstance(value, dict):
        value = value.get("positions")
    if not isinstance(value, list):
        raise ValueError("state JSON must be a list or contain a positions list")
    positions = [float(item) for item in value]
    if len(positions) != 20:
        raise ValueError(f"expected 20 state positions, got {len(positions)}")
    return positions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-report", type=pathlib.Path, required=True)
    parser.add_argument("--contract", type=pathlib.Path, required=True)
    parser.add_argument("--task-id", type=int, required=True)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--state-json", type=pathlib.Path, required=True)
    args = parser.parse_args()

    report = load_json(args.dataset_report)
    contract = load_json(args.contract)
    if report.get("schema") != "cruzr-s2-vla-dataset-entry-states-v1":
        raise ValueError("unexpected dataset report schema")
    if contract.get("schema") != "cruzr-s2-vla-task-entry-contract-e6.0z-v1":
        raise ValueError("unexpected entry contract schema")
    if contract.get("physical_execution_authorized") is not False:
        raise ValueError("entry contract must not authorize physical execution")

    task_key = str(args.task_id)
    task_contract = contract["tasks"].get(task_key)
    task_report = report["tasks"].get(task_key)
    if task_contract is None or task_report is None:
        raise ValueError(f"task {args.task_id} is absent from contract or dataset")

    names = report["joint_names"]
    positions = load_positions(args.state_json)
    if len(names) != 20:
        raise ValueError("dataset report does not contain 20 joint names")
    records = [
        record
        for record in report.get("frame_zero_records", [])
        if int(record["task"]) == args.task_id
    ]
    if not records:
        raise ValueError("dataset report has no frame-zero records for task")

    ranked: list[tuple[float, dict[str, Any], list[float]]] = []
    for record in records:
        deltas = [
            abs(observed - reference)
            for observed, reference in zip(positions, record["state"], strict=True)
        ]
        ranked.append((max(deltas), record, deltas))
    nearest_distance, nearest, nearest_deltas = min(ranked, key=lambda item: item[0])
    maximum_axis = max(range(20), key=nearest_deltas.__getitem__)

    outside_bounds = []
    for index, name in enumerate(names):
        stats = task_report["frame_zero_state"][name]
        if positions[index] < stats["min"] or positions[index] > stats["max"]:
            outside_bounds.append(
                {
                    "joint_index": index,
                    "joint": name,
                    "observed": positions[index],
                    "dataset_min": stats["min"],
                    "dataset_max": stats["max"],
                }
            )

    required_scenario = task_contract["required_scenario"]
    distance_limit = float(contract["entry_state"]["maximum_distance_rad"])
    reasons = []
    if args.scenario != required_scenario:
        reasons.append("task_scene_mismatch")
    if outside_bounds:
        reasons.append("state_outside_same_task_observed_bounds")
    if nearest_distance > distance_limit:
        reasons.append("state_not_close_to_any_same_task_frame_zero")

    result = {
        "schema": "cruzr-s2-vla-task-entry-assessment-e6.0z-v1",
        "mode": "offline_read_only_no_ros_no_robot_no_publisher",
        "task_id": args.task_id,
        "instruction": task_contract["instruction"],
        "scenario_observed": args.scenario,
        "scenario_required": required_scenario,
        "action_semantics": contract["action_semantics"],
        "entry_distance_limit_rad": distance_limit,
        "nearest_same_task_episode": nearest["episode"],
        "nearest_same_task_chebyshev_rad": nearest_distance,
        "nearest_maximum_axis": {
            "joint_index": maximum_axis,
            "joint": names[maximum_axis],
            "observed": positions[maximum_axis],
            "reference": nearest["state"][maximum_axis],
            "absolute_delta": nearest_deltas[maximum_axis],
        },
        "outside_same_task_observed_bounds": outside_bounds,
        "entry_qualified_for_fresh_shadow": not reasons,
        "physical_execution_authorized": False,
        "rejection_reasons": reasons,
    }
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if not reasons else 3


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
