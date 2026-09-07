#!/usr/bin/env python3
"""Fixed read-only host queries, no ROS calls/container exec/restarts/robot commands."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REMOTE = r'''
import datetime, hashlib, json, pathlib, subprocess
result = {'collected_at_host_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
commands = {
 'hostname': ['hostname'],
 'boot_time': ['uptime','-s'],
 'guard_state': ['systemctl','show','cruzr-v020-boot-guard.service',
     '--property=LoadState,ActiveState,SubState,UnitFileState,ExecMainStatus,ActiveEnterTimestamp,ExecMainStartTimestamp'],
 'containers': ['docker','ps','-a','--format','{{.Names}}\t{{.Image}}\t{{.Status}}'],
}
result['queries'] = {}
for key, command in commands.items():
 try:
  p = subprocess.run(command, capture_output=True, text=True, timeout=8)
  result['queries'][key] = {'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
 except (OSError,subprocess.TimeoutExpired) as exc:
  result['queries'][key] = {'error':str(exc)}
result['files'] = {}
for name in ('/usr/local/sbin/cruzr-v020-boot-guard',
             '/etc/systemd/system/cruzr-v020-boot-guard.service'):
 try:
  p = pathlib.Path(name)
  if p.stat().st_size > 250000: raise ValueError('file exceeds bounded read')
  raw = p.read_bytes()
  result['files'][name] = {'sha256':hashlib.sha256(raw).hexdigest(),'text':raw.decode()}
 except (OSError,ValueError) as exc:
  result['files'][name] = {'error':str(exc)}
print(json.dumps(result))
'''


def main():
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    outdir = ROOT.parent/'Humanoide-vla-evidence'/(stamp+'_BOOT-READONLY')
    outdir.mkdir(exist_ok=False)
    env = dict(os.environ, CRUZR_INTERNAL_ASKPASS='1',
               SSH_ASKPASS=str(ROOT/'scripts/cruzr_recover_to_home.sh'),
               SSH_ASKPASS_REQUIRE='force', DISPLAY=os.environ.get('DISPLAY', ':0'))
    summary = {}
    for host, ip in [('motion','192.168.11.2'),('vision','192.168.11.3')]:
        command = ['setsid','-w','ssh','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=5',
                   '-o','PreferredAuthentications=password','-o','PubkeyAuthentication=no',
                   '-o','NumberOfPasswordPrompts=1',f'walker@{ip}','python3 -']
        p = subprocess.run(command, input=REMOTE, env=env, capture_output=True, text=True, timeout=45)
        (outdir/(host+'-ssh.stderr')).write_text(p.stderr)
        if p.returncode:
            summary[host] = {'ssh_returncode': p.returncode}
            continue
        data = json.loads(p.stdout)
        (outdir/(host+'.json')).write_text(json.dumps(data, indent=2)+'\n')
        for path, entry in data['files'].items():
            if 'text' in entry:
                (outdir/(host+'-'+Path(path).name)).write_text(entry['text'])
        summary[host] = {'queries':data['queries'],
                         'files':{k:{kk:vv for kk,vv in v.items() if kk != 'text'} for k,v in data['files'].items()}}
    report = {'scope':'host metadata and two guard files only', 'hosts':summary,
              'ros_calls':0,'movement_commands':0,'remote_configuration_changes':0,
              'physical_state_verified':False,'physical_authorized':False}
    (outdir/'summary.json').write_text(json.dumps(report, indent=2)+'\n')
    (outdir/'collector.py').write_bytes(Path(__file__).read_bytes())
    (outdir/'evidence.sha256').write_text(''.join(
        f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n' for p in sorted(outdir.iterdir()) if p.is_file()))
    print(outdir)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
