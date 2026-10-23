#!/usr/bin/env python3
"""Build a self-contained resident executor directory. No robot/network access."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def build(output):
    output = Path(output).resolve()
    if output == ROOT or ROOT in output.parents:
        raise ValueError('Output must be outside the repository')
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    tracked = subprocess.check_output(['git', '-C', str(ROOT), 'ls-files'], text=True).splitlines()
    paths = [p for p in tracked if (p.startswith('scripts/box_handling/') and
             Path(p).suffix in ('.py', '.json') and not Path(p).name.startswith('test_')) or
             (p.startswith('vendor/ubtech/cruzr_s2/snapshot_20260916/motion/') and Path(p).suffix in ('.xml', '.yaml'))]
    paths += ['scripts/optimistic_scenario1.sh', 'scripts/lib/cruzr_home_posture_gate.py',
              'scripts/box_handling/scenario1_robot_home.py']
    paths += [str(p.relative_to(ROOT)) for p in (ROOT/'scripts/web/robot').iterdir() if p.suffix in ('.py','.html','.js','.css')]
    for relative in sorted(set(paths)):
        source = ROOT/relative
        if source.is_symlink():
            raise ValueError('Symlink source refused: '+relative)
        target = output/'app'/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    # Keep reviewed pins, never ship the historical shell's embedded SSH secrets.
    pin_text = (ROOT/'scripts/cruzr_blue_workbin_cycle.sh').read_text()
    pins = re.findall(r'^readonly \w+_SHA="[a-f0-9]{64}"$', pin_text, re.M)
    if len(pins) < 7:
        raise ValueError('Missing reviewed HOME pins')
    (output/'app/scripts/cruzr_blue_workbin_cycle.sh').write_text('\n'.join(pins)+'\n')
    shutil.copyfile(ROOT/'scripts/web/install_robot_scenario1.py', output/'install.py')
    shutil.copyfile(ROOT/'docs/box_handling/OPTIMISTIC_SCENARIO1.md', output/'MANUAL_ES.md')
    files = {str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in output.rglob('*') if p.is_file()}
    (output/'manifest.json').write_text(json.dumps({'version':1, 'git_commit':subprocess.check_output(
        ['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(), 'files':files,
        'physical_validation':'pending', 'includes_working_tree_bytes':True}, indent=2)+'\n')
    print(output)
    return output


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    build(p.parse_args().output)
