"""Offline installer tests: synthetic calibration, fake Docker, real temp files."""
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
    from . import scenario1_deposit as deposit
    from . import scenario1_deposit_install as installer
else:
    import scenario1_deposit as deposit
    import scenario1_deposit_install as installer


ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT/'vendor/ubtech/cruzr_s2/snapshot_20260916/motion'


def source_files():
    return {deposit.SOURCE_XML_PATH: (SNAPSHOT/'tasks/wrc_cruzr/put_cruzr_wrc_low.xml').read_text(),
            deposit.SOURCE_YAML_PATH: (SNAPSHOT/'meta_clamp/wrc/put_cruzr_wrc_low.yaml').read_text(),
            deposit.SOURCE_OPEN_PATH: (SNAPSHOT/'meta_clamp/wrc/open_arm_cruzr.yaml').read_text()}


def bundle():
    profile = json.loads((ROOT/'config/box_handling/scenario1_put1.json').read_text())
    profile.update(reference_box_bottom_above_floor_m=.90,
                   reference_left_hand_motion_z_m=.84, reference_right_hand_motion_z_m=.85,
                   horizontal_alignment_verified=True, release_clearance_verified=True,
                   evidence='Synthetic installer unit test only; not physical calibration')
    return deposit.build_bundle(profile, *source_files().values())


def inventory():
    return [dict(Name='/renamed-motion', Id='container-native', Image='sha256:native',
                 State=dict(Running=True, Paused=False, Restarting=False, StartedAt='boot-native'),
                 Config=dict(Image='vendor/utars-integration:zs2_motion-v0.2.0',
                             Labels={'com.docker.compose.service': 'motion.manipulation_robot_app'},
                             Env=['HW_TYPE=cruzr_s2_v1'])),
            dict(Name='/renamed-ros', Id='container-ros', Image='sha256:ros',
                 State=dict(Running=True, Paused=False, Restarting=False, StartedAt='boot-ros'),
                 Config=dict(Image='vendor/ros', Labels={'com.docker.compose.service': 'ros.ros2'}, Env=[]))]


class FakeDocker:
    def __init__(self):
        self.files = source_files()
        self.inventory = inventory()
        self.calls = []
        self.writes = []
        self.failure_at = None
        self.corrupt_reply = False
        self.changed_inventory_at = None
        self.inspects = 0

    def __call__(self, args, *, data=None, timeout=20):
        self.calls.append(list(args))
        if args == ['docker', 'ps', '-q']:
            return 'container-native\ncontainer-ros\n'
        if args[:2] == ['docker', 'inspect']:
            self.inspects += 1
            rows = copy.deepcopy(self.inventory)
            if self.changed_inventory_at is not None and self.inspects >= self.changed_inventory_at:
                rows[0]['State']['StartedAt'] = 'restarted'
            return json.dumps(rows)
        if args[:6] != ['docker', 'exec', '-i', 'renamed-motion', 'python3', '-c']:
            raise AssertionError('Unexpected command; no motion/service/restart commands allowed: '+repr(args[:6]))
        code = args[6]
        if code == installer.READ_SOURCE:
            request = json.loads(data)
            result = {path: installer.sha(self.files[path]) for path in request['dependencies']}
            result.update({path: installer.sha(self.files[path]) if path in self.files else None
                           for path in request['targets']})
            return json.dumps(result)
        if code != installer.WRITE_SOURCE or len(args) != 8:
            raise AssertionError('Unreviewed Docker operation')
        path = args[-1]
        self.writes.append(path)
        if len(self.writes) == self.failure_at:
            raise RuntimeError('Synthetic writer failure')
        existed = path in self.files
        if existed and self.files[path] != data:
            raise RuntimeError('Synthetic destination conflict')
        self.files[path] = data
        return json.dumps({'created': not existed, 'sha256': '0'*64 if self.corrupt_reply else installer.sha(data)})


class BundleValidationTests(unittest.TestCase):
    def test_real_builder_contract_is_accepted(self):
        value = bundle()
        identity, hashes = installer.validate_bundle(value)
        self.assertEqual(identity, value['manifest']['id'])
        self.assertEqual(set(hashes), set(value['tasks']))
        self.assertEqual(installer.DEPENDENCIES, deposit.SOURCE_HASHES)
        self.assertEqual(installer.BUILDER_VERSION, deposit.BUILDER_VERSION)

    def test_pending_review_and_claimed_physical_validation_rejected(self):
        for target, key, value in [('review', 'ready', False), ('review', 'ready', 1),
                                   ('review', 'missing', ['calibration']),
                                   ('manifest', 'physical_validation', 'verified')]:
            data = bundle()
            data[target][key] = value
            with self.subTest(target=target, key=key), self.assertRaises(ValueError):
                installer.validate_bundle(data)

    def test_paths_names_and_contents_must_match_manifest(self):
        for change in ('path', 'name', 'content', 'dependency', 'config', 'id', 'extra'):
            data = bundle()
            first = next(iter(data['tasks']))
            if change == 'path': data['tasks']['/tmp/arbitrary.yaml'] = data['tasks'].pop(first)
            if change == 'name': data['task_name'] = '../vendor'
            if change == 'content': data['tasks'][first] += '\nchanged'
            if change == 'dependency': data['dependencies'][next(iter(data['dependencies']))] = '0'*64
            if change == 'config': data['review']['config']['surface_height_m'] += .01
            if change == 'id': data['manifest']['id'] = '../escape'
            if change == 'extra': data['extra'] = True
            with self.subTest(change=change), self.assertRaises(ValueError):
                installer.validate_bundle(data)

    def test_xml_cannot_add_an_action_even_with_adjusted_hash(self):
        data = bundle()
        path = next(path for path in data['tasks'] if path.endswith('.xml'))
        data['tasks'][path] = data['tasks'][path].replace('</Sequence>', '<Action ID="MetaMove" name="other"/></Sequence>')
        data['manifest']['robot_files'][path] = installer.sha(data['tasks'][path])
        with self.assertRaisesRegex(ValueError, 'two-action'):
            installer.validate_bundle(data)

    def test_invalid_json_or_duplicate_fields_rejected(self):
        for value in ('[]', '{"id":1,"id":2}', '{"v":NaN}', '{"v":1e999}'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                installer.object_json(value)

    def test_standalone_source_works_without_repository_imports(self):
        scope = {'__name__': 'installer_in_memory'}  # Deliberately no __file__.
        exec(compile(installer.remote_source(), 'installer_in_memory', 'exec'), scope)
        self.assertEqual(scope['validate_bundle'](bundle()), installer.validate_bundle(bundle()))
        self.assertEqual(scope['discover_motion'](inventory())[0], 'renamed-motion')
        self.assertEqual(installer.remote_source(), installer.build_remote_source())


class DiscoveryTests(unittest.TestCase):
    def test_exact_service_aliases_work_under_arbitrary_container_names(self):
        for native, ros in [('motion.manipulation_robot_app', 'ros.ros2'), ('manipulation_robot_app', 'ros2')]:
            rows = inventory()
            rows[0]['Config']['Labels']['com.docker.compose.service'] = native
            rows[1]['Config']['Labels']['com.docker.compose.service'] = ros
            self.assertEqual(installer.discover_motion(rows)[0], 'renamed-motion')

    def test_unknown_hardware_image_or_ambiguous_role_rejected(self):
        for case in ('hardware', 'image', 'duplicate', 'paused', 'unlabeled'):
            rows = inventory()
            if case == 'hardware': rows[0]['Config']['Env'] = ['HW_TYPE=other']
            if case == 'image': rows[0]['Config']['Image'] = 'unreviewed:v1'
            if case == 'duplicate':
                duplicate = copy.deepcopy(rows[0]); duplicate['Name'] = '/another-motion'; rows.append(duplicate)
            if case == 'paused': rows[0]['State']['Paused'] = True
            if case == 'unlabeled':
                rows[0]['Name'] = '/walker-motion.manipulation_robot_app-1'; rows[0]['Config']['Labels'] = {}
            with self.subTest(case=case), self.assertRaises(ValueError):
                installer.discover_motion(rows)


class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.evidence = self.root/'evidence'
        self.lock = self.root/'install.lock'
        self.data = bundle()
        self.docker = FakeDocker()

    def tearDown(self):
        self.directory.cleanup()

    def install(self):
        return installer.install_bundle(self.data, run=self.docker,
                                        evidence_root=self.evidence, lock_path=self.lock)

    def receipt(self):
        return json.loads((self.evidence/self.data['manifest']['id']/'install-receipt.json').read_text())

    def test_yaml_precedes_xml_and_records_exact_files_without_motion(self):
        receipt = self.install()
        self.assertEqual([Path(path).suffix for path in self.docker.writes], ['.yaml', '.xml'])
        self.assertEqual(receipt['created_files'], sorted(self.data['tasks']))
        self.assertEqual(receipt['status'], 'installed')
        self.assertEqual(receipt['movement_commands'], 0)
        self.assertEqual(receipt['restarts'], 0)
        self.assertEqual(receipt['loaded'], 'not_verified')
        self.assertEqual(receipt['physical_validation'], 'pending')
        self.assertEqual(receipt['rollback_remove_only_if_sha256_matches'], receipt['task_hashes'])
        self.assertEqual(self.receipt(), receipt)
        for path, text in source_files().items(): self.assertEqual(self.docker.files[path], text)

    def test_repeated_install_preserves_created_receipt_and_originals(self):
        first = self.install()
        second = self.install()
        self.assertEqual(first['created_files'], second['created_files'])
        self.assertEqual(second['status'], 'installed')
        self.assertEqual(set(self.docker.files), set(source_files()) | set(self.data['tasks']))

    def test_preexisting_equal_files_are_not_claimed_for_rollback(self):
        self.docker.files.update(self.data['tasks'])
        receipt = self.install()
        self.assertEqual(receipt['created_files'], [])
        self.assertEqual(receipt['rollback_remove_only_if_sha256_matches'], {})

    def test_all_destinations_checked_before_first_write(self):
        xml = next(path for path in self.data['tasks'] if path.endswith('.xml'))
        self.docker.files[xml] = 'existing different task'
        with self.assertRaisesRegex(RuntimeError, 'refusing overwrite'):
            self.install()
        self.assertEqual(self.docker.writes, [])
        self.assertFalse(self.evidence.exists())
        self.assertEqual(self.docker.files[xml], 'existing different task')

    def test_all_original_hashes_checked_before_first_write(self):
        self.docker.files[next(iter(installer.DEPENDENCIES))] = 'changed vendor'
        with self.assertRaisesRegex(RuntimeError, 'dependency changed'):
            self.install()
        self.assertEqual(self.docker.writes, [])
        self.assertFalse(self.evidence.exists())

    def test_active_lock_prevents_every_docker_operation(self):
        with self.lock.open('a') as held:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError): self.install()
        self.assertEqual(self.docker.calls, [])
        self.assertFalse(self.evidence.exists())

    def test_container_restart_before_install_is_rejected_without_writes(self):
        self.docker.changed_inventory_at = 2
        with self.assertRaisesRegex(RuntimeError, 'Container changed'):
            self.install()
        self.assertEqual(self.docker.writes, [])
        self.assertFalse(self.evidence.exists())

    def test_container_restart_after_install_marks_failure(self):
        self.docker.changed_inventory_at = 3
        with self.assertRaisesRegex(RuntimeError, 'Container changed'):
            self.install()
        receipt = self.receipt()
        self.assertEqual(receipt['status'], 'installation_failed')
        self.assertEqual(receipt['created_files'], sorted(self.data['tasks']))

    def test_partial_failure_retains_created_and_unconfirmed_paths(self):
        self.docker.failure_at = 2
        with self.assertRaisesRegex(RuntimeError, 'Synthetic writer'):
            self.install()
        receipt = self.receipt()
        self.assertEqual(receipt['status'], 'installation_failed')
        self.assertEqual(len(receipt['created_files']), 1)
        self.assertTrue(receipt['created_files'][0].endswith('.yaml'))
        self.assertEqual(len(receipt['unconfirmed_created_files']), 1)
        self.assertTrue(receipt['unconfirmed_created_files'][0].endswith('.xml'))
        self.assertEqual(set(receipt['rollback_remove_only_if_sha256_matches']), set(self.data['tasks']))

    def test_lost_writer_verification_is_never_reported_installed(self):
        self.docker.corrupt_reply = True
        with self.assertRaisesRegex(RuntimeError, 'receipt/hash'):
            self.install()
        receipt = self.receipt()
        self.assertEqual(receipt['created_files'], [])
        self.assertEqual(receipt['status'], 'installation_failed')
        self.assertEqual(receipt['unconfirmed_created_files'], self.docker.writes)

    def test_immutable_evidence_conflict_prevents_task_writes(self):
        package = self.evidence/self.data['manifest']['id']
        package.mkdir(parents=True)
        (package/'bundle.json').write_text('unrelated evidence')
        with self.assertRaisesRegex(RuntimeError, 'Immutable evidence conflict'):
            self.install()
        self.assertEqual(self.docker.writes, [])

    def test_lock_and_evidence_links_are_rejected(self):
        external = self.root/'external'; external.mkdir()
        self.evidence.symlink_to(external, target_is_directory=True)
        with self.assertRaisesRegex(RuntimeError, 'symlink'):
            self.install()
        self.assertEqual(self.docker.writes, [])
        self.evidence.unlink()
        self.lock.unlink()
        target = self.root/'lock-target'; target.write_text('preserve')
        self.lock.symlink_to(target)
        with self.assertRaises(OSError): self.install()
        self.assertEqual(target.read_text(), 'preserve')


class StandaloneFileWriterTests(unittest.TestCase):
    def invoke(self, path, value='new data'):
        return subprocess.run([sys.executable, '-B', '-c', installer.WRITE_SOURCE, str(path)],
                              input=value, text=True, capture_output=True, timeout=5)

    def test_exclusive_creation_and_idempotence_without_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'namespace'/'task.yaml'
            first = self.invoke(path)
            second = self.invoke(path)
            conflict = self.invoke(path, 'different')
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertTrue(json.loads(first.stdout)['created'])
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertFalse(json.loads(second.stdout)['created'])
            self.assertNotEqual(conflict.returncode, 0)
            self.assertEqual(path.read_text(), 'new data')
            self.assertEqual([p.name for p in path.parent.iterdir()], ['task.yaml'])

    def test_file_and_namespace_symlinks_cannot_redirect_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root/'target'; target.mkdir()
            original = target/'task.yaml'; original.write_text('preserved')
            alias = root/'alias'; alias.symlink_to(target, target_is_directory=True)
            self.assertNotEqual(self.invoke(alias/'task.yaml').returncode, 0)
            (root/'file-link.yaml').symlink_to(original)
            self.assertNotEqual(self.invoke(root/'file-link.yaml').returncode, 0)
            self.assertEqual(original.read_text(), 'preserved')

    def test_read_preflight_rejects_destination_link(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root/'target'; target.write_text('preserved')
            alias = root/'alias'; alias.symlink_to(target)
            result = subprocess.run([sys.executable, '-B', '-c', installer.READ_SOURCE],
                                    input=json.dumps({'dependencies': [], 'targets': [str(alias)]}),
                                    text=True, capture_output=True, timeout=5)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(target.read_text(), 'preserved')


if __name__ == '__main__':
    unittest.main()
