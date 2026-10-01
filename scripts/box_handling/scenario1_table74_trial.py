#!/usr/bin/env python3
"""Build an offline, immutable APPROACH-ONLY trial; never install or run it.

The height difference uses an approximate operator measurement of this held
box in its unchanged post-grasp posture. It is not an absolute Motion hand-Z
calibration and cannot be reused for other grasps without a new reference.
The mixed native mode fixes XY and orientation while adding the requested Z
to the previous hand Z. Its static binary review is not a physical validation.
No final lowering, opening, release, navigation or HOME is included.
"""
import argparse
import copy
from decimal import Decimal
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
NAMESPACE = 'local_table74_trial/'
TASK_ROOT = deposit.TASK_ROOT
META_ROOT = deposit.META_ROOT
SOURCE_XML_PATH = deposit.SOURCE_XML_PATH
SOURCE_YAML_PATH = deposit.SOURCE_YAML_PATH
META_CLAMP_PATH = '/opt/walker/manipulation_meta_tasks/lib/libmeta_clamp.so'
META_CLAMP_SHA256 = 'd6bc61a493f7d790150fdbd673108121f46589fef56620de4a9023dcc2ba520a'
BINARY_SHA = META_CLAMP_SHA256
DEPENDENCIES = {
    deposit.SOURCE_XML_PATH: deposit.SOURCE_HASHES[deposit.SOURCE_XML_PATH],
    deposit.SOURCE_YAML_PATH: deposit.SOURCE_HASHES[deposit.SOURCE_YAML_PATH],
    META_CLAMP_PATH: META_CLAMP_SHA256,
}
_REFERENCE_KEYS = {'version', 'box_bottom_above_floor_m', 'surface_height_m',
                   'precontact_clearance_m', 'evidence', 'scope'}
_TASK_TOKEN = '__TABLE74_APPROACH_TASK_NAME__'


def sha256(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False)


def validate_reference(reference):
    """Pin this trial to its reviewed measurement, not a physical reach envelope."""
    if not isinstance(reference, dict) or set(reference) != _REFERENCE_KEYS:
        raise ValueError('Trial reference: missing or unknown fields')
    if type(reference['version']) is not int or reference['version'] != 1:
        raise ValueError('Unsupported trial reference version')
    if reference['scope'] != 'current_post_grasp_box_only':
        raise ValueError('Trial reference is limited to this unchanged held box')
    if type(reference['evidence']) is not str or not reference['evidence'].strip():
        raise ValueError('Trial requires an explicit operator measurement evidence reference')
    result = copy.deepcopy(reference)
    for name in ('box_bottom_above_floor_m', 'surface_height_m', 'precontact_clearance_m'):
        value = reference[name]
        try:
            valid = type(value) in (int, float) and math.isfinite(value) and value > 0
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError(name + ': expected a positive finite number')
        result[name] = float(value)
    if result['surface_height_m'] != .74 or result['precontact_clearance_m'] != .05:
        raise ValueError('This trial is scoped to a 0.74 m table and 0.05 m precontact clearance')
    if result['box_bottom_above_floor_m'] != 1.10:
        raise ValueError('This trial requires the current 1.10 m box reference; another value requires a new review')
    return result


def _replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError('Pinned approach source structure changed')
    return text.replace(before, after, 1)


def build_bundle(reference, source_xml, source_yaml):
    """Return task texts, exact dependencies, manifest and an unverified review.

    ``tasks`` maps two immutable Motion destination paths to UTF-8 text, YAML
    before XML. These are artifacts only: this function performs no I/O and
    authorizes no execution. A future caller must independently check the robot,
    reference continuity, environment and exact dependency hashes.

    Identity covers normalized reference values and provenance, dependency pins,
    the final YAML bytes, and XML template bytes before insertion of that ID.
    The manifest additionally hashes both completed file contents.
    """
    config = validate_reference(reference)
    for path, source in ((deposit.SOURCE_XML_PATH, source_xml),
                         (deposit.SOURCE_YAML_PATH, source_yaml)):
        if type(source) is not str or sha256(source) != DEPENDENCIES[path]:
            raise ValueError('Trial source checksum mismatch: ' + path)
    target_base = Decimal(str(config['surface_height_m'])) + Decimal(str(config['precontact_clearance_m']))
    delta = target_base - Decimal(str(config['box_bottom_above_floor_m']))
    delta_z = float(delta)
    if not math.isfinite(delta_z):
        raise ValueError('Trial height difference must remain finite')
    changed_yaml = source_yaml
    for y in ('0.285', '-0.285'):
        before = ('          position: [0.75, ' + y + ', 0.65] # x y z\n'
                  '          orientation: [0.5, 0.5, 0.5, -0.5] # w x y z\n'
                  '          tranform_mode: "ABSOLUTE"')
        after = ('          position: [0.75, ' + y + ', ' + repr(delta_z) + '] # x y z\n'
                 '          orientation: [0.5, 0.5, 0.5, -0.5] # w x y z\n'
                 '          tranform_mode: "Z_REL_XYRPY_ABSOLUTE"')
        changed_yaml = _replace_once(changed_yaml, before, after)
    descent = '          position: [0.0, 0.0, -0.20] # x y z'
    if changed_yaml.count(descent) != 3:
        raise ValueError('Expected exactly two final hand descents and one torso descent')
    changed_yaml = changed_yaml.replace(descent, '          position: [0.0, 0.0, 0.0] # x y z')
    changed_yaml = _replace_once(changed_yaml, '  box_size: [0.6, 0.4, 0.28]',
                                '  box_size: [0.603, 0.397, 0.22]')
    xml_template = _replace_once(source_xml, 'name="wrc/put_cruzr_wrc_low"',
                                 'name="' + _TASK_TOKEN + '"')
    xml_template = _replace_once(xml_template,
        '            <Action ID="MetaClamp" name="wrc/open_arm_cruzr" />\n', '')
    template_hashes = {'yaml': sha256(changed_yaml), 'xml_template': sha256(xml_template)}
    identity = sha256(canonical(dict(builder_version=BUILDER_VERSION, reference=config,
                                     dependencies=DEPENDENCIES, content_templates=template_hashes)))
    task_name = NAMESPACE + identity + '_approach'
    changed_xml = _replace_once(xml_template, _TASK_TOKEN, task_name)
    tasks = {deposit.META_ROOT + task_name + '.yaml': changed_yaml,
             deposit.TASK_ROOT + task_name + '.xml': changed_xml}
    hashes = {path: sha256(content) for path, content in tasks.items()}
    review = {
        'phase': 'approach_only', 'reference': copy.deepcopy(config),
        'physical_validation': 'pending', 'automatic_execution_authorized': False,
        'installed': False, 'integrated_in_optimistic': False,
        'operator_box_height_is_approximate': True, 'bounded_height_uncertainty_m': None,
        'absolute_hand_motion_z_m': None, 'absolute_hand_z_calibration_created': False,
        'nominal_target_box_bottom_above_floor_m': float(target_base),
        'first_hand_delta_z_m': delta_z, 'first_hand_absolute_x_m': .75,
        'first_hand_absolute_y_m': {'left': .285, 'right': -.285},
        'first_hand_absolute_quaternion_wxyz': [.5, .5, .5, -.5],
        'first_hand_mode': 'Z_REL_XYRPY_ABSOLUTE',
        'following_hand_delta_x_m': .20, 'final_hand_delta_z_m': 0.0,
        'final_torso_delta_z_m': 0.0, 'nominal_duration_s': 12.0,
        'native_mode_evidence': 'Static archived binary review: handler 0xfeed0, dispatch 0x111990; no physical trial.',
        'excluded_phases': ['final_5cm_lowering', 'pin_release_3cm', 'opening', 'navigation', 'home'],
        'assumptions_not_verified': [
            'The same box, grasp, posture and reported floor-height reference remain valid at dispatch, including after transport.',
            'The held box stays rigid relative to the tools and its orientation matches the vendor absolute hand orientations.',
            'Motion relative Z is parallel to physical gravity and the floor reference is unchanged.',
            'The entire diagonal approach, torso motion and subsequent 0.20 m advance clear the surroundings.',
            'The approximate height measurement leaves sufficient clearance above the table throughout the approach.',
        ],
        'limitations': [
            'This is not an autorun bundle; building it neither installs files nor dispatches an action.',
            'The native mixed mode preserves only relative Z; it sets XY and orientation absolutely.',
            'The original torso targets at 6 and 10 seconds and all native force/contact controls remain.',
            'The original contact window is 10 to 12 seconds; it does not cover an earlier table impact.',
            'Zero final descent and action success do not prove table support or pin disengagement.',
            'No physical height/reach envelope or measurement error bound has been invented.',
            'The 1.10 m reference is pinned to this reviewed trial; another measured height requires a new review.',
            'Repetition from the resulting pose would apply the relative descent again; this is not an idempotent task.',
        ],
    }
    manifest = dict(version=1, builder_version=BUILDER_VERSION, id=identity,
                    task_name=task_name, reference_sha256=sha256(canonical(config)),
                    content_template_sha256=template_hashes, dependencies=dict(DEPENDENCIES),
                    robot_files={**DEPENDENCIES, **hashes}, physical_validation='pending',
                    phase='approach_only', automatic_execution_authorized=False)
    return dict(task_name=task_name, tasks=tasks, dependencies=dict(DEPENDENCIES),
                manifest=manifest, review=review)


prepare = build_bundle


def validate_bundle(bundle):
    """Purely verify every byte against pinned originals, returning a deep copy.

    Reverse only the builder's allowed edits, verify the recovered source
    checksums, then reproduce and compare the complete bundle. No filesystem,
    network or ``__file__`` access is required, including for an in-memory
    runtime. Exact comparison covers provenance, immutable names and review
    statements; recomputing a hash cannot authorize an additional trajectory.
    """
    if not isinstance(bundle, dict) or set(bundle) != {
            'task_name', 'tasks', 'dependencies', 'manifest', 'review'}:
        raise ValueError('Invalid trial bundle fields')
    name = bundle['task_name']
    if type(name) is not str or re.fullmatch(NAMESPACE + r'[0-9a-f]{64}_approach', name) is None:
        raise ValueError('Invalid immutable approach task name')
    paths = {META_ROOT + name + '.yaml', TASK_ROOT + name + '.xml'}
    tasks = bundle['tasks']
    if not isinstance(tasks, dict) or set(tasks) != paths or any(
            type(value) is not str or not value or len(value.encode('utf-8')) > 262144
            for value in tasks.values()):
        raise ValueError('Trial requires exactly one YAML and one XML with bounded text content')
    try:
        config = validate_reference(bundle['review']['reference'])
        delta_z = float(Decimal(str(config['surface_height_m'])) +
                        Decimal(str(config['precontact_clearance_m'])) -
                        Decimal(str(config['box_bottom_above_floor_m'])))
        restored_yaml = tasks[META_ROOT + name + '.yaml']
        for y in ('0.285', '-0.285'):
            changed = ('          position: [0.75, ' + y + ', ' + repr(delta_z) + '] # x y z\n'
                       '          orientation: [0.5, 0.5, 0.5, -0.5] # w x y z\n'
                       '          tranform_mode: "Z_REL_XYRPY_ABSOLUTE"')
            original = ('          position: [0.75, ' + y + ', 0.65] # x y z\n'
                        '          orientation: [0.5, 0.5, 0.5, -0.5] # w x y z\n'
                        '          tranform_mode: "ABSOLUTE"')
            restored_yaml = _replace_once(restored_yaml, changed, original)
        zero = '          position: [0.0, 0.0, 0.0] # x y z'
        if restored_yaml.count(zero) != 3:
            raise ValueError('Trial must retain exactly three final zero-displacement points')
        restored_yaml = restored_yaml.replace(zero, '          position: [0.0, 0.0, -0.20] # x y z')
        restored_yaml = _replace_once(restored_yaml,
            '  box_size: [0.603, 0.397, 0.22]', '  box_size: [0.6, 0.4, 0.28]')
        restored_xml = _replace_once(tasks[TASK_ROOT + name + '.xml'],
            '            <Action ID="MetaClamp" name="' + name + '" />\n',
            '            <Action ID="MetaClamp" name="wrc/put_cruzr_wrc_low" />\n'
            '            <Action ID="MetaClamp" name="wrc/open_arm_cruzr" />\n')
        expected = build_bundle(config, restored_xml, restored_yaml)
        if canonical(bundle) != canonical(expected):
            raise ValueError('Trial bundle does not match its exact reproducible approach contract')
    except (KeyError, TypeError, OverflowError) as error:
        raise ValueError('Malformed trial bundle') from error
    return copy.deepcopy(expected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True, help='Local JSON with the reported measurement and scope')
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
    print('OFFLINE_APPROACH_ONLY=' + str(args.output))
    print('NO_INSTALLATION_NO_AUTORUN; support and release are not included.')


if __name__ == '__main__':
    main()
