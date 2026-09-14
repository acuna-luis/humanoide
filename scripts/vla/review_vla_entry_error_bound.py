#!/usr/bin/env python3
"""Recheck one archived ENTRY route with angular uncertainty; no robot access."""
import argparse
import json
import math
from pathlib import Path
import time

import numpy as np

from prepare_vla_entry_bundle import ROOT, RobotGeometry, digest, certify_pairs, JOINT_ORDER
from evaluate_checkpoint_offline import write_json_exclusive
from general_home.geometry import solid_distance
from refine_entry_pair_distances import RefinedPairDistances, refinement_indices
from entry_local_displacement_bounds import LocalDisplacementBounds, SelectivePairDistances
from prepare_vla_entry_bundle import common
from entry_directional_bounds import DirectionalSceneBounds
from entry_subdivided_scene_bounds import SubdividedSceneBounds


def scene_objects(obstacles, z_offset_mm=0.):
    """Translate the listed scene, preserving extents and original provenance."""
    if not math.isfinite(z_offset_mm):
        raise ValueError('Invalid scene offset')
    if not isinstance(obstacles, dict) or not obstacles:
        raise ValueError('Nonempty archived scene required')
    objects = []
    for name, values in obstacles.items():
        bounds = np.asarray(values, dtype=float)
        if bounds.shape != (2, 3) or not np.isfinite(bounds).all() or not (bounds[1] > bounds[0]).all():
            raise ValueError('Invalid obstacle bounds')
        center = bounds.mean(axis=0)
        center[2] += z_offset_mm / 1000.
        if not np.isfinite(center).all():
            raise ValueError('Invalid translated bounds')
        objects.append(dict(id=name, type='box', size_m=(bounds[1] - bounds[0]).tolist(),
                            center_m=center.tolist(), rpy_rad=[0., 0., 0.]))
    return objects


def validate_refinement_scene(prior, z_offset_mm):
    # Older reports used only the unmodified scene. Never reuse their selection
    # of unresolved pairs as if it belonged to a translated scenario.
    if prior.get('scene_z_offset_mm', 0.) != z_offset_mm:
        raise ValueError('Refinement scene translation mismatch')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('access-review', 'selection', 'obstacles', 'output'):
        parser.add_argument('--' + key, type=Path, required=True)
    parser.add_argument('--route', default='via_ready')
    parser.add_argument('--error-degrees', type=float, default=5.)
    parser.add_argument('--budget-seconds', type=float, default=90.)
    parser.add_argument('--subdivision-depth', type=int, default=16,
                        help='Numerical budget only; exhausted resolution remains UNRESOLVED')
    parser.add_argument('--refine-unresolved-from', type=Path,
                        help='Completed same-scenario report; refine solid distances, retain ALL pairs')
    parser.add_argument('--local-radius-bounds', action='store_true',
                        help='Offline finite-rotation enclosure at each interval centre')
    parser.add_argument('--scene-z-offset-mm', type=float, default=0.,
                        help='Hypothetical vertical translation of ALL listed obstacles; no physical calibration')
    parser.add_argument('--directional-bounds', action='store_true',
                        help='Offline scene support bounds with global Hessian remainder; requires local bounds')
    parser.add_argument('--uncertainty-partition-nodes', type=int, default=0,
                        help='Optional finite error-box subdivision, no relaxation; requires directional bounds')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output must be new')
    if args.directional_bounds and not args.local_radius_bounds:
        parser.error('Directional scene bounds require --local-radius-bounds')
    if not 0 <= args.uncertainty_partition_nodes <= 4096:
        parser.error('Invalid uncertainty partition budget')
    if args.uncertainty_partition_nodes and not args.directional_bounds:
        parser.error('Uncertainty subdivision requires directional bounds')
    if not math.isfinite(args.error_degrees) or not 0 <= args.error_degrees <= 180:
        parser.error('Invalid angular error scenario')
    report = json.loads(args.access_review.read_text())
    selection = json.loads(args.selection.read_text())
    if report['selected_candidate'] != selection['selected_candidate']:
        parser.error('Candidate identity mismatch')
    if selection['sources_sha256'].get(str(args.obstacles.resolve())) != digest(args.obstacles):
        parser.error('Scene differs from the reviewed scene')
    if args.route not in report['routes']:
        parser.error('Unknown archived route')
    for path, expected in report['model_sources'].items():
        if digest(Path(path)) != expected:
            parser.error('Model differs from reviewed model: ' + path)
    objects = scene_objects(json.loads(args.obstacles.read_text()), args.scene_z_offset_mm)
    package = ROOT / 'cruzr_s2_description_splint/cruzr_s2_description'
    geometry = RobotGeometry(package/'urdf/cruzr_s2_v1/cruzr_s2_v1.urdf', package,
                             dict(frame_id='base_link', complete=True, objects=objects))
    route = report['routes'][args.route]
    if route['joint_order'] != JOINT_ORDER:
        parser.error('Canonical joint order changed')
    if geometry.labels != [row['pair'] for row in route['audit']['pairs']]:
        parser.error('Pair set differs from previous review')
    if args.local_radius_bounds:
        geometry = SelectivePairDistances(geometry, common, solid_distance)
    sources = [args.access_review, args.selection, args.obstacles, Path(__file__),
               ROOT/'scripts/vla/prepare_vla_entry_bundle.py',
               ROOT/'scripts/vla/refine_entry_pair_distances.py',
               ROOT/'scripts/vla/entry_local_displacement_bounds.py',
               ROOT/'scripts/vla/entry_interval_boxes.py',
               ROOT/'scripts/vla/entry_directional_bounds.py',
               ROOT/'scripts/vla/entry_subdivided_scene_bounds.py',
               ROOT/'scripts/teleoperation/general_home/geometry.py']
    if args.refine_unresolved_from:
        prior = json.loads(args.refine_unresolved_from.read_text())
        validate_refinement_scene(prior, args.scene_z_offset_mm)
        indices = refinement_indices(prior, geometry.labels,
            candidate=report['selected_candidate'], route=args.route,
            error_rad=math.radians(args.error_degrees), model_sources=geometry.manifest,
            sources={str(p.resolve()):digest(p) for p in
                     (args.access_review, args.selection, args.obstacles)})
        geometry = RefinedPairDistances(geometry, indices, solid_distance)
        sources.append(args.refine_unresolved_from)
    if args.local_radius_bounds:
        geometry = LocalDisplacementBounds(geometry, common, JOINT_ORDER)
    if args.directional_bounds:
        geometry = DirectionalSceneBounds(geometry, common, JOINT_ORDER)
    if args.uncertainty_partition_nodes:
        geometry = SubdividedSceneBounds(geometry, args.uncertainty_partition_nodes)
    source_hashes = {str(p.resolve()):digest(p) for p in sources}
    started = time.monotonic()
    audit = certify_pairs(geometry, route['waypoints_20d_rad'],
                          seconds=args.budget_seconds, max_depth=args.subdivision_depth,
                          joint_error_rad=math.radians(args.error_degrees))
    result = dict(scope='ARCHIVED_AFFINE_ROUTE_ERROR_SCENARIO_NOT_EXECUTION',
                  physical_approval=False, scene_complete=False, live_state_verified=False,
                  route=args.route, candidate=report['selected_candidate'],
                  elapsed_analysis_seconds=time.monotonic()-started, audit=audit,
                  scene_z_offset_mm=args.scene_z_offset_mm,
                  scene_hypothetical=args.scene_z_offset_mm != 0.,
                  evaluated_scene_objects=objects,
                  directional_bounds_used=args.directional_bounds,
                  uncertainty_partition_nodes=args.uncertainty_partition_nodes,
                  sources_sha256=source_hashes, model_sources=geometry.manifest)
    if args.uncertainty_partition_nodes:
        result['uncertainty_partition'] = dict(queries=geometry.partition_queries,
            proofs=geometry.partition_proofs, incomplete=geometry.partition_incomplete)
    if args.refine_unresolved_from:
        result['distance_refinement'] = geometry.summary()
    if not geometry.source_files_unchanged() or any(digest(Path(p)) != h for p,h in source_hashes.items()):
        raise RuntimeError('Model or input/source changed during analysis')
    write_json_exclusive(args.output, result)
    print(json.dumps({k: result[k] for k in ('candidate', 'route', 'elapsed_analysis_seconds')}))
    print(json.dumps(audit['counts']), 'timed_out', audit['timed_out'])


if __name__ == '__main__':
    main()
