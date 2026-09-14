#!/usr/bin/env python3
"""Execute one qualified ENTRY410 stage. Never install, reload or chain stages."""
import argparse
import base64
import fcntl
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time

from entry410_stage_contract import load_stage, qualify
from prepare_vla_entry_bundle import ROOT, digest
from general_home.trace_analysis import ACTUATORS


def command(argv, log, *, timeout=120, env=None):
    with log.open('x') as stream:
        result = subprocess.run(argv, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout, env=env)
    if result.returncode: raise RuntimeError(f'Command failed ({result.returncode}); see {log}')
    return log.read_text()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true', help='Local bundle verification; no network')
    mode.add_argument('--preflight', action='store_true', help='Read-only live preflight and release verification')
    mode.add_argument('--run', action='store_true', help='One single stage, only with reviewed commissioning release')
    mode.add_argument('--prepare-installation', type=Path, metavar='NEW_DIRECTORY',
                      help='Prepare all ten XML and additive task registry fragment locally; no network')
    p.add_argument('--review', type=Path, required=True)
    p.add_argument('--step', type=int, choices=range(1, 6), required=True)
    p.add_argument('--direction', choices=('forward', 'reverse'), required=True)
    p.add_argument('--qualification', type=Path)
    p.add_argument('--evidence-dir', type=Path)
    args = p.parse_args()
    stage = load_stage(args.review, args.step, args.direction)
    if args.prepare_installation:
        destination = args.prepare_installation
        if destination.exists(): p.error('Installation package directory must be new')
        stages = [load_stage(args.review, step, direction) for step in range(1, 6) for direction in ('forward', 'reverse')]
        destination.mkdir(parents=True)
        registry = []
        for selected in stages:
            name = selected['task'].split('/')[-1]
            (destination/(name+'.xml')).write_bytes(Path(selected['xml']).read_bytes())
            registry.append(name+':\n  motion_id: '+json.dumps(selected['task'])+'\n  json_args: \'{"Reverse": false,"TimeRatio": 1.0}\'\n  cmd: "start"\n')
        (destination/'task_list.ADDITIVE_FRAGMENT.yaml').write_text('\n'.join(registry))
        (destination/'manifest.json').write_text(json.dumps(dict(stages=stages, installable=False,
            status='PREPARED_ONLY_REQUIRES_QUALIFIED_INSTALLATION_AND_LOADING',
            file_sha256={f.name:digest(f) for f in sorted(destination.iterdir())}), indent=2)+'\n')
        print('LOCAL_INSTALLATION_PACKAGE_PREPARED; no robot files changed or reloaded'); return
    if args.check:
        print(json.dumps(dict(status='LOCAL_STAGE_INTEGRITY_OK_NOT_MOVEMENT_APPROVAL', **stage), indent=2)); return
    if not args.qualification:
        p.error('--qualification is required; existing stage drafts are not execution authorization')
    release = qualify(args.qualification, stage)
    if not args.evidence_dir or args.evidence_dir.exists():
        p.error('Choose a new --evidence-dir')
    args.evidence_dir.mkdir(parents=True)
    evidence = args.evidence_dir.resolve()
    lock = (ROOT/'.entry410-stage.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    (evidence/'stage.json').write_text(json.dumps(stage, indent=2)+'\n')
    (evidence/'qualification.json').write_bytes(args.qualification.read_bytes())
    command(['bash', str(ROOT/'scripts/vla/audit_vla_live_preflight_e6_0g.sh'), '--check', '--expect-released'],
            evidence/'preflight.log', timeout=150)
    if args.preflight:
        print('READ_ONLY_PREFLIGHT_OK; remote stage admission still required immediately before motion'); return
    phrase = f'ENSAYO ENTRY410 ETAPA {args.step} {args.direction}: VACIO, ZONA LIBRE, CONTROL EXCLUSIVO Y PERSONA EN E-STOP'
    print(phrase, flush=True)
    if not sys.stdin.isatty() or input('Escriba la frase para esta etapa: ').strip() != phrase:
        raise RuntimeError('Current single-stage operator confirmation missing; no motion sent')
    # Recheck after the operator prompt; do not use the earlier snapshot as a motion permit.
    command(['bash', str(ROOT/'scripts/vla/audit_vla_live_preflight_e6_0g.sh'), '--check', '--expect-released'],
            evidence/'preflight-after-confirmation.log', timeout=150)
    if load_stage(args.review, args.step, args.direction) != stage:
        raise RuntimeError('Bundle changed')
    if qualify(args.qualification, stage) != release:
        raise RuntimeError('Qualification changed')
    helper = ROOT/'scripts/vla/runtime/entry410_single_stage_remote.py'
    payload = dict(stage=stage, release=release, actuator_names=ACTUATORS)
    encoded = base64.b64encode(json.dumps(payload, allow_nan=False).encode()).decode()
    code = 'PAYLOAD_B64='+repr(encoded)+'\n'+helper.read_text()
    (evidence/'remote-helper.sha256').write_text(digest(helper)+'\n')
    (evidence/'dispatch-intent.json').write_text(json.dumps(dict(time_ns=time.time_ns(), task=stage['task'], retry=False))+'\n')
    env = dict(os.environ, SSH_ASKPASS=str(ROOT/'scripts/vla/audit_vla_live_preflight_e6_0g.sh'),
               SSH_ASKPASS_REQUIRE='force', CRUZR_INTERNAL_ASKPASS='1', DISPLAY=os.environ.get('DISPLAY', ':0'))
    admission = ROOT/'scripts/vla/runtime/entry410_installed_task_admission.py'
    remote = ('docker exec walker-motion.manipulation_robot_app-1 python3 -c '+shlex.quote(admission.read_text())
              +' '+shlex.quote(encoded)+' && docker exec -i walker-ros.ros2-1 bash -lc '+shlex.quote(
        'source /opt/ros/humble/setup.bash; export ROS2CLI_DISABLE_DAEMON=1; python3 -'))
    argv = ['setsid', '-w', 'ssh', '-o', 'ConnectTimeout=5', '-o', 'ConnectionAttempts=1',
            '-o', 'StrictHostKeyChecking=yes', '-o', 'PreferredAuthentications=password',
            '-o', 'PubkeyAuthentication=no', 'walker@192.168.11.2', remote]
    # No automatic retry, recovery or subsequent stage on any result.
    try:
        with (evidence/'action.jsonl').open('x') as out:
            completed = subprocess.run(argv, input=code, text=True, stdout=out, stderr=subprocess.STDOUT,
                                       env=env, timeout=stage['duration_seconds']+90)
        if completed.returncode: raise RuntimeError('Remote action/admission failed')
        records = [json.loads(line) for line in (evidence/'action.jsonl').read_text().splitlines() if line.startswith('{')]
        if not records or records[-1].get('status') != 'SINGLE_STAGE_SUCCEEDED_AND_SETTLED':
            raise RuntimeError('No verified settled completion')
        print('ONE_STAGE_COMPLETE; inspect physically before requesting any next stage')
    except BaseException:
        (evidence/'outcome-uncertain.json').write_text('{"automatic_retry":false,"further_motion_permitted":false}\n')
        print('NO RETRY. If movement/contact is unexpected, operate E-stop; inspect robot and logs.', file=sys.stderr)
        raise
    finally:
        (evidence/'evidence.sha256').write_text(''.join(digest(f)+'  '+f.name+'\n' for f in sorted(evidence.iterdir()) if f.is_file() and f.name != 'evidence.sha256'))


if __name__ == '__main__': main()
