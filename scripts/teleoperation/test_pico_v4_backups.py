"""Migration must reject unfinished or corrupted external backups."""
import hashlib
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from scripts.teleoperation.verify_pico_v4_backups import verify_backup


class BackupVerificationTest(unittest.TestCase):
    def archive(self, directory, *, status=b'CAPTURED_REVIEW_COVERAGE\n', corrupt=False):
        path = Path(directory)/'backup.tar'
        files = {'STATUS':status, 'failures.txt':b'', 'configuration.tar.gz':b'private data'}
        manifest = ''.join(hashlib.sha256(value).hexdigest()+'  ./'+key+'\n'
                           for key,value in files.items()).encode()
        if corrupt:
            files['configuration.tar.gz'] = b'truncated'
        files['SHA256SUMS'] = manifest
        with tarfile.open(path,'w') as archive:
            for key,value in files.items():
                info=tarfile.TarInfo('backup/'+key); info.size=len(value)
                archive.addfile(info,io.BytesIO(value))
        return path

    def test_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(verify_backup(self.archive(directory))['files'],3)

    def test_unfinished_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                verify_backup(self.archive(directory,status=b'IN_PROGRESS\n'))

    def test_corruption_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                verify_backup(self.archive(directory,corrupt=True))
