"""Loopback HTTP tests; no robot, proxy, subprocess or vendor backend."""
import functools
import hashlib
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import unittest

from scripts.web.preview_scenario1 import Preview


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.original = b'<html><head><title>Original</title></head><body><div id="root"></div></body></html>'
        (self.root/'index.html').write_bytes(self.original)
        self.server = ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Preview,directory=str(self.root)))
        self.thread = threading.Thread(target=self.server.serve_forever,kwargs={'poll_interval':.01},daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(); self.temp.cleanup()

    def request(self,path='/',method='GET'):
        c = HTTPConnection('127.0.0.1',self.server.server_port,timeout=2)
        c.request(method,path);r=c.getresponse();result=r.status,dict(r.getheaders()),r.read();c.close();return result

    def test_original_snapshot_is_unchanged_and_injection_is_preview_only(self):
        status,headers,body=self.request()
        self.assertEqual(status,200)
        self.assertIn(b'data-mode="preview"',body)
        self.assertIn(b'controls.js',body)
        self.assertEqual((self.root/'index.html').read_bytes(),self.original)
        self.assertIn("connect-src 'self'",headers['Content-Security-Policy'])
        self.assertEqual(headers['Cache-Control'],'no-store')

    def test_all_mutating_methods_are_rejected(self):
        for method in ('POST','PUT','DELETE','PATCH'):
            self.assertEqual(self.request('/api/scenario1/jobs',method)[0],405)
        self.assertEqual((self.root/'index.html').read_bytes(),self.original)

    def test_robot_api_is_not_proxied(self):
        self.assertEqual(self.request('/api/v1/status')[0],503)
        self.assertEqual(self.request('/cc/api/connect')[0],503)

    def test_external_symlink_traversal_and_directory_listing_are_not_served(self):
        (self.root/'outside.txt').symlink_to('/etc/passwd')
        (self.root/'static').mkdir()
        for path in ('/outside.txt','/../etc/passwd','/static/'):
            # Extensionless paths are SPA entrypoints, never directory listings.
            status,_,body=self.request(path)
            self.assertNotIn(b'root:x:',body)
            self.assertNotIn(b'Directory listing',body)
            self.assertIn(status,(200,404))

    def test_controls_are_served_and_disabled_by_default_without_preview_attribute(self):
        status,headers,body=self.request('/_scenario1/controls.js')
        self.assertEqual(status,200)
        self.assertIn("dataset.mode === 'preview'",body.decode())
        self.assertIn('!preview || running',body.decode())
        self.assertNotIn('WebSocket(',body.decode())
        self.assertNotIn('fetch(',body.decode())
        self.assertIn(b'Ir a HOME',body)
        self.assertIn(b'Ejecutar ciclo',body)

    def test_navigation_routes_keep_the_overlay(self):
        self.assertIn(b'controls.js',self.request('/status')[2])
        self.assertIn(b'controls.js',self.request('/login')[2])


if __name__=='__main__':unittest.main()
