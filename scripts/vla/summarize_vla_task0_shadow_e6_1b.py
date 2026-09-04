#!/usr/bin/env python3
"""Fail-closed audit of one or five E6.1B task-0 shadow repetitions."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def distance(values: list[float], reference: list[float]) -> float:
    if len(values) != 20:
        raise ValueError(f"expected 20D state, got {len(values)}")
    numeric = [float(value) for value in values]
    if not all(math.isfinite(value) for value in numeric):
        raise ValueError("state contains non-finite values")
    return max(abs(value - target) for value, target in zip(numeric, reference, strict=True))


def audit_run(run_dir: Path, contract: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    exported = run_dir / "exported"
    result = (run_dir / "actual_result.yaml").read_text(encoding="utf-8")
    required_markers = (
        f"shadow_profile: {profile['profile_file']}",
        "physical_movement_commanded: false",
        "command_publishers: 0",
    )
    for marker in required_markers:
        if marker not in result:
            raise ValueError(f"{run_dir.name}: missing result marker: {marker}")
    status = (exported / "status_after_export.log").read_text(encoding="utf-8")
    for marker in (
        "INFERENCE_CONTAINER=exited",
        "CONTROL_CONTAINER=exited",
        "COMMAND_PATH_SAFE=publishers:0",
    ):
        if marker not in status:
            raise ValueError(f"{run_dir.name}: missing final STOP marker: {marker}")

    lines = [line for line in (exported / "shadow.jsonl").read_text(encoding="utf-8").splitlines() if line]
    chunks = [json.loads(line) for line in lines]
    minimum_chunks = int(contract["shadow_gate"]["accepted_chunks_required_per_repetition"])
    if len(chunks) < minimum_chunks:
        raise ValueError(f"{run_dir.name}: no qualifying shadow chunk")
    if any(not chunk.get("accepted") or chunk.get("reasons") for chunk in chunks):
        raise ValueError(f"{run_dir.name}: rejected shadow chunk present")

    reference = [float(value) for value in contract["candidate"]["entry_state_20d_rad"]]
    names = contract["candidate"]["joint_order"]
    entry_limit = float(contract["entry_gate"]["maximum_chebyshev_distance_to_frozen_frame_rad"])
    delta_limit = float(contract["shadow_gate"]["maximum_p14_first_point_delta_rad"])
    max_entry_distance = 0.0
    max_first_delta = 0.0
    for chunk in chunks:
        metrics = chunk["metrics"]
        if metrics.get("state_defaulted_joints"):
            raise ValueError(f"{run_dir.name}: shadow used defaulted state axes")
        state_map = metrics.get("state_positions", {})
        if set(state_map) != set(names):
            raise ValueError(f"{run_dir.name}: shadow state axes differ from frozen 20D contract")
        current_distance = distance([state_map[name] for name in names], reference)
        max_entry_distance = max(max_entry_distance, current_distance)
        if current_distance > entry_limit:
            raise ValueError(f"{run_dir.name}: chunk state left frozen ENTRY")
        maximum = metrics.get("maximum_commanded_first_point_delta", {})
        current_delta = float(maximum.get("absolute_delta", math.inf))
        max_first_delta = max(max_first_delta, current_delta)
        if current_delta > delta_limit:
            raise ValueError(f"{run_dir.name}: first P14 delta exceeded limit")

    input_dir = exported / "inputs"
    input_json = sorted(input_dir.glob("input-*.json"))
    if len(input_json) < len(chunks):
        raise ValueError(f"{run_dir.name}: fewer exact input records than chunks")
    seen_indices: set[int] = set()
    max_input_distance = 0.0
    for metadata_path in input_json:
        metadata = load_object(metadata_path)
        if metadata.get("schema") != "cruzr-s2-vla-shadow-input-evidence-v1":
            raise ValueError(f"{metadata_path}: unexpected schema")
        if int(metadata.get("task_id", -1)) != 0:
            raise ValueError(f"{metadata_path}: input was not task 0")
        index = int(metadata["input_index"])
        if index in seen_indices:
            raise ValueError(f"{run_dir.name}: duplicate input index {index}")
        seen_indices.add(index)
        image = metadata["image"]
        image_path = input_dir / image["png_file"]
        if not image_path.is_file() or sha256(image_path) != image["png_sha256"]:
            raise ValueError(f"{metadata_path}: image hash mismatch")
        state = metadata["state"]
        if state.get("joint_names") != names:
            raise ValueError(f"{metadata_path}: input state order differs")
        current_distance = distance(state["positions_rad"], reference)
        max_input_distance = max(max_input_distance, current_distance)
        if current_distance > entry_limit:
            raise ValueError(f"{metadata_path}: synchronized input left frozen ENTRY")

    return {
        "run_dir": str(run_dir.resolve()),
        "chunks": len(chunks),
        "accepted": len(chunks),
        "rejected": 0,
        "input_records": len(input_json),
        "maximum_chunk_entry_distance_rad": max_entry_distance,
        "maximum_input_entry_distance_rad": max_input_distance,
        "maximum_p14_first_point_delta_rad": max_first_delta,
        "containers_stopped": True,
        "command_publishers_after_stop": 0,
        "physical_movement_commanded": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    contract = load_object(args.contract)
    profile = load_object(args.profile)
    if contract.get("schema") != "cruzr-s2-vla-task0-entry-recovery-e6.1b-v1":
        raise ValueError("unexpected E6.1B contract")
    expected_profile = "cruzr_s2_vla_task0_p14_shadow_e6_1b.json"
    if args.profile.name != expected_profile:
        raise ValueError("unexpected E6.1B profile filename")
    profile = {**profile, "profile_file": expected_profile}
    expected_runs = int(contract["shadow_gate"]["independent_repetitions"])
    if len(args.run_dir) not in (1, expected_runs):
        raise ValueError(f"provide one repetition or exactly {expected_runs}")
    if len({path.resolve() for path in args.run_dir}) != len(args.run_dir):
        raise ValueError("repetition directories must be independent")
    repetitions = [audit_run(path, contract, profile) for path in args.run_dir]
    complete = len(repetitions) == expected_runs
    report = {
        "schema": "cruzr-s2-vla-task0-five-shadow-e6.1b-v1",
        "status": "PASS_FIVE_LIVE_SHADOW" if complete else "PASS_SINGLE_LIVE_SHADOW",
        "task_id": 0,
        "scenario": "SUPPORTED_LOW",
        "candidate_episode": "episode_000040",
        "candidate_frame": 0,
        "profile": profile["profile"],
        "repetitions_expected": expected_runs,
        "repetitions_validated": len(repetitions),
        "repetitions": repetitions,
        "validator_modified_or_projected_targets": False,
        "physical_command_publishers_created": 0,
        "physical_movement_commanded": False,
        "physical_execution_authorized": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"E6.1B_SHADOW_REPETITIONS_VALIDATED={len(repetitions)}/{expected_runs}")
    print(f"E6.1B_SHADOW_STATUS={report['status']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=__import__("sys").stderr)
        raise SystemExit(2) from exc
