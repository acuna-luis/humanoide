#!/usr/bin/env python3
"""Classify workbin release history; does not certify physical clearance."""
import json
import sys


def classify_context(data):
    if type(data.get("writers")) is not int or data["writers"] != 0:
        raise ValueError("Otro cliente publica comandos o no se pudo comprobarlo")
    if type(data.get("unsafe_event")) is not bool or data["unsafe_event"]:
        raise ValueError("Evento de fuerza/autocolisión posterior; recuperación específica requerida")
    task = data.get("last_task")
    if task == "cruzr/blue_workbin_open_only":
        return "already_attempted"
    if task != "cruzr/blue_workbin_clamp_only":
        raise ValueError("La última tarea no es el agarre workbin; no usar desde PICO/HOME/postura desconocida")
    return "clamp"


if __name__ == "__main__":
    try:
        print(classify_context(json.load(sys.stdin)))
    except (ValueError, TypeError, AttributeError) as error:
        print("OPEN_ONLY_BLOCKED: " + str(error), file=sys.stderr)
        sys.exit(2)
