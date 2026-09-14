#!/usr/bin/env python3
"""Compare a visible tabletop patch with archived bounds; never calibrate motion."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def inside_polygon(uv, polygon):
    uv = np.asarray(uv, float)
    polygon = np.asarray(polygon, float)
    if uv.ndim != 2 or uv.shape[1] != 2 or polygon.ndim != 2 or polygon.shape[1] != 2 or len(polygon) < 3:
        raise ValueError('Invalid pixel polygon')
    if not np.isfinite(uv).all() or not np.isfinite(polygon).all():
        raise ValueError('Nonfinite pixel coordinates')
    x, y = uv.T
    result = np.zeros(len(uv), bool)
    for a, b in zip(polygon, np.roll(polygon, -1, axis=0)):
        if a[1] == b[1]:
            continue
        crossing = ((a[1] > y) != (b[1] > y))
        edge_x = a[0] + (y-a[1])*(b[0]-a[0])/(b[1]-a[1])
        result ^= crossing & (x < edge_x)
    return result


def fit_visible_plane(points, *, threshold_m=.005, iterations=600):
    points = np.asarray(points, float)
    if points.ndim != 2 or points.shape[1] != 3 or len(points) < 30 or not np.isfinite(points).all():
        raise ValueError('At least 30 finite XYZ points required')
    if not np.isfinite(threshold_m) or threshold_m <= 0 or iterations < 1:
        raise ValueError('Invalid fitting budget')
    rng = np.random.default_rng(149)
    best = np.zeros(len(points), bool)
    for _ in range(iterations):
        a, b, c = points[rng.choice(len(points), 3, replace=False)]
        n = np.cross(b-a, c-a)
        length = np.linalg.norm(n)
        if length < 1e-10:
            continue
        n /= length
        if abs(n[2]) < np.cos(np.deg2rad(30)):
            continue
        inliers = np.abs((points-a) @ n) <= threshold_m
        if inliers.sum() > best.sum():
            best = inliers
    if best.sum() < max(30, len(points)*.5):
        raise ValueError('No dominant near-horizontal plane in observed patch')
    centre = points[best].mean(axis=0)
    _, singular, vh = np.linalg.svd(points[best]-centre, full_matrices=False)
    if singular[1] < 1e-4 or singular[1]/singular[0] < .01:
        raise ValueError('Insufficient two-dimensional support')
    normal = vh[-1]
    if normal[2] < 0:
        normal = -normal
    if normal[2] < np.cos(np.deg2rad(30)):
        raise ValueError('Refitted plane outside orientation hypothesis')
    residual = np.abs((points-centre) @ normal)
    return centre, normal, best, residual


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('points', 'annotations', 'obstacles', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output must be new')
    sources = [args.points, args.annotations, args.obstacles, Path(__file__)]
    hashes = {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    with np.load(args.points, allow_pickle=False) as archive:
        uv, xyz = archive['uv'], archive['points_base']
    if xyz.shape != (len(uv), 3) or not np.isfinite(xyz).all():
        parser.error('Invalid base-frame point array')
    annotations = json.loads(args.annotations.read_text())
    if annotations['frame_id'] != 'base_link':
        parser.error('Wrong point frame')
    mask = inside_polygon(uv, annotations['table_visible_polygon_uv'])
    for exclusion in annotations['exclude_polygons_uv']:
        mask &= ~inside_polygon(uv, exclusion)
    points = xyz[mask]
    centre, normal, inliers, residual = fit_visible_plane(points)
    old = np.asarray(json.loads(args.obstacles.read_text())['tabletop_inferred'], float)
    if old.shape != (2, 3) or not np.isfinite(old).all() or not (old[1] > old[0]).all():
        parser.error('Invalid archived bounds')
    observed = points[inliers]
    result = dict(scope='VISIBLE_SURFACE_COMPARISON_ONLY', physical_approval=False,
        scene_complete=False, collision_geometry_changed=False, total_uncertainty_bounded=False,
        fitting_threshold_m=.005, fitting_threshold_is_not_sensor_error_bound=True,
        selected_points=len(points), inlier_points=int(inliers.sum()),
        plane_point_base_m=centre.tolist(), plane_normal_base=normal.tolist(),
        fitted_tilt_degrees=float(np.rad2deg(np.arccos(normal[2]))),
        fitted_tilt_is_not_verified_physical_table_tilt=True,
        inlier_residual95_m=float(np.quantile(residual[inliers], .95)),
        observed_patch_bounds_base_m=[observed.min(axis=0).tolist(), observed.max(axis=0).tolist()],
        observed_bounds_are_not_full_table_bounds=True,
        archived_table_bounds_base_m=old.tolist(),
        archived_top_minus_fitted_patch_centre_m=float(old[1, 2]-centre[2]),
        archived_front_to_nearest_patch_point_m=float(observed[:, 0].min()-old[0, 0]),
        inliers_outside_archived_bounds=int(np.any((observed < old[0]) | (observed > old[1]), axis=1).sum()),
        sources_sha256=hashes, annotations=annotations)
    if any(hashlib.sha256(Path(p).read_bytes()).hexdigest() != h for p, h in hashes.items()):
        raise RuntimeError('Input changed during inspection')
    with args.output.open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('sources_sha256', 'annotations')}, indent=2))


if __name__ == '__main__':
    main()
