"""Remote implementation. Invoked by switch_effector.py; no standalone default action."""
import base64
import hashlib
import http.client
import io
import json
import os
from pathlib import Path
import posixpath
import socket
import stat
import subprocess
import sys
import tarfile
import tempfile
import yaml
from urllib.parse import quote

# effector_profile_config is injected as a module by the SSH launcher.
if __package__:
    from .effector_profile_config import PROFILES, SERVICES, ENI_SHA, GUARD_SHA, validate_container, plan_files
    from .prepare_v4_bus_profile import prepare as prepare_bus
else:
    from effector_profile_config import PROFILES, SERVICES, ENI_SHA, GUARD_SHA, validate_container, plan_files
    from effector_bus import prepare as prepare_bus

CONFIG = {
    'motion': {'compose.yml': '/home/walker/.config/udoke/walker/compose.yml',
               'db.json': '/home/walker/.config/udoke/db.json'},
    'vision': {'compose.yml': '/home/walker/.config/udoke/walker/compose.yml',
               'system.metafile.yml': '/home/walker/.config/udoke/walker/.metafiles/system.metafile.yml'},
}
LIMIT = 256 * 1024 * 1024
ENI = '/opt/walker/ubt_ethercat_master/bin/eni_cruzr_kw_unified_noimu.xml'


def run(command):
    return subprocess.check_output(command, timeout=90)


class DockerSocket(http.client.HTTPConnection):
    def __init__(self):
        super().__init__('localhost', timeout=30)
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect('/var/run/docker.sock')


def docker_archive(container, path, head=False):
    client = DockerSocket()
    try:
        client.request('HEAD' if head else 'GET', '/containers/' + quote(container, safe='') + '/archive?path=' + quote(path, safe=''))
        response = client.getresponse()
        if response.status != 200:
            raise RuntimeError('Docker archive read failed: ' + path)
        if head:
            return json.loads(base64.b64decode(response.getheader('X-Docker-Container-Path-Stat')))
        raw = response.read(LIMIT + 1)
        if len(raw) > LIMIT:
            raise RuntimeError('Archive exceeds reviewed limit')
        return raw
    finally:
        client.close()


def container_file(container, path):
    with tarfile.open(fileobj=io.BytesIO(docker_archive(container, path))) as archive:
        members=archive.getmembers()
        if len(members)!=1 or not members[0].isfile():
            raise RuntimeError('Expected one regular file: '+path)
        return archive.extractfile(members[0]).read()


def discover(host):
    services = SERVICES if host == 'motion' else ['system.control_center']
    ids = run(['docker', 'ps', '-aq', '--filter', 'label=com.docker.compose.project=walker']).decode().split()
    if not ids:
        raise RuntimeError('No walker containers discovered')
    items = json.loads(run(['docker', 'inspect', *ids]))
    selected = {}
    for service in services:
        matches = [c for c in items if c['Config']['Labels'].get('com.docker.compose.service') == service]
        if len(matches) != 1:
            raise RuntimeError('Missing/ambiguous service: ' + service)
        selected[service] = matches[0]
    extras = [c['Name'] for c in items if c['Config']['Labels'].get('com.docker.compose.service') not in services
              and c['State']['Running'] and any(x.startswith('HW_TYPE=') for x in c['Config']['Env'])]
    if host == 'motion' and extras:
        raise RuntimeError('Additional active HW_TYPE services require review')
    for c in selected.values():
        value = dict(x.split('=', 1) for x in c['Config']['Env']).get('HW_TYPE')
        if value not in PROFILES.values():
            raise RuntimeError('Unknown effective HW_TYPE')
    return selected


def write_json(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)


def mounted_path(path, mounts):
    """Mount contents belong to the host/volume, never to a writable-layer tar."""
    path = posixpath.normpath('/' + path.lstrip('/'))
    for mount in mounts:
        destination = posixpath.normpath(mount['Destination'])
        if destination == '/' or path == destination or path.startswith(destination + '/'):
            return True
    return False


def restore_archive(path, mounts, manifest):
    """Filter old backups too, preserving their original bytes on disk."""
    buffer = io.BytesIO()
    seen, skipped, restored = set(), [], []
    with tarfile.open(path) as source, tarfile.open(fileobj=buffer, mode='w') as target:
        for member in source.getmembers():
            if member.name.startswith('/') or '..' in member.name.split('/'):
                raise RuntimeError('Unsafe backup member')
            if member.name != posixpath.normpath(member.name) or member.name in ('', '.'):
                raise RuntimeError('Noncanonical backup member')
            name = '/' + member.name
            if name in seen or name not in manifest or not (member.isfile() or member.issym()):
                raise RuntimeError('Unexpected/duplicate backup member')
            seen.add(name)
            expected = manifest[name]
            data = source.extractfile(member).read() if member.isfile() else None
            if member.isfile():
                if expected != {'sha256': hashlib.sha256(data).hexdigest()}:
                    raise RuntimeError('Backup member hash differs from manifest')
            elif expected != {'link': member.linkname} or member.linkname.startswith('/') or '..' in member.linkname.split('/'):
                raise RuntimeError('Unsafe/mismatched backup link')
            if mounted_path(name, mounts):
                skipped.append(name)
                continue
            if any(posixpath.normpath(m['Destination']).startswith(name + '/') for m in mounts):
                raise RuntimeError('Backup file is an ancestor of a mount')
            if member.issym() and mounted_path(posixpath.join(posixpath.dirname(name), member.linkname), mounts):
                raise RuntimeError('Backup link resolves into a mount')
            clean = tarfile.TarInfo(member.name)
            for field in ('mode', 'uid', 'gid', 'mtime', 'type', 'linkname', 'uname', 'gname', 'size'):
                setattr(clean, field, getattr(member, field))
            target.addfile(clean, io.BytesIO(data) if data is not None else None)
            restored.append(name)
    if seen != set(manifest):
        raise RuntimeError('Incomplete backup members')
    return buffer.getvalue(), restored, skipped


def selected_paths(container, mounts=()):
    result = []
    diff = run(['docker', 'diff', container]).decode()
    for line in diff.splitlines():
        kind, path = line[:1], line[2:]
        if mounted_path(path, mounts):
            continue
        transient = ('/__pycache__/' in path or path.endswith('.pyc')
                     or path.startswith(('/var/log/', '/run/', '/var/cache/'))
                     or path == '/root/.bash_history'
                     or (path.startswith('/tmp/') and not path.endswith('.motion')))
        if transient:
            continue
        if kind == 'D':
            raise RuntimeError('Deleted writable-layer path requires review: ' + path)
        if kind not in ('A', 'C'):
            raise RuntimeError('Unknown docker diff operation')
        info = docker_archive(container, path, head=True)
        if info['mode'] & (1 << 31):  # Go FileMode directory flag.
            continue
        if info['mode'] & ~0o777 and not info['mode'] & (1 << 27):
            raise RuntimeError('Unsupported special file: ' + path)
        result.append(path)
    return sorted(set(result))


def make_backup(stage, original, host):
    manifests = {}
    for service, c in original.items():
        manifest = {}
        with tarfile.open(stage / (service + '.tar'), 'w') as output:
            for path in selected_paths(c['Id'], c['Mounts']):
                raw = docker_archive(c['Id'], path)
                with tarfile.open(fileobj=io.BytesIO(raw)) as source:
                    members = source.getmembers()
                    if len(members) != 1 or not (members[0].isfile() or members[0].issym()):
                        raise RuntimeError('Unexpected archive members: ' + path)
                    member = members[0]
                    member.name = path.lstrip('/')
                    member.pax_headers = {k:v for k,v in member.pax_headers.items() if k not in ('path','linkpath')}
                    if member.isfile():
                        data = source.extractfile(member).read()
                        manifest[path] = {'sha256': hashlib.sha256(data).hexdigest()}
                        output.addfile(member, io.BytesIO(data))
                    else:
                        # Retain existing links, reject link escapes from their parent tree.
                        if member.linkname.startswith('/') or '..' in Path(member.linkname).parts:
                            raise RuntimeError('Custom link requires review: ' + path)
                        manifest[path] = {'link': member.linkname}
                        output.addfile(member)
        manifests[service] = manifest
    write_json(stage / 'manifests.json', manifests)
    write_json(stage / 'archives.json', {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in stage.glob('*.tar')})
    for name, path in CONFIG[host].items():
        (stage / (name + '.before')).write_bytes(Path(path).read_bytes())


def verify_files(stage, items, live=False, profile=None):
    manifests = json.loads((stage / 'manifests.json').read_text())
    for service, manifest in manifests.items():
        for path, expected in manifest.items():
            if mounted_path(path, items[service]['Mounts']):
                continue
            raw = docker_archive(items[service]['Id'], path)
            with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
                member = archive.getmembers()[0]
                if 'sha256' in expected:
                    actual = hashlib.sha256(archive.extractfile(member).read()).hexdigest()
                    if actual != expected['sha256']:
                        if profile=='v4' and path==ENI and actual==ENI_SHA:
                            continue
                        # Bus selection can legitimately update its own last_eni after boot.
                        if live and path.endswith('/ubt_ethercat_master/config/dynamic_config.yaml'):
                            with tarfile.open(stage/(service+'.tar')) as before_archive:
                                before=yaml.safe_load(before_archive.extractfile(path.lstrip('/')).read())
                            after=yaml.safe_load(archive.extractfile(member).read())
                            known={'eni_cruzr_kw_noimu.xml','eni_cruzr_kw_unified_noimu.xml'}
                            if isinstance(before,dict) and isinstance(after,dict) and before.get('last_eni') in known and after.get('last_eni') in known:
                                before.pop('last_eni');after.pop('last_eni')
                                if before==after:continue
                        raise RuntimeError('Restored file hash differs: ' + path)
                elif not member.issym() or member.linkname != expected['link']:
                    raise RuntimeError('Restored link differs: ' + path)


def atomic_write(path, value):
    path = Path(path)
    before = path.stat()
    if before.st_uid != os.getuid():
        raise RuntimeError('Unexpected config owner')
    fd, tmp = tempfile.mkstemp(prefix='.effector-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(tmp, stat.S_IMODE(before.st_mode))
        os.chown(tmp,before.st_uid,before.st_gid)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def restore_files(stage, current):
    manifests = json.loads((stage / 'manifests.json').read_text())
    for name, digest in json.loads((stage / 'archives.json').read_text()).items():
        if hashlib.sha256((stage / name).read_bytes()).hexdigest() != digest:
            raise RuntimeError('Backup hash mismatch')
    report = {}
    for service, c in current.items():
        data, restored, skipped = restore_archive(stage / (service + '.tar'), c['Mounts'], manifests[service])
        if restored:
            subprocess.run(['docker', 'cp', '-a', '-', c['Id']+':/'], input=data, check=True, timeout=45)
        report[service] = {'restored': restored, 'preserved_mounts': skipped}
    verify_files(stage, current)
    return report


def verify_sources(stage, host, profile):
    before = {name: (stage / (name + '.before')).read_bytes() for name in CONFIG[host]}
    global_hw = None
    if host == 'vision':
        global_hw = json.loads(Path('/home/walker/.config/udoke/db.json').read_text()).get('envs', {}).get('HW_TYPE')
    expected = plan_files(host, before, profile, global_hw)
    if any(Path(CONFIG[host][name]).read_bytes() != value for name, value in expected.items()):
        raise RuntimeError('Persistent configuration differs from the session plan')


def main(request):
    host, phase = request['host'], request['phase']
    current = discover(host)
    state_root=Path('/home/walker/.local/share/cruzr-effector-switch')
    active=state_root/'active.json'
    if phase == 'snapshot':
        extra = {}
        if host == 'vision':
            extra['guard_sha256']=hashlib.sha256(Path('/etc/walker/boot/cruzr_cc_start_when_ready.py').read_bytes()).hexdigest()
            extra['global_hw_type']=json.loads(Path('/home/walker/.config/udoke/db.json').read_text()).get('envs',{}).get('HW_TYPE')
        else:
            extra['eni_sha256']=hashlib.sha256(container_file(current['motion.hw']['Id'],ENI)).hexdigest()
        ros_ids=run(['docker','ps','-q','--filter','label=com.docker.compose.project=walker','--filter','label=com.docker.compose.service=ros.ros2']).decode().split()
        if len(ros_ids)!=1:raise RuntimeError('Missing/ambiguous active ROS container')
        return {'containers': current, 'active_session': json.loads(active.read_text()) if active.exists() else None, 'ros_container': ros_ids[0], 'extra': extra, 'files': {name: base64.b64encode(Path(path).read_bytes()).decode()
                for name, path in CONFIG[host].items()}}
    stage = Path('/home/walker/.local/share/cruzr-effector-switch') / request['session']
    if phase == 'backup':
        if active.exists():raise RuntimeError('An unfinished effector session requires review')
        for name,path in CONFIG[host].items():
            if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=request['expected_files'][name]:
                raise RuntimeError('Configuration changed after the reviewed plan')
        if {s:c['Id'] for s,c in current.items()}!=request['expected_ids']:
            raise RuntimeError('Containers changed after inventory')
        stage.mkdir(mode=0o700, parents=True, exist_ok=False)
        write_json(active,{'session':request['session'],'profile':request['profile']})
        write_json(stage / 'original.json', current)
        make_backup(stage, current, host)
        if host=='motion':
            (stage/'eni.before.xml').write_bytes(container_file(current['motion.hw']['Id'],ENI))
        return {'stage': str(stage), 'archives': json.loads((stage / 'archives.json').read_text())}
    if phase == 'export':
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
            archive.add(stage, arcname='session')
        data = buffer.getvalue()
        if len(data) > LIMIT:
            raise RuntimeError('External backup exceeds size limit')
        return {'base64': base64.b64encode(data).decode(), 'sha256': hashlib.sha256(data).hexdigest()}
    if not active.exists() or json.loads(active.read_text())!={'session':request['session'],'profile':request['profile']}:
        raise RuntimeError('Active session mismatch')
    original = json.loads((stage / 'original.json').read_text())
    if 'expected_ids' in request and {s:c['Id'] for s,c in current.items()} != request['expected_ids']:
        raise RuntimeError('Container identity changed after recovery inventory')
    for name, digest in request.get('expected_staged_files', {}).items():
        if '/' in name or name in ('', '.', '..') or hashlib.sha256((stage/name).read_bytes()).hexdigest() != digest:
            raise RuntimeError('Remote backup differs from verified external backup')
    for service, c in current.items():
        if c['Image'] != original[service]['Image']:
            raise RuntimeError('Vendor image changed during operation')
    if phase in ('stop','install') and any(current[s]['Id']!=original[s]['Id'] for s in current):
        raise RuntimeError('Container identity drift')
    if phase == 'complete':
        for service,c in current.items():validate_container(original[service],c,request['profile'])
        verify_files(stage,current,live=True,profile=request['profile'])
        write_json(stage/'completed.json',{'profile':request['profile'],'verified':True})
        active.unlink()
        return {'completed':True}
    if phase == 'stop':
        subprocess.run(['docker', 'stop', '--time', '5', *[c['Id'] for c in current.values()]], check=True, timeout=45)
        return {'stopped': True}
    if any(c['State']['Running'] for c in current.values()):
        raise RuntimeError('Containers must remain stopped')
    if phase == 'validate':
        verify_sources(stage, host, request['profile'])
        for service,c in current.items():validate_container(original[service],c,request['profile'])
        # Validate every tar without writing into a container.
        manifests=json.loads((stage/'manifests.json').read_text())
        for service,c in current.items():restore_archive(stage/(service+'.tar'),c['Mounts'],manifests[service])
        return {'validated':True,'started':False}
    if phase == 'verify-stopped':
        verify_sources(stage, host, request['profile'])
        for service,c in current.items():validate_container(original[service],c,request['profile'])
        verify_files(stage,current,profile=request['profile'])
        return {'files_verified':True,'started':False}
    if phase == 'install':
        pending = {}
        for name, path in CONFIG[host].items():
            before = (stage / (name + '.before')).read_bytes()
            if Path(path).read_bytes() != before:
                raise RuntimeError('Configuration drift since backup')
            pending[path] = base64.b64decode(request['files'][name])
        for path, value in pending.items():
            atomic_write(path, value)
        return {'installed': True, 'started': False}
    profile = request['profile']
    if phase in ('recreate', 'restore'):
        verify_sources(stage, host, profile)
        root = '/home/walker/.config/udoke/walker'
        command = ['docker', 'compose', '--project-name', 'walker', '--project-directory', root, '-f', root+'/compose.yml']
        config = json.loads(run(command + ['config', '--format', 'json']))
        for service in current:
            c = config['services'][service]
            if c.get('depends_on') or c['environment'].get('HW_TYPE') != PROFILES[profile]:
                raise RuntimeError('Unexpected dependency or HW_TYPE before recreation')
            if c['image'] != original[service]['Config']['Image']:
                raise RuntimeError('Compose image reference drift')
        if phase == 'recreate':
            subprocess.run(command + ['create', '--no-build', '--pull', 'never', '--force-recreate', *current], check=True, timeout=60)
        new = discover(host)
        for service, c in new.items():
            validate_container(original[service], c, profile)
        restoration = restore_files(stage, new)
        if host=='motion' and profile=='v4':
            c=new['motion.hw']['Id']
            before=container_file(c,ENI)
            if hashlib.sha256(before).hexdigest()!=ENI_SHA:
                fixed=prepare_bus(before)
                if hashlib.sha256(fixed).hexdigest()!=ENI_SHA:raise RuntimeError('Unexpected ENI derivative')
                buffer=io.BytesIO()
                with tarfile.open(fileobj=buffer,mode='w') as archive:
                    member=tarfile.TarInfo(ENI.lstrip('/'));member.size=len(fixed);member.mode=0o644
                    archive.addfile(member,io.BytesIO(fixed))
                subprocess.run(['docker','cp','-a','-',c+':/'],input=buffer.getvalue(),check=True,timeout=30)
            if hashlib.sha256(container_file(c,ENI)).hexdigest()!=ENI_SHA:raise RuntimeError('ENI verification failed')
        return {'recreated': phase == 'recreate', 'restoration': restoration,
                'restored_and_verified': True, 'started': False}
    if phase == 'start':
        verify_sources(stage, host, profile)
        if profile=='v4':
            if host=='motion' and hashlib.sha256(container_file(current['motion.hw']['Id'],ENI)).hexdigest()!=ENI_SHA:
                raise RuntimeError('ENI drift before start')
            if host=='vision' and hashlib.sha256(Path('/etc/walker/boot/cruzr_cc_start_when_ready.py').read_bytes()).hexdigest()!=GUARD_SHA:
                raise RuntimeError('Boot guard drift before start')
        for service, c in current.items():
            validate_container(original[service], c, profile)
        verify_files(stage, current, profile=profile)
        subprocess.run(['docker', 'start', *[c['Id'] for c in current.values()]], check=True, timeout=30)
        return {'started': True}
    raise ValueError('Unknown phase')


if __name__ == '__main__':
    try:
        result = main(json.loads(sys.argv[1]))
        print('EFFECTOR_JSON=' + json.dumps(result))
    except Exception as error:
        print('EFFECTOR_ERROR=' + type(error).__name__ + ': ' + str(error), file=sys.stderr)
        sys.exit(1)
