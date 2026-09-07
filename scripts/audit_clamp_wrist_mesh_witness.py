#!/usr/bin/env python3
"""Refine TWO worst sampled AABB witnesses with STL; not a whole-path clearance."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from audit_clamp_pessimistic_screen import ROOT, URDF, ARCHIVE, fk
import analyze_vla_clearance_guards_e6_0d as distances

SOURCE = ROOT.parent/'Humanoide-vla-evidence/20260907_clamp_pessimistic_path_201.json'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    report = json.loads(SOURCE.read_text())
    if report['status'] != 'SAMPLED_HISTORICAL_PATH_SENSITIVITY_NOT_PHYSICAL_VALIDATION':
        raise ValueError('wrong_source_status')
    checks = {'distance_cases': distances.distance_self_test(),
              'randomized_reference_cases': distances.randomized_distance_reference_test()}
    joints, _, meshes = fk.load_robot(URDF, ARCHIVE)
    current_hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (URDF, ARCHIVE, Path(fk.__file__))}
    if any(report['source_sha256'].get(path) != digest for path, digest in current_hashes.items()):
        raise ValueError('geometry_or_fk_changed_since_path_report')
    case = min(report['cases'], key=lambda c: c['candidate_radius_m'])
    witnesses = []
    for side in ('L', 'R'):
        category = side+'_same_arm_non_attachment'
        segment = min(case['segments'], key=lambda s: s['categories'][category]['envelope_gap_m'])
        row = segment['categories'][category]
        target = row['pair'][1]
        q = row['joint_state']
        if any(j['name'] not in q for j in joints if j['type'] != 'fixed'):
            raise ValueError('incomplete_witness_state')
        poses = fk.forward_kinematics(joints, q)
        world_center = poses[f'{side}_sixforce_link'][:3, 3]
        pose = poses[target]
        local_center = pose[:3, :3].T @ (world_center-pose[:3, 3])
        triangles = meshes[target]
        measured = distances.point_triangle_distances_batch(
            np.broadcast_to(local_center, (len(triangles), 3)), triangles)
        if not len(measured) or not np.isfinite(measured).all():
            raise ValueError('invalid_mesh_distances')
        index = int(np.argmin(measured))
        distance = float(measured[index])
        witnesses.append({'side': side, 'target_mesh': target,
            'schedule': segment['schedule'], 'segment': segment['segment'],
            'segment_fraction': row['segment_fraction'], 'joint_state': q,
            'center_to_mesh_surface_m': distance,
            'closest_triangle_index': index, 'triangle_local_coordinates_m': triangles[index].tolist(),
            'local_center_m': local_center.tolist(),
            'candidate_radius_m': case['candidate_radius_m'],
            'sphere_surface_gap_m': distance-case['candidate_radius_m'],
            'sphere_intersects_mesh_surface': distance <= case['candidate_radius_m']})
    result = {'status': 'TWO_STL_WITNESSES_NOT_ACTUAL_TOOL_COLLISION',
        'tests': checks, 'witnesses': witnesses,
        'interpretation': 'STL refinement tests the enclosing sphere, not the real oriented clamp. Surface intersection is sufficient to retain an overlap warning; positive surface distance alone is not a solid containment test.',
        'full_path_rescanned': False, 'actual_clamp_collision_proven': False,
        'physical_authorized': False, 'robot_connections': 0, 'movement_commands': 0,
        'source_sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in (SOURCE, URDF, ARCHIVE, Path(fk.__file__), Path(distances.__file__), Path(__file__))}}
    with args.output.open('x') as out:
        json.dump(result, out, indent=2, allow_nan=False)
        out.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
