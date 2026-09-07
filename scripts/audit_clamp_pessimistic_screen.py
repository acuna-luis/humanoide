#!/usr/bin/env python3
"""LOCAL sensitivity screen at synthetic URDF zero; NEVER certifies HOME."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

from audit_clamp_orientation_bound import ROOT, audit
from audit_clamp_sensor_reference import ARCHIVE

sys.path.insert(0, str(ROOT/'scripts/vla'))
import analyze_vla_fixture_collision_e4_1c as fk

URDF = ROOT.parent/'Humanoide-vla-evidence/20260903T093408_E4.1C/artifacts/vendor_cruzr_s2_v1.urdf'


def point_aabb_distance(point, low, high):
    arrays = [np.asarray(x, dtype=float) for x in (point, low, high)]
    if any(x.shape != (3,) or not np.isfinite(x).all() for x in arrays):
        raise ValueError('invalid_point_or_bounds')
    point, low, high = arrays
    if np.any(low > high):
        raise ValueError('inverted_bounds')
    return math.hypot(*np.maximum(np.maximum(low-point, point-high), 0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    contract_path = ROOT/'config/clamp_mount_requalification.json'
    nominal = audit(json.loads(contract_path.read_text()))
    joints, boxes, _ = fk.load_robot(URDF, ARCHIVE)
    # Explicit artificial pose, NOT a missing-state default or live HOME.
    state = {j['name']: 0.0 for j in joints if j['type'] != 'fixed'}
    poses = fk.forward_kinematics(joints, state)
    body_links = sorted(k for k in boxes if not k.startswith(('L_', 'R_')))
    if 'torso_link' not in body_links:
        raise ValueError('torso_link_missing')
    distances = {}
    for side in ('L', 'R'):
        center = poses[f'{side}_sixforce_link'][:3, 3]
        distances[side] = {}
        for link in body_links:
            world = fk.apply(fk.corners(*boxes[link]), poses[link])
            distances[side][link] = point_aabb_distance(center, world.min(axis=0), world.max(axis=0))
    cases = []
    for center_error in (.010, .025, .050, .075):
        geometry_reserve = .010
        radius = nominal['nominal_radius_m']+center_error+geometry_reserve
        cases.append({
            'assumed_center_error_m': center_error,
            'assumed_geometry_reserve_m': geometry_reserve,
            'both_errors_are_unverified_sensitivity_parameters': True,
            'candidate_radius_m': radius,
            'sides': {side: {
                'sphere_aabb_gap_m': {link: dist-radius for link, dist in d.items()},
                'inconclusive_overlapping_body_bounds': [link for link, dist in d.items() if dist <= radius],
            } for side, d in distances.items()},
        })
    result = {
        'status': 'SYNTHETIC_ZERO_SENSITIVITY_NOT_PHYSICAL_VALIDATION',
        'nominal_radius_m': nominal['nominal_radius_m'],
        'state_explicit_synthetic_zero': state,
        'center_hypothesis': 'URDF sixforce origin; real offset not established, varied as radial error',
        'body_links_tested': body_links,
        'center_to_body_aabb_distance_m': distances,
        'cases': cases,
        'limitations': ['AABB overlap does not prove real collision',
                        'positive gap only conditional at one artificial pose',
                        'not a trajectory or startup/rearm/HOME simulation',
                        'arm-arm, clamp-arm, fixtures and environment not tested',
                        'assumptions not verified against physical installation',
                        'stopping time, tracking error and mesh uncertainty not qualified'],
        'selected_operating_profile': None,
        'physical_authorized': False, 'robot_connections': 0, 'movement_commands': 0,
        'source_sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in (contract_path, URDF, ARCHIVE, Path(__file__), Path(fk.__file__))},
    }
    with args.output.open('x') as out:
        json.dump(result, out, indent=2, allow_nan=False)
        out.write('\n')
    print(result['status'])
    for case in cases:
        print(round(case['candidate_radius_m']*1000, 3), 'mm',
              {side: row['inconclusive_overlapping_body_bounds'] for side, row in case['sides'].items()})


if __name__ == '__main__':
    main()
