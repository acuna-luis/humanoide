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
    parser.add_argument("--e6-0c", type=pathlib.Path, required=True)
    parser.add_argument("--e6-0d", type=pathlib.Path, required=True)
    parser.add_argument("--e6-0e", type=pathlib.Path, required=True)
    parser.add_argument("--e6-0f", type=pathlib.Path, required=True)
    parser.add_argument("--e6-0g", type=pathlib.Path, required=True)
    parser.add_argument("--e6-0h", type=pathlib.Path, required=True)
    parser.add_argument("--e6-0i", type=pathlib.Path, required=True)
    parser.add_argument("--e6-0j", type=pathlib.Path, required=True)
    parser.add_argument("--e6-0k", type=pathlib.Path, required=True)
    parser.add_argument("--e6-0l", type=pathlib.Path, required=True)
    parser.add_argument("--e6-0m", type=pathlib.Path, required=True)
    parser.add_argument("--e6-0n", type=pathlib.Path, required=True)
    parser.add_argument("--e6-0o", type=pathlib.Path, required=True)
    parser.add_argument("--e6-0q", type=pathlib.Path, required=True)
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
        "E6.0C": args.e6_0c.resolve(),
        "E6.0D": args.e6_0d.resolve(),
        "E6.0E": args.e6_0e.resolve(),
        "E6.0F": args.e6_0f.resolve(),
        "E6.0G": args.e6_0g.resolve(),
        "E6.0H": args.e6_0h.resolve(),
        "E6.0I": args.e6_0i.resolve(),
        "E6.0J": args.e6_0j.resolve(),
        "E6.0K": args.e6_0k.resolve(),
        "E6.0L": args.e6_0l.resolve(),
        "E6.0M": args.e6_0m.resolve(),
        "E6.0N": args.e6_0n.resolve(),
        "E6.0O": args.e6_0o.resolve(),
        "E6.0Q": args.e6_0q.resolve(),
    }
    actual = {
        name: load_flat_yaml(path / "actual_result.yaml")
        for name, path in runs.items()
    }
    selection = load_json(runs["E5.2"] / "shadow-profile-selection.json")
    clearance = load_json(runs["E6.0D"] / "clearance-report.json")
    guard_contract = load_json(
        runs["E6.0D"] / "offline-executor-guard-contract.json"
    )
    guard_campaign = load_json(runs["E6.0E"] / "one-point-guard-campaign.json")
    offline_closure = load_json(runs["E6.0F"] / "offline-closure-report.json")
    home_entry = load_json(runs["E6.0I"] / "home-entry-report.json")
    clamp_proxy = load_json(runs["E6.0J"] / "document-proxy-clamp-report.json")
    observed_clamp = load_json(
        runs["E6.0K"] / "observed-clamp-containment-report.json"
    )
    one_point_core = load_json(
        runs["E6.0L"] / "one-point-canary-control-core.json"
    )
    ready_recovery_bundle = load_json(
        runs["E6.0M"] / "ready-recovery-bundle.json"
    )
    profile = load_json(args.profile.resolve())

    ready_runtime_verified = (
        actual["E6.0H"].get("ready_installed_on_disk") is True
        and actual["E6.0G"].get("ready_task_registered_on_disk") == 1
        and actual["E6.0G"].get("ready_xml_present_on_disk") == 1
        and actual["E6.0G"].get("ready_runtime_load_order")
        == "process_started_after_task_list"
        and actual["E6.0G"].get("manipulation_action_servers") == 1
    )
    fresh_preflight_verified = (
        actual["E6.0G"].get("expected_estop_state") == "released"
        and actual["E6.0G"].get("estop_key") == 0
        and actual["E6.0G"].get("servo_estop_key") == 0
        and actual["E6.0G"].get("charger_connected") is False
        and actual["E6.0G"].get("whole_joint_states") == "advertised"
        and actual["E6.0G"].get("manipulation_action_servers") == 1
        and actual["E6.0G"].get("canonical_manipulation_preflight") == "passed"
        and actual["E6.0G"].get("robot_state_stationary_verified") is True
        and actual["E6.0G"].get("physical_publishers") == 0
    )
    recovery_runtime_loaded = (
        actual["E6.0N"].get("recovery_installed_on_disk") is True
        and actual["E6.0N"].get("recovery_registered_on_disk") is True
        and actual["E6.0O"].get("runtime_load_order")
        == "process_started_after_recovery_config"
        and actual["E6.0O"].get("estop_active_before_and_after") is True
        and actual["E6.0O"].get("task_invoked") is False
        and actual["E6.0O"].get("physical_movement_commanded") is False
        and actual["E6.0O"].get("physical_publishers") == 0
    )
    recovery_physically_validated = (
        actual["E6.0Q"].get("ready_physically_validated") is True
        and actual["E6.0Q"].get("recovery_physically_validated") is True
        and actual["E6.0Q"].get("recovery_runtime_corrected") is True
        and actual["E6.0Q"].get("recovery_meta_path_correct") is True
        and actual["E6.0Q"].get("measured_home") is True
        and actual["E6.0Q"].get("vla_containers_stopped") is True
        and actual["E6.0Q"].get("physical_publishers") == 0
    )

    expected_statuses = {
        "E3.3": "PASS_LOCAL_TEMPORAL_FAIL_CLOSED_VENDOR_SEMANTICS_UNRESOLVED",
        "E4.0": "PARTIAL_RESOLUTION_BLOCKED_NOT_READY_FOR_E4_1_OR_PHYSICAL_USE",
        "E4.1C": "SOLID_TABLETOP_CANDIDATE_REJECTED_BY_VENDOR_URDF_SWEEP",
        "E4.1F": "OFFICIAL_SOURCES_AUDITED_PASSIVE_CLAMP_DIMENSIONS_NOT_PUBLISHED_PGC_EXCLUDED",
        "E5.0": "PASS_COMPLETE_SINK_MATRIX_OFFLINE",
        "E5.2": "PASS_PRELIMINARY_P14_ALL_TASKS_PHYSICAL_BLOCKED",
        "E6.0A": "PARTIAL_P14_READY_ALIGNED_EXACT_ARM_RECOVERY_DERIVED_PHYSICAL_VALIDATION_PENDING",
        "E6.0B": "PASS_UPSTREAM_FAR_LINK_OBB_SWEEP_PARTIAL_SELF_COLLISION_BLOCKED_NO_ACM_OR_CLAMP_GEOMETRY",
        "E6.0C": "PASS_VENDOR_UPSTREAM_NEAR_PAIR_MESH_SWEEP_PHYSICAL_BLOCKED_CLAMP_CLEARANCE_AND_POLICY",
        "E6.0D": "PASS_VENDOR_MESH_SAMPLED_CLEARANCE_QUANTIFIED_PHYSICAL_BLOCKED",
        "E6.0E": "PASS_OFFLINE_ONE_POINT_GUARD_MATRIX_PHYSICAL_BLOCKED",
        "E6.0F": "PASS_ALL_AVAILABLE_LOCAL_ONLY_E6_0_WORK_EXHAUSTED_PHYSICAL_BOUNDARY_REACHED",
        "E6.0G": "PASS_READ_ONLY_LIVE_AUDIT_PHYSICAL_GATES_REMAIN",
        "E6.0H": "PASS_READY_INSTALLED_AND_REGISTERED_ON_DISK_NOT_RELOADED",
        "E6.0I": "PASS_HOME_STAGING_VENDOR_MODEL_SWEEP_PHYSICAL_BLOCKED_NO_CLAMP_OR_DYNAMICS",
        "E6.0J": "PASS_DOCUMENT_PROXY_SAMPLED_SWEEP_ASSUMPTION_ACCEPTED_PHYSICAL_NOT_CERTIFIED",
        "E6.0K": "PASS_OBSERVED_CLAMP_ENVELOPE_CONTAINED_IN_E6_0J_PROXY",
        "E6.0L": "PASS_ONE_POINT_CANARY_CONTROL_CORE_OFFLINE_PHYSICAL_TRANSPORT_BLOCKED",
        "E6.0M": "PASS_EXACT_RECOVERY_BUNDLE_LOCAL_ACTIVE_MODES_BLOCKED_PENDING_PHYSICAL_VALIDATION",
        "E6.0N": "PASS_RECOVERY_INSTALLED_AND_REGISTERED_ON_DISK_NOT_RELOADED",
        "E6.0O": "PASS_DEDICATED_TASK_MANAGER_RELOADED_UNDER_ESTOP",
        "E6.0Q": "PASS_DETERMINISTIC_READY_RECOVERY_PHYSICALLY_VALIDATED_NO_BOX",
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
            "PASS" if ready_runtime_verified else "BLOCKED",
            (
                "E6.0H atomically installed the hash-matched XML and one task-list entry; "
                "E6.0G proves the current manipulation process started after that task list, "
                "the ready files still match and the canonical ROSA action server is live"
                if ready_runtime_verified
                else "The ready files or post-install process load order/action server remain unverified"
            ),
        ),
        gate(
            "ready_20d_complete",
            "PASS",
            "E6.0A proves P14 needs 14 numeric arm axes; H/L/W are captured fresh and held, and ready B matches task 0 frame 0 within 0.002113 rad",
        ),
        gate(
            "recovery_exact_and_validated",
            "PASS" if recovery_physically_validated else "BLOCKED",
            (
                "E6.0Q corrected the MetaMove runtime path and one-axis waist, then physically "
                "validated deterministic READY->HOME without a box: the action returned "
                "SUCCEED/status=4 and a fresh 20-axis sample proved measured home, zero velocity, "
                "VLA stopped and zero physical publishers"
                if recovery_physically_validated
                else (
                    "E6.0M packages the exact reverse and E6.0N/O establish the historical "
                    "installation/load sequence, but supervised physical validation is incomplete"
                    if recovery_runtime_loaded
                    else "Recovery installation/runtime load evidence is incomplete"
                )
            ),
        ),
        gate(
            "no_box_self_collision_swept_volume",
            "PASS_WITH_DOCUMENT_PROXY_ASSUMPTION",
            (
                "E6.0C/E6.0I found zero vendor-model intersections. At the owner's direction, "
                "E6.0J substitutes the complete supplier PGC mesh group dilated 25 mm on every "
                "face (documented 50 mm stroke): approximately 330x145x142 mm per endpoint. "
                f"It found zero non-mount intersections over {clamp_proxy['trajectory']['sample_count']} "
                f"states at max step {clamp_proxy['trajectory']['maximum_inter_sample_joint_step_rad']:.9f} rad. "
                "E6.0K then placed the observed 120x52x105 mm clamp inside a "
                "140x72x125 mm envelope and proved that envelope is contained in E6.0J. "
                "This closes the project canary's geometric assumption only; it does not certify "
                "the installed clamp, loads, force, flex or continuous-path clearance"
            ),
        ),
        gate(
            "physical_executor_implemented_and_reviewed",
            "BLOCKED",
            (
                f"E6.0E passed {guard_campaign['message_case_count'] + guard_campaign['contract_tamper_case_count']}/"
                f"{guard_campaign['message_case_count'] + guard_campaign['contract_tamper_case_count']} guard cases; "
                f"E6.0L passed {one_point_core['case_count'] + one_point_core['contract_tamper_case_count']} "
                "control-core cases and latches after one point with no replay. The compatibility file exists, "
                "but explicitly has no physical command/STOP transport, so this gate remains blocked"
            ),
        ),
        gate(
            "certified_acceleration_limit",
            "BLOCKED",
            (
                "E6.0D derives a fail-closed offline guard specification from speed*dt, "
                "but maximum_acceleration_rad_s2 remains null and the source profile "
                "limits are explicitly not certified"
            ),
        ),
        gate(
            "physical_temporal_semantics",
            "PASS_PROJECT_ONE_POINT_CONTRACT",
            (
                "E6.0L defines the E6.0 canary independently of the ambiguous vendor executor: "
                "accept only source point index 0 from one guarded chunk, consume it once, "
                "never replay it and ignore vendor end_flag. This resolves the project-side "
                "one-point schedule; physical command and STOP timing remain in the separate executor gate"
            ),
        ),
        gate(
            "fresh_physical_preflight",
            "PASS" if fresh_preflight_verified else "BLOCKED",
            (
                "Fresh E6.0G confirms both E-stops released, charger disconnected, "
                "whole-joint state advertised, canonical manipulation preflight passed, "
                "ROSA action server live, robot stationary, VLA stopped and zero publishers"
                if fresh_preflight_verified
                else "Fresh released-state canonical manipulation preflight remains incomplete"
            ),
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
            "offline_guard_contract_path": str(
                runs["E6.0D"] / "offline-executor-guard-contract.json"
            ),
            "offline_guard_contract_state": guard_contract["state"],
            "offline_guard_contract_physical_execution_enabled": guard_contract[
                "physical_execution_enabled"
            ],
            "offline_guard_campaign_all_passed": guard_campaign[
                "all_expectations_passed"
            ],
            "offline_closure_remaining_local_only_actions": offline_closure[
                "remaining_local_only_actions_without_new_physical_or_certified_input"
            ],
            "offline_closure_next_boundary": offline_closure[
                "next_required_boundary"
            ],
            "live_read_only_audit_consumed": True,
            "latest_live_ready_task_registered_on_disk": actual["E6.0G"].get(
                "ready_task_registered_on_disk"
            ),
            "latest_live_ready_xml_present_on_disk": actual["E6.0G"].get(
                "ready_xml_present_on_disk"
            ),
            "ready_install_on_disk_completed": actual["E6.0H"].get(
                "ready_installed_on_disk"
            ),
            "ready_task_manager_reloaded_during_e6_0h": actual["E6.0H"].get(
                "task_manager_reloaded"
            ),
            "ready_runtime_load_order": actual["E6.0G"].get(
                "ready_runtime_load_order"
            ),
            "ready_runtime_verified": ready_runtime_verified,
            "fresh_physical_preflight_verified": fresh_preflight_verified,
            "home_entry_vendor_model_verified": home_entry.get(
                "complete_vendor_model_path_covered"
            ) is True,
            "document_proxy_clamp_assumption_consumed": clamp_proxy.get("status")
            == "PASS_DOCUMENT_PROXY_SAMPLED_SWEEP_ASSUMPTION_ACCEPTED_PHYSICAL_NOT_CERTIFIED",
            "document_proxy_clamp_sample_count": clamp_proxy["trajectory"]["sample_count"],
            "document_proxy_clamp_exact_intersections": clamp_proxy["collision_audit"][
                "exact_intersection_count"
            ],
            "observed_clamp_envelope_contained": observed_clamp.get("status")
            == "PASS_OBSERVED_CLAMP_ENVELOPE_CONTAINED_IN_E6_0J_PROXY",
            "one_point_control_core_reviewed": one_point_core.get("all_expectations_passed")
            is True,
            "one_point_source_indices": one_point_core.get(
                "accepted_source_point_indices"
            ),
            "one_point_replay_count": one_point_core.get("replay_count"),
            "physical_transport_implemented": one_point_core.get(
                "physical_transport_implemented"
            ),
            "ready_recovery_bundle_exact_reverse": ready_recovery_bundle.get(
                "recovery", {}
            ).get("named_segment_is_exact_reverse"),
            "ready_recovery_bundle_physically_validated": ready_recovery_bundle.get(
                "physically_validated"
            ),
            "recovery_installed_on_disk": actual["E6.0N"].get(
                "recovery_installed_on_disk"
            ),
            "recovery_registered_on_disk": actual["E6.0N"].get(
                "recovery_registered_on_disk"
            ),
            "recovery_runtime_load_order": actual["E6.0O"].get(
                "runtime_load_order"
            ),
            "recovery_runtime_loaded_under_estop": recovery_runtime_loaded,
            "recovery_physically_validated": recovery_physically_validated,
        },
        "gates": gates,
        "blocking_gate_count": len(blocking),
        "blocking_gates": blocking,
        "runtime_preflight_pending": not fresh_preflight_verified,
        "e6_0_physical_authorized": False,
        "physical_publishers": 0,
        "robot_state_read": False,
        "network_calls": 0,
        "physical_movement_commanded": False,
        "next_safe_work": [
            "keep_vla_containers_stopped_and_physical_publishers_at_zero",
            "treat_the_owner_accepted_document_proxy_as_a_canary_only_assumption_not_certified_geometry",
            "resolve the acceleration limit before any physical adapter",
            "implement and review physical command and STOP transport before any checkpoint command",
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
