#!/usr/bin/env python3
"""Offline, hash-pinned Motion group-pair trace; not a CAD exclusion policy."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path

from general_home.native_collision_policy import trace_group_pairs
import general_home.native_collision_policy as implementation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', type=Path, required=True, help='Private archived librobot.so')
    parser.add_argument('--output', type=Path, required=True, help='New JSON report')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a new output file')
    sources = [Path(__file__), Path(implementation.__file__), args.library]
    hashes = {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    traces = [trace_group_pairs(args.library, count) for count in (1, 2, 3, 4, 8, 16)]
    for trace in traces:
        expected = [list(pair) for pair in itertools.combinations(range(trace['group_count']), 2)]
        if trace['queried_group_pairs'] != expected:
            raise ValueError('Observed native loop differs from complete cross-group iteration')
    if any(hashlib.sha256(Path(p).read_bytes()).hexdigest() != sha for p, sha in hashes.items()):
        raise ValueError('Sources changed during analysis')
    result = dict(schema='cruzr-native-group-pair-audit-v1',
        status='GROUP_PAIR_LOOP_VERIFIED_NOT_CAD_INTERFACE_APPROVAL', traces=traces,
        source_sha256=hashes, physical_approval=False, installable=False,
        movement_commands=0, remote_changes=0,
        conclusion='The reviewed loop compares distinct primitive sets; it does not test a set against itself.',
        limitations=[
            'Synthetic group contents; no live group membership or control state read.',
            'Distance is stubbed; this report makes no geometric separation claim.',
            'Other branches and callers may perform further checks.',
            'Native primitives and CAD links are different representations.',
            'No CAD pair exclusion or mechanical contact region follows from this trace.'])
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(result['status'])


if __name__ == '__main__':
    main()
