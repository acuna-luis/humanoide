#!/usr/bin/env python3
"""Offline regression tests for the exact E6.1B fixture/ENTRY gate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    root = Path(__file__).resolve().parent
    checker = root / "check_vla_task0_entry_e6_1b.py"
    contract_path = root / "runtime/cruzr_s2_vla_task0_entry_recovery_e6_1b.json"
    dataset_report = Path(
        "/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/"
        "20260904T094803_E6.0Z/dataset-entry-states.json"
    )
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="e6_1b_gate_") as temporary:
        work = Path(temporary)
        photo = work / "fixture.jpg"
        photo.write_bytes(b"fixture-evidence")
        manifest = {
            "schema": "cruzr-s2-vla-supported-low-fixture-e6.1b-v1",
            "scenario": "SUPPORTED_LOW",
            "fixture_id": "TEST_ONLY",
            "measured_at": "2026-09-04T12:00:00+02:00",
            "measurement_uncertainty_m": 0.002,
            "support": {
                "surface_height_floor_m": 0.7746,
                "width_m": 0.75,
                "depth_m": 0.5,
                "thickness_m": 0.04,
                "rigid": True,
                "stable": True,
                "locked": True,
            },
            "box": {
                "box_id": "B0",
                "lwh_m": [0.603, 0.397, 0.217],
                "empty": True,
                "open_top": True,
                "material_family": "rigid_plastic",
                "color_family": "gray",
                "supported_and_stable": True,
            },
            "evidence_files": [{"path": photo.name, "sha256": digest(photo)}],
            "physical_fixture_frozen": True,
            "movement_authorized": False,
        }
        state = {
            "observed_at_unix": time.time(),
            "names": contract["candidate"]["joint_order"],
            "positions": contract["candidate"]["entry_state_20d_rad"],
            "velocities": [0.0] * 20,
        }
        manifest_path = work / "fixture.json"
        state_path = work / "state.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        state_path.write_text(json.dumps(state), encoding="utf-8")

        base = [
            sys.executable,
            str(checker),
            "--contract", str(contract_path),
            "--dataset-report", str(dataset_report),
            "--fixture-manifest", str(manifest_path),
            "--state-json", str(state_path),
            "--require-fresh-state",
        ]
        accepted = subprocess.run(base, check=False, text=True, capture_output=True)
        assert accepted.returncode == 0, accepted.stderr
        assert json.loads(accepted.stdout)["qualified_for_five_shadow"] is True

        bad_state = dict(state)
        bad_state["positions"] = list(state["positions"])
        bad_state["positions"][0] += 0.011
        state_path.write_text(json.dumps(bad_state), encoding="utf-8")
        rejected_state = subprocess.run(base, check=False, text=True, capture_output=True)
        assert rejected_state.returncode == 3, rejected_state.stderr
        assert "state_not_close_to_frozen_episode_000040_frame_0" in json.loads(
            rejected_state.stdout
        )["rejection_reasons"]

        state_path.write_text(json.dumps(state), encoding="utf-8")
        bad_manifest = dict(manifest)
        bad_manifest["support"] = dict(manifest["support"])
        bad_manifest["support"]["surface_height_floor_m"] = 1.0
        manifest_path.write_text(json.dumps(bad_manifest), encoding="utf-8")
        rejected_fixture = subprocess.run(base, check=False, text=True, capture_output=True)
        assert rejected_fixture.returncode == 3, rejected_fixture.stderr
        assert "support_height_uncertainty_outside_reconstructed_range" in json.loads(
            rejected_fixture.stdout
        )["rejection_reasons"]

        bad_manifest["support"]["surface_height_floor_m"] = 0.7746
        bad_manifest["evidence_files"] = [{"path": photo.name, "sha256": "0" * 64}]
        manifest_path.write_text(json.dumps(bad_manifest), encoding="utf-8")
        rejected_hash = subprocess.run(base, check=False, text=True, capture_output=True)
        assert rejected_hash.returncode == 3, rejected_hash.stderr
        assert "fixture_evidence_hash_mismatch:0" in json.loads(
            rejected_hash.stdout
        )["rejection_reasons"]

    print("E6.1B_ENTRY_GATE_CASES=4")
    print("E6.1B_ENTRY_GATE_FAILED_EXPECTATIONS=0")
    print("E6.1B_ENTRY_GATE_ROS_IMPORTED=0")
    print("E6.1B_ENTRY_GATE_ROBOT_ACCESSED=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
