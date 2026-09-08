import unittest
from audit_ready_entry_resume import named_state, targets, relative_movers, RUNTIME


class ResumeTests(unittest.TestCase):
    def test_missing_duplicate_and_nonfinite_state_rejected(self):
        for message in [dict(name=['a', 'a'], position=[0., 0.], velocity=[0., 0.]),
                        dict(name=['b'], position=[0.], velocity=[0.]),
                        dict(name=['a'], position=[float('nan')], velocity=[0.]),
                        dict(name=['a'], position=[False], velocity=[0.])]:
            with self.assertRaises(ValueError):
                named_state(message, ['a'])

    def test_moving_state_rejected(self):
        with self.assertRaises(ValueError):
            named_state(dict(name=['a'], position=[0.], velocity=[.1]), ['a'])

    def test_body_xml_rejects_arm_command_and_bad_duration(self):
        xml = (RUNTIME / 'tasks/s2_vla_e6_1c_ready_to_entry_preview.xml').read_text()
        self.assertEqual(len(targets(xml)), 6)
        for tampered in (xml.replace('type="head"', 'type="arm"'),
                         xml.replace('duration="12.0"', 'duration="1.0"'),
                         xml.replace('type="waist"', 'type="head"')):
            with self.assertRaises(ValueError):
                targets(tampered)

    def test_shared_ancestor_motion_cancels_but_branch_does_not(self):
        parents = {'torso': ('base', 'lifter'), 'arm': ('torso', 'shoulder'),
                   'sensor': ('arm', 'wrist'), 'head': ('torso', 'neck')}
        self.assertEqual(relative_movers('sensor', 'torso', parents, {'lifter', 'neck'}), [])
        self.assertEqual(relative_movers('sensor', 'head', parents, {'lifter', 'neck'}), ['neck'])
        self.assertEqual(relative_movers('sensor', 'base', parents, {'lifter'}), ['lifter'])
        self.assertEqual(relative_movers('sensor', 'arm', parents, {'wrist'}), ['wrist'])

    def test_disconnected_and_cyclic_tree_rejected(self):
        with self.assertRaises(ValueError):
            relative_movers('a', 'b', {}, set())
        with self.assertRaises(ValueError):
            relative_movers('a', 'b', {'a': ('a', 'j')}, {'j'})

    def test_urdf_forward_kinematics_preserves_arm_torso_but_changes_base(self):
        import json
        import numpy as np
        from audit_clamp_pessimistic_screen import fk, URDF, ARCHIVE
        contract = json.loads((RUNTIME / 'cruzr_s2_vla_ready_entry_transition_e6_1c.json').read_text())
        joints, _, _ = fk.load_robot(URDF, ARCHIVE)
        zero = {j['name']: 0. for j in joints if j['type'] != 'fixed'}
        states = [{**zero, **dict(zip(contract['joint_order'], contract[key], strict=True))}
                  for key in ('observed_ready_reference_20d_rad', 'entry_target_20d_rad')]
        poses = [fk.forward_kinematics(joints, q) for q in states]
        for side in ('L', 'R'):
            for other in ('torso_link', side+'_wrist_pitch_link'):
                relative = [np.linalg.inv(p[other]) @ p[side+'_sixforce_link'] for p in poses]
                self.assertTrue(np.allclose(*relative, atol=1e-12, rtol=0))
            self.assertFalse(np.allclose(poses[0][side+'_sixforce_link'],
                                         poses[1][side+'_sixforce_link']))


if __name__ == '__main__':
    unittest.main()
