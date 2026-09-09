#!/usr/bin/env python3
"""Fail-closed endpoint gate for the measured PICO -> numeric HOME recovery."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

import yaml


JOINT_ORDER = [
    "L_elbow_roll_joint", "L_elbow_yaw_joint", "L_shoulder_pitch_joint",
    "L_shoulder_roll_joint", "L_shoulder_yaw_joint", "L_wrist_pitch_joint",
    "L_wrist_roll_joint", "R_elbow_roll_joint", "R_elbow_yaw_joint",
    "R_shoulder_pitch_joint", "R_shoulder_roll_joint", "R_shoulder_yaw_joint",
    "R_wrist_pitch_joint", "R_wrist_roll_joint", "head_pitch_joint",
    "head_yaw_joint", "lifter_pitch_1_joint", "lifter_pitch_2_joint",
    "lifter_pitch_3_joint", "waist_yaw_joint",
]
PICO_REFERENCE = [
    -1.567920112817611, -0.37400369084636786, -0.001342233189399936,
    -0.19912988102740478, -1.5693582198062537, 0.00009587379924285257,
    0.0, -1.5677283652191252, 0.37333257425166794,
    0.0012463593901570836, -0.19903400722816195, 1.569166472207768,
    -0.00047936899621426287, -0.0005752427954571154,
    -0.002876213977285577, 0.0005752427954571154,
    0.2999891178308857, -0.5002694844492047, 0.19960925002361907, 0.0,
]
HOME_REFERENCE = [0.0] * 20
# Discrete second endpoint: PICO arms with head/lifter/waist at numeric HOME.
# Do not accept an arbitrary body posture or mix joints from the two endpoints.
PICO_BODY_ZERO_REFERENCE = PICO_REFERENCE[:14] + HOME_REFERENCE[14:]
PICO_VARIANTS = {
    "pico_body_flexed": PICO_REFERENCE,
    "pico_body_zero": PICO_BODY_ZERO_REFERENCE,
}
POSITION_TOLERANCE_RAD = 0.02
VELOCITY_TOLERANCE_RAD_S = 0.01


def load_sample(path: Path) -> dict:
    documents = [item for item in yaml.safe_load_all(path.read_text(encoding="utf-8")) if item]
    if len(documents) != 1 or not isinstance(documents[0], dict):
        raise ValueError("la captura debe contener un único objeto JointState")
    return documents[0]


def evaluate(sample: dict, expected: str) -> dict:
    if expected not in ("pico", "home"):
        raise ValueError("referencia desconocida: " + str(expected))
    names = sample.get("name")
    positions = sample.get("position")
    velocities = sample.get("velocity")
    if not all(isinstance(value, list) for value in (names, positions, velocities)):
        raise ValueError("faltan listas name/position/velocity")
    if len(names) != len(positions) or len(names) != len(velocities):
        raise ValueError("las listas JointState tienen longitudes distintas")
    if len(names) != len(set(names)):
        raise ValueError("hay nombres articulares duplicados")
    values = {}
    for name, position, velocity in zip(names, positions, velocities, strict=True):
        if not isinstance(name, str) or type(position) not in (int, float) or type(velocity) not in (int, float):
            raise ValueError("JointState contiene tipos inválidos")
        pair = (float(position), float(velocity))
        if not all(math.isfinite(value) for value in pair):
            raise ValueError("JointState contiene valores no finitos")
        values[name] = pair
    missing = [name for name in JOINT_ORDER if name not in values]
    if missing:
        raise ValueError("faltan articulaciones: " + ",".join(missing))
    references = PICO_VARIANTS if expected == "pico" else {"home": HOME_REFERENCE}
    variant_errors = {
        label: max(abs(values[name][0] - target) for name, target in zip(JOINT_ORDER, ref, strict=True))
        for label, ref in references.items()
    }
    closest_variant = min(variant_errors, key=variant_errors.get)
    reference = references[closest_variant]
    errors = [abs(values[name][0] - target) for name, target in zip(JOINT_ORDER, reference, strict=True)]
    velocities_20d = [abs(values[name][1]) for name in JOINT_ORDER]
    worst_index = max(range(20), key=errors.__getitem__)
    reasons = []
    if errors[worst_index] > POSITION_TOLERANCE_RAD:
        reasons.append("postura_no_coincide_con_" + expected)
    if max(velocities_20d) > VELOCITY_TOLERANCE_RAD_S:
        reasons.append("robot_no_inmovil")
    return {
        "schema": "cruzr-pico-to-home-owner-endpoint-gate-v1",
        "expected": expected,
        "closest_reference": closest_variant,
        "matched_reference": closest_variant if not reasons else None,
        "reference_maximum_errors_rad": variant_errors,
        "qualified": not reasons,
        "maximum_position_error_rad": errors[worst_index],
        "maximum_position_error_joint": JOINT_ORDER[worst_index],
        "maximum_position_error_measured_rad": values[JOINT_ORDER[worst_index]][0],
        "maximum_position_error_expected_rad": reference[worst_index],
        "out_of_tolerance_joints": [
            {"joint": name, "measured_rad": values[name][0], "expected_rad": target,
             "absolute_error_rad": error}
            for name, target, error in zip(JOINT_ORDER, reference, errors, strict=True)
            if error > POSITION_TOLERANCE_RAD
        ],
        "maximum_absolute_velocity_rad_s": max(velocities_20d),
        "position_tolerance_rad": POSITION_TOLERANCE_RAD,
        "velocity_tolerance_rad_s": VELOCITY_TOLERANCE_RAD_S,
        "rejection_reasons": reasons,
        "scope": "endpoint_and_stationarity_only",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--expect", choices=("pico", "home"), required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate(load_sample(args.input), args.expect)
    rendered = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["qualified"] else 3


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
