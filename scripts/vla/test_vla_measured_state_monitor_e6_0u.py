#!/usr/bin/env python3
"""Offline fault campaign for the E6.0U measured-state monitor."""

from __future__ import annotations

import argparse
import ast
import copy
import importlib.util
import json
import pathlib
import sys
from typing import Any, Callable


def load_module(path: pathlib.Path):
    spec = importlib.util.spec_from_file_location("e6_0u_monitor", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sample(
    contract: dict[str, Any],
    *,
    timestamp: float,
    arm_positions: list[float] | None = None,
    arm_velocities: list[float] | None = None,
    locked_positions: list[float] | None = None,
    locked_velocities: list[float] | None = None,
    source: str = "/mc/whole_joint_states",
) -> dict[str, Any]:
    ready = list(contract["ready_arm_positions"])
    return {
        "schema": "cruzr-s2-vla-normalized-joint-state-e6.0u-v1",
        "source_topic": source,
        "sample_time_seconds": timestamp,
        "received_time_seconds": timestamp,
        "joint_names": [
            *contract["commanded_joint_names"],
            *contract["locked_joint_names"],
        ],
        "positions": [
            *(ready if arm_positions is None else arm_positions),
            *([0.0] * 6 if locked_positions is None else locked_positions),
        ],
        "velocities": [
            *([0.0] * 14 if arm_velocities is None else arm_velocities),
            *([0.0] * 6 if locked_velocities is None else locked_velocities),
        ],
    }


class StopProbe:
    def __init__(self, fail: bool = False) -> None:
        self.count = 0
        self.fail = fail

    def __call__(self) -> None:
        self.count += 1
        if self.fail:
            raise RuntimeError("injected_stop_failure")


def new_monitor(module: Any, contract: dict[str, Any], limits: dict[str, Any], probe: StopProbe):
    return module.MeasuredStateMonitor(
        contract=contract,
        limits=limits,
        stop_callback=probe,
    )


def fault_case(
    name: str,
    module: Any,
    contract: dict[str, Any],
    limits: dict[str, Any],
    mutate: Callable[[dict[str, Any]], None],
    *,
    phase: str = "arm",
) -> dict[str, Any]:
    probe = StopProbe()
    monitor = new_monitor(module, contract, limits, probe)
    initial = sample(contract, timestamp=10.0)
    if phase == "arm":
        mutate(initial)
        decision = monitor.arm(initial, now_seconds=10.0)
    else:
        armed = monitor.arm(initial, now_seconds=10.0)
        candidate = sample(contract, timestamp=10.01)
        mutate(candidate)
        decision = monitor.observe(candidate, now_seconds=10.01)
        if not armed.accepted:
            raise RuntimeError(f"setup failed: {name}")
    passed = (
        not decision.accepted
        and monitor.state == "FAULTED"
        and probe.count == 1
        and monitor.stop_invocations == 1
    )
    second = monitor.stop()
    passed = passed and probe.count == 1 and second.state == "STOPPED"
    return {
        "case": name,
        "passed": passed,
        "phase": phase,
        "reasons": decision.reasons,
        "stop_count_after_explicit_stop": probe.count,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--monitor", type=pathlib.Path, required=True)
    parser.add_argument("--contract", type=pathlib.Path, required=True)
    parser.add_argument("--limits", type=pathlib.Path, required=True)
    parser.add_argument("--transport", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()

    module = load_module(args.monitor)
    transport = load_module(args.transport)
    contract = module.load_monitor_contract(args.contract)
    limits = module.load_limits(args.limits)
    cases: list[dict[str, Any]] = []

    # Nominal maximum-delta trajectories in both directions for every P14 axis.
    for axis in range(14):
        for sign, label in ((1.0, "positive"), (-1.0, "negative")):
            probe = StopProbe()
            monitor = new_monitor(module, contract, limits, probe)
            ready = list(contract["ready_arm_positions"])
            armed = monitor.arm(sample(contract, timestamp=1.0), now_seconds=1.0)
            target = list(ready)
            target[axis] += sign * float(limits["maximum_target_delta_rad"][axis])
            trajectory = transport.plan_minimum_jerk(ready, target, limits)
            decisions = []
            for point in trajectory[1:]:
                timestamp = 1.0 + float(point["elapsed_seconds"])
                decisions.append(monitor.observe(sample(
                    contract,
                    timestamp=timestamp,
                    arm_positions=list(point["positions"]),
                    arm_velocities=list(point["velocities"]),
                ), now_seconds=timestamp))
            cases.append({
                "case": f"nominal_axis_{axis:02d}_{label}",
                "passed": (
                    armed.accepted
                    and all(item.accepted for item in decisions)
                    and any(item.checked_acceleration for item in decisions)
                    and monitor.state == "MONITORING"
                    and probe.count == 0
                ),
                "phase": "trajectory",
                "reasons": [reason for item in decisions for reason in item.reasons],
            })

    # Every arm axis must trip independently on velocity and acceleration.
    for axis in range(14):
        for sign, label in ((1.0, "positive"), (-1.0, "negative")):
            def velocity_mutator(value: dict[str, Any], i: int = axis, s: float = sign) -> None:
                value["velocities"][i] = s * 0.151
            cases.append(fault_case(
                f"velocity_axis_{axis:02d}_{label}", module, contract, limits,
                velocity_mutator, phase="observe",
            ))

            def acceleration_mutator(value: dict[str, Any], i: int = axis, s: float = sign) -> None:
                value["velocities"][i] = s * 0.0051
            cases.append(fault_case(
                f"acceleration_axis_{axis:02d}_{label}", module, contract, limits,
                acceleration_mutator, phase="observe",
            ))

    # Locked head/lifter/waist axes may neither move nor drift.
    for axis in range(6):
        for sign, label in ((1.0, "positive"), (-1.0, "negative")):
            def locked_velocity(value: dict[str, Any], i: int = axis, s: float = sign) -> None:
                value["velocities"][14 + i] = s * 0.011
            cases.append(fault_case(
                f"locked_velocity_{axis:02d}_{label}", module, contract, limits,
                locked_velocity, phase="observe",
            ))

            def locked_drift(value: dict[str, Any], i: int = axis, s: float = sign) -> None:
                value["positions"][14 + i] = s * 0.011
            cases.append(fault_case(
                f"locked_drift_{axis:02d}_{label}", module, contract, limits,
                locked_drift, phase="observe",
            ))

    structural: list[tuple[str, Callable[[dict[str, Any]], None], str]] = [
        ("schema", lambda value: value.__setitem__("schema", "bad"), "arm"),
        ("unknown_source", lambda value: value.__setitem__("source_topic", "/unknown"), "arm"),
        ("stale", lambda value: value.__setitem__("received_time_seconds", 9.8), "arm"),
        ("received_future", lambda value: value.__setitem__("received_time_seconds", 10.01), "arm"),
        ("message_after_receive", lambda value: value.__setitem__("sample_time_seconds", 10.01), "arm"),
        ("duplicate_name", lambda value: value["joint_names"].__setitem__(1, value["joint_names"][0]), "arm"),
        ("missing_joint", lambda value: [value[key].pop() for key in ("joint_names", "positions", "velocities")], "arm"),
        ("missing_velocity", lambda value: value.__setitem__("velocities", []), "arm"),
        ("nonfinite_position", lambda value: value["positions"].__setitem__(0, float("nan")), "arm"),
        ("nonfinite_velocity", lambda value: value["velocities"].__setitem__(0, float("inf")), "arm"),
        ("source_change", lambda value: value.__setitem__("source_topic", "/mc/sdk/robot_state"), "observe"),
        ("time_not_increasing", lambda value: value.__setitem__("sample_time_seconds", 10.0), "observe"),
        ("acceleration_gap", lambda value: (
            value.__setitem__("sample_time_seconds", 10.06),
            value.__setitem__("received_time_seconds", 10.06),
        ), "observe"),
    ]
    for name, mutator, phase in structural:
        cases.append(fault_case(name, module, contract, limits, mutator, phase=phase))

    for axis in range(14):
        def not_ready(value: dict[str, Any], i: int = axis) -> None:
            value["positions"][i] += 0.011
        cases.append(fault_case(
            f"not_ready_{axis:02d}", module, contract, limits, not_ready,
        ))

        def not_stationary(value: dict[str, Any], i: int = axis) -> None:
            value["velocities"][i] = 0.011
        cases.append(fault_case(
            f"not_stationary_{axis:02d}", module, contract, limits, not_stationary,
        ))

    # Samples faster than the acceleration window are accepted but accumulated.
    probe = StopProbe()
    monitor = new_monitor(module, contract, limits, probe)
    arm_decision = monitor.arm(sample(contract, timestamp=20.0), now_seconds=20.0)
    early = monitor.observe(sample(
        contract, timestamp=20.004, arm_velocities=[0.001] * 14,
    ), now_seconds=20.004)
    accumulated = monitor.observe(sample(
        contract, timestamp=20.01, arm_velocities=[0.004] * 14,
    ), now_seconds=20.01)
    cases.append({
        "case": "short_interval_accumulates",
        "passed": (
            arm_decision.accepted and early.accepted and not early.checked_acceleration
            and accumulated.accepted and accumulated.checked_acceleration
            and probe.count == 0
        ),
        "phase": "observe",
        "reasons": [*early.reasons, *accumulated.reasons],
    })

    # Explicit STOP is idempotent; callback failure is visible and terminal.
    probe = StopProbe()
    monitor = new_monitor(module, contract, limits, probe)
    monitor.arm(sample(contract, timestamp=30.0), now_seconds=30.0)
    first_stop = monitor.stop()
    second_stop = monitor.stop()
    cases.append({
        "case": "explicit_stop_idempotent",
        "passed": first_stop.accepted and second_stop.accepted and probe.count == 1,
        "phase": "stop",
        "reasons": [*first_stop.reasons, *second_stop.reasons],
    })
    failing_probe = StopProbe(fail=True)
    monitor = new_monitor(module, contract, limits, failing_probe)
    bad = sample(contract, timestamp=40.0)
    bad["schema"] = "bad"
    failed_stop = monitor.arm(bad, now_seconds=40.0)
    cases.append({
        "case": "stop_callback_failure_latches",
        "passed": (
            not failed_stop.accepted and monitor.state == "FAULTED"
            and failing_probe.count == 1
            and any(reason.startswith("stop_callback:RuntimeError") for reason in failed_stop.reasons)
        ),
        "phase": "fault",
        "reasons": failed_stop.reasons,
    })

    # Contract mutations must fail closed.
    contract_value = json.loads(args.contract.read_text(encoding="utf-8"))
    tamper: list[dict[str, Any]] = []
    mutations = {
        "physical_execution_authorized": True,
        "physical_execution_default": True,
        "active_launcher_implemented": True,
        "software_stop_is_hardware_estop_equivalent": True,
        "velocity_field_required": False,
        "task_id": 1,
        "axis_profile": "P20_AHLW",
        "scenario": "BOX_PRESENT",
    }
    for key, value in mutations.items():
        candidate = copy.deepcopy(contract_value)
        candidate[key] = value
        temporary = args.contract.parent / f".e6_0u_tamper_{key}.json"
        temporary.write_text(json.dumps(candidate), encoding="utf-8")
        rejected = False
        try:
            module.load_monitor_contract(temporary)
        except ValueError:
            rejected = True
        finally:
            temporary.unlink(missing_ok=True)
        tamper.append({"case": f"contract_{key}", "passed": rejected})

    tree = ast.parse(args.monitor.read_text(encoding="utf-8"))
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    forbidden = sorted(imports & {"rclpy", "rospy", "socket", "subprocess"})
    static_checks = {
        "monitor_has_no_ros_network_subprocess_import": not forbidden,
        "contract_physical_default_false": contract["physical_execution_default"] is False,
        "contract_launcher_false": contract["active_launcher_implemented"] is False,
        "contract_physical_authorized_false": contract["physical_execution_authorized"] is False,
        "two_state_sources_named": len(contract["allowed_state_sources"]) == 2,
        "twenty_required_named_joints": (
            len(contract["commanded_joint_names"]) + len(contract["locked_joint_names"])
        ) == 20,
    }
    failed = sum(not item["passed"] for item in cases)
    tamper_failed = sum(not item["passed"] for item in tamper)
    report = {
        "schema": "cruzr-s2-vla-measured-state-monitor-audit-e6.0u-v1",
        "experiment_id": "E6.0U",
        "status": "PASS_MEASURED_STATE_MONITOR_OFFLINE_ACTIVE_LAUNCHER_BLOCKED",
        "mode": "local_memory_only_no_robot_no_network_no_ros_no_publisher",
        "all_expectations_passed": (
            failed == 0 and tamper_failed == 0 and all(static_checks.values())
        ),
        "case_count": len(cases),
        "failed_case_count": failed,
        "contract_tamper_case_count": len(tamper),
        "failed_contract_tamper_count": tamper_failed,
        "static_checks": static_checks,
        "forbidden_imports": forbidden,
        "cases": cases,
        "contract_tamper_cases": tamper,
        "runtime_measured_acceleration_monitor_implemented": True,
        "measured_physical_acceleration_validated": False,
        "active_launcher_implemented": False,
        "owner_accepted": False,
        "physical_execution_authorized": False,
        "physical_publisher_count": 0,
        "network_calls": 0,
        "robot_state_read": False,
        "physical_movement_commanded": False,
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"E6.0U_CASES={len(cases)}")
    print(f"E6.0U_TAMPER_CASES={len(tamper)}")
    print(f"E6.0U_FAILED_EXPECTATIONS={failed + tamper_failed}")
    print("E6.0U_MEASURED_MONITOR_IMPLEMENTED=1")
    print("E6.0U_ACTIVE_LAUNCHER_IMPLEMENTED=0")
    print("E6.0U_PHYSICAL_AUTHORIZED=0")
    return 0 if report["all_expectations_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
