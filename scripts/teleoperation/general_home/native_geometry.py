"""Offline extraction of constructor arguments from pinned S2 libraries.

Unicorn interprets only reviewed data-initialization prefixes. Every call is
replaced by a bounded Python data stub; no vendor function, loader, ROS or
system call runs on the host. Results describe compiled defaults, not the
active runtime model, FK, coverage of CAD, or permission to execute a path.
"""
from __future__ import annotations

import hashlib
import math
import struct
from pathlib import Path

from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE
from unicorn import UC_PROT_READ, UC_PROT_WRITE, UC_PROT_EXEC
from unicorn.x86_const import (UC_X86_REG_RDI, UC_X86_REG_RSI,
    UC_X86_REG_RDX, UC_X86_REG_RCX, UC_X86_REG_R8, UC_X86_REG_RAX,
    UC_X86_REG_RSP, UC_X86_REG_RIP, UC_X86_REG_XMM0,
    UC_X86_REG_XMM1, UC_X86_REG_XMM2)

BUILDS = {
    'arm': {
        'sha256': '2a41cf5520672c9dcbd1c532eff775b4ce6d9ff1e100485d6ca7ba8174ad251c',
        'start': 0xd580, 'end': 0xf7cf, 'array': 0x37920, 'count': 7,
        'stubs': {0xa050: 'noop', 0x9f30: 'noop', 0x24130: 'string',
            0x9aa0: 'identity', 0x9ad0: 'vector', 0x9c60: 'points',
            0x9990: 'noop', 0xa0e0: 'noop', 0x9e30: 'noop', 0x9a70: 'default'},
    },
    'head': {
        'sha256': 'ba3707df647ee435041de713e6dabe451fd1bb59795b783179ec529901855866',
        'start': 0x8460, 'end': 0xa3bf, 'array': 0x32360, 'count': 2,
        'stubs': {0x7b50: 'noop', 0x7aa0: 'noop', 0x83a0: 'string',
            0x7730: 'identity', 0x7760: 'vector', 0x7840: 'points',
            0x76c0: 'noop', 0x7bd0: 'noop', 0x7a20: 'noop', 0x7720: 'default',
            0x7920: 'dimensions'},
    },
    'leg': {
        'sha256': '0de5bc0bbd7469693e23eb4c58c0fbb1012fc5063ecd7a2184a4886eab6a1fe7',
        'start': 0xb380, 'end': 0xd6b2, 'code_end': 0xda78,
        'array': 0x27500, 'count': 6,
        'local_relocations': {0x26f18: 0x298f0, 0x26fa8: 0x298e8},
        'stubs': {0xa0b0: 'noop', 0x9fb0: 'noop', 0xe1c0: 'string',
            0x9ab0: 'identity', 0x9b00: 'vector', 0x9c40: 'points',
            0x99e0: 'noop', 0xa150: 'noop', 0x9ee0: 'noop', 0x9a40: 'allocate',
            0xa120: 'three_scalars', 0x9a80: 'default', 0xa130: 'matrix_append'},
    },
}

IMAGE, STACK, HEAP = 0x1000000, 0x2000000, 0x3000000


class InitializerArguments:
    """Intercept constructor inputs; deliberately do not construct primitives."""

    def __init__(self, path, component):
        if component not in BUILDS:
            raise ValueError('Unknown component')
        self.build = build = BUILDS[component]
        self.component = component
        blob = Path(path).read_bytes()
        if hashlib.sha256(blob).hexdigest() != build['sha256']:
            raise ValueError('Unreviewed geometry library hash')
        if blob[:6] != b'\x7fELF\x02\x01' or struct.unpack_from('<H', blob, 18)[0] != 62:
            raise ValueError('Expected little-endian x86-64 ELF')
        phoff = struct.unpack_from('<Q', blob, 32)[0]
        phsize, phnum = struct.unpack_from('<HH', blob, 54)
        segments = [struct.unpack_from('<IIQQQQQQ', blob, phoff+i*phsize)
            for i in range(phnum)]
        loads = [s for s in segments if s[0] == 1]
        length = (max(s[3]+s[6] for s in loads)+4095)//4096*4096
        if length > 1024*1024:
            raise ValueError('Unexpected ELF layout')
        self.uc = uc = Uc(UC_ARCH_X86, UC_MODE_64)
        uc.mem_map(IMAGE, length)
        for _, _, offset, address, _, size, _, _ in loads:
            uc.mem_write(IMAGE+address, blob[offset:offset+size])
        for target, value in build.get('local_relocations', {}).items():
            uc.mem_write(IMAGE+target, struct.pack('<Q', IMAGE+value))
        # Executable pages remain immutable; data/BSS can be initialized.
        for _, flags, _, address, _, _, mem_size, _ in loads:
            low = address//4096*4096
            high = (address+mem_size+4095)//4096*4096
            permissions = UC_PROT_READ | (UC_PROT_EXEC if flags & 1 else 0)
            if flags & 2:
                permissions |= UC_PROT_WRITE
            uc.mem_protect(IMAGE+low, high-low, permissions)
        uc.mem_map(0, 4096, UC_PROT_READ)  # synthetic TLS stack-canary read only
        uc.mem_map(STACK, 0x10000, UC_PROT_READ | UC_PROT_WRITE)
        uc.mem_map(HEAP, 0x100000, UC_PROT_READ | UC_PROT_WRITE)
        self.heap_next = HEAP
        self.strings = {}
        self.vectors = {}
        self.records = []
        self.call_count = 0
        self.instruction_count = 0
        self.finished = False
        self.failure = None
        self.identity = self.allocate(96)
        uc.mem_write(self.identity, struct.pack('<12d', 1,0,0,0,1,0,0,0,1,0,0,0))
        uc.reg_write(UC_X86_REG_RSP, STACK+0xfff8)
        uc.hook_add(UC_HOOK_CODE, self.guard)

    def allocate(self, size):
        if not 0 < size <= 65536 or self.heap_next+size >= HEAP+0x100000:
            raise ValueError('Bounded emulated allocation exceeded')
        address = self.heap_next
        self.heap_next += (size+15)//16*16
        return address

    def doubles(self, address, count):
        if not 1 <= count <= 192:
            raise ValueError('Unexpected data size')
        values = list(struct.unpack('<'+'d'*count, self.uc.mem_read(address, count*8)))
        if not all(math.isfinite(x) and abs(x) < 1000 for x in values):
            raise ValueError('Invalid constructor data')
        return values

    def stub(self, kind):
        uc = self.uc
        rdi, rsi, rdx, rcx, r8 = [uc.reg_read(r) for r in
            (UC_X86_REG_RDI, UC_X86_REG_RSI, UC_X86_REG_RDX, UC_X86_REG_RCX, UC_X86_REG_R8)]
        if kind == 'noop':
            return
        if kind == 'allocate':
            uc.reg_write(UC_X86_REG_RAX, self.allocate(rdi))
            return
        if kind == 'identity':
            uc.reg_write(UC_X86_REG_RAX, self.identity)
            return
        if kind == 'string':
            chars = bytearray()
            for i in range(256):
                byte = bytes(uc.mem_read(rsi+i, 1))
                if byte == b'\0':
                    break
                chars.extend(byte)
            else:
                raise ValueError('Unterminated string')
            self.strings[rdi] = chars.decode('ascii')
            storage = self.allocate(len(chars)+1)
            uc.mem_write(storage, bytes(chars)+b'\0')
            uc.mem_write(rdi, struct.pack('<QQQ', storage, len(chars), len(chars)))
            return
        if kind == 'vector':
            if not 1 <= rdx <= 64:
                raise ValueError('Unexpected point count')
            values = self.doubles(rsi, rdx*3)
            self.vectors[rdi] = [values[i:i+3] for i in range(0, len(values), 3)]
            storage = self.allocate(rdx*24)
            uc.mem_write(storage, struct.pack('<'+'d'*len(values), *values))
            uc.mem_write(rdi, struct.pack('<QQQ', storage, storage+rdx*24, storage+rdx*24))
            return
        if kind == 'matrix_append':
            start, end, capacity = struct.unpack('<QQQ', uc.mem_read(rdi, 24))
            if end != rsi or not 0 <= end-start <= 16*128:
                raise ValueError('Unexpected matrix insertion')
            previous = bytes(uc.mem_read(start, end-start)) if start else b''
            value = bytes(uc.mem_read(rdx, 128))
            storage = self.allocate(len(previous)+128)
            uc.mem_write(storage, previous+value)
            end = storage+len(previous)+128
            uc.mem_write(rdi, struct.pack('<QQQ', storage, end, end))
            return
        record = {'object_offset': hex(rdi-IMAGE), 'constructor': kind}
        if kind != 'default':
            record['type_enum'] = rsi
            if kind in ('points', 'dimensions'):
                record['name'] = self.strings[r8]
                record['transform_raw_12'] = self.doubles(rcx, 12)
                if kind == 'points':
                    record['points'] = self.vectors[rdx]
                else:
                    record['dimensions_argument'] = self.doubles(rdx, 3)
            elif kind == 'three_scalars':
                record['name'] = self.strings[rcx]
                record['transform_raw_12'] = self.doubles(rdx, 12)
            else:
                raise ValueError('Unknown stub')
            if kind in ('points', 'three_scalars'):
                count = 1 if kind == 'points' else 3
                record['scalar_arguments'] = [struct.unpack('<d',
                    (uc.reg_read(reg) & ((1 << 64)-1)).to_bytes(8, 'little'))[0]
                    for reg in (UC_X86_REG_XMM0, UC_X86_REG_XMM1, UC_X86_REG_XMM2)[:count]]
                if not all(math.isfinite(x) for x in record['scalar_arguments']):
                    raise ValueError('Nonfinite scalar')
        self.records.append(record)

    def guard(self, uc, address, size, _):
        self.instruction_count += 1
        offset = address-IMAGE
        try:
            if offset == self.build['end']:
                self.finished = True
                uc.emu_stop()
                return
            if offset in self.build['stubs']:
                self.call_count += 1
                self.stub(self.build['stubs'][offset])
                stack = uc.reg_read(UC_X86_REG_RSP)
                target = struct.unpack('<Q', uc.mem_read(stack, 8))[0]
                if not IMAGE+self.build['start'] <= target <= IMAGE+self.build.get('code_end', self.build['end']):
                    raise ValueError('Stub return left reviewed prefix')
                uc.reg_write(UC_X86_REG_RSP, stack+8)
                uc.reg_write(UC_X86_REG_RIP, target)
                return
            if not self.build['start'] <= offset < self.build.get('code_end', self.build['end']):
                raise ValueError(f'Code left reviewed prefix at {offset:#x}')
            instruction = bytes(uc.mem_read(address, min(size, 2)))
            if instruction in (b'\x0f\x05', b'\x0f\x34', b'\xcd\x80'):
                raise ValueError('System instruction rejected')
        except Exception as exc:
            self.failure = str(exc)
            uc.emu_stop()

    def extract(self):
        if self.instruction_count:
            raise ValueError('Create a fresh extractor for each run')
        self.uc.emu_start(IMAGE+self.build['start'], IMAGE+self.build['end']+1,
            timeout=2000000, count=100000)
        if self.failure or not self.finished:
            raise ValueError(self.failure or 'Emulation budget exhausted')
        indexed = {int(x['object_offset'], 16): x for x in self.records}
        component_records = []
        for index in range(self.build['count']):
            offset = self.build['array']+0x140*index
            if offset not in indexed:
                raise ValueError('Component array was not completely extracted')
            component_records.append(dict(indexed[offset], array_index=index))
        return {'component': self.component, 'sha256': self.build['sha256'],
            'scope': 'compiled_default_constructor_arguments_only',
            'units': 'raw_native_arguments; spatial SI interpretation requires review',
            'component_primitives': component_records, 'all_constructor_calls': self.records,
            'emulated_instructions': self.instruction_count, 'stubbed_calls': self.call_count,
            'host_native_calls': 0, 'movement_commands': 0, 'physical_approval': False,
            'cad_coverage_verified': False, 'active_runtime_selection_verified': False}
