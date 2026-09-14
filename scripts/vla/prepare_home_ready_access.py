#!/usr/bin/env python3
"""Review measured stationary start -> READY, offline only; never authorizes motion."""
import argparse
import json
from pathlib import Path

import numpy as np

from review_entry_from_passive_state import (
    ROOT, JOINT_ORDER, RobotGeometry, common, digest, certify_pairs,
    solid_distance, decode_actuators, strict_json, LocalDisplacementBounds,
    SelectivePairDistances, DirectionalSceneBounds, SubdividedSceneBounds,
)
from prepare_entry360_stages import staged_path, stage_xml


def measured_start(trace, analysis):
    if analysis['input_sha256'] != digest(trace) or analysis['issues']:
        raise ValueError('Trace identity or analysis failed')
    positions = []
    for line in trace.read_text().splitlines():
        record = strict_json(line)
        if record.get('topic') != '/mc/actuator_state':
            continue
        sample = decode_actuators(record['message'])[1]
        if any(abs(v['velocity']) > .001 or v['error_code'] for v in sample.values()):
            raise ValueError('Moving or faulted input')
        positions.append([sample[n]['position'] for n in JOINT_ORDER])
    if len(positions) < 2 or not np.isfinite(positions).all():
        raise ValueError('Missing finite full-state evidence')
    if np.max(np.ptp(positions, axis=0)) > .002:
        raise ValueError('Measured position not stationary')
    return positions[-1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('reference', 'trace', 'trace-analysis', 'output-dir'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    if a.output_dir.exists():
        p.error('Choose a new evidence directory')
    ref = json.loads(a.reference.read_text())
    if (ref['joint_order'] != JOINT_ORDER or ref['candidate'] != 'episode_000410'
            or len(ref['scenarios']) != 1):
        p.error('Expected exact ENTRY410 reference')
    start = measured_start(a.trace, json.loads(a.trace_analysis.read_text()))
    scene = ref['scenarios'][0]
    ready = scene['routes']['access']['waypoints_20d_rad'][1]
    points, stages = staged_path(start, ready)
    package = ROOT/'cruzr_s2_description_splint/cruzr_s2_description'
    base = RobotGeometry(package/'urdf/cruzr_s2_v1/cruzr_s2_v1.urdf', package,
                         dict(frame_id='base_link', complete=True, objects=scene['scene_objects']))
    if base.manifest != ref['model_sources']:
        raise ValueError('Model changed')
    sources = [a.reference, a.trace, a.trace_analysis, Path(__file__),
               *sorted((ROOT/'scripts/vla').glob('*.py')),
               *sorted((ROOT/'scripts/teleoperation/general_home').glob('*.py'))]
    hashes = {str(f.resolve()): digest(f) for f in sources}
    local = LocalDisplacementBounds(SelectivePairDistances(base, common, solid_distance), common, JOINT_ORDER)
    model = SubdividedSceneBounds(DirectionalSceneBounds(local, common, JOINT_ORDER), 512)
    audit = certify_pairs(model, points, seconds=60, max_depth=10,
                          joint_error_rad=scene['routes']['access']['audit']['joint_error_scenario_rad'])
    result = dict(schema='cruzr-measured-start-ready-access-offline-v1',
                  physical_approval=False, robot_commands=0, installable=False,
                  start_is_measured_not_assumed_home=True, joint_order=JOINT_ORDER,
                  stages=stages, geometry_audit=audit, model_sources=base.manifest,
                  sources_sha256=hashes, nominal_seconds=sum(s['duration_seconds'] for s in stages),
                  runtime_mapping_verified=False, dynamic_limits_checked=False,
                  stopping_qualified=False, scene_registration_qualified=False,
                  reverse_scope='Only identical reversed segments from their exact endpoints')
    if not base.source_files_unchanged() or any(digest(Path(f)) != h for f, h in hashes.items()):
        raise RuntimeError('Sources changed during calculation')
    a.output_dir.mkdir(parents=True)
    for i, stage in enumerate(stages, 1):
        for direction in ('forward', 'reverse'):
            (a.output_dir/f'DRAFT_access_{i:02d}_{direction}.xml').write_text(
                stage_xml(stage, direction == 'reverse'))
    result['drafts_sha256'] = {f.name: digest(f) for f in a.output_dir.glob('*.xml')}
    (a.output_dir/'review.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(counts=audit['counts'], timed_out=audit['timed_out'],
                          nominal_seconds=result['nominal_seconds'], physical_approval=False)))


if __name__ == '__main__':
    main()
