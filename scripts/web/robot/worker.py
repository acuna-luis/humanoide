#!/usr/bin/env python3
"""Fixed resident actions. Invoked by the robot job service, never by shell input."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'scripts/box_handling'))
sys.path.insert(0, str(ROOT/'scripts/lib'))
import scenario1_cli as cli
import scenario1_contract as contract


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--action', choices=('home', 'cycle'), required=True)
    p.add_argument('--height', choices=('74', '90'), default='74')
    p.add_argument('--evidence', type=Path, required=True)
    p.add_argument('--run', action='store_true')
    p.add_argument('--physical-confirmed', action='store_true')
    p.add_argument('--height-trial-authorized', action='store_true')
    args = p.parse_args()
    if args.run and (not args.physical_confirmed or (args.action == 'cycle' and not args.height_trial_authorized)):
        p.error('Fresh physical declaration and explicit cycle trial authority required')
    os.environ['CRUZR_SCENARIO1_LOCAL'] = '1'
    if args.action == 'cycle':
        return cli.main(['--table-height-cm', args.height, '--box-alignment-attempts', '7',
            '--voice', 'off', '--evidence-dir', str(args.evidence),
            *(['--run', '--height-deposit-trial'] if args.run else ['--check'])],
            policy='assume', execution_profile='optimistic_v1')
    args.evidence.mkdir(parents=True, exist_ok=False, mode=0o700)
    profile = json.loads((ROOT/'scripts/box_handling/scenario1_current_geometry.json').read_text())
    checkpoint = contract.new_checkpoint(profile, policy='assume', execution_profile='optimistic_v1')
    payload = cli.make_payload('run' if args.run else 'check', profile, checkpoint)
    payload.update(policy='assume', execution_profile='optimistic_v1', home_only=True,
                   box_alignment_attempts=0, voice='off')
    payload['modules'].append(('scenario1_robot_home', (ROOT/'scripts/box_handling/scenario1_robot_home.py').read_text()))
    with open('/tmp/cruzr-improved-scenario1.lock', 'a') as lock, open('/tmp/cruzr_blue_workbin_cycle.lock', 'a') as legacy:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(legacy, fcntl.LOCK_EX | fcntl.LOCK_NB)
        connection = cli.Connection(payload, False, args.evidence)
        try:
            connection.wait('ready')
            if args.run:
                connection.send({'command': 'arm'})
                connection.wait('home_complete', timeout=100)
            return connection.process.wait(timeout=15)
        finally:
            connection.close()


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError) as error:
        print('ROBOT_JOB_FAILED: '+str(error), flush=True)
        raise SystemExit(78)
