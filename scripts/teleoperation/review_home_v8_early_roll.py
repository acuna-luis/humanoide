#!/usr/bin/env python3
"""Offline v8 candidate review. Never installs, dispatches or authorizes movement."""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from audit_pico_home_open_path import audit
from cruzr_pico_to_home_owner_gate import JOINT_ORDER

HERE = Path(__file__).resolve().parent
CANDIDATE = HERE/'tasks/cruzr_home_v8_early_roll_CANDIDATE.xml'
BASE = HERE/'tasks/cruzr_internal_home_body_first_v7_13s.xml'


def duration(node):
    if node.tag == 'Action':
        return float(node.get('duration'))
    times = [duration(c) for c in node]
    return max(times) if node.tag == 'Parallel' else sum(times)


def check_structure():
    original = ET.parse(BASE).getroot()
    changed = ET.parse(CANDIDATE).getroot()
    seq = changed.find('./BehaviorTree/Sequence')
    assert duration(seq) == 13.45
    count = 0
    for arm in changed.findall('.//Sequence'):
        if arm.get('name', '').endswith('_arm_elbow_then_open'):
            assert arm[0].get('delta_joint_angles') == '0; -0.05; 0; -0.03; 0; 0; 0'
            assert arm[1].get('delta_joint_angles') == '0; -0.15; 0; 0; 0; 0; 0'
            arm[0].set('delta_joint_angles', '0; 0; 0; -0.03; 0; 0; 0')
            arm[1].set('delta_joint_angles', '0; -0.2; 0; 0; 0; 0; 0')
            count += 1
    assert count == 2
    seq.set('name', original.find('./BehaviorTree/Sequence').get('name'))
    assert ET.tostring(changed) == ET.tostring(original)


def path_for(order):
    def path(q):
        body = list(q[:14])+[0.0]*6
        first = list(q)
        for elbow, roll in ((0, 3), (7, 10)):
            first[elbow] -= .03
            first[roll] -= .05
        opened = list(first)
        opened[3] -= .15
        opened[10] -= .15
        lowered = [0.0]*20
        lowered[3] = lowered[10] = -.3
        if order == 'body_first':
            return [list(q), body, first[:14]+[0.0]*6, opened[:14]+[0.0]*6,
                    lowered, [0.0]*20]
        return [list(q), first, opened, opened[:14]+[0.0]*6, lowered, [0.0]*20]
    return path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state', required=True, type=Path)
    p.add_argument('--snapshot', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--samples', type=int, default=501)
    a = p.parse_args()
    check_structure()
    s = json.loads(a.state.read_text())
    assert len(s['name']) == len(set(s['name'])) == len(s['position'])
    values = dict(zip(s['name'], s['position']))
    start = [values[n] for n in JOINT_ORDER]
    result = dict(nominal_seconds=13.45, installed=False, physical_approval=False,
                  conditional=False, limitation='Fixed split opening; no native runtime state gate. '
                  'Serial brackets do not bound every concurrent trajectory or controller rejection.', runs={})
    for order, times in [('body_first', (3.75, 1., 1.8, 7., 2.7)),
                         ('arms_first', (1., 1.8, 3.75, 7., 2.7))]:
        result['runs'][order] = audit(a.snapshot, a.samples, path=path_for(order),
            durations=times, revision='v8_early_roll_'+order, variants={'measured':start})
    with a.output.open('x') as f:
        json.dump(result, f, indent=2, allow_nan=False)


if __name__ == '__main__':
    main()
