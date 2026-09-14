#!/usr/bin/env python3
"""Recompute an archived finite-error witness; never controls the robot."""
import argparse
import json
import math
from pathlib import Path

import fcl
import numpy as np

from prepare_vla_entry_bundle import ROOT, RobotGeometry, JOINT_ORDER, common, digest
from review_vla_entry_error_bound import scene_objects
from general_home.geometry import solid_distance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('witness', 'review', 'access-review', 'obstacles', 'output'):
        parser.add_argument('--'+key, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): parser.error('Output must be new')
    witness = json.loads(args.witness.read_text())
    review = json.loads(args.review.read_text())
    if review.get('scene_z_offset_mm', 0.) != 0.:
        parser.error('This verifier requires the unchanged archived scene')
    sources = {str(p.resolve()): digest(p) for p in
               (args.witness, args.review, args.access_review, args.obstacles, Path(__file__),
                ROOT/'scripts/teleoperation/general_home/geometry.py')}
    if review['sources_sha256'][str(args.obstacles.resolve())] != digest(args.obstacles):
        parser.error('Scene differs from reviewed scene')
    if review['sources_sha256'][str(args.access_review.resolve())] != digest(args.access_review):
        parser.error('Access route differs from reviewed route')
    package = ROOT/'cruzr_s2_description_splint/cruzr_s2_description'
    model = RobotGeometry(package/'urdf/cruzr_s2_v1/cruzr_s2_v1.urdf', package,
                          dict(frame_id='base_link', complete=True,
                               objects=scene_objects(json.loads(args.obstacles.read_text()))))
    if model.manifest != review['model_sources']: parser.error('Model differs')
    route = json.loads(args.access_review.read_text())['routes'][review['route']]
    if route['joint_order'] != JOINT_ORDER: parser.error('Joint order differs')
    points = np.asarray(route['waypoints_20d_rad'])
    segment, fraction = witness['segment'], witness['fraction']
    if not 0 <= segment < len(points)-1 or not 0 <= fraction <= 1: parser.error('Invalid location')
    nominal = (1-fraction)*points[segment]+fraction*points[segment+1]
    q = np.asarray(witness['q'])
    if q.shape != (20,) or not np.isfinite(q).all(): parser.error('Invalid posture')
    if not np.allclose(nominal, witness['nominal_q'], atol=1e-12, rtol=0): parser.error('Nominal differs')
    if (q < model.lower).any() or (q > model.upper).any(): parser.error('Outside joint limits')
    maximum_error = float(np.max(np.abs(q-nominal)))
    if maximum_error > review['audit']['joint_error_scenario_rad']+1e-12: parser.error('Outside reviewed error box')
    poses = common.fk.forward_kinematics(model.joints, dict(model.auxiliary, **dict(zip(JOINT_ORDER, q))))
    indices = model.pairs[model.labels.index(witness['pair'])]
    for index in indices:
        if index < model.robot_count: model.shapes[index].place(poses[model.shapes[index].link])
    a, b = [model.shapes[index] for index in indices]
    contacts = int(fcl.collide(a.obj, b.obj, fcl.CollisionRequest(), fcl.CollisionResult()))
    raw = float(fcl.distance(a.obj, b.obj, fcl.DistanceRequest(), fcl.DistanceResult()))
    result = dict(scope='RECOMPUTED_MODEL_WITNESS_NOT_PHYSICAL_CONTACT', physical_approval=False,
                  pair=witness['pair'], fraction=fraction, segment=segment,
                  maximum_error_degrees=math.degrees(maximum_error), joint_limits_pass=True,
                  fcl_contacts=contacts, fcl_raw_distance_m=raw,
                  geometry_errors_m=[a.geometry_error_m, b.geometry_error_m],
                  conservative_solid_distance_m=solid_distance(a, b),
                  model_sources=model.manifest, sources_sha256=sources)
    if not model.source_files_unchanged() or any(digest(Path(p)) != h for p,h in sources.items()):
        raise RuntimeError('Sources changed during verification')
    with args.output.open('x') as stream: json.dump(result, stream, indent=2); stream.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('sources_sha256', 'model_sources')}))


if __name__ == '__main__': main()
