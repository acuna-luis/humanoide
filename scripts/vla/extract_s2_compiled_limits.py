#!/usr/bin/env python3
"""Extract pinned S2 constructor limit data offline; never loads vendor code."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

SHA256 = '2a41cf5520672c9dcbd1c532eff775b4ce6d9ff1e100485d6ca7ba8174ad251c'
ADDRESS = 0x2fe20


def position_domains(a, b, lo, hi, error):
    """Separate command compliance from a geometric uncertainty enclosure.

    Do not clip the error band or infer physical tracking from a configured limit.
    An overhang alone is neither a nominal violation nor an invalid enclosure.
    """
    if not all(math.isfinite(v) for v in (a,b,lo,hi,error)) or lo > hi or error < 0:
        raise ValueError('Invalid position domain')
    return dict(nominal_interval_rad=[min(a,b),max(a,b)],
                uncertainty_interval_rad=[min(a,b)-error,max(a,b)+error],
                nominal_inside=min(a,b)>=lo and max(a,b)<=hi,
                uncertainty_inside=min(a,b)-error>=lo and max(a,b)+error<=hi)


def extract(blob):
    if hashlib.sha256(blob).hexdigest() != SHA256:
        raise ValueError('Unreviewed S2 arm library')
    if blob[:6] != b'\x7fELF\x02\x01' or struct.unpack_from('<H', blob, 18)[0] != 62:
        raise ValueError('Expected x86-64 little-endian ELF')
    start = struct.unpack_from('<Q', blob, 32)[0]
    width, count = struct.unpack_from('<HH', blob, 54)
    for i in range(count):
        typ, flags, offset, va, _, size, _, _ = struct.unpack_from('<IIQQQQQQ', blob, start+i*width)
        if typ == 1 and va <= ADDRESS and ADDRESS+7*48 <= va+size:
            if flags & 2:
                raise ValueError('Expected immutable constructor constants')
            at = offset+ADDRESS-va
            return [list(struct.unpack_from('<6d', blob, at+i*48)) for i in range(7)]
    raise ValueError('Constructor data not in a file-backed ELF segment')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binary', type=Path, required=True)
    p.add_argument('--review', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    raw = extract(a.binary.read_bytes())
    review = json.loads(a.review.read_text())
    error = review['geometry_audit']['joint_error_scenario_rad']
    rows = []
    for stage in review['stages']:
        if stage['type'] != 'arm':
            continue
        if len(stage['joint_names']) != 7:
            raise ValueError('Expected seven arm axes')
        for i, name in enumerate(stage['joint_names']):
            index = review['joint_order'].index(name)
            x,y = stage['start_20d_rad'][index],stage['end_20d_rad'][index]
            lo,hi = raw[i][:2]
            rows.append(dict(joint=name, compiled_position_limits_rad=[lo,hi],
                **position_domains(x,y,lo,hi,error)))
    result = dict(scope='COMPILED_CONSTRUCTOR_DATA_NOT_EFFECTIVE_RUNTIME_LIMITS',
        binary_sha256=SHA256, address=hex(ADDRESS), record_bytes=48,
        constructor_copy_address='0x2766f', setter_call_address='0x276f3',
        raw_six_doubles_per_joint=raw,
        first_two_fields='ClosedInterval position endpoints',
        remaining_fields='Native scalar limits; field semantics not fully qualified',
        comparison_assumes_proposed_joint_order=True, runtime_joint_order_verified=False,
        nominal_position_domain_pass=all(r['nominal_inside'] for r in rows),
        uncertainty_overhang_interpretation='Not a nominal command violation; retain full geometric band. No tracking or stopping guarantee follows.',
        uncertainty_clipped=False,
        rows=rows, physical_approval=False, movement_commands=0,
        sources_sha256={str(f.resolve()):hashlib.sha256(f.read_bytes()).hexdigest()
                       for f in (a.binary,a.review,Path(__file__))})
    with a.output.open('x') as f:
        json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(dict(nominal_outside=[r['joint'] for r in rows if not r['nominal_inside']],
        uncertainty_outside=[r['joint'] for r in rows if not r['uncertainty_inside']],
        physical_approval=False)))


if __name__ == '__main__':
    main()
