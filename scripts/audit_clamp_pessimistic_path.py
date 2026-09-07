#!/usr/bin/env python3
"""Sample synthetic historical arm paths offline; never a runtime collision gate."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from audit_clamp_pessimistic_screen import ROOT, ARCHIVE, URDF, fk, point_aabb_distance
from audit_clamp_orientation_bound import audit

READY = ROOT.parent/'Humanoide-vla-evidence/20260903T093145_E6.0A/p14-ready-recovery-contract.json'
CHECKPOINT_ORDER = ('elbow_roll', 'elbow_yaw', 'shoulder_pitch', 'shoulder_roll',
                    'shoulder_yaw', 'wrist_pitch', 'wrist_roll')


def named_arms(values):
    if (not isinstance(values, list) or len(values) != 14
            or any(type(x) not in (int, float) or not math.isfinite(x) for x in values)):
        raise ValueError('invalid_checkpoint_order_vector')
    names = [f'{side}_{name}_joint' for side in ('L', 'R') for name in CHECKPOINT_ORDER]
    return dict(zip(names, values, strict=True))


def stages(joints, ready, schedule):
    if schedule not in ('synchronous', 'L_then_R', 'R_then_L'):
        raise ValueError('unknown_schedule')
    zero = {j['name']: 0.0 for j in joints if j['type'] != 'fixed'}
    points = [('synthetic_zero', zero)]
    path = ready['arm_path_checkpoint_order']
    for name in ('staging_preposition', 'waypoint_a', 'ready_b',
                 'waypoint_a_return', 'staging_preposition_return', 'synthetic_zero_return'):
        target = dict(zero)
        if name != 'synthetic_zero_return':
            arms = named_arms(path[name.removesuffix('_return')])
            if not arms.keys() <= zero.keys():
                raise ValueError('arm_joint_not_in_URDF')
            target.update(arms)
        if schedule == 'synchronous':
            points.append((name, target))
        else:
            intermediate = dict(points[-1][1])
            first = schedule[0]+'_'
            intermediate.update({k: v for k, v in target.items() if k.startswith(first)})
            points.append((name+'_'+schedule[0]+'_first', intermediate))
            points.append((name, target))
    return points


def interpolated(start, end, count):
    if start.keys() != end.keys() or type(count) is not int or count < 2:
        raise ValueError('inconsistent_states_or_sampling')
    if any(type(v) not in (int, float) or not math.isfinite(v) for state in (start, end) for v in state.values()):
        raise ValueError('nonfinite_or_invalid_state')
    for alpha in np.linspace(0, 1, count):
        yield float(alpha), {k: (1-float(alpha))*start[k]+float(alpha)*end[k] for k in start}


def summarize_minima(minima, radius):
    result = {}
    for category, row in minima.items():
        multiplier = 2 if category == 'clamp_clamp' else 1
        gap = row['distance_m']-multiplier*radius
        result[category] = dict(row, envelope_gap_m=gap,
            result='OVERLAP_INCONCLUSIVE' if gap <= 0 else 'NO_OVERLAP_AT_SAMPLES_CONDITIONAL')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--samples-per-segment', type=int, default=101)
    args = parser.parse_args()
    if not 2 <= args.samples_per_segment <= 1001:
        parser.error('samples-per-segment must be 2..1001')
    if args.output.exists():
        raise FileExistsError(args.output)
    contract_path = ROOT/'config/clamp_mount_requalification.json'
    nominal = audit(json.loads(contract_path.read_text()))
    ready = json.loads(READY.read_text())
    joints, boxes, _ = fk.load_robot(URDF, ARCHIVE)
    body = sorted(k for k in boxes if not k.startswith(('L_', 'R_')))
    arm_links = {side: [f'{side}_{name}_link' for name in CHECKPOINT_ORDER]+[f'{side}_sixforce_link']
                 for side in ('L', 'R')}
    missing_arm_geometry = [link for names in arm_links.values() for link in names if link not in boxes]
    # Diagnostic partial coverage only. Never treat missing geometry as clearance.
    arm_links = {side: [k for k in names if k in boxes] for side, names in arm_links.items()}
    reference_exclusions = {side: [f'{side}_wrist_roll_link', f'{side}_sixforce_link'] for side in ('L', 'R')}
    tested = sorted(set(body+arm_links['L']+arm_links['R']))
    corners = {k: fk.corners(*boxes[k]) for k in tested}
    records = []
    sample_total = 0
    for schedule in ('synchronous', 'L_then_R', 'R_then_L'):
        points = stages(joints, ready, schedule)
        for (start_name, start), (end_name, end) in zip(points, points[1:]):
            minima = {}
            for alpha, state in interpolated(start, end, args.samples_per_segment):
                sample_total += 1
                poses = fk.forward_kinematics(joints, state)
                world_boxes = {}
                for link in tested:
                    world = fk.apply(corners[link], poses[link])
                    world_boxes[link] = (world.min(axis=0), world.max(axis=0))
                centers = {side: poses[f'{side}_sixforce_link'][:3, 3] for side in ('L', 'R')}

                def record(category, distance, pair):
                    if category not in minima or distance < minima[category]['distance_m']:
                        minima[category] = {'distance_m': float(distance), 'pair': pair,
                                             'segment_fraction': alpha, 'joint_state': state}

                for side in ('L', 'R'):
                    other = 'R' if side == 'L' else 'L'
                    groups = {'body': body,
                              'same_arm_non_attachment': [k for k in arm_links[side] if k not in reference_exclusions[side]],
                              'opposite_arm': arm_links[other]}
                    for category, links in groups.items():
                        for link in links:
                            record(side+'_'+category, point_aabb_distance(centers[side], *world_boxes[link]),
                                   [side+'_clamp_sphere', link])
                record('clamp_clamp', math.dist(centers['L'], centers['R']), ['L_clamp_sphere', 'R_clamp_sphere'])
            records.append({'schedule': schedule, 'segment': start_name+' -> '+end_name,
                            'minima_before_inflation': minima})
        print(schedule+' sampled', flush=True)
    cases = []
    for error in (.010, .025, .050, .075):
        radius = nominal['nominal_radius_m']+error+.010
        segments = [{'schedule': r['schedule'], 'segment': r['segment'],
                     'categories': summarize_minima(r['minima_before_inflation'], radius)} for r in records]
        cases.append({'assumed_center_error_m': error, 'assumed_geometry_reserve_m': .010,
                      'candidate_radius_m': radius, 'segments': segments})
    result = {'status': 'SAMPLED_HISTORICAL_PATH_SENSITIVITY_NOT_PHYSICAL_VALIDATION',
              'samples_per_segment': args.samples_per_segment, 'sample_total_including_repeated_endpoints': sample_total,
              'cases': cases, 'body_links': body, 'arm_links': arm_links,
              'missing_arm_collision_geometry': missing_arm_geometry,
              'full_arm_geometry_coverage': not missing_arm_geometry,
              'own_attachment_reference_exclusions_not_an_ACM': reference_exclusions,
              'nominal_radius_m': nominal['nominal_radius_m'],
              'assumptions': ['historical P14 arm vectors mapped by explicit checkpoint joint names',
                              'all non-arm joints explicitly held at synthetic zero, not actual READY',
                              'linear joint interpolation in normalized segment fraction; no durations',
                              'sync and two fully serialized arm orders; not all possible group delays',
                              'center at URDF sixforce origin with unverified radial errors'],
              'not_covered': ['continuous swept volume between samples', 'real Motion law, timing, braking and tracking error',
                              'real initial posture and scene', 'fixtures, payload, environment',
                              'arm-arm and arm-body collisions independent of clamps',
                              'own wrist/sensor mounting interface clearance', 'joint/dynamic limits qualification'],
              'selected_operating_profile': None, 'physical_authorized': False,
              'robot_connections': 0, 'movement_commands': 0,
              'source_sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                               (contract_path, READY, URDF, ARCHIVE, Path(__file__), Path(fk.__file__),
                                ROOT/'scripts/audit_clamp_orientation_bound.py',
                                ROOT/'scripts/build_clamp_simplified_model.py',
                                ROOT/'scripts/audit_clamp_pessimistic_screen.py',
                                ROOT/'scripts/audit_clamp_mount_requalification.py')}}
    with args.output.open('x') as out:
        json.dump(result, out, indent=2, allow_nan=False)
        out.write('\n')
    print(result['status'])
    print('samples:', sample_total)
    for case in cases:
        worst = {}
        for segment in case['segments']:
            for name, row in segment['categories'].items():
                if name not in worst or row['envelope_gap_m'] < worst[name]['gap_mm']*.001:
                    worst[name] = {'gap_mm': row['envelope_gap_m']*1000, 'pair': row['pair'],
                                   'segment': segment['segment'], 'schedule': segment['schedule']}
        print(json.dumps({'radius_mm': case['candidate_radius_m']*1000, 'worst': worst}))


if __name__ == '__main__':
    main()
