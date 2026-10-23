#!/usr/bin/env python3
"""Install fresh resident code on Motion. Defaults to verification/plan only."""
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path, PurePosixPath
import pwd
import re
import secrets
import shutil
import subprocess
import sys
import time
from urllib.parse import urlsplit

PREFIX = Path('/opt/cruzr-scenario1')
STATE = Path('/var/lib/cruzr-scenario1')
CONFIG = Path('/etc/cruzr-scenario1.json')
UNIT = Path('/etc/systemd/system/cruzr-scenario1.service')


def verify(bundle):
    bundle = Path(bundle).resolve()
    manifest = json.loads((bundle/'manifest.json').read_text())
    if manifest.get('version') != 1 or not isinstance(manifest.get('files'), dict):
        raise ValueError('Invalid manifest')
    for name, expected in manifest['files'].items():
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or str(path) != name or not re.fullmatch(r'[a-f0-9]{64}', expected):
            raise ValueError('Unsafe manifest entry')
        file = bundle/name
        if any(p.is_symlink() for p in (file, *file.parents)) or not file.is_file():
            raise ValueError('Invalid package file: '+name)
        if hashlib.sha256(file.read_bytes()).hexdigest() != expected:
            raise ValueError('Checksum mismatch: '+name)
    actual = {str(p.relative_to(bundle)) for p in bundle.rglob('*') if p.is_file()}
    if actual != set(manifest['files']) | {'manifest.json'}:
        raise ValueError('Unmanifested package files')
    for relative in ('install.py', 'app/scripts/web/robot/service.py', 'app/scripts/web/robot/worker.py'):
        if relative not in manifest['files']:
            raise ValueError('Incomplete package')
    return manifest


def unit_text(user):
    if not re.fullmatch(r'[a-z_][a-z0-9_-]*', user):
        raise ValueError('Invalid service account')
    return f'''[Unit]
Description=CRUZR S2 resident HOME and box cycle jobs
After=docker.service network-online.target
Requires=docker.service

[Service]
Type=simple
User={user}
WorkingDirectory={PREFIX}/app
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart=/usr/bin/python3 -B {PREFIX}/app/scripts/web/robot/service.py --config {CONFIG}
Restart=no
UMask=0077
NoNewPrivileges=true
# Native workers already depend on host /tmp mounted into vendor containers.
# Do not enable PrivateTmp or hide Docker's socket here.
KillMode=control-group
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
'''


def activate(height, user):
    config = json.loads(CONFIG.read_text())
    if config['enabled'] is not False:
        raise ValueError('Already enabled; no automatic restart')
    if subprocess.run(['systemctl', 'is-active', '--quiet', 'cruzr-scenario1.service']).returncode == 0:
        raise ValueError('Stop the disabled service before activation; never stop an active job')
    if list(STATE.glob('*/job.json')):
        raise ValueError('Existing job history: reconcile physical state before administrative activation')
    evidence = STATE/('activation-check-'+str(time.time_ns()))
    command = ['runuser', '-u', user, '--', '/usr/bin/python3', '-B',
        str(PREFIX/'app/scripts/web/robot/worker.py'), '--action', 'cycle', '--height', height,
        '--evidence', str(evidence)]
    result = subprocess.run(command, timeout=240)
    if result.returncode:
        raise ValueError('Read-only robot check failed; service remains disabled')
    backup = CONFIG.with_name(CONFIG.name+'.before-activation-'+str(time.time_ns()))
    shutil.copy2(CONFIG, backup)
    config['enabled'] = True
    # No movement is launched by service activation. Only fresh authenticated jobs.
    temporary = CONFIG.with_suffix('.new')
    temporary.write_text(json.dumps(config, indent=2)+'\n')
    shutil.copystat(CONFIG, temporary)
    info = CONFIG.stat()
    os.chown(temporary, info.st_uid, info.st_gid)
    temporary.replace(CONFIG)
    subprocess.run(['systemctl', 'enable', '--now', 'cruzr-scenario1.service'], check=True)
    print('SERVICE_ENABLED_NO_JOB_STARTED')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, default=Path(__file__).resolve().parent)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--apply', action='store_true')
    mode.add_argument('--activate', action='store_true')
    parser.add_argument('--user', default='walker')
    parser.add_argument('--height', choices=('74','90'), default='74')
    parser.add_argument('--bind', default='127.0.0.1')
    parser.add_argument('--origin', default='http://127.0.0.1:18776')
    args = parser.parse_args()
    manifest = verify(args.bundle)
    unit = unit_text(args.user)
    address = ipaddress.ip_address(args.bind)
    origin = urlsplit(args.origin)
    if address.version != 4 or not (address.is_private or address.is_loopback) or address.is_unspecified:
        raise ValueError('An explicit private IPv4 address is required')
    if (origin.scheme not in ('http','https') or not origin.hostname or origin.path or origin.query or
            origin.fragment or origin.username or origin.password):
        raise ValueError('Exact browser origin required')
    print(json.dumps({'status':'PACKAGE_VERIFIED', 'files':len(manifest['files']),
        'target':str(PREFIX), 'execution':'Motion host Docker; no external PC/SSH',
        'enabled_after_install':False, 'movement_commands':0}))
    if not args.apply and not args.activate:
        return 0
    if os.geteuid() != 0:
        raise ValueError('Run installer with sudo on Motion, not on the external PC')
    account = pwd.getpwnam(args.user)
    if args.activate:
        # Must use the same account and installed bytes, never unreviewed sources.
        if UNIT.read_text() != unit:
            raise ValueError('Installed unit/account differs')
        for relative, digest in manifest['files'].items():
            if relative.startswith('app/') and hashlib.sha256((PREFIX/relative).read_bytes()).hexdigest() != digest:
                raise ValueError('Installed code differs from package')
        activate(args.height, args.user)
        return 0
    for path in (PREFIX, STATE, CONFIG, UNIT):
        if path.exists() or path.is_symlink():
            raise ValueError('Fresh install only; existing path preserved: '+str(path))
    if shutil.disk_usage('/opt').free < 512*1024*1024:
        raise ValueError('At least 512 MiB free required')
    # File-only prerequisite; Docker access discovered without printing secrets.
    subprocess.run(['runuser','-u',args.user,'--','docker','ps','-q'], check=True, timeout=15, stdout=subprocess.DEVNULL)
    sys.path.insert(0, str(args.bundle/'app/scripts/box_handling'))
    from scenario1_checks import discover_containers
    ids = subprocess.check_output(['docker', 'ps', '-q'], text=True, timeout=15).split()
    if not ids:
        raise ValueError('No running Motion containers; installation stopped')
    discover_containers(json.loads(subprocess.check_output(['docker', 'inspect', *ids], text=True, timeout=15)))
    PREFIX.mkdir(mode=0o755)
    shutil.copytree(args.bundle/'app', PREFIX/'app')
    shutil.copyfile(args.bundle/'manifest.json', PREFIX/'manifest.json')
    shutil.copyfile(args.bundle/'install.py', PREFIX/'install.py')
    STATE.mkdir(mode=0o700)
    os.chown(STATE, account.pw_uid, account.pw_gid)
    key = secrets.token_urlsafe(32)
    CONFIG.write_text(json.dumps({'version':1, 'enabled':False, 'bind':args.bind,
        'port':18776, 'origin':args.origin, 'state':str(STATE),
        'token_sha256':hashlib.sha256(key.encode()).hexdigest()}, indent=2)+'\n')
    os.chown(CONFIG, 0, account.pw_gid)
    CONFIG.chmod(0o640)
    credentials = STATE/'operator-token.txt'
    credentials.write_text(key+'\n')
    credentials.chmod(0o600)
    os.chown(credentials, account.pw_uid, account.pw_gid)
    UNIT.write_text(unit)
    UNIT.chmod(0o644)
    subprocess.run(['systemctl','daemon-reload'], check=True)
    (PREFIX/'installation.json').write_text(json.dumps({'time_ns':time.time_ns(),
        'manifest_sha256':hashlib.sha256((args.bundle/'manifest.json').read_bytes()).hexdigest(),
        'native_tasks_changed':False, 'service_started':False, 'physical_validation':'pending',
        'rollback':'Stop/disable service only when no job is active; retain evidence and native tasks'}, indent=2)+'\n')
    print('INSTALLED_DISABLED_NO_MOVEMENT; operator key: /var/lib/cruzr-scenario1/operator-token.txt')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print('INSTALL_BLOCKED: '+str(error), file=sys.stderr)
        raise SystemExit(78)
