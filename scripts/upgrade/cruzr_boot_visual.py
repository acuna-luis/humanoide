#!/usr/bin/env python3
"""Short-lived screen indication; no ROS writes and no vendor expression override."""
import hashlib
import json
from pathlib import Path
import subprocess
import time
import uuid

import cruzr_cc_start_when_ready as gate

CONTAINER = 'walker-web.web-expression-1'
WEB_ROOT = '/usr/share/nginx/html'
SCRIPT = 'cruzr-boot-ready.js'
STATUS = 'cruzr-boot-ready.json'
ORIGINAL_INDEX_SHA = 'fb294b019cfef37b3e3d9441da099c3b76af8ceb062c7e4cdf121be18cc93566'
TAG = '    <script defer src="/cruzr-boot-ready.js"></script>\n'
LEASE_SECONDS = 12


def container_read(name):
    return subprocess.run(['docker', 'exec', CONTAINER, 'cat', WEB_ROOT+'/'+name],
                          capture_output=True, text=True, timeout=5)


def container_write(name, content):
    if name not in {SCRIPT, STATUS, 'index.html'}:
        raise ValueError('unreviewed screen file')
    path = WEB_ROOT+'/'+name
    # stdin carries content; no shell interpolation of JSON or JavaScript.
    command = 'umask 022; cat > "$1.tmp" && mv "$1.tmp" "$1"'
    result = subprocess.run(['docker', 'exec', '-i', CONTAINER, 'sh', '-c',
                             command, 'boot-visual', path], input=content,
                            capture_output=True, text=True, timeout=5)
    return result.returncode == 0


def patched_index(text):
    original = text.replace(TAG, '')
    if hashlib.sha256(original.encode()).hexdigest() != ORIGINAL_INDEX_SHA:
        raise ValueError('unreviewed expression page; no change')
    if text.count(TAG) > 1 or original.count('  </head>') != 1:
        raise ValueError('ambiguous expression page')
    return original.replace('  </head>', TAG+'  </head>')


def status_payload(ready, reason, clock=time.time):
    return json.dumps({'schema': 'cruzr-boot-ready-v1', 'ready': bool(ready),
                       'expression': 'inspection', 'sequence': uuid.uuid4().hex,
                       'expires_at_ms': int((clock()+LEASE_SECONDS)*1000) if ready else 0,
                       'reason': reason})+'\n'


def clear():
    try:
        return container_write(STATUS, status_payload(False, 'not_initial_release_ready'))
    except (OSError, subprocess.TimeoutExpired):
        # The browser also expires the last lease independently of this process.
        return False


def prepare():
    """Idempotent known-page patch, including after recreation of this image."""
    try:
        result = container_read('index.html')
        if result.returncode:
            return False
        page = patched_index(result.stdout)
        script = Path(__file__).with_name(SCRIPT).read_text()
        current = container_read(SCRIPT)
        if current.returncode or current.stdout != script:
            if not container_write(SCRIPT, script):
                return False
        if not clear():
            return False
        if result.stdout != page and not container_write('index.html', page):
            return False
        verified = container_read('index.html')
        return verified.returncode == 0 and verified.stdout == page
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        gate.log('VISUAL_DISABLED='+str(error))
        return False


def hold(ready, *, max_wait=1800, clock=time.monotonic, pause=time.sleep):
    """Renew only while fresh checks pass. A loss ends this boot indication."""
    deadline = clock()+max_wait
    shown = False
    try:
        while clock() < deadline:
            if not ready() or clock() >= deadline:
                gate.log('VISUAL_ENDED=release_or_readiness_lost')
                return shown
            if not container_write(STATUS, status_payload(True, 'initial_boot_release_ready')):
                gate.log('VISUAL_ENDED=screen_write_failed')
                return False
            if not shown:
                gate.log('VISUAL_READY=inspection; lease_seconds=12; movement_commands=0')
                shown = True
            pause(min(2, max(0, deadline-clock())))
        gate.log('VISUAL_ENDED=wait_limit')
        return shown
    except (OSError, subprocess.TimeoutExpired):
        gate.log('VISUAL_ENDED=check_error')
        return False
    finally:
        clear()
