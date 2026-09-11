#!/usr/bin/env python3
"""Extract archived S2 defaults and compare the isolated clamp with supplied CAD.

No network, publishers, robot installation, runtime library loading or movement.
This audit cannot approve a trajectory or replace the complete collision model.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import numpy as np
import trimesh

from general_home.native_geometry import InitializerArguments, BUILDS
import review_clamp_trajectory_optimization as common

MATH_SHA = '6381100d2f4b66d262145d508594d0280a616b640d4e6c8c960416e25e678803'


def vertex_coverage(vertices, points, radius):
    """Test a convex point hull dilated by a ball; no tolerance inflation."""
    vertices, points = np.asarray(vertices, dtype=float), np.asarray(points, dtype=float)
    if (vertices.ndim != 2 or vertices.shape[1] != 3 or not len(vertices)
            or points.ndim != 2 or points.shape[1] != 3 or len(points) < 4
            or not np.isfinite(vertices).all() or not np.isfinite(points).all()
            or not np.isfinite(radius) or radius <= 0):
        raise ValueError('Invalid geometry for coverage audit')
    hull = trimesh.convex.convex_hull(points)
    inside = hull.contains(vertices)
    _, distance, _ = trimesh.proximity.closest_point(hull, vertices)
    distance[inside] = 0
    if not np.isfinite(distance).all():
        raise ValueError('Invalid proximity result')
    excess = distance-radius
    index = int(np.argmax(excess))
    return dict(unique_vertices=len(vertices), outside_vertices=int((excess > 1e-8).sum()),
        maximum_vertex_excess_m=max(0., float(excess[index])),
        witness_vertex_in_native_tool_m=vertices[index].tolist(),
        all_vertices_contained=bool((excess <= 1e-8).all()),
        numerical_comparison_epsilon_m=1e-8)


def clamp_coverage(records, frame_root, package_root):
    native_path = frame_root/'opt/walker/manipulation_platforms/share/manipulation_platforms/config/urdf/cruzr_s2.urdf'
    cad_path = package_root/'urdf/cruzr_s2_v1/cruzr_s2_v1.urdf'
    native, cad = [common.model_joints(p) for p in (native_path, cad_path)]
    tree = ET.parse(cad_path).getroot()
    sources = [native_path, cad_path]
    result = {}
    by_offset = {int(r['object_offset'], 16): r for r in records}
    for side, offset in (('L', 0x39c80), ('R', 0x39b40)):
        record = by_offset[offset]
        if record['type_enum'] != 5 or record['name'] != 'S2Clamp':
            raise ValueError('Unexpected clamp constructor')
        if record['transform_raw_12'] != [1,0,0,0,1,0,0,0,1,0,0,0]:
            raise ValueError('Clamp default transform changed')
        transforms = []
        for model in (native, cad):
            transform = np.eye(4)
            for name in (side+'_sixforce_joint', side+'_hand_joint'):
                joint = next(j for j in model if j['name'] == name)
                if joint['type'] != 'fixed':
                    raise ValueError('Tool registration is not fixed')
                transform = transform @ joint['origin']
            transforms.append(transform)
        bridge = np.linalg.inv(transforms[0]) @ transforms[1]
        link = next(l for l in tree.findall('link') if l.get('name') == side+'_hand_link')
        collisions = link.findall('collision')
        if len(collisions) != 1:
            raise ValueError('Expected one complete clamp CAD mesh')
        collision = collisions[0]
        origin, mesh_xml = collision.find('origin'), collision.find('geometry/mesh')
        if (origin is None or origin.get('xyz') != '0 0 0' or origin.get('rpy') != '0 0 0'
                or mesh_xml is None or mesh_xml.get('scale', '1 1 1') != '1 1 1'):
            raise ValueError('Unreviewed collision origin/scale')
        expected = 'package://cruzr_s2_description/meshes/cruzr_s2_v1/'+side+'_hand_link.STL'
        if mesh_xml.get('filename') != expected:
            raise ValueError('Unexpected clamp CAD path')
        mesh_path = package_root/expected.split('package://cruzr_s2_description/', 1)[1]
        sources.append(mesh_path)
        mesh = trimesh.load_mesh(mesh_path, process=False)
        vertices = np.unique(mesh.vertices, axis=0) @ bridge[:3, :3].T + bridge[:3, 3]
        row = vertex_coverage(vertices, record['points'], record['scalar_arguments'][0])
        result[side] = dict(row, cad_tool_to_native_tool=bridge.tolist(),
            registration='archived fixed URDF wrist-to-tool chain; physical registration unverified',
            native_primitive_attachment='assumed native hand/tool frame; active attachment unverified',
            scope='isolated S2Clamp default only; neighbouring wrist shapes excluded',
            full_runtime_union_coverage_verified=False,
            radius_m=record['scalar_arguments'][0], points_m=record['points'])
    return result, sources


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--geometry-root', type=Path, required=True, help='Private local archive containing opt/walker')
    parser.add_argument('--frames-root', type=Path, required=True, help='Local archive containing native URDF')
    parser.add_argument('--package-root', type=Path, default=Path(__file__).resolve().parents[2]/'cruzr_s2_description_splint/cruzr_s2_description')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or any(p.resolve() == Path('/') for p in (args.geometry_root, args.frames_root)):
        parser.error('Use local archives and a new output file')
    paths = [args.geometry_root/'opt/walker/manipulation_kinematics/lib'/f'libs2_{part}_kinematics.so'
        for part in BUILDS]
    math_path = args.geometry_root/'opt/walker/manipulation_common/lib/libgeometric_primitive_set.so'
    hash_file = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    if hash_file(math_path) != MATH_SHA:
        raise ValueError('Unreviewed primitive support-function library')
    # Include files before reading data, then reject a change during the audit.
    cad_path = args.package_root/'urdf/cruzr_s2_v1/cruzr_s2_v1.urdf'
    native_path = args.frames_root/'opt/walker/manipulation_platforms/share/manipulation_platforms/config/urdf/cruzr_s2.urdf'
    all_paths = paths+[math_path, cad_path, native_path, Path(__file__),
        Path(sys.modules[InitializerArguments.__module__].__file__), Path(common.__file__), Path(common.fk.__file__)]
    all_paths += [args.package_root/'meshes/cruzr_s2_v1'/f'{side}_hand_link.STL' for side in ('L', 'R')]
    hashes = {str(p.resolve()): hash_file(p) for p in all_paths}
    extracted = {part: InitializerArguments(p, part).extract() for part, p in zip(BUILDS, paths)}
    coverage, _ = clamp_coverage(extracted['arm']['all_constructor_calls'], args.frames_root, args.package_root)
    # The repeated S2 clamp header constants must agree across the three builds.
    signatures = []
    for part, data in extracted.items():
        rows = [{k:v for k,v in x.items() if k != 'object_offset'}
            for x in data['all_constructor_calls'] if x.get('name') == 'S2Clamp']
        if len(rows) != 2:
            raise ValueError('Expected left/right clamp defaults in '+part)
        signatures.append(rows)
    if any(s != signatures[0] for s in signatures):
        raise ValueError('Conflicting compiled clamp defaults')
    if any(hash_file(Path(p)) != sha for p, sha in hashes.items()):
        raise ValueError('Source changed during audit')
    result = dict(schema='cruzr-native-collision-defaults-audit-v1',
        status='OFFLINE_DEFAULTS_EXTRACTED_GENERAL_HOME_NOT_QUALIFIED',
        extraction=extracted, isolated_clamp_cad_comparison=coverage,
        semantics_review=dict(library_sha256=MATH_SHA, support_function_offset='0x96c0',
            type_2='ellipsoid; vector stores semiaxes', type_3='segment capsule; scalar stores radius',
            type_5='convex hull of points plus ball; scalar stores radius',
            evidence='static disassembly of constructor and unit-direction support function'),
        limitations=['compiled defaults are not a live selected collision model',
            'libs2_leg is a six-joint leg, not this robot\'s cruzr_s2_lifter',
            'isolation counterexample does not prove missing coverage in the full wrist+clamp union',
            'attachment and calibrated FK require separate verification',
            'no collision pairs, physical margins or operational profiles were changed'],
        source_sha256=hashes, cross_library_clamp_constants_agree=True,
        movement_commands=0, remote_changes=0, physical_approval=False, installable=False)
    with args.output.open('x') as file:
        json.dump(result, file, indent=2, allow_nan=False)
        file.write('\n')
    print(json.dumps(dict(output=str(args.output), status=result['status'],
        isolated_clamp_excess_mm={s: r['maximum_vertex_excess_m']*1000 for s,r in coverage.items()},
        physical_approval=False)))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, StopIteration) as exc:
        print('ERROR: '+str(exc), file=sys.stderr)
        raise SystemExit(2)
