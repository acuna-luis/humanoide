#!/usr/bin/env python3
"""Prepare a time-trimmed v4 motion without commanding the robot.

All groups share the same cutoff. The last recorded position at or before the
cut is retained at t=0; later points retain their positions and relative times.
The first interval uses a held recorded position and is not certified to match
the vendor player's interpolation. A result is not permission to replay.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
import re
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.hands.switch_effector import Transport
from scripts.teleoperation.pico_v4_bag_to_motion import ORDER
from scripts.teleoperation.prepare_pico_v4_geometric_replay import checked_hash, one_container
from scripts.teleoperation.prepare_pico_v4_normal_speed import digest_file, finite, upload_new


def trim(source, receipt_file, output, expected_sha, expected_bag_sha, cut):
    if not finite(cut) or cut <= 0:
        raise ValueError('Cut must be finite and positive')
    source = Path(source)
    receipt = json.loads(Path(receipt_file).read_text())
    if (digest_file(source) != expected_sha or receipt.get('output_sha256') != expected_sha
            or receipt.get('source_bag_sha256') != expected_bag_sha
            or receipt.get('time_scale') != 1.0):
        raise ValueError('Source motion or capture provenance mismatch')
    motion = json.loads(source.read_text())
    if (set(motion) != {'robot', 'source', *ORDER} or motion['robot'] != 'Utars'
            or motion['source'] != 'utars_teleop'):
        raise ValueError('Unexpected motion schema')
    duration = receipt.get('duration_s')
    if not finite(duration) or not 0 < cut < duration:
        raise ValueError('Cut outside source duration')
    output_motion = {'robot': motion['robot'], 'source': motion['source']}
    groups = {}
    for group, names in ORDER.items():
        rows = motion[group]
        if not isinstance(rows, list) or len(rows) < 2:
            raise ValueError('Missing samples: ' + group)
        prior = None
        later = []
        last_t = None
        for row in rows:
            if not isinstance(row, dict) or set(row) != {'t', 'q'}:
                raise ValueError('Invalid sample: ' + group)
            t, q = row['t'], row['q']
            if (not finite(t) or t < 0 or (last_t is not None and t <= last_t)
                    or not isinstance(q, list) or len(q) != len(names)
                    or not all(finite(v) for v in q)):
                raise ValueError('Invalid time or positions: ' + group)
            if t <= cut:
                prior = row
            else:
                later.append({'t': t - cut, 'q': q[:]})
            last_t = t
        if rows[0]['t'] != 0.0 or last_t != duration or prior is None or not later:
            raise ValueError('Incomplete time interval: ' + group)
        first_gap = later[0]['t']
        first_delta = max(abs(a-b) for a, b in zip(prior['q'], later[0]['q']))
        new_rows = [{'t': 0.0, 'q': prior['q'][:]}] + later
        output_motion[group] = new_rows
        groups[group] = {
            'names': names, 'samples': len(new_rows),
            'held_sample_original_time_s': prior['t'],
            'held_sample_age_s': cut - prior['t'],
            'first_following_delay_s': first_gap,
            'first_following_max_delta_rad': first_delta,
            'initial_q': prior['q'], 'final_q': rows[-1]['q'],
        }
    if digest_file(source) != expected_sha:
        raise ValueError('Source changed during trim')
    with Path(output).open('x') as stream:
        json.dump(output_motion, stream, allow_nan=False, separators=(',', ':'))
    return {
        'source_sha256': expected_sha, 'source_bag_sha256': expected_bag_sha,
        'output_sha256': digest_file(output), 'cut_s': cut,
        'duration_s': duration - cut, 'time_scale': 1.0, 'groups': groups,
        'initial_sample_method': 'last recorded sample at or before cut, held to first subsequent sample',
        'vendor_interpolation_equivalence_validated': False,
        'force_or_control_modes_reproduced': False,
        'trajectory_validated': False, 'playback_started': False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--capture', required=True)
    p.add_argument('--bag-sha256', required=True)
    p.add_argument('--motion-sha256', required=True)
    p.add_argument('--motion', type=Path, required=True)
    p.add_argument('--receipt', type=Path, required=True)
    p.add_argument('--cut', type=float, required=True)
    args = p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.capture):
        p.error('Invalid capture name')
    if not all(re.fullmatch(r'[0-9a-f]{64}', x) for x in (args.bag_sha256, args.motion_sha256)):
        p.error('Expected lowercase SHA256 digests')
    if not finite(args.cut) or args.cut <= 0:
        p.error('Cut must be finite and positive')
    run_id = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + uuid.uuid4().hex[:8]
    evidence = ROOT.parent/'Humanoide-vla-evidence'/('PICO-V4-TRIMMED-DERIVATIVE-'+run_id)
    evidence.mkdir(parents=True, exist_ok=False)
    print('EVIDENCIA='+str(evidence), flush=True)
    t = Transport(evidence)
    remote_dirs_created = False
    try:
        output = evidence/'geometry_trimmed.motion'
        report = trim(args.motion, args.receipt, output, args.motion_sha256, args.bag_sha256, args.cut)
        t.save('conversion.json', report)
        inventory = t.run('motion', ['docker', 'ps', '--format', '{{.Names}}'], 20)
        ros = one_container(inventory, r'walker-ros\.ros2-\d+')
        app = one_container(inventory, r'walker-motion\.manipulation_robot_app-\d+')
        host_db = '/home/walker/grabaciones_v4_completas/'+args.capture+'/rosbag/rosbag_0.db3'
        ros_db = '/tmp/pico_v4_capture_'+args.capture+'/rosbag/rosbag_0.db3'
        checked_hash(t.run('motion', ['sha256sum', host_db], 45), args.bag_sha256, 'Host original')
        checked_hash(t.run('motion', ['docker', 'exec', ros, 'sha256sum', ros_db], 45), args.bag_sha256, 'ROS original')
        host_dir = '/home/walker/grabaciones_v4_completas/'+args.capture+'/derived_trimmed_'+run_id
        app_dir = '/tmp/pico_v4_app_trimmed_'+run_id
        host_file, app_file = host_dir+'/geometry_trimmed.motion', app_dir+'/geometry_trimmed.motion'
        t.run('motion', ['mkdir', host_dir], 15)
        remote_dirs_created = True
        upload_new(output, host_file)
        checked_hash(t.run('motion', ['sha256sum', host_file], 45), report['output_sha256'], 'Host derivative')
        t.run('motion', ['docker', 'exec', app, 'mkdir', app_dir], 15)
        t.run('motion', ['docker', 'cp', host_file, app+':'+app_file], 45)
        checked_hash(t.run('motion', ['docker', 'exec', app, 'sha256sum', app_file], 45), report['output_sha256'], 'App derivative')
        checked_hash(t.run('motion', ['sha256sum', host_db], 45), args.bag_sha256, 'Host original after trim')
        checked_hash(t.run('motion', ['docker', 'exec', ros, 'sha256sum', ros_db], 45), args.bag_sha256, 'ROS original after trim')
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
