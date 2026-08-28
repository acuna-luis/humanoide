#!/usr/bin/env python3
"""Build and evaluate the image-space E3.1 OOD proxy campaign.

This tool never imports ROS or robot command messages. Metric scene transforms
remain blocked because the supplied dataset contains RGB only: no depth,
intrinsics, object mask, shelf plane, or camera/object pose is provided.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import pathlib
import sys
import time
from typing import Any, Sequence


SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
BASE_EVALUATOR_PATH = SCRIPT_DIR / "evaluate_checkpoint_offline.py"
BASE_SPEC = importlib.util.spec_from_file_location(
    "cruzr_vla_offline_base", BASE_EVALUATOR_PATH
)
if not BASE_SPEC or not BASE_SPEC.loader:
    raise ImportError(f"cannot load {BASE_EVALUATOR_PATH}")
BASE = importlib.util.module_from_spec(BASE_SPEC)
BASE_SPEC.loader.exec_module(BASE)

TASK_IDS = (0, 2)
SOURCE_SELECTION_SEED = 2
PROXY_AXES = (
    {
        "name": "horizontal_frame_shift_fraction",
        "units": "fraction_of_image_width",
        "values": (-0.10, -0.05, 0.0, 0.05, 0.10),
        "nominal": 0.0,
        "interpretation": "global camera-frame horizontal shift; not object x in metres",
    },
    {
        "name": "global_zoom_factor",
        "units": "dimensionless_scale",
        "values": (0.90, 1.0, 1.10),
        "nominal": 1.0,
        "interpretation": "global optical-scale proxy; not front-face shelf depth",
    },
    {
        "name": "global_perspective_yaw_proxy_deg",
        "units": "degrees_proxy_parameter",
        "values": (-15.0, -5.0, 0.0, 5.0, 15.0),
        "nominal": 0.0,
        "interpretation": "whole-frame trapezoid proxy; not object yaw in 3D",
    },
)


def _write_json(path: pathlib.Path, value: Any) -> None:
    BASE.write_json_exclusive(path, value)


def _sample_id(task_id: int, axis_index: int, value_index: int) -> str:
    return f"task{task_id}_axis{axis_index}_value{value_index}"


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
    episodes = BASE.load_episode_catalog(episodes_path)
    metadata_hashes = {
        "info_sha256": BASE.sha256_file(info_path),
        "tasks_sha256": BASE.sha256_file(tasks_path),
        "episodes_sha256": BASE.sha256_file(episodes_path),
    }

    entries: list[dict[str, Any]] = []
    base_samples: dict[str, Any] = {}
    for task_id in TASK_IDS:
        selected, _, held_out_count = BASE.select_campaign_episode(
            episodes, task_id, SOURCE_SELECTION_SEED
        )
        episode_index = int(selected["episode_index"])
        episode_length = int(selected["length"])
        frame_index = int(round((episode_length - 10) * 0.5))
        parquet, video = BASE.episode_paths(dataset, episode_index)
        for required in (parquet, video):
            if not required.is_file() or required.stat().st_size == 0:
                raise FileNotFoundError(required)
        source_hashes = {
            **metadata_hashes,
            "parquet_sha256": BASE.sha256_file(parquet),
            "video_sha256": BASE.sha256_file(video),
        }
        base_samples[str(task_id)] = {
            "task_text": BASE.TASKS[task_id],
            "source_selection_seed": SOURCE_SELECTION_SEED,
            "episode_index": episode_index,
            "episode_length": episode_length,
            "frame_index": frame_index,
            "phase_fraction": 0.5,
            "held_out_episode_count": held_out_count,
            "parquet_sha256": source_hashes["parquet_sha256"],
            "video_sha256": source_hashes["video_sha256"],
        }
        for axis_index, axis in enumerate(PROXY_AXES):
            for value_index, value in enumerate(axis["values"]):
                sample_id = _sample_id(task_id, axis_index, value_index)
                relative_manifest = pathlib.Path("samples") / sample_id / "selection.json"
                manifest = {
                    "schema": "cruzr-s2-vla-offline-ood-sample-v1",
                    "mode": "offline_dataset_image_proxy_only_no_robot",
                    "campaign_id": "E3.1",
                    "sample_id": sample_id,
                    "task_id": task_id,
                    "task_text": BASE.TASKS[task_id],
                    "episode_index": episode_index,
                    "episode_length": episode_length,
                    "frame_index": frame_index,
                    "phase_fraction": 0.5,
                    "initial_state_semantics": "DATASET_REPLAY_FIXED_TASK_STATE_FRAME",
                    "split_definition": "project_stratified_tail_15_percent_not_vendor_split",
                    "seed": 0,
                    "transform": {
                        "axis": axis["name"],
                        "axis_index": axis_index,
                        "value": value,
                        "value_index": value_index,
                        "units": axis["units"],
                        "nominal_value": axis["nominal"],
                        "is_nominal": value == axis["nominal"],
                        "interpretation": axis["interpretation"],
                        "changes_only_rgb": True,
                        "metric_scene_transform_claimed": False,
                    },
                    "source": {
                        "dataset": str(dataset),
                        "parquet": str(parquet),
                        "video": str(video),
                        **source_hashes,
                    },
                    "staged_parquet": "episode.parquet",
                    "staged_video": "episode.mp4",
                }
                _write_json(output_dir / relative_manifest, manifest)
                entries.append(
                    {
                        "sample_id": sample_id,
                        "task_id": task_id,
                        "axis": axis["name"],
                        "value": value,
                        "is_nominal": value == axis["nominal"],
                        "manifest": str(relative_manifest),
                    }
                )
                print(
                    f"E3_1_PROXY_SELECTED={sample_id},task:{task_id},"
                    f"axis:{axis['name']},value:{value}"
                )

    campaign = {
        "schema": "cruzr-s2-vla-offline-e3.1-selection-v1",
        "campaign_id": "E3.1",
        "mode": "offline_dataset_image_proxy_only_no_robot",
        "tasks": list(TASK_IDS),
        "model_seed": 0,
        "unique_source_frame_count": len(TASK_IDS),
        "variant_count": len(entries),
        "base_samples": base_samples,
        "proxy_axes": list(PROXY_AXES),
        "sample_manifests": entries,
        "metric_grid_requested_by_plan": {
            "object_x_m": [-0.10, -0.05, 0.0, 0.05, 0.10],
            "front_face_behind_edge_m": [0.05, 0.10, 0.15],
            "object_yaw_deg": [-15.0, -5.0, 0.0, 5.0, 15.0],
        },
        "metric_grid_status": "BLOCKED_MISSING_RGBD_CALIBRATION_MASK_AND_SCENE_GEOMETRY",
        "metric_grid_blockers": [
            "dataset_has_rgb_only_no_depth",
            "dataset_has_no_camera_intrinsics_or_extrinsics",
            "dataset_has_no_object_mask_or_6d_pose",
            "dataset_has_no_shelf_edge_plane_or_metric_registration",
        ],
        "one_proxy_variable_changed_per_sample": True,
        "checkpoint_training_membership_known": False,
        "generalization_claim_allowed": False,
        "physical_task_success_evaluated": False,
    }
    _write_json(output_dir / "campaign.json", campaign)
    print(
        f"E3_1_PROXY_CAMPAIGN_SELECTED=sources:{len(TASK_IDS)},"
        f"variants:{len(entries)},metric-grid:blocked"
    )
    return 0


def _apply_transform(image: Any, transform: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
    import cv2
    import numpy as np

    height, width = image.shape[:2]
    axis = transform["axis"]
    value = float(transform["value"])
    nominal = float(transform["nominal_value"])
    if value == nominal:
        return image.copy(), {
            "method": "identity",
            "matrix": np.eye(3, dtype=float).tolist(),
            "width": width,
            "height": height,
            "border_mode": "not_applicable",
        }
    if axis == "horizontal_frame_shift_fraction":
        shift_pixels = int(round(value * width))
        affine = np.asarray([[1.0, 0.0, shift_pixels], [0.0, 1.0, 0.0]], dtype=np.float32)
        transformed = cv2.warpAffine(
            image,
            affine,
            (width, height),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REFLECT_101,
        )
        matrix = np.vstack([affine, [0.0, 0.0, 1.0]])
        details = {"shift_pixels": shift_pixels}
        method = "global_horizontal_affine_shift"
    elif axis == "global_zoom_factor":
        affine = cv2.getRotationMatrix2D(
            ((width - 1) / 2.0, (height - 1) / 2.0), 0.0, value
        ).astype(np.float32)
        transformed = cv2.warpAffine(
            image,
            affine,
            (width, height),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REFLECT_101,
        )
        matrix = np.vstack([affine, [0.0, 0.0, 1.0]])
        details = {"scale": value}
        method = "global_centered_affine_zoom"
    elif axis == "global_perspective_yaw_proxy_deg":
        magnitude = abs(math.sin(math.radians(value)))
        horizontal_inset = magnitude * 0.25 * width
        vertical_inset = magnitude * 0.12 * height
        source = np.asarray(
            [[0.0, 0.0], [width - 1.0, 0.0], [width - 1.0, height - 1.0], [0.0, height - 1.0]],
            dtype=np.float32,
        )
        if value > 0:
            destination = np.asarray(
                [
                    [horizontal_inset, vertical_inset],
                    [width - 1.0, 0.0],
                    [width - 1.0, height - 1.0],
                    [horizontal_inset, height - 1.0 - vertical_inset],
                ],
                dtype=np.float32,
            )
        else:
            destination = np.asarray(
                [
                    [0.0, 0.0],
                    [width - 1.0 - horizontal_inset, vertical_inset],
                    [width - 1.0 - horizontal_inset, height - 1.0 - vertical_inset],
                    [0.0, height - 1.0],
                ],
                dtype=np.float32,
            )
        matrix = cv2.getPerspectiveTransform(source, destination)
        transformed = cv2.warpPerspective(
            image,
            matrix,
            (width, height),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REFLECT_101,
        )
        details = {
            "horizontal_inset_pixels": horizontal_inset,
            "vertical_inset_pixels": vertical_inset,
        }
        method = "global_trapezoid_perspective_proxy"
    else:
        raise ValueError(f"unsupported OOD proxy axis: {axis}")
    return transformed, {
        "method": method,
        "matrix": [[float(item) for item in row] for row in matrix.tolist()],
        "width": width,
        "height": height,
        "border_mode": "cv2.BORDER_REFLECT_101",
        **details,
    }


def _array_sha256(image: Any) -> str:
    return hashlib.sha256(image.tobytes(order="C")).hexdigest()


def _aggregate(results: list[dict[str, Any]], joint_names: Sequence[str]) -> dict[str, Any]:
    import numpy as np

    task_aggregates: dict[str, Any] = {}
    for task_id in TASK_IDS:
        task_rows = [row for row in results if int(row["task_id"]) == task_id]
        axes: dict[str, Any] = {}
        nominal_predictions = []
        for axis in PROXY_AXES:
            axis_rows = [row for row in task_rows if row["transform"]["axis"] == axis["name"]]
            nominal_rows = [row for row in axis_rows if row["transform"]["is_nominal"]]
            if len(nominal_rows) != 1:
                raise ValueError(f"task {task_id} axis {axis['name']} lacks one nominal")
            reference = np.asarray(nominal_rows[0]["predicted_action_10x20"], dtype=float)
            nominal_predictions.append(reference)
            curve = []
            for row in axis_rows:
                prediction = np.asarray(row["predicted_action_10x20"], dtype=float)
                absolute_delta = np.abs(prediction - reference)
                per_joint_max = np.max(absolute_delta, axis=0)
                sensitivity = {
                    "mean_abs_action_delta_vs_nominal": float(np.mean(absolute_delta)),
                    "max_abs_action_delta_vs_nominal": float(np.max(absolute_delta)),
                    "max_delta_joint": joint_names[int(np.argmax(per_joint_max))],
                    "per_joint_max_abs_action_delta_vs_nominal": {
                        name: float(value) for name, value in zip(joint_names, per_joint_max)
                    },
                }
                row["sensitivity_vs_axis_nominal"] = sensitivity
                curve.append(
                    {
                        "value": row["transform"]["value"],
                        "verdict": row["verdict"],
                        "mae": row["metrics"]["mae"],
                        **sensitivity,
                    }
                )
            axes[axis["name"]] = {
                "units": axis["units"],
                "interpretation": axis["interpretation"],
                "curve": curve,
                "max_abs_action_delta_across_grid": max(
                    point["max_abs_action_delta_vs_nominal"] for point in curve
                ),
                "rejected_variant_count": sum(
                    point["verdict"] == "REJECT_CONSERVATIVE" for point in curve
                ),
            }
        cross_nominal_max = max(
            float(np.max(np.abs(candidate - nominal_predictions[0])))
            for candidate in nominal_predictions
        )
        task_aggregates[str(task_id)] = {
            "task_text": BASE.TASKS[task_id],
            "source_episode_index": task_rows[0]["episode_index"],
            "source_frame_index": task_rows[0]["frame_index"],
            "variant_count": len(task_rows),
            "rejected_variant_count": sum(
                row["verdict"] == "REJECT_CONSERVATIVE" for row in task_rows
            ),
            "nominal_cross_axis_max_abs_prediction_difference": cross_nominal_max,
            "axes": axes,
        }
    return task_aggregates


def command_infer(args: argparse.Namespace) -> int:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    checkpoint = pathlib.Path(args.checkpoint).resolve()
    profile_path = pathlib.Path(args.profile).resolve()
    campaign_path = pathlib.Path(args.campaign_manifest).resolve()
    output_dir = pathlib.Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    results_dir = output_dir / "runs"
    previews_dir = output_dir / "previews"
    results_dir.mkdir()
    previews_dir.mkdir()
    profile = BASE.load_json(profile_path)
    if int(profile["action_dim"]) != 20 or int(profile["action_horizon"]) != 10:
        raise ValueError("profile must be 10x20")
    campaign = BASE.load_json(campaign_path)
    if campaign.get("campaign_id") != "E3.1" or campaign.get("variant_count") != 26:
        raise ValueError("invalid E3.1 campaign")
    if campaign.get("metric_grid_status") != "BLOCKED_MISSING_RGBD_CALIBRATION_MASK_AND_SCENE_GEOMETRY":
        raise ValueError("metric grid must remain explicitly blocked")
    campaign_parent = campaign_path.parent
    manifests = []
    for entry in campaign["sample_manifests"]:
        candidate = (campaign_parent / entry["manifest"]).resolve()
        if campaign_parent != candidate and campaign_parent not in candidate.parents:
            raise ValueError("campaign manifest escapes staging directory")
        manifests.append(candidate)
    if len(manifests) != 26 or len(set(manifests)) != 26:
        raise ValueError("E3.1 requires 26 distinct variant manifests")

    override_parent = pathlib.Path(args.override_parent).resolve()
    sys.path.insert(0, str(override_parent))
    import cv2
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
    torch.manual_seed(0)
    np.random.seed(0)
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
    model_load_seconds = time.monotonic() - started_load
    results: list[dict[str, Any]] = []
    try:
        for manifest_path in manifests:
            manifest = BASE.load_json(manifest_path)
            task_id = int(manifest["task_id"])
            if task_id not in TASK_IDS or manifest["task_text"] != BASE.TASKS[task_id]:
                raise ValueError("invalid E3.1 task manifest")
            table_sample = BASE._extract_table_sample(manifest, manifest_path)
            original_image_sha256 = _array_sha256(table_sample["image"])
            transformed_image, applied = _apply_transform(
                table_sample["image"], manifest["transform"]
            )
            transformed_image_sha256 = _array_sha256(transformed_image)
            if manifest["transform"]["is_nominal"] and (
                transformed_image_sha256 != original_image_sha256
            ):
                raise ValueError("nominal transform changed the source RGB frame")
            preview_path = previews_dir / f"{manifest['sample_id']}.png"
            if preview_path.exists() or not cv2.imwrite(
                str(preview_path), cv2.cvtColor(transformed_image, cv2.COLOR_RGB2BGR)
            ):
                raise ValueError(f"cannot write preview {preview_path}")
            policy_sample = dict(table_sample)
            policy_sample["image"] = transformed_image
            torch.manual_seed(int(manifest["seed"]))
            np.random.seed(int(manifest["seed"]))
            started_inference = time.monotonic()
            action_chunk = policy.get_action(
                BASE._policy_sample(policy_sample, manifest["task_text"])
            )
            inference_seconds = time.monotonic() - started_inference
            predicted = BASE._flatten_prediction(action_chunk)
            metrics = BASE._metrics(
                predicted,
                table_sample["ground_truth"],
                table_sample["state20"],
                profile,
            )
            verdict = (
                "REJECT_CONSERVATIVE"
                if metrics["range_violations"] or metrics["first_point_delta_violations"]
                else "ACCEPT_STRUCTURAL"
            )
            result = {
                "sample_id": manifest["sample_id"],
                "task_id": task_id,
                "task_text": manifest["task_text"],
                "episode_index": int(manifest["episode_index"]),
                "frame_index": int(manifest["frame_index"]),
                "model_seed": int(manifest["seed"]),
                "transform": manifest["transform"],
                "applied_transform": applied,
                "input": {
                    "state20": table_sample["state20"],
                    "force_torque12": table_sample["force_torque12"],
                    "timestamp": table_sample["timestamp"],
                    "frame_index_source": table_sample["frame_index_source"],
                    "original_image_sha256": original_image_sha256,
                    "transformed_image_sha256": transformed_image_sha256,
                    "preview": f"previews/{preview_path.name}",
                    "preview_sha256": BASE.sha256_file(preview_path),
                    "parquet_sha256": manifest["source"]["parquet_sha256"],
                    "video_sha256": manifest["source"]["video_sha256"],
                },
                "predicted_action_10x20": predicted,
                "predicted_action_sha256": hashlib.sha256(
                    json.dumps(predicted, separators=(",", ":")).encode("utf-8")
                ).hexdigest(),
                "ground_truth_action_10x20": table_sample["ground_truth"],
                "flag_pred": BASE._flag_value(action_chunk),
                "metrics": metrics,
                "inference_seconds": inference_seconds,
                "verdict": verdict,
                "metric_scene_transform_evaluated": False,
                "physical_task_success_evaluated": False,
            }
            results.append(result)
            print(
                f"E3_1_PROXY_RESULT={manifest['sample_id']},task:{task_id},"
                f"axis:{manifest['transform']['axis']},value:{manifest['transform']['value']},"
                f"mae:{metrics['mae']:.9f},verdict:{verdict}"
            )
    finally:
        del policy
        torch.cuda.empty_cache()

    aggregates = _aggregate(results, profile["joint_names"])
    for result in results:
        _write_json(results_dir / f"{result['sample_id']}.json", result)
    summary = {
        "schema": "cruzr-s2-vla-offline-e3.1-image-proxy-v1",
        "campaign_id": "E3.1",
        "mode": "offline_network_none_no_ros_no_robot_image_proxy",
        "checkpoint": {
            "path": str(checkpoint),
            "config_sha256": BASE.sha256_file(checkpoint / "config.json"),
            "index_sha256": BASE.sha256_file(checkpoint / "model.safetensors.index.json"),
        },
        "profile_sha256": BASE.sha256_file(profile_path),
        "campaign_selection_sha256": BASE.sha256_file(campaign_path),
        "gr00t_overlay": str(pathlib.Path(gr00t.__file__).resolve()),
        "cuda_device": torch.cuda.get_device_name(0),
        "model_load_seconds": model_load_seconds,
        "variant_count": len(results),
        "metric_grid_requested_by_plan": campaign["metric_grid_requested_by_plan"],
        "metric_grid_status": campaign["metric_grid_status"],
        "metric_grid_blockers": campaign["metric_grid_blockers"],
        "proxy_axes": campaign["proxy_axes"],
        "one_proxy_variable_changed_per_sample": True,
        "samples": results,
        "aggregates": aggregates,
        "checkpoint_training_membership_known": False,
        "generalization_claim_allowed": False,
        "metric_scene_transform_evaluated": False,
        "physical_task_success_evaluated": False,
        "physical_movement_commanded": False,
        "robot_state_read": False,
        "network_available": False,
    }
    _write_json(output_dir / "summary.json", summary)
    print(
        f"OFFLINE_E3_1_COMPLETE=variants:{len(results)},"
        "metric-grid:blocked,movement:none,network:none"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    campaign_parser = subparsers.add_parser("campaign")
    campaign_parser.add_argument("--dataset", required=True)
    campaign_parser.add_argument("--output-dir", required=True)
    campaign_parser.set_defaults(func=command_campaign)
    infer_parser = subparsers.add_parser("infer")
    infer_parser.add_argument("--checkpoint", required=True)
    infer_parser.add_argument("--profile", required=True)
    infer_parser.add_argument("--override-parent", required=True)
    infer_parser.add_argument("--campaign-manifest", required=True)
    infer_parser.add_argument("--output-dir", required=True)
    infer_parser.set_defaults(func=command_infer)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
