#!/usr/bin/env python3
"""Exercise the guard's cancel watchdog against a synthetic ROS action only.

This diagnostic uses real telemetry but a copied guard whose action endpoints
are remapped to a private fake action server. It never sends to the real robot
action endpoint and it cannot establish physical stopping.
"""
import hashlib
import json
import os
import queue
import re
import subprocess
import sys
import tempfile
import threading
import time
import uuid

import arm_from_pico_supervised as arm
import arm_native_lease_bridge as bridge
import pico_wrist_docker_launcher as launch
import pico_wrist_pc_heartbeat as heartbeat
import prepare_pico_wrist_native_probe as probe


PATTERN = re.compile(r'/codex_smolvla_diag_[0-9a-f]{32}/action\Z')
REAL_ENDPOINT = '/mc/manipulation/action'


class Lines:
    def __init__(self, stream):
        self.lines = queue.Queue()
        self.pending = []
        self.stream = stream
        self.thread = threading.Thread(target=self.read, daemon=True)
        self.thread.start()

    def read(self):
        try:
            for raw in self.stream:
                if len(raw) > 8192:
                    raise ValueError('synthetic_output_oversize')
                self.lines.put(json.loads(raw))
        except BaseException as exc:
            self.lines.put({'event':'SYNTHETIC_OUTPUT_ERROR', 'reason':str(exc)})
        finally:
            self.lines.put({'event':'SYNTHETIC_OUTPUT_CLOSED'})

    def get(self, expected, timeout, goal_id):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for i, row in enumerate(self.pending):
                if row.get('event') == expected and row.get('goal_id') == goal_id:
                    return self.pending.pop(i)
            try:
                row = self.lines.get(timeout=max(.001, deadline-time.monotonic()))
            except queue.Empty:
                break
            if row.get('event') == expected and row.get('goal_id') == goal_id:
                return row
            if row.get('event') in ('SYNTHETIC_OUTPUT_CLOSED', 'SYNTHETIC_OUTPUT_ERROR',
                                    'SYNTHETIC_WRONG_GOAL', 'SYNTHETIC_GOAL_TIMEOUT'):
                raise RuntimeError('synthetic_server_failed:' + str(row))
            self.pending.append(row)
        raise TimeoutError('synthetic_event_missing:' + expected)


class GuardOutputAudit:
    """Retain a preflight failure reason without blocking the guard reader."""
    def __init__(self, source):
        self.source=source
        self.preflight_reason=None

    def readline(self, size):
        raw=self.source.readline(size)
        try:
            row=json.loads(raw)
            if row.get('event')=='preflight_failed':
                reason=row.get('reason')
                self.preflight_reason=reason[:512] if isinstance(reason,str) else 'missing_reason'
        except (UnicodeError,ValueError,TypeError,AttributeError):
            pass  # The original guard reader still validates the actual line.
        return raw

    def close(self):
        return self.source.close()


def check(payload):
    required = {'session','manifest','urdf_text','transmissions_text','guard_source',
                'guard_sha256','synthetic_server_source','synthetic_server_sha256',
                'endpoint','goal_id'}
    if not isinstance(payload, dict) or set(payload) != required:
        raise ValueError('synthetic_payload_invalid')
    endpoint, goal_id = payload['endpoint'], payload['goal_id']
    if not isinstance(endpoint,str) or PATTERN.fullmatch(endpoint) is None:
        raise ValueError('synthetic_endpoint_required')
    if not isinstance(goal_id,str) or str(uuid.UUID(goal_id)) != goal_id or uuid.UUID(goal_id).int == 0:
        raise ValueError('synthetic_goal_uuid_required')
    for key in ('guard','synthetic_server'):
        source = payload[key+'_source']
        if (not isinstance(source,str) or not source or len(source)>1_000_000 or
                hashlib.sha256(source.encode()).hexdigest()!=payload[key+'_sha256']):
            raise ValueError('synthetic_source_hash_mismatch:'+key)
        compile(source, '<synthetic-check>', 'exec')
    guard_source = payload['guard_source']
    if REAL_ENDPOINT in guard_source or guard_source.count(endpoint) != 4:
        raise ValueError('guard_not_fully_remapped')
    arm.validate_preflight(payload['session'], 0, dry_run=True)
    probe.validate(payload['manifest'],payload['urdf_text'],payload['transmissions_text'])
    session=payload['session'];output=launch.HostOutput(sys.stdout.fileno())
    launch.pc_preflight_handoff(session,output,sys.stdin.fileno())
    if not output.emit({'event':'HOST_HEARTBEAT_READY','session_id':session['session_id']}):
        raise RuntimeError('operator_output_unavailable')
    pc=heartbeat.PcHeartbeat(sys.stdin.fileno(),session['session_id'],output.emit)
    guard=server=pipe=None
    try:
        pc.await_ready(3)
        app,ros=launch.discover_containers()
        with tempfile.TemporaryDirectory(prefix='synthetic-wrist-cancel-',dir='/tmp') as directory:
            launch.verify_shared_tmp(directory,app)
            try:
                server=launch.start_streamed(ros,'/opt/ros/humble/setup.bash',
                    payload['synthetic_server_source'],{'endpoint':endpoint,'goal_id':goal_id},
                    stderr=sys.stderr)
                events=Lines(server.stdout)
                ready=events.get('SYNTHETIC_SERVER_READY',12,goal_id)
                if ready.get('endpoint') != endpoint:
                    raise RuntimeError('synthetic_endpoint_mismatch')
                guard=launch.start_streamed(ros,'/opt/ros/humble/setup.bash', guard_source,
                    session,stderr=sys.stderr,
                    verified={'role':'guard','session_id':session['session_id'],
                              'source_sha256':payload['guard_sha256']})
                guard.stdout=GuardOutputAudit(guard.stdout)
                lease=bridge.GuardLease(directory,payload['manifest']['input']['reference_20d'],
                    lambda: guard.poll() is None and pc.alive() and not output.failed,
                    session_id=session['session_id'])
                pipe=bridge.GuardPipe(guard,lease,time.monotonic()-session['age_at_handoff_s'],
                                      enable_guard_heartbeat=True)
                try:
                    pipe.await_ready(26)
                except RuntimeError as exc:
                    reason=guard.stdout.preflight_reason
                    raise RuntimeError(str(exc)+';guard_preflight_reason='+str(reason)) from exc
                pipe.checked_snapshot()
                lease.synchronize_uuid(goal_id,pipe.exchange)
                if lease.goal_id != goal_id:
                    raise RuntimeError('synthetic_uuid_handoff_mismatch')
                launch.write_stream(server.stdin.fileno(),
                    (json.dumps({'command':'send_synthetic','goal_id':goal_id})+'\n').encode(),1)
                events.get('SYNTHETIC_GOAL_SENT',5,goal_id)
                events.get('SYNTHETIC_GOAL_ACTIVE',5,goal_id)
                # Stop only the diagnostic heartbeat; no actual robot action
                # has been created or sent. The copied guard must time out.
                pipe.enable_guard_heartbeat=False
                cancel=events.get('SYNTHETIC_CANCEL_ACCEPTED',8,goal_id)
                terminal=events.get('SYNTHETIC_GOAL_CANCELED',5,goal_id)
                guard.wait(timeout=8)
                pipe.thread.join(3)
                records=list(pipe.guard_events)
                if (guard.returncode != 1 or pipe.thread.is_alive() or
                        not any(e.get('event')=='OPERATOR_ALERT' and
                                'supervisor_heartbeat_expired' in e.get('reason','') for e in records) or
                        not any(e.get('event')=='guard_auto_cancel_requested' for e in records) or
                        not any(e.get('event')=='guard_terminal_observed' and e.get('status')==5 for e in records)):
                    raise RuntimeError('guard_watchdog_cancel_not_observed')
                if server.wait(timeout=5)!=0 or cancel.get('goal_id')!=terminal.get('goal_id'):
                    raise RuntimeError('synthetic_terminal_not_confirmed')
                return {'status':'SYNTHETIC_WATCHDOG_CANCEL_PASSED', 'endpoint':endpoint,
                        'goal_id':goal_id, 'synthetic_goals':1, 'physical_goals':0,
                        'synthetic_cancel_accepted':True, 'synthetic_terminal_status':5,
                        'guard_events':records,'physical_control_qualified':False,
                        'limitations':['guard action endpoints remapped in transient copy',
                         'synthetic action server and goal only', 'no real cancellation or braking',
                         'real telemetry and point-in-time process inventory do not prove exclusivity']}
            finally:
                if pipe is not None:
                    pipe.enable_guard_heartbeat=False
                for child in (server,guard):
                    if child is not None:
                        if child.poll() is None:
                            child.terminate()
                            try: child.wait(timeout=3)
                            except subprocess.TimeoutExpired:
                                child.kill(); child.wait(timeout=3)
                        for stream in (child.stdin,child.stdout):
                            if stream is not None: stream.close()
    finally:
        pc.close()


if __name__=='__main__':
    raise SystemExit('Run through the synthetic no-motion wrapper')
