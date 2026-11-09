#!/usr/bin/env python3
"""Evaluate first action on TRAIN observations only; never connect to a robot.

This is an in-distribution diagnostic on unqualified hypothetical labels, not
an independent evaluation or physical validation. The model receives no ground
truth actions or future-action features during prediction.
"""
import argparse
import importlib.metadata
import json
import math
import os
from pathlib import Path
import statistics
import sys
import time

from train_offline import sha256, verify_dataset


def prediction_input(row):
    """Whitelist observations; deliberately exclude all action/padding fields."""
    keys = ('observation.images.camera1', 'observation.state', 'task')
    if any(k not in row for k in keys):
        raise ValueError('Missing observation, camera or task')
    return {k: row[k] for k in keys}


def guard_prediction_batch(batch):
    """LeRobot inserts action=None for observation-only transitions."""
    if batch.get('action') is not None or batch.get('action_is_pad') is not None:
        raise ValueError('Action leaked into prediction inputs')
    result=dict(batch)
    result.pop('action',None)
    result.pop('action_is_pad',None)
    return result


def loss_input(row):
    """Explicit batch dimension: LeRobot does not batch 2-D action chunks."""
    result=prediction_input(row)
    if 'action' not in row or 'action_is_pad' not in row:
        raise ValueError('Missing action chunk or padding mask')
    result['action']=row['action'].unsqueeze(0)
    result['action_is_pad']=row['action_is_pad'].unsqueeze(0)
    return result


def metrics(records, action_names):
    if not records or len(action_names) != 8:
        raise ValueError('Expected records and 8 action names')
    for record in records:
        for key in ('prediction','target'):
            values=record.get(key)
            if not isinstance(values,list) or len(values)!=8 or any(
                    not isinstance(x,(int,float)) or isinstance(x,bool) or not math.isfinite(x) for x in values):
                raise ValueError(f'Invalid {key} vector')
        if record['target'][7] not in (0,1):
            raise ValueError('Invalid provisional grasp target')
        if any(not isinstance(record.get(k),(int,float)) or isinstance(record[k],bool) or
               not math.isfinite(record[k]) or record[k]<0 for k in ('flow_matching_loss','prediction_seconds')):
            raise ValueError('Invalid loss or prediction timing')
    by_joint = []
    for i, name in enumerate(action_names[:7]):
        errors = [float(r['prediction'][i])-float(r['target'][i]) for r in records]
        predicted = [float(r['prediction'][i]) for r in records]
        target = [float(r['target'][i]) for r in records]
        by_joint.append({'name': name, 'mae_rad': sum(abs(x) for x in errors)/len(errors),
            'rmse_rad': math.sqrt(sum(x*x for x in errors)/len(errors)),
            'max_abs_error_rad': max(abs(x) for x in errors), 'bias_rad': sum(errors)/len(errors),
            'prediction_range_rad': [min(predicted), max(predicted)],
            'target_range_rad': [min(target), max(target)]})
    target = [int(r['target'][7]) for r in records]
    score = [float(r['prediction'][7]) for r in records]
    binary = [int(x >= 0.5) for x in score]
    losses = [float(r['flow_matching_loss']) for r in records]
    times = [float(r['prediction_seconds']) for r in records]
    return {'samples': len(records), 'per_joint': by_joint,
        'arm_mae_rad': sum(x['mae_rad'] for x in by_joint)/7,
        'grasp': {'threshold_exploratory': 0.5, 'accuracy_vs_provisional_labels':
            sum(a == b for a,b in zip(binary,target))/len(target),
            'false_close_count': sum(a == 1 and b == 0 for a,b in zip(binary,target)),
            'false_open_count': sum(a == 0 and b == 1 for a,b in zip(binary,target)),
            'score_range': [min(score),max(score)], 'target_counts': {'0': target.count(0),'1': target.count(1)}},
        'stochastic_flow_matching_loss': {'mean': sum(losses)/len(losses),
            'min': min(losses), 'max': max(losses)},
        'prediction_seconds': {'mean': sum(times)/len(times), 'median': statistics.median(times),
            'min': min(times), 'max': max(times)}}


def load_sidecar(path):
    with path.open(encoding='utf-8') as f:
        rows = [json.loads(line) for line in f]
    if not rows:
        raise ValueError('Empty dataset sidecar')
    return rows


def validate_stats(dataset_root, checkpoint):
    import torch
    from safetensors.torch import load_file
    stats = json.loads((dataset_root/'lerobot_dataset/meta/stats.json').read_text(encoding='utf-8'))
    pre = load_file(str(checkpoint/'policy_preprocessor_step_5_normalizer_processor.safetensors'),device='cpu')
    post = load_file(str(checkpoint/'policy_postprocessor_step_0_unnormalizer_processor.safetensors'),device='cpu')
    for feat in ('observation.state','action'):
        for metric in ('mean','std','min','max'):
            key = feat+'.'+metric
            expected = torch.tensor(stats[feat][metric],dtype=torch.float32)
            if key not in pre or not torch.equal(pre[key],expected) or not torch.isfinite(pre[key]).all():
                raise ValueError(f'Checkpoint normalization differs from dataset: {key}')
            if feat == 'action' and (key not in post or not torch.equal(post[key],expected)):
                raise ValueError(f'Checkpoint denormalization differs from dataset: {key}')


def validate_checkpoint(checkpoint, vlm):
    config=json.loads((checkpoint/'config.json').read_text(encoding='utf-8'))
    pre=json.loads((checkpoint/'policy_preprocessor.json').read_text(encoding='utf-8'))
    features=config.get('input_features',{})
    if (config.get('type') != 'smolvla' or config.get('push_to_hub') is not False or
            features.get('observation.state',{}).get('shape') != [27] or
            features.get('observation.images.camera1',{}).get('shape') != [3,576,960] or
            config.get('output_features',{}).get('action',{}).get('shape') != [8] or
            config.get('chunk_size') != 8 or config.get('n_action_steps') != 8 or
            config.get('vlm_model_name') != str(vlm)):
        raise ValueError('Unexpected checkpoint model schema, chunk or VLM path')
    tokenizer=[s for s in pre.get('steps',[]) if s.get('registry_name')=='tokenizer_processor']
    if len(tokenizer)!=1 or tokenizer[0].get('config',{}).get('tokenizer_name') != str(vlm):
        raise ValueError('Checkpoint tokenizer does not point to local VLM')
    if not (checkpoint/'model.safetensors').is_file():
        raise ValueError('Checkpoint weights missing')
    return config


def evaluate(args):
    if not args.train_only:
        raise ValueError('Must explicitly acknowledge --train-only evaluation')
    if not 0 <= args.seed <= 2**31-1 or not 1 <= args.limit <= 60:
        raise ValueError('Invalid seed or frame limit')
    for key in ('HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE','HF_HUB_DISABLE_TELEMETRY'):
        if os.environ.get(key) != '1':
            raise ValueError(f'{key}=1 required')
    if importlib.metadata.version('lerobot') != '0.5.1':
        raise ValueError('LeRobot 0.5.1 is required')
    dataset,checkpoint,vlm,output=(Path(x).resolve(strict=True) for x in
        (args.dataset,args.checkpoint,args.vlm,args.output))
    if any(not p.is_dir() for p in (dataset,checkpoint,vlm,output)) or list(output.iterdir()):
        raise ValueError('Inputs must be directories and output must be empty')
    for p in (dataset,checkpoint,vlm):
        if p==output or p in output.parents or output in p.parents:
            raise ValueError('Output and input directories must not overlap')
    manifest=verify_dataset(dataset)
    config=validate_checkpoint(checkpoint,vlm)
    validate_stats(dataset,checkpoint)
    sidecar=load_sidecar(dataset/'source_alignment.jsonl')
    if len(sidecar)!=sum(s['frame_count'] for s in manifest['segments']):
        raise ValueError('Sidecar frame count differs from manifest')

    import torch
    from lerobot.configs.policies import PreTrainedConfig
    from lerobot.datasets.lerobot_dataset import LeRobotDataset
    from lerobot.policies.factory import make_pre_post_processors
    from lerobot.policies.smolvla.configuration_smolvla import SmolVLAConfig
    from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy
    if args.device=='cuda':
        if not torch.cuda.is_available():
            raise ValueError('CUDA unavailable')
        free,_=torch.cuda.mem_get_info(0)
        if free<8*1024**3:
            raise ValueError('Less than 8 GiB free on shared GPU')
        torch.cuda.set_per_process_memory_fraction(0.35,0)
    torch.set_num_threads(2)
    policy_config=PreTrainedConfig.from_pretrained(checkpoint,local_files_only=True)
    if not isinstance(policy_config,SmolVLAConfig):
        raise ValueError('Checkpoint is not SmolVLA')
    policy_config.device=args.device
    policy_config.vlm_model_name=str(vlm)
    model=SmolVLAPolicy.from_pretrained(checkpoint,config=policy_config,local_files_only=True)
    model.eval()
    preprocessor,postprocessor=make_pre_post_processors(policy_cfg=policy_config,
        pretrained_path=str(checkpoint),preprocessor_overrides={
            'device_processor':{'device':args.device},
            'tokenizer_processor':{'tokenizer_name':str(vlm)}},
        postprocessor_overrides={'device_processor':{'device':'cpu'}})
    ds=LeRobotDataset(repo_id='local/cruzr-ball-offline-experiment',root=dataset/'lerobot_dataset',
        delta_timestamps={'action':[i/2 for i in range(8)]})
    if ds.num_frames!=len(sidecar) or ds.num_episodes!=len(manifest['segments']):
        raise ValueError('Loaded dataset dimensions differ from its sidecar')
    records=[]
    for i in range(min(args.limit,ds.num_frames)):
        row=ds[i]
        if tuple(row['observation.state'].shape)!=(27,) or tuple(row['observation.images.camera1'].shape)!=(3,576,960) or tuple(row['action'].shape)!=(8,8):
            raise ValueError('Unexpected observation or action chunk shape')
        meta=sidecar[i]
        if (int(row['index'])!=i or int(row['episode_index'])!=meta['episode_index'] or
                int(row['frame_index'])!=meta['frame_index']):
            raise ValueError('Dataset index and sidecar disagree')
        target=row['action'][0].detach().cpu().to(torch.float32)
        if not torch.isfinite(target).all() or float(target[-1]) not in (0.0,1.0):
            raise ValueError('Invalid target or provisional grasp label')
        # The policy gets only the observation and task, NEVER target or future
        # action tensors; the target is used exclusively after prediction.
        observation=prediction_input(row)
        batch=guard_prediction_batch(preprocessor(observation))
        model.reset()
        torch.manual_seed(args.seed+i)
        if args.device=='cuda': torch.cuda.synchronize()
        start=time.perf_counter()
        with torch.inference_mode():
            predicted=model.predict_action_chunk(batch)
            if tuple(predicted.shape)!=(1,8,8):
                raise ValueError('Model produced unexpected action chunk')
            decoded=postprocessor(predicted[:,0,:])
        if args.device=='cuda': torch.cuda.synchronize()
        elapsed=time.perf_counter()-start
        result=decoded.detach().cpu().reshape(-1)
        if tuple(result.shape)!=(8,) or not torch.isfinite(result).all() or not math.isfinite(elapsed):
            raise ValueError('Non-finite prediction or unexpected decoded shape')
        # Separate diagnostic: use the real action chunk only to compute the
        # stochastic flow-matching training loss after prediction is complete.
        loss_batch=preprocessor(loss_input(row))
        if tuple(loss_batch['action'].shape)!=(1,8,8) or tuple(loss_batch['action_is_pad'].shape)!=(1,8):
            raise ValueError('Unexpected batched loss action or padding shape')
        torch.manual_seed(args.seed+1_000_000+i)
        with torch.inference_mode():
            loss,_=model.forward(loss_batch)
        loss_value=float(loss.detach().cpu())
        if not math.isfinite(loss_value):
            raise ValueError('Non-finite diagnostic loss')
        records.append({'index':i,'episode_index':meta['episode_index'],'frame_index':meta['frame_index'],
            'segment_id':meta['segment_id'],'image_source_frame':meta['image_source_frame'],
            'image_file':meta['image_file'],'image_sha256':meta['image_sha256'],
            'grid_source_ns':meta['grid_source_ns'],'image_source_ns':meta['image_source_ns'],
            'joint_source_ns':meta['joint_source_ns'],'hand_state_source_ns':meta['hand_state_source_ns'],
            'motor_command_source_ns':meta['motor_command_source_ns'],
            'hand_command_source_ns':meta['hand_command_source_ns'],
            'seed':args.seed+i,'loss_seed':args.seed+1_000_000+i,
            'prediction':result.tolist(),'target':target.tolist(),
            'prediction_seconds':elapsed,'flow_matching_loss':loss_value})
    report=metrics(records,manifest['action_names'])
    report.update(schema='cruzr_ball_train_only_evaluation_v1',
        split='TRAIN: same examples used for fitting; no held-out evaluation',
        no_action_or_future_features_in_prediction=True,
        offline_experiment_only=True,physical_control_qualified=False,training_ready=False,
        checkpoint_sha256=sha256(checkpoint/'model.safetensors'),
        dataset_manifest_sha256=sha256(dataset/'manifest.json'),seed=args.seed,device=args.device,
        chunk_size=config['chunk_size'],evaluation_timestamp_unix_ns=time.time_ns(),
        limitations=['in-distribution only; no independent generalization evidence',
            'targets are unqualified historical motor mapping and hand-mode hypotheses',
            'HOME start, 20 cm lift, physical synchronization and safety are not validated',
            '0.5 grasp threshold is diagnostic only; not a validated command',
            'prediction timing includes model inference and postprocessing, excluding input preprocessing',
            'loss is stochastic and includes padded action chunks; not a success probability',
            'fixed seeds do not guarantee bitwise deterministic GPU results'])
    with (output/'predictions.jsonl').open('x',encoding='utf-8') as f:
        for row in records: f.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n')
    report['predictions_sha256']=sha256(output/'predictions.jsonl')
    with (output/'report.json').open('x',encoding='utf-8') as f:
        json.dump(report,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps({'samples':len(records),'arm_mae_rad':report['arm_mae_rad'],
                      'physical_control_qualified':False,'split':'train'}),flush=True)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset',required=True);p.add_argument('--checkpoint',required=True)
    p.add_argument('--vlm',required=True);p.add_argument('--output',required=True)
    p.add_argument('--device',choices=('cpu','cuda'),default='cpu')
    p.add_argument('--seed',type=int,default=20261109);p.add_argument('--limit',type=int,default=60)
    p.add_argument('--train-only',action='store_true')
    args=p.parse_args(argv)
    try: evaluate(args)
    except (OSError, ValueError, KeyError, TypeError, importlib.metadata.PackageNotFoundError) as exc:
        print(f'ERROR: {exc}',file=sys.stderr);return 1
    return 0


if __name__=='__main__':
    raise SystemExit(main())
