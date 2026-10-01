"""Bounded JSONL transport to a persistent child; no ROS or robot commands here."""
import json
import queue
import subprocess
import threading
import time


def recoverable_home_receipt(request, request_id, receipt, rows):
    """Validate the narrow opt-in failure before keeping this channel alive.

    This independently checks the worker's claim. A status=6 remains a failure
    result in returned rows; only the supervisor can decide a bounded retry.
    """
    if (request.get('allow_home_retry') is not True
            or request.get('goal') != {'task_name': 'cruzr/home', 'yaml_args': '{}'}
            or receipt.get('recoverable_home_failure') is not True
            or type(receipt.get('returncode')) is not int or receipt['returncode'] != 2
            or receipt.get('request_id') != request_id):
        return False
    goal_id = receipt.get('goal_id')
    if not isinstance(goal_id, str) or not goal_id:
        return False
    allowed = {'dispatched', 'accepted', 'result_pending', 'feedback', 'status', 'result', 'error'}
    if any(row.get('event') not in allowed or row.get('goal_id') != goal_id
           or row.get('request_id') != request_id for row in rows):
        return False
    dispatched = [row for row in rows if row['event'] == 'dispatched']
    accepted = [row for row in rows if row['event'] == 'accepted']
    results = [row for row in rows if row['event'] == 'result']
    errors = [row for row in rows if row['event'] == 'error']
    if (len(dispatched) != 1 or dispatched[0].get('endpoint') != '/mc/manipulation/action'
            or len(accepted) != 1 or accepted[0].get('accepted') is not True
            or len(results) != 1 or len(errors) != 1
            or errors[0].get('reason') != 'Action did not report successful terminal application result'):
        return False
    if not (rows.index(dispatched[0]) < rows.index(accepted[0]) < rows.index(results[0]) < rows.index(errors[0])):
        return False
    terminal = results[0]
    result = terminal.get('result')
    state = result.get('state') if isinstance(result, dict) else None
    if (type(terminal.get('status')) is not int or terminal['status'] != 6
            or not isinstance(state, dict) or type(state.get('state')) is not int
            or state['state'] != 7104050 or state.get('desc') != 'MoveToGoalFailed'):
        return False
    return (all(type(row.get('status')) is int and row['status'] in (1, 2, 6)
                for row in rows if row['event'] == 'status')
            and all(type(row.get('status')) is int and row['status'] in (0, 1, 2)
                    for row in rows if row['event'] == 'result_pending'))


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
                    if recoverable_home_receipt(request, request_id, event, rows):
                        return rows
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
