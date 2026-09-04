#!/usr/bin/env python3
"""Offline regression tests for the E6.0Z task-entry gate."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile


NAMES = [f"joint_{index}" for index in range(20)]


def run_case(checker: pathlib.Path, root: pathlib.Path, scenario: str, state: list[float]):
    state_path = root / f"state-{scenario}.json"
    state_path.write_text(json.dumps({"positions": state}), encoding="utf-8")
    return subprocess.run(
        [
            sys.executable,
            str(checker),
            "--dataset-report",
            str(root / "report.json"),
            "--contract",
            str(root / "contract.json"),
            "--task-id",
            "0",
            "--scenario",
            scenario,
            "--state-json",
            str(state_path),
        ],
        check=False,
        text=True,
        capture_output=True,
    )


def main() -> int:
    checker = pathlib.Path(__file__).with_name("check_vla_task_entry_state.py")
    contract_source = pathlib.Path(__file__).with_name("runtime") / (
        "cruzr_s2_vla_task_entry_contract_e6_0z.json"
    )
    with tempfile.TemporaryDirectory(prefix="e6_0z_") as temporary:
        root = pathlib.Path(temporary)
        contract = json.loads(contract_source.read_text(encoding="utf-8"))
        report = {
            "schema": "cruzr-s2-vla-dataset-entry-states-v1",
            "joint_names": NAMES,
            "frame_zero_records": [
                {
                    "episode": "episode_000001",
                    "task": 0,
                    "state": [0.0] * 20,
                    "action": [0.0] * 20,
                    "action_minus_state": [0.0] * 20,
                }
            ],
            "tasks": {
                "0": {
                    "frame_zero_state": {
                        name: {"min": -0.02, "max": 0.02} for name in NAMES
                    }
                }
            },
        }
        (root / "contract.json").write_text(json.dumps(contract), encoding="utf-8")
        (root / "report.json").write_text(json.dumps(report), encoding="utf-8")

        accepted = run_case(checker, root, "SUPPORTED_LOW", [0.001] * 20)
        wrong_scene = run_case(checker, root, "NO_BOX_READY", [0.001] * 20)
        wrong_state = run_case(checker, root, "SUPPORTED_LOW", [0.0] * 19 + [0.5])
        assert accepted.returncode == 0, accepted.stderr
        assert json.loads(accepted.stdout)["entry_qualified_for_fresh_shadow"] is True
        assert wrong_scene.returncode == 3
        assert "task_scene_mismatch" in json.loads(wrong_scene.stdout)["rejection_reasons"]
        assert wrong_state.returncode == 3
        rejected = json.loads(wrong_state.stdout)
        assert "state_outside_same_task_observed_bounds" in rejected["rejection_reasons"]
        assert rejected["physical_execution_authorized"] is False

    print("E6.0Z_ENTRY_GATE_CASES=3")
    print("E6.0Z_FAILED_EXPECTATIONS=0")
    print("E6.0Z_ROS_IMPORTED=0")
    print("E6.0Z_ROBOT_ACCESSED=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
