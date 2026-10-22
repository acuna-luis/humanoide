#!/usr/bin/env python3
"""Observe a local cycle journal; never launch, query or signal the robot.

Start before the separately authorized cycle. Ctrl+C stops only this observer.
The destination must be new; the cycle journal is always opened read-only.
"""
import argparse
import json
from pathlib import Path
import time


FIELDS = ('created_ns', 'updated_ns', 'status', 'in_flight', 'phase_boundary', 'after')
TERMINAL = {'succeeded', 'failed', 'interrupted', 'paused', 'checked', 'installation_pending'}


def observe(evidence, output, timeout_s):
    journal = evidence / 'cycle.json'
    if output.resolve() == journal.resolve() or output.resolve().is_relative_to(evidence.resolve()):
        raise ValueError('Observer output must be outside cycle evidence')
    # Reserve exclusive output before waiting. Existing evidence is never overwritten.
    with output.open('x', encoding='utf-8', buffering=1) as stream:
        deadline = time.monotonic() + timeout_s
        last, identity = None, None
        malformed_reads = 0
        while time.monotonic() < deadline:
            try:
                cycle = json.loads(journal.read_text())
            except FileNotFoundError:
                time.sleep(.01)
                continue
            except json.JSONDecodeError:
                malformed_reads += 1
                time.sleep(.01)
                continue
            if not isinstance(cycle, dict):
                raise ValueError('Cycle journal must be a JSON object')
            if type(cycle.get('created_ns')) is not int or type(cycle.get('updated_ns')) is not int:
                raise ValueError('Cycle journal needs integer PC timestamps')
            if identity is None:
                identity = cycle['created_ns']
            if cycle['created_ns'] != identity:
                raise ValueError('Cycle identity changed; do not combine runs')
            selected = {key: cycle.get(key) for key in FIELDS}
            if selected != last:
                stream.write(json.dumps(dict(time_ns=time.time_ns(),
                    monotonic_ns=time.monotonic_ns(), cycle=selected,
                    malformed_reads=malformed_reads)) + '\n')
                last = selected
                print(json.dumps(selected), flush=True)
            if cycle.get('status') in TERMINAL:
                return 0
            time.sleep(.01)
    print('Observer timeout; capture is partial. No cycle command was sent.', flush=True)
    return 2


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True, help='Local cycle directory, possibly not created yet')
    parser.add_argument('--output', type=Path, required=True, help='New JSONL file outside cycle directory')
    parser.add_argument('--timeout-s', type=float, default=1800)
    args = parser.parse_args(argv)
    if not 0 < args.timeout_s <= 86400:
        parser.error('--timeout-s must be in (0, 86400]')
    try:
        return observe(args.evidence, args.output, args.timeout_s)
    except KeyboardInterrupt:
        print('Observer stopped; the cycle was not signalled.', flush=True)
        return 130


if __name__ == '__main__':
    raise SystemExit(main())
