#!/usr/bin/env python3
"""Optional additive Vision links. Default check; requires discovered web root."""
import argparse
import hashlib
from pathlib import Path
import shutil
from urllib.parse import urlsplit

MARKER = '<!-- cruzr-resident-controls-v1 -->'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--web-root', type=Path, required=True)
    p.add_argument('--executor-url', required=True)
    p.add_argument('--apply', action='store_true')
    p.add_argument('--backup-dir', type=Path)
    args = p.parse_args()
    url = urlsplit(args.executor_url)
    if url.scheme not in ('http', 'https') or not url.hostname or url.path not in ('','/') or url.query or url.fragment or url.username or any(c in args.executor_url for c in ('"',"'",'<','>','&')):
        p.error('Exact trusted executor base URL required')
    index = args.web_root/'index.html'
    if any(path.is_symlink() for path in (index, *index.parents)):
        p.error('Symlink web path refused')
    raw = index.read_text()
    if MARKER in raw or raw.count('</body>') != 1:
        p.error('Already integrated or unexpected index; preserve original')
    snippet = (MARKER+'\n<nav aria-label="Operación de cajas">'
        f'<a href="{args.executor_url.rstrip("/")}/#home" target="_blank" rel="noopener">Ir a HOME</a> · '
        f'<a href="{args.executor_url.rstrip("/")}/#cycle" target="_blank" rel="noopener">Ejecutar ciclo</a>'
        '</nav>\n')
    print('INDEX_SHA256='+hashlib.sha256(index.read_bytes()).hexdigest())
    print('Adds links only; authentication and fresh confirmation occur on Motion. No command sent.')
    if args.apply:
        if not args.backup_dir:
            p.error('--backup-dir NEW_DIRECTORY required')
        args.backup_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
        shutil.copy2(index, args.backup_dir/'index.html')
        staged = index.with_name('index.html.cruzr-new')
        with staged.open('x') as stream:
            stream.write(raw.replace('</body>', snippet+'</body>'))
        shutil.copystat(index, staged)
        staged.replace(index)
        print('WEB_LINKS_INSTALLED; original backup='+str(args.backup_dir/'index.html'))


if __name__ == '__main__':
    main()
