#!/usr/bin/env python3
"""Offline E6.1 endpoint and kinematic dependency audit; never authorizes motion."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / 'scripts/vla/runtime'
GROUPS = {
    'head': ('head_yaw_joint', 'head_pitch_joint'),
    'lifter': ('lifter_pitch_1_joint', 'lifter_pitch_2_joint', 'lifter_pitch_3_joint'),
    'waist': ('waist_yaw_joint',),
}


def finite(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('finite JSON number required')
    return float(value)


def named_state(message, order):
    names = message['name']
    if (not isinstance(names, list) or any(not isinstance(n, str) for n in names)
            or len(names) != len(set(names))):
        raise ValueError('invalid or duplicate joint names')
    if len(message['position']) != len(names) or len(message['velocity']) != len(names):
        raise ValueError('incomplete joint state')
    positions = dict(zip(names, map(finite, message['position']), strict=True))
    velocities = dict(zip(names, map(finite, message['velocity']), strict=True))
    if not set(order) <= set(names):
        raise ValueError('missing required joints')
    if max(abs(velocities[n]) for n in order) > .01:
        raise ValueError('reference was not stationary')
    return {n: positions[n] for n in order}


def targets(xml):
    root = ET.fromstring(xml)
    actions = root.findall('.//Action')
    if len(actions) != 3:
        raise ValueError('exactly three body actions required')
    result = {}
    seen = set()
    for action in actions:
        group = action.get('type')
        if (group not in GROUPS or group in seen or action.get('ID') != 'MetaMove'
                or action.get('location') != 'single' or action.get('name') is not None):
            raise ValueError('unexpected action/group')
        duration = float(action.get('duration', 'nan'))
        if duration != 12.:
            raise ValueError('expected accepted 12 second design')
        values = [finite(float(x.strip())) for x in action.get('joint_angles', '').split(';')]
        if len(values) != len(GROUPS[group]):
            raise ValueError('unexpected group dimension')
        result.update(zip(GROUPS[group], values, strict=True))
        seen.add(group)
    return result


def ancestors(link, parents):
    path = set()
    visited = set()
    while link in parents:
        if link in visited:
            raise ValueError('cyclic kinematic tree')
        visited.add(link)
        parent, joint = parents[link]
        path.add(joint)
        link = parent
    return path, link


def relative_movers(first, second, parents, moving):
    a, root_a = ancestors(first, parents)
    b, root_b = ancestors(second, parents)
    if root_a != root_b:
        raise ValueError('disconnected links')
    return sorted((a ^ b) & set(moving))


def conditional_variable_pair_screen(joints_states, segments, intervals):
    """Conservative sphere/AABB bounds; unknown mounting errors stay assumptions."""
    import numpy as np
    from clamp_work_model import load, CONTRACT
    from audit_clamp_orientation_bound import audit as radius_audit
    from audit_clamp_continuous_routes import travel_bound
    from audit_clamp_pessimistic_screen import fk, URDF, ARCHIVE
    if type(intervals) is not int or intervals < 2:
        raise ValueError('at least two intervals required')
    joints, boxes, _, profile = load()
    zeros = {j['name']: 0. for j in joints if j['type'] != 'fixed'}
    corners = {n: fk.corners(*b) for n, b in boxes.items()}
    reach = sum(np.linalg.norm(j['origin'][:3, 3]) for j in joints)
    reach += max(np.linalg.norm(v, axis=1).max() for v in corners.values())
    nominal = radius_audit(json.loads(CONTRACT.read_text()))['nominal_radius_m']
    records = []
    for (start, end), segment in zip(joints_states, segments, strict=True):
        pairs = [(s, n) for s in ('L', 'R') for n in boxes
                 if segment['relative_motion_dependencies'][s][n]]
        minima = {pair: float('inf') for pair in pairs}
        delta = {n: end[n]-start[n] for n in start}
        half_travel = travel_bound({n: d/(2*intervals) for n, d in delta.items()}, joints, reach)
        for i in range(intervals):
            t = (i+.5)/intervals
            q = {**zeros, **{n: start[n]+t*d for n, d in delta.items()}}
            poses = fk.forward_kinematics(joints, q)
            for pair in pairs:
                side, link = pair
                center = poses[side+'_sixforce_link'][:3, 3]
                pose = poses[link]
                local = pose[:3, :3].T @ (center-pose[:3, 3])
                low, high = boxes[link]
                distance = np.linalg.norm(np.maximum(np.maximum(low-local, local-high), 0))
                minima[pair] = min(minima[pair], float(distance-2*half_travel))
        records.append(dict(direction=segment['direction'], intervals=intervals,
            half_cell_point_travel_bound_m=float(half_travel),
            cases=[dict(assumed_center_error_m=error, assumed_geometry_reserve_m=.01,
                sphere_radius_m=nominal+error+.01,
                pairs=[dict(clamp=s, link=n, gap_lower_bound_m=value-nominal-error-.01)
                       for (s, n), value in minima.items()]) for error in (.01, .025, .05, .075)],
            missing_variable_geometry={s: [n for n, moving in links.items() if moving and n not in boxes]
                                       for s, links in segment['relative_motion_dependencies'].items()}))
    return dict(status='CONDITIONAL_SPHERE_BOUNDS_NOT_PHYSICAL_CLEARANCE',
        center_assumption='sixforce origin with hypothetical bounded error, not registered mount',
        curves='joint-linear synchronized interpolation between supplied endpoints; not vendor law',
        other_model_joints='explicit synthetic zero',
        fixed_relative_pairs='not screened; initial clearance still required',
        nominal_radius_m=nominal, records=records,
        source_sha256={str(f): hashlib.sha256(f.read_bytes()).hexdigest()
                      for f in (CONTRACT, URDF, ARCHIVE, Path(fk.__file__),
                                ROOT/'scripts/clamp_work_model.py',
                                ROOT/'scripts/audit_clamp_continuous_routes.py',
                                ROOT/'scripts/audit_clamp_orientation_bound.py')})


def audit(snapshot_path, urdf_path, screen_intervals=0):
    contract_path = RUNTIME / 'cruzr_s2_vla_ready_entry_transition_e6_1c.json'
    contract = json.loads(contract_path.read_text())
    order = contract['joint_order']
    if len(order) != 20 or len(set(order)) != 20:
        raise ValueError('invalid contract joint order')
    envelope = json.loads(snapshot_path.read_text())
    if envelope.get('returncode') != 0:
        raise ValueError('unsuccessful archived read')
    q = named_state(json.loads(envelope['stdout']), order)
    ready_error = max(abs(q[n]-finite(v)) for n, v in zip(
        order, contract['observed_ready_reference_20d_rad'], strict=True))
    if ready_error > .01:
        raise ValueError('archived state not READY')
    paths = [RUNTIME / 'tasks' / ('s2_vla_e6_1c_'+name+'_preview.xml')
             for name in ('ready_to_entry', 'entry_to_ready')]
    entry, recovery = [targets(f.read_text()) for f in paths]
    arms = set(contract['uncommanded_arm_joint_names'])
    if len(arms) != 14 or set(entry) & arms or set(recovery) & arms:
        raise ValueError('unexpected arm command')
    entry_q = {**q, **entry}
    return_q = {**entry_q, **recovery}
    dataset_error = max(abs(entry_q[n]-finite(v)) for n, v in zip(
        order, contract['frozen_dataset_entry_20d_rad'], strict=True))
    if dataset_error > .01:
        raise ValueError('candidate ENTRY outside frozen-frame tolerance')
    tree = ET.parse(urdf_path).getroot()
    model_links = {link.get('name') for link in tree.findall('link')}
    parents = {j.find('child').get('link'): (j.find('parent').get('link'), j.get('name'))
               for j in tree.findall('joint')}
    model_joints = {j.get('name'): j for j in tree.findall('joint')}
    segments = []
    for name, start, end in [('READY_TO_ENTRY', q, entry_q), ('ENTRY_TO_READY', entry_q, return_q)]:
        moving = {n for n in order if start[n] != end[n]}
        for n in order:
            joint = model_joints[n]
            limit = joint.find('limit')
            if joint.get('type') != 'revolute' or limit is None:
                raise ValueError('expected revolute joint with position limits: '+n)
            low, high = float(limit.get('lower')), float(limit.get('upper'))
            if not all(math.isfinite(x) for x in (low, high)) or low > high:
                raise ValueError('invalid URDF limit')
            if not all(low <= state[n] <= high for state in (start, end)):
                raise ValueError('endpoint outside URDF limit: '+n)
        delta = max(abs(end[n]-start[n]) for n in order)
        dependencies = {side: {link: relative_movers(side+'_sixforce_link', link, parents, moving)
                              for link in sorted(model_links)
                              if not any(t in link for t in ('pgc', 'finger'))}
                        for side in ('L', 'R')}
        segments.append(dict(direction=name, moving_joints=sorted(moving),
            position_limits_pass_for_monotone_curve=True,
            hypothetical_quintic_velocity_max_rad_s=1.875*delta/12,
            hypothetical_quintic_acceleration_max_rad_s2=(10/math.sqrt(3))*delta/12**2,
            relative_motion_dependencies=dependencies))
    sources = [Path(__file__), snapshot_path, urdf_path, contract_path, *paths]
    result = dict(status='ENDPOINT_AND_KINEMATIC_DEPENDENCIES_ONLY', physical_authorized=False,
        robot_connections=0, movement_commands=0, reference_is_archived_not_live=True,
        archived_ready_error_rad=ready_error, projected_entry_dataset_error_rad=dataset_error,
        return_ready_reference_error_rad=max(abs(return_q[n]-finite(v)) for n, v in zip(
            order, contract['observed_ready_reference_20d_rad'], strict=True)), segments=segments,
        proof='Relative transform depends only on joints outside the shared ancestor path. '
              'No moving joints there implies exact invariance under rigid fixed arm/mount assumptions.',
        limitations=['No clearance computed, no physical clamp registration inferred.',
            'Constant relative transform preserves initial geometry; does not prove initial clearance.',
            'Absent arm commands do not demonstrate zero physical drift or flexion.',
            'No mass, stability, external scene, actual interpolator, force or braking validation.',
            '12 second quintic is a design hypothesis, not measured Motion behavior.'],
        source_sha256={str(f): hashlib.sha256(f.read_bytes()).hexdigest() for f in sources})
    if screen_intervals:
        from audit_clamp_pessimistic_screen import URDF
        if urdf_path.read_bytes() != URDF.read_bytes():
            raise ValueError('screen and dependency URDF must match')
        result['conditional_screen'] = conditional_variable_pair_screen(
            [(q, entry_q), (entry_q, return_q)], segments, screen_intervals)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ready-snapshot', type=Path, required=True)
    parser.add_argument('--urdf', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--screen-intervals', type=int, default=0)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    if args.screen_intervals < 0:
        raise ValueError('nonnegative screen interval count required')
    result = audit(args.ready_snapshot, args.urdf, args.screen_intervals)
    with args.output.open('x') as f:
        json.dump(result, f, indent=2, allow_nan=False)
    print(result['status'])
    print('projected_entry_dataset_error_rad=', result['projected_entry_dataset_error_rad'])


if __name__ == '__main__':
    main()
