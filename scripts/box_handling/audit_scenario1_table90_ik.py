#!/usr/bin/env python3
"""Conditional URDF endpoint IK study, not a Motion or collision certificate."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation, Slerp

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/vla'))
import analyze_vla_fixture_collision_e4_1c as fk


def audit(urdf, *, constrain_torso_position=True, samples_per_segment=1, initial_state=None,
          continuity_weight=0.):
    tree = ET.parse(urdf).getroot()
    joints = []
    names, low, high = [], [], []
    for element in tree.findall('joint'):
        item = dict(name=element.get('name'), type=element.get('type'),
                    parent=element.find('parent').get('link'), child=element.find('child').get('link'),
                    origin=fk.origin_transform(element.find('origin')),
                    axis=fk.xyz(element.find('axis').get('xyz') if element.find('axis') is not None else None, (1, 0, 0)))
        joints.append(item)
        limit = element.find('limit')
        if item['name'].startswith(('L_', 'R_', 'lifter_pitch_', 'waist_yaw')) and limit is not None:
            a, b = float(limit.get('lower')), float(limit.get('upper'))
            if a < b:
                names.append(item['name']); low.append(a); high.append(b)
    by_child = {j['child']: j for j in joints}
    link_names = {e.get('name') for e in tree.findall('link')}
    roots = link_names-set(by_child)
    if len(roots) != 1:
        raise ValueError('Expected one URDF root')
    root_link = next(iter(roots))
    links = (('left_hand', 'right_hand', 'torso') if 'left_hand' in link_names
             else ('L_hand_link', 'R_hand_link', 'torso_link'))
    left_link, right_link, torso_link = links
    chains = {}
    for link in links:
        chain = []
        child = link
        while child in by_child:
            joint = by_child[child]; chain.append(joint); child = joint['parent']
        if child != root_link:
            raise ValueError('Disconnected model')
        chains[link] = chain[::-1]

    def pose(chain, state):
        result = np.eye(4)
        for j in chain:
            motion = np.eye(4)
            if j['type'] in ('revolute', 'continuous'):
                motion[:3, :3] = fk.rotation_axis(j['axis'], state.get(j['name'], 0.))
            elif j['type'] != 'fixed':
                raise ValueError('Unsupported joint type')
            result = result @ j['origin'] @ motion
        return result

    hand_rotation = Rotation.from_quat([.5, .5, -.5, .5]).as_matrix()
    rows = []
    seed = np.clip(np.zeros(len(names)), np.array(low)+1e-8, np.array(high)-1e-8)
    if initial_state is not None:
        seed = np.array([initial_state[name] for name in names])
        if not np.isfinite(seed).all() or (seed < low).any() or (seed > high).any():
            raise ValueError('Initial named joints outside URDF limits')
    measured_seed = seed.copy()
    rng = np.random.default_rng(90)
    for height, label in ((.45, 'vendor_reference'), (.90, 'table90')):
        if initial_state is not None:
            seed = measured_seed.copy()
        endpoints = np.array([(6, .75, height+.20, 0., 1.2),
                              (10, .95, height+.20, .3, 1.2),
                              (12, .95, height, .3, 1.0)])
        points = [endpoints[0]]
        if initial_state is not None:
            state = dict(zip(names, measured_seed))
            start_poses = {link: pose(chains[link], state) for link in links}
            for u in np.linspace(0, 1, samples_per_segment+1)[:-1]:
                hand_z = float((1-u)*start_poses[left_link][2, 3]+u*(height+.20))
                hand_x = float((1-u)*start_poses[left_link][0, 3]+u*.75)
                points.insert(len(points)-1, np.array([6*u, hand_x, hand_z, 0., 1.2]))
        for start, end in zip(endpoints, endpoints[1:]):
            points.extend(start+(end-start)*u for u in np.linspace(0, 1, samples_per_segment+1)[1:])
        for timestamp, x, z, torso_x, torso_z in points:
            targets = {left_link: (np.array([x, .285, z]), hand_rotation),
                       right_link: (np.array([x, -.285, z]), hand_rotation),
                       torso_link: (np.array([torso_x, 0., torso_z]), np.eye(3))}
            if initial_state is not None and timestamp <= 6:
                u = timestamp/6
                final_targets = {left_link: (np.array([.75, .285, height+.20]), hand_rotation),
                                 right_link: (np.array([.75, -.285, height+.20]), hand_rotation),
                                 torso_link: (np.array([0., 0., 1.2]), np.eye(3))}
                for link, (position, rotation) in final_targets.items():
                    start = start_poses[link]
                    orientation = Slerp([0, 1], Rotation.from_matrix([start[:3, :3], rotation]))([u]).as_matrix()[0]
                    targets[link] = ((1-u)*start[:3, 3]+u*position, orientation)
            def residual(q):
                state = dict(zip(names, q)); errors = []
                for link, (position, rotation) in targets.items():
                    actual = pose(chains[link], state)
                    if link != torso_link or constrain_torso_position:
                        errors.extend(actual[:3, 3]-position)
                    errors.extend(Rotation.from_matrix(rotation.T @ actual[:3, :3]).as_rotvec())
                if continuity_weight:
                    errors.extend(continuity_weight*(q-seed))
                return np.array(errors)
            best = None
            for trial in (seed, *[rng.uniform(low, high) for _ in range(3)]):
                solution = least_squares(residual, trial, bounds=(low, high), max_nfev=200,
                                         ftol=1e-9, xtol=1e-9, gtol=1e-9)
                if best is None or np.linalg.norm(solution.fun) < np.linalg.norm(best.fun):
                    best = solution
                if np.linalg.norm(solution.fun) < 1e-5:
                    break
            seed = best.x
            state = dict(zip(names, best.x)); errors = {}
            for link, (position, rotation) in targets.items():
                actual = pose(chains[link], state)
                errors[link] = dict(position_error_m=float(np.linalg.norm(actual[:3, 3]-position)),
                                   orientation_error_rad=float(np.linalg.norm(Rotation.from_matrix(rotation.T @ actual[:3, :3]).as_rotvec())))
            rows.append(dict(configuration=label, timestamp_s=timestamp, errors=errors,
                             joint_state=state, endpoint_fit=all(
                                 (e['position_error_m'] < .001 or (link == torso_link and not constrain_torso_position))
                                 and e['orientation_error_rad'] < .001 for link, e in errors.items())))
    return dict(scope='CONDITIONAL_ENDPOINT_IK_ONLY', physical_approval=False,
                source_urdf_sha256=hashlib.sha256(urdf.read_bytes()).hexdigest(),
                assumptions='YAML ABSOLUTE equals URDF base_link; native named links when available. Not a Motion interpolation certificate.',
                target_links=list(links), samples_per_segment=samples_per_segment,
                root_link=root_link,
                initial_state=initial_state,
                continuity_weight=continuity_weight,
                initial_interpolation='Cartesian linear + quaternion SLERP hypothesis; not native interpolation',
                torso_position_constrained=constrain_torso_position,
                collision_checked=False, continuous_path_checked=False,
                failure_is_not_proof_of_infeasibility=True, rows=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--urdf', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--torso-orientation-only', action='store_true',
                        help='Alternative hypothesis matching torso mask [0,0,0,1,1,1]; not verified in Motion')
    parser.add_argument('--samples-per-segment', type=int, default=1,
                        help='Conditional linear Cartesian samples between 6/10/12 s; not native interpolation')
    parser.add_argument('--initial-joints', type=Path, help='JSON map of fresh named joint positions')
    parser.add_argument('--continuity-weight', type=float, default=0.,
                        help='Regularize proximity to previous solution; conditional numerical study only')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output must be new')
    if not 1 <= args.samples_per_segment <= 100:
        parser.error('samples-per-segment must be between 1 and 100')
    if not np.isfinite(args.continuity_weight) or not 0 <= args.continuity_weight <= 1:
        parser.error('continuity-weight must be finite and between 0 and 1')
    result = audit(args.urdf, constrain_torso_position=not args.torso_orientation_only,
                   samples_per_segment=args.samples_per_segment,
                   initial_state=json.loads(args.initial_joints.read_text()) if args.initial_joints else None,
                   continuity_weight=args.continuity_weight)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2); stream.write('\n')
    for row in result['rows']:
        print(row['configuration'], row['timestamp_s'], row['endpoint_fit'], row['errors'])


if __name__ == '__main__':
    main()
