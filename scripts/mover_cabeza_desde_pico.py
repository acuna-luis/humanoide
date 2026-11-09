#!/usr/bin/env python3
"""Preparación sin movimiento para una futura prueba de cabeza desde PICO.

Este programa no conecta con el robot ni contiene un publicador de órdenes.
La opción --run está bloqueada: el movimiento desde PICO con manos v4 y la
parada de esa intervención todavía no disponen de un procedimiento validado.
"""

import argparse
import datetime as dt
import json
import math
import sys
from pathlib import Path


BODY_JOINTS = (
    "head_yaw_joint", "head_pitch_joint", "waist_yaw_joint",
    *(f"lifter_pitch_{n}_joint" for n in (1, 2, 3)),
    *(f"{side}_{joint}_joint" for side in ("L", "R") for joint in (
        "shoulder_pitch", "shoulder_roll", "shoulder_yaw", "elbow_roll",
        "elbow_yaw", "wrist_pitch", "wrist_roll")),
)


def read_snapshot(path):
    """Lee el formato local control-read.json; no evalúa seguridad física."""
    with path.open(encoding="utf-8") as stream:
        document = json.load(stream)
    capture = document["captured_utc"]
    stamp = dt.datetime.fromisoformat(capture)
    if stamp.tzinfo is None:
        raise ValueError("captured_utc no incluye zona horaria")
    record = document["checks"]["whole_joint_states"]
    if record["returncode"] != 0:
        raise ValueError("la lectura de articulaciones falló")
    # Algunos contenedores anteponen una línea de diagnóstico al JSON ROS.
    raw = record["stdout"]
    start = raw.find("{")
    if start < 0:
        raise ValueError("no se encontró el JSON de articulaciones")
    message, _ = json.JSONDecoder().raw_decode(raw[start:])
    names, positions = message["name"], message["position"]
    if not isinstance(names, list) or not isinstance(positions, list):
        raise ValueError("los nombres o posiciones no son listas")
    if len(names) != len(positions) or any(not isinstance(n, str) for n in names):
        raise ValueError("nombres y posiciones incompatibles")
    if len(set(names)) != len(names):
        raise ValueError("hay nombres articulares duplicados")
    mapped = dict(zip(names, positions))
    if any(name not in mapped for name in BODY_JOINTS):
        raise ValueError("faltan articulaciones corporales")
    for name in BODY_JOINTS:
        value = mapped[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"posición no numérica o no finita: {name}")
    return stamp, mapped


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Diagnóstico local de una captura anterior; no mueve el robot."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="diagnóstico local (opción por defecto)")
    mode.add_argument("--run", action="store_true", help="reservado: movimiento bloqueado")
    parser.add_argument("--estado", type=Path, metavar="CONTROL_READ_JSON",
                        help="analiza una captura control-read.json existente, sin conectarse")
    args = parser.parse_args(argv)

    if args.run:
        print("BLOQUEADO: no hay ejecutor físico cualificado desde PICO con manos v4; "
              "no se ha conectado ni enviado ninguna orden.", file=sys.stderr)
        return 2

    print("Diagnóstico local: no se conecta al robot ni envía órdenes.")
    if args.estado:
        try:
            stamp, positions = read_snapshot(args.estado)
        except (OSError, KeyError, TypeError, ValueError, OverflowError) as exc:
            print(f"Captura inválida o ilegible: {exc}", file=sys.stderr)
            return 2
        largest = max(BODY_JOINTS, key=lambda name: abs(positions[name]))
        print(f"Captura histórica: {stamp.isoformat()}")
        print(f"Cabeza: yaw={positions['head_yaw_joint']:.6f} rad, "
              f"pitch={positions['head_pitch_joint']:.6f} rad")
        print(f"Mayor distancia absoluta al cero corporal: {largest} = "
              f"{abs(positions[largest]):.6f} rad")
        print("Una captura puntual no acredita postura, reposo ni condiciones actuales.")
    else:
        print("Sin captura para analizar; use --estado con control-read.json si dispone de ella.")

    print("Referencia histórica: cruzr/move_head_lower, yaw=0 y pitch=-0,43 rad "
          "en 2 s; hash XML f3a73626f97b471d4a0a03c98c24de32243651116c497328e69b5ddc57ea46c1.")
    print("No se ha comprobado la versión instalada actual ni que ese objetivo vea la pelota.")
    print("PENDIENTE: geometría y recorrido para manos v4 en postura PICO; "
          "modo y exclusividad de control; seguimiento y parada; "
          "verificación física actual supervisada.")
    print("El ejecutor histórico de cabeza exige HOME y no acredita esta configuración.")
    print("Resultado: movimiento NO HABILITADO; ningún parámetro lo desbloquea.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
