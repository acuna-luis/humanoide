#!/usr/bin/env python3
"""Run ONLY an isolated, unqualified SmolVLA offline training experiment.

Inputs must be mounted read-only; output is a new directory. No robot, ROS,
network or Hub publishing is configured. This script must run inside the
network-isolated container created by run_offline.sh, not on a robot host.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import time


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def model_files(root):
    """Hash local model inputs, refusing symlinks escaping the mounted tree."""
    result = {}
    for p in sorted(root.rglob('*')):
        if '.cache' in p.relative_to(root).parts or not p.is_file():
            continue
        if root not in p.resolve(strict=True).parents:
            raise ValueError(f'Model file escapes its input tree: {p}')
        result[str(p.relative_to(root))] = sha256(p)
    if not result:
        raise ValueError('Empty local model tree')
    return result


def verify_dataset(root):
    root = root.resolve(strict=True)
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    if (manifest.get('schema') != 'cruzr_ball_lerobot_offline_experiment_v1'
            or manifest.get('offline_experiment_only') is not True
            or manifest.get('training_ready') is not False
            or manifest.get('physical_control_qualified') is not False
            or manifest.get('not_authorized_for_hub_upload_or_robot_execution') is not True
            or manifest.get('fps') != 2):
        raise ValueError('Dataset is not the expected unqualified offline ball experiment')
    segments = manifest.get('segments')
    if not isinstance(segments, list) or not segments or any(
            s.get('status') != 'candidate_success' or s.get('split') != 'inspection_train'
            for s in segments):
        raise ValueError('Dataset contains unexpected training segments')
    files = manifest.get('output_sha256')
    if not isinstance(files, dict) or not files:
        raise ValueError('Dataset lacks an output integrity manifest')
    for name, expected in files.items():
        if not isinstance(name, str) or not isinstance(expected, str):
            raise ValueError('Malformed integrity record')
        p = (root / name).resolve(strict=True)
        if root not in p.parents or not p.is_file() or sha256(p) != expected:
            raise ValueError(f'Dataset checksum or path failed: {name}')
    info = json.loads((root / 'lerobot_dataset/meta/info.json').read_text(encoding='utf-8'))
    f = info.get('features', {})
    if (info.get('fps') != 2 or info.get('total_episodes') != len(segments)
            or f.get('observation.state', {}).get('shape') != [27]
            or f.get('action', {}).get('shape') != [8]
            or f.get('observation.images.camera1', {}).get('shape') != [3, 576, 960]
            or f.get('action', {}).get('names') != manifest.get('action_names')
            or f.get('observation.state', {}).get('names') != manifest.get('state_names')):
        raise ValueError('LeRobot schema, dimensions or feature names do not match the manifest')
    return manifest


def with_local_tokenizer(original, tokenizer_path):
    """Preserve the base processor while resolving its tokenizer locally."""
    def wrapped(*args, **kwargs):
        overrides = dict(kwargs.get('preprocessor_overrides') or {})
        if 'tokenizer_processor' in overrides:
            raise ValueError('Unexpected pre-existing tokenizer override')
        overrides['tokenizer_processor'] = {'tokenizer_name': str(tokenizer_path)}
        kwargs['preprocessor_overrides'] = overrides
        return original(*args, **kwargs)
    return wrapped


def train(args):
    if not args.offline_experiment:
        raise ValueError('Pass --offline-experiment to acknowledge unqualified labels')
    if not 1 <= args.steps <= 20000 or not 1 <= args.batch_size <= 64 or not 1 <= args.chunk_size <= 8:
        raise ValueError('Allowed ranges: steps 1..20000, batch size 1..64, chunk size 1..8')
    for key in ('HF_HUB_OFFLINE', 'TRANSFORMERS_OFFLINE', 'HF_HUB_DISABLE_TELEMETRY'):
        if os.environ.get(key) != '1':
            raise ValueError(f'{key}=1 is required')
    if importlib.metadata.version('lerobot') != '0.5.1':
        raise ValueError('LeRobot 0.5.1 is required')
    dataset, model, vlm, output = (Path(x).resolve(strict=True) for x in
                                    (args.dataset, args.model, args.vlm, args.output))
    if any(not p.is_dir() for p in (dataset, model, vlm, output)):
        raise ValueError('All inputs and the empty output mount must be directories')
    if list(output.iterdir()):
        raise ValueError('Output directory must be empty')
    for p in (dataset, model, vlm):
        if p == output or p in output.parents or output in p.parents:
            raise ValueError('Output and input directories must not overlap')
    manifest = verify_dataset(dataset)
    required_model = ['config.json', 'model.safetensors', 'policy_preprocessor.json',
                      'policy_postprocessor.json']
    if any(not (model / p).is_file() for p in required_model):
        raise ValueError('Local SmolVLA base is incomplete')
    if not (vlm / 'config.json').is_file():
        raise ValueError('Local SmolVLM configuration is missing')
    model_hashes, vlm_hashes = model_files(model), model_files(vlm)

    import torch
    from lerobot.configs.default import DatasetConfig
    from lerobot.configs.policies import PreTrainedConfig
    from lerobot.configs.train import TrainPipelineConfig
    from lerobot.configs.types import FeatureType, PolicyFeature
    from lerobot.policies.smolvla.configuration_smolvla import SmolVLAConfig
    import lerobot.scripts.lerobot_train as trainer

    if not torch.cuda.is_available():
        raise ValueError('CUDA is unavailable inside isolated container')
    free_bytes, total_bytes = torch.cuda.mem_get_info(0)
    if free_bytes < 12 * 1024**3:
        raise ValueError('Less than 12 GiB VRAM free; shared services preserved')
    torch.cuda.set_per_process_memory_fraction(0.70, 0)
    torch.set_num_threads(4)
    policy = PreTrainedConfig.from_pretrained(model, local_files_only=True)
    if not isinstance(policy, SmolVLAConfig):
        raise ValueError('The local base is not SmolVLA')
    policy.pretrained_path = model
    policy.device = 'cuda'
    policy.push_to_hub = False
    policy.repo_id = None
    policy.input_features = {
        'observation.state': PolicyFeature(type=FeatureType.STATE, shape=(27,)),
        'observation.images.camera1': PolicyFeature(type=FeatureType.VISUAL, shape=(3, 576, 960)),
    }
    policy.output_features = {'action': PolicyFeature(type=FeatureType.ACTION, shape=(8,))}
    policy.vlm_model_name = str(vlm)
    policy.chunk_size = args.chunk_size
    policy.n_action_steps = args.chunk_size
    policy.scheduler_warmup_steps = min(100, max(1, args.steps // 10))
    policy.scheduler_decay_steps = args.steps
    cfg = TrainPipelineConfig(dataset=DatasetConfig(repo_id='local/cruzr-ball-offline-experiment',
        root=str(dataset / 'lerobot_dataset')), policy=policy, output_dir=output / 'run',
        job_name='cruzr-ball-offline-experiment', steps=args.steps, batch_size=args.batch_size,
        num_workers=2, eval_freq=args.steps + 1, log_freq=max(1, min(10, args.steps)),
        save_freq=args.steps, save_checkpoint=True)
    if cfg.env is not None or cfg.wandb.enable or policy.push_to_hub:
        raise ValueError('Environment, remote logging or Hub publishing must stay disabled')
    # The v0.5.1 trainer loads pretrained processors and normally leaves their
    # tokenizer Hub ID unchanged. Inject only a local tokenizer path; its
    # existing overrides still provide this dataset's actual 27/8 statistics.
    trainer.make_pre_post_processors = with_local_tokenizer(trainer.make_pre_post_processors, vlm)
    meta = {'schema': 'cruzr_ball_smolvla_training_run_v1', 'offline_experiment_only': True,
            'physical_control_qualified': False, 'training_ready': False,
            'dataset_manifest_sha256': sha256(dataset / 'manifest.json'),
            'dataset_segments': manifest['segments'], 'model_sha256': model_hashes,
            'vlm_sha256': vlm_hashes, 'lerobot_version': '0.5.1',
            'torch_version': torch.__version__, 'cuda_runtime': torch.version.cuda,
            'gpu': torch.cuda.get_device_name(0), 'gpu_total_bytes': total_bytes,
            'gpu_free_before_bytes': free_bytes, 'gpu_memory_fraction_limit': 0.70,
            'steps': args.steps, 'batch_size': args.batch_size, 'chunk_size': args.chunk_size,
            'fps': 2, 'scheduler_warmup_steps': policy.scheduler_warmup_steps,
            'scheduler_decay_steps': policy.scheduler_decay_steps,
            'limits': ['unqualified hypothetical labels; not for physical execution',
                'no independent successful validation set', 'HOME and 20 cm not demonstrated',
                'source clocks, applied actions and hand command semantics remain unqualified'],
            'started_unix_ns': time.time_ns()}
    (output / 'run_manifest.json').write_text(json.dumps(meta, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    started = time.monotonic()
    trainer.train(cfg)
    result = {'completed': True, 'elapsed_seconds': time.monotonic() - started,
              'physical_control_qualified': False, 'training_ready': False}
    (output / 'completed.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result), flush=True)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset', required=True)
    p.add_argument('--model', required=True)
    p.add_argument('--vlm', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--steps', type=int, default=100)
    p.add_argument('--batch-size', type=int, default=4)
    p.add_argument('--chunk-size', type=int, default=8)
    p.add_argument('--offline-experiment', action='store_true')
    args = p.parse_args(argv)
    try:
        train(args)
    except (OSError, ValueError, KeyError, TypeError, importlib.metadata.PackageNotFoundError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
