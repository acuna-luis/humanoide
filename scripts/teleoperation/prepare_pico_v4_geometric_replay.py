#!/usr/bin/env python3
"""Inspect and stage a v4 capture as a geometric .motion; never moves the robot.

Runs the separately versioned inspector/converter inside the ROS container, then
copies the derivative through a new host directory into the Motion app. This
does not validate the trajectory or authorize an SDK player invocation.
"""
import argparse
import base64
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.hands.switch_effector import Transport, json_message

HELPERS = {
    'inspect_pico_v4_bag.py': '9305b7b5a31f566faba590e989eb5b84c78993743fc6dcf90a9b710f223eab1a',
    'pico_v4_bag_to_motion.py': '8a4ef2de522e012d6c05985190a641bb08d75900477d39f5993e892dc7da9d7d',
}


def one_container(inventory, pattern):
    found = [name for name in inventory.splitlines() if re.fullmatch(pattern, name)]
    if len(found) != 1:
        raise ValueError('Missing or ambiguous running container: ' + pattern)
    return found[0]


def checked_hash(output, expected, label):
    fields = output.strip().split()
    if not fields or fields[0] != expected:
        raise ValueError(label + ' SHA256 mismatch')
    return fields[0]


def staging_paths(capture, run_id):
    # The ROS and app containers may share /tmp: use distinct directory names.
    return ('/tmp/pico_v4_ros_derivative_' + run_id,
            '/home/walker/grabaciones_v4_completas/' + capture + '/derived_' + run_id,
            '/tmp/pico_v4_app_derivative_' + run_id)


def helper_command(source, args):
    # Send reviewed source by value; no helper code is installed on the robot.
    encoded = base64.b64encode(source).decode('ascii')
    arguments = ' '.join(shlex.quote(str(x)) for x in args)
    return ('source /opt/ros/humble/setup.bash; export ROS2CLI_DISABLE_DAEMON=1; '
            'exec python3 -c "$(printf %s ' + shlex.quote(encoded) + ' | base64 -d)" ' + arguments)


def copy_remote_file_to_pc(container, remote_path, destination, expected_sha):
    env = dict(os.environ, CRUZR_INTERNAL_ASKPASS='1',
               SSH_ASKPASS=str(ROOT / 'scripts/cruzr_recover_to_home.sh'),
               SSH_ASKPASS_REQUIRE='force', DISPLAY=os.environ.get('DISPLAY', ':0'))
    command = shlex.join(['docker', 'exec', container, 'cat', remote_path])
    ssh = ['setsid', '-w', 'ssh', '-T', '-o', 'StrictHostKeyChecking=yes',
           '-o', 'ConnectTimeout=5', '-o', 'PreferredAuthentications=password',
           '-o', 'PubkeyAuthentication=no', '-o', 'NumberOfPasswordPrompts=1',
           'walker@192.168.11.2', command]
    with destination.open('xb') as output:
        result = subprocess.run(ssh, env=env, stdout=output, stderr=subprocess.PIPE, timeout=180)
    if result.returncode:
        raise RuntimeError('SSH copy to PC failed (status %s)' % result.returncode)
    digest = hashlib.sha256()
    with destination.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    if digest.hexdigest() != expected_sha:
        raise ValueError('PC derivative SHA256 mismatch')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', required=True, help='capture directory name, without a path')
    parser.add_argument('--sha256', required=True, help='expected SHA256 of the closed SQLite database')
    parser.add_argument('--time-scale', type=float, default=2.0,
                        help='time multiplier (>=2; default 2)')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.capture):
        parser.error('capture must contain only letters, numbers, _ and -')
    if not re.fullmatch(r'[0-9a-f]{64}', args.sha256):
        parser.error('sha256 must be 64 lowercase hexadecimal characters')
    if not math.isfinite(args.time_scale) or args.time_scale < 2:
        parser.error('time-scale must be finite and >=2')

    helpers = {}
    for name, expected in HELPERS.items():
        data = (ROOT / 'scripts/teleoperation' / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('Unreviewed helper: ' + name)
        helpers[name] = data

    run_id = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + uuid.uuid4().hex[:8]
    evidence = ROOT.parent / 'Humanoide-vla-evidence' / ('PICO-V4-DERIVATIVE-' + run_id)
    evidence.mkdir(parents=True, exist_ok=False)
    print('EVIDENCIA=' + str(evidence), flush=True)
    t = Transport(evidence)
    requested = False
    try:
        inventory = t.run('motion', ['docker', 'ps', '--format', '{{.Names}}'], 20)
        ros = one_container(inventory, r'walker-ros\.ros2-\d+')
        app = one_container(inventory, r'walker-motion\.manipulation_robot_app-\d+')
        host_bag = '/home/walker/grabaciones_v4_completas/' + args.capture + '/rosbag'
        ros_bag = '/tmp/pico_v4_capture_' + args.capture + '/rosbag'
        host_db, ros_db = host_bag + '/rosbag_0.db3', ros_bag + '/rosbag_0.db3'
        checked_hash(t.run('motion', ['sha256sum', host_db], 45), args.sha256, 'Host original')
        checked_hash(t.run('motion', ['docker', 'exec', ros, 'sha256sum', ros_db], 45), args.sha256, 'ROS original')
        inspect = t.run('motion', ['docker', 'exec', ros, 'bash', '-lc',
                        helper_command(helpers['inspect_pico_v4_bag.py'], [ros_bag])], 180)
        inspect_data = json_message(inspect)
        if inspect_data.get('sha256') != args.sha256 or inspect_data.get('replay_validated') is not False:
            raise ValueError('Inspector result invalid')
        t.save('inspection.json', inspect_data)

        # Only new directories are created. No existing recording is replaced.
        scratch, host_dir, app_dir = staging_paths(args.capture, run_id)
        filename = 'geometry_slow.motion'
        requested = True
        t.run('motion', ['docker', 'exec', ros, 'mkdir', scratch], 15)
        convert = t.run('motion', ['docker', 'exec', ros, 'bash', '-lc',
                        helper_command(helpers['pico_v4_bag_to_motion.py'],
                                       [ros_db, scratch + '/' + filename, '--time-scale',
                                        str(args.time_scale), '--expected-sha256', args.sha256])], 180)
        report = json_message(convert)
        derived_sha = report.get('output_sha256', '')
        if report.get('source_sha256') != args.sha256 or not re.fullmatch(r'[0-9a-f]{64}', derived_sha):
            raise ValueError('Converter result invalid')
        t.save('conversion.json', report)
        checked_hash(t.run('motion', ['docker', 'exec', ros, 'sha256sum', scratch + '/' + filename], 45),
                     derived_sha, 'ROS derivative')
        t.run('motion', ['mkdir', host_dir], 15)
        t.run('motion', ['docker', 'cp', ros + ':' + scratch + '/' + filename, host_dir + '/' + filename], 45)
        checked_hash(t.run('motion', ['sha256sum', host_dir + '/' + filename], 45), derived_sha, 'Host derivative')
        t.run('motion', ['docker', 'exec', app, 'mkdir', app_dir], 15)
        t.run('motion', ['docker', 'cp', host_dir + '/' + filename, app + ':' + app_dir + '/' + filename], 45)
        checked_hash(t.run('motion', ['docker', 'exec', app, 'sha256sum', app_dir + '/' + filename], 45),
                     derived_sha, 'Motion app derivative')
        pc_derivative = evidence / filename
        copy_remote_file_to_pc(app, app_dir + '/' + filename, pc_derivative, derived_sha)
        # Verify both originals again after the entire operation.
        checked_hash(t.run('motion', ['sha256sum', host_db], 45), args.sha256, 'Host original after conversion')
        checked_hash(t.run('motion', ['docker', 'exec', ros, 'sha256sum', ros_db], 45), args.sha256, 'ROS original after conversion')
        result = {'capture': args.capture, 'source_sha256': args.sha256, 'ros_container': ros,
                  'app_container': app, 'time_scale': args.time_scale, 'derived_sha256': derived_sha,
                  'host_derivative': host_dir + '/' + filename,
                  'app_derivative': app_dir + '/' + filename,
                  'pc_derivative': str(pc_derivative),
                  'trajectory_validated': False, 'playback_started': False}
        t.save('result.json', result)
        print(json.dumps(result, indent=2), flush=True)
        return 0
    except Exception as error:
        t.save('interrupted.json', {'error': str(error), 'scratch_may_exist': requested,
                                    'playback_started': False})
        print('PREPARACION_INTERRUMPIDA: ' + str(error) + '; revisar evidencia antes de reintentar.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
