#!/usr/bin/env python3
"""Test server converter wrapper with an inert fake docker, without networking."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT=Path(__file__).resolve().parent/'convert_on_server.sh'


class ConvertServerTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.stage=self.root/'stage';self.out=self.root/'new_output';self.fakebin=self.root/'bin'
        self.fakebin.mkdir();self.log=self.root/'docker.log'
        docker=self.fakebin/'docker'
        docker.write_text('#!/bin/sh\nprintf "%s\\n" "$@" >> "$DOCKER_LOG"\nexit 0\n')
        docker.chmod(0o755)
        files={'source_capture/samples.jsonl':b'raw private',
               'tools/prepare_ball_observations.py':b'observations',
               'tools/prepare_ball_candidate_targets.py':b'targets',
               'tools/convert_ball_candidates_to_lerobot.py':b'converter',
               'tools/convert_on_server.sh':b'conversion wrapper',
               'candidate_bundle/manifest.json':json.dumps({'segments':[{'source_dir':'/home/lacuna/capture'}]}).encode(),
               'candidate_bundle/episode/rgb/000001.png':b'private image'}
        hashes={}
        for name,data in files.items():
            path=self.stage/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
            hashes[name]=hashlib.sha256(data).hexdigest()
        metadata={'no_hub_upload':True,'no_robot_control':True,'file_sha256':hashes,
            'source_container_path':'/home/lacuna/capture',
            'source_samples_sha256':hashes['source_capture/samples.jsonl'],
            'candidate_manifest_sha256':hashes['candidate_bundle/manifest.json']}
        (self.stage/'STAGING_METADATA.json').write_text(json.dumps(metadata))
        self.env=dict(os.environ,PATH=str(self.fakebin)+':'+os.environ['PATH'],DOCKER_LOG=str(self.log))

    def tearDown(self):
        self.temp.cleanup()

    def run_script(self,*args):
        return subprocess.run(['bash',str(SCRIPT),*args],env=self.env,capture_output=True,text=True)

    def test_help_and_check_only_inspects_without_creating_output(self):
        self.assertEqual(self.run_script('--help').returncode,0)
        result=self.run_script('--check','--staging',str(self.stage),'--output',str(self.out))
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertFalse(self.out.exists())
        self.assertEqual(self.log.read_text().splitlines()[:2],['image','inspect'])
        self.assertNotIn('run',self.log.read_text().splitlines())

    def test_run_is_offline_readonly_no_gpu_and_user_owned(self):
        result=self.run_script('--run','--staging',str(self.stage),'--output',str(self.out))
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(self.out.stat().st_mode & 0o777,0o700)
        args=self.log.read_text().splitlines()
        self.assertIn('--network',args);self.assertIn('none',args)
        self.assertIn('--read-only',args);self.assertIn('--user',args)
        self.assertIn('--pull=never',args);self.assertIn('--offline-experiment',args)
        self.assertNotIn('--gpus',args);self.assertNotIn('--privileged',args)
        self.assertIn(f'type=bind,src={self.stage}/source_capture,dst=/home/lacuna/capture,readonly',args)
        self.assertIn(f'type=bind,src={self.stage}/candidate_bundle,dst=/work/candidates,readonly',args)
        self.assertIn(f'type=bind,src={self.stage}/tools,dst=/work/tools,readonly',args)
        self.assertIn(f'type=bind,src={self.out},dst=/work/output',args)

    def test_hash_failure_and_overlap_rejected_before_output_or_docker(self):
        (self.stage/'source_capture'/'samples.jsonl').write_text('tampered')
        result=self.run_script('--run','--staging',str(self.stage),'--output',str(self.out))
        self.assertNotEqual(result.returncode,0);self.assertFalse(self.out.exists());self.assertFalse(self.log.exists())
        result=self.run_script('--run','--staging',str(self.stage),'--output',str(self.stage/'new'))
        self.assertNotEqual(result.returncode,0);self.assertFalse((self.stage/'new').exists())


if __name__ == '__main__':
    unittest.main()
