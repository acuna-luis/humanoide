#!/usr/bin/env python3
"""Prove that the observed clamp envelope is contained in the E6.0J proxy."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--observed-contract", type=Path, required=True)
    parser.add_argument("--document-proxy-report", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    for path in (args.observed_contract, args.document_proxy_report):
        if not path.is_file():
            raise SystemExit(f"ERROR: falta fuente: {path}")

    observed = json.loads(args.observed_contract.read_text(encoding="utf-8"))
    proxy_report = json.loads(args.document_proxy_report.read_text(encoding="utf-8"))
    if observed.get("schema") != "cruzr-s2-observed-clamp-envelope/e6.0k-v1":
        raise SystemExit("ERROR: contrato observado inesperado")
    if proxy_report.get("status") != (
        "PASS_DOCUMENT_PROXY_SAMPLED_SWEEP_ASSUMPTION_ACCEPTED_PHYSICAL_NOT_CERTIFIED"
    ):
        raise SystemExit("ERROR: E6.0J no está aprobado")
    if proxy_report["collision_audit"]["exact_intersection_count"] != 0:
        raise SystemExit("ERROR: el proxy E6.0J contiene intersecciones")

    observed_size = np.asarray(observed["conservative_envelope"]["size_xyz_m"], dtype=float)
    if observed_size.shape != (3,) or np.any(observed_size <= 0.0):
        raise SystemExit("ERROR: tamaño observado inválido")

    containment = {}
    all_contained = True
    for side in ("L", "R"):
        proxy = proxy_report["proxy"]["dimensions"][side]
        proxy_low = np.asarray(proxy["dilated_proxy_bounds_m"][0], dtype=float)
        proxy_high = np.asarray(proxy["dilated_proxy_bounds_m"][1], dtype=float)
        center = (proxy_low + proxy_high) / 2.0
        observed_low = np.asarray([
            center[0] - observed_size[0] / 2.0,
            center[1] - observed_size[1] / 2.0,
            -0.01,
        ])
        observed_high = np.asarray([
            center[0] + observed_size[0] / 2.0,
            center[1] + observed_size[1] / 2.0,
            observed_size[2] - 0.01,
        ])
        contained = bool(
            np.all(observed_low >= proxy_low - 1e-12)
            and np.all(observed_high <= proxy_high + 1e-12)
        )
        all_contained &= contained
        containment[side] = {
            "proxy_bounds_m": [proxy_low.tolist(), proxy_high.tolist()],
            "observed_conservative_bounds_m": [observed_low.tolist(), observed_high.tolist()],
            "axis_clearance_low_m": (observed_low - proxy_low).tolist(),
            "axis_clearance_high_m": (proxy_high - observed_high).tolist(),
            "contained": contained,
        }

    report = {
        "schema": "cruzr-s2-vla-observed-clamp-envelope-e6.0k-v1",
        "experiment_id": "E6.0K",
        "mode": "local_containment_proof_no_robot_no_network_no_ros_no_publisher",
        "status": (
            "PASS_OBSERVED_CLAMP_ENVELOPE_CONTAINED_IN_E6_0J_PROXY"
            if all_contained else
            "FAIL_OBSERVED_CLAMP_ENVELOPE_EXCEEDS_E6_0J_PROXY"
        ),
        "source_sha256": {
            args.observed_contract.name: sha256(args.observed_contract),
            args.document_proxy_report.name: sha256(args.document_proxy_report),
        },
        "observation": observed["observation"],
        "conservative_envelope": observed["conservative_envelope"],
        "containment": containment,
        "proof": {
            "e6_0j_sample_count": proxy_report["trajectory"]["sample_count"],
            "e6_0j_exact_intersections": proxy_report["collision_audit"]["exact_intersection_count"],
            "logic": "a rigidly mounted subset cannot intersect any obstacle when its containing proxy OBB has no candidate overlap at the same sampled transforms",
            "direct_resweep_required": False,
        },
        "limitations": observed["scope"],
        "physical_authorized": False,
        "robot_state_read": False,
        "network_calls": 0,
        "physical_publishers": 0,
        "physical_movement_commanded": False,
    }
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(f"E6.0K_STATUS={report['status']}")
    print("E6.0K_OBSERVED_RAW_XYZ_M=" + ",".join(
        f"{value:.3f}" for value in observed["observation"]["raw_maximum_envelope_mount_axes_xyz_m"]
    ))
    print("E6.0K_CONSERVATIVE_XYZ_M=" + ",".join(f"{value:.3f}" for value in observed_size))
    print(f"E6.0K_CONTAINED_BOTH={int(all_contained)}")
    print("E6.0K_PHYSICAL_AUTHORIZED=0")
    return 0 if all_contained else 1


if __name__ == "__main__":
    raise SystemExit(main())
