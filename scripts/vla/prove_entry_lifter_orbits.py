#!/usr/bin/env python3
"""Try continuous boundary separation of lifter2/torso with orbit bounds."""
import argparse
import json
from pathlib import Path
import time
import numpy as np

from prepare_vla_entry_bundle import ROOT, RobotGeometry, common, digest
from entry_relative_kinematics import RelativeChain
from entry_orbit_bounds import triangle_bounds, prove_boxes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--interfaces', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--max-boxes', type=int, default=31)
    args = parser.parse_args()
    if args.output.exists() or not 1 <= args.max_boxes <= 255:
        parser.error('Choose a new output and 1..255 boxes')
    source = json.loads(args.interfaces.read_text())
    row = next(r for r in source['interfaces'] if r['pair'] == ['lifter_pitch_2_link#0', 'torso_link#0'])
    if row['controlling_joints'] != ['lifter_pitch_3_joint', 'waist_yaw_joint']:
        parser.error('Unexpected axes')
    package = ROOT/'cruzr_s2_description_splint/cruzr_s2_description'
    model = RobotGeometry(package/'urdf/cruzr_s2_v1/cruzr_s2_v1.urdf', package,
                          dict(frame_id='base_link', complete=True, objects=[]))
    if model.manifest != source['model_sources']:
        parser.error('Model changed')
    a, b = [next(s for s in model.shapes if s.name == name) for name in row['pair']]
    chain = RelativeChain(model.joints, a.link, b.link, common.fk)
    if chain.a or [j['name'] for j in chain.b] != ['lifter_pitch_3_joint', 'waist_yaw_joint', 'torso_waist_joint']:
        parser.error('Unexpected relative chain')
    if not np.array_equal(chain.b[0]['axis'], [0, 0, 1]) or chain.b[2]['type'] != 'fixed':
        parser.error('Unexpected rotation axis or fixed joint')
    inv = np.linalg.inv(chain.b[0]['origin'])
    def local(mesh, pose):
        transform = inv@pose
        return mesh.triangles@transform[:3, :3].T+transform[:3, 3]
    tri_a = local(a.source_mesh, np.eye(4)); bounds_a = triangle_bounds(tri_a)
    yaw_origin = chain.b[1]['origin'][:3, 3]
    yaw_axis = chain.b[1]['origin'][:3, :3]@chain.b[1]['axis']
    if abs(np.linalg.norm(yaw_axis)-1) > 1e-10:
        parser.error('Invalid secondary axis')
    lo, hi = np.array(row['domain_lower_rad']), np.array(row['domain_upper_rad'])
    pending = [(float(lo[1]), float(hi[1]))]; rows = []; minimum = float('inf')
    files = [args.interfaces, Path(__file__), Path(__file__).with_name('entry_orbit_bounds.py'),
             Path(__file__).with_name('entry_relative_kinematics.py'), Path(common.__file__), Path(common.fk.__file__),
             *sorted((ROOT/'scripts/teleoperation/general_home').glob('*.py'))]
    hashes = {str(p.resolve()): digest(p) for p in files}; started = time.monotonic()
    while pending and len(rows) < args.max_boxes:
        low, high = pending.pop(); center = (low+high)/2
        tri_b = local(b.source_mesh, chain.evaluate({'waist_yaw_joint': center}))
        def moving_bounds(triangles):
            rel = triangles-yaw_origin
            radial_to_yaw = rel-np.sum(rel*yaw_axis, axis=2)[:, :, None]*yaw_axis
            radius = np.linalg.norm(radial_to_yaw, axis=2).max(1)
            displacement = 2*radius*np.sin(min((high-low)/2, np.pi)/2)
            return triangle_bounds(triangles, (lo[0], hi[0]), displacement)
        bounds_b = moving_bounds(tri_b)
        result = prove_boxes(bounds_a, bounds_b, tri_a, tri_b, refine_b=moving_bounds)
        result.update(yaw_interval_rad=[low, high]); rows.append(result)
        print(json.dumps(result), flush=True)
        if result['proved']:
            minimum = min(minimum, result['lower_bound_m'])
        elif high-low > 1e-10:
            pending.extend([(center, high), (low, center)])
        else:
            pending.append((low, high)); break
    result = dict(scope='CONTINUOUS_SOURCE_TRIANGLE_BOUNDARIES_ONLY', pair=row['pair'],
                  proved=not pending, boxes=rows, pending_boxes=len(pending),
                  full_pitch_interval_rad=[float(lo[0]), float(hi[0])],
                  full_yaw_interval_rad=[float(lo[1]), float(hi[1])],
                  lower_bound_m=minimum if not pending else 0., elapsed_seconds=time.monotonic()-started,
                  volume_separation_proved=False, margin_2mm_proved=False, physical_approval=False,
                  numerical_cushion_m=1e-7, sources_sha256=hashes, model_sources=model.manifest)
    if not model.source_files_unchanged() or any(digest(Path(p)) != h for p, h in hashes.items()):
        raise RuntimeError('Source changed')
    with args.output.open('x') as f:
        json.dump(result, f, indent=2, allow_nan=False); f.write('\n')


if __name__ == '__main__':
    main()
