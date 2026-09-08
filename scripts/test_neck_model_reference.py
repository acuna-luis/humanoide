import unittest
import xml.etree.ElementTree as ET
import numpy as np
from audit_neck_model_reference import analytic_neck, check_chain, URDF, ARCHIVE, fk


class NeckReferenceTests(unittest.TestCase):
    def test_independent_chain(self):
        check_chain(ET.parse(URDF).getroot())
        joints, _, _ = fk.load_robot(URDF,ARCHIVE)
        for yaw,pitch in [(0,0),(.2,-.65),(-1,.3),(1,-.7)]:
            poses = fk.forward_kinematics(joints,dict(head_yaw_joint=yaw,head_pitch_joint=pitch))
            relative = np.linalg.inv(poses['torso_link']) @ poses['head_pitch_link']
            np.testing.assert_allclose(relative,analytic_neck(yaw,pitch),atol=1e-12)

    def test_reject_changed_origin(self):
        root = ET.parse(URDF).getroot()
        root.find("joint[@name='head_pitch_joint']/origin").set('xyz','0 0 0.05')
        with self.assertRaises(ValueError):
            check_chain(root)

    def test_reject_nonfinite(self):
        for angles in [(float('nan'),0),(0,float('inf'))]:
            with self.assertRaises(ValueError):
                analytic_neck(*angles)


if __name__ == '__main__':
    unittest.main()
