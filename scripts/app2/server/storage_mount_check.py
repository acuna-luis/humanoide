#!/usr/bin/env python3
"""Default/--check: read-only mount and existing-data gate before Docker on aisrv."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import stat
import subprocess
import sys

sys.dont_write_bytecode = True
BASE_SHA = "ec8e727b23d2288ac46be24d4c0ab8867f46100a38a9578ec83a781cebffcee8"
TARGET = Path("/var/lib/docker")
RECEIPT = Path("/home/luisacuna/app2/recovery/rescue-20261020T075927Z-boa8lm5f/receipt.json")
RECEIPT_SHA = "3e497d85e03a9aa42cea0c3462d64b6d612e4e00db35c2e8baee6e555237c4b3"


def validate_mount(source, root_device, rows, target_device):
    if (len(rows) != 1 or rows[0]["device"] != source["maj:min"]
            or rows[0]["type"] != "ext4" or "rw" not in rows[0]["options"]
            or {"ro", "noload", "norecovery"} & (rows[0]["options"] | rows[0]["fsoptions"])
            or target_device == root_device or target_device != source["maj:min"]):
        raise ValueError("Docker directory is not the exact identified read-write data mount")


def validate_tree(base, device, target=TARGET, receipt_path=RECEIPT):
    base.no_symlink_path(receipt_path)
    info = receipt_path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > 2 * 1024 ** 2:
        raise ValueError("Unexpected backup receipt")
    data = receipt_path.read_bytes()
    if hashlib.sha256(data).hexdigest() != RECEIPT_SHA:
        raise ValueError("Backup receipt checksum differs")
    receipt = json.loads(data)
    names = list(receipt["inventory"]["volumes"])
    if (receipt.get("source_uuid") != base.UUID or receipt.get("source_serial") != base.DATA_SERIAL
            or receipt.get("all_named_volumes_archived_and_compared") is not True or len(names) != 20
            or any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,254}", name) for name in names)):
        raise ValueError("Expected 20 backed-up volumes on the identified source")
    for path in [target / name for name in ("containers", "overlay2", "volumes")] + [
            target / "volumes" / name / "_data" for name in names]:
        base.no_symlink_path(path)
        info = path.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_dev != device:
            raise ValueError("Docker data directory missing, redirected or on a different filesystem")
    return len(names)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Read-only checks (default); creates nothing")
    parser.parse_args(argv)
    if os.geteuid() != 0:
        raise PermissionError("Root required for device identity and private Docker data checks")
    if socket.gethostname() != "aisrv":
        raise ValueError("Restricted to aisrv")
    path = Path(__file__).with_name("storage_rescue.py")
    if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != BASE_SHA:
        raise ValueError("Pinned storage identity helper differs")
    spec = importlib.util.spec_from_file_location("mount_check_rescue", path)
    base = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base)
    os.environ["PATH"] = "/usr/sbin:/usr/bin:/sbin:/bin"
    root = os.stat("/").st_dev
    root_device = f"{os.major(root)}:{os.minor(root)}"
    nodes = base.block_nodes(json.loads(base.command("lsblk", "--json", "--bytes", "--paths", "--output",
        "NAME,TYPE,PKNAME,SERIAL,UUID,FSTYPE,MAJ:MIN,SIZE")))
    source = base.identify_source(nodes, root_device)
    base.no_symlink_path(TARGET)
    rows = [row for row in base.parse_mounts(Path("/proc/self/mountinfo").read_text())
            if row["target"] == str(TARGET)]
    device = os.stat(TARGET).st_dev
    validate_mount(source, root_device, rows, f"{os.major(device)}:{os.minor(device)}")
    base.no_symlink_path(Path(source["name"]))
    probe = dict(line.split("=", 1) for line in base.command(
        "blkid", "-p", "-o", "export", source["name"]).splitlines() if "=" in line)
    if probe.get("UUID") != base.UUID or probe.get("TYPE") != "ext4":
        raise ValueError("Direct mounted-device UUID/type differs")
    count = validate_tree(base, device)
    print(json.dumps({"status": "DOCKER_DATA_MOUNT_VERIFIED_NO_START", "target": str(TARGET),
        "source": source["name"], "uuid": base.UUID, "serial": base.DATA_SERIAL,
        "filesystem": "ext4", "mode": "rw", "root_filesystem_excluded": True,
        "expected_volumes_present": count, "backup_receipt_sha256": RECEIPT_SHA}))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        sys.exit("MOUNT_CHECK_BLOCKED: " + str(error))
