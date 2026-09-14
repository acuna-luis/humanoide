#!/usr/bin/env python3
"""Prepare an offline ENTRY/access review from archived data, never robot commands.

Every self/scene pair remains in the result. Interval certificates apply only
to affine joint paths and the listed geometry; they never authorize execution.
The archived scene is partial and must not be presented as a live measurement.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/teleoperation'))
from general_home.geometry import RobotGeometry, digest, finite_vector
from general_home.planner import retime
from cruzr_pico_to_home_owner_gate import JOINT_ORDER
from derive_vla_fixture_pose import quaternion_rotation
import review_clamp_trajectory_optimization as common
import rank_vla_entry_postures as ranking
from evaluate_checkpoint_offline import episode_paths, write_json_exclusive


def validate_first_record(row, episode, archived_state):
    if (row.get('episode_index'), row.get('task_index')) != (episode, 0):
        raise ValueError('Dataset identity mismatch')
    timestamp = row.get('timestamp')
    if not isinstance(timestamp, (int, float)) or not math.isfinite(timestamp) or abs(timestamp) > 1e-6:
        raise ValueError('First row must have timestamp zero')
    if row.get('frame_index', 0) != 0:
        raise ValueError('First row is not frame zero')
    state = finite_vector(row['observation.state'], 32, 'dataset state')[:20]
    if not np.array_equal(state, finite_vector(archived_state, 20, 'archived state')):
        raise ValueError('Archived state differs from original parquet')
    return state


def rim_height(pose, intrinsic, pixels, width, box_height, floor_offset):
    pixels = np.asarray(pixels, dtype=float)
    if pixels.shape != (2, 2) or not np.isfinite(pixels).all():
        raise ValueError('Two finite rim pixels required')
    if any(not math.isfinite(x) or x <= 0 for x in (width, box_height, floor_offset)):
        raise ValueError('Positive dimensions required')
    rays = (pose[:3, :3] @ np.linalg.inv(intrinsic) @
            np.column_stack((pixels, np.ones(2))).T).T
    if not (rays[:, 2] < -1e-9).all():
        raise ValueError('Rim rays must point downward')
    slopes = rays[:, :2] / rays[:, 2, None]
    separation = float(np.linalg.norm(slopes[1] - slopes[0]))
    if separation <= 1e-9:
        raise ValueError('Degenerate rim')
    return float(pose[2, 3] - width / separation - box_height + floor_offset)


def routes(start, ready, entry):
    """Heuristics only. Preserve exact start and dataset endpoint in each route."""
    start, ready, entry = (finite_vector(x, 20, 'route endpoint') for x in (start, ready, entry))
    opened = start.copy()
    opened[[3, 10]] = np.minimum(opened[[3, 10]], ready[[3, 10]])
    lowered_body = opened.copy()
    lowered_body[14:] = entry[14:]
    return {
        'via_ready': [start, ready, entry],
        'body_first_with_open_arms': [start, opened, lowered_body, entry],
        'direct': [start, entry],
    }


def empty_recovery_waypoints(path):
    """Return to the exact archived start, then complete all 20 HOME axes.

    This is not a recovery after a grasp or an interrupted/divergent movement.
    In particular, observation-head pitch must not be labelled complete HOME.
    """
    result = [finite_vector(q, 20, 'recovery point').copy() for q in reversed(path)]
    if not result:
        raise ValueError('Empty access path')
    if np.any(result[-1] != 0):
        result.append(np.zeros(20))
    return result


def certify_pairs(geometry, path, *, seconds=60., max_depth=16, joint_error_rad=0.):
    """Classify EVERY pair across EVERY affine segment with Lipschitz bounds.

    An observed nominal violation is reported as such. A positive distance that
    fails the uncertainty bound is UNRESOLVED, never asserted to be a collision.
    Pairs can leave subdivision only with a witness or complete interval proof;
    unresolved leaves stay unresolved even if all sampled points were clear.
    """
    if not math.isfinite(seconds) or seconds <= 0 or not 1 <= max_depth <= 20:
        raise ValueError('Invalid analysis budget')
    if not math.isfinite(joint_error_rad) or joint_error_rad < 0:
        raise ValueError('Invalid angular uncertainty')
    if len(path) < 2:
        raise ValueError('At least two route points required')
    path = [finite_vector(q, len(geometry.lower), 'route state') for q in path]
    if any((q < geometry.lower).any() or (q > geometry.upper).any() for q in path):
        raise ValueError('Route outside model joint limits')
    count = len(geometry.labels)
    if geometry.weights.shape != (count, len(geometry.lower)) or (geometry.weights < 0).any():
        raise ValueError('Invalid pair motion bounds')
    base_margin = 0.002
    error_widths = np.full(len(geometry.lower), joint_error_rad)
    local_bounds = hasattr(geometry, 'displacement_bounds')
    def displacement(q, widths):
        value = np.asarray(geometry.displacement_bounds(q, widths) if local_bounds
                           else geometry.weights @ widths)
        if value.shape != (count,) or not np.isfinite(value).all() or (value < 0).any():
            raise ValueError('Invalid displacement enclosure')
        return value
    def unresolved_by_box(q,widths,indices):
        if not len(indices) or not hasattr(geometry,'interval_separations'):
            return indices
        value=np.asarray(geometry.interval_separations(q,widths,indices))
        if value.shape!=(len(indices),) or not np.isfinite(value).all() or (value<0).any():
            raise ValueError('Invalid interval separation enclosure')
        return indices[value<=base_margin+1e-9]
    maximum_evaluated_margin = np.full(count, base_margin)
    margin_cache = {}
    witnessed = np.zeros(count, dtype=bool)
    unresolved = np.zeros(count, dtype=bool)
    minimum = np.full(count, np.inf)
    witnesses = {}
    uncertainty_witnesses = {}
    cache = {}
    deadline = time.monotonic() + seconds
    timed_out = False
    def distances(q, indices):
        key = q.tobytes()
        if key not in cache:
            cache[key] = np.full(count, np.nan)
        missing = indices[~np.isfinite(cache[key][indices])]
        if len(missing):
            value = np.asarray(geometry.selected_distances(q, missing) if hasattr(geometry,'selected_distances')
                               else np.asarray(geometry.distances(q))[missing])
            if value.shape != (len(missing),) or not np.isfinite(value).all():
                raise ValueError('Invalid distance result')
            cache[key][missing] = value
        return cache[key]
    def observe(q, segment, fraction, indices):
        d = distances(q, indices)
        key = q.tobytes()
        if key not in margin_cache:
            margin_cache[key] = base_margin + displacement(q, error_widths)
        np.maximum(maximum_evaluated_margin, margin_cache[key], out=maximum_evaluated_margin)
        minimum[indices] = np.minimum(minimum[indices], d[indices])
        bad = np.zeros(count,dtype=bool)
        bad[indices] = d[indices] <= base_margin + 1e-9
        for i in np.flatnonzero(bad & ~witnessed):
            witnesses[str(i)] = dict(segment=segment, fraction=fraction,
                                    separation_lower_bound_m=float(d[i]))
        witnessed[:] |= bad
        return d
    for stage, (a, b) in enumerate(zip(path, path[1:])):
        if time.monotonic() >= deadline:
            timed_out = True
            unresolved |= ~witnessed
            break
        observe(a, stage, 0., np.flatnonzero(~(witnessed | unresolved)))
        observe(b, stage, 1., np.flatnonzero(~(witnessed | unresolved)))
        pending = [(0., 1., 0, np.flatnonzero(~(witnessed | unresolved)))]
        while pending:
            if time.monotonic() >= deadline:
                timed_out = True
                unresolved |= ~witnessed
                break
            lo, hi, depth, indices = pending.pop()
            # Once ANY interval for a pair is unresolved, that pair cannot
            # receive a whole-route certificate. Keep its failure and avoid
            # spending the budget on its sibling intervals. This never drops
            # the pair from the result or turns uncertainty into a pass.
            indices = indices[~(witnessed | unresolved)[indices]]
            if not len(indices):
                continue
            fraction = (lo + hi) / 2
            center = a + (b - a) * fraction
            d = observe(center, stage, fraction, indices)
            margin = margin_cache[center.tobytes()]
            indices = indices[~witnessed[indices]]
            interval_margin = base_margin + displacement(center,
                error_widths + abs(b-a)*(hi-lo)/2)
            uncertain = indices[d[indices] <= interval_margin[indices] + 1e-9]
            uncertain = unresolved_by_box(center,error_widths+abs(b-a)*(hi-lo)/2,uncertain)
            if not len(uncertain):
                continue
            if depth >= max_depth:
                unresolved[uncertain] = True
                for i in uncertain:
                    uncertainty_witnesses.setdefault(str(i), dict(
                        reason='SUBDIVISION_RESOLUTION_EXHAUSTED', segment=stage,
                        fraction=fraction, depth=depth,
                        lower_bound_m=float(d[i]), required_margin_m=float(margin[i])))
                continue
            # If even the midpoint's error ball is not separated, refinement
            # of the time interval cannot prove that ball. Record uncertainty.
            error_unresolved = uncertain[d[uncertain] <= margin[uncertain] + 1e-9]
            error_unresolved = unresolved_by_box(center,error_widths,error_unresolved)
            unresolved[error_unresolved] = True
            for i in error_unresolved:
                uncertainty_witnesses.setdefault(str(i), dict(
                    reason='UNCERTAINTY_MARGIN_NOT_PROVED', segment=stage,
                    fraction=fraction, depth=depth,
                    lower_bound_m=float(d[i]), required_margin_m=float(margin[i])))
            split = uncertain[~np.isin(uncertain, error_unresolved)]
            if len(split):
                pending.extend(((lo, fraction, depth + 1, split),
                                (fraction, hi, depth + 1, split)))
        if timed_out:
            break
    statuses = ['MODEL_MARGIN_VIOLATION' if witnessed[i] else
                'UNRESOLVED' if unresolved[i] else 'CERTIFIED_AFFINE_INTERVALS'
                for i in range(count)]
    return dict(
        physical_approval=False, scope='LISTED_MODEL_AFFINE_GEOMETRY_ONLY',
        timed_out=timed_out, distance_queries=len(cache),
        max_subdivision_depth=max_depth, budget_seconds=seconds,
        joint_error_scenario_rad=joint_error_rad, base_margin_m=base_margin,
        displacement_bound_method='LOCAL_FINITE_ROTATION_TELESCOPING' if local_bounds else 'GLOBAL_RADII',
        scene_interval_boxes_used=hasattr(geometry,'interval_separations'),
        reported_margin_scope='MAXIMUM_AT_EVALUATED_STATES_NOT_GLOBAL' if local_bounds else 'GLOBAL_CONSTANT',
        all_pairs_certified=all(s == 'CERTIFIED_AFFINE_INTERVALS' for s in statuses),
        counts={s: statuses.count(s) for s in sorted(set(statuses))},
        pairs=[dict(pair=label, status=statuses[i],
                    minimum_observed_lower_bound_m=None if not math.isfinite(minimum[i]) else float(minimum[i]),
                    required_margin_with_scenario_m=float(maximum_evaluated_margin[i]),
                    witness=witnesses.get(str(i)),
                    uncertainty_witness=uncertainty_witnesses.get(str(i)), exempted=False)
               for i, label in enumerate(geometry.labels)])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('dataset-report', 'dataset', 'registration', 'camera-info', 'obstacles', 'annotations', 'output-dir'):
        parser.add_argument('--' + flag, required=True, type=Path)
    parser.add_argument('--route-budget-seconds', type=float, default=60.)
    parser.add_argument('--home-tail-only', action='store_true',
                        help='Review only the final archived-start to HOME segment; no access-path approval')
    args = parser.parse_args()
    contract_path = ROOT / 'scripts/vla/runtime/cruzr_s2_vla_task0_entry_e6_1a.json'
    contract = json.loads(contract_path.read_text())
    if digest(args.dataset_report) != contract['candidate']['dataset_entry_report_sha256']:
        parser.error('Dataset archive hash changed')
    records = ranking.validate_records(json.loads(args.dataset_report.read_text()), contract)
    registration = json.loads(args.registration.read_text())
    annotations = json.loads(args.annotations.read_text())
    intrinsic = np.asarray(json.loads(args.camera_info.read_text())['k']).reshape(3, 3)
    package = ROOT / 'cruzr_s2_description_splint/cruzr_s2_description'
    urdf = package / 'urdf/cruzr_s2_v1/cruzr_s2_v1.urdf'
    joints = ranking.load_joints(urdf)
    names = registration['joints']['name']
    if len(names) != len(set(names)) or not set(JOINT_ORDER) <= set(names):
        parser.error('Invalid archived JointState')
    measured = dict(zip(names, registration['joints']['position'], strict=True))
    start = finite_vector([measured[n] for n in JOINT_ORDER], 20, 'archived start')
    tf = registration['camera_to_base']
    camera = np.eye(4)
    camera[:3, :3] = quaternion_rotation(tf['quaternion_xyzw'])
    camera[:3, 3] = tf['translation']
    mount = np.linalg.inv(common.fk.forward_kinematics(joints, measured)['head_pitch_link']) @ camera
    args.output_dir.mkdir(parents=True, exist_ok=False)
    sources = {str(p.resolve()): digest(p) for p in (
        args.dataset_report, args.registration, args.camera_info, args.obstacles,
        args.annotations, contract_path, urdf, Path(__file__))}
    candidates = []
    import av
    import pyarrow.parquet as pq
    for name, pixels in annotations['rim_pixels_uv'].items():
        record = next(r for r in records if r['episode'] == name)
        if record['task'] != 0:
            raise ValueError('Only task 0 entries supported')
        number = int(name.removeprefix('episode_'))
        parquet, video = episode_paths(args.dataset, number)
        table = pq.read_table(parquet)
        if not table.num_rows:
            raise ValueError('Empty parquet')
        validate_first_record(table.slice(0, 1).to_pylist()[0], number, record['state'])
        sources.update({str(p.resolve()): digest(p) for p in (parquet, video)})
        with av.open(str(video)) as container:
            frame = next(container.decode(video=0))
            if frame.time is None or abs(float(frame.time)) > 1e-6:
                raise ValueError('Video does not start at timestamp zero')
            frame.to_image().save(args.output_dir / f'{name}.png')
        tilt, poses = ranking.torso_metrics(joints, dict(zip(JOINT_ORDER, record['state'])))
        pose = poses['head_pitch_link'] @ mount
        def height(points):
            return rim_height(pose, intrinsic, points, annotations['assumed_box_width_m'],
                              annotations['assumed_box_height_m'], annotations['assumed_floor_below_base_m'])
        variation = annotations['pixel_variation_px']
        if not math.isfinite(variation) or variation < 0:
            raise ValueError('Invalid pixel variation')
        heights = [height(np.asarray(pixels) + np.asarray(offset).reshape(2, 2))
                   for offset in itertools.product((-variation, variation), repeat=4)]
        candidates.append(dict(episode=name, state=record['state'],
            torso_tilt_deg=tilt, inferred_support_height_m=height(pixels),
            pixel_only_height_range_m=[min(heights), max(heights)],
            total_height_uncertainty_bounded=False, physical_approval=False))
    # RobotGeometry requires a complete *list* of modeled objects. This local
    # model contains only the listed archived cuboids, NOT the complete workshop.
    obstacles = json.loads(args.obstacles.read_text())
    objects = []
    for name, bounds in obstacles.items():
        bounds = np.asarray(bounds, dtype=float)
        if bounds.shape != (2, 3) or not np.isfinite(bounds).all() or not (bounds[1] > bounds[0]).all():
            raise ValueError('Invalid obstacle bounds')
        objects.append(dict(id=name, type='box', center_m=bounds.mean(axis=0).tolist(),
                            size_m=(bounds[1]-bounds[0]).tolist(), rpy_rad=[0., 0., 0.]))
    geometry = RobotGeometry(urdf, package, dict(frame_id='base_link', complete=True, objects=objects))
    baseline_flags = set(np.flatnonzero(geometry.distances(np.zeros(20)) <= .002 + 1e-9))
    for row in candidates:
        flags = np.flatnonzero(geometry.distances(row['state']) <= .002 + 1e-9)
        row['endpoint_model_margin_violations'] = len(flags)
        row['endpoint_scene_flags'] = sum(any(label.startswith('scene:') for label in geometry.labels[i]) for i in flags)
        row['endpoint_additional_flags_vs_HOME'] = sum(i not in baseline_flags for i in flags)
        row['endpoint_qualified'] = not len(flags)
    # A diagnostic shortlist, not an exemption of the retained HOME flags.
    eligible = [r for r in candidates if r['torso_tilt_deg'] <= 5.
                and r['endpoint_scene_flags'] == 0 and r['endpoint_additional_flags_vs_HOME'] == 0]
    selected = min(eligible, key=lambda r: (abs(r['inferred_support_height_m'] - annotations['target_table_height_m']), r['torso_tilt_deg'])) if eligible else None
    selection = dict(scope='ARCHIVED_DATASET_CANDIDATE_NOT_LIVE_COMPATIBILITY', physical_approval=False,
                     selected_candidate=selected['episode'] if selected else None,
                     candidates=candidates, sources_sha256=sources,
                     ranking='no_additional_or_scene_flags_then_upright_then_inferred_height_difference')
    write_json_exclusive(args.output_dir / 'selection.json', selection)
    if selected is None:
        raise ValueError('No upright candidate without additional or scene flags; see selection.json')
    print('SELECTED_CANDIDATE', selected['episode'], flush=True)
    ready_path = ROOT / 'scripts/vla/runtime/cruzr_s2_vla_ready_entry_transition_e6_1c.json'
    ready = json.loads(ready_path.read_text())['observed_ready_reference_20d_rad']
    result = dict(physical_approval=False, scene_complete=False, live_state_verified=False,
                  selected_candidate=selected['episode'], model_sources=geometry.manifest,
                  ready_source_sha256=digest(ready_path), routes={},
                  recovery_scope='EXACT_REVERSE_PLUS_HOME_TAIL_EMPTY_CLAMPS_UNCHANGED_SCENE_ONLY',
                  execution_contract_verified=False, stopping_distance_verified=False)
    result['recovery_home_tail'] = certify_pairs(geometry, [start, np.zeros(20)], seconds=args.route_budget_seconds)
    if args.home_tail_only:
        result['scope'] = 'HOME_TAIL_ONLY_NOT_ACCESS_PATH_REVIEW'
        result['recovery_waypoints_by_route'] = {
            label: [q.tolist() for q in empty_recovery_waypoints(path)]
            for label, path in routes(start, ready, np.asarray(selected['state'])).items()}
        if not geometry.source_files_unchanged() or any(digest(Path(p)) != h for p, h in sources.items()):
            raise RuntimeError('Source changed during analysis')
        write_json_exclusive(args.output_dir / 'home-tail-review.json', result)
        print('HOME_TAIL_ONLY', result['recovery_home_tail']['counts'], flush=True)
        return
    for label, path in routes(start, ready, np.asarray(selected['state'])).items():
        print('AUDIT_ROUTE', label, flush=True)
        audit = certify_pairs(geometry, path, seconds=args.route_budget_seconds)
        result['routes'][label] = dict(waypoints_20d_rad=[q.tolist() for q in path],
            recovery_waypoints_20d_rad=[q.tolist() for q in empty_recovery_waypoints(path)],
            joint_order=JOINT_ORDER, nominal_timing=retime(path), audit=audit,
            recovery_geometry_same_set_except_separately_checked_home_tail=True,
            recovery_is_not_valid_after_grasp_or_divergence=True)
        write_json_exclusive(args.output_dir / f'route-{label}.json', result['routes'][label])
        print(label, audit['counts'], 'timeout', audit['timed_out'], flush=True)
    # A declared 5-degree scenario remains a separate robustness check; it is
    # not claimed to be measured tracking error, and does not relax any margin.
    preferred = routes(start, ready, np.asarray(selected['state']))['via_ready']
    result['via_ready_error_scenario_5deg'] = certify_pairs(
        geometry, preferred, seconds=args.route_budget_seconds, joint_error_rad=math.radians(5))
    if not geometry.source_files_unchanged() or any(digest(Path(p)) != h for p, h in sources.items()):
        raise RuntimeError('Source changed during analysis')
    write_json_exclusive(args.output_dir / 'access-review.json', result)
    print('OFFLINE_REVIEW_COMPLETE_NO_EXECUTION_APPROVAL', flush=True)


if __name__ == '__main__':
    main()
