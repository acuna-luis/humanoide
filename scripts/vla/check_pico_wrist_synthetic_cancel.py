#!/usr/bin/env python3
"""Isolated ROS watchdog diagnostic: synthetic goal, never physical action.

Starts a fake ArmTask server and a copy of the guard with all action names
remapped to its random namespace. No task is staged or sent to the robot.
The fake server and copied guard share live ROS telemetry; this does not test
the robot's real manipulation server, physical cancellation, or braking.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import subprocess
import sys
import time
import uuid

import check_arm_from_pico_supervised as preflight
import check_arm_native_bridge_live as passive
import pico_wrist_pc_heartbeat as heartbeat
import pico_wrist_review_binding as review
import prepare_pico_wrist_native_probe as probe
import run_head_from_pico_supervised as head
import run_pico_wrist_native_trial as trial

ROOT=Path(__file__).resolve().parents[2]
VLA=ROOT/'scripts/vla'
RUNTIME=VLA/'runtime'
EVIDENCE=ROOT.parent/'Humanoide-vla-evidence/PICO_SYNTHETIC_CANCEL_CHECK'
REAL='/mc/manipulation/action'
ENDPOINT=re.compile(r'/codex_smolvla_diag_[0-9a-f]{32}/action\Z')


def derived_guard(original, endpoint):
    if not isinstance(endpoint,str) or ENDPOINT.fullmatch(endpoint) is None:
        raise ValueError('synthetic_endpoint_required')
    if not isinstance(original,str) or original.count(REAL)!=4:
        raise ValueError('guard_source_layout_changed')
    result=original.replace(REAL,endpoint)
    if REAL in result or result.count(endpoint)!=4:
        raise ValueError('guard_remap_incomplete')
    # Diagnostic process is bounded even after SSH loss. The copied guard can
    # never command the physical action endpoint and is not production code.
    result=('import threading,os\n'
            'timer=threading.Timer(70.0,lambda: os._exit(88));timer.daemon=True;timer.start()\n')+result
    compile(result,'<synthetic-guard>','exec')
    return result


def build_sources(endpoint):
    _,original,_,sources=trial.source_bundle(include_sources=True)
    guard=derived_guard(original,endpoint)
    server_source=(RUNTIME/'synthetic_wrist_action_server.py').read_text()
    compile(server_source,'<synthetic-server>','exec')
    server=passive.module_code({'synthetic_wrist_action_server':
                               (server_source,str(RUNTIME/'synthetic_wrist_action_server.py'))})
    server+=('import json\np=json.loads(sys.stdin.readline())\n'
             'raise SystemExit(sys.modules["synthetic_wrist_action_server"].main('
             '["--endpoint",p["endpoint"],"--goal-id",p["goal_id"]]))\n')
    sources['pico_wrist_synthetic_cancel_host']=(
        (RUNTIME/'pico_wrist_synthetic_cancel_host.py').read_text(),
        str(RUNTIME/'pico_wrist_synthetic_cancel_host.py'))
    host=passive.module_code(sources)
    host+=('import json\nprint(json.dumps({"event":"BRIDGE_READY"}),flush=True)\n'
           'p=json.loads(sys.stdin.readline())\n'
           'print(json.dumps(sys.modules["pico_wrist_synthetic_cancel_host"].check(p),'
           'allow_nan=False),flush=True)\n')
    return host,original,guard,server


def drive(process,session,started,outdir):
    selector=selectors.DefaultSelector()
    for stream,name in ((process.stdout,'stdout'),(process.stderr,'stderr')):
        os.set_blocking(stream.fileno(),False);selector.register(stream,selectors.EVENT_READ,name)
    pump=None;buffer=bytearray();ready=False;ack=False;result=None
    try:
        with (outdir/'stdout.jsonl').open('x') as out, (outdir/'stderr.log').open('x') as err:
            deadline=time.monotonic()+90
            while selector.get_map():
                if time.monotonic()>=deadline: raise TimeoutError('synthetic_check_timeout_cleanup_uncertain')
                if pump is not None and pump.failed.is_set(): raise RuntimeError('pc_heartbeat_failed')
                for key,_ in selector.select(.1):
                    data=os.read(key.fd,65536)
                    if not data: selector.unregister(key.fileobj);continue
                    target=out if key.data=='stdout' else err
                    target.write(data.decode('utf-8','replace'));target.flush()
                    if key.data=='stderr': continue
                    buffer.extend(data)
                    if len(buffer)>1_000_000: raise ValueError('synthetic_output_excessive')
                    while b'\n' in buffer:
                        line,_,remaining=bytes(buffer).partition(b'\n');buffer=bytearray(remaining)
                        row=json.loads(line);event=row.get('event')
                        if event=='HOST_PREFLIGHT_READY':
                            challenge=row.get('challenge')
                            if (ack or row.get('session_id')!=session or not isinstance(challenge,str)
                                    or re.fullmatch('[0-9a-f]{32}',challenge) is None):
                                raise ValueError('invalid_preflight_challenge')
                            reply={'event':'pc_preflight_ack','session_id':session,
                                   'challenge':challenge,'inventory_age_s':time.monotonic()-started}
                            trial.docker_launch.write_stream(process.stdin.fileno(),
                                (json.dumps(reply)+'\n').encode(),1);ack=True
                        elif event=='HOST_HEARTBEAT_READY':
                            if not ack or ready or row.get('session_id')!=session:
                                raise ValueError('invalid_heartbeat_start')
                            pump=heartbeat.PcHeartbeatPump(process.stdin.fileno(),session);ready=True
                        elif event=='pc_ping':
                            if pump is None: raise ValueError('ping_before_ready')
                            pump.submit(row)
                        elif row.get('status')=='SYNTHETIC_WATCHDOG_CANCEL_PASSED':
                            if result is not None: raise ValueError('duplicate_synthetic_result')
                            result=row
            if buffer.strip(): raise ValueError('synthetic_output_truncated')
        rc=process.wait(timeout=3)
        if (rc!=0 or not ack or not ready or not isinstance(result,dict) or
                result.get('physical_goals')!=0 or result.get('synthetic_goals')!=1 or
                result.get('synthetic_cancel_accepted') is not True or
                result.get('synthetic_terminal_status')!=5 or
                result.get('physical_control_qualified') is not False):
            raise RuntimeError('synthetic_cancel_not_confirmed')
        return result
    finally:
        if pump is not None: pump.close()
        selector.close()


def check(manifest_path,urdf_path,transmissions_path,binding,binding_sha256):
    manifest_raw=manifest_path.read_bytes();urdf_raw=urdf_path.read_bytes()
    transmissions_raw=transmissions_path.read_bytes()
    manifest=json.loads(manifest_raw);urdf=urdf_raw.decode();transmissions=transmissions_raw.decode()
    probe.validate(manifest,urdf,transmissions)
    reviewed=review.compare_candidate_inputs(binding,binding_sha256,manifest_raw,urdf_raw,transmissions_raw)
    index=(binding/'bundle-evidence.json').read_bytes()
    if hashlib.sha256(index).hexdigest()!=reviewed['bundle_evidence_sha256']:
        raise ValueError('binding_index_changed')
    endpoint='/codex_smolvla_diag_'+uuid.uuid4().hex+'/action'
    host,original,guard,server=build_sources(endpoint)
    if hashlib.sha256(original.encode()).hexdigest()!=json.loads(index)['sha256']['bundle-guard.py']:
        raise ValueError('reviewed_guard_source_changed')
    mode,started,_=preflight.preflight()
    session_id=uuid.uuid4().hex
    session={'schema':'cruzr_head_pico_preflight_v1','task_sha256':preflight.ARM_TASK_SHA,
             'pico_sha256':head.admission.PICO_SHA,'work_mode':mode,'operator_confirmed':False,
             'controller_status_writers_checked':True,'age_at_handoff_s':time.monotonic()-started,
             'session_id':session_id,'mode':'check'}
    payload={'session':session,'manifest':manifest,'urdf_text':urdf,'transmissions_text':transmissions,
             'guard_source':guard,'guard_sha256':hashlib.sha256(guard.encode()).hexdigest(),
             'synthetic_server_source':server,'synthetic_server_sha256':hashlib.sha256(server.encode()).hexdigest(),
             'endpoint':endpoint,'goal_id':str(uuid.uuid4())}
    sentinel='PICO_HOST_END_'+uuid.uuid4().hex
    EVIDENCE.mkdir(mode=0o700,parents=True,exist_ok=True)
    outdir=EVIDENCE/('check-'+session_id);outdir.mkdir(mode=0o700)
    (outdir/'sources.json').write_text(json.dumps({'guard_original_sha256':hashlib.sha256(original.encode()).hexdigest(),
        'guard_derived_sha256':payload['guard_sha256'],'server_sha256':payload['synthetic_server_sha256'],
        'host_sha256':hashlib.sha256(host.encode()).hexdigest(),'endpoint':endpoint},indent=2)+'\n')
    print('EVIDENCIA='+str(outdir),flush=True)
    env=dict(os.environ,CRUZR_INTERNAL_ASKPASS='1',SSH_ASKPASS=str(ROOT/'scripts/cruzr_recover_to_home.sh'),
             SSH_ASKPASS_REQUIRE='force',DISPLAY=os.environ.get('DISPLAY',':0'))
    process=subprocess.Popen(trial.host_command(sentinel),stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,env=env,bufsize=0)
    try:
        trial.docker_launch.write_stream(process.stdin.fileno(),
            (host+'\n'+sentinel+'\n'+json.dumps(payload,allow_nan=False)+'\n').encode(),10)
        result=drive(process,session_id,started,outdir)
    finally:
        if process.poll() is None:
            process.terminate()
            try:process.wait(timeout=3)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=3)
        for stream in (process.stdin,process.stdout,process.stderr):
            if stream is not None:stream.close()
    print(json.dumps({'status':result['status'],'evidence':str(outdir),
                      'physical_goals':0,'physical_stop_verified':False,
                      'limitations':result['limitations']}),flush=True)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',required=True,action='store_true')
    for name in ('manifest','urdf','transmissions','binding'):
        parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--binding-sha256',required=True)
    args=parser.parse_args(argv)
    try:
        check(args.manifest,args.urdf,args.transmissions,args.binding,args.binding_sha256)
        return 0
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,subprocess.SubprocessError) as exc:
        print('SYNTHETIC_CANCEL_CHECK_FAILED:'+str(exc),file=sys.stderr,flush=True)
        return 1


if __name__=='__main__':raise SystemExit(main())
