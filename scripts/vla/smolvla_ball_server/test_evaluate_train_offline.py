#!/usr/bin/env python3
"""Synthetic evaluation-contract tests; no GPU, robot or network."""
import json
import math
from pathlib import Path
import tempfile
import unittest

import evaluate_train_offline as subject


class EvaluationTests(unittest.TestCase):
    def test_prediction_whitelist_excludes_target_and_future(self):
        row={'observation.images.camera1':'rgb','observation.state':'state','task':'pick',
             'action':'SECRET_TARGET','action_is_pad':'PAD','future_actions':'FUTURE','index':10}
        self.assertEqual(subject.prediction_input(row),{
            'observation.images.camera1':'rgb','observation.state':'state','task':'pick'})
        with self.assertRaisesRegex(ValueError,'Missing'):
            subject.prediction_input({'action':'only'})

    def test_prediction_guard_allows_none_and_rejects_real_target(self):
        self.assertEqual(subject.guard_prediction_batch({'observation.state':'s','action':None}),
                         {'observation.state':'s'})
        with self.assertRaisesRegex(ValueError,'leaked'):
            subject.guard_prediction_batch({'action':'target'})
        with self.assertRaisesRegex(ValueError,'leaked'):
            subject.guard_prediction_batch({'action_is_pad':'padding'})

    def test_loss_input_batches_chunk_and_mask_only_after_prediction(self):
        class FakeTensor:
            def __init__(self,name): self.name=name
            def unsqueeze(self,dim): return (self.name,dim)
        row={'observation.images.camera1':'rgb','observation.state':'state','task':'pick',
             'action':FakeTensor('chunk'),'action_is_pad':FakeTensor('mask'),'future_actions':'ignored'}
        loss=subject.loss_input(row)
        self.assertEqual(loss['action'],('chunk',0))
        self.assertEqual(loss['action_is_pad'],('mask',0))
        self.assertNotIn('future_actions',loss)

    def test_metrics_computes_error_ranges_and_grasp_confusion(self):
        records=[
            {'prediction':[1.0]*7+[0.6], 'target':[0.0]*7+[0.0],
             'flow_matching_loss':1.0,'prediction_seconds':2.0},
            {'prediction':[0.0]*7+[0.4], 'target':[0.0]*7+[1.0],
             'flow_matching_loss':3.0,'prediction_seconds':4.0}]
        result=subject.metrics(records,[f'j{i}' for i in range(7)]+['grasp'])
        self.assertEqual(result['samples'],2)
        self.assertEqual(result['arm_mae_rad'],0.5)
        self.assertAlmostEqual(result['per_joint'][0]['rmse_rad'],math.sqrt(0.5))
        self.assertEqual(result['grasp']['accuracy_vs_provisional_labels'],0.0)
        self.assertEqual(result['grasp']['false_close_count'],1)
        self.assertEqual(result['grasp']['false_open_count'],1)
        self.assertEqual(result['prediction_seconds']['median'],3.0)
        self.assertEqual(result['stochastic_flow_matching_loss']['mean'],2.0)

    def test_metrics_reject_nonfinite_unknown_and_invalid_labels(self):
        row={'prediction':[0.0]*8,'target':[0.0]*8,'flow_matching_loss':0.2,'prediction_seconds':0.3}
        names=[str(i) for i in range(8)]
        bad=dict(row,prediction=[float('nan')]*8)
        with self.assertRaisesRegex(ValueError,'prediction'):
            subject.metrics([bad],names)
        bad=dict(row,target=[0.0]*7+[2.0])
        with self.assertRaisesRegex(ValueError,'grasp'):
            subject.metrics([bad],names)
        bad=dict(row,flow_matching_loss=float('nan'))
        with self.assertRaisesRegex(ValueError,'loss'):
            subject.metrics([bad],names)

    def test_checkpoint_schema_and_local_tokenizer(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);checkpoint=p/'checkpoint';checkpoint.mkdir();vlm=p/'vlm';vlm.mkdir()
            config={'type':'smolvla','push_to_hub':False,'chunk_size':8,'n_action_steps':8,
                'vlm_model_name':str(vlm),'input_features':{'observation.state':{'shape':[27]},
                'observation.images.camera1':{'shape':[3,576,960]}},'output_features':{'action':{'shape':[8]}}}
            pre={'steps':[{'registry_name':'tokenizer_processor','config':{'tokenizer_name':str(vlm)}}]}
            (checkpoint/'config.json').write_text(json.dumps(config))
            (checkpoint/'policy_preprocessor.json').write_text(json.dumps(pre))
            (checkpoint/'model.safetensors').write_bytes(b'fake')
            self.assertEqual(subject.validate_checkpoint(checkpoint,vlm)['chunk_size'],8)
            config['input_features']['observation.state']['shape']=[6]
            (checkpoint/'config.json').write_text(json.dumps(config))
            with self.assertRaisesRegex(ValueError,'schema'):
                subject.validate_checkpoint(checkpoint,vlm)


if __name__=='__main__':
    unittest.main()
