#!/usr/bin/env python3
"""Analyze the vendor S2 VLA-ready artifacts captured read-only in E4.0."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import yaml


SUPPLIED_XML_SHA256 = (
    "f4025124491eba995ec824db3e3be91875f781a4b4e98928654bde9a021d8323"
)
FORWARD_SHA256 = (
    "7722b73457a89d6448954944af98ff50b24f586113f6ec7014dd31b1efdef7f6"
)
BACK_SHA256 = (
    "ee39039cfddd24eaf8602c3eb5fa3418eaeee519ed1ca42b584191bb6582f389"
)

META_ARM_ORDER = [
    "shoulder_pitch", "shoulder_roll", "shoulder_yaw", "elbow_roll",
    "elbow_yaw", "wrist_roll", "wrist_pitch",
]
CHECKPOINT_ARM_ORDER = [
    "elbow_roll", "elbow_yaw", "shoulder_pitch", "shoulder_roll",
    "shoulder_yaw", "wrist_pitch", "wrist_roll",
]
META_TO_CHECKPOINT = [META_ARM_ORDER.index(name) for name in CHECKPOINT_ARM_ORDER]


def parse_angles(raw: str) -> list[float]:
    values = [float(item.strip()) for item in raw.replace(",", ";").split(";") if item.strip()]
    if not all(math.isfinite(value) for value in values):
        raise ValueError("non-finite joint angle")
    return values


def parse_xml_actions(path: Path) -> list[dict[str, object]]:
    root = ET.parse(path).getroot()
    actions: list[dict[str, object]] = []
    for element in root.iter("Action"):
        action: dict[str, object] = dict(element.attrib)
        if "joint_angles" in element.attrib:
            action["joint_angles_parsed"] = parse_angles(element.attrib["joint_angles"])
        if "duration" in element.attrib:
            action["duration_seconds"] = float(element.attrib["duration"])
        actions.append(action)
    return actions


def sha_from_file(path: Path) -> str:
    line = path.read_text(encoding="utf-8").strip().splitlines()[0]
    return line.split()[0]


def yaml_trajectory(path: Path) -> tuple[list[float], list[list[float]]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    request = payload["request"]
    durations = [float(value) for value in request["durations"]]
    goals = [[float(value) for value in goal] for goal in request["goals"]]
    return durations, goals


def reorder_meta_arm(values: list[float]) -> list[float]:
    if len(values) != 7:
        raise ValueError("MetaMove arm vector must be 7D")
    return [values[index] for index in META_TO_CHECKPOINT]


def parse_urdf_limits(path: Path) -> tuple[set[str], dict[str, dict[str, float]]]:
    root = ET.parse(path).getroot()
    names: set[str] = set()
    limits: dict[str, dict[str, float]] = {}
    for joint in root.findall("joint"):
        name = joint.attrib["name"]
        names.add(name)
        limit = joint.find("limit")
        if limit is not None:
            limits[name] = {
                key: float(limit.attrib[key])
                for key in ("lower", "upper", "effort", "velocity")
                if key in limit.attrib
            }
    return names, limits


def aggregate_lifter_stats(path: Path) -> dict[str, object]:
    by_task: dict[int, list[dict[str, object]]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        stats = item["stats"]
        task = int(round(stats["annotation.human.action.task_description"]["mean"][0]))
        by_task.setdefault(task, []).append(stats["action"])

    task_summary: dict[str, object] = {}
    for task, rows in sorted(by_task.items()):
        joints = []
        for index, name in zip(
            range(16, 19),
            ("lifter_pitch_1_joint", "lifter_pitch_2_joint", "lifter_pitch_3_joint"),
        ):
            episode_means = sorted(float(row["mean"][index]) for row in rows)
            middle = len(episode_means) // 2
            median = (
                episode_means[middle]
                if len(episode_means) % 2
                else (episode_means[middle - 1] + episode_means[middle]) / 2.0
            )
            joints.append({
                "name": name,
                "episode_mean_min": min(episode_means),
                "episode_mean_median": median,
                "episode_mean_max": max(episode_means),
                "global_min": min(float(row["min"][index]) for row in rows),
                "global_max": max(float(row["max"][index]) for row in rows),
                "max_within_episode_std": max(float(row["std"][index]) for row in rows),
            })
        task_summary[str(task)] = {"episodes": len(rows), "joints": joints}

    return {
        "episode_count": sum(len(rows) for rows in by_task.values()),
        "task_episode_counts": {
            str(task): len(rows) for task, rows in sorted(by_task.items())
        },
        "per_task": task_summary,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    artifacts = run_dir / "artifacts"

    supplied_xml = artifacts / "vendor_s2_vla_pick_large_teleop_ready.xml"
    forward_yaml = artifacts / "remote_clamp_s2_joints_trajectory.yaml"
    back_yaml = artifacts / "remote_clamp_s2_joints_trajectory_back.yaml"
    task_list = artifacts / "remote_task_list.yaml"
    remote_clamp_ready = artifacts / "remote_cruzr_vla_clamp_ready.xml"
    remote_transport_s2 = artifacts / "remote_transport_clamp_ready_s2.xml"
    non_s2_55_ready = artifacts / "vendor_non_s2_vla_pick_large_55_ready.xml"
    s2_executor = artifacts / "vendor_s2_executor_node_sdk.py"
    s2_executor_config = artifacts / "vendor_s2_executor_config.yaml"
    generic_executor = artifacts / "vendor_s2_generic_executor_7dof.py"
    dataset_info = artifacts / "vendor_dataset_info.json"
    dataset_episode_stats = artifacts / "vendor_dataset_episode_stats.jsonl"
    urdf_path = artifacts / "vendor_cruzr_s2_v1.urdf"
    sdk_manual = artifacts / "vendor_sdk_manual.txt"
    upgrade_listing = artifacts / "vendor_v020_upgrade_file_list.txt"
    supplied_sha = sha_from_file(artifacts / "vendor_s2_ready.sha256")
    forward_sha = sha_from_file(artifacts / "remote_clamp_s2_joints_trajectory.sha256")
    back_sha = sha_from_file(artifacts / "remote_clamp_s2_joints_trajectory_back.sha256")

    if supplied_sha != SUPPLIED_XML_SHA256:
        raise ValueError(f"unexpected supplied XML hash: {supplied_sha}")
    if forward_sha != FORWARD_SHA256:
        raise ValueError(f"unexpected installed forward primitive hash: {forward_sha}")
    if back_sha != BACK_SHA256:
        raise ValueError(f"unexpected installed back primitive hash: {back_sha}")

    supplied_actions = parse_xml_actions(supplied_xml)
    named_actions = [action for action in supplied_actions if action.get("name")]
    if [action.get("name") for action in named_actions] != ["clamp_s2_joints_trajectory"]:
        raise ValueError("supplied S2 XML does not end in the expected primitive")

    explicit = {
        (str(action.get("type")), str(action.get("location"))): action
        for action in supplied_actions
        if action.get("joint_angles_parsed") is not None
    }
    for key, dimension in {
        ("arm", "left"): 7,
        ("arm", "right"): 7,
        ("head", "single"): 2,
        ("waist", "single"): 2,
    }.items():
        if len(explicit[key]["joint_angles_parsed"]) != dimension:
            raise ValueError(f"unexpected supplied preposition dimension for {key}")

    forward_durations, forward_goals = yaml_trajectory(forward_yaml)
    back_durations, back_goals = yaml_trajectory(back_yaml)
    if len(forward_durations) != 2 or [len(goal) for goal in forward_goals] != [14, 14]:
        raise ValueError("installed forward primitive is not 2x14")
    if len(back_durations) != 2 or [len(goal) for goal in back_goals] != [14, 14]:
        raise ValueError("installed back primitive is not 2x14")

    task_list_text = task_list.read_text(encoding="utf-8")
    supplied_task_key = "s2_vla_pick_large_teleop_ready"
    supplied_motion_id = "s2_bio_vla/s2_vla_pick_large_teleop_ready"
    supplied_registered = (
        f"{supplied_task_key}:" in task_list_text
        and f'motion_id: "{supplied_motion_id}"' in task_list_text
    )
    supplied_installed = bool(
        (artifacts / "remote_s2_bio_vla_file_list.txt").read_text(encoding="utf-8").strip()
    )

    remote_clamp_actions = parse_xml_actions(remote_clamp_ready)
    remote_transport_actions = parse_xml_actions(remote_transport_s2)
    remote_clamp_calls_forward = any(
        action.get("name") == "clamp_s2_joints_trajectory"
        for action in remote_clamp_actions
    )
    transport_s2_calls_forward = any(
        action.get("name") == "clamp_s2_joints_trajectory"
        for action in remote_transport_actions
    )

    non_s2_55_actions = parse_xml_actions(non_s2_55_ready)
    last_55_by_location: dict[str, list[float]] = {}
    for action in non_s2_55_actions:
        if action.get("type") == "arm" and action.get("joint_angles_parsed") is not None:
            last_55_by_location[str(action["location"])] = list(action["joint_angles_parsed"])
    if set(last_55_by_location) != {"left", "right"}:
        raise ValueError("vendor non-S2 55 ready does not define both final arms")

    # The installed 14D final goal matches the explicit non-S2 55 cm vendor XML
    # in left-then-right MetaMove order up to rounding. MetaMove uses the motor
    # order documented by the vendor SDK (shoulder, elbow, wrist), whereas the
    # checkpoint uses elbow, shoulder, wrist. They must not be concatenated.
    final_arm_component_order = forward_goals[-1]
    inferred_order_reference = last_55_by_location["left"] + last_55_by_location["right"]
    inferred_order_max_abs_error = max(
        abs(actual - reference)
        for actual, reference in zip(final_arm_component_order, inferred_order_reference)
    )
    if inferred_order_max_abs_error > 0.003:
        raise ValueError(
            "installed final 14D goal does not match the vendor non-S2 left/right reference"
        )

    arm_values_checkpoint_order = (
        reorder_meta_arm(final_arm_component_order[:7])
        + reorder_meta_arm(final_arm_component_order[7:])
    )
    info = json.loads(dataset_info.read_text(encoding="utf-8"))
    checkpoint_joint_order = info["features"]["action"]["names"]
    expected_checkpoint_order = [
        *(f"L_{name}_joint" for name in CHECKPOINT_ARM_ORDER),
        *(f"R_{name}_joint" for name in CHECKPOINT_ARM_ORDER),
        "head_pitch_joint", "head_yaw_joint",
        "lifter_pitch_1_joint", "lifter_pitch_2_joint", "lifter_pitch_3_joint",
        "waist_yaw_joint",
    ]
    if checkpoint_joint_order != expected_checkpoint_order:
        raise ValueError("dataset checkpoint joint order changed")

    urdf_names, urdf_limits = parse_urdf_limits(urdf_path)
    if "waist_yaw_joint" not in urdf_names or "waist_pitch_joint" in urdf_names:
        raise ValueError("unexpected Cruzr S2 waist model")
    executor_text = s2_executor.read_text(encoding="utf-8")
    executor_config = yaml.safe_load(s2_executor_config.read_text(encoding="utf-8"))
    generic_text = generic_executor.read_text(encoding="utf-8")
    if "KEEP_INDICES_20_TO_17 = list(range(16)) + [19]" not in executor_text:
        raise ValueError("S2 executor no longer has the audited 20D-to-17D mapping")
    if set(re.findall(r'"(head_[^"]+|waist_[^"]+)"', executor_text)) < {
        "head_pitch_joint", "head_yaw_joint", "waist_yaw_joint"
    }:
        raise ValueError("S2 executor lock contract changed")
    expected_17d = checkpoint_joint_order[:16] + [checkpoint_joint_order[19]]
    if executor_config["actions"]["joints"]["names"] != expected_17d:
        raise ValueError("S2 executor 17D order does not match checkpoint projection")
    if "['waist_pitch_joint', 'waist_yaw_joint']" not in generic_text:
        raise ValueError("generic two-axis waist ordering not found")
    manual_text = sdk_manual.read_text(encoding="utf-8")
    if not all(token in manual_text for token in (
        "left_shoulder_pitch_motor", "left_elbow_roll_motor", "left_wrist_roll_motor",
        "right_shoulder_pitch_motor", "right_elbow_roll_motor", "right_wrist_roll_motor",
    )):
        raise ValueError("vendor SDK motor-order evidence missing")

    waist_meta_values = list(explicit[("waist", "single")]["joint_angles_parsed"])
    # Generic supplied executors order waist as [pitch, yaw]; the S2 URDF has
    # only yaw. The second XML value is therefore the sole S2 waist coordinate.
    waist_numeric_candidate = waist_meta_values[1]
    ready_20d_candidate: list[float | None] = (
        arm_values_checkpoint_order
        + list(explicit[("head", "single")]["joint_angles_parsed"])
        + [None, None, None]
        + [waist_numeric_candidate]
    )
    if len(ready_20d_candidate) != 20:
        raise ValueError("internal ready candidate is not 20D")

    forward_total = sum(forward_durations)
    supplied_preposition_duration = max(
        float(action["duration_seconds"])
        for action in supplied_actions
        if action.get("duration_seconds") is not None
    )
    supplied_nominal_total = supplied_preposition_duration + forward_total
    back_is_exact_reverse = back_goals == list(reversed(forward_goals))
    back_returns_to_forward_first_waypoint = back_goals[-1] == forward_goals[0]

    preposition_meta = (
        list(explicit[("arm", "left")]["joint_angles_parsed"])
        + list(explicit[("arm", "right")]["joint_angles_parsed"])
    )
    segment_starts = [preposition_meta, forward_goals[0]]
    meta_joint_names = [
        *(f"L_{name}_joint" for name in META_ARM_ORDER),
        *(f"R_{name}_joint" for name in META_ARM_ORDER),
    ]
    nominal_speeds = []
    for segment_index, (start, goal, duration) in enumerate(
        zip(segment_starts, forward_goals, forward_durations)
    ):
        speeds = [abs(after - before) / duration for before, after in zip(start, goal)]
        nominal_speeds.append({
            "segment_index": segment_index,
            "duration_seconds": duration,
            "max_abs_rad_s": max(speeds),
            "per_joint_rad_s": dict(zip(meta_joint_names, speeds)),
        })
    arm_velocity_limits = {
        name: urdf_limits[name]["velocity"] for name in meta_joint_names
    }
    nominal_under_urdf_velocity_limits = all(
        segment["per_joint_rad_s"][name] <= arm_velocity_limits[name]
        for segment in nominal_speeds
        for name in meta_joint_names
    )

    lifter_stats = aggregate_lifter_stats(dataset_episode_stats)
    if lifter_stats["episode_count"] != 500:
        raise ValueError("unexpected dataset episode count")
    upgrade_has_vla_task = any(
        token in upgrade_listing.read_text(encoding="utf-8")
        for token in ("s2_vla", "clamp_s2_joints_trajectory")
    )

    blockers = [
        "supplied_s2_ready_task_not_installed_or_registered",
        "ready_state_is_not_fully_defined_20d_lifter_is_inherited",
        "primitive_contains_no_explicit_joint_velocity_acceleration_or_force_limits",
        "no_swept_volume_or_collision_certificate_is_supplied",
        "back_primitive_is_not_an_exact_inverse_of_the_supplied_ready_sequence",
        "installed_registered_ready_candidates_have_different_semantics_from_supplied_s2_xml",
        "component_header_with_named_14d_fields_is_not_supplied",
        "ready_lifter_is_episode_dependent_and_has_no_single_vendor_target",
    ]
    physical_ready_pass = not blockers and supplied_registered and supplied_installed

    summary = {
        "schema": "cruzr-s2-vla-ready-artifact-audit-e4.0-v2",
        "experiment_id": "E4.0",
        "mode": "local_and_remote_read_only_artifact_resolution",
        "supplied_s2": {
            "xml_sha256": supplied_sha,
            "predicted_task_key_from_vendor_loader": supplied_task_key,
            "predicted_motion_id_from_vendor_loader": supplied_motion_id,
            "installed_directory_or_file_found": supplied_installed,
            "registered_in_task_list": supplied_registered,
            "explicit_preposition_duration_seconds": supplied_preposition_duration,
            "explicit_preposition_components": [
                "waist",
                "head",
                "right_arm",
                "left_arm",
            ],
            "final_named_action": "clamp_s2_joints_trajectory",
            "nominal_sequence_duration_seconds": supplied_nominal_total,
            "waist_meta_values": waist_meta_values,
            "waist_meta_dimension": len(waist_meta_values),
            "vla_waist_dimension": 1,
            "waist_mapping_locally_resolved": True,
            "waist_mapping_basis": [
                "S2_URDF_has_only_waist_yaw_joint",
                "generic_vendor_executor_orders_waist_pitch_then_waist_yaw",
                "S2_executor_keeps_checkpoint_index_19_waist_yaw",
            ],
            "waist_ready_value": waist_numeric_candidate,
            "present_in_supplied_v020_upgrade_archive": upgrade_has_vla_task,
        },
        "installed_forward_primitive": {
            "found": True,
            "sha256": forward_sha,
            "move_type": "follow_joint_space_trajectory",
            "component_type": 0,
            "component_location": 3,
            "durations_seconds": forward_durations,
            "goals_shape": [len(forward_goals), len(forward_goals[0])],
            "goals_14d": forward_goals,
            "nominal_duration_seconds": forward_total,
            "explicit_limits_present": False,
            "meta_component_joint_order": meta_joint_names,
            "nominal_segment_speeds": nominal_speeds,
            "nominal_speeds_below_urdf_velocity_limits": nominal_under_urdf_velocity_limits,
            "nominal_speed_is_not_a_certified_runtime_limit": True,
        },
        "installed_back_primitive": {
            "found": True,
            "sha256": back_sha,
            "durations_seconds": back_durations,
            "goals_shape": [len(back_goals), len(back_goals[0])],
            "goals_14d": back_goals,
            "exact_reverse_of_forward_goals": back_is_exact_reverse,
            "returns_to_forward_first_waypoint": back_returns_to_forward_first_waypoint,
            "restores_supplied_head_waist_and_lifter": False,
        },
        "ready_state_candidate": {
            "component_order": "left_arm_7_then_right_arm_7_in_vendor_meta_motor_order",
            "meta_arm_order": META_ARM_ORDER,
            "checkpoint_arm_order": CHECKPOINT_ARM_ORDER,
            "meta_to_checkpoint_indices": META_TO_CHECKPOINT,
            "component_order_reference": "vendor_non_s2_vla_pick_large_55_ready.xml",
            "component_order_reference_max_abs_error": inferred_order_max_abs_error,
            "joint_order_20d": checkpoint_joint_order,
            "values": ready_20d_candidate,
            "fully_defined": all(value is not None for value in ready_20d_candidate),
            "undefined_indices": [
                index for index, value in enumerate(ready_20d_candidate) if value is None
            ],
            "waist_mapping_locally_resolved": True,
            "lifter_policy": "inherit_current_state_no_numeric_target",
        },
        "urdf_contract": {
            "waist_pitch_joint_present": "waist_pitch_joint" in urdf_names,
            "waist_yaw_joint_present": "waist_yaw_joint" in urdf_names,
            "arm_velocity_limits_rad_s": arm_velocity_limits,
            "lifter_and_waist_effort_velocity_limits_are_zero_and_not_safety_usable": all(
                urdf_limits[name].get("effort") == 0.0
                and urdf_limits[name].get("velocity") == 0.0
                for name in (
                    "lifter_pitch_1_joint", "lifter_pitch_2_joint",
                    "lifter_pitch_3_joint", "waist_yaw_joint",
                )
            ),
        },
        "executor_contract": {
            "input_dim": 20,
            "projected_dim": 17,
            "kept_indices": list(range(16)) + [19],
            "drops_lifter_actions_20d_indices": [16, 17, 18],
            "locks_head_and_waist_before_physical_publication": True,
            "physical_arm_commands_only": True,
        },
        "dataset_lifter_contract": {
            **lifter_stats,
            "single_numeric_ready_target_demonstrated": False,
            "interpretation": (
                "ready_xml_inherits_lifter_and_dataset_episodes_span_multiple_"
                "lifter_configurations"
            ),
        },
        "installed_candidates": {
            "cruzr_vla_clamp_ready_file_exists": remote_clamp_ready.is_file(),
            "cruzr_vla_clamp_ready_calls_forward_primitive": remote_clamp_calls_forward,
            "cruzr_vla_clamp_ready_registered": "cruzr_vla/clamp_ready" in task_list_text,
            "transport_clamp_ready_s2_file_exists": remote_transport_s2.is_file(),
            "transport_clamp_ready_s2_calls_forward_primitive": transport_s2_calls_forward,
            "transport_clamp_ready_s2_registered": (
                'motion_id: "transport/clamp_ready_s2"' in task_list_text
            ),
            "equivalent_to_supplied_s2_xml": False,
        },
        "swept_volume": {
            "supplied": False,
            "computed_in_e4_0": False,
            "reason": "requires_urdf_fk_collision_and_fixture_work_planned_for_e4_1",
        },
        "physical_ready_pass": physical_ready_pass,
        "blockers": blockers,
        "status": "PARTIAL_RESOLUTION_BLOCKED_NOT_READY_FOR_E4_1_OR_PHYSICAL_USE",
        "next_authorized": "E4.0_READ_ONLY_REMEDIATION_OR_VENDOR_CLARIFICATION_ONLY",
        "robot_state_read": False,
        "physical_movement_commanded": False,
        "physical_publisher_created": False,
    }

    (run_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (run_dir / "resolved_ready_contract.yaml").write_text(
        yaml.safe_dump(summary, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    print("E4.0_PRIMITIVE_RESOLVED=forward:2x14/2.5s,back:2x14/5.0s")
    print("E4.0_CANONICAL_TASK_INSTALLED=0")
    print("E4.0_META_TO_CHECKPOINT_REORDER=resolved")
    print("E4.0_WAIST_MAPPING=resolved:xml[1]->waist_yaw_joint=0.0")
    print("E4.0_LIFTER_POLICY=inherited-current,no-single-numeric-ready-target")
    print("E4.0_READY_20D_COMPLETE=0; undefined=lifter[0:3]")
    print("E4.0_RESULT=PARTIAL_RESOLUTION_BLOCKED_NOT_READY_FOR_E4_1_OR_PHYSICAL_USE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
