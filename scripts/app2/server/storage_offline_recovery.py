#!/usr/bin/env python3
"""Incident-specific offline ext4 recovery on aisrv.

--check is read-only. --recover runs one reviewed e2fsck preen with undo, then
read-only checks. It can repair journal AND filesystem metadata; it is not an
atomic operation. Never mounts, starts services, resets or updates firmware.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
BASE_SHA = "ec8e727b23d2288ac46be24d4c0ab8867f46100a38a9578ec83a781cebffcee8"
POST_SHA = "a482e7d08eee61777add951b6a1c7de0d9e91600b4082e787d2a282e87b5bd0f"
PRIOR = Path("/home/luisacuna/app2/maintenance/postfirmware-check-20261020T1023Z.json")
PRIOR_SHA = "324c3b3bdc4d56a657c09d0b5c71a81d3c9188b5967c117444ba95028a3bf5f5"
RECEIPTS = (
    (Path("/home/luisacuna/app2/recovery/rescue-20261020T075927Z-boa8lm5f/receipt.json"),
     "3e497d85e03a9aa42cea0c3462d64b6d612e4e00db35c2e8baee6e555237c4b3", 22),
    (Path("/home/luisacuna/app2/recovery/writable-20261020T082144Z-oeuj8a7l/receipt.json"),
     "89069a9180e452d967d59ed9ab1d33edbba2aeccf09d741feade3d2b3099f53f", 1))
ROOT_BACKUPS = Path("/root/app2-offline-recovery")
RESERVE = 16 * 1024 ** 3
MIN_FREE_BEFORE = 32 * 1024 ** 3
HEAD_BYTES = 2 * 1024 ** 2


def pinned_module(name, digest):
    path = Path(__file__).with_name(name + ".py")
    if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError("Pinned dependency differs: " + name)
    spec = importlib.util.spec_from_file_location("recovery_" + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_pinned_json(path, digest, base):
    base.no_symlink_path(path)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > 2 * 1024 ** 2:
        raise ValueError("Unexpected report/receipt file")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError("Report/receipt SHA256 does not match: " + str(path))
    return json.loads(data), data


def backup_receipts(base, root_device):
    result = []
    for path, digest, count in RECEIPTS:
        receipt, _ = read_pinned_json(path, digest, base)
        expected_status = ("ARCHIVES_VERIFIED_PENDING_EXTERNAL_COPY_AND_RESTORE_TEST" if count == 22
                           else "ARCHIVE_COMPARED_PENDING_EXTERNAL_COPY_AND_RESTORE_TEST")
        if (receipt.get("source_serial") != base.DATA_SERIAL or receipt.get("source_uuid") != base.UUID
                or len(receipt.get("archives", [])) != count
                or receipt.get("status") != expected_status):
            raise ValueError("Backup receipt identity/completion does not match")
        if count == 22 and receipt.get("all_named_volumes_archived_and_compared") is not True:
            raise ValueError("All named volume backup is not confirmed")
        for row in receipt["archives"]:
            name = row["file"]
            if Path(name).name != name or not name.endswith(".tar") or row.get("source_compare") != "PASS":
                raise ValueError("Backup archive path/comparison is not valid")
            archive = path.parent / name
            base.no_symlink_path(archive)
            info = archive.lstat()
            if (not stat.S_ISREG(info.st_mode) or info.st_size != row["bytes"]
                    or info.st_dev != root_device):
                raise ValueError("Backup archive is missing, resized or on a different filesystem")
        result.append({"path": str(path), "sha256": digest, "archives": count,
                       "verification": "PINNED_RECEIPT_AND_FILE_SIZES_NOT_REHASHED"})
    return result


def journal_header(output):
    fields = dict(line.split(":", 1) for line in output.splitlines() if ":" in line)
    fields = {key.strip(): value.strip() for key, value in fields.items()}
    features = fields.get("Filesystem features", "").split()
    if (not {"has_journal", "needs_recovery"} <= set(features) or "journal_dev" in features
            or not fields.get("Journal inode", "").isdigit() or int(fields["Journal inode"]) <= 0
            or fields.get("Journal device", "0") not in ("0", "0x0000", "0x0")
            or fields.get("Journal UUID", "").strip("0-") != ""):
        raise ValueError("A pending INTERNAL journal without external device/UUID must be proven")
    block = int(fields["Block size"])
    blocks = int(fields["Total journal blocks"])
    if block not in (1024, 2048, 4096, 8192, 16384, 32768, 65536) or blocks <= 0:
        raise ValueError("Journal size cannot be established")
    journal_bytes = block * blocks
    return {"inode": int(fields["Journal inode"]), "block_size": block, "blocks": blocks,
            "journal_bytes": journal_bytes, "undo_estimate_bytes": 4 * journal_bytes + 256 * 1024 ** 2,
            "estimate_limit": "ESTIMATE_ONLY_NOT_A_BOUND_FOR_GENERAL_METADATA_REPAIRS"}


def diagnostic_delta(prior, fresh, base):
    def row(report, command, serial=None):
        matches = [item for item in report.get("queries", []) if item["argv"][:len(command)] == command
                   and (serial is None or item.get("serial") == serial)]
        if len(matches) != 1 or matches[0].get("rc") != 0:
            raise ValueError("Prior/fresh diagnostic query is missing, ambiguous or failed")
        return matches[0]
    def integer(value):
        if isinstance(value, str) and re.fullmatch(r"[0-9]+|0[xX][0-9a-fA-F]+", value):
            value = int(value, 16 if value.lower().startswith("0x") else 10)
        if type(value) is not int or value < 0:
            raise ValueError("Cannot interpret incident SMART counters")
        return value
    changes = []
    for serial in (base.DATA_SERIAL, base.OS_SERIAL):
        old, new = [row(report, ["nvme", "smart-log"], serial)["json"] for report in (prior, fresh)]
        for key in ("num_err_log_entries", "unsafe_shutdowns", "power_cycles"):
            if integer(old.get(key)) != integer(new.get(key)):
                changes.append(serial + ":SMART_CHANGED:" + key)
        if row(prior, ["nvme", "error-log"], serial).get("json") != row(fresh, ["nvme", "error-log"], serial).get("json"):
            changes.append(serial + ":ERROR_LOG_CHANGED")
    before = set(row(prior, ["journalctl"])["stdout"].splitlines())
    errors = re.compile(r"nvme.*(?:timeout|reset|controller is down|disabl|fault|error|fail)|"
                        r"I/O error|EXT4-fs (?:warning|error)|AER:|PCIe Bus Error", re.IGNORECASE)
    new_errors = [line for line in row(fresh, ["journalctl"])["stdout"].splitlines()
                  if line not in before and errors.search(line)]
    if changes or new_errors:
        raise ValueError("New/changed SSD counters, error logs or kernel errors; recovery blocked")
    return {"status": "NO_NEW_INCIDENT_ERRORS", "counter_changes": changes, "new_kernel_errors": new_errors}


def prepare(report, base, post):
    if os.geteuid() != 0:
        raise PermissionError("Root is required; --check remains read-only")
    source, root = base.preflight()
    prior, _ = read_pinned_json(PRIOR, PRIOR_SHA, base)
    boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    guard = "PASS_IDENTIFIED_UNMOUNTED_MASKED_INACTIVE"
    if (prior.get("boot_id") != boot or prior.get("source", {}).get("name") != source["name"]
            or prior["source"].get("maj:min") != source["maj:min"]
            or prior.get("storage_rescue_sha256") != BASE_SHA
            or prior.get("guard") != guard or prior.get("final_guard") != guard):
        raise ValueError("Prior report boot/source/guards do not match the current incident")
    report.update(boot_id=boot, source=source, prior_sha256=PRIOR_SHA,
                  backups=backup_receipts(base, root))
    fresh = {}
    rc = post.collect(fresh, filesystem_check=True, base=base)
    report["fresh_readonly"] = fresh
    os_gate = post.filesystem_gate(fresh.get("queries", []), base.OS_SERIAL)
    report["os_undo_destination_smart_gate"] = {"serial": base.OS_SERIAL,
        "eligible": os_gate["eligible"], "counters": os_gate["data_smart_counters"],
        "reasons": [reason.replace("DATA_SMART", "OS_SMART") for reason in os_gate["reasons"]]}
    if not os_gate["eligible"]:
        raise ValueError("OS SSD SMART prerequisites for backup/undo are not satisfied")
    report["diagnostic_delta"] = diagnostic_delta(prior, fresh, base)
    old, current = prior["filesystem_check"], fresh.get("filesystem_check", {})
    if (rc != 1 or not fresh.get("filesystem_check_gate", {}).get("eligible")
            or current.get("rc") != old.get("rc")
            or current.get("stdout") != old.get("stdout") or current.get("stderr") != old.get("stderr")
            or post.fsck_review_reasons(current) != ["JOURNAL_RECOVERY_NOT_APPLIED", "UNRESOLVED_FILESYSTEM_DIAGNOSTIC"]):
        raise ValueError("Fresh read-only result differs from the two known counts plus skipped journal")
    header = post.query(["dumpe2fs", "-h", source["name"]])
    report["dumpe2fs_pre"] = header
    if header.get("rc") != 0 or header.get("output_truncated"):
        raise ValueError("Cannot read complete filesystem/journal header")
    report["journal"] = journal_header(header["stdout"])
    config = Path("/etc/e2fsck.conf")
    base.no_symlink_path(config)
    if config.exists() and (not stat.S_ISREG(config.lstat().st_mode) or config.stat().st_size > 1024 ** 2):
        raise ValueError("Unexpected e2fsck configuration file")
    config_data = config.read_bytes() if config.exists() else b""
    if len(config_data) > 1024 ** 2 or re.search(rb"(?m)^\s*(?:include|includedir)\s+", config_data):
        raise ValueError("Unrecorded/large e2fsck configuration includes are not supported")
    report["e2fsck_config"] = {"exists": config.exists(), "sha256": hashlib.sha256(config_data).hexdigest()}
    report["free_bytes"] = shutil.disk_usage("/root").free
    if report["free_bytes"] < max(MIN_FREE_BEFORE, RESERVE + report["journal"]["undo_estimate_bytes"] + HEAD_BYTES):
        raise ValueError("Insufficient OS free space for reserve and estimated undo")
    report["guard"] = "READY_FOR_REVIEWED_OFFLINE_RECOVERY"
    return source, root, prior, config_data


def save_bytes(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def save_json(path, value):
    save_bytes(path, (json.dumps(value, indent=2) + "\n").encode())


def sync_directory(directory):
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def event(directory, phase, **data):
    fd = os.open(directory / "phases.jsonl", os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "a") as stream:
        stream.write(json.dumps({"at_utc": datetime.now(timezone.utc).isoformat(), "phase": phase, **data}) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    sync_directory(directory)


def recovery_argv(source, undo):
    return ["e2fsck", "-p", "-E", "nodiscard,fixes_only,no_optimize_extents", "-z", str(undo), source["name"]]


def recovery_review(result):
    output = result.get("stdout", "") + "\n" + result.get("stderr", "")
    bad = bool(re.search(r"checksum|corrupt|while recovering|\berror\b|\bI/O\b|input/output|"
        r"read.fail|write.fail|\bfail(?:ed|ure)?\b|abort|no.tty|manual|\?\s*(?:yes|no|y/n)|"
        r"(?:fix|clear|salvage)\?", output, re.IGNORECASE))
    repeated = len(re.findall(r"recovering (?:the )?journal|replaying (?:the )?journal", output, re.IGNORECASE)) > 1
    return result.get("rc") not in (0, 1) or bad or repeated or result.get("output_truncated", False)


def post_recovery_check(result, base, post):
    suspicious = recovery_review(result)
    report = {}
    # Never automatically scan the FS after a failed/suspicious write.
    rc = post.collect(report, filesystem_check=not suspicious, base=base)
    return report, suspicious or rc != 0


@contextmanager
def recovery_lock(create, base):
    _, root = base.preflight()
    base.no_symlink_path(ROOT_BACKUPS)
    if not ROOT_BACKUPS.exists():
        if not create:
            yield None  # First --check creates neither directory nor lock file.
            return
        ROOT_BACKUPS.mkdir(mode=0o700)
    info = ROOT_BACKUPS.stat()
    if info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o700 or info.st_dev != root:
        raise ValueError("Lock directory must be root-private on the verified OS filesystem")
    path = ROOT_BACKUPS / ".recovery.lock"
    if not os.path.lexists(path) and not create:
        yield None
        return
    fd = os.open(path, (os.O_RDWR | os.O_CREAT if create else os.O_RDONLY) | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_dev != root
                or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1):
            raise ValueError("Unexpected recovery lock file")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("A prior recovery/check still owns the lock; no retry") from None
        yield fd
    finally:
        # Never LOCK_UN: a running child inherits the SAME open-file description.
        # Closing only the parent's descriptor preserves its lock until child exit.
        os.close(fd)


def write_once(argv, directory, lock_fd):
    # No execution timeout, resource hard limit, retry, terminate or kill.
    streams = [os.open(directory / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_SYNC | os.O_NOFOLLOW, 0o600)
               for name in ("recovery.stdout.log", "recovery.stderr.log")]
    process = None
    try:
        event(directory, "STARTING_ONE_RECOVERY", argv=argv)
        process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=streams[0], stderr=streams[1],
            env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C"}, start_new_session=True,
            pass_fds=(lock_fd,))
        event(directory, "RECOVERY_RUNNING", pid=process.pid)
        rc = process.wait()
        for fd in streams:
            os.fsync(fd)
        result = {"argv": argv, "rc": rc, "pid": process.pid}
        for key in ("stdout", "stderr"):
            with (directory / ("recovery." + key + ".log")).open("rb") as stream:
                data = stream.read(2 * 1024 ** 2 + 1)
            result[key] = data[:2 * 1024 ** 2].decode(errors="replace")
            result["output_truncated"] = result.get("output_truncated", False) or len(data) > 2 * 1024 ** 2
        event(directory, "RECOVERY_EXITED", rc=rc)
        return result
    except BaseException:
        event(directory, "WAIT_INTERRUPTED_NO_TERMINATION", pid=process.pid if process else None)
        raise
    finally:
        for fd in streams:
            os.close(fd)


def recover(report, base, post, prepared, lock_fd):
    source, root, prior, config_data = prepared
    base.no_symlink_path(ROOT_BACKUPS)
    ROOT_BACKUPS.mkdir(mode=0o700, exist_ok=True)
    info = ROOT_BACKUPS.stat()
    if info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o700 or info.st_dev != root:
        raise ValueError("Root-private backup directory is not on the verified OS filesystem")
    directory = Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-"), dir=ROOT_BACKUPS))
    report["backup_directory"] = str(directory)
    save_json(directory / "preflight.json", report)
    save_bytes(directory / "prior-report.json", read_pinned_json(PRIOR, PRIOR_SHA, base)[1])
    for path, digest, count in RECEIPTS:
        save_bytes(directory / ("backup-receipt-" + str(count) + ".json"),
                   read_pinned_json(path, digest, base)[1])
    save_bytes(directory / "dumpe2fs-pre.stdout", report["dumpe2fs_pre"]["stdout"].encode())
    save_bytes(directory / "dumpe2fs-pre.stderr", report["dumpe2fs_pre"]["stderr"].encode())
    save_bytes(directory / "e2fsck.conf.snapshot", config_data)
    fd = os.open(source["name"], os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if not stat.S_ISBLK(info.st_mode) or f"{os.major(info.st_rdev)}:{os.minor(info.st_rdev)}" != source["maj:min"]:
            raise ValueError("Raw source identity changed before metadata backup")
        head = os.pread(fd, HEAD_BYTES, 0)
    finally:
        os.close(fd)
    if len(head) != HEAD_BYTES:
        raise ValueError("Incomplete first-2MiB backup; recovery not started")
    save_bytes(directory / "source-first-2MiB.bin", head)
    sync_directory(directory)
    sync_directory(ROOT_BACKUPS)
    event(directory, "BACKUPS_FSYNCED", head_sha256=hashlib.sha256(head).hexdigest())
    fresh_source, _ = base.preflight()
    post.validate_controllers(post.controllers(), fresh_source, base)
    post.direct_probe(base, fresh_source)
    if fresh_source["name"] != source["name"] or fresh_source["maj:min"] != source["maj:min"]:
        raise ValueError("Raw source identity changed before recovery")
    if hashlib.sha256(Path("/etc/e2fsck.conf").read_bytes() if Path("/etc/e2fsck.conf").exists() else b"").hexdigest() != report["e2fsck_config"]["sha256"]:
        raise ValueError("e2fsck configuration changed before recovery")
    if shutil.disk_usage(directory).free < max(MIN_FREE_BEFORE, RESERVE + report["journal"]["undo_estimate_bytes"]):
        raise ValueError("Space reserve changed before recovery")
    result = write_once(recovery_argv(source, directory / "recovery.e2undo"), directory, lock_fd)
    report["recovery"] = result
    save_json(directory / "recovery-result.json", result)
    undo = directory / "recovery.e2undo"
    report["undo"] = {"path": str(undo), "present_regular": undo.is_file() and not undo.is_symlink(),
                      "bytes": undo.stat().st_size if undo.is_file() else None}
    post_report, needs_review = post_recovery_check(result, base, post)
    report["post_readonly"] = post_report
    needs_review = needs_review or not report["undo"]["present_regular"]
    report["status"] = "REVIEW_REQUIRED_NO_RETRY_NO_SERVICES" if needs_review else "RECOVERY_AND_READONLY_POSTCHECK_COMPLETED_NO_SERVICES"
    save_json(directory / "result.json", report)
    event(directory, "FINISHED", status=report["status"])
    sync_directory(directory)
    return 1 if needs_review else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="Root read-only eligibility/SMART/RO filesystem/header/backup checks; no files created")
    group.add_argument("--recover", action="store_true", help="ONE offline preen of journal+metadata with undo; may repair before returning bit4; no mounts/services")
    args = parser.parse_args(argv)
    report = {"at_utc": datetime.now(timezone.utc).isoformat(), "mode": "recover" if args.recover else "check"}
    try:
        if os.geteuid() != 0:
            raise PermissionError("Root is required; --check remains read-only")
        base, post = pinned_module("storage_rescue", BASE_SHA), pinned_module("storage_postcheck", POST_SHA)
        os.environ["PATH"] = post.SAFE_PATH
        with recovery_lock(args.recover, base) as lock_fd:
            prepared = prepare(report, base, post)
            if args.recover:
                os.umask(0o077)
                def interrupted(signum, frame):
                    raise InterruptedError("Parent interrupted; any running recovery process is preserved")
                for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
                    signal.signal(sig, interrupted)
                code = recover(report, base, post, prepared, lock_fd)
            else:
                report["status"], code = "CHECK_READY_NO_WRITES", 0
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        report.update(status="BLOCKED_OR_INTERRUPTED_PRESERVE_EVIDENCE_NO_RETRY", error_type=type(error).__name__, error=str(error))
        code = 2
    print(json.dumps(report, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
