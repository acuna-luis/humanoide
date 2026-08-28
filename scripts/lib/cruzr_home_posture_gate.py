#!/usr/bin/env python3
"""Classify a fresh Cruzr S2 actuator snapshot for return-to-home.

The script is deliberately read-only.  It consumes the JSON emitted by
``rosa topic echo --once --no-daemon /mc/actuator_state`` and never imports a
ROS client or publishes anything.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from typing import Any


BODY_IDS = (
    1001,
    1002,
    2001,
    2002,
    2003,
    3001,
    *range(4001, 4008),
    *range(5001, 5008),
)
ARM_IDS = (*range(4001, 4008), *range(5001, 5008))


def numeric(item: dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        value = float(item.get(key, default))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} no es numérico") from exc
    if not math.isfinite(value):
        raise ValueError(f"{key} no es finito")
    return value


def classify(message: dict[str, Any], home_tolerance: float) -> list[str]:
    items = message.get("act_item")
    if not isinstance(items, list):
        raise ValueError("falta act_item")

    by_id: dict[int, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("act_item contiene un elemento no válido")
        try:
            actuator_id = int(item.get("id", 0))
        except (TypeError, ValueError) as exc:
            raise ValueError("id de actuador no válido") from exc
        if actuator_id in by_id:
            raise ValueError(f"actuador duplicado: {actuator_id}")
        by_id[actuator_id] = item

    missing = [actuator_id for actuator_id in BODY_IDS if actuator_id not in by_id]
    if missing:
        raise ValueError("faltan actuadores 20D: " + ",".join(map(str, missing)))

    faults: list[str] = []
    maximum_position = 0.0
    maximum_velocity = 0.0
    maximum_command_delta = 0.0
    arm_maximum_position = 0.0

    for actuator_id in BODY_IDS:
        item = by_id[actuator_id]
        name = str(item.get("name", "unknown"))
        error_code = int(item.get("error_code", 0))
        status = int(item.get("status", 0))
        position = numeric(item, "position")
        velocity = numeric(item, "velocity")
        command_position = numeric(item, "cmd_pos", position)
        command_delta = command_position - position

        maximum_position = max(maximum_position, abs(position))
        maximum_velocity = max(maximum_velocity, abs(velocity))
        maximum_command_delta = max(maximum_command_delta, abs(command_delta))
        if actuator_id in ARM_IDS:
            arm_maximum_position = max(arm_maximum_position, abs(position))

        operation_enabled = (status & 0x0007) == 0x0007
        fault = bool(status & 0x0008)
        if error_code or fault or not operation_enabled:
            faults.append(
                f"{actuator_id},{name},error=0x{error_code:04x},"
                f"status=0x{status:04x}"
            )

    if faults:
        raise ValueError("actuadores no habilitados: " + ";".join(faults))
    if maximum_velocity > 0.02:
        raise ValueError(
            f"robot en movimiento: max_abs_velocity={maximum_velocity:.6f}"
        )
    if maximum_command_delta > 0.01:
        raise ValueError(
            "consigna latente: "
            f"max_abs_command_delta={maximum_command_delta:.6f}"
        )

    near_home = maximum_position < home_tolerance
    return [
        f"ACTUATOR_BODY_COUNT={len(BODY_IDS)}",
        f"ACTUATOR_ARM_COUNT={len(ARM_IDS)}",
        f"BODY_MAX_ABS_POSITION={maximum_position:.6f}",
        f"ARMS_MAX_ABS_POSITION={arm_maximum_position:.6f}",
        f"BODY_MAX_ABS_VELOCITY={maximum_velocity:.6f}",
        f"BODY_MAX_ABS_COMMAND_DELTA={maximum_command_delta:.6f}",
        f"MEASURED_HOME={'1' if near_home else '0'}",
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--home-tolerance",
        type=float,
        default=0.02,
        help="maximum absolute 20D body position in radians (default: 0.02)",
    )
    args = parser.parse_args()
    if not 0.0 < args.home_tolerance <= 0.05:
        parser.error("--home-tolerance debe estar en (0, 0.05]")

    try:
        message = json.load(sys.stdin)
        if not isinstance(message, dict):
            raise ValueError("la muestra raíz no es un objeto JSON")
        lines = classify(message, args.home_tolerance)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"ACTUATOR_POSTURE_ERROR={exc}", file=sys.stderr)
        return 2

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
