#!/usr/bin/env python3
"""Offline hypothesis comparison, NEVER a calibrated 3D mounting transform.

Tests cyclic correspondences in both winding directions. A 2D homography may
include a reflection: it must never be used as a 3D robot rotation matrix.
All points participate in fitting; these are not independent validation errors.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def fit_homography(source, target, probe_source=None):
    source, target = np.asarray(source, dtype=float), np.asarray(target, dtype=float)
    if source.shape != target.shape or source.ndim != 2 or source.shape[1] != 2 or len(source) < 4:
        raise ValueError('invalid_point_shapes')
    if not np.isfinite(source).all() or not np.isfinite(target).all():
        raise ValueError('nonfinite_points')
    def normalize(points):
        center = points.mean(axis=0)
        scale = np.sqrt(((points-center)**2).sum(axis=1).mean())
        if scale <= 1e-12:
            raise ValueError('degenerate_points')
        return (points-center)/scale, center, scale
    s, sc, ss = normalize(source)
    t, tc, ts = normalize(target)
    rows, values = [], []
    for (x,y), (u,v) in zip(s,t):
        rows.extend([[x,y,1,0,0,0,-u*x,-u*y], [0,0,0,x,y,1,-v*x,-v*y]])
        values.extend([u,v])
    h, _, rank, _ = np.linalg.lstsq(rows, values, rcond=None)
    if rank < 8:
        raise ValueError('degenerate_homography')
    h = np.append(h, 1).reshape(3,3)
    projected = np.column_stack([s, np.ones(len(s))]) @ h.T
    if np.any(np.abs(projected[:,2]) < 1e-10):
        raise ValueError('projection_at_infinity')
    predicted = projected[:,:2]/projected[:,2,None]*ts+tc
    errors = np.linalg.norm(predicted-target, axis=1)
    # No transform is exported. Optional projections are 2D candidate features,
    # not a calibrated 3D pose or an assertion that physical features match.
    result = dict(rms_fit_px=float(np.sqrt(np.mean(errors**2))), max_fit_px=float(max(errors)))
    if probe_source is not None:
        probes = np.asarray(probe_source, dtype=float)
        if probes.ndim != 2 or probes.shape[1] != 2 or not len(probes) or not np.isfinite(probes).all():
            raise ValueError('invalid_probe_points')
        projected = np.column_stack([(probes-sc)/ss, np.ones(len(probes))]) @ h.T
        if np.any(np.abs(projected[:,2]) < 1e-10):
            raise ValueError('probe_projection_at_infinity')
        result['probe_prediction_px'] = (projected[:,:2]/projected[:,2,None]*ts+tc).tolist()
    return result


def hypotheses(cad, pixels):
    cad, pixels = np.asarray(cad, dtype=float), np.asarray(pixels, dtype=float)
    if cad.shape != (6,2) or pixels.shape != (6,2):
        raise ValueError('expected_six_points_each')
    def ordered(points):
        d = points-points.mean(axis=0)
        return points[np.argsort(np.arctan2(d[:,1],d[:,0]))]
    cad, pixels = ordered(cad), ordered(pixels)
    results = []
    for winding in (1,-1):
        for shift in range(6):
            target = np.roll(pixels[::winding], shift, axis=0)
            results.append(dict(winding=winding, cyclic_shift=shift,
                                **fit_homography(cad,target)))
    return sorted(results, key=lambda r: r['rms_fit_px'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--landmarks', type=Path, default=ROOT/'config/clamp_photo_landmarks.json')
    parser.add_argument('--cad-report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    spec, cad = json.loads(args.landmarks.read_text()), json.loads(args.cad_report.read_text())
    if spec['schema'] != 'clamp-photo-landmarks-v1' or cad['status'] != 'CAD_REFERENCE_CANDIDATE_ONLY':
        raise ValueError('unexpected_input_schema_or_status')
    results = {}
    for side in ('L','R'):
        photo = spec['sides'][side]
        if hashlib.sha256(Path(photo['path']).read_bytes()).hexdigest() != photo['sha256']:
            raise ValueError('photo_hash_mismatch:'+side)
        pixels = np.asarray(photo['centers_on_annotation_canvas_px'])*(
            np.asarray(photo['original_size_px'])/photo['annotation_canvas_size_px'])
        results[side] = hypotheses(cad['sides'][side]['approx_4p2mm_contour_centers_mm'], pixels)
    result = dict(status='PHOTO_CAD_HYPOTHESES_ONLY_NO_3D_REGISTRATION', sides=results,
                  landmarks_sha256=hashlib.sha256(args.landmarks.read_bytes()).hexdigest(),
                  cad_report_sha256=hashlib.sha256(args.cad_report.read_bytes()).hexdigest(),
                  physical_authorized=False, movement_commands=0, robot_connections=0,
                  limitations=['manual_image_points', 'unproven_CAD_feature_identity',
                               'fit_not_independent_validation', 'no_lens_calibration',
                               'no_3D_transform_or_clearance_derived'])
    with args.output.open('x') as out:
        json.dump(result, out, indent=2, allow_nan=False)
        out.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
