"""Pure, immutable approach-only trial using the operator-assumed vendor45 datum.

This is a new supervised experiment, not a measured calibration or a qualified
deposit profile. Under the explicit same-box/grasp/layout assumption, the
vendor first hand Z .65 is translated by (.74-.45) to .94. Final descent and
opening are omitted. Native force control and IK can still adjust posture.
The builders perform no I/O. The optional CLI writes local artifacts only;
neither path connects to a robot, installs files or executes an action.
"""
import copy
from decimal import Decimal
import hashlib
import json
import math
import re

if __package__:
    from . import scenario1_deposit as deposit
else:
    import scenario1_deposit as deposit


BUILDER_VERSION = 1
PHASE = 'approach_vendor_reference'
NAMESPACE = 'local_table74_current/'
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
_REFERENCE_KEYS = {'version', 'mode', 'source_checkpoint_sha256', 'surface_height_m',
                   'reference_surface_height_m', 'scope', 'evidence'}
_TASK_TOKEN = '__TABLE74_CURRENT_APPROACH_TASK_NAME__'
_ORIGINAL_DESCENT = '          position: [0.0, 0.0, -0.20] # x y z'
_HOLD = '          position: [0.0, 0.0, 0.0] # x y z'


def sha256(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False)


def validate_reference(reference):
    """Normalize an explicit assumption, never upgrade it to a measurement.

    The runner must independently compare source_checkpoint_sha256 with its
    genuine clean held-box put1 source. Including that hash here binds the
    immutable candidate to its source; this pure parser cannot authenticate it.
    """
    if not isinstance(reference, dict) or set(reference) != _REFERENCE_KEYS:
        raise ValueError('Current table74 reference: missing or unknown fields')
    if type(reference['version']) is not int or reference['version'] != 1:
        raise ValueError('Unsupported current table74 reference version')
    if reference['mode'] != 'operator_assumed_vendor45' or reference['scope'] != 'current_held_put1_only':
        raise ValueError('Current table74 trial requires the explicit vendor45 assumption and held-put1 scope')
    source_hash = reference['source_checkpoint_sha256']
    if type(source_hash) is not str or re.fullmatch('[0-9a-f]{64}', source_hash) is None:
        raise ValueError('Current table74 source checkpoint hash is invalid')
    if type(reference['evidence']) is not str or not reference['evidence'].strip() or len(reference['evidence']) > 4096:
        raise ValueError('Current table74 requires bounded, explicit operator assumption evidence')
    result = copy.deepcopy(reference)
    for name, expected in (('surface_height_m', .74), ('reference_surface_height_m', .45)):
        value = reference[name]
        try:
            valid = type(value) in (int, float) and math.isfinite(value) and value == expected
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError(name+': this trial is pinned to .74 m from assumed vendor .45 m')
        result[name] = float(value)
    return result


def _replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Pinned current table74 source structure changed')
    return text.replace(old, new, 1)


def build_bundle(reference, source_xml, source_yaml):
    """Build two additive files; all unlisted source bytes remain unchanged.

    Allowed edits are two first absolute hand Z values, the three final hand/
    torso descents replaced by zero, task redirection and removal of opening.
    X/Y, orientation, torso's earlier waypoints, box_size, force/collision
    controls, task stack and timing retain the pinned vendor source bytes.
    """
    config = validate_reference(reference)
    for path, source in ((SOURCE_XML_PATH, source_xml), (SOURCE_YAML_PATH, source_yaml)):
        if type(source) is not str or sha256(source) != DEPENDENCIES[path]:
            raise ValueError('Current table74 source checksum mismatch: '+path)
    delta = Decimal(str(config['surface_height_m']))-Decimal(str(config['reference_surface_height_m']))
    approach_z = Decimal('0.65')+delta
    if delta != Decimal('.29') or approach_z != Decimal('.94'):
        raise ValueError('Current table74 nominal translation changed')
    changed_yaml = source_yaml
    for lateral in ('0.285', '-0.285'):
        changed_yaml = _replace_once(changed_yaml,
            '          position: [0.75, '+lateral+', 0.65] # x y z',
            '          position: [0.75, '+lateral+', 0.94] # x y z')
    if changed_yaml.count(_ORIGINAL_DESCENT) != 3 or _HOLD in changed_yaml:
        raise ValueError('Expected exactly three original final descents and no preexisting hold')
    changed_yaml = changed_yaml.replace(_ORIGINAL_DESCENT, _HOLD)
    xml_template = _replace_once(source_xml, 'name="wrc/put_cruzr_wrc_low"',
                                 'name="'+_TASK_TOKEN+'"')
    xml_template = _replace_once(xml_template,
        '            <Action ID="MetaClamp" name="wrc/open_arm_cruzr" />\n', '')
    template_hashes = {'yaml': sha256(changed_yaml), 'xml_template': sha256(xml_template)}
    identity = sha256(canonical(dict(builder_version=BUILDER_VERSION, phase=PHASE,
        reference=config, dependencies=DEPENDENCIES, content_templates=template_hashes)))
    task_name = NAMESPACE+identity+'_approach'
    changed_xml = _replace_once(xml_template, _TASK_TOKEN, task_name)
    tasks = {META_ROOT+task_name+'.yaml': changed_yaml, TASK_ROOT+task_name+'.xml': changed_xml}
    hashes = {path: sha256(content) for path, content in tasks.items()}
    review = dict(phase=PHASE, reference=copy.deepcopy(config),
        reference_kind='operator_assumption_not_measurement', source_vendor45_assumed=True,
        physical_validation='pending', kinematic_validation='pending',
        automatic_execution_authorized=False, installed=False, integrated_in_optimistic=False,
        measured_calibration_created=False, support_confirmed=False, pin_disengagement_confirmed=False,
        nominal_height_translation_m=.29, first_hand_absolute_z_m=.94,
        first_hand_absolute_x_m=.75, first_hand_absolute_y_m={'left': .285, 'right': -.285},
        first_hand_quaternion_wxyz=[.5, .5, .5, -.5], first_hand_mode='ABSOLUTE',
        following_hand_delta_x_m=.20, final_hand_delta_z_m=0., final_torso_delta_z_m=0.,
        nominal_precontact_clearance_m=.20, nominal_target_box_bottom_above_floor_m=.94,
        nominal_duration_s=12., source_box_size_unchanged_m=[.6, .4, .28],
        native_controls_preserved=True, original_contact_window_s=[10., 12.],
        excluded_phases=['final_20cm_lowering', 'table_support', 'pin_release', 'opening', 'navigation', 'home'],
        assumptions_not_verified=[
            'The vendor45 reference remains applicable to this same physical box, clamps, grasp and horizontal layout.',
            'The unchanged absolute hand XY/orientations, earlier torso motion and 20 cm forward segment clear the actual table and surroundings.',
            'The internal hand Z translation produces the same physical height translation of the rigidly held box.',
            'The nominal 20 cm clearance describes an assumed recipe, not a measured current gap or a guaranteed clearance.',
        ], limitations=[
            'The source checkpoint hash must match the genuine clean held-put1 source in a separately checked runner.',
            'No complete deposit profile is enabled or physically qualified by this candidate.',
            'The first absolute waypoint can change hand XYZ and orientation; zero final descent does not make the earlier path stationary.',
            'Native IK and retained force/admittance control can adjust posture despite zero final translation requests.',
            'The original contact window only covers nominal times 10 to 12 seconds; earlier table contact is not covered by that window.',
            'Successful action completion would not establish table support, pin clearance or safe release.',
            'A later support trial requires a new measured or explicitly reviewed gap and a genuine successful predecessor.',
            'No automatic retry, opening or HOME is part of this phase.',
        ])
    manifest = dict(version=1, builder_version=BUILDER_VERSION, id=identity, phase=PHASE,
        task_name=task_name, reference_sha256=sha256(canonical(config)),
        content_template_sha256=template_hashes, dependencies=dict(DEPENDENCIES),
        robot_files={**DEPENDENCIES, **hashes}, physical_validation='pending',
        automatic_execution_authorized=False)
    return dict(task_name=task_name, tasks=tasks, dependencies=dict(DEPENDENCIES),
                manifest=manifest, review=review)


prepare = build_bundle


def validate_bundle(bundle):
    """Reverse only the exact edit whitelist and reproduce the complete bundle.

    No source file, __file__, network or native library load is needed. Extra
    changes remain invalid even if someone recomputes every manifest hash.
    """
    if not isinstance(bundle, dict) or set(bundle) != {'task_name', 'tasks', 'dependencies', 'manifest', 'review'}:
        raise ValueError('Invalid current table74 bundle fields')
    name = bundle['task_name']
    if type(name) is not str or re.fullmatch(NAMESPACE+r'[0-9a-f]{64}_approach', name) is None:
        raise ValueError('Invalid immutable current table74 task name')
    tasks = bundle['tasks']
    paths = {META_ROOT+name+'.yaml', TASK_ROOT+name+'.xml'}
    if not isinstance(tasks, dict) or set(tasks) != paths or any(
            type(text) is not str or not text or len(text.encode()) > 262144 for text in tasks.values()):
        raise ValueError('Current table74 requires exactly one bounded YAML and XML')
    try:
        config = validate_reference(bundle['review']['reference'])
        restored_yaml = tasks[META_ROOT+name+'.yaml']
        for lateral in ('0.285', '-0.285'):
            restored_yaml = _replace_once(restored_yaml,
                '          position: [0.75, '+lateral+', 0.94] # x y z',
                '          position: [0.75, '+lateral+', 0.65] # x y z')
        if restored_yaml.count(_HOLD) != 3:
            raise ValueError('Current table74 must preserve exactly three final holds')
        restored_yaml = restored_yaml.replace(_HOLD, _ORIGINAL_DESCENT)
        restored_xml = _replace_once(tasks[TASK_ROOT+name+'.xml'],
            '            <Action ID="MetaClamp" name="'+name+'" />\n',
            '            <Action ID="MetaClamp" name="wrc/put_cruzr_wrc_low" />\n'
            '            <Action ID="MetaClamp" name="wrc/open_arm_cruzr" />\n')
        expected = build_bundle(config, restored_xml, restored_yaml)
        if canonical(bundle) != canonical(expected):
            raise ValueError('Current table74 bundle differs from its exact reproducible contract')
    except (KeyError, TypeError, OverflowError) as exc:
        raise ValueError('Malformed current table74 bundle') from exc
    return copy.deepcopy(expected)


def main(argv=None):
    """Save reproducible local review files in a new directory; never install."""
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True,
                        help='Explicit current operator-assumed vendor45 reference JSON')
    parser.add_argument('--output', type=Path, required=True,
                        help='New local directory; no overwrite, installation or execution')
    args = parser.parse_args(argv)
    snapshot = Path(__file__).resolve().parents[2]/'vendor/ubtech/cruzr_s2/snapshot_20260916/motion'
    bundle = build_bundle(json.loads(args.reference.read_text()),
        (snapshot/'tasks/wrc_cruzr/put_cruzr_wrc_low.xml').read_text(),
        (snapshot/'meta_clamp/wrc/put_cruzr_wrc_low.yaml').read_text())
    validate_bundle(bundle)
    args.output.mkdir(parents=True, exist_ok=False, mode=0o700)
    for path, content in bundle['tasks'].items():
        with (args.output/Path(path).name).open('x') as stream:
            stream.write(content)
    for name, value in (('bundle.json', bundle), ('review.json', bundle['review'])):
        with (args.output/name).open('x') as stream:
            stream.write(json.dumps(value, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(dict(status='PREPARED_LOCALLY_NOT_INSTALLED_OR_EXECUTED',
                         task_name=bundle['task_name'], output=str(args.output))))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
