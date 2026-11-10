#!/usr/bin/env python3
"""Preparación y prueba pasiva de la tarea fija de cabeza desde PICO v4.

--check consulta el robot y supervisa telemetría; no crea un cliente de control.
--run está bloqueado antes de cualquier conexión: PICO/v4, modo y parada aún no
están cualificados. El paso de la revisión no autoriza movimiento.
"""
import argparse
import ast
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from collect_estop_available_readonly import execute, ros

TASK_PATH = '/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/cruzr/move_head_lower.xml'
TASK_SHA = 'f3a73626f97b471d4a0a03c98c24de32243651116c497328e69b5ddc57ea46c1'
PICO_CONFIG = '/opt/walker/manipulation_meta_tasks/share/manipulation_meta_tasks/config/meta_teleoperation/cruzr_v4_pico_tele.yaml'
PICO_SHA = '01a5ca8acba16bbe136a3bdbcb4a593667d672f8ee9613b98631699fc429b582'
RUNTIME = ROOT / 'scripts/vla/runtime'


def parse_containers(result):
    if result.get('returncode') != 0:
        raise ValueError('container_discovery_failed')
    names = result.get('stdout', '').splitlines()
    def exactly_one(pattern):
        matches = [x for x in names if re.fullmatch(pattern, x)]
        if len(matches) != 1:
            raise ValueError('container_not_unique:' + pattern)
        return matches[0]
    return (exactly_one(r'walker-motion\.manipulation_robot_app-1'),
            exactly_one(r'walker-ros\.ros2-1'))


def controller_states(text):
    match = re.search(r'response:.*?Response\(controller=(\[.*\])\)', text, re.S)
    if not match:
        raise ValueError('controller_response_invalid')
    try:
        data = ast.literal_eval(match.group(1))
    except (ValueError, SyntaxError) as exc:
        raise ValueError('controller_response_invalid') from exc
    if not isinstance(data, list) or any(not isinstance(x, dict) for x in data):
        raise ValueError('controller_response_invalid')
    result = {}
    for item in data:
        name, state = item.get('name'), item.get('state')
        if not isinstance(name, str) or name in result or not isinstance(state, str):
            raise ValueError('controller_response_invalid')
        result[name] = state
    for name, expected in {'manipulation_controller': 'running',
                           'dexterous_hand_controller': 'running',
                           'vla_sdk_controller': 'initialized',
                           'sdk_controller': 'initialized'}.items():
        if result.get(name) != expected:
            raise ValueError('controller_not_expected:' + name)
    return result


def action_status(text):
    import yaml
    try:
        rows = [x for x in yaml.safe_load_all(text) if x is not None]
    except yaml.YAMLError as exc:
        raise ValueError('action_status_invalid') from exc
    if len(rows) != 1 or not isinstance(rows[0], dict):
        raise ValueError('action_status_invalid')
    statuses = rows[0].get('status_list')
    if not isinstance(statuses, list) or any(not isinstance(x, dict) or
            type(x.get('status')) is not int or x['status'] not in (4, 5, 6) for x in statuses):
        raise ValueError('action_active_or_unknown')


def check():
    m, r = parse_containers(execute('motion', ['docker', 'ps', '--format', '{{.Names}}']))
    queries = {
        'xml': ['docker', 'exec', m, 'sha256sum', TASK_PATH],
        'pico_config': ['docker', 'exec', m, 'sha256sum', PICO_CONFIG],
        'controllers': ros(m, "rosa service call --no-daemon /mc/controller_manager/list_controllers rosa_control_msgs/srv/ListControllers '{}'", True),
        'writers': ros(m, 'rosa topic info /mc/sdk/robot_command', True),
        'action_status': ros(r, 'ros2 topic echo --once --no-daemon /mc/manipulation/action/_action/status'),
    }
    reads = {name: execute('motion', cmd) for name, cmd in queries.items()}
    if any(x.get('returncode') != 0 for x in reads.values()):
        raise ValueError('read_only_inventory_incomplete')
    if reads['xml'].get('stdout', '').split()[:1] != [TASK_SHA]:
        raise ValueError('installed_head_task_hash_mismatch')
    if reads['pico_config'].get('stdout', '').split()[:1] != [PICO_SHA]:
        raise ValueError('installed_pico_v4_configuration_hash_mismatch')
    controller_states(reads['controllers'].get('stdout', ''))
    if not re.search(r'^Writer count:\s*0\s*$', reads['writers'].get('stdout', ''), re.M):
        raise ValueError('sdk_writer_present_or_unknown')
    action_status(reads['action_status'].get('stdout', ''))

    # Load the existing stop-monitor functions in memory, then stream the new
    # read-only observer to Motion. Neither is copied onto the robot.
    old = (RUNTIME / 'metamove_head_probe.py').read_text(encoding='utf-8')
    observer = (RUNTIME / 'head_from_pico_readonly.py').read_text(encoding='utf-8')
    code = ('import sys,types\n'
            'm=types.ModuleType("metamove_head_probe")\n'
            'exec(' + repr(old) + ',m.__dict__)\n'
            'sys.modules["metamove_head_probe"]=m\n' + observer)
    shell = 'source /opt/ros/humble/setup.bash; export ROS2CLI_DISABLE_DAEMON=1; exec timeout 35 python3 -B -u -'
    remote = ['docker', 'exec', '-i', r, 'bash', '-lc', shell]
    command = ['setsid', '-w', 'ssh', '-T', '-o', 'StrictHostKeyChecking=yes',
               '-o', 'ConnectTimeout=5', '-o', 'PreferredAuthentications=password',
               '-o', 'PubkeyAuthentication=no', '-o', 'NumberOfPasswordPrompts=1',
               'walker@192.168.11.2', shlex.join(remote)]
    env = dict(os.environ, CRUZR_INTERNAL_ASKPASS='1',
               SSH_ASKPASS=str(ROOT / 'scripts/cruzr_recover_to_home.sh'),
               SSH_ASKPASS_REQUIRE='force', DISPLAY=os.environ.get('DISPLAY', ':0'))
    result = subprocess.run(command, input=code, text=True, capture_output=True, timeout=42, env=env)
    print(result.stdout, end='')
    if result.stderr:
        print(result.stderr, end='', file=sys.stderr)
    if result.returncode:
        raise ValueError('passive_monitor_failed')
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true', help='solo lectura y suscripción temporal')
    mode.add_argument('--run', action='store_true', help='reservado, bloqueado antes de conectar')
    args = parser.parse_args(argv)
    if args.run:
        print('BLOQUEADO: ejecución PICO/v4, modo y parada no cualificados; no conectado.', file=sys.stderr)
        return 2
    try:
        return check()
    except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
        print('CHECK_FAILED: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
