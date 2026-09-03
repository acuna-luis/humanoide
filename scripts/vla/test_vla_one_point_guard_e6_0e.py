#!/usr/bin/env python3
"""Run E6.0E fault injection against the no-publisher one-point guard."""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import importlib.util
import json
import pathlib
import sys
from typing import Any, Callable


SCRIPT_PATH = pathlib.Path(__file__).resolve()
MODULE_PATH = SCRIPT_PATH.parent / "runtime" / "vla_one_point_guard.py"
RUNTIME_ID = "cruzr-s2-vla-one-point-guard-e6.0e-v1"
CHECKPOINT_ID = "checkpoint-40000-read-only-contract"
NOW = 6000.0


def load_module():
    spec = importlib.util.spec_from_file_location("vla_one_point_guard", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = load_module()


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def static_safety() -> dict[str, Any]:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports: set[str] = set()
    attributes: set[str] = set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
        elif isinstance(node, ast.Attribute):
            attributes.add(node.attr)
        elif isinstance(node, ast.Name):
            names.add(node.id)
    forbidden_imports = {
        "action_msgs", "mc_command_msgs", "rclpy", "requests", "rosa", "socket",
        "subprocess", "urllib", "vla_msgs",
    }
    forbidden_calls = {"create_client", "create_publisher", "publish", "send_goal_async"}
    forbidden_names = {"RobotCommand", "Gr00tMotionChunk"}
    return {
        "forbidden_imports": sorted(imports & forbidden_imports),
        "publisher_calls": sorted(attributes & forbidden_calls),
        "physical_symbols": sorted(names & forbidden_names),
        "physical_topic_literal": "/mc/sdk/robot_command" in source,
        "safe": not (
            imports & forbidden_imports
            or attributes & forbidden_calls
            or names & forbidden_names
            or "/mc/sdk/robot_command" in source
        ),
    }


def new_guard(contract, profile, ready):
    return MODULE.OnePointGuard(
        contract=contract,
        profile=profile,
        ready_arm_state=ready,
        runtime_id=RUNTIME_ID,
        checkpoint_id=CHECKPOINT_ID,
    )


def decision_case(name: str, expected: bool, decision) -> dict[str, Any]:
    physical = bool(decision.physical_execution_authorized)
    preview = decision.preview
    publisher_count = 0 if preview is None else int(preview["physical_publisher_count"])
    return {
        "case": name,
        "expected_preview_accept": expected,
        "observed_preview_accept": bool(decision.preview_accepted),
        "physical_execution_authorized": physical,
        "physical_publisher_count": publisher_count,
        "reasons": list(decision.reasons),
        "passed": (
            bool(decision.preview_accepted) is expected
            and not physical
            and publisher_count == 0
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--guard-contract", type=pathlib.Path, required=True)
    parser.add_argument("--profile", type=pathlib.Path, required=True)
    parser.add_argument("--ready-contract", type=pathlib.Path, required=True)
    parser.add_argument("--temporal-contract", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()

    contract = MODULE.load_guard_contract(args.guard_contract)
    profile = MODULE.load_profile(args.profile)
    ready_contract = json.loads(args.ready_contract.read_text(encoding="utf-8"))
    ready = ready_contract["arm_path_checkpoint_order"]["ready_b"]
    temporal = json.loads(args.temporal_contract.read_text(encoding="utf-8"))
    if temporal.get("physical_executor_authorized") is not False:
        raise SystemExit("ERROR: temporal contract unexpectedly authorizes physical execution")

    rows: list[dict[str, Any]] = []

    guard = new_guard(contract, profile, ready)
    valid = MODULE.nominal_message(guard, now=NOW)
    rows.append(decision_case("valid_zero_delta_preview", True, guard.evaluate(valid, now=NOW)))
    rows.append(decision_case("second_point_latched", False, guard.evaluate(valid, now=NOW)))

    boundary_guard = new_guard(contract, profile, ready)
    boundary = MODULE.nominal_message(boundary_guard, now=NOW)
    boundary["points"][0]["positions"][2] += 0.1
    rows.append(
        decision_case(
            "valid_delta_boundary_preview", True,
            boundary_guard.evaluate(boundary, now=NOW),
        )
    )

    mutations: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
        ("physical_execution_requested", lambda value: value.__setitem__("physical_execution_requested", True)),
        ("schema_mismatch", lambda value: value.__setitem__("schema", "wrong")),
        ("mode_mismatch", lambda value: value.__setitem__("mode", "physical")),
        ("runtime_mismatch", lambda value: value.__setitem__("runtime_id", "wrong")),
        ("checkpoint_mismatch", lambda value: value.__setitem__("checkpoint_id", "wrong")),
        ("task_mismatch", lambda value: value.__setitem__("task_id", 1)),
        ("profile_mismatch", lambda value: value.__setitem__("axis_profile", "P20_AHLW")),
        ("scenario_mismatch", lambda value: value.__setitem__("scenario", "SUPPORTED_LOW")),
        ("client_empty", lambda value: value.__setitem__("client_id", "")),
        ("sequence_invalid", lambda value: value.__setitem__("sequence_id", -1)),
        ("joint_order", lambda value: value["joint_names"].__setitem__(slice(0, 2), reversed(value["joint_names"][:2]))),
        ("state_dimension", lambda value: value["state_positions"].pop()),
        ("state_nan", lambda value: value["state_positions"].__setitem__(0, float("nan"))),
        ("state_not_ready", lambda value: value["state_positions"].__setitem__(0, value["state_positions"][0] + 1e-6)),
        ("points_empty", lambda value: value.__setitem__("points", [])),
        ("points_two", lambda value: value["points"].append(copy.deepcopy(value["points"][0]))),
        ("point_not_mapping", lambda value: value.__setitem__("points", [0])),
        ("point_dimension", lambda value: value["points"][0]["positions"].pop()),
        ("point_inf", lambda value: value["points"][0]["positions"].__setitem__(0, float("inf"))),
        ("point_time_nonzero", lambda value: value["points"][0].__setitem__("time_from_start", 0.08)),
        ("arm_delta_exceeded", lambda value: value["points"][0]["positions"].__setitem__(2, value["state_positions"][2] + 0.100001)),
        ("locked_head_changed", lambda value: value["points"][0]["positions"].__setitem__(14, value["state_positions"][14] + 1e-6)),
        ("locked_lifter_changed", lambda value: value["points"][0]["positions"].__setitem__(17, value["state_positions"][17] + 1e-6)),
        ("locked_waist_changed", lambda value: value["points"][0]["positions"].__setitem__(19, value["state_positions"][19] + 1e-6)),
        ("state_range", lambda value: value["state_positions"].__setitem__(14, profile["upper_boundary"][14] + profile["range_tolerance"] + 0.01)),
        ("point_range", lambda value: value["points"][0]["positions"].__setitem__(2, profile["upper_boundary"][2] + profile["range_tolerance"] + 0.01)),
        ("sent_stale", lambda value: value.__setitem__("sent_monotonic", NOW - 0.51)),
        ("state_stale", lambda value: value.__setitem__("state_monotonic", NOW - 1.01)),
        ("image_stale", lambda value: value.__setitem__("image_monotonic", NOW - 1.01)),
        ("sent_future", lambda value: value.__setitem__("sent_monotonic", NOW + 0.051)),
        ("state_future", lambda value: value.__setitem__("state_monotonic", NOW + 0.051)),
        ("image_future", lambda value: value.__setitem__("image_monotonic", NOW + 0.051)),
    ]
    for name, mutation in mutations:
        guard = new_guard(contract, profile, ready)
        message = MODULE.nominal_message(guard, now=NOW)
        mutation(message)
        rows.append(decision_case(name, False, guard.evaluate(message, now=NOW)))

    contract_cases = []
    for name, key, value in (
        ("contract_physical_enabled", "physical_execution_enabled", True),
        ("contract_topic_present", "publisher_or_command_topic", "/forbidden"),
        ("contract_acceleration_claimed", "maximum_acceleration_rad_s2", [1.0] * 14),
        ("contract_clearance_claimed", "required_physical_clearance_m", 0.01),
        ("contract_continuous_claimed", "continuous_path_certified", True),
        ("contract_clamp_claimed", "installed_passive_clamp_geometry_present", True),
        ("contract_blockers_removed", "hard_fail_conditions", []),
    ):
        candidate = copy.deepcopy(contract)
        candidate[key] = value
        rejected = False
        try:
            MODULE.validate_guard_contract(candidate)
        except ValueError:
            rejected = True
        contract_cases.append({"case": name, "rejected": rejected, "passed": rejected})

    safety = static_safety()
    failed = [row for row in rows if not row["passed"]]
    failed.extend(row for row in contract_cases if not row["passed"])
    summary = {
        "schema": "cruzr-s2-vla-one-point-guard-campaign-e6.0e-v1",
        "experiment_id": "E6.0E",
        "mode": "local_in_memory_preview_no_robot_no_network_no_ros_no_publisher",
        "source_sha256": {
            "module": sha256(MODULE_PATH),
            "guard_contract": sha256(args.guard_contract),
            "profile": sha256(args.profile),
            "ready_contract": sha256(args.ready_contract),
            "temporal_contract": sha256(args.temporal_contract),
        },
        "message_case_count": len(rows),
        "message_expectation_failures": len([row for row in rows if not row["passed"]]),
        "contract_tamper_case_count": len(contract_cases),
        "contract_tamper_rejected_count": sum(row["rejected"] for row in contract_cases),
        "failed_expectation_count": len(failed),
        "all_expectations_passed": not failed,
        "valid_preview_count": sum(row["observed_preview_accept"] for row in rows),
        "physical_authorization_count": sum(row["physical_execution_authorized"] for row in rows),
        "physical_publisher_count": sum(row["physical_publisher_count"] for row in rows),
        "static_safety": safety,
        "physical_blockers": new_guard(contract, profile, ready).physical_blockers,
        "physical_execution_authorized": False,
        "robot_state_read": False,
        "network_calls": 0,
        "physical_movement_commanded": False,
        "cases": rows,
        "contract_tamper_cases": contract_cases,
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"E6.0E_MESSAGE_CASES={len(rows)}")
    print(f"E6.0E_CONTRACT_TAMPER_CASES={len(contract_cases)}")
    print(f"E6.0E_FAILED_EXPECTATIONS={len(failed)}")
    print(f"E6.0E_VALID_PREVIEWS={summary['valid_preview_count']}")
    print("E6.0E_PHYSICAL_AUTHORIZATIONS=0")
    print("E6.0E_PHYSICAL_PUBLISHERS=0")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
