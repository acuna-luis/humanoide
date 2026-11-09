#!/usr/bin/env python3
"""Download ONLY two pinned, public model snapshots; no training or robot IO.

Called inside an isolated container by fetch_models.sh. Network-level destination
filtering is not provided by this program or Docker bridge.
"""
import datetime
import hashlib
import json
from pathlib import Path

from huggingface_hub import snapshot_download

ROOT = Path('/models')
SPECS = (
    ('smolvla_base', 'lerobot/smolvla_base',
     '5e8d12a6e2975b0e5e5fce7c8caf47c371d257b6'),
    ('smolvlm2_500m_video', 'HuggingFaceTB/SmolVLM2-500M-Video-Instruct',
     '7b375e1b73b11138ff12fe22c8f2822d8fe03467'),
)
PATTERNS = ['*.json', '*.safetensors', '*.txt', '*.model', 'README.md']


def file_digest(path):
    digest = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def main():
    metadata = {
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'snapshots': [],
        'license_metadata': 'apache-2.0 for each Hub model card; review README and terms',
        'purpose': 'public model weights only; no robot data or control',
    }
    hashes = []
    for folder, repo_id, revision in SPECS:
        target = ROOT / folder
        if target.exists():
            raise RuntimeError(f'Refusing to overwrite {target}')
        print(f'Downloading {repo_id}@{revision}', flush=True)
        snapshot_download(
            repo_id=repo_id, revision=revision, local_dir=str(target),
            allow_patterns=PATTERNS, token=False, max_workers=4,
        )
        required = ('config.json', 'model.safetensors', 'README.md')
        missing = [name for name in required if not (target / name).is_file()]
        if missing:
            raise RuntimeError(f'{repo_id} missing required files: {missing}')
        metadata['snapshots'].append({'repo_id': repo_id, 'revision': revision, 'path': folder})
        for path in sorted(target.rglob('*')):
            if path.is_file() and '.cache' not in path.relative_to(target).parts:
                hashes.append(f'{file_digest(path)}  {path.relative_to(ROOT).as_posix()}')
    (ROOT / 'SHA256SUMS').write_text('\n'.join(hashes) + '\n', encoding='utf-8')
    (ROOT / 'manifest.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    print('Public model files downloaded and hashed; no model has been loaded.', flush=True)


if __name__ == '__main__':
    main()
