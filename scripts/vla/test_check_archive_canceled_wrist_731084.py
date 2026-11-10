"""Test read-only transport bootstrap locally; never contacts Motion."""
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0,str(Path(__file__).parent))
import check_archive_canceled_wrist_731084 as m

class BootstrapTests(unittest.TestCase):
    def test_bootstrap_verifies_and_cleans_temp_with_check_only(self):
        source = b'''import json\ndef main(args):\n assert args[0]=='--check' and len(args)==3\n print(json.dumps({'status':'CHECKED_NO_CHANGES','movement_commands':0,'physical_stop_verified':False}))\n return 0\n'''
        evidence=b'historical'
        code=m.BOOTSTRAP.replace(m.SOURCE_SHA,hashlib.sha256(source).hexdigest()).replace(m.EVIDENCE_SHA,hashlib.sha256(evidence).hexdigest())
        payload=json.dumps({'source':base64.b64encode(source).decode(),'evidence':base64.b64encode(evidence).decode()})+'\n'
        p=subprocess.run([sys.executable,'-B','-c',code],input=payload,text=True,capture_output=True,timeout=5)
        self.assertEqual(p.returncode,0,p.stderr)
        receipt=json.loads(p.stdout)
        self.assertTrue(receipt['temporary_dir_removed'])
        self.assertFalse(receipt['archive_requested'])
        self.assertEqual(receipt['movement_commands'],0)
        self.assertEqual(json.loads(receipt['checker_stdout'])['status'],'CHECKED_NO_CHANGES')

    def test_unmatched_source_fails_before_execution(self):
        payload=json.dumps({'source':base64.b64encode(b'bad source').decode(),
                            'evidence':base64.b64encode(b'bad evidence').decode()})+'\n'
        p=subprocess.run([sys.executable,'-B','-c',m.BOOTSTRAP],input=payload,text=True,capture_output=True,timeout=5)
        self.assertNotEqual(p.returncode,0)
        self.assertIn('source_sha_mismatch',p.stderr)

if __name__=='__main__':unittest.main()
