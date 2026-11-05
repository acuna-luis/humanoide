"""Dataset preservation, geometry and leakage tests; no robot or network IO."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
import zipfile

from PIL import Image, ImageDraw

WORKFLOW = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKFLOW))
import coco_prepare as prepare

HAS_MASKS = importlib.util.find_spec("pycocotools") is not None


def image_bytes(index: int) -> bytes:
    image = Image.new("RGB", (32, 32), (10 + index * 20, 25, 40))
    ImageDraw.Draw(image).rectangle((4, 4, 19, 19), fill=(200, 50 + index * 20, 70))
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def fixture():
    images, annotations, mapping, media = [], [], {}, {}
    for number, split in enumerate(("train", "valid", "test")):
        name = f"session_{number}/frame.png"
        images.append({"id": number + 10, "file_name": name, "width": 32, "height": 32})
        annotations.append({"id": number + 100, "image_id": number + 10,
                            "category_id": 3, "bbox": [4, 4, 16, 16], "area": 256,
                            "segmentation": [[4, 4, 20, 4, 20, 20, 4, 20]], "iscrowd": 0})
        mapping[name] = {"split": split, "session_group": f"synthetic_session_{number}"}
        media[f"images/default/{name}"] = image_bytes(number)
    data = {"info": {"description": "Synthetic infrastructure fixture, no ITR claim"},
            "licenses": [], "images": images, "annotations": annotations,
            "categories": [{"id": 3, "name": "synthetic_rectangle", "supercategory": "synthetic"}]}
    return data, {"schema_version": 1, "images": mapping}, media


class CocoPrepareTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="app2-coco-test-")
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        self.archive = self.root / "cvat.zip"
        self.assignments = self.root / "splits.json"
        self.output = self.root / "dataset"

    def write(self, data=None, manifest=None, media=None, extra=None):
        default_data, default_manifest, default_media = fixture()
        data = default_data if data is None else data
        manifest = default_manifest if manifest is None else manifest
        media = default_media if media is None else media
        with zipfile.ZipFile(self.archive, "w") as zipped:
            zipped.writestr("annotations/instances_default.json", json.dumps(data))
            for name, payload in media.items():
                zipped.writestr(name, payload)
            if extra:
                for name, payload in extra:
                    zipped.writestr(name, payload)
        self.assignments.write_text(json.dumps(manifest))

    def run_conversion(self):
        return prepare.prepare_dataset(self.archive, self.assignments, self.output)

    def assert_clean_failure(self, pattern):
        with self.assertRaisesRegex((ValueError, FileExistsError), pattern):
            self.run_conversion()
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.root.glob(".dataset.preparing-*")))

    @unittest.skipUnless(HAS_MASKS, "Full validation requires installed pycocotools")
    def test_round_trip_preserves_bytes_ids_categories_and_provenance(self):
        data, manifest, media = fixture()
        self.write(data, manifest, media)
        result = self.run_conversion()
        self.assertEqual(result["status"], "COCO_PREPARE_PASS")
        for image, split in zip(data["images"], prepare.SPLITS):
            folder = self.output / split
            restored = json.loads((folder / prepare.ANNOTATIONS_NAME).read_text())
            self.assertEqual(restored["images"], [image])
            self.assertEqual(restored["categories"], data["categories"])
            self.assertEqual(restored["info"], data["info"])
            self.assertEqual(restored["licenses"], [])
            self.assertEqual(restored["annotations"][0]["image_id"], image["id"])
            self.assertEqual((folder / image["file_name"]).read_bytes(), media["images/default/" + image["file_name"]])
        receipt = json.loads((self.output / prepare.MANIFEST_NAME).read_text())
        self.assertEqual(receipt["source_zip_sha256"], hashlib.sha256(self.archive.read_bytes()).hexdigest())
        self.assertEqual(receipt["split_manifest_sha256"], hashlib.sha256(self.assignments.read_bytes()).hexdigest())
        self.assertEqual(len(receipt["images"]), 3)
        self.assertEqual([m["mask_pixels"] for m in result["validation"]["splits"]["train"]["masks"]], [256])

    @unittest.skipUnless(HAS_MASKS, "Full validation requires installed pycocotools")
    def test_compressed_and_uncompressed_rle_are_preserved(self):
        import numpy as np
        from pycocotools import mask

        data, manifest, media = fixture()
        binary = np.zeros((32, 32), dtype=np.uint8, order="F")
        binary[4:20, 4:20] = 1
        compressed = mask.encode(binary)
        compressed["counts"] = compressed["counts"].decode("ascii")
        data["annotations"][0]["segmentation"] = compressed
        flattened = binary.ravel(order="F")
        counts, previous, length = [], 0, 0
        for value in flattened:
            if int(value) == previous:
                length += 1
            else:
                counts.append(length)
                previous, length = int(value), 1
        counts.append(length)
        data["annotations"][1]["segmentation"] = {"size": [32, 32], "counts": counts}
        self.write(data, manifest, media)
        self.run_conversion()
        for split, expected in (("train", compressed), ("valid", {"size": [32, 32], "counts": counts})):
            actual = json.loads((self.output / split / prepare.ANNOTATIONS_NAME).read_text())
            self.assertEqual(actual["annotations"][0]["segmentation"], expected)

    def test_existing_destination_is_never_overwritten(self):
        self.write()
        self.output.mkdir()
        marker = self.output / "private-original.txt"
        marker.write_text("keep")
        with self.assertRaises(FileExistsError):
            self.run_conversion()
        self.assertEqual(marker.read_text(), "keep")

    def test_declared_session_cannot_leak_between_splits(self):
        data, manifest, media = fixture()
        manifest["images"][data["images"][1]["file_name"]]["session_group"] = "synthetic_session_0"
        self.write(data, manifest, media)
        self.assert_clean_failure("Session group leaks")

    def test_every_image_needs_an_explicit_assignment(self):
        data, manifest, media = fixture()
        del manifest["images"][data["images"][1]["file_name"]]
        self.write(data, manifest, media)
        self.assert_clean_failure("exactly every COCO image")

    def test_nonempty_train_and_valid_required(self):
        data, manifest, media = fixture()
        for assignment in manifest["images"].values():
            assignment["split"] = "train"
        self.write(data, manifest, media)
        self.assert_clean_failure("train and valid")

    def test_identical_images_rejected_even_with_different_names(self):
        data, manifest, media = fixture()
        keys = list(media)
        media[keys[1]] = media[keys[0]]
        self.write(data, manifest, media)
        self.assert_clean_failure("Duplicate image bytes")

    def test_ambiguous_cvat_image_member_rejected(self):
        data, manifest, media = fixture()
        name = data["images"][0]["file_name"]
        media["images/other/" + name] = image_bytes(4)
        self.write(data, manifest, media)
        self.assert_clean_failure("missing or ambiguous")

    def test_unsafe_zip_paths_rejected_without_extraction(self):
        for path in ("../escape.png", "/absolute.png", "images/../escape.png", "C:/escape.png", "images\\escape.png"):
            with self.subTest(path=path):
                self.write(extra=[(path, b"hostile")])
                self.assert_clean_failure("[Uu]nsafe|Absolute")
        self.assertFalse((self.root.parent / "escape.png").exists())

    def test_zip_symlink_rejected(self):
        self.write()
        link = zipfile.ZipInfo("images/linked.png")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        with zipfile.ZipFile(self.archive, "a") as zipped:
            zipped.writestr(link, "/etc/passwd")
        self.assert_clean_failure("links and special files")

    def test_zip_path_case_collision_rejected(self):
        self.write(extra=[("images/DEFAULT/session_0/FRAME.PNG", image_bytes(4))])
        self.assert_clean_failure("colliding ZIP")

    def test_dimensions_checked_against_decoded_image(self):
        data, manifest, media = fixture()
        data["images"][0]["height"] = 31
        self.write(data, manifest, media)
        self.assert_clean_failure("dimensions differ")

    def test_category_duplicate_and_unknown_rejected(self):
        data, manifest, media = fixture()
        data["categories"].append(copy.deepcopy(data["categories"][0]))
        self.write(data, manifest, media)
        self.assert_clean_failure("Duplicate category")
        data["categories"].pop()
        data["annotations"][0]["category_id"] = 999
        self.write(data, manifest, media)
        self.assert_clean_failure("unknown image or category")

    def test_bbox_outside_image_rejected(self):
        data, manifest, media = fixture()
        data["annotations"][0]["bbox"] = [25, 4, 16, 16]
        self.write(data, manifest, media)
        self.assert_clean_failure("Bounding box outside image")

    def test_bbox_must_contain_polygon(self):
        data, manifest, media = fixture()
        data["annotations"][0]["bbox"] = [5, 4, 15, 16]
        self.write(data, manifest, media)
        self.assert_clean_failure("does not contain its polygon")

    def test_polygon_outside_image_rejected(self):
        data, manifest, media = fixture()
        data["annotations"][0]["segmentation"][0][0] = -1
        self.write(data, manifest, media)
        self.assert_clean_failure("Polygon coordinate outside image")

    def test_nonfinite_json_number_rejected(self):
        data, manifest, media = fixture()
        data["annotations"][0]["bbox"][0] = float("nan")
        self.write(data, manifest, media)
        self.assert_clean_failure("Non-finite JSON")

    def test_duplicate_json_key_rejected(self):
        self.write()
        self.assignments.write_text('{"schema_version":1,"schema_version":2,"images":{}}')
        self.assert_clean_failure("Duplicate JSON object key")

    def test_invalid_compressed_rle_rejected_before_native_decoder(self):
        data, manifest, media = fixture()
        for counts in ("0", "oooo", "invalid!", "é"):
            with self.subTest(counts=counts):
                data["annotations"][0]["segmentation"] = {"size": [32, 32], "counts": counts}
                self.write(data, manifest, media)
                self.assert_clean_failure("RLE")

    @unittest.skipUnless(HAS_MASKS, "Full validation requires installed pycocotools")
    def test_validator_detects_post_conversion_changes(self):
        self.write()
        self.run_conversion()
        changed = self.output / "train" / "session_0/frame.png"
        changed.write_bytes(image_bytes(7))
        with self.assertRaisesRegex(ValueError, "hash differs"):
            prepare.validate_coco_dataset(self.output)

    @unittest.skipUnless(HAS_MASKS, "Full validation requires installed pycocotools")
    def test_validator_rejects_category_change_between_splits(self):
        self.write()
        self.run_conversion()
        annotations = self.output / "valid" / prepare.ANNOTATIONS_NAME
        data = json.loads(annotations.read_text())
        data["categories"][0]["name"] = "another_class"
        annotations.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "Category metadata differs"):
            prepare.validate_coco_dataset(self.output)

    @unittest.skipUnless(HAS_MASKS, "Full validation requires installed pycocotools")
    def test_negative_validation_image_is_supported(self):
        data, manifest, media = fixture()
        data["annotations"] = [a for a in data["annotations"] if a["image_id"] != 11]
        self.write(data, manifest, media)
        result = self.run_conversion()
        self.assertEqual(result["validation"]["splits"]["valid"]["instances"], 0)


if __name__ == "__main__":
    unittest.main()
