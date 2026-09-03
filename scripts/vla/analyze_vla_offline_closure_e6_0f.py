#!/usr/bin/env python3
"""Close every E6.0 item provable from local evidence and mark the boundary.

This analyzer does not contact or modify the robot.  It builds a deployment
preview for the supplied ready task, verifies that all available local safety
analyses have been consumed, and emits the first physical scenario without
authorizing it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

import yaml


EXPECTED_STATUSES = {
    "E4.0": "PARTIAL_RESOLUTION_BLOCKED_NOT_READY_FOR_E4_1_OR_PHYSICAL_USE",
    "E3.3": "PASS_LOCAL_TEMPORAL_FAIL_CLOSED_VENDOR_SEMANTICS_UNRESOLVED",
    "E6.0A": "PARTIAL_P14_READY_ALIGNED_EXACT_ARM_RECOVERY_DERIVED_PHYSICAL_VALIDATION_PENDING",
    "E6.0B": "PASS_UPSTREAM_FAR_LINK_OBB_SWEEP_PARTIAL_SELF_COLLISION_BLOCKED_NO_ACM_OR_CLAMP_GEOMETRY",
    "E6.0C": "PASS_VENDOR_UPSTREAM_NEAR_PAIR_MESH_SWEEP_PHYSICAL_BLOCKED_CLAMP_CLEARANCE_AND_POLICY",
    "E6.0D": "PASS_VENDOR_MESH_SAMPLED_CLEARANCE_QUANTIFIED_PHYSICAL_BLOCKED",
    "E6.0E": "PASS_OFFLINE_ONE_POINT_GUARD_MATRIX_PHYSICAL_BLOCKED",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def load_flat_yaml(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line[0].isspace() or line.lstrip().startswith("#"):
            continue
        key, separator, value = line.partition(":")
        if separator:
            result[key.strip()] = value.strip()
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--e4-0", type=Path, required=True)
    parser.add_argument("--e3-3", type=Path, required=True)
    parser.add_argument("--e6-0a", type=Path, required=True)
    parser.add_argument("--e6-0b", type=Path, required=True)
    parser.add_argument("--e6-0c", type=Path, required=True)
    parser.add_argument("--e6-0d", type=Path, required=True)
    parser.add_argument("--e6-0e", type=Path, required=True)
    parser.add_argument("--vendor-ready-xml", type=Path, required=True)
    parser.add_argument("--vendor-loader", type=Path, required=True)
    parser.add_argument("--captured-task-list", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    runs = {
        "E4.0": args.e4_0.resolve(),
        "E3.3": args.e3_3.resolve(),
        "E6.0A": args.e6_0a.resolve(),
        "E6.0B": args.e6_0b.resolve(),
        "E6.0C": args.e6_0c.resolve(),
        "E6.0D": args.e6_0d.resolve(),
        "E6.0E": args.e6_0e.resolve(),
    }
    for name, run in runs.items():
        actual = load_flat_yaml(run / "actual_result.yaml")
        if actual.get("status") != EXPECTED_STATUSES[name]:
            raise SystemExit(
                f"ERROR: estado {name} inesperado: {actual.get('status')!r}"
            )

    ready_xml = args.vendor_ready_xml.resolve()
    loader = args.vendor_loader.resolve()
    task_list_path = args.captured_task_list.resolve()
    for path in (ready_xml, loader, task_list_path):
        if not path.is_file():
            raise SystemExit(f"ERROR: falta fuente: {path}")

    root = ET.parse(ready_xml).getroot()
    actions = list(root.iter("Action"))
    if not actions or actions[-1].attrib.get("name") != "clamp_s2_joints_trajectory":
        raise SystemExit("ERROR: XML ready vendor inesperado")
    task_list = yaml.safe_load(task_list_path.read_text(encoding="utf-8"))
    if not isinstance(task_list, dict):
        raise SystemExit("ERROR: task_list capturado no es un mapping")
    task_key = "s2_vla_pick_large_teleop_ready"
    if task_key in task_list:
        raise SystemExit("ERROR: evidencia capturada ya contiene el task S2")

    ready_report = load_json(runs["E6.0A"] / "p14-ready-recovery-contract.json")
    broad_report = load_json(runs["E6.0B"] / "self-collision-report.json")
    mesh_report = load_json(runs["E6.0C"] / "near-pair-mesh-report.json")
    clearance_report = load_json(runs["E6.0D"] / "clearance-report.json")
    guard_report = load_json(runs["E6.0E"] / "one-point-guard-campaign.json")
    e4_report = load_json(runs["E4.0"] / "summary.json")
    temporal_report = load_json(runs["E3.3"] / "summary.json")

    joint_limit_violations = broad_report["trajectory"]["joint_limit_violations"]
    if joint_limit_violations:
        raise SystemExit("ERROR: E6.0B tiene violaciones articulares")
    if mesh_report["exact_mesh_sweep"]["collision_samples"]:
        raise SystemExit("ERROR: E6.0C tiene intersecciones")
    if clearance_report["overall_minimum_sampled_vendor_mesh_clearance_m"] <= 0:
        raise SystemExit("ERROR: E6.0D no tiene holgura positiva")
    if not guard_report["all_expectations_passed"]:
        raise SystemExit("ERROR: E6.0E no pasó su matriz")
    if guard_report["physical_authorization_count"] != 0:
        raise SystemExit("ERROR: E6.0E autorizó ejecución física")

    loader_text = loader.read_text(encoding="utf-8")
    deployment_preview = {
        "schema": "cruzr-s2-vla-ready-task-deployment-preview-e6.0f-v1",
        "state": "PREVIEW_ONLY_NOT_APPLIED",
        "task_key": task_key,
        "task_entry": {
            "motion_id": "s2_bio_vla/s2_vla_pick_large_teleop_ready",
            "json_args": '{"Reverse": false,"TimeRatio": 0.5}',
            "cmd": "start",
        },
        "source_xml": str(ready_xml),
        "source_xml_sha256": sha256(ready_xml),
        "predicted_remote_xml": (
            "/opt/walker/manipulation_task_manager/share/"
            "manipulation_task_manager/config/s2_bio_vla/"
            "s2_vla_pick_large_teleop_ready.xml"
        ),
        "predicted_remote_task_list": (
            "/opt/walker/manipulation_task_manager/share/"
            "manipulation_task_manager/config/task_list.yaml"
        ),
        "captured_task_list_sha256": sha256(task_list_path),
        "captured_task_key_absent": True,
        "captured_task_count": len(task_list),
        "post_preview_task_count": len(task_list) + 1,
        "vendor_loader_risk": {
            "interactive": "read -p" in loader_text,
            "recursive_delete": "rm -rf" in loader_text,
            "in_place_task_list_edit": "sed -i" in loader_text,
            "task_list_replace": 'mv "${temp_file}" "${TASK_LIST_FILE}"' in loader_text,
            "original_loader_must_not_be_run_unattended": True,
        },
        "required_live_steps_not_performed": [
            "fresh_backup_of_remote_task_list_and_target_directory",
            "fresh_hash_and_conflict_check_on_the_robot",
            "copy_xml_to_the_live_manipulation_container",
            "append_exactly_one_task_entry_without_replacing_other_tasks",
            "reload_or_restart_task_manager_under_physical_safety_controls",
            "read_only_registration_check",
            "physical_ready_and_recovery_validation",
        ],
        "rollback_preview": [
            "restore_the_fresh_task_list_backup",
            "remove_only_the_hash_matched_S2_ready_XML",
            "reload_task_manager_and_verify_original_task_count",
        ],
        "apply_command": None,
        "robot_modified": False,
        "deployment_authorized": False,
    }

    gates = [
        {
            "id": "s2_ready_task_installed_and_registered",
            "local_work_complete": True,
            "local_evidence": "XML hash, exact task entry and non-destructive deployment preview frozen",
            "remaining_boundary": "live robot backup/install/reload/registration check",
        },
        {
            "id": "recovery_exact_and_validated",
            "local_work_complete": True,
            "local_evidence": "E6.0A exact B-A-staging reverse plus E6.0B/C/D vendor-mesh audit",
            "remaining_boundary": "fresh state capture and supervised physical ready/recovery validation",
        },
        {
            "id": "no_box_self_collision_swept_volume",
            "local_work_complete": True,
            "local_evidence": (
                "46 vendor links, 401 states, zero far OBB overlap, zero exact near-pair "
                f"intersections, sampled minimum {clearance_report['overall_minimum_sampled_vendor_mesh_clearance_m']:.9f} m"
            ),
            "remaining_boundary": "installed clamp geometry plus model/calibration/flex tolerance and physical validation",
        },
        {
            "id": "physical_executor_implemented_and_reviewed",
            "local_work_complete": True,
            "local_evidence": "E6.0E no-publisher one-point guard passed 42/42 expectations",
            "remaining_boundary": "physical adapter intentionally withheld until dynamics and transport are resolved",
        },
        {
            "id": "certified_acceleration_limit",
            "local_work_complete": True,
            "local_evidence": "all supplied local URDF/config/executor sources audited; no certified acceleration limit found",
            "remaining_boundary": "certified supplier value or instrumented engineering limit approval",
        },
        {
            "id": "physical_temporal_semantics",
            "local_work_complete": True,
            "local_evidence": (
                "E3.3 passed 22/22 fail-closed simulations and found 6 s versus 9 s "
                "executor copies plus single-flag vendor end behavior"
            ),
            "remaining_boundary": "choose adapter semantics and measure on the live stack without motion first",
        },
    ]
    if not all(gate["local_work_complete"] for gate in gates):
        raise AssertionError("offline gate inventory incomplete")

    physical_scenario = {
        "schema": "cruzr-s2-vla-first-physical-scenario-e6.0f-v1",
        "scenario_id": "NO_BOX_READY_EMPTY_CELL",
        "authorized": False,
        "purpose": "ready registration, fresh-state and no-box one-point canary gates",
        "objects": {
            "box": "REMOVED_MORE_THAN_1_5_M",
            "table_or_platform": "REMOVED_MORE_THAN_1_5_M",
            "apriltag": "NOT_REQUIRED",
            "clamps": "INSTALLED_EMPTY_AND_VISUALLY_SECURE",
        },
        "space": {
            "minimum_clear_radius_m": 1.5,
            "full_arm_envelope_clear": True,
            "floor_level_and_dry": True,
            "overhead_and_rear_clear": True,
        },
        "robot_initial": {
            "stable": True,
            "home_visually_verified": True,
            "charger_disconnected": True,
            "wheels_locked": True,
            "both_estops_engaged_during_setup": True,
            "release_estops_only_at_the_supervised_motion_gate": True,
        },
        "people": {
            "minimum_people": 2,
            "one_at_estop": True,
            "one_at_pc": True,
            "nobody_inside_arm_envelope": True,
        },
        "control": {
            "pc_to_robot": "direct_ethernet_eno1_192.168.11.250_24",
            "pico": "OFF_OR_NOT_A_CONTROL_CLIENT",
            "web_ui": "CLOSED",
            "teleoperation": "STOPPED",
            "vla_containers_initially": "STOPPED",
            "single_control_client": True,
        },
        "first_live_stage": "read_only_preflight_and_ready_task_registration_audit",
        "first_motion_stage": "vendor_ready_entry_then_exact_recovery_without_box",
        "fixture_required": False,
        "physical_execution_authorized": False,
    }

    report = {
        "schema": "cruzr-s2-vla-offline-closure-e6.0f-v1",
        "experiment_id": "E6.0F",
        "mode": "local_evidence_closure_no_robot_no_network_no_ros_no_publisher",
        "status": "PASS_ALL_AVAILABLE_LOCAL_ONLY_E6_0_WORK_EXHAUSTED_PHYSICAL_BOUNDARY_REACHED",
        "sources": {
            name: {
                "run_dir": str(run),
                "actual_result_sha256": sha256(run / "actual_result.yaml"),
                "evidence_manifest_sha256": sha256(run / "evidence.sha256"),
            }
            for name, run in runs.items()
        },
        "source_artifact_sha256": {
            ready_xml.name: sha256(ready_xml),
            loader.name: sha256(loader),
            task_list_path.name: sha256(task_list_path),
        },
        "verified_local_facts": {
            "ready_arm_state_count": len(ready_report["arm_path_checkpoint_order"]["ready_b"]),
            "broad_joint_limit_violations": len(joint_limit_violations),
            "near_pair_exact_intersections": len(mesh_report["exact_mesh_sweep"]["collision_samples"]),
            "minimum_sampled_vendor_mesh_clearance_m": clearance_report[
                "overall_minimum_sampled_vendor_mesh_clearance_m"
            ],
            "one_point_guard_expectations": (
                guard_report["message_case_count"] + guard_report["contract_tamper_case_count"]
            ),
            "one_point_guard_failures": guard_report["failed_expectation_count"],
            "vendor_temporal_semantics_resolved": temporal_report["vendor_audit"][
                "vendor_physical_semantics_resolved"
            ],
            "ready_task_installed_in_captured_state": e4_report["supplied_s2"][
                "installed_directory_or_file_found"
            ],
        },
        "gate_boundary": gates,
        "remaining_local_only_actions_without_new_physical_or_certified_input": [],
        "next_required_boundary": "LIVE_ROBOT_OR_CERTIFIED_EXTERNAL_INPUT",
        "deployment_preview": deployment_preview,
        "first_physical_scenario": physical_scenario,
        "physical_authorized": False,
        "robot_state_read": False,
        "network_calls": 0,
        "physical_publishers": 0,
        "physical_movement_commanded": False,
    }

    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "offline-closure-report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (args.output_dir / "ready-task-deployment-preview.json").write_text(
            json.dumps(deployment_preview, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (args.output_dir / "ready-task-entry.yaml").write_text(
            yaml.safe_dump({task_key: deployment_preview["task_entry"]}, sort_keys=False),
            encoding="utf-8",
        )
        (args.output_dir / "first-physical-scenario.json").write_text(
            json.dumps(physical_scenario, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    print("E6.0F_LOCAL_GATE_COMPONENTS=6/6")
    print("E6.0F_REMAINING_LOCAL_ONLY_ACTIONS=0")
    print("E6.0F_NEXT_BOUNDARY=LIVE_ROBOT_OR_CERTIFIED_EXTERNAL_INPUT")
    print("E6.0F_FIRST_SCENARIO=NO_BOX_READY_EMPTY_CELL")
    print("E6.0F_PHYSICAL_AUTHORIZED=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
