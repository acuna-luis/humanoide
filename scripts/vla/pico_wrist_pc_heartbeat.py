#!/usr/bin/env python3
"""Challenge/response PC-to-Motion liveness; not a physical stop guarantee.

Motion creates a fresh nonce and enforces each deadline on its own monotonic
clock. The PC replies in a separate writer thread. Old buffered bytes cannot
answer a new nonce; missed, malformed or disconnected sessions never rearm.
"""
import json
import math
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
import pico_wrist_action_client as native

MAX_GAP_S = .75
SEND_INTERVAL_S = .1
WRITE_TIMEOUT_S = .2
MAX_LINE = 4096
MAX_MODEL_PERMIT_NS = 10_000_000_000
GOAL_UUID = re.compile(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\Z')
DIGEST = re.compile(r'[0-9a-f]{64}\Z')


def _model_request(value):
    if (not isinstance(value, dict) or set(value) != {'goal_id', 'task_sha256'} or
            not isinstance(value['goal_id'], str) or not GOAL_UUID.fullmatch(value['goal_id']) or
            not isinstance(value['task_sha256'], str) or not DIGEST.fullmatch(value['task_sha256'])):
        raise ValueError('invalid_model_permit_request')
    return dict(value)


def _model_permit(value, request):
    if value is None:
        return None
    if (not isinstance(value, dict) or set(value) != {'goal_id', 'task_sha256', 'decision_sha256', 'budget_ns'} or
            value['goal_id'] != request['goal_id'] or value['task_sha256'] != request['task_sha256'] or
            not isinstance(value['decision_sha256'], str) or not DIGEST.fullmatch(value['decision_sha256']) or
            type(value['budget_ns']) is not int or not 0 < value['budget_ns'] <= MAX_MODEL_PERMIT_NS):
        raise ValueError('invalid_model_permit')
    return dict(value)


class PcHeartbeat:
    def __init__(self, fd, session_id, send_challenge, *, clock=time.monotonic, model_mode=False):
        if not isinstance(session_id, str) or not re.fullmatch('[0-9a-f]{32}', session_id):
            raise ValueError('invalid_pc_session')
        if not callable(send_challenge): raise ValueError('pc_challenge_sender_required')
        if type(model_mode) is not bool: raise ValueError('invalid_model_mode')
        self.fd, self.session_id, self.send_challenge, self.clock = fd, session_id, send_challenge, clock
        self.lock = threading.Lock(); self.last = None; self.sequence = 0
        self.failure = None; self.closed = threading.Event(); self.ready = threading.Event()
        self.model_mode = model_mode
        self.model_request = None
        self.model_permit = None
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
                with self.lock:
                    if self.model_request is not None:
                        challenge['model_request'] = dict(self.model_request)
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
                permit = None
                if 'model_request' in challenge:
                    if not isinstance(ack, dict) or 'model_permit' not in ack:
                        raise ValueError('model_permit_response_missing')
                    model_value = ack['model_permit']
                    ack = {key:value for key,value in ack.items() if key != 'model_permit'}
                    permit = _model_permit(model_value, challenge['model_request'])
                if ack != expected or not began <= self.clock() <= deadline:
                    raise RuntimeError('pc_heartbeat_ack_invalid_or_expired')
                with self.lock:
                    if self.failure is not None: raise RuntimeError('pc_heartbeat_already_failed')
                    if permit is not None:
                        expires_ns = math.floor(began * 1_000_000_000) + permit['budget_ns']
                        if math.floor(self.clock() * 1_000_000_000) >= expires_ns:
                            raise RuntimeError('model_permit_expired_before_arrival')
                        new = {k:permit[k] for k in ('goal_id', 'task_sha256', 'decision_sha256')}
                        new['deadline_monotonic_ns'] = expires_ns
                        if self.model_permit is None:
                            self.model_permit = new
                        elif any(self.model_permit[k] != new[k] for k in ('goal_id', 'task_sha256', 'decision_sha256')):
                            raise RuntimeError('model_permit_changed')
                        # Later pongs cannot extend the first permit deadline.
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

    def begin_model_permit(self, goal_id, task_sha256):
        request = _model_request({'goal_id':goal_id, 'task_sha256':task_sha256})
        with self.lock:
            if not self.model_mode or self.failure is not None or self.closed.is_set():
                raise RuntimeError('model_permit_mode_unavailable')
            if self.model_request is not None:
                raise RuntimeError('model_permit_already_requested')
            self.model_request = request

    def permit_snapshot(self):
        with self.lock:
            now = self.clock()
            if (self.failure is not None or self.closed.is_set() or self.model_permit is None or
                    self.last is None or not 0 <= now-self.last <= MAX_GAP_S or
                    math.floor(now*1_000_000_000) >= self.model_permit['deadline_monotonic_ns']):
                return None
            return dict(self.model_permit)

    def close(self):
        self.closed.set(); self.thread.join(1.0)
        return not self.thread.is_alive()


class PcHeartbeatPump:
    """Dedicated PC writer fed only with fresh challenges from result reader."""
    def __init__(self, fd, session_id, *, model_permit=None):
        if not isinstance(session_id, str) or not re.fullmatch('[0-9a-f]{32}', session_id):
            raise ValueError('invalid_pc_session')
        if model_permit is not None and not callable(model_permit):
            raise ValueError('model_permit_callback_invalid')
        self.fd, self.session_id = fd, session_id
        self.model_permit_callback = model_permit
        self.closed = threading.Event(); self.failed = threading.Event(); self.failure = None
        self.challenges = queue.Queue(maxsize=1); self.sequence = 0
        # Serialize only the nonblocking write itself with close. No model
        # callback, select wait, or disk/network operation holds this lock.
        self.write_lock = threading.Lock()
        os.set_blocking(fd, False)
        self.thread = threading.Thread(target=self._send_loop, daemon=True); self.thread.start()

    def submit(self, row):
        fields = {'event','session_id','sequence','nonce'}
        if (self.failed.is_set() or self.closed.is_set() or not isinstance(row, dict) or
                set(row) not in (fields, fields | {'model_request'}) or row['event'] != 'pc_ping' or
                row['session_id'] != self.session_id or type(row['sequence']) is not int or
                row['sequence'] != self.sequence or not isinstance(row['nonce'], str) or
                not re.fullmatch('[0-9a-f]{32}', row['nonce'])):
            self.failed.set(); raise ValueError('pc_challenge_invalid')
        copy = dict(row, event='pc_pong')
        if 'model_request' in row:
            try:
                copy['model_request'] = _model_request(row['model_request'])
                if self.model_permit_callback is None:
                    raise ValueError('model_permit_callback_required')
            except ValueError:
                self.failed.set(); raise
        self.sequence += 1
        try: self.challenges.put_nowait(copy)
        except queue.Full as exc:
            self.failure = 'pc_challenge_queue_full'; self.failed.set(); raise RuntimeError(self.failure) from exc

    def _send_loop(self):
        try:
            while not self.closed.is_set():
                try: response = self.challenges.get(timeout=.05)
                except queue.Empty: continue
                if 'model_request' in response:
                    request = _model_request(response['model_request'])
                    response['model_permit'] = _model_permit(self.model_permit_callback(request), request)
                if self.closed.is_set():
                    return
                data = (json.dumps(response, separators=(',', ':'))+'\n').encode()
                view = memoryview(data); deadline = time.monotonic()+WRITE_TIMEOUT_S
                while view:
                    if self.closed.is_set():
                        return
                    remaining = deadline-time.monotonic()
                    if remaining <= 0: raise TimeoutError('pc_heartbeat_write_timeout')
                    _, writable, _ = select.select([], [self.fd], [], remaining)
                    if not writable: raise TimeoutError('pc_heartbeat_write_timeout')
                    with self.write_lock:
                        if self.closed.is_set():
                            return
                        try: count = os.write(self.fd, view)
                        except BlockingIOError: continue
                    if count <= 0: raise BrokenPipeError('pc_heartbeat_write_failed')
                    view = view[count:]
        except BaseException as exc:
            self.failure = type(exc).__name__ + ':' + str(exc); self.failed.set()

    def close(self):
        self.closed.set()
        # Once this lock is acquired, any already-started write completed and
        # no later write can start, even if a callback remains blocked.
        with self.write_lock:
            pass
        self.thread.join(1.0)
        return not self.thread.is_alive()
