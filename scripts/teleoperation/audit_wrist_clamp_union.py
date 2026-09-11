#!/usr/bin/env python3
"""Audit pinned wrist/clamp defaults and build a complete LOCAL CAD cover.

Reads only private archives and CAD. No network, installation or movement.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import numpy as np
import trimesh
import yaml
from scipy.spatial.transform import Rotation

import review_clamp_trajectory_optimization as common
import cruzr_pico_to_home_owner_gate as endpoints
from cruzr_pico_to_home_owner_gate import JOINT_ORDER, PICO_VARIANTS
from general_home.native_geometry import InitializerArguments
from general_home.native_arm_frames import NativeArmFrames, dh_poses
from general_home.union_coverage import Capsule, RoundedHull, build_cover


def transform(spec):
    result = np.eye(4)
    result[:3,:3] = Rotation.from_quat(spec['rotation']).as_matrix()
    result[:3,3] = spec['translation']
    if not np.isfinite(result).all():
        raise ValueError('Nonfinite transform')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arm-library',type=Path,required=True)
    parser.add_argument('--runtime-root',type=Path,required=True)
    parser.add_argument('--package-root',type=Path,default=Path(__file__).resolve().parents[2]/'cruzr_s2_description_splint/cruzr_s2_description')
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    if args.output.exists() or args.runtime_root.resolve() == Path('/'):
        parser.error('Use a private local archive and a new output file')
    config_path = args.runtime_root/'opt/walker/manipulation_platforms/share/manipulation_platforms/config/cruzr_s2_robot_description.yaml'
    native_path = config_path.parent/'urdf/cruzr_s2.urdf'
    cad_path = args.package_root/'urdf/cruzr_s2_v1/cruzr_s2_v1.urdf'
    source_files = [args.arm_library,config_path,native_path,cad_path,Path(__file__),Path(common.__file__),Path(common.fk.__file__)]
    source_files += [Path(module.__file__) for module in (endpoints,common.internal,common.pico)]
    source_files += [Path(sys.modules[c.__module__].__file__) for c in (NativeArmFrames,InitializerArguments,Capsule)]
    for side in ('L','R'):
        source_files += [args.package_root/'meshes/cruzr_s2_v1'/f'{side}_{link}_link.STL'
            for link in ('wrist_roll','sixforce','hand')]
    hashes = {str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}
    config = yaml.safe_load(config_path.read_text())
    if config.get('robot_version') != 'cruzr_s2_v1':
        raise ValueError('Unreviewed robot version')
    defaults = InitializerArguments(args.arm_library,'arm').extract()
    frames = NativeArmFrames(args.arm_library)
    cad_joints,native_joints = [common.model_joints(p) for p in (cad_path,native_path)]
    for joint in native_joints:
        if joint['parent'] == 'mobile_base_link':
            joint['parent'] = 'base_link'
    tree = ET.parse(cad_path).getroot()
    kin = {}
    for name,q in dict(HOME=np.zeros(20),**PICO_VARIANTS).items():
        reference = common.fk.forward_kinematics(native_joints,dict(zip(JOINT_ORDER,q)))
        kin[name] = {}
        for side,component in (('L','left_arm'),('R','right_arm')):
            names = [side+'_'+n+'_joint' for n in ('shoulder_pitch','shoulder_roll','shoulder_yaw','elbow_roll','elbow_yaw','wrist_pitch','wrist_roll')]
            angles = np.array([q[JOINT_ORDER.index(n)] for n in names])
            fk,placed = frames.evaluate(angles)
            native = transform(config[component]['kinematics']['X_ParentBase']) @ fk[-1]
            expected = np.linalg.inv(reference['torso']) @ reference[side+'_wrist_roll_link']
            delta = np.linalg.inv(native) @ expected
            kin[name][side] = dict(native_vs_standard_dh_max_abs=float(np.abs(fk-dh_poses(frames.geometry,angles)).max()),
                native_vs_urdf_wrist_translation_m=float(np.linalg.norm(delta[:3,3])),
                native_vs_urdf_wrist_rotation_rad=float(Rotation.from_matrix(delta[:3,:3]).magnitude()),
                wrist_pitch_in_wrist_roll=(np.linalg.inv(fk[6]) @ placed[5]).tolist())
    # Independent arithmetic/placement checks through the bounded arm domain.
    rng = np.random.default_rng(20260911)
    max_numeric = 0.
    for angles in rng.uniform(-2,2,(128,7)):
        fk,_ = frames.evaluate(angles)
        max_numeric = max(max_numeric,float(np.abs(fk-dh_poses(frames.geometry,angles)).max()))
    if max_numeric > 1e-12:
        raise ValueError('Native numeric FK comparison failed')
    rows = {}
    for side,hand,offset in (('L','left_hand',0x39c80),('R','right_hand',0x39b40)):
        if config[hand]['model'] != 'clamp' or config[hand]['type'] != 'effector':
            raise ValueError('Expected clamp effectors')
        record = next(r for r in defaults['all_constructor_calls'] if int(r['object_offset'],16) == offset)
        if record['name'] != 'S2Clamp' or record['type_enum'] != 5:
            raise ValueError('Unreviewed clamp primitive')
        wrist = defaults['component_primitives'][6]
        if wrist['name'] != 'WristRoll' or wrist['type_enum'] != 3:
            raise ValueError('Unreviewed wrist primitive')
        hand_pose = transform(config[hand]['kinematics']['X_ParentBase'])
        points = np.array(record['points']) @ hand_pose[:3,:3].T + hand_pose[:3,3]
        native_members = [Capsule('native_wrist_roll',wrist['points'],wrist['scalar_arguments'][0]),
            RoundedHull('native_S2Clamp',points,record['scalar_arguments'][0])]
        meshes,source_triangles = [],0
        fixed_pose = np.eye(4)
        for suffix,joint_name in (('wrist_roll',None),('sixforce',side+'_sixforce_joint'),('hand',side+'_hand_joint')):
            if joint_name:
                joint = next(j for j in cad_joints if j['name'] == joint_name)
                if joint['type'] != 'fixed':
                    raise ValueError('Rigid coverage cannot include a moving joint')
                fixed_pose = fixed_pose @ joint['origin']
            link_name = side+'_'+suffix+'_link'
            link = next(l for l in tree.findall('link') if l.get('name') == link_name)
            collisions = link.findall('collision')
            if len(collisions) != 1:
                raise ValueError('Expected one source mesh per rigid link')
            c = collisions[0];o = c.find('origin');m = c.find('geometry/mesh')
            expected_file = 'package://cruzr_s2_description/meshes/cruzr_s2_v1/'+link_name+'.STL'
            if (o is None or o.get('xyz') != '0 0 0' or o.get('rpy') != '0 0 0'
                    or m is None or m.get('filename') != expected_file or m.get('scale','1 1 1') != '1 1 1'):
                raise ValueError('Unreviewed CAD origin/path/scale')
            mesh = trimesh.load_mesh(args.package_root/'meshes/cruzr_s2_v1'/(link_name+'.STL'),process=False)
            mesh.apply_transform(fixed_pose)
            source_triangles += len(mesh.faces)
            meshes.append(mesh)
        vertices = np.unique(np.vstack([m.vertices for m in meshes]),axis=0)
        scores = np.array([m.score(vertices) for m in native_members])
        gap = scores.min(axis=0)
        witness = int(gap.argmax())
        members,certificate,before,hull,patch = build_cover(vertices,native_members,[0,.085,0])
        # The preceding wrist-pitch link moves relative to this assembly. Include
        # it for a reference counterexample only; never use it in the rigid cover.
        pitch_record = defaults['component_primitives'][5]
        counterexamples = {}
        for reference_name in kin:
            t = np.array(kin[reference_name][side]['wrist_pitch_in_wrist_roll'])
            pp = np.array(pitch_record['points']) @ t[:3,:3].T + t[:3,3]
            pitch = Capsule('wrist_pitch_reference',pp,pitch_record['scalar_arguments'][0])
            union_gap = np.minimum(gap,pitch.score(vertices))
            counterexamples[reference_name] = dict(outside_vertices=int((union_gap>1e-8).sum()),
                max_vertex_excess_m=max(0.,float(union_gap.max())))
        rows[side] = dict(frame_id=side+'_wrist_roll_link',original_cad_triangles=source_triangles,
            scope='rigid wrist_roll + sixforce + hand CAD; wrist_pitch remains a separate moving part',
            registration='native DH/URDF wrist frame correspondence; full physical calibration not verified',
            native_only=dict(outside_vertices=int((gap>1e-8).sum()),max_vertex_excess_m=max(0.,float(gap[witness])),
                witness_in_wrist_m=vertices[witness].tolist(),boundary_certificate=before),
            adding_moving_wrist_pitch_at_references=counterexamples,
            derived_local_cover=[m.specification() for m in members],coverage_certificate=certificate,
            supplemental_hull_faces=0 if patch is None else len(patch.hull.faces),
            supplemental_hull_volume_m3=0 if patch is None else float(patch.hull.volume),
            whole_cad_hull_volume_m3=float(hull.volume))
    if any(hashlib.sha256(Path(p).read_bytes()).hexdigest()!=s for p,s in hashes.items()):
        raise ValueError('Source changed during audit')
    result = dict(schema='cruzr-wrist-clamp-union-audit-v1',status='LOCAL_RIGID_CAD_COVER_VERIFIED_NOT_DEPLOYED',
        arms=rows,frame_comparisons=kin,numeric_fk_cases=128,numeric_fk_max_abs_error=max_numeric,
        attachment_evidence=dict(arm_function='UpdateLinkBoundingCapsulePoses:0x26980..0x26d94',
            native_indices=[6,5,3,1],arm_arithmetic='CalcAllPoses:0x1c500; constructor:0x1af00',
            effector_factory='0x2cad0: clamp branch, s2/non-tray selection, SetPose(X_ParentBase)',
            selection_scope='archived configuration plus static native factory; not a memory dump of the running model'),
        source_sha256=hashes,physical_approval=False,installable=False,movement_commands=0,remote_changes=0,
        limitations=['CAD coverage does not certify physical registration, trajectory, tracking or stopping',
            'physical geometry/error margins remain separate and must not be reduced',
            'no moving collision pair was removed; complete robot model remains required',
            'do not install this diagnostic representation in Motion'])
    with args.output.open('x') as f:
        json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(dict(output=str(args.output),status=result['status'],
        native_excess_mm={s:r['native_only']['max_vertex_excess_m']*1000 for s,r in rows.items()},
        covered={s:r['coverage_certificate']['volume_covered'] for s,r in rows.items()},
        numeric_fk_max_abs_error=max_numeric,physical_approval=False)))


if __name__ == '__main__':
    try:
        main()
    except (ValueError,OSError,KeyError,StopIteration) as exc:
        print('ERROR: '+str(exc),file=sys.stderr)
        raise SystemExit(2)
