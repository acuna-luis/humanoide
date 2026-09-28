"""Pure geometry review and immutable WRC deposit bundle construction.

``ready`` means that the required geometry record and explicit review flags are
complete, not that motion, reach, support, calibration evidence or release have
been physically validated. The parser cannot authenticate the evidence record.
The measured-hand reference combines the measured box-bottom height above the
floor with both measured hand Z coordinates in Motion, from the same horizontal
held box and the retained vendor hand orientations. Alternatively, an explicitly
reviewed vendor-final reference records the box-bottom height only AFTER the
original WRC final hand position has actually been reached with the box held.
An early contact stop or SUCCEED result alone does not establish that condition.
Commanded targets are not measured poses. Neither reference is inferred from box
dimensions, a ROS frame name or a previous robot configuration.
``surface_height_m`` is the editable destination height above the floor; changing
it alone never supplies missing calibration or validates a different site.

Only the two first hand Z coordinates and deposit box_size are changed. The
original torso, approach X, 0.20 m descent, force/collision controls and opening
are retained. This module performs no I/O and sends no robot commands.
"""
import copy
from decimal import Decimal
import hashlib
import json
import math
import re


TASK_ROOT = '/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/'
META_ROOT = '/opt/walker/manipulation_meta_tasks/share/manipulation_meta_tasks/config/meta_clamp/'
SOURCE_XML_PATH = TASK_ROOT + 'wrc_cruzr/put_cruzr_wrc_low.xml'
SOURCE_YAML_PATH = META_ROOT + 'wrc/put_cruzr_wrc_low.yaml'
SOURCE_OPEN_PATH = META_ROOT + 'wrc/open_arm_cruzr.yaml'
SOURCE_HASHES = {
    SOURCE_XML_PATH: '579b862962e0ee07a423c92517c29b5ecad80b4929961aac2fae6a0240fa0f78',
    SOURCE_YAML_PATH: '8aeb0a24a3149c7676f481219299ec85bb872d6b17ad93605a6e461776909ff5',
    SOURCE_OPEN_PATH: 'c41bd1d88379c2012ee44639142fb5b55c1d58decd6a75851c8e17763778e37b',
}
BUILDER_VERSION = 3
BOX_SIZE_M = (0.603, 0.397, 0.22)
APPROACH_ABOVE_CONTACT_M = 0.20
VENDOR_CONTACT_Z_M = 0.45
VENDOR_APPROACH_Z_M = 0.65
_REFERENCES = ('reference_box_bottom_above_floor_m', 'reference_left_hand_motion_z_m',
               'reference_right_hand_motion_z_m')
_VERIFICATIONS = ('horizontal_alignment_verified', 'release_clearance_verified')
_LEGACY_PROFILE_KEYS = {'version', 'id', 'surface_height_m', 'surface_pitch_deg',
                        'box_size_m', *_REFERENCES, *_VERIFICATIONS, 'evidence'}
_VENDOR_REFERENCE = 'reference_vendor_box_bottom_above_floor_m'
_VENDOR_VERIFIED = 'reference_vendor_position_reached_verified'
_PROFILE_KEYS = _LEGACY_PROFILE_KEYS | {'calibration_mode', _VENDOR_REFERENCE, _VENDOR_VERIFIED}
_MODES = ('measured_hand_reference', 'vendor_final_reference')


class DepositGeometryPending(ValueError):
    """The missing geometry record prevents creating an executable bundle."""

    def __init__(self, missing):
        self.missing = tuple(missing)
        super().__init__('Deposit geometry pending: ' + ', '.join(missing))


def _number(value, label):
    if type(value) not in (int, float):
        raise ValueError(label + ': expected finite number')
    try:
        number = float(value)
    except OverflowError as exc:
        raise ValueError(label + ': expected finite number') from exc
    if not math.isfinite(number):
        raise ValueError(label + ': expected finite number')
    return number


def _sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False)


def validate_profile(profile):
    """Return a detached, normalized profile; null geometry remains pending.

    Evidence is a nonempty reference string when present. Its contents and the
    applicability of the measurements cannot be established by this parser.
    Hand reference coordinates may be signed; the measured box bottom must be
    above the floor. ``reference_vendor_position_reached_verified`` attests that
    the unchanged original final position was actually reached with the same box
    still held horizontally at the retained hand orientations. It cannot be set
    merely from an action result or a commanded/planned coordinate. Early contact
    and partial descent do not qualify. No reach envelope is invented.

    The earlier v1 schema without the three mode fields remains accepted as a
    measured-hand reference. A complete normalized profile always includes them.
    """
    if not isinstance(profile, dict) or set(profile) not in (_LEGACY_PROFILE_KEYS, _PROFILE_KEYS):
        raise ValueError('Deposit profile: missing or unknown fields')
    if type(profile['version']) is not int or profile['version'] != 1:
        raise ValueError('Unsupported deposit profile version')
    if not isinstance(profile['id'], str) or not re.fullmatch(
            r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}', profile['id']):
        raise ValueError('Invalid deposit profile id')
    result = copy.deepcopy(profile)
    if set(profile) == _LEGACY_PROFILE_KEYS:
        result.update(calibration_mode='measured_hand_reference',
                      reference_vendor_box_bottom_above_floor_m=None,
                      reference_vendor_position_reached_verified=False)
    if result['calibration_mode'] not in _MODES:
        raise ValueError('Unknown deposit calibration_mode')
    result['surface_height_m'] = _number(profile['surface_height_m'], 'surface_height_m')
    if result['surface_height_m'] <= 0:
        raise ValueError('surface_height_m must be positive')
    result['surface_pitch_deg'] = _number(profile['surface_pitch_deg'], 'surface_pitch_deg')
    if result['surface_pitch_deg'] != 0:
        raise ValueError('Only a horizontal surface (surface_pitch_deg=0) is supported')
    size = profile['box_size_m']
    if not isinstance(size, list) or len(size) != 3:
        raise ValueError('box_size_m must contain three numbers')
    result['box_size_m'] = [_number(item, 'box_size_m') for item in size]
    if tuple(result['box_size_m']) != BOX_SIZE_M:
        raise ValueError('Expected box_size_m [0.603, 0.397, 0.22]')
    for name in _REFERENCES:
        if profile[name] is not None:
            result[name] = _number(profile[name], name)
    box_reference = result['reference_box_bottom_above_floor_m']
    if box_reference is not None and box_reference <= 0:
        raise ValueError('reference_box_bottom_above_floor_m must be positive')
    for name in _VERIFICATIONS:
        if type(profile[name]) is not bool:
            raise ValueError(name + ': expected boolean')
    if profile['evidence'] is not None and (
            not isinstance(profile['evidence'], str) or not profile['evidence'].strip()):
        raise ValueError('evidence must be null or a nonempty reference string')
    if result[_VENDOR_REFERENCE] is not None:
        result[_VENDOR_REFERENCE] = _number(result[_VENDOR_REFERENCE], _VENDOR_REFERENCE)
        if result[_VENDOR_REFERENCE] <= 0:
            raise ValueError(_VENDOR_REFERENCE + ' must be positive')
    if type(result[_VENDOR_VERIFIED]) is not bool:
        raise ValueError(_VENDOR_VERIFIED + ': expected boolean')
    if result['calibration_mode'] == 'measured_hand_reference':
        if result[_VENDOR_REFERENCE] is not None or result[_VENDOR_VERIFIED]:
            raise ValueError('Calibration modes are exclusive: measured-hand reference cannot include vendor reference')
    elif any(result[name] is not None for name in _REFERENCES):
        raise ValueError('Calibration modes are exclusive: vendor reference cannot include measured-hand references')
    return result


def review(profile):
    """Review completeness and calculate nominal targets, never certify motion."""
    config = validate_profile(profile)
    vendor_mode = config['calibration_mode'] == 'vendor_final_reference'
    references = (_VENDOR_REFERENCE,) if vendor_mode else _REFERENCES
    missing = [name for name in references if config[name] is None]
    if vendor_mode and not config[_VENDOR_VERIFIED]:
        missing.append(_VENDOR_VERIFIED)
    missing += [name for name in _VERIFICATIONS if not config[name]]
    if config['evidence'] is None:
        missing.append('evidence')
    targets = None
    complete_reference = all(config[name] is not None for name in references)
    # Do not derive a target from an unverified or uncited vendor endpoint: its
    # box height could have been measured after an early stop instead.
    if vendor_mode:
        complete_reference = complete_reference and config[_VENDOR_VERIFIED] and config['evidence'] is not None
    if complete_reference:
        targets = {}
        surface = Decimal(str(config['surface_height_m']))
        for side in ('left', 'right'):
            if vendor_mode:
                delta = surface - Decimal(str(config[_VENDOR_REFERENCE]))
                contact = Decimal(str(VENDOR_CONTACT_Z_M)) + delta
                approach = Decimal(str(VENDOR_APPROACH_Z_M)) + delta
            else:
                box_reference = Decimal(str(config['reference_box_bottom_above_floor_m']))
                hand_reference = Decimal(str(config['reference_' + side + '_hand_motion_z_m']))
                contact = surface + hand_reference - box_reference
                approach = contact + Decimal(str(APPROACH_ABOVE_CONTACT_M))
            targets[side + '_hand'] = {
                'contact_z_m': _number(float(contact), side + ' contact Z'),
                'approach_z_m': _number(float(approach), side + ' approach Z'),
            }
    return {
        'ready': not missing,
        'missing': missing,
        'targets': targets,
        'config': config,
        'calibration_mode': config['calibration_mode'],
        'physical_validation': 'pending',
        'target_semantics': 'Nominal hand targets in Motion; contact is not measured.',
    }


def _replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError('Pinned source structure does not match the deposit template')
    return text.replace(before, after, 1)


def build_bundle(profile, source_xml, source_yaml, source_open_yaml):
    """Build new immutable paths only after a complete geometry record.

    Exact source pins make the limited textual changes auditable without a YAML
    dependency in the runtime. The unchanged opening remains a pinned external
    dependency; its clearance must be recorded for this configuration.
    """
    report = review(profile)
    if not report['ready']:
        raise DepositGeometryPending(report['missing'])
    for path, text in ((SOURCE_XML_PATH, source_xml), (SOURCE_YAML_PATH, source_yaml),
                       (SOURCE_OPEN_PATH, source_open_yaml)):
        if not isinstance(text, str) or _sha(text) != SOURCE_HASHES[path]:
            raise ValueError('Vendor deposit source hash mismatch: ' + path)
    config = report['config']
    config_sha = _sha(_canonical(config))
    package_id = _sha(_canonical({'builder_version': BUILDER_VERSION,
                                 'config': config, 'dependencies': SOURCE_HASHES}))
    task_name = 'local_scenario1_deposit/' + package_id
    changed_yaml = source_yaml
    for side, y_text in (('left', '0.285'), ('right', '-0.285')):
        z_text = repr(report['targets'][side + '_hand']['approach_z_m'])
        before = '          position: [0.75, ' + y_text + ', 0.65] # x y z'
        after = '          position: [0.75, ' + y_text + ', ' + z_text + '] # x y z'
        changed_yaml = _replace_once(changed_yaml, before, after)
    changed_yaml = _replace_once(changed_yaml, '  box_size: [0.6, 0.4, 0.28]',
                                 '  box_size: [0.603, 0.397, 0.22]')
    changed_xml = _replace_once(source_xml, 'name="wrc/put_cruzr_wrc_low"',
                                'name="' + task_name + '"')
    # Consumers install and verify the YAML before publishing its XML entrypoint.
    tasks = {META_ROOT + task_name + '.yaml': changed_yaml,
             TASK_ROOT + task_name + '.xml': changed_xml}
    dependencies = dict(SOURCE_HASHES)
    manifest = {
        'version': 1,
        'id': package_id,
        'task_name': task_name,
        'config_sha256': config_sha,
        'dependencies': dict(dependencies),
        'robot_files': {**dependencies, **{path: _sha(text) for path, text in tasks.items()}},
        'physical_validation': 'pending',
    }
    return {'task_name': task_name, 'tasks': tasks, 'dependencies': dependencies,
            'manifest': manifest, 'review': report}
