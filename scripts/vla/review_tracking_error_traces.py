#!/usr/bin/env python3
"""Offline requested-command discrepancies; never a servo or stopping certificate."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/teleoperation'))
from general_home.trace_analysis import ACT_TOPIC, NAMES, analyze, decode_actuators, strict_json

SCENARIOS = (0.1, 0.5, 1.0, 5.0)


def statistics(values):
    if not values:
        return None  # Absence of evidence must never look like zero error.
    ordered = sorted(values)
    percentile = lambda p: ordered[max(0, math.ceil(p * len(ordered)) - 1)]
    return dict(samples=len(values), maximum_deg=max(values),
                rms_deg=math.sqrt(sum(x*x for x in values)/len(values)),
                p95_deg=percentile(.95), p99_deg=percentile(.99),
                p999_deg=percentile(.999),
                samples_exceeding={str(d): sum(x > d for x in values) for d in SCENARIOS})


def review_records(records, max_gap=.05):
    quality = analyze(records, max_gap)
    result = dict(quality=quality, eligible_for_observed_comparison=False,
                  physical_approval=False, servo_tracking_bound_qualified=False,
                  stopping_bound_qualified=False, joints=None, all_samples=None)
    if quality['issues']:
        return result
    samples = [(r['received_monotonic_ns'], decode_actuators(r['message'])[1])
               for r in records if r.get('topic') == ACT_TOPIC]
    extra_issues = []
    for name in NAMES:
        stamps = [row[name]['stamp_ns'] for _, row in samples]
        if max((b-a)/1e9 for a, b in zip(stamps, stamps[1:])) > max_gap:
            extra_issues.append('source_gap_exceeded:' + name)
    # Fault observations remain in the inventory, never pooled as healthy tracking.
    if any(j['fault_samples'] or j['disabled_samples'] for j in quality['joints'].values()):
        extra_issues.append('fault_or_disabled_actuator')
    result['additional_quality_issues'] = extra_issues
    if extra_issues:
        return result
    rows = {}
    all_errors = []
    moving_frame_errors = []
    for name in NAMES:
        values = [j[name] for _, j in samples]
        errors = [math.degrees(abs(v['cmd_pos']-v['position'])) for v in values]
        peak = max(range(len(errors)), key=errors.__getitem__)
        moving = [e for e, v in zip(errors, values) if abs(v['velocity']) > .01]
        span = math.degrees(max(v['position'] for v in values)-min(v['position'] for v in values))
        rows[name] = dict(all_samples=statistics(errors),
                          moving_joint_samples=statistics(moving),
                          position_span_deg=span,
                          substantial_motion_observed=span >= 1.0 and bool(moving),
                          maximum_abs_velocity_rad_s=max(abs(v['velocity']) for v in values),
                          peak_witness=dict(sample_index=peak,
                              source_stamp_ns=values[peak]['stamp_ns'],
                              received_monotonic_ns=samples[peak][0],
                              position_motor_rad=values[peak]['position'],
                              requested_cmd_pos_motor_rad=values[peak]['cmd_pos']))
        all_errors.extend(errors)
    moving_frames = 0
    for _, joints in samples:
        if max(abs(v['velocity']) for v in joints.values()) > .01:
            moving_frames += 1
            moving_frame_errors.extend(math.degrees(abs(v['cmd_pos']-v['position'])) for v in joints.values())
    source_deltas = [(b[NAMES[0]]['stamp_ns']-a[NAMES[0]]['stamp_ns'])/1e9
                     for (_, a), (_, b) in zip(samples, samples[1:])]
    result.update(eligible_for_observed_comparison=True, joints=rows,
                  all_samples=statistics(all_errors), moving_frame_samples=statistics(moving_frame_errors),
                  moving_frames=moving_frames, actuator_frames=len(samples),
                  observed_duration_seconds=(samples[-1][0]-samples[0][0])/1e9,
                  source_interval_seconds=dict(minimum=min(source_deltas),
                      median=sorted(source_deltas)[len(source_deltas)//2], maximum=max(source_deltas)),
                  substantial_motion_joints=[n for n in NAMES if rows[n]['substantial_motion_observed']])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, action='append', required=True,
                        help='Repeat for each archived passive trace.jsonl; no robot IO')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output must be new')
    paths = [p.resolve() for p in args.input]
    if len(set(paths)) != len(paths):
        parser.error('Duplicate input path')
    reports = []
    seen_hashes = set()
    for path in paths:
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest in seen_hashes:
            parser.error('Duplicate trace contents; do not count the same observation twice')
        seen_hashes.add(digest)
        row = dict(path=str(path), sha256=digest)
        try:
            row.update(review_records([strict_json(line) for line in raw.decode().splitlines() if line.strip()]))
        except (ValueError, TypeError, AttributeError, UnicodeError) as exc:
            row.update(eligible_for_observed_comparison=False, parse_error=str(exc), physical_approval=False)
        reports.append(row)
    result = dict(schema='cruzr-requested-command-discrepancy-review-v1',
                  physical_approval=False, recommended_runtime_error_degrees=None,
                  moving_sample_velocity_threshold_rad_s=.01, substantial_motion_span_threshold_deg=1.,
                  scenarios_degrees=SCENARIOS, traces=reports,
                  sources_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                      (Path(__file__).resolve(), ROOT/'scripts/teleoperation/general_home/trace_analysis.py')},
                  limitations=[
                      'cmd_pos is requested WITHOUT LIMIT; applied servo setpoint is not present',
                      'Difference uses paired fields in the same motor coordinates, no joint-sign conversion or time shifting',
                      'Sampling, firmware field update alignment, external calibration and stopping are not bounded',
                      'Velocity/span thresholds label observed excitation, not safety or dataset qualification',
                      'Percentiles are descriptive, not allowable exceedance rates or future worst-case bounds',
                      'A stationary joint does not provide dynamic evidence for ENTRY or a loaded box'])
    with args.output.open('x') as stream:
        stream.write(json.dumps(result, indent=2, allow_nan=False)+'\n')
    for row in reports:
        print(Path(row['path']).parent, 'usable', row['eligible_for_observed_comparison'],
              'max_deg', (row.get('all_samples') or {}).get('maximum_deg'))


if __name__ == '__main__':
    main()
