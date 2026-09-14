#!/usr/bin/env python3
"""Prepare a disk-only ENTRY410 installation, or apply it with main E-stop active."""
import argparse
import base64
import json
import os
from pathlib import Path
import shlex
import subprocess

from entry410_stage_contract import load_stage
from prepare_vla_entry_bundle import ROOT, digest


def ssh(code, args=()):
    env = dict(os.environ, SSH_ASKPASS=str(ROOT/'scripts/vla/audit_vla_live_preflight_e6_0g.sh'),
               SSH_ASKPASS_REQUIRE='force', CRUZR_INTERNAL_ASKPASS='1', DISPLAY=os.environ.get('DISPLAY', ':0'))
    remote = 'docker exec walker-motion.manipulation_robot_app-1 python3 -c '+shlex.quote(code)
    remote += ''.join(' '+shlex.quote(arg) for arg in args)
    result = subprocess.run(['setsid', '-w', 'ssh', '-o', 'ConnectTimeout=5', '-o', 'ConnectionAttempts=1',
                             '-o', 'StrictHostKeyChecking=yes', '-o', 'PreferredAuthentications=password',
                             '-o', 'PubkeyAuthentication=no', 'walker@192.168.11.2', remote],
                            env=env, capture_output=True, text=True, timeout=30)
    if result.returncode: raise RuntimeError(result.stderr+result.stdout)
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--plan', action='store_true', help='Read remote registry and prepare local plan; no remote writes')
    mode.add_argument('--install-on-disk', action='store_true', help='Install only with main E-stop active; never reload')
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--plan-file', type=Path, required=True)
    parser.add_argument('--evidence-dir', type=Path)
    args = parser.parse_args()
    stages = [load_stage(args.review, i, d) for i in range(1, 6) for d in ('forward', 'reverse')]
    files = {s['task'].split('/')[-1]+'.xml': dict(sha256=s['xml_sha256'],
             base64=base64.b64encode(Path(s['xml']).read_bytes()).decode()) for s in stages}
    helper = ROOT/'scripts/vla/runtime/entry410_install_disk.py'
    bindings = {str(f.resolve()):digest(f) for f in (Path(__file__), helper,
                ROOT/'scripts/vla/entry410_stage_contract.py')}
    if args.plan:
        if args.plan_file.exists(): parser.error('Plan output must be new')
        snapshot = ssh('import hashlib,json;from pathlib import Path; p=Path("/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/task_list.yaml");print(json.dumps({"hash":hashlib.sha256(p.read_bytes()).hexdigest()}))')
        package = dict(expected_registry_sha256=snapshot['hash'], files=files)
        remote_plan = ssh(helper.read_text(), [base64.b64encode(json.dumps(package).encode()).decode(), 'plan'])
        record = dict(schema='entry410-disk-install-plan-v1', package=package,
                      review=str(args.review.resolve()), review_sha256=digest(args.review),
                      source_sha256=bindings, remote_plan=remote_plan, reload=False, physical_approval=False)
        with args.plan_file.open('x') as stream: json.dump(record, stream, indent=2); stream.write('\n')
        print(json.dumps(remote_plan)); return
    record = json.loads(args.plan_file.read_text())
    if (record['schema'] != 'entry410-disk-install-plan-v1' or record['package']['files'] != files
            or record['review_sha256'] != digest(args.review) or record['source_sha256'] != bindings):
        raise ValueError('Plan, reviewed XML or installer sources changed')
    if not args.evidence_dir or args.evidence_dir.exists(): parser.error('Evidence directory must be new')
    args.evidence_dir.mkdir(parents=True)
    log = args.evidence_dir/'preflight-active-estop.log'
    with log.open('x') as out:
        result = subprocess.run(['bash', str(ROOT/'scripts/vla/audit_vla_live_preflight_e6_0g.sh'),
                                 '--check', '--expect-active-estop'], stdout=out, stderr=subprocess.STDOUT, timeout=150)
    lines = log.read_text().splitlines()
    if result.returncode or 'ESTOP_KEY=1' not in lines or 'CHARGER=0' not in lines:
        raise RuntimeError('Main E-stop active preflight failed; no installation sent; see '+str(log))
    # Revalidate local package after the live check. Remote transaction checks registry again.
    for s in stages:
        if load_stage(args.review, s['step'], s['direction']) != s: raise RuntimeError('Stage changed')
    if any(digest(Path(p)) != h for p, h in bindings.items()): raise RuntimeError('Installer changed')
    (args.evidence_dir/'plan.json').write_text(json.dumps(record, indent=2)+'\n')
    (args.evidence_dir/'install-intent.json').write_text('{"reload":false,"main_estop_must_remain_active":true}\n')
    try:
        receipt = ssh(helper.read_text(), [base64.b64encode(json.dumps(record['package']).encode()).decode(), 'install'])
        (args.evidence_dir/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
        print(json.dumps(receipt))
    except BaseException:
        (args.evidence_dir/'outcome-uncertain.json').write_text('{"do_not_retry_or_reload":true,"inspect_remote_backup_and_registry":true}\n')
        raise
    finally:
        (args.evidence_dir/'evidence.sha256').write_text(''.join(digest(f)+'  '+f.name+'\n' for f in sorted(args.evidence_dir.iterdir()) if f.is_file() and f.name!='evidence.sha256'))


if __name__ == '__main__': main()
