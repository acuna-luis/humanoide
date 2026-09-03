#!/usr/bin/env python3
"""Derive an offline tabletop pose/cutout candidate from the E4.1 trajectory."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
import yaml

import analyze_vla_fixture_collision_e4_1c as geometry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--urdf", required=True, type=Path)
    parser.add_argument("--sdk-urdf-zip", required=True, type=Path)
    parser.add_argument("--e4-0-summary", required=True, type=Path)
    parser.add_argument("--e4-1-summary", required=True, type=Path)
    parser.add_argument("--e4-1d-summary", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_samples(e40: dict, e41: dict, samples_per_segment: int):
    inherited = {
        name: float(value)
        for name, value in e41["episode"]["head_lifter_waist_mean_rad"].items()
    }
    supplied = e40["supplied_s2"]
    preposition = geometry.arm_state([0.0, -0.6, 0.0, 0.0, 0.0, 0.0, 0.0] * 2)
    preposition.update(inherited)
    preposition["head_pitch_joint"] = 0.0
    preposition["head_yaw_joint"] = -0.65
    preposition["waist_yaw_joint"] = float(supplied["waist_ready_value"])

    waypoints = [("preposition", preposition)]
    for label, primitive in (
        ("forward", e40["installed_forward_primitive"]),
        ("back", e40["installed_back_primitive"]),
    ):
        for index, values in enumerate(primitive["goals_14d"], 1):
            state = dict(inherited)
            state.update(geometry.arm_state(values))
            state["head_pitch_joint"] = preposition["head_pitch_joint"]
            state["head_yaw_joint"] = preposition["head_yaw_joint"]
            state["waist_yaw_joint"] = preposition["waist_yaw_joint"]
            waypoints.append((f"{label}_{index}", state))

    samples = []
    for segment_index, ((start_name, start), (end_name, end)) in enumerate(
        zip(waypoints, waypoints[1:])
    ):
        for segment_sample, state in enumerate(
            geometry.interpolate(start, end, samples_per_segment)
        ):
            if segment_index and segment_sample == 0:
                continue
            samples.append((f"{start_name}->{end_name}", segment_sample, state))
    return waypoints, samples


def cross_section_points(triangles: np.ndarray, plane_z: float) -> np.ndarray:
    eps = 1e-9
    z = triangles[:, :, 2] - plane_z
    selected = triangles[(z.min(axis=1) <= eps) & (z.max(axis=1) >= -eps)]
    if not len(selected):
        return np.empty((0, 2), dtype=float)
    selected_z = selected[:, :, 2] - plane_z
    pieces = []
    for first, second in ((0, 1), (1, 2), (2, 0)):
        a, b = selected[:, first], selected[:, second]
        za, zb = selected_z[:, first], selected_z[:, second]
        on_a = np.abs(za) <= eps
        if np.any(on_a):
            pieces.append(a[on_a, :2])
        crossing = za * zb < 0.0
        if np.any(crossing):
            alpha = -za[crossing] / (zb[crossing] - za[crossing])
            point = a[crossing] + alpha[:, None] * (b[crossing] - a[crossing])
            pieces.append(point[:, :2])
    return np.vstack(pieces) if pieces else np.empty((0, 2), dtype=float)


def interval_grid(low: float, high: float, step: float) -> np.ndarray:
    if low > high + 1e-12:
        return np.empty(0)
    count = int(math.floor((high - low) / step + 1e-12))
    values = low + step * np.arange(count + 1)
    if not len(values) or values[-1] < high - 1e-9:
        values = np.append(values, high)
    return values


def rectangles_separated(first: np.ndarray, second: np.ndarray) -> bool:
    axes = (
        np.asarray([1.0, 0.0]),
        np.asarray([0.0, 1.0]),
        first[1] - first[0],
        first[3] - first[0],
    )
    for axis in axes:
        axis = axis / np.linalg.norm(axis)
        projection_a = first @ axis
        projection_b = second @ axis
        if projection_a.max() < projection_b.min() or projection_b.max() < projection_a.min():
            return True
    return False


def box_corners(bounds: np.ndarray) -> np.ndarray:
    return np.asarray([
        [bounds[0, 0], bounds[0, 1]],
        [bounds[1, 0], bounds[0, 1]],
        [bounds[1, 0], bounds[1, 1]],
        [bounds[0, 0], bounds[1, 1]],
    ])


def search_solid_table(
    support_corners: np.ndarray,
    danger_rectangles: list[np.ndarray],
    width: float,
    depth: float,
    yaw_values: np.ndarray,
    translation_step: float,
) -> dict:
    feasible = 0
    clear = 0
    best = None
    danger_polygons = [box_corners(bounds) for bounds in danger_rectangles]
    for yaw_deg in yaw_values:
        yaw = math.radians(float(yaw_deg))
        width_axis = np.asarray([math.cos(yaw), math.sin(yaw)])
        depth_axis = np.asarray([-math.sin(yaw), math.cos(yaw)])
        support_width = support_corners @ width_axis
        support_depth = support_corners @ depth_axis
        origin_width_low = support_width.max() - width / 2.0
        origin_width_high = support_width.min() + width / 2.0
        origin_depth_low = support_depth.max() - depth
        origin_depth_high = support_depth.min()
        for origin_width in interval_grid(origin_width_low, origin_width_high, translation_step):
            for origin_depth in interval_grid(origin_depth_low, origin_depth_high, translation_step):
                feasible += 1
                origin = width_axis * origin_width + depth_axis * origin_depth
                table = np.asarray([
                    origin - width_axis * width / 2.0,
                    origin + width_axis * width / 2.0,
                    origin + width_axis * width / 2.0 + depth_axis * depth,
                    origin - width_axis * width / 2.0 + depth_axis * depth,
                ])
                if not all(rectangles_separated(table, danger) for danger in danger_polygons):
                    continue
                clear += 1
                score = (abs(float(yaw_deg)), float(np.linalg.norm(origin)), float(yaw_deg))
                if best is None or score < best[0]:
                    best = (score, origin.copy(), table.copy())
    candidate = None
    if best is not None:
        score, origin, table = best
        candidate = {
            "yaw_delta_deg": score[2],
            "origin_translation_nominal_platform_m": origin.tolist(),
            "origin_translation_norm_m": score[1],
            "table_corners_nominal_platform_m": table.tolist(),
        }
    return {
        "support_feasible_grid_candidates": feasible,
        "collision_free_grid_candidates": clear,
        "best_candidate": candidate,
    }


def outward_round(value: float, quantum: float, direction: str) -> float:
    scaled = value / quantum
    if direction == "down":
        return math.floor(scaled + 1e-12) * quantum
    return math.ceil(scaled - 1e-12) * quantum


def overlap(first: np.ndarray, second: np.ndarray) -> bool:
    return bool(
        first[0, 0] < second[1, 0]
        and second[0, 0] < first[1, 0]
        and first[0, 1] < second[1, 1]
        and second[0, 1] < first[1, 1]
    )


def write_svg(
    path: Path,
    width_m: float,
    depth_m: float,
    box_bounds: np.ndarray,
    support_bounds: np.ndarray,
    raw_bounds: dict[str, np.ndarray],
    cutouts: dict[str, np.ndarray],
) -> None:
    canvas_w, canvas_h = 1000, 560
    margin = 70
    scale = min((canvas_w - 2 * margin) / width_m, (canvas_h - 2 * margin) / depth_m)
    def xy(point):
        x = margin + (point[0] + width_m / 2.0) * scale
        y = canvas_h - margin - point[1] * scale
        return x, y
    def rect(bounds, color, opacity, stroke, dash=""):
        x0, y0 = xy([bounds[0, 0], bounds[1, 1]])
        x1, y1 = xy([bounds[1, 0], bounds[0, 1]])
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        return (
            f'<rect x="{x0:.2f}" y="{y0:.2f}" width="{x1-x0:.2f}" '
            f'height="{y1-y0:.2f}" fill="{color}" fill-opacity="{opacity}" '
            f'stroke="{stroke}" stroke-width="2"{dash_attr}/>'
        )
    table = np.asarray([[-width_m / 2.0, 0.0], [width_m / 2.0, depth_m]])
    elements = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="560" viewBox="0 0 1000 560">',
        '<rect width="1000" height="560" fill="white"/>',
        '<text x="70" y="35" font-family="sans-serif" font-size="22">E4.1E — tablero 1,80 × 0,80 m, vista superior</text>',
        rect(table, "#d9dde3", "1", "#30343b"),
        rect(support_bounds, "#66bb6a", "0.30", "#2e7d32"),
        rect(box_bounds, "#1565c0", "0.30", "#0d47a1"),
    ]
    for side in ("left", "right"):
        elements.append(rect(raw_bounds[side], "#ff9800", "0.20", "#ef6c00", "8 5"))
        elements.append(rect(cutouts[side], "#ef5350", "0.65", "#b71c1c"))
    elements.extend([
        '<text x="70" y="530" font-family="sans-serif" font-size="16">Azul: B0 · verde: apoyo +50 mm · naranja: barrido crudo · rojo: muescas candidatas upstream</text>',
        '</svg>',
    ])
    path.write_text("\n".join(elements) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    contract = yaml.safe_load(args.contract.read_text(encoding="utf-8"))
    e40 = json.loads(args.e4_0_summary.read_text(encoding="utf-8"))
    e41 = json.loads(args.e4_1_summary.read_text(encoding="utf-8"))
    e41d = json.loads(args.e4_1d_summary.read_text(encoding="utf-8"))
    if e40.get("experiment_id") != "E4.0" or e41.get("experiment_id") != "E4.1":
        raise ValueError("fuentes E4.0/E4.1 incorrectas")
    if e41d.get("experiment_id") != "E4.1D" or not e41d["conclusions"]["solid_tabletop_rejection_remains_when_pgc_and_fingers_are_excluded"]:
        raise ValueError("E4.1D no demuestra la dependencia upstream requerida")

    samples_per_segment = int(contract["trajectory"]["samples_per_segment"])
    if samples_per_segment < 31:
        raise ValueError("el barrido no puede ser menos denso que E4.1C")
    waypoints, samples = build_samples(e40, e41, samples_per_segment)
    joints, _, link_triangles = geometry.load_robot(args.urdf, args.sdk_urdf_zip)
    pose = e41["platform_in_base"]
    nominal_platform = geometry.transform(
        (pose["x_m"], pose["y_m"], pose["z_m"]),
        geometry.rotation_rpy(np.asarray([pose["roll_rad"], pose["pitch_rad"], pose["yaw_rad"]])),
    )
    base_to_nominal_platform = np.linalg.inv(nominal_platform)

    included_links = contract["geometry"]["included_links"]
    if sorted(included_links) != sorted(e41d["e4_1c_collision_partition"]["links_by_group"]["upstream_wrist_or_force_sensor"]):
        raise ValueError("los links upstream no coinciden con E4.1D")
    plane_offsets = [float(value) for value in contract["geometry"]["plane_height_offsets_m"]]
    points_by_side = {"left": [], "right": []}
    points_by_link = {link: [] for link in included_links}
    hit_conditions = 0
    for _, _, state in samples:
        poses = geometry.forward_kinematics(joints, state)
        for link in included_links:
            triangles_platform = geometry.apply(
                link_triangles[link].reshape(-1, 3),
                base_to_nominal_platform @ poses[link],
            ).reshape(-1, 3, 3)
            for plane_z in plane_offsets:
                section = cross_section_points(triangles_platform, plane_z)
                if not len(section):
                    continue
                hit_conditions += 1
                side = "left" if link.startswith("L_") else "right"
                points_by_side[side].append(section)
                points_by_link[link].append(section)

    side_points = {side: np.vstack(parts) for side, parts in points_by_side.items()}
    link_bounds = {}
    for link, parts in points_by_link.items():
        points = np.vstack(parts)
        link_bounds[link] = {"min_m": points.min(axis=0).tolist(), "max_m": points.max(axis=0).tolist()}
    raw_bounds = {
        side: np.vstack((points.min(axis=0), points.max(axis=0)))
        for side, points in side_points.items()
    }

    uncertainty = e41["uncertainty"]
    xy_half = np.asarray(uncertainty["platform_position_half_range_m"][:2], dtype=float)
    translation_uncertainty = float(np.linalg.norm(xy_half))
    max_radius = max(float(np.linalg.norm(points, axis=1).max()) for points in side_points.values())
    yaw_half_rad = math.radians(float(uncertainty["yaw_half_range_deg"]))
    yaw_uncertainty = 2.0 * max_radius * math.sin(yaw_half_rad / 2.0)
    engineering_clearance = float(contract["geometry"]["engineering_clearance_m"])
    quantum = float(contract["geometry"]["output_rounding_m"])
    raw_margin = translation_uncertainty + yaw_uncertainty + engineering_clearance
    total_margin = outward_round(raw_margin, quantum, "up")

    fixture = e41["fixture"]
    table_width = float(fixture["table_width_m"])
    table_depth = float(fixture["table_depth_m"])
    box_lwh = np.asarray(fixture["box_lwh_m"], dtype=float)
    front_clearance = float(fixture["box_front_clearance_m"])
    box_bounds = np.asarray([
        [-box_lwh[0] / 2.0, front_clearance],
        [box_lwh[0] / 2.0, front_clearance + box_lwh[1]],
    ])
    support_margin = float(contract["support"]["margin_around_B0_footprint_m"])
    support_bounds = box_bounds + np.asarray([[-support_margin, -support_margin], [support_margin, support_margin]])
    support_corners = box_corners(support_bounds)

    danger_rectangles = {}
    cutouts = {}
    for side, bounds in raw_bounds.items():
        danger = bounds + np.asarray([[-total_margin, -total_margin], [total_margin, total_margin]])
        danger_rectangles[side] = danger
        cutout = np.asarray([
            [outward_round(danger[0, 0], quantum, "down"), 0.0],
            [outward_round(danger[1, 0], quantum, "up"), outward_round(max(0.0, danger[1, 1]), quantum, "up")],
        ])
        cutouts[side] = cutout

    if any(overlap(cutout, support_bounds) for cutout in cutouts.values()):
        raise ValueError("las muescas upstream invaden el apoyo requerido de B0")
    table_bounds = np.asarray([[-table_width / 2.0, 0.0], [table_width / 2.0, table_depth]])
    if any(np.any(cutout[0] < table_bounds[0]) or np.any(cutout[1] > table_bounds[1]) for cutout in cutouts.values()):
        raise ValueError("una muesca sale del tablero nominal")

    search = contract["solid_table_search"]
    aligned_yaws = np.arange(
        float(search["aligned_yaw_range_deg"][0]),
        float(search["aligned_yaw_range_deg"][1]) + float(search["aligned_yaw_step_deg"]) * 0.1,
        float(search["aligned_yaw_step_deg"]),
    )
    aligned = search_solid_table(
        support_corners, list(danger_rectangles.values()), table_width, table_depth,
        aligned_yaws, float(search["aligned_translation_step_m"]),
    )
    global_yaws = np.arange(
        float(search["global_yaw_range_deg"][0]),
        float(search["global_yaw_range_deg"][1]) + float(search["global_yaw_step_deg"]) * 0.1,
        float(search["global_yaw_step_deg"]),
    )
    global_search = search_solid_table(
        support_corners, list(danger_rectangles.values()), table_width, table_depth,
        global_yaws, float(search["global_translation_step_m"]),
    )
    refined = None
    coarse_candidate = global_search["best_candidate"]
    if coarse_candidate is not None:
        center = float(coarse_candidate["yaw_delta_deg"])
        half_range = float(search["refinement_yaw_half_range_deg"])
        step = float(search["refinement_yaw_step_deg"])
        refined_yaws = np.arange(max(-90.0, center - half_range), min(90.0, center + half_range) + step * 0.1, step)
        refined = search_solid_table(
            support_corners, list(danger_rectangles.values()), table_width, table_depth,
            refined_yaws, float(search["refinement_translation_step_m"]),
        )

    best_global = None if refined is None else refined["best_candidate"]
    if aligned["collision_free_grid_candidates"] != 0:
        raise ValueError("se encontró una mesa sólida alineada inesperada")
    if best_global is None:
        raise ValueError("la búsqueda global no produjo la referencia comparativa esperada")
    candidate_translation = np.asarray(best_global["origin_translation_nominal_platform_m"])
    nominal_rotation = nominal_platform[:2, :2]
    candidate_base_xy = nominal_platform[:2, 3] + nominal_rotation @ candidate_translation
    best_global["origin_in_base_m"] = candidate_base_xy.tolist()
    best_global["yaw_in_base_deg"] = float(pose["yaw_deg"]) + float(best_global["yaw_delta_deg"])
    best_global["operationally_accepted"] = False
    best_global["rejection_reason"] = "outside_calibrated_scene_alignment_envelope"

    cutout_area = sum(
        float((bounds[1, 0] - bounds[0, 0]) * (bounds[1, 1] - bounds[0, 1]))
        for bounds in cutouts.values()
    )
    bridge_width = float(cutouts["right"][0, 0] - cutouts["left"][1, 0])
    support_gaps = {
        "left_m": float(support_bounds[0, 0] - cutouts["left"][1, 0]),
        "right_m": float(cutouts["right"][0, 0] - support_bounds[1, 0]),
    }

    result = {
        "schema": "cruzr-s2-vla-fixture-design-e4.1e/v1",
        "experiment_id": "E4.1E",
        "status": "UPSTREAM_CUTOUT_CANDIDATE_DERIVED_SOLID_ALIGNED_POSE_NOT_FOUND_CLAMP_AND_RECOVERY_UNRESOLVED",
        "mode": "local_read_only_no_robot_no_inference_no_publisher",
        "trajectory": {
            "sequence": [name for name, _ in waypoints],
            "samples_per_segment": samples_per_segment,
            "unique_samples": len(samples),
            "plane_height_offsets_m": plane_offsets,
            "sample_link_plane_hit_conditions": hit_conditions,
        },
        "uncertainty_and_clearance": {
            "platform_xy_translation_half_range_norm_m": translation_uncertainty,
            "platform_yaw_half_range_deg": float(uncertainty["yaw_half_range_deg"]),
            "yaw_displacement_at_sweep_radius_m": yaw_uncertainty,
            "vertical_plane_half_range_m": max(abs(value) for value in plane_offsets),
            "engineering_clearance_m": engineering_clearance,
            "unrounded_xy_margin_m": raw_margin,
            "applied_xy_margin_m": total_margin,
        },
        "fixed_scene": {
            "B0_pose_fixed": True,
            "B0_footprint_nominal_platform_m": box_bounds.tolist(),
            "required_support_footprint_nominal_platform_m": support_bounds.tolist(),
            "support_margin_m": support_margin,
            "table_width_m": table_width,
            "table_depth_m": table_depth,
        },
        "upstream_sweep": {
            "links": included_links,
            "link_cross_section_bounds_nominal_platform_m": link_bounds,
            "side_cross_section_bounds_nominal_platform_m": {
                side: bounds.tolist() for side, bounds in raw_bounds.items()
            },
            "danger_rectangles_with_margin_nominal_platform_m": {
                side: bounds.tolist() for side, bounds in danger_rectangles.items()
            },
        },
        "solid_table_pose_search": {
            "aligned_envelope": {
                "yaw_range_deg": search["aligned_yaw_range_deg"],
                "yaw_step_deg": search["aligned_yaw_step_deg"],
                "translation_step_m": search["aligned_translation_step_m"],
                **aligned,
            },
            "global_reference_only": {
                "yaw_range_deg": search["global_yaw_range_deg"],
                "coarse": global_search,
                "refined": refined,
                "best_refined_candidate": best_global,
            },
        },
        "upstream_cutout_candidate": {
            "coordinate_frame": "nominal_platform_frame",
            "type": "two_open_front_rectangular_notches",
            "left_bounds_m": cutouts["left"].tolist(),
            "right_bounds_m": cutouts["right"].tolist(),
            "total_removed_area_m2": cutout_area,
            "removed_fraction_of_tabletop": cutout_area / (table_width * table_depth),
            "central_front_bridge_width_m": bridge_width,
            "gap_to_required_B0_support_m": support_gaps,
            "overlaps_required_B0_support": False,
            "includes_actual_clamp_geometry": False,
            "manufacturing_or_modification_authorized": False,
        },
        "gates": {
            "aligned_solid_table_candidate_found": False,
            "upstream_only_cutout_candidate_found": True,
            "actual_clamp_envelope_validated": False,
            "entry_path_validated": False,
            "recovery_validated": False,
            "box_placement_authorized": False,
            "table_approach_or_modification_authorized": False,
            "physical_test_authorized": False,
            "next_authorized_work": "AUDIT_OFFICIAL_SUPPLIER_CLAMP_GEOMETRY_OFFLINE",
        },
        "blockers": [
            "actual passive clamp CAD/dimensions are unavailable",
            "cutout candidate covers only wrist and force-sensor meshes",
            "no aligned solid tabletop pose exists on the declared grid",
            "the only solid-pose reference requires a large scene rotation and translation",
            "entry into preposition and complete recovery remain unresolved",
            "table thickness, legs and structural feasibility of notches are not modeled",
        ],
        "source_sha256": {
            str(args.contract): sha256(args.contract),
            str(args.urdf): sha256(args.urdf),
            str(args.sdk_urdf_zip): sha256(args.sdk_urdf_zip),
            str(args.e4_0_summary): sha256(args.e4_0_summary),
            str(args.e4_1_summary): sha256(args.e4_1_summary),
            str(args.e4_1d_summary): sha256(args.e4_1d_summary),
        },
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.output_dir / "cutout_candidate.yaml").write_text(
        yaml.safe_dump(
            {
                "frame": "nominal_platform_frame",
                "table_m": {"width": table_width, "depth": table_depth},
                "B0_support_bounds_m": support_bounds.tolist(),
                "applied_xy_margin_m": total_margin,
                "left_open_front_notch_bounds_m": cutouts["left"].tolist(),
                "right_open_front_notch_bounds_m": cutouts["right"].tolist(),
                "physical_use_authorized": False,
            },
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    write_svg(
        args.output_dir / "fixture_plan.svg", table_width, table_depth,
        box_bounds, support_bounds, raw_bounds, cutouts,
    )

    print(f"E4.1E_SAMPLES={len(samples)}; PLANE_LEVELS={len(plane_offsets)}")
    print(f"E4.1E_APPLIED_XY_MARGIN_M={total_margin:.3f}")
    print(f"E4.1E_ALIGNED_SOLID_CANDIDATES={aligned['collision_free_grid_candidates']}")
    print(
        "E4.1E_CUTOUT_LEFT="
        f"x:{cutouts['left'][0,0]:.3f}..{cutouts['left'][1,0]:.3f},"
        f"y:0.000..{cutouts['left'][1,1]:.3f}"
    )
    print(
        "E4.1E_CUTOUT_RIGHT="
        f"x:{cutouts['right'][0,0]:.3f}..{cutouts['right'][1,0]:.3f},"
        f"y:0.000..{cutouts['right'][1,1]:.3f}"
    )
    print(f"E4.1E_GLOBAL_REFERENCE_YAW_DELTA_DEG={best_global['yaw_delta_deg']:.3f}")
    print("E4.1E_PHYSICAL_TEST_AUTHORIZED=0")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise
