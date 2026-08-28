#!/usr/bin/env python3
"""Execute the E3.2 invalid-message campaign against the pure VLA sink."""

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
RUNTIME_DIR = SCRIPT_PATH.parent / "runtime"
MODULE_PATH = RUNTIME_DIR / "vla_executor_sink.py"
DEFAULT_PROFILE = RUNTIME_DIR / "cruzr_s2_vla_profile.json"
RUNTIME_ID = "cruzr-s2-vla-sink-e3.2-v1"
CHECKPOINT_ID = "checkpoint-40000-read-only-contract"
CLIENT_ID = "e3.2-primary"
NOW = 1000.0

SPEC = importlib.util.spec_from_file_location("vla_executor_sink", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {MODULE_PATH}")
SINK_MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SINK_MODULE
SPEC.loader.exec_module(SINK_MODULE)


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def command_sha(command: dict[str, Any] | None) -> str | None:
    if command is None:
        return None
    encoded = json.dumps(command, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def static_safety_report() -> dict[str, Any]:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports: set[str] = set()
    names: set[str] = set()
    called_attributes: set[str] = set()
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
            called_attributes.add(node.func.attr)
    forbidden_imports = {
        "action_msgs",
        "mc_command_msgs",
        "mc_state_msgs",
        "rclpy",
        "requests",
        "rosa",
        "socket",
        "subprocess",
        "urllib",
        "vla_msgs",
    }
    publisher_calls = {"create_client", "create_publisher", "publish", "send_goal_async"}
    forbidden_symbols = {"RobotCommand", "Gr00tMotionChunk"}
    return {
        "schema": "cruzr-s2-vla-sink-static-safety-v1",
        "module": str(MODULE_PATH),
        "module_sha256": sha256_file(MODULE_PATH),
        "forbidden_imports_found": sorted(imports & forbidden_imports),
        "publisher_or_action_calls_found": sorted(called_attributes & publisher_calls),
        "forbidden_symbols_found": sorted(names & forbidden_symbols),
        "physical_command_topic_literal_present": "/mc/sdk/robot_command" in source,
        "network_imports_found": sorted(imports & {"requests", "socket", "urllib"}),
        "subprocess_imported": "subprocess" in imports,
        "safe": not (
            imports & forbidden_imports
            or called_attributes & publisher_calls
            or names & forbidden_symbols
            or "/mc/sdk/robot_command" in source
        ),
    }


def make_sink(profile: dict[str, Any], axis_profile: str, fixture: str, *, deadman: bool = True):
    sink = SINK_MODULE.VlaExecutorSink(
        profile=profile,
        axis_profile=axis_profile,
        fixture=fixture,
        runtime_id=RUNTIME_ID,
        checkpoint_id=CHECKPOINT_ID,
    )
    acquired = sink.acquire_client(CLIENT_ID)
    if not acquired.accepted:
        raise AssertionError(acquired.reasons)
    if deadman:
        refreshed = sink.refresh_deadman(CLIENT_ID, NOW)
        if not refreshed.accepted:
            raise AssertionError(refreshed.reasons)
    return sink


def result_row(
    *,
    name: str,
    family: str,
    expected_accept: bool,
    decision: Any,
) -> dict[str, Any]:
    observed_accept = bool(decision.accepted)
    return {
        "case": name,
        "family": family,
        "expected_accept": expected_accept,
        "observed_accept": observed_accept,
        "passed": observed_accept is expected_accept,
        "event": decision.event,
        "reasons": list(decision.reasons),
        "serialized_sink_command_sha256": command_sha(decision.command),
        "physical_publisher_count": 0,
    }


def mutate_case(
    profile: dict[str, Any],
    axis_profile: str,
    fixture: str,
    name: str,
    family: str,
    mutation: Callable[[dict[str, Any], Any], None],
) -> dict[str, Any]:
    sink = make_sink(profile, axis_profile, fixture)
    message = SINK_MODULE.valid_message(sink, chunk_id=10, now=NOW)
    mutation(message, sink)
    decision = sink.submit(message, now=NOW)
    return result_row(
        name=name,
        family=family,
        expected_accept=False,
        decision=decision,
    )


def run_campaign(profile: dict[str, Any], axis_profile: str, fixture: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    sink = make_sink(profile, axis_profile, fixture)
    first = sink.submit(SINK_MODULE.valid_message(sink, chunk_id=10, now=NOW), now=NOW)
    rows.append(result_row(name="valid_chunk_10", family="valid", expected_accept=True, decision=first))
    second = sink.submit(SINK_MODULE.valid_message(sink, chunk_id=11, now=NOW), now=NOW)
    rows.append(result_row(name="valid_chunk_11", family="valid", expected_accept=True, decision=second))

    simple_mutations: list[tuple[str, str, Callable[[dict[str, Any], Any], None]]] = [
        ("runtime_id_mismatch", "identity", lambda message, _sink: message.__setitem__("runtime_id", "wrong")),
        ("checkpoint_id_mismatch", "identity", lambda message, _sink: message.__setitem__("checkpoint_id", "wrong")),
        ("task_id_invalid", "identity", lambda message, _sink: message.__setitem__("task_id", 99)),
        ("axis_profile_mismatch", "identity", lambda message, _sink: message.__setitem__("axis_profile", "P14_A")),
        ("fixture_mismatch", "identity", lambda message, _sink: message.__setitem__("fixture", "middle" if fixture == "low" else "low")),
        ("client_mismatch", "session", lambda message, _sink: message.__setitem__("client_id", "e3.2-second")),
        ("chunk_id_invalid", "sequence", lambda message, _sink: message.__setitem__("chunk_id", -1)),
        ("joint_order_permuted", "schema", lambda message, _sink: message["joint_names"].__setitem__(slice(0, 2), reversed(message["joint_names"][:2]))),
        ("state_joint_order_permuted", "state", lambda message, _sink: message["state_joint_names"].__setitem__(slice(0, 2), reversed(message["state_joint_names"][:2]))),
        ("state_joint_missing", "state", lambda message, _sink: message["state_joint_names"].pop()),
        ("horizon_wrong", "schema", lambda message, _sink: message["points"].pop()),
        ("action_dimension_wrong", "schema", lambda message, _sink: message["points"][3]["positions"].pop()),
        ("state_dimension_wrong", "state", lambda message, _sink: message["state_positions"].pop()),
        ("action_nan", "finiteness", lambda message, _sink: message["points"][0]["positions"].__setitem__(0, float("nan"))),
        ("action_inf", "finiteness", lambda message, _sink: message["points"][0]["positions"].__setitem__(1, float("inf"))),
        ("state_inf", "finiteness", lambda message, _sink: message["state_positions"].__setitem__(0, float("inf"))),
        ("chunk_stale", "freshness", lambda message, _sink: message.__setitem__("sent_monotonic", NOW - 1.0)),
        ("chunk_from_future", "freshness", lambda message, _sink: message.__setitem__("sent_monotonic", NOW + 0.10)),
        ("state_stale", "freshness", lambda message, _sink: message.__setitem__("state_monotonic", NOW - 1.01)),
        ("image_stale", "freshness", lambda message, _sink: message.__setitem__("image_monotonic", NOW - 1.01)),
        ("point_time_not_monotonic", "timeline", lambda message, _sink: message["points"][2].__setitem__("time_from_start", message["points"][1]["time_from_start"])),
        ("point_time_off_schedule", "timeline", lambda message, _sink: message["points"][1].__setitem__("time_from_start", 0.12)),
        ("range_exceeded", "limits", lambda message, sink: message["points"][0]["positions"].__setitem__(0, float(sink.profile["upper_boundary"][0]) + float(sink.profile["range_tolerance"]) + 0.01)),
        ("first_point_delta_exceeded", "limits", lambda message, sink: message["points"][0]["positions"].__setitem__(0, message["state_positions"][0] + float(sink.profile["max_first_point_delta"][0]) + 0.01)),
        ("interpoint_speed_exceeded", "limits", lambda message, _sink: message["points"][1]["positions"].__setitem__(0, message["points"][0]["positions"][0] + 0.11)),
    ]
    for name, family, mutation in simple_mutations:
        rows.append(mutate_case(profile, axis_profile, fixture, name, family, mutation))

    duplicate_sink = make_sink(profile, axis_profile, fixture)
    accepted = duplicate_sink.submit(
        SINK_MODULE.valid_message(duplicate_sink, chunk_id=10, now=NOW), now=NOW
    )
    if not accepted.accepted:
        raise AssertionError(accepted.reasons)
    duplicate = duplicate_sink.submit(
        SINK_MODULE.valid_message(duplicate_sink, chunk_id=10, now=NOW), now=NOW
    )
    rows.append(result_row(name="chunk_duplicate", family="sequence", expected_accept=False, decision=duplicate))
    regressive = duplicate_sink.submit(
        SINK_MODULE.valid_message(duplicate_sink, chunk_id=9, now=NOW), now=NOW
    )
    rows.append(result_row(name="chunk_regressive", family="sequence", expected_accept=False, decision=regressive))

    canceled_sink = make_sink(profile, axis_profile, fixture)
    cancel_one = canceled_sink.cancel(CLIENT_ID)
    cancel_two = canceled_sink.cancel(CLIENT_ID)
    if not cancel_one.accepted or not cancel_two.accepted:
        raise AssertionError("cancel must be idempotent")
    canceled = canceled_sink.submit(
        SINK_MODULE.valid_message(canceled_sink, chunk_id=10, now=NOW), now=NOW
    )
    rows.append(result_row(name="submit_after_cancel", family="control", expected_accept=False, decision=canceled))

    stopped_sink = make_sink(profile, axis_profile, fixture)
    stop_one = stopped_sink.stop()
    stop_two = stopped_sink.stop()
    if not stop_one.accepted or not stop_two.accepted:
        raise AssertionError("stop must be idempotent")
    stopped = stopped_sink.submit(
        SINK_MODULE.valid_message(stopped_sink, chunk_id=10, now=NOW), now=NOW
    )
    rows.append(result_row(name="submit_after_stop", family="control", expected_accept=False, decision=stopped))

    no_deadman_sink = make_sink(profile, axis_profile, fixture, deadman=False)
    no_deadman = no_deadman_sink.submit(
        SINK_MODULE.valid_message(no_deadman_sink, chunk_id=10, now=NOW), now=NOW
    )
    rows.append(result_row(name="deadman_not_active", family="control", expected_accept=False, decision=no_deadman))

    timeout_sink = make_sink(profile, axis_profile, fixture)
    timeout_decision = timeout_sink.poll(NOW + 0.51)
    rows.append(result_row(name="deadman_timeout", family="control", expected_accept=False, decision=timeout_decision))

    double_client_sink = make_sink(profile, axis_profile, fixture)
    double_client = double_client_sink.acquire_client("e3.2-second")
    rows.append(result_row(name="double_client", family="session", expected_accept=False, decision=double_client))
    return rows


def write_json(path: pathlib.Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--axis-profile", choices=tuple(SINK_MODULE.AXIS_PROFILES), required=True)
    parser.add_argument("--fixture", choices=SINK_MODULE.VALID_FIXTURES, required=True)
    parser.add_argument("--fault-suite", choices=("all",), required=True)
    parser.add_argument("--profile", type=pathlib.Path, default=DEFAULT_PROFILE)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output.resolve()
    if output == pathlib.Path("/"):
        raise SystemExit("ERROR: --output cannot be /")
    output.mkdir(parents=True, exist_ok=True)
    profile = SINK_MODULE.load_profile(args.profile)
    safety = static_safety_report()
    if not safety["safe"]:
        raise SystemExit(f"ERROR: sink static safety failed: {safety}")
    rows = run_campaign(profile, args.axis_profile, args.fixture)
    invalid = [row for row in rows if not row["expected_accept"]]
    valid = [row for row in rows if row["expected_accept"]]
    failed = [row for row in rows if not row["passed"]]
    summary = {
        "schema": "cruzr-s2-vla-executor-sink-e3.2-v1",
        "experiment_id": "E3.2",
        "mode": "local_pure_python_sink_no_ros_no_hardware",
        "axis_profile": args.axis_profile,
        "fixture": args.fixture,
        "fixture_state_semantics": "synthetic_profile_midpoint_not_physical_vla_ready",
        "runtime_id": RUNTIME_ID,
        "checkpoint_id": CHECKPOINT_ID,
        "profile": str(args.profile.resolve()),
        "profile_sha256": sha256_file(args.profile),
        "runner_sha256": sha256_file(SCRIPT_PATH),
        "sink_module_sha256": sha256_file(MODULE_PATH),
        "total_case_count": len(rows),
        "valid_case_count": len(valid),
        "valid_case_accepted_count": sum(row["observed_accept"] for row in valid),
        "invalid_case_count": len(invalid),
        "invalid_case_rejected_count": sum(not row["observed_accept"] for row in invalid),
        "failed_expectation_count": len(failed),
        "all_expectations_passed": not failed,
        "invalid_rejection_rate": (
            sum(not row["observed_accept"] for row in invalid) / len(invalid)
        ),
        "static_safety": safety,
        "sink_physical_publisher_count": 0,
        "sink_network_calls": 0,
        "robot_state_read": False,
        "physical_movement_commanded": False,
        "acceleration_limit_status": "NOT_TESTED_NO_CERTIFIED_LIMIT_IN_PROFILE",
        "physical_executor_authorized": False,
        "next_experiment_authorized": "E3.3_OFFLINE_TEMPORAL_CONTRACT_ONLY",
        "cases": rows,
    }
    write_json(output / "static_safety.json", safety)
    with (output / "cases.jsonl").open("w", encoding="utf-8") as destination:
        for row in rows:
            destination.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
    write_json(output / "summary.json", summary)
    for row in rows:
        label = "PASS" if row["passed"] else "FAIL"
        print(
            f"E3_2_CASE={row['case']},expected:{int(row['expected_accept'])},"
            f"observed:{int(row['observed_accept'])},result:{label}"
        )
    print(
        "E3_2_SINK_COMPLETE="
        f"valid:{len(valid)},invalid:{len(invalid)},failed:{len(failed)},publishers:0"
    )
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
