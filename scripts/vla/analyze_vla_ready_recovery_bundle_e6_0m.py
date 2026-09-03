#!/usr/bin/env python3
"""Validate the local E6.0 deterministic ready/recovery bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import xml.etree.ElementTree as ET
from typing import Any

import yaml


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_yaml(path: pathlib.Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(path)
    return value


def floats(text: str) -> list[float]:
    return [float(value.strip()) for value in text.split(";") if value.strip()]


def same(left: list[float], right: list[float], tolerance: float = 1e-12) -> bool:
    return len(left) == len(right) and all(
        abs(a - b) <= tolerance for a, b in zip(left, right)
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vendor-ready", type=pathlib.Path, required=True)
    parser.add_argument("--forward-yaml", type=pathlib.Path, required=True)
    parser.add_argument("--recovery-xml", type=pathlib.Path, required=True)
    parser.add_argument("--recovery-yaml", type=pathlib.Path, required=True)
    parser.add_argument("--ready-contract", type=pathlib.Path, required=True)
    parser.add_argument("--home-entry-report", type=pathlib.Path, required=True)
    parser.add_argument("--clamp-proxy-report", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()

    sources = (
        args.vendor_ready, args.forward_yaml, args.recovery_xml,
        args.recovery_yaml, args.ready_contract, args.home_entry_report,
        args.clamp_proxy_report,
    )
    for path in sources:
        if not path.is_file():
            raise SystemExit(f"ERROR: falta {path}")

    vendor_root = ET.parse(args.vendor_ready).getroot()
    recovery_root = ET.parse(args.recovery_xml).getroot()
    forward = load_yaml(args.forward_yaml)["request"]
    recovery = load_yaml(args.recovery_yaml)["request"]
    ready_contract = json.loads(args.ready_contract.read_text(encoding="utf-8"))
    home_entry = json.loads(args.home_entry_report.read_text(encoding="utf-8"))
    clamp_proxy = json.loads(args.clamp_proxy_report.read_text(encoding="utf-8"))

    vendor_direct = {
        (action.attrib["type"], action.attrib["location"]): floats(
            action.attrib["joint_angles"]
        )
        for action in vendor_root.findall(".//Action[@ID='MetaMove'][@type]")
    }
    expected_vendor_keys = {
        ("waist", "single"), ("head", "single"),
        ("arm", "left"), ("arm", "right"),
    }
    if set(vendor_direct) != expected_vendor_keys:
        raise SystemExit(f"ERROR: acciones vendor inesperadas: {set(vendor_direct)}")
    vendor_named = [
        action.attrib.get("name")
        for action in vendor_root.findall(".//Action[@ID='MetaMove'][@name]")
    ]
    if vendor_named != ["clamp_s2_joints_trajectory"]:
        raise SystemExit(f"ERROR: named action vendor inesperada: {vendor_named}")

    forward_goals = [[float(value) for value in goal] for goal in forward["goals"]]
    forward_durations = [float(value) for value in forward["durations"]]
    recovery_goals = [[float(value) for value in goal] for goal in recovery["goals"]]
    recovery_durations = [float(value) for value in recovery["durations"]]
    staging_raw = vendor_direct[("arm", "left")] + vendor_direct[("arm", "right")]
    if len(forward_goals) != 2 or any(len(goal) != 14 for goal in forward_goals):
        raise SystemExit("ERROR: forward no es 2x14")
    exact_named_reverse = (
        len(recovery_goals) == 2
        and same(recovery_goals[0], forward_goals[0])
        and same(recovery_goals[1], staging_raw)
        and recovery_durations == list(reversed(forward_durations))
    )
    if not exact_named_reverse:
        raise SystemExit("ERROR: la recuperación named no es B->A->staging exacta")

    recovery_named = [
        action.attrib.get("name")
        for action in recovery_root.findall(".//Action[@ID='MetaMove'][@name]")
    ]
    if recovery_named != ["clamp_s2_vla_e6_0_exact_recovery"]:
        raise SystemExit(f"ERROR: named action recovery inesperada: {recovery_named}")
    recovery_direct = {
        (action.attrib["type"], action.attrib["location"]): floats(
            action.attrib["joint_angles"]
        )
        for action in recovery_root.findall(".//Action[@ID='MetaMove'][@type]")
    }
    if set(recovery_direct) != expected_vendor_keys:
        raise SystemExit("ERROR: retorno final no cubre waist/head/ambos brazos")
    expected_lengths = {
        ("waist", "single"): 2,
        ("head", "single"): 2,
        ("arm", "left"): 7,
        ("arm", "right"): 7,
    }
    for key, length in expected_lengths.items():
        values = recovery_direct[key]
        if len(values) != length or any(abs(value) > 1e-12 for value in values):
            raise SystemExit(f"ERROR: retorno numérico a home inválido: {key}={values}")

    ready_path = ready_contract["arm_path_checkpoint_order"]
    if len(ready_path["ready_b"]) != 14 or len(ready_path["waypoint_a"]) != 14:
        raise SystemExit("ERROR: contrato ready no es P14")
    if home_entry.get("complete_vendor_model_path_covered") is not True:
        raise SystemExit("ERROR: E6.0I no cubre home<->staging")
    if clamp_proxy.get("collision_audit", {}).get("exact_intersection_count") != 0:
        raise SystemExit("ERROR: E6.0J contiene intersecciones")

    report = {
        "schema": "cruzr-s2-vla-ready-recovery-bundle-e6.0m-v1",
        "experiment_id": "E6.0M",
        "status": "PASS_EXACT_RECOVERY_BUNDLE_LOCAL_ACTIVE_MODES_BLOCKED_PENDING_PHYSICAL_VALIDATION",
        "mode": "local_artifact_validation_no_robot_no_network_no_ros_no_publisher",
        "source_sha256": {str(path.resolve()): sha256(path) for path in sources},
        "forward": {
            "sequence": ["numeric_home", "vendor_staging", "waypoint_a", "ready_b"],
            "vendor_named_action": vendor_named[0],
            "named_durations_seconds": forward_durations,
        },
        "recovery": {
            "sequence": ["ready_b", "waypoint_a", "vendor_staging", "numeric_home"],
            "named_action": recovery_named[0],
            "named_durations_seconds": recovery_durations,
            "named_segment_is_exact_reverse": exact_named_reverse,
            "final_parallel_returns_head_waist_and_both_arms_to_numeric_home": True,
        },
        "sampled_vendor_model_and_document_proxy_path_covered": True,
        "active_modes_implemented": False,
        "installed_on_robot": False,
        "physically_validated": False,
        "physical_execution_authorized": False,
        "physical_publisher_count": 0,
        "robot_state_read": False,
        "network_calls": 0,
        "physical_movement_commanded": False,
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("E6.0M_EXACT_NAMED_REVERSE=1")
    print("E6.0M_FULL_SEQUENCE=home->staging->A->B->A->staging->home")
    print("E6.0M_ACTIVE_MODES_IMPLEMENTED=0")
    print("E6.0M_PHYSICAL_AUTHORIZED=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
