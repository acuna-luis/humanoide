#!/usr/bin/env python3
"""Loopback-only read-only preview of the supplied compiled web + two controls.

No SSH, ROS, proxy, command execution or robot backend. Snapshot bytes are never
modified. Browser CSP blocks the vendor bundle's fixed remote endpoints.
"""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
ASSETS = Path(__file__).resolve().parent/'scenario1'
CSP = ("default-src 'self' data: blob:; script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
       "style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data: blob:; "
       "font-src 'self' data:; frame-src 'none'; object-src 'none'; base-uri 'self'; form-action 'self'")


class Preview(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Content-Security-Policy', CSP)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        super().end_headers()

    def send_bytes(self, body, content_type):
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path in ('/_scenario1/controls.js', '/_scenario1/controls.css'):
            name = path.rsplit('/', 1)[-1]
            self.send_bytes((ASSETS/name).read_bytes(), 'text/javascript; charset=utf-8' if name.endswith('.js') else 'text/css; charset=utf-8')
            return
        if path.startswith(('/api/', '/cc/')):
            self.send_error(503, 'Offline preview; no robot backend')
            return
        if path == '/' or path == '/index.html' or ('.' not in path.rsplit('/', 1)[-1]):
            html = (Path(self.directory)/'index.html').read_text()
            additions = ('<link rel="stylesheet" href="/_scenario1/controls.css">'
                         '<script defer src="/_scenario1/controls.js" data-mode="preview"></script>')
            html = html.replace('</head>', additions+'</head>', 1)
            self.send_bytes(html.encode(), 'text/html; charset=utf-8')
            return
        # No directory listing, traversal or serving symlinks/private sources.
        target = (Path(self.directory)/path.lstrip('/')).resolve()
        if not target.is_relative_to(Path(self.directory).resolve()) or not target.is_file():
            self.send_error(404)
            return
        super().do_GET()

    def do_POST(self):
        self.send_error(405, 'Preview never accepts commands')
    do_PUT = do_DELETE = do_PATCH = do_POST


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, default=ROOT/'actual_20261021T103405')
    parser.add_argument('--port', type=int, default=18774)
    args = parser.parse_args()
    snapshot = args.snapshot.resolve()
    if not (snapshot/'index.html').is_file():
        parser.error('Snapshot index.html not found')
    server = ThreadingHTTPServer(('127.0.0.1', args.port), partial(Preview, directory=str(snapshot)))
    print(f'Vista previa sin robot: http://127.0.0.1:{server.server_port}', flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()


if __name__ == '__main__': main()
