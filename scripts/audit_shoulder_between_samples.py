#!/usr/bin/env python3
"""Conditional rigid surface separation bound; not a physical clearance gate."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import numpy as np
from audit_clamp_pessimistic_screen import URDF, ARCHIVE, fk
import analyze_vla_clearance_guards_e6_0d as distance
import analyze_vla_near_pair_mesh_e6_0c as mesh


def lower_bound(samples, radius):
    if not math.isfinite(radius) or radius < 0 or len(samples) < 2:
        raise ValueError('invalid_radius_or_sampling')
    angles = [r['angle_rad'] for r in samples]
    ds = [r['surface_distance_m'] for r in samples]
    if any(type(x) not in (int, float) or not math.isfinite(x) for x in angles+ds):
        raise ValueError('invalid_sample')
    if any(d < 0 for d in ds) or any(a <= b for a, b in zip(angles, angles[1:])):
        raise ValueError('invalid_distance_or_order')
    step = max(a-b for a, b in zip(angles, angles[1:]))
    # Every angle is at most step/2 from a sampled endpoint. Arc length bounds
    # displacement of every vertex and thus every point of a triangle.
    loss = radius*step/2
    return dict(max_step_rad=step, motion_loss_bound_m=loss,
                sampled_minimum_m=min(ds), conditional_surface_lower_bound_m=min(ds)-loss)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    report = json.loads(a.input.read_text())
    if report['status'] != 'SAMPLED_THREE_PAIR_EXIT_RETURN_ONLY':
        raise ValueError('wrong_source')
    for f in (URDF, ARCHIVE, Path(fk.__file__), Path(distance.__file__), Path(mesh.__file__)):
        if report['source_sha256'].get(str(f)) != hashlib.sha256(f.read_bytes()).hexdigest():
            raise ValueError('source_changed_since_sampling')
    joints, _, triangles = fk.load_robot(URDF, ARCHIVE)
    q = {j['name']: 0.0 for j in joints if j['type'] != 'fixed'}
    poses = fk.forward_kinematics(joints, q)
    parents = {j['child']: j['parent'] for j in joints}

    def descendant(link, ancestor):
        while link != ancestor and link in parents:
            link = parents[link]
        return link == ancestor

    rows = []
    for row in report['results']:
        link, target = row['pair']
        joint = next(j for j in joints if j['name'] == link[0]+'_shoulder_roll_joint')
        if target != 'torso_link' or not descendant(link, joint['child']) or descendant(target, joint['child']):
            raise ValueError('not_one_rigid_mover_against_fixed_torso')
        samples = row['samples']
        if abs(samples[0]['angle_rad']) > 1e-12 or abs(samples[-1]['angle_rad']+.6) > 1e-12:
            raise ValueError('unexpected_path_endpoints')
        pivot = poses[joint['child']][:3, 3]
        vertices = fk.apply(triangles[link].reshape(-1, 3), poses[link])
        radius = float(np.max(np.linalg.norm(vertices-pivot, axis=1)))
        rows.append(dict(pair=row['pair'], pivot_radius_bound_m=radius,
                         **lower_bound(samples, radius)))
    result = dict(status='CONDITIONAL_RIGID_SURFACE_BOUND_ONLY', results=rows,
                  basis='d(theta)>=min(sample_distances)-R*max_step/2',
                  assumptions=['sample_surface_distances_numerically_correct',
                               'exact_rigid_URDF_meshes_and_single_joint_rotation',
                               'all_other_joints_fixed_at_synthetic_zero'],
                  numerical_error_certified=False, solid_containment_tested=False,
                  physical_authorized=False, robot_connections=0, movement_commands=0,
                  not_covered=['mesh_installation_error','clamps','environment','braking','tracking','missing_geometry'],
                  source_sha256={str(f): hashlib.sha256(f.read_bytes()).hexdigest()
                                 for f in (a.input, Path(__file__), URDF, ARCHIVE)})
    with a.output.open('x') as out:
        json.dump(result, out, indent=2, allow_nan=False)
        out.write('\n')
    print(json.dumps(rows))


if __name__ == '__main__':
    main()
