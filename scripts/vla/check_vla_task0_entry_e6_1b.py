#!/usr/bin/env python3
"""Fail-closed fixture and exact 20D ENTRY gate for E6.1B.

This standard-library-only checker cannot use ROS, a network, or a command
publisher.  A PASS qualifies five task-matched shadow repetitions only; it
never authorizes an ENTRY motion or a physical checkpoint command.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import time
from typing import Any


def load_object(path: Path, label: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def finite_number(value: Any, label: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def finite_vector(value: Any, length: int, label: str) -> list[float]:
    if not isinstance(value, list) or len(value) != length:
        raise ValueError(f"{label} must contain exactly {length} values")
    return [finite_number(item, f"{label}[{index}]") for index, item in enumerate(value)]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_fixture(
    contract: dict[str, Any], manifest: dict[str, Any], manifest_path: Path
) -> tuple[list[str], dict[str, Any]]:
    reasons: list[str] = []
    if manifest.get("schema") != "cruzr-s2-vla-supported-low-fixture-e6.1b-v1":
        raise ValueError("unexpected fixture manifest schema")
    if manifest.get("scenario") != contract["scenario"]:
        reasons.append("fixture_scenario_mismatch")
    if manifest.get("movement_authorized") is not False:
        raise ValueError("fixture manifest must explicitly keep movement_authorized=false")
    if manifest.get("physical_fixture_frozen") is not True:
        reasons.append("physical_fixture_not_frozen")
    measured_at = manifest.get("measured_at")
    if not isinstance(measured_at, str) or not measured_at.strip():
        reasons.append("fixture_measurement_timestamp_missing")

    uncertainty = finite_number(
        manifest.get("measurement_uncertainty_m"), "measurement_uncertainty_m"
    )
    if not 0.0 < uncertainty <= 0.005:
        reasons.append("fixture_measurement_uncertainty_out_of_range")

    fixture_gate = contract["fixture_gate"]
    support = manifest.get("support")
    if not isinstance(support, dict):
        raise ValueError("support must be an object")
    support_values = [
        finite_number(support.get("width_m"), "support.width_m"),
        finite_number(support.get("depth_m"), "support.depth_m"),
        finite_number(support.get("thickness_m"), "support.thickness_m"),
    ]
    support_nominal = finite_vector(
        fixture_gate["support_nominal_width_depth_thickness_m"], 3, "support nominal"
    )
    support_deviation = [
        abs(observed - expected)
        for observed, expected in zip(support_values, support_nominal, strict=True)
    ]
    if any(deviation > uncertainty for deviation in support_deviation):
        reasons.append("support_geometry_differs_from_audited_candidate")
    if not all(support.get(flag) is True for flag in ("rigid", "stable", "locked")):
        reasons.append("support_not_rigid_stable_and_locked")

    support_height = finite_number(
        support.get("surface_height_floor_m"), "support.surface_height_floor_m"
    )
    height_low, height_high = finite_vector(
        fixture_gate["support_surface_height_floor_range_m"], 2, "height range"
    )
    if support_height - uncertainty < height_low or support_height + uncertainty > height_high:
        reasons.append("support_height_uncertainty_outside_reconstructed_range")

    box = manifest.get("box")
    if not isinstance(box, dict):
        raise ValueError("box must be an object")
    box_lwh = finite_vector(box.get("lwh_m"), 3, "box.lwh_m")
    box_nominal = finite_vector(fixture_gate["box_nominal_lwh_m"], 3, "box nominal")
    box_tolerance = finite_number(
        fixture_gate["box_dimension_tolerance_m"], "box dimension tolerance"
    )
    if any(
        abs(observed - expected) > box_tolerance
        for observed, expected in zip(box_lwh, box_nominal, strict=True)
    ):
        reasons.append("box_dimensions_outside_task0_nominal_tolerance")
    required_box = fixture_gate["required_box_properties"]
    for key, expected in required_box.items():
        if box.get(key) != expected:
            reasons.append(f"box_property_mismatch:{key}")
    if box.get("supported_and_stable") is not True:
        reasons.append("box_not_supported_and_stable")

    evidence = manifest.get("evidence_files")
    evidence_results: list[dict[str, Any]] = []
    if not isinstance(evidence, list) or not evidence:
        reasons.append("fixture_photo_hash_missing")
    else:
        for index, item in enumerate(evidence):
            if not isinstance(item, dict):
                raise ValueError(f"evidence_files[{index}] must be an object")
            source = Path(str(item.get("path", "")))
            if not source.is_absolute():
                source = manifest_path.parent / source
            source = source.resolve()
            expected_hash = str(item.get("sha256", ""))
            if not source.is_file():
                reasons.append(f"fixture_evidence_missing:{index}")
                continue
            actual_hash = file_sha256(source)
            if expected_hash != actual_hash:
                reasons.append(f"fixture_evidence_hash_mismatch:{index}")
            evidence_results.append(
                {"path": str(source), "sha256": actual_hash, "hash_matches": expected_hash == actual_hash}
            )

    return reasons, {
        "fixture_id": manifest.get("fixture_id"),
        "measured_at": measured_at,
        "measurement_uncertainty_m": uncertainty,
        "support_width_depth_thickness_m": support_values,
        "support_nominal_deviation_m": support_deviation,
        "support_surface_height_floor_m": support_height,
        "box_lwh_m": box_lwh,
        "evidence_files": evidence_results,
    }


def validate_state(
    contract: dict[str, Any], report: dict[str, Any], state: dict[str, Any], require_fresh: bool
) -> tuple[list[str], dict[str, Any]]:
    reasons: list[str] = []
    if report.get("schema") != "cruzr-s2-vla-dataset-entry-states-v1":
        raise ValueError("unexpected dataset entry report schema")
    candidate = contract["candidate"]
    names = candidate["joint_order"]
    observed_names = state.get("names")
    if observed_names != names:
        reasons.append("state_joint_order_not_exact")
    positions = finite_vector(state.get("positions"), 20, "state.positions")
    velocities = finite_vector(state.get("velocities"), 20, "state.velocities")
    reference = finite_vector(candidate["entry_state_20d_rad"], 20, "entry reference")
    deltas = [abs(value - expected) for value, expected in zip(positions, reference, strict=True)]
    maximum_index = max(range(20), key=deltas.__getitem__)
    maximum_velocity = max(abs(value) for value in velocities)
    gate = contract["entry_gate"]
    if deltas[maximum_index] > finite_number(
        gate["maximum_chebyshev_distance_to_frozen_frame_rad"], "entry distance limit"
    ):
        reasons.append("state_not_close_to_frozen_episode_000040_frame_0")
    if maximum_velocity > finite_number(
        gate["maximum_absolute_velocity_rad_s"], "velocity limit"
    ):
        reasons.append("state_not_stationary")

    task_report = report.get("tasks", {}).get("0")
    if not isinstance(task_report, dict):
        raise ValueError("dataset report is missing task 0")
    outside_bounds = []
    for index, name in enumerate(names):
        bounds = task_report["frame_zero_state"][name]
        if positions[index] < float(bounds["min"]) or positions[index] > float(bounds["max"]):
            outside_bounds.append(name)
    if outside_bounds:
        reasons.append("state_outside_task0_frame_zero_bounds")

    observed_at = finite_number(state.get("observed_at_unix"), "state.observed_at_unix")
    age = time.time() - observed_at
    if require_fresh:
        maximum_age = finite_number(gate["maximum_state_age_seconds"], "state age limit")
        if age < -1.0 or age > maximum_age:
            reasons.append("state_not_fresh")

    return reasons, {
        "observed_at_unix": observed_at,
        "age_seconds_at_validation": age,
        "maximum_chebyshev_distance_rad": deltas[maximum_index],
        "maximum_distance_joint_index": maximum_index,
        "maximum_distance_joint": names[maximum_index],
        "maximum_absolute_velocity_rad_s": maximum_velocity,
        "outside_task0_frame_zero_bounds": outside_bounds,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--dataset-report", type=Path, required=True)
    parser.add_argument("--fixture-manifest", type=Path, required=True)
    parser.add_argument("--state-json", type=Path)
    parser.add_argument("--require-fresh-state", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    contract = load_object(args.contract, "contract")
    report = load_object(args.dataset_report, "dataset report")
    manifest = load_object(args.fixture_manifest, "fixture manifest")
    if contract.get("schema") != "cruzr-s2-vla-task0-entry-recovery-e6.1b-v1":
        raise ValueError("unexpected E6.1B contract schema")
    if contract.get("physical_execution_authorized") is not False:
        raise ValueError("E6.1B contract must not authorize physical execution")

    fixture_reasons, fixture_metrics = validate_fixture(contract, manifest, args.fixture_manifest)
    state_reasons: list[str] = []
    state_metrics: dict[str, Any] | None = None
    if args.state_json:
        state = load_object(args.state_json, "state")
        state_reasons, state_metrics = validate_state(
            contract, report, state, args.require_fresh_state
        )
    elif args.require_fresh_state:
        raise ValueError("--require-fresh-state requires --state-json")

    reasons = fixture_reasons + state_reasons
    result = {
        "schema": "cruzr-s2-vla-task0-entry-assessment-e6.1b-v1",
        "mode": "local_gate_no_ros_no_network_no_publisher",
        "task_id": 0,
        "scenario": contract["scenario"],
        "candidate_episode": contract["candidate"]["episode"],
        "candidate_frame": contract["candidate"]["frame"],
        "fixture": fixture_metrics,
        "state": state_metrics,
        "fixture_qualified": not fixture_reasons,
        "entry_state_qualified": args.state_json is not None and not state_reasons,
        "qualified_for_five_shadow": args.state_json is not None and not reasons,
        "physical_execution_authorized": False,
        "rejection_reasons": reasons,
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
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=__import__("sys").stderr)
        raise SystemExit(2) from exc
