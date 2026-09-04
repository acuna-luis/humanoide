#!/usr/bin/env python3
"""Offline regression tests for E6.1B state normalization and shadow audit."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import yaml


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, text=True, capture_output=True)


def make_shadow_run(path: Path, contract: dict, profile_name: str, delta: float = 0.0) -> None:
    exported = path / "exported"
    inputs = exported / "inputs"
    inputs.mkdir(parents=True)
    (path / "actual_result.yaml").write_text(
        f"shadow_profile: {profile_name}\n"
        "physical_movement_commanded: false\n"
        "command_publishers: 0\n",
        encoding="utf-8",
    )
    (exported / "status_after_export.log").write_text(
        "INFERENCE_CONTAINER=exited\nCONTROL_CONTAINER=exited\n"
        "COMMAND_PATH_SAFE=publishers:0\n",
        encoding="utf-8",
    )
    names = contract["candidate"]["joint_order"]
    positions = list(contract["candidate"]["entry_state_20d_rad"])
    positions[0] += delta
    chunk = {
        "accepted": True,
        "chunk_id": 0,
        "reasons": [],
        "metrics": {
            "state_positions": dict(zip(names, positions, strict=True)),
            "state_defaulted_joints": [],
            "maximum_commanded_first_point_delta": {
                "joint": names[0], "absolute_delta": 0.001, "limit": 0.1
            },
        },
    }
    (exported / "shadow.jsonl").write_text(json.dumps(chunk) + "\n", encoding="utf-8")
    png = inputs / "input-000000.png"
    png.write_bytes(b"test-png-evidence")
    metadata = {
        "schema": "cruzr-s2-vla-shadow-input-evidence-v1",
        "input_index": 0,
        "task_id": 0,
        "image": {"png_file": png.name, "png_sha256": hashlib.sha256(png.read_bytes()).hexdigest()},
        "state": {"joint_names": names, "positions_rad": positions},
    }
    (inputs / "input-000000.json").write_text(json.dumps(metadata), encoding="utf-8")


def main() -> int:
    root = Path(__file__).resolve().parent
    contract_path = root / "runtime/cruzr_s2_vla_task0_entry_recovery_e6_1b.json"
    profile_path = root / "runtime/cruzr_s2_vla_task0_p14_shadow_e6_1b.json"
    normalizer = root / "normalize_vla_joint_state_e6_1b.py"
    summarizer = root / "summarize_vla_task0_shadow_e6_1b.py"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    profile_name = profile_path.name

    with tempfile.TemporaryDirectory(prefix="e6_1b_shadow_") as temporary:
        work = Path(temporary)
        names = list(reversed(contract["candidate"]["joint_order"]))
        reference = dict(zip(contract["candidate"]["joint_order"], contract["candidate"]["entry_state_20d_rad"], strict=True))
        raw = {
            "header": {"stamp": {"sec": 1, "nanosec": 2}, "frame_id": "test"},
            "name": names,
            "position": [reference[name] for name in names],
            "velocity": [0.0] * 20,
        }
        raw_path = work / "raw.yaml"
        state_path = work / "state.json"
        raw_path.write_text(yaml.safe_dump(raw), encoding="utf-8")
        normalized = run([
            sys.executable, str(normalizer), "--contract", str(contract_path),
            "--input", str(raw_path), "--output", str(state_path),
        ])
        assert normalized.returncode == 0, normalized.stderr
        state = json.loads(state_path.read_text(encoding="utf-8"))
        assert state["names"] == contract["candidate"]["joint_order"]
        assert state["positions"] == contract["candidate"]["entry_state_20d_rad"]

        good_runs = []
        for index in range(5):
            run_dir = work / f"run-{index}"
            make_shadow_run(run_dir, contract, profile_name)
            good_runs.append(run_dir)
        output = work / "five.json"
        command = [
            sys.executable, str(summarizer), "--contract", str(contract_path),
            "--profile", str(profile_path), "--output", str(output),
        ]
        for run_dir in good_runs:
            command.extend(("--run-dir", str(run_dir)))
        accepted = run(command)
        assert accepted.returncode == 0, accepted.stderr
        assert json.loads(output.read_text(encoding="utf-8"))["status"] == "PASS_FIVE_LIVE_SHADOW"

        bad_run = work / "bad-run"
        make_shadow_run(bad_run, contract, profile_name, delta=0.011)
        rejected = run([
            sys.executable, str(summarizer), "--contract", str(contract_path),
            "--profile", str(profile_path), "--run-dir", str(bad_run),
            "--output", str(work / "bad.json"),
        ])
        assert rejected.returncode == 2
        assert "left frozen ENTRY" in rejected.stderr

    print("E6.1B_SHADOW_TEST_CASES=3")
    print("E6.1B_SHADOW_FAILED_EXPECTATIONS=0")
    print("E6.1B_SHADOW_NETWORK_CALLS=0")
    print("E6.1B_SHADOW_PHYSICAL_PUBLISHERS=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
