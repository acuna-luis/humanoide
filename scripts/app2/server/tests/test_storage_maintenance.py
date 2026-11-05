"""Pure-function safeguards; never talks to systemd or modifies host files."""
import importlib.util
from pathlib import Path
import unittest

SOURCE_PATH = Path(__file__).resolve().parents[1] / "storage_maintenance.py"
SPEC = importlib.util.spec_from_file_location("storage_maintenance", SOURCE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class StorageMaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.entry = f"{MODULE.SOURCE}\t/var/lib/docker ext4 defaults,auto,rw,noatime 0 2 # SSD\n".encode()

    def test_changes_only_docker_options_and_pass_number(self):
        prefix = b"# operator comment\nUUID=os / ext4 defaults 0 1\n"
        suffix = b"\nUUID=other /srv ext4 ro 0 2\n"
        prepared = MODULE.prepare_fstab(prefix + self.entry + suffix)
        expected = self.entry.replace(b"defaults,auto,rw,noatime", b"defaults,noatime,noauto,ro,noload")
        expected = expected.replace(b"0 2 #", b"0 0 #")
        self.assertEqual(prepared, prefix + expected + suffix)

    def test_options_are_idempotent_and_writable_auto_removed(self):
        prepared = MODULE.prepare_fstab(self.entry)
        self.assertEqual(MODULE.prepare_fstab(prepared), prepared)
        opts = prepared.split()[3].decode().split(",")
        self.assertTrue({"noauto", "ro", "noload"} <= set(opts))
        self.assertFalse({"auto", "rw"} & set(opts))

    def test_different_uuid_is_rejected(self):
        with self.assertRaises(ValueError):
            MODULE.prepare_fstab(self.entry.replace(MODULE.SOURCE.encode(), b"UUID=other"))

    def test_multiple_entries_rejected_even_if_one_wrong_source(self):
        with self.assertRaises(ValueError):
            MODULE.prepare_fstab(self.entry + b"UUID=other /var/lib/docker ext4 defaults 0 2\n")

    def test_missing_entry_and_wrong_type_rejected(self):
        for contents in (b"# no Docker\n", self.entry.replace(b"ext4", b"xfs")):
            with self.subTest(contents=contents), self.assertRaises(ValueError):
                MODULE.prepare_fstab(contents)

    def test_exact_mount_and_device(self):
        mountinfo = "1 0 252:0 / / rw - ext4 /dev/root rw\n2 1 259:1 / /var/lib/docker rw - ext4 /dev/ssd rw\n"
        self.assertEqual(MODULE.docker_mount_device(mountinfo), (259, 1))
        for bad in (mountinfo.replace("/var/lib/docker", "/var/lib/docker/subdir"), mountinfo + mountinfo):
            with self.assertRaises(ValueError):
                MODULE.docker_mount_device(bad)

    def test_restore_rejects_changed_current_or_backup(self):
        prepared = MODULE.prepare_fstab(self.entry)
        receipt = {"original_sha256": MODULE.sha(self.entry),
                   "prepared_sha256": MODULE.sha(prepared), "state": "prepared"}
        MODULE.guard_restore(prepared, self.entry, receipt)
        for current, original in ((prepared + b"# new change\n", self.entry),
                                  (prepared, self.entry + b"# tampered\n"),
                                  (self.entry, self.entry)):
            with self.subTest(current=current), self.assertRaises(ValueError):
                MODULE.guard_restore(current, original, receipt)

    def test_partial_preparation_can_restore_unchanged_original(self):
        prepared = MODULE.prepare_fstab(self.entry)
        for state in ("preparing", "failed"):
            MODULE.guard_restore(self.entry, self.entry,
                {"original_sha256": MODULE.sha(self.entry),
                 "prepared_sha256": MODULE.sha(prepared), "state": state})


if __name__ == "__main__":
    unittest.main()
