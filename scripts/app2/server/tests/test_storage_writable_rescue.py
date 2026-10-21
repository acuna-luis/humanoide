"""Local overlay2 fixtures only; never mount a disk or access a server."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("storage_writable_rescue",
    Path(__file__).resolve().parents[1] / "storage_writable_rescue.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
BASE = M.load_base()


class WritableRescueTests(unittest.TestCase):
    def fixture(self, root):
        container, layer = "a" * 64, "b" * 64
        image = b'{"fixture":true}'
        image_id = hashlib.sha256(image).hexdigest()
        files = {
            f"containers/{container}/config.v2.json": json.dumps({
                "ID": container, "Driver": "overlay2", "Image": "sha256:" + image_id}).encode(),
            f"containers/{container}/hostconfig.json": b"{}",
            f"image/overlay2/imagedb/content/sha256/{image_id}": image,
            f"image/overlay2/layerdb/mounts/{container}/mount-id": layer.encode(),
            f"image/overlay2/layerdb/mounts/{container}/init-id": (layer + "-init").encode(),
            f"image/overlay2/layerdb/mounts/{container}/parent": ("sha256:" + "c" * 64).encode(),
            f"overlay2/{layer}/diff/data": b"valuable",
        }
        for name, data in files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return container, layer, image_id

    def test_valid_inventory_with_both_init_mapping_formats(self):
        for suffix in ("-init", ""):
            with self.subTest(suffix=suffix), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                container, layer, image = self.fixture(root)
                (root / f"image/overlay2/layerdb/mounts/{container}/init-id").write_text(layer + suffix)
                report = M.inventory(root, BASE, expected=1)
                self.assertEqual(report["container_count"], 1)
                self.assertEqual(report["containers"][0]["layer_id"], layer)
                self.assertIn(f"overlay2/{layer}/diff", report["tar_paths"])
                self.assertIn(f"image/overlay2/imagedb/content/sha256/{image}", report["tar_paths"])
                self.assertFalse(any(path.startswith("/") or ".." in Path(path).parts
                                     for path in report["tar_paths"]))

    def test_identifiers_reject_traversal_uppercase_and_overlong(self):
        for bad in ("../" + "a" * 61, "A" * 64, "a" * 63, "a" * 65,
                    "a" * 64 + "/diff", "a" * 64 + "\n"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                M.hex_id(bad)

    def test_symlink_and_lexical_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            target = root / "outside"
            target.write_bytes(b"x")
            (root / "link").symlink_to(target)
            with self.assertRaises(ValueError):
                M.guarded(root / "link", root, BASE)
            with self.assertRaises(ValueError):
                M.guarded(root / "x" / ".." / "outside", root, BASE)

    def test_bad_mapping_count_and_oversized_metadata_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            container, layer, _ = self.fixture(root)
            with self.assertRaises(ValueError):
                M.inventory(root, BASE, expected=20)
            mapping = root / f"image/overlay2/layerdb/mounts/{container}/mount-id"
            for bad in ("../outside", layer + " " * 101):
                mapping.write_text(bad)
                with self.subTest(mapping=bad), self.assertRaises(ValueError):
                    M.inventory(root, BASE, expected=1)

    def test_config_driver_and_image_content_hash_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            container, _, image = self.fixture(root)
            config_path = root / f"containers/{container}/config.v2.json"
            config = json.loads(config_path.read_text())
            config["Driver"] = "aufs"
            config_path.write_text(json.dumps(config))
            with self.assertRaises(ValueError):
                M.inventory(root, BASE, expected=1)
            config["Driver"] = "overlay2"
            config_path.write_text(json.dumps(config))
            (root / f"image/overlay2/imagedb/content/sha256/{image}").write_text("{}")
            with self.assertRaises(ValueError):
                M.inventory(root, BASE, expected=1)

    def test_size_gate_preserves_all_layers_and_reserve(self):
        report = {"metadata_bytes": 4096, "containers": [
            {"allocated_bytes": 1024, "logical_bytes": 2 * 1024 ** 3}]}
        with self.assertRaises(ValueError):
            M.estimate(report, BASE.RESERVE + 2 * 1024 ** 3, BASE.RESERVE)
        self.assertGreater(M.estimate(report, BASE.RESERVE + 5 * 1024 ** 3, BASE.RESERVE),
                           2 * 1024 ** 3)


if __name__ == "__main__":
    unittest.main()
