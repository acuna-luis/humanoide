#!/usr/bin/env python3
"""Audit E6.1B ENTRY/recovery previews and exact task-0 shadow gates offline."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET
from typing import Any


CHECKPOINT_TO_META = (2, 3, 4, 0, 1, 5, 6)


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def floats(text: str) -> list[float]:
    return [float(part.strip()) for part in text.split(";") if part.strip()]


def parse_preview(path: Path) -> tuple[dict[str, list[float]], float]:
    root = ET.parse(path).getroot()
    parallel = root.find(".//Parallel")
    if parallel is None or parallel.attrib.get("threshold") != "5":
        raise ValueError(f"{path.name}: expected a five-component Parallel")
    result: dict[str, list[float]] = {}
    durations: set[float] = set()
    for action in parallel.findall("Action"):
        key = f"{action.attrib.get('type')}:{action.attrib.get('location')}"
        if key in result:
            raise ValueError(f"{path.name}: duplicate component {key}")
        result[key] = floats(action.attrib["joint_angles"])
        durations.add(float(action.attrib["duration"]))
    expected = {"arm:left", "arm:right", "head:single", "lifter:single", "waist:single"}
    if set(result) != expected or len(durations) != 1:
        raise ValueError(f"{path.name}: incomplete components or inconsistent duration")
    expected_lengths = {
        "arm:left": 7,
        "arm:right": 7,
        "head:single": 2,
        "lifter:single": 3,
        "waist:single": 1,
    }
    for key, length in expected_lengths.items():
        if len(result[key]) != length:
            raise ValueError(f"{path.name}: {key} has {len(result[key])}, expected {length}")
    return result, durations.pop()


def checkpoint_to_components(values: list[float]) -> dict[str, list[float]]:
    if len(values) != 20:
        raise ValueError("20D endpoint required")
    left = [values[index] for index in CHECKPOINT_TO_META]
    right = [values[7 + index] for index in CHECKPOINT_TO_META]
    return {
        "arm:left": left,
        "arm:right": right,
        "head:single": values[14:16],
        "lifter:single": values[16:19],
        "waist:single": values[19:20],
    }


def max_component_error(
    observed: dict[str, list[float]], expected: dict[str, list[float]]
) -> float:
    return max(
        abs(actual - reference)
        for key in expected
        for actual, reference in zip(observed[key], expected[key], strict=True)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--entry-xml", type=Path, required=True)
    parser.add_argument("--recovery-xml", type=Path, required=True)
    parser.add_argument("--e6-1a-report", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    contract = load_object(args.contract)
    profile = load_object(args.profile)
    source_report = load_object(args.e6_1a_report)
    candidate = load_object(args.candidate)
    if contract.get("schema") != "cruzr-s2-vla-task0-entry-recovery-e6.1b-v1":
        raise ValueError("unexpected E6.1B contract")
    if source_report.get("schema") != "cruzr-s2-vla-task0-entry-path-e6.1a-v1":
        raise ValueError("unexpected E6.1A report")
    if source_report.get("status") != "PASS_OFFLINE_TASK0_ENTRY_CANDIDATE_PHYSICAL_AND_SHADOW_STILL_BLOCKED":
        raise ValueError("E6.1A is not the expected offline PASS")
    if sha256(args.e6_1a_report) != contract["sources"]["e6_1a_report_sha256"]:
        raise ValueError("E6.1A report hash changed")
    if sha256(args.candidate) != contract["sources"]["candidate_json_sha256"]:
        raise ValueError("candidate hash changed")

    frozen = contract["candidate"]
    for key, source_key in (
        ("entry_state_20d_rad", "state"),
        ("first_action_20d_rad", "action"),
    ):
        if frozen[key] != candidate[source_key]:
            raise ValueError(f"contract {key} differs from episode candidate")
    if frozen["episode"] != "episode_000040" or frozen["frame"] != 0:
        raise ValueError("candidate identity is not episode_000040/frame 0")
    if frozen["joint_order"] != profile["joint_names"]:
        raise ValueError("profile and frozen candidate joint order differ")

    first_deltas = [
        abs(action - state)
        for action, state in zip(
            frozen["first_action_20d_rad"], frozen["entry_state_20d_rad"], strict=True
        )
    ]
    maximum_first_delta = max(first_deltas[:14])
    if maximum_first_delta > contract["shadow_gate"]["maximum_p14_first_point_delta_rad"]:
        raise ValueError("frozen first action exceeds P14 shadow limit")

    if profile.get("commanded_joint_names") != frozen["joint_order"][:14]:
        raise ValueError("E6.1B profile is not P14")
    if profile.get("locked_joint_names") != frozen["joint_order"][14:]:
        raise ValueError("E6.1B locked axes changed")
    if profile.get("max_first_point_delta", [])[:14] != [0.1] * 14:
        raise ValueError("E6.1B P14 first-point limit is not exactly 0.1 rad")
    if profile.get("state_defaults") != {}:
        raise ValueError("E6.1B profile must reject missing live state axes")

    entry_components, entry_duration = parse_preview(args.entry_xml)
    recovery_components, recovery_duration = parse_preview(args.recovery_xml)
    expected_duration = float(contract["trajectory_preview"]["duration_seconds_each_direction"])
    if entry_duration != expected_duration or recovery_duration != expected_duration:
        raise ValueError("preview duration differs from audited E6.1A duration")
    entry_error = max_component_error(
        entry_components, checkpoint_to_components(frozen["entry_state_20d_rad"])
    )
    recovery_error = max_component_error(
        recovery_components, checkpoint_to_components(frozen["historical_home_20d_rad"])
    )
    if entry_error > 1e-12 or recovery_error > 1e-12:
        raise ValueError("preview endpoint mapping differs from frozen 20D endpoints")

    physical_flags = {
        "contract_physical_execution_authorized": contract["physical_execution_authorized"],
        "contract_physical_publisher_implemented": contract["physical_publisher_implemented"],
        "contract_persistent_install_implemented": contract["persistent_install_implemented"],
        "preview_install_or_run_interface_present": contract["trajectory_preview"][
            "install_or_run_interface_present"
        ],
    }
    if any(physical_flags.values()):
        raise ValueError("an E6.1B offline artifact unexpectedly enables physical use")

    report = {
        "schema": "cruzr-s2-vla-task0-entry-recovery-audit-e6.1b-v1",
        "experiment_id": "E6.1B",
        "status": "PASS_OFFLINE_IMPLEMENTATION_FIXTURE_AND_LIVE_SHADOW_PENDING",
        "mode": "local_offline_no_robot_no_network_no_ros_no_container_no_publisher",
        "candidate": {
            "episode": frozen["episode"],
            "frame": frozen["frame"],
            "task_id": 0,
            "scenario": contract["scenario"],
            "maximum_p14_first_action_delta_rad": maximum_first_delta,
        },
        "entry_recovery_previews": {
            "entry_xml_sha256": sha256(args.entry_xml),
            "recovery_xml_sha256": sha256(args.recovery_xml),
            "duration_seconds_each_direction": entry_duration,
            "entry_endpoint_mapping_max_error_rad": entry_error,
            "recovery_endpoint_mapping_max_error_rad": recovery_error,
            "endpoints_exact": True,
            "runtime_law_equivalence_demonstrated": False,
            "registered_or_installed": False,
        },
        "entry_gate": {
            "exact_frozen_frame_required": True,
            "maximum_distance_rad": contract["entry_gate"][
                "maximum_chebyshev_distance_to_frozen_frame_rad"
            ],
            "task0_bounds_required": True,
            "fresh_state_required_for_live_shadow": True,
        },
        "fixture_gate": {
            "measured_manifest_required": True,
            "photo_hash_required": True,
            "collision_screened_reference_width_depth_thickness_m": contract["fixture_gate"][
                "collision_screened_reference_width_depth_thickness_m"
            ],
            "height_range_m": contract["fixture_gate"][
                "support_surface_height_floor_range_m"
            ],
            "physical_fixture_frozen": False,
        },
        "available_table_observation": contract["available_table_observation"],
        "shadow_gate": contract["shadow_gate"],
        "physical_flags": physical_flags,
        "physical_execution_authorized": False,
        "robot_accessed": False,
        "network_calls": 0,
        "ros_imported": False,
        "persistent_container_started": False,
        "physical_publishers": 0,
        "physical_movement_commanded": False,
        "next_gate": "FREEZE_MEASURED_FIXTURE_AND_REVIEW_SEPARATE_PHYSICAL_ENTRY_THEN_RUN_FIVE_SHADOW",
        "source_sha256": {
            path.name: sha256(path)
            for path in (
                args.contract,
                args.profile,
                args.entry_xml,
                args.recovery_xml,
                args.e6_1a_report,
                args.candidate,
            )
        },
    }
    rendered = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print("E6.1B_STATUS=" + report["status"])
    print(f"E6.1B_CANDIDATE=episode_000040,frame:0,task:0")
    print(f"E6.1B_P14_FIRST_DELTA_RAD={maximum_first_delta:.9f}")
    print(f"E6.1B_ENTRY_RECOVERY_ENDPOINT_ERROR_RAD={max(entry_error, recovery_error):.12f}")
    print("E6.1B_FIXTURE_FROZEN=0")
    print("E6.1B_FIVE_SHADOW_COMPLETED=0")
    print("E6.1B_PHYSICAL_AUTHORIZED=0")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, TypeError, ValueError, OSError, ET.ParseError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=__import__("sys").stderr)
        raise SystemExit(2) from exc
