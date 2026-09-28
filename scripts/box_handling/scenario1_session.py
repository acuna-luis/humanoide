"""Bounded JSONL transport to a persistent child; no ROS or robot commands here."""
import json
import queue
import subprocess
import threading
import time


class ProcessSession:
    def __init__(self, command, emit, *, startup_timeout=20):
        self.emit = emit
        self.sequence = 0
        self.failed = False
        self.events = queue.Queue()
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, bufsize=1)
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()
        try:
            end = time.monotonic()+startup_timeout
            while True:
                event = self._next(end)
                if event['event'] == 'session_ready':
                    if event.get('request_id') is not None:
                        raise RuntimeError('Malformed session readiness')
                    self.emit(event)
                    break
                self.emit(event)
                if event['event'] == 'error':
                    raise RuntimeError('Worker initialization failed: '+event.get('reason', 'unknown'))
        except BaseException:
            self.failed = True
            self.close()
            raise

    def _read(self):
        try:
            for line in self.process.stdout:
                try:
                    value = json.loads(line)
                    if not isinstance(value, dict) or not isinstance(value.get('event'), str):
                        raise ValueError('not a protocol event')
                except (TypeError, ValueError):
                    value = dict(event='worker_log', text=line.rstrip()[:3000])
                self.events.put(value)
        finally:
            self.events.put(None)

    def _next(self, deadline):
        remaining = deadline-time.monotonic()
        if remaining <= 0:
            raise RuntimeError('WORKER_DEADLINE: no result confirmed')
        try:
            event = self.events.get(timeout=remaining)
        except queue.Empty as exc:
            raise RuntimeError('WORKER_DEADLINE: no result confirmed') from exc
        if event is None:
            raise RuntimeError('WORKER_DISCONNECTED: no result confirmed')
        return event

    def call(self, request, *, timeout):
        if self.failed or self.process.poll() is not None:
            raise RuntimeError('WORKER_SESSION_FAILED: do not retry')
        if 'request_id' in request:
            raise ValueError('Request identity belongs to the session')
        self.sequence += 1
        request_id = str(self.sequence)
        rows = []
        try:
            self.process.stdin.write(json.dumps(dict(request_id=request_id, **request), allow_nan=False)+'\n')
            self.process.stdin.flush()
            end = time.monotonic()+timeout
            while True:
                event = self._next(end)
                if event['event'] == 'worker_log':
                    self.emit(event)
                    continue
                if event.get('request_id') != request_id:
                    raise RuntimeError('WORKER_REQUEST_MISMATCH: no result confirmed')
                self.emit(event)
                if event['event'] == 'request_complete':
                    if type(event.get('returncode')) is not int or event['returncode'] != 0:
                        reasons = [row.get('reason', 'unknown') for row in rows if row['event'] == 'error']
                        raise RuntimeError('WORKER_REQUEST_FAILED: '+('; '.join(reasons) or 'do not retry'))
                    return rows
                rows.append(event)
        except BaseException:
            self.failed = True
            raise

    def close(self):
        self.failed = True
        try:
            self.process.stdin.close()  # EOF interrupts an active request in the worker.
        except (OSError, ValueError):
            pass
        try:
            self.process.wait(timeout=12)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=2)
            self.emit(dict(event='worker_exit_unconfirmed', physical_stop_verified=False))
        self.reader.join(timeout=1)
        # Cancellation and terminal observations can arrive after a failed
        # request while EOF/lease expiry is being handled. Preserve them as
        # evidence without clearing the failure or accepting another request.
        while True:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            if event is not None:
                self.emit(event)
        self.emit(dict(event='worker_closed', returncode=self.process.returncode,
                       physical_stop_verified=False))
        self.process.stdout.close()
