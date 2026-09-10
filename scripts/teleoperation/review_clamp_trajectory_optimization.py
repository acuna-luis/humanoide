#!/usr/bin/env python3
"""Offline comparison of clamp HOME timings and geometry; never emits robot commands.

Candidates are numerical reports, not installable tasks. Quintic time laws are
assumptions, not a claim about Motion. Preserve archived tool bounds and errors.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'vla'))
import analyze_vla_fixture_collision_e4_1c as fk
import cruzr_internal_home_open_path as internal
import cruzr_pico_home_open_path as pico
from cruzr_pico_to_home_owner_gate import JOINT_ORDER, PICO_VARIANTS

ORDER_INDEX = {name: i for i, name in enumerate(JOINT_ORDER)}
VMAX = 1.875
AMAX = 10*math.sqrt(3)/3
JMAX = 60.0


@dataclass
class Stage:
    name: str
    start: np.ndarray
    end: np.ndarray
    durations: np.ndarray

    def __post_init__(self):
        self.start, self.end, self.durations = [np.asarray(x, dtype=float) for x in
                                               (self.start, self.end, self.durations)]
        if any(x.shape != (20,) or not np.isfinite(x).all() for x in
               (self.start, self.end, self.durations)):
            raise ValueError('Expected finite 20D stage arrays')
        if (self.durations <= 0).any():
            raise ValueError('Nonpositive duration')

    @property
    def duration(self):
        return float(self.durations.max())

    def samples(self, count):
        # Include the finish of every individual component, even if not on grid.
        times = np.unique(np.r_[np.linspace(0, self.duration, count), self.durations])
        s = np.clip(times[:, None]/self.durations, 0, 1)
        h = s**3*(10+s*(-15+6*s))
        return times, self.start+(self.end-self.start)*h

    def peaks(self):
        d = abs(self.end-self.start)
        return dict(velocity=VMAX*d/self.durations,
                    acceleration=AMAX*d/self.durations**2,
                    jerk=JMAX*d/self.durations**3)


def make_stages(points, durations):
    return [Stage(name, a, b, np.full(20, duration))
            for name, a, b, duration in zip(pico.STAGE_NAMES, points[:-1], points[1:], durations, strict=True)]


def remove_exact_holds(stages):
    # Do not interpret the endpoint gate's 0.02 rad tolerance as exact equality.
    return [s for s in stages if not np.array_equal(s.start, s.end)]


def peak_caps(stages):
    return {key: np.max([s.peaks()[key] for s in stages], axis=0)
            for key in ('velocity', 'acceleration', 'jerk')}


def retime_to_same_joint_peaks(points, reference):
    """Comparison only: keep each joint's analytical v/a/jerk below reference maxima."""
    caps = peak_caps(reference)
    durations = []
    for a, b in zip(points, points[1:]):
        delta = abs(np.asarray(b)-a)
        moving = delta > 0
        if any((caps[key][moving] <= 0).any() for key in caps):
            raise ValueError('Candidate moves a joint that had no reference dynamic budget')
        values = [0.001]
        for key, factor, power in [('velocity', VMAX, 1), ('acceleration', AMAX, 2), ('jerk', JMAX, 3)]:
            if moving.any():
                values.append(float(np.max((factor*delta[moving]/caps[key][moving])**(1/power))))
        durations.append(math.ceil(max(values)*1000)/1000)
    return remove_exact_holds(make_stages(points, durations))


def batch_fk(joints, q):
    """Same URDF FK as the existing scalar implementation, batched by sample."""
    n = len(q)
    poses = {'base_link': np.broadcast_to(np.eye(4), (n, 4, 4)).copy()}
    pending = list(joints)
    while pending:
        progress = False
        for joint in pending[:]:
            if joint['parent'] not in poses:
                continue
            motion = np.broadcast_to(np.eye(4), (n, 4, 4)).copy()
            values = q[:, ORDER_INDEX[joint['name']]] if joint['name'] in ORDER_INDEX else np.zeros(n)
            if joint['type'] in ('revolute', 'continuous'):
                axis = joint['axis']/np.linalg.norm(joint['axis'])
                x, y, z = axis
                skew = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
                c, s = np.cos(values)[:, None, None], np.sin(values)[:, None, None]
                motion[:, :3, :3] = c*np.eye(3)+(1-c)*np.outer(axis, axis)+s*skew
            elif joint['type'] == 'prismatic':
                motion[:, :3, 3] = values[:, None]*joint['axis']
            poses[joint['child']] = poses[joint['parent']] @ joint['origin'] @ motion
            pending.remove(joint)
            progress = True
        if not progress:
            raise ValueError('Disconnected model')
    return poses


def model_joints(urdf):
    root = ET.parse(urdf).getroot()
    return [dict(name=j.get('name'), type=j.get('type'), parent=j.find('parent').get('link'),
                 child=j.find('child').get('link'), origin=fk.origin_transform(j.find('origin')),
                 axis=fk.xyz(j.find('axis').get('xyz') if j.find('axis') is not None else None, (1, 0, 0)))
            for j in root.findall('joint')]


def batch_obb(poses, bounds):
    lo, hi = np.asarray(bounds)
    rotation = poses[:, :3, :3]
    center = np.einsum('nij,j->ni', rotation, (lo+hi)/2)+poses[:, :3, 3]
    return center, rotation, (hi-lo)/2


def batch_gap(a, b):
    ca, ra, ea = a
    cb, rb, eb = b
    aa, ab = ra.transpose(0, 2, 1), rb.transpose(0, 2, 1)
    crosses = np.cross(aa[:, :, None, :], ab[:, None, :, :]).reshape(-1, 9, 3)
    axes = np.concatenate((aa, ab, crosses), axis=1)
    norms = np.linalg.norm(axes, axis=2)
    axes = axes/np.maximum(norms[:, :, None], 1e-30)
    pa = (np.abs(np.einsum('nki,nij->nkj', axes, ra))*ea).sum(axis=2)
    pb = (np.abs(np.einsum('nki,nij->nkj', axes, rb))*eb).sum(axis=2)
    gaps = abs(np.einsum('nki,ni->nk', axes, cb-ca))-pa-pb
    gaps[norms < 1e-10] = -np.inf
    return gaps.max(axis=1)


def pair_radii(joints, link_a, bounds_a, link_b, bounds_b):
    """Whole-configuration radius bound per independent joint of a link pair.

    Common upstream joints cancel: rigidly rotating both shapes preserves distance.
    Remaining radius <= sum of downstream origin lengths + local corner radius.
    """
    by_child = {j['child']: j for j in joints}
    def chain(link):
        result = []
        while link in by_child:
            joint = by_child[link]
            result.append(joint)
            link = joint['parent']
        return result[::-1]
    a, b = chain(link_a), chain(link_b)
    common = {j['name'] for j in a}&{j['name'] for j in b}
    weights = np.zeros(20)
    for seq, bounds in [(a, bounds_a), (b, bounds_b)]:
        corner_radius = float(np.linalg.norm(fk.corners(*bounds), axis=1).max())
        for index, joint in enumerate(seq):
            if joint['name'] in common or joint['name'] not in ORDER_INDEX:
                continue
            if joint['type'] not in ('revolute', 'continuous'):
                raise ValueError('Angular radius bound cannot cover a prismatic control joint')
            weights[ORDER_INDEX[joint['name']]] += corner_radius+sum(
                np.linalg.norm(j['origin'][:3, 3]) for j in seq[index+1:])
    return weights


def candidates(start, family):
    path = pico.waypoints if family == 'pico' else internal.waypoints
    points = path(start)
    reference = make_stages(points, pico.stage_durations(4))
    result = {'baseline_20s': reference, 'omit_exact_holds': remove_exact_holds(reference)}
    # Parallel body reset starts only after arms are fully opened, with each
    # component keeping its original duration. Not a load/torque qualification.
    merged = Stage('lower_arms_and_body_parallel', points[1], points[3],
                   np.r_[np.full(14, 10.0), np.full(6, 3.75)])
    result['parallel_body_candidate'] = [reference[0], merged, reference[3]]
    if family == 'pico':
        for roll in (-0.5, -0.45):
            altered = [list(q) for q in points]
            for q in altered[1:4]:
                q[3] = q[10] = roll
            result[f'roll_{abs(roll):.2f}_same_joint_peaks'] = retime_to_same_joint_peaks(altered, reference)
    return result


def assess(stages, joints, boxes, geometry, samples):
    tool = {s: np.asarray(b) for s, b in geometry['tool_bounds_in_sensor_m'].items()}
    pairs = [(s+':'+name, s+'_sixforce_link', tool[s], name, boxes[name])
             for s in ('L', 'R') for name in geometry['tested_robot_links']]
    pairs.append(('L:R_clamp', 'L_sixforce_link', tool['L'], 'R_sixforce_link', tool['R']))
    local = {s+':'+s+'_'+part+'_link' for s in ('L', 'R')
             for part in ('sixforce', 'wrist_roll', 'wrist_pitch')}
    weights = {key: pair_radii(joints, la, ba, lb, bb) for key, la, ba, lb, bb in pairs}
    records = []
    global_minima = {}
    for stage in stages:
        times, q = stage.samples(samples)
        poses = batch_fk(joints, q)
        minima = {}
        for key, la, ba, lb, bb in pairs:
            gaps = batch_gap(batch_obb(poses[la], ba), batch_obb(poses[lb], bb))
            w = weights[key]
            # Every joint is monotonic during this stage. Any intermediate
            # point is within half weighted travel of at least one endpoint.
            half_travel = abs(np.diff(q, axis=0)) @ w/2
            bound = float(np.min(np.minimum(gaps[:-1], gaps[1:])-half_travel))
            uncertainty = float(2*math.sin(math.radians(5)/2)*w.sum())
            index = int(gaps.argmin())
            minima[key] = dict(sample_gap_m=float(gaps[index]), continuous_nominal_bound_m=bound,
                               time_s=float(times[index]), joint_5deg_displacement_bound_m=uncertainty,
                               bound_after_joint_5deg_m=bound-uncertainty,
                               attachment_pair=key in local)
            if bound < global_minima.get(key, {}).get('continuous_nominal_bound_m', math.inf):
                global_minima[key] = dict(minima[key], stage=stage.name)
        peaks = stage.peaks()
        records.append(dict(name=stage.name, duration_s=stage.duration,
                            samples=len(q), start=stage.start.tolist(), end=stage.end.tolist(),
                            per_joint_durations_s=stage.durations.tolist(),
                            peak_velocity_rad_s=float(peaks['velocity'].max()),
                            peak_acceleration_rad_s2=float(peaks['acceleration'].max()),
                            peak_jerk_rad_s3=float(peaks['jerk'].max()),
                            minimum_by_pair=minima))
    body = {k: v for k, v in global_minima.items() if k not in local}
    worst = min(body, key=lambda k: body[k]['continuous_nominal_bound_m'])
    uncertain = min(body, key=lambda k: body[k]['bound_after_joint_5deg_m'])
    caps = peak_caps(stages)
    return dict(total_s=sum(s.duration for s in stages), stages=records,
                peaks_by_joint={k: dict(zip(JOINT_ORDER, v.tolist())) for k, v in caps.items()},
                minimum_by_pair=global_minima,
                worst_nonattachment_pair=worst, worst_nonattachment=body[worst],
                worst_joint_error_pair=uncertain, worst_joint_error=body[uncertain],
                unresolved_nominal_nonattachment=[k for k, v in body.items() if v['continuous_nominal_bound_m'] <= 0],
                unresolved_joint_error_nonattachment=[k for k, v in body.items() if v['bound_after_joint_5deg_m'] <= 0])


def compare_models(runtime_joints, supplied_urdf, states):
    supplied_joints = model_joints(supplied_urdf)
    old, new = batch_fk(runtime_joints, states), batch_fk(supplied_joints, states)
    errors = {}
    for name in ('L_hand_link', 'R_hand_link', 'L_sixforce_link', 'R_sixforce_link',
                 'torso_link', 'head_pitch_link'):
        difference = old[name][:, :3, :3].transpose(0, 2, 1) @ new[name][:, :3, :3]
        angles = np.arccos(np.clip((np.trace(difference, axis1=1, axis2=2)-1)/2, -1, 1))
        errors[name] = dict(max_translation_m=float(np.linalg.norm(old[name][:, :3, 3]-new[name][:, :3, 3], axis=1).max()),
                            max_orientation_deg=float(np.degrees(angles).max()))
    return dict(samples=len(states), errors=errors, scope='sampled FK agreement, not arbitrary joint-space proof')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot-dir', type=Path, required=True)
    parser.add_argument('--splint-urdf', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--samples', type=int, default=501)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output already exists')
    if not 101 <= args.samples <= 2001:
        parser.error('samples must be 101..2001')
    snapshot = args.snapshot_dir
    joints, boxes, meshes = fk.load_robot(snapshot/'runtime.urdf', snapshot/'runtime-meshes.zip')
    geometry = json.loads((snapshot/'geometry-check-1001.json').read_text())
    budget = json.loads((snapshot/'error-budget-ubtech-reported.json').read_text())
    if geometry.get('error_allowance_m') != .002 or budget.get('joint_error_deg_interpreted') != 5:
        raise ValueError('Review required: archived error budget differs')
    report = dict(schema='clamp-trajectory-optimization-offline-v1', deployable=False,
                  movement_commands=0, physical_approval=False, joint_order=JOINT_ORDER,
                  curve_assumption='quintic, monotonic per joint, component durations as reported',
                  geometry_error_m=.002, angular_error_scenario_deg=5,
                  stopping_distance_bound=None, results={},
                  limitations=[
                      'Tool bounds retain 2 mm geometric inflation and 0..40 mm origin interval; no shrinking or mesh-based exemptions.',
                      '5 degree per independent joint is a conservative scenario relayed by operator, not a measured tracking specification.',
                      'Do not add another 2 mm tracking budget without disambiguating its scope.',
                      'All attachment pairs are reported; nonattachment summaries are not an all-pairs pass.',
                      'Clamps vs robot and vs each other only: no full robot self-collision, floor, scene, cargo, stability, torque or braking qualification.',
                      'Parallel components preserve single-joint peaks but change combined loads and relative timing.',
                      'Exact-hold removal requires exact target equality; existing endpoint tolerance does not establish this.',
                      'No new XML, installation option or controller setting is produced.'])
    state_samples = []
    for family, starts in [('pico', PICO_VARIANTS), ('internal', internal.REVIEW_STARTS)]:
        for variant, start in starts.items():
            key = family+':'+variant
            report['results'][key] = {}
            for label, stages in candidates(start, family).items():
                result = assess(stages, joints, boxes, geometry, args.samples)
                report['results'][key][label] = result
                print(key, label, round(result['total_s'], 3),
                      result['worst_nonattachment_pair'],
                      round(1000*result['worst_nonattachment']['continuous_nominal_bound_m'], 3), flush=True)
                if label == 'baseline_20s':
                    state_samples.extend(stage.samples(31)[1] for stage in stages)
    report['model_comparison'] = compare_models(joints, args.splint_urdf, np.concatenate(state_samples))
    limits = {j.get('name'):j.find('limit') for j in ET.parse(snapshot/'runtime.urdf').getroot().findall('joint')}
    report['urdf_velocity_limits_rad_s'] = {n: float(limits[n].get('velocity')) for n in JOINT_ORDER}
    report['nonpositive_urdf_velocity_limits'] = [n for n, v in report['urdf_velocity_limits_rad_s'].items() if v <= 0]
    for variants in report['results'].values():
        reference = variants['baseline_20s']
        for candidate in variants.values():
            candidate['time_saving_percent'] = 100*(1-candidate['total_s']/reference['total_s'])
            candidate['nominal_position_limits_pass'] = all(
                float(limits[n].get('lower')) <= q <= float(limits[n].get('upper'))
                for stage in candidate['stages'] for point in ('start', 'end')
                for n, q in zip(JOINT_ORDER, stage[point]))
            candidate['analytical_joint_peaks_not_increased'] = all(
                candidate['peaks_by_joint'][kind][n] <= reference['peaks_by_joint'][kind][n]+1e-12
                for kind in ('velocity', 'acceleration', 'jerk') for n in JOINT_ORDER)
    report['uniform_speedup_comparison'] = {
        str(t):dict(velocity_ratio=20/t, acceleration_ratio=(20/t)**2, jerk_ratio=(20/t)**3)
        for t in (20, 16, 15, 12, 6)}
    sources = [Path(__file__), Path(pico.__file__), Path(internal.__file__),
               Path(__file__).with_name('cruzr_pico_to_home_owner_gate.py'), Path(fk.__file__),
               snapshot/'runtime.urdf', snapshot/'runtime-meshes.zip',
               snapshot/'geometry-check-1001.json', snapshot/'error-budget-ubtech-reported.json', args.splint_urdf]
    report['source_sha256'] = {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)


if __name__ == '__main__':
    main()
