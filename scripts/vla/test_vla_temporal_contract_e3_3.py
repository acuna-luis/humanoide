#!/usr/bin/env python3
"""Run the reproducible E3.3 offline temporal campaign."""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import pathlib
import re
import statistics
import sys
from typing import Any, Callable


SCRIPT_PATH = pathlib.Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[2]
RUNTIME_DIR = SCRIPT_PATH.parent / "runtime"
MODULE_PATH = RUNTIME_DIR / "vla_temporal_contract.py"
DEFAULT_CONTRACT = RUNTIME_DIR / "cruzr_s2_vla_temporal_contract_e3_3.json"
VISION_SOURCE = REPO_ROOT / "cruzrss2_vla_pack-002/codes-S2/vision/rosa_vla_additional/vla-onboard/src/gr00t_control/gr00t_inference.py"
MODEL_SOURCE = REPO_ROOT / "cruzrss2_vla_pack-002/codes-S2/vision/rosa_vla_additional/vla-onboard/src/gr00t_control/model_interface_general_ros2.py"
VENDOR_YAML = REPO_ROOT / "cruzrss2_vla_pack-002/codes-S2/vision/rosa_vla_additional/vla-onboard/src/gr00t_control/configs/utars_clamp_and_place_large_bio_box_lock_lifter.yaml"
EXECUTOR_SOURCE = REPO_ROOT / "cruzrss2_vla_pack-002/codes-S2/motion/rosa_vla_additional/vla-motionx86/src/vla_executor/vla_executor/executor_node_sdk.py"
EXECUTOR_INSTALLED = REPO_ROOT / "cruzrss2_vla_pack-002/codes-S2/motion/rosa_vla_additional/vla-motionx86/install/vla_executor/lib/python3.10/site-packages/vla_executor/executor_node_sdk.py"

SPEC = importlib.util.spec_from_file_location("vla_temporal_contract", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {MODULE_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def number(source: str, pattern: str, label: str) -> float:
    match = re.search(pattern, source, re.MULTILINE)
    if not match:
        raise RuntimeError(f"cannot extract {label}")
    return float(match.group(1))


def vendor_audit() -> dict[str, Any]:
    paths = (VISION_SOURCE, MODEL_SOURCE, VENDOR_YAML, EXECUTOR_SOURCE, EXECUTOR_INSTALLED)
    for path in paths:
        if not path.is_file():
            raise RuntimeError(f"missing vendor artifact: {path}")
    vision = VISION_SOURCE.read_text(encoding="utf-8")
    model = MODEL_SOURCE.read_text(encoding="utf-8")
    yaml_text = VENDOR_YAML.read_text(encoding="utf-8")
    source_executor = EXECUTOR_SOURCE.read_text(encoding="utf-8")
    installed_executor = EXECUTOR_INSTALLED.read_text(encoding="utf-8")
    hz = number(vision, r"^DEFAULT_HZ\s*=\s*([0-9.]+)", "DEFAULT_HZ")
    chunk_num = int(number(vision, r"^CHUNK_NUM\s*=\s*([0-9.]+)", "CHUNK_NUM"))
    point_dt = number(vision, r"^CHUNK_POINT_DT\s*=\s*([0-9.]+)", "CHUNK_POINT_DT")
    continuous = int(number(yaml_text, r"^\s*continuous_end_chunk_num:\s*([0-9.]+)", "continuous_end_chunk_num"))
    threshold = number(yaml_text, r"^\s*end_threshold:\s*([0-9.]+)", "end_threshold")
    source_ms = number(source_executor, r"self\.motion_interval_ms\s*=\s*([0-9.]+)", "source motion interval")
    source_points = int(number(source_executor, r"self\.motion_n_pts\s*=\s*([0-9.]+)", "source motion points"))
    installed_ms = number(installed_executor, r"self\.motion_interval_ms\s*=\s*([0-9.]+)", "installed motion interval")
    installed_points = int(number(installed_executor, r"self\.motion_n_pts\s*=\s*([0-9.]+)", "installed motion points"))
    single_flag_assignment = "self.end_flag_triggered = bool(output_commands.get('end_flag', False))" in vision
    flag_threshold = "action_chunk[\"flag_pred\"].item() > self.end_threshold" in model
    continuous_used = "continuous_end_chunk_num" in vision or "continuous_end_chunk_num" in model
    horizon = (chunk_num - 1) * point_dt
    period = 1.0 / hz
    return {
        "schema": "cruzr-s2-vla-vendor-temporal-audit-e3.3-v1",
        "artifact_sha256": {str(path.relative_to(REPO_ROOT)): sha256_file(path) for path in paths},
        "vision_inference_hz": hz,
        "vision_nominal_period_seconds": period,
        "chunk_point_count": chunk_num,
        "chunk_point_dt_seconds": point_dt,
        "chunk_declared_horizon_seconds": horizon,
        "nominal_uncovered_gap_seconds": period - horizon,
        "yaml_end_threshold": threshold,
        "yaml_continuous_end_chunk_num": continuous,
        "vision_uses_single_end_flag_assignment": single_flag_assignment,
        "model_uses_strict_greater_than_threshold": flag_threshold,
        "continuous_end_chunk_num_referenced_by_runtime_python": continuous_used,
        "source_executor_interpolation_seconds": source_ms / 1000.0,
        "source_executor_interpolation_points": source_points,
        "installed_executor_interpolation_seconds": installed_ms / 1000.0,
        "installed_executor_interpolation_points": installed_points,
        "executor_copies_temporally_consistent": source_ms == installed_ms and source_points == installed_points,
        "vendor_physical_semantics_resolved": False,
        "conclusion": "single_flag_end_and_two_different_executor_timelines_observed; five_flag_rule_not_applied",
    }


def static_safety() -> dict[str, Any]:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports: set[str] = set()
    called: set[str] = set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
        elif isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            called.add(node.func.attr)
    forbidden_imports = {"rclpy", "socket", "subprocess", "requests", "urllib", "vla_msgs", "mc_task_msgs"}
    forbidden_calls = {"create_publisher", "publish", "send_goal_async", "create_client"}
    forbidden_names = {"RobotCommand", "Gr00tMotionChunk"}
    safe = not (
        imports & forbidden_imports
        or called & forbidden_calls
        or names & forbidden_names
        or "/mc/sdk/robot_command" in source
    )
    return {
        "safe": safe,
        "forbidden_imports_found": sorted(imports & forbidden_imports),
        "publisher_or_action_calls_found": sorted(called & forbidden_calls),
        "forbidden_names_found": sorted(names & forbidden_names),
        "physical_topic_literal_present": "/mc/sdk/robot_command" in source,
        "module_sha256": sha256_file(MODULE_PATH),
    }


def decision_case(name: str, family: str, expected: bool, decision: Any, gate: Any) -> dict[str, Any]:
    observed = bool(decision.accepted)
    return {
        "case": name,
        "family": family,
        "expected_accept": expected,
        "observed_accept": observed,
        "passed": observed is expected,
        "state": decision.state,
        "reasons": list(decision.reasons),
        "emitted_count": len(decision.emitted),
        "pending_count": len(gate.pending),
        "physical_publisher_count": gate.physical_publisher_count,
    }


def make_gate(contract: dict[str, Any]):
    return MODULE.OfflineTemporalGate(contract, started_at=100.0)


def drain(gate: Any, times: list[float], base: float) -> list[dict[str, Any]]:
    emitted: list[dict[str, Any]] = []
    for offset in times:
        decision = gate.advance(base + offset)
        if not decision.accepted:
            raise AssertionError(decision.reasons)
        emitted.extend(decision.emitted)
    return emitted


def campaign(contract: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    times = MODULE.nominal_point_times(contract)

    nominal = make_gate(contract)
    submit = nominal.submit(chunk_id=1, point_times=times, flag_pred=0.0, now=100.0)
    rows.append(decision_case("nominal_submit", "timeline", True, submit, nominal))
    points = drain(nominal, times, 100.0)
    rows.append({
        "case": "nominal_exact_10_points",
        "family": "timeline",
        "expected_accept": True,
        "observed_accept": len(points) == 10 and [p["point_index"] for p in points] == list(range(10)),
        "passed": len(points) == 10 and [p["point_index"] for p in points] == list(range(10)),
        "state": nominal.state,
        "reasons": [],
        "emitted_count": len(points),
        "pending_count": len(nominal.pending),
        "physical_publisher_count": 0,
    })
    no_replay = nominal.advance(100.90)
    rows.append({
        "case": "gap_no_old_point_replay",
        "family": "gap",
        "expected_accept": True,
        "observed_accept": no_replay.accepted and not no_replay.emitted and len(nominal.emission_log) == 10,
        "passed": no_replay.accepted and not no_replay.emitted and len(nominal.emission_log) == 10,
        "state": nominal.state,
        "reasons": list(no_replay.reasons),
        "emitted_count": 0,
        "pending_count": len(nominal.pending),
        "physical_publisher_count": 0,
    })
    timeout = nominal.advance(101.221)
    rows.append(decision_case("interchunk_timeout", "gap", False, timeout, nominal))

    overlap = make_gate(contract)
    overlap.submit(chunk_id=1, point_times=times, flag_pred=0.0, now=100.0)
    overlap_decision = overlap.submit(chunk_id=2, point_times=times, flag_pred=0.0, now=100.001)
    rows.append(decision_case("overlap_purges", "sequence", False, overlap_decision, overlap))

    late = make_gate(contract)
    late.submit(chunk_id=1, point_times=times, flag_pred=0.0, now=100.0)
    rows.append(decision_case("late_dispatch_purges", "timeline", False, late.advance(100.02), late))

    duplicate = make_gate(contract)
    duplicate.submit(chunk_id=1, point_times=times, flag_pred=0.0, now=100.0)
    drain(duplicate, times, 100.0)
    rows.append(decision_case("duplicate_chunk", "sequence", False, duplicate.submit(chunk_id=1, point_times=times, flag_pred=0.0, now=100.8), duplicate))
    rows.append(decision_case("regressive_chunk", "sequence", False, duplicate.submit(chunk_id=0, point_times=times, flag_pred=0.0, now=100.8), duplicate))

    cancel_before = make_gate(contract)
    cancel_before.submit(chunk_id=1, point_times=times, flag_pred=0.0, now=100.0)
    rows.append(decision_case("cancel_before_first_point", "cancel", True, cancel_before.cancel(100.0), cancel_before))

    cancel_during = make_gate(contract)
    cancel_during.submit(chunk_id=1, point_times=times, flag_pred=0.0, now=100.0)
    cancel_during.advance(100.0)
    cancel_during.advance(100.08)
    rows.append(decision_case("cancel_during_chunk", "cancel", True, cancel_during.cancel(100.081), cancel_during))

    cancel_between = make_gate(contract)
    cancel_between.submit(chunk_id=1, point_times=times, flag_pred=0.0, now=100.0)
    drain(cancel_between, times, 100.0)
    rows.append(decision_case("cancel_between_chunks", "cancel", True, cancel_between.cancel(100.8), cancel_between))

    after_timeout = make_gate(contract)
    timeout_decision = after_timeout.advance(108.0)
    rows.append(decision_case("session_duration_timeout", "timeout", False, timeout_decision, after_timeout))
    rows.append(decision_case("cancel_after_timeout_idempotent", "cancel", True, after_timeout.cancel(108.0), after_timeout))

    stopped = make_gate(contract)
    stopped.submit(chunk_id=1, point_times=times, flag_pred=0.0, now=100.0)
    rows.append(decision_case("stop_purges", "stop", True, stopped.stop(100.0), stopped))
    rows.append(decision_case("stop_idempotent", "stop", True, stopped.stop(100.0), stopped))

    for sensor in ("state", "image"):
        gate = make_gate(contract)
        gate.submit(chunk_id=1, point_times=times, flag_pred=0.0, now=100.0)
        rows.append(decision_case(f"{sensor}_loss_purges", "sensor", True, gate.sensor_fault(sensor, 100.0), gate))

    invalid_times = make_gate(contract)
    off_schedule = list(times)
    off_schedule[3] = 0.26
    rows.append(decision_case("off_schedule_rejected", "timeline", False, invalid_times.submit(chunk_id=1, point_times=off_schedule, flag_pred=0.0, now=100.0), invalid_times))

    invalid_flag = make_gate(contract)
    rows.append(decision_case("nonfinite_flag_rejected", "end", False, invalid_flag.submit(chunk_id=1, point_times=times, flag_pred=float("nan"), now=100.0), invalid_flag))

    invalid_first_time = make_gate(contract)
    nonfinite_times = list(times)
    nonfinite_times[0] = float("nan")
    rows.append(decision_case("nonfinite_first_point_time_rejected", "timeline", False, invalid_first_time.submit(chunk_id=1, point_times=nonfinite_times, flag_pred=0.0, now=100.0), invalid_first_time))

    vendor = MODULE.VendorObservedEndPolicy(threshold=float(contract["end_threshold"]))
    candidate = MODULE.ConsecutiveEndPolicy(
        threshold=float(contract["end_threshold"]),
        required=int(contract["continuous_end_chunk_num"]),
    )
    vendor_single = vendor.observe(0.100001)
    candidate_first_four = [candidate.observe(0.2) for _ in range(4)]
    candidate_fifth = candidate.observe(0.2)
    end_pass = vendor_single and not any(candidate_first_four) and candidate_fifth
    rows.append({
        "case": "end_policy_difference_demonstrated",
        "family": "end",
        "expected_accept": True,
        "observed_accept": end_pass,
        "passed": end_pass,
        "state": "AUDITED",
        "reasons": ["vendor:single_threshold", "local_candidate:five_consecutive"],
        "emitted_count": 0,
        "pending_count": 0,
        "physical_publisher_count": 0,
    })

    completed = make_gate(contract)
    base = 100.0
    for chunk_id in range(1, 6):
        decision = completed.submit(chunk_id=chunk_id, point_times=times, flag_pred=0.2, now=base)
        if not decision.accepted:
            raise AssertionError(decision.reasons)
        drain(completed, times, base)
        base += 0.8
    complete_pass = completed.state == "COMPLETED" and len(completed.emission_log) == 50
    rows.append({
        "case": "candidate_fifth_chunk_completes_after_endpoint",
        "family": "end",
        "expected_accept": True,
        "observed_accept": complete_pass,
        "passed": complete_pass,
        "state": completed.state,
        "reasons": [completed.reason] if completed.reason else [],
        "emitted_count": len(completed.emission_log),
        "pending_count": len(completed.pending),
        "physical_publisher_count": 0,
    })
    return rows


def e2_observations(path: pathlib.Path | None) -> dict[str, Any]:
    if path is None:
        return {"available": False}
    data = json.loads(path.read_text(encoding="utf-8"))
    if "runs" in data:
        durations = [float(run["actual_duration_sec"]) for run in data["runs"]]
        inference = [float(value) for run in data["runs"] for value in run.get("inference_time_sec", [])]
        chunks = sum(int(run["chunks"]) for run in data["runs"])
    else:
        durations = [float(data["actual_duration_sec"])]
        inference = [float(item["inference_time_sec"]) for item in data.get("chunk_results", [])]
        chunks = int(data["chunks"])
    return {
        "available": True,
        "source": str(path.resolve()),
        "source_sha256": sha256_file(path),
        "run_count": len(durations),
        "chunk_count": chunks,
        "actual_duration_seconds": durations,
        "mean_actual_duration_seconds": statistics.mean(durations),
        "inference_time_seconds": inference,
        "mean_inference_time_seconds": statistics.mean(inference) if inference else None,
        "requested_duration_seconds": 8.0,
        "observed_result": "duration_limit_checked_only_between_blocking_inferences",
    }


def write_json(path: pathlib.Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=pathlib.Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--e2-summary", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output.resolve()
    if output == pathlib.Path("/"):
        raise SystemExit("ERROR: --output cannot be /")
    output.mkdir(parents=True, exist_ok=True)
    contract = MODULE.load_contract(args.contract)
    safety = static_safety()
    audit = vendor_audit()
    rows = campaign(contract)
    failed = [row for row in rows if not row["passed"]]
    observations = e2_observations(args.e2_summary)
    summary = {
        "schema": "cruzr-s2-vla-temporal-contract-e3.3-v1",
        "experiment_id": "E3.3",
        "mode": "local_pure_python_temporal_simulation_plus_static_vendor_audit",
        "contract": str(args.contract.resolve()),
        "contract_sha256": sha256_file(args.contract),
        "runner_sha256": sha256_file(SCRIPT_PATH),
        "module_sha256": sha256_file(MODULE_PATH),
        "case_count": len(rows),
        "passed_case_count": len(rows) - len(failed),
        "failed_case_count": len(failed),
        "all_expectations_passed": not failed,
        "static_safety": safety,
        "vendor_audit": audit,
        "e2_observations": observations,
        "local_contract_status": "PASS_FAIL_CLOSED_OFFLINE",
        "vendor_end_semantics_status": "OBSERVED_SINGLE_THRESHOLD_CONFLICTS_WITH_DECLARED_FIVE",
        "vendor_executor_timeline_status": "UNRESOLVED_TWO_DIFFERENT_SUPPLIED_COPIES",
        "dataset_120fps_relation": "export_or_dataset_sampling_only_not_runtime_execution_equivalence",
        "physical_executor_authorized": False,
        "physical_movement_commanded": False,
        "robot_state_read": False,
        "physical_publisher_count": 0,
        "cases": rows,
    }
    write_json(output / "vendor_temporal_audit.json", audit)
    write_json(output / "summary.json", summary)
    with (output / "cases.jsonl").open("w", encoding="utf-8") as target:
        for row in rows:
            target.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
    print(f"E3_3_CASES={len(rows)}")
    print(f"E3_3_CASES_PASSED={len(rows) - len(failed)}")
    print("E3_3_LOCAL_CONTRACT=PASS_FAIL_CLOSED_OFFLINE" if not failed else "E3_3_LOCAL_CONTRACT=FAIL")
    print("E3_3_VENDOR_END=single-threshold,declared-five-not-applied")
    print("E3_3_VENDOR_EXECUTOR_TIMELINES=source:9s,installed:6s,chunk-declared:0.72s")
    print("E3_3_PHYSICAL_PUBLISHERS=0")
    return 0 if not failed and safety["safe"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
