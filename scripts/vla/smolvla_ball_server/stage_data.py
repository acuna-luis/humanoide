#!/usr/bin/env python3
"""Stage private candidate data to a NEW user-owned server directory via SSH.

No Docker Hub, robot connection, training, or deletion. The archive contains
people in RGB images and a raw sensor log; use ONLY the user's server. Files
are hashed before transfer and verified again after extraction. Existing remote
paths are never overwritten. Failed transfers leave a partial private directory.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tarfile


TOOLS = ('prepare_ball_observations.py', 'prepare_ball_candidate_targets.py',
         'convert_ball_candidates_to_lerobot.py')
CODE_DIR = Path(__file__).resolve().parent.parent


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def safe_source(root, relative):
    if not isinstance(relative,str) or not re.fullmatch(r'[A-Za-z0-9_./-]+',relative):
        raise ValueError('unsafe candidate relative path')
    parts=Path(relative).parts
    if not parts or any(x in {'.','..'} for x in parts):
        raise ValueError('unsafe candidate relative path')
    current=root
    for part in parts:
        current=current/part
        if current.is_symlink():
            raise ValueError('symlinks are not accepted in candidate bundle')
    resolved=current.resolve(strict=True)
    if root not in resolved.parents or not resolved.is_file():
        raise ValueError('candidate file is missing or escapes bundle')
    return resolved


def plan(candidate_dir):
    root=candidate_dir.expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError('candidate bundle must be a directory')
    manifest_file=safe_source(root,'manifest.json')
    manifest=json.loads(manifest_file.read_text(encoding='utf-8'))
    if (manifest.get('schema') != 'cruzr_ball_candidate_targets_v1' or
        manifest.get('training_ready') is not False or
        manifest.get('physical_control_qualified') is not False or
        manifest.get('offline_experiment_only') is not True):
        raise ValueError('candidate bundle is not the unqualified offline format')
    segments=manifest.get('segments')
    if not isinstance(segments,list) or not segments:
        raise ValueError('no candidate segments')
    files={'candidate_bundle/manifest.json':(manifest_file,sha(manifest_file))}
    source_path=source_hash=None
    for s in segments:
        ident=s.get('id'); source=s.get('source_dir'); hashes=s.get('source_hashes')
        if not isinstance(ident,str) or not re.fullmatch(r'[A-Za-z0-9_-]+',ident):
            raise ValueError('unsafe segment id')
        if s.get('status') != 'candidate_success' or s.get('split') != 'inspection_train':
            raise ValueError('only candidate_success inspection_train may be staged')
        if not isinstance(source,str) or not Path(source).is_absolute() or not isinstance(hashes,dict):
            raise ValueError('source provenance missing')
        original=Path(source)
        if '..' in original.parts or not re.fullmatch(r'/[A-Za-z0-9_./-]+',source):
            raise ValueError('unsafe original source path for container mount')
        if source_path is not None and (source_path != source or source_hash != hashes.get('samples.jsonl')):
            raise ValueError('expected one original capture and a single consistent raw hash')
        source_path,source_hash=source,hashes.get('samples.jsonl')
        rel=f'{ident}/candidate_targets.jsonl'; rows_path=safe_source(root,rel)
        expected=s.get('candidate_targets_sha256')
        if sha(rows_path) != expected:
            raise ValueError(f'{ident}: candidate target checksum mismatch')
        if 'candidate_bundle/'+rel in files:
            raise ValueError('duplicate segment')
        files['candidate_bundle/'+rel]=(rows_path,expected)
        with rows_path.open(encoding='utf-8') as f:
            rows=[json.loads(line) for line in f]
        lo,hi=s.get('start_frame'),s.get('end_frame')
        if type(lo) is not int or type(hi) is not int or [r.get('source_frame') for r in rows] != list(range(lo,hi+1)):
            raise ValueError(f'{ident}: incomplete or reordered frames')
        for row in rows:
            frame=row['source_frame']; rel=f'{ident}/rgb/{frame:06}.png'
            if row.get('png_file') != f'rgb/{frame:06}.png':
                raise ValueError(f'{ident}: unsafe RGB path')
            img=safe_source(root,rel); expected=row.get('png_sha256')
            if not isinstance(expected,str) or sha(img) != expected:
                raise ValueError(f'{ident}: RGB checksum mismatch')
            files['candidate_bundle/'+rel]=(img,expected)
    raw=Path(source_path)/'samples.jsonl'
    if raw.is_symlink() or not raw.is_file() or not isinstance(source_hash,str) or sha(raw) != source_hash:
        raise ValueError('original raw capture missing, unsafe or hash mismatch')
    files['source_capture/samples.jsonl']=(raw,source_hash)
    for name in TOOLS:
        p=CODE_DIR/name
        if p.is_symlink() or not p.is_file():
            raise ValueError(f'converter source missing or unsafe: {name}')
        files['tools/'+name]=(p,sha(p))
    server_script=CODE_DIR/'smolvla_ball_server'/'convert_on_server.sh'
    if server_script.is_symlink() or not server_script.is_file():
        raise ValueError('server conversion wrapper missing or unsafe')
    files['tools/convert_on_server.sh']=(server_script,sha(server_script))
    return {'files':files,'source_container_path':source_path,
            'source_samples_sha256':source_hash,'candidate_manifest_sha256':sha(manifest_file),
            'privacy':'PRIVATE: images include people and samples include robot telemetry',
            'no_hub_upload':True,'no_robot_control':True,
            'size_bytes':sum(path.stat().st_size for path,_ in files.values())}


def archive(stream, data):
    meta={k:v for k,v in data.items() if k != 'files'}
    meta['file_sha256']={name:expected for name,(_,expected) in sorted(data['files'].items())}
    meta_bytes=(json.dumps(meta,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
    hashes={**meta['file_sha256'],'STAGING_METADATA.json':hashlib.sha256(meta_bytes).hexdigest()}
    sums=''.join(f'{digest}  {name}\n' for name,digest in sorted(hashes.items())).encode()
    with tarfile.open(fileobj=stream,mode='w|',format=tarfile.PAX_FORMAT) as tar:
        for name,(path,expected) in sorted(data['files'].items()):
            if path.is_symlink() or sha(path) != expected:
                raise ValueError(f'local file changed before transfer: {name}')
            info=tar.gettarinfo(str(path),arcname=name)
            if not info.isfile():
                raise ValueError('only regular files may be transferred')
            info.mode=0o600;info.uid=info.gid=0;info.uname=info.gname=''
            with path.open('rb') as f:
                tar.addfile(info,f)
        for name,content in [('STAGING_METADATA.json',meta_bytes),('SHA256SUMS',sums)]:
            info=tarfile.TarInfo(name);info.mode=0o600;info.size=len(content)
            tar.addfile(info,io.BytesIO(content))


def validate_remote(host, remote_dir):
    if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.@-]*',host):
        raise ValueError('host must be an SSH config alias or user@host without shell characters')
    if not re.fullmatch(r'/[A-Za-z0-9_./-]+',remote_dir) or '..' in Path(remote_dir).parts or remote_dir.endswith('/'):
        raise ValueError('remote directory must be an absolute, new safe path without .. or trailing slash')
    if remote_dir == '/':
        raise ValueError('remote directory cannot be root')


def ssh_args(host,port,command):
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError('SSH port must be between 1 and 65535')
    return ['ssh','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes',
            '-o','ConnectTimeout=8','-T','-p',str(port),'--',host,command]


def remote_check(host,port,remote_dir):
    parent=str(Path(remote_dir).parent)
    cmd=(f'test -d {shlex.quote(parent)} && test ! -e {shlex.quote(remote_dir)} && '
         f'test ! -L {shlex.quote(remote_dir)} && command -v tar >/dev/null && command -v sha256sum >/dev/null')
    subprocess.run(ssh_args(host,port,cmd),check=True,stdin=subprocess.DEVNULL)


def transfer(host,port,remote_dir,data):
    quoted=shlex.quote(remote_dir)
    cmd=(f'umask 077; mkdir -m 700 -- {quoted} && tar -xf - -C {quoted} && '
         f'cd -- {quoted} && sha256sum -c SHA256SUMS')
    process=subprocess.Popen(ssh_args(host,port,cmd),stdin=subprocess.PIPE)
    try:
        archive(process.stdin,data)
        process.stdin.close()
    except BaseException:
        try:
            process.stdin.close()
        except BrokenPipeError:
            pass
        process.wait()
        raise
    status=process.wait()
    if status:
        raise RuntimeError('SSH transfer or remote SHA verification failed; preserve and inspect partial directory')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__, epilog=
        'Ejemplo: stage_data.sh --check --candidates /datos/candidate_targets '
        '--host usuario@servidor --port 2649 --remote-dir /datos/nuevo_staging')
    actions=parser.add_mutually_exclusive_group(required=True)
    actions.add_argument('--check',action='store_true',help='verify local hashes and read-only remote destination check')
    actions.add_argument('--copy',action='store_true',help='create a new private remote directory and verify all copied hashes')
    parser.add_argument('--candidates',type=Path,required=True,help='local candidate_targets directory')
    parser.add_argument('--host',required=True,help='SSH config alias or user@host; existing trusted host key required')
    parser.add_argument('--port',type=int,required=True,help='SSH port, for example 2649')
    parser.add_argument('--remote-dir',required=True,help='new absolute destination on user-owned server')
    args=parser.parse_args(argv)
    try:
        validate_remote(args.host,args.remote_dir)
        if not 1 <= args.port <= 65535:
            raise ValueError('SSH port must be between 1 and 65535')
        data=plan(args.candidates)
        remote_check(args.host,args.port,args.remote_dir)
        summary={k:v for k,v in data.items() if k != 'files'}
        summary.update(file_count=len(data['files']),host=args.host,port=args.port,remote_dir=args.remote_dir)
        print(json.dumps(summary,ensure_ascii=False),flush=True)
        if args.copy:
            print('Copiando datos privados al servidor indicado; no se usan servicios externos.',flush=True)
            transfer(args.host,args.port,args.remote_dir,data)
            print('Copia y SHA256 verificados. Mantener candidate_bundle y source_capture en solo lectura.',flush=True)
            print(f"Montaje origen RO dentro del contenedor: {args.remote_dir}/source_capture:{data['source_container_path']}:ro")
            print(f"Montaje bundle RO: {args.remote_dir}/candidate_bundle:/work/candidates:ro")
    except (OSError,ValueError,RuntimeError,subprocess.CalledProcessError) as exc:
        print(f'ERROR: {exc}. No elimine automáticamente un directorio remoto parcial.',file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
