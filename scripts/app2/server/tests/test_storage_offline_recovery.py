"""Safety guards, inherited-lock behavior and disposable ext4 recovery only."""
from contextlib import contextmanager, redirect_stdout
import fcntl
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

SPEC = importlib.util.spec_from_file_location("storage_offline_recovery",
    Path(__file__).resolve().parents[1] / "storage_offline_recovery.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
POST = M.pinned_module("storage_postcheck", M.POST_SHA)

HEADER = ("Filesystem features: has_journal needs_recovery extent metadata_csum\n"
          "Block size: 4096\nJournal inode: 8\nTotal journal blocks: 262144\n")
KNOWN = ("Warning: skipping journal recovery because doing a read-only filesystem check.\n"
         "Free blocks count wrong (1, counted=2).\nFix? no\n"
         "Free inodes count wrong (3, counted=4).\nFix? no\n")


class OfflineRecoveryTests(unittest.TestCase):
    def fixture(self):
        source = {"name": "/dev/nvme7n1p1", "maj:min": "259:7"}
        fsck = {"rc": 0, "stdout": KNOWN, "stderr": "e2fsck 1.47.0\n"}
        queries = []
        for serial in ("known-os", "known"):
            queries += [{"argv": ["nvme", "smart-log", "/dev/example"], "serial": serial, "rc": 0,
                "json": {"critical_warning": 0, "media_errors": 0, "num_err_log_entries": 0,
                         "unsafe_shutdowns": 35, "power_cycles": 17}},
                {"argv": ["nvme", "error-log", "/dev/example"], "serial": serial, "rc": 0,
                 "json": {"errors": [{"error_count": 0}]}}]
        queries.append({"argv": ["journalctl"], "rc": 0, "stdout": "known boot message\n"})
        prior = {"boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(), "queries": copy.deepcopy(queries),
                 "source": source, "storage_rescue_sha256": M.BASE_SHA,
                 "guard": "PASS_IDENTIFIED_UNMOUNTED_MASKED_INACTIVE",
                 "final_guard": "PASS_IDENTIFIED_UNMOUNTED_MASKED_INACTIVE", "filesystem_check": fsck}
        base = SimpleNamespace(preflight=Mock(return_value=(source, os.stat("/").st_dev)),
                               no_symlink_path=Mock(), DATA_SERIAL="known", OS_SERIAL="known-os", UUID="known")
        def collect(report, **kw):
            report.update(filesystem_check_gate={"eligible": True}, filesystem_check=dict(fsck), queries=copy.deepcopy(queries))
            return 1
        post = SimpleNamespace(collect=Mock(side_effect=collect),
            query=Mock(return_value={"rc": 0, "stdout": HEADER, "stderr": "dumpe2fs\n"}),
            filesystem_gate=POST.filesystem_gate,
            fsck_review_reasons=Mock(return_value=["JOURNAL_RECOVERY_NOT_APPLIED", "UNRESOLVED_FILESYSTEM_DIAGNOSTIC"]))
        return source, base, post, prior

    def test_unsafe_os_ssd_smart_blocks_before_snapshot_or_header(self):
        _, base, post, prior = self.fixture()
        original = post.collect.side_effect
        def changed(report, **kw):
            result = original(report, **kw)
            report["queries"][0]["json"]["media_errors"] = 1
            return result
        post.collect.side_effect = changed
        with patch.object(M.os, "geteuid", return_value=0), \
             patch.object(M, "read_pinned_json", return_value=(prior, b"")), \
             patch.object(M, "backup_receipts", return_value=[]):
            with self.assertRaisesRegex(ValueError, "OS SSD SMART"):
                M.prepare({}, base, post)
        post.query.assert_not_called()

    def test_prior_report_wrong_boot_or_source_blocks_before_fresh_scan(self):
        for change in ("boot", "source", "guard"):
            source, base, post, prior = self.fixture()
            if change == "boot":
                prior["boot_id"] = "different"
            elif change == "source":
                prior["source"] = {"name": "/dev/other", "maj:min": "1:1"}
            else:
                prior["final_guard"] = "FAILED"
            with self.subTest(change=change), patch.object(M.os, "geteuid", return_value=0), \
                 patch.object(M, "read_pinned_json", return_value=(prior, b"")):
                with self.assertRaises(ValueError):
                    M.prepare({}, base, post)
            post.collect.assert_not_called()

    def test_mounted_guard_blocks_before_report_or_raw_reads(self):
        _, base, post, _ = self.fixture()
        base.preflight.side_effect = ValueError("existing mount")
        with patch.object(M.os, "geteuid", return_value=0), patch.object(M, "read_pinned_json") as read:
            with self.assertRaisesRegex(ValueError, "existing mount"):
                M.prepare({}, base, post)
        read.assert_not_called()
        post.collect.assert_not_called()

    def test_altered_report_hash_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prior.json"
            path.write_text('{"altered":true}')
            base = SimpleNamespace(no_symlink_path=Mock())
            with self.assertRaisesRegex(ValueError, "SHA256"):
                M.read_pinned_json(path, "0" * 64, base)

    def test_new_readonly_diagnostic_blocks_before_header_and_recovery(self):
        _, base, post, prior = self.fixture()
        original = post.collect.side_effect
        def changed(report, **kw):
            original(report, **kw)
            report["filesystem_check"]["stdout"] = KNOWN + "New error\n"
            return 1
        post.collect.side_effect = changed
        with patch.object(M.os, "geteuid", return_value=0), \
             patch.object(M, "read_pinned_json", return_value=(prior, b"")), \
             patch.object(M, "backup_receipts", return_value=[]):
            with self.assertRaisesRegex(ValueError, "Fresh read-only"):
                M.prepare({}, base, post)
        post.query.assert_not_called()

    def test_new_ssd_errors_or_kernel_reset_block_but_osc_capability_message_does_not(self):
        for change in ("counter", "error_log", "kernel", "osc_capability"):
            _, base, post, prior = self.fixture()
            fresh = {}
            post.collect(fresh)
            if change == "counter":
                fresh["queries"][0]["json"]["num_err_log_entries"] = 1
            elif change == "error_log":
                fresh["queries"][1]["json"]["errors"][0]["error_count"] = 1
            elif change == "kernel":
                fresh["queries"][-1]["stdout"] += "nvme nvme0: controller is down; will reset\n"
            else:
                fresh["queries"][-1]["stdout"] += "_OSC: platform does not support [AER PCIeCapability]\n"
            with self.subTest(change=change):
                if change == "osc_capability":
                    self.assertEqual(M.diagnostic_delta(prior, fresh, base)["status"], "NO_NEW_INCIDENT_ERRORS")
                else:
                    with self.assertRaisesRegex(ValueError, "SSD counters"):
                        M.diagnostic_delta(prior, fresh, base)

    def test_internal_pending_journal_required_and_size_is_only_an_estimate(self):
        info = M.journal_header(HEADER)
        self.assertEqual(info["journal_bytes"], 1024 ** 3)
        self.assertIn("NOT_A_BOUND", info["estimate_limit"])
        for bad in (HEADER.replace("needs_recovery", ""), HEADER.replace("Journal inode: 8", "Journal inode: 0"),
                    HEADER + "Journal device: 0x0900\n", HEADER + "Journal UUID: aaaa-bbbb\n"):
            with self.subTest(header=bad), self.assertRaises(ValueError):
                M.journal_header(bad)

    def test_check_cli_creates_no_files_and_never_invokes_writer(self):
        @contextmanager
        def lock(*args):
            yield None
        with patch.object(M.os, "geteuid", return_value=0), \
             patch.object(M, "pinned_module", return_value=SimpleNamespace(SAFE_PATH=POST.SAFE_PATH)), \
             patch.object(M, "recovery_lock", lock), patch.object(M, "prepare"), \
             patch.object(M, "recover") as recover, patch.object(M, "save_bytes") as save, \
             patch.object(M.tempfile, "mkdtemp") as mkdir, redirect_stdout(io.StringIO()) as out:
            self.assertEqual(M.main(["--check"]), 0)
        recover.assert_not_called()
        save.assert_not_called()
        mkdir.assert_not_called()
        self.assertEqual(json.loads(out.getvalue())["status"], "CHECK_READY_NO_WRITES")

    def test_exact_preen_command_and_review_even_rc0_or_rc1(self):
        argv = M.recovery_argv({"name": "/dev/nvme7n1p1"}, Path("/root/private/undo"))
        self.assertEqual(argv, ["e2fsck", "-p", "-E", "nodiscard,fixes_only,no_optimize_extents", "-z",
                                "/root/private/undo", "/dev/nvme7n1p1"])
        for flag in ("-y", "-f", "-c", "journal_only"):
            self.assertNotIn(flag, argv)
        self.assertFalse(M.recovery_review({"rc": 1, "stdout": "recovering journal\nFILE SYSTEM WAS MODIFIED"}))
        for message in ("checksum mismatch", "I/O error", "corrupted", "Fix? no", "while recovering",
                        "recovering journal\nrecovering journal"):
            with self.subTest(message=message):
                self.assertTrue(M.recovery_review({"rc": 0, "stdout": message}))
        self.assertTrue(M.recovery_review({"rc": 4}))

    def test_rc4_or_suspicious_rc0_never_triggers_automatic_full_fs_postscan(self):
        for result in ({"rc": 4, "stdout": "preserve this"}, {"rc": 0, "stderr": "checksum error"},
                       {"rc": 2, "stdout": "reboot required"}):
            post = SimpleNamespace(collect=Mock(return_value=0))
            original = dict(result)
            _, review = M.post_recovery_check(result, "base", post)
            self.assertTrue(review)
            self.assertFalse(post.collect.call_args.kwargs["filesystem_check"])
            self.assertEqual(result, original)

    def test_writer_inherits_lock_has_no_wait_timeout_or_automatic_termination(self):
        with tempfile.TemporaryDirectory() as directory:
            process = Mock(pid=12345)
            process.wait.return_value = 4
            with patch.object(M.subprocess, "Popen", return_value=process) as start:
                result = M.write_once(["reviewed", "command"], Path(directory), 77)
            self.assertEqual(start.call_args.kwargs["pass_fds"], (77,))
            self.assertEqual(start.call_args.kwargs["stdin"], subprocess.DEVNULL)
            self.assertTrue(start.call_args.kwargs["start_new_session"])
            process.wait.assert_called_once_with()
            process.terminate.assert_not_called()
            process.kill.assert_not_called()
            self.assertEqual(result["rc"], 4)

    def test_real_flock_survives_parent_descriptor_close_until_inheriting_child_exits(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lock"
            fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(0.3)"], pass_fds=(fd,))
            os.close(fd)
            other = os.open(path, os.O_RDONLY)
            try:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
                child.wait(timeout=5)
                fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
            finally:
                os.close(other)
                child.wait(timeout=5)

    @unittest.skipUnless(all(shutil.which(name) for name in ("mke2fs", "debugfs", "e2fsck")), "e2fsprogs required")
    def test_real_disposable_ext4_counter_recovery_with_undo_and_readonly_postcheck(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image, undo = root / "disposable.ext4", root / "undo.e2undo"
            with image.open("wb") as stream:
                stream.truncate(32 * 1024 ** 2)
            subprocess.run(["mke2fs", "-q", "-t", "ext4", "-F", str(image)], check=True, capture_output=True)
            for command in ("set_super_value free_blocks_count 1", "set_super_value state 0"):
                subprocess.run(["debugfs", "-w", "-R", command, str(image)], check=True, capture_output=True)
            before = hashlib.sha256(image.read_bytes()).hexdigest()
            result = subprocess.run(M.recovery_argv({"name": str(image)}, undo), stdin=subprocess.DEVNULL,
                                    capture_output=True, text=True, timeout=30)
            self.assertIn(result.returncode, (0, 1), result.stdout + result.stderr)
            self.assertTrue(undo.is_file())
            self.assertGreater(undo.stat().st_size, 0)
            self.assertNotEqual(hashlib.sha256(image.read_bytes()).hexdigest(), before)
            after = subprocess.run(["e2fsck", "-f", "-n", str(image)], capture_output=True, text=True, timeout=30)
            self.assertEqual(after.returncode, 0, after.stdout + after.stderr)
            self.assertNotIn("wrong", after.stdout.lower())


if __name__ == "__main__":
    unittest.main()
