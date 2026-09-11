"""Emulate a pinned vendor mathematical function; never dlopen Motion or ROS.

Only the numeric CubicSplineInterpolate template is entered. Constructors,
PLT calls, system calls and code outside that function are not permitted.
This verifies binary arithmetic, not controller tracking or physical stopping.
"""
from __future__ import annotations

import hashlib
import struct
from pathlib import Path

import numpy as np
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE, UC_PROT_READ, UC_PROT_WRITE, UC_PROT_EXEC
from unicorn.x86_const import (UC_X86_REG_RDI, UC_X86_REG_RSI, UC_X86_REG_RDX,
    UC_X86_REG_RCX, UC_X86_REG_R8, UC_X86_REG_RSP, UC_X86_REG_RIP,
    UC_X86_REG_XMM0, UC_X86_REG_XMM1)

SHA256 = '1267e370614d5350706caa061a24c162e3333248b9b1af74b8ea319a3d5ee329'
FUNCTION_START = 0x37c0
FUNCTION_END = 0x3c20
IMAGE = 0x1000000
STACK = 0x2000000
DATA = 0x3000000
RETURN = 0x4000000


def vectors(*values):
    arrays = [np.asarray(value, dtype=float) for value in values]
    if (not arrays or arrays[0].ndim != 1 or not 1 <= len(arrays[0]) <= 20
            or any(a.shape != arrays[0].shape or not np.isfinite(a).all() for a in arrays)):
        raise ValueError('Expected equal finite vectors with 1..20 entries')
    return arrays


def cubic_hermite(q0, q1, v0, v1, duration, elapsed):
    q0, q1, v0, v1 = vectors(q0, q1, v0, v1)
    if not np.isfinite([duration, elapsed]).all() or duration <= 0 or not 0 <= elapsed <= duration:
        raise ValueError('Invalid duration/elapsed time')
    u = elapsed/duration
    return ((2*u**3-3*u**2+1)*q0 + (-2*u**3+3*u**2)*q1
            + (u**3-2*u**2+u)*duration*v0 + (u**3-u**2)*duration*v1)


class NativeSplineEmulator:
    def __init__(self, path):
        blob = Path(path).read_bytes()
        if hashlib.sha256(blob).hexdigest() != SHA256:
            raise ValueError('Unreviewed interpolation library hash')
        if blob[:6] != b'\x7fELF\x02\x01' or struct.unpack_from('<H',blob,18)[0] != 62:
            raise ValueError('Expected little-endian x86-64 ELF')
        phoff = struct.unpack_from('<Q',blob,32)[0]
        phsize, phnum = struct.unpack_from('<HH',blob,54)
        segments = [struct.unpack_from('<IIQQQQQQ',blob,phoff+i*phsize) for i in range(phnum)]
        loads = [s for s in segments if s[0] == 1]
        length = (max(s[3]+s[6] for s in loads)+4095)//4096*4096
        if length > 1024*1024:
            raise ValueError('Unexpected ELF layout')
        self.uc = uc = Uc(UC_ARCH_X86, UC_MODE_64)
        uc.mem_map(IMAGE, length)
        for _, _, offset, address, _, file_size, _, _ in loads:
            uc.mem_write(IMAGE+address,blob[offset:offset+file_size])
        uc.mem_protect(IMAGE,length,UC_PROT_READ | UC_PROT_EXEC)
        uc.mem_map(STACK,0x10000,UC_PROT_READ | UC_PROT_WRITE)
        uc.mem_map(DATA,0x10000,UC_PROT_READ | UC_PROT_WRITE)
        uc.mem_map(RETURN,0x1000,UC_PROT_READ | UC_PROT_EXEC)
        self.failure = None

        def instruction_guard(engine, address, size, _):
            if not IMAGE+FUNCTION_START <= address < IMAGE+FUNCTION_END:
                self.failure = 'Code left reviewed numeric function'
                engine.emu_stop()
            elif bytes(engine.mem_read(address, min(size,2))) in (b'\x0f\x05',b'\x0f\x34',b'\xcd\x80'):
                self.failure = 'System call instruction rejected'
                engine.emu_stop()
        uc.hook_add(UC_HOOK_CODE,instruction_guard)

    def evaluate(self, q0, q1, v0, v1, duration, elapsed):
        arrays = vectors(q0,q1,v0,v1)
        # Validate time separately; do not substitute the Python answer.
        if not np.isfinite([duration,elapsed]).all() or duration <= 0 or not 0 <= elapsed <= duration:
            raise ValueError('Invalid duration/elapsed time')
        n = len(arrays[0]); uc=self.uc
        arrays.append(np.full(n,np.nan))
        for index, array in enumerate(arrays):
            obj=DATA+index*0x1000; storage=obj+0x100
            uc.mem_write(obj,struct.pack('<QQ',storage,n))
            uc.mem_write(storage,array.astype('<f8').tobytes())
        for register, index in ((UC_X86_REG_RDI,0),(UC_X86_REG_RSI,1),
                (UC_X86_REG_RDX,2),(UC_X86_REG_RCX,3),(UC_X86_REG_R8,4)):
            uc.reg_write(register,DATA+index*0x1000)
        for register,value in ((UC_X86_REG_XMM0,duration),(UC_X86_REG_XMM1,elapsed)):
            uc.reg_write(register,int.from_bytes(struct.pack('<d',value),'little'))
        stack=STACK+0xfff8
        uc.mem_write(stack,struct.pack('<Q',RETURN));uc.reg_write(UC_X86_REG_RSP,stack)
        self.failure=None
        uc.emu_start(IMAGE+FUNCTION_START,RETURN,timeout=1000000,count=10000)
        if self.failure or uc.reg_read(UC_X86_REG_RIP) != RETURN:
            raise RuntimeError(self.failure or 'Emulation budget exhausted')
        result=np.frombuffer(bytes(uc.mem_read(DATA+0x4100,n*8)),dtype='<f8').copy()
        if not np.isfinite(result).all():
            raise ValueError('Unwritten/nonfinite native output')
        return result
