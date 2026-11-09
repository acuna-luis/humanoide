import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from evaluate_failed_offline import validate_test, verify_hashes


class TestFailedObservations(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        (self.root/'frame.png').write_bytes(b'illustrative-image')
        self.row={'status':'failed','state27':[0]*27,'joint_source_ns':10,'hand_source_ns':11,
            'image_source_ns':12,'image':'frame.png',
            'image_sha256':hashlib.sha256(b'illustrative-image').hexdigest()}
        self.test={'schema':'cruzr_ball_failed_observations_v1','training_ready':False,
            'physical_control_qualified':False,'has_action_column':False,'state_names':[str(i) for i in range(27)],
            'task':'task','source_capture_hashes':{'samples.jsonl':'TEST'},'records':[self.row]}
        self.train={'state_names':self.test['state_names'],'task':'task',
                    'segments':[{'source_samples_sha256':'TRAIN'}]}

    def tearDown(self): self.tmp.cleanup()
    def write(self): (self.root/'manifest.json').write_text(json.dumps(self.test))
    def test_distinct_failed_capture_accepted(self):
        self.write(); self.assertEqual(validate_test(self.root,self.train)['records'][0]['status'],'failed')
    def test_reject_same_capture_as_training(self):
        self.train['segments'][0]['source_samples_sha256']='TEST'; self.write()
        with self.assertRaises(ValueError): validate_test(self.root,self.train)
    def test_reject_success_or_future_state(self):
        self.row['status']='candidate_success'; self.write()
        with self.assertRaises(ValueError): validate_test(self.root,self.train)
        self.row['status']='failed';self.row['hand_source_ns']=12-80_000_001;self.write()
        with self.assertRaises(ValueError): validate_test(self.root,self.train)
        self.row['status']='failed';self.row['hand_source_ns']=13;self.write()
        with self.assertRaises(ValueError): validate_test(self.root,self.train)
    def test_reject_changed_image(self):
        self.write(); (self.root/'frame.png').write_bytes(b'changed')
        with self.assertRaises(ValueError): validate_test(self.root,self.train)
    def test_current_is_unreviewed_and_distinct_from_failed(self):
        self.test['schema']='cruzr_ball_current_observations_v1'
        self.row['status']='unreviewed';self.write()
        self.assertEqual(validate_test(self.root,self.train,'current')['records'][0]['status'],'unreviewed')
        with self.assertRaises(ValueError): validate_test(self.root,self.train,'failed')
        self.row['status']='failed';self.write()
        with self.assertRaises(ValueError): validate_test(self.root,self.train,'current')
    def test_model_tokenizer_pins_reject_modified_content(self):
        expected={'frame.png':hashlib.sha256(b'illustrative-image').hexdigest()}
        verify_hashes(self.root,expected)
        (self.root/'frame.png').write_bytes(b'modified')
        with self.assertRaises(ValueError): verify_hashes(self.root,expected)


if __name__=='__main__': unittest.main()
