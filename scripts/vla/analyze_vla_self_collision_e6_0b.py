#!/usr/bin/env python3
"""Offline broad-phase self-collision audit for the E6.0 P14 ready path.

This program deliberately has no ROS or network imports.  It reconstructs the
vendor URDF FK and checks transformed oriented bounding boxes (OBBs) along the
exact arms-only staging -> A -> B -> A -> staging path.  OBBs enclose the
vendor collision meshes, so absence of an overlap is useful broad-phase
evidence.  It is not a physical certificate: the repository has no SRDF/ACM
and the installed passive clamp geometry is not represented by the PGC meshes.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

import numpy as np


CHECKPOINT_PER_ARM = [
    "elbow_roll", "elbow_yaw", "shoulder_pitch", "shoulder_roll",
    "shoulder_yaw", "wrist_pitch", "wrist_roll",
]
META_PER_ARM = [
    "shoulder_pitch", "shoulder_roll", "shoulder_yaw", "elbow_roll",
    "elbow_yaw", "wrist_pitch", "wrist_roll",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_helper(path: Path):
    spec = importlib.util.spec_from_file_location("e4_1c_fk_helper", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"no se pudo cargar helper FK: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def checkpoint_to_meta(values: list[float]) -> list[float]:
    if len(values) != 14:
        raise ValueError("estado P14 no es 14D")
    result: list[float] = []
    for side in (values[:7], values[7:]):
        by_name = dict(zip(CHECKPOINT_PER_ARM, side, strict=True))
        result.extend(float(by_name[name]) for name in META_PER_ARM)
    return result


def interpolate(start: list[float], end: list[float], count: int) -> list[list[float]]:
    return [
        [float((1.0 - alpha) * a + alpha * b) for a, b in zip(start, end, strict=True)]
        for alpha in np.linspace(0.0, 1.0, count)
    ]


def graph_distances(joints: list[dict[str, Any]]) -> dict[tuple[str, str], int]:
    adjacency: dict[str, set[str]] = {}
    for joint in joints:
        adjacency.setdefault(joint["parent"], set()).add(joint["child"])
        adjacency.setdefault(joint["child"], set()).add(joint["parent"])
    result: dict[tuple[str, str], int] = {}
    for origin in adjacency:
        queue = [(origin, 0)]
        visited = {origin}
        for link, distance in queue:
            result[(origin, link)] = distance
            for neighbor in adjacency.get(link, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, distance + 1))
    return result


def obb_for_link(pose: np.ndarray, bounds: tuple[np.ndarray, np.ndarray]):
    low, high = bounds
    local_center = (low + high) / 2.0
    half_extent = (high - low) / 2.0
    center = pose[:3, :3] @ local_center + pose[:3, 3]
    return center, pose[:3, :3], half_extent


def obb_overlap(first, second, epsilon: float = 1e-9) -> bool:
    """15-axis SAT for two OBBs."""
    center_a, axes_a, extent_a = first
    center_b, axes_b, extent_b = second
    rotation = axes_a.T @ axes_b
    translation = axes_a.T @ (center_b - center_a)
    absolute = np.abs(rotation) + epsilon

    for index in range(3):
        if abs(translation[index]) > extent_a[index] + extent_b @ absolute[index, :]:
            return False
    for index in range(3):
        if abs(translation @ rotation[:, index]) > extent_b[index] + extent_a @ absolute[:, index]:
            return False
    for left in range(3):
        for right in range(3):
            radius_a = (
                extent_a[(left + 1) % 3] * absolute[(left + 2) % 3, right]
                + extent_a[(left + 2) % 3] * absolute[(left + 1) % 3, right]
            )
            radius_b = (
                extent_b[(right + 1) % 3] * absolute[left, (right + 2) % 3]
                + extent_b[(right + 2) % 3] * absolute[left, (right + 1) % 3]
            )
            projected = abs(
                translation[(left + 2) % 3] * rotation[(left + 1) % 3, right]
                - translation[(left + 1) % 3] * rotation[(left + 2) % 3, right]
            )
            if projected > radius_a + radius_b:
                return False
    return True


def limit_violations(joints: list[dict[str, Any]], states: list[dict[str, float]], urdf: Path):
    root = ET.parse(urdf).getroot()
    limits: dict[str, tuple[float, float]] = {}
    for element in root.findall("joint"):
        if element.get("type") not in {"revolute", "prismatic"}:
            continue
        limit = element.find("limit")
        if limit is None or limit.get("lower") is None or limit.get("upper") is None:
            continue
        limits[element.get("name", "")] = (float(limit.get("lower")), float(limit.get("upper")))
    known_joint_names = {joint["name"] for joint in joints}
    violations = []
    for sample_index, state in enumerate(states):
        for name, value in state.items():
            if name not in known_joint_names or name not in limits:
                continue
            lower, upper = limits[name]
            if value < lower - 1e-9 or value > upper + 1e-9:
                violations.append({
                    "sample_index": sample_index, "joint": name,
                    "value_rad": value, "lower_rad": lower, "upper_rad": upper,
                })
    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ready-contract", type=Path, required=True)
    parser.add_argument("--sdk-urdf", type=Path, required=True)
    parser.add_argument("--sdk-urdf-zip", type=Path, required=True)
    parser.add_argument("--fk-helper", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    for path in (args.ready_contract, args.sdk_urdf, args.sdk_urdf_zip, args.fk_helper):
        if not path.is_file():
            raise SystemExit(f"ERROR: falta fuente: {path}")

    helper = load_helper(args.fk_helper)
    joints, link_bounds, _ = helper.load_robot(args.sdk_urdf, args.sdk_urdf_zip)
    contract = json.loads(args.ready_contract.read_text(encoding="utf-8"))
    arm_path = contract["arm_path_checkpoint_order"]
    named_points = [
        ("staging", arm_path["staging_preposition"]),
        ("waypoint_a", arm_path["waypoint_a"]),
        ("ready_b", arm_path["ready_b"]),
        ("waypoint_a_recovery", arm_path["waypoint_a"]),
        ("staging_recovery", arm_path["staging_preposition"]),
    ]
    segments = []
    checkpoint_samples: list[list[float]] = []
    for segment_index, ((start_name, start), (end_name, end)) in enumerate(
        zip(named_points, named_points[1:])
    ):
        samples = interpolate(start, end, 101)
        if segment_index:
            samples = samples[1:]
        offset = len(checkpoint_samples)
        checkpoint_samples.extend(samples)
        segments.append({
            "name": f"{start_name}_to_{end_name}",
            "first_sample": offset,
            "last_sample": len(checkpoint_samples) - 1,
        })

    states = [helper.arm_state(checkpoint_to_meta(values)) for values in checkpoint_samples]
    distances = graph_distances(joints)
    links = sorted(link_bounds)
    overlap_conditions = 0
    near_pairs: dict[tuple[str, str], dict[str, Any]] = {}
    far_pairs: dict[tuple[str, str], dict[str, Any]] = {}
    far_upstream_pairs: dict[tuple[str, str], dict[str, Any]] = {}
    for sample_index, state in enumerate(states):
        poses = helper.forward_kinematics(joints, state)
        boxes = {
            link: obb_for_link(poses[link], bounds)
            for link, bounds in link_bounds.items()
        }
        for left_index, left in enumerate(links):
            for right in links[left_index + 1:]:
                if not obb_overlap(boxes[left], boxes[right]):
                    continue
                overlap_conditions += 1
                distance = distances[(left, right)]
                target = near_pairs if distance <= 3 else far_pairs
                record = target.setdefault((left, right), {
                    "left": left, "right": right, "graph_distance": distance,
                    "first_sample": sample_index, "last_sample": sample_index,
                    "sample_hits": 0,
                })
                record["last_sample"] = sample_index
                record["sample_hits"] += 1
                if distance > 3 and not any(
                    token in left or token in right for token in ("pgc", "finger")
                ):
                    far_upstream_pairs[(left, right)] = dict(record)

    violations = limit_violations(joints, states, args.sdk_urdf)
    gates = [
        {
            "id": "p14_path_continuity",
            "status": "PASS" if len(checkpoint_samples) == 401 else "FAIL",
            "evidence": "401 unique samples over staging-A-B-A-staging",
        },
        {
            "id": "urdf_joint_limits",
            "status": "PASS" if not violations else "FAIL",
            "evidence": f"violations={len(violations)}",
        },
        {
            "id": "far_nonadjacent_upstream_obb",
            "status": "PASS" if not far_upstream_pairs else "FAIL",
            "evidence": f"overlapping_pairs={len(far_upstream_pairs)}; graph_distance>3",
        },
        {
            "id": "allowed_collision_matrix_or_srdf",
            "status": "BLOCKED",
            "evidence": "no SRDF/ACM supplier artifact found; graph-distance<=3 cannot be certified",
        },
        {
            "id": "installed_clamp_collision_geometry",
            "status": "BLOCKED",
            "evidence": "vendor URDF contains PGC gripper meshes, not installed passive clamp plates",
        },
        {
            "id": "physical_clearance_and_dynamics",
            "status": "BLOCKED",
            "evidence": "OBB broad phase does not certify physical clearance, flex, force or acceleration",
        },
    ]
    blocked = [gate["id"] for gate in gates if gate["status"] == "BLOCKED"]
    failed = [gate["id"] for gate in gates if gate["status"] == "FAIL"]
    report = {
        "schema": "cruzr-s2-vla-self-collision-e6.0b-v1",
        "experiment_id": "E6.0B",
        "mode": "local_fk_obb_no_robot_no_network_no_ros_no_publisher",
        "status": (
            "FAIL_OFFLINE_PATH_OR_FAR_LINK_OBB_COLLISION"
            if failed else
            "PASS_UPSTREAM_FAR_LINK_OBB_SWEEP_PARTIAL_SELF_COLLISION_BLOCKED_NO_ACM_OR_CLAMP_GEOMETRY"
        ),
        "source_sha256": {
            "ready_contract": sha256(args.ready_contract),
            "sdk_urdf": sha256(args.sdk_urdf),
            "sdk_urdf_zip": sha256(args.sdk_urdf_zip),
            "fk_helper": sha256(args.fk_helper),
        },
        "trajectory": {
            "joint_order": contract["p14_contract"]["commanded_joint_names"],
            "sample_count": len(checkpoint_samples),
            "segments": segments,
            "joint_limit_violations": violations,
        },
        "collision_model": {
            "vendor_collision_links": len(link_bounds),
            "broad_phase": "transformed local-link aggregate OBB with 15-axis SAT",
            "near_pair_definition": "URDF graph distance <= 3; reported but not classified without ACM",
            "near_overlapping_pairs": list(near_pairs.values()),
            "far_overlapping_pairs_all_vendor_geometry": list(far_pairs.values()),
            "far_overlapping_pairs_upstream_without_pgc_finger": list(far_upstream_pairs.values()),
            "total_overlap_sample_pair_conditions": overlap_conditions,
            "installed_clamp_geometry_available": False,
            "srdf_or_allowed_collision_matrix_available": False,
        },
        "gates": gates,
        "blocking_gates": blocked,
        "failed_gates": failed,
        "e6_0_self_collision_gate_closed": True,
        "physical_authorized": False,
        "robot_state_read": False,
        "network_calls": 0,
        "physical_publishers": 0,
        "physical_movement_commanded": False,
        "next_safe_work": "obtain_or_derive_reviewable_ACM_and_installed_clamp_collision_geometry_then_exact_clearance_audit",
    }
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(f"E6.0B_MODE={report['mode']}")
    print(f"E6.0B_SAMPLES={len(checkpoint_samples)}")
    print(f"E6.0B_URDF_COLLISION_LINKS={len(link_bounds)}")
    print(f"E6.0B_NEAR_OBB_PAIRS={len(near_pairs)}")
    print(f"E6.0B_FAR_OBB_PAIRS_ALL={len(far_pairs)}")
    print(f"E6.0B_FAR_OBB_PAIRS_UPSTREAM={len(far_upstream_pairs)}")
    print(f"E6.0B_JOINT_LIMIT_VIOLATIONS={len(violations)}")
    print(f"E6.0B_BLOCKING_GATES={','.join(blocked)}")
    print("E6.0B_PHYSICAL_AUTHORIZED=0")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
