#!/usr/bin/env python3
"""Verify private migration archives without extracting them or controlling robot."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile


def digest(stream):
    h = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b''):
        h.update(block)
    return h.hexdigest()


def verify_backup(path):
    with tarfile.open(path) as archive:
        members = {m.name: m for m in archive.getmembers()}
        manifests = [n for n in members if n.endswith('/SHA256SUMS')]
        if len(manifests) != 1:
            raise ValueError('Expected one final checksum manifest')
        prefix = manifests[0].rsplit('/', 1)[0] + '/'
        def read(name):
            return archive.extractfile(members[prefix + name]).read()
        if read('STATUS').strip() != b'CAPTURED_REVIEW_COVERAGE' or read('failures.txt').strip():
            raise ValueError('Backup incomplete or contains failures')
        checked = 0
        for line in read('SHA256SUMS').decode().splitlines():
            expected, relative = line.split('  ', 1)
            relative = relative.removeprefix('./')
            if len(expected) != 64 or '..' in PurePosixPath(relative).parts or relative.startswith('/'):
                raise ValueError('Invalid checksum entry')
            member = members[prefix + relative]
            if not member.isfile() or digest(archive.extractfile(member)) != expected:
                raise ValueError('Checksum mismatch: ' + relative)
            checked += 1
        if not checked:
            raise ValueError('Empty checksum manifest')
    return {'verified': True, 'files': checked, 'archive': str(path)}


def verify_selected(directory):
    expected = {}
    for slot in ('hw', 'app'):
        receipt = json.loads((directory / (slot + '-stage-receipt.json')).read_text())
        if receipt['returncode'] != 0:
            raise ValueError('Failed stage receipt')
        expected[slot + '.tar'] = json.loads(receipt['stdout'])['sha256']
    receipt = json.loads((directory / 'env-stage-receipt.json').read_text())
    if receipt['returncode'] != 0:
        raise ValueError('Failed env stage receipt')
    expected.update(json.loads(receipt['stdout']))
    path = directory / 'selected-writable-files.tar'
    with tarfile.open(path) as archive:
        members = {m.name.removeprefix('./'): m for m in archive.getmembers()}
        for name, sha in expected.items():
            member = members[name]
            if not member.isfile() or digest(archive.extractfile(member)) != sha:
                raise ValueError('Selected archive mismatch: ' + name)
    return {'verified': True, 'files': len(expected), 'archive': str(path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', required=True, type=Path)
    parser.add_argument('--role', required=True, choices=('motion', 'vision', 'selected'))
    args = parser.parse_args()
    directory, role = args.evidence, args.role
    report = verify_selected(directory) if role == 'selected' else verify_backup(directory / (role + '-preupgrade.tar'))
    (directory / (role + '-backup-verification.json')).write_text(json.dumps(report, indent=2))
    reports = [directory / (r + '-backup-verification.json') for r in ('motion', 'vision', 'selected')]
    if all(p.exists() and json.loads(p.read_text()).get('verified') is True for p in reports):
        proof = {r: True for r in ('motion', 'vision', 'selected')}
        proof['reports'] = [str(p) for p in reports]
        (directory / 'migration-backups-verified.json').write_text(json.dumps(proof, indent=2))
    print(json.dumps(report))


if __name__ == '__main__':
    main()
