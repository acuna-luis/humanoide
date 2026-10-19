#!/usr/bin/env python3
"""Validate local COCO data; train Seg Nano only when --run is supplied."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import resource
import time

from common import RESOLUTION, cached_weights, local_train_kwargs, new_run, runtime_inventory, sha256, write_json


def validate_dataset(root: Path) -> dict:
    """Check paths, annotations and image leakage before allocating a GPU."""
    result = {}
    category_schema = None
    seen_hashes = {}
    for split in ("train", "valid", "test"):
        split_root = (root / split).resolve()
        annotation_file = split_root / "_annotations.coco.json"
        if split == "test" and not annotation_file.is_file():
            continue
        data = json.loads(annotation_file.read_text(encoding="utf-8"))
        categories = {int(item["id"]): item["name"] for item in data["categories"]}
        if not categories or len(categories) != len(data["categories"]):
            raise ValueError(f"Empty or duplicate category IDs: {annotation_file}")
        if len(set(categories.values())) != len(categories):
            raise ValueError(f"Duplicate category names: {annotation_file}")
        if category_schema is None:
            category_schema = categories
        elif categories != category_schema:
            raise ValueError(f"Category IDs/names differ between splits: {annotation_file}")
        image_ids = set()
        digest = hashlib.sha256()
        for image in data["images"]:
            if image["id"] in image_ids:
                raise ValueError(f"Duplicate image ID in {split}: {image['id']}")
            image_ids.add(image["id"])
            path = (split_root / image["file_name"]).resolve()
            if not path.is_relative_to(split_root) or not path.is_file():
                raise ValueError(f"Invalid/local image path in {split}: {image['file_name']}")
            image_hash = sha256(path)
            if image_hash in seen_hashes and seen_hashes[image_hash] != split:
                raise ValueError(f"The same image content appears in {seen_hashes[image_hash]} and {split}")
            seen_hashes[image_hash] = split
            digest.update(f"{image['file_name']}\0{image_hash}\n".encode())
        if not image_ids:
            raise ValueError(f"Empty image split: {split}")
        annotation_ids = set()
        for annotation in data["annotations"]:
            if annotation["id"] in annotation_ids:
                raise ValueError(f"Duplicate annotation ID in {split}: {annotation['id']}")
            annotation_ids.add(annotation["id"])
            if annotation["image_id"] not in image_ids or annotation["category_id"] not in categories:
                raise ValueError(f"Unknown image/category in {split}: {annotation['id']}")
            if not annotation.get("segmentation"):
                raise ValueError(f"Missing instance segmentation in {split}: {annotation['id']}")
            if len(annotation["bbox"]) != 4 or min(annotation["bbox"][2:]) <= 0:
                raise ValueError(f"Invalid bbox in {split}: {annotation['id']}")
        result[split] = {
            "images": len(image_ids), "instances": len(annotation_ids),
            "annotations_sha256": sha256(annotation_file),
            "image_manifest_sha256": digest.hexdigest(),
        }
    result["categories"] = category_schema
    result["session_split_review"] = "PENDING: exact duplicate check cannot detect near-duplicate/session leakage"
    return result


def parse_batch(value: str) -> int | str:
    if value == "auto":
        return value
    if not value.isdecimal() or int(value) < 1:
        raise argparse.ArgumentTypeError("Use auto or a positive integer")
    return int(value)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=Path("/checkpoints/runs"))
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=parse_batch, default="auto")
    parser.add_argument("--workers", type=int, default=4)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--check", action="store_true", help="Validate only (also the default)")
    action.add_argument("--run", action="store_true", help="Start local GPU training")
    args = parser.parse_args()
    if args.epochs < 1 or args.workers < 0:
        parser.error("epochs must be positive and workers nonnegative")
    dataset = args.dataset.resolve()
    data_info = validate_dataset(dataset)
    if not args.run:
        print(json.dumps({"status": "DATASET_CHECK_PASS", "dataset": str(dataset), "details": data_info}, indent=2))
        return

    import torch
    from rfdetr import RFDETRSegNano

    runtime = runtime_inventory()
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; no CPU fallback will start")
    path = cached_weights()
    output = new_run(args.output_root, "seg_nano_312")
    write_json(output / "runtime.json", runtime)
    write_json(output / "dataset_manifest.json", data_info)
    kwargs = local_train_kwargs(dataset, output, epochs=args.epochs, batch_size=args.batch_size, workers=args.workers)
    write_json(output / "requested_config.json", kwargs)
    model = RFDETRSegNano(pretrain_weights=str(path), resolution=RESOLUTION, device="cuda:0")
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    try:
        model.train(**kwargs)
        torch.cuda.synchronize()
        checkpoints = {str(p.relative_to(output)): {"bytes": p.stat().st_size, "sha256": sha256(p)}
                       for p in sorted(output.rglob("*")) if p.suffix in (".pth", ".ckpt", ".pt")}
        write_json(output / "result.json", {
            "status": "PASS", "elapsed_seconds": time.perf_counter() - started,
            "torch_max_memory_allocated_bytes": torch.cuda.max_memory_allocated(),
            "torch_max_memory_reserved_bytes": torch.cuda.max_memory_reserved(),
            "process_peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "weights_sha256": sha256(path), "checkpoints": checkpoints,
            "note": "Process RSS excludes worker memory; CUDA figures exclude other GPU processes.",
        })
        print(json.dumps({"status": "PASS", "output": str(output)}))
    except Exception as error:
        write_json(output / "result.json", {"status": "FAIL", "error": str(error),
                                         "elapsed_seconds": time.perf_counter() - started})
        raise


if __name__ == "__main__":
    main()
