#!/usr/bin/env python3
"""Audit the reduced READY <-> task-0 ENTRY transition entirely offline.

E6.1C deliberately keeps the fourteen arm joints at the previously observed
vendor READY state.  Only head, lifter and waist move.  The program samples
the joint-space path, checks SDK limits, exact monitored mesh contacts,
documentary clamp proxies and the reconstructed SUPPORTED_LOW fixture.  It has
no ROS, network, container, process or command-publisher code.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
from typing import Any

import numpy as np


EXPECTED_SCHEMA = "cruzr-s2-vla-ready-entry-transition-e6.1c-v1"
EXPECTED_NEAR_PAIRS = {
    ("L_elbow_yaw_link", "L_wrist_roll_link"),
    ("R_elbow_yaw_link", "R_wrist_roll_link"),
    ("L_shoulder_roll_link", "torso_link"),
    ("R_shoulder_roll_link", "torso_link"),
}
WRONG_EFFECTOR_TOKENS = ("pgc", "finger")
GROUPS = {
    ("head", "single"): ("head_pitch_joint", "head_yaw_joint"),
    ("lifter", "single"): (
        "lifter_pitch_1_joint",
        "lifter_pitch_2_joint",
        "lifter_pitch_3_joint",
    ),
    ("waist", "single"): ("waist_yaw_joint",),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--entry-contract", type=Path, required=True)
    parser.add_argument("--ready-source", type=Path, required=True)
    parser.add_argument("--entry-xml", type=Path, required=True)
    parser.add_argument("--recovery-xml", type=Path, required=True)
    parser.add_argument("--e6-1a-report", type=Path, required=True)
    parser.add_argument("--sdk-urdf", type=Path, required=True)
    parser.add_argument("--sdk-urdf-zip", type=Path, required=True)
    parser.add_argument("--document-proxy-report", type=Path, required=True)
    parser.add_argument("--fk-helper", type=Path, required=True)
    parser.add_argument("--path-helper", type=Path, required=True)
    parser.add_argument("--mesh-helper", type=Path, required=True)
    parser.add_argument("--geometry-helper", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def vector(value: Any, length: int, label: str) -> list[float]:
    if not isinstance(value, list) or len(value) != length:
        raise ValueError(f"{label}: expected {length} values")
    parsed = [float(item) for item in value]
    if not all(math.isfinite(item) for item in parsed):
        raise ValueError(f"{label}: non-finite value")
    return parsed


def quintic_states(
    start: list[float], target: list[float], order: list[str], count: int
) -> list[dict[str, float]]:
    first = np.asarray(start, dtype=float)
    delta = np.asarray(target, dtype=float) - first
    result = []
    for index in range(count):
        phase = index / (count - 1)
        scale = 10.0 * phase**3 - 15.0 * phase**4 + 6.0 * phase**5
        result.append(dict(zip(order, first + delta * scale, strict=True)))
    return result


def parse_preview(
    path: Path, expected: dict[str, float], expected_duration: float
) -> dict[str, Any]:
    root = ET.parse(path).getroot()
    actions = root.findall(".//Action")
    if len(actions) != 3:
        raise ValueError(f"{path.name}: expected exactly three actions")
    observed: dict[str, float] = {}
    groups = []
    for action in actions:
        if action.attrib.get("ID") != "MetaMove" or "name" in action.attrib:
            raise ValueError(f"{path.name}: named or non-MetaMove action")
        key = (action.attrib.get("type", ""), action.attrib.get("location", ""))
        names = GROUPS.get(key)
        if names is None:
            raise ValueError(f"{path.name}: forbidden component {key}")
        duration = float(action.attrib.get("duration", "nan"))
        if not math.isclose(duration, expected_duration, abs_tol=1e-12):
            raise ValueError(f"{path.name}: duration mismatch")
        values = [float(item.strip()) for item in action.attrib["joint_angles"].split(";")]
        if len(values) != len(names) or not all(math.isfinite(item) for item in values):
            raise ValueError(f"{path.name}: malformed joint_angles")
        observed.update(zip(names, values, strict=True))
        groups.append(key[0])
    if set(observed) != set(expected):
        raise ValueError(f"{path.name}: commanded axes mismatch")
    maximum_error = max(abs(observed[name] - expected[name]) for name in expected)
    if maximum_error > 1e-12:
        raise ValueError(f"{path.name}: endpoint mismatch")
    parallel = root.find(".//Parallel")
    if parallel is None or parallel.attrib.get("threshold") != "3":
        raise ValueError(f"{path.name}: parallel threshold mismatch")
    return {
        "path": str(path),
        "sha256": digest(path),
        "groups": sorted(groups),
        "action_count": len(actions),
        "duration_seconds": expected_duration,
        "maximum_endpoint_error_rad": maximum_error,
        "arm_actions": 0,
    }


def obb_for_fixture(report: dict[str, Any], width: float, depth: float, thickness: float):
    reconstruction = report["scene_reconstruction"]
    yaw = float(reconstruction["platform_yaw_rad"])
    cosine, sine = math.cos(yaw), math.sin(yaw)
    pose = np.eye(4)
    pose[:3, :3] = np.asarray(
        [[cosine, -sine, 0.0], [sine, cosine, 0.0], [0.0, 0.0, 1.0]]
    )
    pose[:3, 3] = np.asarray(
        reconstruction["platform_front_center_in_base_m"], dtype=float
    )
    support = (
        np.asarray([-width / 2.0, 0.0, -thickness]),
        np.asarray([width / 2.0, depth, 0.0]),
    )
    box = (
        np.asarray([-0.603 / 2.0, 0.05, 0.0]),
        np.asarray([0.603 / 2.0, 0.05 + 0.397, 0.217]),
    )
    return pose, support, box


def main() -> int:
    args = parse_args()
    sources = [
        args.contract,
        args.entry_contract,
        args.ready_source,
        args.entry_xml,
        args.recovery_xml,
        args.e6_1a_report,
        args.sdk_urdf,
        args.sdk_urdf_zip,
        args.document_proxy_report,
        args.fk_helper,
        args.path_helper,
        args.mesh_helper,
        args.geometry_helper,
    ]
    for source in sources:
        if not source.is_file():
            raise ValueError(f"missing source: {source}")
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    if contract.get("schema") != EXPECTED_SCHEMA:
        raise ValueError("unexpected E6.1C contract")
    if contract.get("physical_execution_authorized") is not False:
        raise ValueError("offline contract unexpectedly authorizes movement")
    if digest(args.ready_source) != contract["sources"]["observed_ready_reference_sha256"]:
        raise ValueError("READY reference hash changed")
    if digest(args.entry_contract) != contract["sources"]["entry_contract_sha256"]:
        raise ValueError("ENTRY contract hash changed")

    entry_contract = json.loads(args.entry_contract.read_text(encoding="utf-8"))
    ready_source = json.loads(args.ready_source.read_text(encoding="utf-8"))
    order = contract["joint_order"]
    ready = vector(contract["observed_ready_reference_20d_rad"], 20, "READY")
    target = vector(contract["entry_target_20d_rad"], 20, "target")
    frozen = vector(contract["frozen_dataset_entry_20d_rad"], 20, "frozen ENTRY")
    if ready_source.get("positions") != ready:
        raise ValueError("READY reference does not match its source")
    if entry_contract["candidate"]["joint_order"] != order:
        raise ValueError("joint order changed")
    if entry_contract["candidate"]["entry_state_20d_rad"] != frozen:
        raise ValueError("frozen ENTRY changed")
    if target[:14] != ready[:14] or target[14:] != frozen[14:]:
        raise ValueError("reduced transition endpoint changed")
    if contract["commanded_joint_names"] != order[14:]:
        raise ValueError("only the six locked axes may be commanded")
    if contract["uncommanded_arm_joint_names"] != order[:14]:
        raise ValueError("arm hold set changed")

    design = contract["trajectory_design"]
    duration = float(design["entry_duration_seconds"])
    if duration != 12.0 or float(design["recovery_to_ready_duration_seconds"]) != duration:
        raise ValueError("unexpected transition duration")
    entry_expected = dict(zip(order[14:], target[14:], strict=True))
    ready_expected = dict(zip(order[14:], ready[14:], strict=True))
    entry_preview = parse_preview(args.entry_xml, entry_expected, duration)
    recovery_preview = parse_preview(args.recovery_xml, ready_expected, duration)

    delta = np.asarray(target) - np.asarray(ready)
    largest_delta_index = int(np.argmax(np.abs(delta)))
    maximum_velocity = float(np.max(np.abs(delta))) * 1.875 / duration
    maximum_acceleration = float(np.max(np.abs(delta))) * 5.773502691896258 / duration**2
    if maximum_velocity > float(design["maximum_velocity_rad_s"]):
        raise ValueError("velocity design envelope exceeded")
    if maximum_acceleration > float(design["maximum_acceleration_rad_s2"]):
        raise ValueError("acceleration design envelope exceeded")
    if not math.isclose(maximum_velocity, float(design["analytic_maximum_velocity_rad_s"]), abs_tol=1e-12):
        raise ValueError("stored velocity metric changed")
    if not math.isclose(maximum_acceleration, float(design["analytic_maximum_acceleration_rad_s2"]), abs_tol=1e-12):
        raise ValueError("stored acceleration metric changed")

    count = int(design["geometry_sample_count_each_direction"])
    states = quintic_states(ready, target, order, count)
    fk = load_module(args.fk_helper, "e6_1c_fk")
    path = load_module(args.path_helper, "e6_1c_path")
    mesh = load_module(args.mesh_helper, "e6_1c_mesh")
    geometry = load_module(args.geometry_helper, "e6_1c_geometry")
    joints, bounds, triangles = fk.load_robot(args.sdk_urdf, args.sdk_urdf_zip)
    limit_violations = path.limit_violations(joints, states, args.sdk_urdf)
    poses = [fk.forward_kinematics(joints, state) for state in states]
    graph = path.graph_distances(joints)
    links = sorted(bounds)
    wrong_effectors = {
        link for link in links if any(token in link for token in WRONG_EFFECTOR_TOKENS)
    }

    overlap_samples: dict[tuple[str, str], list[int]] = {}
    for sample_index, current_poses in enumerate(poses):
        boxes = {
            link: path.obb_for_link(current_poses[link], local_bounds)
            for link, local_bounds in bounds.items()
            if link not in wrong_effectors
        }
        active_links = sorted(boxes)
        for left_index, left in enumerate(active_links):
            for right in active_links[left_index + 1 :]:
                pair = (left, right)
                if not path.obb_overlap(boxes[left], boxes[right]):
                    continue
                if graph[pair] > 3 or pair in EXPECTED_NEAR_PAIRS:
                    overlap_samples.setdefault(pair, []).append(sample_index)
    monitored = sorted(set(overlap_samples) | EXPECTED_NEAR_PAIRS)
    roots = {
        link: mesh.BvhNode(
            triangles[link], np.arange(len(triangles[link]), dtype=np.int64)
        )
        for pair in monitored
        for link in pair
    }
    exact_hits = []
    for left, right in monitored:
        for sample_index in overlap_samples.get((left, right), []):
            intersects, _, triangle_ids = mesh.mesh_intersection(
                triangles[left], roots[left], poses[sample_index][left],
                triangles[right], roots[right], poses[sample_index][right], 1e-8,
            )
            if intersects:
                exact_hits.append(
                    {"sample_index": sample_index, "left": left, "right": right,
                     "triangle_ids": triangle_ids}
                )

    proxy_report = json.loads(args.document_proxy_report.read_text(encoding="utf-8"))
    proxy_data = {}
    for side in ("L", "R"):
        low, high = (
            np.asarray(value, dtype=float)
            for value in proxy_report["proxy"]["dimensions"][side]["dilated_proxy_bounds_m"]
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
    robot_roots = {
        link: mesh.BvhNode(
            triangles[link], np.arange(len(triangles[link]), dtype=np.int64)
        )
        for link in links
        if link not in wrong_effectors
    }
    proxy_exact_hits = []
    proxy_pair_candidates = []
    fixture_report = json.loads(args.e6_1a_report.read_text(encoding="utf-8"))
    fixture_pose, support_bounds, box_bounds = obb_for_fixture(
        fixture_report, 0.838, 0.84, 0.038
    )
    environment = {
        "support": path.obb_for_link(fixture_pose, support_bounds),
        "box": path.obb_for_link(fixture_pose, box_bounds),
    }
    fixture_candidates = {"support": [], "box": []}
    for sample_index, current_poses in enumerate(poses):
        robot_boxes = {
            link: path.obb_for_link(current_poses[link], local_bounds)
            for link, local_bounds in bounds.items()
            if link not in wrong_effectors
        }
        proxy_boxes = {
            side: path.obb_for_link(
                current_poses[item["mount"]], (item["low"], item["high"])
            )
            for side, item in proxy_data.items()
        }
        if path.obb_overlap(proxy_boxes["L"], proxy_boxes["R"]):
            proxy_pair_candidates.append(sample_index)
        for kind, environment_box in environment.items():
            for link, robot_box in robot_boxes.items():
                if path.obb_overlap(environment_box, robot_box):
                    fixture_candidates[kind].append(
                        {"sample_index": sample_index, "body": link}
                    )
            for side, proxy_box in proxy_boxes.items():
                if path.obb_overlap(environment_box, proxy_box):
                    fixture_candidates[kind].append(
                        {"sample_index": sample_index, "body": f"{side}_clamp_proxy"}
                    )
        for side, item in proxy_data.items():
            allowed = {
                f"{side}_sixforce_link",
                f"{side}_wrist_roll_link",
                f"{side}_wrist_pitch_link",
            }
            for link, robot_box in robot_boxes.items():
                if link in allowed or not path.obb_overlap(proxy_boxes[side], robot_box):
                    continue
                intersects, _, triangle_ids = mesh.mesh_intersection(
                    item["triangles"], item["root"], current_poses[item["mount"]],
                    triangles[link], robot_roots[link], current_poses[link], 1e-8,
                )
                if intersects:
                    proxy_exact_hits.append(
                        {"sample_index": sample_index, "proxy": side,
                         "robot_link": link, "triangle_ids": triangle_ids}
                    )

    entry_distance = max(abs(value - reference) for value, reference in zip(target, frozen, strict=True))
    failed = bool(
        limit_violations
        or exact_hits
        or proxy_exact_hits
        or proxy_pair_candidates
        or fixture_candidates["support"]
        or fixture_candidates["box"]
        or entry_distance > float(contract["state_gate"]["maximum_chebyshev_distance_rad"])
    )
    report = {
        "schema": "cruzr-s2-vla-ready-entry-transition-audit-e6.1c-v1",
        "experiment_id": "E6.1C",
        "mode": "local_offline_no_robot_no_network_no_ros_no_container_no_publisher",
        "status": (
            "FAIL_OFFLINE_REDUCED_READY_ENTRY"
            if failed
            else "PASS_OFFLINE_REDUCED_READY_ENTRY_OWNER_ACCEPTANCE_PENDING"
        ),
        "transition": {
            "commanded_joint_names": contract["commanded_joint_names"],
            "uncommanded_arm_joint_count": 14,
            "largest_delta_joint": order[largest_delta_index],
            "largest_delta_rad": abs(float(delta[largest_delta_index])),
            "entry_distance_to_frozen_frame_rad": entry_distance,
            "duration_seconds_each_direction": duration,
            "analytic_maximum_velocity_rad_s": maximum_velocity,
            "analytic_maximum_acceleration_rad_s2": maximum_acceleration,
            "geometry_samples_each_direction": count,
            "runtime_law_equivalence_demonstrated": False,
        },
        "previews": {"ready_to_entry": entry_preview, "entry_to_ready": recovery_preview},
        "joint_limit_violations": limit_violations,
        "self_collision_exact_hits": exact_hits,
        "clamp_robot_exact_hits": proxy_exact_hits,
        "clamp_clamp_obb_candidate_samples": proxy_pair_candidates,
        "reconstructed_fixture_obb_candidates": fixture_candidates,
        "gates": {
            "offline_geometry_and_limits_pass": not failed,
            "owner_accepted_for_physical_e6_1c": False,
            "runtime_tasks_installed": False,
            "runtime_task_manager_reloaded": False,
            "physical_execution_authorized": False,
        },
        "limitations": [
            "READY is a historical observed reference; every physical run must recapture all 20 axes.",
            "The fixture pose is reconstructed from the frozen dataset RGB, not measured from the current photographs.",
            "The sampled minimum-jerk law is not proven equivalent to the vendor MetaMove runtime interpolator.",
            "The 0.15 rad/s and 0.5 rad/s^2 limits are provisional project values, not manufacturer certification.",
        ],
        "next_gate": "OWNER_ACCEPT_E6_1C_TRANSITION_LIMITS_THEN_IMPLEMENT_SEPARATE_INSTALL_RELOAD_AND_RUN",
        "robot_accessed": False,
        "network_calls": 0,
        "ros_imported": False,
        "containers_started": 0,
        "physical_publishers": 0,
        "physical_movement_commanded": False,
        "physical_execution_authorized": False,
        "source_sha256": {source.name: digest(source) for source in sources},
    }
    rendered = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(f"E6.1C_STATUS={report['status']}")
    print("E6.1C_ARM_JOINTS_COMMANDED=0")
    print(f"E6.1C_LARGEST_DELTA_RAD={abs(float(delta[largest_delta_index])):.9f}")
    print(f"E6.1C_MAX_VELOCITY_RAD_S={maximum_velocity:.9f}")
    print(f"E6.1C_MAX_ACCELERATION_RAD_S2={maximum_acceleration:.9f}")
    print(f"E6.1C_JOINT_LIMIT_VIOLATIONS={len(limit_violations)}")
    print(f"E6.1C_SELF_COLLISION_EXACT_HITS={len(exact_hits)}")
    print(f"E6.1C_CLAMP_ROBOT_EXACT_HITS={len(proxy_exact_hits)}")
    print(
        "E6.1C_FIXTURE_OBB_CANDIDATES="
        f"{len(fixture_candidates['support']) + len(fixture_candidates['box'])}"
    )
    print("E6.1C_ROBOT_ACCESSED=0")
    print("E6.1C_PHYSICAL_AUTHORIZED=0")
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError, ET.ParseError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
