#!/usr/bin/env python3
"""Challenge/response PC-to-Motion liveness; not a physical stop guarantee.

Motion creates a fresh nonce and enforces each deadline on its own monotonic
clock. The PC replies in a separate writer thread. Old buffered bytes cannot
answer a new nonce; missed, malformed or disconnected sessions never rearm.
"""
import json
import os
from pathlib import Path
import queue
import re
import select
import sys
import threading
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent.parent/'box_handling'))
import scenario1_action_client as native

MAX_GAP_S = .75
SEND_INTERVAL_S = .1
WRITE_TIMEOUT_S = .2
MAX_LINE = 4096


class PcHeartbeat:
    def __init__(self, fd, session_id, send_challenge, *, clock=time.monotonic):
        if not isinstance(session_id, str) or not re.fullmatch('[0-9a-f]{32}', session_id):
            raise ValueError('invalid_pc_session')
        if not callable(send_challenge): raise ValueError('pc_challenge_sender_required')
        self.fd, self.session_id, self.send_challenge, self.clock = fd, session_id, send_challenge, clock
        self.lock = threading.Lock(); self.last = None; self.sequence = 0
        self.failure = None; self.closed = threading.Event(); self.ready = threading.Event()
        os.set_blocking(fd, False)
        self.thread = threading.Thread(target=self._read_loop, daemon=True); self.thread.start()

    def _fault(self, reason):
        with self.lock:
            if self.failure is None: self.failure = reason
        self.ready.set()

    def _read_loop(self):
        buffer = bytearray()
        try:
            while not self.closed.is_set():
                nonce = uuid.uuid4().hex
                challenge = {'event':'pc_ping', 'session_id':self.session_id,
                             'sequence':self.sequence, 'nonce':nonce}
                began = self.clock(); deadline = began+MAX_GAP_S
                if self.send_challenge(challenge) is not True:
                    raise RuntimeError('pc_challenge_delivery_failed')
                ack = None
                while not self.closed.is_set() and self.clock() < deadline:
                    readable, _, _ = select.select([self.fd], [], [], min(.05, max(0.0, deadline-self.clock())))
                    if not readable: continue
                    try: data = os.read(self.fd, MAX_LINE+1)
                    except BlockingIOError: continue
                    if not data: raise RuntimeError('pc_heartbeat_eof')
                    buffer.extend(data)
                    if len(buffer) > MAX_LINE: raise ValueError('pc_heartbeat_oversize')
                    if b'\n' in buffer:
                        line, _, rest = bytes(buffer).partition(b'\n'); buffer = bytearray(rest)
                        # No second response may be queued for the next nonce.
                        if buffer: raise ValueError('pc_heartbeat_extra_data')
                        ack = native.object_json(line.decode('utf-8'))
                        break
                expected = dict(challenge, event='pc_pong')
                if (self.closed.is_set()): return
                if ack != expected or not began <= self.clock() <= deadline:
                    raise RuntimeError('pc_heartbeat_ack_invalid_or_expired')
                with self.lock:
                    if self.failure is not None: raise RuntimeError('pc_heartbeat_already_failed')
                    self.last = self.clock(); self.sequence += 1
                self.ready.set()
                if self.closed.wait(SEND_INTERVAL_S): break
        except BaseException as exc:
            self._fault(type(exc).__name__ + ':' + str(exc))

    def alive(self):
        with self.lock:
            now = self.clock()
            if self.last is not None and not 0 <= now-self.last <= MAX_GAP_S:
                self.failure = self.failure or 'pc_heartbeat_expired'
            return (self.failure is None and self.last is not None and
                    0 <= now-self.last <= MAX_GAP_S and not self.closed.is_set())

    def await_ready(self, timeout):
        if not self.ready.wait(timeout) or not self.alive():
            self._fault('pc_heartbeat_not_ready')
            raise RuntimeError('pc_heartbeat_not_ready')

    def close(self):
        self.closed.set(); self.thread.join(1.0)
        return not self.thread.is_alive()


class PcHeartbeatPump:
    """Dedicated PC writer fed only with fresh challenges from result reader."""
    def __init__(self, fd, session_id):
        if not isinstance(session_id, str) or not re.fullmatch('[0-9a-f]{32}', session_id):
            raise ValueError('invalid_pc_session')
        self.fd, self.session_id = fd, session_id
        self.closed = threading.Event(); self.failed = threading.Event(); self.failure = None
        self.challenges = queue.Queue(maxsize=1); self.sequence = 0
        os.set_blocking(fd, False)
        self.thread = threading.Thread(target=self._send_loop, daemon=True); self.thread.start()

    def submit(self, row):
        if (self.failed.is_set() or self.closed.is_set() or not isinstance(row, dict) or
                set(row) != {'event','session_id','sequence','nonce'} or row['event'] != 'pc_ping' or
                row['session_id'] != self.session_id or type(row['sequence']) is not int or
                row['sequence'] != self.sequence or not isinstance(row['nonce'], str) or
                not re.fullmatch('[0-9a-f]{32}', row['nonce'])):
            self.failed.set(); raise ValueError('pc_challenge_invalid')
        self.sequence += 1
        try: self.challenges.put_nowait(dict(row, event='pc_pong'))
        except queue.Full as exc:
            self.failure = 'pc_challenge_queue_full'; self.failed.set(); raise RuntimeError(self.failure) from exc

    def _send_loop(self):
        try:
            while not self.closed.is_set():
                try: response = self.challenges.get(timeout=.05)
                except queue.Empty: continue
                data = (json.dumps(response, separators=(',', ':'))+'\n').encode()
                view = memoryview(data); deadline = time.monotonic()+WRITE_TIMEOUT_S
                while view:
                    remaining = deadline-time.monotonic()
                    if remaining <= 0: raise TimeoutError('pc_heartbeat_write_timeout')
                    _, writable, _ = select.select([], [self.fd], [], remaining)
                    if not writable: raise TimeoutError('pc_heartbeat_write_timeout')
                    try: count = os.write(self.fd, view)
                    except BlockingIOError: continue
                    if count <= 0: raise BrokenPipeError('pc_heartbeat_write_failed')
                    view = view[count:]
        except BaseException as exc:
            self.failure = type(exc).__name__ + ':' + str(exc); self.failed.set()

    def close(self):
        self.closed.set(); self.thread.join(1.0)
        return not self.thread.is_alive()
