#!/usr/bin/env python3
"""Offline integration tests for the disabled-by-default E6.0W runtime."""

from __future__ import annotations

import argparse
import ast
import copy
import importlib.util
import json
import pathlib
import sys
from typing import Any, Callable


def load(path: pathlib.Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def enabled(template: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(template)
    value.update({
        "owner_accepted_engineering_limits": True,
        "active_launcher_enabled": True,
        "physical_execution_authorized": True,
        "authorization_scope": "E6.0_NO_BOX_ONE_POINT_ONLY",
        "authorization_run_id": "OFFLINE-TEST-ONLY",
        "authorization_issued_at": "2026-09-04T00:00:00+00:00",
        "authorization_expires_at": "2026-09-04T00:02:00+00:00",
        "authorization_valid_seconds": 120,
        "authorization_preflight_sha256": "a" * 64,
        "authorization_ready_sha256": "b" * 64,
        "authorization_acceptance_sha256": "c" * 64,
        "authorization_limits_sha256": "d" * 64,
        "not_authorized_reason": None,
    })
    return value


def state_sample(contract: dict[str, Any], profile: dict[str, Any], timestamp: float) -> dict[str, Any]:
    locked = [
        (float(low) + float(high)) / 2.0
        for low, high in zip(profile["lower_boundary"][14:], profile["upper_boundary"][14:])
    ]
    return {
        "schema": "cruzr-s2-vla-normalized-joint-state-e6.0u-v1",
        "source_topic": "/mc/whole_joint_states",
        "sample_time_seconds": timestamp,
        "received_time_seconds": timestamp,
        "joint_names": list(profile["joint_names"]),
        "positions": [*contract["ready_arm_positions"], *locked],
        "velocities": [0.0] * 20,
    }


def chunk(profile: dict[str, Any], state: dict[str, Any], timestamp: float) -> dict[str, Any]:
    first = list(state["positions"])
    first[0] += 0.05
    return {
        "schema": "cruzr-s2-vla-normalized-checkpoint-chunk-e6.0w-v1",
        "source_topic": "/vla_inference_result",
        "chunk_id": 1,
        "status_code": 1,
        "inference_time_seconds": 10.0,
        "received_time_seconds": timestamp,
        "points": [
            {"positions": list(first), "time_from_start_seconds": index * 0.08}
            for index in range(10)
        ],
    }


class BackendFactory:
    def __init__(self, transport: Any, *, fail_after: int | None = None, fail_create: bool = False) -> None:
        self.transport = transport
        self.fail_after = fail_after
        self.fail_create = fail_create
        self.count = 0
        self.backend: Any | None = None

    def __call__(self):
        self.count += 1
        if self.fail_create:
            raise RuntimeError("injected_create_failure")
        self.backend = self.transport.MemoryRobotCommandBackend(fail_after=self.fail_after)
        return self.backend


def make_runtime(
    runtime_module: Any,
    monitor_module: Any,
    transport_module: Any,
    activation: dict[str, Any],
    monitor_contract: dict[str, Any],
    transport_contract: dict[str, Any],
    limits: dict[str, Any],
    profile: dict[str, Any],
    factory: BackendFactory,
):
    return runtime_module.OnePointCanaryRuntime(
        activation=activation,
        monitor_contract=monitor_contract,
        transport_contract=transport_contract,
        limits=limits,
        profile=profile,
        monitor_type=monitor_module,
        transport_type=transport_module,
        backend_factory=factory,
    )


def prepared(
    modules: tuple[Any, Any, Any],
    values: tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]],
    *,
    fail_after: int | None = None,
    fail_create: bool = False,
):
    runtime_module, monitor_module, transport_module = modules
    activation, monitor_contract, transport_contract, limits, profile = values
    factory = BackendFactory(transport_module, fail_after=fail_after, fail_create=fail_create)
    runtime = make_runtime(
        runtime_module, monitor_module, transport_module, activation,
        monitor_contract, transport_contract, limits, profile, factory,
    )
    state = state_sample(transport_contract, profile, 100.0)
    state_decision = runtime.receive_state(state, now_seconds=100.0)
    return runtime, factory, state, state_decision


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", type=pathlib.Path, required=True)
    parser.add_argument("--monitor", type=pathlib.Path, required=True)
    parser.add_argument("--transport", type=pathlib.Path, required=True)
    parser.add_argument("--activation", type=pathlib.Path, required=True)
    parser.add_argument("--monitor-contract", type=pathlib.Path, required=True)
    parser.add_argument("--transport-contract", type=pathlib.Path, required=True)
    parser.add_argument("--limits", type=pathlib.Path, required=True)
    parser.add_argument("--profile", type=pathlib.Path, required=True)
    parser.add_argument("--ros-process", type=pathlib.Path, required=True)
    parser.add_argument("--ros-backend", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()

    runtime_module = load(args.runtime, "e6_0w_runtime")
    monitor_module = load(args.monitor, "e6_0w_monitor")
    transport_module = load(args.transport, "e6_0w_transport")
    template = json.loads(args.activation.read_text(encoding="utf-8"))
    monitor_contract = monitor_module.load_monitor_contract(args.monitor_contract)
    transport_contract = transport_module.load_transport_contract(args.transport_contract)
    limits = transport_module.load_engineering_limits(args.limits)
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    activation = enabled(template)
    modules = (runtime_module, monitor_module, transport_module)
    values = (activation, monitor_contract, transport_contract, limits, profile)
    cases: list[dict[str, Any]] = []

    # The repository template must refuse before constructing a backend.
    factory = BackendFactory(transport_module)
    rejected = False
    try:
        make_runtime(
            runtime_module, monitor_module, transport_module, template,
            monitor_contract, transport_contract, limits, profile, factory,
        )
    except PermissionError:
        rejected = True
    cases.append({
        "case": "repository_activation_template_refuses",
        "passed": rejected and factory.count == 0,
        "backend_factory_count": factory.count,
    })

    # Full in-memory lifecycle with measured samples following every frame.
    runtime, factory, initial, state_decision = prepared(modules, values)
    chunk_decision = runtime.receive_chunk(chunk(profile, initial, 100.01), now_seconds=100.01)
    tick_decisions = []
    timestamp = 100.01
    while runtime.state == "DISPATCHING_ONE_POINT":
        timestamp += 0.01
        tick_decision = runtime.tick(now_seconds=timestamp)
        tick_decisions.append(tick_decision)
        if runtime.state != "DISPATCHING_ONE_POINT":
            break
        assert factory.backend is not None and factory.backend.frames
        latest = factory.backend.frames[-1]
        measured = state_sample(transport_contract, profile, timestamp)
        measured["positions"][:14] = [value["position"] for value in latest["joint_cmd"]]
        measured["velocities"][:14] = [value["velocity"] for value in latest["joint_cmd"]]
        observed = runtime.receive_state(measured, now_seconds=timestamp)
        if not observed.accepted:
            break
    cases.append({
        "case": "nominal_one_point_lifecycle",
        "passed": (
            state_decision.accepted
            and chunk_decision.accepted
            and tick_decisions
            and all(item.accepted for item in tick_decisions)
            and runtime.state == "COMPLETED"
            and factory.count == 1
            and factory.backend is not None
            and len(factory.backend.frames) == runtime.frames_published
            and len(factory.backend.frames) >= 2
            and factory.backend.stop_count == 1
        ),
        "frames_published": runtime.frames_published,
        "backend_stop_count": 0 if factory.backend is None else factory.backend.stop_count,
    })

    def chunk_fault(name: str, mutate: Callable[[dict[str, Any]], None]) -> None:
        local_runtime, local_factory, state, state_ok = prepared(modules, values)
        candidate = chunk(profile, state, 100.01)
        mutate(candidate)
        decision = local_runtime.receive_chunk(candidate, now_seconds=100.01)
        cases.append({
            "case": name,
            "passed": (
                state_ok.accepted and not decision.accepted
                and local_runtime.state == "FAULTED"
                and local_factory.count == 0
                and local_factory.backend is None
            ),
            "reasons": decision.reasons,
            "backend_factory_count": local_factory.count,
        })

    mutations: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
        ("chunk_schema", lambda value: value.__setitem__("schema", "bad")),
        ("chunk_topic", lambda value: value.__setitem__("source_topic", "/wrong")),
        ("chunk_status", lambda value: value.__setitem__("status_code", -1)),
        ("chunk_id", lambda value: value.__setitem__("chunk_id", -1)),
        ("chunk_stale", lambda value: value.__setitem__("received_time_seconds", 99.0)),
        ("chunk_negative_inference", lambda value: value.__setitem__("inference_time_seconds", -1.0)),
        ("chunk_point_count", lambda value: value["points"].pop()),
        ("chunk_point_dimension", lambda value: value["points"][0]["positions"].pop()),
        ("chunk_nonfinite", lambda value: value["points"][0]["positions"].__setitem__(0, float("nan"))),
        ("chunk_first_time", lambda value: value["points"][0].__setitem__("time_from_start_seconds", 0.01)),
        ("chunk_times_regressive", lambda value: value["points"][2].__setitem__("time_from_start_seconds", 0.01)),
        ("chunk_arm_delta", lambda value: value["points"][0]["positions"].__setitem__(0, value["points"][0]["positions"][0] + 0.11)),
        ("chunk_range", lambda value: value["points"][0]["positions"].__setitem__(0, -100.0)),
    ]
    for name, mutation in mutations:
        chunk_fault(name, mutation)

    local_runtime, local_factory, state, state_ok = prepared(modules, values)
    masked = chunk(profile, state, 100.01)
    masked["points"][0]["positions"][14:] = [100.0] * 6
    masked_decision = local_runtime.receive_chunk(masked, now_seconds=100.01)
    cases.append({
        "case": "checkpoint_locked_axes_are_masked_to_measured_hold",
        "passed": (
            state_ok.accepted and masked_decision.accepted
            and local_runtime.state == "DISPATCHING_ONE_POINT"
            and local_factory.count == 1
        ),
        "reasons": masked_decision.reasons,
    })

    # State-side guards before and during command dispatch.
    for name, mutation in (
        ("state_wrong_source", lambda value: value.__setitem__("source_topic", "/mc/sdk/robot_state")),
        ("state_not_ready", lambda value: value["positions"].__setitem__(0, value["positions"][0] + 0.02)),
        ("state_arm_moving", lambda value: value["velocities"].__setitem__(0, 0.02)),
        ("state_locked_moving", lambda value: value["velocities"].__setitem__(14, 0.02)),
    ):
        factory = BackendFactory(transport_module)
        local_runtime = make_runtime(
            runtime_module, monitor_module, transport_module, activation,
            monitor_contract, transport_contract, limits, profile, factory,
        )
        candidate = state_sample(transport_contract, profile, 100.0)
        mutation(candidate)
        decision = local_runtime.receive_state(candidate, now_seconds=100.0)
        cases.append({
            "case": name,
            "passed": not decision.accepted and local_runtime.state == "FAULTED" and factory.count == 0,
            "reasons": decision.reasons,
        })

    local_runtime, local_factory, state, state_ok = prepared(modules, values)
    stale_chunk = chunk(profile, state, 100.2)
    decision = local_runtime.receive_chunk(stale_chunk, now_seconds=100.2)
    cases.append({
        "case": "fresh_state_required_at_chunk",
        "passed": state_ok.accepted and not decision.accepted and local_runtime.state == "FAULTED" and local_factory.count == 0,
        "reasons": decision.reasons,
    })

    local_runtime, local_factory, state, _ = prepared(modules, values, fail_create=True)
    decision = local_runtime.receive_chunk(chunk(profile, state, 100.01), now_seconds=100.01)
    cases.append({
        "case": "backend_create_failure",
        "passed": not decision.accepted and local_runtime.state == "FAULTED" and local_factory.count == 1,
        "reasons": decision.reasons,
    })

    local_runtime, local_factory, state, _ = prepared(modules, values, fail_after=0)
    local_runtime.receive_chunk(chunk(profile, state, 100.01), now_seconds=100.01)
    decision = local_runtime.tick(now_seconds=100.02)
    cases.append({
        "case": "backend_publish_failure",
        "passed": (
            not decision.accepted and local_runtime.state == "FAULTED"
            and local_factory.backend is not None and local_factory.backend.stop_count == 1
        ),
        "reasons": decision.reasons,
    })

    local_runtime, local_factory, state, _ = prepared(modules, values)
    local_runtime.receive_chunk(chunk(profile, state, 100.01), now_seconds=100.01)
    first_stop = local_runtime.stop()
    second_stop = local_runtime.stop()
    cases.append({
        "case": "runtime_stop_idempotent",
        "passed": (
            first_stop.accepted and second_stop.accepted
            and local_factory.backend is not None and local_factory.backend.stop_count == 1
            and not local_factory.backend.frames
        ),
    })

    # Static activation and source checks.
    runtime_tree = ast.parse(args.runtime.read_text(encoding="utf-8"))
    process_source = args.ros_process.read_text(encoding="utf-8")
    process_tree = ast.parse(process_source)
    backend_source = args.ros_backend.read_text(encoding="utf-8")
    backend_tree = ast.parse(backend_source)
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(runtime_tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").split(".")[0]
        for node in ast.walk(runtime_tree)
        if isinstance(node, ast.ImportFrom)
    }
    static_checks = {
        "runtime_core_has_no_ros_network_subprocess_import": not (
            imports & {"rclpy", "rospy", "socket", "subprocess"}
        ),
        "repository_activation_disabled": template["active_launcher_enabled"] is False,
        "repository_owner_acceptance_false": template["owner_accepted_engineering_limits"] is False,
        "repository_physical_authorization_false": template["physical_execution_authorized"] is False,
        "repository_authorization_run_absent": template["authorization_run_id"] is None,
        "whole_state_selected": template["selected_state_topic"] == "/mc/whole_joint_states",
        "ros_process_has_explicit_main": any(
            isinstance(node, ast.FunctionDef) and node.name == "main"
            for node in ast.walk(process_tree)
        ),
        "ros_import_after_activation_rejection": (
            process_source.index("if not runtime_module.activation_is_enabled(activation):")
            < process_source.index("    import rclpy")
        ),
        "ros_process_subscribes_selected_state_and_chunk": (
            "self.create_subscription(" in process_source
            and 'activation["selected_state_topic"]' in process_source
            and 'activation["chunk_topic"]' in process_source
        ),
        "ros_process_uses_lazy_backend_factory": (
            "backend_factory=lambda: ros_backend_module.RosSdkRobotCommandBackend(self)"
            in process_source
        ),
        "ros_backend_only_command_publisher": (
            sum(
                1
                for node in ast.walk(backend_tree)
                if isinstance(node, ast.Attribute) and node.attr == "create_publisher"
            ) == 1
            and '"/mc/sdk/robot_command"' in backend_source
            and "ReliabilityPolicy.BEST_EFFORT" in backend_source
            and "depth=5" in backend_source
        ),
        "ros_backend_stop_destroys_publisher": "destroy_publisher" in backend_source,
    }

    # Mutated templates that do not satisfy all three gates remain disabled.
    activation_cases = []
    for key in (
        "owner_accepted_engineering_limits",
        "active_launcher_enabled",
        "physical_execution_authorized",
    ):
        candidate = copy.deepcopy(template)
        candidate[key] = True
        activation_cases.append({
            "case": f"only_{key}",
            "passed": runtime_module.activation_is_enabled(candidate) is False,
        })

    failed = sum(not item["passed"] for item in cases)
    activation_failed = sum(not item["passed"] for item in activation_cases)
    report = {
        "schema": "cruzr-s2-vla-one-point-runtime-audit-e6.0w-v1",
        "experiment_id": "E6.0W",
        "status": "PASS_RUNTIME_CORE_OFFLINE_PRODUCTION_ACTIVATION_BLOCKED",
        "mode": "local_memory_only_no_robot_no_network_no_ros_no_publisher",
        "all_expectations_passed": (
            failed == 0 and activation_failed == 0 and all(static_checks.values())
        ),
        "case_count": len(cases),
        "failed_case_count": failed,
        "activation_case_count": len(activation_cases),
        "failed_activation_case_count": activation_failed,
        "static_checks": static_checks,
        "cases": cases,
        "activation_cases": activation_cases,
        "runtime_core_implemented": True,
        "ros_process_implemented": True,
        "active_launcher_enabled": False,
        "owner_accepted_engineering_limits": False,
        "physical_execution_authorized": False,
        "physical_publisher_count": 0,
        "network_calls": 0,
        "robot_state_read": False,
        "physical_movement_commanded": False,
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"E6.0W_CASES={len(cases)}")
    print(f"E6.0W_ACTIVATION_CASES={len(activation_cases)}")
    print(f"E6.0W_FAILED_EXPECTATIONS={failed + activation_failed}")
    print("E6.0W_RUNTIME_CORE_IMPLEMENTED=1")
    print("E6.0W_ROS_PROCESS_IMPLEMENTED=1")
    print("E6.0W_ACTIVE_LAUNCHER_ENABLED=0")
    print("E6.0W_PHYSICAL_AUTHORIZED=0")
    return 0 if report["all_expectations_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
