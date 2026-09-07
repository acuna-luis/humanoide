#!/usr/bin/env python3
"""Offline synthetic shoulder-only diagnostic. No execution or physical approval."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from audit_clamp_pessimistic_screen import ROOT, URDF, ARCHIVE, fk, point_aabb_distance


def relative(parent, child):
    return np.linalg.inv(parent) @ child


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    joints, boxes, _ = fk.load_robot(URDF, ARCHIVE)
    zero = {j['name']: 0.0 for j in joints if j['type'] != 'fixed'}
    body = [k for k in boxes if not k.startswith(('L_', 'R_'))]
    rows = []
    for side in ('L', 'R'):
        reference = None
        errors, distances = [], []
        for angle in np.linspace(0, -.6, 121):
            state = dict(zero)
            state[f'{side}_shoulder_roll_joint'] = float(angle)
            poses = fk.forward_kinematics(joints, state)
            transform = relative(poses[f'{side}_wrist_pitch_link'], poses[f'{side}_sixforce_link'])
            if reference is None:
                reference = transform
            errors.append(float(np.max(np.abs(transform-reference))))
            center = poses[f'{side}_sixforce_link'][:3, 3]
            candidates = []
            for link in body:
                world = fk.apply(fk.corners(*boxes[link]), poses[link])
                candidates.append((point_aabb_distance(center, world.min(axis=0), world.max(axis=0)), link))
            distance, link = min(candidates)
            distances.append(dict(angle_rad=float(angle), center_body_aabb_distance_m=distance, link=link))
        rows.append(dict(side=side, relative_transform_initial=reference.tolist(),
                         max_relative_matrix_component_change=max(errors),
                         rigid_invariance_numerical_check=max(errors) < 1e-12,
                         center_body_distance_samples=distances,
                         center_distance_nondecreasing_at_samples=all(
                             y['center_body_aabb_distance_m'] >= x['center_body_aabb_distance_m']-1e-12
                             for x, y in zip(distances, distances[1:]))))
    result = dict(status='SYNTHETIC_FIXED_WRIST_KINEMATICS_ONLY', sides=rows,
                  initial_state='explicit_URDF_zero_NOT_current_robot',
                  candidate='one_shoulder_roll_0_to_minus_0.6_rad_other_joints_fixed_zero',
                  operator_diagonal_tab_body_distances_m={'L': .174, 'R': .178},
                  measurement_model_residual=None,
                  residual_unavailable_reason='physical_endpoints_not_registered_to_model; no_synchronized_pose',
                  minimum_clearance_lower_bound_m=None,
                  actual_mount_or_clearance_verified=False, physical_authorized=False,
                  robot_connections=0, movement_commands=0,
                  limitations=['rigid_invariance_does_not_prove_initial_clearance',
                               'sensor_origin_distance_is_not_tab_surface_distance',
                               'no_full_arm_body_environment_continuous_collision_check',
                               'no_runtime_tracking_braking_or_load_deformation_validation'],
                  source_sha256={str(f): hashlib.sha256(f.read_bytes()).hexdigest()
                                 for f in (URDF, ARCHIVE, Path(fk.__file__), Path(__file__))})
    with a.output.open('x') as out:
        json.dump(result, out, indent=2, allow_nan=False)
        out.write('\n')
    print(json.dumps([dict(side=r['side'], matrix_change=r['max_relative_matrix_component_change'],
                          first_center_distance=r['center_body_distance_samples'][0]['center_body_aabb_distance_m'],
                          last_center_distance=r['center_body_distance_samples'][-1]['center_body_aabb_distance_m'],
                          nondecreasing=r['center_distance_nondecreasing_at_samples']) for r in rows]))


if __name__ == '__main__':
    main()
