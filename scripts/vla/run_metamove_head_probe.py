#!/usr/bin/env python3
"""Fixed supervised head-lower trial; never enables ENTRY, installs or reloads."""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
from install_entry410_stages import ssh, ROOT

TASK_PATH='/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/cruzr/move_head_lower.xml'
TASK_SHA='f3a73626f97b471d4a0a03c98c24de32243651116c497328e69b5ddc57ea46c1'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    mode=p.add_mutually_exclusive_group(required=True);mode.add_argument('--check',action='store_true');mode.add_argument('--run',action='store_true')
    p.add_argument('--physical-confirmed',action='store_true',help='Current operator confirmation, for this head-only supervised trial')
    p.add_argument('--review',type=Path,required=True);p.add_argument('--evidence-dir',type=Path,required=True)
    a=p.parse_args()
    if a.run and not a.physical_confirmed:p.error('Current physical supervision must be confirmed')
    if a.evidence_dir.exists():p.error('Choose a new evidence directory; never retry an uncertain action')
    review=json.loads(a.review.read_text())
    if review['scope']!='FIXED_HEAD_ONLY_NORMAL_COMPLETION_PROBE' or review['task_sha256']!=TASK_SHA:
        raise ValueError('Not the fixed head-only reviewed task')
    for path,value in {**review['sources_sha256'],**review['model_sources']}.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=value:raise ValueError('Review source changed: '+path)
    audit=review['geometry_audit']
    if audit['timed_out'] or any(r['status']=='UNRESOLVED' for r in audit['pairs']):
        raise ValueError('Unresolved geometric review')
    # This is a head-only supervised commissioning trial. The review retains
    # every internal CAD overlap; it is not a qualification of ENTRY or arms.
    a.evidence_dir.mkdir(parents=True)
    with (ROOT/'.metamove-head-probe.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        helper=ROOT/'scripts/vla/runtime/metamove_head_probe.py'
        intent=dict(time_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            task='cruzr/move_head_lower',mode='run' if a.run else 'check',
            physical_confirmation=a.physical_confirmed,normal_completion_only=True,
            source_sha256={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in (Path(__file__).resolve(),helper,a.review.resolve())})
        (a.evidence_dir/'intent.json').write_text(json.dumps(intent,indent=2)+'\n')
        with (a.evidence_dir/'preflight.log').open('w') as f:
            result=subprocess.run(['bash',str(ROOT/'scripts/vla/audit_vla_live_preflight_e6_0g.sh'),'--check','--expect-released'],stdout=f,stderr=subprocess.STDOUT,timeout=150)
        if result.returncode:raise RuntimeError('Live preflight failed; no action sent')
        observed=ssh('import json,hashlib;from pathlib import Path;print(json.dumps(hashlib.sha256(Path('+repr(TASK_PATH)+').read_bytes()).hexdigest()))')
        if observed!=TASK_SHA:raise RuntimeError('Installed head XML changed; no action sent')
        (a.evidence_dir/'installed-hash.json').write_text(json.dumps(observed)+'\n')
        env=dict(os.environ,SSH_ASKPASS=str(ROOT/'scripts/vla/audit_vla_live_preflight_e6_0g.sh'),SSH_ASKPASS_REQUIRE='force',CRUZR_INTERNAL_ASKPASS='1',DISPLAY=os.environ.get('DISPLAY',':0'))
        remote='docker exec -i walker-ros.ros2-1 bash -lc '+shlex.quote('source /opt/ros/humble/setup.bash; export ROS2CLI_DISABLE_DAEMON=1; timeout 35 python3 - '+('--run' if a.run else '--check'))
        command=['setsid','-w','ssh','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=5','-o','PreferredAuthentications=password','-o','PubkeyAuthentication=no','walker@192.168.11.2',remote]
        with (a.evidence_dir/'trace.jsonl').open('w') as out,(a.evidence_dir/'stderr.log').open('w') as err:
            result=subprocess.run(command,input=helper.read_text(),text=True,stdout=out,stderr=err,env=env,timeout=45)
        rows=[json.loads(line) for line in (a.evidence_dir/'trace.jsonl').read_text().splitlines()]
        expected='HEAD_PROBE_SUCCEEDED_AND_SETTLED' if a.run else 'HEAD_PROBE_READ_ONLY_PASSED'
        passed=result.returncode==0 and any(r.get('status')==expected for r in rows)
        (a.evidence_dir/'result.json').write_text(json.dumps(dict(passed=passed,returncode=result.returncode,expected=expected,physical_approval_of_ENTRY=False))+'\n')
        if not passed:raise RuntimeError('Probe failed; no automatic retry or recovery. Inspect trace before further commands')
        print(expected)


if __name__=='__main__':main()
