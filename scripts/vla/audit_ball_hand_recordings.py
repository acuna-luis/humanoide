#!/usr/bin/env python3
"""Cuenta estados y campos de mano derecha en una grabación, sin mover robot.

Sólo resume mensajes crudos de `samples.jsonl`: correlaciones entre valores y
modos no establecen semántica, control de par, unidades ni seguridad física.
No abre ni modifica el robot, no publica y no genera órdenes para los dedos.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import sys

from prepare_ball_observations import RIGHT_HAND

FIELDS = ('position', 'velocity', 'torque', 'acceleration', 'kp', 'kd')
REQUIRED_FIELDS = ('position', 'velocity', 'torque', 'kp', 'kd')
MAX_LINE = 8 * 1024 * 1024
MAX_VARIANTS = 10000


def finite_vector(value):
    return (isinstance(value, list) and len(value) == 7 and
            all(type(v) in (float, int) and math.isfinite(v) for v in value))


def analyze(stream):
    digest = hashlib.sha256()
    states = commands = invalid = 0
    modes = Counter()
    vectors = defaultdict(Counter)
    fields = Counter()
    acceleration_lengths = Counter()
    for line in iter(lambda: stream.readline(MAX_LINE + 1), b''):
        if len(line) > MAX_LINE or not line.endswith(b'\n'):
            raise ValueError('línea excesiva o truncada')
        digest.update(line)
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError('registro no es objeto')
        kind = row.get('kind')
        if kind == 'hand_right':
            states += 1
            continue
        if kind != 'hand_command_right':
            continue
        commands += 1
        message = row.get('message')
        if not isinstance(message, dict):
            invalid += 1
            continue
        fields.update(message.keys())
        acceleration = message.get('acceleration')
        acceleration_lengths[len(acceleration) if isinstance(acceleration, list) else 'missing_or_invalid'] += 1
        mode = message.get('mode')
        if (message.get('names') != RIGHT_HAND or not isinstance(mode, list) or
                len(mode) != 7 or any(type(x) is not int for x in mode) or
                any(not finite_vector(message.get(name)) for name in REQUIRED_FIELDS) or
                (acceleration != [] and not finite_vector(acceleration))):
            invalid += 1
            continue
        key = tuple(mode)
        torque = tuple(message['torque'])
        modes[key] += 1
        vectors[torque][key] += 1
        if len(vectors) > MAX_VARIANTS or len(modes) > MAX_VARIANTS:
            raise ValueError('exceso de combinaciones distintas')
    shared = [{'torque': list(torque), 'modes': [list(x) for x in sorted(counts)],
               'counts': [counts[x] for x in sorted(counts)]}
              for torque, counts in vectors.items() if len(counts) > 1]
    return {'schema': 'cruzr_ball_hand_recordings_audit_v1', 'samples_sha256': digest.hexdigest(),
            'right_hand_state_messages': states, 'right_hand_command_messages': commands,
            'invalid_commands': invalid,
            'field_counts': dict(sorted(fields.items())),
            'acceleration_length_counts': {str(k): v for k, v in acceleration_lengths.items()},
            'mode_counts': [{'mode': list(mode), 'count': count} for mode, count in sorted(modes.items())],
            'shared_torque_vectors': shared,
            'physical_control_qualified': False, 'physical_commands_generated': 0,
            'limitations': ['raw captured commands may be partial and are not known to have been applied',
                            'mode and torque fields do not establish units, controller semantics or safe force',
                            'this evidence does not identify the PICO trigger or calibrate synchronization']}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('samples_jsonl', type=Path, help='captura samples.jsonl existente, sólo lectura')
    args = p.parse_args(argv)
    try:
        with args.samples_jsonl.open('rb') as stream:
            result = analyze(stream)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))
    except (OSError, ValueError, TypeError, OverflowError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
