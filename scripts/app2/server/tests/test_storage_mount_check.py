"""Material read-only gates before reactivating Docker; no real mounts/services."""
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("storage_mount_check",
    Path(__file__).resolve().parents[1] / "storage_mount_check.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class MountCheckTests(unittest.TestCase):
    def fixture(self, root):
        def no_symlinks(path):
            if any(item.is_symlink() for item in (path, *path.parents)):
                raise ValueError("Symlink")
        base = SimpleNamespace(UUID="known-uuid", DATA_SERIAL="known-serial", no_symlink_path=no_symlinks)
        names = ["volume%02d" % number for number in range(20)]
        receipt = root / "receipt.json"
        receipt.write_text(json.dumps({"source_uuid": base.UUID, "source_serial": base.DATA_SERIAL,
            "all_named_volumes_archived_and_compared": True, "inventory": {"volumes": dict.fromkeys(names, {})}}))
        target = root / "docker"
        for name in ("containers", "overlay2", "volumes"):
            (target / name).mkdir(parents=True)
        for name in names:
            (target / "volumes" / name / "_data").mkdir(parents=True)
        return base, target, receipt, hashlib.sha256(receipt.read_bytes()).hexdigest()

    def test_mount_must_be_exact_rw_data_device_and_never_root(self):
        source = {"maj:min": "259:1"}
        row = {"device": "259:1", "type": "ext4", "options": {"rw"}, "fsoptions": {"rw"}}
        M.validate_mount(source, "259:2", [row], "259:1")
        for rows, device in (([], "259:1"), ([row, row], "259:1"), ([row], "259:2"),
                ([{**row, "options": {"ro"}}], "259:1"),
                ([{**row, "device": "259:9"}], "259:1")):
            with self.subTest(rows=rows, device=device), self.assertRaises(ValueError):
                M.validate_mount(source, "259:2", rows, device)

    def test_expected_twenty_volume_tree_passes_and_missing_volume_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base, target, receipt, digest = self.fixture(root)
            with patch.object(M, "RECEIPT_SHA", digest):
                self.assertEqual(M.validate_tree(base, target.stat().st_dev, target, receipt), 20)
                (target / "volumes" / "volume00" / "_data").rmdir()
                with self.assertRaises(OSError):
                    M.validate_tree(base, target.stat().st_dev, target, receipt)

    def test_tampered_receipt_and_symlink_data_block(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base, target, receipt, digest = self.fixture(root)
            with patch.object(M, "RECEIPT_SHA", digest):
                original = receipt.read_bytes()
                receipt.write_bytes(original + b" ")
                with self.assertRaisesRegex(ValueError, "checksum"):
                    M.validate_tree(base, target.stat().st_dev, target, receipt)
                receipt.write_bytes(original)
                data = target / "volumes" / "volume00" / "_data"
                data.rmdir()
                data.symlink_to(target / "volumes" / "volume01" / "_data", target_is_directory=True)
                with self.assertRaisesRegex(ValueError, "Symlink"):
                    M.validate_tree(base, target.stat().st_dev, target, receipt)

    def test_help_runs_without_root_or_queries_and_real_check_requires_root(self):
        with patch.object(M.os, "geteuid", return_value=1000), \
                patch.object(M.socket, "gethostname", side_effect=AssertionError("No queries expected")), \
                redirect_stdout(io.StringIO()) as output:
            with self.assertRaises(SystemExit) as exit_status:
                M.main(["--help"])
            self.assertEqual(exit_status.exception.code, 0)
            self.assertIn("--check", output.getvalue())
            with self.assertRaises(PermissionError):
                M.main(["--check"])


if __name__ == "__main__":
    unittest.main()
