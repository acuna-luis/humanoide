#!/usr/bin/env python3
"""Create one short-lived E6.0 activation grant from captured evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any


SCOPE = "E6.0_NO_BOX_READY_TASK_0_P14_A_ONE_SOURCE_POINT_ONLY"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"json:not_object:{path}")
    return value


def key_values(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key and key.replace("_", "").replace(".", "").isalnum():
            result[key] = value
    return result


def require(values: dict[str, str], expected: dict[str, str], label: str) -> None:
    failures = [f"{key}={values.get(key)!r}" for key, value in expected.items() if values.get(key) != value]
    if failures:
        raise ValueError(f"{label}:" + ",".join(failures))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--acceptance", type=Path, required=True)
    parser.add_argument("--limits", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--ready", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--valid-seconds", type=int, default=120)
    parser.add_argument(
        "--reference-epoch",
        type=int,
        help="epoch UTC fresco del host Motion que validará el grant",
    )
    args = parser.parse_args()
    if not args.run_id.startswith("20") or not args.run_id.endswith("_E6.0Y"):
        raise SystemExit("ERROR: run-id E6.0Y inválido")
    if not 30 <= args.valid_seconds <= 180:
        raise SystemExit("ERROR: vigencia debe estar entre 30 y 180 s")

    template = load_object(args.template)
    acceptance = load_object(args.acceptance)
    limits = load_object(args.limits)
    preflight = key_values(args.preflight)
    ready = key_values(args.ready)
    preflight_lines = set(args.preflight.read_text(encoding="utf-8").splitlines())
    if acceptance.get("owner_accepted") is not True:
        raise SystemExit("ERROR: falta aceptación del propietario")
    if acceptance.get("scope") != SCOPE:
        raise SystemExit("ERROR: scope de aceptación distinto")
    if acceptance.get("engineering_limits_sha256") != sha256(args.limits):
        raise SystemExit("ERROR: aceptación no corresponde a estos límites")
    for key, expected in (
        ("maximum_target_delta_rad", 0.1),
        ("maximum_velocity_rad_s", 0.15),
        ("maximum_acceleration_rad_s2", 0.5),
    ):
        values = limits.get(key)
        if not isinstance(values, list) or values != [expected] * 14:
            raise SystemExit(f"ERROR: límites inesperados: {key}")
    require(preflight, {
        "ESTOP_KEY": "0",
        "SERVO_ESTOP_KEY": "0",
        "WHOLE_JOINT_STATES": "advertised",
        "MANIPULATION_ACTION_SERVERS": "1",
        "READY_TASK_REGISTERED": "1",
        "READY_XML_VARIANT": "s2-waist-1d-overlay",
        "INFERENCE_CONTAINER": "exited",
        "CONTROL_CONTAINER": "exited",
        "COMMAND_PATH_SAFE": "publishers:0",
        "ACTUATORS_OPERATION_ENABLED": "1",
        "ESTOPS": "0,0",
        "CHARGER": "disconnected",
        "ACTIONS": "ready",
        "CANONICAL_MANIPULATION_PREFLIGHT": "passed-read-only",
    }, "preflight")
    if "CHARGER=0" not in preflight_lines:
        raise SystemExit("ERROR: preflight no contiene la lectura cruda CHARGER=0")
    require(ready, {
        "READY_ARM_COUNT": "14",
        "READY_LOCKED_AXIS_COUNT": "6",
        "MEASURED_READY": "1",
    }, "ready")

    local_now = dt.datetime.now(dt.timezone.utc)
    if args.reference_epoch is None:
        now = local_now
        clock_source = "local-builder-clock"
        clock_skew_seconds = 0.0
    else:
        now = dt.datetime.fromtimestamp(args.reference_epoch, tz=dt.timezone.utc)
        clock_source = "motion-host-epoch"
        clock_skew_seconds = (local_now - now).total_seconds()
        if abs(clock_skew_seconds) > 60.0:
            raise SystemExit(
                "ERROR: desfase PC/Motion mayor de 60 s; no se crea grant"
            )
    expiry = now + dt.timedelta(seconds=args.valid_seconds)
    grant = dict(template)
    grant.update({
        "experiment_id": "E6.0Y",
        "owner_accepted_engineering_limits": True,
        "active_launcher_enabled": True,
        "physical_execution_authorized": True,
        "authorization_scope": SCOPE,
        "authorization_run_id": args.run_id,
        "authorization_issued_at": now.isoformat(),
        "authorization_expires_at": expiry.isoformat(),
        "authorization_valid_seconds": args.valid_seconds,
        "authorization_clock_source": clock_source,
        "authorization_clock_reference_epoch": args.reference_epoch,
        "authorization_clock_skew_seconds": clock_skew_seconds,
        "authorization_preflight_sha256": sha256(args.preflight),
        "authorization_ready_sha256": sha256(args.ready),
        "authorization_acceptance_sha256": sha256(args.acceptance),
        "authorization_limits_sha256": sha256(args.limits),
        "not_authorized_reason": None,
    })
    args.output.write_text(json.dumps(grant, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"E6.0Y_GRANT={args.output}")
    print(f"E6.0Y_GRANT_SHA256={sha256(args.output)}")
    print(f"E6.0Y_GRANT_EXPIRES_AT={grant['authorization_expires_at']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
