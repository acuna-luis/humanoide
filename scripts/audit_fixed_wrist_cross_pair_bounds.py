#!/usr/bin/env python3
"""Conditional interval bounds for the existing synthetic AABB cross-pair sweep."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from audit_clamp_pessimistic_screen import URDF, ARCHIVE, fk


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    report = json.loads(a.input.read_text())
    generator = Path(__file__).with_name('audit_fixed_wrist_arm_body.py')
    for f in (URDF, ARCHIVE, Path(fk.__file__), generator):
        if report['source_sha256'].get(str(f)) != hashlib.sha256(f.read_bytes()).hexdigest():
            raise ValueError('source_mismatch')
    if report['status'] != 'SAMPLED_AABB_SCREEN_NOT_FULL_COLLISION_VALIDATION' or report['samples_per_side'] != 242:
        raise ValueError('unexpected_sampling_contract')
    joints, boxes, _ = fk.load_robot(URDF, ARCHIVE)
    q = {j['name']: 0.0 for j in joints if j['type'] != 'fixed'}
    poses = fk.forward_kinematics(joints, q)
    # Verified generator uses 121 uniformly spaced postures per direction over .6 rad.
    half_step = .6/120/2
    parents = {j['child']: j['parent'] for j in joints}

    def descendant(link, ancestor):
        while link != ancestor and link in parents:
            link = parents[link]
        return link == ancestor

    results = []
    for side in report['sides']:
        pivot_link = side['side']+'_shoulder_roll_link'
        pivot = poses[pivot_link][:3, 3]
        for item in side['minima']:
            moving, fixed = item['pair']
            if not descendant(moving, pivot_link) or descendant(fixed, pivot_link):
                raise ValueError('not_one_rigid_mover')
            # Enclosing-box corner radius bounds every point of enclosed geometry.
            corners = fk.apply(fk.corners(*boxes[moving]), poses[moving])
            radius = float(np.max(np.linalg.norm(corners-pivot, axis=1)))
            loss = radius*half_step
            lower = item['gap_m']-loss
            results.append(dict(side=side['side'], pair=item['pair'],
                sampled_aabb_gap_m=item['gap_m'], radius_bound_m=radius,
                between_sample_loss_m=loss, conditional_surface_lower_bound_m=lower,
                result='CONDITIONAL_SEPARATION' if lower > 0 else 'REQUIRES_REFINEMENT'))
    output = dict(status='PARTIAL_CROSS_PAIR_INTERVAL_BOUNDS', results=results,
        positive_count=sum(r['conditional_surface_lower_bound_m'] > 0 for r in results),
        unresolved=[r for r in results if r['conditional_surface_lower_bound_m'] <= 0],
        missing_geometry=report['missing_geometry'], half_sample_step_rad=half_step,
        assumptions=['generator_sampling_contract_verified_by_hash',
                     'correct_rigid_URDF_enclosures_and_numerical_FK',
                     'only_one_shoulder_rotates_all_other_joints_fixed_zero'],
        physical_authorized=False, whole_robot_collision_validated=False,
        robot_connections=0, movement_commands=0,
        source_sha256={str(f): hashlib.sha256(f.read_bytes()).hexdigest()
                       for f in (a.input, generator, URDF, ARCHIVE, Path(fk.__file__), Path(__file__))})
    with a.output.open('x') as out:
        json.dump(output, out, indent=2, allow_nan=False)
        out.write('\n')
    print(json.dumps(dict(positive=output['positive_count'], total=len(results),
                         unresolved=output['unresolved'])))


if __name__ == '__main__':
    main()
