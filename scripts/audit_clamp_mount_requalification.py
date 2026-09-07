#!/usr/bin/env python3
"""Offline bilateral mount input validation; no collision/physical approval.

Unlike retired E6.0K, transforms all eight corners using measured R/t. No
centering, reflection or zero defaults. Success means input completeness only.
"""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def vector(value, length):
    return isinstance(value, list) and len(value) == length and all(
        type(x) in (int, float) and math.isfinite(x) for x in value)


def mount_bounds(mount, side):
    if mount.get('parent_frame') != f'{side}_sixforce_link':
        raise ValueError('parent_frame')
    t, r, b, margin = (mount.get(k) for k in
                       ('translation_m', 'rotation_matrix', 'local_bounds_m', 'uncertainty_m'))
    if not vector(t, 3):
        raise ValueError('translation_m_missing_or_invalid')
    if not isinstance(r, list) or len(r) != 3 or not all(vector(row, 3) for row in r):
        raise ValueError('rotation_matrix_missing_or_invalid')
    for i in range(3):
        for j in range(3):
            if abs(sum(r[i][k]*r[j][k] for k in range(3)) - (i == j)) > 1e-6:
                raise ValueError('rotation_not_orthonormal')
    det = sum(r[0][i]*(r[1][(i+1)%3]*r[2][(i+2)%3] - r[1][(i+2)%3]*r[2][(i+1)%3]) for i in range(3))
    if abs(det-1) > 1e-6:
        raise ValueError('rotation_reflection_or_invalid')
    if not isinstance(b, list) or len(b) != 2 or not all(vector(row, 3) for row in b):
        raise ValueError('local_bounds_missing_or_invalid')
    if any(b[0][i] >= b[1][i] for i in range(3)):
        raise ValueError('bounds_inverted_or_empty')
    if type(margin) not in (int, float) or not math.isfinite(margin) or margin <= 0:
        raise ValueError('uncertainty_missing_or_invalid')
    if mount.get('includes_tabs_fasteners_and_support') is not True:
        raise ValueError('incomplete_tool_geometry')
    points = [[t[i]+sum(r[i][k]*p[k] for k in range(3)) for i in range(3)]
              for p in itertools.product(*zip(*b))]
    return [[min(p[i] for p in points)-margin for i in range(3)],
            [max(p[i] for p in points)+margin for i in range(3)]]


def reported_front_profile(d):
    """2D bounding rectangle only: u points toward tabs, v toward upper edge.

    Not a ROS frame or a full tool volume. Extending the whole edge encloses
    both tabs without inventing their individual heights/radii.
    """
    keys = ('plate_width_m', 'tab_projection_from_plate_edge_m',
            'upper_edge_from_mount_plane_reported_m',
            'lower_edge_from_mount_plane_reported_m')
    if not all(type(d.get(k)) in (int, float) and math.isfinite(d[k]) and d[k] > 0
               for k in keys):
        return {'status': 'INCOMPLETE_DIMENSIONS'}
    if (d.get('plate_lateral_position_relative_to_sensor_axis_m') != 0.0
            or d.get('tabs_on_same_lateral_edge') is not True
            or d.get('upper_lower_reference_confirmed_after_diagram_correction') is not True):
        return {'status': 'INCOMPLETE_REFERENCE'}
    w, p, b, c = (d[k] for k in keys)
    h = d.get('plate_height_directly_remeasured_m')
    if type(h) not in (int, float) or not math.isfinite(h) or abs(b+c-h) > 1e-9:
        return {'status': 'INCONSISTENT_HEIGHT'}
    return {'status': 'REPORTED_2D_PROFILE_ONLY',
            'axis_definition': 'u_toward_tabs;v_toward_upper_edge;not_ROS_axes',
            'u_bounds_m': [-w/2, w/2+p], 'v_bounds_m': [-c, b],
            'outer_width_m': w+p, 'height_m': h,
            'whole_tab_edge_filled_conservatively': True,
            'includes_support_depth_and_fasteners': False,
            'includes_measurement_uncertainty': False,
            'physical_authorized': False}


def reported_plate_volume(d):
    """Descriptive scalar extents, not an oriented ROS collision object."""
    profile = reported_front_profile(d)
    if profile['status'] != 'REPORTED_2D_PROFILE_ONLY':
        return {'status': 'INCOMPLETE_FRONT_PROFILE'}
    a, f = d.get('axis_to_pad_face_m'), d.get('plate_with_pads_thickness_m')
    if not all(type(x) in (int, float) and math.isfinite(x) and x > 0 for x in (a, f)):
        return {'status': 'INCOMPLETE_DEPTH'}
    if f >= a:
        return {'status': 'UNREVIEWED_DEPTH_CROSSES_SENSOR_AXIS'}
    w = d['plate_width_m']
    return {
        'status': 'REPORTED_PLATE_VOLUME_NOT_FULL_TOOL',
        'coordinates': 'descriptive_distances_only;handedness_and_ROS_mapping_unresolved',
        'lateral_plain_plate_bounds_m': [-w/2, w/2],
        'vertical_bounds_from_mount_plane_m': profile['v_bounds_m'],
        'depth_from_sensor_axis_toward_pads_m': [a-f, a],
        'plain_plate_with_pads_size_m': [w, profile['height_m'], f],
        'candidate_with_tab_edge_size_m': [profile['outer_width_m'], profile['height_m'], f],
        'tab_extrusion_is_candidate_requires_depth_containment_check': True,
        'support_fasteners_and_uncertainty_included': False,
        'physical_authorized': False,
    }


def evaluate(contract):
    if contract.get('schema') != 'cruzr-clamp-requalification-v1':
        raise ValueError('schema')
    errors, bounds = [], {}
    for side in ('L', 'R'):
        mount = contract.get('mounts', {}).get(side, {})
        try:
            bounds[side] = mount_bounds(mount, side)
            entries = mount.get('measurement_evidence')
            if not isinstance(entries, list) or not entries:
                raise ValueError('measurement_evidence_missing')
            for entry in entries:
                path = Path(entry['path'])
                if not path.is_absolute():
                    path = ROOT / path
                if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
                    raise ValueError('measurement_evidence_hash_mismatch')
        except (ValueError, TypeError, KeyError, OSError) as exc:
            errors.append(f'{side}:{exc}')
    return dict(
        status='BLOCKED_MOUNT_INPUTS' if errors else 'INPUTS_COMPLETE_NOT_TRAJECTORY_VALIDATED',
        reported_dimensions=contract.get('reported_dimensions', {}),
        front_profile=reported_front_profile(contract.get('reported_dimensions', {})),
        plate_volume=reported_plate_volume(contract.get('reported_dimensions', {})),
        reported_dimensions_are_not_a_measured_mount_transform=True,
        mount_errors=errors, transformed_bounds_in_parent_frame_m=bounds,
        physical_authorized=False, robot_connections=0, movement_commands=0,
        pending=['measured_mounts' if errors else 'independent_mount_review',
                 'runtime_interpolation_equivalence', 'continuous_sweep_and_stopping_margin',
                 'vendor_boot_home_interception'],
        scenarios={name: 'NOT_QUALIFIED_NO_SWEEP_EXECUTED' for name in
                   ('home_to_ready', 'ready_to_home', 'asymmetric_to_home',
                    'ready_to_entry', 'entry_to_ready', 'boot_home')})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract', type=Path, default=ROOT/'config/clamp_mount_requalification.json')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = evaluate(json.loads(args.contract.read_text()))
    report['contract_sha256'] = hashlib.sha256(args.contract.read_bytes()).hexdigest()
    text = json.dumps(report, indent=2, allow_nan=False)+'\n'
    if args.output:
        with args.output.open('x') as out:
            out.write(text)
    print(text, end='')
    return 3 if report['mount_errors'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
