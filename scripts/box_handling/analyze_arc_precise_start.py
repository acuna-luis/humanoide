#!/usr/bin/env python3
"""Offline reproduction of the first ArcPrecise tick in the 2026-09-22 trial.

Reads one pinned local ELF; never loads or executes it. This is an explanatory
calculation for a straight 5 cm goal from rest, not a controller or simulator.
The allow_backward=False result is a hypothesis, not a physical qualification.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

SHA256 = '872b967b4b397ea6f683bacf007b95588ba55d00b0fcb7964a6844bc972b31d3'


def analyze(binary):
    data = binary.read_bytes()
    if hashlib.sha256(data).hexdigest() != SHA256:
        raise ValueError('Unreviewed ArcPrecise binary; offsets and model must be reviewed again')
    # This exact ELF maps the .rodata virtual addresses to identical file offsets.
    constants = {hex(a): struct.unpack_from('<d', data, a)[0]
                 for a in range(0x41378, 0x413e8, 8)}
    bias = constants['0x41398']
    dt = constants['0x413a0']
    distance = .05
    measured_vx = 0.0
    previous_vx = measured_vx - bias  # setStartToGoal, ELF 0x26ed0..0x26ef0
    # preciseControl: initial deceleration is clamped to [0.1, 1.5].
    deceleration = min(1.5, max(.1, previous_vx**2 / (2 * max(.05, distance-.03))))
    # Aligned forward goal: alpha=0; k_r=0.6 for initial odometry 0.
    target_vx = .6 * distance
    candidate_vx = min(target_vx, previous_vx + deceleration * dt)
    minimum_speed = constants['0x413d0']
    backward_allowed = candidate_vx if abs(candidate_vx) >= minimum_speed else 0.0
    forward_only = candidate_vx if candidate_vx >= minimum_speed else 0.0
    if abs(backward_allowed - (-.04)) > 1e-12:
        raise ValueError('Calculation no longer matches the recorded first command')
    return dict(binary_sha256=SHA256, robot_access=False, binary_executed=False,
                scope='First longitudinal tick only; no simulation of plant, obstacles or subsequent motion',
                constants=constants, measured_vx=measured_vx, distance=distance,
                previous_vx=previous_vx, target_vx=target_vx,
                deceleration=deceleration, dt=dt,
                allow_backward_true_first_vx=backward_allowed,
                allow_backward_false_first_vx=forward_only,
                recorded_first_vx=-.04, recorded_command_matches=True,
                physical_forward_only_trial='PENDING')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(analyze(args.binary), indent=2))


if __name__ == '__main__':
    main()
