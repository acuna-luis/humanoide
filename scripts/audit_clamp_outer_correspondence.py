#!/usr/bin/env python3
"""Screen photo hypotheses with outer fixings; never exports 3D R/t or PASS."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import struct
import zipfile
import numpy as np
from audit_clamp_sensor_reference import ARCHIVE, inspect, boundary_loops
from audit_clamp_photo_correspondence import ROOT, fit_homography


def ordered(points):
    points = np.asarray(points)
    d = points-points.mean(axis=0)
    return points[np.argsort(np.arctan2(d[:,1],d[:,0]))]


def lateral_reflection_residual(points):
    """Point-set reflection test in CAD XY, not a physical rotation."""
    points = np.asarray(points,dtype=float)
    if points.ndim != 2 or points.shape[1] != 2 or not len(points) or not np.isfinite(points).all():
        raise ValueError('invalid_reflection_points')
    reflected = points*np.array([1,-1])
    return float(np.max(np.min(np.linalg.norm(reflected[:,None,:]-points[None,:,:],axis=2),axis=1)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    central_path = ROOT/'config/clamp_photo_landmarks.json'
    outer_path = ROOT/'config/clamp_outer_photo_landmarks.json'
    spec = json.loads(central_path.read_text())
    outer = json.loads(outer_path.read_text())
    cad = inspect(ARCHIVE)
    sides = {}
    with zipfile.ZipFile(ARCHIVE) as archive:
        for side in ('L','R'):
            photo = spec['sides'][side]
            if hashlib.sha256(Path(photo['path']).read_bytes()).hexdigest() != photo['sha256']:
                raise ValueError('photo_hash_mismatch')
            scale = np.asarray(photo['original_size_px'])/photo['annotation_canvas_size_px']
            centers = ordered(np.asarray(photo['centers_on_annotation_canvas_px'])*scale)
            observed = np.asarray(outer['sides'][side]['centers_on_annotation_canvas_px'])*scale
            source = ordered(cad['sides'][side]['approx_4p2mm_contour_centers_mm'])
            data = archive.read(cad['sides'][side]['mesh_member'])
            triangles = []
            for i in range(struct.unpack_from('<I',data,80)[0]):
                tri = [struct.unpack_from('<3f',data,84+50*i+12+12*j) for j in range(3)]
                if all(abs(p[2]-.004)<1e-7 for p in tri):
                    triangles.append(tri)
            probes = sorted(c['center_mm'] for c in boundary_loops(triangles)
                            if c['closed'] and all(abs(s-3.3)<.01 for s in c['size_mm']))
            if len(probes)!=4 or any(abs(abs(x)-28)>.001 or abs(abs(y)-17.5)>.001 for x,y in probes):
                raise ValueError('unexpected_outer_CAD_pattern')
            candidates = []
            for winding in (1,-1):
                for shift in range(6):
                    fit = fit_homography(source,np.roll(centers[::winding],shift,axis=0),probes)
                    predicted = np.asarray(fit['probe_prediction_px'])
                    matches = []
                    for permutation in itertools.permutations(range(4)):
                        distances = np.linalg.norm(predicted-observed[list(permutation)],axis=1)
                        matches.append((float(np.sqrt(np.mean(distances**2))),permutation))
                    rms, permutation = min(matches)
                    candidates.append(dict(winding=winding,cyclic_shift=shift,**fit,
                        outer_candidate_rms_px=rms,observed_outer_permutation=permutation))
            sides[side] = dict(cad_outer_centers_mm=probes,cad_outer_z_mm=4,
                CAD_lateral_reflection_residual_mm={
                    'central':lateral_reflection_residual(source),
                    'outer':lateral_reflection_residual(probes),
                    'combined':lateral_reflection_residual(np.vstack([source,probes]))},
                physical_face_normal_identified=False,
                observed_outer_px=observed.tolist(),
                hypotheses=sorted(candidates,key=lambda c:c['outer_candidate_rms_px']))
    report = dict(status='OUTER_FEATURE_SCREEN_ONLY_NOT_REGISTERED', sides=sides,
        archive_sha256=cad['archive_sha256'],
        input_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in (central_path,outer_path)},
        physical_authorized=False,robot_connections=0,movement_commands=0,
        limitations=['unproven_outer_feature_identity','manual_pixels_no_lens_calibration',
                     'reflection_invariant_landmarks_cannot_determine_face_normal',
                     'planar_extrapolation_ignores_different_head_heights_and_parallax',
                     'outer_permutation_selected_not_independently_confirmed',
                     'no_acceptance_threshold_no_3D_transform_no_clearance'])
    with args.output.open('x') as out:
        json.dump(report,out,indent=2,allow_nan=False)
        out.write('\n')
    for side,s in sides.items():
        print(side,[(c['winding'],c['cyclic_shift'],round(c['rms_fit_px'],3),round(c['outer_candidate_rms_px'],3))
                    for c in s['hypotheses']])
    print(report['status'])


if __name__ == '__main__':
    main()
