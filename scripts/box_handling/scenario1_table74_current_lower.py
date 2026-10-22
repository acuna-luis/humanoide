"""Immutable relative lowering phases after a genuine current table74 trial.

The operator reports a current gap: precontact .19 -> .05 m, or support .05
-> 0 m. Neither nominal subtraction nor native action success proves support.
Builders are pure. The CLI writes local artifacts only, without robot access,
installation, mode changes, opening, HOME or automatic retries.
"""
import copy
from decimal import Decimal
import hashlib
import json
import math
import re
import uuid

if __package__:
    from . import scenario1_deposit as deposit
else:
    import scenario1_deposit as deposit


BUILDER_VERSION = 1
PHASE = 'current_relative_lowering'
NAMESPACE = 'local_table74_lower/'
TASK_ROOT = deposit.TASK_ROOT
META_ROOT = deposit.META_ROOT
SOURCE_XML_PATH = deposit.SOURCE_XML_PATH
SOURCE_YAML_PATH = deposit.SOURCE_YAML_PATH
META_CLAMP_PATH = '/opt/walker/manipulation_meta_tasks/lib/libmeta_clamp.so'
META_CLAMP_SHA256 = 'd6bc61a493f7d790150fdbd673108121f46589fef56620de4a9023dcc2ba520a'
BINARY_SHA = META_CLAMP_SHA256
DEPENDENCIES = {
    SOURCE_XML_PATH: deposit.SOURCE_HASHES[SOURCE_XML_PATH],
    SOURCE_YAML_PATH: deposit.SOURCE_HASHES[SOURCE_YAML_PATH],
    META_CLAMP_PATH: META_CLAMP_SHA256,
}
_REFERENCE_KEYS = {'version', 'stage', 'gap_above_surface_m', 'target_clearance_m',
                   'surface_height_m', 'predecessor_bundle_id', 'predecessor_goal_id',
                   'evidence', 'scope'}
_PAIRS = {'precontact': (.19, .05), 'support': (.05, 0.)}
_IDENTITY_Q = '[1.0, 0.0, 0.0, 0.0]'
_VENDOR_Q = '[0.5, 0.5, 0.5, -0.5]'
_ZERO = '[0.0, 0.0, 0.0]'
_TASK_TOKEN = '__TABLE74_CURRENT_LOWER_TASK_NAME__'


def sha256(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def validate_reference(reference):
    """Pin one of two reviewed relative phases and its actual predecessor.

    This parser cannot authenticate the operator measurement or predecessor
    journal. A runner must verify both identities, continuity of current pose,
    source context and the genuine native result before admitting a new phase.
    """
    if not isinstance(reference, dict) or set(reference) != _REFERENCE_KEYS:
        raise ValueError('Current lowering reference: missing or unknown fields')
    if type(reference['version']) is not int or reference['version'] != 1:
        raise ValueError('Unsupported current lowering reference version')
    stage = reference['stage']
    if type(stage) is not str or stage not in _PAIRS or reference['scope'] != 'current_post_trial_box_only':
        raise ValueError('Current lowering requires an explicit precontact/support stage and current-post-trial scope')
    if (type(reference['predecessor_bundle_id']) is not str or
            re.fullmatch('[0-9a-f]{64}', reference['predecessor_bundle_id']) is None):
        raise ValueError('Current lowering predecessor bundle ID is invalid')
    goal = reference['predecessor_goal_id']
    try:
        parsed = uuid.UUID(goal)
        if type(goal) is not str or str(parsed) != goal or parsed.int == 0:
            raise ValueError
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError('Current lowering predecessor requires a canonical nonzero UUID') from exc
    if type(reference['evidence']) is not str or not reference['evidence'].strip() or len(reference['evidence']) > 4096:
        raise ValueError('Current lowering requires explicit bounded operator measurement evidence')
    gap, target = _PAIRS[stage]
    result = copy.deepcopy(reference)
    for name, expected in (('surface_height_m', .74), ('gap_above_surface_m', gap),
                           ('target_clearance_m', target)):
        value = reference[name]
        try:
            valid = type(value) in (int, float) and math.isfinite(value) and value == expected
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError(name+': outside the exact reviewed '+stage+' pair')
        result[name] = float(value)
    return result


def _replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Pinned current lowering source structure changed')
    return text.replace(old, new, 1)


def _trajectory(*, lowering, delta_z=None):
    """Exact legacy support layout, with a phase-specific final hand delta."""
    output = ['  robot_trajectory_data:\n']
    for body in ('left_hand', 'right_hand', 'torso'):
        if lowering:
            final = _ZERO if body == 'torso' else '[0.0, 0.0, '+repr(delta_z)+']'
            points = [(_ZERO, _IDENTITY_Q, 'RELATIVE'),
                      (_ZERO, _IDENTITY_Q, 'RELATIVE'), (final, _IDENTITY_Q, 'RELATIVE')]
        elif body == 'torso':
            points = [('[0.0, 0.0, 1.2]', _IDENTITY_Q, 'ABSOLUTE'),
                      ('[0.30, 0, 1.2]', _IDENTITY_Q, 'ABSOLUTE'),
                      ('[0.0, 0.0, -0.20]', _IDENTITY_Q, 'RELATIVE')]
        else:
            lateral = '0.285' if body == 'left_hand' else '-0.285'
            points = [('[0.75, '+lateral+', 0.65]', _VENDOR_Q, 'ABSOLUTE'),
                      ('[0.20, 0.0, 0.0]', _IDENTITY_Q, 'RELATIVE'),
                      ('[0.0, 0.0, -0.20]', _IDENTITY_Q, 'RELATIVE')]
        output.extend(['    - body_name: "'+body+'"\n', '      data:\n'])
        for stamp, (position, orientation, mode) in zip(('6.0', '10.0', '12.0'), points):
            output.extend(['        - timestamp: '+stamp+'\n',
                           '          position: '+position+' # x y z\n',
                           '          orientation: '+orientation+' # w x y z\n',
                           '          tranform_mode: "'+mode+'"\n'])
    return ''.join(output)


def build_bundle(reference, source_xml, source_yaml):
    """Return phase files and review, preserving every byte outside trajectory/XML.

    The native force/collision settings, box_size, stack, weights and duration
    remain unchanged. Requested hand XY and rotations are zero/identity; zero
    torso waypoints do not constitute a physical torso lock under native IK.
    """
    config = validate_reference(reference)
    for path, source in ((SOURCE_XML_PATH, source_xml), (SOURCE_YAML_PATH, source_yaml)):
        if type(source) is not str or sha256(source) != DEPENDENCIES[path]:
            raise ValueError('Current lowering source checksum mismatch: '+path)
    delta = float(Decimal(str(config['target_clearance_m']))-Decimal(str(config['gap_above_surface_m'])))
    expected_delta = -.14 if config['stage'] == 'precontact' else -.05
    if delta != expected_delta:
        raise ValueError('Current lowering nominal subtraction changed')
    changed_yaml = _replace_once(source_yaml, _trajectory(lowering=False),
                                 _trajectory(lowering=True, delta_z=delta))
    xml_template = _replace_once(source_xml, 'name="wrc/put_cruzr_wrc_low"', 'name="'+_TASK_TOKEN+'"')
    xml_template = _replace_once(xml_template,
        '            <Action ID="MetaClamp" name="wrc/open_arm_cruzr" />\n', '')
    template_hashes = {'yaml': sha256(changed_yaml), 'xml_template': sha256(xml_template)}
    identity = sha256(canonical(dict(builder_version=BUILDER_VERSION, phase=PHASE,
        reference=config, dependencies=DEPENDENCIES, content_templates=template_hashes)))
    task_name = NAMESPACE+identity+'_lower'
    changed_xml = _replace_once(xml_template, _TASK_TOKEN, task_name)
    tasks = {META_ROOT+task_name+'.yaml': changed_yaml, TASK_ROOT+task_name+'.xml': changed_xml}
    hashes = {path: sha256(content) for path, content in tasks.items()}
    review = dict(phase=PHASE, reference=copy.deepcopy(config),
        reference_kind='operator_reported_current_gap_not_absolute_hand_calibration',
        physical_validation='pending', kinematic_validation='pending',
        automatic_execution_authorized=False, installed=False, integrated_in_optimistic=False,
        measured_absolute_calibration_created=False, physical_support_confirmed=False,
        pin_disengagement_confirmed=False, lower_delta_z_m=delta,
        nominal_target_clearance_m=config['target_clearance_m'],
        hand_mode='RELATIVE', hand_delta_at_6s_m=[0., 0., 0.], hand_delta_at_10s_m=[0., 0., 0.],
        final_hand_delta_m=[0., 0., delta], hand_delta_xy_m=[0., 0.],
        relative_quaternion_wxyz=[1., 0., 0., 0.], torso_delta_at_each_point_m=[0., 0., 0.],
        nominal_duration_s=12., nominal_lowering_waypoint_interval_s=[10., 12.],
        source_box_size_unchanged_m=[.6, .4, .28], native_controls_preserved=True,
        contact_window_s=[10., 12.], contact_reference_time_s=10.,
        configured_collision_force_each_hand=[0., 0., 10., 0., 0., 0.],
        excluded_phases=['approach', 'pin_release', 'opening', 'navigation', 'home'],
        assumptions_not_verified=[
            'The same held box, hand attachment and pose are unchanged from the genuine successful predecessor.',
            'The current gap report applies to both sides of the horizontal box over the stable table.',
            'Motion relative Z is parallel to physical vertical and the box remains rigid relative to its tools.',
            'The complete lowering and native force/IK adjustments clear the actual table and surroundings.',
        ], limitations=[
            'A runner must verify the exact predecessor bundle, native UUID, terminal result and unchanged source context.',
            'The reported gap has no bounded measurement uncertainty; the subtraction is a requested nominal trial.',
            'The 6 and 10 second points request zero displacement; native force/IK can still adjust posture.',
            'The final hand waypoint requests lowering between nominal times 10 and 12; exact physical interpolation and peak velocity are not certified here.',
            'Torso translation requests remain zero, which does not mechanically lock the torso.',
            'Action SUCCEED neither proves table support nor authorizes release, opening or HOME.',
            'Precontact must be followed by a new gap/position confirmation; support requires its own genuine successful predecessor.',
            'No pin relief or lateral opening is included; support must be physically confirmed before any later release task.',
            'Repeating this relative phase would lower the hands again; no automatic retry is authorized.',
        ])
    manifest = dict(version=1, builder_version=BUILDER_VERSION, id=identity, phase=PHASE,
        task_name=task_name, reference_sha256=sha256(canonical(config)),
        content_template_sha256=template_hashes, dependencies=dict(DEPENDENCIES),
        robot_files={**DEPENDENCIES, **hashes}, physical_validation='pending', automatic_execution_authorized=False)
    return dict(task_name=task_name, tasks=tasks, dependencies=dict(DEPENDENCIES), manifest=manifest, review=review)


prepare = build_bundle


def validate_bundle(bundle):
    """Reproduce the complete candidate in memory, rejecting rehashed tampering."""
    if not isinstance(bundle, dict) or set(bundle) != {'task_name', 'tasks', 'dependencies', 'manifest', 'review'}:
        raise ValueError('Invalid current lowering bundle fields')
    name = bundle['task_name']
    if type(name) is not str or re.fullmatch(NAMESPACE+r'[0-9a-f]{64}_lower', name) is None:
        raise ValueError('Invalid immutable current lowering task name')
    paths = {META_ROOT+name+'.yaml', TASK_ROOT+name+'.xml'}
    tasks = bundle['tasks']
    if not isinstance(tasks, dict) or set(tasks) != paths or any(
            type(text) is not str or not text or len(text.encode()) > 262144 for text in tasks.values()):
        raise ValueError('Current lowering requires exactly one bounded YAML and XML')
    try:
        config = validate_reference(bundle['review']['reference'])
        delta = float(Decimal(str(config['target_clearance_m']))-Decimal(str(config['gap_above_surface_m'])))
        source_yaml = _replace_once(tasks[META_ROOT+name+'.yaml'],
            _trajectory(lowering=True, delta_z=delta), _trajectory(lowering=False))
        source_xml = _replace_once(tasks[TASK_ROOT+name+'.xml'],
            '            <Action ID="MetaClamp" name="'+name+'" />\n',
            '            <Action ID="MetaClamp" name="wrc/put_cruzr_wrc_low" />\n'
            '            <Action ID="MetaClamp" name="wrc/open_arm_cruzr" />\n')
        expected = build_bundle(config, source_xml, source_yaml)
        if canonical(bundle) != canonical(expected):
            raise ValueError('Current lowering bundle differs from its exact reproducible contract')
    except (KeyError, TypeError, OverflowError) as exc:
        raise ValueError('Malformed current lowering bundle') from exc
    return copy.deepcopy(expected)


def main(argv=None):
    """Write local review artifacts to a new directory; never install or move."""
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='New local directory; no overwrite or installation')
    args = parser.parse_args(argv)
    snapshot = Path(__file__).resolve().parents[2]/'vendor/ubtech/cruzr_s2/snapshot_20260916/motion'
    bundle = build_bundle(json.loads(args.reference.read_text()),
        (snapshot/'tasks/wrc_cruzr/put_cruzr_wrc_low.xml').read_text(),
        (snapshot/'meta_clamp/wrc/put_cruzr_wrc_low.yaml').read_text())
    validate_bundle(bundle)
    args.output.mkdir(parents=True, exist_ok=False, mode=0o700)
    for path, text in bundle['tasks'].items():
        with (args.output/Path(path).name).open('x') as stream:
            stream.write(text)
    for name, value in (('bundle.json', bundle), ('review.json', bundle['review'])):
        with (args.output/name).open('x') as stream:
            stream.write(json.dumps(value, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(dict(status='PREPARED_LOCALLY_NOT_INSTALLED_OR_EXECUTED',
                         task_name=bundle['task_name'], stage=bundle['review']['reference']['stage'],
                         lower_delta_z_m=bundle['review']['lower_delta_z_m'], output=str(args.output))))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
