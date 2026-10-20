#!/usr/bin/env python3
"""Selective cold rescue on aisrv; never repairs, starts Docker or updates firmware.

--check never mounts. Root --inventory/--backup temporarily mount ONLY the known
Docker partition read-only with journal replay disabled and always unmount normally.
An app2 backup is NOT a full SSD backup or authorization to update firmware.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import pwd
import resource
import socket
import stat
import subprocess
import sys
import tempfile

UUID = "b819b286-2006-4474-b2d5-13982b0f1536"
DATA_SERIAL = "S7DRNJ0X107187F"
OS_SERIAL = "S7DRNJ0X107095A"
APP2 = Path("/home/luisacuna/app2")
RECOVERY = APP2 / "recovery"
UNITS = ("docker.service", "docker.socket", "containerd.service",
         "var-lib-docker.mount", "var-lib-docker.automount")
CVAT = tuple("app2-cvat_cvat_" + suffix for suffix in
             ("cache_db", "data", "db", "events_db", "inmem_db", "keys", "logs"))
ESSENTIAL = CVAT + ("app2_datasets", "app2_checkpoints")
CACHE = "app2_training_cache"
RESERVE = 16 * 1024 ** 3


def command(*args, timeout=30, file_limit=None):
    limit = None if file_limit is None else lambda: resource.setrlimit(
        resource.RLIMIT_FSIZE, (file_limit, file_limit))
    return subprocess.run(args, check=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True, timeout=timeout,
                          preexec_fn=limit).stdout


def parse_mounts(text):
    result = []
    for line in text.splitlines():
        parts = line.split()
        sep = parts.index("-")
        result.append({"device": parts[2], "target": parts[4],
                       "options": set(parts[5].split(",")), "type": parts[sep + 1],
                       "fsoptions": set(parts[sep + 3].split(","))})
    return result


def block_nodes(tree):
    nodes = {}
    def walk(rows, parent=None):
        for row in rows:
            item = dict(row)
            item["parent"] = row.get("pkname") or parent
            nodes[item["name"]] = item
            walk(row.get("children", []), item["name"])
    walk(tree["blockdevices"])
    return nodes


def disk_serial(node, nodes):
    seen = set()
    while node["name"] not in seen:
        seen.add(node["name"])
        if node["type"] == "disk":
            return (node.get("serial") or "").strip()
        node = nodes.get(node.get("parent"), {})
        if not node:
            break
    raise ValueError("Cannot establish physical disk ancestry")


def identify_source(nodes, root_device):
    sources = [n for n in nodes.values() if n.get("uuid") == UUID]
    roots = [n for n in nodes.values() if n.get("maj:min") == root_device]
    if len(sources) != 1 or len(roots) != 1:
        raise ValueError("Known source/root filesystem identity is missing or ambiguous")
    source = sources[0]
    if (source["type"] != "part" or source.get("fstype") != "ext4"
            or int(source.get("size") or 0) <= 0
            or disk_serial(source, nodes) != DATA_SERIAL
            or disk_serial(roots[0], nodes) != OS_SERIAL
            or source["maj:min"] == root_device):
        raise ValueError("Source or OS physical identity does not match the rescue plan")
    return source


def guard_fstab(text):
    entries = []
    for line in text.splitlines():
        fields = line.split("#", 1)[0].split()
        if len(fields) > 1 and fields[1] == "/var/lib/docker":
            entries.append(fields)
    if len(entries) != 1:
        raise ValueError("Expected one Docker fstab entry")
    fields = entries[0]
    if (len(fields) != 6 or fields[:3] != ["UUID=" + UUID, "/var/lib/docker", "ext4"]
            or not {"noauto", "ro", "noload"} <= set(fields[3].split(","))
            or {"auto", "rw"} & set(fields[3].split(",")) or fields[5] != "0"):
        raise ValueError("Docker maintenance fstab guards are not intact")


def no_symlink_path(path):
    for item in (path, *path.parents):
        if item.is_symlink():
            raise ValueError("Symlink in protected path")


def preflight():
    if socket.gethostname() != "aisrv":
        raise ValueError("Restricted to hostname aisrv")
    guard_fstab(Path("/etc/fstab").read_text())
    for unit in UNITS:
        path = Path("/etc/systemd/system") / unit
        state = command("systemctl", "show", unit, "--property=ActiveState", "--value").strip()
        if not path.is_symlink() or os.readlink(path) != "/dev/null" or state != "inactive":
            raise ValueError("Docker/containerd/mount units must remain persistently masked and inactive")
    root = os.stat("/").st_dev
    root_device = f"{os.major(root)}:{os.minor(root)}"
    nodes = block_nodes(json.loads(command("lsblk", "--json", "--bytes", "--paths", "--output",
        "NAME,TYPE,PKNAME,SERIAL,UUID,FSTYPE,MAJ:MIN,SIZE")))
    source = identify_source(nodes, root_device)
    no_symlink_path(Path(source["name"]))
    info = os.lstat(source["name"])
    actual = f"{os.major(info.st_rdev)}:{os.minor(info.st_rdev)}"
    if not stat.S_ISBLK(info.st_mode) or actual != source["maj:min"]:
        raise ValueError("Source is not the identified non-symlink block device")
    if any(m["device"] == actual for m in parse_mounts(Path("/proc/self/mountinfo").read_text())):
        raise ValueError("Source has an existing mount; refusing rescue")
    no_symlink_path(APP2)
    if os.stat(APP2).st_dev != root:
        raise ValueError("Destination must be on the identified healthy OS filesystem")
    return source, root


@contextmanager
def readonly_source(source):
    # Probe the actual block device; do not trust only cached UUID information.
    probe = dict(line.split("=", 1) for line in
                 command("blkid", "-p", "-o", "export", source["name"]).splitlines() if "=" in line)
    if probe.get("UUID") != UUID or probe.get("TYPE") != "ext4":
        raise ValueError("Direct source probe differs from expected filesystem")
    mountpoint = Path(tempfile.mkdtemp(prefix="app2-rescue-", dir="/root"))
    mounted = False
    try:
        command("mount", "-t", "ext4", "-o", "ro,noload,nodev,nosuid,noexec",
                source["name"], str(mountpoint))
        mounted = True
        matches = [m for m in parse_mounts(Path("/proc/self/mountinfo").read_text())
                   if m["target"] == str(mountpoint)]
        if (len(matches) != 1 or matches[0]["device"] != source["maj:min"]
                or matches[0]["type"] != "ext4"
                or not {"ro", "nodev", "nosuid", "noexec"} <= matches[0]["options"]
                or not {"noload", "norecovery"} & matches[0]["fsoptions"]):
            raise ValueError("Read-only/no-replay source mount verification failed")
        yield mountpoint
    finally:
        # Even if mount exited unsuccessfully, detect a mount completed before an error.
        present = any(m["target"] == str(mountpoint)
                      for m in parse_mounts(Path("/proc/self/mountinfo").read_text()))
        if mounted or present:
            try:
                command("umount", str(mountpoint))  # Never lazy or force.
            except BaseException:
                print(f"SOURCE_UNMOUNT_FAILED={mountpoint}; preserve maintenance guards", file=sys.stderr)
                raise
        mountpoint.rmdir()


def size_tree(path):
    if not path.exists() and not path.is_symlink():
        raise ValueError("Required source path is missing")
    values = []
    for extra in ((), ("--apparent-size",)):
        result = command("du", "--summarize", "--block-size=1", "--no-dereference",
                         "--one-file-system", *extra, "--", str(path), timeout=300)
        values.append(int(result.split("\t", 1)[0]))
    return {"allocated_bytes": values[0], "logical_bytes": values[1]}


def plan_tar_paths(volumes):
    missing = set(ESSENTIAL + (CACHE,)) - set(volumes)
    if missing:
        raise ValueError("Required app2 volumes missing: " + ",".join(sorted(missing)))
    return list(ESSENTIAL)


def inventory(mountpoint):
    volume_root = mountpoint / "volumes"
    no_symlink_path(volume_root)
    volumes = {}
    entries = sorted(volume_root.iterdir())
    if len(entries) > 1000:
        raise ValueError("Unexpected volume inventory size")
    for path in entries:
        if path.is_symlink():
            raise ValueError("Unexpected symlink in Docker volume inventory")
        if not path.is_dir():
            continue
        data = path / "_data"
        if not data.is_dir() or data.is_symlink():
            raise ValueError("Unexpected Docker volume data path")
        try:
            volumes[path.name] = size_tree(data)  # Metadata only; no file contents.
        except (OSError, ValueError, subprocess.SubprocessError):
            if path.name in ESSENTIAL + (CACHE,):
                raise
            volumes[path.name] = {"inventory_error": "SIZE_UNREADABLE_NO_CONTENTS_READ"}
    plan_tar_paths(volumes)
    server_paths = sorted(p.name for p in APP2.iterdir() if p.name != "recovery")
    if not {"setup", "cvat", "receipts", "secrets"} <= set(server_paths):
        raise ValueError("Required app2 server configuration directories are missing")
    server_sizes = [size_tree(APP2 / name) for name in server_paths]
    return {"volumes": volumes, "server_paths": server_paths,
            "server_files": {key: sum(item[key] for item in server_sizes)
                             for key in ("allocated_bytes", "logical_bytes")}}


def choose_plan(report, free_bytes):
    names = plan_tar_paths(report["volumes"])
    def estimate(selected):
        # Conservative logical size (even for sparse files), plus tar/PAX metadata margin.
        sizes = [report["server_files"]] + [report["volumes"][name] for name in selected]
        amount = sum(max(item["logical_bytes"], item["allocated_bytes"]) for item in sizes)
        return amount + max(1024 ** 3, amount // 10)
    if free_bytes - estimate(names) < RESERVE:
        raise ValueError("Essential rescue does not fit while preserving 16 GiB free")
    if free_bytes - estimate(names + [CACHE]) >= RESERVE:
        names.append(CACHE)
    return names, estimate(names)


def sha_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(data)
    return digest.hexdigest()


def archive(source, names, destination, file_limit=None):
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    os.close(fd)
    options = ("--numeric-owner", "--acls", "--xattrs", "--xattrs-include=*", "--sparse",
               "--one-file-system", "--directory", str(source), "--file", str(destination))
    try:
        command("tar", "--create", *options, "--", *names, timeout=1800, file_limit=file_limit)
        command("tar", "--compare", *options, "--", *names, timeout=1800)
    except subprocess.SubprocessError as error:
        log = destination.with_suffix(".error.log")
        with log.open("w", opener=lambda p, f: os.open(p, f | os.O_NOFOLLOW, 0o600)) as stream:
            stream.write(str(getattr(error, "stderr", "")))
        raise
    with destination.open("rb") as stream:
        os.fsync(stream.fileno())
    return {"file": destination.name, "bytes": destination.stat().st_size,
            "sha256": sha_file(destination), "source_compare": "PASS"}


def save_json(path, value):
    with path.open("w", opener=lambda p, flags: os.open(p, flags | os.O_NOFOLLOW, 0o600)) as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def backup(mountpoint, source, root_device, report):
    no_symlink_path(RECOVERY)
    user = pwd.getpwnam("luisacuna")
    if not RECOVERY.exists():
        RECOVERY.mkdir(mode=0o700)
        os.chown(RECOVERY, user.pw_uid, user.pw_gid)
    info = RECOVERY.stat()
    if info.st_uid != user.pw_uid or stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError("Recovery parent must be private and owned by luisacuna")
    if os.stat(RECOVERY).st_dev != root_device:
        raise ValueError("Recovery destination filesystem changed")
    selected, estimate = choose_plan(report, os.statvfs(RECOVERY).f_bavail * os.statvfs(RECOVERY).f_frsize)
    dest = Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime("rescue-%Y%m%dT%H%M%SZ-"),
                                 dir=RECOVERY))
    print(f"BACKUP={dest}", flush=True)
    receipt = {"status": "IN_PROGRESS", "source_serial": DATA_SERIAL, "source_uuid": UUID,
               "source_device": source["name"], "estimate_bytes": estimate, "inventory": report,
               "selected_volumes": selected, "excluded_volumes": sorted(set(report["volumes"]) - set(selected)),
               "archives": [], "full_ssd_backup": False,
               "firmware_gate": "NOT_CLEARED_OTHER_CRITICAL_DATA_NOT_BACKED_UP"}
    save_json(dest / "receipt.json", receipt)
    try:
        # Preserve CVAT first; omit only the regenerable training cache if capacity requires.
        jobs = [(mountpoint / "volumes" / name / "_data", ["."], name + ".tar") for name in selected]
        jobs.append((APP2, ["./" + name for name in report["server_paths"]], "server-app2.tar"))
        for directory, names, filename in jobs:
            free = os.statvfs(dest).f_bavail * os.statvfs(dest).f_frsize
            limit = free - RESERVE - 64 * 1024 ** 2
            if limit <= 0:
                raise ValueError("Free-space reserve reached; preserving partial rescue")
            receipt["archives"].append(archive(directory, names, dest / filename, file_limit=limit))
            save_json(dest / "receipt.json", receipt)
        receipt["status"] = "ARCHIVES_VERIFIED_PENDING_EXTERNAL_COPY_AND_RESTORE_TEST"
        save_json(dest / "receipt.json", receipt)
    except BaseException:
        receipt["status"] = "FAILED_PARTIAL_PRESERVED"
        save_json(dest / "receipt.json", receipt)
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
    for name in ("check", "inventory", "backup"):
        modes.add_argument("--" + name, action="store_true")
    args = parser.parse_args()
    try:
        source, root_device = preflight()
        if args.check:
            result = {"status": "CHECK_OK_NO_MOUNT", "source_device": source["name"],
                      "source_serial": DATA_SERIAL, "destination_serial": OS_SERIAL}
        else:
            if os.geteuid() != 0:
                raise ValueError("Inventory/backup require root for the temporary read-only mount")
            with readonly_source(source) as mounted:
                report = inventory(mounted)
                result = backup(mounted, source, root_device, report) if args.backup else report
            result["source_unmounted"] = True
        print(json.dumps(result, indent=2))
    except Exception as error:
        # A subprocess stderr could contain private names; do not echo it.
        detail = type(error).__name__ if isinstance(error, subprocess.SubprocessError) else str(error)
        parser.exit(1, f"RESCUE_FAILED: {detail}; preserve partial files and maintenance guards\n")


if __name__ == "__main__":
    main()
