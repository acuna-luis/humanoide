#!/usr/bin/env python3
"""Build a single right-wrist MetaMove candidate; never connect or dispatch.

The input state and URDF are caller-supplied snapshots. This builder checks a
PICO/head-down reference and nominal URDF endpoints only; it does not validate
freshness, loaded configuration, v4 hand geometry, collision, braking, or
operator conditions. The task and its ROSA ArmTask goal are NOT authorized for
physical execution by this builder. No automatic return or HOME is generated.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'runtime'))
sys.path.insert(0, str(HERE.parent / 'box_handling'))
from arm_from_pico_supervised import ARM_AXIS, ARM_STEP, BODY, check_body
from pico_wrist_action_client import validate_goal

ARM = ('R_shoulder_pitch_joint', 'R_shoulder_roll_joint', 'R_shoulder_yaw_joint',
       'R_elbow_roll_joint', 'R_elbow_yaw_joint', 'R_wrist_pitch_joint',
       'R_wrist_roll_joint')
DURATION_S = 4.0
REVIEW_MARGIN_RAD = .002  # Diagnostic uncertainty margin, not a safety limit.
TASK_ROOT = '/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/'
LIB_META_SHA256 = 'bfeab1c7a295b58cd96fddd20916fc3f7fe16bd8c8ad1e77720f48aad34ccc69'


def nominal_arm_limits(urdf_text, initial, target, duration_s=DURATION_S):
    """Check endpoint limits and necessary average speeds, not the path."""
    if (type(duration_s) not in (int, float) or not math.isfinite(duration_s)
            or duration_s <= 0):
        raise ValueError('invalid_nominal_duration')
    root = ET.fromstring(urdf_text)
    if root.tag != 'robot':
        raise ValueError('expected_robot_urdf')
    nodes = root.findall('joint')
    names = [node.get('name') for node in nodes]
    if len(names) != len(set(names)):
        raise ValueError('duplicate_urdf_joint')
    by_name = dict(zip(names, nodes))
    result = {}
    for name, end in zip(ARM, target, strict=True):
        node = by_name.get(name)
        if node is None or node.get('type') != 'revolute' or node.find('limit') is None:
            raise ValueError('missing_urdf_limit:' + name)
        try:
            limit = node.find('limit').attrib
            low, high, speed = [float(limit[key]) for key in ('lower', 'upper', 'velocity')]
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError('invalid_urdf_limit:' + name) from exc
        if not all(math.isfinite(x) for x in (low, high, speed)) or low >= high or speed <= 0:
            raise ValueError('invalid_urdf_limit:' + name)
        start = initial[name]
        if not (low <= start <= high and low <= end <= high):
            raise ValueError('nominal_endpoint_outside_urdf:' + name)
        required = abs(end - start) / duration_s
        if required > speed:
            raise ValueError('necessary_average_speed_above_urdf:' + name)
        result[name] = {'lower_rad': low, 'upper_rad': high, 'speed_rad_s': speed,
                        'start_rad': start, 'target_rad': end, 'average_rad_s': required}
    return result


def hardware_endpoints(transmissions_text, initial, target):
    """Check all 20 named body axes against the supplied SPS transmission."""
    data = yaml.safe_load(transmissions_text)
    if not isinstance(data, dict) or not isinstance(data.get('transmissions'), dict):
        raise ValueError('invalid_transmissions')
    joints = {}
    for item in data['transmissions'].values():
        if not isinstance(item, dict) or not isinstance(item.get('joint'), dict):
            continue
        joint = item['joint']
        name = joint.get('name')
        if name in BODY:
            if name in joints:
                raise ValueError('duplicate_transmission_joint:' + name)
            joints[name] = joint.get('limit')
    if set(joints) != set(BODY):
        raise ValueError('incomplete_sps_body_limits')
    target_by_name = dict(zip(ARM, target, strict=True))
    result = {}
    for name in BODY:
        limit = joints[name]
        if not isinstance(limit, dict):
            raise ValueError('missing_sps_limit:' + name)
        low, high = limit.get('lower'), limit.get('upper')
        if (type(low) not in (int, float) or type(high) not in (int, float) or
                not all(math.isfinite(x) for x in (low, high)) or low >= high):
            raise ValueError('invalid_sps_limit:' + name)
        end = target_by_name.get(name, initial[name])
        margin = min(initial[name]-low, high-initial[name], end-low, high-end)
        if margin < 0:
            raise ValueError('nominal_endpoint_outside_sps_transmissions:' + name)
        result[name] = {'lower_rad': float(low), 'upper_rad': float(high),
                        'minimum_endpoint_margin_rad': margin,
                        'within_nominal_limits': margin >= 0,
                        'diagnostic_margin_satisfied': margin >= REVIEW_MARGIN_RAD}
    return result


def prepare(state, urdf_text, transmissions_text):
    if (not isinstance(state, dict) or not isinstance(urdf_text, str) or
            not isinstance(transmissions_text, str)):
        raise ValueError('invalid_input_type')
    # Uses the already-tested passive PICO/v4 body reference, including the
    # lowered head and actual per-axis speeds; it never infers current state.
    initial = check_body(state)
    target = [initial[name] + (ARM_STEP if name == ARM_AXIS else 0.0) for name in ARM]
    limits = nominal_arm_limits(urdf_text, initial, target)
    hardware_limits = hardware_endpoints(transmissions_text, initial, target)
    root = ET.Element('root', {'main_tree_to_execute': 'MainTree'})
    tree = ET.SubElement(root, 'BehaviorTree', {'ID': 'MainTree'})
    seq = ET.SubElement(tree, 'Sequence', {'name': 'pico_v4_wrist_single_probe'})
    ET.SubElement(seq, 'Action', {'ID': 'MetaMove', 'type': 'arm', 'location': 'right',
                                 'joint_angles': ';'.join(format(q, '.17g') for q in target),
                                 'duration': format(DURATION_S, '.17g')})
    ET.indent(root, space='    ')
    xml = ET.tostring(root, encoding='unicode') + '\n'
    digest = hashlib.sha256(xml.encode()).hexdigest()
    task_name = 'diagnostics/pico_v4_wrist_' + digest[:16]
    goal = {'task_name': task_name, 'yaml_args': '{}'}
    if validate_goal('motion', json.dumps(goal)) != goal:
        raise ValueError('native_goal_contract_mismatch')
    return {
        'schema': 'cruzr_pico_v4_wrist_native_probe_v1',
        'status': 'PREPARED_NOT_INSTALLED_OR_EXECUTED',
        'physical_control_qualified': False, 'robot_connections': 0,
        'remote_writes': 0, 'movement_commands': 0,
        'input': {'canonical_joint_state': state, 'reference_20d': initial,
                  'urdf_sha256': hashlib.sha256(urdf_text.encode()).hexdigest(),
                  'transmissions_sha256': hashlib.sha256(transmissions_text.encode()).hexdigest(),
                  'freshness_verified': False},
        'candidate': {'xml': xml, 'xml_sha256': digest, 'task_name': task_name,
                      'runtime_path': TASK_ROOT + task_name + '.xml', 'goal': goal,
                      'arm_joint_order': list(ARM), 'target_rad': target,
                      'moved_axis': ARM_AXIS, 'step_rad_experimental': ARM_STEP,
                      'duration_s_experimental': DURATION_S, 'actions': 1,
                      'automatic_return': False, 'home_requested': False},
        'expected_meta_move_sha256': LIB_META_SHA256,
        'nominal_urdf_limits': limits,
        'nominal_sps_transmission_limits': hardware_limits,
        'diagnostic_margin_rad': REVIEW_MARGIN_RAD,
        'all_endpoints_inside_nominal_sps_limits': all(x['within_nominal_limits'] for x in hardware_limits.values()),
        'all_endpoints_satisfy_diagnostic_margin': all(x['diagnostic_margin_satisfied'] for x in hardware_limits.values()),
        'limitations': [
            'state is a snapshot; current physical and control conditions are not established',
            'the robot URDF must be independently re-read and matched before any physical use',
            'SPS margins are diagnostic endpoints only; the exact profile and uncertainty are not established',
            'endpoint and necessary average speed do not establish interpolation, overshoot, peak speed or acceleration',
            'v4 hand geometry, table, other obstacles and self-collision are not checked',
            'the model is not invoked; this fixed wrist probe is not an SmolVLA action',
            'no staging, runtime task loading, ROS communication, cancel or physical stop is validated',
            'task is only a local candidate; do not install or run without a separately reviewed supervisor and gates',
        ],
    }


def validate(bundle, urdf_text, transmissions_text):
    if not isinstance(bundle, dict):
        raise ValueError('invalid_bundle')
    section = bundle.get('input')
    if not isinstance(section, dict):
        raise ValueError('invalid_bundle_input')
    sample = section.get('canonical_joint_state')
    expected = prepare(sample, urdf_text, transmissions_text)
    if bundle != expected:
        raise ValueError('bundle_mismatch')
    return {'schema': bundle['schema'], 'task_name': bundle['candidate']['task_name'],
            'all_endpoints_inside_nominal_sps_limits': bundle['all_endpoints_inside_nominal_sps_limits'],
            'all_endpoints_satisfy_diagnostic_margin': bundle['all_endpoints_satisfy_diagnostic_margin'],
            'physical_control_qualified': False, 'movement_commands': 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--state', type=Path, help='freshly captured named JointState JSON')
    mode.add_argument('--check', type=Path, help='verify a previously generated manifest')
    mode.add_argument('--run', action='store_true', help='physical dispatch is not implemented')
    parser.add_argument('--urdf', type=Path, help='native URDF snapshot')
    parser.add_argument('--transmissions', type=Path, help='SPS transmissions YAML snapshot')
    parser.add_argument('--output', type=Path, help='new output directory')
    args = parser.parse_args(argv)
    if args.run:
        print('BLOCKED: this local builder cannot connect or dispatch', file=sys.stderr)
        return 2
    try:
        if args.urdf is None or args.transmissions is None:
            raise ValueError('--urdf_and_transmissions_required')
        # Preserve CRLF bytes exactly. Text-mode universal newline conversion
        # would silently change the hash relative to the installed URDF.
        urdf_text = args.urdf.read_bytes().decode('utf-8')
        transmissions_text = args.transmissions.read_bytes().decode('utf-8')
        if args.check:
            if args.output is not None:
                raise ValueError('--output_not_supported_with_check')
            bundle = json.loads(args.check.read_text(encoding='utf-8'))
            result = validate(bundle, urdf_text, transmissions_text)
        else:
            if args.output is None:
                raise ValueError('--output_required')
            state = json.loads(args.state.read_text(encoding='utf-8'))
            bundle = prepare(state, urdf_text, transmissions_text)
            args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
            with (args.output / 'task.xml').open('x', encoding='utf-8') as f:
                f.write(bundle['candidate']['xml'])
            with (args.output / 'manifest.json').open('x', encoding='utf-8') as f:
                json.dump(bundle, f, indent=2, allow_nan=False)
                f.write('\n')
            result = validate(bundle, urdf_text, transmissions_text)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError, ET.ParseError, yaml.YAMLError) as exc:
        print('PREPARATION_FAILED: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
