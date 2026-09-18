#!/usr/bin/env python3
"""Offline clearance sweep of body-first v5 opening widths; never contacts the robot.

Compares clamp clearance to non-own-arm links (torso, lifter, head, other arm,
other clamp) for the v5 sequence with several shoulder openings, plus the vendor
direct HOME as calibration (it produced real clamp-to-body approach).
Archived geometry only: no tracking, braking, load or external obstacles.
"""
import argparse
import json
from pathlib import Path

import audit_pico_home_open_path as audit_model
from cruzr_pico_to_home_owner_gate import PICO_VARIANTS

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT.parent/'Humanoide-vla-evidence/20260908T115359.543954Z_PICO-HOME-CHECK'
L_ELBOW, R_ELBOW, L_ROLL, R_ROLL = 0, 7, 3, 10
V5_DURATIONS = (3.75, 1.8, 10.0, 2.7)
OPENINGS = {'v4_full': (-0.4, -0.6), 'two_thirds': (-0.27, -0.4), 'v5_half': (-0.2, -0.3)}
# Measured 2026-09-18 15:27 CST before the failed boot HOME (JOINT_ORDER).
SEPARATE_RIGHT = [-0.47285, -0.14985, 0.95404, -0.12568, -1.68498, -0.28858, 0.29021,
                  0.02800, -0.49548, -1.25911, 0.05599, 2.36521, 0.57198, 0.77246] + [0.0]*6
STARTS = dict(PICO_VARIANTS, arms_down_body_zero=[0.0]*20,
              arms_down_body_flexed=[0.0]*14 + PICO_VARIANTS['pico_body_flexed'][14:],
              separate_right_20260918=SEPARATE_RIGHT)


def v5_path(open_delta, lowered_roll):
    def path(start):
        # v5 18 s: elbows move together with head/lifter/waist.
        elbows = list(start[:14]) + [0.0]*6
        elbows[L_ELBOW] -= 0.03
        elbows[R_ELBOW] -= 0.03
        opened = list(elbows)
        opened[L_ROLL] += open_delta
        opened[R_ROLL] += open_delta
        lowered = [0.0]*20
        lowered[L_ROLL] = lowered[R_ROLL] = lowered_roll
        return [list(start), elbows, opened, lowered, [0.0]*20]
    return path


def v7_path(order):
    """First stage runs body and arms concurrently; bracket every timing overlap."""
    def path(start):
        body = list(start[:14]) + [0.0]*6
        arms = list(start)
        for i, d in ((L_ELBOW, -0.03), (R_ELBOW, -0.03), (L_ROLL, -0.2), (R_ROLL, -0.2)):
            arms[i] += d
        both = arms[:14] + [0.0]*6
        middle = {'body_then_arms': [body], 'arms_then_body': [arms], 'diagonal': []}[order]
        lowered = [0.0]*20
        lowered[L_ROLL] = lowered[R_ROLL] = -0.3
        return [list(start)] + middle + [both, lowered, [0.0]*20]
    return path


def cross_minimum(record):
    pairs = {k: v for k, v in record['minimum_by_pair'].items()
             if not k.startswith(k[0]+':'+k[0]+'_')}
    key = min(pairs, key=lambda k: pairs[k]['gap_m'])
    return {'segment': record['segment'], 'pair': key,
            'sample_min_mm': round(1000*pairs[key]['gap_m'], 1),
            'conditional_bound_mm': round(1000*(pairs[key]['gap_m']-record['sampling_pair_travel_bound_m']), 1)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--samples', type=int, default=501)
    parser.add_argument('--v7', action='store_true', help='Only the v7 first-stage overlap brackets')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output already exists')
    result = {'movement_commands': 0, 'physical_approval': False, 'samples': args.samples, 'runs': {}}
    runs = {name: (v5_path(*opening), V5_DURATIONS) for name, opening in OPENINGS.items()}
    runs['vendor_direct_calibration'] = (lambda s: [list(s), [0.0]*20], (6.0,))
    if args.v7:
        runs = {'v7_'+o: (v7_path(o), (1.9, 1.85, 7.0, 2.7) if o != 'diagonal' else (3.75, 7.0, 2.7))
                for o in ('body_then_arms', 'arms_then_body', 'diagonal')}
    for name, (path, durations) in runs.items():
        report = audit_model.audit(SNAPSHOT, args.samples, path=path, durations=durations,
                                   revision=name, variants=STARTS)
        result['runs'][name] = {v: [cross_minimum(r) for r in records]
                                for v, records in report['variants'].items()}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=1)


if __name__ == '__main__':
    main()
