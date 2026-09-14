#!/usr/bin/env python3
"""Screen every archived task-0 endpoint against the listed scene, offline only.

No exemptions are applied. A comparison to HOME only identifies which pairs
need new investigation; a matching set of flags is not an approval.
"""
import argparse
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/teleoperation'))
from general_home.geometry import RobotGeometry, digest
import rank_vla_entry_postures as ranking
from evaluate_checkpoint_offline import write_json_exclusive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('dataset-report', 'obstacles', 'output'):
        parser.add_argument('--' + key, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output already exists')
    contract_path = ROOT / 'scripts/vla/runtime/cruzr_s2_vla_task0_entry_e6_1a.json'
    contract = json.loads(contract_path.read_text())
    if digest(args.dataset_report) != contract['candidate']['dataset_entry_report_sha256']:
        parser.error('Dataset archive hash changed')
    records = ranking.validate_records(json.loads(args.dataset_report.read_text()), contract)
    obstacles = json.loads(args.obstacles.read_text())
    if not isinstance(obstacles, dict) or not obstacles:
        parser.error('Nonempty archived obstacle set required')
    objects = []
    for name, raw in obstacles.items():
        bounds = np.asarray(raw, dtype=float)
        if bounds.shape != (2, 3) or not np.isfinite(bounds).all() or not (bounds[1] > bounds[0]).all():
            parser.error('Invalid bounds: ' + name)
        objects.append(dict(id=name, type='box', size_m=(bounds[1]-bounds[0]).tolist(),
                            center_m=bounds.mean(axis=0).tolist(), rpy_rad=[0., 0., 0.]))
    package = ROOT / 'cruzr_s2_description_splint/cruzr_s2_description'
    urdf = package / 'urdf/cruzr_s2_v1/cruzr_s2_v1.urdf'
    # Complete listed mathematical object set, deliberately partial real scene.
    model = RobotGeometry(urdf, package, dict(frame_id='base_link', complete=True, objects=objects))
    baseline = model.distances(np.zeros(20))
    baseline_flags = set(np.flatnonzero(baseline <= .002 + 1e-9))
    rows = []
    for record in records:
        if record['task'] != 0:
            continue
        q = np.asarray(record['state'])
        tilt, poses = ranking.torso_metrics(model.joints, dict(zip(contract['joint_order'], q)))
        row = dict(episode=record['episode'], state=record['state'], torso_tilt_deg=tilt,
                   sensor_origins_base_m={side: poses[f'{side}_sixforce_link'][:3, 3].tolist() for side in ('L', 'R')},
                   physical_approval=False)
        if (q < model.lower).any() or (q > model.upper).any():
            row.update(status='OUTSIDE_JOINT_LIMITS', endpoint_qualified=False)
            rows.append(row)
            continue
        distances = model.distances(q)
        flags = np.flatnonzero(distances <= .002 + 1e-9)
        row.update(status='ENDPOINT_REVIEW_ONLY', endpoint_qualified=not len(flags),
            flagged_pairs=len(flags),
            scene_flagged_pairs=sum(any(label.startswith('scene:') for label in model.labels[i]) for i in flags),
            additional_flags_vs_HOME=sum(i not in baseline_flags for i in flags),
            flags=[dict(pair=model.labels[i], lower_bound_m=float(distances[i]),
                        also_flagged_in_HOME=i in baseline_flags, exempted=False) for i in flags])
        rows.append(row)
        if len(rows) % 25 == 0:
            print('ENDPOINTS_CHECKED', len(rows), flush=True)
    candidates = [r for r in rows if r.get('scene_flagged_pairs') == 0
                  and r.get('additional_flags_vs_HOME') == 0 and r['torso_tilt_deg'] <= 5]
    result = dict(scope='ALL_TASK0_ENDPOINTS_ARCHIVED_PARTIAL_SCENE_ONLY', physical_approval=False,
                  scene_complete=False, live_state_verified=False, rows=rows,
                  upright_candidates_without_additional_or_scene_flags=[r['episode'] for r in candidates],
                  baseline_flags=[model.labels[i] for i in sorted(baseline_flags)],
                  model_sources=model.manifest,
                  sources_sha256={str(p.resolve()): digest(p) for p in (args.dataset_report, args.obstacles, contract_path, Path(__file__))})
    if not model.source_files_unchanged():
        raise RuntimeError('Model sources changed')
    write_json_exclusive(args.output, result)
    print('ENDPOINTS_COMPLETE', len(rows), 'CANDIDATES', len(candidates), flush=True)


if __name__ == '__main__':
    main()
