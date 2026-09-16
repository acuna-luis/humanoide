import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cruzr_install_internal_home_body_first as installer


class InstallTests(unittest.TestCase):
    def test_preflight_rejects_bad_safety_and_build(self):
        def fake(host, cmd):
            if cmd[:2] == ['docker','ps']: value=installer.CONTAINER+'\nwalker-ros.ros2-1\n'
            elif cmd[-1] == installer.TARGET: value=installer.BASE_SHA+'  home.xml\n'
            elif cmd[-1] == installer.META_LIB: value=installer.META_SHA+'  meta.so\n'
            elif 'inspect' in cmd: value='2026-09-10T00:00:00Z\n'
            else:
                value='data: '+('1' if '/emb/estop_key_state ' in cmd[-1] else '0')+'\n---\n'
            return {'returncode':0,'stdout':value,'stderr':''}
        with tempfile.TemporaryDirectory() as d:
            with patch.object(installer,'execute',side_effect=fake):
                self.assertEqual(installer.status(Path(d)), installer.BASE_SHA)
            for match,stdout,rc in [('/emb/estop_key_state','data: 0\n---\n',0),
                                    ('/emb/chrg_input_status','data: 1\n---\n',0),
                                    (installer.META_LIB,'unknown  meta.so\n',0),
                                    (installer.TARGET,'unknown  home.xml\n',0),
                                    ('/emb/estop_key_state','',124)]:
                def bad(host,cmd):
                    if match in ' '.join(cmd): return {'returncode':rc,'stdout':stdout,'stderr':''}
                    return fake(host,cmd)
                with patch.object(installer,'execute',side_effect=bad):
                    with self.assertRaises(RuntimeError): installer.status(Path(d))

    def test_atomic_install_preserves_backup_and_rejects_conflict(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); target=root/'home.xml'; original=b'<old/>\n'; new=b'<new/>\n'
            target.write_bytes(original); target.chmod(0o640)
            code=installer.INSTALL.replace('/etc/walker/trajectory-overlays',str(root/'backups'))
            cmd=[sys.executable,'-c',code,str(target),hashlib.sha256(original).hexdigest(),
                 hashlib.sha256(new).hexdigest(),base64.b64encode(new).decode()]
            result=subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(target.read_bytes(),new)
            self.assertEqual(target.stat().st_mode & 0o777,0o640)
            backup=Path(json.loads(result.stdout)['backup'])
            self.assertEqual((backup/'home.before.xml').read_bytes(),original)
            # A stale preflight must never overwrite a concurrent change.
            target.write_bytes(b'other change')
            result=subprocess.run(cmd,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertEqual(target.read_bytes(),b'other change')
            self.assertEqual(len(list((root/'backups').iterdir())),1)

    def test_six_second_install_rejected_before_connection(self):
        result=subprocess.run([sys.executable,installer.__file__,'--install','--seconds','6'],capture_output=True,text=True)
        self.assertEqual(result.returncode,2)
        self.assertNotIn('EVIDENCE=',result.stdout)


class BodyFirstTests(unittest.TestCase):
    def test_order_and_preservation_of_arm_commands(self):
        import xml.etree.ElementTree as ET
        import cruzr_internal_home_body_first as model
        import cruzr_internal_home_open_path as old
        new = ET.fromstring(model.xml_bytes()).find('.//Sequence')
        original = old.xml_tree(20).find('.//Sequence')
        self.assertEqual([a.get('type') for a in new[0]], ['head','lifter','waist'])
        self.assertTrue(all(float(v)==0 for a in new[0] for v in a.get('joint_angles').split(';')))
        for a,b in zip(list(new)[1:], [original[0],original[1],original[3]]):
            self.assertEqual([n.attrib for n in a], [n.attrib for n in b])
        self.assertEqual(sum(float(s[0].get('duration')) for s in new),20)
        self.assertEqual(hashlib.sha256(model.xml_bytes()).hexdigest(),installer.NEW_SHA)
        self.assertEqual(installer.XML.read_bytes(),model.xml_bytes())
        model.validate_xml(model.xml_bytes())
        with self.assertRaises(ValueError): model.validate_xml(old.xml_bytes())

if __name__ == '__main__': unittest.main()
