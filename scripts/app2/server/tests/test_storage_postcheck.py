"""Post-firmware safety tests, plus a local disposable ext4 read-only check."""
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

SPEC = importlib.util.spec_from_file_location("storage_postcheck",
    Path(__file__).resolve().parents[1] / "storage_postcheck.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class StoragePostcheckTests(unittest.TestCase):
    def setUp(self):
        self.source = {"name": "/dev/nvme7n1p1", "maj:min": "259:7"}
        self.base = SimpleNamespace(DATA_SERIAL="S7DRNJ0X107187F", OS_SERIAL="S7DRNJ0X107095A",
            UUID="known-data-uuid", preflight=Mock(return_value=(self.source, 0)),
            command=Mock(return_value="UUID=known-data-uuid\nTYPE=ext4\n"))
        self.rows = [{"controller": "nvme7", "serial": self.base.DATA_SERIAL,
                      "firmware_rev": "8B2QJXD7", "state": "live"},
                     {"controller": "nvme8", "serial": self.base.OS_SERIAL,
                      "firmware_rev": "4B2QJXD7", "state": "live"}]

    def test_wrong_missing_duplicate_firmware_and_controller_identity_rejected(self):
        for change in ("serial", "duplicate", "firmware", "dead", "partition"):
            rows = [dict(row) for row in self.rows]
            source = dict(self.source)
            if change == "serial":
                rows[0]["serial"] = "wrong"
            elif change == "duplicate":
                rows.append(dict(rows[0]))
            elif change == "firmware":
                rows[0]["firmware_rev"] = "4B2QJXD7"
            elif change == "dead":
                rows[0]["state"] = "dead"
            else:
                source["name"] = "/dev/nvme8n1p1"
            with self.subTest(change=change), self.assertRaises(ValueError):
                M.validate_controllers(rows, source, self.base)

    def test_mounted_source_preflight_blocks_all_raw_diagnostics(self):
        self.base.preflight.side_effect = ValueError("Source has an existing mount")
        with patch.object(M.os, "geteuid", return_value=0), patch.object(M, "query") as query:
            with self.assertRaisesRegex(ValueError, "existing mount"):
                M.collect({}, True, self.base)
        query.assert_not_called()
        self.base.command.assert_not_called()

    def test_raw_uuid_probe_mismatch_blocks_smart_and_filesystem_check(self):
        self.base.command.return_value = "UUID=another-disk\nTYPE=ext4\n"
        with patch.object(M.os, "geteuid", return_value=0), \
             patch.object(M, "controllers", return_value=self.rows), patch.object(M, "query") as query:
            with self.assertRaisesRegex(ValueError, "UUID/type"):
                M.collect({}, True, self.base)
        query.assert_not_called()

    def test_only_explicit_option_adds_exact_readonly_fsck_command_and_rechecks(self):
        for enabled in (False, True):
            calls = []
            def query(argv, timeout=30):
                calls.append((argv, timeout))
                return {"argv": argv, "rc": 0, "stdout": "", "stderr": "",
                        "json": {"critical_warning": 0, "media_errors": 0}}
            with self.subTest(enabled=enabled), patch.object(M.os, "geteuid", return_value=0), \
                 patch.object(M, "controllers", return_value=self.rows), patch.object(M, "query", query):
                report = {}
                self.base.preflight.reset_mock()
                self.assertEqual(M.collect(report, enabled, self.base), 0)
                self.assertEqual(self.base.preflight.call_count, 3 if enabled else 2)
            self.assertEqual({argv[0] for argv, _ in calls},
                             {"nvme", "journalctl", "e2fsck"} if enabled else {"nvme", "journalctl"})
            fsck = [(argv, timeout) for argv, timeout in calls if argv[0] == "e2fsck"]
            self.assertEqual(fsck, [(["e2fsck", "-f", "-n", "/dev/nvme7n1p1"], 300)] if enabled else [])
            self.assertEqual([argv[2] for argv, _ in calls if argv[:2] == ["nvme", "smart-log"]],
                             ["/dev/nvme7", "/dev/nvme8"])

    def test_mount_appearing_before_fsck_prevents_fsck(self):
        self.base.preflight.side_effect = [(self.source, 0), ValueError("new external mount")]
        q = Mock(side_effect=lambda argv, **kw: {"argv": argv, "rc": 0, "stdout": "", "stderr": "",
            "json": {"critical_warning": 0, "media_errors": 0}})
        with patch.object(M.os, "geteuid", return_value=0), \
             patch.object(M, "controllers", return_value=self.rows), patch.object(M, "query", q):
            with self.assertRaisesRegex(ValueError, "external mount"):
                M.collect({}, True, self.base)
        self.assertFalse(any(call.args[0][0] == "e2fsck" for call in q.call_args_list))

    def test_uncorrected_filesystem_errors_are_reported_without_retry_or_repair(self):
        calls = []
        def query(argv, timeout=30):
            calls.append(argv)
            return {"argv": argv, "rc": 4 if argv[0] == "e2fsck" else 0,
                    "stdout": "Errors left uncorrected", "stderr": "",
                    "json": {"critical_warning": 0, "media_errors": 0}}
        with patch.object(M.os, "geteuid", return_value=0), \
             patch.object(M, "controllers", return_value=self.rows), patch.object(M, "query", query):
            report = {}
            self.assertEqual(M.collect(report, True, self.base), 1)
        self.assertEqual(report["status"], "FILESYSTEM_REVIEW_REQUIRED")
        self.assertEqual(report["filesystem_check"]["rc"], 4)
        self.assertEqual(sum(argv[0] == "e2fsck" for argv in calls), 1)
        self.assertEqual(report["final_guard"], "PASS_IDENTIFIED_UNMOUNTED_MASKED_INACTIVE")

    def test_real_rc0_with_skipped_journal_and_wrong_counts_requires_review_without_rewriting_output(self):
        # Actual 2026-10-20 e2fsck 1.47.0 result: rc0 was not a clean-filesystem proof.
        stdout = ("Warning: skipping journal recovery because doing a read-only filesystem check.\n"
            "Pass 1: Checking inodes, blocks, and sizes\n"
            "Pass 2: Checking directory structure\n"
            "Pass 3: Checking directory connectivity\n"
            "Pass 4: Checking reference counts\n"
            "Pass 5: Checking group summary information\n"
            "Free blocks count wrong (463783574, counted=463807698).\nFix? no\n\n"
            "Free inodes count wrong (121891505, counted=121917075).\nFix? no\n\n"
            "dockerdata: 210255/122101760 files (0.2% non-contiguous), 24594794/488378368 blocks\n")
        stderr = "e2fsck 1.47.0 (5-Feb-2023)\n"
        calls = []
        def query(argv, timeout=30):
            calls.append(argv)
            return {"argv": argv, "rc": 0, "stdout": stdout if argv[0] == "e2fsck" else "",
                    "stderr": stderr if argv[0] == "e2fsck" else "",
                    "json": {"critical_warning": 0, "media_errors": 0}}
        with patch.object(M.os, "geteuid", return_value=0), \
             patch.object(M, "controllers", return_value=self.rows), patch.object(M, "query", query):
            report = {}
            self.assertEqual(M.collect(report, True, self.base), 1)
        result = report["filesystem_check"]
        self.assertEqual((result["rc"], result["stdout"], result["stderr"]), (0, stdout, stderr))
        self.assertEqual(result["review_reasons"],
                         ["JOURNAL_RECOVERY_NOT_APPLIED", "UNRESOLVED_FILESYSTEM_DIAGNOSTIC"])
        self.assertEqual(result["interpretation"], "JOURNAL_OR_FILESYSTEM_REVIEW_REQUIRED_READ_ONLY")
        self.assertEqual(report["status"], "FILESYSTEM_REVIEW_REQUIRED")
        self.assertEqual(sum(argv[0] == "e2fsck" for argv in calls), 1)

    def test_rc0_alone_does_not_hide_journal_or_unfixed_diagnostics(self):
        for message in ("needs-recovery flag set", "Journal recovery was omitted",
                        "Unfixed filesystem problems", "Free inodes count wrong"):
            with self.subTest(message=message):
                self.assertEqual(M.fsck_status({"rc": 0, "stdout": message, "stderr": ""})[1], 1)

    def test_incomplete_queries_or_unsafe_smart_skip_fsck_with_complete_report(self):
        for bad in ("warning", "media", "unknown_counter", "bad_json", "error_log", "kernel"):
            calls = []
            def query(argv, timeout=30):
                calls.append(argv)
                result = {"argv": argv, "rc": 0, "stdout": "kept", "stderr": "",
                          "json": {"critical_warning": 0, "media_errors": 0}}
                if argv[:3] == ["nvme", "smart-log", "/dev/nvme7"]:
                    if bad == "warning":
                        result["json"]["critical_warning"] = 1
                    elif bad == "media":
                        result["json"]["media_errors"] = 3
                    elif bad == "unknown_counter":
                        result["json"].pop("media_errors")
                    elif bad == "bad_json":
                        result["json"] = ["not a SMART object"]
                if bad == "error_log" and argv[:2] == ["nvme", "error-log"]:
                    result["rc"] = 1
                if bad == "kernel" and argv[0] == "journalctl":
                    result.update(rc=None, error="TIMEOUT")
                return result
            with self.subTest(bad=bad), patch.object(M.os, "geteuid", return_value=0), \
                 patch.object(M, "controllers", return_value=self.rows), patch.object(M, "query", query):
                report = {}
                self.assertEqual(M.collect(report, True, self.base), 2)
                self.assertTrue(report["filesystem_check"]["skipped"])
                self.assertTrue(report["filesystem_check"]["reasons"])
                self.assertEqual(len(report["queries"]), 5)
                self.assertFalse(any(argv[0] == "e2fsck" for argv in calls))

    def test_smart_zero_must_be_interpretable_integer_not_boolean_or_float(self):
        for value, expected in ((0, True), ("0x00", True), ("0000", True),
                                (True, False), (0.0, False), (None, False), ("0?", False)):
            row = {"argv": ["nvme", "smart-log", "/dev/nvme7"], "serial": self.base.DATA_SERIAL,
                   "rc": 0, "json": {"critical_warning": value, "media_errors": 0}}
            with self.subTest(value=value):
                self.assertEqual(M.filesystem_gate([row], self.base.DATA_SERIAL)["eligible"], expected)

    def test_fsck_exit_codes_preserve_uncorrected_vs_failed_and_unexpected_write_bits(self):
        for rc, expected in ((0, 0), (4, 1), (1, 2), (2, 2), (8, 2), (12, 2), (32, 2), (128, 2)):
            with self.subTest(rc=rc):
                self.assertEqual(M.fsck_status({"rc": rc})[1], expected)
        self.assertEqual(M.fsck_status({"rc": None, "error": "TIMEOUT"})[1], 2)

    def test_timeout_retains_partial_output_and_uses_no_shell_or_stdin(self):
        argv = ["e2fsck", "-f", "-n", "/dev/nvme7n1p1"]
        error = subprocess.TimeoutExpired(argv, 300, output=b"Pass 1\n", stderr=b"interrupted\n")
        with patch.object(M.subprocess, "run", side_effect=error) as run:
            result = M.query(argv, timeout=300)
        self.assertIsNone(result["rc"])
        self.assertEqual(result["error"], "TIMEOUT")
        self.assertEqual(result["stdout"], "Pass 1\n")
        self.assertIs(run.call_args.kwargs["stdin"], subprocess.DEVNULL)
        self.assertNotIn("shell", run.call_args.kwargs)
        self.assertEqual(run.call_args.kwargs["env"], {"PATH": M.SAFE_PATH, "LC_ALL": "C"})

    def test_tampered_or_symlink_dependency_is_never_executed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "storage_rescue.py"
            path.write_text("raise RuntimeError('must never be imported')\n")
            with self.assertRaises(ValueError):
                M.load_rescue(path)
            link = Path(directory) / "link.py"
            link.symlink_to(path)
            with self.assertRaises(ValueError):
                M.load_rescue(link)

    def test_nonroot_json_report_fails_before_loading_dependency(self):
        out = io.StringIO()
        with patch.object(M.os, "geteuid", return_value=1000), patch.object(M, "load_rescue") as load, \
             redirect_stdout(out):
            self.assertEqual(M.main([]), 2)
        self.assertEqual(json.loads(out.getvalue())["error_type"], "PermissionError")
        load.assert_not_called()

    @unittest.skipUnless(shutil.which("mke2fs") and shutil.which("e2fsck"), "e2fsprogs not installed")
    def test_real_disposable_ext4_readonly_check_leaves_every_byte_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "disposable.ext4"
            with image.open("wb") as stream:
                stream.truncate(32 * 1024 ** 2)
            subprocess.run([shutil.which("mke2fs"), "-q", "-t", "ext4", "-F", str(image)],
                           check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            before = hashlib.sha256(image.read_bytes()).hexdigest()
            result = M.query([shutil.which("e2fsck"), "-f", "-n", str(image)])
            self.assertEqual(result["rc"], 0, result)
            self.assertEqual(hashlib.sha256(image.read_bytes()).hexdigest(), before)


if __name__ == "__main__":
    unittest.main()
