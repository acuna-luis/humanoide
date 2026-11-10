import platform
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).with_name('verify_evdev_wheel.sh')


class VerifyGuardTests(unittest.TestCase):
    def test_help_and_isolation(self):
        run = subprocess.run(['bash', str(SCRIPT), '--help'], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0)
        source = SCRIPT.read_text(encoding='utf-8')
        for required in ('--network none', '--read-only', '--cap-drop ALL',
                         '--security-opt no-new-privileges', 'nodev,exec',
                         'cruzr.evdev.owner', 'sha256sum'):
            self.assertIn(required, source)

    @unittest.skipIf(platform.machine() == 'aarch64', 'only checks non-ARM rejection')
    def test_non_arm_rejects_before_container(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'evdev-2.0.0-cp312-cp312-linux_aarch64.whl'
            path.write_bytes(b'wheel')
            import hashlib
            digest = hashlib.sha256(b'wheel').hexdigest()
            run = subprocess.run(['bash', str(SCRIPT), '--verify', str(path), digest],
                                 capture_output=True, text=True)
            self.assertNotEqual(run.returncode, 0)
            self.assertNotIn('Temporary container:', run.stderr)


if __name__ == '__main__':
    unittest.main()
