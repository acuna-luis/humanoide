#!/usr/bin/env python3
"""Summarize frame-zero 20D state/action entries in the supplied VLA dataset.

The program is read-only and emits one JSON object to stdout.  It is intended
for an offline container with ``--network none``; it imports no ROS package and
has no robot command path.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
from typing import Any

import pyarrow.parquet as pq


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("empty percentile input")
    position = fraction * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def vector_stats(rows: list[list[float]], names: list[str]) -> dict[str, Any]:
    columns = list(zip(*rows, strict=True))
    return {
        name: {
            "min": min(column),
            "q01": percentile(list(column), 0.01),
            "median": percentile(list(column), 0.50),
            "q99": percentile(list(column), 0.99),
            "max": max(column),
        }
        for name, column in zip(names, columns, strict=True)
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=pathlib.Path, required=True)
    args = parser.parse_args()
    dataset = args.dataset.resolve()
    info = json.loads((dataset / "meta/info.json").read_text(encoding="utf-8"))
    names = info["features"]["action"]["names"]
    if len(names) != 20 or info["features"]["observation.state"]["shape"] != [32]:
        raise ValueError("unexpected supplied dataset dimensions")

    by_task: dict[int, dict[str, Any]] = {}
    records: list[dict[str, Any]] = []
    files = sorted((dataset / "data/chunk-000").glob("episode_*.parquet"))
    for path in files:
        table = pq.read_table(
            path,
            columns=["observation.state", "action", "task_index", "timestamp"],
        )
        if table.num_rows < 1:
            raise ValueError(f"empty episode: {path.name}")
        timestamps = [float(value) for value in table["timestamp"].to_pylist()]
        first_index = min(range(len(timestamps)), key=timestamps.__getitem__)
        task = int(table["task_index"][first_index].as_py())
        state = [
            float(value)
            for value in table["observation.state"][first_index].as_py()[:20]
        ]
        action = [float(value) for value in table["action"][first_index].as_py()]
        if len(state) != 20 or len(action) != 20:
            raise ValueError(f"bad frame-zero dimensions: {path.name}")
        delta = [target - observed for observed, target in zip(state, action)]
        bucket = by_task.setdefault(
            task, {"state": [], "action": [], "delta": [], "episode": []}
        )
        bucket["state"].append(state)
        bucket["action"].append(action)
        bucket["delta"].append(delta)
        bucket["episode"].append(path.stem)
        records.append(
            {
                "episode": path.stem,
                "task": task,
                "state": state,
                "action": action,
                "action_minus_state": delta,
            }
        )

    report: dict[str, Any] = {
        "schema": "cruzr-s2-vla-dataset-entry-states-v1",
        "mode": "offline_dataset_read_only_no_ros_no_robot_no_publisher",
        "episode_count": len(files),
        "joint_names": names,
        "frame_zero_records": records,
        "tasks": {},
    }
    for task, bucket in sorted(by_task.items()):
        maximum_initial_action_delta = max(
            (
                (abs(value), row_index, axis, value)
                for row_index, row in enumerate(bucket["delta"])
                for axis, value in enumerate(row)
            ),
            key=lambda item: item[0],
        )
        nearest_neighbours: list[tuple[float, int, int]] = []
        for row_index, state in enumerate(bucket["state"]):
            candidates = (
                (
                    max(abs(left - right) for left, right in zip(state, other)),
                    other_index,
                )
                for other_index, other in enumerate(bucket["state"])
                if other_index != row_index
            )
            distance, other_index = min(candidates)
            nearest_neighbours.append((distance, row_index, other_index))
        nearest_distances = [item[0] for item in nearest_neighbours]
        worst_nearest = max(nearest_neighbours)
        report["tasks"][str(task)] = {
            "episode_count": len(bucket["state"]),
            "frame_zero_state": vector_stats(bucket["state"], names),
            "frame_zero_action": vector_stats(bucket["action"], names),
            "frame_zero_action_minus_state": vector_stats(bucket["delta"], names),
            "maximum_absolute_frame_zero_action_delta": {
                "absolute_delta": maximum_initial_action_delta[0],
                "episode_offset": maximum_initial_action_delta[1],
                "joint_index": maximum_initial_action_delta[2],
                "joint": names[maximum_initial_action_delta[2]],
                "signed_delta": maximum_initial_action_delta[3],
            },
            "frame_zero_nearest_neighbour_chebyshev_rad": {
                "min": min(nearest_distances),
                "q01": percentile(nearest_distances, 0.01),
                "median": percentile(nearest_distances, 0.50),
                "q99": percentile(nearest_distances, 0.99),
                "max": max(nearest_distances),
                "worst_episode": bucket["episode"][worst_nearest[1]],
                "worst_neighbour_episode": bucket["episode"][worst_nearest[2]],
            },
        }
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
