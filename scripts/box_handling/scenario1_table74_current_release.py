"""Separate, immutable pin relief and lateral opening after current support.

This pure builder preserves the vendor opening controls and creates only one
two-second relative phase. Operator support/clearance declarations are required
inputs, not sensor measurements or physical qualification. No installation,
robot connection, automatic retry, rotation or HOME is provided here.
"""
import copy
import hashlib
import json
import math
import re
import uuid

if __package__:
    from . import scenario1_deposit as deposit
else:
    import scenario1_deposit as deposit


BUILDER_VERSION = 2
RECIPE_BUILDER_VERSION = 3
PHASE = 'current_pin_release'
NAMESPACE = 'local_table74_release/'
TASK_ROOT = deposit.TASK_ROOT
META_ROOT = deposit.META_ROOT
SOURCE_XML_PATH = deposit.SOURCE_XML_PATH
SOURCE_YAML_PATH = deposit.SOURCE_OPEN_PATH
SOURCE_OPEN_PATH = SOURCE_YAML_PATH
META_CLAMP_PATH = '/opt/walker/manipulation_meta_tasks/lib/libmeta_clamp.so'
META_CLAMP_SHA256 = 'd6bc61a493f7d790150fdbd673108121f46589fef56620de4a9023dcc2ba520a'
BINARY_SHA = META_CLAMP_SHA256
DEPENDENCIES = {
    SOURCE_XML_PATH: deposit.SOURCE_HASHES[SOURCE_XML_PATH],
    SOURCE_YAML_PATH: deposit.SOURCE_HASHES[SOURCE_YAML_PATH],
    META_CLAMP_PATH: META_CLAMP_SHA256,
}
_REFERENCE_KEYS = {'version', 'stage', 'surface_height_m', 'predecessor_bundle_id',
    'predecessor_goal_id', 'operator_support_confirmed', 'tool_table_clearance_m',
    'required_pin_exit_m', 'operator_pins_free', 'lateral_path_clear', 'evidence', 'scope'}
_TASK_TOKEN = '__TABLE74_CURRENT_RELEASE_TASK_NAME__'
_PUT_LINE = '            <Action ID="MetaClamp" name="wrc/put_cruzr_wrc_low" />\n'
_OPEN_LINE = '            <Action ID="MetaClamp" name="wrc/open_arm_cruzr" />\n'
_SOURCE_TRAJECTORY = '''  robot_trajectory_data:
    - body_name: "left_hand"
      data:
        - timestamp: 2.0
          position: [0, 0.1, -0.05] # x y z
          orientation: [0.7933533, 0.6087614, 0.0, 0.0] # w x y z
          # orientation: [1.0, 0.0, 0.0, 0.0] # w x y z
          tranform_mode: "RELATIVE"
    - body_name: "right_hand"
      data:
        - timestamp: 2.0
          position: [0, -0.1, -0.05] # x y z
          orientation: [0.7933533, -0.6087614, 0.0, 0.0] # w x y z
          # orientation: [1.0, 0.0, 0.0, 0.0] # w x y z
          tranform_mode: "RELATIVE"
    - body_name: "torso"
      data:
        - timestamp: 2.0
          position: [0.0, 0.0, -0.0] # x y z
          orientation: [1.0, 0.0, 0.0, 0.0] # w x y z
          tranform_mode: "RELATIVE"
'''


def sha256(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def pin_relief_distance_m(version):
    """Keep v1 immutable for historical proofs/rollback; new references use v2."""
    if type(version) is not int or version not in (1, BUILDER_VERSION, RECIPE_BUILDER_VERSION):
        raise ValueError('Unsupported current release reference version')
    return .03 if version == 1 else .04


def minimum_tool_clearance_m(version, stage):
    pin_relief_distance_m(version)
    return .05 if version in (2, RECIPE_BUILDER_VERSION) and stage == 'pin_relief' else .04


def _validate_recipe_reference(reference, stage):
    """Check fixed historical assumptions without upgrading them to observations."""
    if __package__:
        from . import scenario1_table74_recipe as recipe
    else:
        import scenario1_table74_recipe as recipe
    recipe.validate_record(reference['assumption_provenance'])
    facts = reference['assumption_provenance']['recipe']['facts']
    if (reference['operator_support_confirmed'] is not False or
            reference['operator_pins_free'] is not False or
            reference['lateral_path_clear'] is not False or
            facts['support_assumed'] is not True or
            facts['lateral_path_assumed_clear'] is not True or
            stage == 'lateral_open' and facts['pins_free_assumed'] is not True):
        raise ValueError('Recipe assumptions must remain distinct from current operator declarations')
    expected_clearance = facts['tool_clearance_before_relief_cm' if stage == 'pin_relief'
                               else 'tool_clearance_after_relief_cm'] / 100.
    if (type(reference['tool_table_clearance_m']) not in (int, float) or
            reference['tool_table_clearance_m'] != expected_clearance or
            type(reference['required_pin_exit_m']) not in (int, float) or
            reference['required_pin_exit_m'] != facts['required_pin_exit_cm'] / 100.):
        raise ValueError('Release dimensions differ from the pinned historical recipe')


def validate_reference(reference):
    """Require the exact phase and explicit current physical declarations.

    Authentic predecessor journals, unchanged robot context and the truth of
    operator declarations must be checked separately by the supervised runner.
    """
    if not isinstance(reference, dict):
        raise ValueError('Current release reference: missing or unknown fields')
    version = reference.get('version')
    expected_keys = _REFERENCE_KEYS | ({'assumption_provenance'} if version == RECIPE_BUILDER_VERSION else set())
    if set(reference) != expected_keys:
        raise ValueError('Current release reference: missing or unknown fields')
    relief_distance = pin_relief_distance_m(reference['version'])
    stage = reference['stage']
    expected_scope = ('recorded_recipe_supported_box_assumption_only'
                      if version == RECIPE_BUILDER_VERSION else 'current_supported_box_only')
    if (type(stage) is not str or stage not in ('pin_relief', 'lateral_open') or
            reference['scope'] != expected_scope):
        raise ValueError('Current release requires one explicit supported-box phase')
    if version == RECIPE_BUILDER_VERSION:
        _validate_recipe_reference(reference, stage)
    elif (reference['operator_support_confirmed'] is not True or
            reference['lateral_path_clear'] is not True or
            reference['operator_pins_free'] is not (stage == 'lateral_open')):
        raise ValueError('Current release support/path/pin declarations do not admit this stage')
    if (type(reference['predecessor_bundle_id']) is not str or
            re.fullmatch('[0-9a-f]{64}', reference['predecessor_bundle_id']) is None):
        raise ValueError('Current release predecessor bundle ID is invalid')
    goal = reference['predecessor_goal_id']
    try:
        parsed = uuid.UUID(goal)
        if type(goal) is not str or str(parsed) != goal or parsed.int == 0:
            raise ValueError
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError('Current release predecessor requires a canonical nonzero UUID') from exc
    if type(reference['evidence']) is not str or not reference['evidence'].strip() or len(reference['evidence']) > 4096:
        raise ValueError('Current release requires explicit bounded current operator evidence')
    result = copy.deepcopy(reference)
    for name in ('surface_height_m', 'tool_table_clearance_m', 'required_pin_exit_m'):
        value = reference[name]
        try:
            valid = type(value) in (int, float) and math.isfinite(value)
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError(name+': finite numeric value required')
        result[name] = float(value)
    if result['surface_height_m'] != .74:
        raise ValueError('Current release is restricted to the 74 cm surface')
    clearance = minimum_tool_clearance_m(reference['version'], stage)
    if result['tool_table_clearance_m'] < clearance:
        raise ValueError('Current tool/table clearance must be at least '+format(clearance*100, 'g')+' cm')
    if not 0. < result['required_pin_exit_m'] <= relief_distance:
        raise ValueError('Required pin exit must be positive and at most the nominal '+format(relief_distance*100, 'g')+' cm relief')
    return result


def _replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Pinned current release source structure changed')
    return text.replace(old, new, 1)


def _trajectory(stage, version=BUILDER_VERSION):
    distance = pin_relief_distance_m(version)
    if stage not in ('pin_relief', 'lateral_open'):
        raise ValueError('Unknown release trajectory stage')
    output = ['  robot_trajectory_data:\n']
    for body in ('left_hand', 'right_hand', 'torso'):
        position = '[0.0, 0.0, 0.0]'
        if body != 'torso':
            if stage == 'pin_relief':
                position = '[0.0, 0.0, -'+format(distance, '.2f')+']'
            else:
                position = '[0.0, '+('0.1' if body == 'left_hand' else '-0.1')+', 0.0]'
        output.extend(['    - body_name: "'+body+'"\n', '      data:\n',
            '        - timestamp: 2.0\n', '          position: '+position+' # x y z\n',
            '          orientation: [1.0, 0.0, 0.0, 0.0] # w x y z\n',
            '          tranform_mode: "RELATIVE"\n'])
    return ''.join(output)


def build_bundle(reference, source_xml, source_yaml):
    """Build one phase; preserve all bytes outside the XML action and trajectory."""
    config = validate_reference(reference)
    version = config['version']
    for path, source in ((SOURCE_XML_PATH, source_xml), (SOURCE_YAML_PATH, source_yaml)):
        if type(source) is not str or sha256(source) != DEPENDENCIES[path]:
            raise ValueError('Current release source checksum mismatch: '+path)
    stage = config['stage']
    changed_yaml = _replace_once(source_yaml, _SOURCE_TRAJECTORY, _trajectory(stage, version))
    xml_template = _replace_once(source_xml, _PUT_LINE, '')
    xml_template = _replace_once(xml_template, 'name="wrc/open_arm_cruzr"', 'name="'+_TASK_TOKEN+'"')
    templates = {'yaml': sha256(changed_yaml), 'xml_template': sha256(xml_template)}
    identity = sha256(canonical(dict(builder_version=version, phase=PHASE,
        reference=config, dependencies=DEPENDENCIES, content_templates=templates)))
    task_name = NAMESPACE+identity+'_release'
    changed_xml = _replace_once(xml_template, _TASK_TOKEN, task_name)
    tasks = {META_ROOT+task_name+'.yaml': changed_yaml, TASK_ROOT+task_name+'.xml': changed_xml}
    hashes = {path: sha256(text) for path, text in tasks.items()}
    distance = pin_relief_distance_m(version)
    positions = ([0., 0., -distance], [0., 0., -distance]) if stage == 'pin_relief' else ([0., .1, 0.], [0., -.1, 0.])
    review = dict(phase=PHASE, stage=stage, reference=copy.deepcopy(config),
        reference_kind='operator_confirmed_current_support_clearance_and_pin_state_not_sensor_measurement',
        physical_validation='pending', kinematic_validation='pending',
        automatic_execution_authorized=False, installed=False, integrated_in_optimistic=False,
        measured_absolute_calibration_created=False, physical_support_sensor_verified=False,
        pin_disengagement_sensor_verified=False, release_physically_qualified=False,
        nominal_duration_s=2., hand_mode='RELATIVE', relative_quaternion_wxyz=[1., 0., 0., 0.],
        left_hand_delta_m=positions[0], right_hand_delta_m=positions[1], torso_delta_m=[0., 0., 0.],
        source_box_size_unchanged_m=[.6, .4, .28], native_controls_preserved=True,
        vendor_position_rotation_limit_up_unchanged=[1., .1, 0., .5, .4],
        excluded_phases=['approach', 'support_lowering', 'rotation', 'navigation', 'home',
                         'lateral_open' if stage == 'pin_relief' else 'pin_relief'],
        assumptions_not_verified=[
            'The operator confirms the same box is fully supported and stable over the table.',
            'The stated tool/table clearance and required pin exit apply to both actual effectors.',
            'The box, robot pose and surrounding clearance are unchanged from the authenticated predecessor.',
            'Relative Z is the required physical pin extraction direction and hand Y opens away from the box.',
        ], limitations=[
            'The runner must authenticate the exact predecessor bundle, UUID, terminal result and unchanged source context.',
            'Pin relief requires the genuine support task; lateral opening requires genuine pin relief and a fresh pins-free confirmation.',
            'No sensor measurement, certified reachability, swept-volume clearance or pin extraction proof is created.',
            'Native force/IK may adjust posture; zero torso waypoints are not a physical torso lock.',
            'All source opening parameters outside the trajectory remain unchanged, including the five-value upper limit vector.',
            'Exact interpolation, peak velocity and the physical result are not certified by the two-second waypoint.',
            'SUCCEED does not prove pin disengagement, stable support, release or authorization for HOME.',
            'A repeated relative task repeats its displacement; no automatic retry or next phase is authorized.',
        ])
    if version == RECIPE_BUILDER_VERSION:
        review.update(
            reference_kind='recorded_recipe_assumptions_not_current_physical_measurements',
            assumption_provenance=copy.deepcopy(config['assumption_provenance']),
            current_operator_support_confirmed=False, current_operator_pins_free=False,
            support_assumed=True, pins_free_assumed=stage == 'lateral_open',
            lateral_path_assumed_clear=True, current_physical_measurement=False,
            assumptions_not_verified=[
                'The fixed historical recipe assumes full stable support; there is no current support observation.',
                'Tool clearance, pin exit and lateral clearance are values recorded in the successful take, not new measurements.',
                'The same box, table, effectors and placement are assumed; native health and motion checks remain required.',
                'After nominal relief the recipe assumes free pins; SUCCEED alone does not measure pin disengagement.',
            ],
        )
        review['limitations'][1] = (
            'Pin relief requires genuine completed support and lateral opening genuine completed pin relief; '
            'support and free pins remain fixed recipe assumptions, not fresh physical confirmations.')
    manifest = dict(version=1, builder_version=version, id=identity, phase=PHASE,
        task_name=task_name, reference_sha256=sha256(canonical(config)),
        content_template_sha256=templates, dependencies=dict(DEPENDENCIES),
        robot_files={**DEPENDENCIES, **hashes}, physical_validation='pending', automatic_execution_authorized=False)
    return dict(task_name=task_name, tasks=tasks, dependencies=dict(DEPENDENCIES), manifest=manifest, review=review)


prepare = build_bundle


def validate_bundle(bundle):
    """Reproduce the complete contract in memory, rejecting rehashed tampering."""
    if not isinstance(bundle, dict) or set(bundle) != {'task_name', 'tasks', 'dependencies', 'manifest', 'review'}:
        raise ValueError('Invalid current release bundle fields')
    name = bundle['task_name']
    if type(name) is not str or re.fullmatch(NAMESPACE+r'[0-9a-f]{64}_release', name) is None:
        raise ValueError('Invalid immutable current release task name')
    tasks = bundle['tasks']
    if (not isinstance(tasks, dict) or set(tasks) != {META_ROOT+name+'.yaml', TASK_ROOT+name+'.xml'} or
            any(type(text) is not str or not text or len(text.encode()) > 262144 for text in tasks.values())):
        raise ValueError('Current release requires exactly one bounded XML and opening YAML')
    try:
        config = validate_reference(bundle['review']['reference'])
        source_yaml = _replace_once(tasks[META_ROOT+name+'.yaml'], _trajectory(config['stage'], config['version']), _SOURCE_TRAJECTORY)
        source_xml = _replace_once(tasks[TASK_ROOT+name+'.xml'],
            '            <Action ID="MetaClamp" name="'+name+'" />\n', _PUT_LINE+_OPEN_LINE)
        expected = build_bundle(config, source_xml, source_yaml)
        if canonical(bundle) != canonical(expected):
            raise ValueError('Current release bundle differs from its exact reproducible contract')
    except (KeyError, TypeError, OverflowError) as exc:
        raise ValueError('Malformed current release bundle') from exc
    return copy.deepcopy(expected)


def main(argv=None):
    """Write local artifacts to a new directory; never install, connect or move."""
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='New local directory; no overwrite or installation')
    args = parser.parse_args(argv)
    snapshot = Path(__file__).resolve().parents[2]/'vendor/ubtech/cruzr_s2/snapshot_20260916/motion'
    bundle = build_bundle(json.loads(args.reference.read_text()),
        (snapshot/'tasks/wrc_cruzr/put_cruzr_wrc_low.xml').read_text(),
        (snapshot/'meta_clamp/wrc/open_arm_cruzr.yaml').read_text())
    validate_bundle(bundle)
    args.output.mkdir(parents=True, exist_ok=False, mode=0o700)
    for path, text in bundle['tasks'].items():
        with (args.output/Path(path).name).open('x') as stream:
            stream.write(text)
    for name, value in (('bundle.json', bundle), ('review.json', bundle['review'])):
        with (args.output/name).open('x') as stream:
            stream.write(json.dumps(value, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(dict(status='PREPARED_LOCALLY_NOT_INSTALLED_OR_EXECUTED',
        task_name=bundle['task_name'], stage=bundle['review']['stage'], output=str(args.output))))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
