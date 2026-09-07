#!/usr/bin/env python3
"""Conditional orientation-independent bound; no ROS export or motion gate."""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path

from build_clamp_simplified_model import ROOT, build


def radius_about_origin(bounds):
    if (not isinstance(bounds, list) or len(bounds) != 2
            or any(not isinstance(row, list) or len(row) != 3 for row in bounds)
            or any(type(x) not in (int, float) or not math.isfinite(x)
                   for row in bounds for x in row)
            or any(bounds[0][i] >= bounds[1][i] for i in range(3))):
        raise ValueError('invalid_bounds')
    # Every point of a box has norm <= that of a furthest corner.
    corners = list(itertools.product(*zip(*bounds)))
    witness = max(corners, key=lambda p: math.hypot(*p))
    radius = math.hypot(*witness)
    if not math.isfinite(radius):
        raise ValueError('nonfinite_radius')
    return radius, list(witness)


def audit(contract):
    model = build(contract)
    envelope = model['nominal_full_tool_envelope']
    if envelope is None:
        raise ValueError('nominal_full_envelope_missing')
    radius, witness = radius_about_origin(envelope['bounds_m'])
    return {
        'status': 'CONDITIONAL_ORIENTATION_BOUND_NOT_REGISTERED',
        'nominal_radius_m': radius,
        'furthest_corner_m': witness,
        'nominal_tool_bounds_m': envelope['bounds_m'],
        'proof': 'Euclidean norm is rotation invariant; box maximum attained at a corner',
        'required_assumptions': [
            'reported descriptive axes form an orthonormal metric construction',
            'reported full-tool containment holds',
            'origin is the intersection of reported sensor axis and mounting datum plane'],
        'center_in_L_sixforce_link_m': None,
        'center_in_R_sixforce_link_m': None,
        'center_uncertainty_radius_m': None,
        'tool_measurement_uncertainty_radius_m': None,
        'safe_radius_m': None,
        'inflation_rule': 'nominal radius + bounded center error + bounded tool measurement error; dynamic stopping envelope separate',
        'interpretation': {
            'sphere_disjoint': 'conditional geometric separation only if center, assumptions and errors validated',
            'sphere_overlap': 'inconclusive; does not prove actual clamp collision',
        },
        'trajectories_evaluated': [],
        'physical_authorized': False,
        'robot_connections': 0, 'movement_commands': 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raw = (ROOT/'config/clamp_mount_requalification.json').read_bytes()
    result = audit(json.loads(raw))
    result['contract_sha256'] = hashlib.sha256(raw).hexdigest()
    with args.output.open('x') as out:
        json.dump(result, out, indent=2, allow_nan=False)
        out.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
