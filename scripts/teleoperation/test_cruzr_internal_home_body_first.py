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


class HomePostureRecordTests(unittest.TestCase):
    def run_check(self, record, boot='b1', log='/l/robot_app.x.log', tasks='4', now_offset=60):
        def fake(host, cmd):
            if cmd[0] == 'cat': out = boot+'\n'
            elif cmd[0] == 'bash': out = log+'\n'
            else: out = tasks+'\n'
            return {'returncode': 0, 'stdout': out, 'stderr': ''}
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'rec.json'
            if record is not None: path.write_text(json.dumps(record))
            with patch.object(installer, 'POSTURE_RECORD', path), \
                 patch.object(installer, 'execute', side_effect=fake):
                installer.require_recent_home(now=1000.0+now_offset)

    def test_install_requires_fresh_same_boot_record_without_new_tasks(self):
        good = {'boot_id': 'b1', 'robot_app_log': '/l/robot_app.x.log', 'btree_tasks': 4, 'measured_epoch': 1000.0}
        self.run_check(good)
        for record, kwargs in ((None, {}), (good, {'boot': 'b2'}), (good, {'log': '/l/robot_app.y.log'}),
                               (good, {'tasks': '5'}), (good, {'now_offset': installer.POSTURE_MAX_AGE_S+1}),
                               (good, {'now_offset': -5})):
            with self.assertRaises(RuntimeError):
                self.run_check(record, **kwargs)


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
        # v4 stays byte-identical to the definition installed until 2026-09-18.
        self.assertEqual(hashlib.sha256(model.xml_bytes()).hexdigest(),installer.V4_SHA)
        model.validate_xml(model.xml_bytes())
        with self.assertRaises(ValueError): model.validate_xml(old.xml_bytes())

    def test_v5_elbows_with_body_half_opening_and_v4_speed_bounds(self):
        import xml.etree.ElementTree as ET
        import cruzr_internal_home_body_first as model
        v4 = list(ET.fromstring(model.xml_bytes(4)).find('.//Sequence'))
        v5 = list(ET.fromstring(model.xml_bytes(5)).find('.//Sequence'))
        self.assertEqual([s.get('name') for s in v5], ['body_home_and_elbows_into_limits',
                         'open_arms','lower_arms_while_open','close_lowered_arms'])
        body = v5[0]
        self.assertEqual(body.get('threshold'), '5')
        self.assertEqual([a.attrib for a in body[:3]], [a.attrib for a in v4[0]])
        self.assertEqual([a.get('location') for a in body[3:]], ['left','right'])
        for a in body[3:]:
            # Only elbow_roll (J4), toward the joint interior; soft upper limit 0.0187 rad.
            self.assertEqual([float(v) for v in a.get('delta_joint_angles').split(';')], [0,0,0,-0.03,0,0,0])
        for stage, key, expected in ((v5[1], 'delta_joint_angles', [0,-0.2,0,0,0,0,0]),
                                     (v5[2], 'joint_angles', [0,-0.3,0,0,0,0,0])):
            for a in stage:
                self.assertEqual([float(v) for v in a.get(key).split(';')], expected)
        self.assertTrue(all(float(v)==0 for a in v5[-1] for v in a.get('joint_angles').split(';')))
        # Fixed-delta stages must not exceed v4 quintic peak speed/acceleration.
        def peaks(delta, seconds): return 1.875*delta/seconds, 5.7735*delta/seconds**2
        for new, old in ((peaks(0.2, float(v5[1][0].get('duration'))), peaks(0.4, float(v4[1][0].get('duration')))),
                         (peaks(0.3, float(v5[3][0].get('duration'))), peaks(0.6, float(v4[3][0].get('duration'))))):
            self.assertLessEqual(new[0], old[0]); self.assertLessEqual(new[1], old[1])
        self.assertEqual(v5[2][0].get('duration'), v4[2][0].get('duration'))
        self.assertAlmostEqual(sum(float(s[0].get('duration')) for s in v5), 18.25)
        self.assertEqual(hashlib.sha256(model.xml_bytes(5)).hexdigest(),installer.V5_18S_SHA)
        model.validate_xml(model.xml_bytes(5), version=5)
        with self.assertRaises(ValueError): model.validate_xml(model.xml_bytes(4), version=5)

    def test_v6_v7_parallel_first_stage_and_v7_speed_below_vendor_direct(self):
        import xml.etree.ElementTree as ET
        import cruzr_internal_home_body_first as model
        from cruzr_pico_to_home_owner_gate import JOINT_ORDER, PICO_VARIANTS
        v5 = list(ET.fromstring(model.xml_bytes(5)).find('.//Sequence'))
        for version, lower in ((6, '10.000'), (7, '7.000')):
            seq = list(ET.fromstring(model.xml_bytes(version)).find('.//Sequence'))
            self.assertEqual([s.get('name') for s in seq], ['body_home_with_arm_elbows_then_open',
                             'lower_arms_while_open','close_lowered_arms'])
            first = seq[0]
            self.assertEqual(first.get('threshold'), str(len(first)))
            self.assertEqual([a.attrib for a in first[:3]], [a.attrib for a in v5[0][:3]])
            for side, arm in zip(('left','right'), first[3:]):
                self.assertEqual(arm.tag, 'Sequence')
                # Elbow and opening stay separate commands: an out-of-limit elbow
                # must not hold back (and later jump) the shoulder opening.
                self.assertEqual([(a.get('location'), a.get('delta_joint_angles')) for a in arm],
                                 [(side, model.V5_ELBOW_DELTA), (side, model.V5_OPEN_DELTA)])
                self.assertLessEqual(sum(float(a.get('duration')) for a in arm), float(first[0].get('duration')))
                self.assertEqual(arm[1].get('duration'), v5[1][0].get('duration'))
            self.assertEqual([a.get('joint_angles') for a in seq[1]], [a.get('joint_angles') for a in v5[2]])
            self.assertEqual([a.get('duration') for a in seq[1]], [lower]*2)
            self.assertEqual([a.attrib for a in seq[2]], [a.attrib for a in v5[3]])
            model.validate_xml(model.xml_bytes(version), version=version)
        # v7 lowering peak speed/acceleration never exceeds the highest peak already
        # executed from the same start: vendor direct HOME (all joints to zero in
        # 6 s) or any v4 arm stage (open 0.4/2.5 s, lower 10 s, close 0.6/3.75 s).
        separate = [-0.47285,-0.14985,0.95404,-0.12568,-1.68498,-0.28858,0.29021,
                    0.028,-0.49548,-1.25911,0.05599,2.36521,0.57198,0.77246]+[0.0]*6
        roll = [JOINT_ORDER.index(n) for n in ('L_shoulder_roll_joint','R_shoulder_roll_joint')]
        for start in list(PICO_VARIANTS.values())+[[0.0]*20, separate]:
            opened = list(start[:14])
            for i in roll: opened[i] -= 0.2
            lowered = [0.0]*14
            for i in roll: lowered[i] = -0.3
            v7 = max(abs(a-b) for a,b in zip(opened, lowered))
            v4_open = list(start[:14]); v4_low = [0.0]*14
            for i in roll: v4_open[i] -= 0.4; v4_low[i] = -0.6
            v4 = max(abs(a-b) for a,b in zip(v4_open, v4_low))
            direct = max(abs(x) for x in start[:14])
            speed = max(direct/6.0, v4/10.0, 0.4/2.5, 0.6/3.75)
            accel = max(direct/36.0, v4/100.0, 0.4/2.5**2, 0.6/3.75**2)
            self.assertLessEqual(v7/7.0, speed + 1e-9)
            self.assertLessEqual(v7/49.0, accel + 1e-9)
        self.assertEqual(hashlib.sha256(model.xml_bytes(7)).hexdigest(),installer.NEW_SHA)
        self.assertEqual(installer.XML.read_bytes(),model.xml_bytes(7))

if __name__ == '__main__': unittest.main()
