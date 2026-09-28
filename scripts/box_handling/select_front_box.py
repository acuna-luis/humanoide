#!/usr/bin/env python3
"""Offline frontal-box selection; no ROS, network, publishers or motion.

Input: {"frame_id": "base_link", "poses": [geometry_msgs/Pose dictionaries]}.
The caller must transform a single coherent detection into the robot frame.
This diagnostic does not certify TF, freshness, reachability or a grasp.
"""
import argparse
import copy
import json
import math
from pathlib import Path


def select_front_box(detection, *, front_angle_deg=20.0, ambiguity_deg=2.0):
    """Select the top detected box of the most frontal stack.

    No reachability filtering: an unreachable frontal box must never cause
    selection of a different lateral box. Height only resolves a coherent
    vertical stack of the configured 0.22 m workbins, never competing stacks.
    Aligned stacks with tops at the same level use nearest depth first: a
    background box must not win merely because perspective centers its bearing.
    Incompatible levels or ambiguous lateral lanes fail closed.
    Angles are diagnostic policy values, not physical safety limits.
    """
    if detection.get('frame_id') != 'base_link':
        raise ValueError('Expected poses transformed to base_link')
    for value in (front_angle_deg, ambiguity_deg):
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError('Angles must be finite numbers')
    if not 0 <= ambiguity_deg < front_angle_deg < 90:
        raise ValueError('Require 0 <= ambiguity < front angle < 90 degrees')
    poses = detection.get('poses')
    if not isinstance(poses, list) or not poses:
        raise ValueError('No detected poses')
    ranked = []
    for index, pose in enumerate(poses):
        try:
            p, q = pose['position'], pose['orientation']
            values = [p[k] for k in 'xyz'] + [q[k] for k in 'xyzw']
            if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
                raise ValueError('Nonfinite pose')
            if abs(math.sqrt(sum(q[k] ** 2 for k in 'xyzw')) - 1) > 0.01:
                raise ValueError('Invalid quaternion')
            angle = math.degrees(math.atan2(p['y'], p['x']))
        except (KeyError, TypeError, OverflowError) as exc:
            raise ValueError('Invalid pose at index %d' % index) from exc
        if p['x'] > 0:
            ranked.append((abs(angle), index, angle))
    if not any(row[0] <= front_angle_deg for row in ranked):
        raise ValueError('No box within the frontal sector')
    # Group only near-coincident XY centers. Connected components must also
    # satisfy a full diameter bound: chains cannot merge separate columns.
    stack_xy_tolerance = 0.08
    stack_height = 0.22
    stack_height_tolerance = 0.04
    remaining = {row[1] for row in ranked}
    groups = {}
    def xy_distance(a, b):
        pa, pb = poses[a]['position'], poses[b]['position']
        return math.hypot(pa['x']-pb['x'], pa['y']-pb['y'])
    bearings = {row[1]: row[2] for row in ranked}
    while remaining:
        members = {min(remaining)}
        while True:
            additions = {j for j in remaining-members
                         if any(xy_distance(i, j) <= stack_xy_tolerance for i in members)}
            if not additions:
                break
            members.update(additions)
        remaining.difference_update(members)
        if not any(abs(bearings[i]) <= front_angle_deg for i in members):
            continue
        ordered = sorted(members, key=lambda i: poses[i]['position']['z'])
        if len(ordered) > 1:
            if any(xy_distance(a, b) > stack_xy_tolerance for a in members for b in members):
                raise ValueError('Ambiguous stack: horizontal spread exceeds grouping tolerance')
            gaps = [poses[b]['position']['z']-poses[a]['position']['z']
                    for a, b in zip(ordered, ordered[1:])]
            if any(abs(gap-stack_height) > stack_height_tolerance for gap in gaps):
                raise ValueError('Ambiguous stack: heights do not match successive 0.22m boxes')
        top = ordered[-1]
        # Never expose a support as the target merely because the top box is
        # just outside the frontal sector. Group first, apply the sector last.
        if abs(bearings[top]) > front_angle_deg:
            continue
        groups[top] = ordered
    # Collapse front/back alternatives BEFORE bearing ranking. This is target
    # selection, never a reachability filter or a fallback to a lateral box.
    # Only same-level tops in one narrow lateral lane can be ordered by depth;
    # differing levels need scene interpretation that this selector cannot do.
    lane_y_tolerance = stack_xy_tolerance
    level_z_tolerance = stack_height_tolerance
    remaining_tops = set(groups)
    front_representatives = []
    background = []
    while remaining_tops:
        lane = {min(remaining_tops)}
        while True:
            additions = {j for j in remaining_tops-lane
                         if any(abs(poses[i]['position']['y']-poses[j]['position']['y'])
                                <= lane_y_tolerance for i in lane)}
            if not additions:
                break
            lane.update(additions)
        remaining_tops.difference_update(lane)
        ordered = sorted(lane, key=lambda i: poses[i]['position']['x'])
        if len(ordered) > 1:
            ys = [poses[i]['position']['y'] for i in ordered]
            zs = [poses[i]['position']['z'] for i in ordered]
            if max(ys)-min(ys) > lane_y_tolerance:
                raise ValueError('Ambiguous frontal lane: lateral chain exceeds tolerance')
            if max(zs)-min(zs) > level_z_tolerance:
                raise ValueError('Ambiguous frontal lane: different top levels at different depths')
            if any(poses[b]['position']['x']-poses[a]['position']['x'] <= stack_xy_tolerance
                   for a, b in zip(ordered, ordered[1:])):
                raise ValueError('Ambiguous frontal lane: depth separation too small')
            background.extend(dict(front_index=ordered[0], background_index=i)
                              for i in ordered[1:])
        front = ordered[0]
        front_representatives.append((abs(bearings[front]), front, bearings[front]))
    ranked = sorted(front_representatives)
    if not ranked:
        raise ValueError('No top box within the frontal sector')
    if len(ranked) > 1 and ranked[1][0] - ranked[0][0] <= ambiguity_deg:
        raise ValueError('Ambiguous frontal stacks; do not choose by height or list order')
    _, index, angle = ranked[0]
    return {
        'selected_index': index,
        'selected_pose': copy.deepcopy(poses[index]),
        'horizontal_bearing_deg': angle,
        'selection_rule': 'nearest_depth_in_same_level_frontal_lane; minimum_absolute_horizontal_bearing_between_lanes; top_detected_box_within_stack',
        'selected_stack_indices_bottom_to_top': groups[index],
        'stack_xy_tolerance_m': stack_xy_tolerance,
        'stack_box_height_m': stack_height,
        'stack_height_tolerance_m': stack_height_tolerance,
        'lane_y_tolerance_m': lane_y_tolerance,
        'lane_level_z_tolerance_m': level_z_tolerance,
        'background_stack_tops_excluded': background,
        'front_angle_deg': front_angle_deg,
        'ambiguity_deg': ambiguity_deg,
        'scope': 'offline_selection_only',
        'reachability_checked': False,
        'motion_authorized': False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('detection', type=Path)
    parser.add_argument('--front-angle-deg', type=float, default=20.0)
    parser.add_argument('--ambiguity-deg', type=float, default=2.0)
    args = parser.parse_args()
    try:
        result = select_front_box(json.loads(args.detection.read_text()),
                                  front_angle_deg=args.front_angle_deg,
                                  ambiguity_deg=args.ambiguity_deg)
    except (ValueError, TypeError, AttributeError, OSError) as exc:
        parser.exit(2, 'SELECTION_REJECTED: %s\n' % exc)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
