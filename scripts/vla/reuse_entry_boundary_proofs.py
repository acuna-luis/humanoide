#!/usr/bin/env python3
"""Reuse only source-bound CAD boundary proofs enclosing the new joint domain."""
import argparse
import json
from pathlib import Path
import numpy as np
from prepare_vla_entry_bundle import digest


def domain_contains(source, target):
    if source['controlling_joints'] != target['controlling_joints']:
        return False
    a, b, c, d = (np.asarray(row[key], float) for row, key in (
        (source, 'domain_lower_rad'), (source, 'domain_upper_rad'),
        (target, 'domain_lower_rad'), (target, 'domain_upper_rad')))
    if a.ndim != 1 or any(v.shape != a.shape for v in (b, c, d)) or not np.isfinite([a,b,c,d]).all() or (a>b).any() or (c>d).any():
        raise ValueError('Invalid interval')
    return bool((a <= c).all() and (d <= b).all())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source-interfaces', 'target-interfaces', 'orbit-proof', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--proof', type=Path, action='append', required=True)
    args = p.parse_args()
    if args.output.exists(): p.error('Choose a new output')
    source = json.loads(args.source_interfaces.read_text()); target = json.loads(args.target_interfaces.read_text())
    if source['model_sources'] != target['model_sources']:
        p.error('Different CAD sources')
    proofs = {}; paths = [args.source_interfaces, args.target_interfaces, args.orbit_proof, *args.proof, Path(__file__)]
    for path in [*args.proof, args.orbit_proof]:
        proof = json.loads(path.read_text()); hashes = proof.get('source_sha256', proof.get('sources_sha256', {}))
        if hashes.get(str(args.source_interfaces.resolve())) != digest(args.source_interfaces) or proof['model_sources'] != source['model_sources']:
            p.error('Proof refers to different input')
        for row in proof.get('interfaces', [proof]):
            if row['proved']:
                proofs[tuple(row['pair'])] = dict(row, proof_file=str(path.resolve()), proof_sha256=digest(path))
    old = {tuple(row['pair']):row for row in source['interfaces']}; rows = []
    for row in target['interfaces']:
        if not row['controlling_joints'] or row['surface_intersection_samples']: continue
        pair = tuple(row['pair']); proof = proofs.get(pair)
        covered = bool(pair in old and proof and domain_contains(old[pair], row))
        rows.append(dict(pair=row['pair'], proved=covered, reason='SOURCE_PROOF_DOMAIN_CONTAINS_TARGET' if covered else 'NEW_DOMAIN_REQUIRES_PROOF',
                         proof_file=proof['proof_file'] if covered else None,
                         proof_sha256=proof['proof_sha256'] if covered else None,
                         lower_bound_m=proof['lower_bound_m'] if covered else 0.,
                         volume_separation_proved=False, physical_approval=False))
    hashes = {str(path.resolve()):digest(path) for path in paths}
    result = dict(scope='SOURCE_CAD_BOUNDARY_PROOF_DOMAIN_INCLUSION_ONLY', interfaces=rows,
                  source_sha256=hashes, model_sources=target['model_sources'], physical_approval=False)
    with args.output.open('x') as f: json.dump(result, f, indent=2, allow_nan=False); f.write('\n')
    print(json.dumps(dict(reused=sum(row['proved'] for row in rows), need_new_proof=sum(not row['proved'] for row in rows))))


if __name__ == '__main__': main()
