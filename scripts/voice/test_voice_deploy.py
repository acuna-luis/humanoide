import hashlib,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from deploy_voice_assets import HELPER
class DeployTests(unittest.TestCase):
 def test_restore_and_conflict(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);(r/'payload').mkdir();f=r/'target';f.write_bytes(b'original');(r/'payload/k').write_bytes(b'new');(r/'helper.py').write_text(HELPER)
   row={'container':'test','target':str(f),'before_sha256':hashlib.sha256(b'original').hexdigest(),'after_sha256':hashlib.sha256(b'new').hexdigest(),'payload':'k','metadata':{'mode':0o644,'uid':os.getuid(),'gid':os.getgid()}}
   (r/'plan.json').write_text(json.dumps([row]))
   def run(mode):return subprocess.run([sys.executable,str(r/'helper.py'),str(r),'test',mode],capture_output=True)
   self.assertEqual(run('check').returncode,0);self.assertEqual(run('apply').returncode,0)
   f.write_bytes(b'other change');self.assertNotEqual(run('rollback').returncode,0);self.assertEqual(f.read_bytes(),b'other change')
   f.write_bytes(b'new');self.assertEqual(run('rollback').returncode,0);self.assertEqual(f.read_bytes(),b'original')
if __name__=='__main__':unittest.main()
