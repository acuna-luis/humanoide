#!/usr/bin/env python3
"""Prepare only the Control Center command change; no Docker or robot calls."""
import argparse
from pathlib import Path
import yaml

ORIGINAL = 'rosa run control_center control_center -- --tbox-args --config config/base.conf --config config/cc.conf'
GATED = 'python3 /etc/walker/boot/cruzr_cc_start_when_ready.py --start'


def rewrite(text):
    before = yaml.safe_load(text)
    expected = yaml.safe_load(text)
    service = expected['services']['system.control_center']
    if service['command'] == [GATED]:
        return text
    if service['command'] != [ORIGINAL]:
        raise ValueError('Unexpected Control Center command; do not overwrite')
    # Keep every byte outside this exact scalar. Fail if the layout is ambiguous.
    original_line = '      - '+ORIGINAL+'\n'
    if text.count(original_line) != 1:
        raise ValueError('Command line missing or ambiguous')
    result = text.replace(original_line, '      - '+GATED+'\n', 1)
    service['command'] = [GATED]
    if yaml.safe_load(result) != expected or before == expected:
        raise ValueError('Unexpected changes outside the target command')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = rewrite(args.input.read_text())
    with args.output.open('x') as output:
        output.write(result)
