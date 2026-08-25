#!/usr/bin/env python3
"""Patch ubt-controller 5.3.0 for Cruzr S2 clamp/PICO sessions.

The supplied backend ignores the UI's ``arm_type`` field and assigns
``ARM_TYPE.GRIPPER`` whenever no data glove is connected.  On a Cruzr S2
equipped with factory clamp plates, that selects the wrong kinematic matrices.

The mandatory patch changes only the ``WebsocketServer.collect`` code object
embedded in the PyInstaller PYZ archive.  It replaces the single enum
attribute lookup ``GRIPPER`` with ``CLAMP``.

The optional ``--swap-pico-x-y`` workaround changes only the two Pico SDK
button lookups in ``PicoPublisher.publish_joysticks``.  It swaps X and Y so a
working physical X button performs the vendor-defined Y enable/disable action
when the left controller's Y switch does not report a mechanical press.  This
does not force enable_control, fabricate a heartbeat, or modify the robot.

The mutually exclusive ``--pico-enable-left-trigger`` workaround replaces
only the vendor Y lookup used for ``left_joystick.b_button`` with the physical
left-trigger value and emits ``left_joystick.b_button`` only on its rising
edge.  It is intended for a clamp configuration where the trigger has no
finger actuator to command.  The trigger must still be pressed by the
operator; holding it cannot repeat the vendor Y toggle.  This option does not
synthesize input or alter the watchdog.

The optional ``--heartbeat-timeout-seconds`` diagnostic workaround replaces
only the heartbeat comparison operand in
``WebsocketServer._broadcast_publisher_states``.  The STOP path remains in
place and still runs when the configured interval expires.  This does not
fabricate or acknowledge a heartbeat and does not change the robot.

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


def patch_pico_button_code(code: types.CodeType, path: str = ""):
    current_path = f"{path}/{code.co_name}"
    changed = 0
    constants = []
    for value in code.co_consts:
        if isinstance(value, types.CodeType):
            value, child_changes = patch_pico_button_code(value, current_path)
            changed += child_changes
        constants.append(value)

    names = code.co_names
    if current_path.endswith("/PicoPublisher/publish_joysticks"):
        if names.count("get_X_button") != 1 or names.count("get_Y_button") != 1:
            fail(f"Unexpected Pico button bytecode names: {names!r}")
        names = tuple(
            "get_Y_button"
            if name == "get_X_button"
            else "get_X_button"
            if name == "get_Y_button"
            else name
            for name in names
        )
        changed += 1

    if tuple(constants) != code.co_consts or names != code.co_names:
        code = code.replace(co_consts=tuple(constants), co_names=names)
    return code, changed


def _publish_joysticks_left_trigger_edge(self):
    """Vendor publish_joysticks with a rising-edge left-trigger enable."""
    left_joystick = Joystick()
    left_joystick.a_button = xrt.get_X_button()

    left_trigger_value = xrt.get_left_trigger()
    left_trigger_pressed = left_trigger_value != 0
    left_joystick.b_button = left_trigger_pressed and not getattr(
        self, "_left_trigger_enable_pressed", False
    )
    self._left_trigger_enable_pressed = left_trigger_pressed
    left_joystick.trigger_value = left_trigger_value

    left_joystick.squeeze_value = xrt.get_left_grip()
    left_joystick.squeeze = left_joystick.squeeze_value != 0
    left_joystick.thumbstick = xrt.get_left_axis_click()
    left_joystick.thumbstick_value = xrt.get_left_axis()
    if left_joystick.thumbstick_value[1] != 0:
        left_joystick.thumbstick_value[1] *= -1

    self.update_vr_button_state(left_joystick)
    logger.info(f"Left hand state: {left_joystick.model_dump_json()}")

    right_joystick = Joystick()
    right_joystick.a_button = xrt.get_A_button()
    right_joystick.b_button = xrt.get_B_button()
    right_joystick.trigger_value = xrt.get_right_trigger()
    right_joystick.trigger = right_joystick.trigger_value != 0
    right_joystick.squeeze_value = xrt.get_right_grip()
    right_joystick.squeeze = right_joystick.squeeze_value != 0
    right_joystick.thumbstick = xrt.get_right_axis_click()
    right_joystick.thumbstick_value = xrt.get_right_axis()
    if right_joystick.thumbstick_value[1] != 0:
        right_joystick.thumbstick_value[1] *= -1

    if right_joystick.b_button and self.tele_operation_enable:
        self.handle_collection_request()
    if left_joystick.b_button:
        if not self.enable_operation_switch():
            left_joystick.b_button = False

    self.update_vr_button_state(right_joystick)
    logger.info(f"Right hand state: {right_joystick.model_dump_json()}")

    message_bytes = msgpack.dumps(
        Message(
            type=MessageType.PICO_VR_JOYSTICKS,
            message=Joysticks(
                left=left_joystick, right=right_joystick
            ),
        ).model_dump()
    )
    self.put_to_send(message_bytes)


def patch_pico_trigger_enable_code(code: types.CodeType, path: str = ""):
    current_path = f"{path}/{code.co_name}"
    changed = 0
    constants = []
    for value in code.co_consts:
        if isinstance(value, types.CodeType):
            value, child_changes = patch_pico_trigger_enable_code(
                value, current_path
            )
            changed += child_changes
        constants.append(value)

    names = code.co_names
    if current_path.endswith("/PicoPublisher/publish_joysticks"):
        if names.count("get_Y_button") != 1:
            fail(f"Unexpected Pico Y button bytecode names: {names!r}")
        if names.count("get_left_trigger") != 1:
            fail(f"Unexpected Pico trigger bytecode names: {names!r}")
        template = _publish_joysticks_left_trigger_edge.__code__
        code = template.replace(
            co_name=code.co_name,
            co_filename=code.co_filename,
            co_firstlineno=code.co_firstlineno,
        )
        changed += 1
    elif tuple(constants) != code.co_consts:
        code = code.replace(co_consts=tuple(constants), co_names=names)
    return code, changed


def patch_heartbeat_timeout_code(
    code: types.CodeType, timeout_seconds: int, path: str = ""
):
    """Replace only the heartbeat watchdog threshold with a literal value."""
    dis_module = __import__("dis")
    heartbeat_time_attr = "_".join(("last", "heartbeat", "time"))
    release_timeout_attr = "_".join(("release", "timeout"))
    current_path = f"{path}/{code.co_name}"
    changed = 0
    constants = []
    for value in code.co_consts:
        if isinstance(value, types.CodeType):
            value, child_changes = patch_heartbeat_timeout_code(
                value, timeout_seconds, current_path
            )
            changed += child_changes
        constants.append(value)

    if current_path.endswith(
        "/WebsocketServer/_broadcast_publisher_states"
    ):
        instructions = list(dis_module.get_instructions(code))
        sites = []
        for index, instruction in enumerate(instructions[:-4]):
            following = instructions[index + 1 : index + 5]
            if (
                instruction.opname == "LOAD_ATTR"
                and instruction.argval == heartbeat_time_attr
                and following[0].opname == "BINARY_SUBTRACT"
                and following[1].opname == "LOAD_FAST"
                and following[1].argval == "self"
                and following[2].opname == "LOAD_ATTR"
                and following[2].argval == release_timeout_attr
                and following[3].opname == "COMPARE_OP"
                and following[3].argval == ">"
            ):
                sites.append((following[1], following[2]))
        if len(sites) != 1:
            fail(
                "Expected one heartbeat timeout comparison, got "
                f"{sites!r}"
            )

        if timeout_seconds in constants:
            timeout_index = constants.index(timeout_seconds)
        else:
            constants.append(timeout_seconds)
            timeout_index = len(constants) - 1
        if timeout_index > 255:
            fail("Heartbeat timeout constant needs EXTENDED_ARG")

        load_self, load_release_timeout = sites[0]
        bytecode = bytearray(code.co_code)
        if (
            bytecode[load_self.offset] != dis_module.opmap["LOAD_FAST"]
            or bytecode[load_self.offset + 1] != load_self.arg
            or bytecode[load_release_timeout.offset]
            != dis_module.opmap["LOAD_ATTR"]
            or bytecode[load_release_timeout.offset + 1]
            != load_release_timeout.arg
        ):
            fail("Unexpected Python 3.10 heartbeat bytecode encoding")
        bytecode[load_self.offset] = dis_module.opmap["LOAD_CONST"]
        bytecode[load_self.offset + 1] = timeout_index
        bytecode[load_release_timeout.offset] = dis_module.opmap["NOP"]
        bytecode[load_release_timeout.offset + 1] = 0
        code = code.replace(
            co_code=bytes(bytecode), co_consts=tuple(constants)
        )
        changed += 1
    elif tuple(constants) != code.co_consts:
        code = code.replace(co_consts=tuple(constants))
    return code, changed


def patch_pyz(
    pyz: bytes,
    swap_pico_x_y: bool,
    pico_enable_left_trigger: bool,
    heartbeat_timeout_seconds: int | None,
) -> bytes:
    if pyz[:4] != b"PYZ\0":
        fail("Embedded PYZ header not found")
    toc_offset = struct.unpack("!i", pyz[8:12])[0]
    toc_object = marshal.loads(pyz[toc_offset:])
    if not isinstance(toc_object, (list, tuple)):
        fail("Unexpected PYZ TOC format")

    targets_found = set()
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

        if name == "websocket_server":
            code = marshal.loads(zlib.decompress(compressed))
            code, changes = patch_collect_code(code)
            if changes != 1:
                fail(f"Expected one collect() patch, got {changes}")
            if heartbeat_timeout_seconds is not None:
                code, changes = patch_heartbeat_timeout_code(
                    code, heartbeat_timeout_seconds
                )
                if changes != 1:
                    fail(
                        "Expected one heartbeat timeout patch, got "
                        f"{changes}"
                    )
            compressed = zlib.compress(marshal.dumps(code), 6)
            targets_found.add(name)
        elif name == "pico" and (swap_pico_x_y or pico_enable_left_trigger):
            code = marshal.loads(zlib.decompress(compressed))
            if swap_pico_x_y:
                code, changes = patch_pico_button_code(code)
            else:
                code, changes = patch_pico_trigger_enable_code(code)
            if changes != 1:
                fail(f"Expected one Pico enable-input patch, got {changes}")
            compressed = zlib.compress(marshal.dumps(code), 6)
            targets_found.add(name)

        rebuilt_entries.append((name, (typecode, cursor, len(compressed))))
        data_chunks.append(compressed)
        cursor += len(compressed)

    expected_targets = {"websocket_server"}
    if swap_pico_x_y or pico_enable_left_trigger:
        expected_targets.add("pico")
    if targets_found != expected_targets:
        fail(f"Missing PYZ patch targets: {expected_targets - targets_found!r}")

    toc_bytes = marshal.dumps(rebuilt_entries)
    header = bytearray(pyz[:header_length])
    struct.pack_into("!i", header, 8, cursor)
    return bytes(header) + b"".join(data_chunks) + toc_bytes


def rebuild_pkg(
    pkg: bytes,
    entries,
    pyvers: int,
    pylib: str,
    swap_pico_x_y: bool,
    pico_enable_left_trigger: bool,
    heartbeat_timeout_seconds: int | None,
) -> bytes:
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
            raw = patch_pyz(
                raw,
                swap_pico_x_y,
                pico_enable_left_trigger,
                heartbeat_timeout_seconds,
            )
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


def validate_patch(
    executable_path: Path,
    swap_pico_x_y: bool,
    pico_enable_left_trigger: bool,
    heartbeat_timeout_seconds: int | None,
) -> None:
    executable = executable_path.read_bytes()
    pkg, entries, _, _ = parse_pkg(executable)
    pyz_entry = next(entry for entry in entries if entry["name"] == "PYZ.pyz")
    pyz = pkg[pyz_entry["offset"] : pyz_entry["offset"] + pyz_entry["length"]]
    toc_offset = struct.unpack("!i", pyz[8:12])[0]
    toc = dict(marshal.loads(pyz[toc_offset:]))
    matches = []

    def walk(item: types.CodeType, path: str = "") -> None:
        current = f"{path}/{item.co_name}"
        if current.endswith("/WebsocketServer/collect"):
            matches.append(item.co_names)
        for child in item.co_consts:
            if isinstance(child, types.CodeType):
                walk(child, current)

    typecode, offset, length = toc["websocket_server"]
    del typecode
    code = marshal.loads(zlib.decompress(pyz[offset : offset + length]))
    walk(code)
    if len(matches) != 1 or "CLAMP" not in matches[0] or "GRIPPER" in matches[0]:
        fail(f"Patched collect() validation failed: {matches!r}")

    if heartbeat_timeout_seconds is not None:
        dis_module = __import__("dis")
        heartbeat_time_attr = "_".join(("last", "heartbeat", "time"))
        heartbeat_matches = []

        def walk_heartbeat(item: types.CodeType, path: str = "") -> None:
            current = f"{path}/{item.co_name}"
            if current.endswith(
                "/WebsocketServer/_broadcast_publisher_states"
            ):
                heartbeat_matches.append(item)
            for child in item.co_consts:
                if isinstance(child, types.CodeType):
                    walk_heartbeat(child, current)

        walk_heartbeat(code)
        if len(heartbeat_matches) != 1:
            fail("Patched heartbeat watchdog validation failed")
        instructions = list(
            dis_module.get_instructions(heartbeat_matches[0])
        )
        sites = []
        for index, instruction in enumerate(instructions[:-4]):
            following = instructions[index + 1 : index + 5]
            if (
                instruction.opname == "LOAD_ATTR"
                and instruction.argval == heartbeat_time_attr
                and following[0].opname == "BINARY_SUBTRACT"
                and following[1].opname == "LOAD_CONST"
                and following[1].argval == heartbeat_timeout_seconds
                and following[2].opname == "NOP"
                and following[3].opname == "COMPARE_OP"
                and following[3].argval == ">"
            ):
                sites.append(instruction.offset)
        if len(sites) != 1:
            fail(
                "Heartbeat timeout validation failed: "
                f"expected {heartbeat_timeout_seconds}, sites={sites!r}"
            )

    if swap_pico_x_y or pico_enable_left_trigger:
        _, offset, length = toc["pico"]
        code = marshal.loads(zlib.decompress(pyz[offset : offset + length]))
        joystick_matches = []

        def walk_pico(item: types.CodeType, path: str = "") -> None:
            current = f"{path}/{item.co_name}"
            if current.endswith("/PicoPublisher/publish_joysticks"):
                joystick_matches.append(item)
            for child in item.co_consts:
                if isinstance(child, types.CodeType):
                    walk_pico(child, current)

        walk_pico(code)
        if len(joystick_matches) != 1:
            fail("Patched Pico publish_joysticks() validation failed")
        joystick = joystick_matches[0]
        # LOAD_METHOD name operands are verified by disassembly order: the
        # first left-controller lookup must now be Y and the second must be X.
        instructions = [
            instruction.argval
            for instruction in __import__("dis").get_instructions(joystick)
            if instruction.opname == "LOAD_METHOD"
            and instruction.argval
            in {"get_X_button", "get_Y_button", "get_left_trigger"}
        ]
        if swap_pico_x_y:
            if instructions[:2] != ["get_Y_button", "get_X_button"]:
                fail(f"Pico X/Y validation failed: {instructions[:2]!r}")
        elif (
            instructions[:2] != ["get_X_button", "get_left_trigger"]
            or instructions.count("get_left_trigger") != 1
            or "_left_trigger_enable_pressed" not in joystick.co_names
            or "getattr" not in joystick.co_names
        ):
            fail(f"Pico trigger-edge validation failed: {instructions!r}")
        if pico_enable_left_trigger:
            stores = [
                instruction.argval
                for instruction in __import__("dis").get_instructions(joystick)
                if instruction.opname == "STORE_ATTR"
            ]
            if stores[:5] != [
                "a_button",
                "b_button",
                "_left_trigger_enable_pressed",
                "trigger_value",
                "squeeze_value",
            ]:
                fail(
                    "Pico trigger-edge store validation failed: "
                    f"{stores[:5]!r}"
                )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    pico_group = parser.add_mutually_exclusive_group()
    pico_group.add_argument(
        "--swap-pico-x-y",
        action="store_true",
        help="map physical X to the vendor Y teleoperation switch",
    )
    pico_group.add_argument(
        "--pico-enable-left-trigger",
        action="store_true",
        help="map the left trigger to the vendor Y teleoperation switch",
    )
    parser.add_argument(
        "--heartbeat-timeout-seconds",
        type=int,
        metavar="SECONDS",
        help=(
            "set the backend heartbeat STOP interval while retaining the "
            "watchdog"
        ),
    )
    args = parser.parse_args()

    if sys.version_info[:2] != (3, 10):
        fail(f"Python 3.10 required, got {sys.version.split()[0]}")
    if args.input.resolve() == args.output.resolve():
        fail("Output must be a separate file")
    if not args.input.is_file():
        fail(f"Input executable not found: {args.input}")
    if (
        args.heartbeat_timeout_seconds is not None
        and not 1 <= args.heartbeat_timeout_seconds <= 3600
    ):
        fail("Heartbeat timeout must be between 1 and 3600 seconds")

    source = args.input.read_bytes()
    pkg, entries, pyvers, pylib = parse_pkg(source)
    if pyvers != 310 or pylib != "libpython3.10.so.1.0":
        fail(f"Unexpected bundle runtime: pyvers={pyvers}, pylib={pylib}")
    rebuilt_pkg = rebuild_pkg(
        pkg,
        entries,
        pyvers,
        pylib,
        args.swap_pico_x_y,
        args.pico_enable_left_trigger,
        args.heartbeat_timeout_seconds,
    )

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
    validate_patch(
        args.output,
        args.swap_pico_x_y,
        args.pico_enable_left_trigger,
        args.heartbeat_timeout_seconds,
    )
    print("PATCH_OK=WebsocketServer.collect:GRIPPER->CLAMP")
    if args.swap_pico_x_y:
        print("PICO_BUTTON_WORKAROUND_OK=X->vendor-Y,Y->vendor-X")
    if args.pico_enable_left_trigger:
        print("PICO_BUTTON_WORKAROUND_OK=left-trigger-rising-edge->vendor-Y")
    if args.heartbeat_timeout_seconds is not None:
        print(
            "HEARTBEAT_WATCHDOG_OK="
            f"{args.heartbeat_timeout_seconds}s"
        )
    print(f"OUTPUT={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
