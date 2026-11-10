#!/usr/bin/env python3
"""Compara predicciones SmolVLA con fases externas, exclusivamente en memoria.

Lee JSONL de stdin y escribe JSONL en stdout. No accede al robot ni crea
mensajes, objetivos de articulaciones, corrientes o comandos. El escalar de la
mano es informativo, no determina cuándo cerrar. Las señales externas no están
verificadas y este ensayo no habilita el control físico.
"""

import argparse
import json
import math
import re
import sys

from ball_hand_phase_policy import BallHandPhasePolicy

MAX_LINE = 1024 * 1024


class BallHandBridgePreview:
    """Un único intento simbólico, sin rearme, cuyos datos deben corresponder."""

    def __init__(self):
        self._policy = BallHandPhasePolicy()
        self._last_stamp = 0

    def update(self, row):
        if not isinstance(row, dict):
            raise ValueError('la entrada debe ser un objeto')
        prediction = row.get('prediction')
        evidence = row.get('phase_evidence')
        if not isinstance(prediction, dict) or prediction.get('event') != 'prediction':
            raise ValueError('falta una predicción del shadow')
        if not isinstance(evidence, dict):
            raise ValueError('faltan señales externas de fase')
        stamp = prediction.get('image_source_ns')
        digest = prediction.get('image_sha256')
        values = prediction.get('prediction')
        sequence = row.get('sequence')
        if (type(stamp) is not int or stamp <= self._last_stamp
                or not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest)):
            raise ValueError('imagen sin hash válido o sello creciente')
        if (type(evidence.get('image_source_ns')) is not int
                or evidence.get('image_source_ns') != stamp
                or evidence.get('image_sha256') != digest):
            raise ValueError('las señales deben referirse a la misma imagen')
        if (not isinstance(values, list) or len(values) != 8
                or any(type(value) not in (int, float) or not math.isfinite(value)
                       for value in values)):
            raise ValueError('la predicción debe contener ocho valores finitos')
        signals = evidence.get('signals')
        if not isinstance(signals, dict):
            raise ValueError('se requieren señales de fase explícitas, aunque estén vacías')
        phase = self._policy.update(sequence, signals)
        self._last_stamp = stamp
        return {
            'schema': 'cruzr_ball_hand_bridge_preview_v1',
            'sequence': sequence,
            'image_source_ns': stamp,
            'image_sha256': digest,
            'model_hand_scalar_uninterpreted': values[7],
            'simulated_phase': phase['phase'],
            'simulated_hand_label': phase['symbolic_hand_goal'],
            'physical_control_qualified': False,
            'physical_commands_generated': 0,
            'limitations': [
                'external phase signals and their association with an image are not independently verified',
                'the model scalar is not calibrated and does not change the simulated phase',
                'matching image identifiers does not establish freshness or clock synchronization',
                'no finger targets, control modes, current, ROS messages or commands are generated',
            ],
        }


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    preview = BallHandBridgePreview()
    try:
        for raw in iter(lambda: sys.stdin.buffer.readline(MAX_LINE + 1), b''):
            if len(raw) > MAX_LINE or not raw.endswith(b'\n'):
                raise ValueError('línea excesiva o truncada')
            row = json.loads(raw)
            print(json.dumps(preview.update(row), ensure_ascii=False, allow_nan=False), flush=True)
    except (ValueError, TypeError, OverflowError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
