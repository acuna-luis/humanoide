#!/usr/bin/env python3
"""Offline self-proximity comparison; all pairs retained, no execution approval."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'teleoperation'))
from general_home.geometry import RobotGeometry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--entries-json', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): parser.error('Output already exists')
    entries = json.loads(args.entries_json.read_text())
    root = Path(__file__).resolve().parents[2]
    package = root / 'cruzr_s2_description_splint/cruzr_s2_description'
    model = RobotGeometry(package/'urdf/cruzr_s2_v1/cruzr_s2_v1.urdf', package,
                          dict(frame_id='base_link', complete=True, objects=[]))
    states = {'HOME_REFERENCE': np.zeros(20)}
    states.update({key: np.asarray(entries[key]['first_state'])
                   for key in ('episode_000040','episode_000430','episode_000438')})
    result = dict(scope='SELF_GEOMETRY_ENDPOINTS_ONLY_NO_ENVIRONMENT_OR_TRAJECTORY',
                  physical_approval=False, margin_m=0.002, diagnostic_model=model.diagnostics,
                  sources=model.manifest, endpoints={})
    baseline = set()
    for name, q in states.items():
        distances = model.distances(q)
        # Match the existing planner gate, including its numerical tolerance.
        indices = np.flatnonzero(distances <= 0.002 + 1e-9)
        if name == 'HOME_REFERENCE': baseline = set(map(int, indices))
        flags = [dict(pair=model.labels[i], distance_m=float(distances[i]),
                      also_flagged_in_HOME=int(i) in baseline,
                      details=model.pair_details[i], exempted=False) for i in indices]
        result['endpoints'][name] = dict(flagged_pairs=len(flags),
            additional_flags_vs_HOME=sum(not flag['also_flagged_in_HOME'] for flag in flags),
            flags=flags, nominal_endpoint_qualified=not flags)
        print(name, 'flags', len(flags), 'additional', result['endpoints'][name]['additional_flags_vs_HOME'], flush=True)
    assert model.source_files_unchanged()
    args.output.write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    main()
