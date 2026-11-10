#!/usr/bin/env python3
"""Audita offline la intención de mano frente a fases anotadas, sin control.

El escalar de SmolVLA es una regresión no calibrada de etiquetas provisionales.
Las fases deben proceder de una revisión externa; el script no comprueba que la
mano haya alcanzado la pelota, que esté cerrada ni que la pelota esté apoyada.
No produce mensajes ROS, posiciones de dedos, modos, pares ni órdenes físicas.
"""
import argparse
import json
import math
from pathlib import Path
import re
import sys

PHASES = ('approach', 'grasp', 'lift', 'lower', 'release')
MAX_ROWS = 10000
MAX_LINE = 4 * 1024 * 1024


def load_rows(path):
    rows = []
    with Path(path).open(encoding='utf-8') as stream:
        for number, line in enumerate(stream, 1):
            if number > MAX_ROWS or len(line) > MAX_LINE:
                raise ValueError('entrada excede el límite de filas o de línea')
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f'JSON inválido en línea {number}') from exc
            if not isinstance(row, dict):
                raise ValueError(f'la línea {number} no es un objeto')
            rows.append(row)
    return rows


def analyze(predictions, annotations, threshold=0.5):
    if (type(threshold) not in (float, int) or not math.isfinite(threshold)
            or not 0 < threshold < 1):
        raise ValueError('el umbral exploratorio debe ser finito y estar entre 0 y 1')
    if len(predictions) > MAX_ROWS or len(annotations) > MAX_ROWS:
        raise ValueError('demasiadas filas')
    by_stamp = {}
    last_stamp = 0
    last_phase = -1
    for row in annotations:
        if not isinstance(row, dict):
            raise ValueError('anotación inválida')
        stamp, phase, digest = row.get('image_source_ns'), row.get('phase'), row.get('image_sha256')
        if (type(stamp) is not int or stamp <= last_stamp or phase not in PHASES or
                not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest)):
            raise ValueError('anotaciones requieren tiempos crecientes y fase conocida')
        index = PHASES.index(phase)
        if index < last_phase:
            raise ValueError('la secuencia anotada de fases retrocede')
        by_stamp[stamp] = (phase, digest)
        last_stamp, last_phase = stamp, index

    findings = []
    observed_stamps = set()
    last_stamp = 0
    for row in predictions:
        if not isinstance(row, dict):
            raise ValueError('predicción inválida')
        if row.get('event') != 'prediction':
            continue
        stamp, values = row.get('image_source_ns'), row.get('prediction')
        if type(stamp) is not int or stamp <= last_stamp:
            raise ValueError('sellos de predicción ausentes, duplicados o no crecientes')
        if (not isinstance(values, list) or len(values) != 8 or
                any(type(v) not in (int, float) or not math.isfinite(v) for v in values)):
            raise ValueError('cada predicción debe tener ocho números finitos')
        observed_stamps.add(stamp)
        last_stamp = stamp
        score = values[7]
        candidate = 'grasp_hold_candidate' if score >= threshold else 'open_candidate'
        annotation = by_stamp.get(stamp)
        if annotation is not None and row.get('image_sha256') != annotation[1]:
            raise ValueError('el hash de la imagen anotada no coincide con la predicción')
        phase = annotation[0] if annotation is not None else None
        issue = None
        if phase == 'approach' and candidate == 'grasp_hold_candidate':
            issue = 'candidate_premature_closure'
        elif phase == 'grasp' and candidate == 'open_candidate':
            issue = 'candidate_missing_closure'
        elif phase in ('lift', 'lower') and candidate == 'open_candidate':
            issue = 'candidate_premature_opening'
        elif phase == 'release' and candidate == 'grasp_hold_candidate':
            issue = 'candidate_missing_release'
        findings.append({'image_source_ns': stamp, 'phase_annotation': phase,
                         'hand_score': score, 'candidate_label': candidate,
                         'finding': issue})
    if not findings:
        raise ValueError('no hay predicciones para auditar')
    if set(by_stamp) - observed_stamps:
        raise ValueError('una anotación no corresponde a ninguna predicción')
    issues = [item for item in findings if item['finding'] is not None]
    coverage = 'unannotated' if not by_stamp else ('complete' if len(by_stamp) == len(findings) else 'partial')
    return {'schema': 'cruzr_ball_hand_intent_audit_v1',
            'physical_control_qualified': False, 'physical_commands_generated': 0,
            'audit_coverage': coverage,
            'threshold_exploratory_not_calibrated': threshold,
            'samples': len(findings), 'annotated_samples': len(by_stamp),
            'unannotated_samples': len(findings) - len(by_stamp),
            'mismatch_count': len(issues) if by_stamp else None, 'findings': findings,
            'limitations': ['phase annotations are supplied externally and are not independently verified',
                            'a model score is not a calibrated probability or seven-finger command',
                            'absence of a mismatch does not validate hand state, force or physical safety']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--predictions', type=Path, required=True,
                        help='JSONL del shadow en vivo, entrada de sólo lectura')
    parser.add_argument('--annotations', type=Path,
                        help='JSONL externo: image_source_ns, image_sha256 y phase '
                             '(approach, grasp, lift, lower, release); no valida la fase')
    parser.add_argument('--threshold', type=float, default=0.5,
                        help='umbral exclusivamente exploratorio, no calibrado (por defecto 0,5)')
    args = parser.parse_args(argv)
    try:
        annotations = load_rows(args.annotations) if args.annotations else []
        result = analyze(load_rows(args.predictions), annotations, args.threshold)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))
    except (OSError, ValueError, OverflowError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
