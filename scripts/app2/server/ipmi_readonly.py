#!/usr/bin/env python3
"""Bounded local IPMI reads using an isolated, checksum-pinned Ubuntu payload.

No package installation, daemon, network interface, BMC settings or firmware
operations. The operator must review the source/package before staging it.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import sys

BASE = Path("/home/luisacuna/app2/maintenance/ipmi-readonly-tools")
LOADER = Path("/lib64/ld-linux-x86-64.so.2")
PAYLOAD = {
    "bin/ipmitool": "37910be2ba09a7effcfac016e601d54f69396b925584f871a475ae41b814fd61",
    "lib/libfreeipmi.so.17": "57db493603d605a684006438177d5630176d86dfa7775d3ba605736527fbfe08",
}
HOST_LIBS = (
    "libm.so.6", "libreadline.so.8", "libcrypto.so.3", "libc.so.6",
    "libgcrypt.so.20", "libgpg-error.so.0", "libtinfo.so.6",
)
CLEAN_ENV = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C", "LC_ALL": "C"}


def arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true", help="files/host only; no BMC call")
    modes.add_argument("--mc-info", action="store_true")
    modes.add_argument("--channel-info", type=int, choices=(1, 8))
    modes.add_argument("--lan-print", type=int, choices=(1, 8))
    return parser.parse_args(argv)


def readonly_args(args):
    if args.check:
        return None
    if args.mc_info:
        return ["mc", "info"]
    if args.channel_info is not None:
        return ["channel", "info", str(args.channel_info)]
    if args.lan_print is not None:
        return ["lan", "print", str(args.lan_print)]
    raise ValueError("No approved read operation")


def no_links(path):
    for item in (path, *path.parents):
        if item.is_symlink():
            raise ValueError("Symlink in isolated tool path")


def trusted_regular(path, private=False):
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o022:
        raise ValueError("Regular non-writable-by-group/others file required")
    if info.st_uid not in ((0, 1001) if private else (0,)):
        raise ValueError("Unexpected file owner")


def preflight():
    if platform.node() != "aisrv" or platform.machine() != "x86_64":
        raise ValueError("Restricted to the inventoried aisrv x86_64 server")
    if Path(__file__).absolute().parent != BASE:
        raise ValueError("Wrapper is not in the approved isolated directory")
    no_links(BASE)
    for directory in (BASE, BASE / "bin", BASE / "lib"):
        info = directory.stat()
        if not stat.S_ISDIR(info.st_mode) or info.st_mode & 0o077:
            raise ValueError("Isolated tool directories must be private")
    if {path.name for path in (BASE / "lib").iterdir()} != {"libfreeipmi.so.17"}:
        raise ValueError("Unexpected private library; refusing altered loader search path")
    for relative, expected in PAYLOAD.items():
        path = BASE / relative
        no_links(path)
        trusted_regular(path, private=True)
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("Ubuntu payload checksum mismatch")
    trusted_regular(LOADER.resolve())
    for name in HOST_LIBS:
        path = Path("/lib/x86_64-linux-gnu") / name
        trusted_regular(path.resolve())
    no_links(Path("/dev/ipmi0"))
    if not stat.S_ISCHR(os.stat("/dev/ipmi0").st_mode):
        raise ValueError("Expected local IPMI character device is absent")


def command_for(read_args):
    allowed = (["mc", "info"], ["channel", "info", "1"], ["channel", "info", "8"],
               ["lan", "print", "1"], ["lan", "print", "8"])
    if read_args not in allowed:
        raise ValueError("IPMI arguments are outside the fixed read-only list")
    return [str(LOADER), "--library-path", str(BASE / "lib"),
            str(BASE / "bin/ipmitool"), "-I", "open", "-d", "0", *read_args]


def redact(text):
    return re.sub(r"(?im)^(\s*SNMP Community String\s*:).*$", r"\1 [REDACTED]", text)


def main(argv=None):
    args = arguments(argv)
    try:
        preflight()
        read_args = readonly_args(args)
        if read_args is None:
            print(json.dumps({"status": "CHECK_OK_NO_BMC_CALL", "private_payloads": len(PAYLOAD),
                              "package_installed": False, "daemon_started": False}))
            return 0
        if os.geteuid() != 0:
            raise ValueError("The selected local IPMI query requires operator sudo")
        result = subprocess.run(command_for(read_args), env=CLEAN_ENV, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15,
                                cwd=BASE)
        sys.stdout.write(redact(result.stdout))
        sys.stderr.write(redact(result.stderr))
        return result.returncode
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"IPMI_READ_FAILED: {type(error).__name__}; no fallback/write operation attempted",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
