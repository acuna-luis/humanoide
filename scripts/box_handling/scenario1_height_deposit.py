"""Immutable height profiles for the common scenario runtime; pure, no I/O.

74 cm integrates the observed 19 cm lowering into the native approach. This
interpolation has NOT been physically tested. Support and pin clearance remain
recipe assumptions, not sensor measurements. 90 cm retains the historical
native descent/opening geometry, but uses the same runtime and builder.
"""
import copy
import hashlib
import json

TASK_ROOT = '/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/'
META_ROOT = '/opt/walker/manipulation_meta_tasks/share/manipulation_meta_tasks/config/meta_clamp/'
SOURCE_XML_PATH = TASK_ROOT+'wrc_cruzr/put_cruzr_wrc_low.xml'
SOURCE_YAML_PATH = META_ROOT+'wrc/put_cruzr_wrc_low.yaml'
SOURCE_OPEN_PATH = META_ROOT+'wrc/open_arm_cruzr.yaml'
TEXT_SOURCES = (SOURCE_XML_PATH, SOURCE_YAML_PATH, SOURCE_OPEN_PATH)
CURRENT_MODEL_PINS = {
    TASK_ROOT+'cruzr/home.xml': 'd9e9462792b41300d352604b53ea2a4890a9382e942321990708f6ded2e26ccb',
    '/opt/walker/manipulation_platforms/share/manipulation_platforms/config/cruzr_s2_robot_description.yaml': 'bcc4a0dd3f013e42db2c57c063b00d5517f94cfef0b36aa10fce8d10070f22d7',
    '/opt/walker/manipulation_platforms/share/manipulation_platforms/config/urdf/cruzr_s2.urdf': 'c01acb400366ec154a852e75853bc2b5cf4807d5bd217a89578b8f4cd8ae1760',
    META_ROOT+'task_stack/task_stack_cruzr_clamp_manipulability.yaml': '34441b6be6e2ad4936e648bc791689bd27db8eef88ced73fe847cb879d121085',
    '/opt/walker/manipulation_meta_tasks/lib/libmeta_clamp.so': 'd6bc61a493f7d790150fdbd673108121f46589fef56620de4a9023dcc2ba520a',
    '/opt/walker/manipulation_kinematics/lib/libs2_arm_kinematics.so': '2a41cf5520672c9dcbd1c532eff775b4ce6d9ff1e100485d6ca7ba8174ad251c',
}
DEPENDENCIES = dict(zip(TEXT_SOURCES, (
    '579b862962e0ee07a423c92517c29b5ecad80b4929961aac2fae6a0240fa0f78',
    '8aeb0a24a3149c7676f481219299ec85bb872d6b17ad93605a6e461776909ff5',
    'c41bd1d88379c2012ee44639142fb5b55c1d58decd6a75851c8e17763778e37b')))
DEPENDENCIES.update(CURRENT_MODEL_PINS)
PHASE = 'unified_height_deposit'
NAMESPACE = 'local_scenario1_height/'
COMPATIBILITY = 'calculated_pending_motion'
RECIPES = {
    74: dict(version=1, height_cm=74, approach_z='0.94', hand_descent='-0.19',
             torso_descent='0.0', sequential_pin_relief_cm=4,
             physical_validation='pending_integrated_trajectory'),
    90: dict(version=1, height_cm=90, approach_z='1.10', hand_descent='-0.20',
             torso_descent='-0.20', sequential_pin_relief_cm=0,
             physical_validation='historical_geometry_new_packaging_pending'),
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def identity(height):
    recipe = RECIPES[height]
    return sha(canonical(dict(recipe=recipe, dependencies=DEPENDENCIES)))


def profile(height):
    if type(height) not in (int, float) or height not in RECIPES:
        raise ValueError('Only reviewed heights 74 and 90 cm are supported')
    return dict(id='scenario1_height_'+str(int(height))+'_v1', box_size_m=[.603, .397, .22],
        intended_use='separate_nested_box',
        grasp=dict(task='local_front_box/separate_right_cruzr', compatibility='operator_assumed_existing'),
        deposit=dict(task=NAMESPACE+identity(height), compatibility=COMPATIBILITY))


def profile_height(value):
    for height in RECIPES:
        if value == profile(height):
            return height
    return None


def _replace(text, old, new, count=1):
    if text.count(old) != count:
        raise ValueError('Pinned native source structure changed')
    return text.replace(old, new)


def _release(source, stage):
    trajectory = '  robot_trajectory_data:\n'
    for body in ('left_hand', 'right_hand', 'torso'):
        position = '[0.0, 0.0, 0.0]'
        if body != 'torso':
            position = ('[0.0, 0.0, -0.04]' if stage == 'relief' else
                        '[0.0, '+('0.1' if body == 'left_hand' else '-0.1')+', 0.0]')
        trajectory += ('    - body_name: "'+body+'"\n      data:\n'
            '        - timestamp: 2.0\n          position: '+position+' # x y z\n'
            '          orientation: [1.0, 0.0, 0.0, 0.0] # w x y z\n'
            '          tranform_mode: "RELATIVE"\n')
    prefix, separator, _ = source.partition('  robot_trajectory_data:\n')
    if not separator:
        raise ValueError('Missing pinned release trajectory')
    return prefix+trajectory


def build_bundle(reference, source_xml, source_yaml, source_open):
    if reference not in RECIPES.values() or type(reference) is not dict:
        raise ValueError('Unsupported height recipe')
    height = reference['height_cm']
    if canonical(reference) != canonical(RECIPES[height]):
        raise ValueError('Height recipe changed')
    for path, text in zip(TEXT_SOURCES, (source_xml, source_yaml, source_open)):
        if type(text) is not str or sha(text) != DEPENDENCIES[path]:
            raise ValueError('Native source hash mismatch: '+path)
    name = NAMESPACE+identity(height)
    changed = source_yaml
    for lateral in ('0.285', '-0.285'):
        changed = _replace(changed, 'position: [0.75, '+lateral+', 0.65]',
            'position: [0.75, '+lateral+', '+reference['approach_z']+']')
    # The first two final relative waypoints belong to the hands; the third
    # belongs to the torso. Keep every other byte, including force/collision.
    old = '          position: [0.0, 0.0, -0.20] # x y z'
    if changed.count(old) != 3:
        raise ValueError('Expected exactly two hand and one torso descents')
    parts = changed.split(old)
    changed = parts[0]
    for part, descent in zip(parts[1:], (reference['hand_descent'], reference['hand_descent'], reference['torso_descent'])):
        changed += '          position: [0.0, 0.0, '+descent+'] # x y z'+part
    xml = _replace(source_xml, 'name="wrc/put_cruzr_wrc_low"', 'name="'+name+'"')
    tasks = {META_ROOT+name+'.yaml': changed}
    if reference['sequential_pin_relief_cm']:
        actions = ('name="'+name+'_relief" />\n'
                   '            <Action ID="MetaClamp" name="'+name+'_open"')
        xml = _replace(xml, 'name="wrc/open_arm_cruzr"', actions)
        tasks[META_ROOT+name+'_relief.yaml'] = _release(source_open, 'relief')
        tasks[META_ROOT+name+'_open.yaml'] = _release(source_open, 'open')
    tasks[TASK_ROOT+name+'.xml'] = xml
    hashes = {path: sha(text) for path, text in tasks.items()}
    review = dict(reference=copy.deepcopy(reference), source_open=source_open, physical_validation=reference['physical_validation'],
        native_controls_preserved=True, current_support_measured=False, current_pins_free_measured=False,
        nominal_duration_s=16 if height == 74 else 14,
        assumptions='Same clamps, box, grasp, table placement and clearances; support/release assumed after native success')
    manifest = dict(version=1, id=identity(height), phase=PHASE, task_name=name,
        dependencies=dict(DEPENDENCIES), robot_files={**DEPENDENCIES, **hashes}, physical_validation='pending')
    return dict(task_name=name, tasks=tasks, dependencies=dict(DEPENDENCIES), manifest=manifest, review=review)


def validate_bundle(bundle):
    """Reverse only allowed edits, pin originals, then reproduce every byte."""
    try:
        height = bundle['review']['reference']['height_cm']
        reference = RECIPES[height]
        name = NAMESPACE+identity(height)
        source_yaml = bundle['tasks'][META_ROOT+name+'.yaml']
        for lateral in ('0.285', '-0.285'):
            source_yaml = _replace(source_yaml,
                'position: [0.75, '+lateral+', '+reference['approach_z']+']',
                'position: [0.75, '+lateral+', 0.65]')
        # Reverse in trajectory order, including the unchanged 90 cm values.
        marker = '          position: [0.0, 0.0, '
        # Select only final waypoints: t12 has this exact preceding line.
        for descent in set((reference['hand_descent'], reference['torso_descent'])):
            source_yaml = source_yaml.replace('        - timestamp: 12.0\n'+marker+descent+'] # x y z',
                '        - timestamp: 12.0\n'+marker+'-0.20] # x y z')
        source_xml = bundle['tasks'][TASK_ROOT+name+'.xml']
        source_xml = _replace(source_xml, 'name="'+name+'"', 'name="wrc/put_cruzr_wrc_low"')
        if reference['sequential_pin_relief_cm']:
            source_xml = _replace(source_xml,
                'name="'+name+'_relief" />\n            <Action ID="MetaClamp" name="'+name+'_open"',
                'name="wrc/open_arm_cruzr"')
            # The opening source is stored as a pinned dependency, supplied in
            # the bundle for reproducible isolated validation, never dispatched.
        source_open = bundle['review']['source_open']
        expected = build_bundle(reference, source_xml, source_yaml, source_open)
        if canonical(expected) != canonical(bundle):
            raise ValueError('Height bundle differs from exact reconstruction')
        return copy.deepcopy(expected)
    except (KeyError, TypeError, IndexError) as exc:
        raise ValueError('Malformed height bundle') from exc


def main(argv=None):
    """Export a local immutable installation/rollback package, without network."""
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--height-cm', type=int, choices=tuple(RECIPES), required=True)
    parser.add_argument('--output', type=Path, required=True, help='New private directory; never overwritten')
    args = parser.parse_args(argv)
    snapshot = Path(__file__).resolve().parents[2]/'vendor/ubtech/cruzr_s2/snapshot_20260916/motion'
    b = build_bundle(RECIPES[args.height_cm], *((snapshot/path).read_text() for path in (
        'tasks/wrc_cruzr/put_cruzr_wrc_low.xml', 'meta_clamp/wrc/put_cruzr_wrc_low.yaml',
        'meta_clamp/wrc/open_arm_cruzr.yaml')))
    validate_bundle(b)
    args.output.mkdir(parents=True, exist_ok=False, mode=0o700)
    (args.output/'bundle.json').write_text(json.dumps(b, indent=2)+'\n')
    print(json.dumps(dict(status='EXPORTED_LOCALLY_NO_INSTALL_NO_MOTION',
        task_name=b['task_name'], bundle=str(args.output/'bundle.json'))))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
