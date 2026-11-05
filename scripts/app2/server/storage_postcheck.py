#!/usr/bin/env python3
"""Read-only post-firmware diagnostics for the identified aisrv Docker SSD.

Requires root. Never mounts, repairs, resets, starts services or updates firmware.
--filesystem-check adds ONLY e2fsck -f -n on the identified unmounted partition.
JSON goes to stdout; redirect it with umask 077 to a NEW file on the OS SSD.
Exit: 0=queries completed, 1=filesystem/journal review needed, 2=blocked/error/timeout.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

# Import the pinned helper without creating a root-owned __pycache__ on the host.
sys.dont_write_bytecode = True

BASE_SHA256 = "ec8e727b23d2288ac46be24d4c0ab8867f46100a38a9578ec83a781cebffcee8"
EXPECTED_FW = {"S7DRNJ0X107187F": "8B2QJXD7", "S7DRNJ0X107095A": "4B2QJXD7"}
SAFE_PATH = "/usr/sbin:/usr/bin:/sbin:/bin"
OUTPUT_LIMIT = 2 * 1024 ** 2


def load_rescue(path=None):
    path = path or Path(__file__).with_name("storage_rescue.py")
    if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != BASE_SHA256:
        raise ValueError("Pinned storage_rescue.py is missing, a symlink or has a different SHA256")
    spec = importlib.util.spec_from_file_location("postcheck_storage_rescue", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def controllers():
    rows = []
    for path in sorted(Path("/sys/class/nvme").glob("nvme*")):
        if not re.fullmatch(r"nvme[0-9]+", path.name):
            continue
        rows.append({"controller": path.name, **{name: (path / name).read_text().strip()
                    for name in ("serial", "model", "firmware_rev", "state")}})
    return rows


def validate_controllers(rows, source, base):
    selected = {}
    for serial, firmware in EXPECTED_FW.items():
        matches = [row for row in rows if row["serial"] == serial]
        if len(matches) != 1:
            raise ValueError("Expected SSD controller identity is missing or ambiguous")
        row = matches[0]
        if (not re.fullmatch(r"nvme[0-9]+", row["controller"])
                or row["firmware_rev"] != firmware or row["state"] != "live"):
            raise ValueError("SSD firmware/state differs from the post-update plan")
        selected[serial] = row
    data_controller = selected[base.DATA_SERIAL]["controller"]
    if not re.fullmatch(r"/dev/" + re.escape(data_controller) + r"n[0-9]+p[0-9]+", source["name"]):
        raise ValueError("Source partition does not belong to the identified data controller")
    return selected


def text(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value or ""


def query(argv, timeout=30):
    started = time.monotonic()
    result = {"argv": argv, "timeout_s": timeout}
    try:
        process = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, timeout=timeout,
            env={"PATH": SAFE_PATH, "LC_ALL": "C"})
        result.update(rc=process.returncode, stdout=process.stdout, stderr=process.stderr)
    except subprocess.TimeoutExpired as error:
        result.update(rc=None, error="TIMEOUT", stdout=text(error.stdout), stderr=text(error.stderr))
    except OSError as error:
        result.update(rc=None, error=type(error).__name__, stdout="", stderr=str(error))
    for key in ("stdout", "stderr"):
        if len(result[key]) > OUTPUT_LIMIT:
            result[key] = result[key][:OUTPUT_LIMIT]
            result["output_truncated"] = True
    result["duration_s"] = round(time.monotonic() - started, 3)
    if result["rc"] == 0 and not result.get("output_truncated"):
        try:
            result["json"] = json.loads(result["stdout"])
        except (TypeError, ValueError):
            pass
    return result


def direct_probe(base, source):
    # Probe raw partition identity again; cached lsblk UUID alone is insufficient.
    probe = dict(line.split("=", 1) for line in base.command(
        "blkid", "-p", "-o", "export", source["name"]).splitlines() if "=" in line)
    if probe.get("UUID") != base.UUID or probe.get("TYPE") != "ext4":
        raise ValueError("Direct data partition UUID/type probe does not match")
    return {key: probe[key] for key in ("UUID", "TYPE")}


def fsck_review_reasons(result):
    output = text(result.get("stdout")) + "\n" + text(result.get("stderr"))
    patterns = (
        ("JOURNAL_RECOVERY_NOT_APPLIED", r"\bskipping journal recovery\b|"
         r"\bjournal recovery (?:was )?(?:skipped|omitted)\b|"
         r"\bneeds?[_ -](?:journal[_ -])?recovery\b|\brequires? (?:journal )?recovery\b"),
        ("UNRESOLVED_FILESYSTEM_DIAGNOSTIC", r"\bwrong\b|\bunfixed\b|\buncorrected\b|"
         r"\binconsisten(?:cy|cies|t)\b|\b(?:fix|clear|salvage|recreate)\?\s*no\b"),
    )
    return [name for name, pattern in patterns if re.search(pattern, output, re.IGNORECASE)]


def fsck_status(result):
    if result.get("error") or result.get("output_truncated"):
        return "INCOMPLETE_READ_ONLY_CHECK", 2
    if result["rc"] == 0:
        if fsck_review_reasons(result):
            return "JOURNAL_OR_FILESYSTEM_REVIEW_REQUIRED_READ_ONLY", 1
        return "COMPLETED_WITHOUT_REVIEW_MARKERS_READ_ONLY", 0
    if result["rc"] == 4:
        return "ERRORS_LEFT_UNCORRECTED_READ_ONLY", 1
    return "UNEXPECTED_OR_FAILED_READ_ONLY_CHECK", 2


def filesystem_gate(queries, data_serial):
    reasons = []
    for row in queries:
        if (row.get("rc") != 0 or row.get("error") or row.get("output_truncated")
                or row["argv"][0] == "nvme" and not isinstance(row.get("json"), dict)):
            reasons.append("INCOMPLETE_QUERY:" + " ".join(row["argv"][:2]))
    smart = [row for row in queries if row.get("serial") == data_serial
             and row["argv"][:2] == ["nvme", "smart-log"]]
    counters = {}
    if len(smart) != 1:
        reasons.append("DATA_SMART_MISSING_OR_AMBIGUOUS")
    else:
        data = smart[0].get("json")
        data = data if isinstance(data, dict) else {}
        for key in ("critical_warning", "media_errors"):
            value = data.get(key)
            if isinstance(value, str) and re.fullmatch(r"[0-9]+|0[xX][0-9a-fA-F]+", value):
                value = int(value, 16 if value.lower().startswith("0x") else 10)
            if type(value) is not int or value < 0:
                reasons.append("DATA_SMART_UNINTERPRETABLE:" + key)
            elif value != 0:
                reasons.append("DATA_SMART_NONZERO:" + key)
            else:
                counters[key] = value
    return {"eligible": not reasons, "reasons": reasons, "data_smart_counters": counters,
            "scope": "Prerequisites for an optional read-only fsck, not proof of SSD health"}


def collect(report, filesystem_check=False, base=None):
    if os.geteuid() != 0:
        raise PermissionError("Run with sudo/root for raw diagnostics; nothing was mounted or changed")
    base = base or load_rescue()
    source, _ = base.preflight()
    report["source"] = source
    rows = controllers()
    report["controllers"] = rows
    selected = validate_controllers(rows, source, base)
    report["direct_probe"] = direct_probe(base, source)
    report["boot_id"] = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    report["uptime_s"] = float(Path("/proc/uptime").read_text().split()[0])
    report["guard"] = "PASS_IDENTIFIED_UNMOUNTED_MASKED_INACTIVE"
    report["queries"] = []
    for serial in (base.DATA_SERIAL, base.OS_SERIAL):
        device = "/dev/" + selected[serial]["controller"]
        for command in (["nvme", "smart-log", device, "--output-format=json"],
                        ["nvme", "error-log", device, "--log-entries=16", "--output-format=json"]):
            report["queries"].append({"serial": serial, **query(command)})
    report["queries"].append(query(["journalctl", "-k", "-b", "--no-pager", "-n", "250",
        "--grep=nvme|I/O error|AER|PCIe Bus Error|EXT4-fs"]))
    code = 0 if all(row.get("rc") == 0 and not row.get("output_truncated")
                    for row in report["queries"]) else 2
    gate = filesystem_gate(report["queries"], base.DATA_SERIAL)
    report["filesystem_check_gate"] = gate
    if filesystem_check:
        if not gate["eligible"]:
            report["filesystem_check"] = {"skipped": True, "rc": None,
                "reasons": gate["reasons"], "interpretation": "SKIPPED_BEFORE_FILESYSTEM_READ"}
            code = 2
        else:
            code = max(code, perform_filesystem_check(report, base, source))
    # Final guard detects a concurrent external mount/service change; never undo it.
    base.preflight()
    report["final_guard"] = "PASS_IDENTIFIED_UNMOUNTED_MASKED_INACTIVE"
    report["status"] = {0: "READ_ONLY_CHECKS_COMPLETED", 1: "FILESYSTEM_REVIEW_REQUIRED",
                        2: "DIAGNOSTICS_INCOMPLETE_OR_FAILED"}[code]
    return code


def perform_filesystem_check(report, base, source):
    # Recheck every guard immediately before the optional, longer filesystem read.
    current, _ = base.preflight()
    if current["name"] != source["name"] or current["maj:min"] != source["maj:min"]:
        raise ValueError("Source identity changed during diagnostics")
    validate_controllers(controllers(), current, base)
    direct_probe(base, current)
    result = query(["e2fsck", "-f", "-n", current["name"]], timeout=300)
    result["review_reasons"] = fsck_review_reasons(result)
    result["interpretation"], code = fsck_status(result)
    report["filesystem_check"] = result
    return code


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--filesystem-check", action="store_true",
        help="Also run ONLY e2fsck -f -n (read-only/no to repairs), unmounted data SSD; timeout 300s")
    args = parser.parse_args(argv)
    os.environ["PATH"] = SAFE_PATH
    report = {"at_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "READ_ONLY_NO_MOUNT_NO_REPAIR_NO_START_NO_FIRMWARE",
              "filesystem_check_requested": args.filesystem_check,
              "storage_rescue_sha256": BASE_SHA256}
    try:
        code = collect(report, args.filesystem_check)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        report.update(status="BLOCKED_OR_FAILED", error_type=type(error).__name__, error=str(error))
        if isinstance(error, (subprocess.CalledProcessError, subprocess.TimeoutExpired)):
            report["failed_query"] = {"argv": error.cmd, "rc": getattr(error, "returncode", None),
                "stdout": text(error.stdout)[:OUTPUT_LIMIT], "stderr": text(error.stderr)[:OUTPUT_LIMIT]}
        code = 2
    print(json.dumps(report, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
