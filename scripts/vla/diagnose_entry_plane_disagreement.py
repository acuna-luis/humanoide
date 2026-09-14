#!/usr/bin/env python3
"""Offline plane disagreement diagnosis; does not estimate a robot calibration."""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from check_entry_scene_planes import decode_points
from inspect_entry_table_observation import inside_polygon, fit_visible_plane
from prepare_vla_entry_bundle import digest


def intersect_rays(pixels, intrinsic, camera, origin, normal):
    rays = np.column_stack([pixels, np.ones(len(pixels))]) @ np.linalg.inv(intrinsic).T
    rays = rays @ camera[:3, :3].T
    denominator = rays @ normal
    if np.any(abs(denominator) < 1e-9):
        raise ValueError('Ray parallel to plane')
    scale = ((origin-camera[:3, 3]) @ normal)/denominator
    if not np.isfinite(scale).all() or (scale <= 0).any():
        raise ValueError('Invalid forward intersection')
    return camera[:3, 3] + rays*scale[:, None]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('capture', 'annotations', 'fit', 'output'):
        parser.add_argument('--'+key, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): parser.error('Choose new output')
    sources = [args.capture, args.annotations, args.fit, Path(__file__),
               Path(__file__).with_name('check_entry_scene_planes.py'),
               Path(__file__).with_name('inspect_entry_table_observation.py')]
    hashes = {str(p.resolve()): digest(p) for p in sources}
    capture = json.loads(args.capture.read_text()); annotations = json.loads(args.annotations.read_text())
    uv, xyz = decode_points(capture)
    mask = inside_polygon(uv, annotations['table_visible_polygon_uv'])
    for polygon in annotations['exclude_polygons_uv']: mask &= ~inside_polygon(uv, polygon)
    xyz, uv = xyz[mask], uv[mask]
    table = next(r for r in json.loads(args.fit.read_text())['objects'] if r['id'] == 'tabletop_fit')
    rgb_origin = np.asarray(table['front_top_midpoint_base_m'])
    rgb_normal = Rotation.from_rotvec(table['rotation_vector_rad']).apply([0, 0, 1])
    tf = capture['camera_to_base']; camera = np.eye(4)
    camera[:3, :3] = Rotation.from_quat(tf['quaternion_xyzw']).as_matrix(); camera[:3, 3] = tf['translation']
    median_u, median_v = np.median(uv, axis=0)
    regions = {'all': np.ones(len(uv), bool), 'left': uv[:, 0] <= median_u,
               'right': uv[:, 0] > median_u, 'upper': uv[:, 1] <= median_v,
               'lower': uv[:, 1] > median_v}
    rows = []
    for name, selected in regions.items():
        try:
            origin, normal, inliers, residual = fit_visible_plane(xyz[selected])
        except ValueError as error:
            rows.append(dict(region=name, status='INSUFFICIENT_PLANE_SUPPORT', reason=str(error))); continue
        points = xyz[selected][inliers]
        signed = (points-rgb_origin) @ rgb_normal
        # A common rigid camera-to-base transform preserves this disagreement.
        optical_points = (points-camera[:3, 3]) @ camera[:3, :3]
        optical_origin = (rgb_origin-camera[:3, 3]) @ camera[:3, :3]
        optical_normal = rgb_normal @ camera[:3, :3]
        invariant_error = float(np.max(abs(signed-(optical_points-optical_origin) @ optical_normal)))
        corners = intersect_rays(np.asarray(table['top_corners_uv']), np.asarray(capture['camera']['k']).reshape(3, 3), camera, origin, normal)
        rows.append(dict(region=name, status='OBSERVATION_ONLY', points=len(points),
                         median_rgb_difference_mm=float(np.median(signed)*1000),
                         residual95_mm=float(np.quantile(residual[inliers], .95)*1000),
                         common_transform_invariance_error_m=invariant_error,
                         corner_edge_lengths_m=np.linalg.norm(np.roll(corners, -1, axis=0)-corners, axis=1).tolist(),
                         corner_points_base_m=corners.tolist()))
    result = dict(scope='PLANE_AND_ANNOTATION_DIAGNOSTIC_NOT_CALIBRATION', physical_approval=False,
                  common_camera_to_base_error_identifiable_from_this_comparison=False,
                  declared_table_size_m=table['size_m'], regions=rows, source_sha256=hashes)
    if any(digest(Path(p)) != h for p, h in hashes.items()): raise RuntimeError('Sources changed')
    with args.output.open('x') as f: json.dump(result, f, indent=2, allow_nan=False); f.write('\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'source_sha256'}))


if __name__ == '__main__': main()
