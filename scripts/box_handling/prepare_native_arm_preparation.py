#!/usr/bin/env python3
"""Build an additive native arm preparation and measured return, locally only.

Copies exactly the selected original three-second MetaMove, then returns that
arm to the measured HOME reference in six seconds. No SSH, installation, SDK
player, perception, MetaClamp, head, lifter, waist or global HOME command.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

if __package__:
    from .prepare_empty_arm_diagnostic import canonical_state, finite_number, json_object, JOINTS, REQUIRED_JOINTS
else:
    from prepare_empty_arm_diagnostic import canonical_state, finite_number, json_object, JOINTS, REQUIRED_JOINTS


ROOT = Path(__file__).resolve().parents[2]
SOURCE_XML = ROOT/'vendor/ubtech/cruzr_s2/snapshot_20260916/motion/tasks/Singapore/separate_right_cruzr.xml'
SOURCE_SHA256 = '4ba2515ba030f7f1483eed704ce68e0d888ac29754bef1645908fb9f96345e0b'
TASK_ROOT = '/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/'
OUTBOUND_S = 3.
RETURN_S = 6.


def native_action(source_xml, arm):
    if hashlib.sha256(source_xml.encode()).hexdigest() != SOURCE_SHA256:
        raise ValueError('NATIVE_PREPARATION_SOURCE_SHA256_MISMATCH')
    if arm not in ('right', 'left'):
        raise ValueError('Arm must be right or left')
    root = ET.fromstring(source_xml)
    matches = [node for node in root.findall('./BehaviorTree/Sequence/Parallel/Action')
               if node.get('ID') == 'MetaMove' and node.get('type') == 'arm' and node.get('location') == arm]
    if len(matches) != 1:
        raise ValueError('Native preparation arm action is missing or ambiguous')
    action = copy.deepcopy(matches[0])
    if set(action.attrib) != {'ID', 'type', 'location', 'joint_angles', 'duration'} or list(action):
        raise ValueError('Unexpected native arm action contract')
    if float(action.get('duration')) != OUTBOUND_S:
        raise ValueError('Original native preparation duration changed')
    target = [finite_number(float(value.strip()), 'Native angle') for value in action.get('joint_angles').split(';')]
    if len(target) != 7:
        raise ValueError('Native arm preparation must contain exactly seven angles')
    return action, target


def nominal_limits(urdf_text, initial, target, moving_names):
    """Check endpoints and necessary average speed, not unknown native peaks.

    Coordinatewise monotone interpolation would keep the entire joint path
    inside these endpoint intervals. The actual native interpolation and its
    tracking/overshoot are not certified by this check.
    """
    model = ET.fromstring(urdf_text)
    if model.tag != 'robot':
        raise ValueError('Expected native URDF robot root')
    joints = model.findall('joint')
    names = [node.get('name') for node in joints]
    if len(names) != len(set(names)):
        raise ValueError('Duplicate URDF joint names')
    by_name = dict(zip(names, joints))
    limits, omitted = {}, []
    for name in REQUIRED_JOINTS:
        node = by_name.get(name)
        end = target.get(name, initial[name])
        if node is None and name in JOINTS['head'] and name not in moving_names and end == initial[name]:
            omitted.append(name)
            continue
        if node is None or node.get('type') != 'revolute' or node.find('limit') is None:
            raise ValueError('Missing bounded native URDF joint '+name)
        try:
            limit = node.find('limit')
            low, high, speed = [finite_number(float(limit.attrib[key]), 'URDF '+key) for key in ('lower', 'upper', 'velocity')]
        except (KeyError, TypeError) as error:
            raise ValueError('Incomplete native URDF limits '+name) from error
        if low >= high or speed <= 0:
            raise ValueError('Invalid native URDF limits '+name)
        path_low, path_high = min(initial[name], end), max(initial[name], end)
        if not low <= path_low <= path_high <= high:
            raise ValueError('Native URDF position interval violation '+name)
        distance = abs(end-initial[name])
        outbound_average, return_average = distance/OUTBOUND_S, distance/RETURN_S
        if max(outbound_average, return_average) > speed:
            raise ValueError('Native URDF necessary average speed violation '+name)
        limits[name] = dict(lower_rad=low, upper_rad=high, endpoint_interval_rad=[path_low, path_high],
            velocity_limit_rad_s=speed, outbound_average_required_rad_s=outbound_average,
            return_average_required_rad_s=return_average)
    return dict(sha256=hashlib.sha256(urdf_text.encode()).hexdigest(), checked_joint_count=len(limits),
        unmodelled_unchanged_joints=omitted, limits=limits,
        position_check='ENDPOINT_INTERVALS_PASS; full-path claim conditional on coordinatewise monotone interpolation',
        velocity_check='NECESSARY_AVERAGE_ONLY', native_peak_velocity_verified=False,
        native_interpolation_verified=False, collision_checked=False)


def prepare(sample, arm, source_xml, urdf_text):
    """Return new XML and manifest data without any execution or transport."""
    initial = canonical_state(sample)
    outbound, target = native_action(source_xml, arm)
    moving_names = JOINTS[arm+'_arm']
    target_by_name = dict(zip(moving_names, target))
    limits = nominal_limits(urdf_text, initial, target_by_name, moving_names)
    return_q = [initial[name] for name in moving_names]
    root = ET.Element('root', main_tree_to_execute='MainTree')
    tree = ET.SubElement(root, 'BehaviorTree', ID='MainTree')
    sequence = ET.SubElement(tree, 'Sequence', name='native_arm_preparation_diagnostic')
    sequence.append(outbound)
    ET.SubElement(sequence, 'Action', ID='MetaMove', type='arm', location=arm,
                  joint_angles='; '.join(format(value, '.17g') for value in return_q), duration='6')
    ET.indent(root, space='    ')
    text = ET.tostring(root, encoding='unicode')+'\n'
    digest = hashlib.sha256(text.encode()).hexdigest()
    task_name = 'diagnostics/native_arm_preparation_'+arm+'_'+digest[:16]
    manifest = dict(schema='cruzr-native-arm-preparation-v1', status='PREPARED_NOT_INSTALLED_OR_EXECUTED',
        physical_approval=False, robot_connections=0, remote_writes=0, movement_commands=0,
        xml=text,
        source=dict(native_xml_sha256=SOURCE_SHA256,
            native_xml_runtime_path=TASK_ROOT+'Singapore/separate_right_cruzr.xml',
            canonical_header=copy.deepcopy(sample['header']), canonical_joint_state=copy.deepcopy(sample),
            initial_joint_reference_20d={n: initial[n] for n in REQUIRED_JOINTS},
            ignored_extra_axes={n: q for n, q in initial.items() if n not in REQUIRED_JOINTS}, freshness_verified=False),
        candidate=dict(arm=arm, xml_sha256=digest, task_name=task_name, runtime_path=TASK_ROOT+task_name+'.xml',
            selected_native_attributes=copy.deepcopy(outbound.attrib), joint_order=list(moving_names),
            outbound_joint_target_rad=target, return_joint_target_rad=return_q,
            outbound_duration_s=OUTBOUND_S, return_duration_s=RETURN_S, total_nominal_duration_s=9.,
            action_count=2, commands_only_selected_arm=True, commands_head_lifter_waist=False,
            has_metaclamp=False, has_vision=False, has_force_parameters=False, has_global_home=False,
            native_outbound_action_preserved=True), urdf=limits,
        limitations=['Preparation only: no box separation, pickup, left insertion, grasp, payload or bodyback is reproduced',
            'Only the selected-arm MetaMove action is copied; serial/right-only execution differs from the original bimanual Parallel',
            'Full native three-second amplitude is not the earlier two-degree candidate',
            'Necessary average speed within URDF limits does not certify peak speed, acceleration, native interpolation or tracking',
            'Nominal model endpoints/conditional intervals do not certify clamps, swept volume, environment, stopping or current controller limits',
            'Return is a new selected-arm six-second MetaMove to measured reference, not a guaranteed recovery after an interrupted outbound action',
            'No retry, recovery, E-stop manipulation, automatic second-arm execution or installation is implemented',
            'Fresh preflight, explicit admission and postflight remain independent; no synthetic SPS result is provided'])
    return text, manifest


def build(state_path, arm, output, urdf_path, *, source_xml_path=SOURCE_XML):
    state_path, output, urdf_path, source_xml_path = map(Path, (state_path, output, urdf_path, source_xml_path))
    if output.exists():
        raise ValueError('Output directory must be new; refusing overwrite')
    state_raw, source_raw, urdf_raw = state_path.read_bytes(), source_xml_path.read_bytes(), urdf_path.read_bytes()
    xml, manifest = prepare(json_object(state_raw), arm, source_raw.decode(), urdf_raw.decode())
    manifest['source'].update(canonical_path=str(state_path.resolve()), canonical_sha256=hashlib.sha256(state_raw).hexdigest(),
                              native_xml_path=str(source_xml_path.resolve()))
    manifest['urdf'].update(path=str(urdf_path.resolve()), sha256=hashlib.sha256(urdf_raw).hexdigest())
    manifest['builder_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    manifest['candidate']['local_path'] = str((output/'task.xml').resolve())
    output.mkdir(parents=True, mode=0o700, exist_ok=False)
    with (output/'task.xml').open('x') as stream:
        stream.write(xml)
    with (output/'manifest.json').open('x') as stream:
        json.dump(manifest, stream, indent=2, allow_nan=False)
        stream.write('\n')
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--urdf', type=Path, required=True)
    parser.add_argument('--arm', choices=('right', 'left'), required=True)
    parser.add_argument('--output', type=Path, required=True, help='New private local candidate directory')
    parser.add_argument('--source-xml', type=Path, default=SOURCE_XML, help='Pinned native XML; alternative bytes are rejected')
    args = parser.parse_args(argv)
    try:
        manifest = build(args.state, args.arm, args.output, args.urdf, source_xml_path=args.source_xml)
    except (ValueError, OSError, ET.ParseError) as error:
        parser.error(str(error))
    print(json.dumps(dict(status=manifest['status'], candidate=manifest['candidate'],
                         urdf_checked_joint_count=manifest['urdf']['checked_joint_count'], movement_commands=0), indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
