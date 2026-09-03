#!/usr/bin/env python3
"""Audit the evidence gates for the no-box E6.0 physical canary."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--e3-3", type=pathlib.Path, required=True)
    parser.add_argument("--e4-0", type=pathlib.Path, required=True)
    parser.add_argument("--e4-1c", type=pathlib.Path, required=True)
    parser.add_argument("--e4-1f", type=pathlib.Path, required=True)
    parser.add_argument("--e5-0", type=pathlib.Path, required=True)
    parser.add_argument("--e5-2", type=pathlib.Path, required=True)
    parser.add_argument("--e6-0a", type=pathlib.Path, required=True)
    parser.add_argument("--e6-0b", type=pathlib.Path, required=True)
    parser.add_argument("--profile", type=pathlib.Path, required=True)
    parser.add_argument("--physical-executor", type=pathlib.Path, required=True)
    parser.add_argument("--ready-script", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path)
    return parser.parse_args()


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if value in {"true", "false"}:
        return value == "true"
    if value in {"null", "~"}:
        return None
    if value.startswith("[") and value.endswith("]"):
        return [part.strip() for part in value[1:-1].split(",") if part.strip()]
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value.strip("'\"")


def load_flat_yaml(path: pathlib.Path) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line or raw_line[0].isspace() or raw_line.lstrip().startswith("#"):
            continue
        key, separator, value = raw_line.partition(":")
        if separator:
            result[key.strip()] = parse_scalar(value)
    return result


def load_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def source_record(run_dir: pathlib.Path) -> dict[str, str]:
    actual = run_dir / "actual_result.yaml"
    return {
        "run_dir": str(run_dir.resolve()),
        "actual_result_sha256": sha256_file(actual),
        "evidence_manifest_sha256": sha256_file(run_dir / "evidence.sha256"),
    }


def gate(
    identifier: str,
    status: str,
    evidence: str,
    *,
    required_for_e6_0: bool = True,
) -> dict[str, Any]:
    return {
        "id": identifier,
        "status": status,
        "required_for_e6_0": required_for_e6_0,
        "evidence": evidence,
    }


def main() -> int:
    args = parse_args()
    runs = {
        "E3.3": args.e3_3.resolve(),
        "E4.0": args.e4_0.resolve(),
        "E4.1C": args.e4_1c.resolve(),
        "E4.1F": args.e4_1f.resolve(),
        "E5.0": args.e5_0.resolve(),
        "E5.2": args.e5_2.resolve(),
        "E6.0A": args.e6_0a.resolve(),
        "E6.0B": args.e6_0b.resolve(),
    }
    actual = {
        name: load_flat_yaml(path / "actual_result.yaml")
        for name, path in runs.items()
    }
    selection = load_json(runs["E5.2"] / "shadow-profile-selection.json")
    profile = load_json(args.profile.resolve())

    expected_statuses = {
        "E3.3": "PASS_LOCAL_TEMPORAL_FAIL_CLOSED_VENDOR_SEMANTICS_UNRESOLVED",
        "E4.0": "PARTIAL_RESOLUTION_BLOCKED_NOT_READY_FOR_E4_1_OR_PHYSICAL_USE",
        "E4.1C": "SOLID_TABLETOP_CANDIDATE_REJECTED_BY_VENDOR_URDF_SWEEP",
        "E4.1F": "OFFICIAL_SOURCES_AUDITED_PASSIVE_CLAMP_DIMENSIONS_NOT_PUBLISHED_PGC_EXCLUDED",
        "E5.0": "PASS_COMPLETE_SINK_MATRIX_OFFLINE",
        "E5.2": "PASS_PRELIMINARY_P14_ALL_TASKS_PHYSICAL_BLOCKED",
        "E6.0A": "PARTIAL_P14_READY_ALIGNED_EXACT_ARM_RECOVERY_DERIVED_PHYSICAL_VALIDATION_PENDING",
        "E6.0B": "PASS_UPSTREAM_FAR_LINK_OBB_SWEEP_PARTIAL_SELF_COLLISION_BLOCKED_NO_ACM_OR_CLAMP_GEOMETRY",
    }
    for name, expected in expected_statuses.items():
        if actual[name].get("status") != expected:
            raise SystemExit(
                f"ERROR: {name} status changed: {actual[name].get('status')!r}"
            )

    selections = selection.get("task_selections", {})
    selected_profiles = {
        str(task_id): value.get("selected_profile")
        for task_id, value in selections.items()
    }
    if selected_profiles != {str(task): "P14_A" for task in range(4)}:
        raise SystemExit(f"ERROR: unexpected E5.2 selection: {selected_profiles}")
    if profile.get("action_dim") != 20:
        raise SystemExit("ERROR: action_dim is not 20")
    if len(profile.get("commanded_joint_names", [])) != 14:
        raise SystemExit("ERROR: P14 commanded-joint contract is not 14D")

    gates = [
        gate(
            "offline_profile_selected",
            "PASS",
            "E5.2 selects P14_A for tasks 0..3; selection is replay-only",
        ),
        gate(
            "offline_sink_fail_closed",
            "PASS",
            "E5.0 passed 544/544 matrix expectations with zero publishers",
        ),
        gate(
            "offline_temporal_fault_policy",
            "PASS",
            "E3.3 passed 22/22 local temporal cases",
        ),
        gate(
            "fixture_e4_4",
            "NOT_APPLICABLE",
            "E6.0 is NO_BOX_READY with platform and B0 removed; E4.4 remains mandatory for E7+",
            required_for_e6_0=False,
        ),
        gate(
            "passive_clamp_fixture_geometry",
            "NOT_APPLICABLE",
            "No fixture or box may be present in E6.0; clamp geometry remains mandatory for E7+",
            required_for_e6_0=False,
        ),
        gate(
            "s2_ready_task_installed_and_registered",
            "BLOCKED",
            "E4.0 found supplied_s2_task_installed=false and registered=false",
        ),
        gate(
            "ready_20d_complete",
            "PASS",
            "E6.0A proves P14 needs 14 numeric arm axes; H/L/W are captured fresh and held, and ready B matches task 0 frame 0 within 0.002113 rad",
        ),
        gate(
            "recovery_exact_and_validated",
            "BLOCKED",
            "E6.0A derives exact B->A->staging arm reversal; collision and physical validation remain pending",
        ),
        gate(
            "no_box_self_collision_swept_volume",
            "BLOCKED",
            "E6.0B found zero far-link upstream OBB overlaps over 401 entry/recovery samples, but no SRDF/ACM or installed-clamp geometry exists and physical clearance remains unvalidated",
        ),
        gate(
            "physical_executor_implemented_and_reviewed",
            "BLOCKED" if not args.physical_executor.is_file() else "PENDING_REVIEW",
            (
                f"missing {args.physical_executor}"
                if not args.physical_executor.is_file()
                else f"candidate exists but is not physically authorized: {args.physical_executor}"
            ),
        ),
        gate(
            "certified_acceleration_limit",
            "BLOCKED",
            "profile has speed/delta limits but no max_interpoint_acceleration; E4.0 says explicit limits absent",
        ),
        gate(
            "physical_temporal_semantics",
            "BLOCKED",
            "E3.3 proves a local candidate only; vendor execution is 5 s inference plus 6/9 s interpolation with unresolved end behavior",
        ),
        gate(
            "fresh_physical_preflight",
            "PENDING_RUNTIME",
            "must be measured immediately before any future authorized motion",
        ),
    ]
    blocking = [
        item["id"]
        for item in gates
        if item["required_for_e6_0"] and item["status"] in {"BLOCKED", "PENDING_REVIEW"}
    ]
    report = {
        "schema": "cruzr-s2-vla-canary-readiness-e6.0-check-v1",
        "experiment_id": "E6.0-CHECK",
        "mode": "local_read_only_evidence_audit_no_robot_no_ros_no_publisher",
        "requested_canary": {
            "task_id": 0,
            "axis_profile": "P14_A",
            "scenario": "NO_BOX_READY",
            "point_count": 1,
        },
        "sources": {name: source_record(path) for name, path in runs.items()},
        "profile": {
            "path": str(args.profile.resolve()),
            "sha256": sha256_file(args.profile.resolve()),
            "action_dim": profile["action_dim"],
            "commanded_axis_count": len(profile["commanded_joint_names"]),
            "locked_axis_count": len(profile.get("locked_joint_names", [])),
            "has_speed_limit": "max_interpoint_speed" in profile,
            "has_acceleration_limit": "max_interpoint_acceleration" in profile,
        },
        "implementation": {
            "ready_script_path": str(args.ready_script),
            "ready_script_exists": args.ready_script.is_file(),
            "physical_executor_path": str(args.physical_executor),
            "physical_executor_exists": args.physical_executor.is_file(),
        },
        "gates": gates,
        "blocking_gate_count": len(blocking),
        "blocking_gates": blocking,
        "runtime_preflight_pending": True,
        "e6_0_physical_authorized": False,
        "physical_publishers": 0,
        "robot_state_read": False,
        "network_calls": 0,
        "physical_movement_commanded": False,
        "next_safe_work": [
            "resolve_and_validate_the_S2_ready_and_recovery_contract",
            "resolve_near_link_allowed_collisions_and_installed_clamp_geometry_then_validate_physical_clearance",
            "implement_and_review_an_offline_first_P14_executor_with_acceleration_and_temporal_guards",
        ],
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    print("E6.0_CHECK_MODE=local-evidence-only,no-robot,no-network,no-publisher")
    print("E6.0_PROFILE=P14_A,task:0,scenario:NO_BOX_READY")
    print("E6.0_FIXTURE_GATE=not-applicable-to-no-box;required-for-E7+")
    print(f"E6.0_BLOCKING_GATE_COUNT={len(blocking)}")
    print("E6.0_BLOCKING_GATES=" + ",".join(blocking))
    print("E6.0_PHYSICAL_AUTHORIZED=0")
    if args.output:
        print(f"E6.0_READINESS_REPORT={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
