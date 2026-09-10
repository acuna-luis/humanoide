#!/usr/bin/env python3
"""Adaptive empty-clamp HOME planner and offline audit; no robot commands.

This module implements posture-dependent opening and timing. Its report is
not an execution permit: tracking and stopping must also be bounded before
replacing a physical task, especially the automatic boot HOME.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

from cruzr_pico_to_home_owner_gate import JOINT_ORDER, PICO_REFERENCE, load_sample
import review_clamp_trajectory_optimization as review

ROLLS = (3, 10)
ARM_SHAPE_INDICES = tuple(i for i in range(14) if i not in ROLLS)
MIN_OPEN_RAD = -.5
MAX_OPEN_RAD = -.65
SHAPE_TOL_RAD = .02
STATIONARY_RAD_S = .002
# Numerical comparison caps, not manufacturer ratings. Below the largest
# quintic peaks of the existing 20 s PICO profile (0.301 / 0.370 / 1.540).
CAPS = dict(velocity=.3, acceleration=.35, jerk=1.5)


@dataclass
class Step:
    name: str
    start: list[float]
    end: list[float]
    seconds: float

    def stage(self):
        return review.Stage(self.name, self.start, self.end, np.full(20, self.seconds))


def vector(values, name):
    if not isinstance(values, (list, tuple)) or len(values) != 20:
        raise ValueError(name + ': expected twenty values')
    if any(type(x) not in (int, float) or not math.isfinite(x) for x in values):
        raise ValueError(name + ': expected finite numeric values')
    return list(map(float, values))


def classify(q):
    # Preserve asymmetric roll values; do not accept an asymmetric elbow/wrist
    # posture left by an interrupted grasp as a PICO reference.
    if any(not MAX_OPEN_RAD <= q[i] <= .02 for i in ROLLS):
        raise ValueError('shoulder roll outside reviewed planning domain')
    if max(abs(q[i]) for i in ARM_SHAPE_INDICES) <= SHAPE_TOL_RAD:
        arms = 'down'
    elif max(abs(q[i]-PICO_REFERENCE[i]) for i in ARM_SHAPE_INDICES) <= SHAPE_TOL_RAD:
        arms = 'pico'
    else:
        raise ValueError('unknown arm posture: do not use a generic HOME')
    if max(abs(x) for x in q[14:]) <= .005:
        body = 'near_zero'
    elif max(abs(a-b) for a,b in zip(q[14:], PICO_REFERENCE[14:])) <= SHAPE_TOL_RAD:
        body = 'pico_flexed'
    else:
        raise ValueError('unknown body posture')
    return arms, body


def duration(start, end, minimum):
    d = max(abs(a-b) for a,b in zip(start,end))
    t = max(minimum, review.VMAX*d/CAPS['velocity'],
            math.sqrt(review.AMAX*d/CAPS['acceleration']),
            (review.JMAX*d/CAPS['jerk'])**(1/3))
    return math.ceil(t*1000)/1000


def plan(positions, velocities):
    q = vector(positions, 'positions')
    dq = vector(velocities, 'velocities')
    if max(abs(x) for x in dq) > STATIONARY_RAD_S:
        raise ValueError('robot is not stationary')
    arms, body = classify(q)
    steps = []

    def add(name, target, minimum=1.):
        nonlocal q
        # Only exact equality skips a step. Near HOME still receives a small,
        # explicitly timed correction, not an invented claim of exact zero.
        if target == q:
            return
        steps.append(Step(name, q.copy(), target.copy(), duration(q,target,minimum)))
        q = target.copy()

    initial = q.copy()
    # Already-down arms and a body near zero need no wide opening to lower
    # arms. Keep the body fixed while correcting tiny non-roll arm errors.
    # Do not use this branch for a flexed body: open first, then move body.
    direct_down = arms == 'down' and body == 'near_zero'
    if direct_down:
        if any(q[i] != 0 for i in ARM_SHAPE_INDICES):
            target = q.copy()
            for i in ARM_SHAPE_INDICES: target[i] = 0.
            add('align_already_lowered_arms', target)
    else:
        opened = q.copy()
        for i in ROLLS:
            opened[i] = min(q[i], MIN_OPEN_RAD)
        add('open_only_missing_clearance', opened)
        lowered = q.copy()
        for i in ARM_SHAPE_INDICES: lowered[i] = 0.
        add('lower_with_opening_preserved', lowered, 10.)
    body_home = q[:14] + [0.]*6
    add('body_home_with_arm_posture_preserved', body_home)
    add('close_only_lowered_arms', [0.]*20)
    return dict(schema='cruzr-adaptive-home-plan-v1',
                arm_posture=arms, body_posture=body, initial_position_rad=initial,
                opening_floor_rad=MIN_OPEN_RAD, steps=[asdict(s) for s in steps],
                nominal_seconds=sum(s.seconds for s in steps),
                analytical_peak_caps=CAPS, interpolation_assumption='common quintic per step',
                state_match_is_not_physical_validation=True,
                physical_approval=False, installable=False, movement_commands=0)


def audit(candidate, snapshot, samples=501):
    if not 2 <= samples <= 2001:
        raise ValueError('samples must be 2..2001')
    joints, boxes, _ = review.fk.load_robot(snapshot/'runtime.urdf', snapshot/'runtime-meshes.zip')
    geometry = json.loads((snapshot/'geometry-check-1001.json').read_text())
    if geometry.get('error_allowance_m') != .002:
        raise ValueError('unexpected geometry error budget')
    stages = [Step(**s).stage() for s in candidate['steps']]
    # Even an exact HOME no-op must be audited as a posture; do not call min([]).
    if not stages:
        q = candidate['initial_position_rad']
        stages = [review.Stage('no_motion_posture',q,q,np.ones(20))]
    result = review.assess(stages,joints,boxes,geometry,samples)
    limits = {j.get('name'): j.find('limit') for j in review.ET.parse(snapshot/'runtime.urdf').getroot().findall('joint')}
    result['position_limits_pass'] = all(
        float(limits[n].get('lower')) <= value <= float(limits[n].get('upper'))
        for stage in stages for q in (stage.start,stage.end) for n,value in zip(JOINT_ORDER,q))
    result['source_sha256'] = {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
        [Path(__file__),Path(review.__file__),snapshot/'runtime.urdf',
         snapshot/'runtime-meshes.zip',snapshot/'geometry-check-1001.json']}
    result['stopping_distance_bound_m'] = None
    result['activation_blockers'] = ['actual_interpolation_and_stopping_not_bounded']
    if not result['position_limits_pass']:
        result['activation_blockers'].append('joint_position_limits')
    if result['unresolved_nominal_nonattachment']:
        result['activation_blockers'].append('nominal_geometry_not_demonstrated')
    if result['unresolved_joint_error_nonattachment']:
        result['activation_blockers'].append('5_degree_tracking_scenario_not_demonstrated')
    result['physical_approval'] = False
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True,help='Archived JointState YAML/JSON; never reads ROS')
    parser.add_argument('--snapshot-dir',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--samples',type=int,default=501)
    args = parser.parse_args()
    if args.output.exists(): parser.error('output already exists')
    sample = load_sample(args.input)
    names = sample.get('name',[])
    if len(names) != len(set(names)) or not all(n in names for n in JOINT_ORDER):
        raise ValueError('duplicate or missing joint names')
    if len(sample.get('position',[])) != len(names) or len(sample.get('velocity',[])) != len(names):
        raise ValueError('inconsistent joint arrays')
    positions = [sample['position'][names.index(n)] for n in JOINT_ORDER]
    velocities = [sample['velocity'][names.index(n)] for n in JOINT_ORDER]
    result = plan(positions,velocities)
    result['input_sha256'] = hashlib.sha256(args.input.read_bytes()).hexdigest()
    result['audit'] = audit(result,args.snapshot_dir,args.samples)
    with args.output.open('x') as out: json.dump(result,out,indent=2,allow_nan=False)
    print(json.dumps(dict(output=str(args.output),nominal_seconds=result['nominal_seconds'],
                         activation_blockers=result['audit']['activation_blockers'],
                         installed=False,movement_commands=0)))


if __name__ == '__main__':
    try:
        main()
    except (OSError,TypeError,ValueError,KeyError) as exc:
        print('ERROR: '+str(exc),file=sys.stderr)
        raise SystemExit(2)
