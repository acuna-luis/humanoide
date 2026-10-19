#!/usr/bin/env python3
"""Validate a small, real APP2 image batch and optionally import it into CVAT.

The default --check is entirely local. --import creates one new, unannotated
task in the already existing, owner-checked app2-itr-v0 project. It never
creates projects, edits labels/annotations, deletes tasks, or trains a model.
Run on the server with PYTHONPATH=$HOME/app2/setup/cvat:$HOME/app2/workflow.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import sys
import urllib.parse
import zlib


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server" / "cvat"))
from cvat_demo import (  # noqa: E402
    API, REAL_LABELS, REAL_PROJECT, collection, multipart, normalized_labels,
)


MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
MAX_MANIFEST_BYTES = 1024 * 1024
RECEIPT_NAME = "real-images-import-result.json"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def regular_path(path, description):
    """Reject symlinks in every component before reading a local regular file."""
    path = Path(os.path.abspath(path))
    for component in (*reversed(path.parents), path):
        require(not component.is_symlink(), description + " must not use symlinks")
    require(path.is_file() and stat.S_ISREG(path.stat().st_mode),
            description + " must be a regular file")
    return path


def read_bounded(path, limit, description):
    path = regular_path(path, description)
    require(path.stat().st_size <= limit, description + " exceeds the allowed byte limit")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags), "rb") as source:
        require(stat.S_ISREG(os.fstat(source.fileno()).st_mode),
                description + " must remain a regular file")
        content = source.read(limit + 1)
    require(len(content) <= limit, description + " exceeds the allowed byte limit")
    return path, content


def no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON object key")
        result[key] = value
    return result


def load_json(content):
    return json.loads(content.decode("utf-8"), object_pairs_hook=no_duplicate_keys)


def png_dimensions(content):
    require(len(content) >= 33 and content[:8] == b"\x89PNG\r\n\x1a\n"
            and content[8:12] == struct.pack(">I", 13) and content[12:16] == b"IHDR",
            "Expected a PNG with the standard IHDR header")
    require(struct.unpack(">I", content[29:33])[0]
            == zlib.crc32(content[12:29]) & 0xffffffff, "PNG IHDR checksum mismatch")
    width, height = struct.unpack(">II", content[16:24])
    require(0 < width <= 20000 and 0 < height <= 20000 and width * height <= 100_000_000,
            "PNG dimensions exceed the bounded pilot size")
    return width, height


def validate_manifest(manifest_path):
    manifest_path, content = read_bounded(manifest_path, MAX_MANIFEST_BYTES, "Manifest")
    manifest = load_json(content)
    require(isinstance(manifest, dict), "Manifest must be a JSON object")
    require(type(manifest.get("schema_version")) is int and manifest["schema_version"] == 1,
            "Expected schema_version 1")
    require(manifest.get("synthetic") is False, "Real image manifest must declare synthetic=false")
    require("material_id" in manifest and manifest["material_id"] is None,
            "Unconfirmed pilot must explicitly declare material_id=null")
    require(all(manifest.get(key) is None for key in ("split", "splits", "partition")),
            "This single-scene importer does not assign training/validation splits")
    require(manifest.get("label", "itr_candidate") == "itr_candidate"
            and manifest.get("identity_status", "provisional") == "provisional",
            "This pilot only accepts itr_candidate with provisional identity")
    name = manifest.get("task_name")
    require(isinstance(name, str) and 1 <= len(name) <= 200
            and name == name.strip() and not any(ord(c) < 32 or ord(c) == 127 for c in name)
            and "synthetic" not in name.lower(), "Expected a distinctive real-image task_name")
    group = manifest.get("session_group")
    require(isinstance(group, str) and re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", group),
            "Expected an explicit ASCII session_group shared by these views")
    entries = manifest.get("images")
    require(isinstance(entries, list) and 1 <= len(entries) <= 100,
            "Manifest must contain between 1 and 100 images")
    names, hashes, paths = set(), set(), set()
    validated, blobs, total = [], {}, 0
    for entry in entries:
        require(isinstance(entry, dict), "Each image must be a JSON object")
        require(all(entry.get(key) is None for key in ("split", "splits", "partition")),
                "Image split assignment is forbidden in this annotation-only import")
        require(entry.get("material_id") is None
                and entry.get("identity_status", "provisional") == "provisional",
                "Individual images cannot claim a confirmed material identity")
        require("session_group" not in entry or entry["session_group"] == group,
                "All views must share the manifest session_group")
        filename = entry.get("file_name")
        require(isinstance(filename, str)
                and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,195}\.png", filename),
                "Image file_name must be a safe ASCII PNG basename")
        require(filename not in names, "Repeated image file_name")
        expected_hash = entry.get("sha256")
        require(isinstance(expected_hash, str) and re.fullmatch(r"[0-9a-f]{64}", expected_hash),
                "Every image needs its original lowercase SHA256")
        local = entry.get("local_path")
        require(isinstance(local, str) and bool(local) and "\x00" not in local,
                "Every image needs an explicit local_path")
        path = Path(local).expanduser()
        if not path.is_absolute():
            path = manifest_path.parent / path
        path, image = read_bounded(path, MAX_FILE_BYTES, "Image")
        require(path not in paths, "Repeated local image path")
        actual_hash = hashlib.sha256(image).hexdigest()
        require(actual_hash == expected_hash, "Image SHA256 differs from the original manifest")
        require(actual_hash not in hashes, "Duplicate image bytes in the pilot")
        dimensions = png_dimensions(image)
        require(all(type(entry.get(key)) is int for key in ("width", "height"))
                and dimensions == (entry["width"], entry["height"]),
                "PNG header dimensions differ from the manifest")
        source_kind = entry.get("source_kind")
        require(isinstance(source_kind, str) and 1 <= len(source_kind) <= 200
                and not any(ord(c) < 32 for c in source_kind)
                and "synthetic" not in source_kind.lower(),
                "Each real image requires its non-synthetic source_kind")
        total += len(image)
        require(total <= MAX_TOTAL_BYTES, "Batch exceeds the 64 MiB upload limit")
        names.add(filename)
        hashes.add(actual_hash)
        paths.add(path)
        blobs[filename] = image
        validated.append({"file_name": filename, "local_path": str(path),
                          "sha256": actual_hash, "bytes": len(image),
                          "width": dimensions[0], "height": dimensions[1],
                          "source_kind": source_kind, "session_group": group,
                          "annotation_review": "PENDING", "identity_status": "provisional"})
    return manifest, blobs, {"manifest_path": str(manifest_path),
                            "manifest_sha256": hashlib.sha256(content).hexdigest(),
                            "image_count": len(validated), "total_bytes": total,
                            "images": validated, "validation": "PNG_HEADER_HASH_ONLY",
                            "decoded_image_review": "PENDING"}


def save_receipt(receipt):
    path = Path(receipt["output_dir"]) / RECEIPT_NAME
    temporary = path.with_name("." + path.name + ".tmp")
    with temporary.open("x", encoding="utf-8") as output:
        json.dump(receipt, output, indent=2, ensure_ascii=False)
        output.write("\n")
    temporary.replace(path)


def existing_project(api, user_id):
    query = urllib.parse.urlencode({"search": REAL_PROJECT, "page_size": 100})
    matches = [project for project in collection(api, "/api/projects?" + query)
               if project.get("name") == REAL_PROJECT]
    require(len(matches) == 1, "Expected one existing app2-itr-v0 project; no project was created")
    project = matches[0]
    owner = project.get("owner")
    require(isinstance(owner, dict) and owner.get("id") == user_id,
            "Real project owner differs from the authenticated user")
    project_id = int(project["id"])
    labels = collection(api, f"/api/labels?project_id={project_id}&page_size=100")
    require(normalized_labels(labels) == normalized_labels(REAL_LABELS),
            "Real project ontology differs; no labels were changed")
    return {"id": project_id, "name": REAL_PROJECT, "owner_id": user_id,
            "schema_verified": True, "created": False,
            "url": api.base + f"/projects/{project_id}"}


def verify_task(api, task_id, manifest):
    expected = {entry["file_name"]: entry for entry in manifest["images"]}
    task = api.request("GET", f"/api/tasks/{task_id}")
    require(task.get("size") == len(expected), "Imported real task image count differs")
    meta = api.request("GET", f"/api/tasks/{task_id}/data/meta")
    frames = meta.get("frames", [])
    require(meta.get("start_frame", 0) == 0 and len(frames) == len(expected),
            "Imported frame metadata differs")
    seen, details = set(), []
    for index, frame in enumerate(frames):
        name = frame.get("name")
        require(isinstance(name, str) and "\\" not in name and ".." not in PurePosixPath(name).parts,
                "Unexpected real frame filename")
        filename = PurePosixPath(name).name
        require(filename in expected and filename not in seen, "Unexpected or duplicate real frame")
        entry = expected[filename]
        require((frame.get("width"), frame.get("height")) == (entry["width"], entry["height"]),
                "Imported real frame dimensions differ")
        seen.add(filename)
        details.append({"frame": index, "file_name": filename,
                        "width": frame["width"], "height": frame["height"]})
    labels = collection(api, f"/api/labels?task_id={task_id}&page_size=100")
    require(normalized_labels(labels) == normalized_labels(REAL_LABELS),
            "Imported task ontology differs")
    annotations = api.request("GET", f"/api/tasks/{task_id}/annotations")
    require(all(annotations.get(key) == [] for key in ("shapes", "tracks", "tags")),
            "New task unexpectedly has annotations; preserved without alteration")
    jobs = collection(api, f"/api/jobs?task_id={task_id}&page_size=100")
    require(bool(jobs), "Imported task has no annotation job")
    return {"frames": details, "annotations": 0,
            "jobs": [{"id": int(job["id"]), "state": job.get("state"),
                      "url": api.base + f"/tasks/{task_id}/jobs/{int(job['id'])}"}
                     for job in jobs]}


def import_images(api, args, manifest, blobs, receipt):
    credentials_path = regular_path(args.credentials.expanduser(), "Credentials")
    file_stat = credentials_path.stat()
    require(stat.S_IMODE(file_stat.st_mode) == 0o600 and file_stat.st_uid == os.geteuid(),
            "Credentials must be owned by the current user with mode 0600")
    _, content = read_bounded(credentials_path, 16384, "Credentials")
    credentials = load_json(content)
    require(isinstance(credentials, dict)
            and all(isinstance(credentials.get(key), str) and credentials[key]
                    for key in ("username", "password")), "Invalid private credentials schema")
    login = api.request("POST", "/api/auth/login", data={
        "username": credentials["username"], "password": credentials["password"]})
    api.token = login["key"]
    del credentials, login, content
    user = api.request("GET", "/api/users/self")
    receipt["server_version"] = api.request("GET", "/api/server/about").get("version")
    require(receipt["server_version"] == "2.79.0", "This recipe requires verified CVAT 2.79.0")
    receipt["project"] = existing_project(api, user["id"])
    project_id = receipt["project"]["id"]
    query = urllib.parse.urlencode({"project_id": project_id,
                                    "search": manifest["task_name"], "page_size": 100})
    matches = [task for task in collection(api, "/api/tasks?" + query)
               if task.get("name") == manifest["task_name"]
               and task.get("project_id") == project_id]
    require(not matches, "Task with this name already exists in the real project; choose a new name")
    save_receipt(receipt)
    task = api.request("POST", "/api/tasks", data={"name": manifest["task_name"],
                                                               "project_id": project_id}, expected=(201,))
    task_id = int(task["id"])
    receipt["created_task_id"] = task_id
    receipt["task"] = {"id": task_id, "name": manifest["task_name"], "project_id": project_id,
                       "url": api.base + f"/tasks/{task_id}", "retained": True}
    save_receipt(receipt)
    files = [(f"client_files[{index}]", name, "image/png", blobs[name])
             for index, name in enumerate(sorted(blobs))]
    body, content_type = multipart({"image_quality": "100", "sorting_method": "lexicographical"}, files)
    upload = api.request("POST", f"/api/tasks/{task_id}/data", data=body,
                         content_type=content_type, expected=(202,))
    require(isinstance(upload, dict) and bool(upload.get("rq_id")), "Upload request ID is missing")
    receipt["upload_rq_id"] = upload["rq_id"]
    save_receipt(receipt)
    api.wait(upload["rq_id"], args.timeout)
    receipt["verification"] = verify_task(api, task_id, manifest)
    receipt["real_images_uploaded"] = len(blobs)
    receipt["status"] = "IMPORTED_UNANNOTATED_REVIEW_PENDING"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path,
                        help="Private directory for a new receipt; never overwrite an existing receipt")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="Default: local validation only, no CVAT API calls")
    mode.add_argument("--import", dest="do_import", action="store_true", help="Create a new unannotated real task")
    parser.add_argument("--credentials", type=Path, default=Path.home() / "app2/secrets/cvat-admin.json")
    parser.add_argument("--base-url", default="http://localhost:18080")
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    os.umask(0o077)
    output_dir = Path(os.path.abspath(args.output_dir.expanduser()))
    for component in (*reversed(output_dir.parents), output_dir):
        if component.is_symlink():
            parser.error("Private output directory must not use symlinks")
    output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not output_dir.is_dir() or stat.S_IMODE(output_dir.stat().st_mode) & 0o077:
        parser.error("Output directory must be private (0700)")
    if any((output_dir / name).exists() or (output_dir / name).is_symlink()
           for name in (RECEIPT_NAME, "." + RECEIPT_NAME + ".tmp")):
        parser.error("Output receipt already exists; choose a new private directory")
    receipt = {"schema_version": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
               "output_dir": str(output_dir), "mode": "import" if args.do_import else "check",
               "success": False, "synthetic": False, "material_id": None,
               "identity_status": "provisional", "annotation_review": "PENDING",
               "split_assignment": "NOT_ASSIGNED", "training_started": False,
               "created_task_id": None, "real_images_uploaded": 0, "tasks_deleted": 0,
               "project_or_labels_modified": False, "robot_controls_connected": False}
    code = 1
    try:
        save_receipt(receipt)
        manifest, blobs, validation = validate_manifest(args.manifest.expanduser())
        receipt.update(validation)
        receipt["task_name"] = manifest["task_name"]
        receipt["session_group"] = manifest["session_group"]
        receipt["provisional_label"] = "itr_candidate"
        if args.do_import:
            import_images(API(args.base_url), args, manifest, blobs, receipt)
        else:
            receipt["status"] = "LOCAL_CHECK_PASS_NO_API_CALLS"
        receipt["success"] = True
        code = 0
    except (Exception, KeyboardInterrupt) as error:
        receipt["error_type"] = type(error).__name__
        # API RuntimeErrors omit HTTP bodies, headers and credentials. Do not
        # serialize other exception text, environments or private auth values.
        receipt["error"] = str(error) if isinstance(error, RuntimeError) else "See error_type"
        receipt["status"] = "FAILED_TASK_RETAINED" if receipt["created_task_id"] else "FAILED_NO_TASK_CREATED"
    finally:
        save_receipt(receipt)
    print(json.dumps(receipt, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
