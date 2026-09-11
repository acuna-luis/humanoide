"""Pinned, isolated arithmetic for S2 arm FK and capsule attachment frames.

No dynamic loader or robot transport. Only two numeric functions and the
reviewed capsule-placement prefix are interpreted. sincos is a Python stub;
SetPose is intercepted as data. This does not reconstruct runtime calibration.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
import struct

import numpy as np
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE
from unicorn import UC_PROT_READ, UC_PROT_WRITE, UC_PROT_EXEC
from unicorn.x86_const import (UC_X86_REG_RDI, UC_X86_REG_RSI, UC_X86_REG_RDX,
    UC_X86_REG_RSP, UC_X86_REG_RIP, UC_X86_REG_XMM0)
from .native_geometry import BUILDS

IMAGE, STACK, DATA, RETURN = 0x1000000, 0x2000000, 0x3000000, 0x4000000


def dh_poses(geometry, q):
    """Independent standard-DH calculation for comparison, not emulated output."""
    geometry, q = np.asarray(geometry), np.asarray(q)
    if geometry.shape != (4,7) or q.shape != (7,) or not np.isfinite(geometry).all() or not np.isfinite(q).all():
        raise ValueError('Expected finite 4x7 DH parameters and seven angles')
    result, pose = [], np.eye(4)
    for k, angle in enumerate(q):
        theta, a, d, alpha = geometry[:,k]
        c, s = math.cos(theta+angle), math.sin(theta+angle)
        ca, sa = math.cos(alpha), math.sin(alpha)
        pose = pose @ np.array([[c,-s*ca,s*sa,a*c], [s,c*ca,-c*sa,a*s],
            [0,sa,ca,d], [0,0,0,1]])
        result.append(pose.copy())
    return np.array(result)


class NativeArmFrames:
    def __init__(self, path):
        blob = Path(path).read_bytes()
        if hashlib.sha256(blob).hexdigest() != BUILDS['arm']['sha256']:
            raise ValueError('Unreviewed arm library hash')
        if blob[:6] != b'\x7fELF\x02\x01' or struct.unpack_from('<H',blob,18)[0] != 62:
            raise ValueError('Expected little-endian x86-64 ELF')
        phoff = struct.unpack_from('<Q',blob,32)[0]
        phsize, phnum = struct.unpack_from('<HH',blob,54)
        loads = [struct.unpack_from('<IIQQQQQQ',blob,phoff+i*phsize) for i in range(phnum)]
        loads = [s for s in loads if s[0] == 1]
        length = (max(s[3]+s[6] for s in loads)+4095)//4096*4096
        if length > 1024*1024:
            raise ValueError('Unexpected library size')
        self.uc = uc = Uc(UC_ARCH_X86, UC_MODE_64)
        uc.mem_map(IMAGE, length)
        for _, _, offset, address, _, size, _, _ in loads:
            uc.mem_write(IMAGE+address, blob[offset:offset+size])
        uc.mem_protect(IMAGE, length, UC_PROT_READ | UC_PROT_EXEC)
        uc.mem_map(0,4096,UC_PROT_READ)
        uc.mem_map(STACK,0x10000,UC_PROT_READ | UC_PROT_WRITE)
        uc.mem_map(DATA,0x10000,UC_PROT_READ | UC_PROT_WRITE)
        uc.mem_map(RETURN,4096,UC_PROT_READ | UC_PROT_EXEC)
        self.geometry = np.frombuffer(bytes(uc.mem_read(IMAGE+0x2ff80,224)),dtype='<f8').reshape(4,7).copy()
        self.failure = None
        self.placed = []
        self.placement_done = False
        self.mode = None
        uc.hook_add(UC_HOOK_CODE,self.guard)
        self.run('constructor', 0x1af00, [DATA, IMAGE+0x2ff80, IMAGE+0x30060])

    def guard(self, uc, address, size, _):
        offset = address-IMAGE
        try:
            if self.mode == 'placement' and offset == 0x26d94:
                self.placement_done = True
                uc.emu_stop()
                return
            if offset == 0x9ef0:  # bounded libm sincos replacement
                raw = uc.reg_read(UC_X86_REG_XMM0) & ((1<<64)-1)
                angle = struct.unpack('<d',raw.to_bytes(8,'little'))[0]
                if not math.isfinite(angle) or abs(angle) > 100:
                    raise ValueError('Invalid trigonometric input')
                uc.mem_write(uc.reg_read(UC_X86_REG_RDI),struct.pack('<d',math.sin(angle)))
                uc.mem_write(uc.reg_read(UC_X86_REG_RSI),struct.pack('<d',math.cos(angle)))
                self.stub_return()
                return
            if self.mode == 'placement' and offset == 0x9c40:
                uc.reg_write(UC_X86_REG_RIP,IMAGE+0x1c500)
                return
            if self.mode == 'placement' and offset == 0x9b50:
                target, source = [uc.reg_read(r) for r in (UC_X86_REG_RDI,UC_X86_REG_RSI)]
                raw = bytes(uc.mem_read(source,128))
                self.placed.append((target,np.frombuffer(raw,dtype='<f8').reshape(4,4,order='F').copy()))
                self.stub_return()
                return
            ranges = {'constructor': [(0x1af00,0x1b414)], 'fk': [(0x1c500,0x1caaa)],
                'placement': [(0x26980,0x26d94),(0x1c500,0x1caaa)]}[self.mode]
            if not any(a <= offset < b for a,b in ranges):
                raise ValueError(f'Code outside reviewed arithmetic: {offset:#x}')
            if bytes(uc.mem_read(address,min(size,2))) in (b'\x0f\x05',b'\x0f\x34',b'\xcd\x80'):
                raise ValueError('System instruction rejected')
        except Exception as exc:
            self.failure = str(exc)
            uc.emu_stop()

    def stub_return(self):
        uc = self.uc
        stack = uc.reg_read(UC_X86_REG_RSP)
        target = struct.unpack('<Q',uc.mem_read(stack,8))[0]
        # Destination is checked again at the next emulated instruction.
        uc.reg_write(UC_X86_REG_RSP,stack+8)
        uc.reg_write(UC_X86_REG_RIP,target)

    def run(self, mode, entry, args):
        self.mode, self.failure = mode, None
        self.placed, self.placement_done = [], False
        uc = self.uc
        stack = STACK+0xfff8
        uc.mem_write(stack,struct.pack('<Q',RETURN))
        uc.reg_write(UC_X86_REG_RSP,stack)
        for register,value in zip((UC_X86_REG_RDI,UC_X86_REG_RSI,UC_X86_REG_RDX),args):
            uc.reg_write(register,value)
        uc.emu_start(IMAGE+entry,RETURN,timeout=1000000,count=100000)
        done = self.placement_done if mode == 'placement' else uc.reg_read(UC_X86_REG_RIP) == RETURN
        if self.failure or not done:
            raise ValueError(self.failure or 'Arithmetic budget exhausted')

    def evaluate(self, q):
        q = np.asarray(q,dtype=float)
        if q.shape != (7,) or not np.isfinite(q).all() or (np.abs(q)>10).any():
            raise ValueError('Expected seven finite joint angles in bounded domain')
        uc = self.uc
        uc.mem_write(DATA+0x1000,q.astype('<f8').tobytes())
        self.run('fk',0x1c500,[DATA+0x2000,DATA,DATA+0x1000])
        fk = np.array([np.frombuffer(bytes(uc.mem_read(DATA+0x2000+i*128,128)),dtype='<f8').reshape(4,4,order='F') for i in range(7)])
        if not np.isfinite(fk).all():
            raise ValueError('Invalid numeric FK output')
        # Minimal data fixture for UpdateLinkBoundingCapsulePoses. Identity base,
        # zero calibration offsets; the same constructor selects these indices.
        obj, primitives, indices, zeros, qobj = [DATA+x for x in (0x3000,0x4000,0x5000,0x6000,0x7000)]
        uc.mem_write(obj,b'\0'*0x300)
        uc.mem_write(obj+0x30,struct.pack('<12d',1,0,0,0,1,0,0,0,1,0,0,0))
        uc.mem_write(obj+0x90,struct.pack('<QQ',zeros,7))
        uc.mem_write(obj+0xd8,struct.pack('<QQQ',primitives,primitives+4*0x140,primitives+4*0x140))
        uc.mem_write(indices,struct.pack('<4i',6,5,3,1))
        uc.mem_write(obj+0x108,struct.pack('<QQQ',indices,indices+16,indices+16))
        uc.mem_write(obj+0x198,struct.pack('<Q',DATA))
        uc.mem_write(qobj,struct.pack('<QQ',DATA+0x1000,7))
        self.run('placement',0x26980,[obj,qobj])
        if len(self.placed) != 4:
            raise ValueError('Wrong capsule placement count')
        placed = {index: matrix for index,(_,matrix) in zip((6,5,3,1),self.placed)}
        if any(not np.allclose(placed[i],fk[i],atol=1e-13,rtol=0) for i in placed):
            raise ValueError('Capsule attachment differs from expected DH index')
        return fk, placed
