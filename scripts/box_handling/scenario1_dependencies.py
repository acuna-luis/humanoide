"""Plan and verify complete dependency reads, batched once per container.

The returned collector is a standalone read-only program. It rereads and hashes
every requested byte each invocation; there is no mtime-based or cross-stage
cache. The caller runs one collector per container and compares the returned
identity with its existing session identity before each physical stage.
"""
import copy
import hashlib
import json
from pathlib import PurePosixPath
import re
import xml.etree.ElementTree as ET


TASK_ROOT = '/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/'
HOME_PATH = TASK_ROOT + 'cruzr/home.xml'
HOME_META_PATH = '/opt/walker/manipulation_meta_tasks/lib/libmeta_move.so'
VISION_PATH = TASK_ROOT + 'vision/enable_transport_vision_switch.xml'


def _sha(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value):
        raise ValueError('Invalid dependency SHA256')
    return value


def _path(value, *, absolute=True):
    if (not isinstance(value, str) or not value or any(ord(character) < 32 for character in value)
            or PurePosixPath(value).is_absolute() != absolute
            or '..' in PurePosixPath(value).parts or str(PurePosixPath(value)) != value):
        raise ValueError('Invalid dependency path')
    return value


def _hashes(value, *, absolute=True):
    if not isinstance(value, dict):
        raise ValueError('Missing dependency hash map')
    return {_path(path, absolute=absolute): _sha(digest) for path, digest in value.items()}


def _merge(target, additions):
    for path, digest in additions.items():
        if path in target and target[path] != digest:
            raise ValueError('Conflicting hashes for one dependency')
        target[path] = digest


def plan_files(payload):
    """Return all original pins, plus the paths needed for HOME/vision checks."""
    try:
        manifest = payload['bundle']['manifest']
        package_id = manifest['id']
        if not isinstance(package_id, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}', package_id):
            raise ValueError('Invalid SPS package identity')
        root = '/opt/cruzr-front-box/' + package_id
        sources = _hashes(manifest['sources'], absolute=False)
        if not sources:
            raise ValueError('SPS source inventory must not be empty')
        common = {root + '/' + name: digest for name, digest in sources.items()}
        native = dict(common)
        _merge(native, _hashes(manifest['robot_files']))
        _merge(native, _hashes(manifest['native_binaries']))
        extra = _hashes(payload['extra_hashes'])
        _merge(native, extra)
        pins = payload['home_pins']
        if not isinstance(pins, dict) or set(pins) != {'accepted', 'direct', 'meta'}:
            raise ValueError('Malformed HOME pins')
        accepted = pins['accepted']
        if not isinstance(accepted, list) or not accepted:
            raise ValueError('Missing accepted HOME hashes')
        accepted = [_sha(value) for value in accepted]
        direct, meta = _sha(pins['direct']), _sha(pins['meta'])
        if direct not in accepted:
            raise ValueError('Direct HOME is absent from accepted hashes')
        return dict(native=native, ros2=common, home_path=HOME_PATH,
                    home_direct=direct, home_accepted=accepted,
                    home_meta_path=HOME_META_PATH, home_meta_sha256=meta,
                    vision_path=VISION_PATH, sps_package=package_id, extra=extra)
    except (KeyError, TypeError) as exc:
        raise ValueError('Malformed dependency payload') from exc


def collect_request(payload, native):
    """Build one JSON request for one container, without shell interpolation."""
    if type(native) is not bool:
        raise ValueError('Container role must be an explicit boolean')
    plan = plan_files(payload)
    if not native:
        return dict(paths=sorted(plan['ros2']), text_paths=[])
    paths = set(plan['native']) | {plan['home_path'], plan['vision_path']}
    return dict(paths=sorted(paths), text_paths=[plan['vision_path']],
                home_path=plan['home_path'], home_direct=plan['home_direct'],
                home_meta_path=plan['home_meta_path'])


def collector_source():
    """Standalone Python receiving the JSON request as its only argv argument."""
    return '''import hashlib,json,os,sys
import xml.etree.ElementTree as ET

request=json.loads(sys.argv[1])
common={'paths','text_paths'}
special={'home_path','home_direct','home_meta_path'}
if not isinstance(request,dict) or set(request) not in (common,common|special):
    raise ValueError('Malformed dependency collection request')
paths=request['paths']; text_paths=request['text_paths']
if not isinstance(paths,list) or not paths or len(paths)!=len(set(paths)):
    raise ValueError('Invalid dependency collection paths')
if not isinstance(text_paths,list) or len(text_paths)>1 or not set(text_paths)<=set(paths):
    raise ValueError('Invalid dependency text paths')
native='home_path' in request
if native and (request['home_path'] not in paths or len(text_paths)!=1):
    raise ValueError('Native dependency collection requires HOME and vision')
if not native and text_paths:
    raise ValueError('ROS2 dependency collection must not include text')
hashes={}; texts={}
def collect(path):
    digest=hashlib.sha256(); chunks=[]
    try:
        stream=open(path,'rb')
    except FileNotFoundError:
        prefix='/opt/cruzr-front-box/'
        if path.startswith(prefix):
            package=path[len(prefix):].split('/')[0]
            raise SystemExit('SPS_PACKAGE_MISSING: paquete '+package+
                ' ausente o incompleto en este contenedor; falta '+path+
                '. Las fuentes PC determinan el paquete requerido. Revise los limites locales; '
                'despues instale la misma version con python3 scripts/box_handling/'
                'front_box_integration.py --install y verifique con --check-runtime. '
                'No se usara otra version automaticamente.')
        raise SystemExit('DEPENDENCY_MISSING: falta el archivo requerido '+path)
    with stream:
        before=os.fstat(stream.fileno())
        while True:
            chunk=stream.read(1024*1024)
            if not chunk:break
            digest.update(chunk)
            if path in text_paths:chunks.append(chunk)
        after=os.fstat(stream.fileno())
    # These metadata only detect changes DURING the full read. They are never
    # used to skip hashing or to reuse a prior digest.
    if (before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_size,after.st_mtime_ns,after.st_ctime_ns):
        raise ValueError('Dependency changed during its full read')
    hashes[path]=digest.hexdigest()
    if path in text_paths:texts[path]=b''.join(chunks).decode('utf-8')
for path in paths:collect(path)
if native and hashes[request['home_path']]!=request['home_direct'] and request['home_meta_path'] not in hashes:
    collect(request['home_meta_path'])
report={'hashes':hashes}
if native:
    text=texts[text_paths[0]]
    ET.fromstring(text)
    report['vision_xml']=text
print(json.dumps(report,allow_nan=False))
'''


def _report(value, native):
    expected_keys = {'hashes', 'vision_xml'} if native else {'hashes'}
    if not isinstance(value, dict) or set(value) != expected_keys:
        raise ValueError('Malformed dependency report')
    hashes = _hashes(value['hashes'])
    if native and not isinstance(value['vision_xml'], str):
        raise ValueError('Missing vision XML text')
    return hashes


def validate_reports(payload, native_report, ros_report):
    """Validate every pin and special contract; preserve previous identity shape."""
    plan = plan_files(payload)
    native = _report(native_report, True)
    ros2 = _report(ros_report, False)
    if ros2 != plan['ros2']:
        raise ValueError('DEPENDENCY_CHANGED: ROS2 SPS source hashes do not match')
    home_hash = native.get(plan['home_path'])
    if home_hash not in plan['home_accepted']:
        raise ValueError('HOME no reconocido por el contrato actual')
    expected_paths = set(plan['native']) | {plan['home_path'], plan['vision_path']}
    if home_hash != plan['home_direct']:
        expected_paths.add(plan['home_meta_path'])
        if native.get(plan['home_meta_path']) != plan['home_meta_sha256']:
            raise ValueError('Biblioteca HOME no reconocida')
    if set(native) != expected_paths or any(native[path] != digest for path, digest in plan['native'].items()):
        raise ValueError('DEPENDENCY_CHANGED: native package/task/library hashes do not match')
    vision = native_report['vision_xml']
    try:
        vision_hash = hashlib.sha256(vision.encode('utf-8')).hexdigest()
        tree = ET.fromstring(vision)
    except (UnicodeError, ET.ParseError) as exc:
        raise ValueError('Malformed vision prerequisite XML') from exc
    if native[plan['vision_path']] != vision_hash:
        raise ValueError('Vision text does not match its full-read hash')
    actions = list(tree.iter('Action'))
    if len(actions) != 1 or actions[0].attrib != {'ID': 'MetaLook', 'start_vision_mode': 'transport_vision'}:
        raise ValueError('Prerrequisito de visión distinto del contrato MetaLook esperado')
    return dict(sps_package=plan['sps_package'], home_sha256=home_hash,
                vision_sha256=vision_hash, extra=copy.deepcopy(plan['extra']))
