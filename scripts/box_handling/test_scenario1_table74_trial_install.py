"""Immutable file-operation tests; fake Docker, no robot, ROS or network."""
import copy
import fcntl
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

if __package__:
    from . import scenario1_table74_trial as trial
    from . import scenario1_table74_support as support
    from . import scenario1_table74_trial_install as installer
else:
    import scenario1_table74_trial as trial
    import scenario1_table74_support as support
    import scenario1_table74_trial_install as installer


ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT/'vendor/ubtech/cruzr_s2/snapshot_20260916/motion'


def sources():
    return {trial.SOURCE_XML_PATH: (SNAPSHOT/'tasks/wrc_cruzr/put_cruzr_wrc_low.xml').read_text(),
            trial.SOURCE_YAML_PATH: (SNAPSHOT/'meta_clamp/wrc/put_cruzr_wrc_low.yaml').read_text()}


def bundle():
    reference = dict(version=1, box_bottom_above_floor_m=1.10, surface_height_m=.74,
        precontact_clearance_m=.05, evidence='SYNTHETIC installer test, not an operator measurement',
        scope='current_post_grasp_box_only')
    return trial.build_bundle(reference, *sources().values())


def support_bundle():
    reference = dict(version=1, gap_above_surface_m=.05, surface_height_m=.74,
        predecessor_bundle_id='9360060014e4103ce31da084426302ee4c2e06900a0f5707bf68df0d07ada9ef',
        predecessor_goal_id='7553e90f-cde1-4ca7-a488-96c86816d988',
        evidence='SYNTHETIC support installer test; not a physical measurement',
        scope='current_post_approach_box_only')
    return support.build_bundle(reference, *sources().values())


def inventory():
    return [dict(Name='/renamed-motion', Id='native-id', Image='native-image',
        State=dict(Running=True, Paused=False, Restarting=False, StartedAt='boot-native'),
        Config=dict(Image='vendor/utars-integration:zs2_motion-v0.2.0',
                    Labels={'com.docker.compose.service': 'motion.manipulation_robot_app'},
                    Env=['HW_TYPE=cruzr_s2_v1'])),
        dict(Name='/renamed-ros', Id='ros-id', Image='ros-image',
             State=dict(Running=True, Paused=False, Restarting=False, StartedAt='boot-ros'),
             Config=dict(Image='vendor/ros', Labels={'com.docker.compose.service': 'ros.ros2'}, Env=[]))]


class FakeDocker:
    def __init__(self):
        self.files = sources()
        self.rows = inventory()
        self.binary_hash = trial.META_CLAMP_SHA256
        self.calls, self.writes, self.removes = [], [], []
        self.fail_write = None
        self.lost_write_reply = False
        self.restart_after_inspect = None
        self.inspects = 0
        self.before_write = None

    def __call__(self, args, *, data=None, timeout=20):
        self.calls.append(args)
        if args == ['docker', 'ps', '-q']:
            return 'native-id\nros-id\n'
        if args[:2] == ['docker', 'inspect']:
            self.inspects += 1
            rows = copy.deepcopy(self.rows)
            if self.restart_after_inspect and self.inspects >= self.restart_after_inspect:
                rows[0]['State']['StartedAt'] = 'restarted'
            return json.dumps(rows)
        if args[:6] != ['docker', 'exec', '-i', 'renamed-motion', 'python3', '-c']:
            raise AssertionError('Unreviewed command: '+repr(args[:6]))
        code = args[6]
        if code == installer.READ_SOURCE:
            request = json.loads(data)
            dependencies = {}
            for path in request['dependencies']:
                if path == trial.META_CLAMP_PATH:
                    dependencies[path] = {'sha256': self.binary_hash}
                else:
                    dependencies[path] = dict(sha256=installer.files.sha(self.files[path]), text=self.files[path])
            return json.dumps(dict(dependencies=dependencies, targets={
                p: installer.files.sha(self.files[p]) if p in self.files else None for p in request['targets']}))
        if code == installer.WRITE_SOURCE:
            path = args[-1]
            if self.before_write:
                self.before_write(path)
            self.writes.append(path)
            if len(self.writes) == self.fail_write:
                raise RuntimeError('Synthetic write failure')
            existed = path in self.files
            if existed and self.files[path] != data:
                raise RuntimeError('Synthetic immutable conflict')
            self.files[path] = data
            if self.lost_write_reply:
                raise RuntimeError('Synthetic lost writer response')
            return json.dumps(dict(created=not existed, sha256=installer.files.sha(data)))
        if code == installer.REMOVE_SOURCE:
            targets = json.loads(data)['targets']
            for p, digest in targets.items():
                if p in self.files and installer.files.sha(self.files[p]) != digest:
                    raise RuntimeError('Synthetic changed rollback file')
            removed = []
            for p in targets:
                if p in self.files:
                    del self.files[p]; removed.append(p); self.removes.append(p)
            return json.dumps(dict(removed=removed))
        raise AssertionError('Unexpected embedded operation')


class TrialInstallationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.evidence, self.lock = self.root/'evidence', self.root/'lock'
        self.bundle, self.docker = bundle(), FakeDocker()

    def tearDown(self):
        self.temp.cleanup()

    def run_operation(self, operation='install'):
        return installer.operate(self.bundle, operation=operation, run=self.docker,
                                 evidence_root=self.evidence, lock_path=self.lock)

    def receipt_path(self):
        return self.evidence/self.bundle['manifest']['id']/'install-receipt.json'

    def receipt(self):
        return json.loads(self.receipt_path().read_text())

    def test_default_check_reads_live_sources_binary_and_creates_no_artifacts(self):
        result = installer.operate(self.bundle, run=self.docker, evidence_root=self.evidence, lock_path=self.lock)
        self.assertEqual(result['status'], 'checked')
        self.assertFalse(self.evidence.exists())
        self.assertEqual(self.docker.writes, [])
        self.assertEqual(self.docker.removes, [])

    def test_yaml_before_xml_and_originals_saved_unchanged(self):
        result = self.run_operation()
        self.assertEqual(result['status'], 'installed')
        self.assertEqual([Path(p).suffix for p in self.docker.writes], ['.yaml', '.xml'])
        self.assertEqual(set(result['created_files']), set(self.bundle['tasks']))
        self.assertEqual(result['unconfirmed_created_files'], [])
        self.assertEqual(result['movement_commands'], 0)
        self.assertEqual(result['restarts'], 0)
        self.assertEqual(result['loaded'], 'not_verified')
        self.assertEqual(result['physical_validation'], 'pending')
        backup = json.loads((self.receipt_path().parent/'originals.json').read_text())
        for p, text in sources().items():
            self.assertEqual(backup[p]['text'], text)
            self.assertEqual(self.docker.files[p], text)

    def test_durable_attempt_and_uncertainty_precede_each_write(self):
        def before(path):
            receipt = self.receipt()
            self.assertIn(path, receipt['attempted_files'])
            self.assertIn(path, receipt['unconfirmed_created_files'])
        self.docker.before_write = before
        self.run_operation()

    def test_repeated_install_preserves_ownership(self):
        first = self.run_operation()
        second = self.run_operation()
        self.assertEqual(first['before'], second['before'])
        self.assertEqual(first['created_files'], second['created_files'])

    def test_preexisting_equal_files_never_owned_or_removed(self):
        self.docker.files.update(self.bundle['tasks'])
        installed = self.run_operation()
        self.assertEqual(installed['created_files'], [])
        self.run_operation('rollback')
        self.assertEqual(self.docker.removes, [])
        self.assertTrue(all(p in self.docker.files for p in self.bundle['tasks']))

    def test_modified_sources_binary_or_destinations_prevent_all_writes(self):
        for kind in ('xml', 'yaml', 'binary', 'destination'):
            with self.subTest(kind=kind):
                self.docker = FakeDocker()
                if kind == 'xml': self.docker.files[trial.SOURCE_XML_PATH] += 'changed'
                elif kind == 'yaml': self.docker.files[trial.SOURCE_YAML_PATH] += 'changed'
                elif kind == 'binary': self.docker.binary_hash = '0'*64
                else: self.docker.files[next(iter(self.bundle['tasks']))] = 'foreign'
                with self.assertRaises(RuntimeError): self.run_operation()
                self.assertEqual(self.docker.writes, [])
                self.assertFalse(self.evidence.exists())

    def test_tampered_bundle_rejected_before_docker_even_with_updated_hash(self):
        for change in ('yaml', 'path', 'review', 'manifest', 'extra'):
            with self.subTest(change=change):
                self.bundle = bundle()
                if change == 'yaml':
                    p = next(iter(self.bundle['tasks']))
                    self.bundle['tasks'][p] += '\nrequest: dangerous\n'
                    self.bundle['manifest']['robot_files'][p] = installer.files.sha(self.bundle['tasks'][p])
                elif change == 'path': self.bundle['tasks']['/tmp/other'] = 'text'
                elif change == 'review': self.bundle['review']['physical_validation'] = 'verified'
                elif change == 'manifest': self.bundle['manifest']['phase'] = 'deposit'
                else: self.bundle['extra'] = True
                with self.assertRaises(ValueError): self.run_operation()
                self.assertEqual(self.docker.calls, [])

    def test_partial_failure_records_uncertain_target_and_rolls_back_exactly(self):
        self.docker.fail_write = 2
        with self.assertRaisesRegex(RuntimeError, 'write failure'): self.run_operation()
        failed = self.receipt()
        self.assertEqual(failed['status'], 'installation_failed')
        self.assertEqual(len(failed['created_files']), 1)
        self.assertEqual(len(failed['unconfirmed_created_files']), 1)
        result = self.run_operation('rollback')
        self.assertEqual(result['status'], 'rolled_back')
        self.assertEqual(set(self.docker.files), set(sources()))
        self.assertTrue((self.receipt_path().parent/'bundle.json').is_file())

    def test_lost_reply_leaves_durable_rollback_permission(self):
        self.docker.lost_write_reply = True
        with self.assertRaisesRegex(RuntimeError, 'lost writer'): self.run_operation()
        self.assertEqual(self.receipt()['created_files'], [])
        self.assertEqual(len(self.receipt()['unconfirmed_created_files']), 1)
        self.run_operation('rollback')
        self.assertEqual(set(self.docker.files), set(sources()))

    def test_rollback_xml_first_is_idempotent_and_retains_audit(self):
        self.run_operation()
        first = self.run_operation('rollback')
        self.assertEqual([Path(p).suffix for p in self.docker.removes], ['.xml', '.yaml'])
        second = self.run_operation('rollback')
        self.assertEqual(first['removed_files'], second['removed_files'])
        self.assertEqual(len(self.docker.removes), 2)

    def test_changed_rollback_file_or_container_is_preserved(self):
        self.run_operation()
        p = next(iter(self.bundle['tasks']))
        self.docker.files[p] = 'foreign modification'
        with self.assertRaisesRegex(RuntimeError, 'Destination conflict'): self.run_operation('rollback')
        self.assertEqual(self.docker.removes, [])
        self.docker.files[p] = self.bundle['tasks'][p]
        self.docker.rows[0]['State']['StartedAt'] = 'new boot'
        with self.assertRaisesRegex(RuntimeError, 'receipt identity'): self.run_operation('rollback')
        self.assertEqual(self.docker.removes, [])

    def test_rollback_requires_receipt_and_cannot_claim_preexisting_file(self):
        with self.assertRaisesRegex(RuntimeError, 'requires an existing'): self.run_operation('rollback')
        self.docker.files.update(self.bundle['tasks'])
        self.run_operation()
        receipt = self.receipt()
        receipt['created_files'] = list(self.bundle['tasks'])
        installer.files.write_json(self.receipt_path(), receipt)
        with self.assertRaisesRegex(RuntimeError, 'not absent'): self.run_operation('rollback')
        self.assertEqual(self.docker.removes, [])

    def test_container_restart_before_write_aborts(self):
        self.docker.restart_after_inspect = 2
        with self.assertRaisesRegex(RuntimeError, 'Container changed'): self.run_operation()
        self.assertEqual(self.docker.writes, [])

    def test_container_restart_after_first_write_is_reported_with_rollback_record(self):
        self.docker.restart_after_inspect = 4
        with self.assertRaisesRegex(RuntimeError, 'Container changed'): self.run_operation()
        self.assertEqual(len(self.docker.writes), 1)
        self.assertEqual(self.receipt()['status'], 'installation_failed')
        self.assertEqual(self.receipt()['created_files'], self.docker.writes)

    def test_live_source_change_between_writes_rejected_before_xml(self):
        original_callback = self.docker.__call__
        def run(args, **kwargs):
            result = original_callback(args, **kwargs)
            if len(self.docker.writes) == 1:
                self.docker.files[trial.SOURCE_YAML_PATH] += '\nchanged after first write'
            return result
        with self.assertRaisesRegex(RuntimeError, 'dependency changed'):
            installer.install_bundle(self.bundle, run=run, evidence_root=self.evidence, lock_path=self.lock)
        self.assertEqual(len(self.docker.writes), 1)
        self.assertEqual(self.receipt()['status'], 'installation_failed')

    def test_ambiguous_or_paused_container_is_rejected_without_task_writes(self):
        self.docker.rows.append(copy.deepcopy(self.docker.rows[0]))
        self.docker.rows[-1]['Name'] = '/another-native'
        with self.assertRaises(ValueError): self.run_operation()
        self.assertEqual(self.docker.writes, [])
        self.docker = FakeDocker()
        self.docker.rows[0]['State']['Paused'] = True
        with self.assertRaises(ValueError): self.run_operation()
        self.assertEqual(self.docker.writes, [])

    def test_lock_busy_or_symlink_prevents_docker(self):
        with self.lock.open('w') as held:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError): self.run_operation()
        self.assertEqual(self.docker.calls, [])
        self.lock.unlink()
        target = self.root/'target'; target.write_text('keep')
        self.lock.symlink_to(target)
        with self.assertRaisesRegex(RuntimeError, 'symlink'): self.run_operation()
        self.assertEqual(target.read_text(), 'keep')

    def test_evidence_conflict_prevents_writes(self):
        package = self.evidence/self.bundle['manifest']['id']; package.mkdir(parents=True)
        (package/'bundle.json').write_text('foreign')
        with self.assertRaisesRegex(RuntimeError, 'Immutable evidence conflict'): self.run_operation()
        self.assertEqual(self.docker.writes, [])

    def test_broken_receipt_symlink_is_rejected_before_task_writes(self):
        self.receipt_path().parent.mkdir(parents=True)
        self.receipt_path().symlink_to(self.root/'nonexistent')
        with self.assertRaisesRegex(RuntimeError, 'symlink'): self.run_operation()
        self.assertEqual(self.docker.writes, [])


class EmbeddedProgramsTests(unittest.TestCase):
    def test_in_memory_modules_and_discovery_without_repository_file_access(self):
        code = installer.remote_source()
        code += '\nassert sys.modules["scenario1_deposit_install"].discover_motion('+repr(inventory())+')[0]=="renamed-motion"\n'
        code += 'assert sys.modules["scenario1_table74_trial"].validate_bundle('+repr(bundle())+')["review"]["phase"]=="approach_only"\n'
        code += 'assert sys.modules["scenario1_table74_support"].validate_bundle('+repr(support_bundle())+')["review"]["phase"]=="support_only"\n'
        result = subprocess.run([sys.executable, '-I', '-'], input=code, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_read_and_remove_programs_reject_symlinks_and_changed_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); original = root/'original'; original.write_text('keep')
            link = root/'alias'; link.symlink_to(original)
            request = dict(dependencies=[], text_sources=[], targets=[str(link)])
            result = subprocess.run([sys.executable, '-c', installer.READ_SOURCE], input=json.dumps(request), text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            request = dict(targets={str(original): '0'*64})
            result = subprocess.run([sys.executable, '-c', installer.REMOVE_SOURCE], input=json.dumps(request), text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(original.read_text(), 'keep')

    def test_cli_streams_source_through_stdin_and_defaults_to_check(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'bundle.json'; p.write_text(json.dumps(bundle()))
            result = subprocess.CompletedProcess([], 0, '{"status":"checked"}\n', '')
            with patch.object(installer.subprocess, 'run', return_value=result) as run:
                self.assertEqual(installer.main(['--bundle', str(p)]), 0)
            args, kwargs = run.call_args
            self.assertEqual(args[0][-1], 'python3 -')
            self.assertLess(sum(map(len, args[0])), 1024)
            self.assertIn("'operation': 'check'", kwargs['input'])
            self.assertNotIn('source', ' '.join(args[0]))


class SupportPhaseInstallationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.evidence, self.lock = self.root/'evidence', self.root/'lock'
        self.docker = FakeDocker()

    def tearDown(self):
        self.temp.cleanup()

    def operate(self, value, operation='check'):
        return installer.operate(value, operation=operation, run=self.docker,
                                 evidence_root=self.evidence, lock_path=self.lock)

    def test_support_check_uses_its_builder_and_phase_without_writes(self):
        value = support_bundle()
        self.assertIs(installer._builder(value), support)
        result = self.operate(value)
        self.assertEqual(result['status'], 'checked')
        self.assertEqual(result['phase'], 'support_only')
        self.assertEqual(result['dependencies'], support.DEPENDENCIES)
        self.assertEqual(self.docker.writes, [])

    def test_support_install_and_rollback_preserve_preexisting_approach(self):
        approach = bundle()
        self.operate(approach, 'install')
        self.docker.writes.clear()
        value = support_bundle()
        installed = self.operate(value, 'install')
        self.assertEqual(installed['phase'], 'support_only')
        self.assertEqual(installed['original_dependencies'], support.DEPENDENCIES)
        self.assertEqual(set(installed['created_files']), set(value['tasks']))
        self.assertEqual([Path(p).suffix for p in self.docker.writes], ['.yaml', '.xml'])
        self.assertTrue(all('/local_table74_support/' in p for p in self.docker.writes))
        self.assertEqual(self.operate(value, 'install')['created_files'], installed['created_files'])
        rolled_back = self.operate(value, 'rollback')
        self.assertEqual(rolled_back['status'], 'rolled_back')
        self.assertEqual(set(rolled_back['removed_files']), set(value['tasks']))
        for p, text in {**sources(), **approach['tasks']}.items():
            self.assertEqual(self.docker.files[p], text)

    def test_unknown_phase_and_cross_builder_payloads_are_rejected_before_docker(self):
        for original, phase in ((bundle(), 'support_only'),
                                (support_bundle(), 'approach_only'),
                                (support_bundle(), 'open_release'),
                                (support_bundle(), None)):
            with self.subTest(phase=phase, original=original['manifest']['phase']):
                value = copy.deepcopy(original)
                value['manifest']['phase'] = phase
                with self.assertRaises(ValueError): self.operate(value, 'install')
                self.assertEqual(self.docker.calls, [])

    def test_phase_mismatched_receipt_cannot_authorize_support_rollback(self):
        value = support_bundle()
        self.operate(value, 'install')
        path = self.evidence/value['manifest']['id']/'install-receipt.json'
        receipt = json.loads(path.read_text())
        receipt['phase'] = 'approach_only'
        installer.files.write_json(path, receipt)
        with self.assertRaisesRegex(RuntimeError, 'receipt identity'):
            self.operate(value, 'rollback')
        self.assertEqual(self.docker.removes, [])


if __name__ == '__main__':
    unittest.main()
