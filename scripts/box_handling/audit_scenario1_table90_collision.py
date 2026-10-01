#!/usr/bin/env python3
"""Sample installed CAD self distances for conditional IK states; no motion.

This audit cannot certify table, box, tools or a continuous Motion trajectory.
Every moving CAD pair is retained, including pairs overlapping at HOME.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts/teleoperation'))
from general_home.geometry import RobotGeometry
from cruzr_pico_to_home_owner_gate import JOINT_ORDER


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--urdf', type=Path, required=True)
    parser.add_argument('--package-root', type=Path, required=True)
    parser.add_argument('--ik-report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output must be new')
    # Complete describes only the empty external-object list of this self-only
    # calculation, never the physical scene, which is explicitly not reviewed.
    model = RobotGeometry(args.urdf, args.package_root,
                          {'frame_id': 'base_link', 'objects': [], 'complete': True})
    source = json.loads(args.ik_report.read_text())
    distances = model.distances(np.zeros(20))
    home_overlaps = [model.labels[i] for i, d in enumerate(distances) if d <= 0]
    rows = []
    for row in source['rows']:
        q = np.array([row['joint_state'].get(name, (source.get('initial_state') or {}).get(name, 0.))
                      for name in JOINT_ORDER])
        distances = model.distances(q)
        index = int(np.argmin(distances))
        rows.append(dict(configuration=row['configuration'], timestamp_s=row['timestamp_s'],
                         minimum_distance_m=float(distances[index]), closest_pair=model.labels[index],
                         overlapping_pairs=[model.labels[i] for i, d in enumerate(distances) if d <= 0]))
    report = dict(scope='SAMPLED_INSTALLED_CAD_SELF_DISTANCES_ONLY', physical_approval=False,
                  continuous_certificate=False, external_scene_reviewed=False,
                  held_box_reviewed=False, native_solver_path_reproduced=False,
                  ik_report_sha256=hashlib.sha256(args.ik_report.read_bytes()).hexdigest(),
                  geometry_sources_sha256=model.manifest, diagnostics=model.diagnostics,
                  home_overlapping_pairs=home_overlaps, rows=rows)
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2); stream.write('\n')
    for configuration in ('vendor_reference', 'table90'):
        subset = [r for r in rows if r['configuration'] == configuration]
        print(configuration, 'samples', len(subset), 'overlap_samples', sum(bool(r['overlapping_pairs']) for r in subset),
              'minimum', min(r['minimum_distance_m'] for r in subset))


if __name__ == '__main__':
    main()
