#!/usr/bin/env python3
"""Release a confirmed stale video accept() only; never sends robot commands.

This intentionally consumes the broken receiver, unlike the read-only checks.
The operator must subsequently activate a fresh Listen in XRoboToolkit.
"""
import argparse
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time

if __package__:
    from .pico_camera_receiver import _app_pid, _query, forwarded_port, has_listener, lifecycle_status, ReceiverError
else:
    from pico_camera_receiver import _app_pid, _query, forwarded_port, has_listener, lifecycle_status, ReceiverError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', required=True)
    parser.add_argument('--expected-pid', required=True)
    parser.add_argument('--failed-log', type=Path, required=True, help='Saved logcat JSON from this same failed PID')
    parser.add_argument('--evidence', type=Path, required=True, help='New private receipt file')
    parser.add_argument('--apply', action='store_true', help='Send one empty EOF connection to the broken video receiver')
    args = parser.parse_args()
    if args.evidence.exists():
        raise RuntimeError('Receipt already exists')
    if _query(args.serial, ['shell','getprop','ro.serialno'], None).strip() != args.serial:
        raise RuntimeError('PICO identity differs')
    if _app_pid(args.serial, None) != args.expected_pid:
        raise RuntimeError('Failed app PID changed; do not release a different receiver')
    saved = json.loads(args.failed_log.read_text())['stdout']
    if not saved.splitlines() or any(line.split()[2] != args.expected_pid for line in saved.splitlines()
                                   if len(line.split()) >= 6 and line[0].isdigit()):
        raise RuntimeError('Saved log PID does not match')
    try:
        lifecycle_status(saved, 12345)
    except ReceiverError as error:
        if not any(word in str(error) for word in ('terminate in time','EADDRINUSE','Address already in use')):
            raise
    else:
        raise RuntimeError('No confirmed stale-accept error in the saved log')
    remote = forwarded_port(_query(args.serial, ['forward','--list'], None), args.serial, 12345)
    if remote != 12345:
        raise RuntimeError('This recovery only supports video port 12345')
    if not has_listener(_query(args.serial, ['shell','ss','-ltn'], None), 12345):
        raise RuntimeError('No stale listener remains to release')
    connections = _query(args.serial, ['shell','ss','-tn'], None)
    if any(':12345' in line and 'ESTAB' in line for line in connections.splitlines()):
        raise RuntimeError('Video already has a connection; recovery not allowed')
    for item in Path('/proc').iterdir():
        if not item.name.isdecimal():
            continue
        try:
            command = (item/'cmdline').read_bytes().split(b'\0')
        except (OSError, PermissionError):
            continue
        if any(arg.endswith((b'/pico_camera_relay.py', b'/pico_control')) or arg == b'pico_control'
               for arg in command):
            raise RuntimeError('A camera relay or control client is active')
    check = subprocess.run(['bash', str(Path(__file__).with_name('configure_pico_xr_usb.sh')), '--check'],
                           capture_output=True, text=True, timeout=15,
                           env=dict(os.environ,PICO_SERIAL=args.serial))
    if check.returncode or 'BACKEND_STOP_CONFIRMED=1' not in check.stdout:
        raise RuntimeError('Passive backend STOP not confirmed')
    # The operator must have explicitly closed this video window. Do not
    # consume a later healthy Listen just because this PID once had an error.
    latest = _query(args.serial, ['logcat','--pid='+args.expected_pid,'-d','-s',
                                 'MediaDecoder:I','Unity:I','*:S'], None)
    closed = list(re.finditer(r'RemoteCameraWindow OnDisable',latest))
    opened = list(re.finditer(r'StartListen port:|startTCPServer:',latest))
    if not closed or (opened and opened[-1].start() > closed[-1].start()):
        raise RuntimeError('Close the video window/Listen first; a fresh close must be visible in current logcat')
    if _app_pid(args.serial,None) != args.expected_pid:
        raise RuntimeError('Application changed before release')
    if forwarded_port(_query(args.serial,['forward','--list'],None),args.serial,12345) != 12345:
        raise RuntimeError('Forward changed before release')
    if any(':12345' in line and 'ESTAB' in line for line in _query(args.serial,['shell','ss','-tn'],None).splitlines()):
        raise RuntimeError('A video connection appeared; recovery not allowed')
    if not has_listener(_query(args.serial,['shell','ss','-ltn'],None),12345):
        raise RuntimeError('Listener already closed; no disposal needed')
    receipt = {'pid':args.expected_pid,'serial':args.serial,'saved_failed_log':str(args.failed_log),
               'backend_stop_confirmed':True,'applied':args.apply,'control_commands_sent':False,
               'fresh_window_close_verified':True,'current_logcat':latest}
    with args.evidence.open('x') as output:
        json.dump(receipt,output,indent=2)
    try:
        if args.apply:
            # Intentional disposal of this proven broken server, never a health probe.
            receipt['connection_attempted'] = True
            with socket.create_connection(('127.0.0.1',12345), timeout=2) as connection:
                connection.shutdown(socket.SHUT_WR)
                try:
                    receipt['remote_eof_received'] = connection.recv(1) == b''
                except TimeoutError:
                    receipt['remote_eof_received'] = False
            deadline = time.monotonic()+8
            while has_listener(_query(args.serial, ['shell','ss','-ltn'], deadline),12345):
                if time.monotonic() >= deadline:
                    raise RuntimeError('Stale listener did not close; do not retry automatically')
                time.sleep(.2)
            receipt['listener_closed'] = True
    except Exception as error:
        receipt['error'] = str(error)
        raise
    finally:
        with args.evidence.open('w') as output:
            json.dump(receipt,output,indent=2)
    print('PICO_STALE_VIDEO_RELEASED=1' if args.apply else 'PICO_STALE_VIDEO_RELEASE_CHECK_OK=1')
    print('Ahora activar una nueva sesión ZEDMINI / Listen una sola vez.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('PICO_STALE_VIDEO_RELEASE_ERROR='+str(error),file=sys.stderr)
        sys.exit(1)
