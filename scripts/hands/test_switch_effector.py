"""Offline failure and orchestration checks; never connects to a robot."""
import base64
import copy
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.hands.effector_profile_config import (
    ENI_SHA, GUARD_SHA, PROFILES, SERVICES, database_environment, plan_files, validate_container, yaml_environment)
from scripts.hands import switch_effector as cli
from scripts.hands import effector_profile_remote as remote

MOTION = b'''env: &shared
  - HW_TYPE=cruzr_s2_v1
  - KEEP=yes
services:
  motion.mc_common:
    environment: *shared
  motion.hw:
    environment: *shared
'''
VISION = b'''services:
  system.control_center:
    environment:
      - HW_TYPE=cruzr_s2_v1
  drivers.imu:
    environment:
      - HW_TYPE=cruzr_s2_v1
'''
META = b'''nodes:
  control_center:
    environment:
      - 'HW_TYPE={{env "HW_TYPE"}}'
'''
DB = b'{ "envs": {"HW_TYPE" : "cruzr_s2_v1", "keep": 7}, "other":true}\n'


def snapshot():
    def container(name):
        return {'Id': name, 'Config': {'Env': ['HW_TYPE=cruzr_s2_v1']},
                'State': {'Running': True}, 'RestartCount': 0}
    def encoded(d):
        return {k: base64.b64encode(v).decode() for k, v in d.items()}
    return {
        'motion': {'containers': {s: container(s) for s in SERVICES}, 'ros_container': 'ros',
                   'extra': {'eni_sha256': ENI_SHA}, 'files': encoded({'compose.yml': MOTION, 'db.json': DB})},
        'vision': {'containers': {'system.control_center': container('cc')}, 'ros_container': 'ros-v',
                   'extra': {'guard_sha256': GUARD_SHA}, 'files': encoded({'compose.yml': VISION, 'system.metafile.yml': META})}}


def bundle(host):
    b = io.BytesIO()
    originals = snapshot()[host]['containers']
    archives = {s+'.tar': b'example backup bytes' for s in originals}
    payload = {'original.json': json.dumps(originals).encode(),
               'archives.json': json.dumps({n: hashlib.sha256(v).hexdigest() for n, v in archives.items()}).encode(), **archives}
    with tarfile.open(fileobj=b, mode='w:gz') as tar:
        for n, v in payload.items():
            m = tarfile.TarInfo('session/'+n); m.size = len(v); tar.addfile(m, io.BytesIO(v))
    data = b.getvalue()
    return {'base64': base64.b64encode(data).decode(), 'sha256': hashlib.sha256(data).hexdigest()}


class ConfigTests(unittest.TestCase):
    def test_motion_aliases_both_directions_and_idempotence(self):
        up = plan_files('motion', {'compose.yml': MOTION, 'db.json': DB}, 'v4')
        self.assertEqual(up['compose.yml'].count(b'cruzr_s2_v1_sps'), 1)
        self.assertEqual(up, plan_files('motion', up, 'v4'))
        down = plan_files('motion', up, 'clamp')
        import yaml
        self.assertEqual(yaml.safe_load(down['compose.yml']), yaml.safe_load(MOTION))
        self.assertEqual(down['db.json'], DB)

    def test_vision_keeps_other_services_and_global_environment(self):
        files = {'compose.yml': VISION, 'system.metafile.yml': META}
        for profile in ('v4', 'clamp'):
            files = plan_files('vision', files, profile)
            import yaml
            parsed = yaml.safe_load(files['compose.yml'])
            self.assertEqual(parsed['services']['drivers.imu']['environment'], ['HW_TYPE=cruzr_s2_v1'])
            self.assertIn('HW_TYPE='+PROFILES[profile], parsed['services']['system.control_center']['environment'])

    def test_refuses_unknown_duplicate_and_missing_fields(self):
        for source in (MOTION.replace(b'cruzr_s2_v1', b'unknown'), MOTION.replace(b'  - KEEP=yes', b'  - HW_TYPE=cruzr_s2_v1')):
            with self.assertRaises(ValueError):
                yaml_environment(source, ('services', 'motion.mc_common'), 'v4')
        with self.assertRaises(ValueError):
            database_environment(b'{"envs":{"HW_TYPE":"unknown"}}', 'clamp')
        with self.assertRaises(ValueError):
            database_environment(b'{"envs":{"HW_TYPE":"cruzr_s2_v1"},"x":{"HW_TYPE":"cruzr_s2_v1"}}', 'v4')

    def test_mixed_database_formatting_is_preserved(self):
        self.assertEqual(database_environment(DB, 'clamp'), DB)
        up = database_environment(DB, 'v4')
        self.assertEqual(up.replace(b'cruzr_s2_v1_sps', b'cruzr_s2_v1'), DB)

    def test_container_refuses_image_env_mount_and_privilege_drift(self):
        a = {'Image': 'sha256:vendor', 'Config': {'Env': ['HW_TYPE=cruzr_s2_v1', 'KEEP=1'], 'Cmd': ['wait']},
             'HostConfig': {'Privileged': True}, 'Mounts': []}
        good = copy.deepcopy(a); good['Config']['Env'][0] = 'HW_TYPE=cruzr_s2_v1_sps'
        validate_container(a, good, 'v4')
        bad_cases = []
        for key, value in [('Image', 'different'), ('Mounts', [{'Source': 'a', 'Destination': 'b', 'RW': True, 'Type': 'bind'}])]:
            bad = copy.deepcopy(good); bad[key] = value; bad_cases.append(bad)
        bad = copy.deepcopy(good); bad['Config']['Env'].append('EXTRA=1'); bad_cases.append(bad)
        bad = copy.deepcopy(good); bad['HostConfig']['Privileged'] = False; bad_cases.append(bad)
        for bad in bad_cases:
            with self.assertRaises(ValueError): validate_container(a, bad, 'v4')


class BackupAndReadTests(unittest.TestCase):
    def test_complete_backup_and_corruption(self):
        for host in ('motion', 'vision'):
            b = bundle(host); data = base64.b64decode(b['base64'])
            self.assertEqual(cli.verify_backup(data, b['sha256']), 9 if host == 'motion' else 1)
            with self.assertRaises(ValueError): cli.verify_backup(data+b'corrupt', b['sha256'])

    def test_backup_requires_all_container_archives(self):
        b = io.BytesIO()
        with tarfile.open(fileobj=b, mode='w:gz') as tar:
            for name, data in [('original.json', b'{"hw":{}}'), ('archives.json', b'{}')]:
                m = tarfile.TarInfo('session/'+name); m.size=len(data);tar.addfile(m,io.BytesIO(data))
        data=b.getvalue()
        with self.assertRaises(ValueError): cli.verify_backup(data,hashlib.sha256(data).hexdigest())

    def test_controller_parser_never_evaluates_calls(self):
        text="response: rosa_control_msgs.srv.ListControllers.Response(controller=[{'name':'x','state':'running'}])"
        self.assertEqual(cli.controller_states(text), {'x':'running'})
        with self.assertRaises((ValueError, SyntaxError)):
            cli.controller_states('ListControllers.Response(controller=__import__("os").system("false"))')

    def test_deleted_custom_file_refused_before_recreation(self):
        with patch.object(remote, 'run', return_value=b'D /opt/walker/home.xml'):
            with self.assertRaises(RuntimeError): remote.selected_paths('id')

    def test_bytecode_ignored_but_binary_customization_is_preserved(self):
        diff=b'C /opt/walker/plugin.so\nA /opt/walker/__pycache__/x.pyc\nC /opt/walker\n'
        def metadata(_, path, head=False): return {'mode': (1 << 31) if path=='/opt/walker' else 0o644}
        with patch.object(remote,'run',return_value=diff),patch.object(remote,'docker_archive',side_effect=metadata):
            self.assertEqual(remote.selected_paths('id'), ['/opt/walker/plugin.so'])


class FlowTests(unittest.TestCase):
    def run_main(self, arguments, fail=None, target='v4', initial=None, corrupt=False, confirm=True):
        events=[]
        class FakeTransport:
            def __init__(self,evidence): self.evidence=evidence;self.ros_container='ros'
            def save(self,name,data): (self.evidence/name).write_text(json.dumps(data))
            def remote(self,host,phase,session,profile,**extra):
                events.append((host,phase))
                if fail==(host,phase): raise RuntimeError('injected failure')
                if phase=='snapshot': return (initial or snapshot())[host]
                if phase=='export':
                    data=bundle(host)
                    if corrupt:data['sha256']='bad'
                    return data
                return {'ok': True}
            def run(self,*args,**kwargs): return '2026-10-15T00:00:00Z'
        with tempfile.TemporaryDirectory() as d, \
             patch.object(cli,'Transport',FakeTransport), \
             patch.object(cli.sys.stdin,'isatty',return_value=True), \
             patch.object(cli,'prompt',side_effect=(lambda *a: events.append(('operator',a[1]))) if confirm else RuntimeError('not confirmed')), \
             patch.object(cli,'safety',side_effect=lambda t,p: events.append(('safety',p))), \
             patch.object(cli,'pose',return_value=([],1)), \
             patch.object(cli,'battery',return_value=[80,80]), \
             patch.object(cli,'wait_ready',side_effect=lambda *a:events.append(('wait','ready'))), \
             patch.object(cli,'verify',return_value={'verified':True}), \
             patch.object(cli.subprocess,'run',return_value=SimpleNamespace(returncode=1)):
            rc=cli.main(['--to',target,'--evidence',str(Path(d)/'run'),*arguments])
        return rc,events

    def test_default_check_cannot_mutate(self):
        rc,events=self.run_main([])
        self.assertEqual(rc,0)
        self.assertEqual(set(events),{('motion','snapshot'),('vision','snapshot')})

    def test_apply_orders_backup_stop_install_recreate_and_operator_release(self):
        rc,events=self.run_main(['--apply'])
        self.assertEqual(rc,0)
        self.assertLess(events.index(('vision','stop')),events.index(('motion','stop')))
        for host in ('motion','vision'):
            self.assertLess(events.index((host,'export')),events.index(('vision','stop')))
            self.assertLess(events.index((host,'install')),events.index((host,'recreate')))
        self.assertLess(events.index(('motion','start')),events.index(('vision','start')))
        self.assertLess(events.index(('wait','ready')),events.index(('operator','PARO LIBERADO')))

    def test_failure_cannot_start_or_automatically_rollback(self):
        rc,events=self.run_main(['--apply'],fail=('motion','recreate'))
        self.assertEqual(rc,2)
        self.assertNotIn(('vision','start'),events)
        self.assertNotIn(('motion','start'),events)
        self.assertNotIn(('operator','PARO LIBERADO'),events)

    def test_reverse_flow_from_sps_to_clamp(self):
        initial=snapshot()
        for host,data in initial.items():
            files={n:base64.b64decode(v) for n,v in data['files'].items()}
            data['files']={n:base64.b64encode(v).decode() for n,v in plan_files(host,files,'v4').items()}
            for c in data['containers'].values():c['Config']['Env']=['HW_TYPE=cruzr_s2_v1_sps']
        rc,events=self.run_main(['--apply'],target='clamp',initial=initial)
        self.assertEqual(rc,0)
        self.assertIn(('motion','recreate'),events)
        self.assertIn(('vision','complete'),events)

    def test_corrupt_external_backup_cannot_stop_services(self):
        rc,events=self.run_main(['--apply'],corrupt=True)
        self.assertEqual(rc,2)
        self.assertNotIn(('vision','stop'),events)
        self.assertNotIn(('motion','install'),events)

    def test_unfinished_session_blocks_new_application(self):
        initial=snapshot();initial['motion']['active_session']={'session':'old','profile':'v4'}
        rc,events=self.run_main(['--apply'],initial=initial)
        self.assertEqual(rc,2)
        self.assertNotIn(('motion','backup'),events)

    def test_unconfirmed_conditions_do_not_mutate(self):
        rc,events=self.run_main(['--apply'],confirm=False)
        self.assertEqual(rc,2)
        self.assertNotIn(('motion','backup'),events)

    def test_unknown_v4_guard_cannot_install(self):
        initial=snapshot();initial['vision']['extra']['guard_sha256']='unreviewed'
        rc,events=self.run_main(['--apply'],initial=initial)
        self.assertEqual(rc,2)
        self.assertNotIn(('motion','backup'),events)

    def test_unknown_eni_cannot_install(self):
        initial=snapshot();initial['motion']['extra']['eni_sha256']='unreviewed'
        rc,events=self.run_main(['--apply'],initial=initial)
        self.assertEqual(rc,2)
        self.assertNotIn(('motion','backup'),events)

    def test_noninteractive_application_cannot_even_connect(self):
        with patch.object(cli.sys.stdin,'isatty',return_value=False),patch.object(cli,'Transport') as transport:
            with self.assertRaises(SystemExit):cli.main(['--to','v4','--apply'])
            transport.assert_not_called()


if __name__=='__main__':unittest.main()
