#!/usr/bin/env python3
"""Select and evaluate Cruzr S2 VLA samples without ROS or robot access.

The ``select`` subcommand only uses the Python standard library and runs on the
PC.  The ``infer`` subcommand is intended for UBTECH's NVIDIA inference image
started with ``--network none``.  This file deliberately imports neither ROS
nor any robot command message.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pathlib
import random
import sys
import time
from typing import Any, Iterable, Sequence


TASKS = {
    0: "Pick up the large box from the lowest level of shelf",
    1: "Place the large box on the lowest level of shelf",
    2: "Pick up the large box from the middle level of shelf",
    3: "Place the large box on the middle level of shelf",
}
PLACE_TASK_IDS = (1, 3)
CAMPAIGN_SEEDS = (0, 1, 2, 3, 4)
STATE_PARTS = {
    "left_arm": (0, 7),
    "right_arm": (7, 14),
    "head": (14, 16),
    "lifter": (16, 19),
    "waist": (19, 20),
}
ACTION_KEYS = tuple(STATE_PARTS)


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: pathlib.Path) -> Any:
    with path.open("r", encoding="utf-8") as source:
        return json.load(source)


def write_json_exclusive(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as target:
        json.dump(value, target, indent=2, sort_keys=True, allow_nan=False)
        target.write("\n")


def load_episode_catalog(path: pathlib.Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as source:
        for line_number, line in enumerate(source, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid episodes.jsonl line {line_number}: {exc}") from exc
            if not isinstance(row.get("episode_index"), int) or not isinstance(row.get("tasks"), str):
                raise ValueError(f"invalid episode catalog row at line {line_number}")
            rows.append(row)
    if not rows:
        raise ValueError("episode catalog is empty")
    return rows


def test_pool_for_task(
    episodes: Sequence[dict[str, Any]], task_id: int, fraction: float = 0.15
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if task_id not in TASKS:
        raise ValueError(f"unsupported task ID: {task_id}")
    eligible = sorted(
        (row for row in episodes if row["tasks"] == TASKS[task_id]),
        key=lambda row: int(row["episode_index"]),
    )
    if not eligible:
        raise ValueError(f"no episodes found for task {task_id}")
    held_out_count = max(1, math.ceil(len(eligible) * fraction))
    return eligible, eligible[-held_out_count:]


def train_and_test_pools_for_task(
    episodes: Sequence[dict[str, Any]], task_id: int, fraction: float = 0.15
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    eligible, held_out = test_pool_for_task(episodes, task_id, fraction)
    train = eligible[: len(eligible) - len(held_out)]
    if {int(row["episode_index"]) for row in train} & {
        int(row["episode_index"]) for row in held_out
    }:
        raise ValueError(f"task {task_id} has train/test episode overlap")
    return train, held_out


def select_episode(
    episodes: Sequence[dict[str, Any]], task_id: int, seed: int
) -> tuple[dict[str, Any], int, int]:
    eligible, held_out = test_pool_for_task(episodes, task_id)
    rng = random.Random(seed + task_id * 1009)
    selected = held_out[rng.randrange(len(held_out))]
    return selected, len(eligible), len(held_out)


def select_campaign_episode(
    episodes: Sequence[dict[str, Any]], task_id: int, seed: int
) -> tuple[dict[str, Any], int, int]:
    if seed not in CAMPAIGN_SEEDS:
        raise ValueError(f"E3.0 seed must be one of {CAMPAIGN_SEEDS}")
    train, held_out = train_and_test_pools_for_task(episodes, task_id)
    valid = [row for row in held_out if int(row["length"]) >= 10]
    if len(valid) < len(CAMPAIGN_SEEDS):
        raise ValueError(f"task {task_id} has fewer than five valid held-out episodes")
    ordered = list(valid)
    random.Random(30_000 + task_id * 1_009).shuffle(ordered)
    selected = ordered[seed]
    return selected, len(train), len(held_out)


def episode_paths(dataset: pathlib.Path, episode_index: int) -> tuple[pathlib.Path, pathlib.Path]:
    episode_name = f"episode_{episode_index:06d}"
    parquet = dataset / "data" / "chunk-000" / f"{episode_name}.parquet"
    video = (
        dataset
        / "videos"
        / "chunk-000"
        / "observation.images.rgb"
        / f"{episode_name}.mp4"
    )
    return parquet, video


def command_select(args: argparse.Namespace) -> int:
    dataset = pathlib.Path(args.dataset).resolve()
    output = pathlib.Path(args.output).resolve()
    task_id = int(args.task_id)
    if task_id not in PLACE_TASK_IDS:
        raise ValueError("E2.2 only supports PLACE task IDs 1 and 3")
    if args.split != "test":
        raise ValueError("E2.2 currently defines only the project test holdout")
    info_path = dataset / "meta" / "info.json"
    tasks_path = dataset / "meta" / "tasks.jsonl"
    episodes_path = dataset / "meta" / "episodes.jsonl"
    for required in (info_path, tasks_path, episodes_path):
        if not required.is_file():
            raise FileNotFoundError(required)

    selected, eligible_count, held_out_count = select_episode(
        load_episode_catalog(episodes_path), task_id, int(args.seed)
    )
    episode_index = int(selected["episode_index"])
    parquet, video = episode_paths(dataset, episode_index)
    for required in (parquet, video):
        if not required.is_file() or required.stat().st_size == 0:
            raise FileNotFoundError(required)

    manifest = {
        "schema": "cruzr-s2-vla-offline-sample-v1",
        "mode": "offline_dataset_only_no_robot",
        "task_id": task_id,
        "task_text": TASKS[task_id],
        "episode_index": episode_index,
        "episode_length": int(selected["length"]),
        "frame_index": int(args.frame_index),
        "initial_state_semantics": "HELD_FROM_PLACE_EPISODE_TASK_AND_FRAME_0",
        "split_requested": "test",
        "split_definition": "project_stratified_tail_15_percent_not_vendor_split",
        "eligible_episode_count": eligible_count,
        "held_out_episode_count": held_out_count,
        "seed": int(args.seed),
        "source": {
            "dataset": str(dataset),
            "parquet": str(parquet),
            "video": str(video),
            "info_sha256": sha256_file(info_path),
            "tasks_sha256": sha256_file(tasks_path),
            "episodes_sha256": sha256_file(episodes_path),
            "parquet_sha256": sha256_file(parquet),
            "video_sha256": sha256_file(video),
        },
        "staged_parquet": "episode.parquet",
        "staged_video": "episode.mp4",
    }
    if manifest["frame_index"] < 0 or manifest["frame_index"] + 10 > manifest["episode_length"]:
        raise ValueError("selected frame cannot provide a ten-action ground-truth horizon")
    write_json_exclusive(output, manifest)
    print(f"OFFLINE_SAMPLE_SELECTED=task:{task_id},episode:{episode_index},frame:{args.frame_index}")
    print(f"OFFLINE_SAMPLE_MANIFEST={output}")
    return 0


def command_campaign(args: argparse.Namespace) -> int:
    dataset = pathlib.Path(args.dataset).resolve()
    output_dir = pathlib.Path(args.output_dir).resolve()
    if output_dir.exists():
        raise FileExistsError(output_dir)
    output_dir.mkdir(parents=True)
    info_path = dataset / "meta" / "info.json"
    tasks_path = dataset / "meta" / "tasks.jsonl"
    episodes_path = dataset / "meta" / "episodes.jsonl"
    for required in (info_path, tasks_path, episodes_path):
        if not required.is_file():
            raise FileNotFoundError(required)
    episodes = load_episode_catalog(episodes_path)
    metadata_hashes = {
        "info_sha256": sha256_file(info_path),
        "tasks_sha256": sha256_file(tasks_path),
        "episodes_sha256": sha256_file(episodes_path),
    }

    split_tasks: dict[str, Any] = {}
    all_train: set[int] = set()
    all_test: set[int] = set()
    sample_entries: list[dict[str, Any]] = []
    selected_episode_indices: set[int] = set()
    for task_id in sorted(TASKS):
        train, held_out = train_and_test_pools_for_task(episodes, task_id)
        train_indices = [int(row["episode_index"]) for row in train]
        test_indices = [int(row["episode_index"]) for row in held_out]
        all_train.update(train_indices)
        all_test.update(test_indices)
        split_tasks[str(task_id)] = {
            "task_text": TASKS[task_id],
            "train_episode_count": len(train_indices),
            "test_episode_count": len(test_indices),
            "train_episode_indices": train_indices,
            "test_episode_indices": test_indices,
            "test_episodes_shorter_than_action_horizon": [
                int(row["episode_index"]) for row in held_out if int(row["length"]) < 10
            ],
        }
        for seed in CAMPAIGN_SEEDS:
            selected, train_count, held_out_count = select_campaign_episode(
                episodes, task_id, seed
            )
            episode_index = int(selected["episode_index"])
            if episode_index in selected_episode_indices:
                raise ValueError(f"campaign selected duplicate episode {episode_index}")
            selected_episode_indices.add(episode_index)
            episode_length = int(selected["length"])
            max_frame_index = episode_length - 10
            phase_fraction = seed / (len(CAMPAIGN_SEEDS) - 1)
            frame_index = int(round(max_frame_index * phase_fraction))
            parquet, video = episode_paths(dataset, episode_index)
            for required in (parquet, video):
                if not required.is_file() or required.stat().st_size == 0:
                    raise FileNotFoundError(required)
            sample_id = f"task{task_id}_seed{seed}"
            relative_manifest = pathlib.Path("samples") / sample_id / "selection.json"
            manifest = {
                "schema": "cruzr-s2-vla-offline-sample-v2",
                "mode": "offline_dataset_only_no_robot",
                "campaign_id": "E3.0",
                "sample_id": sample_id,
                "task_id": task_id,
                "task_text": TASKS[task_id],
                "episode_index": episode_index,
                "episode_length": episode_length,
                "frame_index": frame_index,
                "phase_fraction": phase_fraction,
                "initial_state_semantics": "DATASET_REPLAY_TASK_PHASE_NOT_LIVE_ROBOT",
                "split_requested": "test",
                "split_definition": "project_stratified_tail_15_percent_not_vendor_split",
                "selection_policy": "task_tail15_deterministic_shuffle_unique_seed_slots",
                "frame_policy": "phase_grid_0_25_50_75_100_percent_valid_horizon",
                "train_episode_count": train_count,
                "held_out_episode_count": held_out_count,
                "seed": seed,
                "source": {
                    "dataset": str(dataset),
                    "parquet": str(parquet),
                    "video": str(video),
                    **metadata_hashes,
                    "parquet_sha256": sha256_file(parquet),
                    "video_sha256": sha256_file(video),
                },
                "staged_parquet": "episode.parquet",
                "staged_video": "episode.mp4",
            }
            write_json_exclusive(output_dir / relative_manifest, manifest)
            sample_entries.append(
                {
                    "sample_id": sample_id,
                    "task_id": task_id,
                    "seed": seed,
                    "episode_index": episode_index,
                    "frame_index": frame_index,
                    "phase_fraction": phase_fraction,
                    "manifest": str(relative_manifest),
                }
            )
            print(
                f"CAMPAIGN_SAMPLE_SELECTED={sample_id},episode:{episode_index},"
                f"frame:{frame_index},phase:{phase_fraction:.2f}"
            )

    overlap = sorted(all_train & all_test)
    if overlap:
        raise ValueError(f"global train/test episode overlap: {overlap}")
    split_audit = {
        "schema": "cruzr-s2-vla-project-split-audit-v1",
        "split_definition": "project_stratified_tail_15_percent_not_vendor_split",
        "provider_declared_splits": ["train"],
        "checkpoint_training_membership_known": False,
        "checkpoint_generalization_claim_allowed": False,
        "tasks": split_tasks,
        "global_train_episode_count": len(all_train),
        "global_test_episode_count": len(all_test),
        "global_train_test_overlap": overlap,
        "selected_test_episode_count": len(selected_episode_indices),
        "selected_test_episode_indices": sorted(selected_episode_indices),
        "selected_episodes_all_in_project_test": selected_episode_indices <= all_test,
        "source": {"dataset": str(dataset), **metadata_hashes},
    }
    split_path = output_dir / "split_audit.json"
    write_json_exclusive(split_path, split_audit)
    campaign = {
        "schema": "cruzr-s2-vla-offline-e3.0-selection-v1",
        "campaign_id": "E3.0",
        "mode": "offline_dataset_only_no_robot",
        "tasks": sorted(TASKS),
        "seeds": list(CAMPAIGN_SEEDS),
        "seed0_total_repetitions_per_task": int(args.seed0_repetitions),
        "unique_sample_count": len(sample_entries),
        "expected_inference_run_count": len(sample_entries)
        + len(TASKS) * (int(args.seed0_repetitions) - 1),
        "sample_manifests": sample_entries,
        "split_audit": "split_audit.json",
        "split_audit_sha256": sha256_file(split_path),
        "physical_task_success_evaluated": False,
    }
    write_json_exclusive(output_dir / "campaign.json", campaign)
    print(
        f"E3_0_CAMPAIGN_SELECTED=samples:{len(sample_entries)},"
        f"runs:{campaign['expected_inference_run_count']},overlap:0"
    )
    return 0


def _finite_matrix(values: Iterable[Iterable[Any]], rows: int, cols: int, label: str) -> list[list[float]]:
    matrix = [[float(value) for value in row] for row in values]
    if len(matrix) != rows or any(len(row) != cols for row in matrix):
        shape = [len(matrix), len(matrix[0]) if matrix else 0]
        raise ValueError(f"{label} shape {shape}, expected [{rows}, {cols}]")
    if not all(math.isfinite(value) for row in matrix for value in row):
        raise ValueError(f"{label} contains NaN or infinity")
    return matrix


def _flatten_prediction(action_chunk: dict[str, Any]) -> list[list[float]]:
    import numpy as np

    missing = [f"action.{key}" for key in ACTION_KEYS if f"action.{key}" not in action_chunk]
    if missing:
        raise ValueError(f"model output is missing keys: {missing}")
    horizon = int(np.asarray(action_chunk["action.left_arm"]).shape[0])
    rows: list[list[float]] = []
    for row_index in range(horizon):
        row = np.concatenate(
            [np.atleast_1d(action_chunk[f"action.{key}"][row_index]) for key in ACTION_KEYS]
        )
        rows.append([float(value) for value in row.tolist()])
    return _finite_matrix(rows, 10, 20, "predicted_action")


def _read_video_frame(video_path: pathlib.Path, frame_index: int) -> tuple[Any, dict[str, Any]]:
    import cv2

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"cannot open video {video_path}")
    try:
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, bgr = capture.read()
        if not ok or bgr is None:
            raise ValueError(f"cannot decode video frame {frame_index}")
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        return rgb, {
            "frame_count": frame_count,
            "fps": fps,
            "width": width,
            "height": height,
            "decoded_frame_index": frame_index,
            "color_order_supplied_to_policy": "RGB",
        }
    finally:
        capture.release()


def _extract_table_sample(manifest: dict[str, Any], manifest_path: pathlib.Path) -> dict[str, Any]:
    import pyarrow.parquet as pq

    parquet_path = manifest_path.parent / manifest["staged_parquet"]
    video_path = manifest_path.parent / manifest["staged_video"]
    if sha256_file(parquet_path) != manifest["source"]["parquet_sha256"]:
        raise ValueError("staged parquet SHA-256 mismatch")
    if sha256_file(video_path) != manifest["source"]["video_sha256"]:
        raise ValueError("staged video SHA-256 mismatch")

    table = pq.read_table(parquet_path)
    required_columns = {
        "observation.state",
        "action",
        "episode_index",
        "task_index",
        "timestamp",
    }
    missing = sorted(required_columns - set(table.column_names))
    if missing:
        raise ValueError(f"parquet is missing columns: {missing}")
    requested_frame = int(manifest["frame_index"])
    if "frame_index" in table.column_names:
        frame_values = [int(value) for value in table.column("frame_index").to_pylist()]
        try:
            row_index = frame_values.index(requested_frame)
        except ValueError as exc:
            raise ValueError("requested frame_index is absent from parquet") from exc
        frame_index_source = "parquet.frame_index"
    else:
        # The supplied info.json advertises frame_index, but the inspected
        # episode parquets omit it.  Their row order starts at timestamp zero
        # and advances exactly at 120 Hz, so row index is the auditable fallback.
        row_index = requested_frame
        if row_index < 0 or row_index >= table.num_rows:
            raise ValueError("requested row-derived frame index is out of range")
        timestamps = [float(value) for value in table.column("timestamp").to_pylist()]
        expected_timestamp = requested_frame / 120.0
        if abs(timestamps[row_index] - expected_timestamp) > 1e-6:
            raise ValueError(
                "frame_index is absent and row/timestamp does not match the 120 Hz timeline"
            )
        frame_index_source = "row_index_validated_by_timestamp_120hz"
    if row_index + 10 > table.num_rows:
        raise ValueError("parquet cannot provide ten action rows")

    episode_values = {int(value) for value in table.column("episode_index").to_pylist()}
    task_values = {int(value) for value in table.column("task_index").to_pylist()}
    if episode_values != {int(manifest["episode_index"])}:
        raise ValueError(f"unexpected episode indices in parquet: {sorted(episode_values)}")
    if task_values != {int(manifest["task_id"])}:
        raise ValueError(f"unexpected task indices in parquet: {sorted(task_values)}")

    state32 = [float(value) for value in table.column("observation.state")[row_index].as_py()]
    if len(state32) != 32 or not all(math.isfinite(value) for value in state32):
        raise ValueError("observation.state must contain 32 finite values")
    state20 = state32[:20]
    ground_truth = _finite_matrix(
        [table.column("action")[row].as_py() for row in range(row_index, row_index + 10)],
        10,
        20,
        "ground_truth_action",
    )
    image, video_info = _read_video_frame(video_path, int(manifest["frame_index"]))
    return {
        "state20": state20,
        "force_torque12": state32[20:],
        "ground_truth": ground_truth,
        "image": image,
        "video_info": video_info,
        "frame_index_source": frame_index_source,
        "timestamp": float(table.column("timestamp")[row_index].as_py()),
        "parquet_rows": int(table.num_rows),
    }


def _policy_sample(sample: dict[str, Any], task_text: str) -> dict[str, Any]:
    import numpy as np

    state = np.asarray(sample["state20"], dtype=np.float64)
    result: dict[str, Any] = {
        "video.rgb": np.expand_dims(np.asarray(sample["image"], dtype=np.uint8), axis=0),
        "annotation.human.action.task_description": [task_text],
    }
    for key, (start, end) in STATE_PARTS.items():
        result[f"state.{key}"] = np.expand_dims(state[start:end], axis=0)
    return result


def _metrics(
    predicted: Sequence[Sequence[float]],
    ground_truth: Sequence[Sequence[float]],
    state: Sequence[float],
    profile: dict[str, Any],
) -> dict[str, Any]:
    import numpy as np

    pred = np.asarray(predicted, dtype=np.float64)
    truth = np.asarray(ground_truth, dtype=np.float64)
    current = np.asarray(state, dtype=np.float64)
    error = pred - truth
    first_delta = np.abs(pred[0] - current)
    lower = np.asarray(profile["lower_boundary"], dtype=np.float64)
    upper = np.asarray(profile["upper_boundary"], dtype=np.float64)
    delta_limits = np.asarray(profile["max_first_point_delta"], dtype=np.float64)
    tolerance = float(profile["range_tolerance"])
    range_violations = []
    for row_index, row in enumerate(pred):
        for joint_index, value in enumerate(row):
            if value < lower[joint_index] - tolerance or value > upper[joint_index] + tolerance:
                range_violations.append(
                    {
                        "point": row_index,
                        "joint": profile["joint_names"][joint_index],
                        "value": float(value),
                        "lower": float(lower[joint_index]),
                        "upper": float(upper[joint_index]),
                    }
                )
    first_delta_violations = [
        {
            "joint": profile["joint_names"][index],
            "delta": float(first_delta[index]),
            "limit": float(delta_limits[index]),
        }
        for index in range(20)
        if first_delta[index] > delta_limits[index]
    ]
    return {
        "mae": float(np.mean(np.abs(error))),
        "mse": float(np.mean(error ** 2)),
        "first_point_mae": float(np.mean(np.abs(error[0]))),
        "per_joint_mae": {
            name: float(value)
            for name, value in zip(profile["joint_names"], np.mean(np.abs(error), axis=0))
        },
        "per_horizon_mae": [float(value) for value in np.mean(np.abs(error), axis=1)],
        "max_first_point_delta": {
            "joint": profile["joint_names"][int(np.argmax(first_delta))],
            "value": float(np.max(first_delta)),
        },
        "first_point_delta_violations": first_delta_violations,
        "range_violations": range_violations,
    }


def _flag_value(action_chunk: dict[str, Any]) -> float | None:
    if "flag_pred" not in action_chunk:
        return None
    value = action_chunk["flag_pred"]
    if hasattr(value, "detach"):
        value = value.detach().float().cpu().reshape(-1)[0].item()
    elif hasattr(value, "item"):
        value = value.item()
    return float(value)


def _campaign_aggregates(
    results: Sequence[dict[str, Any]], profile: dict[str, Any], seed0_repetitions: int
) -> dict[str, Any]:
    import numpy as np

    aggregates: dict[str, Any] = {}
    for task_id in sorted(TASKS):
        task_runs = [row for row in results if int(row["task_id"]) == task_id]
        baseline = [row for row in task_runs if int(row["repetition_index"]) == 0]
        seed0_runs = [row for row in task_runs if int(row["seed"]) == 0]
        if len(baseline) != len(CAMPAIGN_SEEDS):
            raise ValueError(f"task {task_id} does not contain five unique-seed baselines")
        if {int(row["seed"]) for row in baseline} != set(CAMPAIGN_SEEDS):
            raise ValueError(f"task {task_id} baseline seeds are incomplete")
        if len(seed0_runs) != seed0_repetitions:
            raise ValueError(f"task {task_id} seed 0 repetition count is incorrect")
        baseline_mae = np.asarray([row["metrics"]["mae"] for row in baseline], dtype=float)
        baseline_mse = np.asarray([row["metrics"]["mse"] for row in baseline], dtype=float)
        joint_values = np.asarray(
            [
                [row["metrics"]["per_joint_mae"][name] for name in profile["joint_names"]]
                for row in baseline
            ],
            dtype=float,
        )
        horizon_values = np.asarray(
            [row["metrics"]["per_horizon_mae"] for row in baseline], dtype=float
        )
        repeat_reference = np.asarray(seed0_runs[0]["predicted_action_10x20"], dtype=float)
        repeat_differences = [
            float(
                np.max(
                    np.abs(
                        np.asarray(row["predicted_action_10x20"], dtype=float)
                        - repeat_reference
                    )
                )
            )
            for row in seed0_runs
        ]
        aggregates[str(task_id)] = {
            "task_text": TASKS[task_id],
            "unique_seed_count": len(baseline),
            "unique_episode_count": len({int(row["episode_index"]) for row in baseline}),
            "total_inference_run_count": len(task_runs),
            "baseline_mae": {
                "mean": float(np.mean(baseline_mae)),
                "min": float(np.min(baseline_mae)),
                "max": float(np.max(baseline_mae)),
            },
            "baseline_mse": {
                "mean": float(np.mean(baseline_mse)),
                "min": float(np.min(baseline_mse)),
                "max": float(np.max(baseline_mse)),
            },
            "per_joint_mae_mean": {
                name: float(value)
                for name, value in zip(profile["joint_names"], np.mean(joint_values, axis=0))
            },
            "per_horizon_mae_mean": [
                float(value) for value in np.mean(horizon_values, axis=0)
            ],
            "baseline_runs_with_range_violations": sum(
                bool(row["metrics"]["range_violations"]) for row in baseline
            ),
            "baseline_runs_with_first_point_delta_violations": sum(
                bool(row["metrics"]["first_point_delta_violations"]) for row in baseline
            ),
            "seed0_repeatability": {
                "total_runs": len(seed0_runs),
                "max_abs_prediction_difference_vs_rep0_by_run": repeat_differences,
                "max_abs_prediction_difference": max(repeat_differences),
                "bitwise_numeric_repeatability_observed": max(repeat_differences) == 0.0,
            },
        }
    return aggregates


def command_infer(args: argparse.Namespace) -> int:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    checkpoint = pathlib.Path(args.checkpoint).resolve()
    profile_path = pathlib.Path(args.profile).resolve()
    output_dir = pathlib.Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    profile = load_json(profile_path)
    if int(profile["action_dim"]) != 20 or int(profile["action_horizon"]) != 10:
        raise ValueError("profile must be 10x20")
    campaign: dict[str, Any] | None = None
    split_audit: dict[str, Any] | None = None
    if args.campaign_manifest:
        campaign_path = pathlib.Path(args.campaign_manifest).resolve()
        campaign = load_json(campaign_path)
        if campaign.get("campaign_id") != "E3.0":
            raise ValueError("offline campaign must be E3.0")
        if campaign.get("tasks") != sorted(TASKS) or campaign.get("seeds") != list(
            CAMPAIGN_SEEDS
        ):
            raise ValueError("E3.0 campaign task/seed matrix is incomplete")
        campaign_parent = campaign_path.parent
        manifests = []
        for entry in campaign.get("sample_manifests", []):
            candidate = (campaign_parent / entry["manifest"]).resolve()
            if campaign_parent != candidate and campaign_parent not in candidate.parents:
                raise ValueError("campaign sample manifest escapes its staging directory")
            manifests.append(candidate)
        if len(manifests) != 20 or len(set(manifests)) != 20:
            raise ValueError("E3.0 campaign must contain 20 distinct sample manifests")
        split_path = (campaign_parent / campaign["split_audit"]).resolve()
        if sha256_file(split_path) != campaign["split_audit_sha256"]:
            raise ValueError("campaign split audit SHA-256 mismatch")
        split_audit = load_json(split_path)
        if split_audit.get("global_train_test_overlap") != []:
            raise ValueError("campaign split audit contains train/test overlap")
        if split_audit.get("selected_episodes_all_in_project_test") is not True:
            raise ValueError("campaign selected a non-test episode")
        seed0_repetitions = int(campaign["seed0_total_repetitions_per_task"])
        if seed0_repetitions != 5:
            raise ValueError("E3.0 requires five total seed-0 runs per task")
    else:
        manifests = [pathlib.Path(path).resolve() for path in args.sample_manifest]
        if not manifests:
            raise ValueError("at least one sample manifest is required")
        seed0_repetitions = 1

    override_parent = pathlib.Path(args.override_parent).resolve()
    sys.path.insert(0, str(override_parent))
    import numpy as np
    import torch
    import gr00t
    from gr00t.data.embodiment_tags import EmbodimentTag
    from gr00t.experiment.data_config import Utars_1RGBDataConfig
    from gr00t.model.policy import Gr00tPolicy

    if override_parent not in pathlib.Path(gr00t.__file__).resolve().parents:
        raise ImportError(f"GR00T overlay is not active: {gr00t.__file__}")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable in offline inference container")
    torch.manual_seed(int(args.seed))
    np.random.seed(int(args.seed))
    started_load = time.monotonic()
    data_config = Utars_1RGBDataConfig()
    policy = Gr00tPolicy(
        model_path=str(checkpoint),
        modality_config=data_config.modality_config(),
        modality_transform=data_config.transform(),
        embodiment_tag=EmbodimentTag.NEW_EMBODIMENT,
        denoising_steps=4,
        device="cuda",
    )
    load_seconds = time.monotonic() - started_load

    results = []
    try:
        for manifest_path in manifests:
            manifest = load_json(manifest_path)
            if int(manifest["task_id"]) not in TASKS:
                raise ValueError("manifest contains an unsupported task")
            if campaign is None and int(manifest["task_id"]) not in PLACE_TASK_IDS:
                raise ValueError("non-campaign inference only supports PLACE tasks")
            if manifest["task_text"] != TASKS[int(manifest["task_id"])]:
                raise ValueError("manifest task text does not match task ID")
            table_sample = _extract_table_sample(manifest, manifest_path)
            repetitions = (
                seed0_repetitions
                if campaign is not None and int(manifest["seed"]) == 0
                else 1
            )
            for repetition_index in range(repetitions):
                torch.manual_seed(int(manifest["seed"]))
                np.random.seed(int(manifest["seed"]))
                started_inference = time.monotonic()
                action_chunk = policy.get_action(
                    _policy_sample(table_sample, manifest["task_text"])
                )
                inference_seconds = time.monotonic() - started_inference
                predicted = _flatten_prediction(action_chunk)
                metrics = _metrics(
                    predicted,
                    table_sample["ground_truth"],
                    table_sample["state20"],
                    profile,
                )
                sample_id = manifest.get("sample_id", f"task{manifest['task_id']}")
                run_id = (
                    f"{sample_id}_rep{repetition_index}"
                    if campaign is not None
                    else sample_id
                )
                result = {
                    "run_id": run_id,
                    "sample_id": sample_id,
                    "task_id": int(manifest["task_id"]),
                    "task_text": manifest["task_text"],
                    "seed": int(manifest["seed"]),
                    "repetition_index": repetition_index,
                    "episode_index": int(manifest["episode_index"]),
                    "frame_index": int(manifest["frame_index"]),
                    "phase_fraction": manifest.get("phase_fraction"),
                    "initial_state_semantics": manifest["initial_state_semantics"],
                    "split_definition": manifest["split_definition"],
                    "input": {
                        "state20": table_sample["state20"],
                        "force_torque12": table_sample["force_torque12"],
                        "timestamp": table_sample["timestamp"],
                        "parquet_rows": table_sample["parquet_rows"],
                        "video": table_sample["video_info"],
                        "frame_index_source": table_sample["frame_index_source"],
                        "parquet_sha256": manifest["source"]["parquet_sha256"],
                        "video_sha256": manifest["source"]["video_sha256"],
                    },
                    "predicted_action_10x20": predicted,
                    "predicted_action_sha256": hashlib.sha256(
                        json.dumps(predicted, separators=(",", ":")).encode("utf-8")
                    ).hexdigest(),
                    "ground_truth_action_10x20": table_sample["ground_truth"],
                    "flag_pred": _flag_value(action_chunk),
                    "metrics": metrics,
                    "inference_seconds": inference_seconds,
                    "verdict": (
                        "PASS_OFFLINE_INFERENCE_WITH_CONSERVATIVE_VIOLATIONS"
                        if metrics["range_violations"]
                        or metrics["first_point_delta_violations"]
                        else "PASS_OFFLINE_INFERENCE_CONSERVATIVE_CHECKS_CLEAR"
                    ),
                    "physical_task_success_evaluated": False,
                }
                task_output = (
                    output_dir / "runs" / f"{run_id}.json"
                    if campaign is not None
                    else output_dir / f"task{result['task_id']}_result.json"
                )
                write_json_exclusive(task_output, result)
                results.append(result)
                print(
                    f"OFFLINE_TASK_RESULT=run:{run_id},task:{result['task_id']},"
                    f"episode:{result['episode_index']},frame:{result['frame_index']},"
                    f"mae:{metrics['mae']:.9f},verdict:{result['verdict']}"
                )
    finally:
        del policy
        torch.cuda.empty_cache()

    summary: dict[str, Any] = {
        "schema": (
            "cruzr-s2-vla-offline-e3.0-v1"
            if campaign is not None
            else "cruzr-s2-vla-offline-e2.2-v1"
        ),
        "mode": "offline_network_none_no_ros_no_robot",
        "checkpoint": {
            "path": str(checkpoint),
            "config_sha256": sha256_file(checkpoint / "config.json"),
            "index_sha256": sha256_file(checkpoint / "model.safetensors.index.json"),
        },
        "profile_sha256": sha256_file(profile_path),
        "gr00t_overlay": str(pathlib.Path(gr00t.__file__).resolve()),
        "cuda_device": torch.cuda.get_device_name(0),
        "model_load_seconds": load_seconds,
        "seed": int(args.seed),
        "samples": results,
        "physical_movement_commanded": False,
        "robot_state_read": False,
        "network_available": False,
    }
    if campaign is not None and split_audit is not None:
        summary.update(
            {
                "campaign_id": "E3.0",
                "campaign_selection_sha256": sha256_file(
                    pathlib.Path(args.campaign_manifest).resolve()
                ),
                "split_audit_sha256": campaign["split_audit_sha256"],
                "split_train_test_overlap": split_audit["global_train_test_overlap"],
                "checkpoint_training_membership_known": False,
                "generalization_claim_allowed": False,
                "unique_sample_count": int(campaign["unique_sample_count"]),
                "inference_run_count": len(results),
                "seed0_total_repetitions_per_task": seed0_repetitions,
                "aggregates": _campaign_aggregates(
                    results, profile, seed0_repetitions
                ),
            }
        )
    write_json_exclusive(output_dir / "summary.json", summary)
    if campaign is not None:
        print(
            f"OFFLINE_E3_0_COMPLETE=samples:{campaign['unique_sample_count']},"
            f"runs:{len(results)},movement:none,network:none"
        )
    else:
        print(f"OFFLINE_E2_2_COMPLETE=samples:{len(results)},movement:none,network:none")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    select_parser = subparsers.add_parser("select", help="select a deterministic PLACE sample")
    select_parser.add_argument("--dataset", required=True)
    select_parser.add_argument("--task-id", type=int, choices=PLACE_TASK_IDS, required=True)
    select_parser.add_argument("--split", choices=("test",), default="test")
    select_parser.add_argument("--seed", type=int, default=0)
    select_parser.add_argument("--frame-index", type=int, default=0)
    select_parser.add_argument("--output", required=True)
    select_parser.set_defaults(func=command_select)

    campaign_parser = subparsers.add_parser(
        "campaign", help="select the complete deterministic E3.0 campaign"
    )
    campaign_parser.add_argument("--dataset", required=True)
    campaign_parser.add_argument("--seed0-repetitions", type=int, choices=(5,), default=5)
    campaign_parser.add_argument("--output-dir", required=True)
    campaign_parser.set_defaults(func=command_campaign)

    infer_parser = subparsers.add_parser("infer", help="run model inference over staged samples")
    infer_parser.add_argument("--checkpoint", required=True)
    infer_parser.add_argument("--profile", required=True)
    infer_parser.add_argument("--override-parent", required=True)
    manifest_group = infer_parser.add_mutually_exclusive_group(required=True)
    manifest_group.add_argument("--sample-manifest", action="append")
    manifest_group.add_argument("--campaign-manifest")
    infer_parser.add_argument("--output-dir", required=True)
    infer_parser.add_argument("--seed", type=int, default=0)
    infer_parser.set_defaults(func=command_infer)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
