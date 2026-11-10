import platform
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).with_name('build_evdev_host_gcc.sh')


class BuildGuardTests(unittest.TestCase):
    def test_build_uses_tmp_venv_and_read_only_root(self):
        source = SCRIPT.read_text(encoding='utf-8')
        self.assertIn('--read-only', source)
        self.assertIn('python -m venv /tmp/build-venv', source)
        self.assertIn('/tmp/build-venv/bin/python -m pip install', source)
        self.assertNotIn('/usr/local/bin/python -m pip install', source)

    def test_help_does_not_create_output(self):
        result = subprocess.run(['bash', str(SCRIPT), '--help'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn('not yet run', result.stdout)

    @unittest.skipIf(platform.machine() == 'aarch64', 'only checks non-ARM host rejection')
    def test_non_arm_build_is_rejected_before_creating_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'output'
            result = subprocess.run(['bash', str(SCRIPT), '--build', tmp, str(output)],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
