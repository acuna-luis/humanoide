#!/usr/bin/env python3
"""Compare archived upright ENTRY endpoints; no hardware or motion approval."""
import argparse
import json
import math
from pathlib import Path

import numpy as np

from prepare_vla_entry_bundle import ROOT, RobotGeometry, common, JOINT_ORDER, certify_pairs, digest
from general_home.geometry import solid_distance
from entry_local_displacement_bounds import LocalDisplacementBounds, SelectivePairDistances
from refine_entry_pair_distances import RefinedPairDistances
from evaluate_checkpoint_offline import write_json_exclusive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('survey', 'obstacles', 'output'):
        parser.add_argument('--' + key, required=True, type=Path)
    parser.add_argument('--error-degrees', required=True, type=float)
    args = parser.parse_args()
    if args.output.exists() or not math.isfinite(args.error_degrees) or not 0 <= args.error_degrees <= 5:
        parser.error('New output and finite error between 0 and 5 degrees required')
    survey = json.loads(args.survey.read_text())
    for name, checksum in {**survey['model_sources'], **survey['sources_sha256']}.items():
        if digest(Path(name)) != checksum:
            parser.error('Archived input changed: ' + name)
    if survey['sources_sha256'].get(str(args.obstacles.resolve())) != digest(args.obstacles):
        parser.error('Different archived scene')
    objects = []
    for name, values in json.loads(args.obstacles.read_text()).items():
        bounds = np.asarray(values, float)
        if bounds.shape != (2, 3) or not np.isfinite(bounds).all() or not (bounds[1] > bounds[0]).all():
            parser.error('Invalid scene bounds')
        objects.append(dict(id=name, type='box', size_m=(bounds[1]-bounds[0]).tolist(),
                            center_m=bounds.mean(axis=0).tolist(), rpy_rad=[0., 0., 0.]))
    package = ROOT / 'cruzr_s2_description_splint/cruzr_s2_description'
    base = RobotGeometry(package/'urdf/cruzr_s2_v1/cruzr_s2_v1.urdf', package,
                         dict(frame_id='base_link', complete=True, objects=objects))
    model = LocalDisplacementBounds(SelectivePairDistances(base, common, solid_distance), common, JOINT_ORDER)
    candidates = set(survey['upright_candidates_without_additional_or_scene_flags'])
    rows = []
    sources = [args.survey, args.obstacles, Path(__file__),
               *[ROOT/'scripts/vla'/name for name in ('prepare_vla_entry_bundle.py',
                 'entry_local_displacement_bounds.py', 'entry_interval_boxes.py',
                 'refine_entry_pair_distances.py')]]
    hashes = {str(p.resolve()): digest(p) for p in sources}
    for record in survey['rows']:
        if record['episode'] not in candidates:
            continue
        q = record['state']
        audit = certify_pairs(model, [q, q], seconds=20., max_depth=1,
                              joint_error_rad=math.radians(args.error_degrees))
        pending = [i for i, pair in enumerate(audit['pairs']) if pair['status'] == 'UNRESOLVED']
        if pending and not audit['timed_out']:
            refined = LocalDisplacementBounds(RefinedPairDistances(model.base, pending, solid_distance), common, JOINT_ORDER)
            audit = certify_pairs(refined, [q, q], seconds=20., max_depth=1,
                                  joint_error_rad=math.radians(args.error_degrees))
        rows.append(dict(episode=record['episode'], state=q, audit=audit, physical_approval=False))
        print(record['episode'], audit['counts'], flush=True)
    if not base.source_files_unchanged() or any(digest(Path(p)) != h for p, h in hashes.items()):
        raise RuntimeError('Sources changed during analysis')
    write_json_exclusive(args.output, dict(scope='ARCHIVED_ENDPOINT_ERROR_BOXES_ONLY',
        physical_approval=False, scene_complete=False, live_state_verified=False,
        error_degrees=args.error_degrees, rows=rows, sources_sha256=hashes,
        model_sources=base.manifest))


if __name__ == '__main__':
    main()
