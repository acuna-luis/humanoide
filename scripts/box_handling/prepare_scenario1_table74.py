#!/usr/bin/env python3
"""Save an offline table-74 deposit candidate, never install or send motion.

Unmeasured hand coordinates remain explicit template tokens. No nominal tool
dimension, box height or successful action can substitute for that reference.
Even with a complete reference this produces review files, not a task bundle.
The operator proposes 3 cm of hand lowering AFTER support to free under-rim
pins, then lateral separation. That distance is not a verified clearance.
"""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path

try:
    from . import scenario1_deposit as deposit
except ImportError:
    import scenario1_deposit as deposit


ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / 'vendor/ubtech/cruzr_s2/snapshot_20260916/motion'
PROFILE = ROOT / 'config/box_handling/scenario1_put1.json'
FINAL_DESCENT_M = .05
RELEASE_DROP_M = .03


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Unexpected source structure: ' + old)
    return text.replace(old, new, 1)


def prepare(profile, original_xml, original_deposit, original_opening):
    for path, source in zip((deposit.SOURCE_XML_PATH, deposit.SOURCE_YAML_PATH,
                            deposit.SOURCE_OPEN_PATH),
                           (original_xml, original_deposit, original_opening)):
        if hashlib.sha256(source.encode()).hexdigest() != deposit.SOURCE_HASHES[path]:
            raise ValueError('Source checksum mismatch: ' + path)
    review = deposit.review(profile)
    if review['config']['surface_height_m'] != .74:
        raise ValueError('This candidate requires a horizontal table at 0.74 m')
    values = review['targets']
    ready = review['ready']
    # The original builder keeps the vendor 20 cm approach clearance. This
    # separate candidate uses the requested 5 cm final lowering segment.
    if values is not None:
        for target in values.values():
            target['approach_z_m'] = float(Decimal(str(target['contact_z_m'])) +
                                          Decimal(str(FINAL_DESCENT_M)))
    changed_deposit = original_deposit
    for side, y in (('left', '0.285'), ('right', '-0.285')):
        value = repr(values[side+'_hand']['approach_z_m']) if ready else (
            '${' + side.upper() + '_HAND_APPROACH_Z_M}')
        changed_deposit = replace_once(changed_deposit,
            '          position: [0.75, ' + y + ', 0.65] # x y z',
            '          position: [0.75, ' + y + ', ' + value + '] # x y z')
    changed_deposit = replace_once(changed_deposit,
        '  box_size: [0.6, 0.4, 0.28]', '  box_size: [0.603, 0.397, 0.22]')
    old_descent = '          position: [0.0, 0.0, -0.20] # x y z'
    if changed_deposit.count(old_descent) != 3:
        raise ValueError('Expected exactly two hand descents and one torso descent')
    changed_deposit = changed_deposit.replace(old_descent,
        '          position: [0.0, 0.0, -0.05] # x y z')
    opening = replace_once(original_opening, '  duration: 2.0', '  duration: 4.0')
    for y, qx in (('0.1', '0.6087614'), ('-0.1', '-0.6087614')):
        old = ('        - timestamp: 2.0\n'
               '          position: [0, ' + y + ', -0.05] # x y z\n'
               '          orientation: [0.7933533, ' + qx + ', 0.0, 0.0] # w x y z\n'
               '          # orientation: [1.0, 0.0, 0.0, 0.0] # w x y z\n'
               '          tranform_mode: "RELATIVE"')
        new = ('        - timestamp: 2.0\n'
               f'          position: [0, 0, {-RELEASE_DROP_M}] # x y z; proposed relief AFTER support\n'
               '          orientation: [1.0, 0.0, 0.0, 0.0] # w x y z\n'
               '          tranform_mode: "RELATIVE"\n'
               '        - timestamp: 4.0\n'
               '          position: [0, ' + y + ', 0.0] # x y z; lateral separation only\n'
               '          orientation: [1.0, 0.0, 0.0, 0.0] # w x y z\n'
               '          tranform_mode: "RELATIVE"')
        opening = replace_once(opening, old, new)
    opening = replace_once(opening,
        '        - timestamp: 2.0\n          position: [0.0, 0.0, -0.0]',
        '        - timestamp: 4.0\n          position: [0.0, 0.0, -0.0]')
    opening = replace_once(opening,
        '  box_size: [0.6, 0.4, 0.28]', '  box_size: [0.603, 0.397, 0.22]')
    banner = '# OFFLINE CANDIDATE ONLY: no installation, task XML or physical validation.\n'
    report = {
        'id': 'BOX-01-TABLE74-DRAFT-01', 'status': 'blocked_height_and_pin_release',
        'revision': 'BOX-01-TABLE74-RELEASE3-01',
        'installed': False, 'integrated_in_optimistic': False, 'can_install': False,
        'physical_validation': 'pending', 'source_hashes': dict(deposit.SOURCE_HASHES),
        'geometry_review': review,
        'nominal_box_on_table_floor_m': {'bottom': .74, 'center': .85, 'top': .96},
        'nominal_box_note': 'Horizontal box of height 0.22 m, resting on table; not hand coordinates.',
        'hand_formula': {
            'measured_hand_reference_contact_z_m':
                '0.74 + measured_hand_motion_z_m - measured_box_bottom_above_floor_m',
            'vendor_final_reference_contact_z_m':
                '0.45 + (0.74 - measured_box_bottom_at_verified_original_vendor_endpoint_m)',
            'approach_z_m': 'contact_z_m + 0.05',
            'after_release_z_m': f'contact_z_m - {RELEASE_DROP_M}',
            'requires': 'Same horizontal held box and hand orientations; actual simultaneous measured reference or verified original vendor endpoint.',
        },
        'deposit_descent_m': {'hands': -.05, 'torso': -.05},
        'deposit_descent_previous_m': {'hands': -.20, 'torso': -.20},
        'maximum_nominal_final_hand_descent_m': FINAL_DESCENT_M,
        'opening': {'duration_s': 4.0,
                    'lowering': {'duration_s': 2.0, 'both_hand_delta_m': [0, 0, -RELEASE_DROP_M]},
                    'separation': {'duration_s': 2.0, 'left_delta_m': [0, .10, 0],
                                   'right_delta_m': [0, -.10, 0]},
                    'relative_quaternion_wxyz': [1, 0, 0, 0],
                    'torso_delta_m': [0, 0, 0], 'status': 'operator_proposed_unverified'},
        'release_review': {
            'retention': 'pins_under_rim', 'source': 'operator_report_2026-09-30',
            'zero_drop_clearance_verified': False,
            'required_relative_hand_drop_after_support_m': None,
            'proposed_relative_hand_drop_after_support_m': RELEASE_DROP_M,
            'operator_max_drop_after_support_m': RELEASE_DROP_M,
            'rotation_for_disengagement': None,
            'note': 'Lowering box and hands together does not establish pin disengagement after support.',
        },
        'nominal_hand_drop_from_precontact_through_release_m': float(
            Decimal(str(FINAL_DESCENT_M)) + Decimal(str(RELEASE_DROP_M))),
        'opening_previous': {'hand_delta_z_m': -.05, 'relative_roll_deg_approx': [75, -75]},
        'limitations': [
            'No verified hand-to-box/floor reference is invented.',
            'Deposit contact window remains 10 to 12 seconds; early contact is not covered by that window.',
            'The 5 cm limit applies to the final relative lowering segment, not the preceding absolute approach from an unknown current pose.',
            '3 cm of lowering after support is an operator proposal, not a verified pin or table clearance.',
            'The zero-drop opening is rejected: under-rim pins may remain engaged. No minimum disengagement drop is known.',
            'Separate 2 second stages do not detect support: a future executor must establish stable support before release.',
            'Waypoints do not prove an exact stop or lack of interpolation blending at the 2 second transition.',
            'No executable task or robot installer is emitted; runtime still uses the original WRC task.',
        ],
    }
    deposit_name = 'put_table74.candidate.yaml' if ready else 'put_table74.yaml.in'
    return {
        deposit_name: banner + changed_deposit,
        'release_under_rim.candidate.yaml': banner + opening,
        'profile.json': json.dumps(profile, indent=2, ensure_ascii=False, allow_nan=False)+'\n',
        'review.json': json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False)+'\n',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, default=PROFILE)
    parser.add_argument('--output', type=Path, required=True, help='New local directory; never overwritten')
    args = parser.parse_args()
    sources = [(SNAPSHOT / path).read_text() for path in (
        'tasks/wrc_cruzr/put_cruzr_wrc_low.xml',
        'meta_clamp/wrc/put_cruzr_wrc_low.yaml', 'meta_clamp/wrc/open_arm_cruzr.yaml')]
    files = prepare(json.loads(args.profile.read_text()), *sources)
    args.output.mkdir(parents=True, exist_ok=False)
    for name, content in files.items():
        (args.output / name).write_text(content)
    print('CANDIDATO_LOCAL=' + str(args.output))
    print('SIN_INSTALACION_NI_MOVIMIENTO; revisar review.json antes de cualquier integración.')


if __name__ == '__main__':
    main()
