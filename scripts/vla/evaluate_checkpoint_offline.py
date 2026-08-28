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
    manifests = [pathlib.Path(path).resolve() for path in args.sample_manifest]
    if not manifests:
        raise ValueError("at least one sample manifest is required")

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
                raise ValueError("manifest contains a non-PLACE task")
            if manifest["task_text"] != TASKS[int(manifest["task_id"])]:
                raise ValueError("manifest task text does not match task ID")
            table_sample = _extract_table_sample(manifest, manifest_path)
            torch.manual_seed(int(manifest["seed"]))
            np.random.seed(int(manifest["seed"]))
            started_inference = time.monotonic()
            action_chunk = policy.get_action(_policy_sample(table_sample, manifest["task_text"]))
            inference_seconds = time.monotonic() - started_inference
            predicted = _flatten_prediction(action_chunk)
            metrics = _metrics(
                predicted,
                table_sample["ground_truth"],
                table_sample["state20"],
                profile,
            )
            result = {
                "task_id": int(manifest["task_id"]),
                "task_text": manifest["task_text"],
                "episode_index": int(manifest["episode_index"]),
                "frame_index": int(manifest["frame_index"]),
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
                "ground_truth_action_10x20": table_sample["ground_truth"],
                "flag_pred": _flag_value(action_chunk),
                "metrics": metrics,
                "inference_seconds": inference_seconds,
                "verdict": (
                    "PASS_OFFLINE_INFERENCE_WITH_CONSERVATIVE_VIOLATIONS"
                    if metrics["range_violations"] or metrics["first_point_delta_violations"]
                    else "PASS_OFFLINE_INFERENCE_CONSERVATIVE_CHECKS_CLEAR"
                ),
                "physical_task_success_evaluated": False,
            }
            task_output = output_dir / f"task{result['task_id']}_result.json"
            write_json_exclusive(task_output, result)
            results.append(result)
            print(
                f"OFFLINE_TASK_RESULT=task:{result['task_id']},episode:{result['episode_index']},"
                f"mae:{metrics['mae']:.9f},verdict:{result['verdict']}"
            )
    finally:
        del policy
        torch.cuda.empty_cache()

    summary = {
        "schema": "cruzr-s2-vla-offline-e2.2-v1",
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
    write_json_exclusive(output_dir / "summary.json", summary)
    print(f"OFFLINE_E2_2_COMPLETE=samples:{len(results)},movement:none,network:none")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    select_parser = subparsers.add_parser("select", help="select a deterministic PLACE sample")
    select_parser.add_argument("--dataset", required=True)
    select_parser.add_argument("--task-id", type=int, choices=sorted(TASKS), required=True)
    select_parser.add_argument("--split", choices=("test",), default="test")
    select_parser.add_argument("--seed", type=int, default=0)
    select_parser.add_argument("--frame-index", type=int, default=0)
    select_parser.add_argument("--output", required=True)
    select_parser.set_defaults(func=command_select)

    infer_parser = subparsers.add_parser("infer", help="run model inference over staged samples")
    infer_parser.add_argument("--checkpoint", required=True)
    infer_parser.add_argument("--profile", required=True)
    infer_parser.add_argument("--override-parent", required=True)
    infer_parser.add_argument("--sample-manifest", action="append", required=True)
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
