#!/usr/bin/env python3
"""Run on Motion via SSH: check by default, one tiny empty-arm SDK test with --run.

Requires separate onsite physical authorization. Does not change modes, guards,
limits or vendor tasks. The operator and native protections remain responsible
for stopping: accompanying telemetry is passive, not an active safety guard.
No retry and no HOME action, including after interruption.
"""
import argparse
import concurrent.futures
import datetime
import hashlib
import json
import math
from pathlib import PurePosixPath
import re
import shlex
import subprocess
import time

SUFFIXES = ('shoulder_pitch', 'shoulder_roll', 'shoulder_yaw', 'elbow_roll',
            'elbow_yaw', 'wrist_pitch', 'wrist_roll')
ORDERS = {'head': ('head_yaw_joint', 'head_pitch_joint'),
          'left_arm': tuple('L_'+n+'_joint' for n in SUFFIXES),
          'right_arm': tuple('R_'+n+'_joint' for n in SUFFIXES),
          'lifter': ('lifter_pitch_1_joint', 'lifter_pitch_2_joint', 'lifter_pitch_3_joint'),
          'waist': ('waist_yaw_joint',)}
NATIVE = {'right': (.315, -.484, 1.910, -1.503, .697, .362, .142),
          'left': (-.315, -.484, -1.910, -1.503, -.697, -.362, .142)}
CONTRACT = {
    '/opt/walker/manipulation_outline_sdk/lib/manipulation_outline_sdk/player':
        '8744a30ecce20c414dcf67b60d9aa7ac486bab752d5eee3de08a7336d65ddf0d',
    '/opt/walker/manipulation_outline_sdk/share/manipulation_outline_sdk/config/motion_sdk/joint_order/utars_joints.yaml':
        '7f9d7975ebd27774e5248afa666a71ecaeb24bad30a234c9af2b81abc321f39c',
    '/opt/walker/manipulation_platforms/share/manipulation_platforms/config/urdf/cruzr_s2.urdf':
        'c01acb400366ec154a852e75853bc2b5cf4807d5bd217a89578b8f4cd8ae1760',
}


def numeric(x):
    return type(x) in (int, float) and math.isfinite(x)


def validate_motion(motion, joints, arm):
    """Exact scaled native envelope; no arbitrary motion accepted by this runner."""
    if arm not in NATIVE or set(motion) != set(ORDERS) | {'robot', 'source'}:
        raise ValueError('Unexpected arm or motion fields')
    if motion['robot'] != 'Utars' or motion['source'] != 'utars_teleop':
        raise ValueError('Unexpected robot/source')
    names, q, velocity = (joints[k] for k in ('name', 'position', 'velocity'))
    if len(names) != len(q) or len(names) != len(velocity) or len(set(names)) != len(names):
        raise ValueError('Ambiguous canonical state')
    if not all(numeric(v) and abs(v) < .002 for v in velocity):
        raise ValueError('Canonical state not stationary')
    current = dict(zip(names, q))
    first = {}
    for group, group_names in ORDERS.items():
        rows = motion[group]
        if len(rows) != 11001:
            raise ValueError('Expected exactly22s at500Hz')
        for row in rows:
            if set(row) != {'q', 't'} or len(row['q']) != len(group_names) or not all(numeric(x) for x in row['q']):
                raise ValueError('Bad SDK row')
        for n, v in zip(group_names, rows[0]['q']):
            if n not in current or not numeric(current[n]) or abs(current[n]) >= .02:
                raise ValueError('Outside measured HOME or incomplete body')
            if abs(v-current[n]) > .003:
                raise ValueError('Stale initial joint reference')
            first[n] = v
    moving = arm+'_arm'
    offsets = [a-b for a, b in zip(motion[moving][5000]['q'], motion[moving][0]['q'])]
    scale = offsets[2]/NATIVE[arm][2]
    if not numeric(scale) or not 0 < scale <= math.radians(2)/1.910+1e-14:
        raise ValueError('Excursion must be in(0,2]degrees')
    if any(abs(offset-native*scale) > 1e-12 for offset, native in zip(offsets, NATIVE[arm])):
        raise ValueError('Not the selected scaled native preparation')
    for group, group_names in ORDERS.items():
        for i, row in enumerate(motion[group]):
            t = i/500.
            if not numeric(row['t']) or row['t'] != t:
                raise ValueError('Bad sample times')
            if t <= 2 or t >= 20:
                envelope = 0.
            elif t < 10:
                u = (t-2)/8
                envelope = u*u*u*(10+u*(-15+6*u))
            elif t <= 12:
                envelope = 1.
            else:
                u = (t-12)/8
                envelope = 1.-u*u*u*(10+u*(-15+6*u))
            for index, (n, actual) in enumerate(zip(group_names, row['q'])):
                expected = first[n]+(offsets[index]*envelope if group == moving else 0.)
                if abs(actual-expected) > 1e-12:
                    raise ValueError('Motion not the reviewed envelope or another axis changed')
        if motion[group][-1]['q'] != motion[group][0]['q']:
            raise ValueError('Return is not exact')
    return dict(max_initial_delta_rad=max(abs(current[n]-v) for n, v in first.items()),
                amplitude_deg=math.degrees(abs(offsets[2])), duration_s=22,
                moving_joints=list(ORDERS[moving]), held_joint_count=13)


def query(command):
    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        p = subprocess.run(command, text=True, capture_output=True, timeout=9)
        return dict(requested_utc=start, completed_monotonic=time.monotonic(), returncode=p.returncode, stdout=p.stdout, stderr=p.stderr)
    except subprocess.TimeoutExpired:
        return dict(requested_utc=start, returncode=124)


def checks_for(queries):
    checks = {key: value.get('returncode') == 0 for key, value in queries.items()}
    def native(key):
        raw = queries[key]['stdout']
        return json.loads(raw[raw.index('{'):])
    actuators, joints = native('actuators')['act_item'], native('joints')
    body = [v for v in actuators if v['type'] != 'cruzr_s2_wheel']
    checks['body20'] = len(body) == 20 and len({v['name'] for v in body}) == 20
    aliases = ((1001,), (1002,), (2001, 11004), (2002, 11003), (2003, 11002), (3001, 11001),
               *((i,) for i in range(4001, 4008)), *((i,) for i in range(5001, 5008)))
    ids = [v['id'] for v in body]
    checks['body_id_coverage'] = all(type(axis) is int for axis in ids) and len(set(ids)) == 20 and all(sum(axis in ids for axis in group) == 1 for group in aliases)
    checks['healthy'] = all(type(v['error_code']) is int and v['error_code'] == 0 and type(v['status']) is int and not(v['status'] & 8) and (v['status'] & 0x6f) == 0x27 for v in body)
    checks['stationary'] = all(numeric(v['velocity']) and abs(v['velocity']) < .002 for v in actuators)
    checks['tracking_at_rest'] = all(numeric(v['cmd_pos']) and numeric(v['position']) and abs(v['cmd_pos']-v['position']) <= .01 for v in body)
    for key in ('estop_key_state', 'servo_estop_key_state', 'chrg_input_status'):
        checks[key+'_clear'] = bool(re.fullmatch(r'\s*data:\s*0\s*(?:---)?\s*', queries[key]['stdout']))
    soc = [float(v) for v in re.findall(r'\bbatsoc:\s*([0-9.]+)', queries['battery_state']['stdout'])]
    checks['battery'] = len(soc) == 2 and min(soc) > 20
    statuses = [int(v) for v in re.findall(r'^\s+status:\s*(\d+)\s*$', queries['manip_status']['stdout'], re.M)]
    checks['no_active_manipulation'] = bool(statuses) and all(s in (4, 5, 6) for s in statuses)
    locks = queries['locks']['stdout']
    checks['unlocked'] = bool(re.search(r'^locked: false\s*$', locks, re.M) and re.search(r"^module_name: ''\s*$", locks, re.M))
    checks['sdk_idle'] = bool(re.search(r'Action server count: 1\s*$', queries['sdk_action']['stdout'], re.M) and re.search(r'Action client count: 0\s*$', queries['sdk_action']['stdout'], re.M))
    checks['sdk_writers0'] = bool(re.search(r'Writer count: 0\s*$', queries['sdk_commands']['stdout'], re.M))
    for name, state in [('manipulation_controller', 'running'), ('sdk_controller', 'initialized'), ('vla_sdk_controller', 'initialized')]:
        checks[name] = bool(re.search("'name': '"+name+"', 'state': '"+state+"'", queries['controllers']['stdout']))
    return checks, joints


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--motion', required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--arm', required=True, choices=('right', 'left'))
    parser.add_argument('--run', action='store_true', help='One physical test; default only checks')
    args = parser.parse_args(argv)
    path = PurePosixPath(args.motion)
    if not path.is_absolute() or str(path) != args.motion or '..' in path.parts or path.parts[:2] != ('/', 'tmp') or path.suffix != '.motion':
        parser.error('--motion must be a canonical temporary .motion path')
    if not re.fullmatch('[0-9a-f]{64}', args.sha256):
        parser.error('Invalid checksum')
    ps = subprocess.run(['docker', 'ps', '--format', '{{.Names}}'], capture_output=True, text=True, timeout=5)
    names = ps.stdout.splitlines()
    apps = [n for n in names if 'manipulation_robot_app' in n]
    bridges = [n for n in names if n.endswith('ros2-1')]
    if ps.returncode or len(apps) != 1 or len(bridges) != 1:
        raise ValueError('Ambiguous containers')
    def command(raw, native=True):
        setup = '/opt/walker/setup.bash' if native else '/opt/ros/humble/setup.bash'
        return ['docker', 'exec', apps[0] if native else bridges[0], 'bash', '-lc',
                'source '+setup+'; export ROS2CLI_DISABLE_DAEMON=1; timeout 6 '+raw]
    queries = {key: command(raw) for key, raw in {
        'actuators': 'rosa topic echo --once --qos-reliability best_effort /mc/actuator_state',
        'joints': 'rosa topic echo --once --qos-reliability best_effort /mc/whole_joint_states',
        'controllers': 'rosa service call /mc/controller_manager/list_controllers rosa_control_msgs/srv/ListControllers "{}"',
        'sdk_action': 'rosa action info /mc/action/outline_sdk_play',
        'sdk_commands': 'rosa topic info /mc/sdk/robot_command'}.items()}
    queries['manip_status'] = command('ros2 topic echo --once --no-daemon /mc/manipulation/action/_action/status', False)
    queries['locks'] = command('ros2 topic echo --once --no-daemon /sys/state/module_lock_info', False)
    for key in ('estop_key_state', 'servo_estop_key_state', 'chrg_input_status', 'battery_state'):
        queries[key] = command('ros2 topic echo --once --no-daemon /emb/'+key, False)
    report = dict(kind='preflight', app_container=apps[0], movement_commands=0, queries={})
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(query, cmd): key for key, cmd in queries.items()}
        for future in concurrent.futures.as_completed(futures):
            report['queries'][futures[future]] = future.result()
    checks = {}
    try:
        checks, joints = checks_for(report['queries'])
        initial_checks = dict(checks)
        probe = ('import pathlib,json,hashlib; p=pathlib.Path('+repr(str(path))+'); b=p.read_bytes(); '
                 'print(json.dumps(dict(sha256=hashlib.sha256(b).hexdigest(),motion=json.loads(b),'
                 'contract={p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() for p in '+repr(CONTRACT)+'})))')
        p = subprocess.run(['docker', 'exec', apps[0], 'python3', '-B', '-c', probe], capture_output=True, text=True, timeout=8)
        if p.returncode:
            raise ValueError('Cannot read input and SDK contract')
        data = json.loads(p.stdout)
        checks['motion_sha'] = data['sha256'] == args.sha256
        checks['native_contract'] = data['contract'] == CONTRACT
        # Refresh the four immediate body/stop readings after slower contract reads.
        old_queries = dict(report['queries'])
        immediate = ('actuators', 'joints', 'estop_key_state', 'servo_estop_key_state')
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            futures = {pool.submit(query, queries[key]): key for key in immediate}
            for future in concurrent.futures.as_completed(futures):
                report['queries'][futures[future]] = future.result()
        checks, joints = checks_for(report['queries'])
        checks.update({'initial_'+key: value for key, value in initial_checks.items()})
        report['earlier_body_stop_readings'] = {key: old_queries[key] for key in immediate}
        now = time.monotonic()
        checks['immediate_receipts_recent'] = all(now-report['queries'][key].get('completed_monotonic', 0.) <= 4. for key in immediate)
        for key in ('actuators', 'joints'):
            def stamp(entry):
                raw = entry['stdout']
                value = json.loads(raw[raw.index('{'):])['header']['stamp']
                sec, nano = value['sec'], value['nanosec']
                if type(sec) is not int or sec < 0 or type(nano) is not int or not 0 <= nano < 10**9:
                    raise ValueError('Invalid source timestamp')
                return sec*10**9+nano
            checks[key+'_source_advances'] = stamp(report['queries'][key]) > stamp(old_queries[key]) > 0
        checks['motion_sha'] = data['sha256'] == args.sha256
        checks['native_contract'] = data['contract'] == CONTRACT
        report['candidate'] = validate_motion(data['motion'], joints, args.arm)
        checks['candidate_contract'] = True
    except Exception as exc:
        checks['parsing_and_candidate'] = False
        report['error'] = type(exc).__name__+': '+str(exc)
    report['checks'] = checks
    report['all_pass'] = bool(checks) and all(checks.values())
    print(json.dumps(report), flush=True)
    if not report['all_pass']:
        return 78
    if not args.run:
        return 0
    print(json.dumps(dict(kind='physical_start', utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                         arm=args.arm, repetitions=1, home_requested=False, passive_telemetry_not_guard=True)), flush=True)
    raw = 'source /opt/walker/setup.bash; export ROS2CLI_DISABLE_DAEMON=1; exec rosa run manipulation_outline_sdk player -- --robot utars --input '+shlex.quote(str(path))
    start = time.monotonic()
    try:
        p = subprocess.run(['docker', 'exec', apps[0], 'bash', '-lc', raw], capture_output=True, text=True, timeout=65)
        success = p.returncode == 0 and 'Action finished with is_finished=true, bag has been played successfully' in p.stdout
        print(json.dumps(dict(kind='player_result', elapsed_s=time.monotonic()-start, returncode=p.returncode,
                              application_success=success, stdout=p.stdout, stderr=p.stderr,
                              automatic_retry=False, home_requested=False)), flush=True)
        return 0 if success else 78
    except subprocess.TimeoutExpired:
        print(json.dumps(dict(kind='player_timeout', physical_state='INDETERMINATE',
                              automatic_retry=False, home_requested=False)), flush=True)
        return 78


if __name__ == '__main__':
    raise SystemExit(main())
