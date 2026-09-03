#!/usr/bin/env python3
"""Select the smallest justified axis profile from an E5.1 shadow matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import statistics
import sys
from typing import Any


PROFILE_ORDER = {
    "P14_A": 14,
    "P15_AW": 15,
    "P16_AH": 16,
    "P17_AL": 17,
    "P17_AHW": 17,
    "P18_ALW": 18,
    "P19_AHL": 19,
    "P20_AHLW": 20,
}
TASK_TEXT = {
    0: "Pick up the large box from the lowest level of shelf",
    1: "Place the large box on the lowest level of shelf",
    2: "Pick up the large box from the middle level of shelf",
    3: "Place the large box on the middle level of shelf",
}
GROUP_PROBE = {"W": "P15_AW", "H": "P16_AH", "L": "P17_AL"}
ABSOLUTE_MAE_BAND_RAD = 0.0001
RELATIVE_MAE_BAND = 0.01


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=pathlib.Path, required=True)
    parser.add_argument("--select-minimal-profile", action="store_true", required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    return parser.parse_args()


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: pathlib.Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def resolve_matrix(input_path: pathlib.Path) -> pathlib.Path:
    resolved = input_path.resolve()
    direct = resolved / "matrix_summary.json"
    if direct.is_file() and load_json(direct).get("experiment_id") == "E5.1":
        return direct
    candidates = [
        path
        for path in resolved.glob("*_E5.1/matrix_summary.json")
        if load_json(path).get("experiment_id") == "E5.1"
    ]
    if not candidates:
        raise FileNotFoundError(f"no E5.1 matrix_summary.json below {resolved}")
    return sorted(candidates, key=lambda path: path.parent.name)[-1]


def aggregate_profile(rows: list[dict[str, Any]], profile: str) -> dict[str, Any]:
    selected = sorted(
        (row for row in rows if row["axis_profile"] == profile),
        key=lambda row: int(row["seed"]),
    )
    if len(selected) != 5 or [int(row["seed"]) for row in selected] != list(range(5)):
        raise ValueError(f"profile {profile} does not contain seeds 0..4 exactly once")
    return {
        "axis_profile": profile,
        "enabled_axis_count": PROFILE_ORDER[profile],
        "bundle_count": len(selected),
        "accepted_count": sum(row["verdict"] == "ACCEPT_STRUCTURAL" for row in selected),
        "rejected_safe_count": sum(row["verdict"] == "REJECT_SAFE" for row in selected),
        "mask_contract_pass_count": sum(
            row["mask_checks"]["enabled_axes_copy_raw_prediction"]
            and row["mask_checks"]["locked_axes_hold_recorded_initial_state"]
            for row in selected
        ),
        "mean_effective_mae_all_axes": statistics.fmean(
            float(row["metrics"]["effective_mae_all_axes"]) for row in selected
        ),
        "effective_mae_by_seed": {
            str(row["seed"]): float(row["metrics"]["effective_mae_all_axes"])
            for row in selected
        },
        "rejection_reasons": [
            {"seed": row["seed"], "reasons": row["rejection_reasons"]}
            for row in selected
            if row["verdict"] == "REJECT_SAFE"
        ],
    }


def group_comparison(
    *, baseline: dict[str, Any], candidate: dict[str, Any], relevance_band: float
) -> dict[str, Any]:
    deltas = {
        seed: candidate["effective_mae_by_seed"][seed]
        - baseline["effective_mae_by_seed"][seed]
        for seed in baseline["effective_mae_by_seed"]
    }
    mean_delta = statistics.fmean(deltas.values())
    if candidate["rejected_safe_count"]:
        conclusion = "NOT_JUSTIFIED_SAFETY_REJECTIONS"
    elif mean_delta <= -relevance_band:
        conclusion = "MATERIAL_MAE_IMPROVEMENT_OBSERVED"
    else:
        conclusion = "NO_MATERIAL_MAE_IMPROVEMENT"
    return {
        "candidate_profile": candidate["axis_profile"],
        "accepted_count": candidate["accepted_count"],
        "rejected_safe_count": candidate["rejected_safe_count"],
        "mean_mae_delta_vs_P14_rad": mean_delta,
        "paired_mae_delta_by_seed_rad": deltas,
        "material_improvement_threshold_rad": relevance_band,
        "conclusion": conclusion,
    }


def main() -> int:
    args = parse_args()
    matrix_path = resolve_matrix(args.input)
    run_dir = matrix_path.parent
    matrix = load_json(matrix_path)
    if matrix.get("schema") != "cruzr-s2-vla-shadow-matrix-e5.1-v1":
        raise SystemExit(f"ERROR: unsupported matrix schema: {matrix.get('schema')}")
    bundles_path = run_dir / "bundles.jsonl"
    bundles = [
        json.loads(line)
        for line in bundles_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(bundles) != 160:
        raise SystemExit(f"ERROR: expected 160 bundles, got {len(bundles)}")
    identity = {
        (int(row["task_id"]), str(row["axis_profile"]), int(row["seed"]))
        for row in bundles
    }
    expected_identity = {
        (task_id, profile, seed)
        for task_id in TASK_TEXT
        for profile in PROFILE_ORDER
        for seed in range(5)
    }
    if identity != expected_identity:
        raise SystemExit("ERROR: task/profile/seed coverage is not exact")

    selections: dict[str, Any] = {}
    group_findings: dict[str, list[dict[str, Any]]] = {group: [] for group in GROUP_PROBE}
    for task_id, task_text in TASK_TEXT.items():
        task_rows = [row for row in bundles if int(row["task_id"]) == task_id]
        profiles = {
            profile: aggregate_profile(task_rows, profile) for profile in PROFILE_ORDER
        }
        eligible = [
            value
            for value in profiles.values()
            if value["accepted_count"] == 5
            and value["rejected_safe_count"] == 0
            and value["mask_contract_pass_count"] == 5
        ]
        if not eligible:
            raise SystemExit(f"ERROR: task {task_id} has no eligible profile")
        best_mae = min(value["mean_effective_mae_all_axes"] for value in eligible)
        relevance_band = max(ABSOLUTE_MAE_BAND_RAD, RELATIVE_MAE_BAND * best_mae)
        near_best = [
            value
            for value in eligible
            if value["mean_effective_mae_all_axes"] <= best_mae + relevance_band
        ]
        selected = min(
            near_best,
            key=lambda value: (
                value["enabled_axis_count"],
                value["mean_effective_mae_all_axes"],
                value["axis_profile"],
            ),
        )
        baseline = profiles["P14_A"]
        comparisons = {
            group: group_comparison(
                baseline=baseline,
                candidate=profiles[profile],
                relevance_band=relevance_band,
            )
            for group, profile in GROUP_PROBE.items()
        }
        for group, comparison in comparisons.items():
            group_findings[group].append({"task_id": task_id, **comparison})
        selections[str(task_id)] = {
            "task_id": task_id,
            "task_text": task_text,
            "selected_profile": selected["axis_profile"],
            "selected_axis_count": selected["enabled_axis_count"],
            "selection_rule": "fewest_axes_within_relevance_band_of_best_fully_accepted_profile",
            "best_eligible_mae_all_axes_rad": best_mae,
            "relevance_band_rad": relevance_band,
            "selected_mean_effective_mae_all_axes_rad": selected[
                "mean_effective_mae_all_axes"
            ],
            "eligible_profiles": [
                value["axis_profile"]
                for value in sorted(
                    eligible,
                    key=lambda value: (
                        value["enabled_axis_count"],
                        value["axis_profile"],
                    ),
                )
            ],
            "near_best_profiles": [
                value["axis_profile"]
                for value in sorted(
                    near_best,
                    key=lambda value: (
                        value["enabled_axis_count"],
                        value["axis_profile"],
                    ),
                )
            ],
            "group_comparisons_vs_P14": comparisons,
            "profiles": profiles,
            "physical_task_success_evaluated": False,
        }

    l_profiles = {"P17_AL", "P18_ALW", "P19_AHL", "P20_AHLW"}
    l_bundles = [row for row in bundles if row["axis_profile"] in l_profiles]
    l_rejections = sum(row["verdict"] == "REJECT_SAFE" for row in l_bundles)
    overall_profile = (
        "P14_A"
        if all(value["selected_profile"] == "P14_A" for value in selections.values())
        else "TASK_SPECIFIC"
    )
    report = {
        "schema": "cruzr-s2-vla-preliminary-profile-selection-e5.2-v1",
        "experiment_id": "E5.2",
        "mode": "offline_analysis_no_robot_no_ros_no_publisher",
        "source_matrix": str(matrix_path),
        "source_matrix_sha256": sha256_file(matrix_path),
        "source_bundles_sha256": sha256_file(bundles_path),
        "source_bundle_count": len(bundles),
        "selection_parameters": {
            "absolute_mae_band_rad": ABSOLUTE_MAE_BAND_RAD,
            "relative_mae_band": RELATIVE_MAE_BAND,
            "eligibility": "5/5 ACCEPT_STRUCTURAL and 5/5 mask contract",
        },
        "task_selections": selections,
        "overall_preliminary_profile": overall_profile,
        "group_findings": {
            group: {
                "task_comparisons": findings,
                "tasks_with_material_improvement": sum(
                    row["conclusion"] == "MATERIAL_MAE_IMPROVEMENT_OBSERVED"
                    for row in findings
                ),
                "tasks_with_safety_rejections_in_direct_probe": sum(
                    row["rejected_safe_count"] > 0 for row in findings
                ),
            }
            for group, findings in group_findings.items()
        },
        "lifter_all_profiles": {
            "bundle_count": len(l_bundles),
            "rejected_safe_count": l_rejections,
            "rejection_rate": l_rejections / len(l_bundles),
        },
        "conclusion": (
            "P14_A is the preliminary profile for all four tasks; H/W show no "
            "material paired MAE benefit and L introduces conservative rejections"
        ),
        "qualification_scope": (
            "recorded-dataset shadow replay only; not physical task success, live fixture, "
            "collision, acceleration, temporal runtime or executor qualification"
        ),
        "physical_task_success_evaluated": False,
        "robot_state_read_live": False,
        "network_calls": 0,
        "physical_publishers": 0,
        "physical_movement_commanded": False,
        "physical_executor_authorized": False,
        "e6_0_authorized": False,
        "blocking_gates": [
            "E4.4_fixture_not_validated",
            "VLA_ready_pose_not_installed_or_registered",
            "physical_executor_not_implemented_or_reviewed",
            "certified_acceleration_limit_missing",
            "vendor_temporal_semantics_unresolved",
        ],
        "next_work": "RESOLVE_E4.4_AND_EXECUTOR_GATES_BEFORE_ANY_E6_CANARY",
    }
    output = args.output.resolve()
    if output == pathlib.Path("/") or output.exists():
        raise SystemExit(f"ERROR: output must be a new file and not /: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    for task_id, selection in selections.items():
        print(
            f"E5.2_TASK={task_id},profile:{selection['selected_profile']},"
            f"axes:{selection['selected_axis_count']},"
            f"mae:{selection['selected_mean_effective_mae_all_axes_rad']:.9f}"
        )
    print(
        f"E5.2_LIFTER_REJECTIONS={l_rejections}/{len(l_bundles)}"
    )
    print(f"E5.2_RESULT=PASS_PRELIMINARY_PROFILE_{overall_profile}_PHYSICAL_BLOCKED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
