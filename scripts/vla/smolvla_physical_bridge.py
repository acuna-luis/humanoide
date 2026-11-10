#!/usr/bin/env python3
"""Puente mínimo SmolVLA -> brazo derecho físico (MetaMove), paso a paso.

Cadena: run_ball_live_shadow.py (cámara+estado reales -> inferencia en Ada)
-> recorte por articulación -> un XML MetaMove por paso en Motion ->
`rosa action send_goal` (misma vía que los scripts de cajas) -> registro JSONL.

Seguridad deliberadamente simple y revisable:
  * sólo brazo derecho, sin mano;
  * |delta| <= --max-step-rad por articulación y paso, duración >= 1 s;
  * envolvente: cada articulación queda a <= --envelope-rad de la postura inicial;
  * límites URDF con margen;
  * aborta si el estado observado se aleja del último objetivo > --jump-abort-rad;
  * Ctrl-C: detiene el bucle y pide cancel_goal (todas las metas) al servidor;
  * la protección real es la persona en el paro físico.

Modos: --dry-run (no envía nada), --step (Enter antes de cada paso),
por defecto continuo hasta --max-steps.
"""

import argparse
import base64
import json
import math
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import time

REPO = Path(__file__).resolve().parents[2]
EVIDENCE = REPO.parent / 'Humanoide-vla-evidence' / 'SMOLVLA_PHYSICAL_BRIDGE'
MOTION = 'walker@192.168.11.2'
APP = 'walker-motion.manipulation_robot_app-1'
ROS = 'walker-ros.ros2-1'
CONFIG = '/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config'
JOINTS = ['R_shoulder_pitch_joint', 'R_shoulder_roll_joint', 'R_shoulder_yaw_joint',
          'R_elbow_roll_joint', 'R_elbow_yaw_joint', 'R_wrist_pitch_joint', 'R_wrist_roll_joint']
# cruzr_s2_v1.urdf leído en Motion el 10-11-2026.
URDF_LIMITS = [(-2.8623, 2.8623), (-1.885, 0.1222), (-2.9322, 2.9322), (-2.6529, 0.0349),
               (-2.9322, 2.9322), (-1.658, 1.658), (-2.0245, 2.0245)]
# Posturas de dedos v4 medidas en la toma 2 (935-1008): abierta y sujetando la pelota.
HAND_OPEN = [0.8, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
HAND_CLOSED = [1.824, 0.737, 1.018, 1.638, 0.853, 0.76, 0.234]
# Postura PICO inicial del brazo derecho (igual en todas las demos del 10-11).
PICO_POSE = [0.0, -0.15, 1.57, -1.57, -2.88, 0.0, 0.0]
ADA = dict(host='luisacuna@192.168.1.43', port='2649',
           runner='/home/luisacuna/cruzr-smolvla-ball-20261109/live-shadow-20261109-2144/shadow_live_inference.sh',
           train='/home/luisacuna/cruzr-smolvla-ball-20261109/dataset-v2/lerobot-experiment',
           volume='cruzr-smolvla-ball-public-models-20261109',
           checkpoint='/home/luisacuna/cruzr-smolvla-ball-20261109/pilot-1000step/run/checkpoints/001000/pretrained_model')


# ---------------------------------------------------------------- lógica pura
def plan_step(prediction, diff, start, last_target, *, max_step, envelope, margin, jump_abort):
    """Devuelve (observado, objetivo, info). Lanza ValueError para abortar."""
    arm = [float(x) for x in prediction[:7]]
    obs = [p - float(d) for p, d in zip(arm, diff[:7])]
    if len(arm) != 7 or len(obs) != 7 or not all(map(math.isfinite, arm + obs)):
        raise ValueError('prediccion_invalida')
    tracking = None
    if last_target is not None:
        tracking = [o - t for o, t in zip(obs, last_target)]
        worst = max(map(abs, tracking))
        if worst > jump_abort:
            raise ValueError('estado_inesperado: |obs-objetivo|=%.3f rad' % worst)
    target, clipped = [], []
    for i, (o, a) in enumerate(zip(obs, arm)):
        d = max(-max_step, min(max_step, a - o))
        t = o + d
        t = max(start[i] - envelope, min(start[i] + envelope, t))
        lo, hi = URDF_LIMITS[i]
        t = max(lo + margin, min(hi - margin, t))
        target.append(t)
        clipped.append(abs(t - a) > 1e-9)
    info = {'model_delta': [a - o for a, o in zip(arm, obs)],
            'sent_delta': [t - o for t, o in zip(target, obs)],
            'clipped': clipped, 'tracking_error': tracking,
            'hand_scalar_ignored': float(prediction[7]) if len(prediction) > 7 else None}
    return obs, target, info


class HandGate:
    """Cierra sólo si el modelo pide cerrar `confirm` pasos seguidos y el brazo ya
    está cerca de su objetivo (max|delta modelo| < near); abre tras `confirm` pasos
    pidiendo abrir. Devuelve la nueva consigna ('open'/'closed') o None si no cambia."""
    def __init__(self, threshold, confirm, near):
        self.threshold, self.confirm, self.near = threshold, confirm, near
        self.state, self.votes = None, 0

    def update(self, scalar, model_delta):
        if self.state is None:
            self.state = 'open'
            return 'open'
        want = 'closed' if scalar >= self.threshold else 'open'
        # La proximidad sólo condiciona el cierre: una mano cerrada no se abre
        # porque el brazo se mueva (corrige aperturas del run 20261110T190321).
        if want == 'closed' and self.state == 'open' and max(map(abs, model_delta)) >= self.near:
            want = 'open'
        if want == self.state:
            self.votes = 0
            return None
        self.votes += 1
        if self.votes >= self.confirm:
            self.state, self.votes = want, 0
            return want
        return None


def step_xml(target, duration, hand=None):
    angles = ';'.join('%.6f' % x for x in target)
    arm = ('<Action ID="MetaMove" type="arm" location="right" joint_angles="%s" duration="%.3f" />'
           % (angles, duration))
    if hand is None:
        body = '      ' + arm + '\n'
    else:
        fingers = ';'.join('%.4f' % x for x in (HAND_CLOSED if hand == 'closed' else HAND_OPEN))
        body = ('      <Parallel threshold="2">\n        ' + arm + '\n        '
                '<Action ID="MetaMove" type="effector" location="right" eef_joint_commands="%s" '
                'duration="%.3f" />\n      </Parallel>\n' % (fingers, duration))
    return ('<root main_tree_to_execute="MainTree">\n  <BehaviorTree ID="MainTree">\n'
            '    <Sequence name="smolvla_step">\n' + body +
            '    </Sequence>\n  </BehaviorTree>\n</root>\n')


def plan_chunk(chunk, k, obs, start, *, max_step, envelope, margin, offset=0):
    """Objetivos para k acciones del bloque desde `offset`, recortando cada una
    respecto a la anterior (la primera respecto al estado observado).

    La acción grabada es la consigna simultánea a la observación (~estado), así
    que chunk[0] ~ "quedarse"; el movimiento está en chunk[1:] (+0,5 s cada uno)."""
    targets, prev = [], obs
    for action in chunk[offset:offset + k]:
        target = []
        for i, (p, a) in enumerate(zip(prev, action[:7])):
            t = p + max(-max_step, min(max_step, float(a) - p))
            t = max(start[i] - envelope, min(start[i] + envelope, t))
            lo, hi = URDF_LIMITS[i]
            target.append(max(lo + margin, min(hi - margin, t)))
        if not all(map(math.isfinite, target)):
            raise ValueError('chunk_invalido')
        targets.append(target)
        prev = target
    return targets


def arm_action(target, duration):
    return ('<Action ID="MetaMove" type="arm" location="right" joint_angles="%s" duration="%.3f" />'
            % (';'.join('%.6f' % x for x in target), duration))


def chunk_xml(targets, duration, hand=None):
    """Secuencia de MetaMove de brazo; la mano (si cambia) en paralelo con el primero."""
    moves = [arm_action(t, duration) for t in targets]
    if hand is not None:
        fingers = ';'.join('%.4f' % x for x in (HAND_CLOSED if hand == 'closed' else HAND_OPEN))
        moves[0] = ('<Parallel threshold="2">' + moves[0] +
                    '<Action ID="MetaMove" type="effector" location="right" eef_joint_commands="%s" '
                    'duration="%.3f" /></Parallel>' % (fingers, duration))
    return ('<root main_tree_to_execute="MainTree">\n  <BehaviorTree ID="MainTree">\n'
            '    <Sequence name="smolvla_chunk">\n' + ''.join('      %s\n' % m for m in moves) +
            '    </Sequence>\n  </BehaviorTree>\n</root>\n')


def setup_xml(head, arm_pose, duration):
    """Preparación antes de la política: cabeza (yaw, pitch), brazo y mano abierta."""
    actions = []
    if head is not None:
        actions.append('<Action ID="MetaMove" type="head" location="single" joint_angles="%.4f; %.4f" '
                       'duration="%.3f" />' % (head[0], head[1], duration))
    if arm_pose is not None:
        actions.append(arm_action(arm_pose, duration))
        actions.append('<Action ID="MetaMove" type="effector" location="right" eef_joint_commands="%s" '
                       'duration="%.3f" />' % (';'.join('%.4f' % x for x in HAND_OPEN), duration))
    return ('<root main_tree_to_execute="MainTree">\n  <BehaviorTree ID="MainTree">\n'
            '    <Parallel threshold="%d">\n' % len(actions) + ''.join('      %s\n' % a for a in actions) +
            '    </Parallel>\n  </BehaviorTree>\n</root>\n')


# ---------------------------------------------------------------- transporte
REMOTE_EXECUTOR = r'''
import json, os, subprocess, sys
root = sys.argv[1]
os.makedirs(root, exist_ok=True)
print(json.dumps({"event": "executor_ready"}), flush=True)
for line in sys.stdin:
    req = json.loads(line)
    path = os.path.join(root, req["name"] + ".xml")
    with open(path, "w") as f:
        f.write(req["xml"])
    goal = json.dumps({"task_name": req["task"], "yaml_args": "{}"})
    t0 = __import__("time").monotonic()
    try:
        p = subprocess.run(["rosa", "action", "send_goal", "/mc/manipulation/action",
                            "mc_task_msgs/action/ArmTask", goal],
                           capture_output=True, text=True, timeout=req["timeout"])
        out, rc = p.stdout + p.stderr, p.returncode
    except subprocess.TimeoutExpired as e:
        out, rc = str(e.stdout or "") + "TIMEOUT", -1
    ok = "'desc': 'SUCCEED'" in out and "status=4" in out
    print(json.dumps({"event": "step_result", "name": req["name"], "rc": rc, "succeed": ok,
                      "seconds": __import__("time").monotonic() - t0,
                      "tail": out[-600:]}), flush=True)
'''


class Motion:
    def __init__(self, askpass):
        self.env = dict(os.environ, SSH_ASKPASS=askpass, SSH_ASKPASS_REQUIRE='force',
                        DISPLAY=os.environ.get('DISPLAY', ':0'))
        self.base = ['setsid', '-w', 'ssh', '-T', '-o', 'ConnectTimeout=6', '-o', 'ServerAliveInterval=3',
                     '-o', 'ServerAliveCountMax=2', '-o', 'PreferredAuthentications=password',
                     '-o', 'PubkeyAuthentication=no', '-o', 'NumberOfPasswordPrompts=1',
                     '-o', 'StrictHostKeyChecking=yes', MOTION]

    def run(self, command, timeout=40):
        return subprocess.run(self.base + [command], env=self.env, capture_output=True,
                              text=True, timeout=timeout)

    def ros2(self, command, timeout=40):
        inner = 'source /opt/ros/humble/setup.bash; export ROS2CLI_DISABLE_DAEMON=1; ' + command
        return self.run('docker exec %s bash -lc %s' % (ROS, sh_quote(inner)), timeout)

    def executor(self, task_dir):
        code = base64.b64encode(REMOTE_EXECUTOR.encode()).decode()
        inner = ('set +u; source /opt/walker/setup.bash; exec python3 -u -c '
                 '"import base64;exec(base64.b64decode(\'%s\'))" %s' % (code, sh_quote(task_dir)))
        cmd = 'docker exec -i %s bash -c %s' % (APP, sh_quote(inner))
        return subprocess.Popen(self.base + [cmd], env=self.env, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, text=True, bufsize=1)

    def cancel_all(self):
        r = self.ros2("timeout 10 ros2 service call /mc/manipulation/action/_action/cancel_goal "
                      "action_msgs/srv/CancelGoal '{}'", timeout=25)
        return r.returncode, (r.stdout + r.stderr)[-400:]


def sh_quote(s):
    return "'" + s.replace("'", "'\"'\"'") + "'"


def preflight(motion):
    """Sólo lectura: paros, baterías, cargador, metas activas."""
    topics = ['/emb/estop_key_state', '/emb/servo_estop_key_state', '/emb/chrg_input_status',
              '/emb/battery_state', '/mc/manipulation/action/_action/status']
    cmd = '; '.join('echo "== %s"; timeout 6 ros2 topic echo --once %s' % (t, t) for t in topics)
    out = motion.ros2(cmd, timeout=60).stdout
    sections = {}
    for chunk in out.split('== ')[1:]:
        name, _, body = chunk.partition('\n')
        sections[name.strip()] = body
    import yaml
    val = lambda t: yaml.safe_load(sections[t].split('---')[0])
    estops = (val(topics[0])['data'], val(topics[1])['data'])
    charger = val(topics[2])['data']
    socs = [b['batsoc'] for b in val(topics[3])['batteries_states']]
    status = val(topics[4]) or {}
    active = [s['status'] for s in status.get('status_list', []) if s['status'] not in (4, 5, 6)]
    return {'estops': estops, 'charger': charger, 'battery_soc': socs, 'active_goals': active,
            'ok': estops == (0, 0) and min(socs) >= 30 and not active}


def read_arm_and_head(motion):
    """Sólo lectura de /mc/joint_states: (brazo derecho 7, (yaw, pitch) cabeza)."""
    import yaml
    out = motion.ros2('timeout 8 ros2 topic echo --once /mc/joint_states', timeout=40).stdout
    msg = yaml.safe_load(out.split('---')[0])
    pos = dict(zip(msg['name'], msg['position']))
    return [pos[j] for j in JOINTS], (pos['head_yaw_joint'], pos['head_pitch_joint'])


def start_shadow(args):
    cmd = [sys.executable, '-B', str(REPO / 'scripts/vla/run_ball_live_shadow.py'),
           '--host', ADA['host'], '--port', ADA['port'], '--runner', args.runner,
           '--train', args.train, '--volume', ADA['volume'], '--checkpoint', args.checkpoint,
           '--device', 'cuda', '--seconds', str(args.seconds), '--fps', str(args.fps),
           '--max-samples', str(args.seconds * 2 + 10), '--startup-timeout', '120']
    if args.pins_file:
        cmd += ['--pins-file', args.pins_file]
    proc = subprocess.Popen(cmd, cwd=REPO, stdout=subprocess.PIPE, text=True, bufsize=1)
    q = queue.Queue()

    def reader():
        for line in proc.stdout:
            try:
                q.put((time.monotonic(), json.loads(line)))
            except ValueError:
                q.put((time.monotonic(), {'event': 'unparsed', 'line': line[:200]}))
        q.put((time.monotonic(), {'event': 'shadow_eof'}))
    threading.Thread(target=reader, daemon=True).start()
    return proc, q


# ---------------------------------------------------------------- bucle
def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--dry-run', action='store_true', help='inferencia y plan, sin enviar metas')
    p.add_argument('--step', action='store_true', help='pedir Enter antes de cada paso')
    p.add_argument('--max-steps', type=int, default=20)
    p.add_argument('--max-step-rad', type=float, default=0.05)
    p.add_argument('--duration-s', type=float, default=1.0)
    p.add_argument('--envelope-rad', type=float, default=0.5)
    p.add_argument('--margin-rad', type=float, default=0.03)
    p.add_argument('--jump-abort-rad', type=float, default=0.15)
    p.add_argument('--settle-s', type=float, default=1.5,
                   help='sólo usar predicciones llegadas este tiempo después del fin del paso')
    p.add_argument('--fps', type=float, default=1.0)
    p.add_argument('--seconds', type=int, default=60, help='duración del shadow (1-60 s)')
    p.add_argument('--hand', action='store_true', help='controlar la mano v4 derecha (abrir/cerrar)')
    p.add_argument('--hand-threshold', type=float, default=0.5)
    p.add_argument('--hand-confirm', type=int, default=2)
    p.add_argument('--grasp-near-rad', type=float, default=0.15,
                   help='sólo cerrar si max|delta del modelo| < este valor')
    p.add_argument('--allow-charger', action='store_true', help='aceptar cargador conectado')
    p.add_argument('--train', default=ADA['train'], help='dataset de entrenamiento en Ada (estadísticas)')
    p.add_argument('--checkpoint', default=ADA['checkpoint'], help='checkpoint en Ada')
    p.add_argument('--runner', default=ADA['runner'], help='shadow_live_inference.sh en Ada')
    p.add_argument('--pins-file', help='JSON local con hashes esperados (checkpoint distinto del piloto)')
    p.add_argument('--chunk-steps', type=int, default=1,
                   help='acciones del bloque ejecutadas por paso (1-8); >1 usa --action-duration-s')
    p.add_argument('--chunk-offset', type=int, default=1,
                   help='primera acción del bloque a ejecutar (0 = la simultánea a la observación)')
    p.add_argument('--action-duration-s', type=float, default=0.5,
                   help='duración de cada acción del bloque (cadencia del dataset: 0,5 s a 2 Hz)')
    p.add_argument('--head-pose', help='YAW,PITCH de cabeza antes de empezar (p. ej. -0.49,-0.65)')
    p.add_argument('--start-pose', choices=('pico',), help='llevar el brazo a la postura PICO y abrir la mano antes')
    p.add_argument('--setup-duration-s', type=float, default=5.0)
    args = p.parse_args()
    if not 1 <= args.chunk_steps <= 8 or not 0 <= args.chunk_offset or args.chunk_offset + args.chunk_steps > 8:
        raise SystemExit('--chunk-offset + --chunk-steps debe caber en el bloque de 8')
    if args.chunk_steps > 1 and (args.action_duration_s < 0.5 or args.max_step_rad > 0.10):
        raise SystemExit('Con bloques: duración por acción >= 0,5 s y paso <= 0,10 rad')
    if not 1 <= args.seconds <= 240 or not .5 <= args.fps <= 2:
        raise SystemExit('--seconds debe estar en 1-240 y --fps en 0,5-2 (límites del shadow)')
    if args.duration_s < 1.0 or args.max_step_rad > 0.15 or args.envelope_rad > 1.5:
        raise SystemExit('Parámetros fuera del rango conservador (duración>=1 s, paso<=0,15 rad, envolvente<=1,5 rad)')

    run_id = time.strftime('%Y%m%dT%H%M%S')
    out_dir = EVIDENCE / ('run-' + run_id)
    out_dir.mkdir(parents=True, exist_ok=False)
    log_file = (out_dir / 'bridge.jsonl').open('w')

    def log(row):
        row = dict(row, t=time.time())
        log_file.write(json.dumps(row) + '\n'); log_file.flush()
        return row

    tmp = tempfile.mkdtemp(prefix='svla-askpass-')
    askpass = os.path.join(tmp, 'askpass.sh')
    with open(askpass, 'w') as f:
        f.write('#!/bin/sh\nexec python3 %s\n' % (REPO / 'scripts/lib/cruzr_ssh_askpass.py'))
    os.chmod(askpass, 0o700)
    motion = Motion(askpass)

    pre = log({'event': 'preflight', **preflight(motion), 'args': vars(args)})
    print('Preflight:', json.dumps({k: pre[k] for k in ('estops', 'charger', 'battery_soc', 'active_goals')}))
    if not pre['ok']:
        raise SystemExit('Preflight no superado; no se envía nada.')
    if pre['charger'] != 0 and not args.allow_charger and not args.dry_run:
        raise SystemExit('Cargador conectado o desconocido (%s); use --allow-charger si lo acepta.' % pre['charger'])

    task_rel = 'diagnostics/svla_' + run_id
    executor = None
    if not args.dry_run:
        executor = motion.executor(CONFIG + '/' + task_rel)
        ready = json.loads(executor.stdout.readline() or '{}')
        if ready.get('event') != 'executor_ready':
            raise SystemExit('Ejecutor remoto no disponible')

    head = tuple(float(x) for x in args.head_pose.split(',')) if args.head_pose else None
    if head is not None and (len(head) != 2 or not -0.8 <= head[0] <= 0.8 or not -0.7 <= head[1] <= 0.3):
        raise SystemExit('--head-pose fuera de rango (yaw ±0,8, pitch -0,7..0,3)')
    if head is not None or args.start_pose:
        arm_now, head_now = read_arm_and_head(motion)
        dev = max(abs(a - b) for a, b in zip(arm_now, PICO_POSE))
        log({'event': 'setup_state', 'arm': arm_now, 'head_yaw_pitch': head_now, 'max_dev_from_pico': dev})
        print('Estado actual: max|brazo-PICO|=%.3f rad, cabeza yaw/pitch=%.3f/%.3f' % (dev, *head_now))
        if args.start_pose and dev > 0.6:
            raise SystemExit('El brazo está a %.2f rad de la postura PICO (>0,6); llévelo cerca antes.' % dev)
        xml = setup_xml(head, PICO_POSE if args.start_pose else None, args.setup_duration_s)
        log({'event': 'setup_plan', 'xml': xml})
        if not args.dry_run:
            executor.stdin.write(json.dumps({'name': 'setup', 'task': task_rel + '/setup', 'xml': xml,
                                             'timeout': args.setup_duration_s + 15}) + '\n')
            executor.stdin.flush()
            result = json.loads(executor.stdout.readline() or '{"event":"executor_eof"}')
            log(dict(result, step='setup'))
            print('Preparación (cabeza/brazo/mano): %s en %.2f s' % (
                'SUCCEED' if result.get('succeed') else 'FALLO', result.get('seconds', -1)))
            if not result.get('succeed'):
                raise SystemExit('Preparación no completada: ' + str(result.get('tail', ''))[-300:])

    gate = HandGate(args.hand_threshold, args.hand_confirm, args.grasp_near_rad) if args.hand else None
    shadow, q = start_shadow(args)
    start = last_target = None
    steps, step_end = 0, 0.0
    ready_after = 0.0
    try:
        print('Esperando modelo en Ada…')
        waiting_enter = args.step and not args.dry_run
        while steps < args.max_steps:
            arrival, row = q.get(timeout=args.seconds + 180)
            if row.get('event') == 'shadow_eof':
                log({'event': 'shadow_eof'}); break
            if row.get('event') != 'prediction':
                log({'event': 'shadow', 'row': row})
                if row.get('event') == 'model_ready':
                    print('Modelo listo.')
                continue
            if waiting_enter:
                answer = input('Paso %d: Enter para usar la siguiente observación, q para salir: ' % (steps + 1))
                if answer.strip().lower() == 'q':
                    break
                waiting_enter, ready_after = False, time.monotonic()
                continue
            if arrival < max(step_end + args.settle_s, ready_after):
                continue
            pred = row['prediction']
            pred = json.loads(pred) if isinstance(pred, str) else pred
            obs, target, info = plan_step(pred, row['proposed_minus_observed_rad'],
                                          start or [p - d for p, d in zip(pred[:7], row['proposed_minus_observed_rad'])],
                                          last_target, max_step=args.max_step_rad,
                                          envelope=args.envelope_rad, margin=args.margin_rad,
                                          jump_abort=args.jump_abort_rad)
            if start is None:
                start = obs
                log({'event': 'start_pose', 'joints': JOINTS, 'obs': obs})
            name = 'step_%03d' % steps
            chunk = row.get('chunk') if args.chunk_steps > 1 else None
            if args.chunk_steps > 1 and not chunk:
                raise ValueError('el servidor no devuelve bloque (chunk); actualice shadow_live_inference.py en Ada')
            targets = plan_chunk(chunk, args.chunk_steps, obs, start, max_step=args.max_step_rad,
                                 envelope=args.envelope_rad, margin=args.margin_rad,
                                 offset=args.chunk_offset) if chunk else [target]
            target = targets[-1]
            window = chunk[args.chunk_offset:args.chunk_offset + args.chunk_steps] if chunk else None
            hand_scalar = (sum(a[7] for a in window) / len(window)
                           if chunk else info['hand_scalar_ignored'])
            hand = gate.update(hand_scalar, info['model_delta']) if gate else None
            log({'event': 'plan', 'hand_command': hand, 'hand_state': gate.state if gate else None, 'step': steps, 'index': row.get('index'),
                 'image_sha256': row.get('image_sha256'), 'obs': obs, 'target': target,
                 'targets': targets, 'hand_scalar': hand_scalar, **info})
            print('%s modelo Δ=%s  enviado Δ=%s  mano=%.2f%s' % (
                name, ['%+.3f' % x for x in info['model_delta']], ['%+.3f' % x for x in info['sent_delta']],
                hand_scalar, (' -> ' + hand.upper()) if hand else ''))
            if args.dry_run:
                steps += 1; step_end = arrival
                continue
            executor.stdin.write(json.dumps({'name': name, 'task': task_rel + '/' + name,
                                             'xml': (chunk_xml(targets, args.action_duration_s, hand) if chunk
                                                     else step_xml(target, args.duration_s, hand)),
                                             'timeout': (args.action_duration_s * len(targets) if chunk
                                                         else args.duration_s) + 12}) + '\n')
            executor.stdin.flush()
            result = json.loads(executor.stdout.readline() or '{"event":"executor_eof"}')
            step_end = time.monotonic()
            log(dict(result, step=steps))
            print('   -> %s en %.2f s' % ('SUCCEED' if result.get('succeed') else 'FALLO', result.get('seconds', -1)))
            if not result.get('succeed'):
                raise ValueError('meta no completada: ' + str(result.get('tail', ''))[-200:])
            last_target = target
            steps += 1
            waiting_enter = args.step
        log({'event': 'finished', 'steps': steps})
        print('Terminado: %d pasos. Registro: %s' % (steps, out_dir / 'bridge.jsonl'))
    except (KeyboardInterrupt, ValueError, queue.Empty) as error:
        log({'event': 'abort', 'reason': repr(error)})
        print('\nABORT: %r' % (error,))
        if not args.dry_run:
            rc, out = motion.cancel_all()
            log({'event': 'cancel_all', 'rc': rc, 'out': out})
            print('cancel_goal rc=%s' % rc)
    finally:
        if executor:
            try:
                executor.stdin.close()
            except OSError:
                pass
            try:
                executor.wait(timeout=15)
            except subprocess.TimeoutExpired:
                executor.kill()
        if shadow.poll() is None:
            shadow.send_signal(2)
            try:
                shadow.wait(timeout=30)
            except subprocess.TimeoutExpired:
                shadow.kill()
        os.remove(askpass); os.rmdir(tmp)
        log_file.close()


if __name__ == '__main__':
    main()
