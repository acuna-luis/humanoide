#!/usr/bin/env python3
"""Measure sampled vendor-mesh clearance and derive a disabled guard contract.

This is a local-only E6.0D analysis.  It measures exact triangle distance for
the four moving upstream pairs selected by E6.0C over the sampled
staging-A-B-A-staging path.  The result is not a continuous collision proof
and cannot account for the installed passive clamps or hardware/model error.
"""

from __future__ import annotations

import argparse
import hashlib
import heapq
import importlib.util
import json
import multiprocessing
from pathlib import Path
from typing import Any

import numpy as np


_PAIR_WORKER_CONTEXT: dict[str, Any] = {}


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


def point_triangle_distance(point: np.ndarray, tri: np.ndarray) -> float:
    """Return Euclidean point-to-triangle distance (Ericson regions)."""
    a, b, c = tri
    ab, ac, ap = b - a, c - a, point - a
    d1, d2 = float(ab @ ap), float(ac @ ap)
    if d1 <= 0.0 and d2 <= 0.0:
        return float(np.linalg.norm(ap))

    bp = point - b
    d3, d4 = float(ab @ bp), float(ac @ bp)
    if d3 >= 0.0 and d4 <= d3:
        return float(np.linalg.norm(bp))

    vc = d1 * d4 - d3 * d2
    if vc <= 0.0 and d1 >= 0.0 and d3 <= 0.0:
        v = d1 / (d1 - d3)
        return float(np.linalg.norm(point - (a + v * ab)))

    cp = point - c
    d5, d6 = float(ab @ cp), float(ac @ cp)
    if d6 >= 0.0 and d5 <= d6:
        return float(np.linalg.norm(cp))

    vb = d5 * d2 - d1 * d6
    if vb <= 0.0 and d2 >= 0.0 and d6 <= 0.0:
        w = d2 / (d2 - d6)
        return float(np.linalg.norm(point - (a + w * ac)))

    va = d3 * d6 - d5 * d4
    if va <= 0.0 and (d4 - d3) >= 0.0 and (d5 - d6) >= 0.0:
        edge = c - b
        w = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        return float(np.linalg.norm(point - (b + w * edge)))

    denominator = va + vb + vc
    if abs(denominator) < 1e-24:
        return min(
            segment_segment_distance(point, point, a, b),
            segment_segment_distance(point, point, b, c),
            segment_segment_distance(point, point, c, a),
        )
    v = vb / denominator
    w = vc / denominator
    projection = a + ab * v + ac * w
    return float(np.linalg.norm(point - projection))


def segment_segment_distance(
    first_a: np.ndarray,
    first_b: np.ndarray,
    second_a: np.ndarray,
    second_b: np.ndarray,
) -> float:
    """Return distance between two closed 3-D segments."""
    epsilon = 1e-24
    u, v, w = first_b - first_a, second_b - second_a, first_a - second_a
    a, b, c = float(u @ u), float(u @ v), float(v @ v)
    d, e = float(u @ w), float(v @ w)
    denominator = a * c - b * b
    s_num, s_den = denominator, denominator
    t_num, t_den = denominator, denominator

    if a <= epsilon and c <= epsilon:
        return float(np.linalg.norm(first_a - second_a))
    if a <= epsilon:
        s_num, s_den = 0.0, 1.0
        t_num, t_den = e, c
    elif c <= epsilon:
        t_num, t_den = 0.0, 1.0
        s_num, s_den = -d, a
    else:
        if denominator <= epsilon:
            s_num, s_den = 0.0, 1.0
            t_num, t_den = e, c
        else:
            s_num = b * e - c * d
            t_num = a * e - b * d
            if s_num < 0.0:
                s_num = 0.0
                t_num, t_den = e, c
            elif s_num > s_den:
                s_num = s_den
                t_num, t_den = e + b, c
        if t_num < 0.0:
            t_num = 0.0
            if -d < 0.0:
                s_num = 0.0
            elif -d > a:
                s_num = s_den
            else:
                s_num, s_den = -d, a
        elif t_num > t_den:
            t_num = t_den
            if -d + b < 0.0:
                s_num = 0.0
            elif -d + b > a:
                s_num = s_den
            else:
                s_num, s_den = -d + b, a

    sc = 0.0 if abs(s_num) <= epsilon else s_num / s_den
    tc = 0.0 if abs(t_num) <= epsilon else t_num / t_den
    return float(np.linalg.norm(w + sc * u - tc * v))


def point_segment_distances_batch(
    points: np.ndarray,
    starts: np.ndarray,
    ends: np.ndarray,
) -> np.ndarray:
    directions = ends - starts
    squared_lengths = np.einsum("ij,ij->i", directions, directions)
    parameters = np.divide(
        np.einsum("ij,ij->i", points - starts, directions),
        squared_lengths,
        out=np.zeros(len(points), dtype=float),
        where=squared_lengths > 1e-24,
    )
    parameters = np.clip(parameters, 0.0, 1.0)
    closest = starts + parameters[:, None] * directions
    return np.linalg.norm(points - closest, axis=1)


def point_triangle_distances_batch(points: np.ndarray, triangles: np.ndarray) -> np.ndarray:
    """Vectorized exact point-to-triangle distance for matching rows."""
    a, b, c = triangles[:, 0], triangles[:, 1], triangles[:, 2]
    ab, ac, ap = b - a, c - a, points - a
    normal = np.cross(ab, ac)
    normal_squared = np.einsum("ij,ij->i", normal, normal)
    signed_numerator = np.einsum("ij,ij->i", ap, normal)
    plane_distance = np.divide(
        np.abs(signed_numerator),
        np.sqrt(normal_squared),
        out=np.full(len(points), np.inf),
        where=normal_squared > 1e-24,
    )
    projection = points - np.divide(
        signed_numerator,
        normal_squared,
        out=np.zeros(len(points), dtype=float),
        where=normal_squared > 1e-24,
    )[:, None] * normal
    projected = projection - a
    dot00 = np.einsum("ij,ij->i", ab, ab)
    dot01 = np.einsum("ij,ij->i", ab, ac)
    dot11 = np.einsum("ij,ij->i", ac, ac)
    dot20 = np.einsum("ij,ij->i", projected, ab)
    dot21 = np.einsum("ij,ij->i", projected, ac)
    denominator = dot00 * dot11 - dot01 * dot01
    coordinate_ab = np.divide(
        dot11 * dot20 - dot01 * dot21,
        denominator,
        out=np.full(len(points), np.inf),
        where=np.abs(denominator) > 1e-24,
    )
    coordinate_ac = np.divide(
        dot00 * dot21 - dot01 * dot20,
        denominator,
        out=np.full(len(points), np.inf),
        where=np.abs(denominator) > 1e-24,
    )
    inside = (
        (coordinate_ab >= -1e-12)
        & (coordinate_ac >= -1e-12)
        & (coordinate_ab + coordinate_ac <= 1.0 + 1e-12)
    )
    edge_distance = np.minimum.reduce([
        point_segment_distances_batch(points, a, b),
        point_segment_distances_batch(points, b, c),
        point_segment_distances_batch(points, c, a),
    ])
    return np.where(inside, plane_distance, edge_distance)


def segment_segment_distances_batch(
    first_a: np.ndarray,
    first_b: np.ndarray,
    second_a: np.ndarray,
    second_b: np.ndarray,
) -> np.ndarray:
    """Vectorized constrained segment distance for matching rows."""
    u, v, w = first_b - first_a, second_b - second_a, first_a - second_a
    a = np.einsum("ij,ij->i", u, u)
    b = np.einsum("ij,ij->i", u, v)
    c = np.einsum("ij,ij->i", v, v)
    d = np.einsum("ij,ij->i", u, w)
    e = np.einsum("ij,ij->i", v, w)
    denominator = a * c - b * b
    s = np.divide(
        b * e - c * d,
        denominator,
        out=np.full(len(a), np.inf),
        where=np.abs(denominator) > 1e-24,
    )
    t = np.divide(
        a * e - b * d,
        denominator,
        out=np.full(len(a), np.inf),
        where=np.abs(denominator) > 1e-24,
    )
    interior = (s >= 0.0) & (s <= 1.0) & (t >= 0.0) & (t <= 1.0)
    safe_s = np.where(interior, s, 0.0)
    safe_t = np.where(interior, t, 0.0)
    line_distance = np.linalg.norm(
        w + safe_s[:, None] * u - safe_t[:, None] * v, axis=1
    )
    line_distance[~interior] = np.inf
    return np.minimum.reduce([
        line_distance,
        point_segment_distances_batch(first_a, second_a, second_b),
        point_segment_distances_batch(first_b, second_a, second_b),
        point_segment_distances_batch(second_a, first_a, first_b),
        point_segment_distances_batch(second_b, first_a, first_b),
    ])


def triangle_distances_batch(first: np.ndarray, second: np.ndarray) -> np.ndarray:
    """Exact distances for matching triangle rows, including edge crossings."""
    distances = [
        point_triangle_distances_batch(first[:, vertex], second)
        for vertex in range(3)
    ]
    distances.extend(
        point_triangle_distances_batch(second[:, vertex], first)
        for vertex in range(3)
    )
    edges = ((0, 1), (1, 2), (2, 0))
    distances.extend(
        segment_segment_distances_batch(
            first[:, a], first[:, b], second[:, c], second[:, d]
        )
        for a, b in edges
        for c, d in edges
    )
    return np.minimum.reduce(distances)


def triangle_distance(first: np.ndarray, second: np.ndarray) -> float:
    return float(triangle_distances_batch(first[None, ...], second[None, ...])[0])


def distance_self_test() -> int:
    base = np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    cases = [
        ("parallel_planes", base + np.asarray([0.0, 0.0, 1.0]), 1.0),
        (
            "coplanar_gap",
            np.asarray([[2.0, 0.0, 0.0], [3.0, 0.0, 0.0], [2.0, 1.0, 0.0]]),
            1.0,
        ),
        (
            "overlap",
            np.asarray([[0.2, 0.2, -1.0], [0.2, 0.2, 1.0], [0.8, 0.2, 0.0]]),
            0.0,
        ),
        (
            "point_face",
            np.asarray([[0.25, 0.25, 0.5], [0.35, 0.25, 0.5], [0.25, 0.35, 0.5]]),
            0.5,
        ),
    ]
    for name, candidate, expected in cases:
        observed = triangle_distance(base, candidate)
        if not np.isclose(observed, expected, atol=1e-10, rtol=0.0):
            raise ValueError(
                f"triangle distance self-test {name}: expected={expected} observed={observed}"
            )
    return len(cases)


def randomized_distance_reference_test(count: int = 300) -> int:
    """Cross-check the vector kernel against the independent scalar routines."""
    generator = np.random.default_rng(600)
    first_batch = generator.normal(size=(count, 3, 3))
    second_batch = generator.normal(size=(count, 3, 3))
    observed = triangle_distances_batch(first_batch, second_batch)
    edges = ((0, 1), (1, 2), (2, 0))
    reference = []
    for first, second in zip(first_batch, second_batch):
        distances = [point_triangle_distance(point, second) for point in first]
        distances.extend(point_triangle_distance(point, first) for point in second)
        distances.extend(
            segment_segment_distance(first[a], first[b], second[c], second[d])
            for a, b in edges
            for c, d in edges
        )
        reference.append(min(distances))
    maximum_error = float(np.max(np.abs(observed - np.asarray(reference))))
    if maximum_error >= 1e-9:
        raise ValueError(f"vector/scalar triangle distance mismatch: {maximum_error}")
    return count


def aabb_distance(first, second) -> float:
    delta = np.maximum(np.maximum(first[0] - second[1], second[0] - first[1]), 0.0)
    return float(np.linalg.norm(delta))


def exact_mesh_distance(
    triangles_a: np.ndarray,
    root_a,
    pose_a: np.ndarray,
    triangles_b: np.ndarray,
    root_b,
    pose_b: np.ndarray,
    mesh_helper,
    epsilon: float,
) -> tuple[float, tuple[int, int], dict[str, int]]:
    """Best-first BVH distance with exact triangle narrow phase."""
    stats = {"node_pair_tests": 0, "leaf_pair_tests": 0, "triangle_distance_tests": 0}
    cache_a: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    cache_b: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    counter = 0
    best = float("inf")
    best_ids = (-1, -1)
    queue: list[tuple[float, int, Any, Any]] = []
    world_triangles_a = mesh_helper.transform_triangles(triangles_a, pose_a)
    world_triangles_b = mesh_helper.transform_triangles(triangles_b, pose_b)
    triangle_low_a = world_triangles_a.min(axis=1)
    triangle_high_a = world_triangles_a.max(axis=1)
    triangle_low_b = world_triangles_b.min(axis=1)
    triangle_high_b = world_triangles_b.max(axis=1)
    pending: list[np.ndarray] = []
    pending_count = 0

    def bounds_a(node):
        return cache_a.setdefault(id(node), mesh_helper.world_aabb(node, pose_a))

    def bounds_b(node):
        return cache_b.setdefault(id(node), mesh_helper.world_aabb(node, pose_b))

    def push(node_a, node_b):
        nonlocal counter
        lower = aabb_distance(bounds_a(node_a), bounds_b(node_b))
        if lower < best:
            counter += 1
            heapq.heappush(queue, (lower, counter, node_a, node_b))

    def flush_pending() -> None:
        nonlocal best, best_ids, pending, pending_count
        if not pending:
            return
        pairs = np.concatenate(pending, axis=0)
        distances = triangle_distances_batch(
            world_triangles_a[pairs[:, 0]], world_triangles_b[pairs[:, 1]]
        )
        closest = int(np.argmin(distances))
        distance = float(distances[closest])
        if distance < best:
            best = distance
            best_ids = (int(pairs[closest, 0]), int(pairs[closest, 1]))
        pending = []
        pending_count = 0

    push(root_a, root_b)
    while queue:
        lower, _, node_a, node_b = heapq.heappop(queue)
        stats["node_pair_tests"] += 1
        if lower >= best:
            flush_pending()
            if lower >= best:
                break
        if node_a.indices is not None and node_b.indices is not None:
            stats["leaf_pair_tests"] += 1
            delta = np.maximum(
                np.maximum(
                    triangle_low_a[node_a.indices][:, None, :]
                    - triangle_high_b[node_b.indices][None, :, :],
                    triangle_low_b[node_b.indices][None, :, :]
                    - triangle_high_a[node_a.indices][:, None, :],
                ),
                0.0,
            )
            candidates = np.argwhere(np.linalg.norm(delta, axis=2) < best)
            if len(candidates):
                stats["triangle_distance_tests"] += int(len(candidates))
                global_pairs = np.column_stack(
                    (
                        node_a.indices[candidates[:, 0]],
                        node_b.indices[candidates[:, 1]],
                    )
                )
                pending.append(global_pairs)
                pending_count += len(global_pairs)
                if not np.isfinite(best) or pending_count >= 2048:
                    flush_pending()
                    if best <= epsilon:
                        return 0.0, best_ids, stats
            continue

        split_a = node_b.indices is not None or (
            node_a.indices is None and node_a.size >= node_b.size
        )
        if split_a:
            assert node_a.left is not None and node_a.right is not None
            push(node_a.left, node_b)
            push(node_a.right, node_b)
        else:
            assert node_b.left is not None and node_b.right is not None
            push(node_a, node_b.left)
            push(node_a, node_b.right)
    flush_pending()
    if not np.isfinite(best):
        raise ValueError("BVH distance search did not reach a leaf pair")
    return best, best_ids, stats


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
    return [path_helper.checkpoint_to_meta(sample) for sample in samples]


def derive_guard_contract(
    profile: dict[str, Any],
    pair_results: list[dict[str, Any]],
) -> dict[str, Any]:
    commanded_count = len(profile["commanded_joint_names"])
    dt = float(profile["point_dt_seconds"])
    speeds = [float(value) for value in profile["max_interpoint_speed"][:commanded_count]]
    first_deltas = [
        float(value) for value in profile["max_first_point_delta"][:commanded_count]
    ]
    effective_deltas = [min(delta, speed * dt) for delta, speed in zip(first_deltas, speeds)]
    minimum = min(result["minimum_sampled_clearance_m"] for result in pair_results)
    missing = [
        "certified_joint_acceleration_limits_rad_s2",
        "certified_force_or_current_limits",
        "installed_passive_clamp_collision_geometry",
        "model_calibration_and_flex_tolerance_m",
        "continuous_time_collision_clearance_proof",
        "reviewed_physical_command_transport_and_stop_semantics",
    ]
    return {
        "schema": "cruzr-s2-vla-offline-executor-guard-contract-e6.0d-v1",
        "experiment_id": "E6.0D",
        "state": "SPECIFICATION_ONLY_FAIL_CLOSED",
        "physical_execution_enabled": False,
        "publisher_or_command_topic": None,
        "scenario": "NO_BOX_READY",
        "task_id": 0,
        "axis_profile": "P14_A",
        "maximum_canary_point_count": 1,
        "commanded_joint_names": profile["commanded_joint_names"],
        "locked_joint_names": profile["locked_joint_names"],
        "locked_axis_policy": "capture_fresh_runtime_state_then_hold_exactly",
        "maximum_state_age_seconds": float(profile["max_state_age_seconds"]),
        "candidate_point_dt_seconds": dt,
        "profile_max_speed_rad_s_not_certified": speeds,
        "profile_max_first_delta_rad_not_certified": first_deltas,
        "derived_effective_first_delta_rad_not_certified": effective_deltas,
        "derived_delta_formula": "min(profile_first_delta, profile_speed * point_dt)",
        "maximum_acceleration_rad_s2": None,
        "force_or_current_limit": None,
        "sampled_vendor_mesh_minimum_clearance_m": minimum,
        "required_physical_clearance_m": None,
        "model_calibration_and_flex_tolerance_m": None,
        "sample_count": 401,
        "continuous_path_certified": False,
        "installed_passive_clamp_geometry_present": False,
        "hard_fail_conditions": missing,
        "offline_validation_requirements": [
            "exactly_20_finite_input_axes",
            "exactly_14_commanded_arm_axes",
            "fresh_20d_state_and_exact_hold_of_H_L_W",
            "all_axes_inside_profile_support_envelope",
            "one_output_point_only",
            "effective_first_delta_and_speed_checks",
            "all_four_upstream_pair_clearances_above_zero_in_sampled_vendor_meshes",
        ],
        "not_authorized_reason": (
            "measured vendor-mesh sampled clearance cannot supply the missing physical "
            "tolerance, passive-clamp geometry, acceleration/force limits or transport semantics"
        ),
    }


def analyze_pair_worker(pair: tuple[str, str]) -> dict[str, Any]:
    context = _PAIR_WORKER_CONTEXT
    left, right = pair
    unique_state_count = context["unique_state_count"]
    unique_distances = []
    sample_details = []
    totals = {"node_pair_tests": 0, "leaf_pair_tests": 0, "triangle_distance_tests": 0}
    for sample_index, state in enumerate(context["states"][:unique_state_count]):
        poses = context["fk_helper"].forward_kinematics(context["joints"], state)
        distance, triangle_ids, stats = exact_mesh_distance(
            context["triangles"][left], context["roots"][left], poses[left],
            context["triangles"][right], context["roots"][right], poses[right],
            context["mesh_helper"], context["epsilon_m"],
        )
        unique_distances.append(distance)
        sample_details.append((distance, sample_index, triangle_ids))
        for key, value in stats.items():
            totals[key] += value
    full_distances = unique_distances + list(reversed(unique_distances[:-1]))
    if len(full_distances) != 401:
        raise AssertionError(len(full_distances))
    minimum, minimum_sample, triangle_ids = min(sample_details, key=lambda item: item[0])
    values = np.asarray(full_distances)
    return {
        "left": left,
        "right": right,
        "minimum_sampled_clearance_m": minimum,
        "minimum_sample_index_first_half": minimum_sample,
        "minimum_triangle_ids": list(triangle_ids),
        "median_sampled_clearance_m": float(np.median(values)),
        "maximum_sampled_clearance_m": float(values.max()),
        "sample_count": len(full_distances),
        "unique_state_count_computed": unique_state_count,
        "zero_or_epsilon_clearance_sample_count": int(
            np.sum(values <= context["epsilon_m"])
        ),
        **totals,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--e6-0c-report", type=Path, required=True)
    parser.add_argument("--ready-contract", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--sdk-urdf", type=Path, required=True)
    parser.add_argument("--sdk-urdf-zip", type=Path, required=True)
    parser.add_argument("--fk-helper", type=Path, required=True)
    parser.add_argument("--path-helper", type=Path, required=True)
    parser.add_argument("--mesh-helper", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--guard-output", type=Path)
    parser.add_argument("--epsilon-m", type=float, default=1e-8)
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()

    sources = (
        args.e6_0c_report, args.ready_contract, args.profile, args.sdk_urdf,
        args.sdk_urdf_zip, args.fk_helper, args.path_helper, args.mesh_helper,
    )
    for path in sources:
        if not path.is_file():
            raise SystemExit(f"ERROR: falta fuente: {path}")
    if not 0.0 < args.epsilon_m <= 1e-5:
        raise SystemExit("ERROR: --epsilon-m fuera de (0,1e-5]")
    if not 1 <= args.jobs <= 4:
        raise SystemExit("ERROR: --jobs debe estar entre 1 y 4")

    mesh_helper = load_module(args.mesh_helper, "e6_0c_mesh_helper")
    fk_helper = load_module(args.fk_helper, "e4_1c_fk_helper")
    path_helper = load_module(args.path_helper, "e6_0b_path_helper")
    self_tests = distance_self_test()
    randomized_self_tests = randomized_distance_reference_test()

    e6_0c = json.loads(args.e6_0c_report.read_text(encoding="utf-8"))
    if e6_0c.get("schema") != "cruzr-s2-vla-near-pair-mesh-e6.0c-v1":
        raise SystemExit("ERROR: esquema E6.0C inesperado")
    if e6_0c["exact_mesh_sweep"]["collision_samples"]:
        raise SystemExit("ERROR: E6.0C contiene intersecciones; no procede medir holgura")
    selected_pairs = sorted(
        (pair["left"], pair["right"])
        for pair in e6_0c["near_pair_partition"]["moving_upstream_exactly_tested"]
    )
    if len(selected_pairs) != 4:
        raise SystemExit(f"ERROR: se esperaban cuatro pares: {selected_pairs}")

    joints, _, triangles = fk_helper.load_robot(args.sdk_urdf, args.sdk_urdf_zip)
    contract = json.loads(args.ready_contract.read_text(encoding="utf-8"))
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    meta_samples = build_path(contract, path_helper)
    if len(meta_samples) != 401:
        raise SystemExit(f"ERROR: path no tiene 401 muestras: {len(meta_samples)}")
    states = [fk_helper.arm_state(sample) for sample in meta_samples]
    required_links = sorted({link for pair in selected_pairs for link in pair})
    roots = {
        link: mesh_helper.BvhNode(mesh, np.arange(len(mesh), dtype=np.int64))
        for link, mesh in triangles.items() if link in required_links
    }
    if set(roots) != set(required_links):
        raise SystemExit(f"ERROR: faltan mallas: {sorted(set(required_links) - set(roots))}")

    # The path is exactly A->B followed by B->A, so samples 201..400 mirror
    # 199..0.  Compute 201 unique states and expand the audit back to 401.
    unique_state_count = 201
    _PAIR_WORKER_CONTEXT.update({
        "unique_state_count": unique_state_count,
        "states": states,
        "fk_helper": fk_helper,
        "joints": joints,
        "triangles": triangles,
        "roots": roots,
        "mesh_helper": mesh_helper,
        "epsilon_m": args.epsilon_m,
    })
    if args.jobs == 1:
        pair_results = [analyze_pair_worker(pair) for pair in selected_pairs]
    else:
        with multiprocessing.get_context("fork").Pool(
            processes=min(args.jobs, len(selected_pairs))
        ) as pool:
            pair_results = pool.map(analyze_pair_worker, selected_pairs)
    overall_minimum = min(
        result["minimum_sampled_clearance_m"] for result in pair_results
    )

    guard = derive_guard_contract(profile, pair_results)
    failed = overall_minimum <= args.epsilon_m
    status = (
        "FAIL_VENDOR_MESH_SAMPLED_CLEARANCE_NONPOSITIVE"
        if failed else
        "PASS_VENDOR_MESH_SAMPLED_CLEARANCE_QUANTIFIED_PHYSICAL_BLOCKED"
    )
    report = {
        "schema": "cruzr-s2-vla-clearance-guards-e6.0d-v1",
        "experiment_id": "E6.0D",
        "mode": "local_exact_distance_and_guard_derivation_no_robot_no_network_no_ros_no_publisher",
        "status": status,
        "source_sha256": {path.name: sha256(path) for path in sources},
        "trajectory_sample_count": 401,
        "unique_state_count_computed": unique_state_count,
        "parallel_pair_workers": min(args.jobs, len(selected_pairs)),
        "symmetry_expansion": "samples 201..400 mirror samples 199..0",
        "triangle_distance_self_tests_passed": self_tests,
        "triangle_distance_randomized_reference_tests_passed": randomized_self_tests,
        "algorithm": "best-first STL BVH AABB lower bounds plus exact triangle distance",
        "epsilon_m": args.epsilon_m,
        "pairs": pair_results,
        "overall_minimum_sampled_vendor_mesh_clearance_m": overall_minimum,
        "interpretation": {
            "sampled_vendor_mesh_clearance_quantified": not failed,
            "continuous_path_certified": False,
            "physical_clearance_certified": False,
            "installed_passive_clamps_modeled": False,
            "model_calibration_flex_tolerance_available": False,
        },
        "guard_contract": guard,
        "blocking_gates": guard["hard_fail_conditions"],
        "physical_authorized": False,
        "robot_state_read": False,
        "network_calls": 0,
        "physical_publishers": 0,
        "physical_movement_commanded": False,
        "next_safe_work": (
            "obtain_or_measure_clamp_geometry_and_certified_dynamics_then implement "
            "the guard evaluator without any physical publisher"
        ),
    }
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    if args.guard_output:
        args.guard_output.parent.mkdir(parents=True, exist_ok=True)
        args.guard_output.write_text(
            json.dumps(guard, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(f"E6.0D_MODE={report['mode']}")
    print(f"E6.0D_TRAJECTORY_SAMPLES={report['trajectory_sample_count']}")
    print(f"E6.0D_UNIQUE_STATES_COMPUTED={unique_state_count}")
    print(f"E6.0D_TRIANGLE_DISTANCE_SELF_TESTS={self_tests}")
    print(f"E6.0D_RANDOMIZED_REFERENCE_TESTS={randomized_self_tests}")
    for result in pair_results:
        print(
            "E6.0D_PAIR="
            f"{result['left']}:{result['right']},"
            f"minimum_m:{result['minimum_sampled_clearance_m']:.9f},"
            f"sample:{result['minimum_sample_index_first_half']},"
            f"triangle_tests:{result['triangle_distance_tests']}"
        )
    print(f"E6.0D_OVERALL_MINIMUM_M={overall_minimum:.9f}")
    print("E6.0D_CONTINUOUS_PATH_CERTIFIED=0")
    print("E6.0D_GUARD_CONTRACT=SPECIFICATION_ONLY_FAIL_CLOSED")
    print("E6.0D_PHYSICAL_AUTHORIZED=0")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
