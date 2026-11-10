#!/usr/bin/env python3
"""Prepare pinned building blocks for the *experimental* ARM64 CPU runtime.

This is NOT a complete wheelhouse and never installs anything. It downloads
five audited wheels and three source distributions; the latter require
building wheels, and many transitive dependencies remain to be resolved on
the target architecture. The report does not qualify robot motion or runtime.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import urllib.request

ARTIFACTS = {
    'torch-2.7.1-cp312-cp312-manylinux_2_28_aarch64.whl':
        ('torch', '2.7.1', '27ea1e518df4c9de73af7e8a720770f3628e7f667280bce2be7a16292697e3fa'),
    'torchvision-0.22.1-cp312-cp312-manylinux_2_28_aarch64.whl':
        ('torchvision', '0.22.1', '964414eef19459d55a10e886e2fca50677550e243586d1678f65e3f6f6bac47a'),
    'lerobot-0.5.1-py3-none-any.whl':
        ('lerobot', '0.5.1', 'bbd11021023fde0947b6d1ff1c52fe91c86a28ab09a96359892f3ef7e8866862'),
    'docopt-0.6.2.tar.gz':
        ('docopt', '0.6.2', '49b3a825280bd66b3aa83585ef59c4a8c82f2c8a522dbe754a8bc8d08c85c491'),
    'evdev-1.9.2.tar.gz':
        ('evdev', '1.9.2', '5d3278892ce1f92a74d6bf888cc8525d9f68af85dbe336c95d1c87fb8f423069'),
    'evdev-2.0.0.tar.gz':
        ('evdev', '2.0.0', '442fb3f4c8dfc9e61e901133c356220c02d663eca8f34722e0cecdd637eba504'),
    'setuptools-78.1.0-py3-none-any.whl':
        ('setuptools', '78.1.0', '3e386e96793c8702ae83d17b853fb93d3e09ef82ec62722e61da5cd22376dcd8'),
    'wheel-0.45.1-py3-none-any.whl':
        ('wheel', '0.45.1', '708e7481cc80179af0e556bbf0cc00b8444c7321e2700b8d8580231d13017248'),
}
CHUNK = 1024 * 1024
MAX_FILE = 150 * CHUNK


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(CHUNK), b''):
            h.update(b)
    return h.hexdigest()


def check(directory):
    directory = Path(directory)
    errors = []
    for name, (_, _, expected) in ARTIFACTS.items():
        path = directory / name
        if path.is_symlink() or not path.is_file():
            errors.append(name + ': missing or symlink')
        elif digest(path) != expected:
            errors.append(name + ': sha256 mismatch')
    return errors


def download(directory):
    directory = Path(directory)
    # Refuse reuse or replacement, including a dangling symlink.
    directory.mkdir(mode=0o700)
    for name, (project, version, expected) in ARTIFACTS.items():
        request = urllib.request.Request(f'https://pypi.org/pypi/{project}/{version}/json',
                                         headers={'User-Agent': 'cruzr-arm64-cpu-prep/1'})
        with urllib.request.urlopen(request, timeout=30) as response:
            metadata = json.load(response)
        matches = [v for v in metadata.get('urls', []) if v.get('filename') == name]
        if len(matches) != 1 or matches[0].get('digests', {}).get('sha256') != expected:
            raise ValueError('unexpected PyPI metadata for ' + name)
        url = matches[0].get('url', '')
        if not url.startswith('https://files.pythonhosted.org/'):
            raise ValueError('unexpected artifact host')
        if type(matches[0].get('size')) is not int or not 0 < matches[0]['size'] <= MAX_FILE:
            raise ValueError('unexpected artifact size')
        path = directory / name
        h = hashlib.sha256()
        count = 0
        with urllib.request.urlopen(url, timeout=60) as response, path.open('xb') as output:
            while True:
                block = response.read(CHUNK)
                if not block:
                    break
                count += len(block)
                if count > MAX_FILE:
                    raise ValueError('artifact too large')
                output.write(block)
                h.update(block)
        if h.hexdigest() != expected or count != matches[0]['size']:
            raise ValueError('download checksum or size mismatch: ' + name)
    if check(directory):
        raise ValueError('post-download audit failed')
    report = {'schema': 'cruzr_smolvla_arm64_cpu_partial_wheelhouse_v1',
              'complete_wheelhouse': False, 'runtime_tested': False,
              'physical_control_qualified': False,
              'artifacts': {name: meta[2] for name, meta in ARTIFACTS.items()},
              'pending': ['Build docopt and evdev wheels for CPython 3.12 ARM64',
                          'Resolve and pin every transitive ARM64 dependency',
                          'Verify offline installation and model inference on compatible ARM64',
                          'Assess CPU time, memory and impact before robot deployment']}
    with (directory / 'report.json').open('x', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
        f.write('\n')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument('--download', action='store_true', help='create new directory and download pinned artifacts')
    actions.add_argument('--check', action='store_true', help='verify downloaded files without network or writes')
    parser.add_argument('--output', type=Path, required=True, help='new directory for download, existing for check')
    args = parser.parse_args(argv)
    try:
        if args.download:
            download(args.output)
        errors = check(args.output)
        if errors:
            raise ValueError('; '.join(errors))
        print(f'{len(ARTIFACTS)} artifacts verified; wheelhouse INCOMPLETE; no installation or motion.')
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
