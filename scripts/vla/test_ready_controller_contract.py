import copy
import hashlib
import unittest

import yaml
from audit_ready_controller_contract import configuration_checks, compiled_fields


class ControllerContractTests(unittest.TestCase):
    def example(self):
        def record(data):
            text=yaml.safe_dump(data)
            return dict(text=text,sha256=hashlib.sha256(text.encode()).hexdigest())
        snapshot={
            '/cruzr_s2_v1_mc_config/config/controllers_config.yaml':record({
                'head_controller':dict(joints=['head_yaw_joint','head_pitch_joint'],controller_dof=2)}),
            '/ecat_hardware/transmissions.yaml':record({'transmissions':{
                n:dict(joint=dict(name=n,limit=dict(lower=-.65,upper=.5)))
                for n in ['head_yaw_joint','head_pitch_joint']}})}
        review=dict(joint_order=['head_yaw_joint','head_pitch_joint'], stages=[dict(
            type='head',location='single',joint_names=['head_yaw_joint','head_pitch_joint'],
            start_20d_rad=[0.,-.43],end_20d_rad=[0.,-.651])])
        return review,snapshot

    def test_small_nominal_limit_violation_is_reported(self):
        review,snapshot=self.example()
        result=configuration_checks(review,snapshot)
        self.assertTrue(result['configured_group_order_matches'])
        self.assertEqual(result['hardware_nominal_outside'],['head_pitch_joint'])

    def test_changed_order_and_corrupt_snapshot_rejected(self):
        review,snapshot=self.example()
        review['stages'][0]['joint_names'].reverse()
        self.assertFalse(configuration_checks(review,snapshot)['configured_group_order_matches'])
        damaged=copy.deepcopy(snapshot)
        next(iter(damaged.values()))['text']+='\n'
        with self.assertRaises(ValueError):configuration_checks(review,damaged)

    def test_unreviewed_binary_does_not_inherit_field_labels(self):
        with self.assertRaises(ValueError):compiled_fields(b'unreviewed',b'unreviewed')


if __name__=='__main__':unittest.main()
