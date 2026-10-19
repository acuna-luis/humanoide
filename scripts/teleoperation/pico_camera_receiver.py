"""Read-only verification of a PICO camera listener behind an ADB forward.

The PC's forwarded port can accept a connection while the PICO decoder is
closed. Inspect the device listener instead, without consuming its one session.
"""
from __future__ import annotations

import argparse
import math
import re
import subprocess
import sys
import time


class ReceiverError(RuntimeError):
    pass


def lifecycle_status(output: str, port: int) -> str:
    """Inspect only the latest Listen activation, using log order, not clocks."""
    activations = list(re.finditer(r'(?m)^.*\bStartListen port:\s*([0-9]+)\b.*$', output))
    if not activations:
        return 'unavailable'
    latest = activations[-1]
    if int(latest[1]) != port:
        raise ReceiverError('Latest PICO Listen activation targets a different camera port')
    block = output[latest.start():]
    fatal = re.search(r'TCP thread did not terminate in time|EADDRINUSE|Address already in use|'
                      r'TCP server error|Failed to initialize MediaCodec', block, re.IGNORECASE)
    if fatal:
        raise ReceiverError('PICO camera lifecycle failed after the latest Listen: ' + fatal[0]
                            + '. No alterne Listen otra vez: cierre la ventana y recupere el receptor '
                              'antes del siguiente intento. No reinicie el robot.')
    if re.search(r'\bstartTCPServer:\s*' + str(port) + r'\b', block):
        return 'verified'
    return 'unavailable'


def forwarded_port(output: str, target: str, local_port: int) -> int:
    """Require one exact TCP mapping owned by the selected ADB target."""
    rows = [line.split() for line in output.splitlines() if line.strip()]
    matches = [row for row in rows if len(row) >= 2
               and row[0] == target and row[1] == 'tcp:' + str(local_port)]
    if len(matches) != 1 or len(matches[0]) != 3:
        raise ReceiverError('Require one unambiguous ADB forward for the selected PICO and local port')
    remote = re.fullmatch(r'tcp:([0-9]+)', matches[0][2])
    if remote is None or not 1 <= int(remote[1]) <= 65535:
        raise ReceiverError('ADB forward must target a valid remote TCP port')
    return int(remote[1])


def has_listener(output: str, port: int) -> bool:
    """Parse IPv4/IPv6 ss LISTEN rows without opening any socket."""
    for line in output.splitlines():
        fields = line.split()
        if len(fields) < 5 or fields[0] != 'LISTEN':
            continue
        endpoint = fields[3]
        if ':' not in endpoint:
            continue
        raw_port = endpoint.rsplit(':', 1)[1]
        if raw_port.isdecimal() and int(raw_port) == port:
            return True
    return False


def _query(target: str, arguments: list[str], deadline: float | None) -> str:
    timeout = 5.0 if deadline is None else min(5.0, deadline - time.monotonic())
    if timeout <= 0:
        raise TimeoutError('PICO camera receiver deadline reached')
    try:
        result = subprocess.run(['adb', '-s', target, *arguments], capture_output=True,
                                text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as error:
        raise ReceiverError('ADB receiver query timed out; no connection probe was sent') from error
    if result.returncode:
        raise ReceiverError('ADB receiver query failed: ' + ' '.join(arguments))
    # Some PICO builds print a netlink permission warning on stderr while ss
    # returns successful, complete LISTEN rows on stdout. Only stdout is parsed.
    return result.stdout


def _app_pid(target: str, deadline: float | None) -> str:
    output = _query(target, ['shell', 'pidof', 'com.xrobotoolkit.client'], deadline).strip()
    pids = set(output.split())
    if len(pids) != 1 or not all(re.fullmatch(r'[1-9][0-9]*', pid) for pid in pids):
        raise ReceiverError('Cannot identify one current XRoboToolkit application PID')
    return pids.pop()


def _check_lifecycle(target: str, port: int, deadline: float | None) -> str:
    pid = _app_pid(target, deadline)
    output = _query(target, ['logcat', '--pid=' + pid, '-d', '-s',
                             'MediaDecoder:I', 'Unity:I', '*:S'], deadline)
    if _app_pid(target, deadline) != pid:
        raise ReceiverError('XRoboToolkit restarted during the receiver check; repeat the check')
    status = lifecycle_status(output, port)
    if status == 'unavailable':
        print('PICO_CAMERA_RECEIVER_WARNING: No hay marcadores suficientes de la última activación '
              'en el log del PID actual; sólo se verifica LISTEN, no el ciclo del decoder.',
              file=sys.stderr, flush=True)
    return status


def wait_for_receiver(serial: str, target: str | None = None, port: int = 12345,
                      wait: float = 0) -> int:
    """Verify identity/forward and wait for the decoder; return its remote port."""
    if not serial or not serial.strip() or any(c.isspace() for c in serial):
        raise ValueError('Expected PICO serial must be nonempty and contain no whitespace')
    target = serial if target is None else target
    if not target or any(c.isspace() for c in target):
        raise ValueError('ADB target must be nonempty and contain no whitespace')
    if not 1 <= port <= 65535:
        raise ValueError('Local camera port must be between 1 and 65535')
    if not math.isfinite(wait) or not 0 <= wait <= 600:
        raise ValueError('Receiver wait must be between 0 and 600 seconds')
    deadline = time.monotonic() + wait if wait > 0 else None
    identity = _query(target, ['shell', 'getprop', 'ro.serialno'], deadline).strip()
    if identity != serial:
        raise ReceiverError('PICO identity mismatch; camera receiver was not accepted')
    remote_port = forwarded_port(_query(target, ['forward', '--list'], deadline), target, port)
    next_notice = 0.0
    while True:
        if deadline is not None and time.monotonic() >= deadline:
            break
        try:
            output = _query(target, ['shell', 'ss', '-ltn'], deadline)
        except TimeoutError:
            break
        if has_listener(output, remote_port):
            lifecycle = _check_lifecycle(target, remote_port, deadline)
            print('PICO_CAMERA_RECEIVER_READY=1; serial=%s; forward=%s->%s; '
                  'lifecycle=%s; source=adb-ss-logcat-no-probe'
                  % (serial, port, remote_port, lifecycle), flush=True)
            return remote_port
        if deadline is None:
            break
        now = time.monotonic()
        if now >= next_notice:
            print('PICO_CAMERA_RECEIVER_WAIT: En Remote Vision seleccione ZEDMINI, active Listen '
                  'y confirme la IP; esperando LISTEN PICO:%s.' % remote_port,
                  file=sys.stderr, flush=True)
            next_notice = now + 5
        remaining = deadline - now
        if remaining <= 0:
            break
        time.sleep(min(1, remaining))
    raise ReceiverError('PICO decoder is not listening on TCP %s. En Remote Vision seleccione '
                        'ZEDMINI, cierre la ventana anterior, active Listen y confirme la IP. '
                        'El forward del PC no demuestra que el receptor esté abierto.' % remote_port)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', required=True, help='Expected physical PICO serial')
    parser.add_argument('--target', help='ADB target; defaults to expected serial')
    parser.add_argument('--port', type=int, default=12345, help='Local ADB forwarded camera port')
    parser.add_argument('--wait', type=float, default=0, help='Wait 0..600 seconds; 0 checks once')
    args = parser.parse_args()
    try:
        wait_for_receiver(args.serial, args.target, args.port, args.wait)
    except (ReceiverError, OSError, ValueError) as error:
        print('PICO_CAMERA_RECEIVER_ERROR=' + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
