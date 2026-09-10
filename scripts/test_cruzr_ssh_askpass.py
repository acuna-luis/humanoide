"""Autenticación local con valores ficticios; no conecta con el robot."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts/lib/cruzr_ssh_askpass.py"
SCRIPTS = (
    "scripts/cruzr_blue_workbin_cycle.sh",
    "scripts/teleoperation/cruzr_pico_to_home_owner.sh",
    "scripts/vla/audit_vla_live_preflight_e6_0g.sh",
)


class AskpassTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "password"
        self.env = dict(os.environ)
        self.env.pop("CRUZR_SSH_PASSWORD", None)
        self.env.pop("CRUZR_INTERNAL_ASKPASS", None)
        self.env["CRUZR_SSH_PASSWORD_FILE"] = str(self.path)

    def write_secret(self, value=b"test-only-value\n", mode=0o600):
        self.path.write_bytes(value)
        self.path.chmod(mode)

    def run_helper(self):
        return subprocess.run([sys.executable, str(HELPER)], env=self.env,
                              capture_output=True, text=True, timeout=5)

    def assert_rejected(self):
        result = self.run_helper()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertNotIn("test-only-value", result.stderr)

    def test_private_file_preserves_spaces(self):
        self.write_secret(b" test-only-value \n")
        result = self.run_helper()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, " test-only-value \n")
        self.assertEqual(result.stderr, "")

    def test_environment_has_priority(self):
        self.env["CRUZR_SSH_PASSWORD"] = "env-test-only"
        result = self.run_helper()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "env-test-only\n")

    def test_missing_and_public_files_rejected(self):
        self.assert_rejected()
        self.write_secret(mode=0o644)
        self.assert_rejected()

    def test_invalid_contents_rejected(self):
        for value in (b"", b"\n", b"test-only-value\n\n", b"test-only-value\r\n",
                      b"test-only-value\0", b"\xff", b"x" * 4097):
            with self.subTest(length=len(value)):
                self.write_secret(value)
                self.assert_rejected()

    def test_symlink_and_fifo_rejected(self):
        target = self.path.with_name("target")
        target.write_text("test-only-value")
        target.chmod(0o600)
        self.path.symlink_to(target)
        self.assert_rejected()
        self.path.unlink()
        os.mkfifo(self.path, mode=0o600)
        self.assert_rejected()

    def test_invalid_environment_is_not_silently_replaced(self):
        self.write_secret()
        self.env["CRUZR_SSH_PASSWORD"] = "test-only-value\n"
        self.assert_rejected()

    def test_script_askpass_branches(self):
        self.write_secret()
        self.env["CRUZR_INTERNAL_ASKPASS"] = "1"
        for script in SCRIPTS:
            with self.subTest(script=script):
                result = subprocess.run(["bash", str(ROOT / script)], env=self.env,
                                        capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "test-only-value\n")
                self.assertEqual(result.stderr, "")

    def test_help_needs_no_credential(self):
        for script in SCRIPTS:
            with self.subTest(script=script):
                result = subprocess.run(["bash", str(ROOT / script), "--help"],
                                        env=self.env, capture_output=True, text=True,
                                        timeout=5)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("Uso:", result.stdout)


if __name__ == "__main__":
    unittest.main()
