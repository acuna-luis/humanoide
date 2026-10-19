#!/usr/bin/env python3
"""Configure only SRS video delivery, with an external backup and HUP reload.

No robot-control endpoints or publishers are used. Application/restoration
requires an idle SRS server; this tool never stops another camera session.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import time
import urllib.request


ROOT = Path(__file__).resolve().parents[2]
CONFIG = 'conf/rtmp2rtc.conf'
BEGIN = '    # BEGIN CRUZR PICO LOW LATENCY 20261016\n'
SETTINGS = (BEGIN
            + '    tcp_nodelay on;\n    min_latency on;\n'
            + '    play {\n        gop_cache off;\n        queue_length 1;\n'
            + '        mw_latency 20;\n    }\n'
            + '    publish { mr off; }\n'
            + '    # END CRUZR PICO LOW LATENCY 20261016\n')


def digest(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


def tuned_config(original: str) -> str:
    if SETTINGS in original:
        return original
    if 'CRUZR PICO LOW LATENCY' in original:
        raise ValueError('Existing latency block differs; review before replacing it')
    uncommented = re.sub(r'#[^\n]*', '', original)
    if re.search(r'\b(tcp_nodelay|min_latency|play|publish)\s', uncommented):
        raise ValueError('Existing delivery settings require manual review')
    anchor = 'vhost __defaultVhost__ {\n'
    if original.count(anchor) != 1 or len(re.findall(r'\bvhost\s', uncommented)) != 1:
        raise ValueError('Expected exactly one default vhost')
    return original.replace(anchor, anchor + SETTINGS, 1)


def ssh(host: str, parts: list[str], data: str | None = None) -> str:
    env = os.environ.copy()
    env.update(CRUZR_INTERNAL_ASKPASS='1',
               SSH_ASKPASS=str(ROOT / 'scripts/cruzr_blue_workbin_cycle.sh'),
               SSH_ASKPASS_REQUIRE='force', DISPLAY=env.get('DISPLAY', ':0'))
    command = ['setsid', '-w', 'ssh', '-o', 'ConnectTimeout=5',
               '-o', 'ConnectionAttempts=1', '-o', 'StrictHostKeyChecking=yes',
               '-o', 'PreferredAuthentications=password', '-o', 'PubkeyAuthentication=no',
               '-o', 'NumberOfPasswordPrompts=1', 'walker@' + host, shlex.join(parts)]
    result = subprocess.run(command, input=data, capture_output=True, text=True,
                            timeout=20, env=env, check=False)
    if result.returncode:
        raise RuntimeError('Video SSH query failed: ' + result.stderr[-1500:]
                           + result.stdout[-1500:])
    return result.stdout


def inventory(host: str, container: str) -> dict:
    template = ('{"id":{{json .Id}},"image":{{json .Config.Image}},'
                '"workdir":{{json .Config.WorkingDir}},"cmd":{{json .Config.Cmd}},'
                '"running":{{json .State.Running}},"mounts":{{json .Mounts}}}')
    info = json.loads(ssh(host, ['docker', 'inspect', '--format', template, container]))
    if (not info['running'] or not info['image'].endswith('/ossrs/srs:v5.0.213')
            or info['workdir'] != '/usr/local/srs'
            or info['cmd'] != ['./objs/srs', '-c', CONFIG]):
        raise ValueError('SRS image/process differs from the verified 5.0.213 baseline')
    target = '/usr/local/srs/' + CONFIG
    if any(target == m['Destination'] or target.startswith(m['Destination'].rstrip('/') + '/')
           for m in info['mounts']):
        raise ValueError('Configuration is mounted externally; review its persistent source')
    return info


def require_idle(host: str) -> None:
    with urllib.request.urlopen('http://' + host + ':1985/api/v1/streams/', timeout=5) as response:
        data = json.load(response)
    if data.get('code') != 0 or data.get('streams') != []:
        raise ValueError('SRS is busy or unavailable; close its camera sessions first')


def install(host: str, container: str, expected_hash: str, text: str) -> str:
    # Validate the candidate before touching the live file. Preserve ownership
    # and permissions by writing the existing file only after a hash recheck.
    script = '''set -eu
target=conf/rtmp2rtc.conf
candidate=$(mktemp /tmp/cruzr-pico-srs.XXXXXX.conf)
trap 'rm -f "$candidate"' EXIT
cat > "$candidate"
./objs/srs -t -c "$candidate"
actual=$(sha256sum "$target")
test "${actual%% *}" = "$1"
cat "$candidate" > "$target"
sha256sum "$target"
'''
    # Pass configuration over stdin; never interpolate its $CANDIDATE into shell.
    remote = ['docker', 'exec', '-i', container, 'sh', '-c', script, 'sh', expected_hash]
    return ssh(host, remote, text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true', help='Read-only inspection (default)')
    mode.add_argument('--apply', action='store_true', help='Back up, validate and reload video only')
    mode.add_argument('--restore', type=Path, metavar='BACKUP_DIR', help='Restore a backup made by --apply')
    parser.add_argument('--vision-ip', default='192.168.11.3')
    parser.add_argument('--container', default='walker-backend.srs-1')
    parser.add_argument('--evidence', type=Path, help='New private receipt directory for mutations')
    args = parser.parse_args()
    receipt = None
    try:
        # Avoid treating an arbitrary SSH option as a hostname.
        import ipaddress
        ipaddress.IPv4Address(args.vision_ip)
        if not re.fullmatch(r'[a-zA-Z0-9_.-]+', args.container):
            raise ValueError('Invalid container name')
        info = inventory(args.vision_ip, args.container)
        current = ssh(args.vision_ip, ['docker', 'exec', args.container, 'cat', CONFIG])
        expected = tuned_config(current)
        if args.restore:
            previous = json.loads((args.restore / 'receipt.json').read_text())
            expected = (args.restore / 'original.conf').read_text()
            if (previous['host'] != args.vision_ip or previous['container_id'] != info['id']
                    or digest(current) != previous['installed_sha256']
                    or digest(expected) != previous['original_sha256']):
                raise ValueError('Backup/container/hash mismatch; restoration blocked')
        print('SRS_VIDEO_LATENCY_PROFILE=' + ('low' if SETTINGS in current else 'vendor'))
        if not args.apply and not args.restore:
            print('SRS_CONFIG_SHA256=' + digest(current))
            return 0
        if current == expected:
            print('SRS_CONFIG_ALREADY_MATCHES=1')
            return 0
        require_idle(args.vision_ip)
        folder = args.evidence or (ROOT.parent / 'Humanoide-vla-evidence' /
                                   (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_SRS_VIDEO_LATENCY'))
        folder.mkdir(parents=True, exist_ok=False, mode=0o700)
        (folder / 'original.conf').write_text(current)
        (folder / 'installed.conf').write_text(expected)
        receipt = folder / 'receipt.json'
        record = dict(host=args.vision_ip, container=args.container, container_id=info['id'],
                      image=info['image'], config=CONFIG, original_sha256=digest(current),
                      installed_sha256=digest(expected), phase='backed-up',
                      operation='restore' if args.restore else 'apply', control_commands_sent=False)
        receipt.write_text(json.dumps(record, indent=2) + '\n')
        # Recheck the service and inactivity immediately before writing.
        if inventory(args.vision_ip, args.container)['id'] != info['id']:
            raise ValueError('SRS container changed')
        require_idle(args.vision_ip)
        record['phase'] = 'installing'
        receipt.write_text(json.dumps(record, indent=2) + '\n')
        (folder / 'validation.txt').write_text(install(args.vision_ip, args.container, digest(current), expected))
        record['phase'] = 'written'
        receipt.write_text(json.dumps(record, indent=2) + '\n')
        ssh(args.vision_ip, ['docker', 'kill', '--signal=HUP', args.container])
        # Allow the signal handler to reload; do not restart the container.
        time.sleep(.3)
        after = inventory(args.vision_ip, args.container)
        if after['id'] != info['id']:
            raise ValueError('SRS instance changed during reload')
        live = ssh(args.vision_ip, ['docker', 'exec', args.container, 'cat', CONFIG])
        if digest(live) != digest(expected):
            raise ValueError('Configuration readback differs')
        for attempt in range(5):
            logs = ssh(args.vision_ip, ['docker', 'logs', '--since', '10s', '--tail', '100', args.container])
            latest = logs.rsplit('starting reload config.', 1)[-1]
            if 'starting reload config.' in logs and 'reload config success' in latest:
                break
            time.sleep(.3)
        else:
            (folder / 'reload.log').write_text(logs)
            raise ValueError('SRS reload success was not confirmed; keep the saved backup')
        (folder / 'reload.log').write_text(logs)
        # Runtime parameters are consumed by new camera connections. Keep
        # measured headset latency separate from configuration verification.
        require_idle(args.vision_ip)
        record.update(phase='reloaded', config_readback_verified=True,
                      headset_latency_measured=False)
        receipt.write_text(json.dumps(record, indent=2) + '\n')
        print('SRS_VIDEO_CONFIG_RELOADED=1')
        print('EVIDENCE=' + str(folder))
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        if receipt is not None:
            record['error'] = str(error)
            receipt.write_text(json.dumps(record, indent=2) + '\n')
        print('SRS_VIDEO_CONFIG_ERROR=' + str(error))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
