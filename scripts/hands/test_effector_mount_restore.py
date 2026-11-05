"""Offline regressions for writable-layer backups; Docker and SSH are never used."""
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from scripts.hands import effector_profile_remote as remote


SERVICE = 'system.control_center'
HISTORIES = ('/home/ubt/.bash_history', '/home/ubt/.zsh_history')


def mounts(*destinations):
    return [{'Destination': destination, 'Source': '/host' + destination,
             'Type': 'bind', 'RW': True} for destination in destinations]


def regular(name, data=b'', **metadata):
    member = tarfile.TarInfo(name)
    member.size = len(data)
    member.mode = metadata.pop('mode', 0o640)
    member.uid = metadata.pop('uid', 1000)
    member.gid = metadata.pop('gid', 1000)
    for key, value in metadata.items():
        setattr(member, key, value)
    return member, data


def symlink(name, target):
    member = tarfile.TarInfo(name)
    member.type = tarfile.SYMTYPE
    member.linkname = target
    member.mode = 0o777
    return member, None


def tar_bytes(entries):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w', format=tarfile.PAX_FORMAT) as archive:
        for member, data in entries:
            archive.addfile(member, io.BytesIO(data) if data is not None else None)
    return buffer.getvalue()


def expected_manifest(entries):
    return {'/' + member.name: ({'sha256': hashlib.sha256(data).hexdigest()}
                               if member.isfile() else {'link': member.linkname})
            for member, data in entries}


def write_stage(stage, entries, manifest=None):
    raw = tar_bytes(entries)
    archive_name = SERVICE + '.tar'
    (stage / archive_name).write_bytes(raw)
    (stage / 'archives.json').write_text(json.dumps({
        archive_name: hashlib.sha256(raw).hexdigest()}))
    (stage / 'manifests.json').write_text(json.dumps({
        SERVICE: expected_manifest(entries) if manifest is None else manifest}))
    return raw


class MountRestoreTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.stage = Path(temporary.name)
        self.docker_diff = self.enterContext(patch.object(remote, 'run'))
        self.archive_read = self.enterContext(patch.object(remote, 'docker_archive'))
        self.docker_write = self.enterContext(patch.object(remote.subprocess, 'run'))
        self.docker_diff.side_effect = AssertionError('Unexpected Docker command in offline test')
        self.archive_read.side_effect = AssertionError('Unexpected Docker API read in offline test')
        self.docker_write.side_effect = AssertionError('Unexpected Docker mutation in offline test')

    def current(self, destinations=HISTORIES):
        return {SERVICE: {'Id': 'new-cc', 'Mounts': mounts(*destinations)}}

    def test_mounts_exclude_exact_paths_and_descendants_without_prefix_collisions(self):
        destinations = mounts('/tmp', '/etc/walker', HISTORIES[0])
        for path in ('/tmp', '/tmp/record.motion', '/etc/walker',
                     '/etc/walker/nested/profile.yaml', HISTORIES[0]):
            with self.subTest(path=path):
                self.assertTrue(remote.mounted_path(path, destinations))
        for path in ('/tmp2/record.motion', '/etc/walker-old/profile.yaml',
                     '/home/ubt/.bash_history.before', '/opt/walker/file'):
            with self.subTest(path=path):
                self.assertFalse(remote.mounted_path(path, destinations))

    def test_mount_filter_applies_to_all_mount_types(self):
        for kind in ('bind', 'volume', 'tmpfs'):
            with self.subTest(kind=kind):
                self.assertTrue(remote.mounted_path('/state/profile.yaml', [
                    {'Destination': '/state', 'Type': kind}]))
        self.assertTrue(remote.mounted_path('/anything/file', mounts('/')))

    def test_backup_excludes_mounts_before_head_or_deleted_file_checks(self):
        kept = {'/opt/walker/plugin.so': b'\x00\xffbinary',
                '/home/ubt/.bash_history.before': b'layer file'}
        self.docker_diff.side_effect = None
        self.docker_diff.return_value = (
            'C ' + HISTORIES[0] + '\nD ' + HISTORIES[1] + '\n'
            'D /etc/walker/removed.yaml\nA /tmp/take.motion\n' +
            ''.join('C ' + path + '\n' for path in kept)).encode()

        def read(container, path, head=False):
            self.assertEqual(container, 'old-cc')
            self.assertIn(path, kept, 'Mounted path reached the archive API')
            if head:
                return {'mode': 0o640}
            return tar_bytes([regular(path.rsplit('/', 1)[-1], kept[path])])

        self.archive_read.side_effect = read
        original = {SERVICE: {'Id': 'old-cc',
                              'Mounts': mounts(*HISTORIES, '/etc/walker', '/tmp')}}
        with patch.dict(remote.CONFIG, {'vision': {}}):
            remote.make_backup(self.stage, original, 'vision')
        manifest = json.loads((self.stage / 'manifests.json').read_text())[SERVICE]
        self.assertEqual(set(manifest), set(kept))
        with tarfile.open(self.stage / (SERVICE + '.tar')) as archive:
            self.assertEqual(set(archive.getnames()), {path[1:] for path in kept})
            for path, content in kept.items():
                self.assertEqual(archive.extractfile(path[1:]).read(), content)
        self.docker_write.assert_not_called()

    def test_deleted_unmounted_customization_still_requires_review(self):
        self.docker_diff.side_effect = None
        self.docker_diff.return_value = b'D /opt/walker/custom.xml\n'
        with self.assertRaises(RuntimeError):
            remote.selected_paths('old-cc', mounts('/etc/walker'))
        self.archive_read.assert_not_called()

    def test_backup_rewrites_pax_path_to_the_full_container_path(self):
        path = '/opt/walker/settings.yml'
        self.docker_diff.side_effect = None
        self.docker_diff.return_value = ('C ' + path + '\n').encode()
        source = tar_bytes([regular('settings.yml', b'keep: true\n',
                                    pax_headers={'path': 'settings.yml'})])
        self.archive_read.side_effect = lambda *args, head=False: (
            {'mode': 0o640} if head else source)
        with patch.dict(remote.CONFIG, {'vision': {}}):
            remote.make_backup(self.stage, self.current(()), 'vision')
        with tarfile.open(self.stage / (SERVICE + '.tar')) as archive:
            self.assertEqual(archive.getnames(), [path[1:]])
            self.assertEqual(archive.extractfile(path[1:]).read(), b'keep: true\n')

    def test_legacy_histories_only_backup_never_calls_docker_cp_or_reads_mounts(self):
        entries = [regular(path[1:]) for path in HISTORIES]
        original = write_stage(self.stage, entries)
        report = remote.restore_files(self.stage, self.current())
        self.assertEqual(report[SERVICE]['restored'], [])
        self.assertEqual(report[SERVICE]['preserved_mounts'], list(HISTORIES))
        self.assertEqual((self.stage / (SERVICE + '.tar')).read_bytes(), original)
        self.archive_read.assert_not_called()
        self.docker_write.assert_not_called()

    def test_old_backup_preserves_real_file_bytes_permissions_and_links(self):
        entries = [regular(HISTORIES[0][1:]),
                   regular('opt/walker/config.yml', b'\x00\xffconfiguration', mode=0o600,
                           uid=1234, gid=4321),
                   symlink('opt/walker/config-link', 'config.yml')]
        original = write_stage(self.stage, entries)
        restored = {}

        def docker_cp(command, *, input, check, timeout):
            self.assertEqual(command, ['docker', 'cp', '-a', '-', 'new-cc:/'])
            self.assertTrue(check)
            self.assertGreater(timeout, 0)
            with tarfile.open(fileobj=io.BytesIO(input)) as archive:
                for member in archive.getmembers():
                    self.assertNotIn('/' + member.name, HISTORIES)
                    data = archive.extractfile(member).read() if member.isfile() else None
                    restored['/' + member.name] = (member, data)

        def read(container, path, head=False):
            self.assertEqual(container, 'new-cc')
            self.assertFalse(head)
            self.assertNotIn(path, HISTORIES)
            member, data = restored[path]
            return tar_bytes([(member, data)])

        self.docker_write.side_effect = docker_cp
        self.archive_read.side_effect = read
        report = remote.restore_files(self.stage, self.current())
        self.assertEqual(report[SERVICE]['restored'], [
            '/opt/walker/config.yml', '/opt/walker/config-link'])
        self.assertEqual(report[SERVICE]['preserved_mounts'], [HISTORIES[0]])
        self.assertEqual(restored['/opt/walker/config.yml'][1], b'\x00\xffconfiguration')
        member = restored['/opt/walker/config.yml'][0]
        self.assertEqual((member.mode, member.uid, member.gid), (0o600, 1234, 4321))
        self.assertEqual(restored['/opt/walker/config-link'][0].linkname, 'config.yml')
        self.assertEqual(self.archive_read.call_count, 2)
        self.docker_write.assert_called_once()
        self.assertEqual((self.stage / (SERVICE + '.tar')).read_bytes(), original)

    def test_real_file_verification_failure_is_not_hidden_by_mounted_entries(self):
        write_stage(self.stage, [regular(HISTORIES[0][1:]),
                                 regular('opt/walker/config.yml', b'expected')])
        self.archive_read.side_effect = lambda container, path: tar_bytes([
            regular('config.yml', b'changed')])
        with self.assertRaises(RuntimeError):
            remote.verify_files(self.stage, self.current())
        self.archive_read.assert_called_once_with('new-cc', '/opt/walker/config.yml')

    def test_real_link_verification_failure_is_not_hidden_by_mounted_entries(self):
        write_stage(self.stage, [regular(HISTORIES[0][1:]),
                                 symlink('opt/walker/link', 'config.yml')])
        self.archive_read.side_effect = lambda container, path: tar_bytes([
            symlink('link', 'other.yml')])
        with self.assertRaises(RuntimeError):
            remote.verify_files(self.stage, self.current())

    def test_corrupt_archive_is_rejected_before_any_docker_call(self):
        write_stage(self.stage, [regular('opt/walker/config.yml', b'expected')])
        with (self.stage / (SERVICE + '.tar')).open('ab') as stream:
            stream.write(b'changed after checksum')
        with self.assertRaises(RuntimeError):
            remote.restore_files(self.stage, self.current())
        self.docker_write.assert_not_called()
        self.archive_read.assert_not_called()

    def test_invalid_tar_structure_or_manifest_is_rejected_before_docker_cp(self):
        good = regular('opt/walker/config.yml', b'expected')
        hardlink = tarfile.TarInfo('opt/walker/link')
        hardlink.type = tarfile.LNKTYPE
        hardlink.linkname = 'opt/walker/config.yml'
        directory = tarfile.TarInfo('opt/walker/directory')
        directory.type = tarfile.DIRTYPE
        cases = [
            ('absolute', [regular('/opt/walker/config.yml', b'x')], None),
            ('parent traversal', [regular('opt/../config.yml', b'x')], None),
            ('dot path component', [regular('./opt/walker/config.yml', b'x')], None),
            ('empty path component', [regular('opt//walker/config.yml', b'x')], None),
            ('duplicate', [good, good], None),
            ('unlisted member', [good], {}),
            ('missing member', [], expected_manifest([good])),
            ('hardlink', [(hardlink, None)], None),
            ('directory', [(directory, None)], None),
            ('wrong checksum', [good], {'/opt/walker/config.yml': {'sha256': '0' * 64}}),
            ('regular file expected as link', [good], {'/opt/walker/config.yml': {'link': 'other'}}),
            ('link expected as regular file', [symlink('opt/walker/link', 'config.yml')],
             {'/opt/walker/link': {'sha256': '0' * 64}}),
            ('wrong link target', [symlink('opt/walker/link', 'config.yml')],
             {'/opt/walker/link': {'link': 'other.yml'}}),
            ('absolute link target', [symlink('opt/walker/link', '/etc/walker/config.yml')], None),
            ('parent link target', [symlink('opt/walker/link', '../config.yml')], None),
            ('relative link into mount', [symlink('home/ubt/history-link', '.bash_history')], None),
            ('file ancestor of mount', [regular('home/ubt', b'x')], None),
        ]
        for label, entries, manifest in cases:
            with self.subTest(case=label):
                write_stage(self.stage, entries, manifest)
                with self.assertRaises(RuntimeError):
                    remote.restore_files(self.stage, self.current())
                self.docker_write.assert_not_called()
                self.archive_read.assert_not_called()

    def test_mounted_member_corruption_is_rejected_even_when_restore_would_skip_it(self):
        write_stage(self.stage, [regular(HISTORIES[0][1:])],
                    {HISTORIES[0]: {'sha256': '0' * 64}})
        with self.assertRaises(RuntimeError):
            remote.restore_files(self.stage, self.current())
        self.docker_write.assert_not_called()
        self.archive_read.assert_not_called()


if __name__ == '__main__':
    unittest.main()
