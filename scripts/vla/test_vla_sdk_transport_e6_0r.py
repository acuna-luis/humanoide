#!/usr/bin/env python3
"""Exhaustive offline audit for the E6.0R SDK transport implementation."""

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


SCRIPT = pathlib.Path(__file__).resolve()
RUNTIME = SCRIPT.parent / "runtime" / "cruzr_s2_vla_sdk_transport.py"
ROS_BACKEND = SCRIPT.parent / "runtime" / "cruzr_s2_vla_ros_sdk_backend.py"


def load(path: pathlib.Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


TRANSPORT = load(RUNTIME, "e6_0r_transport")


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def intent(contract: dict[str, Any], target: list[float], sequence: int = 1) -> dict[str, Any]:
    return {
        "schema": contract["input_intent_schema"],
        "task_id": 0,
        "axis_profile": "P14_A",
        "scenario": "NO_BOX_READY",
        "sequence_id": sequence,
        "source_point_index": 0,
        "joint_names": [
            *contract["commanded_joint_names"],
            *contract["locked_joint_names"],
        ],
        "positions": [*target, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        "physical_execution_authorized": False,
        "physical_transport": None,
        "physical_publisher_count": 0,
    }


def trajectory_metrics(frames: list[dict[str, Any]]) -> dict[str, float]:
    velocity = max(
        abs(command["velocity"])
        for frame in frames
        for command in frame["joint_cmd"]
    )
    acceleration = max(
        abs(command["planned_acceleration"])
        for frame in frames
        for command in frame["joint_cmd"]
    )
    return {"maximum_velocity_rad_s": velocity, "maximum_acceleration_rad_s2": acceleration}


def nominal_case(
    contract: dict[str, Any],
    limits: dict[str, Any],
    target: list[float],
    name: str,
) -> dict[str, Any]:
    ready = list(contract["ready_arm_positions"])
    backend = TRANSPORT.MemoryRobotCommandBackend()
    adapter = TRANSPORT.OnePointSdkTransportAdapter(
        contract=contract, limits=limits, backend=backend, dispatch_enabled=True
    )
    armed = adapter.arm(
        intent(contract, target), measured_arm_positions=ready, state_age_seconds=0.01
    )
    completed = adapter.run_to_completion()
    frames = backend.frames
    metrics = trajectory_metrics(frames) if frames else {
        "maximum_velocity_rad_s": float("inf"),
        "maximum_acceleration_rad_s2": float("inf"),
    }
    names_ok = bool(frames) and all(
        [value["name"] for value in frame["joint_cmd"]]
        == contract["commanded_joint_names"]
        for frame in frames
    )
    source_ok = bool(frames) and all(
        frame["source_point_index"] == 0
        and frame["source_sequence_id"] == 1
        for frame in frames
    )
    position_mode_ok = bool(frames) and all(
        value["control_mode"] == 2
        for frame in frames
        for value in frame["joint_cmd"]
    )
    start_ok = bool(frames) and all(
        abs(value["position"] - expected) <= 1e-12
        for value, expected in zip(frames[0]["joint_cmd"], ready)
    )
    end_ok = bool(frames) and all(
        abs(value["position"] - expected) <= 1e-12
        for value, expected in zip(frames[-1]["joint_cmd"], target)
    )
    velocity_ok = metrics["maximum_velocity_rad_s"] <= max(
        limits["maximum_velocity_rad_s"]
    ) + 1e-12
    acceleration_ok = metrics["maximum_acceleration_rad_s2"] <= max(
        limits["maximum_acceleration_rad_s2"]
    ) + 1e-12
    passed = all((
        armed.accepted,
        completed.accepted,
        adapter.state == "COMPLETED",
        names_ok,
        source_ok,
        position_mode_ok,
        start_ok,
        end_ok,
        velocity_ok,
        acceleration_ok,
        len(frames) == adapter.frames_published,
        len(frames) >= 2,
        backend.stop_count == 0,
    ))
    return {
        "case": name,
        "passed": passed,
        "frame_count": len(frames),
        "state": adapter.state,
        "names_exact": names_ok,
        "source_point_zero_only": source_ok,
        "position_mode_exact": position_mode_ok,
        "start_exact": start_ok,
        "target_exact": end_ok,
        **metrics,
    }


def reject_case(
    name: str,
    contract: dict[str, Any],
    limits: dict[str, Any],
    candidate_intent: Any,
    measured: Any,
    age: Any,
    *,
    enabled: bool = True,
) -> dict[str, Any]:
    backend = TRANSPORT.MemoryRobotCommandBackend()
    adapter = TRANSPORT.OnePointSdkTransportAdapter(
        contract=contract, limits=limits, backend=backend, dispatch_enabled=enabled
    )
    decision = adapter.arm(
        candidate_intent, measured_arm_positions=measured, state_age_seconds=age
    )
    return {
        "case": name,
        "passed": (
            not decision.accepted
            and adapter.state == "FAULTED"
            and not backend.frames
            and backend.stopped
            and backend.stop_count == 1
        ),
        "state": adapter.state,
        "reasons": decision.reasons,
        "frame_count": len(backend.frames),
    }


def source_audit(
    vendor_executor: pathlib.Path,
    joint_cmd_msg: pathlib.Path,
    robot_command_msg: pathlib.Path,
) -> dict[str, Any]:
    vendor = vendor_executor.read_text(encoding="utf-8")
    backend_source = ROS_BACKEND.read_text(encoding="utf-8")
    backend_tree = ast.parse(backend_source)
    attributes = {
        node.attr for node in ast.walk(backend_tree) if isinstance(node, ast.Attribute)
    }
    calls = {
        node.func.attr
        for node in ast.walk(backend_tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    definitions = {
        node.name
        for node in ast.walk(backend_tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    joint_spec = joint_cmd_msg.read_text(encoding="utf-8")
    robot_spec = robot_command_msg.read_text(encoding="utf-8")
    checks = {
        "vendor_sdk_topic": 'DEFAULT_COMMAND_TOPIC = "/mc/sdk/robot_command"' in vendor,
        "vendor_sdk_state": 'DEFAULT_ROBOT_STATE_TOPIC = "/mc/sdk/robot_state"' in vendor,
        "vendor_robot_command": "RobotCommand" in vendor and "JointCmd" in vendor,
        "vendor_position_mode": "JointCmd.MODE_POSITION" in vendor,
        "vendor_locks_head_waist": all(
            name in vendor
            for name in ("head_pitch_joint", "head_yaw_joint", "waist_yaw_joint")
        ),
        "joint_cmd_spec": all(
            literal in joint_spec
            for literal in (
                "int8 MODE_POSITION=2",
                "string name",
                "float64 position",
                "float64 velocity",
                "float64 effort",
            )
        ),
        "robot_command_spec": "JointCmd[] joint_cmd" in robot_spec,
        "ros_backend_publisher": "create_publisher" in calls,
        "ros_backend_publish": "publish" in calls,
        "ros_backend_stop_destroys_publisher": "destroy_publisher" in calls,
        "ros_backend_no_main": "main" not in definitions,
        "ros_backend_no_ros_init": "init" not in attributes and "spin" not in attributes,
        "ros_backend_sdk_topic": '"/mc/sdk/robot_command"' in backend_source,
        "ros_backend_best_effort_depth_5": (
            "ReliabilityPolicy.BEST_EFFORT" in backend_source and "depth=5" in backend_source
        ),
        "ros_backend_no_hold_on_stop": ".publish(" not in backend_source.split("def stop", 1)[1],
    }
    return {"checks": checks, "all_passed": all(checks.values())}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=pathlib.Path, required=True)
    parser.add_argument("--limits", type=pathlib.Path, required=True)
    parser.add_argument("--vendor-executor", type=pathlib.Path, required=True)
    parser.add_argument("--joint-cmd-msg", type=pathlib.Path, required=True)
    parser.add_argument("--robot-command-msg", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()

    contract = TRANSPORT.load_transport_contract(args.contract)
    limits = TRANSPORT.load_engineering_limits(args.limits)
    ready = list(contract["ready_arm_positions"])

    cases: list[dict[str, Any]] = [
        nominal_case(contract, limits, ready, "zero_delta"),
    ]
    for index in range(14):
        for sign, label in ((1.0, "positive"), (-1.0, "negative")):
            target = list(ready)
            target[index] += sign * float(limits["maximum_target_delta_rad"][index])
            cases.append(nominal_case(
                contract, limits, target, f"joint_{index:02d}_{label}_maximum_delta"
            ))

    baseline_intent = intent(contract, ready)
    bad_schema = copy.deepcopy(baseline_intent)
    bad_schema["schema"] = "wrong"
    bad_names = copy.deepcopy(baseline_intent)
    bad_names["joint_names"][0], bad_names["joint_names"][1] = (
        bad_names["joint_names"][1], bad_names["joint_names"][0]
    )
    bad_delta = copy.deepcopy(baseline_intent)
    bad_delta["positions"][0] += 0.100001
    bad_nan = copy.deepcopy(baseline_intent)
    bad_nan["positions"][0] = float("nan")
    bad_source = copy.deepcopy(baseline_intent)
    bad_source["source_point_index"] = 1
    bad_authorization = copy.deepcopy(baseline_intent)
    bad_authorization["physical_execution_authorized"] = True
    not_ready = list(ready)
    not_ready[0] += 0.010001
    cases.extend([
        reject_case("dispatch_disabled", contract, limits, baseline_intent, ready, 0.01, enabled=False),
        reject_case("intent_not_mapping", contract, limits, [], ready, 0.01),
        reject_case("wrong_schema", contract, limits, bad_schema, ready, 0.01),
        reject_case("wrong_joint_order", contract, limits, bad_names, ready, 0.01),
        reject_case("excess_target_delta", contract, limits, bad_delta, ready, 0.01),
        reject_case("nonfinite_target", contract, limits, bad_nan, ready, 0.01),
        reject_case("wrong_source_point", contract, limits, bad_source, ready, 0.01),
        reject_case("unexpected_upstream_authorization", contract, limits, bad_authorization, ready, 0.01),
        reject_case("stale_state", contract, limits, baseline_intent, ready, 0.100001),
        reject_case("future_state_age", contract, limits, baseline_intent, ready, -0.001),
        reject_case("measured_not_ready", contract, limits, baseline_intent, not_ready, 0.01),
    ])

    # STOP before and during dispatch is idempotent, purges, and prevents replay.
    backend = TRANSPORT.MemoryRobotCommandBackend()
    adapter = TRANSPORT.OnePointSdkTransportAdapter(
        contract=contract, limits=limits, backend=backend, dispatch_enabled=True
    )
    first_stop = adapter.stop()
    second_stop = adapter.stop()
    cases.append({
        "case": "stop_before_arm_idempotent",
        "passed": (
            first_stop.accepted and second_stop.accepted and adapter.state == "STOPPED"
            and backend.stop_count == 1 and not backend.frames
        ),
        "state": adapter.state,
        "frame_count": len(backend.frames),
    })

    backend = TRANSPORT.MemoryRobotCommandBackend()
    adapter = TRANSPORT.OnePointSdkTransportAdapter(
        contract=contract, limits=limits, backend=backend, dispatch_enabled=True
    )
    target = list(ready)
    target[0] += 0.05
    adapter.arm(intent(contract, target), measured_arm_positions=ready, state_age_seconds=0.01)
    for _ in range(5):
        adapter.step()
    count_before_stop = len(backend.frames)
    adapter.stop()
    after_stop = adapter.step()
    adapter.stop()
    cases.append({
        "case": "stop_during_dispatch_purges_no_replay",
        "passed": (
            adapter.state == "STOPPED" and backend.stop_count == 1
            and len(backend.frames) == count_before_stop == 5
            and not after_stop.accepted
        ),
        "state": adapter.state,
        "frame_count": len(backend.frames),
    })

    backend = TRANSPORT.MemoryRobotCommandBackend(fail_after=3)
    adapter = TRANSPORT.OnePointSdkTransportAdapter(
        contract=contract, limits=limits, backend=backend, dispatch_enabled=True
    )
    adapter.arm(intent(contract, target), measured_arm_positions=ready, state_age_seconds=0.01)
    failed = adapter.run_to_completion()
    cases.append({
        "case": "publish_failure_latches_stop",
        "passed": (
            not failed.accepted and adapter.state == "FAULTED"
            and len(backend.frames) == 3 and backend.stop_count == 1
        ),
        "state": adapter.state,
        "frame_count": len(backend.frames),
    })

    tamper_cases = []
    for name, source, key, value in (
        ("contract_topic", "contract", "command_topic", "/wrong"),
        ("contract_launcher", "contract", "active_launcher_implemented", True),
        ("contract_authorized", "contract", "physical_execution_authorized", True),
        ("contract_stop", "contract", "software_stop_semantics", "hold"),
        ("limits_certified", "limits", "manufacturer_certified", True),
        ("limits_owner_accepted", "limits", "owner_accepted", True),
        ("limits_authorized", "limits", "physical_execution_authorized", True),
        ("limits_duration", "limits", "maximum_transition_duration_seconds", 0.1),
    ):
        candidate = copy.deepcopy(contract if source == "contract" else limits)
        candidate[key] = value
        temp = args.contract.parent / f".e6_0r_{name}.json"
        temp.write_text(json.dumps(candidate), encoding="utf-8")
        rejected = False
        try:
            if source == "contract":
                TRANSPORT.load_transport_contract(temp)
            else:
                TRANSPORT.load_engineering_limits(temp)
        except ValueError:
            rejected = True
        finally:
            temp.unlink(missing_ok=True)
        tamper_cases.append({"case": name, "rejected": rejected, "passed": rejected})

    source = source_audit(args.vendor_executor, args.joint_cmd_msg, args.robot_command_msg)
    failed_cases = [case for case in cases if not case["passed"]]
    failed_cases.extend(case for case in tamper_cases if not case["passed"])
    if not source["all_passed"]:
        failed_cases.append({"case": "source_audit"})
    report = {
        "schema": "cruzr-s2-vla-sdk-transport-audit-e6.0r-v1",
        "experiment_id": "E6.0R",
        "status": "PASS_SDK_TRANSPORT_IMPLEMENTED_OFFLINE_ACTIVE_LAUNCHER_BLOCKED",
        "mode": "local_memory_transport_no_robot_no_network_no_ros_no_publisher",
        "case_count": len(cases),
        "tamper_case_count": len(tamper_cases),
        "failed_expectation_count": len(failed_cases),
        "all_expectations_passed": not failed_cases,
        "source_audit": source,
        "source_sha256": {
            "transport": sha256(RUNTIME),
            "ros_backend": sha256(ROS_BACKEND),
            "contract": sha256(args.contract),
            "limits": sha256(args.limits),
            "vendor_executor": sha256(args.vendor_executor),
            "joint_cmd_msg": sha256(args.joint_cmd_msg),
            "robot_command_msg": sha256(args.robot_command_msg),
        },
        "command_topic": contract["command_topic"],
        "command_message_type": contract["command_message_type"],
        "state_topic": contract["state_topic"],
        "state_message_type": contract["state_message_type"],
        "commanded_axis_count": 14,
        "locked_axis_count": 6,
        "maximum_source_point_count": 1,
        "transport_interpolation_frames_are_not_extra_vla_source_points": True,
        "software_stop_implemented": True,
        "software_stop_is_hardware_estop": False,
        "ros_backend_code_present": True,
        "active_launcher_implemented": False,
        "engineering_limits_present": True,
        "engineering_limits_manufacturer_certified": False,
        "engineering_limits_owner_accepted": False,
        "physical_execution_authorized": False,
        "physical_publisher_count": 0,
        "robot_state_read": False,
        "network_calls": 0,
        "physical_movement_commanded": False,
        "cases": cases,
        "tamper_cases": tamper_cases,
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"E6.0R_CASES={len(cases)}")
    print(f"E6.0R_TAMPER_CASES={len(tamper_cases)}")
    print(f"E6.0R_FAILED_EXPECTATIONS={len(failed_cases)}")
    print("E6.0R_COMMAND_TOPIC=/mc/sdk/robot_command")
    print("E6.0R_SOFTWARE_STOP_IMPLEMENTED=1")
    print("E6.0R_ACTIVE_LAUNCHER_IMPLEMENTED=0")
    print("E6.0R_PHYSICAL_AUTHORIZED=0")
    return 0 if not failed_cases else 1


if __name__ == "__main__":
    raise SystemExit(main())
