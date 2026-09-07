#!/usr/bin/env python3
"""Offline CAD asymmetry witness; NOT a photo registration or collision gate."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import zipfile

from audit_clamp_sensor_reference import ARCHIVE, inspect


def bounds_witness(points, degrees):
    """Rotated vertex outside original AABB proves non-symmetry, not clearance.

    Zero does NOT prove symmetry. Positive is a lower bound on distance to
    the original mesh, since that mesh is contained by its vertex AABB.
    """
    if not points or not math.isfinite(degrees):
        raise ValueError('empty_points_or_invalid_angle')
    if any(len(p) != 3 or any(not math.isfinite(v) for v in p) for p in points):
        raise ValueError('invalid_points')
    low = [min(p[k] for p in points) for k in range(3)]
    high = [max(p[k] for p in points) for k in range(3)]
    a = math.radians(degrees)
    candidates = []
    for p in points:
        q = [math.cos(a)*p[0]-math.sin(a)*p[1],
             math.sin(a)*p[0]+math.cos(a)*p[1], p[2]]
        excess = max(max(low[k]-q[k], q[k]-high[k], 0) for k in range(3))
        candidates.append((excess, p, q))
    excess, p, q = max(candidates, key=lambda c: c[0])
    return dict(degrees=degrees, original_bounds_mm=[low, high],
                outside_bound_mm=excess, original_vertex_mm=p, rotated_vertex_mm=q,
                non_symmetry_witness=excess > 0.001,
                zero_is_not_proof_of_symmetry=True)


def audit():
    reference = inspect(ARCHIVE)
    sides = {}
    with zipfile.ZipFile(ARCHIVE) as archive:
        for side, spec in reference['sides'].items():
            data = archive.read(spec['mesh_member'])
            count = struct.unpack_from('<I', data, 80)[0]
            points, plane_points = set(), set()
            for i in range(count):
                tri = [struct.unpack_from('<3f', data, 84+50*i+12+12*j) for j in range(3)]
                points.update(tuple(v*1000 for v in p) for p in tri)
                if all(abs(p[2]) < 1e-7 for p in tri):
                    plane_points.update(tuple(v*1000 for v in p) for p in tri)
            sides[side] = dict(mesh_sha256=hashlib.sha256(data).hexdigest(),
                full_mesh=[bounds_witness(sorted(points), a) for a in (0,120,240)],
                z_zero_triangles=[bounds_witness(sorted(plane_points), a) for a in (0,120,240)])
    return dict(status='CAD_ASYMMETRY_ONLY_PHOTO_REGISTRATION_UNRESOLVED',
                archive_sha256=reference['archive_sha256'], sides=sides,
                physical_authorized=False, robot_connections=0, movement_commands=0,
                limitations=['CAD_only_no_photo_feature_matching',
                             'CAD_visibility_and_physical_part_identity_unproven',
                             'no_clamp_transform_support_envelope_or_path_qualification'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit()
    with args.output.open('x') as out:
        json.dump(result, out, indent=2, allow_nan=False)
        out.write('\n')
    print(result['status'])
    for side, r in result['sides'].items():
        print(side, {key: [round(v['outside_bound_mm'],6) for v in r[key]]
                     for key in ('full_mesh','z_zero_triangles')})
