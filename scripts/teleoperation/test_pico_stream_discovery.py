"""Exercise production peer discovery with stale USB sockets; no robot access."""
import os
from pathlib import Path
import subprocess
import unittest


SCRIPT = Path(__file__).with_name('cruzr_pico_teleop_pc.sh').read_text()
FUNCTIONS = ('endpoint_ip() {' + SCRIPT.split('endpoint_ip() {', 1)[1]
             .split('\nhas_established_pico_stream()', 1)[0])


class StreamDiscoveryTests(unittest.TestCase):
    def discover(self, sockets, addresses, pc='', pico=''):
        setup = '''set -Eeuo pipefail
ss() { printf '%s\\n' "$TEST_SOCKETS"; }
ip() { printf '%s\\n' "$TEST_ADDRESSES"; }
pc_pico_ip="$TEST_PC"
pico_ip="$TEST_PICO"
'''
        return subprocess.run(['bash', '-c', setup + FUNCTIONS + '''
discover_pico_stream
printf '%s %s\\n' "$pc_pico_ip" "$pico_ip"
'''], env=dict(os.environ, TEST_SOCKETS=sockets, TEST_ADDRESSES=addresses,
               TEST_PC=pc, TEST_PICO=pico), text=True, capture_output=True, timeout=5)

    def test_stale_usb_socket_cannot_hide_current_wifi_peer(self):
        result = self.discover(
            'ESTAB 0 0 [::ffff:192.168.224.6]:63901 [::ffff:192.168.224.184]:47840\n'
            'ESTAB 0 0 [::ffff:192.168.42.215]:63901 [::ffff:192.168.42.211]:49000',
            '1: lo inet 127.0.0.1/8 scope host lo\n'
            '31: wlan inet 192.168.42.215/24 scope global wlan')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), '192.168.42.215 192.168.42.211')

    def test_explicit_peer_constraints_are_kept(self):
        sockets = ('ESTAB 0 0 192.168.42.215:63901 192.168.42.212:49001\n'
                   'ESTAB 0 0 192.168.42.215:63901 192.168.42.211:49002')
        addresses = '31: wlan inet 192.168.42.215/24 scope global wlan'
        match = self.discover(sockets, addresses, '192.168.42.215', '192.168.42.211')
        self.assertEqual(match.returncode, 0, match.stderr)
        self.assertEqual(match.stdout.strip(), '192.168.42.215 192.168.42.211')
        self.assertNotEqual(self.discover(sockets, addresses, pico='192.168.42.250').returncode, 0)

    def test_only_stale_socket_fails_without_reusing_its_address(self):
        result = self.discover('ESTAB 0 0 192.168.224.6:63901 192.168.224.184:47840',
                               '1: lo inet 127.0.0.1/8 scope host lo')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')

    def test_usb_loopback_remains_supported(self):
        result = self.discover('ESTAB 0 0 127.0.0.1:63901 127.0.0.1:51000',
                               '1: lo inet 127.0.0.1/8 scope host lo')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), '127.0.0.1 127.0.0.1')


if __name__ == '__main__':
    unittest.main()
