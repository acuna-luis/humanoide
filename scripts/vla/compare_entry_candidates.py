#!/usr/bin/env python3
"""Choose an offline adaptation baseline among reviewed entries; never actuate."""
import argparse
import itertools
import json
from pathlib import Path
import numpy as np

from prepare_vla_entry_bundle import (ROOT, JOINT_ORDER, common, ranking, digest,
    quaternion_rotation, rim_height, validate_first_record)
from evaluate_checkpoint_offline import episode_paths


def select_candidate(rows, target_height):
    if not rows or not np.isfinite(target_height) or target_height <= 0:
        raise ValueError('Candidates and positive target height required')
    if any(not np.isfinite(row['inferred_support_height_m']) for row in rows):
        raise ValueError('Invalid inferred height')
    return min(rows, key=lambda row: (abs(row['inferred_support_height_m']-target_height), row['episode']))['episode']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('alternatives', 'dataset', 'registration', 'camera-info', 'annotations', 'output-dir'):
        p.add_argument('--'+name, type=Path, required=True)
    args = p.parse_args()
    if args.output_dir.exists():
        p.error('Output directory must be new')
    import av
    import pyarrow.parquet as pq
    alternatives = json.loads(args.alternatives.read_text())
    annotations = json.loads(args.annotations.read_text())
    registration = json.loads(args.registration.read_text())
    intrinsic = np.array(json.loads(args.camera_info.read_text())['k']).reshape(3, 3)
    urdf = ROOT/'cruzr_s2_description_splint/cruzr_s2_description/urdf/cruzr_s2_v1/cruzr_s2_v1.urdf'
    joints = ranking.load_joints(urdf)
    measured = dict(zip(registration['joints']['name'], registration['joints']['position'], strict=True))
    camera = np.eye(4)
    camera[:3, :3] = quaternion_rotation(registration['camera_to_base']['quaternion_xyzw'])
    camera[:3, 3] = registration['camera_to_base']['translation']
    mount = np.linalg.inv(common.fk.forward_kinematics(joints, measured)['head_pitch_link'])@camera
    sources = [args.alternatives, args.registration, args.camera_info, args.annotations, urdf, Path(__file__),
               Path(common.__file__), Path(common.fk.__file__), Path(ranking.__file__),
               ROOT/'scripts/vla/prepare_vla_entry_bundle.py', ROOT/'scripts/vla/evaluate_checkpoint_offline.py']
    hashes = {str(path.resolve()):digest(path) for path in sources}
    args.output_dir.mkdir(parents=True)
    rows = []
    for episode, pixels in annotations['rim_pixels_uv'].items():
        route = next(r for r in alternatives['route_reviews'] if r['episode'] == episode)
        for direction in ('access', 'empty_recovery'):
            audit = route[direction]
            if audit['timed_out'] or audit['counts'] != {'CERTIFIED_AFFINE_INTERVALS':1018, 'MODEL_MARGIN_VIOLATION':54}:
                raise ValueError('Candidate lacks the same complete partial-geometry review')
            if any(any(n.startswith('scene:') for n in row['pair']) and row['status'] != 'CERTIFIED_AFFINE_INTERVALS' for row in audit['pairs']):
                raise ValueError('Candidate has an uncertified scene pair')
        archived = next(r for r in alternatives['ranked_upright_endpoints'] if r['episode'] == episode)
        number = int(episode.removeprefix('episode_'))
        parquet, video = episode_paths(args.dataset, number)
        hashes.update({str(path.resolve()):digest(path) for path in (parquet, video)})
        q = validate_first_record(pq.read_table(parquet).slice(0, 1).to_pylist()[0], number, archived['state'])
        if not np.array_equal(q, route['waypoints_20d_rad'][-1]):
            raise ValueError('Route endpoint differs from verified source')
        with av.open(str(video)) as container:
            frame = next(container.decode(video=0))
            if frame.time is None or float(frame.time) != 0:
                raise ValueError('Expected frame zero')
            frame.to_image().save(args.output_dir/f'{episode}.png')
        tilt, poses = ranking.torso_metrics(joints, dict(zip(JOINT_ORDER, q)))
        def height(points):
            return rim_height(poses['head_pitch_link']@mount, intrinsic, points,
                annotations['assumed_box_width_m'], annotations['assumed_box_height_m'], annotations['assumed_floor_below_base_m'])
        variation = annotations['pixel_variation_px']
        if not np.isfinite(variation) or variation < 0:
            raise ValueError('Invalid pixel sensitivity')
        values = [height(np.array(pixels)+np.array(offset).reshape(2, 2))
                  for offset in itertools.product((-variation, variation), repeat=4)]
        rows.append(dict(episode=episode, state_20d_rad=q.tolist(), torso_tilt_deg=tilt,
                         inferred_support_height_m=height(pixels), pixel_only_height_range_m=[min(values), max(values)],
                         wrist_origins_base_m={name:poses[name][:3, 3].tolist() for name in ('L_sixforce_link', 'R_sixforce_link')},
                         nominal_scene_lower_bound_m=archived['minimum_nominal_scene_lower_bound_m'],
                         access_counts=route['access']['counts'], recovery_counts=route['empty_recovery']['counts'],
                         total_height_uncertainty_bounded=False, source_frame_and_state_verified=True))
    pairs = []
    for a, b in itertools.combinations(rows, 2):
        pairs.append(dict(episodes=[a['episode'], b['episode']],
                          maximum_joint_difference_deg=float(np.rad2deg(np.max(np.abs(np.array(a['state_20d_rad'])-b['state_20d_rad'])))),
                          maximum_wrist_origin_difference_m=max(float(np.linalg.norm(np.array(a['wrist_origins_base_m'][name])-b['wrist_origins_base_m'][name])) for name in a['wrist_origins_base_m'])))
    result = dict(schema='cruzr-entry-adaptation-selection-v1', selected_for_adaptation=select_candidate(rows, annotations['target_table_height_m']),
                  target_table_height_m=annotations['target_table_height_m'], candidates=rows, pairwise=pairs,
                  selection_basis='Among these route-reviewed candidates, smallest inferred training-support height difference under shared assumptions',
                  scope='OFFLINE_BASELINE_SELECTION_NOT_PHYSICAL_APPROVAL', physical_approval=False,
                  robot_entry_changed=False, execution_enabled=False, all_dataset_routes_screened=False,
                  limitations=['Rim dimensions, camera mounting and floor offset remain hypotheses.',
                               'Pixel sensitivity is not total metrological uncertainty.',
                               'Different episodes are not necessarily different starting postures.',
                               'Internal-interface, tracking, stopping and current-scene gates remain.'], sources_sha256=hashes)
    if any(digest(Path(path)) != value for path, value in hashes.items()):
        raise RuntimeError('Source changed')
    (args.output_dir/'comparison.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(selected=result['selected_for_adaptation'], pairwise=pairs,
                         heights={r['episode']:r['inferred_support_height_m'] for r in rows}), indent=2))


if __name__ == '__main__':
    main()
