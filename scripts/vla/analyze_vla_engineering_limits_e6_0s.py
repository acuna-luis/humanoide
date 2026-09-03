#!/usr/bin/env python3
"""Validate the replaceable project acceleration envelope for E6.0."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import pathlib
import random
import sys
from typing import Any


def load_module(path: pathlib.Path):
    spec = importlib.util.spec_from_file_location("e6_0s_transport", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def metrics(trajectory: list[dict[str, Any]], dt: float) -> dict[str, float]:
    analytic_v = max(abs(value) for point in trajectory for value in point["velocities"])
    analytic_a = max(abs(value) for point in trajectory for value in point["accelerations"])
    positions = [point["positions"] for point in trajectory]
    discrete_v = 0.0
    velocities: list[list[float]] = []
    for first, second in zip(positions, positions[1:]):
        velocity = [(b - a) / dt for a, b in zip(first, second)]
        velocities.append(velocity)
        discrete_v = max(discrete_v, *(abs(value) for value in velocity))
    discrete_a = 0.0
    for first, second in zip(velocities, velocities[1:]):
        discrete_a = max(
            discrete_a,
            *(abs(b - a) / dt for a, b in zip(first, second)),
        )
    return {
        "analytic_maximum_velocity_rad_s": analytic_v,
        "analytic_maximum_acceleration_rad_s2": analytic_a,
        "discrete_maximum_velocity_rad_s": discrete_v,
        "discrete_maximum_acceleration_rad_s2": discrete_a,
        "duration_seconds": trajectory[-1]["elapsed_seconds"],
        "frame_count": len(trajectory),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limits", type=pathlib.Path, required=True)
    parser.add_argument("--transport", type=pathlib.Path, required=True)
    parser.add_argument("--vendor-direct-executor", type=pathlib.Path, required=True)
    parser.add_argument("--vendor-sdk-executor", type=pathlib.Path, required=True)
    parser.add_argument("--joint-cmd-msg", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()

    transport = load_module(args.transport)
    limits = transport.load_engineering_limits(args.limits)
    start = [0.0] * 14
    dt = float(limits["sample_period_seconds"])
    vmax = max(float(value) for value in limits["maximum_velocity_rad_s"])
    amax = max(float(value) for value in limits["maximum_acceleration_rad_s2"])
    maximum_duration = float(limits["maximum_transition_duration_seconds"])

    cases: list[dict[str, Any]] = []
    for index in range(14):
        for sign, label in ((1.0, "positive"), (-1.0, "negative")):
            target = list(start)
            target[index] = sign * float(limits["maximum_target_delta_rad"][index])
            trajectory = transport.plan_minimum_jerk(start, target, limits)
            observed = metrics(trajectory, dt)
            passed = (
                observed["analytic_maximum_velocity_rad_s"] <= vmax + 1e-12
                and observed["analytic_maximum_acceleration_rad_s2"] <= amax + 1e-12
                and observed["discrete_maximum_velocity_rad_s"] <= vmax + 1e-12
                and observed["discrete_maximum_acceleration_rad_s2"] <= amax + 1e-9
                and observed["duration_seconds"] <= maximum_duration + 1e-12
                and trajectory[0]["positions"] == start
                and trajectory[-1]["positions"] == target
            )
            cases.append({"case": f"axis_{index:02d}_{label}_limit", "passed": passed, **observed})

    rng = random.Random(600)
    random_max_v = 0.0
    random_max_a = 0.0
    random_max_duration = 0.0
    random_failed = 0
    for _ in range(2000):
        target = [
            rng.uniform(-float(limit), float(limit))
            for limit in limits["maximum_target_delta_rad"]
        ]
        trajectory = transport.plan_minimum_jerk(start, target, limits)
        observed = metrics(trajectory, dt)
        random_max_v = max(random_max_v, observed["discrete_maximum_velocity_rad_s"])
        random_max_a = max(random_max_a, observed["discrete_maximum_acceleration_rad_s2"])
        random_max_duration = max(random_max_duration, observed["duration_seconds"])
        if not (
            observed["discrete_maximum_velocity_rad_s"] <= vmax + 1e-12
            and observed["discrete_maximum_acceleration_rad_s2"] <= amax + 1e-9
            and observed["duration_seconds"] <= maximum_duration + 1e-12
        ):
            random_failed += 1

    dense_peak_v = 0.0
    dense_peak_a = 0.0
    for index in range(100001):
        _, velocity, acceleration = transport._minimum_jerk(index / 100000.0)
        dense_peak_v = max(dense_peak_v, abs(velocity))
        dense_peak_a = max(dense_peak_a, abs(acceleration))

    direct_source = args.vendor_direct_executor.read_text(encoding="utf-8")
    sdk_source = args.vendor_sdk_executor.read_text(encoding="utf-8")
    joint_spec = args.joint_cmd_msg.read_text(encoding="utf-8")
    supplier_audit = {
        "alternate_direct_executor_speed_check_3_14_present": "self.max_joint_speed = 3.14" in direct_source,
        "sdk_source_speed_check_6_28_present": "self.max_joint_speed = 6.28" in sdk_source,
        "sdk_source_has_no_max_acceleration_check": "max_joint_acceleration" not in sdk_source and "max_acceleration" not in sdk_source,
        "sdk_joint_cmd_has_no_acceleration_field": "acceleration" not in joint_spec,
        "supplier_speed_values_treated_as_certified": False,
    }
    envelope_passed = (
        all(case["passed"] for case in cases)
        and random_failed == 0
        and abs(dense_peak_v - float(limits["analytic_peak_velocity_factor"])) < 1e-10
        and abs(dense_peak_a - float(limits["analytic_peak_acceleration_factor"])) < 1e-8
        and all(value is True for key, value in supplier_audit.items() if key != "supplier_speed_values_treated_as_certified")
    )
    report = {
        "schema": "cruzr-s2-vla-engineering-limits-audit-e6.0s-v1",
        "experiment_id": "E6.0S",
        "status": "PASS_PROJECT_ENGINEERING_ENVELOPE_OFFLINE_PENDING_OWNER_ACCEPTANCE",
        "mode": "local_math_only_no_robot_no_network_no_ros_no_publisher",
        "all_expectations_passed": envelope_passed,
        "directed_case_count": len(cases),
        "directed_failed_count": sum(not case["passed"] for case in cases),
        "random_case_count": 2000,
        "random_failed_count": random_failed,
        "dense_derivative_sample_count": 100001,
        "dense_normalized_peak_velocity": dense_peak_v,
        "dense_normalized_peak_acceleration": dense_peak_a,
        "random_observed_maximum_velocity_rad_s": random_max_v,
        "random_observed_maximum_acceleration_rad_s2": random_max_a,
        "random_observed_maximum_duration_seconds": random_max_duration,
        "configured_maximum_velocity_rad_s": vmax,
        "configured_maximum_acceleration_rad_s2": amax,
        "configured_maximum_target_delta_rad": max(limits["maximum_target_delta_rad"]),
        "configured_sample_period_seconds": dt,
        "configured_maximum_transition_duration_seconds": maximum_duration,
        "manufacturer_certified": False,
        "owner_acceptance_required": True,
        "owner_accepted": False,
        "measured_physical_acceleration_validated": False,
        "runtime_measured_acceleration_monitor_implemented": False,
        "physical_execution_authorized": False,
        "supplier_source_audit": supplier_audit,
        "source_sha256": {
            "limits": sha256(args.limits),
            "transport": sha256(args.transport),
            "vendor_direct_executor": sha256(args.vendor_direct_executor),
            "vendor_sdk_executor": sha256(args.vendor_sdk_executor),
            "joint_cmd_msg": sha256(args.joint_cmd_msg),
        },
        "directed_cases": cases,
        "physical_publisher_count": 0,
        "robot_state_read": False,
        "network_calls": 0,
        "physical_movement_commanded": False,
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"E6.0S_DIRECTED_CASES={len(cases)}")
    print("E6.0S_RANDOM_CASES=2000")
    print(f"E6.0S_FAILED_EXPECTATIONS={sum(not case['passed'] for case in cases) + random_failed}")
    print(f"E6.0S_PROJECT_MAX_VELOCITY_RAD_S={vmax}")
    print(f"E6.0S_PROJECT_MAX_ACCELERATION_RAD_S2={amax}")
    print("E6.0S_MANUFACTURER_CERTIFIED=0")
    print("E6.0S_OWNER_ACCEPTED=0")
    print("E6.0S_PHYSICAL_AUTHORIZED=0")
    return 0 if envelope_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
