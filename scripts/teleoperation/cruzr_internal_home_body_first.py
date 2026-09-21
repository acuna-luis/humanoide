"""Body-first HOME candidate. No assertion of safety from arbitrary poses."""
import xml.etree.ElementTree as ET
from cruzr_internal_home_open_path import xml_tree as old_tree

# v5: elbow_roll soft upper limit is 0.0187 rad (URDF 0.0349). A straight elbow
# that sags past it after power loss makes Motion reject every command of that
# arm, including the relative open step (incident 2026-09-18). Bend both elbows
# slightly first; the final absolute close step returns them to 0.
V5_ELBOW_DELTA = '0; 0; 0; -0.03; 0; 0; 0'
# v5 also opens the shoulders half as much as v4 (owner request 2026-09-18).
# Offline sweep (audit_body_first_v5_opening.py): clamp-to-torso minimum from
# PICO starts 164 -> 133 mm (conditional bound 102 -> 69 mm); direct HOME 3-10 mm.
V5_OPEN_DELTA = '0; -0.2; 0; 0; 0; 0; 0'
V5_LOWERED = '0; -0.3; 0; 0; 0; 0; 0'
# Faster v5 without exceeding v4 peak joint speed/acceleration (quintic):
# elbows move during the 3.75 s body stage; the halved 0.2/0.3 rad roll moves
# use 1.8/2.7 s (v4: 0.4/0.6 rad in 2.5/3.75 s). The 10 s lowering is unchanged.
V5_OPEN_SECONDS = '1.800'
V5_CLOSE_SECONDS = '2.700'
# v6 (candidate, not installed): v5 geometry, but each arm runs "elbows then
# open" as its own sequence in parallel with head/lifter/waist. Separate elbow
# and open commands keep the out-of-limit elbow recovery free of shoulder jumps.
V6_ELBOW_SECONDS = '1.000'
# v7 = v6 with the 10 s lowering shortened to 7 s (owner-supervised trial,
# 2026-09-18). Same path geometry; peak speed/acceleration of the lowering stays
# below the vendor direct HOME (6 s) for the reviewed starts (see tests).
V7_LOWER_SECONDS = '7.000'


def xml_bytes(version=4):
    if version not in (4, 5, 6, 7):
        raise ValueError('Unknown body-first HOME version')
    root = old_tree(20)
    seq = root.find('.//Sequence')
    seq.set('name', {4: 'home_body_first_v4_20s', 5: 'home_body_first_v5_18s',
                     6: 'home_body_first_v6_16s', 7: 'home_body_first_v7_13s'}[version])
    body = seq[2]
    seq.remove(body)
    body.set('name', 'body_home_preserving_arm_joints')
    seq.insert(0, body)
    if version in (6, 7):
        opening = seq.find("Parallel[@name='open_arms']")
        seq.remove(opening)
        body.set('name', 'body_home_with_arm_elbows_then_open')
        body.set('threshold', '5')
        for side, action in zip(('left', 'right'), list(opening)):
            arm = ET.SubElement(body, 'Sequence', name=side+'_arm_elbow_then_open')
            ET.SubElement(arm, 'Action', ID='MetaMove', type='arm', location=side,
                          duration=V6_ELBOW_SECONDS, delta_joint_angles=V5_ELBOW_DELTA)
            action.set('delta_joint_angles', V5_OPEN_DELTA)
            action.set('duration', V5_OPEN_SECONDS)
            arm.append(action)
        for action in seq.find("Parallel[@name='lower_arms_while_open']"):
            action.set('joint_angles', V5_LOWERED)
        for action in seq.find("Parallel[@name='close_lowered_arms']"):
            action.set('duration', V5_CLOSE_SECONDS)
        if version == 7:
            for action in seq.find("Parallel[@name='lower_arms_while_open']"):
                action.set('duration', V7_LOWER_SECONDS)
    if version == 5:
        body.set('name', 'body_home_and_elbows_into_limits')
        body.set('threshold', '5')
        for side in ('left', 'right'):
            ET.SubElement(body, 'Action', ID='MetaMove', type='arm', location=side,
                          duration=body[0].get('duration'), delta_joint_angles=V5_ELBOW_DELTA)
        for action in seq.find("Parallel[@name='open_arms']"):
            action.set('delta_joint_angles', V5_OPEN_DELTA)
            action.set('duration', V5_OPEN_SECONDS)
        for action in seq.find("Parallel[@name='lower_arms_while_open']"):
            action.set('joint_angles', V5_LOWERED)
        for action in seq.find("Parallel[@name='close_lowered_arms']"):
            action.set('duration', V5_CLOSE_SECONDS)
    ET.indent(root, space='    ')
    return (ET.tostring(root, encoding='unicode')+'\n').encode()

def validate_xml(data, seconds=20, version=4):
    def signature(n):
        return n.tag, sorted(n.attrib.items()), [signature(c) for c in n]
    if seconds != 20 or signature(ET.fromstring(data)) != signature(ET.fromstring(xml_bytes(version))):
        raise ValueError('Unexpected body-first HOME sequence')
