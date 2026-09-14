#!/usr/bin/env python3
"""Search exact archived scene/route for a counterexample; strictly offline."""
import argparse
import json
import math
from pathlib import Path

import fcl
import numpy as np
from scipy.optimize import differential_evolution

from prepare_vla_entry_bundle import ROOT, RobotGeometry, JOINT_ORDER, common, digest
from general_home.geometry import solid_distance
from entry_local_displacement_bounds import LocalDisplacementBounds, SelectivePairDistances


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pair', nargs=2, required=True)
    parser.add_argument('--route', choices=('access', 'empty_recovery'), default='access')
    parser.add_argument('--segment', type=int, default=1)
    parser.add_argument('--iterations', type=int, default=80)
    parser.add_argument('--seed', type=int, default=1450)
    parser.add_argument('--fraction-range', type=float, nargs=2, default=[0., 1.])
    parser.add_argument('--verify-witness', type=Path)
    args = parser.parse_args()
    if args.output.exists(): parser.error('Output must be new')
    review = json.loads(args.review.read_text())
    if review['joint_order'] != JOINT_ORDER or len(review['scenarios']) != 1:
        parser.error('Requires one archived scenario and canonical joint order')
    scenario = review['scenarios'][0]
    route = scenario['routes'][args.route]
    path = np.asarray(route['waypoints_20d_rad'], float)
    error = float(route['audit']['joint_error_scenario_rad'])
    if (path.ndim != 2 or path.shape[1] != 20 or not np.isfinite(path).all()
            or not 0 <= args.segment < len(path)-1 or not 0 < error <= math.radians(5)
            or not 1 <= args.iterations <= 500
            or not 0 <= args.fraction_range[0] <= args.fraction_range[1] <= 1):
        parser.error('Invalid route/search domain')
    sources = [args.review, Path(__file__), ROOT/'scripts/vla/prepare_vla_entry_bundle.py',
               ROOT/'scripts/vla/entry_local_displacement_bounds.py',
               ROOT/'scripts/teleoperation/general_home/geometry.py',
               Path(common.__file__), Path(common.fk.__file__)]
    if args.verify_witness: sources.append(args.verify_witness)
    hashes = {str(p.resolve()): digest(p) for p in sources}
    package = ROOT/'cruzr_s2_description_splint/cruzr_s2_description'
    base = RobotGeometry(package/'urdf/cruzr_s2_v1/cruzr_s2_v1.urdf', package,
                         dict(frame_id='base_link', complete=True, objects=scenario['scene_objects']))
    if base.manifest != review['model_sources']: parser.error('Model sources differ')
    local = LocalDisplacementBounds(SelectivePairDistances(base, common, solid_distance), common, JOINT_ORDER)
    index = base.labels.index(args.pair)
    a, b = base.pairs[index]
    active = np.flatnonzero(local.masks[a] | local.masks[b])

    def place(q):
        poses = common.fk.forward_kinematics(base.joints, dict(base.auxiliary, **dict(zip(JOINT_ORDER, q))))
        for i in (a, b):
            if i < base.robot_count: base.shapes[i].place(poses[base.shapes[i].link])

    def posture(x):
        nominal = (1-x[0])*path[args.segment]+x[0]*path[args.segment+1]
        q = nominal.copy(); q[active] += x[1:]
        return nominal, q

    def objective(x):
        _, q = posture(x)
        if (q < base.lower).any() or (q > base.upper).any(): return 1000.
        place(q)
        return solid_distance(base.shapes[a], base.shapes[b])

    if args.verify_witness:
        witness = json.loads(args.verify_witness.read_text())
        if (witness['pair'] != args.pair or witness['route'] != args.route
                or witness['segment'] != args.segment
                or witness['sources_sha256'][str(args.review.resolve())] != digest(args.review)):
            parser.error('Witness is for a different query')
        fraction = float(witness['fraction']); q = np.asarray(witness['q'], float)
        if not 0 <= fraction <= 1 or q.shape != (20,) or not np.isfinite(q).all(): parser.error('Invalid witness')
        nominal = (1-fraction)*path[args.segment]+fraction*path[args.segment+1]
        if not np.allclose(nominal, witness['nominal_q'], atol=1e-12, rtol=0): parser.error('Nominal differs')
        queries = 0
    else:
        result = differential_evolution(objective, [tuple(args.fraction_range)]+[(-error, error)]*len(active),
            seed=args.seed, popsize=8, maxiter=args.iterations, polish=True, tol=1e-7)
        fraction = float(result.x[0]); nominal, q = posture(result.x); queries = int(result.nfev)
    maximum_error = float(np.max(np.abs(q-nominal)))
    if (q < base.lower).any() or (q > base.upper).any() or maximum_error > error+1e-12:
        parser.error('No valid in-domain witness found')
    place(q)
    sa, sb = base.shapes[a], base.shapes[b]
    distance = float(solid_distance(sa, sb))
    raw = float(fcl.distance(sa.obj, sb.obj, fcl.DistanceRequest(), fcl.DistanceResult()))
    contacts = int(fcl.collide(sa.obj, sb.obj, fcl.CollisionRequest(), fcl.CollisionResult()))
    output = dict(scope='RECOMPUTED_MODEL_WITNESS' if args.verify_witness else 'NUMERICAL_MODEL_WITNESS_SEARCH',
        physical_approval=False, physical_contact_observed=False, global_minimum_proved=False,
        pair=args.pair, route=args.route, segment=args.segment, fraction=fraction,
        nominal_q=nominal.tolist(), q=q.tolist(), delta_degrees=np.degrees(q-nominal).tolist(),
        maximum_error_degrees=math.degrees(maximum_error), joint_limits_pass=True,
        conservative_solid_distance_m=distance, fcl_raw_distance_m=raw, fcl_contacts=contacts,
        geometry_errors_m=[sa.geometry_error_m, sb.geometry_error_m],
        minimum_clearance_counterexample=bool(distance <= .002), queries=queries,
        seed=args.seed, iterations=args.iterations, fraction_range=args.fraction_range,
        model_sources=base.manifest, sources_sha256=hashes)
    if not base.source_files_unchanged() or any(digest(Path(p)) != h for p,h in hashes.items()):
        raise RuntimeError('Sources changed during query')
    with args.output.open('x') as stream: json.dump(output, stream, indent=2); stream.write('\n')
    print(json.dumps({k:v for k,v in output.items() if k not in ('q','nominal_q','delta_degrees','model_sources','sources_sha256')}), flush=True)


if __name__ == '__main__': main()
