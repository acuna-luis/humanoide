#!/usr/bin/env python3
"""Continue table74 after the precise post-success approach log failure.

Default --plan is offline. --check prepares a local immutable recovery record
and checks precontact without moving; --run continues precontact through HOME.
The original failed journal remains failed. It is consumed once only after
current preflight, immediately before the next action; approach is not replayed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = 'scripts.box_handling'

from . import scenario1_cli as cli
from . import scenario1_table74_cycle as cycle
from . import scenario1_table74_current_lower_run as lower
from . import scenario1_table74_log_recovery as recovery


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--continue-deposit', action='store_true', required=True)
    p.add_argument('--table-height-cm', type=float, choices=(74.,), required=True)
    p.add_argument('--after', type=Path, required=True, help='Original failed approach/physical-run directory')
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('--plan', action='store_true', help='Offline default; no source reads or files created')
    mode.add_argument('--check', action='store_true', help='Read-only precontact check; no installation or movement')
    mode.add_argument('--run', action='store_true', help='Continue from precontact; never repeat approach or pickup')
    p.add_argument('--recovery-confirmed', action='store_true',
        help='Current box remains held, stable, entirely above the 74 cm table, same posture/setup; '
             'no reboot, manual movement or competing control since the interruption. '
             'Path including HOME clear, charger off, stops released, wheels in navigation, '
             'other controls stopped and observer at E-stop; geometry follows the recorded recipe')
    p.add_argument('--evidence-dir', type=Path, help='New private local directory')
    return p


def prepare_recovery(after, evidence):
    """Copy exact source bytes; add separate provenance, never edit history."""
    after, evidence = Path(after), Path(evidence)
    if any(p.is_symlink() for p in (after, *after.parents)):
        raise ValueError('Recovery source path cannot contain symlinks')
    after = after.resolve(strict=True)
    if not after.is_dir() or (after/'trial.json.consumed.json').exists():
        raise ValueError('Recovery source missing or already consumed; no replay')
    raw = {}
    for name in lower.FILES:
        path = after/name
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 16*1024*1024:
            raise ValueError('Recovery source file missing, unsafe or oversized: '+name)
        raw[name] = path.read_bytes()
    if sum(map(len, raw.values())) > 32*1024*1024:
        raise ValueError('Recovery source exceeds aggregate proof bounds')
    proof = {name: ([json.loads(line) for line in value.decode().splitlines() if line.strip()]
                   if name == 'events.jsonl' else json.loads(value)) for name, value in raw.items()}
    receipt = dict(version=1, kind='table74_log_only_recovery', next_stage='precontact',
        source_directory=str(after), source_sha256={name:hashlib.sha256(value).hexdigest() for name,value in raw.items()},
        proof_sha256=lower.digest(proof), operator_state_assumed_unchanged=True,
        current_physical_measurement=False)
    proof['recovery-authorization.json'] = receipt
    recovery.validate_proof(proof, json.loads(cycle.PROFILE.read_text()))
    lower.validate_recovery_source(proof)
    copied = evidence/'recovery-source'
    copied.mkdir(parents=False, exist_ok=False, mode=0o700)
    for name, value in raw.items():
        (copied/name).write_bytes(value)
    cli.atomic_json(copied/'recovery-authorization.json', receipt)
    return copied


def main(argv=None):
    args = parser().parse_args(argv)
    if not args.run and not args.check:
        print(json.dumps(dict(mode='plan', application='table74_continue_after_log_failure',
            source=str(args.after), source_validated=False, movement_commands_sent=0, files_created=0,
            original_journal_modified=False, approach_repeated=False, pickup_repeated=False,
            remaining=['precontact_14cm', 'support_5cm', 'pin_relief_4cm', 'lateral_open_10cm', 'measured_home'],
            requires_current_recovery_confirmation=True), indent=2, ensure_ascii=False))
        return 0
    if not args.recovery_confirmed:
        raise ValueError('--recovery-confirmed is required: current held box, unchanged posture, '
            'clear full path, charger off, stops released, other controls stopped and observer at E-stop')
    evidence = args.evidence_dir or cli.ROOT.parent/'Humanoide-vla-evidence'/(
        time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())+'_TABLE74_CONTINUATION_'+str(os.getpid()))
    evidence.mkdir(parents=True, exist_ok=False, mode=0o700)
    copied = prepare_recovery(args.after, evidence)
    selected = cli.parser('assume', 'optimistic_v1').parse_args([
        '--table-height-cm', '74', '--run' if args.run else '--check',
        '--evidence-dir', str(evidence/'continuation')])
    selected.table74_after = copied
    print('CONTINUACION74: se omiten recogida, navegación y aproximación; primer movimiento: descenso14cm.', flush=True)
    return cycle.run(selected, SimpleNamespace(requested=False))


def entrypoint(argv=None):
    try:
        return main(argv)
    except (Exception, KeyboardInterrupt) as exc:
        print('CONTINUACION74_BLOQUEADA: '+(str(exc) or type(exc).__name__), file=sys.stderr)
        print('Sin repetición de aproximación, recogida ni HOME de recuperación.', file=sys.stderr)
        return 130 if isinstance(exc, KeyboardInterrupt) else 78


if __name__ == '__main__':
    raise SystemExit(entrypoint())
