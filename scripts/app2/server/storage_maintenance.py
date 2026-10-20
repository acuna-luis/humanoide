#!/usr/bin/env python3
"""Prepare aisrv's failed Docker SSD for a separate, operator-controlled shutdown.

No stop, start, mount, unmount, reset, repair or power command is issued here.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import stat
import subprocess
import tempfile

SOURCE = "UUID=b819b286-2006-4474-b2d5-13982b0f1536"
TARGET = "/var/lib/docker"
UNITS = ("docker.service", "docker.socket", "containerd.service",
         "var-lib-docker.mount", "var-lib-docker.automount")
FSTAB = Path("/etc/fstab")
UNIT_DIR = Path("/etc/systemd/system")
BACKUPS = Path("/root/app2-storage-maintenance")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def prepare_fstab(data):
    """Change exactly the verified Docker entry, preserving all other bytes."""
    lines = data.decode("utf-8", "surrogateescape").splitlines(keepends=True)
    matches = []
    for index, line in enumerate(lines):
        tokens = list(re.finditer(r"\S+", line))
        tokens = tokens[:next((n for n, t in enumerate(tokens)
                              if t.group().startswith("#")), len(tokens))]
        if len(tokens) > 1 and tokens[1].group() == TARGET:
            matches.append((index, tokens))
    if len(matches) != 1:
        raise ValueError("Expected exactly one Docker fstab entry")
    index, tokens = matches[0]
    if (len(tokens) != 6 or tokens[0].group() != SOURCE
            or tokens[2].group() != "ext4"):
        raise ValueError("Docker fstab source/type/field count differs from known SSD")
    opts = [v for v in tokens[3].group().split(",")
            if v not in {"auto", "rw", "noauto", "ro", "noload"}]
    opts += ["noauto", "ro", "noload"]
    line = lines[index]
    for token, value in ((tokens[5], "0"), (tokens[3], ",".join(opts))):
        line = line[:token.start()] + value + line[token.end():]
    lines[index] = line
    return "".join(lines).encode("utf-8", "surrogateescape")


def docker_mount_device(mountinfo):
    entries = [line.split() for line in mountinfo.splitlines()
               if len(line.split()) > 5 and line.split()[4] == TARGET]
    if len(entries) != 1:
        raise ValueError("Docker must currently be an exact, unique mount")
    return tuple(map(int, entries[0][2].split(":")))


def run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=30).stdout


def metadata(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError(f"Expected non-symlink, unshared regular file: {path}")
    return {"mode": stat.S_IMODE(info.st_mode), "uid": info.st_uid, "gid": info.st_gid}


def atomic_write(path, data, meta):
    fd, name = tempfile.mkstemp(prefix=".app2-maint-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            os.fchmod(stream.fileno(), meta["mode"])
            os.fchown(stream.fileno(), meta["uid"], meta["gid"])
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        directory = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def save_receipt(backup, receipt):
    atomic_write(backup / "receipt.json", json.dumps(receipt, indent=2).encode() + b"\n",
                 {"mode": 0o600, "uid": 0, "gid": 0})


def guard_restore(current, original, receipt):
    if sha(original) != receipt["original_sha256"]:
        raise ValueError("Original backup checksum mismatch")
    allowed = {receipt["prepared_sha256"]}
    if receipt["state"] in {"preparing", "failed"}:
        allowed.add(receipt["original_sha256"])
    if sha(current) not in allowed:
        raise ValueError("Current fstab differs; refusing to overwrite other changes")


def check():
    if socket.gethostname() != "aisrv":
        raise ValueError("This recipe is restricted to hostname aisrv")
    metadata(FSTAB)
    original = FSTAB.read_bytes()
    prepared = prepare_fstab(original)
    paths = {unit: os.path.lexists(UNIT_DIR / unit) for unit in UNITS}
    return original, prepared, paths


def prepare():
    original, prepared, paths = check()
    if any(paths.values()):
        raise ValueError("Pre-existing local unit file/mask; refusing any replacement")
    device = docker_mount_device(Path("/proc/self/mountinfo").read_text())
    root_device = os.stat("/root").st_dev
    if device == (os.major(root_device), os.minor(root_device)):
        raise ValueError("Backup and failed Docker volume must be different filesystems")
    if os.stat("/").st_dev != root_device:
        raise ValueError("Expected /root on the OS root filesystem")
    BACKUPS.mkdir(mode=0o700, exist_ok=True)
    info = BACKUPS.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077:
        raise ValueError("Backup parent must be a private root-owned directory")
    backup = Path(tempfile.mkdtemp(prefix="aisrv-", dir=BACKUPS))
    receipt = {"schema": 1, "hostname": "aisrv", "state": "preparing",
               "original_sha256": sha(original), "prepared_sha256": sha(prepared),
               "fstab_metadata": metadata(FSTAB), "masks_created": [],
               "unit_states": {}, "inflight_mask": None}
    print(f"BACKUP={backup}", flush=True)
    atomic_write(backup / "fstab.original", original, receipt["fstab_metadata"])
    save_receipt(backup, receipt)
    try:
        for unit in UNITS:
            receipt["unit_states"][unit] = run("systemctl", "show", unit,
                "--property=LoadState,UnitFileState,ActiveState,SubState")
        save_receipt(backup, receipt)
        if FSTAB.read_bytes() != original or any(os.path.lexists(UNIT_DIR / u) for u in UNITS):
            raise ValueError("Configuration changed during preparation")
        atomic_write(FSTAB, prepared, receipt["fstab_metadata"])
        for unit in UNITS:
            receipt["inflight_mask"] = unit
            save_receipt(backup, receipt)
            run("systemctl", "mask", unit)  # Deliberately no --now.
            if not (UNIT_DIR / unit).is_symlink() or os.readlink(UNIT_DIR / unit) != "/dev/null":
                raise ValueError("Mask verification failed")
            receipt["masks_created"].append(unit)
            receipt["inflight_mask"] = None
            save_receipt(backup, receipt)
        run("systemctl", "daemon-reload")
        if sha(FSTAB.read_bytes()) != receipt["prepared_sha256"]:
            raise ValueError("Final fstab verification failed")
        if any(not (UNIT_DIR / u).is_symlink() or os.readlink(UNIT_DIR / u) != "/dev/null" for u in UNITS):
            raise ValueError("Final masks verification failed")
        receipt["state"] = "prepared"
        save_receipt(backup, receipt)
        print("CONFIG_PREPARED_NO_SHUTDOWN=1")
    except Exception:
        receipt["state"] = "failed"
        save_receipt(backup, receipt)
        print("PREPARATION_FAILED_DO_NOT_POWEROFF=1", flush=True)
        raise


def restore(backup):
    check()
    backup = Path(backup)
    if backup.is_symlink() or backup.resolve().parent != BACKUPS or not backup.is_dir():
        raise ValueError("Expected a backup directory directly under the private backup root")
    info = backup.stat()
    if info.st_uid != 0 or info.st_mode & 0o077:
        raise ValueError("Backup directory ownership/mode mismatch")
    for name in ("receipt.json", "fstab.original"):
        metadata(backup / name)
    receipt = json.loads((backup / "receipt.json").read_text())
    if receipt.get("schema") != 1 or receipt.get("hostname") != "aisrv":
        raise ValueError("Unexpected receipt identity/schema")
    original = (backup / "fstab.original").read_bytes()
    guard_restore(FSTAB.read_bytes(), original, receipt)
    units = list(receipt["masks_created"])
    if receipt.get("inflight_mask"):
        units.append(receipt["inflight_mask"])
    if any(unit not in UNITS for unit in units):
        raise ValueError("Unexpected unit in receipt")
    for unit in units:
        path = UNIT_DIR / unit
        if os.path.lexists(path) and (not path.is_symlink() or os.readlink(path) != "/dev/null"):
            raise ValueError("Recorded mask was changed; refusing removal")
    atomic_write(FSTAB, original, receipt["fstab_metadata"])
    for unit in dict.fromkeys(units):
        path = UNIT_DIR / unit
        if path.is_symlink():
            path.unlink()
    run("systemctl", "daemon-reload")
    receipt["state"] = "restored"
    save_receipt(backup, receipt)
    print("CONFIG_RESTORED_NO_START=1")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Read-only configuration checks")
    mode.add_argument("--prepare", action="store_true", help="Root: prepare next boot; no shutdown")
    mode.add_argument("--restore-config", metavar="BACKUP", help="Root: restore recorded config; no starts")
    args = parser.parse_args()
    try:
        if args.check:
            _, _, paths = check()
            print(json.dumps({"hostname": "aisrv", "fstab_entry": "verified",
                              "existing_local_unit_paths": paths}))
        else:
            if os.geteuid() != 0:
                raise ValueError("Run preparation/restoration as root")
            prepare() if args.prepare else restore(args.restore_config)
    except Exception as error:
        parser.exit(1, f"ERROR: {error}\n")


if __name__ == "__main__":
    main()
