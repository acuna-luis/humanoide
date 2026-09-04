#!/usr/bin/env python3
"""Offline tests for the guarded E6.0Y launcher and activation grant."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def joint_state_sample(contract: dict, delta: float = 0.0) -> dict:
    names = []
    positions = []
    for index, (name, position) in enumerate(zip(
        contract["commanded_joint_names"], contract["ready_arm_positions"], strict=True
    )):
        value = float(position) + (delta if index == 0 else 0.0)
        names.append(name)
        positions.append(value)
    for name in contract["locked_joint_names"]:
        names.append(name)
        positions.append(-0.65 if name == "head_pitch_joint" else 0.0)
    return {"name": names, "position": positions, "velocity": [0.0] * len(names)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-dir", type=Path, required=True)
    parser.add_argument("--launcher", type=Path, required=True)
    args = parser.parse_args()
    root = args.runtime_dir
    gate = load(root / "cruzr_s2_vla_ready_state_gate.py", "e6_0y_gate")
    runtime = load(root / "cruzr_s2_vla_one_point_runtime.py", "e6_0y_runtime")
    contract = json.loads((root / "cruzr_s2_vla_sdk_transport_contract_e6_0r.json").read_text())
    nominal = gate.classify(
        joint_state_sample(contract), contract,
        ready_tolerance=0.01, velocity_tolerance=0.01,
    )
    outside = gate.classify(
        joint_state_sample(contract, 0.011), contract,
        ready_tolerance=0.01, velocity_tolerance=0.01,
    )
    assert "MEASURED_READY=1" in nominal
    assert "MEASURED_READY=0" in outside

    preflight_text = """MOTION_CONTAINER=running
ROS_CONTAINER=running
HW_TYPE=cruzr_s2_v1
ESTOP_KEY=0
SERVO_ESTOP_KEY=0
CHARGER=0
BATTERY_1=50
BATTERY_2=50
WHOLE_JOINT_STATES=advertised
MANIPULATION_ACTION_SERVERS=1
READY_TASK_REGISTERED=1
READY_XML_VARIANT=s2-waist-1d-overlay
INFERENCE_CONTAINER=exited
CONTROL_CONTAINER=exited
COMMAND_PATH_SAFE=publishers:0
ACTUATORS_OPERATION_ENABLED=1
ESTOPS=0,0
CHARGER=disconnected
ACTIONS=ready
CANONICAL_MANIPULATION_PREFLIGHT=passed-read-only
"""
    ready_text = "\n".join(nominal) + "\n"
    builder = root / "create_cruzr_s2_vla_activation_grant_e6_0y.py"
    template = root / "cruzr_s2_vla_canary_activation_template_e6_0w.json"
    acceptance = root / "cruzr_s2_vla_owner_acceptance_e6_0x.json"
    limits = root / "cruzr_s2_vla_canary_engineering_limits_e6_0s.json"
    with tempfile.TemporaryDirectory(prefix="e6_0y_") as temporary:
        temporary_path = Path(temporary)
        preflight = temporary_path / "preflight.log"
        ready = temporary_path / "ready.log"
        grant = temporary_path / "grant.json"
        preflight.write_text(preflight_text, encoding="utf-8")
        ready.write_text(ready_text, encoding="utf-8")
        command = [
            sys.executable, str(builder), "--template", str(template),
            "--acceptance", str(acceptance), "--limits", str(limits),
            "--preflight", str(preflight), "--ready", str(ready),
            "--run-id", "20260904T000000_E6.0Y", "--output", str(grant),
            "--valid-seconds", "120",
            "--reference-epoch", str(int(time.time()) - 20),
        ]
        created = subprocess.run(command, check=False, text=True, capture_output=True)
        assert created.returncode == 0, created.stderr
        value = json.loads(grant.read_text(encoding="utf-8"))
        assert runtime.activation_is_enabled(value)
        assert value["authorization_clock_source"] == "motion-host-epoch"
        assert 19 <= value["authorization_clock_skew_seconds"] <= 22
        assert value["authorization_preflight_sha256"] == digest(preflight)
        assert value["authorization_ready_sha256"] == digest(ready)

        skewed_command = [*command[:-1], str(int(time.time()) - 61)]
        skewed = subprocess.run(
            skewed_command, check=False, text=True, capture_output=True
        )
        assert skewed.returncode != 0
        assert "mayor de 60 s" in skewed.stderr

        preflight.write_text(preflight_text.replace("ESTOP_KEY=0", "ESTOP_KEY=1"), encoding="utf-8")
        rejected = subprocess.run(command, check=False, text=True, capture_output=True)
        assert rejected.returncode != 0
        assert "ESTOP_KEY" in rejected.stderr

    launcher_source = args.launcher.read_text(encoding="utf-8")
    checks = {
        "vendor_executor_not_started": "vla_control_node.py" not in launcher_source,
        "checkpoint_trigger_removed": "ros2 action send_goal /gr00t/trigger_inference" not in launcher_source,
        "active_runtime_removed": "cruzr_s2_vla_ros_one_point_process.py" not in launcher_source,
        "activation_grant_removed": "--expected-activation-sha256" not in launcher_source,
        "ready_retired": "E6.0Y_READY_RETIRED=1" in launcher_source,
        "one_point_retired": "E6.0Y_ONE_POINT_RETIRED=1" in launcher_source,
        "recovery_only_motion_task": launcher_source.count('run_motion_task "$RECOVERY_TASK"') == 1,
        "stop_remains_available": '"$SHADOW" --stop' in launcher_source,
        "hardware_estop_warning": "STOP software no" in launcher_source,
        "task_matched_successor_required": (
            "task-matched-scene,task-matched-20D-entry,five-fresh-shadow-chunks"
            in launcher_source
        ),
    }
    assert all(checks.values()), checks
    print("E6.0Y_OFFLINE_CASES=grant-valid,grant-estop-rejected,grant-clock-skew-rejected,ready-valid,ready-delta-rejected")
    print("E6.0Y_STATIC_CHECKS=" + str(len(checks)))
    print("E6.0Y_FAILED_EXPECTATIONS=0")
    print("E6.0Y_ACTIVE_PATH=removed")
    print("E6.0Y_READY_PATH=retired")
    print("E6.0Y_RECOVERY_PATH=retained")
    print("E6.0Y_ROBOT_ACCESSED=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
