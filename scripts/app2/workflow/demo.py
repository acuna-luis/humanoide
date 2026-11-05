#!/usr/bin/env python3
"""Run real local perception and label reading on files; never command hardware."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import sys
import time
from typing import Any

if __package__:
    from .material import IDENTITY_SCOPES, compare_codes, decode_codes, parser_configuration
else:
    from material import IDENTITY_SCOPES, compare_codes, decode_codes, parser_configuration


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_ready(value: Any) -> Any:
    """Allow finite scalar metadata, never silently serialize an image/mask array."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Nonfinite value in perception output")
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [json_ready(item) for item in value]
    if getattr(value, "ndim", None) == 0 and hasattr(value, "item"):
        return json_ready(value.item())
    raise TypeError(f"Unsupported non-scalar perception metadata: {type(value).__name__}")


def exception_record(component: str, error: Exception) -> dict:
    return {"component": component, "type": type(error).__name__, "message": str(error)[:4000]}


def frame_exception_code(read_state: str, exceptions: list[dict]) -> str | None:
    if exceptions:
        return "APP2_PROCESSING_ERROR"
    return {"MATCH": None, "MISMATCH": "APP2_WRONG_MATERIAL", "NO_READ": "APP2_NO_READ",
            "AMBIGUOUS": "APP2_AMBIGUOUS", "PROCESSING_ERROR": "APP2_PROCESSING_ERROR",
            "UNKNOWN": "APP2_IDENTITY_UNCONFIRMED"}[read_state]


def diagnostic(image: Any, perception: dict, material: dict, *, public_model: bool) -> Any:
    from PIL import ImageDraw

    result = image.copy().convert("RGB")
    draw = ImageDraw.Draw(result, "RGBA")
    colors = ((10, 220, 100), (50, 150, 255), (240, 130, 30), (200, 60, 255))
    for index, detection in enumerate(perception.get("detections", [])):
        color = colors[index % len(colors)]
        polygon = detection.get("mask_polygon")
        polygons = detection.get("mask_polygons")
        if polygon:
            polygons = [polygon]
        for points in polygons or []:
            if len(points) >= 3:
                draw.polygon([tuple(map(float, point)) for point in points], fill=(*color, 65), outline=(*color, 255))
        box = detection.get("bbox_xyxy")
        if box is not None and len(box) == 4:
            x0, y0, x1, y1 = map(float, box)
            if x1 >= x0 and y1 >= y0:
                draw.rectangle((x0, y0, x1, y1), outline=(*color, 255), width=2)
                name = str(detection.get("class_name", detection.get("class_id", "unknown")))
                score = float(detection.get("confidence", 0))
                text = f"{name} {score:.3f}".encode("ascii", "replace").decode()
                draw.text((max(0, x0), max(22, y0 - 12)), text[:100], fill=(*color, 255))
    code_color = (20, 220, 80, 255) if material["result"] == "MATCH" else (255, 165, 0, 255)
    for code in material.get("codes", []):
        position = code.get("position")
        if isinstance(position, list) and len(position) >= 3:
            points = [tuple(map(float, point)) for point in position]
            draw.line(points + [points[0]], fill=code_color, width=3)
    banner = f"OFFLINE | code: {material['result']} | container: UNKNOWN | 3D: CALIBRATION_REQUIRED"
    if public_model:
        banner += " | PUBLIC MODEL, NOT TRAINED FOR ITR"
    # Multiple short lines remain readable on small input frames.
    lines = [banner[offset:offset + 84] for offset in range(0, len(banner), 84)]
    draw.rectangle((0, 0, result.width, 14 * len(lines) + 4), fill=(0, 0, 0, 210))
    for index, line in enumerate(lines):
        draw.text((3, index * 14 + 2), line, fill=(255, 255, 255, 255))
    return result


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--image", type=Path, help="One local image")
    source.add_argument("--sequence", type=Path, help="Directory of local images, filename order; no live camera")
    parser.add_argument("--output-root", type=Path, required=True, help="New directory; existing paths are rejected")
    parser.add_argument("--expected-material", help="Exact expected identifier; omitted means UNKNOWN")
    parser.add_argument("--identity-scope", choices=IDENTITY_SCOPES, default="unconfirmed")
    parser.add_argument("--parser-config", type=Path, help="JSON parser contract: exact_utf8 or json_field")
    parser.add_argument("--model", choices=("public", "checkpoint"), default="public")
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--threshold", type=float, default=.5)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--task-id")
    parser.add_argument("--location", help="Operator-supplied location description; omitted means null")
    parser.add_argument("--dataset-version", help="Known training dataset version; omitted means null")
    parser.add_argument("--synthetic-input", action="store_true", help="Declare that input pixels are synthetic, without faking inference")
    args = parser.parse_args(argv)
    if not math.isfinite(args.threshold) or not 0 <= args.threshold <= 1:
        parser.error("threshold must be finite and between 0 and 1")
    if args.model == "checkpoint" and args.checkpoint is None:
        parser.error("--model checkpoint requires --checkpoint")
    if args.model == "public" and args.checkpoint is not None:
        parser.error("--checkpoint requires --model checkpoint")
    if args.expected_material == "":
        parser.error("expected-material cannot be empty")
    try:
        args.payload_parser = parser_configuration(
            json.loads(args.parser_config.read_text(encoding="utf-8")) if args.parser_config else None)
    except (ValueError, OSError, TypeError) as error:
        parser.error(f"Invalid parser configuration: {error}")
    if args.image:
        if not args.image.is_file():
            parser.error("--image must name an existing local file")
        args.images = [args.image.resolve()]
    else:
        if not args.sequence.is_dir():
            parser.error("--sequence must name an existing directory")
        args.images = sorted(path.resolve() for path in args.sequence.iterdir()
                             if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES)
        if not args.images:
            parser.error("No supported image files in --sequence")
    if args.output_root.exists():
        parser.error("output-root already exists; select a new directory to preserve prior evidence")
    args.output_root = args.output_root.resolve()
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_arguments(argv)
    from PIL import Image
    import numpy as np

    args.output_root.mkdir(parents=True, exist_ok=False)
    code_hashes = {path.name: sha256(path) for path in sorted(Path(__file__).parent.glob("*.py"))}
    model = None
    model_error = None
    started_load = time.perf_counter()
    try:
        if __package__:
            from .perception import LocalPerception
        else:
            from perception import LocalPerception
        model = LocalPerception(weights=args.checkpoint, device=args.device, threshold=args.threshold)
    except Exception as error:
        model_error = error
    load_seconds = time.perf_counter() - started_load
    run_id = args.output_root.name
    failures = 0
    log_path = args.output_root / "events.jsonl"
    with log_path.open("x", encoding="utf-8") as log:
        for index, source in enumerate(args.images):
            started = time.perf_counter()
            exceptions = []
            image = None
            source_hash = None
            try:
                source_hash = sha256(source)
                with Image.open(source) as original:
                    image = original.convert("RGB")
            except Exception as error:
                exceptions.append(exception_record("image", error))
            placeholder = image is None
            if placeholder:
                image = Image.new("RGB", (640, 240), "#222222")
            perception = {"detections": [], "metadata": {}, "status": "PROCESSING_ERROR"}
            perception_started = time.perf_counter()
            if not placeholder:
                try:
                    if model_error is not None:
                        raise model_error
                    perception = json_ready(model.predict(image))
                    if not isinstance(perception, dict) or not isinstance(perception.get("detections"), list):
                        raise ValueError("LocalPerception must return a dictionary with a detections list")
                    perception["status"] = "DETECTIONS_PRESENT" if perception["detections"] else "NO_DETECTIONS"
                except Exception as error:
                    perception = {"detections": [], "metadata": {}, "status": "PROCESSING_ERROR"}
                    exceptions.append(exception_record("perception", error))
            perception_seconds = time.perf_counter() - perception_started
            material = compare_codes([], args.expected_material, args.identity_scope, parser=args.payload_parser)
            if not placeholder:
                try:
                    material = compare_codes(decode_codes(np.asarray(image)), args.expected_material,
                                             args.identity_scope, parser=args.payload_parser)
                    for error in material["exceptions"]:
                        exceptions.append({"component": "material", **error})
                except Exception as error:
                    material["result"] = "PROCESSING_ERROR"
                    material["exceptions"].append(exception_record("decoder", error))
                    exceptions.append(exception_record("decoder", error))
            else:
                material["result"] = "PROCESSING_ERROR"
                material["exceptions"] = [exception_record("image", ValueError("Image could not be loaded"))]
            stem = f"{index:06d}_{source.stem}"
            diagnostic_path = args.output_root / f"{stem}.png"
            try:
                diagnostic(image, perception, material, public_model=args.model == "public").save(diagnostic_path)
            except Exception as error:
                exceptions.append(exception_record("diagnostic", error))
                # Keep a viewable source even if an invalid model overlay fails.
                image.save(diagnostic_path)
            if exceptions:
                failures += 1
            try:
                zxing_version = importlib.metadata.version("zxing-cpp")
            except importlib.metadata.PackageNotFoundError:
                zxing_version = None
            read_state = material["result"]
            dataset_version = (args.dataset_version if args.dataset_version is not None
                               else perception.get("metadata", {}).get("dataset_version"))
            record = {
                "schema_version": "app2-offline-1.0", "application_id": "app2",
                "task_id": args.task_id, "run_id": run_id, "frame_index": index,
                "timestamp_utc": utc_now(), "location": args.location,
                "input": {"path": str(source), "sha256": source_hash, "synthetic": args.synthetic_input},
                "expected_material": args.expected_material,
                "recognized_material": material["recognized_material"],
                "identity_scope": args.identity_scope,
                "perception": perception, "material": material,
                "result": {"vision": perception["status"], "material_read": material["result"]},
                "pass_fail": "PASS" if read_state == "MATCH" else None if read_state == "UNKNOWN" else "FAIL",
                "evaluation_scope": "offline_label_comparison_only",
                "no_read": read_state == "NO_READ", "misread": None,
                "exception_code": frame_exception_code(read_state, exceptions), "scan_quality": None,
                "retries": 0, "exceptions": exceptions, "interventions": [], "stops": [],
                "events_scope": "offline_processor_only",
                "operator_intervention_status": None,
                "safety_stop_status": None, "protective_stop_status": None,
                "cycle_time_s": None, "physical_cycle_status": "NOT_EXECUTED",
                "offline_processing_time_s": time.perf_counter() - started,
                "perception_time_s": perception_seconds, "model_load_time_s": load_seconds,
                "robot_versions": None,
                "completion_status": "offline_processing_failed" if exceptions else "offline_processing_completed",
                "model": {"selection": args.model, "checkpoint": str(args.checkpoint) if args.checkpoint else None,
                          "training_domain": "PUBLIC_COCO_NOT_VALIDATED_FOR_APP2" if args.model == "public" else "CUSTOM_CHECKPOINT_VALIDATION_PENDING",
                          "metadata": perception.get("metadata", {})},
                "dataset": {"version": dataset_version,
                            "manifest_sha256": perception.get("metadata", {}).get("dataset_manifest_sha256")},
                "code": {"source_sha256": code_hashes, "zxing_cpp_version": zxing_version},
                "geometry_3d": {"status": "CALIBRATION_REQUIRED", "pose": None, "grasp": None},
                "empty_container": "UNKNOWN", "destination_ready": "UNKNOWN",
                "simulated_physical_interfaces": True,
                "interfaces": {"robot": "SIMULATED_NOT_CONNECTED", "plc": "SIMULATED_NOT_CONNECTED"},
                "diagnostic_image": str(diagnostic_path), "diagnostic_is_placeholder": placeholder,
            }
            text = json.dumps(record, ensure_ascii=False, sort_keys=True, allow_nan=False)
            (args.output_root / f"{stem}.json").write_text(text + "\n", encoding="utf-8")
            log.write(text + "\n")
            log.flush()
            print(json.dumps({"frame": index, "vision": perception["status"], "material": material["result"],
                              "completion_status": record["completion_status"], "record": f"{stem}.json"}))
    print(json.dumps({"output": str(args.output_root), "frames": len(args.images), "processing_failures": failures,
                      "physical_control": "NOT_CONNECTED"}))
    return 2 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
