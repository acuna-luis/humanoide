#!/usr/bin/env python3
"""Render a verified LOCAL wrist/clamp audit as a standalone, offline 3D HTML."""
import argparse
import base64
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

import review_clamp_trajectory_optimization as common
from general_home.union_coverage import convex_mesh


def mesh_data(mesh):
    return {key: base64.b64encode(np.asarray(value,dtype=dtype).tobytes()).decode()
        for key,value,dtype in [('vertices',mesh.vertices,'<f4'),
            ('normals',mesh.vertex_normals,'<f4'),('faces',mesh.faces,'<u4')]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--package-root',type=Path,default=Path(__file__).resolve().parents[2]/'cruzr_s2_description_splint/cruzr_s2_description')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a new output file')
    audit = json.loads(args.audit.read_text())
    if (audit['schema'] != 'cruzr-wrist-clamp-union-audit-v1'
            or audit['status'] != 'LOCAL_RIGID_CAD_COVER_VERIFIED_NOT_DEPLOYED'
            or any(not row['coverage_certificate']['volume_covered'] for row in audit['arms'].values())):
        raise ValueError('Expected a complete local coverage audit')
    sources = dict(audit['source_sha256'])
    sources[str(args.audit.resolve())] = hashlib.sha256(args.audit.read_bytes()).hexdigest()
    template = Path(__file__).with_name('general_home')/'wrist_clamp_review.html'
    for path in (Path(__file__),template):
        sources[str(path.resolve())] = hashlib.sha256(path.read_bytes()).hexdigest()

    def unchanged():
        if any(hashlib.sha256(Path(p).read_bytes()).hexdigest()!=sha for p,sha in sources.items()):
            raise ValueError('Audit source changed; regenerate the audit before rendering')
    unchanged()
    cad_path = args.package_root/'urdf/cruzr_s2_v1/cruzr_s2_v1.urdf'
    mesh_root = args.package_root/'meshes/cruzr_s2_v1'
    # Refuse substitution of an unrecorded CAD package even with matching names.
    for p in [cad_path,*[mesh_root/(s+'_'+part+'_link.STL') for s in ('L','R')
                        for part in ('wrist_roll','sixforce','hand')]]:
        if str(p.resolve()) not in sources:
            raise ValueError('CAD path not present in audit manifest')
    joints = common.model_joints(cad_path)
    sphere = trimesh.creation.icosphere(subdivisions=2,radius=1)
    rows = {}
    for side,row in audit['arms'].items():
        meshes,pose = [],np.eye(4)
        for part in ('wrist_roll','sixforce','hand'):
            if part != 'wrist_roll':
                pose = pose @ next(j['origin'] for j in joints if j['name']==side+'_'+part+'_joint')
            mesh = trimesh.load_mesh(mesh_root/(side+'_'+part+'_link.STL'),process=False)
            mesh.apply_transform(pose)
            meshes.append(mesh)
        cad = trimesh.util.concatenate(meshes)
        primitives = []
        for spec in row['derived_local_cover']:
            points = np.array(spec['endpoints_m'] if spec['kind']=='capsule' else spec['vertices_m'])
            # Display tessellation only. The audit uses analytic distances, not
            # this inscribed approximation of the curved surfaces.
            if spec['name']=='CAD_supplement':
                shape = convex_mesh(points)
            else:
                shape = convex_mesh((points[:,None,:]+sphere.vertices[None,:,:]*spec['radius_m']).reshape(-1,3))
            primitives.append(dict(name=spec['name'],mesh=mesh_data(shape)))
        marker = trimesh.creation.icosphere(subdivisions=2,radius=.003)
        marker.apply_translation(row['native_only']['witness_in_wrist_m'])
        rows[side] = dict(cad=mesh_data(cad),primitives=primitives,marker=mesh_data(marker),
            bounds=cad.bounds.tolist(),excess_mm=row['native_only']['max_vertex_excess_m']*1000,
            witness_mm=(np.array(row['native_only']['witness_in_wrist_m'])*1000).tolist(),
            triangles=row['original_cad_triangles'],certificate=row['coverage_certificate'])
    data = dict(arms=rows,source_sha256=sources,movement_commands=0,physical_approval=False)
    html = template.read_text().replace('__MODEL_DATA__',json.dumps(data,allow_nan=False,separators=(',',':')).replace('<','\\u003c'))
    unchanged()
    with args.output.open('x') as file:
        file.write(html)
    print(json.dumps(dict(output=str(args.output),bytes=args.output.stat().st_size,movement_commands=0,physical_approval=False)))


if __name__ == '__main__':
    main()
