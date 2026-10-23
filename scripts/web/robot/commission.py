#!/usr/bin/env python3
"""File-only native package preparation. No reload, mode change or movement."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'scripts/box_handling'))
import scenario1_height_deposit as height
import scenario1_table74_trial_install as installer
from front_box_integration import SNAPSHOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--height', choices=('74', '90'), required=True)
    parser.add_argument('--install-files', action='store_true')
    args = parser.parse_args()
    bundle = height.build_bundle(height.RECIPES[float(args.height)],
        *((SNAPSHOT/p).read_text() for p in ('tasks/wrc_cruzr/put_cruzr_wrc_low.xml',
           'meta_clamp/wrc/put_cruzr_wrc_low.yaml', 'meta_clamp/wrc/open_arm_cruzr.yaml')))
    print(json.dumps(installer.operate(bundle, operation='install' if args.install_files else 'check'), indent=2))


if __name__ == '__main__':
    main()
