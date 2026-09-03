#!/usr/bin/env python3
"""Classify E6.0B near pairs and sweep moving upstream pairs by exact meshes.

The program is intentionally local-only.  It loads the vendor collision STL
triangles, builds local BVHs and tests the four non-adjacent moving upstream
pairs over the 401-state P14 entry/recovery path.  It does not create an
official ACM and cannot model the passive clamps absent from the vendor URDF.
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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"no se pudo cargar módulo: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BvhNode:
    __slots__ = ("center", "half", "indices", "left", "right", "size")

    def __init__(self, triangles: np.ndarray, indices: np.ndarray, leaf_size: int = 16):
        points = triangles[indices]
        low = points.min(axis=(0, 1))
        high = points.max(axis=(0, 1))
        self.center = (low + high) / 2.0
        self.half = (high - low) / 2.0
        self.size = int(len(indices))
        self.left: BvhNode | None = None
        self.right: BvhNode | None = None
        if len(indices) <= leaf_size:
            self.indices: np.ndarray | None = indices
            return
        centroids = points.mean(axis=1)
        axis = int(np.argmax(np.ptp(centroids, axis=0)))
        ordered = indices[np.argsort(centroids[:, axis], kind="stable")]
        midpoint = len(ordered) // 2
        self.indices = None
        self.left = BvhNode(triangles, ordered[:midpoint], leaf_size)
        self.right = BvhNode(triangles, ordered[midpoint:], leaf_size)


def world_aabb(node: BvhNode, pose: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    center = pose[:3, :3] @ node.center + pose[:3, 3]
    half = np.abs(pose[:3, :3]) @ node.half
    return center - half, center + half


def aabb_overlap(first, second, epsilon: float) -> bool:
    return bool(
        np.all(first[1] >= second[0] - epsilon)
        and np.all(second[1] >= first[0] - epsilon)
    )


def transform_triangles(triangles: np.ndarray, pose: np.ndarray) -> np.ndarray:
    shape = triangles.shape
    transformed = triangles.reshape(-1, 3) @ pose[:3, :3].T + pose[:3, 3]
    return transformed.reshape(shape)


def triangle_overlap(first: np.ndarray, second: np.ndarray, epsilon: float) -> bool:
    """Separating-axis test, including in-plane edge normals for coplanarity."""
    first_edges = np.roll(first, -1, axis=0) - first
    second_edges = np.roll(second, -1, axis=0) - second
    first_normal = np.cross(first_edges[0], first_edges[1])
    second_normal = np.cross(second_edges[0], second_edges[1])
    axes = [first_normal, second_normal]
    axes.extend(np.cross(a, b) for a in first_edges for b in second_edges)
    axes.extend(np.cross(first_normal, edge) for edge in first_edges)
    axes.extend(np.cross(second_normal, edge) for edge in second_edges)
    for axis in axes:
        squared_norm = float(axis @ axis)
        if squared_norm < 1e-20:
            continue
        scale = squared_norm ** 0.5
        projected_first = first @ axis
        projected_second = second @ axis
        tolerance = epsilon * scale
        if (
            projected_first.max() < projected_second.min() - tolerance
            or projected_second.max() < projected_first.min() - tolerance
        ):
            return False
    return True


def triangle_sat_self_test(epsilon: float) -> int:
    base = np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    cases = [
        (
            "coplanar_overlap",
            np.asarray([[0.2, 0.2, 0.0], [0.8, 0.2, 0.0], [0.2, 0.8, 0.0]]),
            True,
        ),
        (
            "coplanar_disjoint",
            np.asarray([[2.0, 0.0, 0.0], [3.0, 0.0, 0.0], [2.0, 1.0, 0.0]]),
            False,
        ),
        (
            "noncoplanar_overlap",
            np.asarray([[0.2, 0.2, -1.0], [0.2, 0.2, 1.0], [0.8, 0.2, 0.0]]),
            True,
        ),
        (
            "parallel_plane_disjoint",
            np.asarray([[0.2, 0.2, 1.0], [0.8, 0.2, 1.0], [0.2, 0.8, 1.0]]),
            False,
        ),
    ]
    for name, candidate, expected in cases:
        observed = triangle_overlap(base, candidate, epsilon)
        if observed != expected:
            raise ValueError(
                f"triangle SAT self-test {name} expected={expected} observed={observed}"
            )
    return len(cases)


def mesh_intersection(
    triangles_a: np.ndarray,
    root_a: BvhNode,
    pose_a: np.ndarray,
    triangles_b: np.ndarray,
    root_b: BvhNode,
    pose_b: np.ndarray,
    epsilon: float,
) -> tuple[bool, dict[str, int], tuple[int, int] | None]:
    stats = {
        "node_pair_tests": 0,
        "leaf_pair_tests": 0,
        "triangle_aabb_candidates": 0,
        "triangle_sat_tests": 0,
    }
    cache_a: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    cache_b: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    stack = [(root_a, root_b)]
    while stack:
        node_a, node_b = stack.pop()
        stats["node_pair_tests"] += 1
        bounds_a = cache_a.setdefault(id(node_a), world_aabb(node_a, pose_a))
        bounds_b = cache_b.setdefault(id(node_b), world_aabb(node_b, pose_b))
        if not aabb_overlap(bounds_a, bounds_b, epsilon):
            continue
        if node_a.indices is not None and node_b.indices is not None:
            stats["leaf_pair_tests"] += 1
            world_a = transform_triangles(triangles_a[node_a.indices], pose_a)
            world_b = transform_triangles(triangles_b[node_b.indices], pose_b)
            low_a, high_a = world_a.min(axis=1), world_a.max(axis=1)
            low_b, high_b = world_b.min(axis=1), world_b.max(axis=1)
            candidates = np.argwhere(
                np.all(high_a[:, None, :] >= low_b[None, :, :] - epsilon, axis=2)
                & np.all(high_b[None, :, :] >= low_a[:, None, :] - epsilon, axis=2)
            )
            stats["triangle_aabb_candidates"] += int(len(candidates))
            for local_a, local_b in candidates:
                stats["triangle_sat_tests"] += 1
                if triangle_overlap(world_a[local_a], world_b[local_b], epsilon):
                    return (
                        True,
                        stats,
                        (int(node_a.indices[local_a]), int(node_b.indices[local_b])),
                    )
            continue
        if node_b.indices is not None or (
            node_a.indices is None and node_a.size >= node_b.size
        ):
            assert node_a.left is not None and node_a.right is not None
            stack.extend(((node_a.left, node_b), (node_a.right, node_b)))
        else:
            assert node_b.left is not None and node_b.right is not None
            stack.extend(((node_a, node_b.left), (node_a, node_b.right)))
    return False, stats, None


def build_path(contract: dict[str, Any], path_helper) -> list[dict[str, float]]:
    points = contract["arm_path_checkpoint_order"]
    named = [
        points["staging_preposition"], points["waypoint_a"], points["ready_b"],
        points["waypoint_a"], points["staging_preposition"],
    ]
    samples: list[list[float]] = []
    for index, (start, end) in enumerate(zip(named, named[1:])):
        segment = path_helper.interpolate(start, end, 101)
        samples.extend(segment if index == 0 else segment[1:])
    return [
        path_helper.checkpoint_to_meta(sample)
        for sample in samples
    ]


def add_stats(target: dict[str, int], source: dict[str, int]) -> None:
    for key, value in source.items():
        target[key] += value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--e6-0b-report", type=Path, required=True)
    parser.add_argument("--ready-contract", type=Path, required=True)
    parser.add_argument("--sdk-urdf", type=Path, required=True)
    parser.add_argument("--sdk-urdf-zip", type=Path, required=True)
    parser.add_argument("--fk-helper", type=Path, required=True)
    parser.add_argument("--path-helper", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--epsilon-m", type=float, default=1e-8)
    args = parser.parse_args()

    sources = (
        args.e6_0b_report, args.ready_contract, args.sdk_urdf,
        args.sdk_urdf_zip, args.fk_helper, args.path_helper,
    )
    for path in sources:
        if not path.is_file():
            raise SystemExit(f"ERROR: falta fuente: {path}")
    if not 0.0 < args.epsilon_m <= 1e-5:
        raise SystemExit("ERROR: --epsilon-m fuera de (0,1e-5]")
    sat_self_test_count = triangle_sat_self_test(args.epsilon_m)

    e6_0b = json.loads(args.e6_0b_report.read_text(encoding="utf-8"))
    if e6_0b.get("schema") != "cruzr-s2-vla-self-collision-e6.0b-v1":
        raise SystemExit("ERROR: esquema E6.0B inesperado")
    near_pairs = e6_0b["collision_model"]["near_overlapping_pairs"]
    direct = [pair for pair in near_pairs if pair["graph_distance"] == 1]
    pgc = [
        pair for pair in near_pairs
        if pair["graph_distance"] > 1
        and any(token in pair[side] for token in ("pgc", "finger") for side in ("left", "right"))
    ]
    exact = [
        pair for pair in near_pairs
        if (pair["left"], pair["right"]) in EXPECTED_EXACT_PAIRS
    ]
    classified_keys = {
        (pair["left"], pair["right"])
        for pair in direct + pgc + exact
    }
    static = [
        pair for pair in near_pairs
        if (pair["left"], pair["right"]) not in classified_keys
        and pair["sample_hits"] == 401
        and not pair["left"].startswith(("L_", "R_"))
        and not pair["right"].startswith(("L_", "R_"))
    ]
    classified_keys.update((pair["left"], pair["right"]) for pair in static)
    unexpected = [
        pair for pair in near_pairs
        if (pair["left"], pair["right"]) not in classified_keys
    ]
    exact_keys = {(pair["left"], pair["right"]) for pair in exact}
    if exact_keys != EXPECTED_EXACT_PAIRS:
        raise SystemExit(f"ERROR: conjunto exacto inesperado: {sorted(exact_keys)}")
    if unexpected:
        raise SystemExit(f"ERROR: pares cercanos sin clase: {unexpected}")
    if (len(direct), len(static), len(pgc), len(exact)) != (40, 12, 2, 4):
        raise SystemExit(
            "ERROR: partición E6.0B cambió: "
            f"direct={len(direct)},static={len(static)},pgc={len(pgc)},exact={len(exact)}"
        )

    fk_helper = load_module(args.fk_helper, "e4_1c_fk_helper")
    path_helper = load_module(args.path_helper, "e6_0b_path_helper")
    joints, _, triangles = fk_helper.load_robot(args.sdk_urdf, args.sdk_urdf_zip)
    contract = json.loads(args.ready_contract.read_text(encoding="utf-8"))
    meta_samples = build_path(contract, path_helper)
    if len(meta_samples) != 401:
        raise SystemExit(f"ERROR: path no tiene 401 muestras: {len(meta_samples)}")
    states = [fk_helper.arm_state(sample) for sample in meta_samples]

    required_links = sorted({link for pair in EXPECTED_EXACT_PAIRS for link in pair})
    missing_triangles = [link for link in required_links if link not in triangles]
    if missing_triangles:
        raise SystemExit(f"ERROR: links sin triángulos: {missing_triangles}")
    roots = {
        link: BvhNode(mesh, np.arange(len(mesh), dtype=np.int64))
        for link, mesh in triangles.items() if link in required_links
    }

    exact_results = []
    collision_samples = []
    for left, right in sorted(EXPECTED_EXACT_PAIRS):
        totals = {
            "node_pair_tests": 0, "leaf_pair_tests": 0,
            "triangle_aabb_candidates": 0, "triangle_sat_tests": 0,
        }
        root_aabb_overlap_samples = 0
        pair_collisions = []
        first_triangles = None
        for sample_index, state in enumerate(states):
            poses = fk_helper.forward_kinematics(joints, state)
            root_bounds_left = world_aabb(roots[left], poses[left])
            root_bounds_right = world_aabb(roots[right], poses[right])
            if not aabb_overlap(root_bounds_left, root_bounds_right, args.epsilon_m):
                continue
            root_aabb_overlap_samples += 1
            intersects, stats, triangle_ids = mesh_intersection(
                triangles[left], roots[left], poses[left],
                triangles[right], roots[right], poses[right], args.epsilon_m,
            )
            add_stats(totals, stats)
            if intersects:
                pair_collisions.append(sample_index)
                first_triangles = first_triangles or triangle_ids
                collision_samples.append({
                    "sample_index": sample_index, "left": left, "right": right,
                    "triangle_ids": triangle_ids,
                })
        exact_results.append({
            "left": left,
            "right": right,
            "left_triangle_count": int(len(triangles[left])),
            "right_triangle_count": int(len(triangles[right])),
            "root_aabb_overlap_samples": root_aabb_overlap_samples,
            "exact_intersection_sample_count": len(pair_collisions),
            "first_exact_intersection_sample": pair_collisions[0] if pair_collisions else None,
            "first_intersecting_triangle_ids": first_triangles,
            **totals,
        })

    failed = bool(collision_samples)
    status = (
        "FAIL_VENDOR_UPSTREAM_NEAR_PAIR_MESH_INTERSECTION"
        if failed else
        "PASS_VENDOR_UPSTREAM_NEAR_PAIR_MESH_SWEEP_PHYSICAL_BLOCKED_CLAMP_CLEARANCE_AND_POLICY"
    )
    report = {
        "schema": "cruzr-s2-vla-near-pair-mesh-e6.0c-v1",
        "experiment_id": "E6.0C",
        "mode": "local_exact_mesh_no_robot_no_network_no_ros_no_publisher",
        "status": status,
        "source_sha256": {path.name: sha256(path) for path in sources},
        "trajectory_sample_count": len(states),
        "near_pair_partition": {
            "total": len(near_pairs),
            "direct_joint_structural": direct,
            "static_outside_p14": static,
            "pgc_not_installed": pgc,
            "moving_upstream_exactly_tested": exact,
            "unexpected": unexpected,
        },
        "exact_mesh_sweep": {
            "algorithm": "local STL BVH AABB broad phase plus triangle SAT narrow phase",
            "epsilon_m": args.epsilon_m,
            "triangle_sat_self_tests_passed": sat_self_test_count,
            "pairs": exact_results,
            "collision_samples": collision_samples,
        },
        "derived_scenario_pair_policy": {
            "scope": "P14 arms-only staging-A-B-A-staging with H/L/W captured and held",
            "not_an_official_acm_or_srdf": True,
            "direct_joint_pairs_candidate_ignore_count": len(direct),
            "static_pairs_require_unchanged_runtime_baseline_count": len(static),
            "pgc_pairs_excluded_as_wrong_effector_count": len(pgc),
            "moving_upstream_pairs_remain_monitored_count": len(exact),
            "moving_upstream_exact_intersections": len(collision_samples),
        },
        "blocking_gates": [
            "installed_passive_clamp_collision_geometry",
            "reviewed_runtime_collision_pair_policy",
            "minimum_clearance_with_model_and_calibration_tolerance",
            "physical_validation",
        ],
        "self_collision_gate_closed": True,
        "physical_authorized": False,
        "robot_state_read": False,
        "network_calls": 0,
        "physical_publishers": 0,
        "physical_movement_commanded": False,
        "next_safe_work": "derive_minimum_clearance_bounds_for_the_four_monitored_pairs_and_specify_offline_physical_executor_guards",
    }
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(f"E6.0C_MODE={report['mode']}")
    print("E6.0C_PAIR_PARTITION=direct:40,static:12,pgc:2,exact:4")
    print(f"E6.0C_TRAJECTORY_SAMPLES={len(states)}")
    print(f"E6.0C_TRIANGLE_SAT_SELF_TESTS={sat_self_test_count}")
    print(f"E6.0C_EXACT_INTERSECTION_SAMPLES={len(collision_samples)}")
    for result in exact_results:
        print(
            "E6.0C_PAIR="
            f"{result['left']}:{result['right']},"
            f"root_overlap_samples:{result['root_aabb_overlap_samples']},"
            f"triangle_candidates:{result['triangle_aabb_candidates']},"
            f"exact_hits:{result['exact_intersection_sample_count']}"
        )
    print("E6.0C_SELF_COLLISION_GATE_CLOSED=1")
    print("E6.0C_PHYSICAL_AUTHORIZED=0")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
