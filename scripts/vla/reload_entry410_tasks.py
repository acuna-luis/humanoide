#!/usr/bin/env python3
"""One guarded Motion reload after exact ENTRY410 disk installation; no goal sent."""
import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess

from entry410_stage_contract import load_stage
from prepare_vla_entry_bundle import ROOT, digest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reload', action='store_true', required=True)
    p.add_argument('--review', type=Path, required=True)
    p.add_argument('--receipt', type=Path, required=True)
    p.add_argument('--evidence-dir', type=Path, required=True)
    args = p.parse_args()
    if args.evidence_dir.exists(): p.error('Choose a new evidence directory')
    receipt = json.loads(args.receipt.read_text())
    expected = {}
    root = '/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/'
    for i in range(1, 6):
        for direction in ('forward', 'reverse'):
            stage = load_stage(args.review, i, direction)
            expected[root+stage['task']+'.xml'] = stage['xml_sha256']
    if receipt['status'] != 'INSTALLED_ON_DISK_NOT_LOADED' or receipt['installed_files'] != expected:
        raise ValueError('Receipt not for reviewed stages')
    backup = args.receipt.parent/'backup-from-robot/task_list.yaml'
    if digest(backup) != receipt['registry_before_sha256']:
        raise ValueError('Verified external backup required before reload')
    args.evidence_dir.mkdir(parents=True)
    with (args.evidence_dir/'preflight.log').open('x') as out:
        result = subprocess.run(['bash', str(ROOT/'scripts/vla/audit_vla_live_preflight_e6_0g.sh'),
                                 '--check', '--expect-active-estop'], stdout=out, stderr=subprocess.STDOUT, timeout=150)
    lines = (args.evidence_dir/'preflight.log').read_text().splitlines()
    if result.returncode or 'ESTOP_KEY=1' not in lines or 'CHARGER=0' not in lines:
        raise RuntimeError('Main E-stop active preflight failed; no reload')
    expected[root+'task_list.yaml'] = receipt['registry_after_sha256']
    check = 'from pathlib import Path;import hashlib; expected='+repr(expected)+'; assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in expected.items()), "installed file mismatch"'
    # A reload may affect boot state. Keep E-stop active and never release/rearm here.
    remote = '\n'.join([
        'set -eu',
        'container=walker-motion.manipulation_robot_app-1',
        'test "$(docker inspect --format \'{{.State.Status}}\' "$container")" = running',
        'docker exec "$container" python3 -c '+shlex.quote(check),
        'before=$(docker inspect --format \'{{.State.StartedAt}}\' "$container")',
        'echo "STARTED_BEFORE=$before"',
        'timeout 40 docker restart --time 10 "$container"',
        'test "$(docker inspect --format \'{{.State.Status}}\' "$container")" = running',
        'after=$(docker inspect --format \'{{.State.StartedAt}}\' "$container")',
        'test "$after" != "$before"',
        'docker exec "$container" python3 -c '+shlex.quote(check),
        'echo "STARTED_AFTER=$after"',
        'echo MOTION_RESTARTED_ONCE=1',
        'echo MOVEMENT_GOALS_SENT=0',
    ])
    (args.evidence_dir/'reload-recipe.sh').write_text(remote+'\n')
    (args.evidence_dir/'intent.json').write_text('{"restart_count_requested":1,"estop_must_remain_active":true}\n')
    env = dict(os.environ, SSH_ASKPASS=str(ROOT/'scripts/vla/audit_vla_live_preflight_e6_0g.sh'),
               SSH_ASKPASS_REQUIRE='force', CRUZR_INTERNAL_ASKPASS='1', DISPLAY=os.environ.get('DISPLAY', ':0'))
    argv = ['setsid', '-w', 'ssh', '-o', 'ConnectTimeout=5', '-o', 'ConnectionAttempts=1',
            '-o', 'StrictHostKeyChecking=yes', '-o', 'PreferredAuthentications=password',
            '-o', 'PubkeyAuthentication=no', 'walker@192.168.11.2', 'bash -s']
    try:
        with (args.evidence_dir/'reload.log').open('x') as out:
            result = subprocess.run(argv, input=remote, text=True, stdout=out, stderr=subprocess.STDOUT, env=env, timeout=60)
        if result.returncode: raise RuntimeError('Reload outcome failed/uncertain; do not repeat automatically')
        print('MOTION_RESTARTED_ONCE; keep main E-stop active; verify boot and task loading before release')
    finally:
        (args.evidence_dir/'evidence.sha256').write_text(''.join(digest(f)+'  '+f.name+'\n' for f in sorted(args.evidence_dir.iterdir()) if f.is_file() and f.name!='evidence.sha256'))


if __name__ == '__main__': main()
