#!/usr/bin/env python3
"""Preserve READY targets and test a necessary endpoint condition, offline only."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import yaml
from audit_clamp_pessimistic_screen import ROOT, URDF, ARCHIVE, fk
import audit_home_ready_full_screen as screen
import analyze_vla_clearance_guards_e6_0d as distance
import analyze_vla_near_pair_mesh_e6_0c as mesh

TASK = ROOT / 'scripts/vla/runtime/tasks/s2_vla_e6_0_ready_s2.xml'


def endpoint_contract():
    root = ET.parse(TASK).getroot()
    def angles(kind):
        actions = root.findall(f".//Action[@type='{kind}']")
        if len(actions) != 1:
            raise ValueError('ambiguous endpoint: '+kind)
        return [float(x.strip()) for x in actions[0].get('joint_angles').split(';')]
    meta = root.findall(".//Action[@name='clamp_s2_joints_trajectory']")
    if len(meta) != 1:
        raise ValueError('unexpected MetaMove reference')
    request = yaml.safe_load(screen.FORWARD.read_text())['request']
    arms = request['goals'][-1]
    head, waist = angles('head'), angles('waist')
    if len(arms) != 14 or len(head) != 2 or len(waist) != 1:
        raise ValueError('unexpected endpoint dimensions')
    if not np.isfinite(arms+head+waist).all():
        raise ValueError('nonfinite endpoint')
    return dict(arms_vendor_order=arms, head_command_order=head, waist_command_order=waist,
        arm_order_per_side=list(screen.ORDER), current_installed_equivalence_verified=False)


def require_same_endpoint(expected, candidate):
    for key in ('arms_vendor_order', 'head_command_order', 'waist_command_order'):
        a, b = np.asarray(expected[key]), np.asarray(candidate[key])
        if a.shape != b.shape or not np.isfinite(b).all() or not np.array_equal(a, b):
            raise ValueError('READY endpoint changed: '+key)


def independent_crossing(a, b):
    """Independent 3x3 solve of edge/face crossing, not the distance kernel."""
    hits = []
    for owner, (edge_tri, face) in enumerate(((a, b), (b, a))):
        for i in range(3):
            start, end = edge_tri[i], edge_tri[(i+1)%3]
            matrix = np.column_stack((face[1]-face[0], face[2]-face[0], start-end))
            if np.linalg.matrix_rank(matrix) < 3:
                continue
            u, v, t = np.linalg.solve(matrix, start-face[0])
            if min(u, v, t, 1-u-v, 1-t) >= -1e-9:
                point = start+t*(end-start)
                residual = float(np.linalg.norm(point-(face[0]+u*(face[1]-face[0])+v*(face[2]-face[0]))))
                hits.append(dict(edge_owner=owner, edge_index=i, u=float(u), v=float(v),
                    t=float(t), point_m=point.tolist(), residual_m=residual))
    return hits


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    contract = endpoint_contract()
    require_same_endpoint(contract, contract)
    joints, _, triangles = fk.load_robot(URDF, ARCHIVE)
    a, b = 'head_pitch_link', 'torso_link'
    roots = {n: mesh.BvhNode(triangles[n], np.arange(len(triangles[n]), dtype=np.int64)) for n in (a, b)}
    rows = []
    for order in (('head_yaw_joint', 'head_pitch_joint'), ('head_pitch_joint', 'head_yaw_joint')):
        q = {j['name']: 0. for j in joints if j['type'] != 'fixed'}
        for i, side in enumerate(('L', 'R')):
            for k, name in enumerate(screen.ORDER):
                q[side+'_'+name+'_joint'] = contract['arms_vendor_order'][i*7+k]
        q.update(zip(order, contract['head_command_order']))
        q['waist_yaw_joint'] = contract['waist_command_order'][0]
        poses = fk.forward_kinematics(joints, q)
        d, ids, _ = distance.exact_mesh_distance(triangles[a], roots[a], poses[a],
            triangles[b], roots[b], poses[b], mesh, 1e-8)
        witnesses = [fk.apply(triangles[n][index], poses[n]) for n, index in zip((a,b), ids)]
        hits = independent_crossing(*witnesses)
        rows.append(dict(head_order_hypothesis=order, joint_state=q, distance_m=d,
            triangle_ids=ids, world_triangles=[x.tolist() for x in witnesses], independent_crossings=hits))
    failed = all(r['distance_m'] <= 1e-8 and r['independent_crossings'] for r in rows)
    result = dict(status='MODEL_ENDPOINT_INTERSECTION_CONFIRMED' if failed else 'INCONCLUSIVE',
        endpoint_contract=contract, results=rows, physical_authorized=False,
        route_search_can_resolve_this_model_endpoint=False if failed else None,
        rejected_alternative='head_hold_changes_READY_endpoint',
        reasoning='Every path preserving this endpoint contains the endpoint; intermediate detours cannot remove its modeled intersection.',
        limitations=['not_proof_of_physical_collision', 'physical_mesh_correspondence_unverified',
                     'current_installed_endpoint_unverified', 'other_axes_synthetic_zero',
                     'not_full_robot_or_tool_or_scene_validation'],
        robot_connections=0, movement_commands=0,
        source_sha256={str(f): hashlib.sha256(f.read_bytes()).hexdigest() for f in
            (TASK, screen.FORWARD, URDF, ARCHIVE, Path(__file__), Path(fk.__file__), Path(distance.__file__), Path(mesh.__file__))})
    encoded = json.dumps(result, indent=2, allow_nan=False)
    with args.output.open('x') as out:
        out.write(encoded+'\n')
    print(json.dumps(dict(status=result['status'], distances=[r['distance_m'] for r in rows],
                         independent_hit_counts=[len(r['independent_crossings']) for r in rows])))


if __name__ == '__main__':
    main()
