#!/usr/bin/env python3
"""Three shoulder/torso surface pairs at zero or sampled exit, offline."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from audit_clamp_pessimistic_screen import URDF, ARCHIVE, fk
import analyze_vla_clearance_guards_e6_0d as distance
import analyze_vla_near_pair_mesh_e6_0c as mesh


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--samples', type=int, default=1)
    a = p.parse_args()
    if not 1 <= a.samples <= 1001:
        p.error('samples must be 1..1001')
    if a.output.exists():
        raise FileExistsError(a.output)
    tests = [distance.distance_self_test(), distance.randomized_distance_reference_test()]
    joints, _, triangles = fk.load_robot(URDF, ARCHIVE)
    state = {j['name']: 0.0 for j in joints if j['type'] != 'fixed'}
    poses = fk.forward_kinematics(joints, state)
    names = ['L_shoulder_roll_link', 'R_shoulder_roll_link', 'R_shoulder_yaw_link']
    roots = {n: mesh.BvhNode(triangles[n], np.arange(len(triangles[n]), dtype=np.int64))
             for n in names+['torso_link']}
    results = []
    for n in names:
        samples = []
        for index, angle in enumerate(np.linspace(0, -.6, a.samples)):
            q = dict(state)
            q[n[0]+'_shoulder_roll_joint'] = float(angle)
            poses = fk.forward_kinematics(joints, q)
            d, ids, stats = distance.exact_mesh_distance(triangles[n], roots[n], poses[n],
                triangles['torso_link'], roots['torso_link'], poses['torso_link'], mesh, 1e-8)
            samples.append(dict(angle_rad=float(angle), surface_distance_m=d, triangle_ids=ids, stats=stats))
            if index % 10 == 0:
                print(json.dumps(dict(pair=n, completed=index+1, total=a.samples)), flush=True)
        minimum = min(samples, key=lambda s: s['surface_distance_m'])
        row = dict(pair=[n, 'torso_link'], surface_distance_m=minimum['surface_distance_m'],
                   minimum=minimum, samples=samples,
                   ideal_return_sample_indices=list(reversed(range(a.samples))))
        results.append(row)
        print(json.dumps(dict(pair=n, minimum=minimum)), flush=True)
    result = dict(status='INITIAL_SURFACE_WITNESSES_ONLY' if a.samples == 1 else 'SAMPLED_THREE_PAIR_EXIT_RETURN_ONLY',
        samples_per_pair=a.samples, results=results, tests=tests,
        return_basis='same_ideal_joint_states_in_reverse; not_runtime_reversal_verification',
        initial_state='synthetic_zero_other_arm_and_all_other_joints_held_zero',
        physical_authorized=False, continuous_path_validated=False, solid_containment_tested=False,
        current_physical_state_verified=False, robot_connections=0, movement_commands=0,
        source_sha256={str(f): hashlib.sha256(f.read_bytes()).hexdigest()
                       for f in (URDF, ARCHIVE, Path(fk.__file__), Path(mesh.__file__),
                                 Path(distance.__file__), Path(__file__))})
    with a.output.open('x') as out:
        json.dump(result, out, indent=2, allow_nan=False)
        out.write('\n')


if __name__ == '__main__':
    main()
