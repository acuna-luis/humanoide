"""Offline voice packaging, launcher fallback and rollback; no robot or playback."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepare_speech_voice as prepare
from deploy_voice_assets import HELPER


def digest(data):
    return hashlib.sha256(data).hexdigest()


def catalog():
    return [dict(kind='fixed', id='speech_ready', zh='语音服务准备就绪',
                 es='El servicio de voz está listo.', en='The voice service is ready.'),
            dict(kind='fixed', id='speech_failed', zh='语音服务启动失败',
                 es='No se pudo iniciar el servicio de voz.',
                 en='The voice service could not start.')]


class CatalogTests(unittest.TestCase):
    def test_only_nonempty_reviewed_fixed_chinese_catalogs_are_accepted(self):
        dynamic = catalog(); dynamic[0]['kind'] = 'dynamic'
        not_chinese = catalog(); not_chinese[0]['zh'] = 'Unreviewed English input'
        for value in ([], {}, [None], dynamic, not_chinese):
            with self.subTest(value=value), self.assertRaises(ValueError):
                prepare.validate_catalog(value)

    def test_valid_catalog_keeps_exact_chinese_keys_and_both_translations(self):
        rows = catalog()
        before = copy.deepcopy(rows)
        selected = prepare.validate_catalog(rows)
        self.assertEqual(selected, rows)
        self.assertEqual(rows, before)
        header = prepare.build_catalog_header(rows)
        for row in rows:
            for key in ('id', 'zh', 'en'):
                self.assertIn(json.dumps(row[key], ensure_ascii=False), header)

    def test_duplicate_id_or_source_text_is_ambiguous(self):
        for key in ('id', 'zh'):
            rows = catalog()
            rows[1][key] = rows[0][key]
            with self.subTest(key=key), self.assertRaises(ValueError):
                prepare.validate_catalog(rows)

    def test_audio_id_cannot_escape_directory_or_inject_a_path(self):
        for value in ('../other', '/absolute', 'a/b', 'a\\b', '.', '..', '', 'a\x00b'):
            rows = catalog()
            rows[0]['id'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                prepare.validate_catalog(rows)

    def test_missing_or_blank_text_cannot_silence_original_announcement(self):
        for key in ('zh', 'es', 'en'):
            for value in ('', '   ', None):
                rows = catalog()
                rows[0][key] = value
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    prepare.validate_catalog(rows)

    def test_untranslated_chinese_is_rejected_in_spanish_and_english(self):
        for key in ('es', 'en'):
            rows = catalog()
            rows[0][key] = rows[0]['zh']
            with self.subTest(key=key), self.assertRaises(ValueError):
                prepare.validate_catalog(rows)

    def test_header_escapes_quoted_english_and_chinese_literals(self):
        rows = catalog()
        rows[0]['zh'] += '，消息"测试"'
        rows[0]['en'] = 'Service "voice" is ready; path C:\\voice.'
        header = prepare.build_catalog_header(rows)
        self.assertIn(json.dumps(rows[0]['zh'], ensure_ascii=False), header)
        self.assertIn(json.dumps(rows[0]['en'], ensure_ascii=False), header)


class LauncherTests(unittest.TestCase):
    ORIGINAL = '''#!/usr/bin/env bash
set -e
export ORIGINAL_MARKER=preserved
cmd='printf "%s\\n" "ORIGINAL_CMD:$ORIGINAL_MARKER:preload=$LD_PRELOAD"'
eval "$cmd"
'''

    def invoke(self, script, existing='/existing-one.so:/existing-two.so'):
        # This shell function changes only the test's handling of the export.
        # No fake .so is exported to the dynamic linker, even with valid hashes.
        probe = '''LD_PRELOAD=EXISTING
export() {
 if [[ "$1" == LD_PRELOAD=* ]]; then
  LD_PRELOAD="${1#LD_PRELOAD=}"
 else
  builtin export "$@"
 fi
}
source "$1"
'''.replace('EXISTING', shlex.quote(existing))
        env = os.environ.copy()
        env.pop('LD_PRELOAD', None)
        return subprocess.run(['bash', '-c', probe, 'voice-guard-test', str(script)],
                              env=env, capture_output=True, text=True, timeout=5)

    def test_hash_guard_preserves_original_command_and_existing_preload(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            library = root/'lib voice.so'
            audio = root/'spanish.wav'
            native = root/'vendor binary'
            for path, value in ((library, b'fake-library-never-loaded'),
                                (audio, b'fake-audio-never-played'), (native, b'vendor')):
                path.write_bytes(value)
            hashes = {str(path): digest(path.read_bytes()) for path in (library, audio, native)}
            after = prepare.launcher_with_voice(self.ORIGINAL, hashes, str(library))
            before_prefix, before_suffix = self.ORIGINAL.split('eval "$cmd"')
            self.assertTrue(after.startswith(before_prefix))
            self.assertTrue(after.endswith('eval "$cmd"'+before_suffix))
            script = root/'entrypoint.sh'
            script.write_text(after)
            check = subprocess.run(['bash', '-n', str(script)], capture_output=True, text=True)
            self.assertEqual(check.returncode, 0, check.stderr)
            for existing in ('', '/existing-one.so:/existing-two.so'):
                result = self.invoke(script, existing)
                self.assertEqual(result.returncode, 0, result.stderr)
                wanted = str(library) + (':'+existing if existing else '')
                self.assertIn('ORIGINAL_CMD:preserved:preload='+wanted, result.stdout)
                self.assertNotIn('ld.so', result.stderr)

            for path in (library, audio, native):
                original = path.read_bytes()
                for state in ('corrupt', 'missing'):
                    if state == 'corrupt':
                        path.write_bytes(b'changed')
                    else:
                        path.unlink()
                    result = self.invoke(script)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn('ORIGINAL_CMD:preserved:preload=/existing-one.so:/existing-two.so',
                                  result.stdout)
                    self.assertNotIn('ld.so', result.stderr)
                    path.write_bytes(original)

    def test_launcher_rejects_ambiguous_or_already_modified_entrypoint(self):
        hashes = {'/voice/lib.so': 'a'*64}
        for before in ('#!/bin/bash\ntrue\n', self.ORIGINAL+'eval "$cmd"\n'):
            with self.subTest(before=before), self.assertRaises(ValueError):
                prepare.launcher_with_voice(before, hashes, '/voice/lib.so')
        after = prepare.launcher_with_voice(self.ORIGINAL, hashes, '/voice/lib.so')
        with self.assertRaises(ValueError):
            prepare.launcher_with_voice(after, hashes, '/voice/lib.so')

    def test_unpinned_library_cannot_be_preloaded(self):
        with self.assertRaises(ValueError):
            prepare.launcher_with_voice(self.ORIGINAL, {'/voice/file.wav': 'b'*64}, '/voice/lib.so')


class RollbackTests(unittest.TestCase):
    def fixture(self, root):
        payload = root/'payload'; payload.mkdir()
        entry = root/'entrypoint.sh'
        entry.write_bytes(LauncherTests.ORIGINAL.encode())
        entry.chmod(0o751)
        os.utime(entry, ns=(1_000_000_000, 2_000_000_000))
        paths = [root/'voice-es.wav', root/'libvoice.so', entry]
        rows = []
        for index, path in enumerate(paths):
            new = ('installed-'+str(index)).encode()
            (payload/str(index)).write_bytes(new)
            rows.append(dict(container='speech-test', target=str(path),
                             before_sha256=digest(path.read_bytes()) if path.exists() else None,
                             after_sha256=digest(new), payload=str(index),
                             metadata=dict(mode=0o644, uid=os.getuid(), gid=os.getgid())))
        (root/'plan.json').write_text(json.dumps(rows))
        helper = root/'helper.py'; helper.write_text(HELPER)

        def run(mode):
            return subprocess.run([sys.executable, '-B', str(helper), str(root), 'speech-test', mode],
                                  capture_output=True, text=True, timeout=5)
        return paths, rows, run

    def test_rollback_restores_entrypoint_and_removes_only_new_voice_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths, rows, run = self.fixture(root)
            for mode in ('check', 'apply', 'rollback'):
                result = run(mode)
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(paths[0].exists())
            self.assertFalse(paths[1].exists())
            self.assertEqual(paths[2].read_bytes(), LauncherTests.ORIGINAL.encode())
            self.assertEqual(paths[2].stat().st_mode & 0o7777, 0o751)
            self.assertEqual(paths[2].stat().st_mtime_ns, 2_000_000_000)
            self.assertEqual(run('rollback').returncode, 0)

    def test_rollback_stops_on_later_changes_and_keeps_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths, rows, run = self.fixture(root)
            self.assertEqual(run('apply').returncode, 0)
            paths[2].write_bytes(b'operator change after installation')
            result = run('rollback')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('ROLLBACK_CONFLICT', result.stderr)
            self.assertEqual(paths[2].read_bytes(), b'operator change after installation')
            self.assertTrue(all(path.exists() for path in paths))
            self.assertEqual((root/'before'/'2').read_bytes(), LauncherTests.ORIGINAL.encode())
            self.assertTrue((root/'receipts'/'speech-test.json').exists())
            paths[2].write_bytes(b'installed-2')
            self.assertEqual(run('rollback').returncode, 0)

    def test_rollback_handles_interruption_after_rename_before_verified_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths, rows, run = self.fixture(root)
            self.assertEqual(run('apply').returncode, 0)
            journal = root/'receipts'/'speech-test.json'
            recorded = json.loads(journal.read_text())
            # Recorded intent + installed bytes is the state after atomic
            # rename and before the final receipt update reaches disk.
            recorded[-1].pop('verified')
            self.assertTrue(recorded[-1]['intent'])
            journal.write_text(json.dumps(recorded))
            self.assertEqual(run('rollback').returncode, 0)
            self.assertEqual(paths[2].read_bytes(), LauncherTests.ORIGINAL.encode())
            self.assertFalse(paths[0].exists())
            self.assertFalse(paths[1].exists())


if __name__ == '__main__':
    unittest.main()
