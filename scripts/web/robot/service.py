#!/usr/bin/env python3
"""Robot-resident authenticated job service; starts no jobs at boot."""
import argparse
import fcntl
import hashlib
import hmac
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent


def write_json(path, data):
    temporary = path.with_suffix('.tmp')
    with temporary.open('w') as f:
        json.dump(data, f, allow_nan=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    temporary.replace(path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def validate_request(value):
    if not isinstance(value, dict) or set(value) != {'action', 'height', 'key', 'physical_confirmed', 'trial_authorized'}:
        raise ValueError('Invalid job fields')
    if value['action'] not in ('home', 'cycle') or value['height'] not in ('74', '90'):
        raise ValueError('Only HOME/cycle and 74/90 are supported')
    if not isinstance(value['key'], str) or not re.fullmatch(r'[a-f0-9]{32}', value['key']):
        raise ValueError('Invalid idempotency key')
    if value['physical_confirmed'] is not True or type(value['trial_authorized']) is not bool:
        raise ValueError('Fresh physical declaration required')
    if value['action'] == 'cycle' and value['trial_authorized'] is not True:
        raise ValueError('Integrated height recipe is a commissioning trial')
    return value


class Jobs:
    def __init__(self, state, enabled=False, launch=subprocess.Popen):
        self.state, self.enabled, self.launch = Path(state), enabled, launch
        self.state.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.mutex = threading.Lock()
        self.lock = (self.state/'service.lock').open('a')
        fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.current = None
        self.blocked = False
        self.history = {}
        for path in sorted(self.state.glob('*/job.json')):
            job = json.loads(path.read_text())
            if job['status'] in ('accepted', 'running', 'checking'):
                job.update(status='indeterminate', reason='Service restarted; physical state not confirmed')
                write_json(path, job)
            if job['status'] in ('failed', 'indeterminate'):
                self.blocked = True
            self.history[job['key']] = job
            self.current = job

    def status(self):
        with self.mutex:
            return {'enabled': self.enabled, 'blocked': self.blocked, 'job': dict(self.current) if self.current else None,
                    'execution_host': 'Motion', 'pc_required': False,
                    'physical_validation': 'pending', 'cancel_is_estop': False}

    def submit(self, value):
        value = validate_request(value)
        with self.mutex:
            old = self.history.get(value['key'])
            if old:
                if any(old[k] != value[k] for k in value):
                    raise ValueError('Idempotency key was used for a different request')
                return dict(old)
            if not self.enabled or self.blocked or self.current and self.current['status'] in ('accepted', 'checking', 'running'):
                raise ValueError('Service disabled, occupied or physical reconciliation required')
            job = dict(value, id=secrets.token_hex(16), status='accepted', created_ns=time.time_ns())
            directory = self.state/job['id']
            directory.mkdir(mode=0o700)
            write_json(directory/'job.json', job)  # Durable BEFORE any child process.
            self.history[job['key']] = job
            self.current = job
            threading.Thread(target=self.run, args=(job, directory), daemon=True).start()
            return dict(job)

    def run(self, job, directory):
        def update(**data):
            with self.mutex:
                job.update(data)
                write_json(directory/'job.json', job)
        try:
            base = [sys.executable, '-B', str(HERE/'worker.py'), '--action', job['action'], '--height', job['height']]
            with (directory/'console.log').open('a') as log:
                update(status='checking')
                result = self.launch(base+['--evidence', str(directory/'check')],
                    stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                    env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'), close_fds=True)
                rc = result.wait(timeout=240)
                if rc:
                    raise RuntimeError('Read-only preflight failed; rc='+str(rc))
                # A declaration cannot wait indefinitely behind a slow check.
                if time.time_ns()-job['created_ns'] > 120_000_000_000:
                    raise RuntimeError('Operator declaration expired before dispatch')
                update(status='running', started_ns=time.time_ns())
                result = self.launch(base+['--evidence', str(directory/'run'), '--run', '--physical-confirmed']+
                    (['--height-trial-authorized'] if job['action'] == 'cycle' else []),
                    stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                    env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'), close_fds=True)
                # No automatic kill/retry/HOME. Native runtime owns its bounded
                # deadlines, cancellation and expiring control leases.
                rc = result.wait()
                if rc:
                    raise RuntimeError('Execution interrupted; physical state must be checked; rc='+str(rc))
                update(status='succeeded', finished_ns=time.time_ns(), reason='Measured HOME; box support remains recipe/operator assumption')
        except BaseException as error:
            with self.mutex:
                self.blocked = True
            update(status='failed', finished_ns=time.time_ns(), reason=str(error))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass  # Never log credentials, cookies or request bodies.

    def response(self, code, data, kind='application/json', cookie=None):
        raw = json.dumps(data, allow_nan=False).encode() if kind == 'application/json' else data
        self.send_response(code)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()
        self.wfile.write(raw)

    def same_origin(self):
        return self.headers.get('Host') == urlsplit(self.server.origin).netloc and self.headers.get('Origin') == self.server.origin

    def session(self):
        try:
            cookies = SimpleCookie(self.headers.get('Cookie', ''))
            value = cookies['cruzr_job_session'].value
        except (KeyError, ValueError):
            return None
        with self.server.session_lock:
            now = time.monotonic()
            self.server.sessions = {k: v for k, v in self.server.sessions.items() if now-v[1] < 1800}
            return self.server.sessions.get(value)

    def do_GET(self):
        if self.headers.get('Host') != urlsplit(self.server.origin).netloc:
            return self.response(403, {'error': 'Invalid Host'})
        if self.path in ('/', '/app.js', '/app.css'):
            name = {'/': 'index.html', '/app.js': 'app.js', '/app.css': 'app.css'}[self.path]
            kind = {'/': 'text/html; charset=utf-8', '/app.js': 'text/javascript', '/app.css': 'text/css'}[self.path]
            return self.response(200, (HERE/name).read_bytes(), kind)
        session = self.session()
        if not session:
            return self.response(401, {'error': 'Login required'})
        if self.path == '/api/status':
            result = self.server.jobs.status()
            result['csrf'] = session[0]
            return self.response(200, result)
        return self.response(404, {'error': 'Unknown endpoint'})

    def do_POST(self):
        if not self.same_origin() or self.headers.get('Content-Type') != 'application/json':
            return self.response(403, {'error': 'Same-origin JSON required'})
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 4096:
                raise ValueError('Invalid size')
            self.connection.settimeout(5)
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError('JSON object required')
            if self.path == '/api/login':
                # Global rate limit also bounds session count; constant-time digest comparison.
                with self.server.session_lock:
                    if time.monotonic()-self.server.last_login < 1:
                        return self.response(429, {'error': 'Wait before retry'})
                    self.server.last_login = time.monotonic()
                    token = data.get('token', '')
                    if not isinstance(token, str) or not hmac.compare_digest(hashlib.sha256(token.encode()).hexdigest(), self.server.token_sha):
                        return self.response(401, {'error': 'Invalid access token'})
                    session, csrf = secrets.token_hex(32), secrets.token_hex(32)
                    self.server.sessions[session] = (csrf, time.monotonic())
                secure = '; Secure' if self.server.origin.startswith('https:') else ''
                return self.response(200, {'ok': True}, cookie='cruzr_job_session='+session+'; Path=/; HttpOnly; SameSite=Strict; Max-Age=1800'+secure)
            session = self.session()
            if not session or not hmac.compare_digest(self.headers.get('X-CSRF-Token', ''), session[0]):
                return self.response(403, {'error': 'Login/CSRF required'})
            if self.path != '/api/jobs':
                return self.response(404, {'error': 'Unknown endpoint'})
            return self.response(202, self.server.jobs.submit(data))
        except (ValueError, TypeError, OSError) as error:
            return self.response(409, {'error': str(error)})

    def do_DELETE(self):
        self.response(405, {'error': 'No remote reset/cancel; use physical stop when needed'})
    do_PUT = do_DELETE
    do_PATCH = do_DELETE


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    if not re.fullmatch(r'[a-f0-9]{64}', config['token_sha256']):
        parser.error('Invalid token digest')
    origin = urlsplit(config['origin'])
    if origin.scheme not in ('http', 'https') or origin.path or origin.username or not origin.hostname:
        parser.error('Exact origin required')
    server = ThreadingHTTPServer((config['bind'], config['port']), Handler)
    server.origin = config['origin']
    server.token_sha = config['token_sha256']
    server.sessions, server.session_lock, server.last_login = {}, threading.Lock(), float('-inf')
    server.jobs = Jobs(config['state'], config['enabled'])
    server.serve_forever()


if __name__ == '__main__':
    main()
