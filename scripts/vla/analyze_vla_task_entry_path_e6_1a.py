#!/usr/bin/env python3
"""Audit a task-matched 20D HOME <-> ENTRY candidate without a robot.

The program freezes one supplied-dataset frame, reconstructs its approximate
SUPPORTED_LOW fixture from the frozen RGB frame and calibrated camera, plans a
minimum-jerk 20-axis transition, and samples robot/clamp/fixture collision
geometry.  It deliberately has no ROS, network, process or publisher code.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np


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
EXPECTED_NEAR_PAIRS = {
    ("L_elbow_yaw_link", "L_wrist_roll_link"),
    ("R_elbow_yaw_link", "R_wrist_roll_link"),
    ("L_shoulder_roll_link", "torso_link"),
    ("R_shoulder_roll_link", "torso_link"),
}
WRONG_EFFECTOR_TOKENS = ("pgc", "finger")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entry-contract", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--candidate-rgb", type=Path, required=True)
    parser.add_argument("--dataset-entry-report", type=Path, required=True)
    parser.add_argument("--dataset-info", type=Path, required=True)
    parser.add_argument("--task-contract", type=Path, required=True)
    parser.add_argument("--historical-home", type=Path, required=True)
    parser.add_argument("--camera-info", type=Path, required=True)
    parser.add_argument("--tf-static", type=Path, required=True)
    parser.add_argument("--metric-fixture-summary", type=Path, required=True)
    parser.add_argument("--sdk-urdf", type=Path, required=True)
    parser.add_argument("--sdk-urdf-zip", type=Path, required=True)
    parser.add_argument("--document-proxy-report", type=Path, required=True)
    parser.add_argument("--observed-clamp-report", type=Path, required=True)
    parser.add_argument("--fk-helper", type=Path, required=True)
    parser.add_argument("--path-helper", type=Path, required=True)
    parser.add_argument("--mesh-helper", type=Path, required=True)
    parser.add_argument("--geometry-helper", type=Path, required=True)
    parser.add_argument("--fixture-pose-helper", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"no se pudo cargar helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def finite_vector(value: Any, count: int, label: str) -> list[float]:
    if not isinstance(value, list) or len(value) != count:
        raise ValueError(f"{label}: dimensión distinta de {count}")
    result = [float(item) for item in value]
    if not all(math.isfinite(item) for item in result):
        raise ValueError(f"{label}: valor no finito")
    return result


def measured_home(path: Path, order: list[str]) -> tuple[dict[str, float], dict[str, Any]]:
    message = json.loads(path.read_text(encoding="utf-8"))
    items = {int(item.get("id", -1)): item for item in message.get("act_item", [])}
    missing = sorted(set(BODY_IDS) - set(items))
    if missing:
        raise ValueError(f"historical HOME incompleto: {missing}")
    state: dict[str, float] = {}
    maximum_position = maximum_velocity = maximum_command_delta = 0.0
    for actuator_id, name in BODY_IDS.items():
        item = items[actuator_id]
        position = float(item["position"])
        velocity = float(item["velocity"])
        command = float(item.get("cmd_pos", position))
        status = int(item.get("status", 0))
        error = int(item.get("error_code", 0))
        if not all(math.isfinite(value) for value in (position, velocity, command)):
            raise ValueError(f"HOME no finito: {actuator_id}")
        if error or status & 0x0008 or status & 0x0007 != 0x0007:
            raise ValueError(f"HOME no sano: {actuator_id}")
        if abs(position) >= 0.02 or abs(velocity) > 0.02 or abs(command - position) > 0.01:
            raise ValueError(f"snapshot histórico no es HOME inmóvil: {actuator_id}")
        state[name] = position
        maximum_position = max(maximum_position, abs(position))
        maximum_velocity = max(maximum_velocity, abs(velocity))
        maximum_command_delta = max(maximum_command_delta, abs(command - position))
    if set(state) != set(order):
        raise ValueError("orden 20D no coincide con los 20 actuadores HOME")
    return state, {
        "source_is_historical_offline_only": True,
        "axis_count": 20,
        "maximum_absolute_position_rad": maximum_position,
        "maximum_absolute_velocity_rad_s": maximum_velocity,
        "maximum_absolute_command_delta_rad": maximum_command_delta,
    }


def minimum_jerk_metrics(
    start: list[float], target: list[float], design: dict[str, Any]
) -> dict[str, Any]:
    velocity_limit = float(design["maximum_velocity_rad_s_all_20_axes"])
    acceleration_limit = float(design["maximum_acceleration_rad_s2_all_20_axes"])
    dt = float(design["sample_period_seconds"])
    delta = np.asarray(target, dtype=float) - np.asarray(start, dtype=float)
    duration = max(
        float(design["minimum_duration_seconds"]),
        *(1.875 * abs(value) / velocity_limit for value in delta),
        *(math.sqrt(5.773502691896258 * abs(value) / acceleration_limit) for value in delta),
    )
    steps = math.ceil(duration / dt)
    duration = steps * dt
    maximum_v = maximum_a = maximum_discrete_v = maximum_discrete_a = 0.0
    positions: list[np.ndarray] = []
    velocities: list[np.ndarray] = []
    for step in range(steps + 1):
        scale = step / steps
        s = 10.0 * scale**3 - 15.0 * scale**4 + 6.0 * scale**5
        ds = 30.0 * scale**2 - 60.0 * scale**3 + 30.0 * scale**4
        dds = 60.0 * scale - 180.0 * scale**2 + 120.0 * scale**3
        position = np.asarray(start) + delta * s
        velocity = delta * ds / duration
        acceleration = delta * dds / duration**2
        positions.append(position)
        velocities.append(velocity)
        maximum_v = max(maximum_v, float(np.max(np.abs(velocity))))
        maximum_a = max(maximum_a, float(np.max(np.abs(acceleration))))
    for first, second in zip(positions, positions[1:]):
        maximum_discrete_v = max(
            maximum_discrete_v, float(np.max(np.abs((second - first) / dt)))
        )
    for first, second in zip(velocities, velocities[1:]):
        maximum_discrete_a = max(
            maximum_discrete_a, float(np.max(np.abs((second - first) / dt)))
        )
    return {
        "law": design["law"],
        "duration_seconds_each_direction": duration,
        "round_trip_duration_seconds": 2.0 * duration,
        "frame_count_each_direction": steps + 1,
        "sample_period_seconds": dt,
        "maximum_absolute_target_delta_rad": float(np.max(np.abs(delta))),
        "maximum_delta_joint_index": int(np.argmax(np.abs(delta))),
        "analytic_maximum_velocity_rad_s": maximum_v,
        "analytic_maximum_acceleration_rad_s2": maximum_a,
        "discrete_maximum_velocity_rad_s": maximum_discrete_v,
        "discrete_maximum_acceleration_rad_s2": maximum_discrete_a,
        "velocity_limit_rad_s": velocity_limit,
        "acceleration_limit_rad_s2": acceleration_limit,
        "passes_design_envelope": (
            maximum_v <= velocity_limit + 1e-12
            and maximum_a <= acceleration_limit + 1e-12
            and maximum_discrete_v <= velocity_limit + 1e-12
            and maximum_discrete_a <= acceleration_limit + 1e-9
        ),
        "manufacturer_certified": False,
        "owner_accepted_for_physical_e6_1": False,
    }


def interpolate_states(
    start: dict[str, float], target: dict[str, float], order: list[str], count: int
) -> list[dict[str, float]]:
    return [
        {
            name: float((1.0 - alpha) * start[name] + alpha * target[name])
            for name in order
        }
        for alpha in np.linspace(0.0, 1.0, count)
    ]


def solve_rim_plane(fixture, k_inverse, camera_pose, rim, known_width):
    low = -0.5
    high = float(camera_pose[2, 3]) - 0.001
    for _ in range(80):
        height = (low + high) / 2.0
        left = fixture.intersect_pixel(k_inverse, camera_pose, rim[0], height)
        right = fixture.intersect_pixel(k_inverse, camera_pose, rim[1], height)
        if float(np.linalg.norm(right - left)) > known_width:
            low = height
        else:
            high = height
    height = (low + high) / 2.0
    left = fixture.intersect_pixel(k_inverse, camera_pose, rim[0], height)
    right = fixture.intersect_pixel(k_inverse, camera_pose, rim[1], height)
    return height, left, right


def fixture_reconstruction(
    contract: dict[str, Any], candidate_state: dict[str, float], args, fixture
) -> tuple[dict[str, Any], np.ndarray, list[np.ndarray]]:
    scene = contract["scene_reconstruction"]
    camera_info = json.loads(args.camera_info.read_text(encoding="utf-8"))
    intrinsic = np.asarray(camera_info["k"], dtype=float).reshape(3, 3)
    edges = fixture.urdf_edges(args.sdk_urdf, candidate_state)
    base_head = fixture.compose_chain(edges, "base_link", "head_pitch_link")
    static_edges, _ = fixture.tf_edges(args.tf_static)
    head_camera = fixture.compose_chain(
        static_edges, "head_pitch_link", "stereo_left_rectified_optical_frame"
    )
    base_camera = base_head @ head_camera
    rim = [np.asarray(item, dtype=float) for item in scene["back_rim_pixels_uv"]]
    width, depth, height = map(float, scene["box_lwh_m"])
    top_z, left, right = solve_rim_plane(
        fixture, np.linalg.inv(intrinsic), base_camera, rim, width
    )
    support_z = top_z - height
    front, x_axis, y_axis, yaw, far_center = fixture.fixture_from_rim(
        left, right, support_z, depth, float(scene["box_front_clearance_m"])
    )
    pose = np.eye(4)
    pose[:3, 0] = x_axis
    pose[:3, 1] = y_axis
    pose[:3, 2] = [0.0, 0.0, 1.0]
    pose[:3, 3] = front

    metric = json.loads(args.metric_fixture_summary.read_text(encoding="utf-8"))
    floor_offset = (
        float(metric["fixture"]["surface_height_floor_m"])
        - float(metric["platform_in_base"]["z_m"])
    )
    uncertainty = float(scene["pixel_uncertainty_per_coordinate_px"])
    variants: list[np.ndarray] = []
    variant_values = []
    for du_left, dv_left, du_right, dv_right in itertools.product(
        (-uncertainty, uncertainty), repeat=4
    ):
        varied_rim = (
            rim[0] + np.asarray([du_left, dv_left]),
            rim[1] + np.asarray([du_right, dv_right]),
        )
        varied_top, varied_left, varied_right = solve_rim_plane(
            fixture, np.linalg.inv(intrinsic), base_camera, varied_rim, width
        )
        varied_support = varied_top - height
        varied_front, varied_x, varied_y, varied_yaw, _ = fixture.fixture_from_rim(
            varied_left,
            varied_right,
            varied_support,
            depth,
            float(scene["box_front_clearance_m"]),
        )
        varied_pose = np.eye(4)
        varied_pose[:3, 0] = varied_x
        varied_pose[:3, 1] = varied_y
        varied_pose[:3, 2] = [0.0, 0.0, 1.0]
        varied_pose[:3, 3] = varied_front
        variants.append(varied_pose)
        variant_values.append(
            [*varied_front.tolist(), varied_yaw, varied_support + floor_offset]
        )
    array = np.asarray(variant_values)
    reconstruction = {
        "method": scene["method"],
        "camera_frame": camera_info["header"]["frame_id"],
        "camera_position_in_base_m": base_camera[:3, 3].tolist(),
        "back_rim_pixels_uv": [item.tolist() for item in rim],
        "pixel_uncertainty_per_coordinate_px": uncertainty,
        "reconstructed_rim_width_m": float(np.linalg.norm(right - left)),
        "box_lwh_m": [width, depth, height],
        "box_top_height_base_m": top_z,
        "support_surface_height_base_m": support_z,
        "base_floor_offset_m": floor_offset,
        "inferred_support_surface_height_floor_m": support_z + floor_offset,
        "platform_front_center_in_base_m": front.tolist(),
        "platform_yaw_rad": yaw,
        "far_rim_center_in_base_m": far_center.tolist(),
        "uncertainty_variant_count": len(variants),
        "uncertainty_ranges": {
            "front_center_base_min_m": array[:, :3].min(axis=0).tolist(),
            "front_center_base_max_m": array[:, :3].max(axis=0).tolist(),
            "yaw_min_rad": float(array[:, 3].min()),
            "yaw_max_rad": float(array[:, 3].max()),
            "support_height_floor_min_m": float(array[:, 4].min()),
            "support_height_floor_max_m": float(array[:, 4].max()),
        },
        "is_supplier_measured_fixture_pose": False,
        "physical_fixture_frozen": False,
    }
    return reconstruction, pose, variants


def transformed_bounds(pose: np.ndarray, low: np.ndarray, high: np.ndarray):
    points = np.asarray(
        list(itertools.product(*zip(low, high, strict=True))), dtype=float
    )
    world = points @ pose[:3, :3].T + pose[:3, 3]
    return world.min(axis=0), world.max(axis=0)


def main() -> int:
    args = parse_args()
    sources = [
        args.entry_contract,
        args.candidate,
        args.candidate_rgb,
        args.dataset_entry_report,
        args.dataset_info,
        args.task_contract,
        args.historical_home,
        args.camera_info,
        args.tf_static,
        args.metric_fixture_summary,
        args.sdk_urdf,
        args.sdk_urdf_zip,
        args.document_proxy_report,
        args.observed_clamp_report,
        args.fk_helper,
        args.path_helper,
        args.mesh_helper,
        args.geometry_helper,
        args.fixture_pose_helper,
    ]
    for path in sources:
        if not path.is_file():
            raise SystemExit(f"ERROR: falta fuente: {path}")

    contract = json.loads(args.entry_contract.read_text(encoding="utf-8"))
    if contract.get("schema") != "cruzr-s2-vla-task0-entry-e6.1a-v1":
        raise SystemExit("ERROR: contrato E6.1A inesperado")
    source_map = {
        "candidate_json_sha256": args.candidate,
        "candidate_rgb_sha256": args.candidate_rgb,
        "dataset_entry_report_sha256": args.dataset_entry_report,
    }
    for key, path in source_map.items():
        if sha256(path) != contract["candidate"][key]:
            raise SystemExit(f"ERROR: cambió fuente candidata: {key}")
    hash_paths = {
        "historical_measured_home_actuator_state": args.historical_home,
        "camera_info": args.camera_info,
        "tf_static": args.tf_static,
        "e4_1_metric_fixture_summary": args.metric_fixture_summary,
        "sdk_urdf": args.sdk_urdf,
        "sdk_urdf_zip": args.sdk_urdf_zip,
        "document_proxy_clamp_report": args.document_proxy_report,
        "observed_clamp_report": args.observed_clamp_report,
        "task_entry_contract_e6_0z": args.task_contract,
        "dataset_info": args.dataset_info,
    }
    for key, path in hash_paths.items():
        if sha256(path) != contract["source_hashes"][key]:
            raise SystemExit(f"ERROR: cambió fuente E6.1A: {key}")

    info = json.loads(args.dataset_info.read_text(encoding="utf-8"))
    order = info["features"]["action"]["names"]
    if order != contract["joint_order"] or len(order) != 20:
        raise SystemExit("ERROR: orden 20D distinto del contrato")
    candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
    if (
        candidate.get("episode") != contract["candidate"]["episode"]
        or candidate.get("task") != contract["task_id"]
    ):
        raise SystemExit("ERROR: identidad del candidato distinta")
    candidate_state_values = finite_vector(candidate.get("state"), 20, "candidate.state")
    candidate_action = finite_vector(candidate.get("action"), 20, "candidate.action")
    candidate_state = dict(zip(order, candidate_state_values, strict=True))
    initial_action_delta = [
        action - state
        for state, action in zip(candidate_state_values, candidate_action, strict=True)
    ]
    dataset_report = json.loads(args.dataset_entry_report.read_text(encoding="utf-8"))
    dataset_record = next(
        record
        for record in dataset_report["frame_zero_records"]
        if record["episode"] == candidate["episode"]
    )
    if dataset_record["task"] != 0 or dataset_record["state"] != candidate_state_values:
        raise SystemExit("ERROR: candidato no coincide con el dataset auditado")
    task_contract = json.loads(args.task_contract.read_text(encoding="utf-8"))
    if task_contract["tasks"]["0"]["required_scenario"] != "SUPPORTED_LOW":
        raise SystemExit("ERROR: escenario task 0 inesperado")

    home, home_metrics = measured_home(args.historical_home, order)
    home_values = [home[name] for name in order]
    dynamics = minimum_jerk_metrics(
        home_values, candidate_state_values, contract["trajectory_design"]
    )
    dynamics["maximum_delta_joint"] = order[dynamics["maximum_delta_joint_index"]]
    sample_count = int(contract["trajectory_design"]["geometry_sample_count_per_direction"])
    states = interpolate_states(home, candidate_state, order, sample_count)

    fk = load_module(args.fk_helper, "e6_1a_fk")
    path = load_module(args.path_helper, "e6_1a_path")
    mesh = load_module(args.mesh_helper, "e6_1a_mesh")
    geometry = load_module(args.geometry_helper, "e6_1a_geometry")
    fixture = load_module(args.fixture_pose_helper, "e6_1a_fixture")
    joints, bounds, triangles = fk.load_robot(args.sdk_urdf, args.sdk_urdf_zip)
    violations = path.limit_violations(joints, states, args.sdk_urdf)
    poses = [fk.forward_kinematics(joints, state) for state in states]
    graph = path.graph_distances(joints)
    links = sorted(bounds)
    wrong_effectors = {
        link for link in links if any(token in link for token in WRONG_EFFECTOR_TOKENS)
    }

    overlap_samples: dict[tuple[str, str], list[int]] = {}
    swept: dict[str, list[np.ndarray]] = {}
    for sample_index, current_poses in enumerate(poses):
        boxes = {
            link: path.obb_for_link(current_poses[link], local_bounds)
            for link, local_bounds in bounds.items()
        }
        for link, (low, high) in bounds.items():
            # The SDK URDF carries PGC/finger geometry for another effector.
            # The installed passive clamps are represented separately below by
            # the conservative document proxies, so mixing both would inflate
            # and mislabel the swept volume.
            if link in wrong_effectors:
                continue
            world_low, world_high = transformed_bounds(current_poses[link], low, high)
            record = swept.setdefault(link, [world_low.copy(), world_high.copy()])
            record[0] = np.minimum(record[0], world_low)
            record[1] = np.maximum(record[1], world_high)
        for left_index, left in enumerate(links):
            if left in wrong_effectors:
                continue
            for right in links[left_index + 1 :]:
                if right in wrong_effectors or not path.obb_overlap(boxes[left], boxes[right]):
                    continue
                pair = (left, right)
                if graph[pair] > 3 or pair in EXPECTED_NEAR_PAIRS:
                    overlap_samples.setdefault(pair, []).append(sample_index)

    monitored_pairs = sorted(set(overlap_samples) | EXPECTED_NEAR_PAIRS)
    roots = {
        link: mesh.BvhNode(
            triangles[link], np.arange(len(triangles[link]), dtype=np.int64)
        )
        for pair in monitored_pairs
        for link in pair
    }
    exact_results = []
    exact_hits = []
    for left, right in monitored_pairs:
        samples = overlap_samples.get((left, right), [])
        pair_hits = []
        for sample_index in samples:
            current_poses = poses[sample_index]
            intersects, _, triangle_ids = mesh.mesh_intersection(
                triangles[left],
                roots[left],
                current_poses[left],
                triangles[right],
                roots[right],
                current_poses[right],
                1e-8,
            )
            if intersects:
                pair_hits.append(sample_index)
                exact_hits.append(
                    {
                        "sample_index": sample_index,
                        "left": left,
                        "right": right,
                        "triangle_ids": triangle_ids,
                    }
                )
        exact_results.append(
            {
                "left": left,
                "right": right,
                "graph_distance": graph[(left, right)],
                "obb_overlap_sample_count": len(samples),
                "exact_intersection_sample_count": len(pair_hits),
                "first_exact_intersection_sample": pair_hits[0] if pair_hits else None,
            }
        )

    proxy_report = json.loads(args.document_proxy_report.read_text(encoding="utf-8"))
    proxy_data = {}
    proxy_robot_candidates: dict[tuple[str, str], list[int]] = {}
    proxy_exact_hits = []
    proxy_pair_candidates = []
    for side in ("L", "R"):
        low, high = (
            np.asarray(value, dtype=float)
            for value in proxy_report["proxy"]["dimensions"][side][
                "dilated_proxy_bounds_m"
            ]
        )
        proxy_triangles = geometry.box_triangles(low, high)
        proxy_data[side] = {
            "low": low,
            "high": high,
            "triangles": proxy_triangles,
            "root": mesh.BvhNode(
                proxy_triangles,
                np.arange(len(proxy_triangles), dtype=np.int64),
            ),
            "mount": f"{side}_sixforce_link",
        }
        swept[f"{side}_clamp_proxy"] = [
            np.full(3, np.inf),
            np.full(3, -np.inf),
        ]
    robot_roots = {
        link: mesh.BvhNode(
            triangles[link], np.arange(len(triangles[link]), dtype=np.int64)
        )
        for link in links
        if link not in wrong_effectors
    }
    for sample_index, current_poses in enumerate(poses):
        robot_boxes = {
            link: path.obb_for_link(current_poses[link], local_bounds)
            for link, local_bounds in bounds.items()
            if link not in wrong_effectors
        }
        proxy_boxes = {}
        for side, item in proxy_data.items():
            mount_pose = current_poses[item["mount"]]
            proxy_boxes[side] = path.obb_for_link(
                mount_pose, (item["low"], item["high"])
            )
            world_low, world_high = transformed_bounds(
                mount_pose, item["low"], item["high"]
            )
            record = swept[f"{side}_clamp_proxy"]
            record[0] = np.minimum(record[0], world_low)
            record[1] = np.maximum(record[1], world_high)
        if path.obb_overlap(proxy_boxes["L"], proxy_boxes["R"]):
            proxy_pair_candidates.append(sample_index)
        for side, item in proxy_data.items():
            allowed = {
                f"{side}_sixforce_link",
                f"{side}_wrist_roll_link",
                f"{side}_wrist_pitch_link",
            }
            for link, robot_box in robot_boxes.items():
                if link in allowed or not path.obb_overlap(proxy_boxes[side], robot_box):
                    continue
                proxy_robot_candidates.setdefault((side, link), []).append(sample_index)
                intersects, _, triangle_ids = mesh.mesh_intersection(
                    item["triangles"],
                    item["root"],
                    current_poses[item["mount"]],
                    triangles[link],
                    robot_roots[link],
                    current_poses[link],
                    1e-8,
                )
                if intersects:
                    proxy_exact_hits.append(
                        {
                            "sample_index": sample_index,
                            "proxy": side,
                            "robot_link": link,
                            "triangle_ids": triangle_ids,
                        }
                    )

    reconstruction, fixture_pose, fixture_variants = fixture_reconstruction(
        contract, candidate_state, args, fixture
    )
    scene = contract["scene_reconstruction"]
    width, depth, height = map(float, scene["box_lwh_m"])
    support_low = np.asarray(
        [-float(scene["candidate_support_width_m"]) / 2.0, 0.0, -float(scene["candidate_support_thickness_m"])]
    )
    support_high = np.asarray(
        [float(scene["candidate_support_width_m"]) / 2.0, float(scene["candidate_support_depth_m"]), 0.0]
    )
    box_low = np.asarray([-width / 2.0, float(scene["box_front_clearance_m"]), 0.0])
    box_high = np.asarray(
        [width / 2.0, float(scene["box_front_clearance_m"]) + depth, height]
    )

    def environment_obb_candidates(
        environment_pose: np.ndarray, low: np.ndarray, high: np.ndarray
    ) -> list[dict[str, Any]]:
        environment_box = path.obb_for_link(environment_pose, (low, high))
        found = []
        for sample_index, current_poses in enumerate(poses):
            for link, local_bounds in bounds.items():
                if link in wrong_effectors:
                    continue
                if path.obb_overlap(
                    environment_box,
                    path.obb_for_link(current_poses[link], local_bounds),
                ):
                    found.append({"sample_index": sample_index, "body": link})
            for side, item in proxy_data.items():
                if path.obb_overlap(
                    environment_box,
                    path.obb_for_link(
                        current_poses[item["mount"]], (item["low"], item["high"])
                    ),
                ):
                    found.append({"sample_index": sample_index, "body": f"{side}_clamp_proxy"})
        return found

    support_candidates = environment_obb_candidates(
        fixture_pose, support_low, support_high
    )
    box_candidates = environment_obb_candidates(fixture_pose, box_low, box_high)
    uncertainty_candidates = []
    for variant_index, variant_pose in enumerate(fixture_variants):
        for kind, low, high in (
            ("support", support_low, support_high),
            ("box_outer", box_low, box_high),
        ):
            for item in environment_obb_candidates(variant_pose, low, high):
                uncertainty_candidates.append(
                    {"variant_index": variant_index, "environment": kind, **item}
                )

    existing_table_low = np.asarray(
        [-float(scene["existing_table_width_m"]) / 2.0, 0.0, -float(scene["candidate_support_thickness_m"])]
    )
    existing_table_high = np.asarray(
        [float(scene["existing_table_width_m"]) / 2.0, float(scene["existing_table_depth_m"]), 0.0]
    )
    existing_table_candidates = environment_obb_candidates(
        fixture_pose, existing_table_low, existing_table_high
    )
    inferred_height = reconstruction["inferred_support_surface_height_floor_m"]
    table_height_difference = abs(
        inferred_height - float(scene["existing_table_surface_height_floor_m"])
    )

    moving_names = [
        name
        for name, values in swept.items()
        if name.endswith("_clamp_proxy")
        or not np.allclose(poses[0].get(name, np.eye(4)), poses[-1].get(name, np.eye(4)), atol=1e-8)
    ]
    moving_low = np.min([swept[name][0] for name in moving_names], axis=0)
    moving_high = np.max([swept[name][1] for name in moving_names], axis=0)
    entry_delta_max = max(abs(value) for value in initial_action_delta)
    failed = bool(
        violations
        or exact_hits
        or proxy_exact_hits
        or proxy_pair_candidates
        or support_candidates
        or box_candidates
        or uncertainty_candidates
        or not dynamics["passes_design_envelope"]
        or entry_delta_max > 0.1
    )
    report = {
        "schema": "cruzr-s2-vla-task0-entry-path-e6.1a-v1",
        "experiment_id": "E6.1A",
        "mode": "local_offline_no_robot_no_network_no_ros_no_container_no_publisher",
        "status": (
            "FAIL_OFFLINE_TASK0_ENTRY_PATH"
            if failed
            else "PASS_OFFLINE_TASK0_ENTRY_CANDIDATE_PHYSICAL_AND_SHADOW_STILL_BLOCKED"
        ),
        "candidate": {
            "episode": candidate["episode"],
            "task": candidate["task"],
            "scenario": contract["scenario"],
            "joint_order": order,
            "state_20d_rad": candidate_state_values,
            "first_action_20d_rad": candidate_action,
            "first_action_minus_state_rad": initial_action_delta,
            "maximum_absolute_first_action_delta_rad": entry_delta_max,
            "physical_pose_frozen": False,
        },
        "historical_home": {
            **home_metrics,
            "state_20d_rad": home_values,
            "not_a_fresh_physical_preflight": True,
        },
        "trajectory": {
            "segments": ["historical_HOME_to_candidate_ENTRY", "candidate_ENTRY_to_historical_HOME"],
            "entry_and_return_are_exact_time_reverses": True,
            "geometry_samples_each_direction": sample_count,
            "joint_limit_violations": violations,
            "dynamics": dynamics,
        },
        "self_collision": {
            "wrong_pgc_geometry_excluded": sorted(wrong_effectors),
            "monitored_pairs": exact_results,
            "exact_intersections": exact_hits,
            "document_proxy_clamp_dimensions_m": {
                side: (proxy_data[side]["high"] - proxy_data[side]["low"]).tolist()
                for side in ("L", "R")
            },
            "proxy_robot_obb_candidate_pairs": [
                {
                    "proxy": side,
                    "robot_link": link,
                    "sample_count": len(samples),
                }
                for (side, link), samples in sorted(proxy_robot_candidates.items())
            ],
            "proxy_robot_exact_intersections": proxy_exact_hits,
            "proxy_proxy_obb_candidate_samples": proxy_pair_candidates,
        },
        "swept_volume": {
            "representation": "union_AABB_of_transformed_vendor_collision_bounds_plus_document_proxy_clamps",
            "moving_body_count": len(moving_names),
            "moving_bodies": sorted(moving_names),
            "composite_min_base_m": moving_low.tolist(),
            "composite_max_base_m": moving_high.tolist(),
            "continuous_path_certified": False,
        },
        "scene_reconstruction": reconstruction,
        "fixture_screen": {
            "candidate_support_width_depth_thickness_m": [
                float(scene["candidate_support_width_m"]),
                float(scene["candidate_support_depth_m"]),
                float(scene["candidate_support_thickness_m"]),
            ],
            "central_support_obb_candidates": support_candidates,
            "central_box_outer_obb_candidates": box_candidates,
            "pixel_uncertainty_obb_candidates": uncertainty_candidates,
            "existing_table_width_depth_height_floor_m": [
                float(scene["existing_table_width_m"]),
                float(scene["existing_table_depth_m"]),
                float(scene["existing_table_surface_height_floor_m"]),
            ],
            "existing_table_height_difference_from_candidate_m": table_height_difference,
            "existing_table_at_candidate_height_obb_candidates": existing_table_candidates,
            "existing_table_usable_for_candidate": False,
            "candidate_support_physically_approved": False,
        },
        "gates": {
            "candidate_identity_and_20d_frozen": True,
            "first_action_continuous_at_entry": entry_delta_max <= 0.1,
            "urdf_joint_limits_sampled_pass": not violations,
            "minimum_jerk_design_envelope_pass": dynamics["passes_design_envelope"],
            "sampled_vendor_mesh_self_collision_pass": not exact_hits,
            "sampled_document_proxy_clamp_pass": not proxy_exact_hits and not proxy_pair_candidates,
            "candidate_support_and_box_obb_screen_pass": not support_candidates and not box_candidates and not uncertainty_candidates,
            "fixture_metric_pose_requires_physical_confirmation": True,
            "fresh_measured_home_required_before_any_motion": True,
            "fresh_five_shadow_chunks_required": True,
            "physical_execution_authorized": False,
        },
        "limitations": [
            "The HOME state is historical and is used only as an offline endpoint.",
            "The fixture pose is reconstructed from two annotated pixels and known box width; it is not a supplier pose or physical measurement.",
            "Collision checking is sampled and uses the conservative document proxy because exact passive-clamp CAD is unavailable.",
            "The 0.15 rad/s and 0.5 rad/s^2 values are design inputs only and have not been accepted for E6.1 physical motion.",
            "No shadow inference was run because the physical task-matched scene and fresh measured ENTRY do not yet exist.",
        ],
        "next_gate": "E6.1B_REVIEW_SUPPORT_GEOMETRY_IMPLEMENT_FAIL_CLOSED_ENTRY_RECOVERY_THEN_FRESH_PHYSICAL_PREFLIGHT",
        "robot_accessed": False,
        "persistent_container_started": False,
        "ros_imported": False,
        "physical_publisher_created": False,
        "physical_movement_commanded": False,
        "physical_execution_authorized": False,
        "source_sha256": {path.name: sha256(path) for path in sources},
    }
    rendered = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(f"E6.1A_STATUS={report['status']}")
    print(f"E6.1A_CANDIDATE={candidate['episode']},task:0,scenario:SUPPORTED_LOW")
    print(f"E6.1A_FIRST_ACTION_DELTA_RAD={entry_delta_max:.9f}")
    print(f"E6.1A_ENTRY_DURATION_SECONDS={dynamics['duration_seconds_each_direction']:.2f}")
    print(f"E6.1A_JOINT_LIMIT_VIOLATIONS={len(violations)}")
    print(f"E6.1A_SELF_COLLISION_EXACT_HITS={len(exact_hits)}")
    print(f"E6.1A_CLAMP_PROXY_EXACT_HITS={len(proxy_exact_hits)}")
    print(f"E6.1A_SUPPORT_HEIGHT_FLOOR_M={inferred_height:.6f}")
    print(f"E6.1A_SUPPORT_BOX_OBB_CANDIDATES={len(support_candidates) + len(box_candidates)}")
    print(f"E6.1A_EXISTING_TABLE_USABLE=0")
    print("E6.1A_ROBOT_ACCESSED=0")
    print("E6.1A_PHYSICAL_AUTHORIZED=0")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
