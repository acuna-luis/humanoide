"""Bind a single-stage executor to the reviewed ENTRY410 files and evidence."""
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from prepare_entry360_stages import GROUPS, JOINT_ORDER, stage_xml, staged_path
from prepare_vla_entry_bundle import digest


def checked_hashes(hashes):
    if not isinstance(hashes, dict) or not hashes:
        raise ValueError('Missing source hashes')
    for name, expected in hashes.items():
        if not Path(name).is_file() or digest(Path(name)) != expected:
            raise ValueError('Changed or missing source: '+name)


def load_stage(review_path, step, direction):
    if type(step) is not int or not 1 <= step <= 5 or direction not in ('forward', 'reverse'):
        raise ValueError('Expected step 1..5 and forward/reverse')
    review_path = Path(review_path).resolve()
    review = json.loads(review_path.read_text())
    if (review.get('schema') != 'cruzr-entry410-stages-offline-v1'
            or review.get('candidate') != 'episode_000410' or review.get('joint_order') != JOINT_ORDER):
        raise ValueError('Not the exact ENTRY410 stage schema')
    checked_hashes(review['sources_sha256']); checked_hashes(review['model_sources'])
    audit = review['geometry_audit']
    if (audit['timed_out'] or any(r['status'] == 'UNRESOLVED' for r in audit['pairs'])
            or not any(any(n.startswith('scene:') for n in r['pair']) for r in audit['pairs'])
            or any(r['status'] != 'CERTIFIED_AFFINE_INTERVALS' for r in audit['pairs']
                   if any(n.startswith('scene:') for n in r['pair']))
            or review['configured_limits_check']['configuration_files_match_current_hashes'] is not True):
        raise ValueError('Scene intervals or configured limit check not complete')
    points = review['access_waypoints_20d_rad']
    if len(points) != 6 or len(review['stages']) != 5:
        raise ValueError('Expected five stages')
    expected_points, expected_stages = staged_path(points[0], points[-1])
    if [p.tolist() for p in expected_points] != points or expected_stages != review['stages']:
        raise ValueError('Stage order, duration or endpoints differ from generator')
    stage = review['stages'][step-1]
    name = f'DRAFT_{step:02d}_{stage["type"]}_{stage["location"]}_{direction}.xml'
    xml = review_path.parent/name
    if digest(xml) != review['drafts_sha256'][name] or xml.read_text() != stage_xml(stage, direction == 'reverse'):
        raise ValueError('Stage XML differs from reviewed command')
    root = ET.fromstring(xml.read_text())
    if len(root.findall('.//Action')) != 1:
        raise ValueError('Expected exactly one action')
    start, end = stage['start_20d_rad'], stage['end_20d_rad']
    if direction == 'reverse': start, end = end, start
    return dict(review=str(review_path), review_sha256=digest(review_path), step=step,
                direction=direction, task=f's2_bio_vla/entry410_stage_{step:02d}_{direction}',
                xml=str(xml), xml_sha256=digest(xml), start=start, end=end,
                duration_seconds=stage['duration_seconds'], joint_order=JOINT_ORDER,
                group_joint_order=stage['joint_names'], physical_approval=False)


REQUIRED_EVIDENCE = ('group_mapping', 'loaded_task_identity', 'scene_and_interfaces',
                     'commissioning_motion_and_stop_protocol')


def qualify(path, stage):
    """Require independently reviewed evidence; this executor never issues it."""
    record = json.loads(Path(path).read_text())
    if (record.get('schema') != 'cruzr-entry410-stage-commissioning-release-v1'
            or record.get('review_sha256') != stage['review_sha256']
            or record.get('purpose') != 'supervised_empty_single_stage_trial'
            or record.get('authorized') is not True or not record.get('reviewer')):
        raise ValueError('Missing reviewed commissioning release for this exact bundle')
    checked_hashes(record['evidence_sha256'])
    if set(record['evidence_roles']) != set(REQUIRED_EVIDENCE):
        raise ValueError('Incomplete qualification evidence roles')
    for role in REQUIRED_EVIDENCE:
        if record['evidence_roles'][role] not in record['evidence_sha256']:
            raise ValueError('Unbound evidence: '+role)
    if (not isinstance(record.get('task_list_sha256'), str) or len(record['task_list_sha256']) != 64
            or not record.get('boot_id') or not str(record.get('pid1_start_ticks', '')).isdigit()):
        raise ValueError('Missing exact loaded registry/process identity')
    executor_sources = [Path(__file__), Path(__file__).with_name('run_entry410_stage.py'),
                        Path(__file__).parent/'runtime/entry410_single_stage_remote.py',
                        Path(__file__).parent/'runtime/entry410_installed_task_admission.py']
    for source in executor_sources:
        if record.get('executor_sha256', {}).get(str(source.resolve())) != digest(source):
            raise ValueError('Executor not bound to qualification: '+str(source))
    for key in ('position_tolerance_rad', 'velocity_tolerance_rad_s', 'stationary_joint_tolerance_rad'):
        value = record.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value <= .02:
            raise ValueError('Invalid qualified tolerance: '+key)
    if stage['task'] not in record['loaded_tasks'] or record['loaded_tasks'][stage['task']] != stage['xml_sha256']:
        raise ValueError('Selected task is not qualified as loaded')
    return record
