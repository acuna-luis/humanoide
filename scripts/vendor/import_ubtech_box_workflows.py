#!/usr/bin/env python3
"""Archive small Cruzr task files by read-only SSH; never installs or runs tasks.

Original robot bytes are retained in private-dir. Repo snapshots omit credentials.
"""
import argparse
import base64
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
from lxml import etree as LX
import xml.etree.ElementTree as ET
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from collect_estop_available_readonly import execute

VISION = '/opt/walker/task_manager/share/task_manager/config/cruzr_s2'
MOTION = '/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config'
META = '/opt/walker/manipulation_meta_tasks/share/manipulation_meta_tasks/config/meta_clamp'
MAIN = ['utars_task_canada_wrc_20250930_start.xml', 'utars_task_zhucheng_env_20260428_start.xml']
CREDENTIAL = re.compile(r'password|passwd|contrase[nñ]a|密码|账号|secret[_ -]?key|api[_ -]?key|access[_ -]?token', re.I)
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fetch(host, container, root, names=None):
    # Only fixed config roots, text extensions and bounded regular files are read.
    script = '''import base64,json,pathlib,hashlib
root=pathlib.Path(ROOT)
files=sorted(root.rglob('*')) if NAMES is None else [root/n for n in NAMES]
result=[]
for p in files:
 if not p.is_file() or p.suffix not in ('.xml','.yaml'): continue
 if not p.resolve().is_relative_to(root.resolve()): raise ValueError('Path escapes root')
 data=p.read_bytes()
 if len(data)>2000000: raise ValueError('Unexpected large config')
 result.append(dict(path=str(p.relative_to(root)),sha256=hashlib.sha256(data).hexdigest(),data=base64.b64encode(data).decode()))
print(json.dumps(result))
'''.replace('ROOT', repr(root)).replace('NAMES', repr(names))
    reply = execute(host, ['docker', 'exec', container, 'python3', '-c', script])
    if reply.get('returncode') != 0:
        raise RuntimeError('Read-only export failed: '+host+' '+root)
    rows = json.loads(reply['stdout'])
    for row in rows:
        row['bytes'] = base64.b64decode(row.pop('data'), validate=True)
        if sha(row['bytes']) != row['sha256']:
            raise ValueError('Export checksum mismatch')
    return {v['path']: v for v in rows}


def parse(data):
    return ET.fromstring(data)


def sanitize_docx(source, target):
    """Remove credential paragraphs while preserving namespace maps and images."""
    if target.exists():
        raise FileExistsError(target)
    count=0
    with tempfile.NamedTemporaryFile(dir=target.parent, suffix='.tmp', delete=False) as f:
        temporary=Path(f.name)
    try:
        with ZipFile(source) as zin, ZipFile(temporary,'w') as zout:
            for entry in zin.infolist():
                data=zin.read(entry.filename)
                if entry.filename.endswith('.xml'):
                    tree=LX.fromstring(data, LX.XMLParser(resolve_entities=False, no_network=True))
                    changed=False
                    for p in tree.iter(W+'p'):
                        value=''.join(t.text or '' for t in p.iter(W+'t'))
                        if CREDENTIAL.search(value):
                            ts=list(p.iter(W+'t'))
                            for t in ts: t.text=''
                            if ts: ts[0].text='[Credenciales omitidas / Access credentials redacted]'
                            count+=1; changed=True
                    if CREDENTIAL.search(''.join(tree.itertext())):
                        raise ValueError('Unredacted credential field in DOCX: '+entry.filename)
                    if changed:
                        data=LX.tostring(tree, encoding='UTF-8', xml_declaration=True, standalone=True)
                zout.writestr(entry,data)
        temporary.replace(target)
        return count
    finally:
        temporary.unlink(missing_ok=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--snapshot-dir', type=Path, required=True)
    ap.add_argument('--docs-dir', type=Path, required=True)
    ap.add_argument('--private-dir', type=Path, required=True)
    ap.add_argument('--docx', type=Path, action='append', default=[])
    a = ap.parse_args()
    repo = Path(__file__).resolve().parents[2]
    if a.private_dir.resolve().is_relative_to(repo):
        ap.error('--private-dir must be outside the repository')
    for directory in (a.snapshot_dir, a.docs_dir, a.private_dir):
        directory.mkdir(parents=True, exist_ok=False)
    manifest = dict(captured_at=dt.datetime.now().astimezone().isoformat(),
                    scope='read-only installed snapshot, not deployment or physical qualification',
                    robot_mutations=0, movement_commands=0, files=[], unresolved=[], xml_parse_errors=[],
                    collector_path='scripts/vendor/import_ubtech_box_workflows.py',
                    collector_sha256=sha(Path(__file__).read_bytes()))
    manifest['runtime_images']=[]
    for host, name in [('vision','walker-system.task_manager-1'), ('motion','walker-motion.manipulation_robot_app-1')]:
        result=execute(host, ['docker','inspect','--format','{{.Config.Image}}\n{{.Image}}',name])
        if result.get('returncode') != 0:
            raise RuntimeError('Cannot read container identity: '+host)
        image, image_id=result['stdout'].strip().splitlines()
        manifest['runtime_images'].append(dict(host=host,container=name,image=image,image_id=image_id))
    vision = fetch('vision', 'walker-system.task_manager-1', VISION)
    for name in MAIN:
        if name not in vision:
            raise ValueError('Expected scenario XML missing: '+name)
    pending = set()
    for name in MAIN:
        for e in parse(vision[name]['bytes']).iter():
            n = e.get('task_name') or e.get('TaskName')
            if n and '{' not in n:
                pending.add(n+'.xml')
    motion = {}; meta_names = set(); visited=set()
    while pending:
        visited.update(pending)
        batch = fetch('motion', 'walker-motion.manipulation_robot_app-1', MOTION, sorted(pending))
        for missing in sorted(pending-set(batch)):
            manifest['unresolved'].append(dict(kind='motion_task', path=missing))
        motion.update(batch); pending = set()
        for row in batch.values():
            for e in parse(row['bytes']).iter():
                n = e.get('task_name') or e.get('TaskName')
                if n and '{' not in n and n+'.xml' not in visited:
                    pending.add(n+'.xml')
                if e.get('ID') == 'MetaClamp' and e.get('name'):
                    meta_names.add(e.get('name')+'.yaml')
    meta = fetch('motion', 'walker-motion.manipulation_robot_app-1', META, sorted(meta_names))
    for missing in sorted(meta_names-set(meta)):
        manifest['unresolved'].append(dict(kind='meta_clamp', path=missing))
    for label, host, container, root, rows in [
        ('vision/cruzr_s2', 'vision', 'walker-system.task_manager-1', VISION, vision),
        ('motion/tasks', 'motion', 'walker-motion.manipulation_robot_app-1', MOTION, motion),
        ('motion/meta_clamp', 'motion', 'walker-motion.manipulation_robot_app-1', META, meta)]:
        for name, row in sorted(rows.items()):
            data = row['bytes']; text = data.decode('utf-8')
            private = a.private_dir/label/name; private.parent.mkdir(parents=True, exist_ok=True); private.write_bytes(data)
            if CREDENTIAL.search(text):
                raise ValueError('Credential-like content requires review; not copied to repo: '+label+'/'+name)
            target = a.snapshot_dir/label/name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
            if target.suffix == '.xml':
                try: parse(data)
                except ET.ParseError as exc: manifest['xml_parse_errors'].append(dict(path=str(target.relative_to(a.snapshot_dir)), error=str(exc)))
            manifest['files'].append(dict(path=str(target.relative_to(a.snapshot_dir)), host=host,
                container=container, original_path=root+'/'+name, sha256=sha(data), bytes=len(data),
                source='installed_on_robot; may include local customizations', modified=False))
    # A top-level catalog is not a declaration that other workflows/dependencies were qualified.
    catalog=[]
    for name, row in sorted(vision.items()):
        if '/' in name or not name.endswith('.xml'): continue
        try:
            tree=parse(row['bytes']); points=[]
            for e in tree.iter():
                n=e.get('target_id') or (e.get('ID','').removeprefix('logo_nav_') if e.get('ID','').startswith('logo_nav_') else '')
                if n and n not in points: points.append(n)
            catalog.append(dict(file=name,points=points,scenario=MAIN.index(name)+1 if name in MAIN else None,
                includes=[e.get('path') for e in tree.iter('include')]))
        except ET.ParseError:
            catalog.append(dict(file=name,parse_error=True))
    (a.snapshot_dir/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    doc_manifest=[]
    for source in a.docx:
        raw=source.read_bytes(); original=a.private_dir/'documents'/source.name;original.parent.mkdir(exist_ok=True);original.write_bytes(raw)
        lang='es' if source.name.endswith('_ES.docx') else 'zh'
        target=a.docs_dir/('procedimiento_traslado_cajas_'+lang+'_sin_credenciales.docx')
        if target.exists(): raise ValueError('Duplicate document language')
        redacted=sanitize_docx(source, target)
        with ZipFile(target) as z:
            tree=ET.fromstring(z.read('word/document.xml'))
            paragraphs=[''.join(t.text or '' for t in p.iter(W+'t')) for p in tree.iter(W+'p')]
            md='\n\n'.join(p for p in paragraphs if p)
            (a.docs_dir/('texto_'+lang+'.md')).write_text('# Procedimiento UBTECH — '+lang+'\n\nExtracción textual; figuras y formato en el DOCX saneado. Credenciales omitidas.\n\n'+md+'\n')
        doc_manifest.append(dict(source_name=source.name,original_sha256=sha(raw),repo_file=target.name,
            repo_sha256=sha(target.read_bytes()),redacted_paragraphs=redacted,
            original_location=str(source),private_copy=str(original.resolve())))
    (a.docs_dir/'provenance.json').write_text(json.dumps(doc_manifest,ensure_ascii=False,indent=2)+'\n')
    (a.snapshot_dir/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(files=len(manifest['files']),workflows=len(catalog),motion=len(motion),meta=len(meta),
         unresolved=manifest['unresolved'],xml_parse_errors=manifest['xml_parse_errors'],documents=len(doc_manifest)),indent=2))


if __name__=='__main__':
    main()
