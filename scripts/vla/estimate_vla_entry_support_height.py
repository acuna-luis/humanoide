#!/usr/bin/env python3
"""Exploratory height reconstruction from selected dataset rim pixels.

Assumes the archived camera calibration/mount, level support, a 603x217 mm
box width/height and a 150 mm base-to-floor offset. Pixel variation is NOT
the total uncertainty. This does not calibrate or approve a physical fixture.
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import sys
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'teleoperation'))
import review_clamp_trajectory_optimization as common
from cruzr_pico_to_home_owner_gate import JOINT_ORDER
from derive_vla_fixture_pose import quaternion_rotation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('registration','entries','camera-info','output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): parser.error('Output already exists')
    registration = json.loads(args.registration.read_text())
    entries = json.loads(args.entries.read_text())
    inverse_k = np.linalg.inv(np.asarray(json.loads(args.camera_info.read_text())['k']).reshape(3,3))
    urdf = Path(__file__).resolve().parents[2] / 'cruzr_s2_description_splint/cruzr_s2_description/urdf/cruzr_s2_v1/cruzr_s2_v1.urdf'
    joints = common.model_joints(urdf)
    current = common.fk.forward_kinematics(joints,dict(zip(registration['joints']['name'],registration['joints']['position'])))
    tf = registration['camera_to_base']
    camera = np.eye(4)
    camera[:3,:3] = quaternion_rotation(tf['quaternion_xyzw'])
    camera[:3,3] = tf['translation']
    mount = np.linalg.inv(current['head_pitch_link']) @ camera
    output = dict(scope='INFERENCE_NOT_CALIBRATION', physical_approval=False,
                  box_width_height_m=[0.603,0.217], assumed_floor_below_base_m=0.15,
                  pixel_only_variation_px=4, total_uncertainty_bounded=False, estimates={},
                  sources_sha256={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in (args.registration,args.entries,args.camera_info,urdf)})
    for episode,pixels in [('episode_000430',[[296,283],[720,284]]),('episode_000438',[[307,259],[749,260]])]:
        pose = common.fk.forward_kinematics(joints,dict(zip(JOINT_ORDER,entries[episode]['first_state'])))['head_pitch_link'] @ mount
        def height(points):
            rays = np.asarray([pose[:3,:3] @ inverse_k @ np.asarray([u,v,1.]) for u,v in points])
            if not (rays[:,2] < 0).all(): raise ValueError('Rim rays must point downward')
            slopes = rays[:,:2] / rays[:,2,None]
            separation = np.linalg.norm(slopes[1]-slopes[0])
            if separation < 1e-9: raise ValueError('Degenerate rim')
            return float(pose[2,3] - 0.603/separation - 0.217 + 0.15)
        variations = [height(np.asarray(pixels)+np.asarray(offset).reshape(2,2))
                      for offset in itertools.product((-4,4),repeat=4)]
        output['estimates'][episode] = dict(rim_pixels_uv=pixels,
            surface_height_floor_m=height(pixels), pixel_only_height_range_m=[min(variations),max(variations)])
    args.output.write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(output['estimates'],indent=2))


if __name__ == '__main__':
    main()
