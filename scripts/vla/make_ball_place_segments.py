#!/usr/bin/env python3
"""Genera la especificación de segmentos para prepare_ball_observations.py a
partir de grabaciones PICO de "coger pelota del aro 1 y dejarla en el aro 2".

Protocolo de grabación (10-11-2026): cada intento sale de la postura PICO del
brazo derecho y vuelve a ella; la cabeza sigue al visor (erguida en la postura
PICO, bajada durante el intento). Un intento se marca `candidate_success` si
contiene un cierre de mano (modo 7) mantenido >= --success-hold-s; si no,
`failed`. El segmento empieza en el primer fotograma del intento con la cabeza
bajada (pitch <= --head-pitch-max) y termina al volver a la postura PICO.

Sólo lee las grabaciones; escribe un JSON nuevo (no sobrescribe).
Uso:
  python3 -B scripts/vla/make_ball_place_segments.py \
     --capture ../Humanoide-vla-evidence/<EP1>:inspection_train \
     --capture ../Humanoide-vla-evidence/<EP2>:inspection_validation \
     --output config/vla/ball_place_segments_YYYYMMDD.json
"""
import argparse
import ast
import json
import math
from pathlib import Path
import sys

R_ARM = ['R_shoulder_pitch_joint', 'R_shoulder_roll_joint', 'R_shoulder_yaw_joint',
         'R_elbow_roll_joint', 'R_elbow_yaw_joint', 'R_wrist_pitch_joint', 'R_wrist_roll_joint']
PICO_POSE = [0.0, -0.15, 1.57, -1.57, -2.88, 0.0, 0.0]
SPLITS = {'inspection_train', 'inspection_validation', 'inspection_test', 'unassigned'}


def parse_list(value):
    return value if isinstance(value, list) else ast.literal_eval(value)


def hand_closes(source):
    """Intervalos (inicio_ns, fin_ns) con orden de mano derecha modo 7."""
    closes, start, last = [], None, None
    with (source / 'samples.jsonl').open(encoding='utf-8') as f:
        for line in f:
            if '"hand_command_right"' not in line:
                continue
            row = json.loads(line)
            mode, ns = row.get('message', {}).get('mode'), row.get('source_ns')
            if not isinstance(mode, list) or not isinstance(ns, int):
                continue
            last = ns
            if mode == [7] * 7 and start is None:
                start = ns
            elif mode == [5] * 7 and start is not None:
                closes.append((start, ns))
                start = None
    if start is not None and last is not None:
        closes.append((start, last))
    return closes


def segments_for(source, split, args):
    manifest = json.loads((source / 'manifest.json').read_text(encoding='utf-8'))
    names = parse_list(manifest['joint_names'])
    idx = [names.index(j) for j in R_ARM]
    hp = names.index('head_pitch_joint')
    frames = []
    with (source / 'aligned.jsonl').open(encoding='utf-8') as f:
        for line in f:
            row = json.loads(line)
            state = parse_list(row['state20'])
            n = int(Path(row['png_file']).stem)
            frames.append((n, row['image_source_ns'], [state[i] for i in idx], state[hp]))
    frames.sort()
    closes = hand_closes(source)
    attempts, current = [], None
    for n, ns, arm, pitch in frames:
        away = math.dist(arm, PICO_POSE) > args.pico_tolerance_rad
        if away and current is None:
            current = [n, ns, None, None]
        if current is not None:
            if away:
                current[2], current[3] = n, ns
            else:
                attempts.append(current)
                current = None
    if current is not None:
        attempts.append(current)
    result, tag = [], manifest.get('task', source.name)
    for k, (n0, ns0, n1, ns1) in enumerate(attempts):
        lowered = [n for n, ns, arm, pitch in frames if n0 <= n <= n1 and pitch <= args.head_pitch_max]
        if not lowered or n1 - lowered[0] + 1 < args.min_frames:
            continue
        holds = [(a, b) for a, b in closes if ns0 <= a <= ns1]
        best = max(((b - a) / 1e9 for a, b in holds), default=0.0)
        ok = best >= args.success_hold_s
        # Si la grabación terminó durante el intento, no es un ciclo completo.
        truncated = n1 == frames[-1][0]
        status = 'candidate_success' if ok and not truncated else 'failed'
        result.append({
            'id': f'{tag}_a{k:02d}_{lowered[0]}_{n1}',
            'source_dir': str(source),
            'start_frame': lowered[0], 'end_frame': n1,
            'status': status, 'split': split,
            'notes': (f'Auto: intento {k} desde postura PICO; cabeza bajada desde frame {lowered[0]}; '
                      f'{len(holds)} cierres, máximo {best:.1f} s; '
                      f'{"truncado por fin de grabación; " if truncated else ""}'
                      f'éxito = cierre >= {args.success_hold_s} s (confirmado por el operador 10-11-2026).'),
        })
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--capture', action='append', required=True, help='DIR:SPLIT (repetible)')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--success-hold-s', type=float, default=4.0)
    p.add_argument('--head-pitch-max', type=float, default=-0.6)
    p.add_argument('--pico-tolerance-rad', type=float, default=0.05)
    p.add_argument('--min-frames', type=int, default=8)
    args = p.parse_args(argv)
    if args.output.exists():
        print('ERROR: la salida ya existe', file=sys.stderr)
        return 1
    segments = []
    for item in args.capture:
        path, _, split = item.rpartition(':')
        if split not in SPLITS:
            print(f'ERROR: split inválido {split}', file=sys.stderr)
            return 2
        segments += segments_for(Path(path).resolve(strict=True), split, args)
    with args.output.open('x', encoding='utf-8') as f:
        json.dump({'segments': segments}, f, ensure_ascii=False, indent=2)
        f.write('\n')
    for s in segments:
        print(f"{s['id']:40s} {s['split']:22s} {s['status']:18s} frames {s['start_frame']}-{s['end_frame']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
