#!/usr/bin/env python3
"""Prepare the vendor SPS environment offline, preserving all other bytes.

Does not deploy, recreate containers or control the robot. Inputs may contain
private settings; keep the output directory outside Git.
"""
import argparse
import copy
import json
from pathlib import Path
import re

import yaml


def prepare(compose, database):
    before = yaml.safe_load(compose)
    db = json.loads(database)
    if db.get('envs', {}).get('HW_TYPE') != 'cruzr_s2_v1':
        raise ValueError('Expected the inspected clamp HW_TYPE in uDoke')
    after_compose, count = re.subn(
        rb'(?m)^(\s*-\s+HW_TYPE=)cruzr_s2_v1(\r?\n|$)',
        rb'\1cruzr_s2_v1_sps\2', compose)
    if count != 1:
        raise ValueError('Expected exactly one shared HW_TYPE in compose')
    after_db, count = re.subn(
        rb'("HW_TYPE"\s*:\s*")cruzr_s2_v1(")',
        rb'\1cruzr_s2_v1_sps\2', database)
    if count != 1:
        raise ValueError('Expected exactly one HW_TYPE in uDoke database')
    expected = copy.deepcopy(before)
    env = expected['services']['motion.mc_common']['environment']
    if env.count('HW_TYPE=cruzr_s2_v1') != 1:
        raise ValueError('Unexpected shared environment structure')
    env[env.index('HW_TYPE=cruzr_s2_v1')] = 'HW_TYPE=cruzr_s2_v1_sps'
    if yaml.safe_load(after_compose) != expected:
        raise ValueError('Compose contains unexpected changes')
    expected_db = copy.deepcopy(db)
    expected_db['envs']['HW_TYPE'] = 'cruzr_s2_v1_sps'
    if json.loads(after_db) != expected_db:
        raise ValueError('uDoke database contains unexpected changes')
    return after_compose, after_db


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--compose', required=True, type=Path)
    p.add_argument('--database', required=True, type=Path)
    p.add_argument('--output-directory', required=True, type=Path)
    args = p.parse_args()
    compose, database = prepare(args.compose.read_bytes(), args.database.read_bytes())
    args.output_directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    (args.output_directory / 'compose.yml').write_bytes(compose)
    (args.output_directory / 'db.json').write_bytes(database)
    print('PREPARED_OFFLINE=HW_TYPE:cruzr_s2_v1_sps; deployment_required')


if __name__ == '__main__':
    main()
