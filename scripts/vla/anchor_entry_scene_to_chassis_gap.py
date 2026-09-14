#!/usr/bin/env python3
"""Translate an offline RGB scene hypothesis to a reported chassis/table gap."""
import argparse
import copy
import json
from pathlib import Path
import numpy as np
import trimesh
import xml.etree.ElementTree as ET
from scipy.spatial.transform import Rotation
from prepare_vla_entry_bundle import digest


def front_edge_x_at_centreline(table):
    point = np.asarray(table['front_top_midpoint_base_m'], float)
    direction = Rotation.from_rotvec(table['rotation_vector_rad']).apply([0., 1., 0.])
    if abs(direction[1]) < .5:
        raise ValueError('Front edge insufficiently transverse to robot')
    offset = -point[1]/direction[1]
    if abs(offset) > table['size_m'][1]/2:
        raise ValueError('Robot centreline does not cross front edge')
    return float(point[0]+offset*direction[0])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('fit', 'measurement', 'urdf', 'chassis-mesh', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): parser.error('Choose new output')
    sources = [args.fit, args.measurement, args.urdf, args.chassis_mesh, Path(__file__)]
    hashes = {str(p.resolve()): digest(p) for p in sources}
    measurement = json.loads(args.measurement.read_text())
    gap = measurement['chassis_tip_to_table_projection_m']
    if type(gap) not in (int, float) or not np.isfinite(gap) or gap <= 0:
        parser.error('Positive finite measured gap required')
    root = ET.parse(args.urdf).getroot(); collisions = root.findall("link[@name='base_link']/collision")
    if len(collisions) != 1: parser.error('Expected single chassis collision')
    collision = collisions[0]; origin = collision.find('origin'); mesh = collision.find('geometry/mesh')
    if mesh is None or Path(mesh.get('filename')).name != args.chassis_mesh.name:
        parser.error('Wrong chassis mesh')
    if origin is not None and any(float(v) != 0 for k in ('xyz', 'rpy') for v in origin.get(k, '0 0 0').split()):
        parser.error('Nonzero chassis collision origin not supported')
    if mesh.get('scale', '1 1 1').split() != ['1', '1', '1']: parser.error('Non-unit mesh scale')
    vertices = trimesh.load(args.chassis_mesh, force='mesh').vertices
    tip = float(vertices[:, 0].max())
    result = copy.deepcopy(json.loads(args.fit.read_text()))
    table = next(row for row in result['objects'] if row['id'] == 'tabletop_fit')
    before = front_edge_x_at_centreline(table); target = tip+gap; delta = target-before
    for row in result['objects']:
        row['front_top_midpoint_base_m'][0] += delta
        row['scene_object']['center_m'][0] += delta
        for bound in row['bounds_base_m']: bound[0] += delta
        # The translated estimate is no longer the original pixel fit.
        row['original_rgb_fit_diagnostics'] = {k: row.pop(k) for k in ('corner_residuals_px', 'reprojected_corners_uv', 'pixel_only_sensitivity_poses') if k in row}
        row['physical_approval'] = False
    result.update(scope='MEASURED_GAP_ANCHORED_SCENE_HYPOTHESIS', physical_approval=False,
                  registration_qualified=False, scene_complete=False, total_uncertainty_bounded=False,
                  anchor=dict(chassis_model_tip_x_m=tip, reported_gap_m=gap,
                              original_table_edge_x_at_robot_centreline_m=before,
                              anchored_table_edge_x_at_robot_centreline_m=target, translation_x_m=delta,
                              interpretation='Gap measured along robot +X at y=0 to front tabletop edge projection',
                              tip_correspondence_and_measurement_error_verified=False,
                              preserves_camera_orientation_lateral_position_and_relative_box_pose=True),
                  sources_sha256=hashes)
    if any(digest(Path(p)) != h for p, h in hashes.items()): raise RuntimeError('Sources changed')
    with args.output.open('x') as f: json.dump(result, f, indent=2, allow_nan=False); f.write('\n')
    print(json.dumps(result['anchor']))


if __name__ == '__main__': main()
