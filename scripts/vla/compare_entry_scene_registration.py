#!/usr/bin/env python3
"""Compare a fitted table plane to the same observed points, offline only."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from inspect_entry_table_observation import inside_polygon, fit_visible_plane


def signed_plane_residual(points, origin, normal):
    points,origin,normal=(np.asarray(x,float) for x in (points,origin,normal))
    if (points.ndim!=2 or points.shape[1]!=3 or origin.shape!=(3,) or normal.shape!=(3,)
            or not np.isfinite(points).all() or not np.isfinite([origin,normal]).all()
            or np.linalg.norm(normal)<1e-12):raise ValueError('Invalid plane comparison')
    return (points-origin)@(normal/np.linalg.norm(normal))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('points','annotations','fit','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('Choose a new output')
    sources=[args.points,args.annotations,args.fit,Path(__file__),
             Path(__file__).with_name('inspect_entry_table_observation.py')]
    hashes={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    annotations=json.loads(args.annotations.read_text());fit=json.loads(args.fit.read_text())
    if annotations['frame_id']!='base_link':parser.error('Expected base frame')
    with np.load(args.points,allow_pickle=False) as archive:uv,xyz=archive['uv'],archive['points_base']
    mask=inside_polygon(uv,annotations['table_visible_polygon_uv'])
    for polygon in annotations['exclude_polygons_uv']:mask &= ~inside_polygon(uv,polygon)
    center,normal,inliers,residual=fit_visible_plane(xyz[mask]);points=xyz[mask][inliers]
    tables=[o for o in fit['objects'] if o['id']=='tabletop_fit']
    if len(tables)!=1:parser.error('Expected one fitted table')
    table=tables[0];fit_normal=Rotation.from_rotvec(table['rotation_vector_rad']).apply([0,0,1])
    signed=signed_plane_residual(points,table['front_top_midpoint_base_m'],fit_normal)
    result=dict(scope='SAME_OBSERVED_PATCH_PLANE_COMPARISON_NOT_CALIBRATION',physical_approval=False,
                point_count=len(points),fitted_plane_signed_residual_median_mm=float(np.median(signed)*1000),
                fitted_plane_absolute_residual95_mm=float(np.quantile(abs(signed),.95)*1000),
                fitted_plane_signed_range_mm=(np.array([signed.min(),signed.max()])*1000).tolist(),
                cloud_plane_residual95_mm=float(np.quantile(residual[inliers],.95)*1000),
                angle_between_plane_normals_degrees=float(np.rad2deg(np.arccos(np.clip(abs(normal@fit_normal),0,1)))),
                same_points_compared=True,total_error_bound_established=False,
                timestamp_synchronization_verified=False,source_sha256=hashes)
    if any(hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h for p,h in hashes.items()):raise RuntimeError('Sources changed')
    with args.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'}))


if __name__=='__main__':main()
