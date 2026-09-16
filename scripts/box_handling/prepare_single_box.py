#!/usr/bin/env python3
"""Offline layout arithmetic only. No ROS, SSH, installer or movement output."""
import argparse
import json
import math
from pathlib import Path


def prepare(p):
    if p['units'] != 'm' or p['execution']['enabled'] is not False:
        raise ValueError('Expected metres and disabled execution')
    b, r, g = p['box'], p['rack'], p['pickup']
    for v in [*([b[k] for k in ('width', 'depth', 'height')]),
              *([r[k] for k in ('clear_width', 'reported_clear_height', 'horizontal_depth',
                               'entry_surface_above_floor', 'exit_surface_above_floor')]),
              g['box_base_above_floor'], g['proposed_vertical_lift']]:
        if not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0:
            raise ValueError('Dimensions must be finite and positive')
    fall = r['entry_surface_above_floor'] - r['exit_surface_above_floor']
    if fall <= 0:
        raise ValueError('Expected entry higher than exit')
    a = math.atan2(fall, r['horizontal_depth'])
    # Bounding projections of a rectangular box pitched from horizontal to slope.
    def maximum_projection(u, v):
        t = min(a, math.atan2(v, u))
        return u * math.cos(t) + v * math.sin(t)
    depth = b['depth'] * math.cos(a) + b['height'] * math.sin(a)
    height = b['height'] * math.cos(a) + b['depth'] * math.sin(a)
    return {
        'status': 'OFFLINE_LAYOUT_ONLY_NOT_MOTION_APPROVAL',
        'units': 'm, degrees',
        'calculated': {
            'slope_degrees': math.degrees(a),
            'pickup_box_top': g['box_base_above_floor'] + b['height'],
            'proposed_lift_above_reported_minimum': g['proposed_vertical_lift'] - g['reported_minimum_disengagement'],
            'box_horizontal_depth_at_slope': depth,
            'box_vertical_extent_at_slope': height,
            'maximum_box_depth_during_pitch': maximum_projection(b['depth'], b['height']),
            'maximum_box_height_during_pitch': maximum_projection(b['height'], b['depth']),
            'nominal_width_residual_total_box_only': r['clear_width'] - b['width'],
            'nominal_depth_residual_total_box_only': r['horizontal_depth'] - depth,
            'nominal_height_residual_box_only': r['reported_clear_height'] - height,
            'ideal_static_friction_threshold_tan_slope': math.tan(a)
        },
        'limitations': [
            'Residual dimensions are not robot collision clearance or allowable positioning error.',
            'Pitch projections exclude translation sweep, clamps, arms, shelf lips, posts and stop.',
            'Reported 0.50 m opening is not yet a measured minimum along the entire insertion.',
            'Friction threshold is idealised, not a measurement or a retention qualification.',
            'A reported minimum disengagement is not an upper bound on required lift.'
        ],
        'stages': [
            {'id': 'grasp', 'requirement': 'Detect top box, approach sides and confirm bimanual grip; no lateral extraction.'},
            {'id': 'disengage', 'proposed_vertical_translation_m': g['proposed_vertical_lift'],
             'requirement': 'Lift vertically without tilt; confirm lower boxes remain supported and upper rim clears.'},
            {'id': 'withdraw', 'requirement': 'Only after disengagement; path from registered pile and pallet geometry.'},
            {'id': 'transport', 'requirement': 'Navigate once to taught pre-rack pose with held-box geometry.'},
            {'id': 'place', 'requirement': 'Review approach, rigid bimanual rotation, insertion and support on actual slope.'},
            {'id': 'release', 'requirement': 'Release only with stable support and verified retention; do not assume sliding.'},
            {'id': 'retreat', 'requirement': 'Withdraw empty clamps clear of rack before separate HOME.'}
        ],
        'pending': ['Registration of pickup/rack and actual joint state',
                    'Box-to-clamp contact frame and bimanual tilted pose/IK',
                    'Full shelf/posts/upper-level/stop and clamp swept geometry',
                    'Disengagement and stable support/retention confirmation',
                    'Runtime trajectory semantics, monitoring and supervised trial'],
        'execution_enabled': False
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, default=Path(__file__).resolve().parents[2] / 'config/box_handling/single_box_inclined_rack.json')
    args = parser.parse_args()
    print(json.dumps(prepare(json.loads(args.profile.read_text())), indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == '__main__':
    main()
