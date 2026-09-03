#!/usr/bin/env python3
"""Conservative, offline fixture-collision audit for the Cruzr S2 VLA ready path.

The audit deliberately never imports ROS.  It reconstructs FK from the vendor
URDF and uses the collision-mesh AABB of every link, transformed into the
calibrated platform frame.  This is conservative: an AABB overlap is a
potential collision, not proof of mesh contact.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import struct
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
import yaml


META_ARM_NAMES = [
    "shoulder_pitch", "shoulder_roll", "shoulder_yaw", "elbow_roll",
    "elbow_yaw", "wrist_pitch", "wrist_roll",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def xyz(raw: str | None, default: tuple[float, float, float] = (0, 0, 0)) -> np.ndarray:
    if raw is None:
        return np.asarray(default, dtype=float)
    values = np.asarray([float(value) for value in raw.split()], dtype=float)
    if values.shape != (3,) or not np.all(np.isfinite(values)):
        raise ValueError(f"vector 3D inválido: {raw!r}")
    return values


def rotation_rpy(values: np.ndarray) -> np.ndarray:
    roll, pitch, yaw = values
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    return np.asarray([
        [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
        [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
        [-sp, cp * sr, cp * cr],
    ])


def rotation_axis(axis: np.ndarray, angle: float) -> np.ndarray:
    norm = float(np.linalg.norm(axis))
    if norm == 0:
        raise ValueError("joint axis nulo")
    x, y, z = axis / norm
    c, s, one = math.cos(angle), math.sin(angle), 1.0 - math.cos(angle)
    return np.asarray([
        [c + x*x*one, x*y*one - z*s, x*z*one + y*s],
        [y*x*one + z*s, c + y*y*one, y*z*one - x*s],
        [z*x*one - y*s, z*y*one + x*s, c + z*z*one],
    ])


def transform(translation=(0, 0, 0), rotation=None) -> np.ndarray:
    result = np.eye(4)
    result[:3, 3] = np.asarray(translation, dtype=float)
    if rotation is not None:
        result[:3, :3] = rotation
    return result


def origin_transform(element: ET.Element | None) -> np.ndarray:
    if element is None:
        return np.eye(4)
    return transform(xyz(element.get("xyz")), rotation_rpy(xyz(element.get("rpy"))))


def corners(bounds_min: np.ndarray, bounds_max: np.ndarray) -> np.ndarray:
    return np.asarray(list(itertools.product(*zip(bounds_min, bounds_max))), dtype=float)


def apply(points: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    return points @ matrix[:3, :3].T + matrix[:3, 3]


def stl_bounds(data: bytes) -> tuple[np.ndarray, np.ndarray]:
    if len(data) >= 84:
        facets = struct.unpack_from("<I", data, 80)[0]
        if 84 + facets * 50 == len(data):
            dtype = np.dtype([
                ("normal", "<f4", (3,)), ("vertices", "<f4", (9,)), ("attr", "<u2"),
            ])
            records = np.frombuffer(data, dtype=dtype, offset=84, count=facets)
            vertices = records["vertices"].reshape(-1, 3).astype(float)
            return vertices.min(axis=0), vertices.max(axis=0)
    vertices = []
    for line in data.decode("ascii", errors="ignore").splitlines():
        words = line.strip().split()
        if len(words) == 4 and words[0].lower() == "vertex":
            vertices.append([float(value) for value in words[1:]])
    if not vertices:
        raise ValueError("STL sin vértices")
    array = np.asarray(vertices, dtype=float)
    return array.min(axis=0), array.max(axis=0)


def stl_triangles(data: bytes) -> np.ndarray:
    if len(data) >= 84:
        facets = struct.unpack_from("<I", data, 80)[0]
        if 84 + facets * 50 == len(data):
            dtype = np.dtype([
                ("normal", "<f4", (3,)), ("vertices", "<f4", (9,)), ("attr", "<u2"),
            ])
            records = np.frombuffer(data, dtype=dtype, offset=84, count=facets)
            return records["vertices"].reshape(-1, 3, 3).astype(float)
    vertices = []
    for line in data.decode("ascii", errors="ignore").splitlines():
        words = line.strip().split()
        if len(words) == 4 and words[0].lower() == "vertex":
            vertices.append([float(value) for value in words[1:]])
    if not vertices or len(vertices) % 3:
        raise ValueError("STL ASCII sin triángulos completos")
    return np.asarray(vertices, dtype=float).reshape(-1, 3, 3)


def geometry_bounds(geometry: ET.Element, archive: zipfile.ZipFile,
                    members: dict[str, str]) -> tuple[np.ndarray, np.ndarray]:
    mesh = geometry.find("mesh")
    if mesh is not None:
        filename = mesh.get("filename", "").replace("package://", "")
        filename = filename.split("cruzr_s2_description/", 1)[-1]
        member = members.get(filename)
        if member is None:
            matches = [name for suffix, name in members.items() if suffix.endswith(filename)]
            if len(matches) != 1:
                raise ValueError(f"mesh no resuelto en ZIP: {filename}")
            member = matches[0]
        low, high = stl_bounds(archive.read(member))
        scale = xyz(mesh.get("scale"), (1, 1, 1))
        scaled = np.vstack((low * scale, high * scale))
        return scaled.min(axis=0), scaled.max(axis=0)
    box = geometry.find("box")
    if box is not None:
        half = xyz(box.get("size")) / 2.0
        return -half, half
    cylinder = geometry.find("cylinder")
    if cylinder is not None:
        radius = float(cylinder.get("radius", "nan"))
        half_length = float(cylinder.get("length", "nan")) / 2.0
        return np.asarray([-radius, -radius, -half_length]), np.asarray([radius, radius, half_length])
    sphere = geometry.find("sphere")
    if sphere is not None:
        radius = float(sphere.get("radius", "nan"))
        return np.full(3, -radius), np.full(3, radius)
    raise ValueError("geometría de colisión URDF no soportada")


def geometry_triangles(geometry: ET.Element, archive: zipfile.ZipFile,
                       members: dict[str, str]) -> np.ndarray | None:
    mesh = geometry.find("mesh")
    if mesh is None:
        return None
    filename = mesh.get("filename", "").replace("package://", "")
    filename = filename.split("cruzr_s2_description/", 1)[-1]
    member = members.get(filename)
    if member is None:
        matches = [name for suffix, name in members.items() if suffix.endswith(filename)]
        if len(matches) != 1:
            raise ValueError(f"mesh no resuelto en ZIP: {filename}")
        member = matches[0]
    triangles = stl_triangles(archive.read(member))
    return triangles * xyz(mesh.get("scale"), (1, 1, 1))


def load_robot(urdf: Path, sdk_zip: Path):
    root = ET.parse(urdf).getroot()
    with zipfile.ZipFile(sdk_zip) as archive:
        members = {
            name.split("cruzr_s2_description/", 1)[-1]: name
            for name in archive.namelist() if not name.endswith("/")
        }
        link_bounds: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        link_triangles: dict[str, np.ndarray] = {}
        for link in root.findall("link"):
            pieces = []
            triangle_pieces = []
            for collision in link.findall("collision"):
                geometry = collision.find("geometry")
                if geometry is None:
                    continue
                low, high = geometry_bounds(geometry, archive, members)
                collision_origin = origin_transform(collision.find("origin"))
                points = apply(corners(low, high), collision_origin)
                pieces.append(points)
                triangles = geometry_triangles(geometry, archive, members)
                if triangles is not None:
                    transformed = apply(triangles.reshape(-1, 3), collision_origin).reshape(-1, 3, 3)
                    triangle_pieces.append(transformed)
            if pieces:
                points = np.vstack(pieces)
                link_bounds[link.get("name", "")] = (points.min(axis=0), points.max(axis=0))
            if triangle_pieces:
                link_triangles[link.get("name", "")] = np.concatenate(triangle_pieces)

    joints = []
    child_names = set()
    for joint in root.findall("joint"):
        parent = joint.find("parent")
        child = joint.find("child")
        if parent is None or child is None:
            continue
        item = {
            "name": joint.get("name", ""), "type": joint.get("type", "fixed"),
            "parent": parent.get("link", ""), "child": child.get("link", ""),
            "origin": origin_transform(joint.find("origin")),
            "axis": xyz(joint.find("axis").get("xyz") if joint.find("axis") is not None else None, (1, 0, 0)),
        }
        joints.append(item)
        child_names.add(item["child"])
    roots = [link.get("name", "") for link in root.findall("link") if link.get("name", "") not in child_names]
    if roots != ["base_link"]:
        raise ValueError(f"raíz URDF inesperada: {roots}")
    return joints, link_bounds, link_triangles


def forward_kinematics(joints, state: dict[str, float]) -> dict[str, np.ndarray]:
    poses = {"base_link": np.eye(4)}
    pending = list(joints)
    while pending:
        progress = False
        for joint in list(pending):
            if joint["parent"] not in poses:
                continue
            motion = np.eye(4)
            if joint["type"] in ("revolute", "continuous"):
                motion[:3, :3] = rotation_axis(joint["axis"], float(state.get(joint["name"], 0.0)))
            elif joint["type"] == "prismatic":
                motion[:3, 3] = joint["axis"] * float(state.get(joint["name"], 0.0))
            poses[joint["child"]] = poses[joint["parent"]] @ joint["origin"] @ motion
            pending.remove(joint)
            progress = True
        if not progress:
            raise ValueError("árbol URDF inconexo")
    return poses


def arm_state(meta_values: list[float]) -> dict[str, float]:
    if len(meta_values) != 14:
        raise ValueError("goal MetaMove no es 14D")
    names = [*(f"L_{name}_joint" for name in META_ARM_NAMES), *(f"R_{name}_joint" for name in META_ARM_NAMES)]
    return dict(zip(names, map(float, meta_values)))


def interpolate(start: dict[str, float], end: dict[str, float], count: int):
    names = sorted(set(start) | set(end))
    for index in range(count):
        alpha = index / (count - 1)
        yield {name: (1 - alpha) * start.get(name, 0.0) + alpha * end.get(name, 0.0) for name in names}


def aabb_overlap(low_a, high_a, low_b, high_b, tolerance=0.0) -> bool:
    return bool(np.all(high_a >= low_b - tolerance) and np.all(high_b >= low_a - tolerance))


def segment_intersects_rectangle(a: np.ndarray, b: np.ndarray,
                                 low: np.ndarray, high: np.ndarray) -> bool:
    direction = b - a
    t_min, t_max = 0.0, 1.0
    for axis in range(2):
        if abs(direction[axis]) < 1e-12:
            if a[axis] < low[axis] or a[axis] > high[axis]:
                return False
            continue
        first = (low[axis] - a[axis]) / direction[axis]
        second = (high[axis] - a[axis]) / direction[axis]
        if first > second:
            first, second = second, first
        t_min, t_max = max(t_min, first), min(t_max, second)
        if t_min > t_max:
            return False
    return True


def triangle_plane_hits_rectangle(triangles: np.ndarray, low: np.ndarray,
                                  high: np.ndarray) -> bool:
    eps = 1e-9
    tri_low_z = triangles[:, :, 2].min(axis=1)
    tri_high_z = triangles[:, :, 2].max(axis=1)
    candidates = triangles[(tri_low_z <= eps) & (tri_high_z >= -eps)]
    for triangle in candidates:
        intersections = []
        for first, second in ((0, 1), (1, 2), (2, 0)):
            a, b = triangle[first], triangle[second]
            if abs(a[2]) <= eps:
                intersections.append(a[:2])
            if a[2] * b[2] < 0.0:
                alpha = -a[2] / (b[2] - a[2])
                intersections.append((a + alpha * (b - a))[:2])
        if not intersections:
            continue
        unique = []
        for point in intersections:
            if not any(np.linalg.norm(point - existing) < 1e-9 for existing in unique):
                unique.append(point)
        if any(np.all(point >= low) and np.all(point <= high) for point in unique):
            return True
        for a, b in itertools.combinations(unique, 2):
            if segment_intersects_rectangle(a, b, low, high):
                return True
    return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--urdf", required=True, type=Path)
    parser.add_argument("--sdk-urdf-zip", required=True, type=Path)
    parser.add_argument("--e4-0-summary", required=True, type=Path)
    parser.add_argument("--e4-1-summary", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--samples-per-segment", type=int, default=31)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.samples_per_segment < 3:
        raise ValueError("se requieren al menos tres muestras por segmento")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    e40 = json.loads(args.e4_0_summary.read_text(encoding="utf-8"))
    e41 = json.loads(args.e4_1_summary.read_text(encoding="utf-8"))
    if e40.get("experiment_id") != "E4.0" or e41.get("experiment_id") != "E4.1":
        raise ValueError("fuentes E4.0/E4.1 incorrectas")

    joints, link_bounds, link_triangles = load_robot(args.urdf, args.sdk_urdf_zip)
    fixture = e41["fixture"]
    pose = e41["platform_in_base"]
    table_width, table_depth = float(fixture["table_width_m"]), float(fixture["table_depth_m"])
    platform = transform(
        (pose["x_m"], pose["y_m"], pose["z_m"]),
        rotation_rpy(np.asarray([pose["roll_rad"], pose["pitch_rad"], pose["yaw_rad"]])),
    )
    base_to_platform = np.linalg.inv(platform)
    table_xy_low = np.asarray([-table_width / 2.0, 0.0])
    table_xy_high = np.asarray([table_width / 2.0, table_depth])
    box_lwh = np.asarray(fixture["box_lwh_m"], dtype=float)
    front_clearance = float(fixture["box_front_clearance_m"])
    box_low = np.asarray([-box_lwh[0] / 2.0, front_clearance, 0.0])
    box_high = np.asarray([box_lwh[0] / 2.0, front_clearance + box_lwh[1], box_lwh[2]])

    episode = e41["episode"]["head_lifter_waist_mean_rad"]
    inherited = {name: float(value) for name, value in episode.items()}
    supplied = e40["supplied_s2"]
    forward = e40["installed_forward_primitive"]
    back = e40["installed_back_primitive"]
    preposition = arm_state([0.0, -0.6, 0.0, 0.0, 0.0, 0.0, 0.0] * 2)
    preposition.update(inherited)
    # The supplied XML is [head_pitch, head_yaw] in the audited 20D contract.
    preposition["head_pitch_joint"] = 0.0
    preposition["head_yaw_joint"] = -0.65
    preposition["waist_yaw_joint"] = float(supplied["waist_ready_value"])

    waypoints = [("preposition", preposition)]
    for index, values in enumerate(forward["goals_14d"], 1):
        state = dict(inherited)
        state.update(arm_state(values))
        state["head_pitch_joint"] = preposition["head_pitch_joint"]
        state["head_yaw_joint"] = preposition["head_yaw_joint"]
        state["waist_yaw_joint"] = preposition["waist_yaw_joint"]
        waypoints.append((f"forward_{index}", state))
    for index, values in enumerate(back["goals_14d"], 1):
        state = dict(inherited)
        state.update(arm_state(values))
        state["head_pitch_joint"] = preposition["head_pitch_joint"]
        state["head_yaw_joint"] = preposition["head_yaw_joint"]
        state["waist_yaw_joint"] = preposition["waist_yaw_joint"]
        waypoints.append((f"back_{index}", state))

    samples = []
    for segment_index, ((start_name, start), (end_name, end)) in enumerate(zip(waypoints, waypoints[1:])):
        for sample_index, state in enumerate(interpolate(start, end, args.samples_per_segment)):
            if segment_index and sample_index == 0:
                continue
            samples.append((f"{start_name}->{end_name}", segment_index, sample_index, state))

    top_events = []
    exact_top_events = []
    box_events = []
    min_above_top = None
    min_below_top = None
    mesh_bounds_output = {}
    for link, (low, high) in sorted(link_bounds.items()):
        mesh_bounds_output[link] = {"min_link_m": low.tolist(), "max_link_m": high.tolist()}
    for sample_number, (segment, segment_index, sample_index, state) in enumerate(samples):
        poses = forward_kinematics(joints, state)
        for link, (low, high) in link_bounds.items():
            points_platform = apply(corners(low, high), base_to_platform @ poses[link])
            local_low, local_high = points_platform.min(axis=0), points_platform.max(axis=0)
            xy_overlap = aabb_overlap(local_low[:2], local_high[:2], table_xy_low, table_xy_high)
            if xy_overlap:
                if local_low[2] <= 0.0 <= local_high[2]:
                    event = {
                        "sample": sample_number, "segment": segment,
                        "segment_sample": sample_index, "link": link,
                        "aabb_min_platform_m": local_low.tolist(),
                        "aabb_max_platform_m": local_high.tolist(),
                    }
                    top_events.append(event)
                    triangles = link_triangles.get(link)
                    if triangles is not None:
                        matrix = base_to_platform @ poses[link]
                        triangles_platform = apply(triangles.reshape(-1, 3), matrix).reshape(-1, 3, 3)
                        if triangle_plane_hits_rectangle(triangles_platform, table_xy_low, table_xy_high):
                            exact_top_events.append({
                                "sample": sample_number, "segment": segment,
                                "segment_sample": sample_index, "link": link,
                            })
                elif local_low[2] > 0.0:
                    candidate = (float(local_low[2]), link, sample_number, segment)
                    min_above_top = candidate if min_above_top is None or candidate < min_above_top else min_above_top
                else:
                    candidate = (float(-local_high[2]), link, sample_number, segment)
                    min_below_top = candidate if min_below_top is None or candidate < min_below_top else min_below_top
            if aabb_overlap(local_low, local_high, box_low, box_high):
                box_events.append({
                    "sample": sample_number, "segment": segment,
                    "segment_sample": sample_index, "link": link,
                    "aabb_min_platform_m": local_low.tolist(),
                    "aabb_max_platform_m": local_high.tolist(),
                })

    top_links = sorted({event["link"] for event in top_events})
    exact_top_links = sorted({event["link"] for event in exact_top_events})
    box_links = sorted({event["link"] for event in box_events})
    blockers = [
        "tabletop_thickness_and_underside_not_measured",
        "table_legs_and_crossmembers_not_measured",
        "vendor_preposition_entry_state_is_undefined",
        "ready_lifter_is_inherited_not_vendor_defined",
        "back_primitive_is_not_exact_inverse_and_does_not_restore_full_state",
        "link_local_aabb_is_conservative_not_triangle_level_collision",
        "self_collision_and_force_limits_not_certified",
    ]
    if exact_top_events:
        blockers.append("triangle_mesh_tabletop_surface_intersections_detected")
    elif top_events:
        blockers.append("potential_tabletop_surface_intersections_detected_by_conservative_aabb")
    if box_events:
        blockers.append("potential_B0_intersections_detected")

    status = (
        "SOLID_TABLETOP_CANDIDATE_REJECTED_BY_VENDOR_URDF_SWEEP"
        if exact_top_events
        else "PARTIAL_CONSERVATIVE_COLLISION_MODEL_PHYSICAL_GATE_CLOSED"
    )
    result = {
        "schema": "cruzr-s2-vla-fixture-collision-e4.1c-v1",
        "experiment_id": "E4.1C",
        "status": status,
        "mode": "offline_fk_link_aabb_no_robot_no_inference_no_publisher",
        "method": "URDF_FK_plus_transformed_link-local-collision-AABBs",
        "trajectory_scope": {
            "sequence": [name for name, _ in waypoints],
            "segments": len(waypoints) - 1,
            "samples_per_segment": args.samples_per_segment,
            "unique_samples": len(samples),
            "entry_into_preposition_modeled": False,
            "lifter_source": "episode_90_mean_correlated_fixture_state",
        },
        "fixture": {
            "platform_in_base": pose,
            "table_width_m": table_width, "table_depth_m": table_depth,
            "top_surface_z_platform_m": 0.0,
            "top_thickness_m": None,
            "legs_and_crossmembers": None,
            "B0_aabb_platform_m": {"min": box_low.tolist(), "max": box_high.tolist()},
        },
        "robot_geometry": {
            "collision_links": len(link_bounds),
            "mesh_bounds": mesh_bounds_output,
        },
        "results": {
            "potential_tabletop_surface_event_count": len(top_events),
            "potential_tabletop_surface_links": top_links,
            "triangle_mesh_tabletop_surface_event_count": len(exact_top_events),
            "triangle_mesh_tabletop_surface_links": exact_top_links,
            "potential_B0_event_count": len(box_events),
            "potential_B0_links": box_links,
            "nearest_aabb_above_top_m": None if min_above_top is None else min_above_top[0],
            "nearest_aabb_above_top_context": None if min_above_top is None else {
                "link": min_above_top[1], "sample": min_above_top[2], "segment": min_above_top[3]},
            "nearest_aabb_below_top_m": None if min_below_top is None else min_below_top[0],
            "nearest_aabb_below_top_context": None if min_below_top is None else {
                "link": min_below_top[1], "sample": min_below_top[2], "segment": min_below_top[3]},
            "tabletop_events": top_events,
            "triangle_mesh_tabletop_events": exact_top_events,
            "B0_events": box_events,
        },
        "gates": {
            "tabletop_surface_clear_in_conservative_model": not top_events,
            "tabletop_surface_clear_at_triangle_mesh_level": not exact_top_events,
            "B0_clear_in_conservative_model": not box_events,
            "full_table_geometry_validated": False,
            "entry_path_validated": False,
            "recovery_validated": False,
            "physical_test_authorized": False,
        },
        "blockers": blockers,
        "source_sha256": {
            str(args.urdf): sha256(args.urdf),
            str(args.sdk_urdf_zip): sha256(args.sdk_urdf_zip),
            str(args.e4_0_summary): sha256(args.e4_0_summary),
            str(args.e4_1_summary): sha256(args.e4_1_summary),
        },
    }
    output = args.output_dir / "summary.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    remaining = (
        [
            "confirm_actual_clamp_collision_geometry_against_vendor_URDF",
            "derive_a_new_fixture_pose_or_a_rigid_platform_with_verified_cutouts",
        ]
        if exact_top_events else
        [
            "tabletop_thickness_and_underside_height",
            "nearest_leg_or_crossmember_boxes_relative_to_platform_frame",
        ]
    )
    contract = {
        "experiment_id": "E4.1C", "status": result["status"],
        "tabletop_surface_clear_conservative": not top_events,
        "tabletop_surface_clear_triangle_mesh": not exact_top_events,
        "B0_clear_conservative": not box_events,
        "tabletop_potential_links": top_links,
        "B0_potential_links": box_links,
        "full_table_geometry_validated": False,
        "physical_test_authorized": False,
        "minimal_remaining_resolution": remaining,
    }
    (args.output_dir / "collision_contract.yaml").write_text(
        yaml.safe_dump(contract, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"E4.1C_SAMPLES={len(samples)}; COLLISION_LINKS={len(link_bounds)}")
    print(f"TABLETOP_POTENTIAL_EVENTS={len(top_events)}; LINKS={','.join(top_links) or 'none'}")
    print(f"TABLETOP_TRIANGLE_EVENTS={len(exact_top_events)}; LINKS={','.join(exact_top_links) or 'none'}")
    print(f"B0_POTENTIAL_EVENTS={len(box_events)}; LINKS={','.join(box_links) or 'none'}")
    print("FULL_TABLE_GEOMETRY_VALIDATED=0")
    print("PHYSICAL_TEST_AUTHORIZED=0")
    print(f"E4.1C_STATUS={result['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
