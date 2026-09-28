#!/usr/bin/env python3
"""Promote the physically tested v8 XML to automatic HOME under measured E-stop.

Never releases stops, reloads processes or sends movement goals.
"""
import argparse
import base64
import datetime as dt
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import cruzr_install_internal_home_body_first as base
from review_home_v8_early_roll import CANDIDATE, check_structure

SHA = 'd9e9462792b41300d352604b53ea2a4890a9382e942321990708f6ded2e26ccb'


def measure(evidence):
    before = base.motion_identity()
    command = ('env ROSA_LOG_LEVEL=ERROR rosa topic echo --once --no-daemon '
               '/mc/actuator_state mc_state_msgs/msg/ActuatorState '
               '--qos-reliability best_effort --qos-durability volatile')
    result = base.execute('motion', base.ros(base.CONTAINER, command, True))
    (evidence/'read.json').write_text(json.dumps(result, indent=2)+'\n')
    sample = base.require(result, 'actuator_state')
    gate = subprocess.run([sys.executable, str(base.HOME_GATE), '--home-tolerance', '0.02'],
                          input=sample, capture_output=True, text=True, timeout=10)
    (evidence/'actuator_state.json').write_text(sample)
    (evidence/'home_gate.log').write_text(gate.stdout+gate.stderr)
    if gate.returncode or 'MEASURED_HOME=1' not in gate.stdout.split():
        raise RuntimeError('HOME measurement failed; no installation')
    after = base.motion_identity()
    if before != after:
        raise RuntimeError('Motion changed during measurement')
    record = dict(after, measured_epoch=time.time(), measured_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                  gate=gate.stdout.split())
    (evidence/'home_posture.json').write_text(json.dumps(record, indent=2)+'\n')
    base.POSTURE_RECORD.write_text(json.dumps(record, indent=2)+'\n')
    print(gate.stdout, end='')


def require_home_continuity(evidence):
    """Accept a restarted app only with retained, task-free successor journals.

    This does not qualify controller health or authorize release/movement.
    The caller separately requires the main stop immediately before writing.
    """
    record = json.loads(base.POSTURE_RECORD.read_text())
    age = time.time() - float(record.get('measured_epoch', 0))
    if not 0 <= age <= base.POSTURE_MAX_AGE_S:
        raise RuntimeError('HOME measurement expired')
    current = base.motion_identity()
    if current['boot_id'] != record['boot_id']:
        raise RuntimeError('Robot rebooted since HOME measurement')
    if current['robot_app_log'] == record['robot_app_log']:
        base.require_recent_home()
        return
    code = r"""
from pathlib import Path
import json,hashlib
old=Path(OLD)
paths=sorted(old.parent.glob('robot_app.*.log'))
if old not in paths:raise SystemExit('Original journal missing')
paths=paths[paths.index(old):]
rows=[]
for path in paths:
 data=path.read_bytes()
 rows.append({'path':str(path),'tasks':data.count(b'BTree task: '),
              'sha256':hashlib.sha256(data).hexdigest(),
              'heartbeat_exit':b'Now robot_app is done because delta_t between two beat is:' in data,
              'waiting_controllers':b'ListControllers]: service not available' in data})
print(json.dumps(rows))
""".replace('OLD', repr(record['robot_app_log']), 1)
    result = base.execute('motion', ['python3', '-c', code])
    (evidence/'continuity-journals.json').write_text(json.dumps(result, indent=2)+'\n')
    rows = json.loads(base.require(result, 'journal continuity'))
    validate_journals(record, current, rows)
    if base.motion_identity() != current:
        raise RuntimeError('Motion changed while inspecting journals')
    (evidence/'continuity-record.json').write_text(json.dumps(
        {'original_measurement':record,'current_identity':current,'qualification':'disk installation under stop only'},
        indent=2)+'\n')
    print('HOME_CONTINUITY=retained journals; no task since measurement; app restarted; DISK_ONLY=1')


def validate_journals(record, current, rows):
    if len(rows) < 2 or rows[0]['path'] != record['robot_app_log']:
        raise RuntimeError('Missing original journal')
    if rows[-1]['path'] != current['robot_app_log']:
        raise RuntimeError('Successor journal chain inconsistent')
    if rows[0]['tasks'] != record['btree_tasks'] or any(r['tasks'] for r in rows[1:]):
        raise RuntimeError('Task occurred after HOME measurement')
    if not all(r['heartbeat_exit'] for r in rows[:-1]) or not rows[-1]['waiting_controllers']:
        raise RuntimeError('Restart history not explained by retained heartbeat logs')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group()
    g.add_argument('--measure-home', action='store_true')
    g.add_argument('--preflight', action='store_true')
    g.add_argument('--install', action='store_true')
    g.add_argument('--check', action='store_true')
    p.add_argument('--evidence', type=Path)
    a = p.parse_args()
    check_structure()
    data = CANDIDATE.read_bytes()
    if hashlib.sha256(data).hexdigest() != SHA:
        raise RuntimeError('Candidate differs from physically tested bytes')
    if not (a.measure_home or a.preflight or a.install):
        print('LOCAL_CHECK_OK=v8; nominal_seconds=13.45; MOVEMENT_COMMANDS=0'); return
    if a.evidence is None:
        p.error('--evidence required for robot access')
    a.evidence.mkdir(parents=True, exist_ok=False)
    if a.measure_home:
        measure(a.evidence); return
    base.LABELS[SHA] = 'early-roll-v8-13s'
    old_sha = base.status(a.evidence)
    if a.preflight: return
    if old_sha == SHA:
        print('INSTALL_NOOP=already-exact'); return
    if old_sha != base.NEW_SHA:
        raise RuntimeError('Only verified v7 baseline may be replaced')
    require_home_continuity(a.evidence)
    before = base.require(base.execute('motion', ['docker','exec',base.CONTAINER,'cat',base.TARGET]), 'external backup')
    if hashlib.sha256(before.encode()).hexdigest() != old_sha:
        raise RuntimeError('Baseline changed during backup')
    (a.evidence/'home.v7.before.xml').write_text(before)
    install = base.INSTALL.replace('Physical trial pending.', 'Separate v8 task physically tested once; automatic boot validation pending.')
    cmd = ['docker','exec','-u','0',base.CONTAINER,'python3','-c',install,
           base.TARGET,old_sha,SHA,base64.b64encode(data).decode()]
    code = base.ESTOP_CHECK+'\nimport sys\n'+f'cmd={cmd!r}\n'+(
        "r=subprocess.run(cmd,capture_output=True,text=True,timeout=5)\n"
        "print(r.stdout,end='')\nprint(r.stderr,end='',file=sys.stderr)\nraise SystemExit(r.returncode)\n")
    result = base.execute('motion', ['python3','-c',code])
    (a.evidence/'installation.json').write_text(json.dumps(result, indent=2)+'\n')
    print(base.require(result, 'installation'), end='')
    after = a.evidence/'after'; after.mkdir()
    if base.status(after) != SHA:
        raise RuntimeError('Postcheck failed; keep stop pressed, no retry')
    (a.evidence/'home.v8.installed.xml').write_bytes(data)
    print('V8_INSTALLED=1; KEEP_ESTOP_PRESSED=1; RESTARTS=0; MOVEMENT_COMMANDS=0; BOOT_TEST=pending')


if __name__ == '__main__':
    main()
