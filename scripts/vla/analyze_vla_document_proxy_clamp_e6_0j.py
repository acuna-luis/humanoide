#!/usr/bin/env python3
"""Audit the complete no-box ready/recovery path with a documented clamp proxy.

The installed passive clamp has no published CAD or dimensions.  At the
project owner's direction, this local-only audit substitutes a deliberately
larger envelope derived from the supplier PGC URDF group and the documented
50 mm stroke.  It never connects to ROS or a robot and never authorizes
physical execution.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

import numpy as np


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


def interpolate_states(start: dict[str, float], end: dict[str, float], count: int):
    names = sorted(set(start) | set(end))
    for alpha in np.linspace(0.0, 1.0, count):
        yield {
            name: float((1.0 - alpha) * start.get(name, 0.0) + alpha * end.get(name, 0.0))
            for name in names
        }


def transform_points(points: np.ndarray, pose: np.ndarray) -> np.ndarray:
    return points @ pose[:3, :3].T + pose[:3, 3]


def bounds_corners(low: np.ndarray, high: np.ndarray) -> np.ndarray:
    return np.asarray(
        [[x, y, z] for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])],
        dtype=float,
    )


def box_triangles(low: np.ndarray, high: np.ndarray) -> np.ndarray:
    points = bounds_corners(low, high)
    # bounds_corners order is binary xyz: 000,001,010,011,100,101,110,111.
    faces = (
        (0, 1, 3, 2), (4, 6, 7, 5),
        (0, 4, 5, 1), (2, 3, 7, 6),
        (0, 2, 6, 4), (1, 5, 7, 3),
    )
    triangles = []
    for a, b, c, d in faces:
        triangles.extend((points[[a, b, c]], points[[a, c, d]]))
    return np.asarray(triangles, dtype=float)


def path_states(home: dict[str, float], contract: dict[str, Any], fk, path_helper):
    arms = contract["arm_path_checkpoint_order"]
    named: list[tuple[str, dict[str, float]]] = [("measured_home", dict(home))]
    for label, key in (
        ("staging", "staging_preposition"),
        ("waypoint_a", "waypoint_a"),
        ("ready_b", "ready_b"),
        ("waypoint_a_recovery", "waypoint_a"),
        ("staging_recovery", "staging_preposition"),
    ):
        state = dict(home)
        state.update(fk.arm_state(path_helper.checkpoint_to_meta(arms[key])))
        state["head_pitch_joint"] = 0.0
        state["head_yaw_joint"] = -0.65
        state["waist_yaw_joint"] = 0.0
        named.append((label, state))
    named.append(("measured_home_recovery", dict(home)))

    states: list[dict[str, float]] = []
    segments = []
    for segment_index, ((start_name, start), (end_name, end)) in enumerate(zip(named, named[1:])):
        samples = list(interpolate_states(start, end, 201))
        if segment_index:
            samples = samples[1:]
        first = len(states)
        states.extend(samples)
        segments.append({
            "name": f"{start_name}_to_{end_name}",
            "first_sample": first,
            "last_sample": len(states) - 1,
        })
    return states, segments


def derive_proxy_bounds(side: str, poses, bounds, fk, dilation: np.ndarray):
    mount = f"{side}_sixforce_link"
    mount_inverse = np.linalg.inv(poses[mount])
    pieces = []
    for suffix in ("pgc_base_link", "finger1_link", "finger2_link"):
        link = f"{side}_{suffix}"
        local = bounds_corners(*bounds[link])
        world = transform_points(local, poses[link])
        pieces.append(transform_points(world, mount_inverse))
    points = np.vstack(pieces)
    raw_low, raw_high = points.min(axis=0), points.max(axis=0)
    return raw_low - dilation, raw_high + dilation, raw_low, raw_high


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--proxy-contract", type=Path, required=True)
    parser.add_argument("--official-contract", type=Path, required=True)
    parser.add_argument("--actuator-state", type=Path, required=True)
    parser.add_argument("--ready-contract", type=Path, required=True)
    parser.add_argument("--sdk-urdf", type=Path, required=True)
    parser.add_argument("--sdk-urdf-zip", type=Path, required=True)
    parser.add_argument("--fk-helper", type=Path, required=True)
    parser.add_argument("--path-helper", type=Path, required=True)
    parser.add_argument("--mesh-helper", type=Path, required=True)
    parser.add_argument("--home-helper", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--epsilon-m", type=float, default=1e-8)
    args = parser.parse_args()

    sources = (
        args.proxy_contract, args.official_contract, args.actuator_state,
        args.ready_contract, args.sdk_urdf, args.sdk_urdf_zip, args.fk_helper,
        args.path_helper, args.mesh_helper, args.home_helper,
    )
    for path in sources:
        if not path.is_file():
            raise SystemExit(f"ERROR: falta fuente: {path}")

    proxy_contract = json.loads(args.proxy_contract.read_text(encoding="utf-8"))
    if proxy_contract.get("schema") != "cruzr-s2-document-proxy-clamp/e6.0j-v1":
        raise SystemExit("ERROR: contrato proxy inesperado")
    fk = load_module(args.fk_helper, "e6_0j_fk")
    path_helper = load_module(args.path_helper, "e6_0j_path")
    mesh = load_module(args.mesh_helper, "e6_0j_mesh")
    home_helper = load_module(args.home_helper, "e6_0j_home")
    home, home_metrics = home_helper.actuator_home(args.actuator_state)
    ready = json.loads(args.ready_contract.read_text(encoding="utf-8"))
    states, segments = path_states(home, ready, fk, path_helper)

    joints, bounds, triangles = fk.load_robot(args.sdk_urdf, args.sdk_urdf_zip)
    violations = path_helper.limit_violations(joints, states, args.sdk_urdf)
    zero_poses = fk.forward_kinematics(joints, {})
    dilation = np.asarray(
        proxy_contract["conservative_proxy_rule"]["dilation_m_per_face_xyz"], dtype=float
    )
    if dilation.shape != (3,) or np.any(dilation <= 0.0):
        raise SystemExit("ERROR: dilatación proxy inválida")

    proxy: dict[str, dict[str, Any]] = {}
    official_body = np.sort(np.asarray(
        proxy_contract["documented_sources"]["pgc_body_size_lwh_m"], dtype=float
    ))
    for side in ("L", "R"):
        low, high, raw_low, raw_high = derive_proxy_bounds(
            side, zero_poses, bounds, fk, dilation
        )
        if np.any(np.sort(high - low) + 1e-12 < official_body):
            raise SystemExit(f"ERROR: proxy {side} menor que cuerpo PGC documentado")
        local_triangles = box_triangles(low, high)
        proxy[side] = {
            "mount": f"{side}_sixforce_link",
            "low": low,
            "high": high,
            "raw_low": raw_low,
            "raw_high": raw_high,
            "triangles": local_triangles,
            "root": mesh.BvhNode(local_triangles, np.arange(len(local_triangles), dtype=np.int64)),
        }

    wrong_effector_links = {link for link in bounds if "pgc" in link or "finger" in link}
    mount_suffixes = proxy_contract["collision_policy"][
        "allowed_same_side_mount_chain_suffixes"
    ]
    expected_mount_suffixes = {"sixforce_link", "wrist_roll_link", "wrist_pitch_link"}
    if set(mount_suffixes) != expected_mount_suffixes:
        raise SystemExit(f"ERROR: política de montaje proxy inesperada: {mount_suffixes}")
    allowed_mount_contact = {
        side: {f"{side}_{suffix}" for suffix in mount_suffixes}
        for side in ("L", "R")
    }
    link_roots = {
        link: mesh.BvhNode(data, np.arange(len(data), dtype=np.int64))
        for link, data in triangles.items()
        if link not in wrong_effector_links
    }

    candidate_hits: dict[tuple[str, str], dict[str, Any]] = {}
    exact_intersections: list[dict[str, Any]] = []
    proxy_pair_hits = 0
    maximum_joint_step = 0.0
    previous = None
    for sample_index, state in enumerate(states):
        if previous is not None:
            maximum_joint_step = max(
                maximum_joint_step,
                max(abs(state.get(name, 0.0) - previous.get(name, 0.0)) for name in state),
            )
        previous = state
        poses = fk.forward_kinematics(joints, state)
        robot_boxes = {
            link: path_helper.obb_for_link(poses[link], local_bounds)
            for link, local_bounds in bounds.items()
            if link not in wrong_effector_links
        }
        proxy_boxes = {
            side: path_helper.obb_for_link(
                poses[item["mount"]], (item["low"], item["high"])
            )
            for side, item in proxy.items()
        }
        if path_helper.obb_overlap(proxy_boxes["L"], proxy_boxes["R"]):
            proxy_pair_hits += 1
            left, right = proxy["L"], proxy["R"]
            intersects, _, triangle_ids = mesh.mesh_intersection(
                left["triangles"], left["root"], poses[left["mount"]],
                right["triangles"], right["root"], poses[right["mount"]], args.epsilon_m,
            )
            if intersects:
                exact_intersections.append({
                    "sample_index": sample_index,
                    "left": "L_document_proxy_clamp",
                    "right": "R_document_proxy_clamp",
                    "triangle_ids": triangle_ids,
                })

        for side, item in proxy.items():
            for link, robot_box in robot_boxes.items():
                if link in allowed_mount_contact[side]:
                    continue
                if not path_helper.obb_overlap(proxy_boxes[side], robot_box):
                    continue
                key = (f"{side}_document_proxy_clamp", link)
                hit = candidate_hits.setdefault(key, {
                    "proxy": key[0], "robot_link": link,
                    "first_sample": sample_index, "last_sample": sample_index,
                    "sample_hits": 0, "exact_intersection_hits": 0,
                })
                hit["last_sample"] = sample_index
                hit["sample_hits"] += 1
                intersects, _, triangle_ids = mesh.mesh_intersection(
                    item["triangles"], item["root"], poses[item["mount"]],
                    triangles[link], link_roots[link], poses[link], args.epsilon_m,
                )
                if intersects:
                    hit["exact_intersection_hits"] += 1
                    exact_intersections.append({
                        "sample_index": sample_index,
                        "left": key[0], "right": link,
                        "triangle_ids": triangle_ids,
                    })

    failed = bool(violations or exact_intersections)
    dimensions = {
        side: {
            "raw_vendor_group_bounds_m": [item["raw_low"].tolist(), item["raw_high"].tolist()],
            "raw_vendor_group_size_xyz_m": (item["raw_high"] - item["raw_low"]).tolist(),
            "dilated_proxy_bounds_m": [item["low"].tolist(), item["high"].tolist()],
            "dilated_proxy_size_xyz_m": (item["high"] - item["low"]).tolist(),
            "mount_frame": item["mount"],
        }
        for side, item in proxy.items()
    }
    report = {
        "schema": "cruzr-s2-vla-document-proxy-clamp-e6.0j-v1",
        "experiment_id": "E6.0J",
        "mode": "local_document_proxy_sweep_no_robot_no_network_no_ros_no_publisher",
        "status": (
            "FAIL_DOCUMENT_PROXY_INTERSECTS_VENDOR_ROBOT_MODEL"
            if failed else
            "PASS_DOCUMENT_PROXY_SAMPLED_SWEEP_ASSUMPTION_ACCEPTED_PHYSICAL_NOT_CERTIFIED"
        ),
        "source_sha256": {path.name: sha256(path) for path in sources},
        "fresh_home_snapshot_inherited_from_e6_0i": home_metrics,
        "owner_assumption": proxy_contract["decision"],
        "proxy": {
            "derivation": proxy_contract["conservative_proxy_rule"],
            "dimensions": dimensions,
            "documented_pgc_body_size_lwh_m": proxy_contract["documented_sources"]["pgc_body_size_lwh_m"],
            "documented_pgc_stroke_m": proxy_contract["documented_sources"]["pgc_stroke_m"],
            "exact_installed_clamp_geometry": False,
            "collision_policy": proxy_contract["collision_policy"],
        },
        "trajectory": {
            "sample_count": len(states),
            "segments": segments,
            "maximum_inter_sample_joint_step_rad": maximum_joint_step,
            "joint_limit_violations": violations,
        },
        "collision_audit": {
            "wrong_pgc_links_replaced_by_proxy": sorted(wrong_effector_links),
            "allowed_mount_contacts": {
                side: sorted(links) for side, links in allowed_mount_contact.items()
            },
            "proxy_proxy_obb_candidate_samples": proxy_pair_hits,
            "proxy_robot_obb_candidate_pairs": list(candidate_hits.values()),
            "exact_intersection_count": len(exact_intersections),
            "exact_intersections": exact_intersections[:50],
        },
        "interpretation": {
            "sampled_document_proxy_clear": not failed,
            "continuous_path_certified": False,
            "installed_clamp_geometry_certified": False,
            "mass_center_of_gravity_force_flex_certified": False,
        },
        "remaining_blocking_gates": [
            "certified_acceleration_and_force_limits",
            "physical_ready_and_recovery_validation",
            "physical_executor_and_temporal_semantics",
        ],
        "robot_state_read": False,
        "network_calls": 0,
        "physical_publishers": 0,
        "physical_movement_commanded": False,
        "physical_authorized": False,
    }
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(f"E6.0J_STATUS={report['status']}")
    print(f"E6.0J_SAMPLES={len(states)}")
    print(f"E6.0J_MAX_INTER_SAMPLE_JOINT_STEP_RAD={maximum_joint_step:.9f}")
    for side in ("L", "R"):
        size = dimensions[side]["dilated_proxy_size_xyz_m"]
        print(f"E6.0J_{side}_PROXY_SIZE_XYZ_M=" + ",".join(f"{value:.9f}" for value in size))
    print(f"E6.0J_OBB_CANDIDATE_PAIRS={len(candidate_hits)}")
    print(f"E6.0J_EXACT_INTERSECTIONS={len(exact_intersections)}")
    print("E6.0J_PHYSICAL_AUTHORIZED=0")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
