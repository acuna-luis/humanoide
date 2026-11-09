#!/usr/bin/env python3
"""Offline tests with a fake LeRobot writer; no external services or robot."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import bisect
import types

import numpy as np

from PIL import Image
import convert_ball_candidates_to_lerobot as subject


def make_rows():
    result=[]
    for n in range(14):
        ts=1_000_000_000+n*240_000_000
        label=1 if 4 <= n <= 9 else 0
        target=[float(n)/100]*7
        result.append({'source_frame':n, 'image_source_ns':ts, 'whole_joint_source_ns':ts-10_000_000,
            'actuator_source_ns':ts+10_000_000, 'hand_state_source_ns':ts-20_000_000,
            'hand_command_source_ns':ts-1_000_000, 'state20':[0.0]*20,
            'hand_right_position7':[0.0]*7, 'experimental_joint_target7':target,
            'experimental_hand_label':label, 'experimental_target8':target+[label],
            'candidate_is_qualified_action':False, 'historical_position_limit_exceeded':[False]*7,
            'png_file':f'rgb/{n:06}.png', 'png_sha256':'placeholder'})
    return result


def make_commands(rows):
    image_times=[r['image_source_ns'] for r in rows]
    start=image_times[0]-50_000_000;end=image_times[-1]+50_000_000
    commands=[]
    for t in range(start,end+1,50_000_000):
        index=max(0,bisect.bisect_right(image_times,t)-1)
        commands.append({'source_ns':t,'source_line':len(commands)+1,
                         'candidate_label':rows[index]['experimental_hand_label']})
    return commands


class FakeLeRobot:
    last=None
    @classmethod
    def create(cls, **kwargs):
        cls.last=cls(); cls.last.kwargs=kwargs; cls.last.frames=[]; cls.last.episodes=0; cls.last.finalized=False
        cls.last.episode_stats=[];cls.last.saved_count=0
        kwargs['root'].mkdir()
        return cls.last
    def add_frame(self,frame):
        self.frames.append(frame)
    def save_episode(self):
        frames=self.frames[self.saved_count:]
        data={key:np.stack([f[key] for f in frames]) for key in subject.NUMERICAL_FEATURES}
        self.episode_stats.append(self.writer_module.compute_episode_stats(data,{}))
        self.saved_count=len(self.frames)
        self.episodes+=1
    def finalize(self):
        self.finalized=True
        meta=self.kwargs['root']/'meta';meta.mkdir()
        stats={key:{name:(value.tolist() if isinstance(value,np.ndarray) else value)
                    for name,value in self.episode_stats[0][key].items()}
               for key in subject.NUMERICAL_FEATURES}
        stats['observation.images.camera1']={'unmodified':'image statistics'}
        (meta/'stats.json').write_text(json.dumps(stats))


def fake_episode_stats(data, features):
    result={}
    for key in subject.NUMERICAL_FEATURES:
        width=data[key].shape[1]
        result[key]={'min':np.zeros(width),'max':np.zeros(width),'mean':np.zeros(width),
                     'std':np.ones(width),'count':np.array([len(data[key])]),'q01':np.zeros(width),
                     'q10':np.zeros(width),'q50':np.zeros(width),'q90':np.zeros(width),'q99':np.ones(width)}
    result['image']={'untouched':True}
    return result


def fake_saved_reader(dataset_dir):
    return [(0,i,frame['observation.state'].copy(),frame['action'].copy())
            for i,frame in enumerate(FakeLeRobot.last.frames)]


def fake_episode_reader(dataset_dir):
    return [(i,{key:{name:(value.tolist() if isinstance(value,np.ndarray) else value)
                    for name,value in stats[key].items()} for key in subject.NUMERICAL_FEATURES})
            for i,stats in enumerate(FakeLeRobot.last.episode_stats)]


class CausalResamplingTest(unittest.TestCase):
    def test_preserves_order_and_both_grip_transitions(self):
        rows=make_rows()
        samples=subject.select_causal_samples(rows,make_commands(rows))
        self.assertGreaterEqual(len(samples),3)
        labels=[s['target8'][-1] for s in samples]
        changes=[v for i,v in enumerate(labels) if i==0 or v!=labels[i-1]]
        self.assertEqual(changes,[0,1,0])
        for s in samples:
            self.assertLessEqual(s['image_source_ns'],s['motor_command_source_ns'])
            self.assertLessEqual(s['joint_source_ns'],s['motor_command_source_ns'])
            self.assertLessEqual(s['hand_state_source_ns'],s['motor_command_source_ns'])
            self.assertLessEqual(s['hand_command_source_ns'],s['motor_command_source_ns'])
            self.assertLessEqual(s['motor_command_source_ns'],s['grid_source_ns'])
        self.assertTrue(all(b['grid_source_ns']-a['grid_source_ns']==500_000_000 for a,b in zip(samples,samples[1:])))

    def test_unknown_hand_label_is_rejected_even_if_it_would_be_skipped(self):
        rows=make_rows();rows[5]['experimental_hand_label']=None;rows[5]['experimental_target8']=None
        with self.assertRaisesRegex(ValueError,'unknown'):
            subject.select_causal_samples(rows,make_commands(rows))

    def test_hidden_short_transition_is_rejected(self):
        rows=make_rows()
        for r in rows:
            r['experimental_hand_label']=0;r['experimental_target8'][-1]=0
        rows[5]['experimental_hand_label']=1;rows[5]['experimental_target8'][-1]=1
        with self.assertRaisesRegex(ValueError,'hide a hand-intent transition'):
            subject.select_causal_samples(rows,make_commands(rows))

    def test_timestamp_duplicates_gaps_and_stale_commands_are_rejected(self):
        rows=make_rows();rows[4]['actuator_source_ns']=rows[3]['actuator_source_ns']
        with self.assertRaisesRegex(ValueError,'duplicate'):
            subject.select_causal_samples(rows,make_commands(rows))
        rows=make_rows();rows[4]['image_source_ns']-=200_000_000
        with self.assertRaisesRegex(ValueError,'gap exceeds'):
            subject.select_causal_samples(rows,make_commands(rows))
        rows=make_rows();rows[2]['hand_command_source_ns']=rows[2]['image_source_ns']-90_000_000
        with self.assertRaisesRegex(ValueError,'older than 80 ms'):
            subject.select_causal_samples(rows,make_commands(rows))

    def test_release_between_images_uses_raw_command_not_stale_frame_label(self):
        rows=make_rows();commands=make_commands(rows)
        release=rows[8]['image_source_ns']+5_000_000
        for cmd in commands:
            if cmd['source_ns'] >= release:
                cmd['candidate_label']=0
        commands.append({'source_ns':release,'source_line':999,'candidate_label':0})
        commands.sort(key=lambda x:(x['source_ns'],x['source_line']))
        samples=subject.select_causal_samples(rows,commands)
        selected=next(s for s in samples if s['motor_command_source_ns']==rows[8]['actuator_source_ns'])
        self.assertEqual(rows[8]['experimental_hand_label'],1)
        self.assertEqual(selected['target8'][-1],0)
        self.assertEqual(selected['hand_command_source_ns'],release)
        self.assertEqual(selected['hand_command_source_line'],999)

    def test_raw_missing_stale_and_conflicting_commands_are_unknown(self):
        with self.assertRaisesRegex(ValueError,'UNKNOWN: no prior'):
            subject.raw_intent_at([],[],100)
        stale=[{'source_ns':100,'source_line':1,'candidate_label':0}]
        with self.assertRaisesRegex(ValueError,'older than 80'):
            subject.raw_intent_at(stale,[100],80_000_101)
        ambiguous=[{'source_ns':100,'source_line':1,'candidate_label':0},
                   {'source_ns':100,'source_line':2,'candidate_label':1}]
        with self.assertRaisesRegex(ValueError,'conflicting'):
            subject.raw_intent_at(ambiguous,[100,100],100)


class StableStatsTest(unittest.TestCase):
    def test_float32_difference_of_squares_invents_constant_axis_deviation(self):
        data=np.full((60,1),-0.15,dtype=np.float32)
        old_variance=np.mean(data**2,axis=0)-np.mean(data,axis=0)**2
        self.assertGreater(float(np.sqrt(np.maximum(old_variance,0))[0]),0.0)
        existing={'min':[0],'max':[0],'mean':[0],'std':[1],'count':[60],'q01':[0]}
        stats=subject.stable_feature_stats(data,existing)
        self.assertEqual(float(stats['std'][0]),0.0)

    def test_exact_constant_and_nearly_constant_float32(self):
        data=np.array([[1.234567,1000.0,-0.3125] for _ in range(60)],dtype=np.float32)
        data[-1,1]=np.nextafter(data[-1,1],np.float32(np.inf))
        existing={'min':[0]*3,'max':[0]*3,'mean':[0]*3,'std':[1]*3,'count':[60],
                  'q01':[0]*3,'q99':[0]*3,'extra_metadata':'keep'}
        stats=subject.stable_feature_stats(data,existing)
        self.assertEqual(stats['std'][0],0.0);self.assertEqual(stats['std'][2],0.0)
        reference=data.astype(np.float64).std(axis=0)
        self.assertAlmostEqual(stats['std'][1],reference[1],places=15)
        self.assertEqual(stats['count'].tolist(),[60]);self.assertEqual(stats['extra_metadata'],'keep')
        self.assertEqual(stats['min'][0],float(data[0,0]));self.assertEqual(stats['max'][1],float(data[-1,1]))
        np.testing.assert_allclose(stats['q01'],np.quantile(data.astype(np.float64),0.01,axis=0),rtol=0,atol=0)
        np.testing.assert_allclose(stats['q99'],np.quantile(data.astype(np.float64),0.99,axis=0),rtol=0,atol=0)
        with self.assertRaisesRegex(ValueError,'float32'):
            subject.stable_feature_stats(data.astype(np.float64),existing)

    def test_episode_hook_preserves_other_features_and_restores_vendor_function(self):
        module=types.SimpleNamespace(compute_episode_stats=fake_episode_stats)
        data={'observation.state':np.ones((3,27),dtype=np.float32),
              'action':np.ones((3,8),dtype=np.float32)}
        with subject.stable_episode_stats_hook(module):
            result=module.compute_episode_stats(data,{})
            self.assertEqual(result['image'],{'untouched':True})
            self.assertTrue(np.all(result['action']['std']==0))
        self.assertIs(module.compute_episode_stats,fake_episode_stats)
        with self.assertRaises(ValueError):
            with subject.stable_episode_stats_hook(module):
                bad={'observation.state':np.ones((3,26),dtype=np.float32),'action':data['action']}
                module.compute_episode_stats(bad,{})
        self.assertIs(module.compute_episode_stats,fake_episode_stats)


class ConversionTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); self.bundle=self.root/'candidate'
        segment=self.bundle/'demo';(segment/'rgb').mkdir(parents=True)
        rows=make_rows()
        for r in rows:
            img=segment/r['png_file'];Image.new('RGB',(4,3),(r['source_frame'],0,0)).save(img)
            r['png_sha256']=hashlib.sha256(img.read_bytes()).hexdigest()
        data=segment/'candidate_targets.jsonl';data.write_text(''.join(json.dumps(x)+'\n' for x in rows))
        source=self.root/'capture';source.mkdir();raw=source/'samples.jsonl'
        commands=make_commands(rows)
        raw.write_text(''.join(json.dumps({'kind':'hand_command_right','source_ns':c['source_ns'],
             'message':{'names':subject.RIGHT_HAND,'mode':[5 if c['candidate_label']==0 else 7]*7}})+'\n'
             for c in commands))
        self.source=str(source);state_names=[f'L_{i}_joint' for i in range(13)]+subject.JOINTS
        self.manifest={'schema':'cruzr_ball_candidate_targets_v1','training_ready':False,
            'physical_control_qualified':False,'offline_experiment_only':True,
            'historical_hardware_snapshot_sha256':subject.SNAPSHOT_SHA256,
            'historical_transmissions_sha256':subject.TRANSMISSIONS_SHA256,
            'experimental_target8_order':subject.EXPECTED_ORDER,'state_right_hand_names':subject.RIGHT_HAND,
            'state20_names_by_source':{self.source:state_names},'task':'Pick the tennis ball',
            'limitations':['not qualified'],'segments':[{'id':'demo','source_dir':self.source,
                'status':'candidate_success','split':'inspection_train','start_frame':0,'end_frame':13,
                'candidate_targets_sha256':hashlib.sha256(data.read_bytes()).hexdigest(),
                'source_hashes':{'samples.jsonl':hashlib.sha256(raw.read_bytes()).hexdigest()}}]}
        (self.bundle/'manifest.json').write_text(json.dumps(self.manifest))

    def tearDown(self):
        self.tmp.cleanup()

    def test_requires_explicit_ack_and_uses_fake_local_dataset_only(self):
        out=self.root/'out'
        with self.assertRaisesRegex(ValueError,'explicitly pass'):
            subject.convert(self.bundle,out,False,FakeLeRobot)
        self.assertFalse(out.exists())
        module=types.SimpleNamespace(compute_episode_stats=fake_episode_stats)
        FakeLeRobot.writer_module=module
        m=subject.convert(self.bundle,out,True,FakeLeRobot,module,fake_saved_reader,fake_episode_reader)
        ds=FakeLeRobot.last
        self.assertIs(module.compute_episode_stats,fake_episode_stats)
        self.assertEqual(ds.kwargs['fps'],2);self.assertFalse(ds.kwargs['use_videos'])
        self.assertEqual(ds.kwargs['repo_id'],'local/cruzr-ball-offline-experiment')
        self.assertTrue(ds.finalized);self.assertEqual(ds.episodes,1)
        self.assertEqual(ds.frames[0]['action'].shape,(8,));self.assertEqual(ds.frames[0]['observation.state'].shape,(27,))
        self.assertEqual(ds.frames[0]['observation.images.camera1'].shape,(3,4,3))
        self.assertFalse(m['training_ready']);self.assertFalse(m['physical_control_qualified'])
        self.assertTrue(m['not_authorized_for_hub_upload_or_robot_execution'])
        self.assertEqual(len((out/'source_alignment.jsonl').read_text().splitlines()),len(ds.frames))
        stats=json.loads((out/'lerobot_dataset'/'meta'/'stats.json').read_text())
        self.assertEqual(stats['observation.images.camera1'],{'unmodified':'image statistics'})
        self.assertEqual(stats['observation.state']['count'],[len(ds.frames)])
        self.assertEqual(stats['observation.state']['std'],[0.0]*27)
        self.assertEqual(ds.episode_stats[0]['observation.state']['std'].tolist(),[0.0]*27)
        self.assertTrue((out/'stats_before_global_correction.json').is_file())
        self.assertTrue((out/'statistics_audit.json').is_file())
        audit=json.loads((out/'statistics_audit.json').read_text())
        self.assertTrue(audit['episode_stats_verified_from_saved_parquet'])

    def test_rejects_saved_float32_values_different_from_inputs(self):
        module=types.SimpleNamespace(compute_episode_stats=fake_episode_stats)
        FakeLeRobot.writer_module=module
        def corrupt(dataset_dir):
            rows=fake_saved_reader(dataset_dir)
            state=rows[0][2].copy();state[0]=1.0
            rows[0]=(rows[0][0],rows[0][1],state,rows[0][3])
            return rows
        out=self.root/'out'
        with self.assertRaisesRegex(ValueError,'saved float32 values differ'):
            subject.convert(self.bundle,out,True,FakeLeRobot,module,corrupt,fake_episode_reader)
        self.assertFalse((out/'manifest.json').exists())
        self.assertIs(module.compute_episode_stats,fake_episode_stats)

    def test_rejects_bad_saved_episode_stats(self):
        module=types.SimpleNamespace(compute_episode_stats=fake_episode_stats)
        FakeLeRobot.writer_module=module
        def corrupt(dataset_dir):
            rows=fake_episode_reader(dataset_dir)
            rows[0][1]['observation.state']['std'][0]=0.0001
            return rows
        out=self.root/'out'
        with self.assertRaisesRegex(ValueError,'per-episode std'):
            subject.convert(self.bundle,out,True,FakeLeRobot,module,fake_saved_reader,corrupt)
        self.assertFalse((out/'manifest.json').exists())

    def test_rejects_assisted_and_cross_split_without_creating_output(self):
        self.manifest['segments'][0]['status']='assisted'
        (self.bundle/'manifest.json').write_text(json.dumps(self.manifest))
        with self.assertRaisesRegex(ValueError,'assisted'):
            subject.convert(self.bundle,self.root/'out',True,FakeLeRobot)
        self.assertFalse((self.root/'out').exists())
        self.manifest['segments'][0]['status']='candidate_success'
        self.manifest['segments'].append(dict(self.manifest['segments'][0],id='other',split='inspection_test'))
        (self.bundle/'manifest.json').write_text(json.dumps(self.manifest))
        with self.assertRaisesRegex(ValueError,'multiple splits'):
            subject.convert(self.bundle,self.root/'out',True,FakeLeRobot)

    def test_rejects_changed_or_missing_original_raw_command_source(self):
        raw=Path(self.source)/'samples.jsonl'
        raw.write_text(raw.read_text()+'{}\n')
        with self.assertRaisesRegex(ValueError,'source SHA256 mismatch'):
            subject.convert(self.bundle,self.root/'out',True,FakeLeRobot)
        self.assertFalse((self.root/'out').exists())
        raw.unlink()
        with self.assertRaises(FileNotFoundError):
            subject.convert(self.bundle,self.root/'out',True,FakeLeRobot)
        self.assertFalse((self.root/'out').exists())

    def test_output_must_not_overlap_original_capture(self):
        out=Path(self.source)/'unsafe_child'
        with self.assertRaisesRegex(ValueError,'overlap an original capture'):
            subject.convert(self.bundle,out,True,FakeLeRobot)
        self.assertFalse(out.exists())
        self.assertTrue((Path(self.source)/'samples.jsonl').is_file())

    def test_recording_order_regression_or_conflicting_duplicates_rejected(self):
        raw=Path(self.source)/'samples.jsonl'
        def row(stamp,mode):
            return {'kind':'hand_command_right','source_ns':stamp,
                    'message':{'names':subject.RIGHT_HAND,'mode':[mode]*7}}
        def run(rows):
            raw.write_text(''.join(json.dumps(x)+'\n' for x in rows))
            return subject.read_raw_hand_commands(Path(self.source),hashlib.sha256(raw.read_bytes()).hexdigest())
        with self.assertRaisesRegex(ValueError,'regressed in recording order'):
            run([row(200,5),row(100,5)])
        with self.assertRaisesRegex(ValueError,'conflicting simultaneous'):
            run([row(100,5),row(100,7)])
        same=run([row(100,5),row(100,5)])
        self.assertEqual(len(same),2)
        self.assertEqual(subject.raw_intent_at(same,[100,100],100)['source_line'],2)


if __name__ == '__main__':
    unittest.main()
