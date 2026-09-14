#!/usr/bin/env python3
"""Fit declared rectangular fixtures to RGB corners; hypotheses, never motion gates."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation


def rectangle(length, width):
    if not np.isfinite([length, width]).all() or min(length, width) <= 0:
        raise ValueError('Invalid rectangle dimensions')
    # Front-left, back-left, back-right, front-right in robot-oriented axes.
    return np.array([[0., width/2, 0.], [length, width/2, 0.],
                     [length, -width/2, 0.], [0., -width/2, 0.]])


def project(corners, pose, camera, intrinsic):
    points = corners @ Rotation.from_rotvec(pose[:3]).as_matrix().T + pose[3:]
    optical = (points-camera[:3, 3]) @ camera[:3, :3]
    if (optical[:, 2] <= .01).any():
        raise ValueError('Points behind camera')
    homogeneous = optical @ intrinsic.T
    return homogeneous[:, :2]/homogeneous[:, 2, None]


def fit(corners, pixels, camera, intrinsic, seed):
    pixels = np.asarray(pixels, float)
    if pixels.shape != (4, 2) or not np.isfinite(pixels).all():
        raise ValueError('Four finite ordered corners required')
    def residual(pose):
        try:
            return (project(corners, pose, camera, intrinsic)-pixels).ravel()
        except ValueError:
            return np.full(8, 1e6)
    result = least_squares(residual, seed, max_nfev=500,
        bounds=([-.6, -.6, -.8, .05, -1., .1], [.6, .6, .8, 2., 1., 1.5]),
        ftol=1e-12, xtol=1e-12, gtol=1e-12)
    if not result.success or not np.isfinite(result.x).all():
        raise ValueError('Pose fit did not converge')
    return result.x, project(corners, result.x, camera, intrinsic)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('capture', 'camera-to-base', 'annotations', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output must be new')
    sources = [args.capture, args.camera_to_base, args.annotations, Path(__file__)]
    hashes = {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    capture = json.loads(args.capture.read_text()); tf = json.loads(args.camera_to_base.read_text())
    annotations = json.loads(args.annotations.read_text())
    if tf['parent'] != 'base_link' or tf['child'] != capture['camera']['frame_id']:
        parser.error('Camera frame mismatch')
    intrinsic = np.array(capture['camera']['k'], float).reshape(3, 3)
    if not np.isfinite(intrinsic).all() or np.linalg.det(intrinsic) <= 0:
        parser.error('Invalid intrinsic matrix')
    camera = np.eye(4); camera[:3, :3] = Rotation.from_quat(tf['quaternion_xyzw']).as_matrix()
    camera[:3, 3] = tf['translation']
    variations = annotations['pixel_variation_px']
    if not np.isfinite(variations) or not 0 <= variations <= 20:
        parser.error('Invalid pixel sensitivity scenario')
    rng = np.random.default_rng(149); rows = []
    for record in annotations['objects']:
        length, width, thickness = record['size_m']
        if not np.isfinite(thickness) or thickness <= 0:
            parser.error('Invalid thickness')
        corners = rectangle(length, width); pixels = np.array(record['top_corners_uv'], float)
        poses = []
        for angles in ([0, 0, 0], [.1, -.1, 0], [-.1, .1, 0]):
            pose, predicted = fit(corners, pixels, camera, intrinsic, angles+record['seed_front_midpoint_base_m'])
            poses.append((float(np.linalg.norm(predicted-pixels)), pose, predicted))
        _, pose, predicted = min(poses, key=lambda x: x[0])
        rotation = Rotation.from_rotvec(pose[:3])
        centre = pose[3:]+rotation.apply([length/2, 0, -thickness/2])
        sensitivity = []
        for _ in range(32):
            varied = pixels + rng.uniform(-variations, variations, pixels.shape)
            trial, _ = fit(corners, varied, camera, intrinsic, pose)
            sensitivity.append(trial.tolist())
        vertices = np.vstack([corners, corners-[0, 0, thickness]])
        world = rotation.apply(vertices)+pose[3:]
        rows.append(dict(id=record['id'], size_m=record['size_m'],
            front_top_midpoint_base_m=pose[3:].tolist(), rotation_vector_rad=pose[:3].tolist(),
            scene_object=dict(id=record['id'], type='box', size_m=record['size_m'],
                              center_m=centre.tolist(), rpy_rad=rotation.as_euler('xyz').tolist()),
            top_corners_uv=pixels.tolist(), reprojected_corners_uv=predicted.tolist(),
            corner_residuals_px=np.linalg.norm(predicted-pixels, axis=1).tolist(),
            fitted_surface_tilt_degrees=float(np.rad2deg(np.arccos(rotation.as_matrix()[2, 2]))),
            bounds_base_m=[world.min(axis=0).tolist(), world.max(axis=0).tolist()],
            pixel_only_sensitivity_poses=sensitivity, pixel_sensitivity_is_not_total_error=True,
            physical_approval=False))
    result = dict(scope='RECTANGLE_FIT_HYPOTHESES_ONLY', physical_approval=False,
        registration_qualified=False, scene_complete=False, total_uncertainty_bounded=False,
        rounded_corners_and_occlusion_not_resolved=True, objects=rows,
        annotations=annotations, sources_sha256=hashes)
    if any(hashlib.sha256(Path(p).read_bytes()).hexdigest() != h for p, h in hashes.items()):
        raise RuntimeError('Input changed during fitting')
    with args.output.open('x') as f: json.dump(result, f, indent=2); f.write('\n')
    for r in rows:
        print(r['id'], 'pixel residuals', r['corner_residuals_px'],
              'front midpoint', r['front_top_midpoint_base_m'], 'tilt', r['fitted_surface_tilt_degrees'])


if __name__ == '__main__':
    main()
