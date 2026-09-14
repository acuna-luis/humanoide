import unittest
import numpy as np
from prepare_vla_entry_bundle import ROOT,common,JOINT_ORDER
from entry_relative_kinematics import RelativeChain


class RelativeKinematicsTests(unittest.TestCase):
    def test_full_model_random_states_and_both_branch_directions(self):
        joints=common.model_joints(ROOT/'cruzr_s2_description_splint/cruzr_s2_description/urdf/cruzr_s2_v1/cruzr_s2_v1.urdf')
        pairs=[('lifter_pitch_2_link','torso_link'),('torso_link','lifter_pitch_2_link'),
               ('L_wrist_roll_link','R_wrist_pitch_link'),('base_link','head_pitch_link')]
        rng=np.random.default_rng(14952)
        for _ in range(32):
            state=dict(zip(JOINT_ORDER,rng.uniform(-1,1,20)))
            poses=common.fk.forward_kinematics(joints,state)
            for a,b in pairs:
                expected=np.linalg.inv(poses[a])@poses[b]
                np.testing.assert_allclose(RelativeChain(joints,a,b,common.fk).evaluate(state),
                                           expected,rtol=0,atol=2e-14)


if __name__=='__main__':unittest.main()
