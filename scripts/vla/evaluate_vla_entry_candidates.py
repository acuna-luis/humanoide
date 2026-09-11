#!/usr/bin/env python3
"""Compare task-0 entries 40/430/438 on original dataset inputs, offline only.

prepare runs locally. infer requires an isolated CUDA container (--network none),
read-only checkpoint/overlay, and no ROS or robot command transport.
Results cannot authorize motion or replace fresh live shadow qualification.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import time

import evaluate_checkpoint_offline as common

EPISODES = (40, 430, 438)


def prepare(dataset, output):
    output.mkdir(parents=True, exist_ok=False)
    for episode in EPISODES:
        directory = output / f'episode_{episode:06d}'
        directory.mkdir()
        parquet, video = common.episode_paths(dataset, episode)
        manifest = dict(task_id=0, task_text=common.TASKS[0], episode_index=episode,
                        frame_index=0, staged_parquet='episode.parquet', staged_video='episode.mp4',
                        source=dict(parquet_sha256=common.sha256_file(parquet),
                                    video_sha256=common.sha256_file(video)))
        shutil.copy2(parquet, directory / 'episode.parquet')
        shutil.copy2(video, directory / 'episode.mp4')
        common.write_json_exclusive(directory / 'manifest.json', manifest)
    print('PREPARED_ORIGINAL_DATASET_ONLY', flush=True)


def infer(inputs, output, checkpoint, profile_path, overlay):
    for name in ('HF_HUB_OFFLINE', 'TRANSFORMERS_OFFLINE'):
        os.environ[name] = '1'
    output.mkdir(parents=True, exist_ok=False)
    profile = common.load_json(profile_path)
    # Validate every sample/hash/task/frame before loading the expensive model.
    samples = {}
    for episode in EPISODES:
        path = inputs / f'episode_{episode:06d}' / 'manifest.json'
        manifest = common.load_json(path)
        if (manifest['episode_index'], manifest['task_id'], manifest['frame_index']) != (episode, 0, 0):
            raise ValueError('Candidate identity changed')
        samples[episode] = common._extract_table_sample(manifest, path)
    sys.path.insert(0, str(overlay.resolve()))
    import numpy as np
    import torch
    import gr00t
    from gr00t.data.embodiment_tags import EmbodimentTag
    from gr00t.experiment.data_config import Utars_1RGBDataConfig
    from gr00t.model.policy import Gr00tPolicy
    if overlay.resolve() not in Path(gr00t.__file__).resolve().parents:
        raise RuntimeError('Unexpected model library')
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable')
    config = Utars_1RGBDataConfig()
    started = time.monotonic()
    policy = Gr00tPolicy(model_path=str(checkpoint), modality_config=config.modality_config(),
                        modality_transform=config.transform(), embodiment_tag=EmbodimentTag.NEW_EMBODIMENT,
                        denoising_steps=4, device='cuda')
    print('MODEL_LOADED_SECONDS', time.monotonic()-started, flush=True)
    results = []
    indices = [profile['joint_names'].index(n) for n in profile['commanded_joint_names']]
    try:
        for episode, sample in samples.items():
            for seed in range(5):
                torch.manual_seed(seed)
                np.random.seed(seed)
                action = common._flatten_prediction(policy.get_action(common._policy_sample(sample, common.TASKS[0])))
                metrics = common._metrics(action, sample['ground_truth'], sample['state20'], profile)
                delta = np.abs(np.asarray(action[0])-sample['state20'])
                worst = max(indices, key=lambda i: delta[i])
                result = dict(episode=episode, seed=seed, original_state20=sample['state20'],
                              predicted_action_10x20=action, metrics=metrics,
                              max_arm_first_delta_rad=float(delta[worst]),
                              max_arm_first_delta_joint=profile['joint_names'][worst],
                              first_arm_delta_pass=all(delta[i] <= profile['max_first_point_delta'][i] for i in indices),
                              physical_approval=False)
                common.write_json_exclusive(output / f'episode_{episode:06d}_seed{seed}.json', result)
                results.append(result)
                print(json.dumps({k:result[k] for k in ('episode','seed','max_arm_first_delta_rad','first_arm_delta_pass')}), flush=True)
    finally:
        del policy
        torch.cuda.empty_cache()
    common.write_json_exclusive(output/'summary.json', dict(
        scope='ORIGINAL_DATASET_ONLY_NOT_LIVE_SHADOW_OR_EXECUTION', physical_approval=False,
        checkpoint_config_sha256=common.sha256_file(checkpoint/'config.json'),
        profile_sha256=common.sha256_file(profile_path),
        episodes={str(e):dict(first_arm_delta_passes=sum(r['first_arm_delta_pass'] for r in results if r['episode']==e),
                             repetitions=5, worst_first_arm_delta_rad=max(r['max_arm_first_delta_rad'] for r in results if r['episode']==e))
                  for e in EPISODES}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare','infer'))
    parser.add_argument('--dataset', type=Path)
    parser.add_argument('--input-dir', type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--checkpoint', type=Path)
    parser.add_argument('--profile', type=Path)
    parser.add_argument('--override-parent', type=Path)
    args = parser.parse_args()
    if args.mode == 'prepare':
        if not args.dataset: parser.error('--dataset required')
        prepare(args.dataset, args.output_dir)
    else:
        if any(x is None for x in (args.input_dir,args.checkpoint,args.profile,args.override_parent)):
            parser.error('infer requires input-dir, checkpoint, profile and override-parent')
        infer(args.input_dir,args.output_dir,args.checkpoint,args.profile,args.override_parent)


if __name__ == '__main__':
    main()
