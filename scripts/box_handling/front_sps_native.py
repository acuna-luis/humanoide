#!/usr/bin/env python3
"""Native ROSA SPS perception adapter. Only box/0, no motion endpoints."""
import argparse
import json
from pathlib import Path
import socket
import threading
import time

from front_sps_contract import (DETECTION_ACTION, PRECISE_ACTION,
                                SelectionTransaction, validate_goal, wait_terminal_result)


def main():
    import rosa
    from rosa.common import GoalResponse, CancelResponse
    from rosa.base._ActionType import to_string
    from cv_task_msgs.action import VisionActionTask

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True, type=Path)
    args = parser.parse_args()
    transaction = SelectionTransaction()
    lock = threading.Lock()
    busy = False
    canceled = set()
    state_lock = threading.Lock()
    rosa.init()
    node = rosa.Node('front_box_sps_adapter')
    goal_type = VisionActionTask.Goal.getTypeHelper()
    result_type = VisionActionTask.Result.getTypeHelper()

    class TerminalResultServer(rosa.ActionServer):
        # Vendor Python ActionServer returns EXECUTING immediately when a C++
        # client asks GetResult before computation ends. Its callback executes
        # in the server thread pool; wait boundedly for our terminal result.
        # This local subclass does not modify the installed ROSA library.
        def result_request_received(self, request, response, request_header):
            try:
                final = wait_terminal_result(self.goal_result, self.handle_lock,
                                             to_string(request.goal_id.uuid))
                response.result = final.result
                response.status = final.status
            except TimeoutError as exc:
                transaction.invalidate()
                event('failed', stage='get_result', reason=str(exc))
                response.status = 6
                response.result = result_type.msg_from_json('{"ok":false}')

    def event(kind, **fields):
        entry = dict(event=kind, time_ns=time.time_ns(), **fields)
        with (args.session/'selection.jsonl').open('a') as stream:
            stream.write(json.dumps(entry, allow_nan=False)+'\n')
        print(json.dumps(entry, allow_nan=False), flush=True)

    def goal_cb(uuid, goal):
        nonlocal busy
        try:
            validate_goal(json.loads(goal_type.msg_to_json(goal)))
            with state_lock:
                if busy or transaction.failed or (args.session/'stop').exists():
                    return GoalResponse.REJECT
                busy = True
            return GoalResponse.ACCEPT_AND_EXECUTE
        except Exception as exc:
            event('goal_rejected', reason=str(exc))
            return GoalResponse.REJECT

    def cancel_cb(handle):
        with state_lock:
            canceled.add(to_string(handle.get_goal_id()))
        transaction.invalidate()
        return CancelResponse.ACCEPT

    def accepted(handle, stage):
        nonlocal busy
        goal_id = to_string(handle.get_goal_id())
        released = False
        try:
            with lock:
                if stage == 'detect':
                    with socket.socket(socket.AF_UNIX) as conn:
                        conn.settimeout(8.5)
                        conn.connect(str(args.session/'perception.sock'))
                        conn.sendall(b'capture\n')
                        with conn.makefile('rb') as stream:
                            raw = stream.readline(2_000_001)
                        if len(raw) > 2_000_000 or not raw.endswith(b'\n'):
                            raise RuntimeError('Malformed worker response')
                    payload = json.loads(raw)
                    if 'error' in payload:
                        raise RuntimeError(payload['error'])
                    # Preserve the actual camera poses and exact-time TF even
                    # if selection fails; a generic Motion error loses these.
                    event('captured', native_goal=goal_id, detection=payload['report'])
                    result = transaction.detect(payload['report'], time.time_ns())
                    event('detected', native_goal=goal_id, **transaction.pending)
                else:
                    result, selected = transaction.select(time.time_ns())
                    event('selected', native_goal=goal_id, **selected)
                with state_lock:
                    if goal_id in canceled or transaction.failed:
                        raise RuntimeError('Perception transaction canceled')
                    handle.succeed(result_type.msg_from_json(json.dumps(result)))
                    busy = False
                    released = True
        except Exception as exc:
            transaction.invalidate()
            event('failed', stage=stage, native_goal=goal_id, reason=str(exc))
            result = result_type.msg_from_json('{"ok":false,"sps_outputs":{"is_empty":true}}')
            if goal_id in canceled:
                handle.canceled(result)
            else:
                handle.abort(result)
        finally:
            if not released:
                with state_lock:
                    busy = False

    servers = [TerminalResultServer(node, DETECTION_ACTION, goal_cb, cancel_cb,
                                   lambda handle: accepted(handle, 'detect'), VisionActionTask),
               TerminalResultServer(node, PRECISE_ACTION, goal_cb, cancel_cb,
                                   lambda handle: accepted(handle, 'select'), VisionActionTask)]
    (args.session/'native.ready').write_text('ready\n')
    deadline = json.loads((args.session/'lease.json').read_text())['deadline']
    try:
        while rosa.ok() and time.monotonic() < deadline and not (args.session/'stop').exists():
            rosa.spin_once(node, 20)
            time.sleep(0.01)
    finally:
        rosa.shutdown()


if __name__ == '__main__':
    main()
