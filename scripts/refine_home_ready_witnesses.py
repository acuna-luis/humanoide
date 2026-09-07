#!/usr/bin/env python3
"""Refine archived AABB witnesses against mesh surfaces, entirely offline."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile
import numpy as np
import audit_home_ready_full_screen as screen
from audit_clamp_pessimistic_screen import URDF, ARCHIVE, fk
import analyze_vla_clearance_guards_e6_0d as distance
import analyze_vla_near_pair_mesh_e6_0c as mesh


def witness_state(joints, waypoints, witness):
    stage, t = witness['stage'], witness['fraction']
    if not isinstance(stage, int) or not 0 <= stage < 6 or not 0 <= t <= 1:
        raise ValueError('invalid witness')
    schedule = witness['schedule']
    if schedule not in ('simultaneous', 'left_first', 'right_first'):
        raise ValueError('invalid schedule')
    head = witness['head_hypothesis']
    if head not in ('head_pitch_joint', 'head_yaw_joint'):
        raise ValueError('invalid head hypothesis')
    fractions = [t, t]
    if schedule != 'simultaneous':
        fractions = [min(2*t, 1), max(2*t-1, 0)]
        if schedule == 'right_first':
            fractions.reverse()
    q = {j['name']: 0. for j in joints if j['type'] != 'fixed'}
    start, end = waypoints[stage:stage+2]
    for side, prefix in enumerate(('L', 'R')):
        for k, name in enumerate(screen.ORDER):
            index = 7*side+k
            q[prefix+'_'+name+'_joint'] = float(start[index]+fractions[side]*(end[index]-start[index]))
    q[head] = float(-.65*(t if stage == 0 else 1-t if stage == 5 else 1))
    return q


def head_hold_candidate(joints, waypoints):
    """Explicit synthetic alternative, not an operational READY replacement."""
    points = []
    for stage in range(6):
        q = witness_state(joints, waypoints, dict(stage=stage, fraction=0.,
            schedule='simultaneous', head_hypothesis='head_pitch_joint'))
        q['head_pitch_joint'] = q['head_yaw_joint'] = 0.
        points.append(q)
    points.append(dict(points[0]))
    return dict(name='SYNTHETIC_ARMS_READY_HEAD_HOLD_NOT_FULL_READY',
        status='INCONCLUSIVE_NOT_EXECUTABLE', waypoints=points,
        physical_authorized=False, durations=None,
        changes=['head_pitch_and_yaw_fixed_at_synthetic_zero', 'arm_waypoints_unchanged'],
        prerequisites=['measured_initial_head_pose_and_clearance', 'full_tool_and_scene_model',
                       'continuous_collision_and_tracking_bounds', 'timing_and_executor_equivalence'],
        warning='does_not_preserve_full_READY_camera_pose_or_prove_initial_clearance')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    evidence = json.loads(args.input.read_text())
    for name, expected in evidence['source_sha256'].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != expected:
            raise ValueError('source changed: '+name)
    tests = [distance.distance_self_test(), distance.randomized_distance_reference_test()]
    joints, _, triangles = fk.load_robot(URDF, ARCHIVE)
    tree = ET.parse(URDF).getroot()
    with zipfile.ZipFile(ARCHIVE) as archive:
        members = {n.split('cruzr_s2_description/', 1)[-1]: n for n in archive.namelist() if not n.endswith('/')}
        for name in evidence['visual_fallbacks']:
            visual = tree.find(f"link[@name='{name}']/visual")
            tri = fk.geometry_triangles(visual.find('geometry'), archive, members)
            triangles[name] = fk.apply(tri.reshape(-1, 3), fk.origin_transform(visual.find('origin'))).reshape(-1, 3, 3)
    selected = [r for r in evidence['pairs'] if r['minimum_sampled_aabb_gap_m'] == 0]
    names = {n for r in selected for n in r['pair']}
    roots = {n: mesh.BvhNode(triangles[n], np.arange(len(triangles[n]), dtype=np.int64)) for n in names}
    waypoints = screen.stages()
    rows = []
    for r in selected:
        a, b = r['pair']
        q = witness_state(joints, waypoints, r['witness'])
        poses = fk.forward_kinematics(joints, q)
        d, ids, stats = distance.exact_mesh_distance(triangles[a], roots[a], poses[a],
            triangles[b], roots[b], poses[b], mesh, 1e-8)
        rows.append(dict(**r, surface_distance_m=d, triangle_ids=ids,
            joint_state=q, numerical_intersection=d <= 1e-8,
            uses_historical_gripper=any('pgc' in n or 'finger' in n for n in (a,b)),
            uses_visual_fallback=any(n in evidence['visual_fallbacks'] for n in (a,b))))
        print(json.dumps(dict(completed=len(rows), total=len(selected), pair=r['pair'], distance_m=d)), flush=True)
    # Isolate the head/torso pair: same HOME arms, both head-order hypotheses.
    # Zero-angle candidate is comparison only; does not approve removing head motion.
    head_rows = []
    for axis in ('head_pitch_joint', 'head_yaw_joint'):
        for angle in np.linspace(0, -.65, 27):
            q = {j['name']: 0. for j in joints if j['type'] != 'fixed'}
            q[axis] = float(angle)
            poses = fk.forward_kinematics(joints, q)
            a, b = 'head_pitch_link', 'torso_link'
            d, ids, _ = distance.exact_mesh_distance(triangles[a], roots[a], poses[a],
                triangles[b], roots[b], poses[b], mesh, 1e-8)
            head_rows.append(dict(axis=axis, angle_rad=float(angle), distance_m=d, triangle_ids=ids))
        print(json.dumps(dict(head_axis=axis, samples=27)), flush=True)
    result = dict(status='MESH_WITNESSES_AND_HEAD_SWEEP_NOT_ROUTE_APPROVAL', pairs=rows,
        head_sweep=head_rows, offline_candidate=head_hold_candidate(joints, waypoints),
        tests=tests, physical_authorized=False,
        robot_connections=0, movement_commands=0,
        limitations=['one_witness_per_AABB_pair_not_global_minimum', 'mesh_not_physical_contact_proof',
            'no_solid_containment_test', 'adjacency_not_contact_permission',
            'clamps_and_scene_absent', 'no_continuous_sweep_or_tracking_or_braking',
            'historical_gripper_not_installed_tool', 'head_joint_order_unverified'],
        source_sha256={str(f): hashlib.sha256(f.read_bytes()).hexdigest() for f in
            (args.input, Path(__file__), Path(screen.__file__), Path(distance.__file__), Path(mesh.__file__))})
    encoded = json.dumps(result, indent=2, allow_nan=False)
    with args.output.open('x') as out:
        out.write(encoded+'\n')
    print(json.dumps(dict(witnesses=len(rows), intersections=sum(r['numerical_intersection'] for r in rows))))


if __name__ == '__main__':
    main()
