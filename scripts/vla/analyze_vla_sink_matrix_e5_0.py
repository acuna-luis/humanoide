#!/usr/bin/env python3
"""Validate the complete E5.0 sink matrix and its axis-mask semantics."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import pathlib
import sys
from typing import Any


EXPECTED_PROFILES = {
    "P14_A": 14,
    "P15_AW": 15,
    "P16_AH": 16,
    "P17_AL": 17,
    "P17_AHW": 17,
    "P18_ALW": 18,
    "P19_AHL": 19,
    "P20_AHLW": 20,
}
EXPECTED_FIXTURES = ("low", "middle")
NOW = 2000.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=pathlib.Path, required=True)
    parser.add_argument("--sink", type=pathlib.Path, required=True)
    parser.add_argument("--profile", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    return parser.parse_args()


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_sink_module(path: pathlib.Path):
    spec = importlib.util.spec_from_file_location("vla_executor_sink_e5_0", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load sink module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_json(path: pathlib.Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise AssertionError(f"expected JSON object: {path}")
    return value


def close(left: float, right: float) -> bool:
    return abs(float(left) - float(right)) <= 1e-12


def mask_probe(module: Any, profile: dict[str, Any], axis_profile: str, fixture: str) -> dict[str, Any]:
    sink = module.VlaExecutorSink(
        profile=profile,
        axis_profile=axis_profile,
        fixture=fixture,
        runtime_id="cruzr-s2-vla-sink-e5.0-mask-probe-v1",
        checkpoint_id="checkpoint-40000-read-only-contract",
    )
    assert sink.acquire_client("e5.0-mask-probe").accepted
    assert sink.refresh_deadman("e5.0-mask-probe", NOW).accepted
    message = module.valid_message(sink, chunk_id=1, now=NOW)
    input_row = list(message["points"][0]["positions"])
    for index, (low, high, delta_limit) in enumerate(
        zip(profile["lower_boundary"], profile["upper_boundary"], profile["max_first_point_delta"])
    ):
        delta = min(0.001, 0.10 * (float(high) - float(low)), 0.10 * float(delta_limit))
        if delta <= 0:
            raise AssertionError(f"joint {index} has no positive probe delta")
        input_row[index] += delta
    for point in message["points"]:
        point["positions"] = list(input_row)
    decision = sink.submit(message, now=NOW)
    if not decision.accepted or decision.command is None:
        raise AssertionError(
            f"mask probe rejected for {axis_profile}/{fixture}: {decision.reasons}"
        )
    enabled = set(sink.enabled)
    locked = set(range(int(profile["action_dim"]))) - enabled
    effective = decision.command["effective_points"]
    enabled_copy_ok = all(
        close(row[index], input_row[index]) for row in effective for index in enabled
    )
    locked_hold_ok = all(
        close(row[index], sink.hold_state[index]) for row in effective for index in locked
    )
    locked_differ_from_requested = all(
        not close(input_row[index], sink.hold_state[index]) for index in locked
    )
    hold_is_not_all_zero = any(not close(value, 0.0) for value in sink.hold_state)
    passed = (
        enabled_copy_ok
        and locked_hold_ok
        and locked_differ_from_requested
        and hold_is_not_all_zero
        and len(enabled) == EXPECTED_PROFILES[axis_profile]
        and decision.command["physical_publisher_count"] == 0
    )
    return {
        "axis_profile": axis_profile,
        "fixture": fixture,
        "enabled_axis_count": len(enabled),
        "locked_axis_count": len(locked),
        "enabled_indices": sorted(enabled),
        "locked_indices": sorted(locked),
        "enabled_axes_copy_requested_chunk": enabled_copy_ok,
        "locked_axes_equal_fixture_hold": locked_hold_ok,
        "locked_axes_ignore_distinct_requested_values": locked_differ_from_requested,
        "fixture_hold_vector_not_all_zero": hold_is_not_all_zero,
        "hold_source": "synthetic_fixture_midpoint_not_live_robot_state",
        "physical_publisher_count": decision.command["physical_publisher_count"],
        "passed": passed,
    }


def main() -> int:
    args = parse_args()
    results = args.results.resolve()
    sink_path = args.sink.resolve()
    profile_path = args.profile.resolve()
    output = args.output.resolve()
    module = load_sink_module(sink_path)
    profile = module.load_profile(profile_path)
    assert dict(module.AXIS_PROFILES) == {
        name: module.AXIS_PROFILES[name] for name in EXPECTED_PROFILES
    }
    assert tuple(module.VALID_FIXTURES) == EXPECTED_FIXTURES

    cells: list[dict[str, Any]] = []
    probes: list[dict[str, Any]] = []
    for axis_profile, enabled_count in EXPECTED_PROFILES.items():
        for fixture in EXPECTED_FIXTURES:
            summary_path = results / axis_profile / fixture / "summary.json"
            cases_path = results / axis_profile / fixture / "cases.jsonl"
            summary = load_json(summary_path)
            cases = [
                json.loads(line)
                for line in cases_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            mismatch = [row for row in cases if row.get("case") == "axis_profile_mismatch"]
            cell_passed = (
                summary.get("schema") == "cruzr-s2-vla-executor-sink-e3.2-v1"
                and summary.get("mode") == "local_pure_python_sink_no_ros_no_hardware"
                and summary.get("axis_profile") == axis_profile
                and summary.get("fixture") == fixture
                and summary.get("total_case_count") == 34
                and summary.get("valid_case_count") == 2
                and summary.get("valid_case_accepted_count") == 2
                and summary.get("invalid_case_count") == 32
                and summary.get("invalid_case_rejected_count") == 32
                and summary.get("failed_expectation_count") == 0
                and summary.get("all_expectations_passed") is True
                and summary.get("static_safety", {}).get("safe") is True
                and summary.get("sink_physical_publisher_count") == 0
                and summary.get("sink_network_calls") == 0
                and summary.get("robot_state_read") is False
                and summary.get("physical_movement_commanded") is False
                and len(cases) == 34
                and all(row.get("passed") is True for row in cases)
                and len(mismatch) == 1
                and mismatch[0].get("observed_accept") is False
                and "axis_profile:mismatch" in mismatch[0].get("reasons", [])
                and len(module.enabled_indices(axis_profile)) == enabled_count
            )
            cells.append(
                {
                    "axis_profile": axis_profile,
                    "fixture": fixture,
                    "enabled_axis_count": enabled_count,
                    "total_cases": summary.get("total_case_count"),
                    "valid_accepted": summary.get("valid_case_accepted_count"),
                    "invalid_rejected": summary.get("invalid_case_rejected_count"),
                    "failed_expectations": summary.get("failed_expectation_count"),
                    "passed": cell_passed,
                    "summary_sha256": sha256_file(summary_path),
                    "cases_sha256": sha256_file(cases_path),
                }
            )
            probes.append(mask_probe(module, profile, axis_profile, fixture))

    totals = {
        "matrix_cell_count": len(cells),
        "matrix_cell_pass_count": sum(cell["passed"] for cell in cells),
        "fault_case_count": sum(int(cell["total_cases"]) for cell in cells),
        "valid_case_accepted_count": sum(int(cell["valid_accepted"]) for cell in cells),
        "invalid_case_rejected_count": sum(int(cell["invalid_rejected"]) for cell in cells),
        "failed_expectation_count": sum(int(cell["failed_expectations"]) for cell in cells),
        "mask_probe_count": len(probes),
        "mask_probe_pass_count": sum(probe["passed"] for probe in probes),
    }
    all_passed = (
        totals
        == {
            "matrix_cell_count": 16,
            "matrix_cell_pass_count": 16,
            "fault_case_count": 544,
            "valid_case_accepted_count": 32,
            "invalid_case_rejected_count": 512,
            "failed_expectation_count": 0,
            "mask_probe_count": 16,
            "mask_probe_pass_count": 16,
        }
        and all(cell["passed"] for cell in cells)
        and all(probe["passed"] for probe in probes)
    )
    report = {
        "schema": "cruzr-s2-vla-executor-sink-matrix-e5.0-v1",
        "experiment_id": "E5.0",
        "mode": "local_pure_python_no_robot_no_network_no_ros_no_publisher",
        "profiles": list(EXPECTED_PROFILES),
        "fixtures": list(EXPECTED_FIXTURES),
        "profile_sha256": sha256_file(profile_path),
        "sink_sha256": sha256_file(sink_path),
        "totals": totals,
        "cells": cells,
        "mask_probes": probes,
        "all_expectations_passed": all_passed,
        "robot_state_read": False,
        "network_calls": 0,
        "physical_publishers": 0,
        "physical_movement_commanded": False,
        "physical_executor_authorized": False,
        "qualification_scope": (
            "offline synthetic validation only; fixture holds are not live robot poses"
        ),
        "next_experiment_authorized": "E5.1_SHADOW_ONLY",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        "E5.0_MATRIX="
        f"cells:{totals['matrix_cell_pass_count']}/{totals['matrix_cell_count']},"
        f"faults:{totals['fault_case_count']},"
        f"invalid_rejected:{totals['invalid_case_rejected_count']},"
        f"mask_probes:{totals['mask_probe_pass_count']}/{totals['mask_probe_count']}"
    )
    print(f"E5.0_RESULT={'PASS' if all_passed else 'FAIL'}")
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
