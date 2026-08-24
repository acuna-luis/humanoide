#!/usr/bin/env python3
"""Patch ubt-controller 5.3.0 to select clamp plates for PICO sessions.

The supplied backend ignores the UI's ``arm_type`` field and assigns
``ARM_TYPE.GRIPPER`` whenever no data glove is connected.  On a Cruzr S2
equipped with factory clamp plates, that selects the wrong kinematic matrices.

This script changes only the ``WebsocketServer.collect`` code object embedded
in the PyInstaller PYZ archive.  It replaces the single enum attribute lookup
``GRIPPER`` with ``CLAMP`` and leaves the robot and all other PC modules intact.

Run this with the Python 3.10 interpreter used by the vendor bundle.  The
result is written to a separate executable; the caller is responsible for
keeping a backup and installing it.
"""

from __future__ import annotations

import argparse
import marshal
import os
import stat
import struct
import subprocess
import sys
import tempfile
import types
import zlib
from pathlib import Path


COOKIE_MAGIC = b"MEI\x0c\x0b\x0a\x0b\x0e"
COOKIE_FORMAT = "!8sIIII64s"
COOKIE_LENGTH = struct.calcsize(COOKIE_FORMAT)
TOC_ENTRY_FORMAT = "!IIIIBc"
TOC_ENTRY_LENGTH = struct.calcsize(TOC_ENTRY_FORMAT)


def fail(message: str) -> "NoReturn":
    raise RuntimeError(message)


def parse_pkg(executable: bytes):
    cookie_offset = executable.rfind(COOKIE_MAGIC)
    if cookie_offset < 0:
        fail("PyInstaller cookie not found")
    cookie = executable[cookie_offset : cookie_offset + COOKIE_LENGTH]
    magic, pkg_length, toc_offset, toc_length, pyvers, pylib_raw = struct.unpack(
        COOKIE_FORMAT, cookie
    )
    pkg_end = cookie_offset + COOKIE_LENGTH
    pkg_start = pkg_end - pkg_length
    pkg = executable[pkg_start:pkg_end]
    if pkg_start < 0 or len(pkg) != pkg_length:
        fail("Invalid PyInstaller package bounds")
    toc_data = pkg[toc_offset : toc_offset + toc_length]
    entries = []
    cursor = 0
    while cursor < len(toc_data):
        header = toc_data[cursor : cursor + TOC_ENTRY_LENGTH]
        entry_length, offset, length, uncompressed, compressed, typecode = struct.unpack(
            TOC_ENTRY_FORMAT, header
        )
        name_raw = toc_data[
            cursor + TOC_ENTRY_LENGTH : cursor + entry_length
        ]
        name = name_raw.rstrip(b"\0").decode("utf-8")
        entries.append(
            {
                "name": name,
                "offset": offset,
                "length": length,
                "uncompressed": uncompressed,
                "compressed": compressed,
                "typecode": typecode.decode("ascii"),
            }
        )
        cursor += entry_length
    if cursor != len(toc_data):
        fail("Invalid CArchive TOC")
    pylib = pylib_raw.split(b"\0", 1)[0].decode("ascii")
    return pkg, entries, pyvers, pylib


def serialize_pkg_toc(entries) -> bytes:
    serialized = []
    for entry in entries:
        name = entry["name"].encode("utf-8")
        name_length = len(name) + 1
        entry_length = TOC_ENTRY_LENGTH + name_length
        if entry_length % 16:
            name_length += 16 - entry_length % 16
        serialized.append(
            struct.pack(
                TOC_ENTRY_FORMAT + f"{name_length}s",
                TOC_ENTRY_LENGTH + name_length,
                entry["offset"],
                entry["length"],
                entry["uncompressed"],
                entry["compressed"],
                entry["typecode"].encode("ascii"),
                name,
            )
        )
    return b"".join(serialized)


def patch_collect_code(code: types.CodeType, path: str = ""):
    current_path = f"{path}/{code.co_name}"
    changed = 0
    constants = []
    for value in code.co_consts:
        if isinstance(value, types.CodeType):
            value, child_changes = patch_collect_code(value, current_path)
            changed += child_changes
        constants.append(value)

    names = code.co_names
    if current_path.endswith("/WebsocketServer/collect"):
        required = {"ARM_TYPE", "ARM_TYPES", "GRIPPER", "environ"}
        if not required.issubset(names):
            fail(f"Unexpected collect() bytecode names: {names!r}")
        if names.count("GRIPPER") != 1:
            fail("Expected exactly one GRIPPER lookup in collect()")
        names = tuple("CLAMP" if name == "GRIPPER" else name for name in names)
        changed += 1

    if tuple(constants) != code.co_consts or names != code.co_names:
        code = code.replace(co_consts=tuple(constants), co_names=names)
    return code, changed


def patch_pyz(pyz: bytes) -> bytes:
    if pyz[:4] != b"PYZ\0":
        fail("Embedded PYZ header not found")
    toc_offset = struct.unpack("!i", pyz[8:12])[0]
    toc_object = marshal.loads(pyz[toc_offset:])
    if not isinstance(toc_object, (list, tuple)):
        fail("Unexpected PYZ TOC format")

    target_name = "websocket_server"
    target_found = False
    rebuilt_entries = []
    data_chunks = []
    nonempty_offsets = [entry[1][1] for entry in toc_object if entry[1][2] > 0]
    header_length = min(nonempty_offsets)
    cursor = header_length

    for name, (typecode, old_offset, old_length) in toc_object:
        if old_length:
            compressed = pyz[old_offset : old_offset + old_length]
            if len(compressed) != old_length:
                fail(f"Truncated PYZ member: {name}")
        else:
            compressed = b""

        if name == target_name:
            code = marshal.loads(zlib.decompress(compressed))
            code, changes = patch_collect_code(code)
            if changes != 1:
                fail(f"Expected one collect() patch, got {changes}")
            compressed = zlib.compress(marshal.dumps(code), 6)
            target_found = True

        rebuilt_entries.append((name, (typecode, cursor, len(compressed))))
        data_chunks.append(compressed)
        cursor += len(compressed)

    if not target_found:
        fail(f"{target_name!r} not found in PYZ")

    toc_bytes = marshal.dumps(rebuilt_entries)
    header = bytearray(pyz[:header_length])
    struct.pack_into("!i", header, 8, cursor)
    return bytes(header) + b"".join(data_chunks) + toc_bytes


def rebuild_pkg(pkg: bytes, entries, pyvers: int, pylib: str) -> bytes:
    output = bytearray()
    rebuilt_entries = []
    pyz_count = 0
    for old in entries:
        raw = pkg[old["offset"] : old["offset"] + old["length"]]
        if len(raw) != old["length"]:
            fail(f"Truncated CArchive member: {old['name']}")
        if old["name"] == "PYZ.pyz" and old["typecode"] == "z":
            if old["compressed"]:
                fail("Unexpected compressed PYZ CArchive member")
            raw = patch_pyz(raw)
            pyz_count += 1
        rebuilt = dict(old)
        rebuilt["offset"] = len(output)
        rebuilt["length"] = len(raw)
        rebuilt["uncompressed"] = len(raw) if old["typecode"] == "z" else old["uncompressed"]
        output.extend(raw)
        rebuilt_entries.append(rebuilt)

    if pyz_count != 1:
        fail(f"Expected one PYZ.pyz member, got {pyz_count}")

    toc_offset = len(output)
    toc = serialize_pkg_toc(rebuilt_entries)
    output.extend(toc)
    pkg_length = len(output) + COOKIE_LENGTH
    output.extend(
        struct.pack(
            COOKIE_FORMAT,
            COOKIE_MAGIC,
            pkg_length,
            toc_offset,
            len(toc),
            pyvers,
            pylib.encode("ascii"),
        )
    )
    return bytes(output)


def validate_patch(executable_path: Path) -> None:
    executable = executable_path.read_bytes()
    pkg, entries, _, _ = parse_pkg(executable)
    pyz_entry = next(entry for entry in entries if entry["name"] == "PYZ.pyz")
    pyz = pkg[pyz_entry["offset"] : pyz_entry["offset"] + pyz_entry["length"]]
    toc_offset = struct.unpack("!i", pyz[8:12])[0]
    toc = dict(marshal.loads(pyz[toc_offset:]))
    typecode, offset, length = toc["websocket_server"]
    del typecode
    code = marshal.loads(zlib.decompress(pyz[offset : offset + length]))
    matches = []

    def walk(item: types.CodeType, path: str = "") -> None:
        current = f"{path}/{item.co_name}"
        if current.endswith("/WebsocketServer/collect"):
            matches.append(item.co_names)
        for child in item.co_consts:
            if isinstance(child, types.CodeType):
                walk(child, current)

    walk(code)
    if len(matches) != 1 or "CLAMP" not in matches[0] or "GRIPPER" in matches[0]:
        fail(f"Patched collect() validation failed: {matches!r}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    if sys.version_info[:2] != (3, 10):
        fail(f"Python 3.10 required, got {sys.version.split()[0]}")
    if args.input.resolve() == args.output.resolve():
        fail("Output must be a separate file")
    if not args.input.is_file():
        fail(f"Input executable not found: {args.input}")

    source = args.input.read_bytes()
    pkg, entries, pyvers, pylib = parse_pkg(source)
    if pyvers != 310 or pylib != "libpython3.10.so.1.0":
        fail(f"Unexpected bundle runtime: pyvers={pyvers}, pylib={pylib}")
    rebuilt_pkg = rebuild_pkg(pkg, entries, pyvers, pylib)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cruzr-clamp-patch-") as temp_dir:
        pkg_path = Path(temp_dir) / "pydata.pkg"
        pkg_path.write_bytes(rebuilt_pkg)
        subprocess.run(
            [
                "objcopy",
                "--update-section",
                f"pydata={pkg_path}",
                str(args.input),
                str(args.output),
            ],
            check=True,
        )
    mode = stat.S_IMODE(args.input.stat().st_mode)
    os.chmod(args.output, mode)
    validate_patch(args.output)
    print("PATCH_OK=WebsocketServer.collect:GRIPPER->CLAMP")
    print(f"OUTPUT={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
