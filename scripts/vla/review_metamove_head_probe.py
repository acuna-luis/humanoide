#!/usr/bin/env python3
"""Offline geometric review of the fixed installed head-lower task from measured HOME."""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
from prepare_home_ready_access import (ROOT, JOINT_ORDER, RobotGeometry, common, digest,
    certify_pairs, solid_distance, LocalDisplacementBounds, SelectivePairDistances,
    DirectionalSceneBounds, SubdividedSceneBounds)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('reference','joints','tasks','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    record=json.loads(a.joints.read_text());msg=json.loads(record['stdout'])
    if record['returncode'] or record['stderr'] or len(set(msg['name']))!=len(msg['name']):
        raise ValueError('Invalid named joint state')
    measured=dict(zip(msg['name'],msg['position'],strict=True))
    velocities=dict(zip(msg['name'],msg['velocity'],strict=True))
    start=np.array([measured[n] for n in JOINT_ORDER])
    if not np.isfinite(start).all() or np.max(abs(start))>.02 or any(abs(velocities[n])>.001 for n in JOINT_ORDER):
        raise ValueError('Expected stationary numeric HOME')
    task='/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/cruzr/move_head_lower.xml'
    tasks=json.loads(a.tasks.read_text());xml=tasks[task]['text']
    actions=ET.fromstring(xml).findall('.//Action')
    expected={'ID':'MetaMove','type':'head','location':'single','joint_angles':'0; -0.43','duration':'2'}
    if len(actions)!=1 or actions[0].attrib!=expected:
        raise ValueError('Not the fixed reviewed head task')
    end=start.copy();end[JOINT_ORDER.index('head_yaw_joint')]=0;end[JOINT_ORDER.index('head_pitch_joint')]=-.43
    ref=json.loads(a.reference.read_text());scene=ref['scenarios'][0]
    package=ROOT/'cruzr_s2_description_splint/cruzr_s2_description'
    base=RobotGeometry(package/'urdf/cruzr_s2_v1/cruzr_s2_v1.urdf',package,
                       dict(frame_id='base_link',complete=True,objects=scene['scene_objects']))
    if base.manifest!=ref['model_sources']:raise ValueError('Changed model')
    files=[a.reference,a.joints,a.tasks,Path(__file__),*sorted((ROOT/'scripts/vla').glob('*.py')),
           *sorted((ROOT/'scripts/teleoperation/general_home').glob('*.py'))]
    hashes={str(f.resolve()):digest(f) for f in files}
    local=LocalDisplacementBounds(SelectivePairDistances(base,common,solid_distance),common,JOINT_ORDER)
    model=SubdividedSceneBounds(DirectionalSceneBounds(local,common,JOINT_ORDER),512)
    audit=certify_pairs(model,[start,end],seconds=60,max_depth=10,joint_error_rad=np.deg2rad(1))
    result=dict(scope='FIXED_HEAD_ONLY_NORMAL_COMPLETION_PROBE',task='cruzr/move_head_lower',
        task_path=task,task_sha256=tasks[task]['sha256'],duration_seconds=2,
        start=start.tolist(),end=end.tolist(),joint_order=JOINT_ORDER,
        geometry_audit=audit,model_sources=base.manifest,sources_sha256=hashes,
        physical_approval=False,qualifies_arms_or_estop=False)
    if not base.source_files_unchanged() or any(digest(Path(f))!=h for f,h in hashes.items()):
        raise ValueError('Sources changed')
    with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(audit['counts']))


if __name__=='__main__':main()
