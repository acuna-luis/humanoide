#!/usr/bin/env python3
"""Compare archived Motion configuration and CAD frames. No network or execution."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-root',type=Path,required=True,help='Local archive containing opt/walker; never /')
    parser.add_argument('--package-root',type=Path,default=Path(__file__).resolve().parents[2]/'cruzr_s2_description_splint/cruzr_s2_description')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('Output already exists')
    if args.runtime_root.resolve()==Path('/'):parser.error('Use an archived runtime directory')
    import numpy as np
    import yaml
    import review_clamp_trajectory_optimization as common
    from cruzr_pico_to_home_owner_gate import JOINT_ORDER,PICO_VARIANTS
    config_path=args.runtime_root/'opt/walker/manipulation_platforms/share/manipulation_platforms/config/cruzr_s2_robot_description.yaml'
    native_path=config_path.parent/'urdf/cruzr_s2.urdf'
    cad_path=args.package_root/'urdf/cruzr_s2_v1/cruzr_s2_v1.urdf'
    paths=[config_path,native_path,cad_path,Path(__file__),Path(common.__file__),Path(common.fk.__file__)]
    hashes={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    cfg=yaml.safe_load(config_path.read_text())
    if cfg.get('robot_version')!='cruzr_s2_v1':raise ValueError('Unexpected runtime robot version')
    native,cad=[common.model_joints(p) for p in (native_path,cad_path)]
    roots={j['parent'] for j in native}-{j['child'] for j in native}
    if roots!={'mobile_base_link'}:raise ValueError('Unexpected native root')
    for joint in native:
        if joint['parent']=='mobile_base_link':joint['parent']='base_link'
    trees=[ET.parse(p).getroot() for p in (native_path,cad_path)]
    xml_limits=[{j.get('name'):j.find('limit').attrib for j in tree.findall('joint') if j.find('limit') is not None} for tree in trees]
    limits={}
    for component,names in [('lifter',[f'lifter_pitch_{i}_joint' for i in (1,2,3)]),
                            ('waist',['waist_yaw_joint']),('head',['head_yaw_joint','head_pitch_joint'])]:
        raw=cfg[component]['kinematics']['joint_limits']
        for i,name in enumerate(names):
            position=[float(x) for x in raw['pos'][i]]
            velocities=[float(raw['vel'][i])]
            for source in xml_limits:
                if name in source:
                    position=[max(position[0],float(source[name]['lower'])),min(position[1],float(source[name]['upper']))]
                    v=float(source[name].get('velocity',0))
                    if v>0:velocities.append(v)
            acc=float(raw['acc'][i])
            if not np.isfinite(position+velocities+[acc]).all() or position[0]>=position[1] or min(velocities)<=0 or acc<=0:
                raise ValueError('Invalid archived limits: '+name)
            limits[name]=dict(position_intersection_rad=position,
                minimum_positive_configured_velocity_rad_s=min(velocities),
                yaml_velocity_rad_s=float(raw['vel'][i]),yaml_acceleration_rad_s2=acc,
                physically_validated=False)
    bridges={}
    for side in ('L','R'):
        transforms=[]
        for joints in (native,cad):
            transform=np.eye(4)
            for name in [side+'_sixforce_joint',side+'_hand_joint']:
                joint=next(j for j in joints if j['name']==name)
                if joint['type']!='fixed':raise ValueError('Tool chain is not fixed')
                transform=transform@joint['origin']
            transforms.append(transform)
        bridges[side]=dict(cad_tool_to_native_tool=(np.linalg.inv(transforms[0])@transforms[1]).tolist(),
            native_wrist_to_tool=transforms[0].tolist(),cad_wrist_to_tool=transforms[1].tolist(),
            definition='p_native_tool = cad_tool_to_native_tool @ p_cad_tool; homogeneous metres',
            physical_registration_verified=False)
    comparisons={}
    for name,q in dict(HOME=np.zeros(20),**PICO_VARIANTS).items():
        poses=[common.fk.forward_kinematics(joints,dict(zip(JOINT_ORDER,q))) for joints in (native,cad)]
        rows={}
        for link in sorted(poses[0].keys()&poses[1].keys()):
            delta=np.linalg.inv(poses[0][link])@poses[1][link]
            rows[link]=dict(translation_m=float(np.linalg.norm(delta[:3,3])),
                rotation_rad=float(np.arccos(np.clip((np.trace(delta[:3,:3])-1)/2,-1,1))))
        comparisons[name]=rows
    if any(hashlib.sha256(Path(p).read_bytes()).hexdigest()!=sha for p,sha in hashes.items()):
        raise ValueError('Input changed during audit')
    result=dict(schema='cruzr-home-runtime-contract-audit-v1',status='ARCHIVED_CONFIGURATION_AUDIT_ONLY',
        base_alignment_assumption='mobile_base_link coincides with base_link; not physically measured',
        configured_frequency_hz=cfg['frequency'],limits=limits,tool_frame_bridges=bridges,
        reference_frame_comparison=comparisons,native_links=len(trees[0].findall('link')),
        native_urdf_has_head=False if not any('head' in l.get('name','') for l in trees[0].findall('link')) else True,
        limitations=['configuration values are not stopping or tracking measurements',
                     'calibrated arm/head kinematics are not reconstructed here',
                     'distinct frame names/orientations cannot be interchanged',
                     'no model modification or controller setting is applied'],
        source_sha256=hashes,physical_approval=False,movement_commands=0)
    with args.output.open('x') as file:json.dump(result,file,indent=2,allow_nan=False);file.write('\n')
    print(json.dumps(dict(output=str(args.output),status=result['status'],physical_approval=False)))


if __name__=='__main__':
    try:main()
    except (ValueError,OSError,ImportError,KeyError,StopIteration) as exc:
        print('ERROR: '+str(exc),file=sys.stderr);raise SystemExit(2)
