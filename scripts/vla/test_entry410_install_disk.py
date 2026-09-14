import base64
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from runtime.entry410_install_disk import plan, install, sha


class DiskInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/'config'; self.root.mkdir()
        self.before = b'# preserve this comment\nready:\n  cmd: "start"\n'
        (self.root/'task_list.yaml').write_bytes(self.before)
        raw = b'<root><!--fixture--></root>\n'
        self.package = dict(expected_registry_sha256=sha(self.before), files={
            f'entry410_stage_{i:02d}_{d}.xml':dict(sha256=sha(raw), base64=base64.b64encode(raw).decode())
            for i in range(1, 6) for d in ('forward', 'reverse')})

    def test_plan_preserves_bytes_and_writes_nothing(self):
        before, after = plan(self.root, self.package)
        self.assertTrue(after.startswith(before)); self.assertEqual(before, self.before)
        self.assertEqual([p.name for p in self.root.iterdir()], ['task_list.yaml'])

    def test_install_preserves_registry_and_backs_up(self):
        result = install(self.root, self.package, Path(self.temp.name)/'backup')
        self.assertFalse(result['reloaded'])
        self.assertEqual((Path(result['backup'])/'task_list.yaml').read_bytes(), self.before)
        self.assertTrue((self.root/'task_list.yaml').read_bytes().startswith(self.before))
        self.assertEqual(len(list((self.root/'s2_bio_vla').glob('*.xml'))), 10)

    def test_changed_registry_rejected(self):
        (self.root/'task_list.yaml').write_bytes(self.before+b'#changed\n')
        with self.assertRaises(ValueError): plan(self.root, self.package)

    def test_preexisting_file_rejected(self):
        directory = self.root/'s2_bio_vla'; directory.mkdir()
        (directory/next(iter(self.package['files']))).write_text('existing')
        with self.assertRaises(ValueError): plan(self.root, self.package)

    def test_quoted_duplicate_key_rejected(self):
        before = self.before+b'"entry410_stage_01_forward": {}\n'
        (self.root/'task_list.yaml').write_bytes(before); self.package['expected_registry_sha256']=sha(before)
        with self.assertRaises(ValueError): plan(self.root, self.package)

    def test_path_injection_and_bad_hash_rejected(self):
        altered = copy.deepcopy(self.package); altered['files']['../bad'] = altered['files'].pop(next(iter(altered['files'])))
        with self.assertRaises(ValueError): plan(self.root, altered)
        altered = copy.deepcopy(self.package); next(iter(altered['files'].values()))['sha256'] = '0'*64
        with self.assertRaises(ValueError): plan(self.root, altered)

    def test_write_failure_cleans_created_files_preserves_registry(self):
        with patch('runtime.entry410_install_disk.os.replace', side_effect=OSError('injected write failure')):
            with self.assertRaises(OSError): install(self.root, self.package, Path(self.temp.name)/'backup')
        self.assertEqual((self.root/'task_list.yaml').read_bytes(), self.before)
        self.assertEqual(list((self.root/'s2_bio_vla').glob('*.xml')), [])


class CorrectedReadyInstallTests(DiskInstallTests):
    def setUp(self):
        super().setUp()
        value=next(iter(self.package['files'].values()))
        self.package['profile']='ready410_head063'
        self.package['files']={f'ready410_h63_{part}_{i:02d}_{d}.xml':dict(value)
            for part in ('access','entry') for i in range(1,6) for d in ('forward','reverse')}

    def test_install_preserves_registry_and_backs_up(self):
        result=install(self.root,self.package,Path(self.temp.name)/'backup')
        self.assertEqual(len(result['installed_files']),20)
        self.assertFalse(result['motion_command_sent']);self.assertFalse(result['reloaded'])
        self.assertEqual((Path(result['backup'])/'task_list.yaml').read_bytes(),self.before)
        self.assertTrue((self.root/'task_list.yaml').read_bytes().startswith(self.before))

    def test_quoted_duplicate_key_rejected(self):
        key=next(iter(self.package['files']))[:-4]
        before=self.before+f'"{key}": {{}}\n'.encode()
        (self.root/'task_list.yaml').write_bytes(before);self.package['expected_registry_sha256']=sha(before)
        with self.assertRaises(ValueError):plan(self.root,self.package)

    def test_incomplete_or_unknown_profile_rejected(self):
        altered=copy.deepcopy(self.package);altered['files'].pop(next(iter(altered['files'])))
        with self.assertRaises(ValueError):plan(self.root,altered)
        altered=copy.deepcopy(self.package);altered['profile']='arbitrary'
        with self.assertRaises(ValueError):plan(self.root,altered)


if __name__ == '__main__': unittest.main()
