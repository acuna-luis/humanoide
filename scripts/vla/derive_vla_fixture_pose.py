#!/usr/bin/env python3
"""Derive the S2 VLA table pose without creating a physical command path."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--urdf", required=True, type=Path)
    parser.add_argument("--tf-static", required=True, type=Path)
    parser.add_argument("--tf-live", required=True, type=Path)
    parser.add_argument("--camera-info", required=True, type=Path)
    parser.add_argument("--dataset-info", required=True, type=Path)
    parser.add_argument("--episode-stats", required=True, type=Path)
    parser.add_argument("--reference-frame", required=True, type=Path)
    parser.add_argument("--tag-log", required=True, type=Path)
    parser.add_argument("--base-mesh", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--episode", type=int, default=90)
    parser.add_argument("--rim-pixels", default="307,293,713,293")
    parser.add_argument("--box-lwh", default="0.603,0.397,0.217")
    parser.add_argument("--table-wh", default="1.800,0.800")
    parser.add_argument("--platform-height", type=float, default=1.0)
    parser.add_argument("--box-front-clearance", type=float, default=0.05)
    parser.add_argument("--pixel-uncertainty", type=float, default=2.0)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_vector(raw: str, count: int) -> tuple[float, ...]:
    values = tuple(float(value) for value in raw.split(","))
    if len(values) != count or not all(math.isfinite(value) for value in values):
        raise ValueError(f"Se esperaban {count} valores finitos: {raw}")
    return values


def rpy_rotation(roll: float, pitch: float, yaw: float) -> np.ndarray:
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    return np.array(
        [
            [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
            [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
            [-sp, cp * sr, cp * cr],
        ],
        dtype=float,
    )


def axis_rotation(axis: tuple[float, ...], angle: float) -> np.ndarray:
    vector = np.asarray(axis, dtype=float)
    vector /= np.linalg.norm(vector)
    x, y, z = vector
    cosine, sine = math.cos(angle), math.sin(angle)
    one_minus = 1.0 - cosine
    return np.array(
        [
            [cosine + x * x * one_minus, x * y * one_minus - z * sine, x * z * one_minus + y * sine],
            [y * x * one_minus + z * sine, cosine + y * y * one_minus, y * z * one_minus - x * sine],
            [z * x * one_minus - y * sine, z * y * one_minus + x * sine, cosine + z * z * one_minus],
        ],
        dtype=float,
    )


def quaternion_rotation(values: tuple[float, float, float, float]) -> np.ndarray:
    x, y, z, w = values
    norm = math.sqrt(x * x + y * y + z * z + w * w)
    x, y, z, w = x / norm, y / norm, z / norm, w / norm
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ],
        dtype=float,
    )


def transform(translation=(0.0, 0.0, 0.0), rotation=None) -> np.ndarray:
    result = np.eye(4)
    result[:3, :3] = np.eye(3) if rotation is None else rotation
    result[:3, 3] = translation
    return result


def json_documents(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    decoder = json.JSONDecoder()
    position = 0
    while position < len(text):
        start = text.find("{", position)
        if start < 0:
            break
        try:
            value, end = decoder.raw_decode(text, start)
        except json.JSONDecodeError:
            position = start + 1
            continue
        yield value
        position = end


def tf_edges(*paths: Path) -> tuple[dict[str, tuple[str, np.ndarray]], int]:
    edges: dict[str, tuple[str, np.ndarray]] = {}
    count = 0
    for path in paths:
        for document in json_documents(path):
            for item in document.get("transforms", []):
                child = item.get("child_frame_id", "")
                parent = item.get("header", {}).get("frame_id", "")
                if not child or not parent:
                    continue
                raw = item["transform"]
                translation = raw["translation"]
                rotation = raw["rotation"]
                edges[child] = (
                    parent,
                    transform(
                        tuple(float(translation[key]) for key in ("x", "y", "z")),
                        quaternion_rotation(tuple(float(rotation[key]) for key in ("x", "y", "z", "w"))),
                    ),
                )
                count += 1
    return edges, count


def compose_chain(edges: dict[str, tuple[str, np.ndarray]], root: str, child: str) -> np.ndarray:
    sequence = []
    seen = set()
    current = child
    while current != root:
        if current in seen or current not in edges:
            raise RuntimeError(f"No existe cadena TF {root}->{child}; detenida en {current}")
        seen.add(current)
        parent, value = edges[current]
        sequence.append(value)
        current = parent
    result = np.eye(4)
    for value in reversed(sequence):
        result = result @ value
    return result


def episode_state(info_path: Path, stats_path: Path, episode: int) -> tuple[dict[str, float], dict[str, float]]:
    info = json.loads(info_path.read_text(encoding="utf-8"))
    names = info["features"]["observation.state"]["names"]
    selected = None
    for line in stats_path.read_text(encoding="utf-8").splitlines():
        candidate = json.loads(line)
        if int(candidate["episode_index"]) == episode:
            selected = candidate
            break
    if selected is None:
        raise RuntimeError(f"No existe episodio {episode}")
    stats = selected["stats"]["observation.state"]
    return dict(zip(names, stats["mean"])), dict(zip(names, stats["std"]))


def urdf_edges(path: Path, joint_values: dict[str, float]) -> dict[str, tuple[str, np.ndarray]]:
    root = ET.parse(path).getroot()
    edges = {}
    for joint in root.findall("joint"):
        name = joint.attrib["name"]
        joint_type = joint.attrib["type"]
        parent = joint.find("parent").attrib["link"]
        child = joint.find("child").attrib["link"]
        origin = joint.find("origin")
        xyz = parse_vector((origin.attrib.get("xyz", "0 0 0") if origin is not None else "0 0 0").replace(" ", ","), 3)
        rpy = parse_vector((origin.attrib.get("rpy", "0 0 0") if origin is not None else "0 0 0").replace(" ", ","), 3)
        value = transform(xyz, rpy_rotation(*rpy))
        if joint_type in {"revolute", "continuous"}:
            axis_node = joint.find("axis")
            axis = parse_vector(axis_node.attrib.get("xyz", "1 0 0").replace(" ", ","), 3)
            value = value @ transform(rotation=axis_rotation(axis, float(joint_values.get(name, 0.0))))
        edges[child] = (parent, value)
    return edges


def binary_stl_bounds(path: Path) -> tuple[np.ndarray, np.ndarray]:
    data = path.read_bytes()
    if len(data) < 84:
        raise RuntimeError("STL de base incompleto")
    triangles = int.from_bytes(data[80:84], "little")
    if len(data) != 84 + triangles * 50:
        raise RuntimeError("Se esperaba STL binario de base")
    points = []
    import struct

    for index in range(triangles):
        offset = 84 + index * 50 + 12
        for vertex in range(3):
            points.append(struct.unpack_from("<fff", data, offset + vertex * 12))
    array = np.asarray(points, dtype=float)
    return np.min(array, axis=0), np.max(array, axis=0)


def intersect_pixel(K_inv, T_base_camera, pixel, plane_z):
    ray_camera = K_inv @ np.array([pixel[0], pixel[1], 1.0])
    ray_base = T_base_camera[:3, :3] @ ray_camera
    origin = T_base_camera[:3, 3]
    scale = (plane_z - origin[2]) / ray_base[2]
    if scale <= 0:
        raise RuntimeError("El píxel no intersecta la plataforma delante de la cámara")
    return origin + scale * ray_base


def fixture_from_rim(left, right, platform_z, box_depth, front_clearance):
    width_vector = right - left
    width_vector[2] = 0.0
    x_axis = width_vector / np.linalg.norm(width_vector)
    y_axis = np.array([-x_axis[1], x_axis[0], 0.0])
    far_center = (left + right) / 2.0
    front_center = far_center - (front_clearance + box_depth) * y_axis
    front_center[2] = platform_z
    yaw = math.atan2(x_axis[1], x_axis[0])
    return front_center, x_axis, y_axis, yaw, far_center


def parse_tag_log(path: Path) -> tuple[np.ndarray, tuple[float, float, float], float]:
    text = path.read_text(encoding="utf-8")
    pose_match = re.search(r"^TAG_POSE=([-+0-9.eE ]+)$", text, re.MULTILINE)
    quality_match = re.search(
        r"^TAG_QUALITY=samples:(\d+),std_mm:([-+0-9.eE]+),([-+0-9.eE]+),([-+0-9.eE]+),max_angle_deg:([-+0-9.eE]+),margin_min:([-+0-9.eE]+)$",
        text,
        re.MULTILINE,
    )
    if not pose_match or not quality_match:
        raise RuntimeError("El log no contiene pose y calidad AprilTag completas")
    values = tuple(float(value) for value in pose_match.group(1).split())
    if len(values) != 7 or int(quality_match.group(1)) != 20:
        raise RuntimeError("La calibración exige exactamente 20 muestras AprilTag")
    quality = tuple(float(quality_match.group(index)) for index in (2, 3, 4))
    max_angle_deg = float(quality_match.group(5))
    if max(quality) > 4.0:
        raise RuntimeError("La posición AprilTag no es suficientemente estable")
    if max_angle_deg > 2.0 and "TAG_ORIENTATION_AMBIGUOUS=" not in text:
        raise RuntimeError("La ambigüedad angular AprilTag no fue declarada")
    T_camera_tag = transform(values[:3], quaternion_rotation(values[3:7]))
    return T_camera_tag, quality, max_angle_deg


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rim = parse_vector(args.rim_pixels, 4)
    box_lwh = parse_vector(args.box_lwh, 3)
    table_wh = parse_vector(args.table_wh, 2)
    camera_info = next(json_documents(args.camera_info))
    if camera_info.get("width") != 960 or camera_info.get("height") != 576:
        raise RuntimeError("CameraInfo no coincide con la entrada VLA 960x576")
    if camera_info.get("header", {}).get("frame_id") != "stereo_left_rectified_optical_frame":
        raise RuntimeError("Frame de CameraInfo inesperado")
    K = np.asarray(camera_info["k"], dtype=float).reshape(3, 3)
    K_inv = np.linalg.inv(K)

    means, stds = episode_state(args.dataset_info, args.episode_stats, args.episode)
    robot_edges = urdf_edges(args.urdf, means)
    T_base_head = compose_chain(robot_edges, "base_link", "head_pitch_link")
    static_edges, static_count = tf_edges(args.tf_static)
    T_head_camera = compose_chain(static_edges, "head_pitch_link", "stereo_left_rectified_optical_frame")
    T_episode_camera = T_base_head @ T_head_camera

    live_edges, live_count = tf_edges(args.tf_live, args.tf_static)
    T_live_camera = compose_chain(live_edges, "base_link", "stereo_left_rectified_optical_frame")
    T_camera_tag, tag_std_mm, tag_angle_spread_deg = parse_tag_log(args.tag_log)
    T_base_tag = T_live_camera @ T_camera_tag

    base_floor_offset = float(live_edges["base_link"][1][2, 3])
    platform_z = args.platform_height - base_floor_offset
    top_z = platform_z + box_lwh[2]
    left = intersect_pixel(K_inv, T_episode_camera, rim[:2], top_z)
    right = intersect_pixel(K_inv, T_episode_camera, rim[2:], top_z)
    front, x_axis, y_axis, yaw, far_center = fixture_from_rim(
        left, right, platform_z, box_lwh[1], args.box_front_clearance
    )
    reconstructed_width = float(np.linalg.norm(right - left))
    width_error = reconstructed_width - box_lwh[0]

    mesh_min, mesh_max = binary_stl_bounds(args.base_mesh)
    bumper_point = np.array([mesh_max[0], 0.0, 0.0])
    bumper_distance = float(np.dot(front[:2] - bumper_point[:2], y_axis[:2]))

    # La pose viva sólo valida posición y escala. La orientación de un tag
    # planar puede saltar entre ramas PnP; no se usa para la solución E4.1.
    live_y = T_base_tag[:3, 3].copy()
    live_y[2] = 0.0
    live_y /= np.linalg.norm(live_y)
    tag_x = np.array([live_y[1], -live_y[0], 0.0])
    live_front = T_base_tag[:3, 3].copy() - (table_wh[1] / 2.0) * live_y
    live_front[2] = platform_z
    live_bumper_distance = float(np.dot(live_front[:2] - bumper_point[:2], live_y[:2]))

    variants = []
    delta = args.pixel_uncertainty
    for du_left in (-delta, delta):
        for dv_left in (-delta, delta):
            for du_right in (-delta, delta):
                for dv_right in (-delta, delta):
                    for height_delta in (-0.01, 0.01):
                        candidate_top = top_z + height_delta
                        candidate_left = intersect_pixel(K_inv, T_episode_camera, (rim[0] + du_left, rim[1] + dv_left), candidate_top)
                        candidate_right = intersect_pixel(K_inv, T_episode_camera, (rim[2] + du_right, rim[3] + dv_right), candidate_top)
                        candidate_front, _, candidate_y, candidate_yaw, _ = fixture_from_rim(
                            candidate_left, candidate_right, platform_z + height_delta, box_lwh[1], args.box_front_clearance
                        )
                        candidate_distance = float(np.dot(candidate_front[:2] - bumper_point[:2], candidate_y[:2]))
                        variants.append([*candidate_front, candidate_yaw, candidate_distance])
    variants_array = np.asarray(variants)
    uncertainty = {
        "assumptions": {"pixel_endpoint_px": delta, "vertical_geometry_m": 0.01},
        "platform_position_half_range_m": ((variants_array[:, :3].max(axis=0) - variants_array[:, :3].min(axis=0)) / 2.0).tolist(),
        "yaw_half_range_deg": math.degrees((variants_array[:, 3].max() - variants_array[:, 3].min()) / 2.0),
        "bumper_distance_half_range_m": float((variants_array[:, 4].max() - variants_array[:, 4].min()) / 2.0),
    }

    result = {
        "experiment_id": "E4.1",
        "status": "METRIC_FIXTURE_CANDIDATE_RESOLVED_PHYSICAL_GATES_OPEN",
        "method": "episode_90_known_height_two_ray_metric_reconstruction_plus_live_apriltag_validation",
        "coordinate_contract": {
            "parent": "base_link",
            "child": "platform_frame",
            "origin": "center_of_front_table_edge_on_top_surface",
            "x": "along_table_width_toward_image_right",
            "y": "from_front_edge_to_rear_edge",
            "z": "up",
        },
        "platform_in_base": {
            "x_m": float(front[0]), "y_m": float(front[1]), "z_m": float(front[2]),
            "roll_rad": 0.0, "pitch_rad": 0.0, "yaw_rad": yaw,
            "yaw_deg": math.degrees(yaw),
        },
        "fixture": {
            "table_width_m": table_wh[0], "table_depth_m": table_wh[1],
            "surface_height_floor_m": args.platform_height,
            "box_lwh_m": list(box_lwh), "box_front_clearance_m": args.box_front_clearance,
            "far_rim_pixels_uv": [[rim[0], rim[1]], [rim[2], rim[3]]],
            "far_rim_in_base_m": [left.tolist(), right.tolist()],
            "far_rim_center_in_base_m": far_center.tolist(),
            "reconstructed_width_m": reconstructed_width,
            "known_width_m": box_lwh[0], "width_residual_mm": width_error * 1000.0,
        },
        "D_BUMPER_PLATFORM": {
            "signed_m": bumper_distance,
            "source": "base_link_binary_collision_mesh_max_x_to_platform_front_line",
            "base_mesh_max_x_m": float(mesh_max[0]),
            "interpretation": "negative_means_vertical_projection_overlap",
        },
        "live_validation_fixture_pose": {
            "purpose": "safe_far_table_pose_only_not_operational_target",
            "front_edge_center_in_base_m": live_front.tolist(),
            "yaw_deg": math.degrees(math.atan2(tag_x[1], tag_x[0])),
            "D_BUMPER_PLATFORM_signed_m": live_bumper_distance,
            "tag_center_in_base_m": T_base_tag[:3, 3].tolist(),
            "tag_position_std_mm": list(tag_std_mm),
            "tag_orientation_spread_deg": tag_angle_spread_deg,
            "orientation_policy": "position_only_planar_pnp_ambiguity",
        },
        "camera": {
            "frame": camera_info["header"]["frame_id"], "width": 960, "height": 576,
            "K": K.tolist(), "episode_camera_position_in_base_m": T_episode_camera[:3, 3].tolist(),
            "static_tf_transform_count": static_count, "live_tf_transform_count": live_count,
        },
        "episode": {
            "index": args.episode,
            "head_lifter_waist_mean_rad": {name: means[name] for name in (
                "head_pitch_joint", "head_yaw_joint", "lifter_pitch_1_joint",
                "lifter_pitch_2_joint", "lifter_pitch_3_joint", "waist_yaw_joint")},
            "head_lifter_waist_std_rad": {name: stds[name] for name in (
                "head_pitch_joint", "head_yaw_joint", "lifter_pitch_1_joint",
                "lifter_pitch_2_joint", "lifter_pitch_3_joint", "waist_yaw_joint")},
        },
        "uncertainty": uncertainty,
        "gates": {
            "metric_width_residual_within_5mm": abs(width_error) <= 0.005,
            "live_tag_20_samples_stable": max(tag_std_mm) <= 4.0,
            "ready_and_inverse_complete": False,
            "swept_volume_collision_validated": False,
            "physical_test_authorized": False,
        },
        "source_sha256": {str(path): sha256(path) for path in (
            args.urdf, args.tf_static, args.tf_live, args.camera_info,
            args.dataset_info, args.episode_stats, args.reference_frame,
            args.tag_log, args.base_mesh)},
    }
    if not result["gates"]["metric_width_residual_within_5mm"]:
        result["status"] = "FAIL_METRIC_RIM_RECONSTRUCTION"

    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    pose = result["platform_in_base"]
    yaml_text = f"""experiment_id: E4.1
status: {result['status']}
platform_frame_contract: front-edge-center,width-x,depth-y,up-z
platform_in_base:
  x_m: {pose['x_m']:.9f}
  y_m: {pose['y_m']:.9f}
  z_m: {pose['z_m']:.9f}
  roll_rad: 0.000000000
  pitch_rad: 0.000000000
  yaw_rad: {pose['yaw_rad']:.9f}
  yaw_deg: {pose['yaw_deg']:.6f}
D_BUMPER_PLATFORM_signed_m: {bumper_distance:.9f}
reconstructed_box_width_m: {reconstructed_width:.9f}
known_box_width_m: {box_lwh[0]:.9f}
width_residual_mm: {width_error * 1000.0:.6f}
physical_test_authorized: false
blocking_gates:
  - canonical_ready_and_inverse_incomplete
  - swept_volume_and_table_collision_not_validated
  - negative_bumper_projection_requires_physical_geometry_review
"""
    (args.output_dir / "fixture_pose.yaml").write_text(yaml_text, encoding="utf-8")
    print(f"PLATFORM_IN_BASE={pose['x_m']:.9f} {pose['y_m']:.9f} {pose['z_m']:.9f} 0 0 {pose['yaw_rad']:.9f}")
    print(f"D_BUMPER_PLATFORM_SIGNED_M={bumper_distance:.9f}")
    print(f"RIM_WIDTH_RECONSTRUCTED_M={reconstructed_width:.9f}; ERROR_MM={width_error * 1000.0:.3f}")
    print(f"LIVE_SAFE_TABLE_D_BUMPER_PLATFORM_SIGNED_M={live_bumper_distance:.9f}")
    print(f"E4.1_STATUS={result['status']}")
    print("PHYSICAL_TEST_AUTHORIZED=0")


if __name__ == "__main__":
    main()
