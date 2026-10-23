"""Resident posture-only HOME. Native supervision reused; no base command/retry."""
import fcntl
import signal
import threading
import time
from scenario1_runtime import Runtime, atomic_json
import scenario1_contract as contract


def main(payload):
    runtime = Runtime(payload)
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, lambda *_: runtime.stop.set())
    threading.Thread(target=runtime.receive, daemon=True).start()
    watcher = threading.Thread(target=runtime.watchdog, daemon=True)
    watcher.start()
    try:
        runtime.lock = open('/tmp/cruzr-front-sps.lock', 'a')
        fcntl.flock(runtime.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        runtime.discover()
        runtime.hashes()
        runtime.health(require_home=False)
        runtime.start_live_monitor()
        runtime.stationary_base()
        runtime.quick_health()
        runtime.emit('ready', context={'containers': runtime.container_identity},
                     map_name='not_used_home_only', nav_state='not_used_home_only')
        if payload['mode'] == 'check':
            return 0
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            runtime.connected()
            try:
                message = runtime.commands.get(timeout=.1)
            except __import__('queue').Empty:
                continue
            if message != {'command': 'arm'}:
                raise RuntimeError('HOME requires one explicit arm')
            runtime.discover()
            runtime.hashes()
            runtime.health(require_home=False)
            runtime.stationary_base()
            runtime.quick_health()
            ledger = {'status': 'dispatch_intent', 'time_ns': time.time_ns(),
                      'empty_and_path': 'current_operator_declaration', 'base_commands': 0}
            atomic_json(runtime.session/'resident-home.json', ledger)
            runtime.armed = True
            result = runtime.action('motion', {'task_name': 'cruzr/home', 'yaml_args': '{}'}, 60)
            contract.validate_motion_result(result)
            runtime.health(require_home=True)  # Two new stamped 20D samples.
            ledger.update(status='home_measured', result=result)
            atomic_json(runtime.session/'resident-home.json', ledger)
            runtime.emit('home_complete', record=ledger)
            return 0
        raise RuntimeError('HOME arm deadline expired')
    except BaseException as exc:
        runtime.emit('error', reason=str(exc), physical_state='unconfirmed')
        return 78
    finally:
        runtime.stop.set()
        watcher.join(timeout=2)
        if runtime.session:
            runtime.write_lease()
            (runtime.session/'stop').touch()
        for worker in list(runtime.action_sessions.values()) + ([runtime.health_session] if runtime.health_session else []):
            worker.close()
        if runtime.lock:
            runtime.lock.close()
