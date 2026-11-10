"""Tests for staging and verification, without network or robot."""

import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import prepare_arm64_cpu_wheelhouse as prep


class StageTests(unittest.TestCase):
    def test_check_rejects_missing_corruption_and_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            body = b'fixture'
            expected = hashlib.sha256(body).hexdigest()
            fake = {'artifact.whl': ('example', '1', expected)}
            with patch.object(prep, 'ARTIFACTS', fake):
                self.assertEqual(len(prep.check(root)), 1)
                (root / 'artifact.whl').write_bytes(body)
                self.assertEqual(prep.check(root), [])
                (root / 'artifact.whl').write_bytes(b'corrupt')
                self.assertIn('sha256 mismatch', prep.check(root)[0])
                (root / 'artifact.whl').unlink()
                (root / 'target').write_bytes(body)
                (root / 'artifact.whl').symlink_to(root / 'target')
                self.assertIn('symlink', prep.check(root)[0])

    def test_existing_directory_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'keep').write_text('unchanged')
            with self.assertRaises(FileExistsError):
                prep.download(root)
            self.assertEqual((root / 'keep').read_text(), 'unchanged')

    def test_check_is_offline(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(prep.urllib.request, 'urlopen', side_effect=AssertionError('network')):
                self.assertEqual(prep.main(['--check', '--output', tmp]), 1)


if __name__ == '__main__':
    unittest.main()
