#!/usr/bin/env python3
"""Prepare an offline ENI derivative for the bridge observed on 2026-10-15.

Does not connect to the robot, install files, start controllers or move anything.
Only accepts the inspected vendor profile; preserves all other bytes/checks.
"""
import argparse
import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET

SOURCE_SHA256 = '1b0c9323a7dc1fa627aa4bfddae216374cea2f68157b7a0e8739176f42843d1d'


def prepare(data):
    if hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError('Unrecognized source ENI; inspect the new version first')
    root = ET.fromstring(data)
    slaves = root.findall('.//Config/Slave')
    bridge = [s for s in slaves if s.findtext('Info/PhysAddr') == '18000']
    if len(slaves) != 27 or len(bridge) != 1:
        raise ValueError('Unexpected bus topology')
    # Locate the complete bridge block, without serializing the vendor XML.
    blocks = data.split(b'<Slave>')
    matches = [i for i, b in enumerate(blocks) if b'<PhysAddr>18000</PhysAddr>' in b.split(b'</Slave>')[0]]
    if len(matches) != 1:
        raise ValueError('Ambiguous bridge block')
    i = matches[0]
    block, suffix = blocks[i].split(b'</Slave>', 1)
    old_vendor = b'<VendorId>4294967295</VendorId>'
    old_check = b'<Data>ffffffff</Data>'
    if block.count(old_vendor) != 1 or block.count(old_check) != 1:
        raise ValueError('Unexpected bridge identity checks')
    block = block.replace(old_vendor, b'<VendorId>3758096386</VendorId>')
    block = block.replace(old_check, b'<Data>020000e0</Data>')
    blocks[i] = block + b'</Slave>' + suffix
    result = b'<Slave>'.join(blocks)
    ET.fromstring(result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    result = prepare(args.input.read_bytes())
    with args.output.open('xb') as f:
        f.write(result)
    print('PREPARED_OFFLINE_SHA256=' + hashlib.sha256(result).hexdigest())


if __name__ == '__main__':
    main()
