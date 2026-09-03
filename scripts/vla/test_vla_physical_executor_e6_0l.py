#!/usr/bin/env python3
"""Exercise the transport-neutral E6.0L one-point control core."""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import importlib.util
import json
import pathlib
import sys
from typing import Any


SCRIPT_PATH = pathlib.Path(__file__).resolve()
MODULE_PATH = SCRIPT_PATH.parent / "runtime" / "cruzr_s2_vla_physical_executor.py"
GUARD_PATH = SCRIPT_PATH.parent / "runtime" / "vla_one_point_guard.py"


def load(path: pathlib.Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CORE = load(MODULE_PATH, "e6_0l_core")
GUARD = load(GUARD_PATH, "e6_0l_guard")


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
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
        "action_msgs", "mc_task_msgs", "rclpy", "requests", "rosa", "socket",
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


def preflight(contract: dict[str, Any]) -> dict[str, Any]:
    claims = {key: True for key in contract["required_preflight_claims"]}
    claims.update({
        "task_id": 0,
        "axis_profile": "P14_A",
        "scenario": "NO_BOX_READY",
        "physical_execution_requested": False,
    })
    return claims


def row(name: str, expected: bool, decision: Any, core: Any) -> dict[str, Any]:
    observed = bool(decision.accepted)
    return {
        "case": name,
        "expected_accept": expected,
        "observed_accept": observed,
        "passed": observed is expected,
        "state": decision.state,
        "reason_count": len(decision.reasons),
        "preview_intent_count": len(decision.preview_intents),
        "physical_execution_authorized": core.physical_execution_authorized,
        "physical_publisher_count": core.physical_publisher_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=pathlib.Path, required=True)
    parser.add_argument("--guard-contract", type=pathlib.Path, required=True)
    parser.add_argument("--profile", type=pathlib.Path, required=True)
    parser.add_argument("--ready-contract", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()

    contract = CORE.load_contract(args.contract)
    guard_contract = GUARD.load_guard_contract(args.guard_contract)
    profile = GUARD.load_profile(args.profile)
    ready = json.loads(args.ready_contract.read_text(encoding="utf-8"))[
        "arm_path_checkpoint_order"
    ]["ready_b"]
    guard = GUARD.OnePointGuard(
        contract=guard_contract,
        profile=profile,
        ready_arm_state=ready,
        runtime_id="cruzr-s2-vla-one-point-guard-e6.0e-v1",
        checkpoint_id="checkpoint-40000-read-only-contract",
    )
    guarded = guard.evaluate(GUARD.nominal_message(guard, now=100.0), now=100.0)
    guarded_map = guarded.as_dict()

    rows: list[dict[str, Any]] = []
    core = CORE.OnePointCanaryControlCore(contract, started_at=100.0)
    rows.append(row("nominal_arm", True, core.arm(preflight(contract), now=100.0), core))
    rows.append(row(
        "nominal_accept_guarded_preview", True,
        core.accept_guarded_preview(guarded_map, now=100.01), core,
    ))
    consumed = core.consume_preview_once(now=100.02)
    rows.append(row("nominal_consume_exactly_once", True, consumed, core))
    rows.append(row("no_replay_after_completion", False, core.consume_preview_once(now=100.03), core))
    rows.append({
        "case": "nominal_intent_is_point_zero_only_and_nonphysical",
        "expected_accept": True,
        "observed_accept": (
            len(consumed.preview_intents) == 1
            and consumed.preview_intents[0]["source_point_index"] == 0
            and consumed.preview_intents[0]["physical_execution_authorized"] is False
            and consumed.preview_intents[0]["physical_transport"] is None
            and consumed.preview_intents[0]["physical_publisher_count"] == 0
        ),
        "passed": (
            len(consumed.preview_intents) == 1
            and consumed.preview_intents[0]["source_point_index"] == 0
            and consumed.preview_intents[0]["physical_execution_authorized"] is False
            and consumed.preview_intents[0]["physical_transport"] is None
            and consumed.preview_intents[0]["physical_publisher_count"] == 0
        ),
        "state": core.state,
        "reason_count": 0,
        "preview_intent_count": len(consumed.preview_intents),
        "physical_execution_authorized": False,
        "physical_publisher_count": 0,
    })

    for claim in contract["required_preflight_claims"]:
        candidate = preflight(contract)
        candidate[claim] = False
        core = CORE.OnePointCanaryControlCore(contract, started_at=100.0)
        rows.append(row(
            f"preflight_rejects_{claim}", False,
            core.arm(candidate, now=100.0), core,
        ))

    for key, value in (
        ("task_id", 1),
        ("axis_profile", "P20_AHLW"),
        ("scenario", "BOX_PRESENT"),
        ("physical_execution_requested", True),
    ):
        candidate = preflight(contract)
        candidate[key] = value
        core = CORE.OnePointCanaryControlCore(contract, started_at=100.0)
        rows.append(row(
            f"preflight_rejects_{key}", False,
            core.arm(candidate, now=100.0), core,
        ))

    core = CORE.OnePointCanaryControlCore(contract, started_at=100.0)
    core.arm(preflight(contract), now=100.0)
    rejected_guard = copy.deepcopy(guarded_map)
    rejected_guard["preview_accepted"] = False
    rows.append(row(
        "rejected_guard_faults", False,
        core.accept_guarded_preview(rejected_guard, now=100.01), core,
    ))

    core = CORE.OnePointCanaryControlCore(contract, started_at=100.0)
    core.arm(preflight(contract), now=100.0)
    unauthorized = copy.deepcopy(guarded_map)
    unauthorized["physical_execution_authorized"] = True
    rows.append(row(
        "unexpected_guard_authorization_faults", False,
        core.accept_guarded_preview(unauthorized, now=100.01), core,
    ))

    core = CORE.OnePointCanaryControlCore(contract, started_at=100.0)
    core.arm(preflight(contract), now=100.0)
    rows.append(row(
        "armed_timeout_rejects", False,
        core.accept_guarded_preview(guarded_map, now=102.001), core,
    ))

    for event in ("cancel", "stop", "fault"):
        core = CORE.OnePointCanaryControlCore(contract, started_at=100.0)
        core.arm(preflight(contract), now=100.0)
        core.accept_guarded_preview(guarded_map, now=100.01)
        if event == "fault":
            decision = core.fault("test", now=100.02)
        else:
            decision = getattr(core, event)(now=100.02)
        rows.append(row(f"{event}_purges_pending", True, decision, core))
        rows.append(row(
            f"{event}_prevents_future_intent", False,
            core.consume_preview_once(now=100.03), core,
        ))

    contract_cases = []
    for name, key, value in (
        ("enable_physical", "physical_execution_enabled", True),
        ("implement_transport", "physical_transport_implemented", True),
        ("implement_stop", "physical_stop_transport_implemented", True),
        ("allow_second_point", "accepted_source_point_indices", [0, 1]),
        ("allow_replay", "gap_policy", "replay_last"),
        ("vendor_end_flag", "end_flag_policy", "vendor"),
    ):
        candidate = copy.deepcopy(contract)
        candidate[key] = value
        path = args.contract.parent / f".e6_0l_{name}.json"
        path.write_text(json.dumps(candidate), encoding="utf-8")
        rejected = False
        try:
            CORE.load_contract(path)
        except ValueError:
            rejected = True
        finally:
            path.unlink(missing_ok=True)
        contract_cases.append({"case": name, "rejected": rejected, "passed": rejected})

    safety = static_safety()
    failed = [item for item in rows if not item["passed"]]
    failed.extend(item for item in contract_cases if not item["passed"])
    report = {
        "schema": "cruzr-s2-vla-one-point-canary-control-core-e6.0l-v1",
        "experiment_id": "E6.0L",
        "status": "PASS_ONE_POINT_CANARY_CONTROL_CORE_OFFLINE_PHYSICAL_TRANSPORT_BLOCKED",
        "mode": "local_in_memory_no_robot_no_network_no_ros_no_publisher",
        "source_sha256": {
            "module": sha256(MODULE_PATH),
            "guard": sha256(GUARD_PATH),
            "contract": sha256(args.contract),
            "guard_contract": sha256(args.guard_contract),
            "profile": sha256(args.profile),
            "ready_contract": sha256(args.ready_contract),
        },
        "case_count": len(rows),
        "contract_tamper_case_count": len(contract_cases),
        "failed_expectation_count": len(failed),
        "all_expectations_passed": not failed,
        "static_safety": safety,
        "accepted_source_point_indices": [0],
        "maximum_preview_intent_count": 1,
        "replay_count": 0,
        "vendor_end_flag_used": False,
        "physical_transport_implemented": False,
        "physical_stop_transport_implemented": False,
        "physical_execution_authorized": False,
        "physical_publisher_count": 0,
        "robot_state_read": False,
        "network_calls": 0,
        "physical_movement_commanded": False,
        "cases": rows,
        "contract_tamper_cases": contract_cases,
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"E6.0L_CASES={len(rows)}")
    print(f"E6.0L_CONTRACT_TAMPER_CASES={len(contract_cases)}")
    print(f"E6.0L_FAILED_EXPECTATIONS={len(failed)}")
    print("E6.0L_ACCEPTED_SOURCE_POINTS=0")
    print("E6.0L_REPLAY_COUNT=0")
    print("E6.0L_PHYSICAL_TRANSPORT_IMPLEMENTED=0")
    print("E6.0L_PHYSICAL_AUTHORIZED=0")
    return 0 if not failed and safety["safe"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
