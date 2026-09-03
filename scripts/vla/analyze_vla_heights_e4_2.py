#!/usr/bin/env python3
"""Resolve the E4.2 low/middle height contract from local vendor artifacts."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET


PROFILE_HEIGHTS_CM = (55, 70, 85, 100, 115)
PROFILE_MATCH_L2_RAD = 0.05
EXPECTED_TASKS = {
    0: "Pick up the large box from the lowest level of shelf",
    1: "Place the large box on the lowest level of shelf",
    2: "Pick up the large box from the middle level of shelf",
    3: "Place the large box on the middle level of shelf",
}
EXPECTED_EPISODE_COUNTS = {0: 150, 1: 150, 2: 100, 3: 100}


Matrix = list[list[float]]


def identity() -> Matrix:
    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def matmul(left: Matrix, right: Matrix) -> Matrix:
    return [
        [sum(left[row][inner] * right[inner][column] for inner in range(4))
         for column in range(4)]
        for row in range(4)
    ]


def rotation_x(angle: float) -> list[list[float]]:
    cosine, sine = math.cos(angle), math.sin(angle)
    return [[1.0, 0.0, 0.0], [0.0, cosine, -sine], [0.0, sine, cosine]]


def rotation_y(angle: float) -> list[list[float]]:
    cosine, sine = math.cos(angle), math.sin(angle)
    return [[cosine, 0.0, sine], [0.0, 1.0, 0.0], [-sine, 0.0, cosine]]


def rotation_z(angle: float) -> list[list[float]]:
    cosine, sine = math.cos(angle), math.sin(angle)
    return [[cosine, -sine, 0.0], [sine, cosine, 0.0], [0.0, 0.0, 1.0]]


def matmul3(left: list[list[float]], right: list[list[float]]) -> list[list[float]]:
    return [
        [sum(left[row][inner] * right[inner][column] for inner in range(3))
         for column in range(3)]
        for row in range(3)
    ]


def transform(xyz: list[float], rpy: list[float]) -> Matrix:
    result = identity()
    rotation = matmul3(rotation_z(rpy[2]), matmul3(rotation_y(rpy[1]), rotation_x(rpy[0])))
    for row in range(3):
        for column in range(3):
            result[row][column] = rotation[row][column]
        result[row][3] = xyz[row]
    return result


def axis_rotation(axis: list[float], angle: float) -> Matrix:
    length = math.sqrt(sum(value * value for value in axis))
    if length == 0.0:
        raise ValueError("URDF revolute joint has a zero axis")
    x, y, z = (value / length for value in axis)
    cosine, sine, complement = math.cos(angle), math.sin(angle), 1.0 - math.cos(angle)
    rotation = [
        [cosine + x * x * complement, x * y * complement - z * sine,
         x * z * complement + y * sine],
        [y * x * complement + z * sine, cosine + y * y * complement,
         y * z * complement - x * sine],
        [z * x * complement - y * sine, z * y * complement + x * sine,
         cosine + z * z * complement],
    ]
    result = identity()
    for row in range(3):
        for column in range(3):
            result[row][column] = rotation[row][column]
    return result


def vector(raw: str | None, size: int, default: str) -> list[float]:
    values = [float(value) for value in (raw or default).split()]
    if len(values) != size or not all(math.isfinite(value) for value in values):
        raise ValueError(f"invalid vector: {raw!r}")
    return values


def parse_lifter_profile(path: Path) -> list[float]:
    values: list[float] | None = None
    for action in ET.parse(path).getroot().iter("Action"):
        if action.get("type") != "lifter":
            continue
        parts = [part.strip() for part in re.split(r"[;,]", action.get("joint_angles", ""))]
        values = [float(part) for part in parts if part]
    if values is None or len(values) != 3 or not all(math.isfinite(value) for value in values):
        raise ValueError(f"no valid 3D lifter profile in {path}")
    return values


class UrdfForwardKinematics:
    def __init__(self, path: Path) -> None:
        root = ET.parse(path).getroot()
        by_child: dict[str, ET.Element] = {}
        for joint in root.findall("joint"):
            child = joint.find("child")
            if child is not None:
                by_child[child.attrib["link"]] = joint

        chain: list[ET.Element] = []
        current = "torso_link"
        while current != "base_link":
            if current not in by_child:
                raise ValueError(f"URDF chain base_link -> torso_link is broken at {current}")
            joint = by_child[current]
            chain.append(joint)
            parent = joint.find("parent")
            if parent is None:
                raise ValueError(f"URDF joint {joint.attrib['name']} lacks parent")
            current = parent.attrib["link"]
        self.chain = list(reversed(chain))
        self.chain_names = [joint.attrib["name"] for joint in self.chain]

        expected = [
            "base_lifter_joint",
            "lifter_pitch_1_joint",
            "lifter_pitch_2_joint",
            "lifter_pitch_3_joint",
            "waist_yaw_joint",
            "torso_waist_joint",
        ]
        if self.chain_names != expected:
            raise ValueError(f"unexpected S2 lifter chain: {self.chain_names}")

    def torso_in_base(self, lifter: list[float], waist_yaw: float = 0.0) -> dict[str, object]:
        positions = {
            "lifter_pitch_1_joint": lifter[0],
            "lifter_pitch_2_joint": lifter[1],
            "lifter_pitch_3_joint": lifter[2],
            "waist_yaw_joint": waist_yaw,
        }
        current = identity()
        for joint in self.chain:
            origin = joint.find("origin")
            xyz = vector(origin.get("xyz") if origin is not None else None, 3, "0 0 0")
            rpy = vector(origin.get("rpy") if origin is not None else None, 3, "0 0 0")
            current = matmul(current, transform(xyz, rpy))
            if joint.attrib.get("type") in {"revolute", "continuous"}:
                axis = joint.find("axis")
                axis_xyz = vector(axis.get("xyz") if axis is not None else None, 3, "1 0 0")
                current = matmul(
                    current,
                    axis_rotation(axis_xyz, positions.get(joint.attrib["name"], 0.0)),
                )
        return {
            "xyz_m": [round(current[index][3], 9) for index in range(3)],
            "rotation": [
                [round(current[row][column], 9) for column in range(3)]
                for row in range(3)
            ],
        }


def l2(left: list[float], right: list[float]) -> float:
    return math.sqrt(sum((first - second) ** 2 for first, second in zip(left, right)))


def median(values: list[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def rounded(values: list[float]) -> list[float]:
    return [round(value, 9) for value in values]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    artifacts = run_dir / "artifacts"

    tasks_path = artifacts / "vendor_dataset_tasks.jsonl"
    episodes_path = artifacts / "vendor_dataset_episodes.jsonl"
    stats_path = artifacts / "vendor_dataset_episode_stats.jsonl"
    urdf_path = artifacts / "vendor_cruzr_s2_v1.urdf"
    manual_path = artifacts / "vendor_sdk_manual.txt"

    task_catalog: dict[int, str] = {}
    for line in tasks_path.read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        task_catalog[int(item["task_index"])] = item["task"]
    if task_catalog != EXPECTED_TASKS:
        raise ValueError(f"unexpected task catalog: {task_catalog}")

    episode_catalog: dict[int, dict[str, object]] = {}
    for line in episodes_path.read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        episode_catalog[int(item["episode_index"])] = item
    if len(episode_catalog) != 500:
        raise ValueError(f"expected 500 episodes, found {len(episode_catalog)}")

    profiles = {
        height: parse_lifter_profile(artifacts / f"vendor_non_s2_pick_large_{height}_ready.xml")
        for height in PROFILE_HEIGHTS_CM
    }
    fk = UrdfForwardKinematics(urdf_path)
    profile_fk = {
        height: fk.torso_in_base(values)
        for height, values in profiles.items()
    }

    rows_by_task: dict[int, list[dict[str, object]]] = defaultdict(list)
    for line in stats_path.read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        stats = item["stats"]
        task = int(round(stats["annotation.human.action.task_description"]["mean"][0]))
        action = stats["action"]
        episode = int(item["episode_index"])
        if episode_catalog[episode]["tasks"] != task_catalog[task]:
            raise ValueError(f"episode {episode} task text/index mismatch")
        lifter_mean = [float(value) for value in action["mean"][16:19]]
        lifter_std = [float(value) for value in action["std"][16:19]]
        torso = fk.torso_in_base(lifter_mean)
        distances = {height: l2(lifter_mean, profile) for height, profile in profiles.items()}
        rows_by_task[task].append({
            "episode": episode,
            "lifter_mean_rad": lifter_mean,
            "lifter_std_rad": lifter_std,
            "torso_xyz_m": torso["xyz_m"],
            "profile_distances_l2_rad": distances,
        })

    counts = {task: len(rows) for task, rows in rows_by_task.items()}
    if counts != EXPECTED_EPISODE_COUNTS:
        raise ValueError(f"unexpected task episode counts: {counts}")

    task_summaries: dict[str, object] = {}
    for task, rows in sorted(rows_by_task.items()):
        matches = {
            str(height): sum(
                row["profile_distances_l2_rad"][height] <= PROFILE_MATCH_L2_RAD
                for row in rows
            )
            for height in PROFILE_HEIGHTS_CM
        }
        representatives = {}
        for height in PROFILE_HEIGHTS_CM:
            best = min(rows, key=lambda row: row["profile_distances_l2_rad"][height])
            representatives[str(height)] = {
                "episode": best["episode"],
                "distance_l2_rad": round(best["profile_distances_l2_rad"][height], 9),
                "lifter_mean_rad": rounded(best["lifter_mean_rad"]),
            }
        torso_xyz = [row["torso_xyz_m"] for row in rows]
        unmatched = sum(
            min(row["profile_distances_l2_rad"].values()) > PROFILE_MATCH_L2_RAD
            for row in rows
        )
        task_summaries[str(task)] = {
            "text": task_catalog[task],
            "episodes": len(rows),
            "vendor_profile_match_counts_at_l2_0_05_rad": matches,
            "episodes_not_matching_any_named_profile": unmatched,
            "max_within_episode_lifter_std_rad": round(max(
                max(row["lifter_std_rad"]) for row in rows
            ), 9),
            "torso_fk_xyz_envelope_m": {
                axis: [round(min(point[index] for point in torso_xyz), 9),
                       round(max(point[index] for point in torso_xyz), 9)]
                for index, axis in enumerate(("x", "y", "z"))
            },
            "nearest_episode_per_vendor_profile": representatives,
        }

    def group_profile_candidates(tasks: tuple[int, int]) -> list[int]:
        result = []
        for height in PROFILE_HEIGHTS_CM:
            if all(
                task_summaries[str(task)]["vendor_profile_match_counts_at_l2_0_05_rad"][str(height)] > 0
                for task in tasks
            ):
                result.append(height)
        return result

    cross_task_witnesses = []
    for low_task, middle_task in ((0, 2), (1, 3)):
        distance, low_row, middle_row = min(
            (
                l2(low["lifter_mean_rad"], middle["lifter_mean_rad"]),
                low,
                middle,
            )
            for low in rows_by_task[low_task]
            for middle in rows_by_task[middle_task]
        )
        cross_task_witnesses.append({
            "task_pair": [low_task, middle_task],
            "episode_pair": [low_row["episode"], middle_row["episode"]],
            "lifter_distance_l2_rad": round(distance, 9),
            "low_lifter_mean_rad": rounded(low_row["lifter_mean_rad"]),
            "middle_lifter_mean_rad": rounded(middle_row["lifter_mean_rad"]),
        })

    low_candidates = group_profile_candidates((0, 1))
    middle_candidates = group_profile_candidates((2, 3))
    if low_candidates != [55, 70, 85] or middle_candidates != [100, 115]:
        raise ValueError(
            f"vendor profile family changed: low={low_candidates}, middle={middle_candidates}"
        )
    if not all(witness["lifter_distance_l2_rad"] < 0.001 for witness in cross_task_witnesses):
        raise ValueError("expected cross-task lifter overlap is no longer present")

    selected_one_meter = []
    for task, expected_episode in ((2, 90), (3, 91)):
        row = next(row for row in rows_by_task[task] if row["episode"] == expected_episode)
        selected_one_meter.append({
            "task": task,
            "episode": expected_episode,
            "distance_to_vendor_100_profile_l2_rad": round(
                row["profile_distances_l2_rad"][100], 9
            ),
            "lifter_mean_rad": rounded(row["lifter_mean_rad"]),
            "torso_fk_xyz_m": row["torso_xyz_m"],
        })
    if max(item["distance_to_vendor_100_profile_l2_rad"] for item in selected_one_meter) >= 0.02:
        raise ValueError("E1.2 episodes 90/91 no longer correlate with the vendor 100 profile")

    manual_text = manual_path.read_text(encoding="utf-8")
    sdk_box_and_platform_found = all(
        token in manual_text for token in ("60cm*40cm*22cm", "1m", "平台")
    )
    if not sdk_box_and_platform_found:
        raise ValueError("SDK 7.3 box/platform sentence not found")

    representative_episodes = []
    for height, tasks in ((55, (0, 1)), (70, (0, 1)), (85, (0, 1)),
                          (100, (2, 3)), (115, (2, 3))):
        for task in tasks:
            representative = task_summaries[str(task)]["nearest_episode_per_vendor_profile"][str(height)]
            representative_episodes.append({
                "vendor_profile_cm": height,
                "task": task,
                **representative,
            })

    summary = {
        "experiment_id": "E4.2",
        "mode": "local_read_only_no_robot_no_inference_no_publisher",
        "profile_match_threshold_l2_rad": PROFILE_MATCH_L2_RAD,
        "source_contract": {
            "dataset_episodes": len(episode_catalog),
            "task_episode_counts": {str(task): count for task, count in sorted(counts.items())},
            "tasks": {str(task): text for task, text in task_catalog.items()},
            "sdk_section_7_3_box_lwh_m": [0.60, 0.40, 0.22],
            "sdk_section_7_3_platform_height_m": 1.0,
            "sdk_sentence_found": sdk_box_and_platform_found,
            "numeric_ready_profiles_source": "vendor codes/ non-S2 tree",
            "numeric_ready_profiles_are_canonical_s2": False,
        },
        "urdf_fk": {
            "model": "cruzr_s2_v1",
            "base_link": "base_link",
            "target_link": "torso_link",
            "joint_chain": fk.chain_names,
            "vendor_profiles": {
                str(height): {
                    "lifter_rad": rounded(profiles[height]),
                    "torso_in_base": profile_fk[height],
                }
                for height in PROFILE_HEIGHTS_CM
            },
        },
        "per_task": task_summaries,
        "cross_task_same_lifter_witnesses": cross_task_witnesses,
        "H_TASK_0_1": {
            "scalar_height_m": None,
            "resolution": "MULTI_HEIGHT_FAMILY_NOT_SCALAR",
            "vendor_named_profile_candidates_m": [height / 100.0 for height in low_candidates],
            "support_pose_in_base": None,
            "uncertainty": (
                "The matching profiles are from the non-S2 tree; unmatched variants and "
                "cross-task-identical lifter states prove that lifter FK alone does not "
                "identify shelf height or support pose."
            ),
        },
        "H_TASK_2_3": {
            "scalar_height_m": None,
            "resolution": "MULTI_HEIGHT_FAMILY_NOT_SCALAR",
            "vendor_named_profile_candidates_m": [height / 100.0 for height in middle_candidates],
            "support_pose_in_base": None,
            "uncertainty": (
                "The matching profiles are from the non-S2 tree; unmatched variants and "
                "cross-task-identical lifter states prove that lifter FK alone does not "
                "identify shelf height or support pose."
            ),
        },
        "one_meter_subset": {
            "status": "CORRELATED_OFFLINE_NOT_METRICALLY_CALIBRATED",
            "task_group": [2, 3],
            "episodes_with_existing_e1_2_frames": selected_one_meter,
            "evidence": [
                "S2 SDK section 7.3 specifies the 60x40x22 cm box on a 1 m platform.",
                "Episodes 90/91 are tasks 2/3 and numerically match the vendor 100 profile.",
                "The 100 profile lives in the non-S2 tree, so this is correlation, not an S2 support pose calibration.",
            ],
            "platform_in_base": None,
        },
        "representative_episodes": representative_episodes,
        "e4_2_pass": False,
        "physical_test_authorized": False,
        "status": "PARTIAL_HEIGHT_FAMILIES_RESOLVED_SINGLE_HEIGHT_MAPPING_REJECTED",
        "next_authorized": "E4.2_VENDOR_CONFIRMATION_OR_METRIC_CALIBRATION_ONLY",
    }

    (run_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": summary["status"],
        "H_TASK_0_1": summary["H_TASK_0_1"],
        "H_TASK_2_3": summary["H_TASK_2_3"],
        "one_meter_subset": summary["one_meter_subset"]["status"],
        "cross_task_witnesses": cross_task_witnesses,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
