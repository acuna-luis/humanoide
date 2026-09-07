#!/usr/bin/env python3
"""Offline timestamp pairing only. No ROS, network, movement or safety approval."""
import argparse
import bisect
import json
from pathlib import Path


def stamp(row):
    s = row['header']['stamp']
    sec, ns = s['sec'], s['nanosec']
    if type(sec) is not int or type(ns) is not int or sec < 0 or not 0 <= ns < 10**9:
        raise ValueError('invalid_timestamp')
    value = sec * 10**9 + ns
    if value == 0:
        raise ValueError('zero_timestamp_not_a_frame_clock')
    return value


def pair(images, joints, max_delta_ns, clock_reference_verified=False):
    if type(max_delta_ns) is not int or max_delta_ns <= 0:
        raise ValueError('invalid_tolerance')
    times = [stamp(j) for j in joints]
    if any(a >= b for a, b in zip(times, times[1:])):
        raise ValueError('joint_timestamps_must_increase_strictly')
    rows = []
    for image in images:
        t = stamp(image)
        k = bisect.bisect_left(times, t)
        candidates = [i for i in (k-1, k) if 0 <= i < len(times)]
        nearest = min(candidates, key=lambda i: (abs(times[i]-t), i)) if candidates else None
        delta = None if nearest is None else times[nearest]-t
        bracketed = bool(times) and times[0] <= t <= times[-1]
        within = delta is not None and abs(delta) <= max_delta_ns
        rows.append(dict(image_stamp_ns=t, joint_index=nearest, delta_ns=delta,
                         bracketed=bracketed, within_tolerance=within,
                         temporal_pair_accepted=(clock_reference_verified is True and bracketed and within)))
    return dict(pairs=rows, clock_reference_verified=clock_reference_verified is True,
                max_delta_ns=max_delta_ns, physical_authorized=False,
                limitations=['nearest_sample_not_interpolated_state',
                             'no_image_visibility_or_joint_content_validation',
                             'tolerance_is_diagnostic_not_a_safety_limit'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--max-delta-ns', type=int, required=True)
    a = p.parse_args()
    data = json.loads(a.input.read_text())
    # CLI cannot self-certify clock synchronization.
    result = pair(data['images'], data['joints'], a.max_delta_ns)
    with a.output.open('x') as out:
        json.dump(result, out, indent=2, allow_nan=False)
        out.write('\n')


if __name__ == '__main__':
    main()
