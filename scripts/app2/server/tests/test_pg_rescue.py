"""Archive/configuration guard tests; no Docker or network operations."""
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("pg_rescue", Path(__file__).resolve().parents[1] / "verify_pg_rescue.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def make_tar(path, members):
    with tarfile.open(path, "w") as archive:
        for name, contents, kind in members:
            member = tarfile.TarInfo(name)
            member.type = kind
            member.size = len(contents) if kind == tarfile.REGTYPE else 0
            member.mode = 0o600
            archive.addfile(member, io.BytesIO(contents) if member.isfile() else None)


class PgRescueTests(unittest.TestCase):
    def test_path_link_and_special_file_rejection(self):
        for name, kind in (("/absolute", tarfile.REGTYPE), ("a/../escape", tarfile.REGTYPE),
                           ("pg_wal", tarfile.SYMTYPE), ("pg_tblspc/1", tarfile.LNKTYPE),
                           ("device", tarfile.CHRTYPE)):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "bad.tar"
                make_tar(path, [(name, b"x", kind)])
                with tarfile.open(path) as archive, self.assertRaises(ValueError):
                    M.safe_members(archive)

    def test_safe_extraction_new_copy_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "data.tar"
            make_tar(archive, [("./PG_VERSION", b"15\n", tarfile.REGTYPE),
                               ("./global/control", b"fixture", tarfile.REGTYPE)])
            digest = M.sha(archive)
            M.extract_copy(archive, root / "copy")
            self.assertEqual((root / "copy/PG_VERSION").read_bytes(), b"15\n")
            self.assertEqual((root / "copy/global/control").stat().st_mode & 0o777, 0o600)
            self.assertEqual(M.sha(archive), digest)
            with self.assertRaises(FileExistsError):
                M.extract_copy(archive, root / "copy")

    def test_transfer_gate_and_independent_source_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            records = []
            for name in (M.DB_ARCHIVE, M.DEF_ARCHIVE):
                (root / name).write_bytes(b"private fixture")
                records.append({"file": name, "bytes": 15, "sha256": M.sha(root / name), "matches": True})
            transfer = {"all_copied_hashes_match": True, "archives": records}
            original = {"result": {"receipt": {"archives": records}}}
            self.assertEqual(len(M.verified_archives(root, transfer, original)), 2)
            with self.assertRaises(ValueError):
                M.verified_archives(root, {**transfer, "all_copied_hashes_match": False}, original)
            (root / M.DB_ARCHIVE).write_bytes(b"changed")
            with self.assertRaises(ValueError):
                M.verified_archives(root, transfer, original)

    def test_original_image_and_pgdata_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "definitions.tar"
            config = {"Config": {"Image": M.IMAGE, "Env": ["POSTGRES_USER=root", "POSTGRES_DB=cvat"],
                "Labels": {"com.docker.compose.project": "app2-cvat", "com.docker.compose.service": "cvat_db"}},
                "MountPoints": {"/var/lib/postgresql/data": {"Name": "app2-cvat_cvat_db"}}}
            make_tar(path, [("./containers/id/config.v2.json", json.dumps(config).encode(), tarfile.REGTYPE)])
            self.assertEqual(M.database_config(path), ("root", "cvat", Path(".")))
            config["Config"]["Image"] = "postgres:16"
            make_tar(path, [("./containers/id/config.v2.json", json.dumps(config).encode(), tarfile.REGTYPE)])
            with self.assertRaises(ValueError):
                M.database_config(path)


if __name__ == "__main__":
    unittest.main()
