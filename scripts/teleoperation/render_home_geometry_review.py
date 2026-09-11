#!/usr/bin/env python3
"""Build a standalone 3D model-conflict review. Offline; no control interface."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New HTML file')
    parser.add_argument('--package-root', type=Path, default=Path(__file__).resolve().parents[2]/'cruzr_s2_description_splint/cruzr_s2_description')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output already exists')
    import numpy as np
    from general_home.geometry import RobotGeometry
    from general_home.planner import Validator
    from cruzr_pico_to_home_owner_gate import JOINT_ORDER, PICO_VARIANTS
    import review_clamp_trajectory_optimization as common
    model = RobotGeometry(args.package_root/'urdf/cruzr_s2_v1/cruzr_s2_v1.urdf',
                          args.package_root, dict(frame_id='base_link',complete=True,objects=[]))
    def mesh_data(mesh):
        return dict(vertices=base64.b64encode(np.asarray(mesh.vertices,dtype='<f4').tobytes()).decode(),
                    normals=base64.b64encode(np.asarray(mesh.vertex_normals,dtype='<f4').tobytes()).decode(),
                    faces=base64.b64encode(np.asarray(mesh.faces,dtype='<u4').tobytes()).decode())
    shapes = [dict(name=s.name,link=s.link,source=mesh_data(s.source_mesh),
                   checked=mesh_data(s.mesh) if s.representation != 'closed_mesh' else None,
                   representation=s.representation,error_m=s.geometry_error_m,
                   bounds=s.source_mesh.bounds.tolist()) for s in model.shapes]
    references = {}
    for name,q in dict(HOME=np.zeros(20),**PICO_VARIANTS).items():
        poses = common.fk.forward_kinematics(model.joints,dict(model.auxiliary,**dict(zip(JOINT_ORDER,q))))
        references[name] = dict(poses={key: value.T.ravel().tolist() for key,value in poses.items()},
                               conflicts=Validator(model).failures(q))
    template = Path(__file__).with_name('general_home')/'geometry_review.html'
    source_sha = dict(model.manifest)
    root=Path(__file__).resolve().parents[2]
    for source in [Path(__file__),template,*template.parent.glob('*.py'),
                   Path(__file__).with_name('review_clamp_trajectory_optimization.py'),
                   Path(__file__).with_name('cruzr_pico_to_home_owner_gate.py'),
                   root/'scripts/vla/analyze_vla_fixture_collision_e4_1c.py']:
        source_sha[str(source.resolve())] = hashlib.sha256(source.read_bytes()).hexdigest()
    if not model.source_files_unchanged():
        raise ValueError('Model changed while rendering')
    data = dict(shapes=shapes,references=references,model=model.diagnostics,
                physical_approval=False,movement_commands=0,source_sha256=source_sha)
    encoded = json.dumps(data,allow_nan=False,separators=(',',':')).replace('<','\\u003c')
    html = template.read_text().replace('__MODEL_DATA__',encoded)
    with args.output.open('x') as file:
        file.write(html)
    print(json.dumps(dict(output=str(args.output),bytes=args.output.stat().st_size,
                          physical_approval=False,movement_commands=0)))


if __name__ == '__main__':
    try:
        main()
    except (ValueError,OSError,ImportError) as exc:
        print('ERROR: '+str(exc),file=sys.stderr)
        raise SystemExit(2)
