#!/usr/bin/env python3
"""Model the internal HOME replacement; no robot connection or motion.

Unlike the PICO-only path, the opening step preserves all non-roll joints.
This does not qualify arbitrary starting poses, loads, interpolation or braking.
"""
import argparse
import math
import xml.etree.ElementTree as ET

from cruzr_pico_home_open_path import META_ARM_NAMES, STAGE_NAMES
from cruzr_pico_to_home_owner_gate import JOINT_ORDER, PICO_VARIANTS

OPEN_DELTA_RAD = -0.4
LOWERED_ROLL_RAD = -0.6
DURATIONS = {20: (2.5, 10.0, 3.75, 3.75), 6: (0.75, 3.0, 1.125, 1.125)}
REVIEW_STARTS = dict(PICO_VARIANTS,
    arms_down_body_zero=[0.0]*20,
    arms_down_body_flexed=[0.0]*14 + PICO_VARIANTS['pico_body_flexed'][14:])


def waypoints(start):
    if len(start) != 20 or not all(type(x) in (int, float) and math.isfinite(x) for x in start):
        raise ValueError('Expected twenty finite joint positions')
    opened = list(start)
    for i in (3, 10):
        opened[i] += OPEN_DELTA_RAD
    lowered = [0.0]*14 + list(start[14:])
    lowered[3] = lowered[10] = LOWERED_ROLL_RAD
    body_home = lowered[:14] + [0.0]*6
    return [list(start), opened, lowered, body_home, [0.0]*20]


def xml_tree(seconds=20):
    if type(seconds) is not int or seconds not in DURATIONS:
        raise ValueError('Only reviewed timing candidates 20 or 6 are defined')
    root = ET.Element('root', main_tree_to_execute='MainTree')
    tree = ET.SubElement(root, 'BehaviorTree', ID='MainTree')
    seq = ET.SubElement(tree, 'Sequence', name=f'home_open_v3_{seconds}s')
    points = waypoints(REVIEW_STARTS['arms_down_body_zero'])[1:]
    for i, (name, duration, target) in enumerate(zip(STAGE_NAMES, DURATIONS[seconds], points)):
        stage = ET.SubElement(seq, 'Parallel', name=name, threshold='3' if i == 2 else '2')
        state = dict(zip(JOINT_ORDER, target))
        groups = [('head', 'single', ['head_yaw_joint', 'head_pitch_joint']),
                  ('lifter', 'single', ['lifter_pitch_1_joint', 'lifter_pitch_2_joint', 'lifter_pitch_3_joint']),
                  ('waist', 'single', ['waist_yaw_joint'])] if i == 2 else [
            ('arm', loc, [side+'_'+joint+'_joint' for joint in META_ARM_NAMES])
            for side, loc in (('L', 'left'), ('R', 'right'))]
        for kind, loc, names in groups:
            # delta_joint_angles is a registered vendor input port, not an
            # invented partial-position sentinel or a low-level command.
            values = [OPEN_DELTA_RAD if n.endswith('_shoulder_roll_joint') else 0.0
                      for n in names] if i == 0 else [state[n] for n in names]
            ET.SubElement(stage, 'Action', ID='MetaMove', type=kind, location=loc,
                          duration=f'{duration:.3f}', **{
                              'delta_joint_angles' if i == 0 else 'joint_angles':
                                  '; '.join(f'{v:.12g}' for v in values)})
    return root


def xml_bytes(seconds=20):
    root = xml_tree(seconds)
    ET.indent(root, space='    ')
    return (ET.tostring(root, encoding='unicode')+'\n').encode()


def validate_xml(data, seconds=20):
    def signature(node):
        return node.tag, sorted(node.attrib.items()), [signature(c) for c in node]
    if signature(ET.fromstring(data)) != signature(xml_tree(seconds)):
        raise ValueError('Internal HOME XML differs from the reviewed sequence')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=int, choices=tuple(DURATIONS), default=20)
    args = parser.parse_args()
    print(xml_bytes(args.seconds).decode(), end='')
