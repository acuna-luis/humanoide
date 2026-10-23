import functools
import hashlib
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch, MagicMock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE/'robot'))
sys.path.insert(0, str(HERE.parent/'box_handling'))
sys.path.insert(0, str(HERE.parent/'lib'))
import service
import scenario1_cli as cli
import scenario1_robot_home as home


def intent(**extra):
    return dict(action='home', height='74', key='a'*32, physical_confirmed=True, trial_authorized=False, **extra)


class JobTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.jobs = service.Jobs(self.temp.name, enabled=True)
    def tearDown(self):
        self.jobs.lock.close()
        self.temp.cleanup()
    def test_strict_request(self):
        for change in ({'action':'shell'}, {'height':'69.5'}, {'physical_confirmed':1}, {'trial_authorized':1}, {'shell':'HOME'}, {'action':'cycle'}):
            with self.assertRaises(ValueError): service.validate_request(dict(intent(), **change))
    def test_durable_submission_idempotent_no_duplicate_dispatch(self):
        with patch.object(threading.Thread, 'start') as start:
            a = self.jobs.submit(intent())
            b = self.jobs.submit(intent())
            self.assertEqual(a['id'], b['id']); self.assertEqual(start.call_count, 1)
            self.assertEqual(json.loads((Path(self.temp.name)/a['id']/'job.json').read_text())['status'], 'accepted')
            with self.assertRaises(ValueError): self.jobs.submit(dict(intent(), key='b'*32))
            with self.assertRaises(ValueError): self.jobs.submit(dict(intent(), action='cycle', trial_authorized=True))
    def test_disabled(self):
        self.jobs.enabled = False
        with self.assertRaises(ValueError): self.jobs.submit(intent())
    def test_restart_blocks_uncertain_job(self):
        with patch.object(threading.Thread, 'start'): self.jobs.submit(intent())
        self.jobs.lock.close()
        self.jobs = service.Jobs(self.temp.name, True)
        self.assertTrue(self.jobs.blocked)
        self.assertEqual(self.jobs.current['status'], 'indeterminate')
        with self.assertRaises(ValueError): self.jobs.submit(dict(intent(), key='b'*32))
    def test_preflight_failure_never_dispatches_run(self):
        result = MagicMock(); result.wait.return_value = 78
        self.jobs.launch = MagicMock(return_value=result)
        with patch.object(threading.Thread, 'start'): job = self.jobs.submit(intent())
        self.jobs.run(job, Path(self.temp.name)/job['id'])
        self.assertEqual(self.jobs.launch.call_count, 1)
        self.assertNotIn('--run', self.jobs.launch.call_args.args[0])
        self.assertTrue(self.jobs.blocked)
    def test_success_calls_only_closed_commands(self):
        result = MagicMock(); result.wait.return_value = 0
        self.jobs.launch = MagicMock(return_value=result)
        with patch.object(threading.Thread, 'start'): job = self.jobs.submit(intent())
        self.jobs.run(job, Path(self.temp.name)/job['id'])
        self.assertEqual(self.jobs.launch.call_count, 2)
        command = self.jobs.launch.call_args.args[0]
        self.assertIn('--run', command); self.assertNotIn('ssh', command)
        self.assertNotIn('shell', self.jobs.launch.call_args.kwargs)
        self.assertEqual(job['status'], 'succeeded')


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.server = ThreadingHTTPServer(('127.0.0.1',0), service.Handler)
        self.server.origin = 'http://127.0.0.1:'+str(self.server.server_port)
        self.server.sessions = {}; self.server.session_lock = threading.Lock(); self.server.last_login = float('-inf')
        self.server.token_sha = hashlib.sha256(b'test-only').hexdigest()
        self.server.jobs = service.Jobs(self.temp.name, enabled=True)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval':.01}, daemon=True)
        self.thread.start()
    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()
        self.server.jobs.lock.close(); self.temp.cleanup()
    def request(self, path, method='GET', data=None, **headers):
        c = HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        body = json.dumps(data) if data is not None else None
        if body is not None: headers.setdefault('Content-Type','application/json')
        c.request(method, path, body, headers)
        r = c.getresponse(); value = r.read(); result = r.status, dict(r.getheaders()), value
        c.close(); return result
    def login(self):
        code, headers, body = self.request('/api/login', 'POST', {'token':'test-only'}, Origin=self.server.origin)
        self.assertEqual(code,200)
        return headers['Set-Cookie'].split(';')[0]
    def test_no_auth_no_state_no_action_and_cross_origin_rejected(self):
        self.assertEqual(self.request('/api/status')[0],401)
        self.assertEqual(self.request('/api/jobs','POST', intent(), Origin='http://evil.example')[0],403)
        self.assertEqual(self.request('/api/login','POST', {'token':'test-only'}, Origin='null')[0],403)
    def test_cookie_csrf_and_idempotency(self):
        cookie = self.login()
        self.assertEqual(self.request('/api/jobs','POST', intent(), Origin=self.server.origin, Cookie=cookie)[0],403)
        code, _, body = self.request('/api/status', Cookie=cookie)
        csrf = json.loads(body)['csrf']
        with patch.object(self.server.jobs, 'run'):
            for _ in range(2):
                self.assertEqual(self.request('/api/jobs','POST', intent(), Origin=self.server.origin, Cookie=cookie, **{'X-CSRF-Token':csrf})[0],202)
        self.assertEqual(len(list(Path(self.temp.name).glob('*/job.json'))),1)
    def test_static_csp_no_arbitrary_paths_or_delete(self):
        code, headers, body = self.request('/')
        self.assertEqual(code,200); self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])
        self.assertEqual(self.request('/../etc/passwd')[0],401)
        self.assertEqual(self.request('/api/jobs','DELETE')[0],405)
    def test_malformed_login(self):
        for value in ([], None, 12):
            self.assertIn(self.request('/api/login','POST',value, Origin=self.server.origin)[0],(403,409,429))


class TransportHomeTests(unittest.TestCase):
    def test_local_transport_no_ssh(self):
        with patch.dict(os.environ, CRUZR_SCENARIO1_LOCAL='1'):
            command = cli.ssh_command(False)
            self.assertEqual(command[:4], [sys.executable,'-u','-B','-c'])
            self.assertNotIn('ssh',command)
            with self.assertRaises(ValueError): cli.ssh_command(True)
    def test_home_one_goal_and_postcondition(self):
        runtime = MagicMock(); runtime.payload = {'mode':'run'}
        runtime.stop.wait.return_value = True
        runtime.session = Path(tempfile.mkdtemp())
        runtime.commands.get.return_value = {'command':'arm'}
        runtime.action_sessions = {}; runtime.health_session = None
        runtime.action.return_value = {'status':4,'result':{'state':{'state':1101001,'desc':'SUCCEED'}}}
        try:
            with patch.object(home,'Runtime',return_value=runtime), patch.object(home.signal,'signal'), patch.object(home.fcntl,'flock'), patch.object(home.contract,'validate_motion_result'), patch.object(home,'atomic_json'):
                self.assertEqual(home.main({'mode':'run'}),0)
            runtime.action.assert_called_once_with('motion', {'task_name':'cruzr/home','yaml_args':'{}'},60)
            self.assertEqual(runtime.health.call_args.kwargs, {'require_home':True})
        finally: runtime.lock.close(); __import__('shutil').rmtree(runtime.session)
    def test_home_no_motion_on_check_or_health_failure(self):
        for fail in (False,True):
            runtime = MagicMock(); runtime.stop.wait.return_value = True
            runtime.session = None; runtime.action_sessions = {}; runtime.health_session = None
            if fail: runtime.health.side_effect = RuntimeError('charger connected')
            with patch.object(home,'Runtime',return_value=runtime), patch.object(home.signal,'signal'), patch.object(home.fcntl,'flock'):
                self.assertEqual(home.main({'mode':'check'}),78 if fail else 0)
            runtime.action.assert_not_called(); runtime.lock.close()

    def test_failed_home_measurement_is_not_reported_as_success(self):
        runtime = MagicMock(); runtime.stop.wait.return_value = True
        runtime.session = Path(tempfile.mkdtemp())
        runtime.commands.get.return_value = {'command':'arm'}
        runtime.action_sessions = {}; runtime.health_session = None
        runtime.health.side_effect = [None, None, RuntimeError('HOME_NOT_MEASURED')]
        try:
            with patch.object(home,'Runtime',return_value=runtime), patch.object(home.signal,'signal'), patch.object(home.fcntl,'flock'), patch.object(home.contract,'validate_motion_result'), patch.object(home,'atomic_json'):
                self.assertEqual(home.main({'mode':'run'}),78)
            self.assertEqual(runtime.action.call_count,1)
            self.assertNotIn('home_complete',[call.args[0] for call in runtime.emit.call_args_list])
        finally:
            runtime.lock.close(); __import__('shutil').rmtree(runtime.session)



class InstallerTests(unittest.TestCase):
    def test_package_is_self_contained_verified_and_secrets_not_shipped(self):
        spec = importlib.util.spec_from_file_location('resident_builder', HERE/'build_robot_installer.py')
        builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)
        spec = importlib.util.spec_from_file_location('resident_installer', HERE/'install_robot_scenario1.py')
        installer = importlib.util.module_from_spec(spec); spec.loader.exec_module(installer)
        with tempfile.TemporaryDirectory() as folder:
            package = builder.build(Path(folder)/'bundle')
            manifest = installer.verify(package)
            pins = (package/'app/scripts/cruzr_blue_workbin_cycle.sh').read_text()
            self.assertNotIn('password', pins.lower()); self.assertNotIn('ssh', pins.lower())
            self.assertFalse((package/'app/scripts/cruzr_recover_to_home.sh').exists())
            # The relocated plan imports all its own modules and builds the full
            # immutable 74/90 bundles without the PC, Docker, ROS or SSH.
            for height in ('74','90'):
                command = ['bash',str(package/'app/scripts/optimistic_scenario1.sh'),'--plan','--table-height-cm',height]
                result = subprocess.run(command,capture_output=True,text=True,cwd=folder,timeout=10,
                    env=dict(os.environ,CRUZR_SCENARIO1_LOCAL='1'))
                self.assertEqual(result.returncode,0,result.stderr)
            (package/'app/scripts/web/robot/app.js').write_text('changed')
            with self.assertRaises(ValueError): installer.verify(package)
    def test_local_cycle_never_installs_during_job(self):
        import scenario1_table74_trial_install as install
        with patch.dict(os.environ, CRUZR_SCENARIO1_LOCAL='1'), tempfile.TemporaryDirectory() as folder:
            with patch.object(install,'operate',return_value={'installed':False}) as operation:
                with self.assertRaises(ValueError): cli.prepare_height_installation({},Path(folder),True)
                operation.assert_called_once_with({},operation='check')
    def test_installer_unit_has_no_pc_and_no_automatic_restart(self):
        spec = importlib.util.spec_from_file_location('resident_installer', HERE/'install_robot_scenario1.py')
        installer = importlib.util.module_from_spec(spec); spec.loader.exec_module(installer)
        unit = installer.unit_text('walker')
        self.assertIn('Restart=no',unit); self.assertNotIn('ssh',unit)
        self.assertNotIn('--run',unit)
        with self.assertRaises(ValueError): installer.unit_text('root\nExecStart=bad')

if __name__ == '__main__': unittest.main()
