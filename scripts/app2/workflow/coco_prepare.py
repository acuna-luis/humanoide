#!/usr/bin/env python3
"""Convert one local CVAT COCO ZIP into RF-DETR's train/valid[/test] layout.

The split manifest explicitly maps every COCO image file_name to a split and a
session_group. This tool never assigns a real material identity or chooses a
random image split. Original image bytes, categories and annotation IDs remain
unchanged. Pillow and pycocotools are required for actual data validation.
"""

from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
from typing import Callable
import zipfile


SPLITS = ("train", "valid", "test")
MAX_ZIP_MEMBERS = 100_000
MAX_ZIP_BYTES = 64 * 1024**3
MAX_MEMBER_BYTES = 512 * 1024**2
MAX_JSON_BYTES = 64 * 1024**2
MAX_IMAGE_PIXELS = 100_000_000
MANIFEST_NAME = "dataset_manifest.json"
ANNOTATIONS_NAME = "_annotations.coco.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json(data: bytes) -> dict:
    if len(data) > MAX_JSON_BYTES:
        raise ValueError("JSON exceeds the 64 MiB preparation limit")
    def reject_constant(value):
        raise ValueError(f"Non-finite JSON number: {value}")

    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON object key: {key}")
            result[key] = value
        return result

    value = json.loads(data, parse_constant=reject_constant, object_pairs_hook=unique_keys)
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value


def _write_json(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def _relative_name(name: object) -> str:
    """Reject ambiguous or unsafe paths, rather than sanitizing them."""
    if not isinstance(name, str) or not name or "\\" in name or ":" in name:
        raise ValueError(f"Unsafe relative path: {name!r}")
    if any(ord(char) < 32 for char in name):
        raise ValueError("Control character in a relative path")
    if name.startswith("/") or any(part in ("", ".", "..") for part in name.split("/")):
        raise ValueError(f"Unsafe relative path: {name!r}")
    if PurePosixPath(name).is_absolute():
        raise ValueError(f"Absolute path: {name!r}")
    return name


def _integer(value: object, label: str, *, positive: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < int(positive):
        raise ValueError(f"Invalid integer {label}: {value!r}")
    return value


def _number(value: object, label: str) -> float:
    try:
        valid = (not isinstance(value, bool) and isinstance(value, (int, float))
                 and math.isfinite(value))
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(f"Invalid finite number {label}")
    return float(value)


def _compressed_rle_counts(encoded: str, pixels: int) -> list[int]:
    """Validate COCO's signed 5-bit differential runs before native decoding."""
    counts, offset = [], 0
    while offset < len(encoded):
        value, shift = 0, 0
        while True:
            if offset >= len(encoded):
                raise ValueError("Truncated compressed RLE count")
            char = ord(encoded[offset]) - 48
            offset += 1
            if not 0 <= char <= 63 or shift > 60:
                raise ValueError("Invalid compressed RLE count")
            value |= (char & 31) << shift
            shift += 5
            if not char & 32:
                if char & 16:
                    value |= -1 << shift
                break
        if len(counts) > 2:
            value += counts[-2]
        if not 0 <= value <= pixels:
            raise ValueError("Compressed RLE count outside image bounds")
        counts.append(value)
        if len(counts) > pixels + 1:
            raise ValueError("Too many compressed RLE counts")
    if not counts or sum(counts) != pixels:
        raise ValueError("Compressed RLE counts do not cover the image")
    return counts


def _categories(data: dict) -> list[dict]:
    categories = data.get("categories")
    if not isinstance(categories, list) or not categories:
        raise ValueError("COCO categories must be a nonempty list")
    ids, names = set(), set()
    for item in categories:
        if not isinstance(item, dict):
            raise ValueError("Invalid category object")
        identifier = _integer(item.get("id"), "category.id")
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Empty category name")
        if identifier in ids or name in names:
            raise ValueError("Duplicate category ID or name")
        ids.add(identifier)
        names.add(name)
    return categories


def _image_description(payload: bytes, image: dict) -> tuple[int, int]:
    from PIL import Image

    width = _integer(image.get("width"), "image.width", positive=True)
    height = _integer(image.get("height"), "image.height", positive=True)
    if width * height > MAX_IMAGE_PIXELS:
        raise ValueError("Image exceeds the 100 million pixel preparation limit")
    with Image.open(io.BytesIO(payload)) as decoded:
        if decoded.size != (width, height):
            raise ValueError(f"Image dimensions differ from COCO: {image['file_name']}")
        if getattr(decoded, "n_frames", 1) != 1:
            raise ValueError("Only single-frame images are supported")
        decoded.load()  # Check the complete payload, not only the image header.
    return width, height


def _mask(annotation: dict, width: int, height: int) -> dict:
    bbox = annotation.get("bbox")
    if not isinstance(bbox, list) or len(bbox) != 4:
        raise ValueError("COCO bbox must contain x,y,width,height")
    x, y, box_width, box_height = [_number(value, "bbox") for value in bbox]
    epsilon = 1e-4
    if (x < 0 or y < 0 or box_width <= 0 or box_height <= 0
            or x + box_width > width + epsilon or y + box_height > height + epsilon):
        raise ValueError(f"Bounding box outside image or empty: annotation {annotation['id']}")
    area = _number(annotation.get("area"), "annotation.area")
    if area <= 0 or area > width * height:
        raise ValueError("Empty or impossible annotation area")
    crowd = annotation.get("iscrowd", 0)
    if isinstance(crowd, bool) or not isinstance(crowd, int) or crowd not in (0, 1):
        raise ValueError("iscrowd must be integer 0 or 1")
    segmentation = annotation.get("segmentation")
    if isinstance(segmentation, list):
        if not segmentation:
            raise ValueError("Missing instance segmentation")
        for polygon in segmentation:
            if not isinstance(polygon, list) or len(polygon) < 6 or len(polygon) % 2:
                raise ValueError("A polygon needs at least three x,y pairs")
            points = [_number(value, "polygon coordinate") for value in polygon]
            if len(set(zip(points[::2], points[1::2]))) < 3:
                raise ValueError("A polygon needs three distinct vertices")
            for point_x, point_y in zip(points[::2], points[1::2]):
                if not (0 <= point_x <= width and 0 <= point_y <= height):
                    raise ValueError("Polygon coordinate outside image")
                if not (x - epsilon <= point_x <= x + box_width + epsilon
                        and y - epsilon <= point_y <= y + box_height + epsilon):
                    raise ValueError("Bounding box does not contain its polygon")
    elif isinstance(segmentation, dict):
        size = segmentation.get("size")
        if (not isinstance(size, list) or len(size) != 2
                or [_integer(v, "RLE size", positive=True) for v in size] != [height, width]):
            raise ValueError("RLE size differs from its image dimensions")
        counts = segmentation.get("counts")
        if isinstance(counts, list):
            if (not counts or len(counts) > width * height + 1
                    or sum(_integer(v, "RLE count") for v in counts) != width * height):
                raise ValueError("Invalid uncompressed RLE counts")
        elif isinstance(counts, str):
            if not counts:
                raise ValueError("Empty compressed RLE counts")
            try:
                counts.encode("ascii")
            except UnicodeEncodeError as error:
                raise ValueError("Compressed RLE must contain ASCII counts") from error
            _compressed_rle_counts(counts, width * height)
        else:
            raise ValueError("Unsupported RLE counts")
    else:
        raise ValueError("Missing or unsupported instance segmentation")

    from pycocotools import mask as masks

    if isinstance(segmentation, list):
        rle = masks.merge(masks.frPyObjects(segmentation, height, width))
    elif isinstance(segmentation["counts"], list):
        rle = masks.frPyObjects(segmentation, height, width)
    else:
        rle = {"size": [height, width], "counts": segmentation["counts"].encode("ascii")}
    try:
        mask_area = int(masks.area(rle))
        mask_bbox = [float(v) for v in masks.toBbox(rle)]
        decoded = masks.decode(rle)
    except Exception as error:
        raise ValueError("pycocotools rejected the segmentation") from error
    if decoded.shape != (height, width) or mask_area <= 0:
        raise ValueError("Segmentation produces an empty or incorrectly shaped mask")
    mask_x, mask_y, mask_width, mask_height = mask_bbox
    # A polygon's continuous bounds and raster bounds can differ by one pixel.
    if (mask_x < x - 1 - epsilon or mask_y < y - 1 - epsilon
            or mask_x + mask_width > x + box_width + 1 + epsilon
            or mask_y + mask_height > y + box_height + 1 + epsilon):
        raise ValueError("Bounding box does not contain its raster mask")
    if isinstance(segmentation, dict) and abs(mask_area - area) > 1:
        raise ValueError("RLE area differs from the decoded mask")
    return {"annotation_id": annotation["id"], "mask_pixels": mask_area}


def _validate_coco(data: dict, read_image: Callable[[str], bytes]) -> dict:
    categories = _categories(data)
    category_ids = {item["id"] for item in categories}
    images, annotations = data.get("images"), data.get("annotations")
    if not isinstance(images, list) or not images or not isinstance(annotations, list):
        raise ValueError("COCO requires a nonempty images list and an annotations list")
    image_index, names, hashes, descriptions = {}, set(), {}, []
    for image in images:
        if not isinstance(image, dict):
            raise ValueError("Invalid image object")
        identifier = _integer(image.get("id"), "image.id")
        name = _relative_name(image.get("file_name"))
        if name.split("/")[0].casefold() == ANNOTATIONS_NAME.casefold():
            raise ValueError("Image path conflicts with the output annotation document")
        if identifier in image_index or name.casefold() in names:
            raise ValueError("Duplicate image ID or colliding image path")
        names.add(name.casefold())
        payload = read_image(name)
        width, height = _image_description(payload, image)
        digest = hashlib.sha256(payload).hexdigest()
        if digest in hashes:
            raise ValueError(f"Duplicate image bytes: {hashes[digest]} and {name}")
        hashes[digest] = name
        image_index[identifier] = (width, height)
        descriptions.append({"image_id": identifier, "file_name": name, "sha256": digest,
                             "bytes": len(payload), "width": width, "height": height})
    annotation_ids, masks = set(), []
    for annotation in annotations:
        if not isinstance(annotation, dict):
            raise ValueError("Invalid annotation object")
        identifier = _integer(annotation.get("id"), "annotation.id")
        image_id = _integer(annotation.get("image_id"), "annotation.image_id")
        category_id = _integer(annotation.get("category_id"), "annotation.category_id")
        if identifier in annotation_ids:
            raise ValueError("Duplicate annotation ID")
        annotation_ids.add(identifier)
        if image_id not in image_index or category_id not in category_ids:
            raise ValueError("Annotation refers to an unknown image or category")
        masks.append(_mask(annotation, *image_index[image_id]))
    return {"images": descriptions, "instances": len(annotations), "masks": masks,
            "categories": categories}


def _zip_members(archive: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    members, portable_names = {}, set()
    total = 0
    infos = archive.infolist()
    if len(infos) > MAX_ZIP_MEMBERS:
        raise ValueError("ZIP exceeds the 100000 member preparation limit")
    for info in infos:
        name = info.filename[:-1] if info.is_dir() else info.filename
        _relative_name(name)
        if name.casefold() in portable_names:
            raise ValueError("Duplicate or colliding ZIP member path")
        portable_names.add(name.casefold())
        mode = info.external_attr >> 16
        kind = stat.S_IFMT(mode)
        if stat.S_ISLNK(mode) or kind not in (0, stat.S_IFREG, stat.S_IFDIR):
            raise ValueError("ZIP links and special files are not supported")
        if info.flag_bits & 1:
            raise ValueError("Encrypted ZIP members are not supported")
        if info.file_size > MAX_MEMBER_BYTES:
            raise ValueError("ZIP member exceeds the 512 MiB preparation limit")
        total += info.file_size
        if total > MAX_ZIP_BYTES:
            raise ValueError("ZIP exceeds the 64 GiB uncompressed preparation limit")
        if not info.is_dir():
            members[name] = info
    return members


def _image_member(name: str, members: dict[str, zipfile.ZipInfo]) -> str:
    candidates = {member for member in members
                  if member == name or member == "images/" + name
                  or (member.startswith("images/") and member.endswith("/" + name))}
    if len(candidates) != 1:
        raise ValueError(f"Image ZIP path is missing or ambiguous: {name}")
    return candidates.pop()


def _split_assignments(manifest: dict, images: list[dict]) -> dict:
    if type(manifest.get("schema_version")) is not int or manifest["schema_version"] != 1:
        raise ValueError("Split manifest requires schema_version=1")
    assignments = manifest.get("images")
    if not isinstance(assignments, dict):
        raise ValueError("Split manifest requires an images mapping")
    filenames = [image["file_name"] for image in images]
    if set(assignments) != set(filenames):
        raise ValueError("Split manifest must cover exactly every COCO image file_name")
    groups, splits = {}, set()
    for name, record in assignments.items():
        _relative_name(name)
        if not isinstance(record, dict) or record.get("split") not in SPLITS:
            raise ValueError(f"Invalid split assignment: {name}")
        group = record.get("session_group")
        if not isinstance(group, str) or not group.strip():
            raise ValueError("Every image requires a nonempty session_group")
        split = record["split"]
        if group in groups and groups[group] != split:
            raise ValueError(f"Session group leaks between splits: {group}")
        groups[group] = split
        splits.add(split)
    if not {"train", "valid"}.issubset(splits):
        raise ValueError("Nonempty train and valid splits are required")
    return assignments


def _local_image(root: Path, name: str) -> bytes:
    current = root
    for part in _relative_name(name).split("/"):
        current = current / part
        if current.is_symlink():
            raise ValueError("Dataset image links are not supported")
    if not current.is_file() or not current.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Missing local dataset image: {name}")
    if current.stat().st_size > MAX_MEMBER_BYTES:
        raise ValueError("Image exceeds the 512 MiB preparation limit")
    return current.read_bytes()


def validate_coco_dataset(root: Path) -> dict:
    """Validate actual images, masks, class consistency and exact data leakage.

    Session separation can only be checked when dataset_manifest.json from the
    converter is present. Neither this nor hashing detects near-duplicate frames
    placed in incorrectly named session groups; review capture provenance too.
    """
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Dataset root must be an existing directory, not a link")
    results, categories, hashes = {}, None, {}
    for split in SPLITS:
        folder = root / split
        annotation_file = folder / ANNOTATIONS_NAME
        if split == "test" and not folder.exists():
            continue
        if folder.is_symlink() or annotation_file.is_symlink():
            raise ValueError("Dataset split/annotation links are not supported")
        data = _json(annotation_file.read_bytes())
        result = _validate_coco(data, lambda name, folder=folder: _local_image(folder, name))
        if categories is None:
            categories = result["categories"]
        elif result["categories"] != categories:
            raise ValueError("Category metadata differs between splits")
        for image in result["images"]:
            if image["sha256"] in hashes:
                raise ValueError(f"Duplicate image bytes across splits: {split}")
            hashes[image["sha256"]] = split
        results[split] = result
    session_review = "PENDING: no converter manifest; review session separation"
    source_manifest = root / MANIFEST_NAME
    if source_manifest.exists():
        if source_manifest.is_symlink():
            raise ValueError("Dataset manifest links are not supported")
        manifest = _json(source_manifest.read_bytes())
        records = manifest.get("images")
        if not isinstance(records, list):
            raise ValueError("Invalid converter dataset manifest")
        actual = {(split, image["file_name"]): image
                  for split, result in results.items() for image in result["images"]}
        recorded, groups = set(), {}
        for record in records:
            key = (record.get("split"), record.get("file_name"))
            if key in recorded or key not in actual:
                raise ValueError("Converter manifest images differ from dataset")
            recorded.add(key)
            if record.get("sha256") != actual[key]["sha256"]:
                raise ValueError("Dataset image hash differs from converter manifest")
            group = record.get("session_group")
            if not isinstance(group, str) or not group.strip():
                raise ValueError("Missing session_group in converter manifest")
            if group in groups and groups[group] != key[0]:
                raise ValueError("Session group leaks between splits")
            groups[group] = key[0]
        if recorded != set(actual):
            raise ValueError("Converter manifest does not cover every image")
        session_review = "PASS: declared groups disjoint; near-duplicate/provenance review still required"
    return {"status": "DATASET_CHECK_PASS", "splits": results,
            "session_split_review": session_review}


def _publish_no_replace(source: Path, destination: Path) -> None:
    """Linux renameat2 atomically publishes a directory without replacing one."""
    library = ctypes.CDLL(None, use_errno=True)
    function = getattr(library, "renameat2", None)
    if function is None:
        raise RuntimeError("Atomic no-replace publish requires Linux renameat2")
    function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    function.restype = ctypes.c_int
    if function(-100, os.fsencode(source), -100, os.fsencode(destination), 1) != 0:
        error = ctypes.get_errno()
        if error == errno.EEXIST:
            raise FileExistsError(f"Refusing to overwrite dataset: {destination}")
        raise OSError(error, os.strerror(error), str(destination))


def prepare_dataset(cvat_zip: Path, split_manifest: Path, output: Path) -> dict:
    cvat_zip, split_manifest, output = Path(cvat_zip), Path(split_manifest), Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"Refusing to overwrite dataset: {output}")
    if cvat_zip.is_symlink() or split_manifest.is_symlink():
        raise ValueError("Input ZIP and split manifest must be regular local files")
    source_hash, assignment_hash = sha256_file(cvat_zip), sha256_file(split_manifest)
    split_data = _json(split_manifest.read_bytes())
    output.parent.mkdir(parents=True, exist_ok=True)
    destination = output.parent.resolve() / output.name
    staging = Path(tempfile.mkdtemp(prefix="." + output.name + ".preparing-", dir=destination.parent))
    try:
        with zipfile.ZipFile(cvat_zip) as archive:
            members = _zip_members(archive)
            documents = [name for name in members if name.startswith("annotations/") and name.endswith(".json")]
            if len(documents) != 1:
                raise ValueError("Expected exactly one annotations/*.json COCO document in CVAT ZIP")
            source_coco = archive.read(members[documents[0]])
            data = _json(source_coco)
            if not isinstance(data.get("images"), list):
                raise ValueError("Missing COCO images list")
            assignments = _split_assignments(split_data, data["images"])
            resolved = {image["file_name"]: _image_member(_relative_name(image["file_name"]), members)
                        for image in data["images"]}
            result = _validate_coco(data, lambda name: archive.read(members[resolved[name]]))
            for split in SPLITS:
                selected = [image for image in data["images"] if assignments[image["file_name"]]["split"] == split]
                if not selected:
                    continue
                folder = staging / split
                folder.mkdir(mode=0o700)
                selected_ids = {image["id"] for image in selected}
                subset = {**data, "images": selected,
                          "annotations": [ann for ann in data["annotations"] if ann["image_id"] in selected_ids]}
                for image in selected:
                    target = folder / image["file_name"]
                    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                    with target.open("xb") as stream:
                        stream.write(archive.read(members[resolved[image["file_name"]]]))
                _write_json(folder / ANNOTATIONS_NAME, subset)
            manifest = {
                "schema_version": 1, "converter": "scripts/app2/workflow/coco_prepare.py",
                "converter_sha256": sha256_file(Path(__file__)),
                "source_zip_sha256": source_hash, "split_manifest_sha256": assignment_hash,
                "source_coco_member": documents[0], "categories": data["categories"],
                "source_coco_sha256": hashlib.sha256(source_coco).hexdigest(),
                "images": [{**image, "split": assignments[image["file_name"]]["split"],
                            "session_group": assignments[image["file_name"]]["session_group"],
                            "zip_member": resolved[image["file_name"]]}
                           for image in result["images"]],
                "identity_status": "UNCONFIRMED: class labels do not certify a material reference",
                "geometry_status": "IMAGE_ONLY: no calibrated pose or grasp",
            }
            _write_json(staging / MANIFEST_NAME, manifest)
        checked = validate_coco_dataset(staging)
        if sha256_file(cvat_zip) != source_hash or sha256_file(split_manifest) != assignment_hash:
            raise ValueError("Input ZIP or split manifest changed during conversion")
        _publish_no_replace(staging, destination)
        return {"status": "COCO_PREPARE_PASS", "output": str(destination),
                "manifest_sha256": sha256_file(destination / MANIFEST_NAME), "validation": checked}
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cvat-zip", type=Path, required=True)
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = prepare_dataset(args.cvat_zip, args.split_manifest, args.output)
    except (ValueError, OSError, KeyError, ImportError, zipfile.BadZipFile) as error:
        parser.exit(2, f"COCO_PREPARE_FAILED: {type(error).__name__}: {error}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
