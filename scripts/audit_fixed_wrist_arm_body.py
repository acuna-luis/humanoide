#!/usr/bin/env python3
"""Offline AABB screening of synthetic single-shoulder exit/return. No robot IO."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from audit_clamp_pessimistic_screen import URDF, ARCHIVE, fk


def gap(a, b):
    arrays = [np.asarray(x, dtype=float) for x in (*a, *b)]
    if any(x.shape != (3,) or not np.isfinite(x).all() for x in arrays):
        raise ValueError('invalid_bounds')
    lo, hi, blo, bhi = arrays
    if np.any(lo > hi) or np.any(blo > bhi):
        raise ValueError('inverted_bounds')
    return float(np.linalg.norm(np.maximum(np.maximum(lo-bhi, blo-hi), 0)))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    joints, boxes, _ = fk.load_robot(URDF, ARCHIVE)
    zero = {j['name']: 0.0 for j in joints if j['type'] != 'fixed'}
    names = ('shoulder_pitch', 'shoulder_roll', 'shoulder_yaw', 'elbow_roll',
             'elbow_yaw', 'wrist_pitch', 'wrist_roll', 'sixforce')
    expected = {s: [f'{s}_{n}_link' for n in names] for s in ('L', 'R')}
    available = {s: [n for n in expected[s] if n in boxes] for s in expected}
    body = [n for n in boxes if not n.startswith(('L_', 'R_'))]
    rows = []
    for side in ('L', 'R'):
        other = 'R' if side == 'L' else 'L'
        pairs = [(x, y) for x in available[side] for y in body+available[other]]
        minima = {pair: None for pair in pairs}
        # Return traverses identical ideal joint states; not a claim about runtime reversal.
        for direction, angles in [('outbound', np.linspace(0, -.6, 121)),
                                  ('return', np.linspace(-.6, 0, 121))]:
            for angle in angles:
                state = dict(zero)
                state[f'{side}_shoulder_roll_joint'] = float(angle)
                poses = fk.forward_kinematics(joints, state)
                bounds = {}
                for n in set(available[side]+available[other]+body):
                    pts = fk.apply(fk.corners(*boxes[n]), poses[n])
                    bounds[n] = (pts.min(axis=0), pts.max(axis=0))
                for pair in pairs:
                    d = gap(bounds[pair[0]], bounds[pair[1]])
                    if minima[pair] is None or d < minima[pair]['gap_m']:
                        minima[pair] = dict(pair=pair, gap_m=d, angle_rad=float(angle), direction=direction)
        records = list(minima.values())
        rows.append(dict(side=side, pairs_tested=len(pairs), minima=records,
                         overlap_or_touch_witnesses=[r for r in records if r['gap_m'] <= 0]))
    result = dict(status='SAMPLED_AABB_SCREEN_NOT_FULL_COLLISION_VALIDATION', sides=rows,
                  samples_per_side=242, body_links=body,
                  missing_geometry=[n for ns in expected.values() for n in ns if n not in boxes],
                  tested_arm_links=available, physical_authorized=False,
                  initial_state='explicit_synthetic_zero_NOT_measured_HOME',
                  environment_validated=False, braking_validated=False,
                  own_arm_internal_pairs_tested=False, passive_clamps_included=False,
                  notes=['AABB_overlap_is_inconclusive_not_proven_collision',
                         'no_attachment_pairs_silently_removed_from_tested_cross_groups',
                         'no_continuous_sweep_or_margin_or_tracking_validation',
                         'one_arm_at_a_time_other_arm_synthetic_zero'],
                  robot_connections=0, movement_commands=0,
                  source_sha256={str(f): hashlib.sha256(f.read_bytes()).hexdigest()
                                 for f in (URDF, ARCHIVE, Path(fk.__file__), Path(__file__))})
    with a.output.open('x') as out:
        json.dump(result, out, indent=2, allow_nan=False)
        out.write('\n')
    print(json.dumps({'missing': result['missing_geometry'], 'sides': [
        {'side': r['side'], 'pairs': r['pairs_tested'], 'overlaps': r['overlap_or_touch_witnesses']}
        for r in rows]}))


if __name__ == '__main__':
    main()
