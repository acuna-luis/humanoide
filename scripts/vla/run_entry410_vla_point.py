#!/usr/bin/env python3
"""Check or execute one reviewed bridge prefix toward one recorded VLA point."""
import argparse
import ast
import base64
import fcntl
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile

from prepare_vla_entry_bundle import ROOT, JOINT_ORDER, digest
from prepare_entry410_vla_point import select_point
from runtime.cruzr_s2_vla_sdk_transport import plan_minimum_jerk
from general_home.trace_analysis import ACTUATORS


def check_controller_inventory(output, names):
    """Native ROSA reply; ROS2 in this firmware lacks rosa_control_msgs types."""
    marker = 'Response(controller='
    if output.count(marker) != 1:
        raise ValueError('Missing/ambiguous native controller inventory')
    literal = output.split(marker, 1)[1].splitlines()[0]
    if not literal.endswith(')'):
        raise ValueError('Malformed controller inventory')
    rows = ast.literal_eval(literal[:-1])
    controllers = {v['name']: v for v in rows}
    if len(controllers) != len(rows):
        raise ValueError('Duplicate controller')
    expected = {'manipulation_controller': 'running', 'vla_sdk_controller': 'initialized',
                'sdk_controller': 'initialized', 'chassis_controller': 'running'}
    if any(controllers.get(n, {}).get('state') != state for n, state in expected.items()):
        raise ValueError('Controller state changed: expected manipulation active, SDK inactive; inspect before retry')
    def joints(row):
        return {n for claim in row['claimed_resources']
                if claim['hardware_interface'].endswith('::MultimodeJointInterface')
                for n in claim['resources']}
    if joints(controllers['vla_sdk_controller']) != set(names):
        raise ValueError('VLA controller does not own exactly the reviewed 20 joints')
    allowed = {'manipulation_controller', 'chassis_controller'}
    if any(v['state'] == 'running' and joints(v) and n not in allowed for n, v in controllers.items()):
        raise ValueError('Unexpected running command controller')
    return expected


def controller_preflight(plan, out):
    sys.path.insert(0, str(ROOT/'scripts'))
    from collect_estop_available_readonly import execute
    command = "source /opt/walker/setup.bash; export ROS2CLI_DISABLE_DAEMON=1; timeout 7 rosa service call /mc/controller_manager/list_controllers rosa_control_msgs/srv/ListControllers '{}'"
    result = execute('motion', ['docker', 'exec', 'walker-motion.manipulation_robot_app-1', 'bash', '-lc', command])
    (out/'controllers-before.json').write_text(json.dumps(result, indent=2)+'\n')
    if result.get('returncode') != 0:
        raise RuntimeError('Cannot read active controller; no handoff or publisher created')
    check_controller_inventory(result['stdout'], plan['joint_order'])
    print('CONTROLLER_HANDOFF_REQUIRED=manipulation_controller->vla_sdk_controller', flush=True)


def new_evidence_dir(requested):
    """Keep prior attempts intact; repeated operator invocation gets a sibling."""
    requested = Path(requested).resolve()
    requested.parent.mkdir(parents=True, exist_ok=True)
    try:
        requested.mkdir()
        return requested
    except FileExistsError:
        if not requested.is_dir():
            raise ValueError('Evidence path is an existing file: '+str(requested))
        return Path(tempfile.mkdtemp(prefix=requested.name+'-', dir=requested.parent))


def check_plan(path):
    r = json.loads(path.read_text())
    if (r['schema'] != 'cruzr-entry410-recorded-vla-point-review-v1'
            or r['joint_order'] != JOINT_ORDER or r['arm_names'] != JOINT_ORDER[:14]
            or r['bridge_fraction'] != .25 or r['duration_seconds'] != 4.):
        raise ValueError('Only the reviewed quarter-bridge trial is supported')
    if len(r['start']) != 20 or len(r['source_target']) != 20 or len(r['target']) != 20:
        raise ValueError('Invalid dimensions')
    for name, expected in r['sources_sha256'].items():
        if digest(Path(name)) != expected:
            raise ValueError('Source changed: '+name)
    required = [Path(__file__), ROOT/'scripts/vla/prepare_entry410_vla_point.py',
                ROOT/'scripts/vla/runtime/entry410_vla_point_remote.py',
                ROOT/'scripts/vla/runtime/entry410_single_stage_remote.py',
                ROOT/'scripts/vla/runtime/cruzr_s2_vla_ros_sdk_backend.py']
    if any(str(p.resolve()) not in r['sources_sha256'] for p in required):
        raise ValueError('Unbound executor')
    # Re-derive selection from the recorded shadow and source capture.
    from prepare_home_ready_access import measured_named_start
    records = [json.loads(Path(n).read_text()) for n in r['sources_sha256'] if n.endswith('capture.json')]
    captures = [c for c in records if c.get('schema') == 'cruzr-entry-named-state-capture-v1']
    logs = [Path(n) for n in r['sources_sha256'] if n.endswith('shadow.jsonl')]
    if len(captures) != 1 or len(logs) != 1 or measured_named_start(captures[0]) != r['start']:
        raise ValueError('Measured start identity mismatch')
    rows = [json.loads(line) for line in logs[0].read_text().splitlines()]
    _, chunk, source_target = select_point(rows, r['start'], JOINT_ORDER, r['arm_names'])
    if chunk != r['source_chunk_id'] or source_target != r['source_target']:
        raise ValueError('Recorded proposal changed')
    if r['target'] != [a+(b-a)*.25 for a, b in zip(r['start'], source_target)]:
        raise ValueError('Bridge endpoint changed')
    if max(abs(a-b) for a, b in zip(r['start'], r['target'])) > .025:
        raise ValueError('Prefix exceeds 0.025 rad')
    limits = r['engineering_limits']
    if (limits['maximum_velocity_rad_s'] != [.05]*14
            or limits['maximum_acceleration_rad_s2'] != [.1]*14
            or limits['maximum_target_delta_rad'] != [.1]*14
            or limits['sample_period_seconds'] != .01
            or limits['minimum_transition_duration_seconds'] != 4.
            or limits['maximum_transition_duration_seconds'] != 4.):
        raise ValueError('Engineering limits changed')
    if r['trajectory'] != plan_minimum_jerk(r['start'][:14], r['target'][:14], limits):
        raise ValueError('Trajectory changed')
    audit = r['geometry_audit']
    if audit['timed_out'] or audit['joint_error_scenario_rad'] < .005 or r['new_or_scene_failures']:
        raise ValueError('Incomplete geometry')
    # Bind the pair set to the original scene audit; never accept novel exemptions.
    candidates = [json.loads(Path(n).read_text()) for n in r['sources_sha256'] if n.endswith('reference.json')]
    refs = [v for v in candidates if v.get('model_sources') == r['model_sources'] and 'scenarios' in v]
    if len(refs) != 1 or refs[0]['scenarios'][0]['scene_objects'] != r['scene_objects']:
        raise ValueError('Scene identity mismatch')
    original = refs[0]['scenarios'][0]['routes']['access']['audit']['pairs']
    historic = {tuple(p['pair']) for p in original if p['status'] == 'MODEL_MARGIN_VIOLATION'}
    if len(audit['pairs']) != len(original) or {tuple(p['pair']) for p in audit['pairs']} != {tuple(p['pair']) for p in original}:
        raise ValueError('Incomplete pair coverage')
    for pair in audit['pairs']:
        if pair.get('exempted') or pair['status'] not in ('CERTIFIED_AFFINE_INTERVALS', 'MODEL_MARGIN_VIOLATION'):
            raise ValueError('Unresolved/exempted pair')
        if pair['status'] == 'MODEL_MARGIN_VIOLATION' and (tuple(pair['pair']) not in historic or any(n.startswith('scene:') for n in pair['pair'])):
            raise ValueError('New/scene violation')
    return r


def main():
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true', help='Local integrity only, no robot access')
    mode.add_argument('--observe', action='store_true', help='Read-only live admission; never creates a command publisher')
    mode.add_argument('--run', action='store_true', help='One 4-second 25-percent bridge; physical movement')
    p.add_argument('--review', type=Path, required=True)
    p.add_argument('--evidence-dir', type=Path)
    p.add_argument('--physical-confirmed', action='store_true',
        help='Operator confirms unchanged scene, empty clamps, wheels locked, no other controller, person at E-stop')
    a = p.parse_args(); plan = check_plan(a.review)
    if a.check:
        print('LOCAL_POINT_REVIEW_OK; recorded-point prefix, 4 s; no movement'); return
    if a.run and not a.physical_confirmed:
        p.error('--physical-confirmed is required for the current physical setup')
    if a.evidence_dir is None:
        p.error('--evidence-dir must be a new directory')
    out = new_evidence_dir(a.evidence_dir)
    print('EVIDENCE_DIR='+str(out), flush=True)
    lock = (ROOT/'.entry410-stage.lock').open('a'); fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    (out/'review.json').write_bytes(a.review.read_bytes())
    with (out/'preflight.log').open('x') as log:
        subprocess.run(['bash', str(ROOT/'scripts/vla/audit_vla_live_preflight_e6_0g.sh'),
            '--check', '--expect-released'], stdout=log, stderr=subprocess.STDOUT, timeout=150, check=True)
    if check_plan(a.review) != plan:
        raise ValueError('Plan changed during preflight')
    controller_preflight(plan, out)
    modules = {
        'stage_monitor': ROOT/'scripts/vla/runtime/entry410_single_stage_remote.py',
        'sdk_backend': ROOT/'scripts/vla/runtime/cruzr_s2_vla_ros_sdk_backend.py',
        'point_trial': ROOT/'scripts/vla/runtime/entry410_vla_point_remote.py',
    }
    payload = dict(plan=plan, actuator_names=ACTUATORS, observe_only=a.observe)
    source = 'import types,sys,json,base64\n'
    for name, file in modules.items():
        encoded = base64.b64encode(file.read_bytes()).decode()
        source += f"m=types.ModuleType({name!r}); sys.modules[{name!r}]=m; exec(base64.b64decode({encoded!r}),m.__dict__)\n"
    encoded = base64.b64encode(json.dumps(payload, allow_nan=False).encode()).decode()
    source += f"sys.modules['point_trial'].main(json.loads(base64.b64decode({encoded!r})))\n"
    (out/'remote_source.py').write_text(source)
    env = dict(os.environ, SSH_ASKPASS=str(ROOT/'scripts/vla/audit_vla_live_preflight_e6_0g.sh'),
               SSH_ASKPASS_REQUIRE='force', CRUZR_INTERNAL_ASKPASS='1', DISPLAY=os.environ.get('DISPLAY', ':0'))
    remote = 'docker exec -i walker-ros.ros2-1 bash -lc '+shlex.quote('source /opt/ros/humble/setup.bash; export ROS2CLI_DISABLE_DAEMON=1; timeout --signal=TERM --kill-after=2 35 python3 -')
    cmd = ['setsid', '-w', 'ssh', '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=5',
           '-o', 'ConnectionAttempts=1', '-o', 'PreferredAuthentications=password', '-o', 'PubkeyAuthentication=no',
           'walker@192.168.11.2', remote]
    with (out/'trace.jsonl').open('x') as log:
        done = subprocess.run(cmd, input=source, text=True, stdout=log, stderr=subprocess.STDOUT, env=env, timeout=45)
    rows = [json.loads(s) for s in (out/'trace.jsonl').read_text().splitlines() if s.startswith('{')]
    expected_status = 'ENTRY_POINT_ADMISSION_OBSERVED_NO_PUBLISHER' if a.observe else 'ONE_POINT_PREFIX_SUCCEEDED_AND_SETTLED'
    success = done.returncode == 0 and bool(rows) and rows[-1].get('status') == expected_status
    (out/'result.json').write_text(json.dumps(dict(success=success, returncode=done.returncode, retry=False, observe_only=a.observe), indent=2)+'\n')
    if not success:
        reason = next((v['error'] for v in reversed(rows) if v.get('error')), 'No final success acknowledgement')
        raise RuntimeError(reason+'; no retry or automatic HOME. Trace: '+str(out/'trace.jsonl'))
    print(expected_status+'; no subsequent proposal or HOME sent')


if __name__ == '__main__':
    main()
