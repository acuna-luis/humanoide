#!/usr/bin/env python3
"""Prepare provisional APP2 ontology and a separate, persistent synthetic demo.

Uses only Python's standard library and the repository's local-only CVAT API
helper. Never uploads real photographs or claims a confirmed part reference.
Created synthetic tasks are retained, including after failure, with their IDs
in the private receipt. Existing projects are only read and schema-checked.

Annotation reimport follows CVAT 2.79's POST annotations + annotation_file API:
https://docs.cvat.ai/docs/api_sdk/sdk/reference/apis/tasks-api/
Pinned implementation: cvat-ai/cvat@9176834830e2e931a8d3a6857dcf43c6cc0ee927
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import sys
import urllib.parse
import uuid
import zipfile
import zlib


# Works in the checkout and with PYTHONPATH=/opt/app2/cvat in the image.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server" / "cvat"))
from verify_annotation import API, inside  # noqa: E402


WIDTH, HEIGHT = 128, 96
REAL_PROJECT = "app2-itr-v0"
DEMO_PROJECT = "app2-infrastructure-demo-v0"
DEMO_LABEL = "synthetic_app2_probe_only"
SCHEMA_VERSION = 1
REAL_LABELS = [{
    "name": "itr_candidate", "type": "polygon", "attributes": [
        {"name": "visibility", "input_type": "select", "mutable": False,
         "default_value": "indeterminate", "values": ["visible", "partial", "indeterminate"]},
        {"name": "identity_status", "input_type": "select", "mutable": False,
         "default_value": "provisional", "values": ["provisional", "confirmed"]},
    ],
}]
DEMO_LABELS = [{"name": DEMO_LABEL, "type": "polygon", "attributes": []}]
SCENES = [
    {"file_name": "synthetic_train_a.png", "split": "train",
     "session_group": "synthetic_scene_train_a", "bbox": [16, 16, 64, 48],
     "background": [35, 45, 65], "foreground": [230, 60, 40]},
    {"file_name": "synthetic_train_b.png", "split": "train",
     "session_group": "synthetic_scene_train_b", "bbox": [48, 12, 48, 64],
     "background": [50, 70, 30], "foreground": [30, 180, 210]},
    {"file_name": "synthetic_valid_a.png", "split": "valid",
     "session_group": "synthetic_scene_valid_a", "bbox": [24, 40, 80, 32],
     "background": [85, 30, 55], "foreground": [200, 210, 35]},
    {"file_name": "synthetic_valid_b.png", "split": "valid",
     "session_group": "synthetic_scene_valid_b", "bbox": [64, 24, 32, 56],
     "background": [20, 85, 95], "foreground": [210, 90, 170]},
]


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def polygon(scene):
    x, y, width, height = scene["bbox"]
    return [x, y, x + width, y, x + width, y + height, x, y + height]


def synthetic_png(scene):
    def chunk(kind, payload):
        checksum = zlib.crc32(kind + payload) & 0xffffffff
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", checksum)

    x0, y0, width, height = scene["bbox"]
    raw = bytearray()
    for y in range(HEIGHT):
        raw.append(0)
        for x in range(WIDTH):
            raw.extend(scene["foreground"] if x0 <= x < x0 + width and y0 <= y < y0 + height
                       else scene["background"])
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw))) + chunk(b"IEND", b""))


def multipart(fields, files):
    """Small local uploads only; generated names never contain header controls."""
    boundary = "app2-" + uuid.uuid4().hex
    body = bytearray()
    for name, value in fields.items():
        body.extend((f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n'
                     f"\r\n{value}\r\n").encode())
    for field, filename, mime, content in files:
        require(re.fullmatch(r"[A-Za-z0-9_.\[\]-]+", field) is not None,
                "Invalid generated upload field")
        require(re.fullmatch(r"[A-Za-z0-9_.-]+", filename) is not None,
                "Invalid generated upload filename")
        body.extend((f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; '
                     f'filename="{filename}"\r\nContent-Type: {mime}\r\n\r\n').encode())
        body.extend(content)
        body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode())
    return bytes(body), f"multipart/form-data; boundary={boundary}"


def collection(api, path):
    result = []
    for _ in range(100):
        page = api.request("GET", path)
        if isinstance(page, list):
            return result + page
        require(isinstance(page, dict) and isinstance(page.get("results"), list),
                "Unexpected CVAT collection response")
        result.extend(page["results"])
        path = page.get("next")
        if not path:
            return result
    raise RuntimeError("CVAT collection exceeded the bounded page limit")


def normalized_labels(labels):
    normalized = []
    for label in labels:
        attrs = [{key: a.get(key) for key in
                  ("name", "input_type", "mutable", "default_value", "values")}
                 for a in label.get("attributes", [])]
        normalized.append({"name": label["name"], "type": label.get("type"),
                           "attributes": sorted(attrs, key=lambda a: a["name"])})
    return sorted(normalized, key=lambda label: label["name"])


def ensure_project(api, name, labels, user_id):
    query = urllib.parse.urlencode({"search": name, "page_size": 100})
    matches = [project for project in collection(api, "/api/projects?" + query)
               if project["name"] == name]
    require(len(matches) <= 1, "Duplicate project name; refusing ambiguous reuse")
    created = not matches
    if created:
        project = api.request("POST", "/api/projects", data={"name": name, "labels": labels},
                              expected=(201,))
    else:
        project = matches[0]
        owner = project.get("owner")
        require(isinstance(owner, dict) and owner.get("id") == user_id,
                "Named project belongs to another owner; refusing reuse")
    project_id = int(project["id"])
    actual = collection(api, f"/api/labels?project_id={project_id}&page_size=100")
    require(normalized_labels(actual) == normalized_labels(labels),
            "Project ontology differs; no existing labels were changed")
    return {"id": project_id, "name": name, "created": created,
            "schema_verified": True, "url": api.base + f"/projects/{project_id}"}


def safe_name(value):
    name = PurePosixPath(value.replace("\\", "/")).name
    require(name in {scene["file_name"] for scene in SCENES},
            "Unexpected synthetic image name in CVAT response")
    return name


def task_frames(api, task_id):
    task = api.request("GET", f"/api/tasks/{task_id}")
    require(task["size"] == len(SCENES), "Unexpected synthetic task image count")
    meta = api.request("GET", f"/api/tasks/{task_id}/data/meta")
    require(meta.get("start_frame", 0) == 0 and len(meta.get("frames", [])) == len(SCENES),
            "Unexpected synthetic frame metadata")
    frames = {index: safe_name(frame["name"]) for index, frame in enumerate(meta["frames"])}
    require(len(set(frames.values())) == len(SCENES), "Repeated synthetic frame filename")
    require(all((frame["width"], frame["height"]) == (WIDTH, HEIGHT)
                for frame in meta["frames"]), "Unexpected synthetic frame dimensions")
    return frames


def create_task(api, project_id, name, images, timeout, receipt, key):
    task = api.request("POST", "/api/tasks", data={"name": name, "project_id": project_id},
                       expected=(201,))
    task_id = int(task["id"])
    receipt[key] = {"id": task_id, "name": name, "project_id": project_id,
                    "url": api.base + f"/tasks/{task_id}", "retained": True}
    save_receipt(receipt)
    files = [(f"client_files[{index}]", scene["file_name"], "image/png", images[scene["file_name"]])
             for index, scene in enumerate(SCENES)]
    data, content_type = multipart({"image_quality": "100", "sorting_method": "lexicographical"}, files)
    upload = api.request("POST", f"/api/tasks/{task_id}/data", data=data,
                         content_type=content_type, expected=(202,))
    receipt[key]["upload_rq_id"] = upload["rq_id"]
    save_receipt(receipt)
    api.wait(upload["rq_id"], timeout)
    return task_id, task_frames(api, task_id)


def label_id(api, task_id):
    labels = collection(api, f"/api/labels?task_id={task_id}&page_size=100")
    require(normalized_labels(labels) == normalized_labels(DEMO_LABELS),
            "Synthetic task labels differ from the isolated demo ontology")
    return int(labels[0]["id"])


def pixel_mask(polygons):
    require(isinstance(polygons, list) and bool(polygons), "Expected polygon segmentation")
    require(all(isinstance(p, list) and len(p) >= 6 and len(p) % 2 == 0
                and all(isinstance(v, (int, float)) and math.isfinite(v) for v in p)
                for p in polygons), "Invalid synthetic polygon")
    return {(x, y) for y in range(HEIGHT) for x in range(WIDTH)
            if any(inside(x + 0.5, y + 0.5, p) for p in polygons)}


def verify_annotations(api, task_id, frames):
    saved = api.request("GET", f"/api/tasks/{task_id}/annotations")
    shapes = saved.get("shapes", [])
    require(len(shapes) == len(SCENES) and not saved.get("tags") and not saved.get("tracks"),
            "Expected exactly four synthetic polygon annotations")
    expected = {scene["file_name"]: scene for scene in SCENES}
    seen = set()
    expected_label_id = label_id(api, task_id)
    details = {}
    for shape in shapes:
        frame = shape.get("frame")
        require(frame in frames and frame not in seen, "Unexpected or repeated annotation frame")
        seen.add(frame)
        name = frames[frame]
        require(shape.get("type") == "polygon" and shape["label_id"] == expected_label_id
                and not shape.get("outside") and not shape.get("occluded")
                and shape.get("rotation", 0) == 0, "Unexpected synthetic annotation properties")
        actual = pixel_mask([shape["points"]])
        require(actual == pixel_mask([polygon(expected[name])]),
                "Saved or reimported contour differs from synthetic ground truth")
        details[name] = {"frame": frame, "mask_pixels": len(actual), "contour_mask_exact": True}
    return {"images": len(frames), "instances": len(shapes), "images_verified": details}


def verify_export(archive, images):
    expected = {scene["file_name"]: scene for scene in SCENES}
    with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
        docs = [name for name in zipped.namelist()
                if name.startswith("annotations/") and name.endswith(".json")]
        require(len(docs) == 1, "Expected a single synthetic COCO annotation document")
        coco = json.loads(zipped.read(docs[0]))
        require(len(coco["images"]) == len(SCENES)
                and len(coco["annotations"]) == len(SCENES), "COCO image/instance count differs")
        categories = coco["categories"]
        require(len(categories) == 1 and categories[0]["name"] == DEMO_LABEL,
                "COCO category differs from the synthetic-only label")
        by_id = {image["id"]: safe_name(image["file_name"]) for image in coco["images"]}
        require(len(by_id) == len(SCENES) and set(by_id.values()) == set(expected),
                "COCO image identities differ")
        media = [name for name in zipped.namelist()
                 if name.startswith("images/") and not name.endswith("/")]
        require(len(media) == len(SCENES), "COCO export omitted synthetic image data")
        for name in media:
            require(zipped.read(name) == images[safe_name(name)],
                    "Exported original PNG bytes changed")
        require(all((image["width"], image["height"]) == (WIDTH, HEIGHT)
                    for image in coco["images"]), "COCO image dimensions differ")
        seen = set()
        details = {}
        for annotation in coco["annotations"]:
            name = by_id.get(annotation["image_id"])
            require(name is not None and name not in seen, "COCO instance image differs or repeats")
            seen.add(name)
            require(annotation["category_id"] == categories[0]["id"]
                    and not annotation.get("iscrowd", 0), "COCO instance category or crowd differs")
            actual = pixel_mask(annotation["segmentation"])
            require(actual == pixel_mask([polygon(expected[name])]),
                    "COCO polygon mask differs from synthetic ground truth")
            require(len(annotation["bbox"]) == 4
                    and all(abs(float(a) - b) <= 1 for a, b in
                            zip(annotation["bbox"], expected[name]["bbox"])), "COCO bounding box differs")
            require(abs(float(annotation["area"]) - len(actual)) <= 1, "COCO area differs")
            details[name] = {"mask_pixels": len(actual), "contour_mask_exact": True,
                             "image_sha256": hashlib.sha256(images[name]).hexdigest()}
    return {"images": len(SCENES), "instances": len(SCENES), "category": DEMO_LABEL,
            "images_verified": details}


def save_receipt(receipt):
    path = Path(receipt["output_dir"]) / "cvat-demo-result.json"
    temporary = path.with_name("." + path.name + ".tmp")
    temporary.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)


def run(api, args, receipt):
    mode = args.credentials.stat().st_mode
    require(stat.S_ISREG(mode) and not stat.S_IMODE(mode) & 0o077,
            "Credentials file must be a private regular file (0600)")
    credentials = json.loads(args.credentials.read_text())
    login = api.request("POST", "/api/auth/login", data={
        "username": credentials["username"], "password": credentials["password"]})
    api.token = login["key"]
    del credentials, login
    user = api.request("GET", "/api/users/self")
    receipt["server_version"] = api.request("GET", "/api/server/about").get("version")
    require(receipt["server_version"] == "2.79.0", "This recipe requires verified CVAT 2.79.0")
    receipt["project"] = ensure_project(api, REAL_PROJECT, REAL_LABELS, user["id"])
    receipt["project"]["identity_is_provisional"] = True
    receipt["project"]["confirmed_reference_policy"] = (
        "Use confirmed only after documented client ground truth; no reference is assigned by this demo")
    save_receipt(receipt)
    receipt["demo_project"] = ensure_project(api, DEMO_PROJECT, DEMO_LABELS, user["id"])
    save_receipt(receipt)
    images = {scene["file_name"]: synthetic_png(scene) for scene in SCENES}
    require(len({hashlib.sha256(image).hexdigest() for image in images.values()}) == len(SCENES),
            "Synthetic PNG scenes must have distinct bytes")
    image_dir = args.output_dir / "synthetic-images"
    image_dir.mkdir(exist_ok=False)
    for name, content in images.items():
        (image_dir / name).write_bytes(content)
    split_manifest = {"schema_version": SCHEMA_VERSION, "synthetic_only": True, "images": {
        scene["file_name"]: {"split": scene["split"], "session_group": scene["session_group"]}
        for scene in SCENES}}
    (args.output_dir / "split-manifest.json").write_text(json.dumps(split_manifest, indent=2) + "\n")
    receipt["split_manifest"] = str(args.output_dir / "split-manifest.json")
    receipt["synthetic_group_note"] = (
        "Four separately generated synthetic scenes, not physical acquisition sessions or real validation")
    demo_task_id, frames = create_task(
        api, receipt["demo_project"]["id"], "SYNTHETIC ONLY app2 demo " + receipt["run_id"],
        images, args.timeout, receipt, "demo_task")
    expected_label_id = label_id(api, demo_task_id)
    by_name = {scene["file_name"]: scene for scene in SCENES}
    api.request("PUT", f"/api/tasks/{demo_task_id}/annotations", data={
        "version": 0, "tags": [], "tracks": [], "shapes": [{
            "type": "polygon", "frame": frame, "label_id": expected_label_id,
            "points": polygon(by_name[name]), "occluded": False, "outside": False,
            "z_order": 0, "rotation": 0, "attributes": [], "source": "manual"}
            for frame, name in frames.items()]})
    receipt["save_annotations"] = verify_annotations(api, demo_task_id, frames)
    query = urllib.parse.urlencode({"format": "COCO 1.0", "save_images": "true", "location": "local"})
    export = api.request("POST", f"/api/tasks/{demo_task_id}/dataset/export?{query}", expected=(202,))
    receipt["export_rq_id"] = export["rq_id"]
    save_receipt(receipt)
    ready = api.wait(export["rq_id"], args.timeout)
    archive = api.request("GET", ready["result_url"], raw=True)
    (args.output_dir / "cvat-export.zip").write_bytes(archive)
    receipt["coco_export"] = verify_export(archive, images)
    receipt["export_sha256"] = hashlib.sha256(archive).hexdigest()
    receipt["export_file"] = str(args.output_dir / "cvat-export.zip")
    save_receipt(receipt)
    reimport_id, reimport_frames = create_task(
        api, receipt["demo_project"]["id"], "SYNTHETIC ONLY reimport " + receipt["run_id"],
        images, args.timeout, receipt, "reimport_task")
    receipt["reimport"] = {"status": "PENDING", "attempted": True}
    save_receipt(receipt)
    data, content_type = multipart({}, [("annotation_file", "cvat-export.zip", "application/zip", archive)])
    query = urllib.parse.urlencode({"format": "COCO 1.0", "location": "local",
                                   "use_default_location": "false"})
    imported = api.request("POST", f"/api/tasks/{reimport_id}/annotations?{query}",
                           data=data, content_type=content_type, expected=(202,))
    require(isinstance(imported, dict) and imported.get("rq_id"),
            "Annotation import did not return a background request ID")
    receipt["reimport"]["rq_id"] = imported["rq_id"]
    save_receipt(receipt)
    api.wait(imported["rq_id"], args.timeout)
    receipt["reimport"].update(verify_annotations(api, reimport_id, reimport_frames))
    receipt["reimport"]["status"] = "VERIFIED"
    receipt["success"] = True


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default="http://localhost:18080")
    parser.add_argument("--credentials", type=Path, default=Path.home() / "app2/secrets/cvat-admin.json")
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="Private output directory; generated files must not already exist")
    parser.add_argument("--run-id", help="Unique letters/digits/underscore/hyphen run name")
    parser.add_argument("--timeout", type=int, default=300, help="Seconds per background operation")
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", run_id):
        parser.error("--run-id must contain only letters, digits, underscores and hyphens")
    os.umask(0o077)
    args.output_dir = args.output_dir.expanduser().resolve()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    targets = ["cvat-demo-result.json", "synthetic-images", "split-manifest.json", "cvat-export.zip"]
    if any((args.output_dir / target).exists() for target in targets):
        parser.error("Output files already exist; choose a new private directory")
    receipt = {"schema_version": SCHEMA_VERSION, "run_id": run_id,
               "output_dir": str(args.output_dir), "synthetic_only": True,
               "success": False, "real_images_uploaded": 0, "tasks_deleted": 0,
               "reimport": {"status": "PENDING", "attempted": False}}
    exit_code = 1
    try:
        save_receipt(receipt)
        run(API(args.base_url), args, receipt)
        exit_code = 0
    except (Exception, KeyboardInterrupt) as error:
        receipt["error_type"] = type(error).__name__
        # The API helper suppresses HTTP bodies/headers. Never serialize other
        # exception text, credentials, environment variables or authentication data.
        receipt["error"] = str(error) if isinstance(error, RuntimeError) else "See error_type"
    finally:
        save_receipt(receipt)
    print(json.dumps(receipt, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
