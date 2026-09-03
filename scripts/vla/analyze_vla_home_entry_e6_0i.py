#!/usr/bin/env python3
"""Audit the missing measured-home <-> VLA staging segment without commanding a robot.

The existing E6.0B/C/D evidence starts at the vendor staging pose.  This
analyzer adds the simultaneous home-to-staging motion of both arms and the
head from a fresh actuator snapshot.  It reuses the reviewed FK, BVH,
triangle-intersection and distance kernels.  It has no ROS/network/publisher
code and never authorizes physical execution.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

import numpy as np


EXPECTED_EXACT_PAIRS = {
    ("L_elbow_yaw_link", "L_wrist_roll_link"),
    ("R_elbow_yaw_link", "R_wrist_roll_link"),
    ("L_shoulder_roll_link", "torso_link"),
    ("R_shoulder_roll_link", "torso_link"),
}
BODY_IDS = {
    1001: "head_yaw_joint",
    1002: "head_pitch_joint",
    11004: "lifter_pitch_1_joint",
    11003: "lifter_pitch_2_joint",
    11002: "lifter_pitch_3_joint",
    11001: "waist_yaw_joint",
    4001: "L_shoulder_pitch_joint",
    4002: "L_shoulder_roll_joint",
    4003: "L_shoulder_yaw_joint",
    4004: "L_elbow_roll_joint",
    4005: "L_elbow_yaw_joint",
    4006: "L_wrist_pitch_joint",
    4007: "L_wrist_roll_joint",
    5001: "R_shoulder_pitch_joint",
    5002: "R_shoulder_roll_joint",
    5003: "R_shoulder_yaw_joint",
    5004: "R_elbow_roll_joint",
    5005: "R_elbow_yaw_joint",
    5006: "R_wrist_pitch_joint",
    5007: "R_wrist_roll_joint",
}


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"no se pudo cargar módulo: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def actuator_home(path: Path) -> tuple[dict[str, float], dict[str, Any]]:
    message = json.loads(path.read_text(encoding="utf-8"))
    items = message.get("act_item", [])
    by_id = {int(item.get("id", -1)): item for item in items}
    missing = sorted(set(BODY_IDS) - set(by_id))
    if missing:
        raise ValueError(f"faltan ejes del snapshot: {missing}")
    state: dict[str, float] = {}
    maximums = {"position": 0.0, "velocity": 0.0, "command_delta": 0.0}
    for actuator_id, joint_name in BODY_IDS.items():
        item = by_id[actuator_id]
        position = float(item["position"])
        velocity = float(item["velocity"])
        command = float(item.get("cmd_pos", position))
        status = int(item.get("status", 0))
        error = int(item.get("error_code", 0))
        values = (position, velocity, command)
        if not all(np.isfinite(value) for value in values):
            raise ValueError(f"valor no finito en eje {actuator_id}")
        if error or status & 0x0008 or status & 0x0007 != 0x0007:
            raise ValueError(
                f"eje no habilitado {actuator_id}: error={error:#x},status={status:#x}"
            )
        delta = command - position
        if abs(velocity) > 0.02 or abs(delta) > 0.01 or abs(position) >= 0.02:
            raise ValueError(
                f"snapshot no es home inmóvil {actuator_id}: "
                f"position={position},velocity={velocity},delta={delta}"
            )
        state[joint_name] = position
        maximums["position"] = max(maximums["position"], abs(position))
        maximums["velocity"] = max(maximums["velocity"], abs(velocity))
        maximums["command_delta"] = max(maximums["command_delta"], abs(delta))
    return state, {"axis_count": len(state), **maximums}


def pair_key(record: dict[str, Any]) -> tuple[str, str]:
    return record["left"], record["right"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--actuator-state", type=Path, required=True)
    parser.add_argument("--ready-contract", type=Path, required=True)
    parser.add_argument("--e6-0b-report", type=Path, required=True)
    parser.add_argument("--e6-0c-report", type=Path, required=True)
    parser.add_argument("--e6-0d-report", type=Path, required=True)
    parser.add_argument("--sdk-urdf", type=Path, required=True)
    parser.add_argument("--sdk-urdf-zip", type=Path, required=True)
    parser.add_argument("--fk-helper", type=Path, required=True)
    parser.add_argument("--path-helper", type=Path, required=True)
    parser.add_argument("--mesh-helper", type=Path, required=True)
    parser.add_argument("--distance-helper", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--epsilon-m", type=float, default=1e-8)
    args = parser.parse_args()

    sources = (
        args.actuator_state, args.ready_contract, args.e6_0b_report,
        args.e6_0c_report, args.e6_0d_report, args.sdk_urdf,
        args.sdk_urdf_zip, args.fk_helper, args.path_helper,
        args.mesh_helper, args.distance_helper,
    )
    for path in sources:
        if not path.is_file():
            raise SystemExit(f"ERROR: falta fuente: {path}")

    fk = load_module(args.fk_helper, "e6_0i_fk")
    path_module = load_module(args.path_helper, "e6_0i_path")
    mesh = load_module(args.mesh_helper, "e6_0i_mesh")
    distance = load_module(args.distance_helper, "e6_0i_distance")
    contract = json.loads(args.ready_contract.read_text(encoding="utf-8"))
    broad = json.loads(args.e6_0b_report.read_text(encoding="utf-8"))
    narrow = json.loads(args.e6_0c_report.read_text(encoding="utf-8"))
    clearance = json.loads(args.e6_0d_report.read_text(encoding="utf-8"))
    if broad.get("schema") != "cruzr-s2-vla-self-collision-e6.0b-v1":
        raise SystemExit("ERROR: esquema E6.0B inesperado")
    if narrow.get("schema") != "cruzr-s2-vla-near-pair-mesh-e6.0c-v1":
        raise SystemExit("ERROR: esquema E6.0C inesperado")
    if clearance.get("schema") != "cruzr-s2-vla-clearance-guards-e6.0d-v1":
        raise SystemExit("ERROR: esquema E6.0D inesperado")
    if narrow["exact_mesh_sweep"]["collision_samples"]:
        raise SystemExit("ERROR: la trayectoria staging existente ya tiene colisiones")

    home, home_metrics = actuator_home(args.actuator_state)
    arms = contract["arm_path_checkpoint_order"]["staging_preposition"]
    staging = dict(home)
    staging.update(fk.arm_state(path_module.checkpoint_to_meta(arms)))
    staging["head_pitch_joint"] = 0.0
    staging["head_yaw_joint"] = -0.65
    staging["waist_yaw_joint"] = 0.0
    states = list(fk.interpolate(home, staging, 101))

    joints, bounds, triangles = fk.load_robot(args.sdk_urdf, args.sdk_urdf_zip)
    violations = path_module.limit_violations(joints, states, args.sdk_urdf)
    graph = path_module.graph_distances(joints)
    links = sorted(bounds)
    near: dict[tuple[str, str], dict[str, Any]] = {}
    far_upstream: dict[tuple[str, str], dict[str, Any]] = {}
    for sample_index, state in enumerate(states):
        poses = fk.forward_kinematics(joints, state)
        boxes = {
            link: path_module.obb_for_link(poses[link], local_bounds)
            for link, local_bounds in bounds.items()
        }
        for left_index, left in enumerate(links):
            for right in links[left_index + 1:]:
                if not path_module.obb_overlap(boxes[left], boxes[right]):
                    continue
                record = {
                    "left": left, "right": right,
                    "graph_distance": graph[(left, right)],
                }
                if record["graph_distance"] <= 3:
                    near.setdefault((left, right), record)
                elif not any(token in left or token in right for token in ("pgc", "finger")):
                    far_upstream.setdefault((left, right), record)

    baseline_near = {
        pair_key(pair) for pair in broad["collision_model"]["near_overlapping_pairs"]
    }
    new_near = sorted(set(near) - baseline_near)
    baseline_far = {
        pair_key(pair)
        for pair in broad["collision_model"]["far_overlapping_pairs_upstream_without_pgc_finger"]
    }
    new_far = sorted(set(far_upstream) - baseline_far)

    monitored_pairs = EXPECTED_EXACT_PAIRS | set(new_far)
    required_links = sorted({link for pair in monitored_pairs for link in pair})
    missing_meshes = [link for link in required_links if link not in triangles]
    if missing_meshes:
        raise SystemExit(f"ERROR: faltan mallas: {missing_meshes}")
    roots = {
        link: mesh.BvhNode(triangles[link], np.arange(len(triangles[link]), dtype=np.int64))
        for link in required_links
    }
    intersection_samples: list[dict[str, Any]] = []
    entry_clearances: list[dict[str, Any]] = []
    for left, right in sorted(monitored_pairs):
        minimum = float("inf")
        minimum_sample = -1
        for sample_index, state in enumerate(states):
            poses = fk.forward_kinematics(joints, state)
            intersects, _, triangle_ids = mesh.mesh_intersection(
                triangles[left], roots[left], poses[left],
                triangles[right], roots[right], poses[right], args.epsilon_m,
            )
            if intersects:
                intersection_samples.append({
                    "sample_index": sample_index, "left": left, "right": right,
                    "triangle_ids": triangle_ids,
                })
                continue
            measured, _, _ = distance.exact_mesh_distance(
                triangles[left], roots[left], poses[left],
                triangles[right], roots[right], poses[right], mesh, args.epsilon_m,
            )
            if measured < minimum:
                minimum, minimum_sample = measured, sample_index
        entry_clearances.append({
            "left": left, "right": right,
            "minimum_sampled_clearance_m": minimum,
            "minimum_sample_index": minimum_sample,
        })

    unresolved_far: list[tuple[str, str]] = []
    failed = bool(violations or new_near or unresolved_far or intersection_samples)
    minimum_entry = min(item["minimum_sampled_clearance_m"] for item in entry_clearances)
    existing_minimum = min(
        item["minimum_sampled_clearance_m"]
        for item in clearance["pairs"]
    )
    report = {
        "schema": "cruzr-s2-vla-home-entry-e6.0i-v1",
        "experiment_id": "E6.0I",
        "mode": "fresh_state_read_then_local_analysis_no_publisher_no_movement",
        "status": (
            "FAIL_HOME_STAGING_VENDOR_MODEL_PATH"
            if failed else
            "PASS_HOME_STAGING_VENDOR_MODEL_SWEEP_PHYSICAL_BLOCKED_NO_CLAMP_OR_DYNAMICS"
        ),
        "source_sha256": {path.name: sha256(path) for path in sources},
        "fresh_home_snapshot": home_metrics,
        "trajectory": {
            "segment": "measured_home_to_vendor_staging_and_symmetric_return",
            "entry_sample_count": len(states),
            "complete_composite_sample_count": 601,
            "head_motion_rad": {"pitch_target": 0.0, "yaw_target": -0.65},
            "joint_limit_violations": violations,
        },
        "broad_phase": {
            "new_near_pairs_vs_e6_0b": [list(pair) for pair in new_near],
            "new_far_upstream_pairs_vs_e6_0b": [list(pair) for pair in new_far],
            "new_far_pairs_exactly_tested": [list(pair) for pair in new_far],
            "new_far_pairs_unresolved": [list(pair) for pair in unresolved_far],
        },
        "exact_mesh": {
            "monitored_pairs": entry_clearances,
            "intersection_samples": intersection_samples,
            "minimum_entry_clearance_m": minimum_entry,
            "minimum_existing_staging_path_clearance_m": existing_minimum,
            "minimum_complete_sampled_vendor_clearance_m": min(minimum_entry, existing_minimum),
        },
        "complete_vendor_model_path_covered": not failed,
        "blocking_gates": [
            "installed_passive_clamp_collision_geometry_and_tolerance",
            "certified_acceleration_and_force_limits",
            "physical_ready_and_recovery_validation",
            "physical_executor_and_temporal_semantics",
        ],
        "robot_state_read": True,
        "network_calls_by_wrapper": 1,
        "physical_publishers": 0,
        "physical_movement_commanded": False,
        "physical_authorized": False,
    }
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(f"E6.0I_STATUS={report['status']}")
    print(f"E6.0I_ENTRY_SAMPLES={len(states)}")
    print(f"E6.0I_NEW_NEAR_PAIRS={len(new_near)}")
    print(f"E6.0I_NEW_FAR_UPSTREAM_PAIRS={len(new_far)}")
    print(f"E6.0I_NEW_FAR_PAIRS_EXACTLY_TESTED={len(new_far)}")
    print(f"E6.0I_EXACT_INTERSECTION_SAMPLES={len(intersection_samples)}")
    print(f"E6.0I_MIN_ENTRY_CLEARANCE_M={minimum_entry:.9f}")
    print("E6.0I_PHYSICAL_AUTHORIZED=0")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
