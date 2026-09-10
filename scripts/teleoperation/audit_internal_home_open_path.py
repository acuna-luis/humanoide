#!/usr/bin/env python3
"""Offline sweep of the internal HOME candidate; never communicates with ROS."""
import argparse
import hashlib
import json
from pathlib import Path

from audit_pico_home_open_path import audit
import cruzr_internal_home_open_path as model


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--samples', type=int, default=501)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output already exists')
    result = audit(args.snapshot_dir, args.samples, path=model.waypoints,
                   durations=model.DURATIONS[20], revision='home_open_v3_20s',
                   variants=model.REVIEW_STARTS)
    result['source_sha256'][model.__file__] = hashlib.sha256(Path(model.__file__).read_bytes()).hexdigest()
    result['timing_candidates'] = {}
    for seconds, durations in model.DURATIONS.items():
        entries = {}
        for label, start in model.REVIEW_STARTS.items():
            points = model.waypoints(start)
            entries[label] = []
            for a, b, duration in zip(points, points[1:], durations):
                delta = max(abs(x-y) for x,y in zip(a,b))
                entries[label].append({'duration_s':duration,
                    'quintic_vmax_rad_s':1.875*delta/duration,
                    'quintic_amax_rad_s2':(10*(3**0.5)/3)*delta/duration**2})
        result['timing_candidates'][str(seconds)] = entries
    result['limitations'].extend([
        'Opening uses native relative joint port; hardware trial of this primitive pending.',
        'Only four nominal starts reviewed; arbitrary poses and loaded HOME not qualified.',
        'Six-second timing is an offline draft, not an approved automatic boot profile.',
    ])
    with args.output.open('x') as f:
        json.dump(result, f, indent=2, allow_nan=False)
