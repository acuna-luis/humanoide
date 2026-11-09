#!/usr/bin/env python3
"""Convert unqualified ball candidates to a local, OFFLINE EXPERIMENT dataset.

No control or robot connection exists here. The resulting actions remain
hypotheses; this program never authorizes physical execution or Hub upload.
Only LeRobot 0.5.1 is supported. Raw timestamps are retained in a sidecar.
"""
import argparse
import bisect
import contextlib
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import sys

import numpy as np
from PIL import Image

from prepare_ball_observations import RIGHT_HAND, digest, finite_vector, load_json
from prepare_ball_candidate_targets import JOINTS, SNAPSHOT_SHA256, TRANSMISSIONS_SHA256


FPS = 2
PERIOD_NS = 1_000_000_000 // FPS
MAX_GAP_NS = 400_000_000
MAX_AGE_NS = 400_000_000
EXPECTED_ORDER = JOINTS + ['grasp_hold_intent_candidate']
NUMERICAL_FEATURES = {'observation.state': 27, 'action': 8}


def stable_feature_stats(array, existing):
    """Population statistics from stored float32 values, centered in float64.

    Keep the LeRobot v0.5.1 shape/keys; replace its approximate quantiles by
    exact linear quantiles of these values. The true std of a constant is zero.
    """
    data = np.asarray(array)
    if data.dtype != np.float32 or data.ndim != 2 or len(data) == 0 or not np.isfinite(data).all():
        raise ValueError('stats require a finite, nonempty float32 matrix')
    if not isinstance(existing, dict) or not {'min','max','mean','std','count'} <= set(existing):
        raise ValueError('existing LeRobot feature stats malformed')
    values = data.astype(np.float64)
    low, high = values.min(axis=0), values.max(axis=0)
    mean = values.mean(axis=0)
    mean[low == high] = low[low == high]
    std = np.sqrt(np.mean((values-mean)**2, axis=0))
    std[low == high] = 0.0
    result = dict(existing)
    result.update(min=low, max=high, mean=mean, std=std, count=np.array([len(data)],dtype=np.int64))
    for key in existing:
        if key.startswith('q') and key[1:].isdigit():
            percentile=int(key[1:])
            if not 0 <= percentile <= 100:
                raise ValueError('unsupported quantile metadata')
            result[key] = np.quantile(values, percentile/100, axis=0, method='linear')
    return result


@contextlib.contextmanager
def stable_episode_stats_hook(writer_module):
    """Patch only the current converter process, then restore vendor code."""
    original = writer_module.compute_episode_stats
    def corrected(episode_data, features, *args, **kwargs):
        stats = original(episode_data, features, *args, **kwargs)
        for key, width in NUMERICAL_FEATURES.items():
            data=np.asarray(episode_data[key])
            if data.ndim != 2 or data.shape[1] != width:
                raise ValueError(f'{key}: unexpected episode dimensions')
            stats[key]=stable_feature_stats(data,stats[key])
        return stats
    writer_module.compute_episode_stats=corrected
    try:
        yield
    finally:
        writer_module.compute_episode_stats=original


def read_saved_float32(dataset_dir):
    """Read actual Parquet rows, without decoding/using the private images."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    files=sorted((dataset_dir/'data').glob('*/*.parquet'))
    if not files:
        raise ValueError('no saved LeRobot parquet data')
    rows=[]
    for path in files:
        table=pq.read_table(path,columns=['episode_index','frame_index',*NUMERICAL_FEATURES])
        for key in NUMERICAL_FEATURES:
            typ=table.schema.field(key).type
            if not (pa.types.is_list(typ) or pa.types.is_large_list(typ) or pa.types.is_fixed_size_list(typ)) or not pa.types.is_float32(typ.value_type):
                raise ValueError(f'{key}: saved parquet is not a float32 vector')
        data=table.to_pydict()
        for i in range(table.num_rows):
            rows.append((int(data['episode_index'][i]),int(data['frame_index'][i]),
                         data['observation.state'][i],data['action'][i]))
    rows.sort(key=lambda x:(x[0],x[1]))
    return rows


def read_saved_episode_stats(dataset_dir):
    """Read per-episode numerical stats written by LeRobot 0.5.1."""
    import pyarrow.parquet as pq
    files=sorted((dataset_dir/'meta'/'episodes').glob('*/*.parquet'))
    if not files:
        raise ValueError('no saved LeRobot episode metadata parquet')
    names=('min','max','mean','std','count','q01','q10','q50','q90','q99')
    columns=['episode_index']+[f'stats/{key}/{name}' for key in NUMERICAL_FEATURES for name in names]
    records=[]
    for path in files:
        table=pq.read_table(path,columns=columns);data=table.to_pydict()
        for i in range(table.num_rows):
            stats={key:{name:data[f'stats/{key}/{name}'][i] for name in names} for key in NUMERICAL_FEATURES}
            records.append((int(data['episode_index'][i]),stats))
    return sorted(records,key=lambda x:x[0])


def verify_episode_statistics(saved_rows, episode_records):
    """Verify stored per-episode statistics against actual saved float32 rows."""
    groups={}
    for episode,frame,state,action in saved_rows:
        groups.setdefault(episode,[]).append((frame,state,action))
    if [r[0] for r in episode_records] != sorted(groups):
        raise ValueError('saved per-episode statistics have missing or duplicate episodes')
    counts={}
    for episode,stats in episode_records:
        values=groups[episode]
        if [r[0] for r in values] != list(range(len(values))):
            raise ValueError('saved episode has missing or duplicate frames')
        counts[str(episode)]=len(values)
        for key,idx in [('observation.state',1),('action',2)]:
            old=stats.get(key)
            if not isinstance(old,dict) or old.get('count') != [len(values)]:
                raise ValueError(f'{key}: saved episode stats count mismatch')
            matrix=np.asarray([r[idx] for r in values],dtype=np.float32)
            reference=stable_feature_stats(matrix,old)
            for name in ('min','max','mean','std','q01','q10','q50','q90','q99'):
                actual=np.asarray(old.get(name),dtype=np.float64)
                expected=np.asarray(reference[name],dtype=np.float64)
                if actual.shape != expected.shape or not np.isfinite(actual).all() or not np.allclose(actual,expected,rtol=1e-12,atol=1e-15):
                    raise ValueError(f'{key}: saved per-episode {name} does not match float32 data')
                if name=='std' and np.any(actual[expected==0] != 0):
                    raise ValueError(f'{key}: constant episode axis has nonzero std')
    return counts


def correct_global_stats(output, saved_rows, expected_rows, episode_records):
    """Audit the stored samples and update only state/action global statistics."""
    if len(saved_rows) != len(expected_rows):
        raise ValueError('saved parquet row count differs from converted samples')
    states=[];actions=[]
    for saved,expected in zip(saved_rows,expected_rows):
        if len(saved) != 4 or saved[:2] != expected[:2]:
            raise ValueError('saved parquet episode/frame order differs from conversion')
        state=np.asarray(saved[2],dtype=np.float32);action=np.asarray(saved[3],dtype=np.float32)
        if (state.shape != (27,) or action.shape != (8,) or not np.array_equal(state,expected[2]) or
                not np.array_equal(action,expected[3])):
            raise ValueError('saved float32 values differ from converter inputs')
        states.append(state);actions.append(action)
    episode_counts=verify_episode_statistics(saved_rows,episode_records)
    dataset_dir=output/'lerobot_dataset'
    path=dataset_dir/'meta'/'stats.json'
    old_bytes=path.read_bytes()
    original=json.loads(old_bytes)
    updated=dict(original)
    changed={}
    for key,values in [('observation.state',states),('action',actions)]:
        old=original.get(key)
        if not isinstance(old,dict) or old.get('count') != [len(saved_rows)]:
            raise ValueError(f'{key}: existing stats count mismatch')
        for stat in ('min','max','mean','std'):
            if not isinstance(old.get(stat),list) or len(old[stat]) != NUMERICAL_FEATURES[key]:
                raise ValueError(f'{key}: existing stats shape mismatch')
        new=stable_feature_stats(np.stack(values),old)
        updated[key]={k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in new.items()}
        changed[key]={'old_std':old['std'],'new_std':updated[key]['std'],
                      'exactly_constant_indices':[i for i,(a,b) in enumerate(zip(updated[key]['min'],updated[key]['max'])) if a==b]}
    backup=output/'stats_before_global_correction.json'
    with backup.open('xb') as f:f.write(old_bytes)
    with path.open('w',encoding='utf-8') as f:
        json.dump(updated,f,ensure_ascii=False,indent=4,allow_nan=False);f.write('\n')
    audit={'schema':'cruzr_ball_stable_stats_audit_v1','count':len(saved_rows),
        'method':'stored float32 values; exact float64 centered population variance; exact linear quantiles',
        'episode_stats':'same float64 centered method via process-local LeRobot writer hook',
        'episode_stats_verified_from_saved_parquet':True,'episode_counts':episode_counts,
        'other_features_preserved':True,'std_constant_axes':0.0,
        'original_sha256':hashlib.sha256(old_bytes).hexdigest(), 'corrected_sha256':digest(path),
        'features':changed}
    with (output/'statistics_audit.json').open('x',encoding='utf-8') as f:
        json.dump(audit,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
    return audit


def validate_rows(rows):
    if not isinstance(rows, list) or len(rows) < 3:
        raise ValueError('at least three candidate frames are required')
    names = ('image_source_ns', 'whole_joint_source_ns', 'actuator_source_ns', 'hand_state_source_ns')
    for kind in names:
        values = [r.get(kind) for r in rows]
        if any(type(t) is not int for t in values) or any(b <= a for a,b in zip(values, values[1:])):
            raise ValueError(f'{kind}: missing, duplicate or non-increasing source timestamp')
        if any(b-a > MAX_GAP_NS for a,b in zip(values, values[1:])):
            raise ValueError(f'{kind}: source gap exceeds 400 ms')
    for r in rows:
        if (not finite_vector(r.get('state20'), 20) or not finite_vector(r.get('hand_right_position7'), 7) or
                not finite_vector(r.get('experimental_joint_target7'), 7) or
                type(r.get('experimental_hand_label')) is not int or r['experimental_hand_label'] not in (0,1) or
                not finite_vector(r.get('experimental_target8'), 8) or
                r['experimental_target8'] != r['experimental_joint_target7'] + [r['experimental_hand_label']] or
                r.get('candidate_is_qualified_action') is not False or
                type(r.get('hand_command_source_ns')) is not int):
            raise ValueError('unknown, malformed or incorrectly qualified target; refusing to fill it')
        if r['hand_command_source_ns'] > r['image_source_ns']:
            raise ValueError('hand intent source occurs after associated image')
        if r['image_source_ns'] - r['hand_command_source_ns'] > 80_000_000:
            raise ValueError('hand intention is older than 80 ms at its associated image')
        flags = r.get('historical_position_limit_exceeded')
        if not isinstance(flags,list) or len(flags) != 7 or any(type(x) is not bool for x in flags) or any(flags):
            raise ValueError('target exceeds historical joint limits or check is missing')
    hand_ts = [r['hand_command_source_ns'] for r in rows]
    if any(b <= a for a,b in zip(hand_ts, hand_ts[1:])):
        raise ValueError('hand command timestamps are duplicate or non-increasing')


def read_raw_hand_commands(source, expected_hash):
    """Read the complete recorded command stream, preserving timestamps/lines.

    Camera-aligned candidate labels are too sparse to establish grip at a motor
    command timestamp; a transition can happen between two camera images.
    """
    path=source/'samples.jsonl'
    if not isinstance(expected_hash,str) or digest(path) != expected_hash:
        raise ValueError('original hand command source SHA256 mismatch')
    commands=[]
    with path.open(encoding='utf-8') as f:
        for lineno,line in enumerate(f,1):
            if 'hand_command_right' not in line:
                continue
            row=json.loads(line)
            if row.get('kind') != 'hand_command_right':
                continue
            stamp=row.get('source_ns'); message=row.get('message')
            if type(stamp) is not int:
                raise ValueError('raw hand command timestamp missing')
            mode=message.get('mode') if isinstance(message,dict) else None
            names=message.get('names') if isinstance(message,dict) else None
            valid_mode = isinstance(mode,list) and len(mode) == 7 and all(type(x) is int for x in mode)
            if names == RIGHT_HAND and valid_mode and mode == [5]*7:
                value=0
            elif names == RIGHT_HAND and valid_mode and mode == [7]*7:
                value=1
            else:
                value=None
            if commands and stamp < commands[-1]['source_ns']:
                raise ValueError('raw hand command source timestamps regressed in recording order')
            if commands and stamp == commands[-1]['source_ns'] and value != commands[-1]['candidate_label']:
                raise ValueError('UNKNOWN: conflicting simultaneous raw hand commands')
            commands.append({'source_ns':stamp,'source_line':lineno,'candidate_label':value})
    if not commands:
        raise ValueError('no original right hand commands available')
    # Identical same-time labels are retained; conflicting labels are rejected.
    # Monotone source timestamps do not certify the physical source clocks.
    return commands


def raw_intent_at(commands, times, reference_ns):
    i=bisect.bisect_right(times,reference_ns)-1
    if i<0:
        raise ValueError('UNKNOWN: no prior raw hand command')
    command=commands[i]; stamp=command['source_ns']
    if reference_ns-stamp > 80_000_000:
        raise ValueError('UNKNOWN: raw hand command older than 80 ms')
    first=bisect.bisect_left(times,stamp)
    if command['candidate_label'] is None or any(x['candidate_label'] != command['candidate_label'] for x in commands[first:i]):
        raise ValueError('UNKNOWN: invalid or conflicting simultaneous raw hand commands')
    return command


def select_causal_samples(rows, raw_commands):
    """Uniform 2 Hz; all observations and grip evidence precede motor command.

    Nearest prior is used independently for each source; no interpolation.
    Gaps or repeated selected records abort rather than silently fill missing data.
    """
    validate_rows(rows)
    streams = {key: [r[key] for r in rows] for key in
        ('image_source_ns', 'whole_joint_source_ns', 'actuator_source_ns', 'hand_state_source_ns')}
    hand_times=[command['source_ns'] for command in raw_commands]
    if any(b < a for a,b in zip(hand_times,hand_times[1:])):
        raise ValueError('raw hand commands not sorted')
    start = rows[0]['image_source_ns']
    end = min(rows[-1]['image_source_ns'], rows[-1]['actuator_source_ns'])
    samples = []
    previous = None
    tick = start + PERIOD_NS  # initial warm-up, permits genuinely prior observations
    while tick <= end:
        command_i = bisect.bisect_right(streams['actuator_source_ns'], tick)-1
        if command_i < 0:
            raise ValueError('no past motor command for resampled timestamp')
        command = rows[command_i]
        command_t = command['actuator_source_ns']
        selected = {}
        for key in ('image_source_ns', 'whole_joint_source_ns', 'hand_state_source_ns'):
            i = bisect.bisect_right(streams[key], command_t)-1
            if i < 0:
                raise ValueError(f'no {key} observation before motor command')
            selected[key] = i
            if command_t-streams[key][i] > MAX_AGE_NS:
                raise ValueError(f'{key} too old relative to motor command')
        if tick-command_t > MAX_AGE_NS:
            raise ValueError('motor command too old for resampled timestamp')
        hand_command=raw_intent_at(raw_commands,hand_times,command_t)
        indices = (command_i, selected['image_source_ns'], selected['whole_joint_source_ns'],
                   selected['hand_state_source_ns'])
        if previous is not None and any(a == b for a,b in zip(previous, indices)):
            raise ValueError('resampling would repeat a source frame/command')
        previous = indices
        image, state, hand = (rows[selected[key]] for key in
            ('image_source_ns','whole_joint_source_ns','hand_state_source_ns'))
        samples.append({'grid_source_ns': tick, 'image_source_frame': image['source_frame'],
            'image_file': image['png_file'], 'image_sha256': image['png_sha256'],
            'image_source_ns': image['image_source_ns'], 'joint_source_ns': state['whole_joint_source_ns'],
            'hand_state_source_ns': hand['hand_state_source_ns'], 'motor_command_source_ns': command_t,
            'hand_command_source_ns': hand_command['source_ns'], 'hand_command_source_line': hand_command['source_line'],
            'state27': state['state20']+hand['hand_right_position7'],
            'target8': command['experimental_joint_target7']+[hand_command['candidate_label']]})
        tick += PERIOD_NS
    if not samples:
        raise ValueError('not enough duration for a causal 2 Hz sample')
    # A lower fixed rate must not silently erase a grasp/open transition from
    # the observational labels, including at either truncated edge.
    def changes(labels):
        return [label for i,label in enumerate(labels) if i == 0 or label != labels[i-1]]
    # Compare to every raw hand command over the full interval, not the sparse
    # camera-aligned labels. Unknown/stale/conflicting events abort.
    begin=rows[0]['actuator_source_ns']; end=rows[-1]['actuator_source_ns']
    first_intent=raw_intent_at(raw_commands,hand_times,begin)
    first_idx=bisect.bisect_right(hand_times,begin)
    last_idx=bisect.bisect_right(hand_times,end)
    events=[first_intent]+raw_commands[first_idx:last_idx]
    for a,b in zip(events,events[1:]):
        if b['source_ns']-a['source_ns'] > 80_000_000:
            raise ValueError('UNKNOWN: gap in raw hand commands exceeds 80 ms')
        raw_intent_at(raw_commands,hand_times,b['source_ns'])
    raw_intent_at(raw_commands,hand_times,end)
    source_transitions = changes([r['candidate_label'] for r in events])
    sampled_transitions = changes([s['target8'][-1] for s in samples])
    if source_transitions != sampled_transitions:
        raise ValueError('2 Hz resampling would hide a hand-intent transition')
    return samples


def load_bundle(input_dir):
    manifest_path = input_dir/'manifest.json'
    m = load_json(manifest_path)
    if (m.get('schema') != 'cruzr_ball_candidate_targets_v1' or m.get('training_ready') is not False or
            m.get('physical_control_qualified') is not False or m.get('offline_experiment_only') is not True or
            m.get('historical_hardware_snapshot_sha256') != SNAPSHOT_SHA256 or
            m.get('historical_transmissions_sha256') != TRANSMISSIONS_SHA256 or
            m.get('experimental_target8_order') != EXPECTED_ORDER or m.get('state_right_hand_names') != RIGHT_HAND):
        raise ValueError('unrecognized or unsafe candidate bundle provenance')
    task = m.get('task')
    if not isinstance(task, str) or not task.strip():
        raise ValueError('empty task instruction')
    selected, source_splits, common_state_names, command_cache = [], {}, None, {}
    all_segments = m.get('segments')
    if not isinstance(all_segments, list) or not all_segments:
        raise ValueError('candidate bundle has no segments')
    ids = set()
    for s in all_segments:
        ident, source, split = s.get('id'), s.get('source_dir'), s.get('split')
        if not isinstance(ident,str) or not re.fullmatch(r'[A-Za-z0-9_-]+', ident) or ident in ids:
            raise ValueError('invalid or duplicate segment id')
        ids.add(ident)
        if not isinstance(source,str) or split not in {'inspection_train','inspection_validation','inspection_test'}:
            raise ValueError('invalid source capture or inspection split')
        previous = source_splits.setdefault(source,split)
        if previous != split:
            raise ValueError('capture assigned to multiple splits')
        if s.get('status') != 'candidate_success':
            raise ValueError('assisted, failed and unreviewed segments must not enter the candidate bundle')
        if split != 'inspection_train':
            continue
        state_names = m.get('state20_names_by_source',{}).get(source)
        if not isinstance(state_names,list) or len(state_names) != 20 or len(set(state_names)) != 20 or not set(JOINTS) <= set(state_names):
            raise ValueError('bad 20D state names')
        if common_state_names is not None and state_names != common_state_names:
            raise ValueError('source state order differs across training episodes')
        common_state_names = state_names
        path = input_dir/ident/'candidate_targets.jsonl'
        if digest(path) != s.get('candidate_targets_sha256'):
            raise ValueError(f'{ident}: candidate target checksum mismatch')
        with path.open(encoding='utf-8') as f:
            rows = [json.loads(line) for line in f]
        lo,hi=s.get('start_frame'),s.get('end_frame')
        if type(lo) is not int or type(hi) is not int or [r.get('source_frame') for r in rows] != list(range(lo,hi+1)):
            raise ValueError(f'{ident}: frame sequence invalid')
        for r in rows:
            n=r['source_frame']; image = input_dir/ident/f'rgb/{n:06}.png'
            if r.get('png_file') != f'rgb/{n:06}.png' or input_dir not in image.resolve(strict=True).parents:
                raise ValueError('candidate image escapes bundle or name differs')
            if digest(image) != r.get('png_sha256'):
                raise ValueError(f'{ident}: image checksum mismatch')
        hashes=s.get('source_hashes')
        if not isinstance(hashes,dict) or not isinstance(hashes.get('samples.jsonl'),str):
            raise ValueError(f'{ident}: original sample hash missing')
        if source not in command_cache:
            command_cache[source]=(hashes['samples.jsonl'],read_raw_hand_commands(Path(source),hashes['samples.jsonl']))
        elif command_cache[source][0] != hashes['samples.jsonl']:
            raise ValueError('conflicting raw sample hashes for one capture')
        samples = select_causal_samples(rows, command_cache[source][1])
        selected.append((s,samples))
    if not selected:
        raise ValueError('no candidate_success inspection_train segments')
    return m, selected, common_state_names


def _dataset_class():
    version = importlib.metadata.version('lerobot')
    if version != '0.5.1':
        raise ValueError(f'expected LeRobot 0.5.1, found {version}')
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
    from lerobot.datasets.lerobot_dataset import LeRobotDataset
    return LeRobotDataset


def convert(input_dir, output, offline_experiment, dataset_class=None, writer_module=None, saved_reader=None,
            episode_stats_reader=None):
    if offline_experiment is not True:
        raise ValueError('must explicitly pass --offline-experiment')
    input_dir,output=(x.expanduser().resolve() for x in (input_dir,output))
    if output.exists() or not output.parent.is_dir():
        raise ValueError('output must be a new directory under an existing parent')
    if output == input_dir or input_dir in output.parents or output in input_dir.parents:
        raise ValueError('output must not overlap candidate bundle')
    m, episodes, state_names = load_bundle(input_dir)
    # The original captures are separate from the candidate bundle. Protect
    # their resolved paths too, including symlinks and future mount layouts.
    for segment in m['segments']:
        source = Path(segment['source_dir']).expanduser().resolve(strict=True)
        if output == source or source in output.parents or output in source.parents:
            raise ValueError('output must not overlap an original capture')
    # Check all selected images and ensure they share one shape before output.
    image_shape = None
    for segment,samples in episodes:
        for s in samples:
            with Image.open(input_dir/segment['id']/s['image_file']) as im:
                if im.mode != 'RGB':
                    raise ValueError('expected RGB images')
                shape=(3,im.height,im.width)
                if image_shape is not None and shape != image_shape:
                    raise ValueError('inconsistent image dimensions')
                image_shape=shape
                im.verify()
    dataset_class = dataset_class or _dataset_class()
    if writer_module is None:
        from lerobot.datasets import dataset_writer as writer_module
    saved_reader = saved_reader or read_saved_float32
    episode_stats_reader = episode_stats_reader or read_saved_episode_stats
    features = {'observation.images.camera1': {'dtype':'image','shape':image_shape,'names':['channel','height','width']},
        'observation.state': {'dtype':'float32','shape':(27,), 'names': state_names+RIGHT_HAND},
        'action': {'dtype':'float32','shape':(8,), 'names': EXPECTED_ORDER}}
    output.mkdir()
    expected_rows=[]
    with stable_episode_stats_hook(writer_module):
        ds = dataset_class.create(repo_id='local/cruzr-ball-offline-experiment', fps=FPS,
            root=output/'lerobot_dataset', features=features, robot_type='cruzr_s2_offline', use_videos=False)
        with (output/'source_alignment.jsonl').open('x',encoding='utf-8') as sidecar:
            for episode_idx,(segment,samples) in enumerate(episodes):
                for frame_idx,s in enumerate(samples):
                    with Image.open(input_dir/segment['id']/s['image_file']) as im:
                        pixels=np.array(im,dtype=np.uint8)
                    state=np.asarray(s['state27'],dtype=np.float32); action=np.asarray(s['target8'],dtype=np.float32)
                    expected_rows.append((episode_idx,frame_idx,state.copy(),action.copy()))
                    frame={'observation.images.camera1':pixels,'observation.state':state,'action':action,'task':m['task']}
                    ds.add_frame(frame)
                    sidecar.write(json.dumps({'episode_index':episode_idx,'frame_index':frame_idx,'segment_id':segment['id'],
                        **{k:v for k,v in s.items() if k not in {'state27','target8'}}},allow_nan=False)+'\n')
                ds.save_episode()
        ds.finalize()
    dataset_root=output/'lerobot_dataset'
    stats_audit=correct_global_stats(output,saved_reader(dataset_root),expected_rows,episode_stats_reader(dataset_root))
    files={str(p.relative_to(output)):digest(p) for p in sorted(output.rglob('*')) if p.is_file()}
    result={'schema':'cruzr_ball_lerobot_offline_experiment_v1', 'lerobot_version':'0.5.1',
        'offline_experiment_only':True,'training_ready':False,'physical_control_qualified':False,
        'not_authorized_for_hub_upload_or_robot_execution':True,
        'candidate_bundle_manifest_sha256':digest(input_dir/'manifest.json'),
        'task':m['task'],'fps':FPS,'state_names':state_names+RIGHT_HAND,'action_names':EXPECTED_ORDER,
        'resampling':{'method':'2 Hz causal last prior for each stream; no interpolation','warmup_ns':PERIOD_NS,
                      'max_source_gap_ns':MAX_GAP_NS,'max_age_to_command_ns':MAX_AGE_NS,
                      'image_must_precede_motor_command':True,'source_reuse_rejected':True,
                      'lost_hand_intent_transitions_rejected':True,
                      'hand_labels_source':'full original hand_command_right stream, SHA256 verified',
                      'max_raw_hand_command_age_ns':80_000_000},
        'limitations':m['limitations']+['experimental action labels are hypothetical and not control-qualified',
            'causal ordering is nominal only: source clocks and sensor latency are not physically calibrated',
            'SmolVLA default horizon of 50 actions would represent 25 s at 2 Hz; choose and validate a shorter horizon',
            'no independently validated test set; no evidence of 20 cm lift or HOME start'],
        'stable_statistics':{'method':stats_audit['method'],'audit_file':'statistics_audit.json',
                             'original_global_stats_sha256':stats_audit['original_sha256'],
                             'corrected_global_stats_sha256':stats_audit['corrected_sha256']},
        'segments':[{'id':seg['id'],'source_dir':seg['source_dir'],'source_samples_sha256':seg['source_hashes']['samples.jsonl'],
                     'status':seg['status'],'split':seg['split'],
                     'frame_count':len(samples)} for seg,samples in episodes], 'output_sha256':files}
    with (output/'manifest.json').open('x',encoding='utf-8') as f:
        json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidates',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--offline-experiment',action='store_true',help='acknowledge hypothetical actions; no physical control')
    args=p.parse_args(argv)
    try:
        result=convert(args.candidates,args.output,args.offline_experiment)
    except (ValueError, KeyError, TypeError, OSError, importlib.metadata.PackageNotFoundError) as exc:
        print(f'ERROR: {exc}',file=sys.stderr);return 1
    print(json.dumps({'output':str(args.output),'episodes':len(result['segments']),
                      'training_ready':False,'physical_control_qualified':False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
