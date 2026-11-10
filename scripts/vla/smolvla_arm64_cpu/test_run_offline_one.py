"""CPU wrapper contract tests with fake docker; no model or robot executed."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).with_name('run_offline_one.sh')
BASE = 'sha256:4703adf8fdd93b1441114e4f87ce2c62f7373fc5f88bda6a546c551625bcc71c'


class WrapperTests(unittest.TestCase):
    def test_one_sample_runner_is_confined_and_readonly(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            envdir, train, checkpoint, vlm = [root / n for n in ('environment', 'training', 'checkpoint', 'vlm')]
            for p in (envdir / 'venv', train, checkpoint, vlm): p.mkdir(parents=True)
            (envdir / 'venv/pyvenv.cfg').write_text('dummy')
            sample = root / 'sample.jsonl'; sample.write_text('{"schema":"cruzr_ball_live_observation_v1","source_status":"historical_recording_not_live","physical_control_qualified":false}\n')
            expected = hashlib.sha256(sample.read_bytes()).hexdigest()
            fakebin = root / 'bin'; fakebin.mkdir()
            (fakebin / 'uname').write_text('#!/bin/sh\nprintf "aarch64\\n"\n')
            (fakebin / 'docker').write_text(
                '#!/bin/sh\n'
                'if [ "$1" = image ]; then printf "%s|arm64\\n" "' + BASE + '"; exit 0; fi\n'
                'if [ "$1" = inspect ]; then exit 1; fi\n'
                'printf "%s\\n" "$@" > "$FAKE_DOCKER_RUN"\n'
            )
            for executable in (fakebin / 'uname', fakebin / 'docker'): executable.chmod(0o755)
            env = dict(os.environ, PATH=str(fakebin) + ':' + os.environ['PATH'], FAKE_DOCKER_RUN=str(root / 'args'))
            args = [str(envdir), str(train), str(checkpoint), str(vlm), str(sample), expected]
            checked = subprocess.run(['bash', str(SCRIPT), '--check', *args], env=env, text=True, capture_output=True)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            self.assertFalse((root / 'args').exists())
            done = subprocess.run(['bash', str(SCRIPT), '--run', *args], env=env, text=True, capture_output=True)
            self.assertEqual(done.returncode, 0, done.stderr)
            invocation = (root / 'args').read_text()
            for part in ('--network\nnone', '--read-only', '--cap-drop\nALL', '--memory\n4g',
                         '--cpus\n2', 'dst=/env,readonly', 'dst=/train,readonly',
                         'dst=/checkpoint,readonly', 'dst=/models/smolvlm2_500m_video,readonly',
                         '--vlm\n/models/smolvlm2_500m_video', '--device\ncpu', '--max-samples\n1'):
                self.assertIn(part, invocation)
            self.assertNotIn('/mc/sdk/robot_command', invocation)

    def test_bad_observation_hash_stops_before_docker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            envdir, train, checkpoint, vlm = [root / n for n in ('environment', 'training', 'checkpoint', 'vlm')]
            for p in (envdir / 'venv', train, checkpoint, vlm): p.mkdir(parents=True)
            (envdir / 'venv/pyvenv.cfg').write_text('dummy')
            sample = root / 'sample.jsonl'; sample.write_text('{}\n')
            run = subprocess.run(['bash', str(SCRIPT), '--run', str(envdir), str(train), str(checkpoint),
                                  str(vlm), str(sample), '0' * 64], text=True, capture_output=True)
            self.assertNotEqual(run.returncode, 0)
            self.assertIn('hash mismatch', run.stderr)

    def test_live_or_unmarked_input_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            envdir, train, checkpoint, vlm = [root / n for n in ('environment', 'training', 'checkpoint', 'vlm')]
            for p in (envdir / 'venv', train, checkpoint, vlm): p.mkdir(parents=True)
            (envdir / 'venv/pyvenv.cfg').write_text('dummy')
            sample = root / 'sample.jsonl'; sample.write_text('{}\n')
            digest = hashlib.sha256(sample.read_bytes()).hexdigest()
            run = subprocess.run(['bash', str(SCRIPT), '--run', str(envdir), str(train), str(checkpoint),
                                  str(vlm), str(sample), digest], text=True, capture_output=True)
            self.assertNotEqual(run.returncode, 0)
            self.assertIn('not explicitly unqualified historical', run.stderr)


if __name__ == '__main__':
    unittest.main()
