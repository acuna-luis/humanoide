"""Trace a reviewed *group-pair loop* in a pinned Motion binary, offline.

This is not an emulator of CollisionHelper, nor a collision checker. The loop
receives synthetic groups; its distance call is replaced with an explicit
non-collision result. No claim about the active robot's groups follows from it.
Never load this ELF with ctypes/dlopen or call the native implementation.
"""
import hashlib
from pathlib import Path
import struct

from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE
from unicorn import UC_PROT_READ, UC_PROT_WRITE, UC_PROT_EXEC
from unicorn.x86_const import (UC_X86_REG_RBP, UC_X86_REG_RSP,
    UC_X86_REG_RIP, UC_X86_REG_RDI, UC_X86_REG_R8, UC_X86_REG_XMM0)

SHA256 = '7322b075badd43ad6f20f87fe9ff6b4b1cd6fc95bcd44d8c5048df26486432de'
IMAGE, STACK, DATA = 0x1000000, 0x2000000, 0x3000000
START, END, DISTANCE_PLT = 0xe2750, 0xe229f, 0xa16d0
# Include only the successful-distance branch and its loop bookkeeping.
RANGES = ((0xe2750, 0xe288a), (0xe29c8, 0xe29f0))


def trace_group_pairs(library, group_count):
    if type(group_count) is not int or not 1 <= group_count <= 16:
        raise ValueError('Expected 1..16 synthetic groups')
    blob = Path(library).read_bytes()
    if hashlib.sha256(blob).hexdigest() != SHA256:
        raise ValueError('Unreviewed librobot.so hash')
    if blob[:6] != b'\x7fELF\x02\x01' or struct.unpack_from('<H', blob, 18)[0] != 62:
        raise ValueError('Expected little-endian x86-64 ELF')
    phoff = struct.unpack_from('<Q', blob, 32)[0]
    phsize, phnum = struct.unpack_from('<HH', blob, 54)
    segments = [struct.unpack_from('<IIQQQQQQ', blob, phoff+i*phsize)
                for i in range(phnum)]
    loads = [s for s in segments if s[0] == 1]
    length = (max(s[3]+s[6] for s in loads)+4095)//4096*4096
    if length > 4*1024*1024:
        raise ValueError('Unexpected ELF size')
    uc = Uc(UC_ARCH_X86, UC_MODE_64)
    uc.mem_map(IMAGE, length)
    for _, _, offset, address, _, size, _, _ in loads:
        uc.mem_write(IMAGE+address, blob[offset:offset+size])
    uc.mem_protect(IMAGE, length, UC_PROT_READ | UC_PROT_EXEC)
    uc.mem_map(STACK, 0x10000, UC_PROT_READ | UC_PROT_WRITE)
    uc.mem_map(DATA, 4096, UC_PROT_READ | UC_PROT_WRITE)
    frame = STACK+0xff00
    # Synthetic std::vector<GeometricPrimitiveSet>; each set occupies 24 bytes.
    # No primitive data is supplied or read by the reviewed pair-selection loop.
    uc.mem_write(frame-0x270, struct.pack('<QQ', DATA, DATA+24*group_count))
    uc.mem_write(frame-0x2b0, struct.pack('<d', .002))
    uc.reg_write(UC_X86_REG_RBP, frame)
    uc.reg_write(UC_X86_REG_RSP, frame-0x330)
    calls, failure = [], []
    state = dict(finished=False, instructions=0)

    def guard(machine, address, size, _):
        offset = address-IMAGE
        state['instructions'] += 1
        if offset == END:
            state['finished'] = True
            machine.emu_stop()
            return
        if offset == DISTANCE_PLT:
            indices = []
            for register in (UC_X86_REG_RDI, UC_X86_REG_R8):
                relative = machine.reg_read(register)-DATA
                if relative < 0 or relative % 24 or relative >= group_count*24:
                    failure.append('Distance argument is not a synthetic group')
                    machine.emu_stop()
                    return
                indices.append(relative//24)
            calls.append(indices)
            # Deliberately stub distance, not physical collision evidence.
            machine.reg_write(UC_X86_REG_XMM0, struct.unpack('<Q', struct.pack('<d', 1.))[0])
            sp = machine.reg_read(UC_X86_REG_RSP)
            target = struct.unpack('<Q', machine.mem_read(sp, 8))[0]
            if target != IMAGE+0xe286e:
                failure.append('Unexpected call site')
                machine.emu_stop()
                return
            machine.reg_write(UC_X86_REG_RSP, sp+8)
            machine.reg_write(UC_X86_REG_RIP, target)
            return
        if not any(lo <= offset < hi for lo, hi in RANGES):
            failure.append('Instruction outside reviewed loop: '+hex(offset))
            machine.emu_stop()

    uc.hook_add(UC_HOOK_CODE, guard)
    uc.emu_start(IMAGE+START, IMAGE+length, timeout=1_000_000, count=20_000)
    if failure or not state['finished']:
        raise ValueError('; '.join(failure) or 'Trace exhausted its instruction/time budget')
    return dict(group_count=group_count, queried_group_pairs=calls,
        instructions=state['instructions'], distance_result_is_stubbed=True,
        active_runtime_group_membership_verified=False,
        scope='reviewed successful-distance group-pair loop only',
        library_sha256=SHA256, start_address=hex(START), stop_address=hex(END),
        host_native_calls=0, physical_approval=False, installable=False)
