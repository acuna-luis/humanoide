#!/usr/bin/env python3
"""Offline internal arm coverage, visual shoulder mesh explicitly provisional."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile
import numpy as np
from audit_clamp_pessimistic_screen import URDF, ARCHIVE, fk
from audit_fixed_wrist_arm_body import gap


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    joints, boxes, _ = fk.load_robot(URDF, ARCHIVE)
    root = ET.parse(URDF).getroot()
    additions = []
    with zipfile.ZipFile(ARCHIVE) as archive:
        members = {n.split('cruzr_s2_description/', 1)[-1]: n for n in archive.namelist() if not n.endswith('/')}
        for side in ('L', 'R'):
            name = side+'_shoulder_pitch_link'
            link = root.find(f"link[@name='{name}']")
            visual = link.find('visual')
            tri = fk.geometry_triangles(visual.find('geometry'), archive, members)
            points = fk.apply(tri.reshape(-1, 3), fk.origin_transform(visual.find('origin')))
            boxes[name] = (points.min(axis=0), points.max(axis=0))
            additions.append(dict(link=name, source='URDF_visual_NOT_collision',
                triangles=len(tri), local_bounds=[x.tolist() for x in boxes[name]],
                vendor_collision_qualification_verified=False))
    zero = {j['name']: 0.0 for j in joints if j['type'] != 'fixed'}
    parents = {j['child']: j['parent'] for j in joints}
    adjacency = {frozenset((j['parent'], j['child'])) for j in joints}
    def below(link, ancestor):
        while link != ancestor and link in parents:
            link = parents[link]
        return link == ancestor
    names = ('shoulder_pitch', 'shoulder_roll', 'shoulder_yaw', 'elbow_roll',
             'elbow_yaw', 'wrist_pitch', 'wrist_roll', 'sixforce')
    results = []
    for side in ('L', 'R'):
        links = [side+'_'+n+'_link' for n in names]
        pivot = side+'_shoulder_roll_link'
        records = {pair: dict(pair=pair, adjacent=frozenset(pair) in adjacency,
                    common_rigid_motion=all(below(n, pivot) for n in pair),
                    uses_visual_fallback=any(n.endswith('shoulder_pitch_link') for n in pair),
                    minimum_aabb_gap_m=float('inf')) for pair in itertools.combinations(links, 2)}
        for angle in np.linspace(0, -.6, 121):
            q = dict(zero)
            q[side+'_shoulder_roll_joint'] = float(angle)
            poses = fk.forward_kinematics(joints, q)
            bounds = {}
            for n in links:
                points = fk.apply(fk.corners(*boxes[n]), poses[n])
                bounds[n] = (points.min(axis=0), points.max(axis=0))
            for pair, r in records.items():
                d = gap(bounds[pair[0]], bounds[pair[1]])
                if d < r['minimum_aabb_gap_m']:
                    r.update(minimum_aabb_gap_m=d, witness_angle_rad=float(angle))
        results.extend(records.values())
    output = dict(status='INTERNAL_ARM_COVERAGE_DIAGNOSTIC', visual_fallbacks=additions,
        pairs=results, physical_authorized=False, robot_connections=0, movement_commands=0,
        limitations=['no_pair_excluded_as_allowed_collision', 'adjacency_is_not_contact_permission',
                     'AABB_overlap_not_physical_collision', 'no_clamps_or_runtime_or_scene',
                     'visual_mesh_is_provisional_not_verified_physical_enclosure'],
        source_sha256={str(f): hashlib.sha256(f.read_bytes()).hexdigest()
                       for f in (URDF, ARCHIVE, Path(fk.__file__), Path(__file__))})
    with a.output.open('x') as out:
        json.dump(output, out, indent=2, allow_nan=False)
        out.write('\n')
    print(json.dumps(dict(total=len(results), common_rigid=sum(r['common_rigid_motion'] for r in results),
        overlap_pairs=[r for r in results if r['minimum_aabb_gap_m'] == 0], visual_fallbacks=additions)))


if __name__ == '__main__':
    main()
