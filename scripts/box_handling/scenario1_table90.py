"""Pure, pinned table90 deposit contract; no robot or filesystem operations."""
import hashlib
import json

TASK_ROOT = '/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/'
META_ROOT = '/opt/walker/manipulation_meta_tasks/share/manipulation_meta_tasks/config/meta_clamp/'
CURRENT_MODEL_PINS = {
    TASK_ROOT+'cruzr/home.xml': 'd9e9462792b41300d352604b53ea2a4890a9382e942321990708f6ded2e26ccb',
    '/opt/walker/manipulation_platforms/share/manipulation_platforms/config/cruzr_s2_robot_description.yaml': 'bcc4a0dd3f013e42db2c57c063b00d5517f94cfef0b36aa10fce8d10070f22d7',
    '/opt/walker/manipulation_platforms/share/manipulation_platforms/config/urdf/cruzr_s2.urdf': 'c01acb400366ec154a852e75853bc2b5cf4807d5bd217a89578b8f4cd8ae1760',
    META_ROOT+'task_stack/task_stack_cruzr_clamp_manipulability.yaml': '34441b6be6e2ad4936e648bc791689bd27db8eef88ced73fe847cb879d121085',
    '/opt/walker/manipulation_meta_tasks/lib/libmeta_clamp.so': 'd6bc61a493f7d790150fdbd673108121f46589fef56620de4a9023dcc2ba520a',
    '/opt/walker/manipulation_kinematics/lib/libs2_arm_kinematics.so': '2a41cf5520672c9dcbd1c532eff775b4ce6d9ff1e100485d6ca7ba8174ad251c',
}
DEPENDENCIES = {
    TASK_ROOT+'wrc_cruzr/put_cruzr_wrc_low.xml': '579b862962e0ee07a423c92517c29b5ecad80b4929961aac2fae6a0240fa0f78',
    META_ROOT+'wrc/put_cruzr_wrc_low.yaml': '8aeb0a24a3149c7676f481219299ec85bb872d6b17ad93605a6e461776909ff5',
    META_ROOT+'wrc/open_arm_cruzr.yaml': 'c41bd1d88379c2012ee44639142fb5b55c1d58decd6a75851c8e17763778e37b',
}
RECIPE = dict(version=1, reference_surface_height_m=.45, surface_height_m=.90,
              delta_height_m=.45, approach_hand_z_m=1.10, final_hand_z_m=.90,
              change='two_absolute_hand_z_only', reference='operator_confirmed_20261001')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


IDENTITY = sha(canonical(dict(recipe=RECIPE, dependencies=DEPENDENCIES)))
TASK_NAME = 'local_scenario1_deposit/'+IDENTITY
PROFILE_ID = 'scenario1_table90_v1'
COMPATIBILITY = 'calculated_pending_motion'

# Actual supervised trial, not an IK/collision certificate or a runtime flag.
# Assumed checkpoint records retain their original evidence classification.
PHYSICAL_QUALIFICATION = {
    'state': 'completed_operator_confirmed',
    'date': '2026-10-01 Europe/Madrid',
    'task_name': TASK_NAME,
    'profile_sha256': '6930bea144020dd338987d108eee9335b024458eececb1d8b96a96368b3a29d0',
    'evidence_root': '../Humanoide-vla-evidence/20261001_SCENARIO1_TABLE90/',
    'checkpoint_sha256': {
        'grasp-trial': '4c9df2c823c83822b4f028863c1b4082d3d8b87dfdda03354a622a866754c03d',
        'deposit-trial': 'e4c7b9b3c15d2398105da9bc53bde58f8e4e8d0f73ae9f093e0eaf019cc9aa76',
        'home-trial': '3760e5a61dafd156e6fcad861880c5a5f3e7d410e00b77c15be18ad7479d4a37',
    },
    'operator_confirmations': ['held_separated_stable', 'supported_on_table90_released_home_path_clear'],
    'home_verified': True,
    'scope': 'Same box, clamps, grasp, horizontal layout and pinned native model/HOME; one supervised trial in segments',
}


def motion_qualified(profile):
    return bool(PHYSICAL_QUALIFICATION and
                PHYSICAL_QUALIFICATION.get('state') == 'completed_operator_confirmed' and
                PHYSICAL_QUALIFICATION.get('task_name') == TASK_NAME and
                PHYSICAL_QUALIFICATION.get('home_verified') is True and
                PHYSICAL_QUALIFICATION.get('profile_sha256') == sha(canonical(profile)))


def is_table90(profile):
    return profile.get('deposit', {}).get('task') == TASK_NAME


def require_motion_ready(profile, stop_after, entry_stage='navigate_get1'):
    # Qualification applies only to the exact tested geometry. A changed
    # profile cannot borrow this trial. All live health/model checks still run.
    if (is_table90(profile) and not motion_qualified(profile) and stop_after in ('deposit', 'verify_home')
            and entry_stage not in ('verify_released', 'home', 'verify_home')):
        raise ValueError('TABLE90_MOTION_PENDING: ciclo completo pendiente de ensayo supervisado de depósito y retorno; use el modo específico y compruebe la liberación antes de HOME')


def build_bundle(source_xml, source_yaml, source_open):
    for path, content in zip(DEPENDENCIES, (source_xml, source_yaml, source_open)):
        if sha(content) != DEPENDENCIES[path]:
            raise ValueError('Table90 vendor source hash mismatch: '+path)
    changed = source_yaml
    for lateral in ('0.285', '-0.285'):
        old = f'position: [0.75, {lateral}, 0.65]'
        if changed.count(old) != 1:
            raise ValueError('Unexpected table90 source structure')
        changed = changed.replace(old, f'position: [0.75, {lateral}, 1.10]', 1)
    old = 'name="wrc/put_cruzr_wrc_low"'
    if source_xml.count(old) != 1:
        raise ValueError('Unexpected table90 XML')
    xml = source_xml.replace(old, 'name="'+TASK_NAME+'"', 1)
    tasks = {META_ROOT+TASK_NAME+'.yaml': changed, TASK_ROOT+TASK_NAME+'.xml': xml}
    hashes = {path: sha(content) for path, content in tasks.items()}
    review = dict(ready=True, missing=[], config=RECIPE, physical_validation='pending',
                  kinematic_validation='pending', executable=False,
                  reference_source='Operator confirmation; not independently measured')
    manifest = dict(version=1, id=IDENTITY, task_name=TASK_NAME,
                    config_sha256=sha(canonical(RECIPE)), dependencies=DEPENDENCIES,
                    robot_files=dict(DEPENDENCIES, **hashes), physical_validation='pending')
    return dict(task_name=TASK_NAME, tasks=tasks, dependencies=DEPENDENCIES,
                manifest=manifest, review=review)


def validate_bundle(bundle):
    if not isinstance(bundle, dict) or set(bundle) != {'task_name', 'tasks', 'dependencies', 'manifest', 'review'}:
        raise ValueError('Malformed table90 bundle')
    if bundle['task_name'] != TASK_NAME or bundle['dependencies'] != DEPENDENCIES:
        raise ValueError('Table90 identity/dependencies changed')
    expected = {META_ROOT+TASK_NAME+'.yaml', TASK_ROOT+TASK_NAME+'.xml'}
    if set(bundle['tasks']) != expected:
        raise ValueError('Table90 destinations changed')
    # Rebuild from the candidate by reversing ONLY the reviewed substitutions;
    # source pins reject every other modification, including torso or force.
    source_yaml = bundle['tasks'][META_ROOT+TASK_NAME+'.yaml']
    for lateral in ('0.285', '-0.285'):
        old = f'position: [0.75, {lateral}, 1.10]'
        if source_yaml.count(old) != 1:
            raise ValueError('Table90 hand targets changed')
        source_yaml = source_yaml.replace(old, f'position: [0.75, {lateral}, 0.65]', 1)
    source_xml = bundle['tasks'][TASK_ROOT+TASK_NAME+'.xml'].replace('name="'+TASK_NAME+'"', 'name="wrc/put_cruzr_wrc_low"', 1)
    # Opening remains an external pinned dependency; only its hash is needed here.
    if sha(source_yaml) != DEPENDENCIES[META_ROOT+'wrc/put_cruzr_wrc_low.yaml'] or sha(source_xml) != DEPENDENCIES[TASK_ROOT+'wrc_cruzr/put_cruzr_wrc_low.xml']:
        raise ValueError('Table90 contains unreviewed changes')
    hashes = {path: sha(text) for path, text in bundle['tasks'].items()}
    expected_manifest = dict(version=1, id=IDENTITY, task_name=TASK_NAME,
                            config_sha256=sha(canonical(RECIPE)), dependencies=DEPENDENCIES,
                            robot_files=dict(DEPENDENCIES, **hashes), physical_validation='pending')
    expected_review = dict(ready=True, missing=[], config=RECIPE, physical_validation='pending',
                           kinematic_validation='pending', executable=False,
                           reference_source='Operator confirmation; not independently measured')
    if bundle['manifest'] != expected_manifest or bundle['review'] != expected_review:
        raise ValueError('Table90 manifest/review changed')
    return IDENTITY, hashes
