"""Run the backup offline against fixture paths and a read-only fake Docker CLI."""
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

SOURCE = Path(__file__).with_name('preupgrade_backup_remote.sh')
FAKE_DOCKER = r'''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
a = sys.argv[1:]
with open(os.environ['TEST_DOCKER_LOG'], 'a') as log:
    log.write(json.dumps(a)+'\n')
if a[0] == 'ps':
    if os.environ.get('TEST_LIST_FAIL'):
        sys.exit(1)
    if '-aq' in a:
        print('a1\nb2')
    elif '--format' in a:
        if os.environ.get('TEST_UNKNOWN'):
            print('c3\tnew-firmware-unknown')
        else:
            print('a1\twalker-motion.manipulation_robot_app-1')
            print('b2\twalker-web.web-expression-1')
elif a[0] == 'image' and a[1] == 'ls':
    print('fixture-image')
elif a[0] == 'inspect':
    print('[{"State":{"Running":false}}]')
elif a[0] == 'diff':
    print('C /opt/walker/config')
elif a[0] == 'cp':
    assert ':' in a[1] and ':' not in a[2], 'only download is allowed'
    assert a[2].startswith(os.environ['TEST_ROOT']), 'write escaped fixture'
    if os.environ.get('TEST_COPY_FAIL') and 'meta_tasks' in a[1]:
        sys.exit(1)
    dest = Path(a[2])
    if a[1].endswith('.html'):
        dest.write_text('<html>fixture original</html>')
    elif a[1].endswith('.js'):
        dest.write_text('// fixture')
    else:
        dest.mkdir()
        (dest/'home.xml').write_text('<root>reviewed fixture</root>')
        (dest/'current.xml').symlink_to('home.xml')
else:
    raise SystemExit('forbidden Docker command: '+repr(a))
'''


class BackupTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root/'bin'
        self.bin.mkdir()
        self.log = self.root/'docker.jsonl'
        self.env = dict(os.environ, PATH=str(self.bin)+':'+os.environ['PATH'],
                        TEST_ROOT=str(self.root), TEST_DOCKER_LOG=str(self.log))
        self.executable('docker', FAKE_DOCKER)
        self.executable('id', '#!/bin/sh\necho 0\n')
        self.executable('chown', '#!/bin/sh\nexit 0\n')
        # Discard ownership arguments in fixture mode; never require root.
        self.executable('install', '''#!/usr/bin/env python3
import subprocess, sys
a = sys.argv[1:]; clean = []
while a:
    arg = a.pop(0)
    if arg in ('-o', '-g'): a.pop(0)
    else: clean.append(arg)
sys.exit(subprocess.call(['/usr/bin/install', *clean]))
''')
        for command in ('systemctl', 'dpkg-query', 'udoke', 'ip'):
            self.executable(command, '#!/bin/sh\necho fixture\n')
        script = SOURCE.read_text()
        for original, replacement in (
            ('/home/walker', str(self.root/'walker')),
            ('/etc/', str(self.root/'etc')+'/'),
            ('/usr/local/sbin/', str(self.root/'sbin')+'/'),
        ):
            script = script.replace(original, replacement)
        self.script = self.root/'backup.sh'
        self.script.write_text(script)
        for relative in ('etc/walker/system/soft_version',
                         'etc/walker/boot/cruzr-boot-ready.js',
                         'etc/walker/trajectory-overlays/before.xml',
                         'etc/systemd/system/cruzr-boot-voice.service',
                         'walker/.local/share/cruzr-pico-arms-only/vendor.yaml'):
            target = self.root/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('fixture '+relative)
        self.backup = self.root/'walker/preupgrade-v0.2.0-20260910-120000'

    def executable(self, name, contents):
        path = self.bin/name
        path.write_text(contents)
        path.chmod(0o700)

    def run_backup(self, **extra):
        return subprocess.run(['bash', str(self.script), '20260910-120000'],
                              env=dict(self.env, **extra), capture_output=True,
                              text=True, timeout=15)

    def verify_checksums(self):
        result = subprocess.run(['sha256sum', '-c', 'SHA256SUMS'],
                                cwd=self.backup, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr+result.stdout)

    def test_capture_stopped_containers_host_overlays_and_private_files(self):
        result = self.run_backup()
        self.assertEqual(result.returncode, 0, result.stderr+result.stdout)
        self.assertEqual((self.backup/'STATUS').read_text().strip(), 'CAPTURED_REVIEW_COVERAGE')
        with tarfile.open(self.backup/'configuration.tar.gz') as archive:
            names = archive.getnames()
            for suffix in ('boot/cruzr-boot-ready.js', 'trajectory-overlays/before.xml',
                           'cruzr-boot-voice.service', 'cruzr-pico-arms-only/vendor.yaml'):
                self.assertTrue(any(name.endswith(suffix) for name in names), suffix)
        with tarfile.open(self.backup/'container-configs.tar.gz') as archive:
            self.assertTrue(any(member.issym() for member in archive))
        commands = [json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertTrue(any(a[0] == 'cp' and 'meta_tasks' in a[1] for a in commands))
        self.assertTrue(all(a[0] in {'ps', 'image', 'inspect', 'diff', 'cp'} for a in commands))
        for path in [self.backup, *self.backup.rglob('*')]:
            if not path.is_symlink():
                self.assertEqual(path.stat().st_mode & 0o077, 0, str(path))
        self.verify_checksums()
        before = (self.backup/'SHA256SUMS').read_bytes()
        self.assertEqual(self.run_backup().returncode, 4)
        self.assertEqual((self.backup/'SHA256SUMS').read_bytes(), before)

    def test_copy_failure_keeps_partial_evidence_and_returns_nonzero(self):
        result = self.run_backup(TEST_COPY_FAIL='1')
        self.assertEqual(result.returncode, 6, result.stderr)
        self.assertEqual((self.backup/'STATUS').read_text().strip(), 'PARTIAL')
        self.assertIn('container_copy_failed', (self.backup/'failures.txt').read_text())
        self.verify_checksums()

    def test_new_container_names_require_coverage_review(self):
        result = self.run_backup(TEST_UNKNOWN='1')
        self.assertEqual(result.returncode, 6, result.stderr)
        self.assertIn('no_known_configuration_containers', (self.backup/'failures.txt').read_text())

    def test_docker_inventory_failure_is_not_a_successful_empty_backup(self):
        result = self.run_backup(TEST_LIST_FAIL='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.backup/'STATUS').read_text().strip(), 'IN_PROGRESS')
        self.assertFalse((self.backup/'SHA256SUMS').exists())


if __name__ == '__main__':
    unittest.main()
