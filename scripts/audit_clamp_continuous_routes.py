#!/usr/bin/env python3
"""Offline continuous bounds for specified curves, NOT a physical motion gate."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile
import numpy as np
from audit_clamp_orientation_bound import audit
from audit_home_ready_full_screen import stages, ORDER, FORWARD, RECOVERY
from clamp_work_model import load, CONTRACT
from audit_clamp_pessimistic_screen import ROOT, URDF, ARCHIVE, fk


def fractions(t, schedule):
    if schedule == 'simultaneous':
        return [t, t]
    out = [min(2*t, 1), max(2*t-1, 0)]
    return out if schedule == 'left_first' else out[::-1]


def travel_bound(delta, joints, reach):
    """Point travel bound for one monotone joint-coordinate interval."""
    total = 0.
    for j in joints:
        d = abs(delta.get(j['name'], 0.))
        if j['type'] in ('revolute', 'continuous'):
            total += reach*d
        elif j['type'] == 'prismatic':
            total += np.linalg.norm(j['axis'])*d
        elif d:
            raise ValueError('moving unsupported joint')
    return float(total)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--intervals', type=int, default=256)
    a = p.parse_args()
    if a.intervals < 2 or a.intervals % 2:
        raise ValueError('even interval count >=2 required for schedule breakpoint')
    if a.output.exists():
        raise FileExistsError(a.output)
    joints, boxes, _, profile = load()
    tree = ET.parse(URDF).getroot()
    # Same explicit visual fallback as the existing robot-only screen.
    with zipfile.ZipFile(ARCHIVE) as z:
        members = {n.split('cruzr_s2_description/', 1)[-1]: n for n in z.namelist() if not n.endswith('/')}
        for side in ('L', 'R'):
            name = side+'_shoulder_pitch_link'
            v = tree.find(f"link[@name='{name}']/visual")
            tri = fk.geometry_triangles(v.find('geometry'), z, members)
            pts = fk.apply(tri.reshape(-1, 3), fk.origin_transform(v.find('origin')))
            boxes[name] = (pts.min(0), pts.max(0))
    names = sorted(boxes)
    corners = {n: fk.corners(*boxes[n]) for n in names}
    zero = {j['name']: 0. for j in joints if j['type'] != 'fixed'}
    way = stages()
    arms = [s+'_'+n+'_joint' for s in ('L', 'R') for n in ORDER]
    # Sum over all branches overbounds any ancestor-to-point lever arm.
    # All prismatic coordinates are explicitly fixed at zero in these curves.
    reach = sum(np.linalg.norm(j['origin'][:3, 3]) for j in joints)
    reach += max(np.linalg.norm(v, axis=1).max() for v in corners.values())
    nominal = audit(json.loads(CONTRACT.read_text()))['nominal_radius_m']
    offsets = [.010, .025, .050, .075]
    records = []
    for schedule in ('simultaneous', 'left_first', 'right_first'):
        for k, (start, end) in enumerate(zip(way, way[1:])):
            def state(t):
                q = dict(zero)
                f = fractions(t, schedule)
                q.update({n: float(start[i]+f[i//7]*(end[i]-start[i])) for i, n in enumerate(arms)})
                q['head_pitch_joint'] = -.65*(t if k == 0 else 1-t if k == 5 else 1)
                return q
            best = np.full((2, len(names)), np.inf)
            witness = np.zeros_like(best)
            pair_best = np.inf
            lows = np.full((2, 3), np.inf)
            highs = np.full((2, 3), -np.inf)
            max_travel = 0.
            for i in range(a.intervals):
                t0, t1 = i/a.intervals, (i+1)/a.intervals
                tm = (t0+t1)/2
                qm, q0, q1 = state(tm), state(t0), state(t1)
                movement = max(travel_bound({n: q[n]-qm[n] for n in qm}, joints, reach) for q in (q0, q1))
                max_travel = max(max_travel, movement)
                poses = fk.forward_kinematics(joints, qm)
                centers = np.array([poses[s+'_sixforce_link'][:3, 3] for s in ('L', 'R')])
                lows = np.minimum(lows, centers-movement)
                highs = np.maximum(highs, centers+movement)
                for si, center in enumerate(centers):
                    for ni, name in enumerate(names):
                        pose = poses[name]
                        point = pose[:3, :3].T @ (center-pose[:3, 3])
                        lo, hi = boxes[name]
                        dist = np.linalg.norm(np.maximum(np.maximum(lo-point, point-hi), 0))
                        # Both the center and every body point can move by movement.
                        bound = dist-2*movement
                        if bound < best[si, ni]:
                            best[si, ni], witness[si, ni] = bound, tm
                pair_best = min(pair_best, np.linalg.norm(centers[0]-centers[1])-2*movement)
            cases = []
            for offset in offsets:
                radius = nominal+offset+.010
                cases.append(dict(assumed_center_error_m=offset, assumed_geometry_error_m=.010,
                    radius_m=radius, clamp_clamp_gap_lower_bound_m=float(pair_best-2*radius),
                    swept_outer_aabb_m={s: [(lows[si]-radius).tolist(), (highs[si]+radius).tolist()] for si, s in enumerate(('L', 'R'))},
                    pairs=[dict(clamp=s, link=n, gap_lower_bound_m=float(best[si, ni]-radius),
                                witness_cell_midfraction=float(witness[si, ni]))
                           for si, s in enumerate(('L', 'R')) for ni, n in enumerate(names)]))
            records.append(dict(direction='HOME_TO_READY' if k < 3 else 'READY_TO_HOME',
                stage=k, schedule=schedule, max_half_cell_point_travel_bound_m=max_travel, cases=cases))
    result = dict(status='CONDITIONAL_CONTINUOUS_ENVELOPES_NOT_PHYSICAL_VALIDATION',
        physical_authorized=False, robot_connections=0, movement_commands=0,
        nominal_radius_m=nominal, global_lever_arm_bound_m=float(reach),
        intervals_per_stage=a.intervals, total_cells=len(records)*a.intervals,
        removed_historical_links=profile['removed_historical_links'], robot_links_tested=names,
        missing_robot_geometry=[n.get('name') for n in tree.findall('link') if n.get('name') not in boxes and n.get('name') not in profile['removed_historical_links']],
        proof='Each monotone half-cell point travel <= global lever bound * sum(abs(delta angles)); prismatic travel added. Distance is Lipschitz in both bodies. Subtract both travel bounds and sphere radius. Sphere covers all tool rotations conditional on stated offsets/containment.',
        limitations=['center/measurement error cases are assumptions, not established physical upper bounds',
            'covers specified joint-linear curves and three schedules, not unknown vendor interpolation/overshoot',
            'synthetic HOME, zero uncommanded axes; head yaw=0 and pitch follows historical mapping',
            'robot collision geometry plus shoulder visual fallback not physically qualified',
            'no external scene, tracking or braking envelope; no attached-interface exclusions',
            'negative lower bound means inconclusive, not proven physical collision'], records=records,
        source_sha256={str(f): hashlib.sha256(f.read_bytes()).hexdigest() for f in
            (Path(__file__), CONTRACT, URDF, ARCHIVE, FORWARD, RECOVERY, ROOT/'scripts/clamp_work_model.py', ROOT/'scripts/audit_clamp_orientation_bound.py')})
    with a.output.open('x') as out:
        json.dump(result, out, indent=2, allow_nan=False)
    print(result['status'], 'cells=', result['total_cells'], 'nominal_radius_mm=', nominal*1000)
    for direction in ('HOME_TO_READY', 'READY_TO_HOME'):
        rows = [r for r in records if r['direction'] == direction]
        for ci, offset in enumerate(offsets):
            pairs = [x for r in rows for x in r['cases'][ci]['pairs']]
            body = [x for x in pairs if not x['link'].startswith(('L_', 'R_'))]
            print(direction, offset, 'all_pairs_lower_min=', min(x['gap_lower_bound_m'] for x in pairs),
                  'body_lower_min=', min(x['gap_lower_bound_m'] for x in body),
                  'unresolved_body_links=', sorted({x['link'] for x in body if x['gap_lower_bound_m'] <= 0}))


if __name__ == '__main__':
    main()
