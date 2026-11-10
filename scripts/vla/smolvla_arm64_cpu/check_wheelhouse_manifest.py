#!/usr/bin/env python3
"""Fail-closed coverage check for a candidate offline wheelhouse, no installs."""
import hashlib
from pathlib import Path
import re
import sys

PINNED = {
    'torch-2.7.1-cp312-cp312-manylinux_2_28_aarch64.whl':
        '27ea1e518df4c9de73af7e8a720770f3628e7f667280bce2be7a16292697e3fa',
    'torchvision-0.22.1-cp312-cp312-manylinux_2_28_aarch64.whl':
        '964414eef19459d55a10e886e2fca50677550e243586d1678f65e3f6f6bac47a',
    'lerobot-0.5.1-py3-none-any.whl':
        'bbd11021023fde0947b6d1ff1c52fe91c86a28ab09a96359892f3ef7e8866862',
}


def check(root):
    root = Path(root)
    manifest = root / 'SHA256SUMS'
    if root.is_symlink() or not root.is_dir() or manifest.is_symlink() or not manifest.is_file():
        raise ValueError('missing directory or regular checksum manifest')
    entries = {}
    for line in manifest.read_text(encoding='ascii').splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9_.+-]+\.whl)', line)
        if not match or match[2] in entries:
            raise ValueError('malformed or duplicate manifest record')
        entries[match[2]] = match[1]
    actual = {p.name for p in root.iterdir() if p.name != 'SHA256SUMS'}
    if not entries or actual != set(entries) or not set(PINNED).issubset(entries):
        raise ValueError('manifest must cover all wheels and required pins exactly')
    for name, expected in entries.items():
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('non-regular or symlink artifact: ' + name)
        if name in PINNED and expected != PINNED[name]:
            raise ValueError('required wheel hash differs: ' + name)
        digest = hashlib.sha256()
        with path.open('rb') as f:
            for block in iter(lambda: f.read(1024 * 1024), b''):
                digest.update(block)
        if digest.hexdigest() != expected:
            raise ValueError('wheel digest mismatch: ' + name)
    return len(entries)


if __name__ == '__main__':
    try:
        if len(sys.argv) != 2:
            raise ValueError('usage: check_wheelhouse_manifest.py WHEELHOUSE')
        print(f'{check(sys.argv[1])} wheels have exact manifest coverage and hashes')
    except (OSError, ValueError, UnicodeError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        sys.exit(1)
