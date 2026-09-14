"""Bind corrected READY access and ENTRY stages; never issue a physical release."""
import json
from pathlib import Path

from entry410_stage_contract import checked_hashes, load_stage, qualify
from prepare_entry360_stages import JOINT_ORDER, staged_path, stage_xml
from prepare_vla_entry_bundle import digest
from audit_ready_controller_contract import configuration_checks


def checked_manifest(path):
    m=json.loads(Path(path).read_text())
    if m['schema']!='cruzr-ready410-head063-trial-v1' or m['part'] not in ('access','entry'):
        raise ValueError('Unexpected corrected trial manifest')
    required=[Path(m[k]).resolve() for k in ('access_review','entry_review','reference','hardware_snapshot')]
    required += [Path(__file__).resolve(),Path(__file__).with_name('audit_ready_controller_contract.py').resolve()]
    if any(str(p) not in m['bindings'] for p in required):
        raise ValueError('Missing required trial identity binding')
    checked_hashes(m['bindings'])
    snapshot=json.loads(Path(m['hardware_snapshot']).read_text())
    for key in ('access_review','entry_review'):
        r=json.loads(Path(m[key]).read_text())
        if r['sources_sha256'].get(str(Path(m['reference']).resolve()))!=digest(Path(m['reference'])):
            raise ValueError('Reviews do not bind the same reference')
        check=configuration_checks(r,snapshot)
        if not check['configured_group_order_matches'] or check['hardware_nominal_outside']:
            raise ValueError('Controller order or hardware position check failed')
    return m


def access_stage(path, step, direction):
    if type(step) is not int or step not in range(1,6) or direction not in ('forward','reverse'):
        raise ValueError('Invalid stage selection')
    path=Path(path).resolve(); r=json.loads(path.read_text())
    if r['schema']!='cruzr-measured-start-ready-access-offline-v1' or r['joint_order']!=JOINT_ORDER:
        raise ValueError('Unexpected access schema')
    if r.get('position_source')!='/mc/whole_joint_states:name' or r.get('actuator_coordinates_used_for_geometry') is not False:
        raise ValueError('Access must use named joint coordinates')
    checked_hashes(r['sources_sha256']);checked_hashes(r['model_sources'])
    audit=r['geometry_audit']; scene=[p for p in audit['pairs'] if any(n.startswith('scene:') for n in p['pair'])]
    if (audit['timed_out'] or not scene or any(p['status']=='UNRESOLVED' for p in audit['pairs'])
            or any(p['status']!='CERTIFIED_AFFINE_INTERVALS' for p in scene)):
        raise ValueError('Access scene review incomplete')
    stages=r['stages']
    if len(stages)!=5 or staged_path(stages[0]['start_20d_rad'],stages[-1]['end_20d_rad'])[1]!=stages:
        raise ValueError('Access stages differ from generator')
    stage=stages[step-1]; name=f'DRAFT_access_{step:02d}_{direction}.xml'; xml=path.parent/name
    if digest(xml)!=r['drafts_sha256'][name] or xml.read_text()!=stage_xml(stage,direction=='reverse'):
        raise ValueError('Access XML differs from generator/review')
    start,end=stage['start_20d_rad'],stage['end_20d_rad']
    if direction=='reverse':start,end=end,start
    return dict(review=str(path),review_sha256=digest(path),step=step,direction=direction,
        xml=str(xml),xml_sha256=digest(xml),start=start,end=end,
        duration_seconds=stage['duration_seconds'],joint_order=JOINT_ORDER,
        group_joint_order=stage['joint_names'],
        geometry_joint_error_rad=audit.get('joint_error_scenario_rad'),physical_approval=False)


def load_trial_stage(path, step, direction):
    path=Path(path).resolve(); m=checked_manifest(path)
    access=access_stage(m['access_review'],5,'forward')
    entry=load_stage(m['entry_review'],1,'forward')
    if access['end']!=entry['start'] or access['end'][JOINT_ORDER.index('head_pitch_joint')]!=-.63:
        raise ValueError('Access/ENTRY discontinuity or uncorrected head target')
    part=m['part']
    selected=(access_stage if part=='access' else load_stage)(m[part+'_review'],step,direction)
    selected.update(review=str(path),review_sha256=digest(path),trial_part=part,
        task=f's2_bio_vla/ready410_h63_{part}_{step:02d}_{direction}')
    return selected


def all_trial_stages(path):
    path=Path(path).resolve(); bundle=json.loads(path.read_text())
    if bundle.get('schema')!='cruzr-ready410-head063-bundle-v1':
        raise ValueError('Unexpected trial bundle')
    checked_hashes(bundle['manifests_sha256'])
    if set(bundle['manifests'])!={'access','entry'}:
        raise ValueError('Both trial parts required')
    result=[]
    manifests=[]
    for part in ('access','entry'):
        manifest=Path(bundle['manifests'][part]).resolve()
        if str(manifest) not in bundle['manifests_sha256']:
            raise ValueError('Unbound trial manifest')
        m=checked_manifest(manifest);manifests.append(m)
        if m['part']!=part: raise ValueError('Wrong trial part')
        result.extend(load_trial_stage(manifest,i,d) for i in range(1,6) for d in ('forward','reverse'))
    if any(manifests[0][k]!=manifests[1][k] for k in ('access_review','entry_review','reference','hardware_snapshot','bindings')):
        raise ValueError('Mixed trial bundle')
    return result


def qualify_trial(path, stage):
    release=qualify(path,stage)
    # Bind the extra access loader/wrapper as well as the common transport.
    for source in (Path(__file__),Path(__file__).with_name('run_ready410_trial.py')):
        if release.get('executor_sha256',{}).get(str(source.resolve()))!=digest(source):
            raise ValueError('Corrected trial executor not bound to release')
    return release
