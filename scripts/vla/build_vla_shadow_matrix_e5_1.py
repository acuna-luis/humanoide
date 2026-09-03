#!/usr/bin/env python3
"""Build one E5.1 profile/task cell from frozen E3.0 inference outputs."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import pathlib
import statistics
import sys
from typing import Any, Sequence


TASKS = {
    0: ("SUPPORTED_LOW", "Pick up the large box from the lowest level of shelf"),
    1: ("HELD_LOW", "Place the large box on the lowest level of shelf"),
    2: ("SUPPORTED_MIDDLE", "Pick up the large box from the middle level of shelf"),
    3: ("HELD_MIDDLE", "Place the large box on the middle level of shelf"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-campaign", type=pathlib.Path, required=True)
    parser.add_argument("--scenario", choices=tuple(value[0] for value in TASKS.values()), required=True)
    parser.add_argument("--task-id", type=int, choices=tuple(TASKS), required=True)
    parser.add_argument("--axis-profile", required=True)
    parser.add_argument("--repetitions", type=int, choices=(5,), required=True)
    parser.add_argument("--profile", type=pathlib.Path, required=True)
    parser.add_argument("--sink", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    return parser.parse_args()


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_json(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def load_json(path: pathlib.Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def load_sink(path: pathlib.Path):
    spec = importlib.util.spec_from_file_location("vla_executor_sink_e5_1", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load sink definitions: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_matrix(value: Any, label: str) -> list[list[float]]:
    if not isinstance(value, list) or len(value) != 10:
        raise ValueError(f"{label} must contain 10 rows")
    matrix: list[list[float]] = []
    for row_index, source_row in enumerate(value):
        if not isinstance(source_row, list) or len(source_row) != 20:
            raise ValueError(f"{label}[{row_index}] must contain 20 values")
        row = [float(item) for item in source_row]
        if not all(math.isfinite(item) for item in row):
            raise ValueError(f"{label}[{row_index}] contains non-finite values")
        matrix.append(row)
    return matrix


def validate_vector(value: Any, label: str) -> list[float]:
    if not isinstance(value, list) or len(value) != 20:
        raise ValueError(f"{label} must contain 20 values")
    vector = [float(item) for item in value]
    if not all(math.isfinite(item) for item in vector):
        raise ValueError(f"{label} contains non-finite values")
    return vector


def mean_absolute_error(left: Sequence[Sequence[float]], right: Sequence[Sequence[float]], indices: Sequence[int]) -> float | None:
    values = [abs(left[row][index] - right[row][index]) for row in range(10) for index in indices]
    return statistics.fmean(values) if values else None


def make_bundle(
    *,
    source_path: pathlib.Path,
    source: dict[str, Any],
    profile: dict[str, Any],
    module: Any,
    scenario: str,
    task_id: int,
    axis_profile: str,
    repetition: int,
) -> dict[str, Any]:
    expected_text = TASKS[task_id][1]
    if source.get("task_id") != task_id or source.get("task_text") != expected_text:
        raise ValueError(f"source task identity mismatch: {source_path}")
    if source.get("seed") != repetition - 1 or source.get("repetition_index") != 0:
        raise ValueError(f"source seed/repetition mismatch: {source_path}")
    raw = validate_matrix(source.get("predicted_action_10x20"), "predicted_action_10x20")
    truth = validate_matrix(source.get("ground_truth_action_10x20"), "ground_truth_action_10x20")
    state = validate_vector(source.get("input", {}).get("state20"), "input.state20")
    enabled = tuple(module.enabled_indices(axis_profile))
    enabled_set = set(enabled)
    locked = tuple(index for index in range(20) if index not in enabled_set)
    effective = [
        [value if index in enabled_set else state[index] for index, value in enumerate(row)]
        for row in raw
    ]

    enabled_copy_ok = all(effective[row][index] == raw[row][index] for row in range(10) for index in enabled)
    locked_hold_ok = all(effective[row][index] == state[index] for row in range(10) for index in locked)
    lower = [float(value) for value in profile["lower_boundary"]]
    upper = [float(value) for value in profile["upper_boundary"]]
    range_tolerance = float(profile["range_tolerance"])
    delta_limits = [float(value) for value in profile["max_first_point_delta"]]
    speed_limits = [float(value) for value in profile["max_interpoint_speed"]]
    point_dt = float(profile["point_dt_seconds"])

    range_violations = [
        {
            "point": row,
            "joint_index": index,
            "joint": profile["joint_names"][index],
            "value": effective[row][index],
            "lower": lower[index],
            "upper": upper[index],
        }
        for row in range(10)
        for index in enabled
        if effective[row][index] < lower[index] - range_tolerance
        or effective[row][index] > upper[index] + range_tolerance
    ]
    first_point_delta_violations = [
        {
            "joint_index": index,
            "joint": profile["joint_names"][index],
            "delta": abs(effective[0][index] - state[index]),
            "limit": delta_limits[index],
        }
        for index in enabled
        if abs(effective[0][index] - state[index]) > delta_limits[index]
    ]
    speed_violations = [
        {
            "point": row,
            "joint_index": index,
            "joint": profile["joint_names"][index],
            "speed": abs(effective[row][index] - effective[row - 1][index]) / point_dt,
            "limit": speed_limits[index],
        }
        for row in range(1, 10)
        for index in enabled
        if abs(effective[row][index] - effective[row - 1][index]) / point_dt
        > speed_limits[index]
    ]
    rejection_reasons: list[str] = []
    if range_violations:
        rejection_reasons.append(f"enabled_range_violations:{len(range_violations)}")
    if first_point_delta_violations:
        rejection_reasons.append(
            f"enabled_first_point_delta_violations:{len(first_point_delta_violations)}"
        )
    if speed_violations:
        rejection_reasons.append(f"enabled_speed_violations:{len(speed_violations)}")
    if not enabled_copy_ok or not locked_hold_ok:
        rejection_reasons.append("mask_contract_failed")

    return {
        "schema": "cruzr-s2-vla-shadow-profile-bundle-e5.1-v1",
        "experiment_id": "E5.1",
        "mode": "offline_shadow_replay_no_robot_no_ros_no_publisher",
        "scenario_id": scenario,
        "scenario_semantics": "recorded_dataset_frame_not_live_fixture",
        "task_id": task_id,
        "task_text": expected_text,
        "axis_profile": axis_profile,
        "enabled_indices": list(enabled),
        "locked_indices": list(locked),
        "repetition": repetition,
        "seed": repetition - 1,
        "source_result": str(source_path),
        "source_result_sha256": sha256_file(source_path),
        "source_run_id": source.get("run_id"),
        "source_episode_index": source.get("episode_index"),
        "source_frame_index": source.get("frame_index"),
        "source_phase_fraction": source.get("phase_fraction"),
        "source_split_definition": source.get("split_definition"),
        "source_checkpoint_verdict": source.get("verdict"),
        "input": source.get("input"),
        "initial_state_semantics": source.get("initial_state_semantics"),
        "initial_state20": state,
        "raw_prediction_10x20": raw,
        "raw_prediction_sha256": sha256_json(raw),
        "effective_prediction_10x20": effective,
        "effective_prediction_sha256": sha256_json(effective),
        "ground_truth_action_10x20": truth,
        "mask_checks": {
            "enabled_axes_copy_raw_prediction": enabled_copy_ok,
            "locked_axes_hold_recorded_initial_state": locked_hold_ok,
            "locked_hold_source": "recorded_dataset_state20",
        },
        "metrics": {
            "raw_mae_all_axes": mean_absolute_error(raw, truth, tuple(range(20))),
            "effective_mae_all_axes": mean_absolute_error(effective, truth, tuple(range(20))),
            "effective_mae_enabled_axes": mean_absolute_error(effective, truth, enabled),
            "effective_mae_locked_axes": mean_absolute_error(effective, truth, locked),
            "mask_delta_from_raw_all_axes": mean_absolute_error(effective, raw, tuple(range(20))),
            "inference_seconds_source": source.get("inference_seconds"),
            "range_violations": range_violations,
            "first_point_delta_violations": first_point_delta_violations,
            "speed_violations": speed_violations,
            "continuity_between_independent_samples": "NOT_APPLICABLE",
            "gpu_vram": "NOT_CAPTURED_BY_SOURCE_E3.0",
            "runtime_frequency": "NOT_CAPTURED_BY_SOURCE_E3.0",
            "flag_pred": source.get("flag_pred"),
        },
        "verdict": "ACCEPT_STRUCTURAL" if not rejection_reasons else "REJECT_SAFE",
        "rejection_reasons": rejection_reasons,
        "physical_task_success_evaluated": False,
        "robot_state_read_live": False,
        "physical_publisher_count": 0,
        "physical_movement_commanded": False,
    }


def main() -> int:
    args = parse_args()
    source_campaign = args.source_campaign.resolve()
    profile_path = args.profile.resolve()
    sink_path = args.sink.resolve()
    output = args.output.resolve()
    expected_scenario, expected_text = TASKS[args.task_id]
    if args.scenario != expected_scenario:
        raise SystemExit(
            f"ERROR: task {args.task_id} requires scenario {expected_scenario}, got {args.scenario}"
        )
    if output == pathlib.Path("/"):
        raise SystemExit("ERROR: output cannot be /")
    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"ERROR: output must be empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    bundle_dir = output / "bundles"
    bundle_dir.mkdir()

    module = load_sink(sink_path)
    if args.axis_profile not in module.AXIS_PROFILES:
        raise SystemExit(f"ERROR: unknown axis profile: {args.axis_profile}")
    profile = module.load_profile(profile_path)
    bundles: list[dict[str, Any]] = []
    for repetition in range(1, args.repetitions + 1):
        seed = repetition - 1
        source_path = source_campaign / "results" / "runs" / f"task{args.task_id}_seed{seed}_rep0.json"
        if not source_path.is_file():
            raise SystemExit(f"ERROR: missing frozen inference result: {source_path}")
        bundle = make_bundle(
            source_path=source_path,
            source=load_json(source_path),
            profile=profile,
            module=module,
            scenario=args.scenario,
            task_id=args.task_id,
            axis_profile=args.axis_profile,
            repetition=repetition,
        )
        bundle_path = bundle_dir / f"rep_{repetition:02d}.json"
        bundle_path.write_text(
            json.dumps(bundle, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        bundles.append(bundle)

    summary = {
        "schema": "cruzr-s2-vla-shadow-profile-cell-e5.1-v1",
        "experiment_id": "E5.1",
        "mode": "offline_shadow_replay_no_robot_no_ros_no_publisher",
        "scenario_id": args.scenario,
        "scenario_semantics": "recorded_dataset_frame_not_live_fixture",
        "task_id": args.task_id,
        "task_text": expected_text,
        "axis_profile": args.axis_profile,
        "enabled_axis_count": len(module.enabled_indices(args.axis_profile)),
        "locked_axis_count": 20 - len(module.enabled_indices(args.axis_profile)),
        "repetitions": args.repetitions,
        "bundle_count": len(bundles),
        "accepted_count": sum(bundle["verdict"] == "ACCEPT_STRUCTURAL" for bundle in bundles),
        "rejected_safe_count": sum(bundle["verdict"] == "REJECT_SAFE" for bundle in bundles),
        "mask_contract_pass_count": sum(
            bundle["mask_checks"]["enabled_axes_copy_raw_prediction"]
            and bundle["mask_checks"]["locked_axes_hold_recorded_initial_state"]
            for bundle in bundles
        ),
        "mean_raw_mae_all_axes": statistics.fmean(
            bundle["metrics"]["raw_mae_all_axes"] for bundle in bundles
        ),
        "mean_effective_mae_all_axes": statistics.fmean(
            bundle["metrics"]["effective_mae_all_axes"] for bundle in bundles
        ),
        "mean_mask_delta_from_raw_all_axes": statistics.fmean(
            bundle["metrics"]["mask_delta_from_raw_all_axes"] for bundle in bundles
        ),
        "source_campaign": str(source_campaign),
        "profile_sha256": sha256_file(profile_path),
        "sink_sha256": sha256_file(sink_path),
        "physical_task_success_evaluated": False,
        "robot_state_read_live": False,
        "network_calls": 0,
        "physical_publishers": 0,
        "physical_movement_commanded": False,
        "all_bundles_accounted": len(bundles) == args.repetitions,
    }
    (output / "cell_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"E5.1_CELL={args.task_id}/{args.axis_profile},"
        f"accepted:{summary['accepted_count']},rejected_safe:{summary['rejected_safe_count']},"
        f"mask:{summary['mask_contract_pass_count']}/{summary['bundle_count']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
