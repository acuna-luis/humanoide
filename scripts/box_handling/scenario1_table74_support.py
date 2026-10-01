#!/usr/bin/env python3
"""Build a pinned support-only trial after one reviewed table-74 approach.

Offline artifacts only: no installation, action dispatch or automatic opening.
The operator reported approximately 5 cm of current clearance after the pinned
approach succeeded. A 5 cm relative lowering is a requested trial, not proof of
table support, pin clearance or a calibrated absolute Motion hand height.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import re

try:
    from . import scenario1_deposit as deposit
except ImportError:
    import scenario1_deposit as deposit


BUILDER_VERSION = 1
NAMESPACE = 'local_table74_support/'
TASK_ROOT = deposit.TASK_ROOT
META_ROOT = deposit.META_ROOT
SOURCE_XML_PATH = deposit.SOURCE_XML_PATH
SOURCE_YAML_PATH = deposit.SOURCE_YAML_PATH
META_CLAMP_PATH = '/opt/walker/manipulation_meta_tasks/lib/libmeta_clamp.so'
META_CLAMP_SHA256 = 'd6bc61a493f7d790150fdbd673108121f46589fef56620de4a9023dcc2ba520a'
BINARY_SHA = META_CLAMP_SHA256
PINNED_APPROACH_BUNDLE_ID = '9360060014e4103ce31da084426302ee4c2e06900a0f5707bf68df0d07ada9ef'
PINNED_APPROACH_GOAL_ID = '7553e90f-cde1-4ca7-a488-96c86816d988'
DEPENDENCIES = {
    SOURCE_XML_PATH: deposit.SOURCE_HASHES[SOURCE_XML_PATH],
    SOURCE_YAML_PATH: deposit.SOURCE_HASHES[SOURCE_YAML_PATH],
    META_CLAMP_PATH: META_CLAMP_SHA256,
}
_REFERENCE_KEYS = {'version', 'gap_above_surface_m', 'surface_height_m',
                   'predecessor_bundle_id', 'predecessor_goal_id', 'evidence', 'scope'}
_TASK_TOKEN = '__TABLE74_SUPPORT_TASK_NAME__'
_IDENTITY_Q = '[1.0, 0.0, 0.0, 0.0]'
_VENDOR_Q = '[0.5, 0.5, 0.5, -0.5]'
_ZERO = '[0.0, 0.0, 0.0]'


def sha256(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False)


def validate_reference(reference):
    """Pin provenance and the current 5 cm report; do not infer a reach range."""
    if not isinstance(reference, dict) or set(reference) != _REFERENCE_KEYS:
        raise ValueError('Support reference: missing or unknown fields')
    if type(reference['version']) is not int or reference['version'] != 1:
        raise ValueError('Unsupported support reference version')
    if reference['scope'] != 'current_post_approach_box_only':
        raise ValueError('Support reference is limited to the unchanged current post-approach box')
    if (reference['predecessor_bundle_id'] != PINNED_APPROACH_BUNDLE_ID or
            reference['predecessor_goal_id'] != PINNED_APPROACH_GOAL_ID):
        raise ValueError('Support requires the exact reviewed predecessor approach and goal')
    if type(reference['evidence']) is not str or not reference['evidence'].strip():
        raise ValueError('Support requires explicit operator gap measurement evidence')
    result = copy.deepcopy(reference)
    for name, expected in (('gap_above_surface_m', .05), ('surface_height_m', .74)):
        value = reference[name]
        try:
            valid = type(value) in (int, float) and math.isfinite(value) and value > 0
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError(name + ': expected a positive finite number')
        if value != expected:
            raise ValueError(name + ': another measurement requires a new review')
        result[name] = float(value)
    return result


def _replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError('Pinned support source structure changed')
    return text.replace(before, after, 1)


def _trajectory(*, support):
    """Exact source/candidate trajectory blocks; all other source bytes survive."""
    output = ['  robot_trajectory_data:\n']
    for body in ('left_hand', 'right_hand', 'torso'):
        if support:
            points = [(_ZERO, _IDENTITY_Q, 'RELATIVE')] * 2
            points.append((_ZERO if body == 'torso' else '[0.0, 0.0, -0.05]',
                           _IDENTITY_Q, 'RELATIVE'))
        elif body == 'torso':
            points = [('[0.0, 0.0, 1.2]', _IDENTITY_Q, 'ABSOLUTE'),
                      ('[0.30, 0, 1.2]', _IDENTITY_Q, 'ABSOLUTE'),
                      ('[0.0, 0.0, -0.20]', _IDENTITY_Q, 'RELATIVE')]
        else:
            y = '0.285' if body == 'left_hand' else '-0.285'
            points = [('[0.75, ' + y + ', 0.65]', _VENDOR_Q, 'ABSOLUTE'),
                      ('[0.20, 0.0, 0.0]', _IDENTITY_Q, 'RELATIVE'),
                      ('[0.0, 0.0, -0.20]', _IDENTITY_Q, 'RELATIVE')]
        output.extend(['    - body_name: "' + body + '"\n', '      data:\n'])
        for timestamp, (position, orientation, mode) in zip(('6.0', '10.0', '12.0'), points):
            output.extend(['        - timestamp: ' + timestamp + '\n',
                           '          position: ' + position + ' # x y z\n',
                           '          orientation: ' + orientation + ' # w x y z\n',
                           '          tranform_mode: "' + mode + '"\n'])
    return ''.join(output)


def build_bundle(reference, source_xml, source_yaml):
    """Return immutable support YAML/XML texts, dependency hashes and review.

    Reference fields are exactly ``version=1``, ``gap_above_surface_m=.05``,
    ``surface_height_m=.74``, the pinned predecessor bundle/goal IDs, nonempty
    ``evidence``, and ``scope=current_post_approach_box_only``. Those values pin
    this review; they are not a general robot reach envelope.

    ``tasks`` maps the two Motion paths to UTF-8 text, YAML before XML.
    ``manifest.robot_files`` maps the three dependencies plus those tasks to
    exact SHA256. No I/O, installation or execution occurs. A runner must also
    verify the predecessor's genuine result and unchanged physical reference.
    """
    config = validate_reference(reference)
    for path, source in ((SOURCE_XML_PATH, source_xml), (SOURCE_YAML_PATH, source_yaml)):
        if type(source) is not str or sha256(source) != DEPENDENCIES[path]:
            raise ValueError('Support source checksum mismatch: ' + path)
    changed_yaml = _replace_once(source_yaml, _trajectory(support=False), _trajectory(support=True))
    changed_yaml = _replace_once(changed_yaml, '  box_size: [0.6, 0.4, 0.28]',
                                '  box_size: [0.603, 0.397, 0.22]')
    xml_template = _replace_once(source_xml, 'name="wrc/put_cruzr_wrc_low"',
                                 'name="' + _TASK_TOKEN + '"')
    xml_template = _replace_once(xml_template,
        '            <Action ID="MetaClamp" name="wrc/open_arm_cruzr" />\n', '')
    template_hashes = {'yaml': sha256(changed_yaml), 'xml_template': sha256(xml_template)}
    identity = sha256(canonical(dict(builder_version=BUILDER_VERSION, reference=config,
                                     dependencies=DEPENDENCIES, content_templates=template_hashes)))
    task_name = NAMESPACE + identity + '_support'
    changed_xml = _replace_once(xml_template, _TASK_TOKEN, task_name)
    tasks = {META_ROOT + task_name + '.yaml': changed_yaml,
             TASK_ROOT + task_name + '.xml': changed_xml}
    hashes = {path: sha256(content) for path, content in tasks.items()}
    review = {
        'phase': 'support_only', 'reference': copy.deepcopy(config),
        'physical_validation': 'pending', 'automatic_execution_authorized': False,
        'installed': False, 'integrated_in_optimistic': False,
        'operator_gap_is_approximate': True, 'bounded_gap_uncertainty_m': None,
        'absolute_hand_motion_z_m': None, 'absolute_hand_z_calibration_created': False,
        'hand_mode': 'RELATIVE', 'hand_delta_at_6s_m': [0.0, 0.0, 0.0],
        'hand_delta_at_10s_m': [0.0, 0.0, 0.0],
        'final_hand_delta_z_m': -.05, 'hand_delta_xy_m': [0.0, 0.0],
        'relative_quaternion_wxyz': [1.0, 0.0, 0.0, 0.0],
        'torso_delta_at_each_point_m': [0.0, 0.0, 0.0],
        'torso_translation_weights': [0.0, 0.0, 0.0],
        'nominal_duration_s': 12.0, 'nominal_lowering_waypoint_interval_s': [10.0, 12.0],
        'contact_window_s': [10.0, 12.0], 'contact_reference_time_s': 10.0,
        'configured_collision_force_each_hand': [0.0, 0.0, 10.0, 0.0, 0.0, 0.0],
        'native_controls_preserved': True, 'support_confirmed': False,
        'pin_disengagement_confirmed': False,
        'excluded_phases': ['approach', 'pin_release_3cm', 'opening', 'navigation', 'home'],
        'assumptions_not_verified': [
            'The same held box and pose remain unchanged after the pinned successful approach.',
            'The operator-reported approximate 5 cm gap refers to the box bottom and the support surface at 0.74 m.',
            'Motion relative Z is aligned with physical vertical, and the box stays rigid relative to the hands.',
            'The entire lowering and any native force/IK adjustments clear the table, box supports and surroundings.',
            'The original collision and force settings remain appropriate for this current box and table.',
        ],
        'limitations': [
            'This is not an autorun bundle; building it neither installs files nor dispatches an action.',
            'The 6 and 10 second points request zero displacement; force control and native IK can still adjust posture.',
            'The final hand waypoint requests 5 cm down between nominal times 10 and 12; exact physical interpolation is not certified here.',
            'Torso waypoints request no translation, but zero XYZ weights do not lock the physical torso.',
            'The original collision record/start/end times [10,10,12] and positive Z force setting 10 are preserved; no support classifier is added.',
            'Action SUCCEED does not prove that the box is supported or that its pins are disengaged.',
            'No opening or further 3 cm disengagement is included; stable support requires separate physical confirmation.',
            'The approximate gap has no bounded measurement error; a residual gap or earlier contact remains possible.',
            'Repeating this relative task would request another 5 cm down; no automatic retry is authorized.',
        ],
    }
    manifest = dict(version=1, builder_version=BUILDER_VERSION, id=identity,
                    task_name=task_name, reference_sha256=sha256(canonical(config)),
                    content_template_sha256=template_hashes, dependencies=dict(DEPENDENCIES),
                    robot_files={**DEPENDENCIES, **hashes}, physical_validation='pending',
                    phase='support_only', automatic_execution_authorized=False)
    return dict(task_name=task_name, tasks=tasks, dependencies=dict(DEPENDENCIES),
                manifest=manifest, review=review)


prepare = build_bundle


def validate_bundle(bundle):
    """Reproduce the entire bundle by reversing only the pinned edit whitelist.

    This pure verifier works in-memory without ``__file__`` or original files.
    Reconstructed originals must match their pins. Rehashed changes to controls,
    trajectory, provenance or review claims cannot pass the exact comparison.
    """
    if not isinstance(bundle, dict) or set(bundle) != {
            'task_name', 'tasks', 'dependencies', 'manifest', 'review'}:
        raise ValueError('Invalid support bundle fields')
    name = bundle['task_name']
    if type(name) is not str or re.fullmatch(NAMESPACE + r'[0-9a-f]{64}_support', name) is None:
        raise ValueError('Invalid immutable support task name')
    paths = {META_ROOT + name + '.yaml', TASK_ROOT + name + '.xml'}
    tasks = bundle['tasks']
    if not isinstance(tasks, dict) or set(tasks) != paths or any(
            type(value) is not str or not value or len(value.encode('utf-8')) > 262144
            for value in tasks.values()):
        raise ValueError('Support requires exactly one bounded YAML and one XML text')
    try:
        config = validate_reference(bundle['review']['reference'])
        restored_yaml = _replace_once(tasks[META_ROOT + name + '.yaml'],
                                     _trajectory(support=True), _trajectory(support=False))
        restored_yaml = _replace_once(restored_yaml,
            '  box_size: [0.603, 0.397, 0.22]', '  box_size: [0.6, 0.4, 0.28]')
        restored_xml = _replace_once(tasks[TASK_ROOT + name + '.xml'],
            '            <Action ID="MetaClamp" name="' + name + '" />\n',
            '            <Action ID="MetaClamp" name="wrc/put_cruzr_wrc_low" />\n'
            '            <Action ID="MetaClamp" name="wrc/open_arm_cruzr" />\n')
        expected = build_bundle(config, restored_xml, restored_yaml)
        if canonical(bundle) != canonical(expected):
            raise ValueError('Support bundle differs from its exact reproducible contract')
    except (KeyError, TypeError, OverflowError) as error:
        raise ValueError('Malformed support bundle') from error
    return copy.deepcopy(expected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True, help='Local JSON with reported gap and pinned predecessor')
    parser.add_argument('--output', type=Path, required=True, help='New local directory; no overwrite or installation')
    args = parser.parse_args()
    snapshot = Path(__file__).resolve().parents[2] / 'vendor/ubtech/cruzr_s2/snapshot_20260916/motion'
    bundle = build_bundle(json.loads(args.reference.read_text()),
                          (snapshot / 'tasks/wrc_cruzr/put_cruzr_wrc_low.xml').read_text(),
                          (snapshot / 'meta_clamp/wrc/put_cruzr_wrc_low.yaml').read_text())
    args.output.mkdir(parents=True, exist_ok=False)
    for path, content in bundle['tasks'].items():
        (args.output / Path(path).name).write_text(content)
    (args.output / 'bundle.json').write_text(json.dumps(bundle, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    (args.output / 'review.json').write_text(json.dumps(bundle['review'], indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    print('OFFLINE_SUPPORT_ONLY=' + str(args.output))
    print('NO_INSTALLATION_NO_AUTORUN; opening and pin disengagement are not included.')


if __name__ == '__main__':
    main()
