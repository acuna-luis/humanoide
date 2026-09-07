#!/usr/bin/env python3
"""Classify a complete Cruzr S2 actuator snapshot; not motion authorization.

The script is deliberately read-only.  It consumes the JSON emitted by
``rosa topic echo --once --no-daemon /mc/actuator_state`` and never imports a
ROS client or publishes anything. Freshness must be established by the caller;
this classifier does not verify timestamps or collision clearance.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from typing import Any


BODY_ACTUATOR_ALIASES = (
    ("head_yaw", (1001,)),
    ("head_pitch", (1002,)),
    ("lifter_pitch_1", (2001, 11004)),
    ("lifter_pitch_2", (2002, 11003)),
    ("lifter_pitch_3", (2003, 11002)),
    ("waist_yaw", (3001, 11001)),
    *((f"left_arm_{actuator_id}", (actuator_id,)) for actuator_id in range(4001, 4008)),
    *((f"right_arm_{actuator_id}", (actuator_id,)) for actuator_id in range(5001, 5008)),
)
ARM_IDS = (*range(4001, 4008), *range(5001, 5008))


def numeric(item: dict[str, Any], key: str) -> float:
    if type(item.get(key)) not in (int, float):
        raise ValueError(f"{key} ausente o no numérico")
    value = float(item[key])
    if not math.isfinite(value):
        raise ValueError(f"{key} no es finito")
    return value


def integer(item: dict[str, Any], key: str) -> int:
    value = item.get(key)
    if type(value) is not int or value < 0:
        raise ValueError(f"{key} ausente o entero inválido")
    return value


def classify(message: dict[str, Any], home_tolerance: float) -> list[str]:
    if (type(home_tolerance) not in (int, float) or not math.isfinite(home_tolerance)
            or not 0 < home_tolerance <= 0.05):
        raise ValueError("tolerancia HOME inválida")
    if not isinstance(message, dict):
        raise ValueError("muestra raíz inválida")
    items = message.get("act_item")
    if not isinstance(items, list):
        raise ValueError("falta act_item")

    by_id: dict[int, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("act_item contiene un elemento no válido")
        actuator_id = integer(item, "id")
        if actuator_id == 0:
            raise ValueError("id de actuador no válido")
        if actuator_id in by_id:
            raise ValueError(f"actuador duplicado: {actuator_id}")
        by_id[actuator_id] = item

    selected: list[tuple[str, int, dict[str, Any]]] = []
    missing: list[str] = []
    for logical_name, aliases in BODY_ACTUATOR_ALIASES:
        matches = [actuator_id for actuator_id in aliases if actuator_id in by_id]
        if not matches:
            missing.append(f"{logical_name}({'|'.join(map(str, aliases))})")
            continue
        if len(matches) > 1:
            raise ValueError(
                f"actuador lógico duplicado {logical_name}: "
                + ",".join(map(str, matches))
            )
        actuator_id = matches[0]
        selected.append((logical_name, actuator_id, by_id[actuator_id]))
    if missing:
        raise ValueError("faltan actuadores 20D: " + ",".join(missing))

    faults: list[str] = []
    maximum_position = 0.0
    maximum_velocity = 0.0
    maximum_command_delta = 0.0
    arm_maximum_position = 0.0

    for _logical_name, actuator_id, item in selected:
        name = str(item.get("name", "unknown"))
        error_code = integer(item, "error_code")
        status = integer(item, "status")
        position = numeric(item, "position")
        velocity = numeric(item, "velocity")
        command_position = numeric(item, "cmd_pos")
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
        f"ACTUATOR_BODY_COUNT={len(BODY_ACTUATOR_ALIASES)}",
        f"ACTUATOR_ARM_COUNT={len(ARM_IDS)}",
        f"BODY_MAX_ABS_POSITION={maximum_position:.6f}",
        f"ARMS_MAX_ABS_POSITION={arm_maximum_position:.6f}",
        f"BODY_MAX_ABS_VELOCITY={maximum_velocity:.6f}",
        f"BODY_MAX_ABS_COMMAND_DELTA={maximum_command_delta:.6f}",
        f"MEASURED_HOME={'1' if near_home else '0'}",
        "POSTURE_CLASSIFICATION_ONLY=1",
        "PHYSICAL_AUTHORIZED=0",
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
