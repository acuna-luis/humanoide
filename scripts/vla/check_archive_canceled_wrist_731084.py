#!/usr/bin/env python3
"""Transport the pinned 731084 archive checker to Motion for --check only.

The exact source is compiled in memory after SHA256 verification. The prior
status observation is held in a private temporary directory on Motion and
removed before the success receipt. This does not archive, send a goal or
qualify the robot for movement. A lost connection leaves cleanup uncertain.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT/'scripts/vla/runtime/archive_canceled_pico_wrist_731084.py'
EVIDENCE = ROOT.parent/'Humanoide-vla-evidence/SMOLVLA_CURRENT_READONLY_20261110T123648Z/state.json'
OUTROOT = ROOT.parent/'Humanoide-vla-evidence/PICO_731084_ARCHIVE_CHECK'
SOURCE_SHA = 'd178a43a77b711246f7c56edb2acd4354d6d28c8467f01934b2927573f0e7146'
EVIDENCE_SHA = '62da2f4a136218f7de18829ef2dd296b9b825714f812f60b3a6e15e09d2f6db9'

# Executed on Motion, not inside the manipulation container. Its sole input is
# JSON on stdin, and its only permitted entrypoint is --check. The source and
# historical observation are independently pinned before compilation/use.
BOOTSTRAP = r'''import base64,contextlib,hashlib,io,json,os,pathlib,sys,tempfile,types
source_sha = 'd178a43a77b711246f7c56edb2acd4354d6d28c8467f01934b2927573f0e7146'
evidence_sha = '62da2f4a136218f7de18829ef2dd296b9b825714f812f60b3a6e15e09d2f6db9'
value=json.loads(sys.stdin.readline())
if set(value)!={'source','evidence'}: raise ValueError('payload_shape')
source=base64.b64decode(value['source'],validate=True)
evidence=base64.b64decode(value['evidence'],validate=True)
if hashlib.sha256(source).hexdigest()!=source_sha: raise ValueError('source_sha_mismatch')
if hashlib.sha256(evidence).hexdigest()!=evidence_sha: raise ValueError('evidence_sha_mismatch')
out=io.StringIO();err=io.StringIO();ret=None
with tempfile.TemporaryDirectory(prefix='pico731084-check-') as name:
 path=pathlib.Path(name)/'historical-state.json'
 fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_CLOEXEC,0o600)
 with os.fdopen(fd,'wb') as stream:
  stream.write(evidence);stream.flush();os.fsync(stream.fileno())
 mod=types.ModuleType('pico731084_readonly_check')
 exec(compile(source,'<pico731084-reviewed-source>','exec'),mod.__dict__)
 with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
  ret=mod.main(['--check','--terminal-evidence',str(path)])
removed=not os.path.exists(name)
print(json.dumps({'source_sha256':source_sha,'evidence_sha256':evidence_sha,
 'returncode':ret,'checker_stdout':out.getvalue(),'checker_stderr':err.getvalue(),
 'temporary_dir_removed':removed,'movement_commands':0,'archive_requested':False}),flush=True)
if ret!=0 or not removed: raise SystemExit(1)
'''


def sha(data): return hashlib.sha256(data).hexdigest()


def check():
    source, evidence = SOURCE.read_bytes(), EVIDENCE.read_bytes()
    if sha(source) != SOURCE_SHA or sha(evidence) != EVIDENCE_SHA:
        raise ValueError('local_source_or_evidence_sha_mismatch')
    payload = (json.dumps({'source':base64.b64encode(source).decode(),
                           'evidence':base64.b64encode(evidence).decode()})+'\n').encode()
    remote = shlex.join(['python3','-B','-u','-c',BOOTSTRAP])
    command = ['setsid','-w','ssh','-T','-o','StrictHostKeyChecking=yes',
               '-o','ConnectTimeout=5','-o','TCPKeepAlive=yes',
               '-o','PreferredAuthentications=password','-o','PubkeyAuthentication=no',
               '-o','NumberOfPasswordPrompts=1','walker@192.168.11.2',remote]
    env=dict(os.environ, CRUZR_INTERNAL_ASKPASS='1',
             SSH_ASKPASS=str(ROOT/'scripts/cruzr_recover_to_home.sh'),
             SSH_ASKPASS_REQUIRE='force', DISPLAY=os.environ.get('DISPLAY',':0'))
    OUTROOT.mkdir(mode=0o700,parents=True,exist_ok=True)
    outdir=Path(tempfile.mkdtemp(prefix='check-',dir=OUTROOT))
    try:
        result=subprocess.run(command,input=payload,capture_output=True,env=env,timeout=90,check=False)
    except subprocess.TimeoutExpired as exc:
        (outdir/'timeout.txt').write_text('SSH timed out; remote termination and cleanup not confirmed.\n')
        raise RuntimeError('ssh_timeout_remote_cleanup_uncertain:'+str(outdir)) from exc
    (outdir/'stdout.json').write_bytes(result.stdout)
    (outdir/'stderr.txt').write_bytes(result.stderr)
    if result.returncode != 0:
        raise RuntimeError('remote_check_failed:'+str(outdir))
    report=json.loads(result.stdout)
    if (report.get('source_sha256') != SOURCE_SHA or report.get('evidence_sha256') != EVIDENCE_SHA or
            report.get('returncode') != 0 or report.get('temporary_dir_removed') is not True or
            report.get('movement_commands') != 0 or report.get('archive_requested') is not False or
            report.get('checker_stderr') != ''):
        raise ValueError('invalid_remote_receipt:'+str(outdir))
    checked=json.loads(report['checker_stdout'])
    if (checked.get('status') != 'CHECKED_NO_CHANGES' or checked.get('movement_commands') != 0 or
            checked.get('physical_stop_verified') is not False):
        raise ValueError('invalid_checker_result:'+str(outdir))
    return {'status':'CHECKED_NO_CHANGES','evidence':str(outdir),
            'remote_receipt_sha256':sha(result.stdout),'temporary_dir_removed':True,
            'physical_stop_verified':False,'movement_commands':0,'archive_requested':False}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',required=True)
    parser.parse_args(argv)
    try:
        print(json.dumps(check(),ensure_ascii=False,allow_nan=False))
        return 0
    except (OSError,ValueError,KeyError,TypeError,RuntimeError,subprocess.SubprocessError) as exc:
        print('ARCHIVE_READONLY_CHECK_FAILED: '+str(exc),file=sys.stderr)
        return 1


if __name__ == '__main__': raise SystemExit(main())
