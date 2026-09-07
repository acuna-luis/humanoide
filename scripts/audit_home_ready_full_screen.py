#!/usr/bin/env python3
"""Offline hypothetical HOME/READY geometry screen; never connects to robot."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile
import numpy as np
import yaml
from audit_clamp_pessimistic_screen import URDF, ARCHIVE, fk, ROOT

FORWARD = Path('/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260903T103858_E4.0/artifacts/remote_clamp_s2_joints_trajectory.yaml')
RECOVERY = ROOT / 'scripts/vla/runtime/meta_move/clamp_s2_vla_e6_0_exact_recovery.yaml'
ORDER = ('shoulder_pitch', 'shoulder_roll', 'shoulder_yaw', 'elbow_roll',
         'elbow_yaw', 'wrist_pitch', 'wrist_roll')


def stages():
    forward = np.asarray(yaml.safe_load(FORWARD.read_text())['request']['goals'], float)
    recovery = np.asarray(yaml.safe_load(RECOVERY.read_text())['request']['goals'], float)
    if forward.shape != (2, 14) or recovery.shape != (2, 14):
        raise ValueError('unexpected goal dimensions')
    if not np.isfinite([forward, recovery]).all():
        raise ValueError('nonfinite goals')
    staging = np.zeros(14)
    staging[[1, 8]] = -.6
    if not np.array_equal(recovery[0], forward[0]) or not np.array_equal(recovery[1], staging):
        raise ValueError('recovery is not the expected exact waypoint reverse')
    return [np.zeros(14), staging, *forward, *recovery, np.zeros(14)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--tool-profile', choices=('installed-clamps', 'historical-pgc'), default='installed-clamps')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    waypoints = stages()
    profile_sources = []
    if args.tool_profile == 'installed-clamps':
        import clamp_work_model
        joints, boxes, _, tool_profile = clamp_work_model.load()
        profile_sources = [Path(clamp_work_model.__file__), clamp_work_model.CONTRACT,
                           ROOT/'scripts/build_clamp_simplified_model.py',
                           ROOT/'scripts/audit_clamp_mount_requalification.py']
    else:
        joints, boxes, _ = fk.load_robot(URDF, ARCHIVE)
        tool_profile = dict(profile='historical_pgc_not_installed_clamps', collision_coverage_complete=False)
    tree = ET.parse(URDF).getroot()
    fallbacks = []
    with zipfile.ZipFile(ARCHIVE) as archive:
        members = {n.split('cruzr_s2_description/', 1)[-1]: n for n in archive.namelist() if not n.endswith('/')}
        for side in ('L', 'R'):
            name = side + '_shoulder_pitch_link'
            visual = tree.find(f"link[@name='{name}']/visual")
            tri = fk.geometry_triangles(visual.find('geometry'), archive, members)
            pts = fk.apply(tri.reshape(-1, 3), fk.origin_transform(visual.find('origin')))
            boxes[name] = (pts.min(0), pts.max(0))
            fallbacks.append(name)
    links = sorted(boxes)
    pairs = [(i, j) for i, j in itertools.combinations(range(len(links)), 2)
             if any(links[k].startswith(('L_', 'R_', 'head_')) for k in (i, j))]
    indices = np.asarray(pairs)
    minima = np.full(len(pairs), np.inf)
    witnesses = [None] * len(pairs)
    corners = {n: fk.corners(*boxes[n]) for n in links}
    zero = {j['name']: 0. for j in joints if j['type'] != 'fixed'}
    armnames = [s+'_'+n+'_joint' for s in ('L', 'R') for n in ORDER]
    if not set(armnames + ['head_pitch_joint', 'head_yaw_joint']).issubset(zero):
        raise ValueError('missing expected joints')
    count = 0
    # Unknown head command ordering: two hypotheses, neither declared verified.
    # Three schedules are sensitivity cases, NOT every vendor interpolation.
    for head in ('head_pitch_joint', 'head_yaw_joint'):
        for schedule in ('simultaneous', 'left_first', 'right_first'):
            for stage, (start, end) in enumerate(zip(waypoints, waypoints[1:])):
                for t in np.linspace(0, 1, 51):
                    fractions = [t, t]
                    if schedule != 'simultaneous':
                        fractions = [min(2*t, 1), max(2*t-1, 0)]
                        if schedule == 'right_first':
                            fractions.reverse()
                    q = dict(zero)
                    for side in range(2):
                        for k in range(side*7, side*7+7):
                            q[armnames[k]] = float(start[k] + fractions[side]*(end[k]-start[k]))
                    q[head] = float(-.65 * (t if stage == 0 else 1-t if stage == 5 else 1))
                    poses = fk.forward_kinematics(joints, q)
                    world = [fk.apply(corners[n], poses[n]) for n in links]
                    low = np.array([p.min(0) for p in world])
                    high = np.array([p.max(0) for p in world])
                    i, j = indices.T
                    gaps = np.linalg.norm(np.maximum(np.maximum(low[i]-high[j], low[j]-high[i]), 0), axis=1)
                    for k in np.flatnonzero(gaps < minima):
                        minima[k] = gaps[k]
                        witnesses[k] = dict(head_hypothesis=head, schedule=schedule, stage=int(stage), fraction=float(t))
                    count += 1
    adjacent = {frozenset((j['parent'], j['child'])) for j in joints}
    records = [dict(pair=[links[i], links[j]], minimum_sampled_aabb_gap_m=float(minima[k]),
                    adjacent=frozenset((links[i], links[j])) in adjacent, witness=witnesses[k])
               for k, (i, j) in enumerate(pairs)]
    removed = tool_profile.get('removed_historical_links', [])
    result = dict(status='ROBOT_ONLY_WAYPOINT_SCREEN_TOOL_COVERAGE_INCOMPLETE', samples=count,
                  tool_profile=tool_profile,
                  pairs=records, unresolved_aabb_pairs=int(sum(minima == 0)),
                  visual_fallbacks= fallbacks, initial_state=zero,
                  missing_collision_links=[x.get('name') for x in tree.findall('link')
                                           if x.get('name') not in boxes and x.get('name') not in removed],
                  physical_authorized=False, robot_connections=0, movement_commands=0,
                  limitations=['historical_forward_not_current_installed', 'joint_order_mapping_not_runtime_verified',
                      'head_order_two_hypotheses_not_verified', 'synthetic_HOME_not_measured',
                      'three_schedules_not_exhaustive', 'sampled_not_continuous',
                      'AABB_overlap_not_proven_contact', 'visual_fallback_not_qualified',
                      'clamps_and_external_scene_absent', 'no_tracking_braking_or_solid_containment_validation'],
                  source_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in [URDF, ARCHIVE, FORWARD, RECOVERY, Path(__file__), Path(fk.__file__), *profile_sources]})
    encoded = json.dumps(result, indent=2, allow_nan=False)
    with args.output.open('x') as out:
        out.write(encoded + '\n')
    print(json.dumps(dict(samples=count, pairs=len(pairs), unresolved=int(sum(minima == 0)),
                          missing=result['missing_collision_links'])))


if __name__ == '__main__':
    main()
