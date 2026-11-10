#!/usr/bin/env python3
"""Evaluación offline con una grabación apartada usando el servidor del shadow.

Envía los fotogramas de un segmento `candidate_targets` (no usado para entrenar)
como observaciones `cruzr_ball_live_observation_v1` a `shadow_live_inference.sh`
en Ada y compara la acción predicha (primer paso del bloque) con el objetivo
grabado del operador y con la referencia "no moverse" (objetivo = estado).
No usa el robot. Los sellos de articulación/mano se acotan a <= sello de imagen
porque el emparejamiento grabado admite ±80 ms y el servidor exige causalidad.

Uso:
  python3 -B scripts/vla/eval_heldout_with_shadow.py --segment DIR_SEGMENTO \
     --state-names-from CANDIDATE_MANIFEST --task "..." --runner ... --train ... \
     --checkpoint ... --pins-file pins.json [--output resultado.json]
"""
import argparse
import base64
import hashlib
import json
import math
from pathlib import Path
import shlex
import statistics as st
import subprocess
import sys

R_ARM = ['R_shoulder_pitch_joint', 'R_shoulder_roll_joint', 'R_shoulder_yaw_joint',
         'R_elbow_roll_joint', 'R_elbow_yaw_joint', 'R_wrist_pitch_joint', 'R_wrist_roll_joint']
RIGHT_HAND = ['right_thumb_swing', 'right_thumb_mcp', 'right_thumb_pip', 'right_index_mcp',
              'right_middle_mcp', 'right_ring_mcp', 'right_little_mcp']


def as_list(v):
    return json.loads(v) if isinstance(v, str) else v


def observations(segment, state_names, task):
    for line in (segment / 'candidate_targets.jsonl').open(encoding='utf-8'):
        r = json.loads(line)
        png = (segment / r['png_file']).read_bytes()
        img = r['image_source_ns']
        joint = min(r['whole_joint_source_ns'], img)
        hand = min(r['hand_state_source_ns'], img)
        yield r, {'schema': 'cruzr_ball_live_observation_v1', 'task': task, 'state_names': state_names,
                  'state27': as_list(r['state20']) + as_list(r['hand_right_position7']),
                  'image_source_ns': img, 'joint_source_ns': joint, 'hand_source_ns': hand,
                  'received_monotonic_ns': {'image': img, 'joint': joint, 'hand': hand},
                  'image_sha256': hashlib.sha256(png).hexdigest(),
                  'png_b64': base64.b64encode(png).decode()}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--segment', type=Path, required=True)
    p.add_argument('--state-names-from', type=Path, required=True,
                   help='manifest.json de candidate_targets (state20_names_by_source)')
    p.add_argument('--task', required=True)
    p.add_argument('--host', default='luisacuna@192.168.1.43')
    p.add_argument('--port', default='2649')
    p.add_argument('--runner', required=True)
    p.add_argument('--train', required=True)
    p.add_argument('--checkpoint', required=True)
    p.add_argument('--volume', default='cruzr-smolvla-ball-public-models-20261109')
    p.add_argument('--pins-file', required=True)
    p.add_argument('--output', type=Path)
    args = p.parse_args(argv)

    names20 = next(iter(json.loads(args.state_names_from.read_text())['state20_names_by_source'].values()))
    state_names = names20 + RIGHT_HAND
    idx = [names20.index(j) for j in R_ARM]
    pins = base64.b64encode(json.dumps(json.loads(Path(args.pins_file).read_text()), sort_keys=True).encode()).decode()
    rows = list(observations(args.segment, state_names, args.task))
    remote = ['bash', args.runner, args.train, args.volume, args.checkpoint, 'cuda', '20261110',
              str(len(rows)), pins]
    proc = subprocess.Popen(['ssh', '-T', '-p', args.port, '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
                             args.host, shlex.join(remote)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    payload = ''.join(json.dumps(o) + '\n' for _, o in rows)
    out, _ = proc.communicate(payload, timeout=600)
    events = [json.loads(l) for l in out.splitlines() if l.startswith('{')]
    preds = [e for e in events if e.get('event') == 'prediction']
    if proc.returncode != 0 or len(preds) != len(rows):
        print(json.dumps({'error': 'inferencia incompleta', 'rc': proc.returncode,
                          'predictions': len(preds), 'rows': len(rows), 'events': events[-3:]}), file=sys.stderr)
        return 1
    # El bloque i del modelo corresponde a la acción del fotograma +0,5*i s (2 Hz).
    # La acción grabada es la consigna simultánea (~estado), así que se compara
    # el bloque con el objetivo grabado en ese instante futuro, frente a "no moverse".
    times = [r['image_source_ns'] for r, _ in rows]
    horizons = {}
    for h in range(1, 5):
        m_err, s_err = [], []
        for i, ((r, _), e) in enumerate(zip(rows, preds)):
            if not e.get('chunk'):
                continue
            goal_ns = times[i] + int(h * 0.5e9)
            j = min(range(len(times)), key=lambda k: abs(times[k] - goal_ns))
            if abs(times[j] - goal_ns) > 0.15e9:
                continue
            future = as_list(rows[j][0]['experimental_joint_target7'])
            state = [as_list(r['state20'])[k] for k in idx]
            m_err.append(st.mean(abs(a - b) for a, b in zip(e['chunk'][h][:7], future)))
            s_err.append(st.mean(abs(a - b) for a, b in zip(state, future)))
        if m_err:
            horizons['%.1fs' % (h * 0.5)] = {'n': len(m_err), 'mae_model_rad': st.mean(m_err),
                                              'mae_stay_still_rad': st.mean(s_err),
                                              'model_better_fraction': sum(a < b for a, b in zip(m_err, s_err)) / len(m_err)}
    hand_ok = sum(int((e['prediction'][7] >= 0.5) == (r['experimental_hand_label'] == 1))
                  for (r, _), e in zip(rows, preds))
    result = {'segment': str(args.segment), 'samples': len(rows), 'horizons': horizons,
              'hand_accuracy': hand_ok / len(rows),
              'hand_label_closed_fraction': sum(r['experimental_hand_label'] == 1 for r, _ in rows) / len(rows),
              'model_sha256': next((e.get('model_sha256') for e in events if e.get('event') == 'ready'), None)}
    text = json.dumps(result, indent=2)
    print(text)
    if args.output:
        args.output.write_text(text + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
