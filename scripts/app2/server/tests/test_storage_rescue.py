"""Local safeguards and a real GNU tar round trip; no mounts or server access."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("storage_rescue",
    Path(__file__).resolve().parents[1] / "storage_rescue.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class StorageRescueTests(unittest.TestCase):
    def devices(self):
        return M.block_nodes({"blockdevices": [
            {"name": "/dev/nvme7n1", "type": "disk", "serial": M.DATA_SERIAL,
             "children": [{"name": "/dev/nvme7n1p1", "type": "part", "size": 2000398934016,
                "uuid": M.UUID, "fstype": "ext4", "maj:min": "259:7"}]},
            {"name": "/dev/nvme8n1", "type": "disk", "serial": M.OS_SERIAL,
             "children": [{"name": "/dev/nvme8n1p3", "type": "part", "children": [
                {"name": "/dev/dm-0", "type": "lvm", "maj:min": "252:0"}]}]}]})

    def report(self):
        return {"volumes": {name: {"logical_bytes": 1024, "allocated_bytes": 4096}
                            for name in M.ESSENTIAL + (M.CACHE,)},
                "server_files": {"logical_bytes": 1024, "allocated_bytes": 4096}}

    def test_uuid_and_serial_select_source_after_renumbering(self):
        self.assertEqual(M.identify_source(self.devices(), "252:0")["name"], "/dev/nvme7n1p1")

    def test_wrong_or_swapped_serials_rejected(self):
        for name in ("/dev/nvme7n1", "/dev/nvme8n1"):
            nodes = self.devices()
            nodes[name]["serial"] = "WRONG_DISK"
            with self.subTest(name=name), self.assertRaises(ValueError):
                M.identify_source(nodes, "252:0")

    def test_missing_or_duplicate_uuid_and_zero_size_rejected(self):
        for change in ("missing", "duplicate", "zero"):
            nodes = self.devices()
            if change == "missing":
                nodes["/dev/nvme7n1p1"]["uuid"] = "EFI_DIFFERENT"
            elif change == "duplicate":
                nodes["/dev/dm-0"]["uuid"] = M.UUID
            else:
                nodes["/dev/nvme7n1p1"]["size"] = 0
            with self.subTest(change=change), self.assertRaises(ValueError):
                M.identify_source(nodes, "252:0")

    def test_fstab_requires_uuid_readonly_no_replay_noauto(self):
        valid = f"UUID={M.UUID} /var/lib/docker ext4 defaults,noauto,ro,noload 0 0\n"
        M.guard_fstab(valid)
        for bad in (valid.replace("noload", "rw"), valid.replace("noauto", "auto"),
                    valid.replace(M.UUID, "wrong"), valid + valid):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                M.guard_fstab(bad)

    def test_mount_parser_keeps_device_and_readonly_options(self):
        mount = M.parse_mounts("42 1 259:7 / /root/test ro,nosuid,nodev,noexec - ext4 /dev/nvme7n1p1 ro,norecovery\n")[0]
        self.assertEqual(mount["device"], "259:7")
        self.assertIn("norecovery", mount["fsoptions"])
        self.assertTrue({"ro", "noexec", "nosuid", "nodev"} <= mount["options"])

    def test_all_ten_volume_names_required(self):
        volumes = self.report()["volumes"]
        self.assertEqual(len(M.plan_tar_paths(volumes)), 9)
        for name in (M.CVAT[0], M.CACHE, "app2_checkpoints"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                M.plan_tar_paths({k: v for k, v in volumes.items() if k != name})

    def test_capacity_failure_does_not_select_partial_essentials(self):
        with self.assertRaises(ValueError):
            M.choose_plan(self.report(), M.RESERVE + 1024)

    def test_optional_cache_omitted_without_losing_essential_volumes(self):
        report = self.report()
        report["volumes"][M.CACHE] = {"logical_bytes": 100 * 1024 ** 3, "allocated_bytes": 10 * 1024 ** 3}
        selected, estimate = M.choose_plan(report, M.RESERVE + 5 * 1024 ** 3)
        self.assertEqual(set(selected), set(M.ESSENTIAL))
        self.assertGreater(estimate, 1024 ** 3)
        selected, _ = M.choose_plan(report, M.RESERVE + 200 * 1024 ** 3)
        self.assertIn(M.CACHE, selected)

    def test_all_volume_plan_preserves_others_and_essential_first(self):
        report = self.report()
        report["volumes"]["ollama_other_service"] = {"logical_bytes": 3 * 1024 ** 3,
                                                    "allocated_bytes": 3 * 1024 ** 3}
        selected, estimate = M.choose_plan(report, M.RESERVE + 10 * 1024 ** 3, all_volumes=True)
        self.assertEqual(selected[:len(M.ESSENTIAL)], list(M.ESSENTIAL))
        self.assertEqual(set(selected), set(report["volumes"]))
        self.assertGreater(estimate, 3 * 1024 ** 3)
        old, _ = M.choose_plan(report, M.RESERVE + 10 * 1024 ** 3)
        self.assertNotIn("ollama_other_service", old)

    def test_all_volume_plan_refuses_unreadable_or_nonfitting_other_volume(self):
        for sizes in ({"inventory_error": "unreadable"},
                      {"logical_bytes": 100 * 1024 ** 3, "allocated_bytes": 100 * 1024 ** 3}):
            report = self.report()
            report["volumes"]["other_service"] = sizes
            with self.subTest(sizes=sizes), self.assertRaises(ValueError):
                M.choose_plan(report, M.RESERVE + 10 * 1024 ** 3, all_volumes=True)

    def test_symlink_path_guard_including_dangling(self):
        with tempfile.TemporaryDirectory() as directory:
            link = Path(directory) / "link"
            link.symlink_to(Path(directory) / "missing")
            with self.assertRaises(ValueError):
                M.no_symlink_path(link / "child")

    def test_readonly_mount_always_normally_unmounted_after_body_failure(self):
        for no_recovery in (True, False):
            with tempfile.TemporaryDirectory() as directory:
                mounted = Path(directory) / "mount"
                mounted.mkdir()
                calls = []
                state = {"mounted": False}
                def command(*args, **kwargs):
                    calls.append(args)
                    if args[0] == "blkid":
                        return f"UUID={M.UUID}\nTYPE=ext4\n"
                    state["mounted"] = args[0] == "mount"
                    return ""
                def mountinfo(path):
                    if not state["mounted"]:
                        return ""
                    opts = "ro,norecovery" if no_recovery else "ro"
                    return f"42 1 259:7 / {mounted} ro,nosuid,nodev,noexec - ext4 /dev/source {opts}\n"
                with patch.object(M, "command", command), patch.object(M.tempfile, "mkdtemp", return_value=str(mounted)), \
                     patch.object(Path, "read_text", mountinfo):
                    with self.assertRaises(ValueError):
                        with M.readonly_source({"name": "/dev/source", "maj:min": "259:7"}):
                            raise ValueError("body failed")
                self.assertEqual(calls[-1], ("umount", str(mounted)))
                self.assertFalse(mounted.exists())

    @unittest.skipUnless(shutil.which("tar") and "GNU tar" in M.command("tar", "--version"), "GNU tar required")
    def test_real_tar_preserves_symlink_and_compares_contents_without_following(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            (source / "data").write_bytes(b"CVAT private fixture\n")
            (root / "outside").write_bytes(b"must not be archived")
            (source / "link").symlink_to("../outside")
            with (source / "sparse").open("wb") as stream:
                stream.seek(2 * 1024 ** 2)
                stream.write(b"end")
            destination = root / "rescue.tar"
            receipt = M.archive(source, ["."], destination, file_limit=8 * 1024 ** 2)
            self.assertEqual(receipt["source_compare"], "PASS")
            self.assertEqual(receipt["sha256"], M.sha_file(destination))
            with tarfile.open(destination) as archive:
                self.assertTrue(archive.getmember("./link").issym())
                self.assertEqual(archive.getmember("./link").linkname, "../outside")
                self.assertNotIn("./outside", archive.getnames())
            self.assertEqual(destination.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                M.archive(source, ["."], destination)

    @unittest.skipUnless(shutil.which("tar") and "GNU tar" in M.command("tar", "--version"), "GNU tar required")
    def test_real_tar_limit_preserves_partial_archive_and_private_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            (source / "data").write_bytes(os.urandom(65536))
            destination = root / "limited.tar"
            with self.assertRaises(subprocess.SubprocessError):
                M.archive(source, ["."], destination, file_limit=4096)
            self.assertTrue(destination.exists())
            self.assertLessEqual(destination.stat().st_size, 4096)
            self.assertEqual(destination.with_suffix(".error.log").stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
