"""Offline tests only. No ROS, network, or robot commands."""
import copy
import json
from pathlib import Path
import unittest
import yaml

import pico_wrist_model_decision as m
import prepare_pico_wrist_native_probe as probe

BOOT='12345678-1234-4567-8234-123456789abc'
OTHER_BOOT='12345678-1234-4567-8234-123456789abd'
GOAL='2e20ea8d-34d9-4e4d-9192-e5e0c11e921d'


def case():
    names=list(reversed(probe.BODY)); pos=[probe.BODY[n] for n in names]
    msg={'name':names,'position':pos,'velocity':[0.0]*20}
    urdf='<robot>'+''.join('<joint name="%s" type="revolute"><limit lower="-3" upper="3" velocity="1"/></joint>'%n for n in probe.ARM)+'</robot>'
    transmission={'transmissions':{n:{'joint':{'name':n,'limit':{'lower':-3.0,'upper':3.0}}} for n in probe.BODY}}
    manifest=probe.prepare(msg,urdf,yaml.safe_dump(transmission))
    action=[probe.BODY[n] for n in probe.ARM];action[-1]+=.1; action.append(.7)
    diffs=[action[i]-probe.BODY[n] for i,n in enumerate(probe.ARM)]
    rows=[{'event':'model_ready','model_sha256':m.MODEL_SHA256,'physical_control_qualified':False,'movement_commands':0},
          {'event':'prediction','index':0,'image_source_ns':123,'image_sha256':'a'*64,
           'physical_control_qualified':False,'prediction':action,'proposed_minus_observed_rad':diffs,
           'paired_state20':{'names':names,'positions':pos,'velocities':[0.0]*20,'received_monotonic_ns':1000},
           'prediction_received_monotonic_ns':1100},
          {'event':'done','samples':1,'physical_control_qualified':False},
          {'event':'summary','predictions':1,'observations_sent':1,'observations_dropped':3,'movement_commands':0}]
    return rows,manifest

class DecisionTests(unittest.TestCase):
    def decision(self,rows=None,manifest=None):
        realrows,realmanifest=case()
        return m.decision_from_stream(rows if rows is not None else realrows,
                    manifest if manifest is not None else realmanifest,now_ns=1200,boot_id=BOOT)

    def permit(self,decision,**overrides):
        args={'boot_id':BOOT,'now_ns':1300,'max_state_age_ns':500,'max_prediction_age_ns':400}
        args.update(overrides)
        return m.make_dispatch_permission(decision,GOAL,decision['task_sha256'],**args)

    def test_positive_and_actual_jsonl_complete(self):
        rows,manifest=case()
        raw=''.join(json.dumps(r)+'\n' for r in rows).encode()
        decision=self.decision(raw,manifest)
        self.assertEqual(decision['image_sha256'],'a'*64)
        self.assertEqual(decision['model_action_original'],rows[1]['prediction'])
        self.assertFalse(decision['physical_control_qualified'])
        permit=self.permit(decision)
        self.assertEqual(permit,{'goal_id':GOAL,'task_sha256':decision['task_sha256'],
                                 'decision_sha256':decision['decision_sha256'],'budget_ns':200})
        self.assertIsNone(m.make_dispatch_permission(None,GOAL,decision['task_sha256'],boot_id=BOOT,now_ns=1300,max_state_age_ns=500,max_prediction_age_ns=400))

    def test_wrong_or_insufficient_direction_rejected(self):
        for delta in (-.01,0,.005):
            rows,manifest=case(); initial=manifest['input']['reference_20d'][probe.ARM_AXIS]
            rows[1]['prediction'][6]=initial+delta;rows[1]['proposed_minus_observed_rad'][6]=delta
            with self.assertRaisesRegex(ValueError,'not_within_model_proposal'): self.decision(rows,manifest)

    def test_observed_position_changes_no_amplification_or_reverse(self):
        rows,manifest=case();i=rows[1]['paired_state20']['names'].index(probe.ARM_AXIS)
        # q drift within 0.002, but proposed target is below fixed target.
        rows[1]['paired_state20']['positions'][i]+=.001
        q=rows[1]['paired_state20']['positions'][i]
        rows[1]['prediction'][6]=q+.008
        rows[1]['proposed_minus_observed_rad'][6]=.008
        with self.assertRaisesRegex(ValueError,'not_within_model_proposal'): self.decision(rows,manifest)

    def test_reference_difference_and_moving_rejected(self):
        rows,manifest=case();rows[1]['paired_state20']['positions'][0]+=.003
        with self.assertRaisesRegex(ValueError,'reference_mismatch'): self.decision(rows,manifest)
        rows,manifest=case();rows[1]['paired_state20']['velocities'][0]=.002
        with self.assertRaisesRegex(ValueError,'not_stationary'): self.decision(rows,manifest)

    def test_missing_or_extra_state_name_and_nonfinite_rejected(self):
        rows,manifest=case();rows[1]['paired_state20']['names'][0]='alien'
        with self.assertRaises(ValueError): self.decision(rows,manifest)
        rows,manifest=case();rows[1]['paired_state20']['positions'][0]=float('nan')
        with self.assertRaises(ValueError): self.decision(rows,manifest)

    def test_prediction_deltas_must_match_state(self):
        rows,manifest=case();rows[1]['proposed_minus_observed_rad'][0]+=.02
        with self.assertRaisesRegex(ValueError,'model_delta_state_mismatch'): self.decision(rows,manifest)

    def test_model_image_and_lifecycle_rejected(self):
        rows,manifest=case();rows[0]['model_sha256']='b'*64
        with self.assertRaisesRegex(ValueError,'checkpoint'):self.decision(rows,manifest)
        rows,manifest=case();rows[1]['image_sha256']='invalid'
        with self.assertRaisesRegex(ValueError,'identity_invalid'):self.decision(rows,manifest)
        rows,manifest=case();rows[2]['samples']=2
        with self.assertRaisesRegex(ValueError,'completion'):self.decision(rows,manifest)
        rows,manifest=case()
        for partial in (rows[:2],rows[:3],rows+[rows[-1]]):
            with self.assertRaisesRegex(ValueError,'wrong_record_count'): self.decision(partial,manifest)
        with self.assertRaisesRegex(ValueError,'truncated'):self.decision(json.dumps(rows[0]),manifest)

    def test_manifest_xml_hash_and_fixed_probe_rejected(self):
        rows,manifest=case();manifest['candidate']['xml']+=' '
        with self.assertRaisesRegex(ValueError,'candidate_identity'):self.decision(rows,manifest)
        rows,manifest=case();manifest['candidate']['target_rad'][0]+=.01
        with self.assertRaisesRegex(ValueError,'not_fixed'):self.decision(rows,manifest)

    def test_rehashed_extra_action_still_fails_xml_shape(self):
        import hashlib
        rows,manifest=case();c=manifest['candidate']
        c['xml']=c['xml'].replace('</Sequence>', '<Action ID="MetaMove" type="arm" location="right" joint_angles="0;0;0;0;0;0;0" duration="4" /></Sequence>')
        c['xml_sha256']=hashlib.sha256(c['xml'].encode()).hexdigest()
        with self.assertRaisesRegex(ValueError,'candidate_xml_structure'): self.decision(rows,manifest)

    def test_rehashed_reverse_model_still_fails_semantics(self):
        d=self.decision(); ref=d['reference_20d'][probe.ARM_AXIS]
        d['model_action_original'][6]=ref-.01
        d['model_arm_deltas_rad'][6]=-.01
        body=dict(d);body.pop('decision_sha256')
        d['decision_sha256']=m._decision_hash(body)
        with self.assertRaisesRegex(ValueError,'not_within_model_proposal'): self.permit(d)

    def test_expired_future_and_mismatched_boot_or_task(self):
        d=self.decision()
        with self.assertRaisesRegex(ValueError,'expired'):self.permit(d,now_ns=1500)
        with self.assertRaisesRegex(ValueError,'future'):self.permit(d,now_ns=1199)
        with self.assertRaisesRegex(ValueError,'boot_or_task'):self.permit(d,boot_id=OTHER_BOOT)
        with self.assertRaisesRegex(ValueError,'boot_or_task'):
            m.make_dispatch_permission(d,GOAL,'f'*64,boot_id=BOOT,now_ns=1300,max_state_age_ns=500,max_prediction_age_ns=400)
        for n in (0,-1,m.MAX_AGE_NS+1):
            with self.assertRaisesRegex(ValueError,'inputs_invalid'):self.permit(d,max_state_age_ns=n)

    def test_hash_detects_mutation_and_copies_inputs(self):
        rows,manifest=case();d=self.decision(rows,manifest)
        rows[1]['prediction'][6]=100;manifest['candidate']['target_rad'][6]=100
        self.assertNotEqual(d['model_action_original'][6],100)
        self.assertNotEqual(d['target_rad'][6],100)
        d['model_action_original'][6]=100
        with self.assertRaisesRegex(ValueError,'hash_mismatch'):self.permit(d)

if __name__=='__main__':unittest.main()
