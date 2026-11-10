import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import check_wheelhouse_manifest as subject


class WheelManifestTests(unittest.TestCase):
    def test_exact_coverage_and_pins(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = b'wheel'
            digest = hashlib.sha256(data).hexdigest()
            (root / 'test.whl').write_bytes(data)
            (root / 'SHA256SUMS').write_text(f'{digest}  test.whl\n')
            with patch.object(subject, 'PINNED', {'test.whl': digest}):
                self.assertEqual(subject.check(root), 1)
                (root / 'unlisted.whl').write_bytes(data)
                with self.assertRaisesRegex(ValueError, 'cover'):
                    subject.check(root)
                (root / 'unlisted.whl').unlink()
                (root / 'test.whl').write_bytes(b'tampered')
                with self.assertRaisesRegex(ValueError, 'digest'):
                    subject.check(root)

    def test_duplicate_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = b'wheel'
            digest = hashlib.sha256(data).hexdigest()
            (root / 'test.whl').write_bytes(data)
            with patch.object(subject, 'PINNED', {'test.whl': digest}):
                (root / 'SHA256SUMS').write_text(f'{digest}  test.whl\n{digest}  test.whl\n')
                with self.assertRaisesRegex(ValueError, 'duplicate'):
                    subject.check(root)
                (root / 'SHA256SUMS').write_text(f'{digest}  test.whl\n')
                (root / 'test.whl').unlink()
                (root / 'test.whl').symlink_to('/dev/null')
                with self.assertRaisesRegex(ValueError, 'symlink'):
                    subject.check(root)


if __name__ == '__main__':
    unittest.main()
