#!/usr/bin/env python3
"""Generate a pinned local deposit package; never install or move the robot."""
import argparse
import json
from pathlib import Path

if __package__:
    from . import scenario1_table90 as table90
else:
    import scenario1_table90 as table90

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / 'vendor/ubtech/cruzr_s2/snapshot_20260916/motion'


def candidate():
    config = json.loads((ROOT / 'config/box_handling/scenario1_table90_candidate.json').read_text())
    if (config['reference_surface_height_m'], config['surface_height_m']) != (.45, .90):
        raise ValueError('This reviewed recipe supports only table45 to table90')
    bundle = table90.build_bundle(
        (SNAPSHOT / 'tasks/wrc_cruzr/put_cruzr_wrc_low.xml').read_text(),
        (SNAPSHOT / 'meta_clamp/wrc/put_cruzr_wrc_low.yaml').read_text(),
        (SNAPSHOT / 'meta_clamp/wrc/open_arm_cruzr.yaml').read_text())
    table90.validate_bundle(bundle)
    files = {Path(path).name: text for path, text in bundle['tasks'].items()}
    profile = json.loads((ROOT/'config/box_handling/scenario1_table90_geometry.json').read_text())
    report = dict(config, **table90.RECIPE, task_name=table90.TASK_NAME,
                  executable=table90.motion_qualified(profile),
                  physical_qualification=table90.PHYSICAL_QUALIFICATION,
                  source_hashes=table90.DEPENDENCIES,
                  preserved='Torso, X/Y, orientations, box_size, durations, force/collision controls, relative descent and opening')
    files['review.json'] = json.dumps(report, indent=2) + '\n'
    files['bundle.json'] = json.dumps(bundle, indent=2) + '\n'
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='New local directory; existing directories are rejected')
    args = parser.parse_args()
    files = candidate()
    if args.output:
        args.output.mkdir(parents=True, exist_ok=False)
        for name, content in files.items():
            (args.output / name).write_text(content)
    print(files['review.json'], end='')


if __name__ == '__main__':
    main()
