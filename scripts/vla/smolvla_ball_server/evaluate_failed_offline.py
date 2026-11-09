#!/usr/bin/env python3
"""Evaluate one-step proposals for failed recorded trials, never control a robot."""
import argparse
import importlib.metadata
import json
import math
import os
from pathlib import Path
import sys
import time

from train_offline import sha256, verify_dataset
from evaluate_train_offline import guard_prediction_batch, validate_checkpoint, validate_stats

TRAIN_MANIFEST_SHA = '8d6bbe4fcfbbac2e8baeb33a5b456074e26b5e46c81b2353329df4fe95ecbd0c'
CHECKPOINT_FILES = {
    'model.safetensors':'e707eea07b58e14b979e78463b94ba75a52b1c18abf8076aebc8aa34ac77f8da',
    'config.json':'4b86b5c2cfc33f0476797f73bec627572710d702f7cc0181701ea51b2bf37ced',
    'policy_preprocessor.json':'25fc79195b8f105116fcd8e690c75ae4d28f315512b51f927f93ff90c5a5630e',
    'policy_postprocessor.json':'f24875ca8641ab68c5aa70b8785537222e2bea90d4a43365a0b9dc0a64cbe6dc',
    'policy_preprocessor_step_5_normalizer_processor.safetensors':'16c9839512f1c2db5380f41f6e9c3af4a6609b3b0bf684e72ceff4a9a1b8a391',
    'policy_postprocessor_step_0_unnormalizer_processor.safetensors':'16c9839512f1c2db5380f41f6e9c3af4a6609b3b0bf684e72ceff4a9a1b8a391'}
VLM_FILES = {
    'added_tokens.json':'74135b8664b56088c0006f1c8e848d79a8eba003411f72ebf1dc2ee96227be3a',
    'chat_template.json':'b585e3598909a5687f9f9d738d35223724dedef256b9b274e1cbfb32b13c74bf',
    'config.json':'ea6bc1237e96247f6258de3e202e2e62b93d6f386dc47e7b36b5588bf3a15e17',
    'generation_config.json':'34835060c9f0f74d1acb456cc72ca32746d3843d9eb5f578f9cbffac1d2eb840',
    'merges.txt':'0b54e8aa4e53d5383e2e4bc635a56b43f9647f7b13832d5d9ecd8f82dac4f510',
    'model.safetensors':'b9bfd456c9472c0acd5719d6e514c4b859891af205ee1a736552fd3497b8b0c3',
    'preprocessor_config.json':'149e315d9410368e5491455bb06e0f763426e9e56cca731c13b24404a29b6374',
    'processor_config.json':'f3ad45028447b3562b4752be0d5916d6806c1ef589091a469608dcf0faa1737c',
    'special_tokens_map.json':'2dfea2a426162316ff1567c82bc6d36d9690cd9f90455f075c77daca78b45c60',
    'tokenizer.json':'5ece781dc8d2b2f3e2f289ca0ae50b17cfc27dd27bfe7971bb8241e0b964331a',
    'tokenizer_config.json':'dd9ce2ab89a3dd881bd9378f1a79b943a064b9275a7e1706d5b7b47b68977913',
    'vocab.json':'82b84012e3add4d01d12ba14442026e49b8cbbaead1f79ecf3d919784f82dc79'}


def verify_hashes(root, expected):
    for name, digest in expected.items():
        path=(root/name).resolve(strict=True)
        if root not in path.parents or sha256(path) != digest:
            raise ValueError(f'input pin differs: {name}')


def validate_test(root, train, mode='failed'):
    if mode not in ('failed', 'current'):
        raise ValueError('unknown observation mode')
    schema = {'failed':'cruzr_ball_failed_observations_v1', 'current':'cruzr_ball_current_observations_v1'}[mode]
    expected_status = {'failed':'failed', 'current':'unreviewed'}[mode]
    manifest = json.loads((root/'manifest.json').read_text())
    if (manifest.get('schema') != schema or
        manifest.get('training_ready') is not False or manifest.get('physical_control_qualified') is not False or
        manifest.get('has_action_column') is not False or manifest.get('state_names') != train.get('state_names') or
        manifest.get('task') != train.get('task')):
        raise ValueError('test and training observation schema differ')
    source_hash = manifest['source_capture_hashes']['samples.jsonl']
    if any(s.get('source_samples_sha256') == source_hash for s in train['segments']):
        raise ValueError('test source also appears in training')
    records = manifest.get('records')
    if not isinstance(records, list) or not records:
        raise ValueError('empty test')
    for row in records:
        if row.get('status') != expected_status or not isinstance(row.get('state27'), list) or len(row['state27']) != 27:
            raise ValueError('invalid observation status or state')
        if any(not isinstance(v, (int,float)) or isinstance(v,bool) or not math.isfinite(v) for v in row['state27']):
            raise ValueError('nonfinite state')
        if any(type(row.get(k)) is not int for k in ('joint_source_ns','hand_source_ns','image_source_ns')) or any(not 0 <= row['image_source_ns']-row[k] <= 80_000_000 for k in ('joint_source_ns','hand_source_ns')):
            raise ValueError('observation not timestamp-causal or state older than 80 ms')
        image=(root/row['image']).resolve(strict=True)
        if root not in image.parents or sha256(image) != row['image_sha256']:
            raise ValueError('test image integrity failed')
    return manifest


def run(args, mode='failed'):
    if mode not in ('failed','current') or not args.offline_only or any(os.environ.get(k) != '1' for k in ('HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE','HF_HUB_DISABLE_TELEMETRY')):
        raise ValueError('offline environment and explicit offline-only acknowledgement required')
    if importlib.metadata.version('lerobot') != '0.5.1' or not 0 <= args.seed <= 2**31-1:
        raise ValueError('unexpected LeRobot or seed')
    test,train,checkpoint,vlm,out=(Path(x).resolve(strict=True) for x in (args.test,args.train,args.checkpoint,args.vlm,args.output))
    if any(not p.is_dir() for p in (test,train,checkpoint,vlm,out)) or list(out.iterdir()):
        raise ValueError('inputs must exist and output be empty')
    if any(out == p or out in p.parents or p in out.parents for p in (test,train,checkpoint,vlm)):
        raise ValueError('output overlaps input')
    if len(args.test_sha256) != 64 or sha256(test/'manifest.json') != args.test_sha256:
        raise ValueError('observation manifest pin differs')
    if sha256(train/'manifest.json') != TRAIN_MANIFEST_SHA:
        raise ValueError('training manifest pin differs')
    verify_hashes(checkpoint,CHECKPOINT_FILES)
    verify_hashes(vlm,VLM_FILES)
    training=verify_dataset(train)
    data=validate_test(test,training,mode)
    config=validate_checkpoint(checkpoint,vlm)
    validate_stats(train,checkpoint)  # ALWAYS use training statistics, never test statistics
    import numpy as np
    import torch
    from PIL import Image
    from lerobot.configs.policies import PreTrainedConfig
    from lerobot.policies.factory import make_pre_post_processors
    from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy
    if args.device == 'cuda':
        if not torch.cuda.is_available() or torch.cuda.mem_get_info(0)[0] < 8*1024**3:
            raise ValueError('less than 8 GiB free on GPU')
        torch.cuda.set_per_process_memory_fraction(0.35,0)
    torch.set_num_threads(2)
    policy_config=PreTrainedConfig.from_pretrained(checkpoint,local_files_only=True)
    policy_config.device=args.device; policy_config.vlm_model_name=str(vlm)
    model=SmolVLAPolicy.from_pretrained(checkpoint,config=policy_config,local_files_only=True)
    model.eval()
    pre,post=make_pre_post_processors(policy_cfg=policy_config,pretrained_path=str(checkpoint),
        preprocessor_overrides={'device_processor':{'device':args.device},'tokenizer_processor':{'tokenizer_name':str(vlm)}},
        postprocessor_overrides={'device_processor':{'device':'cpu'}})
    names=training['action_names'][:7]
    indices=[data['state_names'].index(name) for name in names]
    predictions=[]
    for i,row in enumerate(data['records']):
        with Image.open(test/row['image']) as im:
            if im.mode != 'RGB' or im.size != (960,576): raise ValueError('unexpected image')
            pixels=np.array(im,dtype=np.uint8)
        # Explicit allowlist: only current image, state and instruction reach the model.
        observation={'observation.images.camera1':torch.from_numpy(pixels).permute(2,0,1).to(torch.float32)/255.0,
            'observation.state':torch.tensor(row['state27'],dtype=torch.float32),'task':data['task']}
        batch=guard_prediction_batch(pre(observation))
        model.reset(); torch.manual_seed(args.seed+i)
        if args.device=='cuda': torch.cuda.synchronize()
        start=time.perf_counter()
        with torch.inference_mode():
            chunk=model.predict_action_chunk(batch)
            if tuple(chunk.shape)!=(1,8,8): raise ValueError('bad output chunk')
            decoded=post(chunk[:,0,:])
        if args.device=='cuda': torch.cuda.synchronize()
        prediction=decoded.detach().cpu().reshape(-1).tolist()
        if len(prediction)!=8 or any(not math.isfinite(v) for v in prediction): raise ValueError('bad prediction')
        delta=[prediction[j]-row['state27'][idx] for j,idx in enumerate(indices)]
        predictions.append({'segment_id':row['segment_id'],'source_frame':row['source_frame'],
            'image_sha256':row['image_sha256'],'prediction':prediction,'proposed_minus_observed_rad':delta,
            'seed':args.seed+i,'seconds':time.perf_counter()-start})
    with (out/'predictions.jsonl').open('x') as f:
        for row in predictions: f.write(json.dumps(row,allow_nan=False)+'\n')
    report={'schema':f'cruzr_ball_{mode}_observation_evaluation_v1','samples':len(predictions),
        'distinct_capture_not_independent_success_test':True,'observation_status':{'failed':'failed','current':'unreviewed'}[mode],
        'no_ground_truth_or_future_actions_in_prediction':True,'physical_control_qualified':False,
        'test_manifest_sha256':sha256(test/'manifest.json'),'train_manifest_sha256':sha256(train/'manifest.json'),
        'checkpoint_sha256':sha256(checkpoint/'model.safetensors'),'predictions_sha256':sha256(out/'predictions.jsonl'),
        'max_abs_proposal_minus_observed_rad':max(abs(v) for row in predictions for v in row['proposed_minus_observed_rad']),
        'hand_output_range':[min(row['prediction'][7] for row in predictions),max(row['prediction'][7] for row in predictions)],
        'limitations':[f'{mode} observations: no objective or successful-task label',
            'held-out capture but not proof of independently varied sessions or generalization',
            'nominal timestamps only; clocks and sensor latency not physically calibrated',
            'single open-loop predictions, not closed-loop shadow or physical rollout',
            'hand output is uncalibrated, not a control command; delta is not a safety or error bound',
            'train statistics reused; test action targets are absent']}
    with (out/'report.json').open('x') as f: json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps({'samples':len(predictions),'physical_control_qualified':False}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('test','train','checkpoint','vlm','output'): p.add_argument('--'+key,required=True)
    p.add_argument('--device',choices=('cpu','cuda'),default='cpu');p.add_argument('--seed',type=int,default=20261109)
    p.add_argument('--test-sha256',required=True)
    p.add_argument('--failed-test-only',dest='offline_only',action='store_true')
    try: run(p.parse_args())
    except (OSError,ValueError,KeyError,TypeError,importlib.metadata.PackageNotFoundError) as exc:
        print(f'ERROR: {exc}',file=sys.stderr);sys.exit(1)
