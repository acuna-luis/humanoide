#!/usr/bin/env python3
"""Contrast tabletop and floor patches from one captured cloud. Offline only."""
import argparse
import base64
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation
from inspect_entry_table_observation import inside_polygon, fit_visible_plane


def decode_points(capture):
    if not capture.get('capture_complete'):
        raise ValueError('Incomplete capture')
    cloud, camera, tf = (capture[k] for k in ('cloud', 'camera', 'camera_to_base'))
    stamps = capture['source_stamps_ns']
    if stamps['cloud'] != stamps['head'] or stamps['cloud'] != tf['stamp_ns']:
        raise ValueError('This comparison requires identical cloud, RGB and TF timestamps')
    if not (cloud['frame_id'] == camera['frame_id'] == tf['child'] == capture['head']['frame_id']) or tf['parent'] != 'base_link':
        raise ValueError('Inconsistent coordinate frames')
    fields = {f[0]: f[1:] for f in cloud['fields']}
    width, height, step, row = (int(cloud[k]) for k in ('width', 'height', 'point_step', 'row_step'))
    data = base64.b64decode(cloud['data_b64'], validate=True)
    if min(width, height, step) <= 0 or row < width*step or len(data) != row*height:
        raise ValueError('Invalid point cloud layout')
    columns = []
    for name in 'xyz':
        offset, datatype, count = fields[name]
        if datatype != 7 or count != 1 or not 0 <= offset <= step-4:
            raise ValueError('Expected scalar FLOAT32 XYZ fields')
        columns.append(np.ndarray((height, width), dtype=('>' if cloud['is_bigendian'] else '<')+'f4',
                                  buffer=data, offset=offset, strides=(row, step)).ravel())
    xyz = np.column_stack(columns).astype(float)
    xyz = xyz[np.isfinite(xyz).all(axis=1) & (xyz[:, 2] > .1) & (xyz[:, 2] < 6.)]
    k = np.asarray(camera['k'], float).reshape(3, 3)
    if not np.isfinite(k).all() or k[0, 0] <= 0 or k[1, 1] <= 0:
        raise ValueError('Invalid camera matrix')
    # Only the verified rectified optical-frame capture is supported here.
    if 'rectified_optical_frame' not in cloud['frame_id']:
        raise ValueError('Raw distorted projection is unsupported')
    projected = xyz @ k.T
    uv = projected[:, :2]/projected[:, 2:]
    q, t = np.asarray(tf['quaternion_xyzw'], float), np.asarray(tf['translation'], float)
    if q.shape != (4,) or t.shape != (3,) or not np.isfinite(q).all() or not np.isfinite(t).all() or abs(np.linalg.norm(q)-1) > 1e-4:
        raise ValueError('Invalid transform')
    return uv, Rotation.from_quat(q).apply(xyz)+t


def compare_patches(uv, points, annotations):
    planes = {}
    for name, patch in annotations['patches'].items():
        mask = inside_polygon(uv, patch['polygon_uv'])
        for excluded in patch.get('exclude_polygons_uv', []):
            mask &= ~inside_polygon(uv, excluded)
        selected = points[mask]
        c, n, inliers, residual = fit_visible_plane(selected)
        planes[name] = dict(point_base_m=c.tolist(), normal_base=n.tolist(), selected=len(selected),
                            inliers=int(inliers.sum()), residual95_m=float(np.quantile(residual[inliers], .95)),
                            observed_xy_bounds=[selected[inliers, :2].min(0).tolist(), selected[inliers, :2].max(0).tolist()])
    table = planes['table']; table_point = np.array(table['point_base_m'])
    comparisons = []
    for name, plane in planes.items():
        if name == 'table':
            continue
        point, normal = np.array(plane['point_base_m']), np.array(plane['normal_base'])
        delta = table_point-point
        vertical_height = float(normal@delta/normal[2])
        comparisons.append(dict(floor_patch=name, table_height_along_base_z_m=vertical_height,
                                table_height_normal_to_floor_m=float(normal@delta),
                                plane_angle_degrees=float(np.rad2deg(np.arccos(np.clip(normal@table['normal_base'], -1, 1)))),
                                table_xy_inside_observed_floor_patch_bounds=bool(np.all(table_point[:2] >= plane['observed_xy_bounds'][0]) and np.all(table_point[:2] <= plane['observed_xy_bounds'][1]))))
    if not comparisons:
        raise ValueError('At least one floor patch required')
    heights = [row['table_height_along_base_z_m'] for row in comparisons]
    return dict(scope='SAME_CAPTURE_PLANE_CONSISTENCY_DIAGNOSTIC', planes=planes, comparisons=comparisons,
                height_spread_m=max(heights)-min(heights),
                known_table_height_m=annotations['known_table_height_m'],
                inferred_height_minus_known_m=[h-annotations['known_table_height_m'] for h in heights],
                physical_approval=False, total_error_bound_established=False, calibration_changed=False,
                limitations=['Visible patches only; plane extrapolation is explicitly identified.',
                             'Residuals do not bound systematic depth bias, hidden geometry or timing.',
                             'Shared TF translation cancels; camera depth distortion does not.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('capture', 'annotations', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a new output')
    sources = [args.capture, args.annotations, Path(__file__), Path(__file__).with_name('inspect_entry_table_observation.py')]
    hashes = {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    uv, points = decode_points(json.loads(args.capture.read_text()))
    result = compare_patches(uv, points, json.loads(args.annotations.read_text()))
    result['sources_sha256'] = hashes
    if any(hashlib.sha256(Path(p).read_bytes()).hexdigest() != h for p, h in hashes.items()):
        raise RuntimeError('Source changed')
    with args.output.open('x') as f:
        json.dump(result, f, indent=2, allow_nan=False); f.write('\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('sources_sha256', 'planes')}, indent=2))


if __name__ == '__main__':
    main()
