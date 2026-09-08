#!/usr/bin/env python3
"""Offline neck-model diagnosis; no robot access or geometry corrections."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

import numpy as np

from audit_ready_endpoint import independent_crossing, endpoint_contract, TASK, screen
from audit_clamp_pessimistic_screen import ROOT, URDF, ARCHIVE, fk
import analyze_vla_clearance_guards_e6_0d as distance
import analyze_vla_near_pair_mesh_e6_0c as mesh

SNAPSHOT = ROOT.parent/'Humanoide-vla-evidence/20260904T130344_E6.1C-READY/whole-joint-state-after.json'


def analytic_neck(yaw, pitch):
    """Explicit torso->head chain, independent of generic FK/rotation helpers.

    Valid only for the exact vendor joint origins/axes checked below.
    """
    if not np.isfinite([yaw, pitch]).all():
        raise ValueError('nonfinite angles')
    def rz(a):
        c, s = math.cos(a), math.sin(a)
        return np.array([[c,-s,0],[s,c,0],[0,0,1]])
    c, s = math.cos(1.5708), math.sin(1.5708)
    rx = np.array([[1,0,0],[0,c,-s],[0,s,c]])
    result = np.eye(4)
    result[:3,:3] = rz(yaw) @ rx @ rz(pitch)
    result[:3,3] = [0,0,0.13546+0.025]
    return result


def check_chain(root):
    expected = [
        ('head_base_joint','fixed','torso_link','head_base_link','0 0 0.13546','0 0 0'),
        ('head_yaw_joint','revolute','head_base_link','head_yaw_link','0 0 0.0','0 0 0'),
        ('head_pitch_joint','revolute','head_yaw_link','head_pitch_link','0 0 0.025','1.5708 0 0'),
    ]
    for name, kind, parent, child, xyz, rpy in expected:
        j = root.find(f"joint[@name='{name}']")
        if j is None or j.get('type') != kind:
            raise ValueError('unexpected joint: '+name)
        for tag, attr, value in [('parent','link',parent),('child','link',child),
                                 ('origin','xyz',xyz),('origin','rpy',rpy),('axis','xyz','0 0 1')]:
            if j.find(tag) is None or j.find(tag).get(attr) != value:
                raise ValueError('chain changed: '+name+'/'+tag+'/'+attr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    root = ET.parse(URDF).getroot()
    check_chain(root)
    joints, bounds, triangles = fk.load_robot(URDF, ARCHIVE)
    links = ('head_pitch_link','torso_link')
    sources = {}
    with zipfile.ZipFile(ARCHIVE) as archive:
        vendor = 'cruzr_s2_description/urdf/cruzr_s2_v1/cruzr_s2_v1.urdf'
        if archive.read(vendor) != URDF.read_bytes():
            raise ValueError('URDF differs from vendor archive')
        for name in links:
            link = root.find(f"link[@name='{name}']")
            entries = {}
            for kind in ('visual','collision'):
                elements = link.findall(kind)
                if len(elements) != 1:
                    raise ValueError('unexpected geometry count')
                element = elements[0]
                m = element.find('geometry/mesh')
                entries[kind] = dict(filename=m.get('filename'), scale=m.get('scale','1 1 1'),
                    origin=element.find('origin').attrib)
            filename = entries['collision']['filename'].removeprefix('package://')
            sources[name] = dict(entries=entries, visual_equals_collision=entries['visual']==entries['collision'],
                mesh_sha256=hashlib.sha256(archive.read(filename)).hexdigest(),
                local_bounds_m=[x.tolist() for x in bounds[name]], triangles=len(triangles[name]))
    snapshot = json.loads(SNAPSHOT.read_text())
    names, values = snapshot['names'], snapshot['positions']
    if len(names) != len(values) or len(set(names)) != len(names) or not np.isfinite(values).all():
        raise ValueError('invalid historical state')
    measured = dict(zip(names, values))
    yaw, pitch = endpoint_contract()['head_command_order']
    cases = [('synthetic_zero',0.,0.),('nominal_READY_yaw_pitch',yaw,pitch),
             ('historical_measured_READY',measured['head_yaw_joint'],measured['head_pitch_joint'])]
    roots = {n: mesh.BvhNode(triangles[n], np.arange(len(triangles[n]),dtype=np.int64)) for n in links}
    results = []
    for label, yaw, pitch in cases:
        # All upstream transforms cancel in torso-relative coordinates.
        state = {j['name']:0. for j in joints if j['type'] != 'fixed'}
        state.update(head_yaw_joint=yaw, head_pitch_joint=pitch)
        poses = fk.forward_kinematics(joints,state)
        relative = np.linalg.inv(poses['torso_link']) @ poses['head_pitch_link']
        independent = analytic_neck(yaw,pitch)
        error = float(np.max(np.abs(relative-independent)))
        if error > 1e-12:
            raise ValueError('FK disagreement')
        a,b = links
        gap, ids, _ = distance.exact_mesh_distance(triangles[a],roots[a],independent,
            triangles[b],roots[b],np.eye(4),mesh,1e-8)
        pair = [fk.apply(triangles[a][ids[0]],independent),triangles[b][ids[1]]]
        hits = independent_crossing(*pair)
        results.append(dict(case=label,yaw_rad=yaw,pitch_rad=pitch,FK_max_abs_error=error,
            head_in_torso=independent.tolist(),surface_distance_m=gap,triangle_ids=ids,
            triangles_in_torso_m=[x.tolist() for x in pair],crossings_in_torso=hits))
    result = dict(status='OFFLINE_MODEL_DIAGNOSIS_NOT_PHYSICAL_VALIDATION',sources=sources,results=results,
        physical_authorized=False,robot_connections=0,movement_commands=0,
        limitations=['historical_not_current_state','surface_test_not_solid_containment',
                     'mesh_physical_correspondence_unverified','no_geometry_modified','no_collision_exclusions'],
        source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
            (URDF,ARCHIVE,SNAPSHOT,TASK,screen.FORWARD,Path(__file__),Path(fk.__file__),Path(distance.__file__),Path(mesh.__file__))})
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False)
        stream.write('\n')
    print(json.dumps([dict(case=r['case'],gap_m=r['surface_distance_m'],FK_error=r['FK_max_abs_error'],
        crossings=len(r['crossings_in_torso'])) for r in results]))


if __name__ == '__main__':
    main()
