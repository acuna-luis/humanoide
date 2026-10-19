"""Offline video transport and SRS configuration boundaries; no robot access."""
import socket
import threading
import unittest

from scripts.teleoperation.configure_pico_srs_latency import SETTINGS, tuned_config
from scripts.teleoperation.pico_camera_relay import connect_pico


class SrsConfigTests(unittest.TestCase):
    def test_preserves_existing_rtc_and_http_configuration(self):
        original = ('listen 1935;\nvhost __defaultVhost__ {\n'
                    '    rtc { enabled on; rtmp_to_rtc on; }\n'
                    '    http_remux { enabled on; mount [vhost]/[app]/[stream].flv; }\n}\n')
        patched = tuned_config(original)
        self.assertEqual(patched.replace(SETTINGS, ''), original)
        self.assertEqual(tuned_config(patched), patched)

    def test_refuses_to_overwrite_existing_custom_delivery_rules(self):
        for directive in ['play { gop_cache on; }', 'publish { mr on; }',
                          'min_latency off;', 'tcp_nodelay off;']:
            with self.subTest(directive=directive), self.assertRaises(ValueError):
                tuned_config('vhost __defaultVhost__ {\n' + directive + '\n}\n')

    def test_ambiguous_or_modified_profile_is_rejected(self):
        for config in ['vhost other {\n}\n',
                       'vhost __defaultVhost__ {\n}\nvhost other {\n}\n',
                       'vhost __defaultVhost__ {\n' + SETTINGS.replace('mw_latency 20', 'mw_latency 350') + '}\n']:
            with self.subTest(config=config), self.assertRaises(ValueError):
                tuned_config(config)


class VideoSocketTests(unittest.TestCase):
    def test_transport_has_no_nagle_and_bounded_send_buffer(self):
        listener = socket.socket()
        listener.bind(('127.0.0.1', 0))
        listener.listen(1)
        accepted = []
        worker = threading.Thread(target=lambda: accepted.append(listener.accept()[0]), daemon=True)
        worker.start()
        try:
            with connect_pico('127.0.0.1', listener.getsockname()[1], 2) as client:
                self.assertEqual(client.getsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY), 1)
                self.assertEqual(client.gettimeout(), 1)
                # Linux reports twice the requested socket-buffer allocation.
                self.assertLessEqual(client.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF), 131072)
        finally:
            worker.join(timeout=2)
            for client in accepted:
                client.close()
            listener.close()


if __name__ == '__main__':
    unittest.main()
