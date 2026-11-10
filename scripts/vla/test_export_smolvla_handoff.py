#!/usr/bin/env python3
"""Offline tests for the portable handoff; no robot, server or real data."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import export_smolvla_handoff as handoff


def run(cwd, *args):
    return subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          check=True).stdout


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base/'repo'
        self.repo.mkdir()
        run(self.repo, 'git', 'init', '-q', '--initial-branch=handoff-test')
        run(self.repo, 'git', 'config', 'user.name', 'handoff-test')
        run(self.repo, 'git', 'config', 'user.email', 'handoff@example.invalid')
        (self.repo/'tracked.bin').write_bytes(b'original\x00')
        run(self.repo, 'git', 'add', 'tracked.bin')
        run(self.repo, 'git', 'commit', '-q', '-m', 'base')
        self.evidence = self.base/'evidence'
        self.evidence.mkdir()
        (self.evidence/'record').mkdir()
        (self.evidence/'record'/'sample.json').write_text('{"sample":1}\n')
        (self.evidence/'record'/'camera.png').write_bytes(b'private-image')
        (self.evidence/'record'/'password.txt').write_text('do-not-copy')
        (self.evidence/'record'/'.env').write_text('do-not-copy')
        (self.evidence/'record'/'binding').mkdir()
        (self.evidence/'record'/'binding'/'anything.json').write_text('{"private":"x"}')
        self.out = self.base/'export'

    def create(self, *, light=False, extra=(), include_untracked=()):
        with patch.object(handoff, 'SMALL_EVIDENCE', ('record',)), \
             patch.object(handoff, 'LARGE_EVIDENCE', ('missing-large',)):
            return handoff.create(self.repo, self.evidence, self.out, light=light, extra=extra,
                                  include_untracked=include_untracked)

    def test_git_bundle_staged_and_unstaged_restore_without_untracked(self):
        (self.repo/'tracked.bin').write_bytes(b'staged\x00')
        run(self.repo, 'git', 'add', 'tracked.bin')
        (self.repo/'tracked.bin').write_bytes(b'unstaged\x00')
        (self.repo/'new.txt').write_text('untracked user data')
        result = self.create(light=True)
        self.assertEqual(result['missing_evidence'], [])
        verified = handoff.verify(self.out, expected_manifest_sha256=result['manifest_sha256'])
        self.assertEqual(verified['status'], 'VERIFIED_INTEGRITY')
        self.assertTrue(verified['external_manifest_digest_compared'])
        self.assertTrue(result['sensitive_git_history_contains_credential'])
        self.assertEqual((self.out.stat().st_mode & 0o777), 0o700)
        self.assertFalse((self.out/'Humanoide-vla-evidence/record/password.txt').exists())
        self.assertFalse((self.out/'Humanoide-vla-evidence/record/.env').exists())
        self.assertFalse((self.out/'Humanoide-vla-evidence/record/binding').exists())
        inventory = json.loads((self.out/'git/untracked.json').read_text())
        self.assertEqual(inventory['paths'], ['new.txt'])
        self.assertFalse((self.out/'git/new.txt').exists())
        clone = self.base/'clone'
        run(self.base, 'git', 'clone', '-q', '--branch', 'handoff-test',
            str(self.out/'git/branch.bundle'), str(clone))
        run(clone, 'git', 'apply', '--index', str(self.out/'git/staged.patch'))
        run(clone, 'git', 'apply', str(self.out/'git/unstaged.patch'))
        self.assertEqual((clone/'tracked.bin').read_bytes(), b'unstaged\x00')
        self.assertEqual(run(clone, 'git', 'show', ':tracked.bin'), b'staged\x00')
        self.assertFalse((clone/'new.txt').exists())

    def test_missing_explicit_and_light_not_claimed_complete(self):
        result = self.create()
        self.assertIn('missing-large', result['missing_evidence'])
        self.assertTrue(any(x.startswith('source-index:') for x in result['missing_evidence']))
        self.assertEqual(handoff.verify(self.out)['missing_evidence'], result['missing_evidence'])
        self.assertEqual(result['status'], 'CREATED_WITH_MISSING_EVIDENCE')
        self.assertFalse(result['light'])

    def test_existing_destination_and_inside_sources_are_rejected(self):
        self.out.mkdir()
        (self.out/'do-not-overwrite').write_text('keep')
        with self.assertRaises(FileExistsError):
            self.create()
        self.assertEqual((self.out/'do-not-overwrite').read_text(), 'keep')
        for path in (self.repo/'export', self.evidence/'export'):
            with self.assertRaisesRegex(ValueError, 'outside_repository_and_evidence'):
                handoff.create(self.repo, self.evidence, path, light=True)
            self.assertFalse(path.exists())

    def test_verify_detects_changed_added_and_symlink_files(self):
        result = self.create(light=True)
        with self.assertRaisesRegex(ValueError, 'manifest_sha256_mismatch'):
            handoff.verify(self.out, expected_manifest_sha256='0'*64)
        self.assertEqual(handoff.verify(self.out, expected_manifest_sha256=result['manifest_sha256'])['status'],
                         'VERIFIED_INTEGRITY')
        target = self.out/'Humanoide-vla-evidence/record/sample.json'
        original = target.read_bytes()
        target.write_bytes(b'altered')
        with self.assertRaisesRegex(ValueError, 'package_file_mismatch'):
            handoff.verify(self.out)
        target.write_bytes(original)
        added = self.out/'extra.txt'
        added.write_text('extra')
        with self.assertRaisesRegex(ValueError, 'package_file_set_mismatch'):
            handoff.verify(self.out)
        added.unlink()
        target.unlink()
        target.symlink_to(self.evidence/'record/sample.json')
        with self.assertRaisesRegex(ValueError, 'symlink_in_package'):
            handoff.verify(self.out)

    def test_extra_selection_rejects_escape_and_secret(self):
        for name in ('../outside', '/etc/passwd', 'record/.env', 'record/password.txt'):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    handoff._safe_rel(name)
        (self.evidence/'outside').symlink_to(self.repo, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlink_or_escape'):
            self.create(light=True, extra=('outside',))
        self.assertFalse((self.out/'manifest.json').exists())

    def test_repository_changing_during_export_is_not_complete(self):
        original = handoff._copy_evidence
        def change(*args, **kwargs):
            value = original(*args, **kwargs)
            (self.repo/'tracked.bin').write_bytes(b'changed mid-export')
            return value
        with patch.object(handoff, '_copy_evidence', side_effect=change):
            with self.assertRaisesRegex(RuntimeError, 'repository_changed_during_export'):
                self.create(light=True)
        self.assertFalse((self.out/'manifest.json').exists())

    def test_changing_evidence_directory_is_not_complete(self):
        original = handoff._copy_file
        called = False
        def change(src, dst):
            nonlocal called
            result = original(src, dst)
            if not called:
                called = True
                (self.evidence/'record'/'new.json').write_text('{}')
            return result
        with patch.object(handoff, '_copy_file', side_effect=change):
            with self.assertRaisesRegex(RuntimeError, 'evidence_directory_changed'):
                self.create(light=True)
        self.assertFalse((self.out/'manifest.json').exists())

    def test_selected_untracked_restore_preflight_and_no_overwrite(self):
        folder = self.repo/'user-data'
        folder.mkdir()
        (folder/'a.txt').write_text('alpha')
        (folder/'b.txt').write_text('beta')
        (folder/'a.txt').chmod(0o640)
        (self.repo/'not-selected.txt').write_text('not copied')
        result = self.create(light=True, include_untracked=('user-data',))
        self.assertEqual(result['copied_untracked_files'], 2)
        self.assertFalse((self.out/'git/untracked-files/not-selected.txt').exists())
        clone = self.base/'clone'
        run(self.base, 'git', 'clone', '-q', '--branch', 'handoff-test',
            str(self.out/'git/branch.bundle'), str(clone))
        (clone/'user-data').mkdir()
        (clone/'user-data'/'b.txt').write_text('preserve me')
        with self.assertRaises(FileExistsError):
            handoff.restore_untracked(self.out, clone, expected_manifest_sha256=result['manifest_sha256'])
        self.assertFalse((clone/'user-data'/'a.txt').exists())
        self.assertEqual((clone/'user-data'/'b.txt').read_text(), 'preserve me')
        (clone/'user-data'/'b.txt').unlink()
        restored = handoff.restore_untracked(self.out, clone, expected_manifest_sha256=result['manifest_sha256'])
        self.assertEqual(restored['created'], ['user-data/a.txt', 'user-data/b.txt'])
        self.assertEqual((clone/'user-data'/'a.txt').read_text(), 'alpha')
        self.assertEqual((clone/'user-data'/'a.txt').stat().st_mode & 0o777, 0o640)
        self.assertFalse((clone/'not-selected.txt').exists())
        with self.assertRaises(FileExistsError):
            handoff.restore_untracked(self.out, clone, expected_manifest_sha256=result['manifest_sha256'])

    def test_selected_untracked_rejects_hidden_transient_and_symlinks(self):
        (self.repo/'data').mkdir()
        (self.repo/'data'/'unsafe.lock').write_text('lock')
        with self.assertRaisesRegex(ValueError, 'transient_untracked_file_rejected'):
            self.create(light=True, include_untracked=('data',))
        self.assertFalse(self.out.exists())
        (self.repo/'data'/'unsafe.lock').unlink()
        (self.repo/'data'/'link.txt').symlink_to(self.evidence/'record'/'sample.json')
        with self.assertRaisesRegex(ValueError, 'untracked_symlink_rejected'):
            self.create(light=True, include_untracked=('data',))
        self.assertFalse(self.out.exists())
        with self.assertRaises(ValueError):
            self.create(light=True, include_untracked=('.env',))

    def test_restore_reports_only_created_paths_on_partial_failure(self):
        (self.repo/'data').mkdir()
        (self.repo/'data'/'a.txt').write_text('one')
        (self.repo/'data'/'b.txt').write_text('two')
        result = self.create(light=True, include_untracked=('data',))
        clone = self.base/'clone'
        run(self.base, 'git', 'clone', '-q', '--branch', 'handoff-test',
            str(self.out/'git/branch.bundle'), str(clone))
        original = handoff._restore_one
        def injected(root, rel, source, expected, mode):
            if rel.name == 'b.txt':
                raise handoff._RestoreFileError('injected', False)
            return original(root, rel, source, expected, mode)
        with patch.object(handoff, '_restore_one', side_effect=injected):
            with self.assertRaises(handoff.PartialRestoreError) as caught:
                handoff.restore_untracked(self.out, clone, expected_manifest_sha256=result['manifest_sha256'])
        self.assertEqual(caught.exception.created, ['data/a.txt'])
        self.assertEqual((clone/'data'/'a.txt').read_text(), 'one')
        self.assertFalse((clone/'data'/'b.txt').exists())

    def test_untracked_mutated_after_copy_fails_export(self):
        source = self.repo/'selected.txt'
        source.write_text('initial')
        original = handoff._copy_file
        def change(src, dst):
            value = original(src, dst)
            if src == source:
                source.write_text('mutated after copy')
            return value
        with patch.object(handoff, '_copy_file', side_effect=change):
            with self.assertRaisesRegex(RuntimeError, 'untracked_changed_during_export'):
                self.create(light=True, include_untracked=('selected.txt',))
        self.assertFalse((self.out/'manifest.json').exists())

    def test_original_index_is_pinned_and_matches_the_copied_set(self):
        directory = self.evidence/'record'
        digest = lambda name: hashlib.sha256((directory/name).read_bytes()).hexdigest()
        index = directory/'SHA256SUMS'
        index.write_text(f'{digest("camera.png")}  camera.png\n{digest("sample.json")}  sample.json\n')
        expected = hashlib.sha256(index.read_bytes()).hexdigest()
        rule = (('record/SHA256SUMS', 'record', expected),)
        with patch.object(handoff, 'INDEX_RULES', rule):
            self.create(light=True)
            checked = handoff.verify(self.out)
            self.assertEqual(checked['status'], 'VERIFIED_INTEGRITY')
            value = json.loads((self.out/'manifest.json').read_text())
            self.assertEqual(value['original_evidence_indexes'][0]['files_verified'], 2)

    def test_original_index_rejects_content_mismatch(self):
        directory = self.evidence/'record'
        index = directory/'SHA256SUMS'
        good = hashlib.sha256((directory/'camera.png').read_bytes()).hexdigest()
        index.write_text(f'{good}  camera.png\n' + '0'*64 + '  sample.json\n')
        rule = (('record/SHA256SUMS', 'record', hashlib.sha256(index.read_bytes()).hexdigest()),)
        with patch.object(handoff, 'INDEX_RULES', rule):
            with self.assertRaisesRegex(ValueError, 'original_index_file_hash_mismatch'):
                self.create(light=True)
        self.assertFalse((self.out/'manifest.json').exists())


if __name__ == '__main__':
    unittest.main()
