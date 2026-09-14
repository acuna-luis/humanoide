#!/usr/bin/env python3
"""Offline disassembly of the pinned vendor E-stop publication path; never runs it."""
import argparse
import hashlib
import json
from pathlib import Path

EXPECTED_SHA256 = '13cea0b9e84e10506a31e1c1e9a9015774984fafcb3fbc0ef40e6ab08f7e1a6d'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if hashlib.sha256(args.binary.read_bytes()).hexdigest() != EXPECTED_SHA256:
        raise ValueError('Unreviewed binary; addresses and interpretation do not apply')
    from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
    from elftools.elf.elffile import ELFFile
    with args.binary.open('rb') as stream:
        elf = ELFFile(stream)
        section = elf.get_section_by_name('.text')
        start, end = 0x35100, 0x35f1c
        code = section.data()[start-section['sh_addr']:end-section['sh_addr']]
        asm = {hex(i.address): i.mnemonic+' '+i.op_str for i in Cs(CS_ARCH_ARM64, CS_MODE_ARM).disasm(code, start)}
    report = dict(schema='cruzr-estop-publication-static-review-v1', binary_sha256=EXPECTED_SHA256,
        process_power_disassembly=asm,
        interpretation='Frame 0x5b: each key change publishes; unchanged keys are suppressed unless shared counter is zero. Counter increments through 10, then resets.',
        publisher_member_offsets={'estop_key_pub_':416, 'estop_servo_pub_':432},
        dwarf_offsets_evidence_required=True,
        physical_event_latency_measured=False, maximum_silent_interval_proven=False,
        stop_distance_qualified=False, motion_authorized=False)
    with args.output.open('x') as output:
        json.dump(report, output, indent=2)
        output.write('\n')


if __name__ == '__main__':
    main()
