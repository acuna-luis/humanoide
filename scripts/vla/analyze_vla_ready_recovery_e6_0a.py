#!/usr/bin/env python3
"""Derive and audit an arms-only ready/recovery contract for E6.0."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import xml.etree.ElementTree as ET
from typing import Any

import yaml


META_ARM_ORDER = (
    "shoulder_pitch",
    "shoulder_roll",
    "shoulder_yaw",
    "elbow_roll",
    "elbow_yaw",
    "wrist_pitch",
    "wrist_roll",
)
CHECKPOINT_ARM_ORDER = (
    "elbow_roll",
    "elbow_yaw",
    "shoulder_pitch",
    "shoulder_roll",
    "shoulder_yaw",
    "wrist_pitch",
    "wrist_roll",
)
META_TO_CHECKPOINT = tuple(META_ARM_ORDER.index(name) for name in CHECKPOINT_ARM_ORDER)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ready-xml", type=pathlib.Path, required=True)
    parser.add_argument("--forward-yaml", type=pathlib.Path, required=True)
    parser.add_argument("--vendor-back-yaml", type=pathlib.Path, required=True)
    parser.add_argument("--profile", type=pathlib.Path, required=True)
    parser.add_argument("--e4-0", type=pathlib.Path, required=True)
    parser.add_argument("--e3-0-task0-frame0", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path)
    return parser.parse_args()


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def floats(text: str) -> list[float]:
    return [float(part.strip()) for part in text.split(";") if part.strip()]


def reorder_side(values: list[float]) -> list[float]:
    if len(values) != 7:
        raise ValueError(f"expected 7 arm values, got {len(values)}")
    return [values[index] for index in META_TO_CHECKPOINT]


def reorder_bimanual(values: list[float]) -> list[float]:
    if len(values) != 14:
        raise ValueError(f"expected 14 bimanual values, got {len(values)}")
    return reorder_side(values[:7]) + reorder_side(values[7:])


def load_yaml(path: pathlib.Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected YAML object: {path}")
    return value


def load_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def violations(
    values: list[float], profile: dict[str, Any], *, tolerance: float = 0.0
) -> list[dict[str, Any]]:
    result = []
    for index, value in enumerate(values):
        lower = float(profile["lower_boundary"][index])
        upper = float(profile["upper_boundary"][index])
        if value < lower - tolerance or value > upper + tolerance:
            distance = lower - value if value < lower else value - upper
            result.append(
                {
                    "index": index,
                    "joint": profile["joint_names"][index],
                    "value_rad": value,
                    "lower_rad": lower,
                    "upper_rad": upper,
                    "distance_outside_rad": distance,
                    "tolerance_rad": tolerance,
                }
            )
    return result


def segment_speed(
    start: list[float], end: list[float], duration: float, profile: dict[str, Any]
) -> dict[str, Any]:
    speeds = [abs(target - source) / duration for source, target in zip(start, end)]
    limits = [float(value) for value in profile["max_interpoint_speed"][:14]]
    failures = [
        {
            "index": index,
            "joint": profile["joint_names"][index],
            "speed_rad_s": speed,
            "analysis_limit_rad_s": limits[index],
        }
        for index, speed in enumerate(speeds)
        if speed > limits[index]
    ]
    return {
        "duration_seconds": duration,
        "max_abs_speed_rad_s": max(speeds),
        "passes_offline_analysis_speed_envelope": not failures,
        "failures": failures,
        "note": "analysis envelope only; not a certified physical limit",
    }


def main() -> int:
    args = parse_args()
    ready_path = args.ready_xml.resolve()
    forward_path = args.forward_yaml.resolve()
    back_path = args.vendor_back_yaml.resolve()
    profile_path = args.profile.resolve()
    e4_path = args.e4_0.resolve()
    task0_frame0_path = args.e3_0_task0_frame0.resolve()

    tree = ET.parse(ready_path)
    root = tree.getroot()
    arm_actions = {
        action.attrib["location"]: floats(action.attrib["joint_angles"])
        for action in root.findall(".//Action[@ID='MetaMove'][@type='arm']")
    }
    if set(arm_actions) != {"left", "right"}:
        raise SystemExit(f"ERROR: expected left/right preposition: {arm_actions.keys()}")
    named = [
        action.attrib.get("name")
        for action in root.findall(".//Action[@ID='MetaMove'][@name]")
    ]
    if named != ["clamp_s2_joints_trajectory"]:
        raise SystemExit(f"ERROR: unexpected final named action: {named}")

    forward = load_yaml(forward_path)["request"]
    vendor_back = load_yaml(back_path)["request"]
    profile = load_json(profile_path)
    task0_frame0 = load_json(task0_frame0_path)
    if profile.get("action_dim") != 20 or len(profile.get("commanded_joint_names", [])) != 14:
        raise SystemExit("ERROR: profile is not the expected 20D/P14 contract")

    forward_goals = forward.get("goals", [])
    forward_durations = [float(value) for value in forward.get("durations", [])]
    back_goals = vendor_back.get("goals", [])
    if len(forward_goals) != 2 or len(forward_durations) != 2 or len(back_goals) != 2:
        raise SystemExit("ERROR: expected two forward and two vendor-back goals")

    staging = reorder_side(arm_actions["left"]) + reorder_side(arm_actions["right"])
    waypoint_a = reorder_bimanual([float(value) for value in forward_goals[0]])
    ready_b = reorder_bimanual([float(value) for value in forward_goals[1]])
    vendor_back_checkpoint = [
        reorder_bimanual([float(value) for value in goal]) for goal in back_goals
    ]
    observed_ready = [float(value) for value in task0_frame0["input"]["state20"][:14]]
    if (
        task0_frame0.get("task_id") != 0
        or task0_frame0.get("frame_index") != 0
        or len(observed_ready) != 14
    ):
        raise SystemExit("ERROR: E3.0 reference is not task 0 frame 0 with 14 arm axes")
    swapped_wrist_indices = (3, 4, 0, 1, 2, 6, 5)
    raw_ready = [float(value) for value in forward_goals[1]]
    swapped_ready = (
        [raw_ready[index] for index in swapped_wrist_indices]
        + [raw_ready[7 + index] for index in swapped_wrist_indices]
    )
    direct_alignment_error = [
        abs(candidate - observed) for candidate, observed in zip(ready_b, observed_ready)
    ]
    swapped_alignment_error = [
        abs(candidate - observed) for candidate, observed in zip(swapped_ready, observed_ready)
    ]
    recovery_goals = [waypoint_a, staging]
    recovery_durations = list(reversed(forward_durations))
    exact_reverse = recovery_goals == [waypoint_a, staging]
    vendor_back_exact_reverse = vendor_back_checkpoint == recovery_goals

    tolerance = float(profile.get("range_tolerance", 0.0))
    envelope = {
        "staging_preposition": {
            "strict": violations(staging, profile),
            "with_profile_tolerance": violations(staging, profile, tolerance=tolerance),
            "used_for_inference": False,
        },
        "waypoint_a": {
            "strict": violations(waypoint_a, profile),
            "with_profile_tolerance": violations(waypoint_a, profile, tolerance=tolerance),
            "used_for_inference": False,
        },
        "ready_b": {
            "strict": violations(ready_b, profile),
            "with_profile_tolerance": violations(ready_b, profile, tolerance=tolerance),
            "used_for_inference": True,
        },
    }
    ready_supported = not envelope["ready_b"]["with_profile_tolerance"]

    candidate_speed = [
        segment_speed(ready_b, waypoint_a, recovery_durations[0], profile),
        segment_speed(waypoint_a, staging, recovery_durations[1], profile),
    ]
    e4_actual = e4_path / "actual_result.yaml"
    e4_text = e4_actual.read_text(encoding="utf-8")
    if "status: PARTIAL_RESOLUTION_BLOCKED_NOT_READY_FOR_E4_1_OR_PHYSICAL_USE" not in e4_text:
        raise SystemExit("ERROR: E4.0 source status changed")

    blockers = [
        "candidate_task_not_installed_or_registered",
        "exact_reverse_candidate_not_collision_or_physically_validated",
        "locked_axes_require_fresh_runtime_capture_and_hold",
        "certified_acceleration_and_force_limits_missing",
    ]
    report = {
        "schema": "cruzr-s2-vla-ready-recovery-e6.0a-v1",
        "experiment_id": "E6.0A",
        "mode": "local_derivation_no_robot_no_network_no_ros_no_publisher",
        "sources": {
            "ready_xml": {"path": str(ready_path), "sha256": sha256_file(ready_path)},
            "forward_yaml": {"path": str(forward_path), "sha256": sha256_file(forward_path)},
            "vendor_back_yaml": {"path": str(back_path), "sha256": sha256_file(back_path)},
            "profile": {"path": str(profile_path), "sha256": sha256_file(profile_path)},
            "e4_0_actual_result": {"path": str(e4_actual), "sha256": sha256_file(e4_actual)},
            "e4_0_manifest": {
                "path": str(e4_path / "evidence.sha256"),
                "sha256": sha256_file(e4_path / "evidence.sha256"),
            },
            "e3_0_task0_frame0": {
                "path": str(task0_frame0_path),
                "sha256": sha256_file(task0_frame0_path),
                "episode_index": task0_frame0["episode_index"],
                "frame_index": task0_frame0["frame_index"],
            },
        },
        "joint_order": {
            "source_meta_per_arm": list(META_ARM_ORDER),
            "checkpoint_per_arm": list(CHECKPOINT_ARM_ORDER),
            "meta_to_checkpoint_indices": list(META_TO_CHECKPOINT),
            "supplier_component_header_available": False,
            "mapping_basis": "direct wrist order validated against E3.0 task 0 episode frame 0",
            "direct_order_max_abs_error_rad": max(direct_alignment_error),
            "direct_order_mae_rad": sum(direct_alignment_error) / len(direct_alignment_error),
            "swapped_wrist_order_max_abs_error_rad": max(swapped_alignment_error),
            "swapped_wrist_order_mae_rad": sum(swapped_alignment_error) / len(swapped_alignment_error),
            "direct_order_locally_validated": max(direct_alignment_error) < 0.003,
            "e4_0_swapped_wrist_hypothesis_rejected": max(swapped_alignment_error) > 0.6,
        },
        "p14_contract": {
            "commanded_joint_names": profile["commanded_joint_names"],
            "locked_joint_names": profile["locked_joint_names"],
            "locked_axis_policy": "capture_fresh_runtime_state_then_hold_every_point",
            "static_numeric_20d_ready_required": False,
            "structurally_complete": True,
            "physically_accepted": False,
        },
        "arm_path_checkpoint_order": {
            "staging_preposition": staging,
            "waypoint_a": waypoint_a,
            "ready_b": ready_b,
            "forward_durations_seconds": forward_durations,
        },
        "checkpoint_support_envelope": {
            "range_tolerance_rad": tolerance,
            "states": envelope,
            "ready_b_supported_with_tolerance": ready_supported,
        },
        "recovery_candidate": {
            "assumed_start": ready_b,
            "goals": recovery_goals,
            "durations_seconds": recovery_durations,
            "exact_time_reverse_of_explicit_arm_path": exact_reverse,
            "offline_analysis_speed_checks": candidate_speed,
            "all_segments_pass_offline_analysis_speed_envelope": all(
                segment["passes_offline_analysis_speed_envelope"] for segment in candidate_speed
            ),
            "physically_validated": False,
        },
        "vendor_back": {
            "goals_checkpoint_order": vendor_back_checkpoint,
            "is_exact_reverse_candidate": vendor_back_exact_reverse,
            "use_for_e6_0_recovery": False,
        },
        "blocking_gates": blockers,
        "blocking_gate_count": len(blockers),
        "e6_0_physical_authorized": False,
        "robot_state_read": False,
        "network_calls": 0,
        "physical_publishers": 0,
        "physical_movement_commanded": False,
        "next_safe_work": "run_offline_self_collision_and_entry_recovery_sweep_for_P14_ready_candidate",
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    ready_violation = envelope["ready_b"]["with_profile_tolerance"]
    print("E6.0A_MODE=local-only,no-robot,no-network,no-ros,no-publisher")
    print("E6.0A_P14_LOCKED_AXES=fresh-runtime-capture-and-hold")
    print("E6.0A_RECOVERY_CANDIDATE=exact-arm-reverse,B->A->staging,physical-validated:false")
    print(f"E6.0A_VENDOR_BACK_EXACT_REVERSE={int(vendor_back_exact_reverse)}")
    print(
        "E6.0A_JOINT_ORDER_ALIGNMENT="
        f"direct-max:{max(direct_alignment_error):.9f},"
        f"swapped-max:{max(swapped_alignment_error):.9f}"
    )
    print(f"E6.0A_READY_SUPPORT_VIOLATIONS={len(ready_violation)}")
    for item in ready_violation:
        print(
            "E6.0A_READY_SUPPORT_VIOLATION="
            f"{item['joint']},value:{item['value_rad']:.9f},upper:{item['upper_rad']:.9f},"
            f"outside:{item['distance_outside_rad']:.9f},tolerance:{item['tolerance_rad']:.9f}"
        )
    print("E6.0A_PHYSICAL_AUTHORIZED=0")
    if args.output:
        print(f"E6.0A_REPORT={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
