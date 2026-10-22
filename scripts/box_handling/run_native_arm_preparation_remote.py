#!/usr/bin/env python3
"""Check a separate native arm-preparation task; --run dispatches it once.

No original task, mode or protection is changed. Physical authorization is
separate. The existing bounded native action client owns cancellation on error;
this runner never retries and never requests HOME after interruption.
"""
import argparse
import concurrent.futures
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import shlex
import subprocess
import time
import xml.etree.ElementTree as ET

if __package__:
    from . import run_empty_arm_diagnostic_remote as passive
else:
    import run_empty_arm_diagnostic_remote as passive


TASK_ROOT = '/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/'
META_MOVE = '/opt/walker/manipulation_meta_tasks/lib/libmeta_move.so'
ORIGINAL = TASK_ROOT+'Singapore/separate_right_cruzr.xml'
CONTRACT = dict(passive.CONTRACT, **{
    META_MOVE: 'bfeab1c7a295b58cd96fddd20916fc3f7fe16bd8c8ad1e77720f48aad34ccc69',
    ORIGINAL: '4ba2515ba030f7f1483eed704ce68e0d888ac29754bef1645908fb9f96345e0b'})
SUPPORT = dict(scenario1_action_client='196b6241de0d1e624b919ab062fc391e6e8ee8837e4a496cbcdad99a57b3b607',
               scenario1_request_ids='904adfb55e621fde1bd03d8e7fd96b61bf1866e5a0b94f92b36eb53999d4092d')
BODY_NAMES = tuple(name for names in passive.ORDERS.values() for name in names)


def canonical(joints):
    names, positions, velocities = (joints[key] for key in ('name', 'position', 'velocity'))
    if (any(type(value) is not list for value in (names, positions, velocities)) or
            len(names) != len(positions) or len(names) != len(velocities) or
            any(type(name) is not str or not name or name != name.strip() for name in names) or
            len(set(names)) != len(names) or not set(BODY_NAMES) <= set(names)):
        raise ValueError('Incomplete or ambiguous canonical 20D state')
    if any(not passive.numeric(value) for value in positions+velocities):
        raise ValueError('Nonfinite canonical state')
    if any(abs(value) >= .002 for value in velocities):
        raise ValueError('Canonical state is moving')
    values = dict(zip(names, positions))
    if any(abs(values[name]) >= .02 for name in BODY_NAMES):
        raise ValueError('Measured full 20D HOME required')
    return {name: values[name] for name in BODY_NAMES}


def validate_xml(xml, arm, reference):
    """Accept only the original arm preparation and measured-reference return."""
    if arm not in passive.NATIVE or type(xml) is not str or len(xml.encode()) > 20000:
        raise ValueError('Invalid native preparation source')
    if set(reference) != set(BODY_NAMES) or any(not passive.numeric(v) or abs(v) >= .02 for v in reference.values()):
        raise ValueError('Complete measured HOME reference required')
    root = ET.fromstring(xml)
    if root.tag != 'root' or root.attrib != {'main_tree_to_execute': 'MainTree'} or len(root) != 1:
        raise ValueError('Unexpected task root')
    tree = root[0]
    if tree.tag != 'BehaviorTree' or tree.attrib != {'ID': 'MainTree'} or len(tree) != 1:
        raise ValueError('Unexpected behavior tree')
    sequence = tree[0]
    if sequence.tag != 'Sequence' or set(sequence.attrib) - {'name'} or len(sequence) != 2:
        raise ValueError('Exactly two sequential arm actions required')
    group = passive.ORDERS[arm+'_arm']
    wanted = [list(passive.NATIVE[arm]), [reference[name] for name in group]]
    for action, duration, expected in zip(sequence, (3., 6.), wanted):
        if (action.tag != 'Action' or len(action) or set(action.attrib) !=
                {'ID', 'type', 'location', 'joint_angles', 'duration'} or
                any(action.get(key) != value for key, value in
                    (('ID', 'MetaMove'), ('type', 'arm'), ('location', arm)))):
            raise ValueError('Only selected-arm MetaMove is permitted')
        raw = action.get('joint_angles').split(';')
        values = [float(value.strip()) for value in raw]
        seconds = float(action.get('duration'))
        if (len(values) != 7 or any(not math.isfinite(value) for value in values) or
                values != expected or not math.isfinite(seconds) or seconds != duration):
            raise ValueError('Native target, measured return or duration changed')
    return dict(arm=arm, preparation_duration_s=3, return_duration_s=6,
                commanded_joint_count=7, actions=2, native_preparation_rad=wanted[0],
                measured_return_rad=wanted[1], full_grasp_reproduced=False)


def stamp(query):
    raw = query['stdout']
    value = json.loads(raw[raw.index('{'):])['header']['stamp']
    sec, ns = value['sec'], value['nanosec']
    if type(sec) is not int or sec < 0 or type(ns) is not int or not 0 <= ns < 10**9:
        raise ValueError('Invalid source timestamp')
    result = sec*10**9+ns
    if result <= 0:
        raise ValueError('Missing source timestamp')
    return result


def validate_result(returncode, stdout):
    rows, native_logs = [], []
    for line in stdout.splitlines():
        try:
            row = json.loads(line)
            if not isinstance(row, dict) or type(row.get('event')) is not str:
                raise ValueError('Not an event')
        except (ValueError, TypeError):
            native_logs.append(line)
            continue
        rows.append(row)
    accepted = [row for row in rows if row['event'] == 'accepted']
    results = [row for row in rows if row['event'] == 'result']
    if (type(returncode) is not int or returncode != 0 or
            any(row['event'] in ('error', 'cancel_requested', 'cancel_response', 'interrupted_terminal') for row in rows) or
            len(accepted) != 1 or accepted[0].get('accepted') is not True or len(results) != 1):
        raise ValueError('Native action did not complete successfully')
    result = results[0]
    application = result.get('result')
    state = application.get('state') if isinstance(application, dict) else None
    if not isinstance(state, dict):
        raise ValueError('Missing native application state')
    if (not isinstance(accepted[0].get('goal_id'), str) or
            not re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', accepted[0]['goal_id']) or
            rows.index(accepted[0]) >= rows.index(result) or result.get('goal_id') != accepted[0]['goal_id'] or
            type(result.get('status')) is not int or result['status'] != 4 or
            type(state.get('state')) is not int or state['state'] != 1101001 or state.get('desc') != 'SUCCEED'):
        raise ValueError('Native terminal status/application/UUID mismatch')
    for row in rows:
        if row['event'] in ('status', 'feedback', 'result', 'accepted', 'dispatched') and row.get('goal_id') != result['goal_id']:
            raise ValueError('Unexpected native goal identity')
        if row['event'] == 'status' and (type(row.get('status')) is not int or row['status'] not in (1, 2, 3, 4)):
            raise ValueError('Contradictory native status')
    return dict(goal_id=result['goal_id'], terminal=result, native_log_lines=native_logs,
                physical_stop_verified=False, home_requested=False, automatic_retry=False)


def validate_bundle(bundle, joints):
    if bundle.get('schema') != 'cruzr-native-arm-preparation-v1':
        raise ValueError('Unexpected preparation bundle schema')
    candidate, source = bundle['candidate'], bundle['source']
    arm, xml = candidate['arm'], bundle['xml']
    reference = source['initial_joint_reference_20d']
    review = validate_xml(xml, arm, reference)
    digest = hashlib.sha256(xml.encode()).hexdigest()
    task_name = 'diagnostics/native_arm_preparation_'+arm+'_'+digest[:16]
    if (candidate['xml_sha256'] != digest or candidate['task_name'] != task_name or
            candidate['runtime_path'] != TASK_ROOT+task_name+'.xml' or
            source['native_xml_sha256'] != CONTRACT[ORIGINAL] or
            bundle['urdf']['sha256'] != CONTRACT[next(path for path in CONTRACT if path.endswith('/urdf/cruzr_s2.urdf'))] or
            candidate['joint_order'] != list(passive.ORDERS[arm+'_arm']) or
            candidate['outbound_joint_target_rad'] != list(passive.NATIVE[arm]) or
            candidate['return_joint_target_rad'] != [reference[name] for name in passive.ORDERS[arm+'_arm']] or
            candidate['outbound_duration_s'] != 3 or candidate['return_duration_s'] != 6 or
            candidate['total_nominal_duration_s'] != 9):
        raise ValueError('Preparation bundle identity or contract mismatch')
    source_values = canonical(source['canonical_joint_state'])
    if source_values != reference:
        raise ValueError('Source canonical state/reference mismatch')
    current = canonical(joints)
    delta = max(abs(current[name]-reference[name]) for name in BODY_NAMES)
    if delta > .003:
        raise ValueError('Measured HOME differs from preparation reference by more than 0.003 rad')
    return dict(review, task_name=task_name, runtime_path=candidate['runtime_path'],
                xml_sha256=digest, max_initial_delta_rad=delta)


def query_commands(app, bridge):
    def command(raw, native=True):
        setup = '/opt/walker/setup.bash' if native else '/opt/ros/humble/setup.bash'
        return ['docker', 'exec', app if native else bridge, 'bash', '-lc',
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
    return queries


def collect(commands):
    result = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(passive.query, cmd): key for key, cmd in commands.items()}
        for future in concurrent.futures.as_completed(futures):
            result[futures[future]] = future.result()
    return result


def temporary_path(raw, suffix=None):
    path = PurePosixPath(raw)
    if (not path.is_absolute() or str(path) != raw or '..' in path.parts or
            path.parts[:2] != ('/', 'tmp') or len(path.parts) < 3 or
            suffix is not None and path.suffix != suffix):
        raise ValueError('Expected canonical private /tmp path')
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True, help='Self-contained manifest JSON on Motion host')
    parser.add_argument('--support-dir', required=True, help='Same private /tmp directory in host and native container')
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args(argv)
    bundle_path = temporary_path(args.bundle, '.json')
    support = temporary_path(args.support_dir)
    if bundle_path.parent != support:
        parser.error('Bundle and support files must share the private staging directory')
    bundle = json.loads(Path(str(bundle_path)).read_text())
    report = dict(kind='native_preparation_preflight', movement_commands=0, checks={}, queries={})
    try:
        ps = subprocess.run(['docker', 'ps', '--format', '{{.Names}}'], capture_output=True, text=True, timeout=5)
        names = ps.stdout.splitlines()
        apps = [name for name in names if 'manipulation_robot_app' in name]
        bridges = [name for name in names if name.endswith('ros2-1')]
        if ps.returncode or len(apps) != 1 or len(bridges) != 1:
            raise ValueError('Ambiguous containers')
        app, bridge = apps[0], bridges[0]
        report['app_container'] = app
        commands = query_commands(app, bridge)
        first = collect(commands)
        initial, joints = passive.checks_for(first)
        report['earlier_queries'] = first
        report['checks'].update({'initial_'+key: value for key, value in initial.items()})
        candidate = validate_bundle(bundle, joints)
        expected = dict(CONTRACT, **{str(support/(name+'.py')): digest for name, digest in SUPPORT.items()},
                        **{candidate['runtime_path']: candidate['xml_sha256']})
        probe = ('import hashlib,json,pathlib; paths='+repr(list(expected))+'; '
                 'print(json.dumps({p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() for p in paths}))')
        result = subprocess.run(['docker', 'exec', app, 'python3', '-B', '-c', probe],
                                capture_output=True, text=True, timeout=8)
        report['checks']['installed_contract'] = result.returncode == 0 and json.loads(result.stdout) == expected
        # Refresh the body/stop readings together after slower discovery and
        # hashing. Re-reading all eleven endpoints would age the first body
        # samples while waiting for unrelated retained service/topic replies.
        immediate = ('actuators', 'joints', 'estop_key_state', 'servo_estop_key_state', 'chrg_input_status')
        second = dict(first, **collect({key: commands[key] for key in immediate}))
        report['queries'] = second
        final, joints = passive.checks_for(second)
        report['checks'].update(final)
        now = time.monotonic()
        for key in ('actuators', 'joints', 'estop_key_state', 'servo_estop_key_state', 'chrg_input_status'):
            receipt = second[key].get('completed_monotonic')
            report['checks'][key+'_receipt_recent'] = passive.numeric(receipt) and 0 <= now-receipt <= 4
        for key in ('actuators', 'joints'):
            report['checks'][key+'_source_advances'] = stamp(second[key]) > stamp(first[key])
        report['candidate'] = validate_bundle(bundle, joints)
        report['checks']['candidate_contract'] = True
    except Exception as exc:
        report['checks']['parsing_and_contract'] = False
        report['error'] = type(exc).__name__+': '+str(exc)
    report['all_pass'] = bool(report['checks']) and all(report['checks'].values())
    print(json.dumps(report, allow_nan=False), flush=True)
    if not report['all_pass']:
        return 78
    if not args.run:
        return 0
    goal = dict(task_name=report['candidate']['task_name'], yaml_args='{}')
    command = ['python3', '-u', '-B', str(support/'scenario1_action_client.py'), '--kind', 'motion',
               '--goal-json', json.dumps(goal), '--timeout', '25']
    shell = 'source /opt/walker/setup.bash; export ROS2CLI_DISABLE_DAEMON=1; exec '+shlex.join(command)
    print(json.dumps(dict(kind='physical_start', arm=report['candidate']['arm'], goal=goal,
                         repetitions=1, home_requested=False, passive_telemetry_not_guard=True)), flush=True)
    try:
        result = subprocess.run(['docker', 'exec', app, 'bash', '-lc', shell],
                                capture_output=True, text=True, timeout=45)
        print(json.dumps(dict(kind='native_action_output', returncode=result.returncode,
                              stdout=result.stdout, stderr=result.stderr)), flush=True)
        terminal = validate_result(result.returncode, result.stdout)
        print(json.dumps(dict(kind='native_preparation_result', **terminal)), flush=True)
        return 0
    except (ValueError, TypeError, KeyError, subprocess.TimeoutExpired) as exc:
        print(json.dumps(dict(kind='native_preparation_failed', reason=type(exc).__name__+': '+str(exc),
            physical_state='INDETERMINATE', home_requested=False, automatic_retry=False)), flush=True)
        return 78


if __name__ == '__main__':
    raise SystemExit(main())
