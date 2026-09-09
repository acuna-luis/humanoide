#!/usr/bin/env python3
"""Explicit PICO -> open -> lowered/open -> body HOME -> arm HOME targets.

Offline model of the commanded endpoints, not a certificate of Motion's
interpolator, tracking, stopping distance or physical clamp registration.
"""
import xml.etree.ElementTree as ET

from cruzr_pico_to_home_owner_gate import JOINT_ORDER, PICO_REFERENCE

REVISION = "pico_to_home_open_v2"
OPEN_ROLL_RAD = -0.6  # Both shoulders: negative roll is outward in the installed S2 URDF.
STAGE_NAMES = ("open_arms", "lower_arms_while_open", "body_home_while_open", "close_lowered_arms")
DURATIONS_S = (10.0, 40.0, 15.0, 15.0)
META_ARM_NAMES = ("shoulder_pitch", "shoulder_roll", "shoulder_yaw", "elbow_roll",
                  "elbow_yaw", "wrist_pitch", "wrist_roll")


def waypoints(start):
    if len(start) != 20:
        raise ValueError("Expected twenty joints")
    opened = list(PICO_REFERENCE[:14]) + list(start[14:])
    opened[3] = opened[10] = OPEN_ROLL_RAD
    lowered = [0.0]*14 + list(start[14:])
    lowered[3] = lowered[10] = OPEN_ROLL_RAD
    body_home = list(lowered[:14]) + [0.0]*6
    return [list(start), opened, lowered, body_home, [0.0]*20]


def xml_tree():
    root = ET.Element("root", main_tree_to_execute="MainTree")
    tree = ET.SubElement(root, "BehaviorTree", ID="MainTree")
    sequence = ET.SubElement(tree, "Sequence", name=REVISION)
    # Body values in the first two points are intentionally not emitted as commands.
    points = waypoints(PICO_REFERENCE)[1:]
    for index, (name, duration, target) in enumerate(zip(STAGE_NAMES, DURATIONS_S, points)):
        stage = ET.SubElement(sequence, "Parallel", name=name, threshold="3" if index == 2 else "2")
        state = dict(zip(JOINT_ORDER, target))
        groups = [("head", "single", ["head_pitch_joint", "head_yaw_joint"]),
                  ("lifter", "single", ["lifter_pitch_1_joint", "lifter_pitch_2_joint", "lifter_pitch_3_joint"]),
                  ("waist", "single", ["waist_yaw_joint"])] if index == 2 else [
                      ("arm", location, [side+"_"+joint+"_joint" for joint in META_ARM_NAMES])
                      for side, location in (("L", "left"), ("R", "right"))]
        for kind, location, names in groups:
            ET.SubElement(stage, "Action", ID="MetaMove", type=kind, location=location,
                          duration=f"{duration:.3f}",
                          joint_angles="; ".join(f"{state[n]:.12g}" for n in names))
    return root


def validate_xml(path):
    def signature(node):
        return node.tag, sorted(node.attrib.items()), [signature(child) for child in node]
    if signature(ET.parse(path).getroot()) != signature(xml_tree()):
        raise ValueError("XML does not match the four-stage outward HOME revision")


if __name__ == "__main__":
    root = xml_tree()
    ET.indent(root, space="    ")
    print(ET.tostring(root, encoding="unicode"))
