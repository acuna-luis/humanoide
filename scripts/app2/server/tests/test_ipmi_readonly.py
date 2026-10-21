"""Offline command guards; optional static private-bundle inspection.

Set APP2_IPMI_BUNDLE to the reviewed tar.gz to run its checksum test as well.
These tests never execute ipmitool, its loader, a package script or a BMC call.
"""
import contextlib
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("ipmi_readonly",
    Path(__file__).resolve().parents[1] / "ipmi_readonly.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
BUNDLE = os.environ.get("APP2_IPMI_BUNDLE")


class IPMIReadonlyTests(unittest.TestCase):
    def test_exact_five_reads(self):
        cases = ((["--mc-info"], ["mc", "info"]),
                 (["--channel-info", "1"], ["channel", "info", "1"]),
                 (["--channel-info", "8"], ["channel", "info", "8"]),
                 (["--lan-print", "1"], ["lan", "print", "1"]),
                 (["--lan-print", "8"], ["lan", "print", "8"]))
        for argv, expected in cases:
            with self.subTest(argv=argv):
                self.assertEqual(M.readonly_args(M.arguments(argv)), expected)
                command = M.command_for(expected)
                self.assertEqual(command[:6], [str(M.LOADER), "--library-path",
                    str(M.BASE / "lib"), str(M.BASE / "bin/ipmitool"), "-I", "open"])
                self.assertEqual(command[6:8], ["-d", "0"])

    def test_all_extra_and_wrong_channels_rejected(self):
        cases = ([], ["--mc-info", "--lan-print", "1"], ["--channel-info", "0"],
                 ["--lan-print", "9"], ["--lan-set", "1"],
                 ["--mc-info", "-H", "1.2.3.4"], ["--mc-info", "--reset"],
                 ["--lan-print", "1", "user", "set", "password"])
        for argv in cases:
            with self.subTest(argv=argv), contextlib.redirect_stderr(io.StringIO()), \
                 self.assertRaises(SystemExit):
                M.arguments(argv)

    def test_direct_builder_rejects_writes(self):
        cases = (["mc", "reset", "cold"], ["lan", "set", "1", "ipaddr", "1.2.3.4"],
                 ["user", "set", "password", "2", "secret"], ["raw", "6", "2"],
                 ["mc", "info", ";", "id"], ["lan", "print", "2"])
        for args in cases:
            with self.subTest(args=args), self.assertRaises(ValueError):
                M.command_for(args)

    def test_check_no_subprocess(self):
        with patch.object(M, "preflight"), patch.object(M.subprocess, "run") as run, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(M.main(["--check"]), 0)
        run.assert_not_called()

    def test_failed_preflight_no_subprocess(self):
        with patch.object(M, "preflight", side_effect=ValueError("changed payload")), \
             patch.object(M.subprocess, "run") as run, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(M.main(["--mc-info"]), 1)
        run.assert_not_called()

    def test_read_query_uses_clean_env_timeout_no_stdin(self):
        result = subprocess.CompletedProcess([], 0,
            "SNMP Community String : secret\nIP Address : 10.0.0.1\n", "")
        with patch.object(M, "preflight"), patch.object(M.os, "geteuid", return_value=0), \
             patch.object(M.subprocess, "run", return_value=result) as run, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(M.main(["--lan-print", "1"]), 0)
        self.assertNotIn("secret", output.getvalue())
        self.assertIn("10.0.0.1", output.getvalue())
        self.assertEqual(run.call_args.kwargs["env"], {
            "PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C", "LC_ALL": "C"})
        self.assertEqual(run.call_args.kwargs["timeout"], 15)
        self.assertIs(run.call_args.kwargs["stdin"], subprocess.DEVNULL)

    def test_nonroot_query_no_subprocess(self):
        with patch.object(M, "preflight"), patch.object(M.os, "geteuid", return_value=1001), \
             patch.object(M.subprocess, "run") as run, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(M.main(["--mc-info"]), 1)
        run.assert_not_called()

    @unittest.skipUnless(BUNDLE and Path(BUNDLE).is_file(), "Set APP2_IPMI_BUNDLE for private payload")
    def test_minimal_archive_and_hashes(self):
        with tarfile.open(BUNDLE, "r:gz") as archive:
            names = archive.getnames()
            self.assertTrue(all(not name.startswith("/") and ".." not in Path(name).parts
                                for name in names))
            self.assertTrue(all(member.isdir() or member.isfile()
                                for member in archive.getmembers()))
            self.assertFalse(any("/ipmievd" in name or name.endswith(".service") or
                                 "/init.d/" in name for name in names))
            for relative, expected in M.PAYLOAD.items():
                data = archive.extractfile("ipmi-readonly-tools/" + relative).read()
                self.assertEqual(hashlib.sha256(data).hexdigest(), expected)

    def test_changed_payload_checksum_rejected_before_loading(self):
        # Exercise the actual preflight checksum branch without needing Ubuntu
        # binaries, aisrv, privileged ownership or the physical IPMI device.
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "bin").mkdir(mode=0o700)
            (root / "lib").mkdir(mode=0o700)
            (root / "bin/ipmitool").write_bytes(b"altered payload")
            (root / "lib/libfreeipmi.so.17").write_bytes(b"altered library")
            with patch.object(M, "BASE", root), \
                 patch.object(M, "__file__", str(root / "ipmi_readonly.py")), \
                 patch.object(M.platform, "node", return_value="aisrv"), \
                 patch.object(M.platform, "machine", return_value="x86_64"), \
                 patch.object(M, "trusted_regular"), patch.object(M.subprocess, "run") as run, \
                 self.assertRaisesRegex(ValueError, "checksum mismatch"):
                M.preflight()
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
