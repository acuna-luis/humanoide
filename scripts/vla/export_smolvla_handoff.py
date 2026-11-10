#!/usr/bin/env python3
"""Create/verify a private offline SmolVLA handoff; never contact the robot.

The Git bundle contains the current branch and its reachable history, including
a known pre-existing credential in that history. Staged and unstaged tracked
changes are retained as separate binary patches. Only explicitly selected
evidence paths are copied; untracked files are inventoried by default and copied
only when selected explicitly. The result contains sensitive material and is
neither encrypted nor authenticated.
Do not upload or share it without protecting/sanitizing the contents.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT.parent / 'Humanoide-vla-evidence'
SCHEMA = 'cruzr_smolvla_handoff_v1'
CHUNK = 1024 * 1024
SMALL_EVIDENCE = (
    '20260914_ARM_MAPPING_LIMITS/hardware-configs.json',
    'SMOLVLA_CURRENT_READONLY_20261110T123648Z/state.json',
    'PICO_FULL_PASSIVE_CHECK/check-efc877e902bf4194be68dc32ab012167',
    'PICO_SYNTHETIC_CANCEL_CHECK',
    'PICO_NATIVE_WRIST_TRIAL/run-731084b3e4f94527a37de07297724bf1',
    'PICO_CANCEL_RESUME_20261110T161204Z_6362c42c',
)
LARGE_EVIDENCE = (
    '20261109T183246Z_EPISODE_7abf3106',
    '20261109T183726Z_EPISODE_879a137d',
    '20261109_VLA_BALL_OFFLINE_PREP/observations_v2',
    '20261109_VLA_BALL_OFFLINE_PREP/candidate_targets',
    '20261109_VLA_BALL_OFFLINE_PREP/checkpoint-backup/001000',
    '20261109_VLA_BALL_OFFLINE_PREP/checkpoint-backup/checkpoint-backup.sha256',
    'PORTABLE_HANDOFF_20261110/ada-dataset-v2',
    'PORTABLE_HANDOFF_20261110/ada-dataset-v2.SHA256',
)
INDEX_RULES = (
    ('20261109T183246Z_EPISODE_7abf3106/SHA256SUMS',
     '20261109T183246Z_EPISODE_7abf3106',
     'b79587a93877f959c66b62c58346ad423b48a63fcae4aa2027dd6da751f4fa00'),
    ('20261109T183726Z_EPISODE_879a137d/SHA256SUMS',
     '20261109T183726Z_EPISODE_879a137d',
     'f8448f7242b311fb7b2b01c76856fa55354cad10262e3e6b615364974d10def3'),
    ('20261109_VLA_BALL_OFFLINE_PREP/checkpoint-backup/checkpoint-backup.sha256',
     '20261109_VLA_BALL_OFFLINE_PREP/checkpoint-backup/001000',
     '4ef9f58239352720726fcf5dff27f50a6017971c2715968132568752635d021f'),
    ('PORTABLE_HANDOFF_20261110/ada-dataset-v2.SHA256',
     'PORTABLE_HANDOFF_20261110/ada-dataset-v2',
     '2492012858bbb868f2d2bb9a65e4e356cde2e816d0d3cd953189fe3d759e296a'),
)
# Strict file selection: no home folders, hidden state, credential/key files,
# arbitrary archives or files from outside the selected evidence. Logs remain
# private and should be reviewed before transmitting the resulting package.
EXTENSIONS = frozenset({'.json', '.jsonl', '.png', '.yaml', '.yml', '.xml',
                        '.txt', '.log', '.sha256', '.safetensors', '.py', '.urdf', '.parquet', '.mp4'})
SENSITIVE = re.compile(r'(?i)(^\.env(?:\.|$)|^\.secrets?$|^\.ssh$|'
                       r'credential|password|passwd|secret|askpass|api[_-]?key|'
                       r'access[_-]?token|private[_-]?key|^id_(?:rsa|ecdsa|ed25519))')
BINDING_DIRS = frozenset({'binding', 'bindings'})
TRANSIENT_SUFFIXES = ('.lock', '.pid', '.sock', '.tmp', '.swp')


def _git(repo: Path, *args: str) -> bytes:
    p = subprocess.run(['git', '-C', str(repo), *args], stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, check=False)
    if p.returncode:
        raise RuntimeError('git_failed:' + ' '.join(args[:2]) + ':' +
                           p.stderr.decode('utf-8', 'replace')[:500])
    return p.stdout


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(CHUNK), b''):
            h.update(block)
    return h.hexdigest()


def _check_current_file(path: Path, expected_sha256: str, expected_mode: int) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | getattr(os, 'O_NOFOLLOW', 0))
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or stat.S_IMODE(before.st_mode) & 0o777 != expected_mode:
            raise RuntimeError('untracked_changed_during_export:' + str(path))
        digest = hashlib.sha256()
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            for block in iter(lambda: stream.read(CHUNK), b''):
                digest.update(block)
        after = os.fstat(fd)
        if ((before.st_dev, before.st_ino, before.st_mode, before.st_size, before.st_mtime_ns, before.st_ctime_ns) !=
                (after.st_dev, after.st_ino, after.st_mode, after.st_size, after.st_mtime_ns, after.st_ctime_ns) or
                digest.hexdigest() != expected_sha256):
            raise RuntimeError('untracked_changed_during_export:' + str(path))
    finally:
        os.close(fd)


def _verify_original_indexes(output: Path, records: list[dict]) -> list[dict]:
    indexed = {row['path']: row for row in records}
    results = []
    for index_rel, data_rel, expected_index in INDEX_RULES:
        index_key = str(Path('Humanoide-vla-evidence') / index_rel)
        data_prefix = str(Path('Humanoide-vla-evidence') / data_rel) + '/'
        if index_key not in indexed:
            results.append({'index': index_rel, 'status': 'not_in_package'})
            continue
        if indexed[index_key]['sha256'] != expected_index:
            raise ValueError('original_index_sha256_changed:' + index_rel)
        index_path = output / index_key
        lines = index_path.read_text(encoding='utf-8').splitlines()
        entries = {}
        for line in lines:
            match = re.fullmatch(r'([0-9a-f]{64}) [ *](.+)', line)
            if match is None:
                raise ValueError('original_index_invalid:' + index_rel)
            name = match.group(2)
            if name.startswith('./'):
                name = name[2:]
            rel = _safe_rel(name)
            key = data_prefix + str(rel)
            if key in entries:
                raise ValueError('original_index_duplicate:' + index_rel)
            entries[key] = match.group(1)
        copied = {name for name in indexed if name.startswith(data_prefix) and name != index_key}
        if not entries or copied != set(entries):
            raise ValueError('original_index_file_set_mismatch:' + index_rel)
        if any(indexed[name]['sha256'] != digest for name, digest in entries.items()):
            raise ValueError('original_index_file_hash_mismatch:' + index_rel)
        results.append({'index': index_rel, 'status': 'matched_copy',
                        'index_sha256': expected_index, 'files_verified': len(entries)})
    return results


def _inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _safe_rel(value: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or '\0' in value or '\\' in value:
        raise ValueError('invalid_relative_path')
    path = PurePosixPath(value)
    if path.is_absolute() or any(x in ('', '.', '..') for x in path.parts):
        raise ValueError('invalid_relative_path:' + value)
    if any(part.startswith('.') or SENSITIVE.search(part) for part in path.parts):
        raise ValueError('private_or_secret_path_excluded:' + value)
    return path


def _selected_file(path: Path) -> bool:
    return path.name == 'SHA256SUMS' or path.suffix.lower() in EXTENSIONS


def _walk_selected(source: Path, evidence: Path) -> tuple[list[Path], list[str]]:
    if source.is_file():
        return [source], []
    if not source.is_dir():
        raise ValueError('selected_evidence_not_file_or_directory:' + str(source))
    paths, excluded = [], []
    for current, dirs, files in os.walk(source, topdown=True, followlinks=False):
        current_path = Path(current)
        keep = []
        for name in sorted(dirs):
            entry = current_path / name
            rel = str(entry.relative_to(evidence))
            if entry.is_symlink():
                excluded.append(rel + ':symlink')
            elif name.startswith('.') or SENSITIVE.search(name):
                excluded.append(rel + ':private_or_secret_name')
            elif name.lower() in BINDING_DIRS:
                excluded.append(rel + ':binding_must_be_regenerated')
            else:
                keep.append(name)
        dirs[:] = keep
        paths.extend(current_path / name for name in sorted(files))
    return paths, excluded


def _copy_file(src: Path, dst: Path) -> dict:
    flags = os.O_RDONLY | os.O_CLOEXEC | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(src, flags)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError('not_a_regular_file:' + str(src))
        dst.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        outfd = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC |
                        getattr(os, 'O_NOFOLLOW', 0), 0o600)
        digest = hashlib.sha256()
        size = 0
        with os.fdopen(outfd, 'wb') as out, os.fdopen(fd, 'rb', closefd=False) as inp:
            while True:
                block = inp.read(CHUNK)
                if not block:
                    break
                out.write(block)
                digest.update(block)
                size += len(block)
        after = os.fstat(fd)
        if ((before.st_dev, before.st_ino, before.st_mode, before.st_size, before.st_mtime_ns, before.st_ctime_ns) !=
                (after.st_dev, after.st_ino, after.st_mode, after.st_size, after.st_mtime_ns, after.st_ctime_ns) or
                size != before.st_size or dst.stat().st_size != size or _sha(dst) != digest.hexdigest()):
            raise RuntimeError('source_changed_or_copy_verification_failed:' + str(src))
        return {'size': size, 'sha256': digest.hexdigest()}
    finally:
        os.close(fd)


def _copy_evidence(evidence: Path, output: Path, selection: tuple[str, ...]) -> dict:
    copied, missing, excluded = [], [], []
    seen = set()
    for value in selection:
        rel = _safe_rel(value)
        source = evidence.joinpath(*rel.parts)
        if any(evidence.joinpath(*rel.parts[:i]).is_symlink() for i in range(1, len(rel.parts))):
            raise ValueError('evidence_symlink_or_escape:' + value)
        if not source.exists() and not source.is_symlink():
            missing.append(value)
            continue
        if source.is_symlink() or not _inside(source.resolve(), evidence):
            raise ValueError('evidence_symlink_or_escape:' + value)
        paths, skipped_dirs = _walk_selected(source, evidence)
        excluded.extend(skipped_dirs)
        initial_names = sorted(str(path.relative_to(evidence)) for path in paths)
        for src in paths:
            relpath = src.relative_to(evidence)
            # Symlinks and hidden/credential-named paths are not followed or copied.
            if src.is_symlink():
                excluded.append(str(relpath) + ':symlink')
                continue
            if any(part.startswith('.') or SENSITIVE.search(part) for part in relpath.parts):
                excluded.append(str(relpath) + ':private_or_secret_name')
                continue
            if any(part.lower() in BINDING_DIRS for part in relpath.parts):
                excluded.append(str(relpath) + ':binding_must_be_regenerated')
                continue
            if src.is_dir():
                continue
            if not stat.S_ISREG(src.lstat().st_mode):
                excluded.append(str(relpath) + ':not_regular_file')
                continue
            if not _selected_file(src):
                excluded.append(str(relpath) + ':file_type_not_selected')
                continue
            if relpath in seen:
                continue
            seen.add(relpath)
            dst = output / 'Humanoide-vla-evidence' / relpath
            entry = _copy_file(src, dst)
            copied.append({'path': str(Path('Humanoide-vla-evidence') / relpath), **entry})
        after, _ = _walk_selected(source, evidence)
        if sorted(str(path.relative_to(evidence)) for path in after) != initial_names:
            raise RuntimeError('evidence_directory_changed_during_export:' + value)
    return {'selected': list(selection), 'copied_files': len(copied), 'missing': missing,
            'excluded': excluded, 'files': copied}


def _write_new(path: Path, raw: bytes) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC |
                 getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
    return {'size': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def _untracked_selection(repo: Path, raw_names: list[str], selections: tuple[str, ...]) -> list[str]:
    result = set()
    all_names = set(raw_names)
    for value in selections:
        rel = _safe_rel(value)
        source = repo.joinpath(*rel.parts)
        if any(repo.joinpath(*rel.parts[:i]).is_symlink() for i in range(1, len(rel.parts) + 1)):
            raise ValueError('untracked_symlink_rejected:' + value)
        if source.is_file():
            candidates = [str(rel)] if str(rel) in all_names else []
        elif source.is_dir():
            candidates = [name for name in raw_names if name.startswith(str(rel) + '/')]
        else:
            raise ValueError('untracked_selection_missing:' + value)
        if not candidates:
            raise ValueError('selection_has_no_untracked_files:' + value)
        for name in candidates:
            path = _safe_rel(name)
            if path.name.lower().endswith(TRANSIENT_SUFFIXES):
                raise ValueError('transient_untracked_file_rejected:' + name)
            if any(repo.joinpath(*path.parts[:i]).is_symlink() for i in range(1, len(path.parts) + 1)):
                raise ValueError('untracked_symlink_rejected:' + name)
            source = repo.joinpath(*path.parts)
            if not source.is_file() or not stat.S_ISREG(source.lstat().st_mode):
                raise ValueError('untracked_not_regular_file:' + name)
            result.add(name)
    return sorted(result)


def create(repo: Path, evidence: Path, output: Path, *, light=False, extra=(),
           include_untracked=()) -> dict:
    repo, evidence = repo.resolve(strict=True), evidence.resolve(strict=True)
    output = output.absolute()
    parent = output.parent.resolve(strict=True)
    output = parent / output.name
    if not output.name or output.name in ('.', '..') or _inside(output, repo) or _inside(output, evidence):
        raise ValueError('output_must_be_outside_repository_and_evidence')
    if output.exists() or output.is_symlink():
        raise FileExistsError('output_already_exists')
    root = Path(os.fsdecode(_git(repo, 'rev-parse', '--show-toplevel').strip())).resolve()
    if root != repo:
        raise ValueError('repository_root_required')
    branch = _git(repo, 'symbolic-ref', '--quiet', '--short', 'HEAD').decode().strip()
    commit = _git(repo, 'rev-parse', 'HEAD').decode().strip()
    if not re.fullmatch(r'[0-9a-f]{40,64}', commit):
        raise ValueError('invalid_git_head')
    staged = _git(repo, 'diff', '--cached', '--binary', '--full-index', '--no-ext-diff', '--no-textconv')
    unstaged = _git(repo, 'diff', '--binary', '--full-index', '--no-ext-diff', '--no-textconv')
    status = _git(repo, 'status', '--short', '--branch')
    untracked = _git(repo, 'ls-files', '--others', '--exclude-standard', '-z').split(b'\0')
    names, raw_names = [], []
    withheld = 0
    for raw in untracked:
        if not raw:
            continue
        name = os.fsdecode(raw)
        raw_names.append(name)
        try:
            _safe_rel(name)
        except ValueError:
            withheld += 1
        else:
            names.append(name)
    selected_untracked = _untracked_selection(repo, raw_names, tuple(include_untracked))
    os.mkdir(output, 0o700)
    # A missing manifest means the export did not complete; never overwrite it.
    records = []
    untracked_modes = {name: stat.S_IMODE((repo / name).lstat().st_mode) & 0o777
                       for name in selected_untracked}
    for name, raw in (('git/staged.patch', staged), ('git/unstaged.patch', unstaged),
                      ('git/status.txt', status),
                      ('git/untracked.json', (json.dumps({'paths': names, 'withheld_count': withheld},
                                                          ensure_ascii=True, indent=2)+'\n').encode())):
        records.append({'path': name, **_write_new(output / name, raw)})
    bundle = output / 'git' / 'branch.bundle'
    _git(repo, 'bundle', 'create', str(bundle), 'HEAD', 'refs/heads/' + branch)
    os.chmod(bundle, 0o600)
    _git(repo, 'bundle', 'verify', str(bundle))
    heads = _git(repo, 'bundle', 'list-heads', str(bundle)).decode()
    if not any(line.split() == [commit, 'refs/heads/' + branch] for line in heads.splitlines()):
        raise RuntimeError('bundle_head_mismatch')
    records.append({'path': 'git/branch.bundle', 'size': bundle.stat().st_size, 'sha256': _sha(bundle)})
    selection = SMALL_EVIDENCE + (() if light else LARGE_EVIDENCE) + tuple(extra)
    selected = _copy_evidence(evidence, output, selection)
    records.extend(selected.pop('files'))
    for name in selected_untracked:
        entry = _copy_file(repo / name, output / 'git' / 'untracked-files' / name)
        if stat.S_IMODE((repo / name).lstat().st_mode) & 0o777 != untracked_modes[name]:
            raise RuntimeError('untracked_mode_changed_during_export:' + name)
        records.append({'path': str(Path('git/untracked-files') / name), **entry})
    record_by_path = {row['path']: row for row in records}
    for name in selected_untracked:
        rel = _safe_rel(name)
        if any(repo.joinpath(*rel.parts[:i]).is_symlink() for i in range(1, len(rel.parts) + 1)):
            raise RuntimeError('untracked_symlink_changed_during_export:' + name)
        _check_current_file(repo / name, record_by_path[str(Path('git/untracked-files') / name)]['sha256'],
                            untracked_modes[name])
    source_indexes = _verify_original_indexes(output, records)
    if not light:
        for result in source_indexes:
            if result['status'] == 'not_in_package':
                selected['missing'].append('source-index:' + result['index'])
    # Catch a changing index/working tree while snapshotting; fail, do not claim
    # this package reproduces a moving workspace.
    if (commit != _git(repo, 'rev-parse', 'HEAD').decode().strip() or
            branch != _git(repo, 'symbolic-ref', '--quiet', '--short', 'HEAD').decode().strip() or
            staged != _git(repo, 'diff', '--cached', '--binary', '--full-index', '--no-ext-diff', '--no-textconv') or
            unstaged != _git(repo, 'diff', '--binary', '--full-index', '--no-ext-diff', '--no-textconv') or
            status != _git(repo, 'status', '--short', '--branch') or
            untracked != _git(repo, 'ls-files', '--others', '--exclude-standard', '-z').split(b'\0')):
        raise RuntimeError('repository_changed_during_export_incomplete')
    manifest = {'schema': SCHEMA, 'branch': branch, 'commit': commit, 'light': light,
                'files': sorted(records, key=lambda x: x['path']), 'evidence': selected,
                'untracked_files_copied': selected_untracked,
                'untracked_modes': untracked_modes,
                'original_evidence_indexes': source_indexes,
                'dataset_provenance': {
                    'source_server': 'luisacuna@192.168.1.43:2649',
                    'source_path': '/home/luisacuna/cruzr-smolvla-ball-20261109/dataset-v2/lerobot-experiment',
                    'local_copy': 'Humanoide-vla-evidence/PORTABLE_HANDOFF_20261110/ada-dataset-v2',
                    'local_index': 'Humanoide-vla-evidence/PORTABLE_HANDOFF_20261110/ada-dataset-v2.SHA256',
                    'index_sha256_when_acquired': '2492012858bbb868f2d2bb9a65e4e356cde2e816d0d3cd953189fe3d759e296a',
                    'included_only_if_selected_and_present': True},
                'limitations': ['KNOWN: git history contains a pre-existing credential; this bundle contains it',
                  'private images, logs, patches and history may contain additional sensitive information',
                  'not encrypted: do not upload or share without protecting/sanitizing',
                  'credential files and old binding directories are excluded from selected evidence; contents not secret-scanned',
                  'only explicitly selected untracked files are copied; Git-ignored vendor packages are omitted',
                  'Ada image/volume and current robot state are not copied; dataset-v2 only if selected copy exists',
                  'hashes establish integrity, not source authenticity',
                  'this snapshot does not authorize motion or reflect current physical state']}
    raw = (json.dumps(manifest, ensure_ascii=True, sort_keys=True, indent=2)+'\n').encode()
    _write_new(output / 'manifest.json', raw)
    return {'status': 'CREATED_WITH_MISSING_EVIDENCE' if selected['missing'] else 'CREATED',
            'output': str(output), 'commit': commit,
            'manifest_sha256': hashlib.sha256(raw).hexdigest(),
            'missing_evidence': selected['missing'], 'excluded_files': len(selected['excluded']),
            'copied_untracked_files': len(selected_untracked),
            'light': light, 'sensitive_git_history_contains_credential': True,
            'do_not_upload_or_share_unprotected': True}


def verify(output: Path, *, expected_manifest_sha256: str | None = None) -> dict:
    output = output.resolve(strict=True)
    manifest_path = output / 'manifest.json'
    if manifest_path.is_symlink():
        raise ValueError('manifest_symlink_rejected')
    if manifest_path.stat().st_size > 16 * 1024 * 1024:
        raise ValueError('manifest_too_large')
    raw = manifest_path.read_bytes()
    manifest_digest = hashlib.sha256(raw).hexdigest()
    if expected_manifest_sha256 is not None:
        if not re.fullmatch('[0-9a-f]{64}', expected_manifest_sha256):
            raise ValueError('invalid_expected_manifest_sha256')
        if manifest_digest != expected_manifest_sha256:
            raise ValueError('manifest_sha256_mismatch')
    data = json.loads(raw)
    if data.get('schema') != SCHEMA or not isinstance(data.get('files'), list):
        raise ValueError('invalid_manifest')
    expected = set()
    for item in data['files']:
        if not isinstance(item, dict) or set(item) != {'path', 'size', 'sha256'}:
            raise ValueError('invalid_file_record')
        rel = _safe_rel(item['path'])
        if str(rel) in expected:
            raise ValueError('duplicate_manifest_path')
        expected.add(str(rel))
        path = output.joinpath(*rel.parts)
        if any(p.is_symlink() for p in (path, *[output.joinpath(*rel.parts[:i]) for i in range(1, len(rel.parts))])):
            raise ValueError('symlink_in_package')
        if (not path.is_file() or type(item['size']) is not int or path.stat().st_size != item['size'] or
                not re.fullmatch('[0-9a-f]{64}', str(item['sha256'])) or _sha(path) != item['sha256']):
            raise ValueError('package_file_mismatch:' + str(rel))
    actual = set()
    for path in output.rglob('*'):
        if path.is_symlink():
            raise ValueError('symlink_in_package')
        if path.is_file() and path != manifest_path:
            actual.add(str(path.relative_to(output)))
    if actual != expected:
        raise ValueError('package_file_set_mismatch')
    if data.get('original_evidence_indexes') != _verify_original_indexes(output, data['files']):
        raise ValueError('original_index_status_mismatch')
    return {'status': ('VERIFIED_INTEGRITY_WITH_MISSING_EVIDENCE' if data['evidence']['missing']
                       else 'VERIFIED_INTEGRITY'), 'manifest_sha256': manifest_digest,
            'commit': data['commit'], 'missing_evidence': data['evidence']['missing'],
            'light': data['light'], 'external_manifest_digest_compared': expected_manifest_sha256 is not None,
            'authenticity_verified': False}


class PartialRestoreError(RuntimeError):
    def __init__(self, message: str, created: list[str]):
        super().__init__(message)
        self.created = list(created)


class _RestoreFileError(RuntimeError):
    def __init__(self, message: str, created: bool):
        super().__init__(message)
        self.created = created


def _preflight_restore_path(root: Path, rel: PurePosixPath) -> None:
    current = root
    for index, part in enumerate(rel.parts):
        current = current / part
        if current.is_symlink():
            raise ValueError('restore_symlink_rejected:' + str(rel))
        if index < len(rel.parts) - 1 and current.exists() and not current.is_dir():
            raise ValueError('restore_parent_not_directory:' + str(rel))
        if index == len(rel.parts) - 1 and current.exists():
            raise FileExistsError('restore_destination_exists:' + str(rel))


def _restore_one(root: Path, rel: PurePosixPath, source: Path, expected: dict, mode: int) -> None:
    # dir_fd + O_NOFOLLOW prevents a substituted symlink from escaping target.
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | getattr(os, 'O_NOFOLLOW', 0)
    current = None
    created = False
    try:
        current = os.open(root, flags)
        for part in rel.parts[:-1]:
            try:
                os.mkdir(part, 0o755, dir_fd=current)
            except FileExistsError:
                pass
            child = os.open(part, flags, dir_fd=current)
            os.close(current)
            current = child
        source_fd = os.open(source, os.O_RDONLY | os.O_CLOEXEC | getattr(os, 'O_NOFOLLOW', 0))
        try:
            target_fd = os.open(rel.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC |
                                getattr(os, 'O_NOFOLLOW', 0), 0o600, dir_fd=current)
            created = True
            digest, size = hashlib.sha256(), 0
            with os.fdopen(target_fd, 'wb') as out, os.fdopen(source_fd, 'rb', closefd=False) as inp:
                while True:
                    block = inp.read(CHUNK)
                    if not block:
                        break
                    out.write(block)
                    digest.update(block)
                    size += len(block)
                if size != expected['size'] or digest.hexdigest() != expected['sha256']:
                    raise ValueError('restore_source_changed:' + str(rel))
                os.fchmod(out.fileno(), mode)
        finally:
            os.close(source_fd)
    except (OSError, ValueError, TypeError) as exc:
        raise _RestoreFileError(str(exc), created) from exc
    finally:
        if current is not None:
            os.close(current)


def restore_untracked(output: Path, checkout: Path, *, expected_manifest_sha256: str) -> dict:
    """Restore explicitly retained files into a checkout; never overwrite.

    Verify all data and destinations before creating files. If an I/O error or
    concurrent change happens later, report every file created and leave it in
    place for inspection; do not erase user's work or apply Git patches.
    """
    if not expected_manifest_sha256:
        raise ValueError('restore_requires_independently_retained_manifest_sha256')
    checked = verify(output, expected_manifest_sha256=expected_manifest_sha256)
    output, checkout = output.resolve(strict=True), checkout.resolve(strict=True)
    if _inside(checkout, output) or _inside(output, checkout):
        raise ValueError('restore_checkout_overlaps_package')
    if Path(os.fsdecode(_git(checkout, 'rev-parse', '--show-toplevel').strip())).resolve() != checkout:
        raise ValueError('restore_checkout_root_required')
    data = json.loads((output/'manifest.json').read_bytes())
    names, modes = data.get('untracked_files_copied'), data.get('untracked_modes')
    if not isinstance(names, list) or not isinstance(modes, dict) or len(set(names)) != len(names):
        raise ValueError('invalid_untracked_restore_manifest')
    if set(modes) != set(names):
        raise ValueError('untracked_restore_modes_mismatch')
    tracked = {os.fsdecode(x) for x in _git(checkout, 'ls-files', '-z').split(b'\0') if x}
    indexed = {row['path']: row for row in data['files']}
    paths = []
    for name in names:
        rel = _safe_rel(name)
        if name in tracked or rel.name.lower().endswith(TRANSIENT_SUFFIXES):
            raise ValueError('restore_tracked_or_transient_rejected:' + name)
        if type(modes[name]) is not int or not 0 <= modes[name] <= 0o777:
            raise ValueError('invalid_untracked_restore_mode:' + name)
        record_name = str(Path('git/untracked-files') / name)
        if record_name not in indexed:
            raise ValueError('untracked_restore_file_missing:' + name)
        _preflight_restore_path(checkout, rel)
        paths.append((name, rel, indexed[record_name]))
    created = []
    for name, rel, record in paths:
        try:
            _restore_one(checkout, rel, output / record['path'], record, modes[name])
            created.append(name)
        except _RestoreFileError as exc:
            if exc.created:
                created.append(name)
            raise PartialRestoreError('restore_incomplete:' + name + ':' + str(exc), created) from exc
    return {'status': 'RESTORED_UNTRACKED', 'checkout': str(checkout),
            'created': created, 'manifest_sha256': checked['manifest_sha256'],
            'patches_applied': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--output', type=Path, help='new private directory outside repository and evidence')
    group.add_argument('--verify', type=Path, help='verify file integrity of an existing export')
    parser.add_argument('--light', action='store_true', help='omit large recordings, candidates and checkpoint')
    parser.add_argument('--include-evidence', action='append', default=[], metavar='RELATIVE_PATH',
                        help='also select a relative path below the evidence root')
    parser.add_argument('--include-untracked', action='append', default=[], metavar='REPO_RELATIVE_PATH',
                        help='also preserve selected untracked, nonignored repository files')
    parser.add_argument('--manifest-sha256', help='independently retained manifest digest, only with --verify')
    parser.add_argument('--restore-untracked', type=Path, metavar='CHECKOUT',
                        help='with --verify and --manifest-sha256, restore retained untracked files without overwrite')
    args = parser.parse_args(argv)
    if args.verify is not None and (args.light or args.include_evidence or args.include_untracked):
        parser.error('--light, --include-evidence and --include-untracked apply only with --output')
    if args.output is not None and args.manifest_sha256 is not None:
        parser.error('--manifest-sha256 applies only with --verify')
    if args.restore_untracked is not None and (args.verify is None or args.manifest_sha256 is None):
        parser.error('--restore-untracked requires --verify and --manifest-sha256')
    try:
        if args.restore_untracked is not None:
            result = restore_untracked(args.verify, args.restore_untracked,
                                       expected_manifest_sha256=args.manifest_sha256)
        elif args.verify is not None:
            result = verify(args.verify, expected_manifest_sha256=args.manifest_sha256)
        else:
            result = create(ROOT, EVIDENCE, args.output, light=args.light, extra=args.include_evidence,
                            include_untracked=args.include_untracked)
        print(json.dumps(result, ensure_ascii=True, sort_keys=True))
        return 0
    except PartialRestoreError as exc:
        print(json.dumps({'status': 'RESTORE_INCOMPLETE', 'error': str(exc),
                          'created_or_partial': exc.created, 'patches_applied': False},
                         ensure_ascii=True, sort_keys=True), file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as exc:
        print('HANDOFF_FAILED:' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
