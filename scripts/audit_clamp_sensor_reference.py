#!/usr/bin/env python3
"""Offline STL/URDF reference inspection, never a physical mounting approval."""
import argparse
from collections import defaultdict, Counter
import hashlib
import json
import math
from pathlib import Path
import struct
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT/'Cruzr S2-20260803T070710Z-1-003/Cruzr S2/SDK/URDF/cruzr_s2_description.zip'


def boundary_loops(triangles):
    """Connected planar boundary components; rounded in mm, not hole semantics."""
    edges = Counter()
    for tri in triangles:
        vertices = [tuple(round(x*1000, 4) for x in p[:2]) for p in tri]
        for i in range(3):
            edges[tuple(sorted((vertices[i], vertices[(i+1)%3])))]+=1
    graph = defaultdict(set)
    for (a, b), count in edges.items():
        if count == 1:
            graph[a].add(b)
            graph[b].add(a)
    seen, components = set(), []
    for start in graph:
        if start in seen:
            continue
        seen.add(start)
        todo, component = [start], []
        while todo:
            node = todo.pop()
            component.append(node)
            for neighbor in graph[node]-seen:
                seen.add(neighbor)
                todo.append(neighbor)
        low = [min(p[k] for p in component) for k in (0,1)]
        high = [max(p[k] for p in component) for k in (0,1)]
        components.append({'center_mm': [(low[k]+high[k])/2 for k in (0,1)],
                           'size_mm': [high[k]-low[k] for k in (0,1)],
                           'closed': all(len(graph[p]) == 2 for p in component)})
    return components


def rotation_residual(points, degrees):
    if not points:
        raise ValueError('empty_pattern')
    angle = math.radians(degrees)
    rotated = [(math.cos(angle)*x-math.sin(angle)*y,
                math.sin(angle)*x+math.cos(angle)*y) for x,y in points]
    return max(min(math.dist(p,q) for q in points) for p in rotated)


def inspect(path):
    sides = {}
    with zipfile.ZipFile(path) as archive:
        prefix = 'cruzr_s2_description/'
        root = ET.fromstring(archive.read(prefix+'urdf/cruzr_s2_v1/cruzr_s2_v1.urdf'))
        for side in ('L', 'R'):
            link = root.find(f"link[@name='{side}_sixforce_link']")
            origin = link.find('collision/origin')
            mesh = link.find('collision/geometry/mesh')
            if (origin.get('xyz') != '0 0 0' or origin.get('rpy') != '0 0 0'
                    or mesh.get('scale', '1 1 1') != '1 1 1'):
                raise ValueError('unsupported_collision_transform')
            member = mesh.get('filename').removeprefix('package://')
            data = archive.read(member)
            count = struct.unpack_from('<I', data, 80)[0]
            if len(data) != 84+50*count:
                raise ValueError('invalid_binary_STL')
            points, planes, zero_triangles = [], defaultdict(float), []
            for i in range(count):
                tri = [struct.unpack_from('<3f', data, 84+50*i+12+12*j) for j in range(3)]
                points.extend(tri)
                if max(abs(p[2]) for p in tri) < 1e-7:
                    zero_triangles.append(tri)
                if max(p[2] for p in tri)-min(p[2] for p in tri) < 1e-7:
                    a = [tri[1][k]-tri[0][k] for k in range(3)]
                    b = [tri[2][k]-tri[0][k] for k in range(3)]
                    planes[round(tri[0][2]*1000, 3)] += abs(a[0]*b[1]-a[1]*b[0])*500000
            loops = boundary_loops(zero_triangles)
            small = [loop['center_mm'] for loop in loops
                     if loop['closed'] and all(abs(size-4.2) < 0.01 for size in loop['size_mm'])]
            sides[side] = {
                'mesh_member': member,
                'mesh_sha256': hashlib.sha256(data).hexdigest(),
                'mesh_bounds_m': [[fn(p[k] for p in points) for k in range(3)] for fn in (min,max)],
                'largest_constant_z_triangle_area_sums': [
                    {'z_mm': z, 'triangle_area_sum_mm2': area}
                    for z, area in sorted(planes.items(), key=lambda pair: -pair[1])[:8]],
                'physical_mount_plane_identified': False,
                'clamp_clocking_identified': False,
                'z_zero_boundary_components': loops,
                'approx_4p2mm_contour_centers_mm': small,
                'pattern_rotation_residual_mm': {
                    str(angle): rotation_residual(small, angle) for angle in (0, 60, 120, 180, 240)
                } if small else {},
                'pattern_not_registered_to_photo': True,
            }
    return {'status': 'CAD_REFERENCE_CANDIDATE_ONLY',
            'archive_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'sides': sides, 'physical_authorized': False,
            'robot_connections': 0, 'movement_commands': 0,
            'limitations': ['triangle_area_sums_are_not_verified_external_flange_faces',
                            'physical_interface_and_clocking_require_correspondence',
                            'passive_support_mesh_not_identified_in_supplier_URDF']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = inspect(ARCHIVE)
    with args.output.open('x') as output:
        json.dump(result, output, indent=2, allow_nan=False)
        output.write('\n')
    print(result['status'])
    print(args.output)
