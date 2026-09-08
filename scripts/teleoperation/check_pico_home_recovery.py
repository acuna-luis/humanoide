#!/usr/bin/env python3
"""Captura sólo lectura para evaluar recuperación PICO→HOME; NO mueve el robot."""
import argparse
import concurrent.futures
import datetime
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'scripts/lib'),
                str(ROOT / 'scripts/vla/runtime')]
from collect_estop_available_readonly import execute, ros
from cruzr_home_posture_gate import classify as home_gate
from cruzr_s2_vla_ready_state_gate import classify as ready_gate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', required=True)
    parser.parse_args()
    out = ROOT.parent / 'Humanoide-vla-evidence' / (
        datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        + '_PICO-HOME-CHECK')
    out.mkdir(parents=True, exist_ok=False)
    def read(key, command):
        result = execute('motion', command)
        (out / (key + '.json')).write_text(json.dumps(result, indent=2) + '\n')
        if result.get('returncode') != 0:
            raise ValueError('Lectura incompleta: ' + key)
        return result['stdout']
    inventory = read('containers', ['docker', 'ps', '--format', '{{.Names}}'])
    def container(fragment):
        matches = [n for n in inventory.splitlines() if fragment in n and n.rsplit(fragment, 1)[1].isdigit()]
        if len(matches) != 1:
            raise ValueError('Contenedor no inequívoco: ' + fragment)
        return matches[0]
    motion = container('motion.manipulation_robot_app-')
    native_ros = container('walker-ros.ros2-')
    queries = {
        'actuators': ros(motion, 'rosa topic echo --once --no-daemon /mc/actuator_state', True),
        'joints': ros(motion, 'rosa topic echo --once --no-daemon /mc/whole_joint_states', True),
        'action-status': ros(native_ros, 'ros2 topic echo --once --no-daemon /mc/manipulation/action/_action/status'),
    }
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        jobs = {k: pool.submit(read, k, c) for k, c in queries.items()}
        samples = {k: f.result() for k, f in jobs.items()}
    home = home_gate(json.loads(samples['actuators']), .02)
    contract = json.loads((ROOT / 'scripts/vla/runtime/cruzr_s2_vla_sdk_transport_contract_e6_0r.json').read_text())
    joints = json.loads(samples['joints'])
    ready = ready_gate(joints, contract, ready_tolerance=.01, velocity_tolerance=.01)
    positions = dict(zip(joints['name'], joints['position']))
    body_ready = all(abs(positions[n] - (-.65 if n == 'head_pitch_joint' else 0)) < .01
                     for n in contract['locked_joint_names'])
    state = ('HOME' if 'MEASURED_HOME=1' in home else
             'READY' if 'MEASURED_READY=1' in ready and body_ready else 'OTHER')
    report = {'measured_posture': state, 'home_gate': home, 'ready_arm_gate': ready,
              'ready_body_gate': body_ready, 'motion_authorized': False,
              'trajectory_available_from_this_check': False,
              'scope': 'Point samples only; no physical clearance, active-control or route approval.'}
    (out / 'assessment.json').write_text(json.dumps(report, indent=2) + '\n')
    print('POSTURA_MEDIDA=' + state)
    print('MOVIMIENTOS_ENVIADOS=0')
    print('EVIDENCIA=' + str(out))
    if state == 'OTHER':
        print('RECUPERACION_PENDIENTE: hace falta una trayectoria revisada desde esta postura.')
    else:
        print('CLASIFICACION_SOLAMENTE: no autoriza una trayectoria ni reanudar control.')
    return 0 if state == 'HOME' else 3


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print('DIAGNOSTICO_INCOMPLETO: ' + str(exc), file=sys.stderr)
        raise SystemExit(2)
