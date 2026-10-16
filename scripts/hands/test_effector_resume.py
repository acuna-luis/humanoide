"""Offline checks for resuming a stopped pair; no transport reaches a robot."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.hands import switch_effector as cli
from scripts.hands.effector_profile_config import PROFILES, plan_files
from scripts.hands.test_switch_effector import bundle, snapshot


SESSION = '20261016T080000Z-1234abcd'


class FakeTransport:
    def __init__(self, evidence, current):
        self.evidence = evidence
        self.current = current
        self.events = []
        self.requests = []
        self.ros_container = None

    def save(self, name, data):
        with (self.evidence / name).open('x') as stream:
            json.dump(data, stream)

    def remote(self, host, phase, session, profile, **extra):
        self.events.append((host, phase))
        self.requests.append((host, phase, session, profile, extra))
        if phase == 'snapshot':
            return copy.deepcopy(self.current[host])
        if phase not in {'validate', 'verify-stopped', 'restore'}:
            raise AssertionError('Unexpected remote operation: ' + phase)
        if phase == 'verify-stopped' and host != 'motion':
            raise AssertionError('Only Motion should be verified without restoring')
        if phase == 'restore' and host != 'vision':
            raise AssertionError('Motion must not be restored again')
        return {'ok': True}

    def run(self, *args, **kwargs):
        raise AssertionError('Unexpected unmocked remote command')


class ResumeStoppedTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.folder = root / 'interrupted'
        self.evidence = root / 'resume'
        self.folder.mkdir()
        self.evidence.mkdir()
        self.current = snapshot()
        self.plan = {'session': SESSION, 'target': 'v4', 'hashes': {}}
        for host, current in self.current.items():
            current['active_session'] = {'session': SESSION, 'profile': 'v4'}
            files = {name: base64.b64decode(data) for name, data in current['files'].items()}
            target = plan_files(host, files, 'v4')
            current['files'] = {name: base64.b64encode(data).decode() for name, data in target.items()}
            self.plan['hashes'][host] = {name: hashlib.sha256(data).hexdigest()
                                         for name, data in target.items()}
            for container in current['containers'].values():
                container['Id'] = 'recreated-' + container['Id']
                container['State']['Running'] = False
                container['Config']['Env'] = ['HW_TYPE=' + PROFILES['v4']]
            backup = bundle(host)
            (self.folder / (host + '-backup.tar.gz')).write_bytes(base64.b64decode(backup['base64']))
            self.write(host + '-backup-verified.json', {'sha256': backup['sha256']})
        self.write('plan.json', self.plan)
        for name in ('phase-recreate-motion.json', 'phase-recreate-vision.json', 'interrupted.json'):
            self.write(name, {})
        self.transport = FakeTransport(self.evidence, self.current)

    def write(self, name, data):
        (self.folder / name).write_text(json.dumps(data))

    def resume(self, profile='v4'):
        def activate(transport, session, selected, journal):
            transport.events.append(('activation', 'called'))
            self.assertEqual((session, selected), (SESSION, profile))
            return 0

        with patch.object(cli, 'activate', side_effect=activate) as activation, \
             patch.object(cli, 'prompt'), \
             patch.object(cli, 'safety'), \
             patch.object(cli, 'battery', return_value=[80, 80]), \
             patch.object(cli.subprocess, 'run', return_value=SimpleNamespace(returncode=1)):
            result = cli.resume_stopped(self.transport, self.folder, profile)
            self.assertEqual(activation.call_count, 1)
            return result

    def assert_rejected(self, reason, profile='v4'):
        with patch.object(cli, 'activate') as activation, \
             patch.object(cli, 'prompt') as prompt, \
             patch.object(cli, 'safety') as safety, \
             patch.object(cli, 'battery') as battery, \
             patch.object(cli.subprocess, 'run', return_value=SimpleNamespace(returncode=1)), \
             self.assertRaisesRegex((RuntimeError, ValueError), reason):
            cli.resume_stopped(self.transport, self.folder, profile)
        activation.assert_not_called()
        prompt.assert_not_called()
        safety.assert_not_called()
        battery.assert_not_called()
        self.assertFalse(any(phase != 'snapshot' for _, phase in self.transport.events))

    def test_resumes_only_after_both_validations_without_repeating_completed_phases(self):
        self.assertEqual(self.resume(), 0)
        operations = [event for event in self.transport.events if event[1] != 'snapshot']
        self.assertEqual(operations, [
            ('motion', 'validate'), ('vision', 'validate'),
            ('motion', 'verify-stopped'), ('vision', 'restore'), ('activation', 'called')])
        requests = {(host, phase): extra for host, phase, session, profile, extra
                    in self.transport.requests if phase != 'snapshot'}
        for host in ('motion', 'vision'):
            request = requests[(host, 'validate')]
            self.assertEqual(request['expected_ids'], {
                service: container['Id'] for service, container in self.current[host]['containers'].items()})
            self.assertIn('original.json', request['expected_staged_files'])
            final = 'verify-stopped' if host == 'motion' else 'restore'
            self.assertEqual(request, requests[(host, final)])
        self.assertTrue((self.evidence / 'phase-verify-stopped-motion.json').is_file())
        self.assertTrue((self.evidence / 'phase-restore-vision.json').is_file())

    def test_refuses_any_prior_start_attempt(self):
        self.write('phase-start-motion.json', {'phase': 'start-motion'})
        self.assert_rejected('no attempted start')

    def test_refuses_destination_different_from_original_plan(self):
        self.assert_rejected('session/target mismatch', profile='clamp')

    def test_refuses_corrupt_external_backup(self):
        path = self.folder / 'motion-backup.tar.gz'
        path.write_bytes(path.read_bytes() + b'corrupt')
        self.assert_rejected('backup checksum mismatch')

    def test_refuses_mismatched_active_marker(self):
        self.current['vision']['active_session'] = {'session': 'another', 'profile': 'v4'}
        self.assert_rejected('active session markers must match')

    def test_refuses_running_container(self):
        self.current['motion']['containers']['motion.hw']['State']['Running'] = True
        self.assert_rejected('already recreated and stopped')

    def test_refuses_current_source_drift(self):
        files = self.current['vision']['files']
        files['compose.yml'] = base64.b64encode(base64.b64decode(files['compose.yml']) + b'\n# drift\n').decode()
        self.assert_rejected('Installed sources differ')

    def test_refuses_unrecreated_container_id(self):
        self.current['motion']['containers']['motion.hw']['Id'] = 'motion.hw'
        self.assert_rejected('service was not recreated')

    def test_refuses_missing_recreation_receipt(self):
        (self.folder / 'phase-recreate-vision.json').unlink()
        self.assert_rejected('both recreation phases')


class StartupReadinessTests(unittest.TestCase):
    def test_fault_after_wait_message_never_allows_release(self):
        class Transport:
            def run(self, *args):
                return 'State -> WaitEStopRelease\nState WaitEStopRelease -> Fault\n'
        with self.assertRaisesRegex(RuntimeError, 'Startup fault'):
            cli.wait_ready(Transport(), 'cc', '2026-10-16T08:00:00Z', seconds=1)


if __name__ == '__main__':
    unittest.main()
