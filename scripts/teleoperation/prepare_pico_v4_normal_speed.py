#!/usr/bin/env python3
"""Prepare a normal-speed derivative of an audited 2x v4 motion, without motion.

Only timestamps change, exactly by a factor of two. This script does not
validate the path, start the player or authorize a physical reproduction.
"""
import argparse
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
from scripts.hands.switch_effector import Transport
from scripts.teleoperation.pico_v4_bag_to_motion import ORDER
from scripts.teleoperation.prepare_pico_v4_geometric_replay import checked_hash, one_container


def digest_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def convert(slow_file, receipt_file, output, expected_slow_sha, expected_bag_sha):
    receipt = json.loads(Path(receipt_file).read_text())
    if (receipt.get('source_sha256') != expected_bag_sha or
            receipt.get('output_sha256') != expected_slow_sha or
            receipt.get('time_scale') != 2.0 or
            digest_file(slow_file) != expected_slow_sha):
        raise ValueError('Slow derivative or original capture provenance mismatch')
    with Path(slow_file).open() as stream:
        motion = json.load(stream)
    if set(motion) != {'robot', 'source', *ORDER} or motion['robot'] != 'Utars' or motion['source'] != 'utars_teleop':
        raise ValueError('Unexpected motion schema')
    slow_duration = receipt.get('duration_s')
    if not finite(slow_duration) or slow_duration <= 0:
        raise ValueError('Invalid source duration')
    rates = {}
    for group, names in ORDER.items():
        rows = motion[group]
        recorded = receipt.get('groups', {}).get(group, {})
        if recorded.get('names') != names or len(rows) != recorded.get('samples') or len(rows) < 2:
            raise ValueError('Invalid group metadata: ' + group)
        previous_t, previous_q = None, None
        max_rate = 0.0
        for row in rows:
            if set(row) != {'t', 'q'} or not finite(row['t']) or row['t'] < 0:
                raise ValueError('Invalid time in ' + group)
            q = row['q']
            if not isinstance(q, list) or len(q) != len(names) or not all(finite(v) for v in q):
                raise ValueError('Invalid positions in ' + group)
            t = row['t'] / 2.0
            if previous_t is not None:
                if t <= previous_t:
                    raise ValueError('Non-increasing timestamps in ' + group)
                max_rate = max(max_rate, max(abs(a-b) for a,b in zip(q, previous_q)) / (t-previous_t))
            previous_t, previous_q = t, q
            row['t'] = t
        if rows[0]['t'] != 0.0 or rows[-1]['t'] != slow_duration / 2.0:
            raise ValueError('Group does not span expected interval: ' + group)
        if rows[0]['q'] != recorded.get('initial_q') or rows[-1]['q'] != recorded.get('final_q'):
            raise ValueError('Endpoint mismatch in ' + group)
        rates[group] = max_rate
    with Path(output).open('x') as stream:
        json.dump(motion, stream, allow_nan=False, separators=(',', ':'))
    return {'source_bag_sha256': expected_bag_sha, 'source_slow_sha256': expected_slow_sha,
            'output_sha256': digest_file(output), 'duration_s': slow_duration / 2.0,
            'time_scale': 1.0, 'max_discrete_rate_rad_s': rates,
            'force_or_control_modes_reproduced': False, 'trajectory_validated': False,
            'playback_started': False}


def upload_new(source, remote_path):
    env = dict(os.environ, CRUZR_INTERNAL_ASKPASS='1',
               SSH_ASKPASS=str(ROOT/'scripts/cruzr_recover_to_home.sh'),
               SSH_ASKPASS_REQUIRE='force', DISPLAY=os.environ.get('DISPLAY', ':0'))
    script = 'set -o noclobber; cat > "$1"'
    remote = shlex.join(['bash', '-c', script, 'upload', remote_path])
    command = ['setsid', '-w', 'ssh', '-T', '-o', 'StrictHostKeyChecking=yes',
               '-o', 'ConnectTimeout=5', '-o', 'PreferredAuthentications=password',
               '-o', 'PubkeyAuthentication=no', '-o', 'NumberOfPasswordPrompts=1',
               'walker@192.168.11.2', remote]
    with Path(source).open('rb') as data:
        result = subprocess.run(command, stdin=data, capture_output=True, timeout=180, env=env)
    if result.returncode:
        raise RuntimeError('Upload failed; output directory may contain partial data')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--capture', required=True)
    p.add_argument('--bag-sha256', required=True)
    p.add_argument('--slow-sha256', required=True)
    p.add_argument('--slow-file', type=Path, required=True)
    p.add_argument('--slow-receipt', type=Path, required=True)
    args = p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.capture):
        p.error('Invalid capture name')
    if not all(re.fullmatch(r'[0-9a-f]{64}', x) for x in (args.bag_sha256, args.slow_sha256)):
        p.error('Expected lowercase SHA256 digests')
    run_id = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + uuid.uuid4().hex[:8]
    evidence = ROOT.parent/'Humanoide-vla-evidence'/('PICO-V4-NORMAL-DERIVATIVE-'+run_id)
    evidence.mkdir(parents=True, exist_ok=False)
    print('EVIDENCIA='+str(evidence), flush=True)
    t = Transport(evidence)
    remote_dirs_created = False
    try:
        output = evidence/'geometry_normal.motion'
        report = convert(args.slow_file, args.slow_receipt, output, args.slow_sha256, args.bag_sha256)
        t.save('conversion.json', report)
        inventory = t.run('motion', ['docker', 'ps', '--format', '{{.Names}}'], 20)
        ros = one_container(inventory, r'walker-ros\.ros2-\d+')
        app = one_container(inventory, r'walker-motion\.manipulation_robot_app-\d+')
        host_db = '/home/walker/grabaciones_v4_completas/'+args.capture+'/rosbag/rosbag_0.db3'
        ros_db = '/tmp/pico_v4_capture_'+args.capture+'/rosbag/rosbag_0.db3'
        checked_hash(t.run('motion', ['sha256sum', host_db], 45), args.bag_sha256, 'Host original')
        checked_hash(t.run('motion', ['docker', 'exec', ros, 'sha256sum', ros_db], 45), args.bag_sha256, 'ROS original')
        host_dir = '/home/walker/grabaciones_v4_completas/'+args.capture+'/derived_normal_'+run_id
        app_dir = '/tmp/pico_v4_app_normal_'+run_id
        host_file, app_file = host_dir+'/geometry_normal.motion', app_dir+'/geometry_normal.motion'
        t.run('motion', ['mkdir', host_dir], 15)
        remote_dirs_created = True
        upload_new(output, host_file)
        checked_hash(t.run('motion', ['sha256sum', host_file], 45), report['output_sha256'], 'Host derivative')
        t.run('motion', ['docker', 'exec', app, 'mkdir', app_dir], 15)
        t.run('motion', ['docker', 'cp', host_file, app+':'+app_file], 45)
        checked_hash(t.run('motion', ['docker', 'exec', app, 'sha256sum', app_file], 45), report['output_sha256'], 'App derivative')
        checked_hash(t.run('motion', ['sha256sum', host_db], 45), args.bag_sha256, 'Host original after conversion')
        checked_hash(t.run('motion', ['docker', 'exec', ros, 'sha256sum', ros_db], 45), args.bag_sha256, 'ROS original after conversion')
        result = dict(report, host_derivative=host_file, app_container=app, app_derivative=app_file,
                      pc_derivative=str(output))
        t.save('result.json', result)
        print(json.dumps(result, indent=2), flush=True)
        return 0
    except Exception as error:
        t.save('interrupted.json', {'error': str(error), 'remote_dirs_may_exist': remote_dirs_created,
                                    'playback_started': False})
        print('PREPARACION_INTERRUMPIDA: '+str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
