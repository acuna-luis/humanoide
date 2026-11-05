"""Offline checks for non-moving v4 derivative preparation."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts.teleoperation import prepare_pico_v4_geometric_replay as prepare


class PrepareTests(unittest.TestCase):
    def test_staging_paths_do_not_collide_with_shared_tmp(self):
        scratch, host, app = prepare.staging_paths('capture_10', 'run_1')
        self.assertNotEqual(scratch, app)
        self.assertEqual(host, '/home/walker/grabaciones_v4_completas/capture_10/derived_run_1')
        # Model /tmp bind-mounted into both containers: both mkdirs must succeed
        # exclusively without ever falling back to an existing directory.
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / Path(scratch).name).mkdir()
            (Path(directory) / Path(app).name).mkdir()
            with self.assertRaises(FileExistsError):
                (Path(directory) / Path(app).name).mkdir()

    def test_running_container_must_be_unique(self):
        pattern = r'walker-ros\.ros2-\d+'
        self.assertEqual(prepare.one_container('walker-ros.ros2-1\nother\n', pattern),
                         'walker-ros.ros2-1')
        for inventory in ('other\n', 'walker-ros.ros2-1\nwalker-ros.ros2-2\n'):
            with self.subTest(inventory=inventory), self.assertRaises(ValueError):
                prepare.one_container(inventory, pattern)

    def test_digest_mismatch_fails_closed(self):
        self.assertEqual(prepare.checked_hash('a' * 64 + '  path\n', 'a' * 64, 'test'), 'a' * 64)
        for value in ('', 'b' * 64 + '  path'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                prepare.checked_hash(value, 'a' * 64, 'test')

    def test_helper_preserves_literal_arguments(self):
        source = b'import json,sys;print(json.dumps(sys.argv[1:]))'
        arguments = ['one space', '$(exit 91)', "quote'and;chars"]
        command = 'source() { :; }; ' + prepare.helper_command(source, arguments)
        result = subprocess.run(['bash', '-c', command], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), arguments)

    def test_pc_copy_is_exclusive_and_hash_checked(self):
        content = b'trajectory bytes'
        digest = hashlib.sha256(content).hexdigest()
        def fake_run(*args, **kwargs):
            kwargs['stdout'].write(content)
            return subprocess.CompletedProcess(args[0], 0)
        with tempfile.TemporaryDirectory() as directory, patch.object(prepare.subprocess, 'run', fake_run):
            destination = Path(directory) / 'new.motion'
            prepare.copy_remote_file_to_pc('safe-container', '/tmp/input', destination, digest)
            self.assertEqual(destination.read_bytes(), content)
            with self.assertRaises(FileExistsError):
                prepare.copy_remote_file_to_pc('safe-container', '/tmp/input', destination, digest)
            with self.assertRaises(ValueError):
                prepare.copy_remote_file_to_pc('safe-container', '/tmp/input', Path(directory) / 'other', '0' * 64)

    def test_invalid_arguments_rejected_before_remote_access(self):
        script = str(Path(prepare.__file__))
        for args in (['--capture', '../bad', '--sha256', 'a' * 64],
                     ['--capture', 'good', '--sha256', 'incorrect'],
                     ['--capture', 'good', '--sha256', 'a' * 64, '--time-scale', '1']):
            with self.subTest(args=args):
                result = subprocess.run(['python3', script, *args], capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertNotIn('EVIDENCIA=', result.stdout)


if __name__ == '__main__':
    unittest.main()
