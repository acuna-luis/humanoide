#!/usr/bin/env python3
"""Offline staging tests; no SSH connection or transfer occurs."""
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import stage_data as subject


class StageDataTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.bundle=self.root/'bundle';self.capture=self.root/'capture';self.code=self.root/'code'
        (self.bundle/'demo'/'rgb').mkdir(parents=True);self.capture.mkdir();self.code.mkdir()
        raw=self.capture/'samples.jsonl';raw.write_text('{"private":"telemetry"}\n')
        self.raw_hash=hashlib.sha256(raw.read_bytes()).hexdigest()
        rows=[]
        for n in (10,11):
            path=self.bundle/'demo'/'rgb'/f'{n:06}.png';path.write_bytes(f'private-image-{n}'.encode())
            rows.append({'source_frame':n,'png_file':f'rgb/{n:06}.png',
                         'png_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        target=self.bundle/'demo'/'candidate_targets.jsonl'
        target.write_text(''.join(json.dumps(x)+'\n' for x in rows))
        manifest={'schema':'cruzr_ball_candidate_targets_v1','training_ready':False,
            'physical_control_qualified':False,'offline_experiment_only':True,
            'segments':[{'id':'demo','source_dir':str(self.capture),'status':'candidate_success',
                'split':'inspection_train','start_frame':10,'end_frame':11,
                'source_hashes':{'samples.jsonl':self.raw_hash},
                'candidate_targets_sha256':hashlib.sha256(target.read_bytes()).hexdigest()}]}
        (self.bundle/'manifest.json').write_text(json.dumps(manifest))
        (self.bundle/'secret-not-included.txt').write_text('should never be staged')
        for name in subject.TOOLS:
            (self.code/name).write_text(f'# test {name}\n')
        (self.code/'smolvla_ball_server').mkdir()
        (self.code/'smolvla_ball_server'/'convert_on_server.sh').write_text('# test conversion wrapper\n')
        self.patch=patch.object(subject,'CODE_DIR',self.code);self.patch.start()

    def tearDown(self):
        self.patch.stop();self.tmp.cleanup()

    def test_plan_and_archive_allowlist_hashes_and_private_modes(self):
        data=subject.plan(self.bundle)
        self.assertEqual(data['source_container_path'],str(self.capture))
        self.assertTrue(data['no_hub_upload']);self.assertTrue(data['no_robot_control'])
        self.assertNotIn('candidate_bundle/secret-not-included.txt',data['files'])
        self.assertEqual(len(data['files']),9)
        buf=io.BytesIO();subject.archive(buf,data);buf.seek(0)
        with tarfile.open(fileobj=buf,mode='r:') as tar:
            members=tar.getmembers();names={m.name for m in members}
            self.assertEqual(names,set(data['files'])|{'STAGING_METADATA.json','SHA256SUMS'})
            self.assertTrue(all(m.isfile() and m.mode==0o600 for m in members))
            meta=json.load(tar.extractfile('STAGING_METADATA.json'))
            self.assertEqual(meta['source_samples_sha256'],self.raw_hash)
            for name,expected in meta['file_sha256'].items():
                self.assertEqual(hashlib.sha256(tar.extractfile(name).read()).hexdigest(),expected)

    def test_modified_source_or_image_rejected(self):
        (self.capture/'samples.jsonl').write_text('changed')
        with self.assertRaisesRegex(ValueError,'raw capture'):
            subject.plan(self.bundle)
        (self.capture/'samples.jsonl').write_text('{"private":"telemetry"}\n')
        (self.bundle/'demo'/'rgb'/'000010.png').write_text('changed')
        with self.assertRaisesRegex(ValueError,'RGB checksum mismatch'):
            subject.plan(self.bundle)

    def test_symlink_and_unknown_segment_rejected(self):
        image=self.bundle/'demo'/'rgb'/'000010.png';image.unlink();image.symlink_to(self.capture/'samples.jsonl')
        with self.assertRaisesRegex(ValueError,'symlinks'):
            subject.plan(self.bundle)
        image.unlink();image.write_bytes(b'private-image-10')
        p=self.bundle/'manifest.json';m=json.loads(p.read_text());m['segments'][0]['status']='assisted';p.write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError,'only candidate_success'):
            subject.plan(self.bundle)

    def test_ssh_arguments_and_remote_path_reject_shell_escape(self):
        subject.validate_remote('operator@server','/srv/private/new-run')
        for host,path in [('host;evil','/safe/run'),('host','/safe/../bad'),('host','/safe/$(evil)'),('-host','/safe/run')]:
            with self.assertRaises(ValueError):subject.validate_remote(host,path)
        args=subject.ssh_args('operator@server',2649,'test -d /srv')
        self.assertIn('StrictHostKeyChecking=yes',args);self.assertIn('BatchMode=yes',args)
        self.assertEqual(args[args.index('-p')+1],'2649')
        for port in [0,65536,-1,True,'2649']:
            with self.assertRaises(ValueError):subject.ssh_args('operator@server',port,'true')

    def test_remote_check_uses_the_requested_port(self):
        with patch.object(subject.subprocess,'run') as run:
            subject.remote_check('operator@server',2649,'/srv/private/run1')
        args=run.call_args.args[0]
        self.assertEqual(args[args.index('-p')+1],'2649')

    def test_transfer_creates_new_directory_and_checks_remote_sha(self):
        data=subject.plan(self.bundle); calls=[]
        class Sink(io.BytesIO):
            def close(self):
                self.captured=self.getvalue();super().close()
        class Proc:
            def __init__(self,args,stdin):
                calls.append(args);self.stdin=Sink()
            def wait(self):return 0
        with patch.object(subject.subprocess,'Popen',Proc):
            subject.transfer('operator@server',2649,'/srv/private/run1',data)
        self.assertEqual(calls[0][calls[0].index('-p')+1],'2649')
        command=calls[0][-1]
        self.assertIn('mkdir -m 700 --',command);self.assertIn('sha256sum -c SHA256SUMS',command)
        self.assertNotIn('rm ',command);self.assertNotIn('docker',command)


if __name__ == '__main__':
    unittest.main()
