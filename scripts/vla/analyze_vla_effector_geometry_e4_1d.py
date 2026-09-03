#!/usr/bin/env python3
"""Audit E4.1C collision dependence on the vendor PGC effector model."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import yaml


EFFECTOR_LINK_RE = re.compile(r"_(?:pgc_base|finger[12])_link$")
UPSTREAM_LINK_RE = re.compile(r"_(?:wrist_pitch|wrist_roll|sixforce)_link$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--urdf", required=True, type=Path)
    parser.add_argument("--sdk-text", required=True, type=Path)
    parser.add_argument("--e4-1c-summary", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def joint_record(joint: ET.Element) -> dict[str, object]:
    parent = joint.find("parent")
    child = joint.find("child")
    limit = joint.find("limit")
    return {
        "name": joint.get("name", ""),
        "type": joint.get("type", ""),
        "parent": "" if parent is None else parent.get("link", ""),
        "child": "" if child is None else child.get("link", ""),
        "lower": None if limit is None else float(limit.get("lower", "nan")),
        "upper": None if limit is None else float(limit.get("upper", "nan")),
    }


def classify_link(link: str) -> str:
    if EFFECTOR_LINK_RE.search(link):
        return "vendor_pgc_or_finger"
    if UPSTREAM_LINK_RE.search(link):
        return "upstream_wrist_or_force_sensor"
    return "other"


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    contract = yaml.safe_load(args.contract.read_text(encoding="utf-8"))
    summary = json.loads(args.e4_1c_summary.read_text(encoding="utf-8"))
    sdk_text = args.sdk_text.read_text(encoding="utf-8", errors="replace")
    root = ET.parse(args.urdf).getroot()

    installed = contract["installed_effector"]
    pgc_reference = contract["vendor_pgc_reference"]
    if installed["verification_state"] != "VERIFIED_ON_UNIT":
        raise ValueError("el efector instalado no consta como verificado")
    if installed["hardware_type"] != "cruzr_s2_v1":
        raise ValueError("HW_TYPE instalado inesperado")
    for required in ("PGC-140-50", "HW_TYPE=cruzr_s2_v1_gripper",
                     "/ecat/left_grip/cmd", "/ecat/right_grip/cmd"):
        if required not in sdk_text:
            raise ValueError(f"el texto SDK no contiene {required!r}")

    all_joints = [joint_record(item) for item in root.findall("joint")]
    pgc_base_joints = [item for item in all_joints if "pgc_base_joint" in str(item["name"])]
    finger_joints = [item for item in all_joints if re.search(r"_finger[12]_joint$", str(item["name"]))]
    if len(pgc_base_joints) != 2 or any(item["type"] != "fixed" for item in pgc_base_joints):
        raise ValueError("topología base PGC inesperada en el URDF")
    if len(finger_joints) != 4 or any(item["type"] != "prismatic" for item in finger_joints):
        raise ValueError("topología de dedos PGC inesperada en el URDF")

    events = summary["results"]["triangle_mesh_tabletop_events"]
    expected_total = summary["results"]["triangle_mesh_tabletop_surface_event_count"]
    if len(events) != expected_total:
        raise ValueError("conteo E4.1C inconsistente")

    group_counts: Counter[str] = Counter()
    group_links: dict[str, Counter[str]] = defaultdict(Counter)
    group_segments: dict[str, Counter[str]] = defaultdict(Counter)
    for event in events:
        link = event["link"]
        group = classify_link(link)
        group_counts[group] += 1
        group_links[group][link] += 1
        group_segments[group][event["segment"]] += 1

    upstream_events = group_counts["upstream_wrist_or_force_sensor"]
    effector_events = group_counts["vendor_pgc_or_finger"]
    other_events = group_counts["other"]
    actual_topology_matches = (
        installed["family"] == "gripper"
        and int(installed["actuated_finger_joints"]) == len(finger_joints)
        and installed["hardware_type"] == pgc_reference["hardware_type"]
    )
    independent_rejection = upstream_events > 0

    if actual_topology_matches:
        raise ValueError("el contrato no describe las abrazaderas pasivas esperadas")
    if not independent_rejection:
        raise ValueError("E4.1C no conserva cruces al excluir PGC/finger")

    def counter_dict(counter: Counter[str]) -> dict[str, int]:
        return dict(sorted(counter.items()))

    result = {
        "schema": "cruzr-s2-vla-effector-audit-e4.1d/v1",
        "experiment_id": "E4.1D",
        "mode": "local_read_only_no_robot_no_inference_no_publisher",
        "status": "PGC_NOT_INSTALLED_EFFECTOR_SOLID_TABLETOP_STILL_REJECTED_BY_UPSTREAM_ARM_SWEEP",
        "installed_effector": installed,
        "vendor_pgc": {
            "model": pgc_reference["model"],
            "sdk_required_hardware_type": pgc_reference["hardware_type"],
            "urdf_base_joints": pgc_base_joints,
            "urdf_prismatic_finger_joints": finger_joints,
            "mechanism_topology_matches_installed_effector": actual_topology_matches,
            "mesh_envelope_matches_installed_effector": "NOT_DEMONSTRATED_NO_CLAMP_CAD_OR_DIMENSIONS",
        },
        "e4_1c_collision_partition": {
            "total_triangle_surface_events": len(events),
            "vendor_pgc_or_finger_events": effector_events,
            "upstream_wrist_or_force_sensor_events": upstream_events,
            "other_events": other_events,
            "links_by_group": {
                group: counter_dict(counts) for group, counts in sorted(group_links.items())
            },
            "segments_by_group": {
                group: counter_dict(counts) for group, counts in sorted(group_segments.items())
            },
        },
        "conclusions": {
            "pgc_is_identity_match_for_installed_clamps": False,
            "pgc_mesh_can_be_treated_as_validated_clamp_envelope": False,
            "solid_tabletop_rejection_depends_only_on_pgc_or_fingers": False,
            "solid_tabletop_rejection_remains_when_pgc_and_fingers_are_excluded": independent_rejection,
        },
        "gates": {
            "solid_tabletop_e4_1_authorized": False,
            "box_placement_authorized": False,
            "physical_e4_3_or_e4_4_authorized": False,
            "next_authorized_work": "OFFLINE_FIXTURE_CUTOUT_OR_ALTERNATE_POSE_DESIGN",
        },
        "blockers": [
            "45 vendor-URDF triangle/plane events remain in wrist and force-sensor links",
            "installed clamp CAD/dimensions are absent, so their exact swept envelope is unknown",
            "entry from arbitrary state into VLA preposition and complete recovery remain unresolved",
        ],
    }

    (args.output_dir / "summary.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (args.output_dir / "collision_partition.tsv").open("w", encoding="utf-8") as stream:
        stream.write("group\tlink\tevents\n")
        for group, links in sorted(group_links.items()):
            for link, count in sorted(links.items()):
                stream.write(f"{group}\t{link}\t{count}\n")

    print(f"E4.1D_TOTAL_EVENTS={len(events)}")
    print(f"E4.1D_PGC_FINGER_EVENTS={effector_events}")
    print(f"E4.1D_UPSTREAM_ARM_EVENTS={upstream_events}")
    print("E4.1D_ACTUAL_EFFECTOR=passive-lateral-clamps,HW_TYPE:cruzr_s2_v1")
    print("E4.1D_VENDOR_MODEL=PGC-140-50,HW_TYPE:cruzr_s2_v1_gripper")
    print("E4.1D_PGC_GEOMETRIC_EQUIVALENCE=NOT_DEMONSTRATED")
    print("E4.1D_SOLID_TABLETOP_REJECTION_WITHOUT_PGC_FINGER=YES")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
