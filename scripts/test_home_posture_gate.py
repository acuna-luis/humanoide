#!/usr/bin/env python3
"""Malformed telemetry must never become an implicit zero/HOME."""
import copy
import unittest
from lib.cruzr_home_posture_gate import BODY_ACTUATOR_ALIASES, classify


class HomePostureTests(unittest.TestCase):
    def sample(self):
        return {'act_item': [dict(id=ids[0], position=0., velocity=0., cmd_pos=0.,
                                 status=7,error_code=0) for _,ids in BODY_ACTUATOR_ALIASES]}

    def test_valid_and_nonhome(self):
        sample = self.sample()
        self.assertIn('MEASURED_HOME=1',classify(sample,.02))
        self.assertIn('PHYSICAL_AUTHORIZED=0',classify(sample,.02))
        sample['act_item'][0].update(position=.1,cmd_pos=.1)
        self.assertIn('MEASURED_HOME=0',classify(sample,.02))

    def test_every_required_field_missing_rejected(self):
        for key in ('id','position','velocity','cmd_pos','error_code','status'):
            with self.subTest(key=key):
                sample = self.sample()
                del sample['act_item'][0][key]
                with self.assertRaises(ValueError): classify(sample,.02)

    def test_invalid_numeric_and_integer_types(self):
        for key in ('position','velocity','cmd_pos'):
            for value in (True,None,'0',float('nan'),float('inf')):
                with self.subTest(key=key,value=value):
                    sample = self.sample()
                    sample['act_item'][0][key] = value
                    with self.assertRaises(ValueError): classify(sample,.02)
        for key in ('id','status','error_code'):
            for value in (True,None,'7',7.1,-1):
                sample = self.sample()
                sample['act_item'][0][key] = value
                with self.assertRaises(ValueError): classify(sample,.02)

    def test_motion_fault_and_latent_command_rejected(self):
        for key,value in (('velocity',.021),('cmd_pos',.011),('error_code',1),('status',15),('status',0)):
            sample = self.sample()
            sample['act_item'][0][key] = value
            with self.assertRaises(ValueError): classify(sample,.02)

    def test_missing_duplicate_and_bad_tolerance(self):
        sample = self.sample()
        sample['act_item'].pop()
        with self.assertRaises(ValueError): classify(sample,.02)
        sample = self.sample()
        sample['act_item'].append(copy.deepcopy(sample['act_item'][0]))
        with self.assertRaises(ValueError): classify(sample,.02)
        for value in (True,0,-1,float('inf'),float('nan'),.1):
            with self.assertRaises(ValueError): classify(self.sample(),value)


if __name__ == '__main__':
    unittest.main()
