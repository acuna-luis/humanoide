import unittest
from clamp_work_model import fixed_component

class AttachmentTests(unittest.TestCase):
    def test_does_not_cross_moving_wrist(self):
        joints=[dict(parent='pitch',child='roll',type='revolute'),
                dict(parent='roll',child='sensor',type='fixed'),
                dict(parent='sensor',child='tool',type='fixed')]
        self.assertEqual(fixed_component(joints,'sensor'),['roll','sensor','tool'])
    def test_fixed_link_names_do_not_define_scope(self):
        joints=[dict(parent='a',child='b',type='fixed'),dict(parent='b',child='c',type='prismatic')]
        self.assertEqual(fixed_component(joints,'a'),['a','b'])
        with self.assertRaises(ValueError):fixed_component(joints,'unknown')

if __name__=='__main__':unittest.main()
