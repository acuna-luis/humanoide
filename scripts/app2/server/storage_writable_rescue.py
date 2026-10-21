#!/usr/bin/env python3
"""Cold rescue of existing overlay2 writable diffs; no Docker, repair or firmware.

The checksum-pinned storage_rescue.py must sit beside this wrapper. Root modes
temporarily mount the known SSD read-only/noload and normally unmount it again.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pwd
import re
import stat
import subprocess
import sys
import tempfile

BASE_SHA256 = "ec8e727b23d2288ac46be24d4c0ab8867f46100a38a9578ec83a781cebffcee8"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
EXPECTED_CONTAINERS = 20
MAX_METADATA_BYTES = 64 * 1024 ** 2


def load_base():
    path = Path(__file__).absolute().with_name("storage_rescue.py")
    if path.is_symlink() or not path.is_file():
        raise ValueError("Expected non-symlink base helper is missing")
    if hashlib.sha256(path.read_bytes()).hexdigest() != BASE_SHA256:
        raise ValueError("Base rescue helper checksum changed; review before proceeding")
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("app2_storage_rescue_pinned", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def hex_id(value):
    if not isinstance(value, str) or not HEX64.fullmatch(value):
        raise ValueError("Expected exactly one lowercase 64-hex identifier")
    return value


def guarded(path, mountpoint, base, directory=False, maximum=16 * 1024 ** 2):
    relative = path.relative_to(mountpoint)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Traversal in source path")
    base.no_symlink_path(path)
    info = path.lstat()
    expected = stat.S_ISDIR if directory else stat.S_ISREG
    if not expected(info.st_mode) or info.st_dev != mountpoint.stat().st_dev:
        raise ValueError("Unexpected source type or filesystem")
    if not directory and (info.st_size < 0 or info.st_size > maximum):
        raise ValueError("Metadata exceeds bounded read")
    return info


def inventory(mountpoint, base, expected=EXPECTED_CONTAINERS):
    containers = mountpoint / "containers"
    guarded(containers, mountpoint, base, directory=True)
    entries = sorted(containers.iterdir())
    if len(entries) > 1000 or len(entries) != expected:
        raise ValueError("Container count differs from the reviewed cold inventory")
    paths, rows, seen_layers = set(), [], set()
    metadata_bytes, total_allocated, total_logical = 0, 0, 0

    def metadata(path, maximum=16 * 1024 ** 2):
        nonlocal metadata_bytes
        info = guarded(path, mountpoint, base, maximum=maximum)
        relative = str(path.relative_to(mountpoint))
        if relative not in paths:
            metadata_bytes += max(info.st_size, info.st_blocks * 512)
            if metadata_bytes > MAX_METADATA_BYTES:
                raise ValueError("Container/layer/image metadata exceeds rescue allowance")
            paths.add(relative)
        return path.read_bytes()

    for container in entries:
        container_id = hex_id(container.name)
        guarded(container, mountpoint, base, directory=True)
        config = json.loads(metadata(container / "config.v2.json"))
        metadata(container / "hostconfig.json")
        if config.get("ID") != container_id or config.get("Driver") != "overlay2":
            raise ValueError("Container identity or storage driver differs from reviewed overlay2")
        image = config.get("Image")
        if not isinstance(image, str) or not image.startswith("sha256:"):
            raise ValueError("Container image is not a content-addressed sha256 ID")
        image_id = hex_id(image.removeprefix("sha256:"))
        image_path = mountpoint / "image/overlay2/imagedb/content/sha256" / image_id
        if hashlib.sha256(metadata(image_path)).hexdigest() != image_id:
            raise ValueError("Image configuration content differs from its sha256 ID")
        mapping = mountpoint / "image/overlay2/layerdb/mounts" / container_id
        guarded(mapping, mountpoint, base, directory=True)
        mapping_files = sorted(mapping.iterdir())
        if not mapping_files or len(mapping_files) > 8:
            raise ValueError("Unexpected layerdb mount mapping inventory")
        layer_id = hex_id(metadata(mapping / "mount-id", maximum=100).decode("ascii").strip())
        if layer_id in seen_layers:
            raise ValueError("Two containers unexpectedly share one writable layer")
        seen_layers.add(layer_id)
        for entry in mapping_files:
            if entry.name not in {"mount-id", "init-id", "parent"}:
                raise ValueError("Unexpected layerdb mapping filename")
            value = metadata(entry, maximum=256).decode("ascii").strip()
            if entry.name == "mount-id":
                if value != layer_id:
                    raise ValueError("Writable mapping changed during inventory")
            elif entry.name == "init-id":
                hex_id(value.removesuffix("-init"))
            else:
                hex_id(value.removeprefix("sha256:"))
        diff = mountpoint / "overlay2" / layer_id / "diff"
        guarded(diff, mountpoint, base, directory=True)
        sizes = base.size_tree(diff)
        if any(not isinstance(sizes.get(key), int) or sizes[key] < 0
               for key in ("allocated_bytes", "logical_bytes")):
            raise ValueError("Invalid writable layer size")
        total_allocated += sizes["allocated_bytes"]
        total_logical += sizes["logical_bytes"]
        relative = str(diff.relative_to(mountpoint))
        paths.add(relative)
        rows.append({"container_id": container_id, "layer_id": layer_id,
                     "image_id": image, "diff": relative, **sizes})
    return {"container_count": len(rows), "containers": rows, "tar_paths": sorted(paths),
            "metadata_bytes": metadata_bytes, "allocated_bytes": total_allocated,
            "logical_bytes": total_logical,
            "scope": "existing_overlay2_writable_diffs_and_referenced_metadata",
            "not_included": ["immutable_image_layers", "container_logs", "complete_docker_root"]}


def estimate(report, free_bytes, reserve):
    amount = report["metadata_bytes"] + sum(max(row["allocated_bytes"], row["logical_bytes"])
                                          for row in report["containers"])
    result = amount + max(1024 ** 3, amount // 10)
    if free_bytes - result < reserve:
        raise ValueError("Writable rescue does not fit while preserving 16 GiB free")
    return result


def backup(mounted, source, root_device, report, base):
    base.no_symlink_path(base.RECOVERY)
    user = pwd.getpwnam("luisacuna")
    info = base.RECOVERY.stat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != user.pw_uid
            or stat.S_IMODE(info.st_mode) != 0o700 or info.st_dev != root_device):
        raise ValueError("Expected private recovery destination on healthy OS is absent")
    free = os.statvfs(base.RECOVERY).f_bavail * os.statvfs(base.RECOVERY).f_frsize
    planned = estimate(report, free, base.RESERVE)
    dest = Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime("writable-%Y%m%dT%H%M%SZ-"),
                                 dir=base.RECOVERY))
    print(f"BACKUP={dest}", flush=True)
    receipt = {"status": "IN_PROGRESS", "source_serial": base.DATA_SERIAL,
               "source_uuid": base.UUID, "source_device": source["name"],
               "estimate_bytes": planned, "inventory": report, "archives": [],
               "full_ssd_backup": False,
               "firmware_gate": "NOT_CLEARED_EXTERNAL_COPY_RESTORE_CONSOLE_PENDING"}
    base.save_json(dest / "receipt.json", receipt)
    try:
        free = os.statvfs(dest).f_bavail * os.statvfs(dest).f_frsize
        estimate(report, free, base.RESERVE)
        limit = free - base.RESERVE - 64 * 1024 ** 2
        receipt["archives"].append(base.archive(mounted, ["./" + name for name in report["tar_paths"]],
                                               dest / "writable-layers.tar", file_limit=limit))
        receipt["status"] = "ARCHIVE_COMPARED_PENDING_EXTERNAL_COPY_AND_RESTORE_TEST"
        base.save_json(dest / "receipt.json", receipt)
    except BaseException:
        receipt["status"] = "FAILED_PARTIAL_PRESERVED"
        base.save_json(dest / "receipt.json", receipt)
        raise
    finally:
        for path in dest.iterdir():
            os.chmod(path, 0o600)
            os.chown(path, user.pw_uid, user.pw_gid)
        os.chmod(dest, 0o700)
        os.chown(dest, user.pw_uid, user.pw_gid)
    return {"backup": str(dest), "status": receipt["status"], "archives": receipt["archives"],
            "firmware_gate": receipt["firmware_gate"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--inventory", action="store_true")
    modes.add_argument("--backup", action="store_true")
    args = parser.parse_args()
    try:
        base = load_base()
        source, root_device = base.preflight()
        if os.geteuid() != 0:
            raise ValueError("Temporary read-only rescue requires operator root")
        with base.readonly_source(source) as mounted:
            report = inventory(mounted, base)
            free = os.statvfs(base.APP2).f_bavail * os.statvfs(base.APP2).f_frsize
            try:
                planned = estimate(report, free, base.RESERVE)
                report["backup_plan"] = {"fits": True, "estimate_bytes": planned,
                                         "free_bytes": free, "reserve_bytes": base.RESERVE}
            except ValueError as error:
                report["backup_plan"] = {"fits": False, "reason": str(error), "free_bytes": free}
            result = backup(mounted, source, root_device, report, base) if args.backup else report
        result["source_unmounted"] = True
        print(json.dumps(result, indent=2))
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        # Avoid printing unfiltered paths/content from a corrupt filesystem or tar stderr.
        parser.exit(1, f"WRITABLE_RESCUE_FAILED: {type(error).__name__}; preserve partial files and guards\n")


if __name__ == "__main__":
    main()
