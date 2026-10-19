"""Offline mocked ADB listener checks; no TCP connection or real ADB command."""
import socket
import subprocess
import io
import unittest
from unittest.mock import patch

from scripts.teleoperation import pico_camera_receiver as receiver


SERIAL = 'PA94Y0MGKB070822G'
LISTEN = 'State Recv-Q Send-Q Local Address:Port Peer Address:Port\nLISTEN 0 50 [::]:12345 [::]:*\n'
CLEAN = ('05-01 09:48:38.913 6257 10033 I Unity : StartListen port:12345\n'
         '05-01 09:48:38.957 6257 10033 I MediaDecoder: stopTCPServer\n'
         '05-01 09:48:39.057 6257 10033 I MediaDecoder: startTCPServer:12345\n')


class ReceiverTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.now = 10.0
        self.identity = SERIAL + '\r\n'
        self.forward = SERIAL + ' tcp:12345 tcp:12345\n'
        self.states = iter([LISTEN])
        self.pids = iter(['6257', '6257'])
        self.logcat = CLEAN

    def run_adb(self, command, **kwargs):
        self.calls.append((command, kwargs))
        self.assertEqual(command[:3], ['adb', '-s', SERIAL])
        operation = command[3:]
        if operation == ['shell', 'getprop', 'ro.serialno']:
            output = self.identity
        elif operation == ['forward', '--list']:
            output = self.forward
        elif operation == ['shell', 'ss', '-ltn']:
            output = next(self.states)
        elif operation == ['shell', 'pidof', 'com.xrobotoolkit.client']:
            output = next(self.pids)
        elif operation == ['logcat', '--pid=6257', '-d', '-s', 'MediaDecoder:I', 'Unity:I', '*:S']:
            output = self.logcat
        else:
            self.fail('Mutation or unsupported ADB command: ' + str(operation))
        self.assertLessEqual(kwargs['timeout'], 5)
        return subprocess.CompletedProcess(command, 0, output, 'Cannot open netlink socket: Permission denied\n')

    def check(self, wait=0):
        def sleep(seconds):
            self.now += seconds
        with patch.object(receiver.subprocess, 'run', side_effect=self.run_adb), \
             patch.object(receiver.time, 'monotonic', side_effect=lambda: self.now), \
             patch.object(receiver.time, 'sleep', side_effect=sleep), \
             patch.object(socket, 'create_connection', side_effect=AssertionError('TCP probe forbidden')), \
             patch.object(socket, 'socket', side_effect=AssertionError('TCP socket forbidden')):
            return receiver.wait_for_receiver(SERIAL, wait=wait)

    def test_waits_for_absent_then_present_decoder_using_read_only_commands(self):
        self.states = iter(['State Recv-Q Send-Q Local Address:Port Peer Address:Port\n', LISTEN])
        self.assertEqual(self.check(wait=2), 12345)
        self.assertEqual(len(self.calls), 7)
        self.assertEqual(self.now, 11)

    def test_ipv4_ipv6_and_nonlistener_rows(self):
        for address in ('0.0.0.0:12345', '127.0.0.1:12345', '[::]:12345', '*:12345', ':::12345'):
            with self.subTest(address=address):
                self.assertTrue(receiver.has_listener('LISTEN 0 50 ' + address + ' *:*', 12345))
        self.assertFalse(receiver.has_listener('ESTAB 0 0 127.0.0.1:12345 127.0.0.1:5678', 12345))
        self.assertFalse(receiver.has_listener('LISTEN 0 50 [::]:123456 [::]:*', 12345))
        self.assertFalse(receiver.has_listener('Cannot open netlink socket: Permission denied', 12345))

    def test_successful_ss_stdout_survives_stderr_permission_warning(self):
        self.assertEqual(self.check(), 12345)
        self.assertEqual(len(self.calls), 6)

    def test_wrong_identity_is_rejected_before_forward_or_listener(self):
        self.identity = 'another-device\n'
        with self.assertRaisesRegex(receiver.ReceiverError, 'identity mismatch'):
            self.check(wait=10)
        self.assertEqual(len(self.calls), 1)

    def test_missing_forward_cannot_accept_pc_listener_as_receiver(self):
        self.forward = 'another-device tcp:12345 tcp:12345\n'
        with self.assertRaisesRegex(receiver.ReceiverError, 'unambiguous ADB forward'):
            self.check(wait=10)
        self.assertEqual(len(self.calls), 2)

    def test_ambiguous_mapping_and_invalid_remote_ports_are_rejected(self):
        for mapping in (SERIAL + ' tcp:12345 tcp:12345\n' + SERIAL + ' tcp:12345 tcp:12346\n',
                        SERIAL + ' tcp:12345 localabstract:camera\n',
                        SERIAL + ' tcp:12345 tcp:65536\n'):
            with self.subTest(mapping=mapping):
                with self.assertRaises(receiver.ReceiverError):
                    receiver.forwarded_port(mapping, SERIAL, 12345)

    def test_remote_port_is_derived_from_selected_mapping(self):
        self.assertEqual(receiver.forwarded_port(SERIAL + ' tcp:12345 tcp:23456\n', SERIAL, 12345), 23456)

    def test_zero_wait_checks_once_and_fails_immediately_without_sleep(self):
        self.states = iter([''])
        with self.assertRaisesRegex(receiver.ReceiverError, 'Remote Vision.*ZEDMINI'):
            self.check(wait=0)
        self.assertEqual(self.now, 10)
        self.assertEqual(len(self.calls), 3)

    def test_wait_expires_at_deadline(self):
        self.states = iter(['', ''])
        with self.assertRaisesRegex(receiver.ReceiverError, 'not listening'):
            self.check(wait=2)
        self.assertEqual(self.now, 12)
        self.assertEqual(len(self.calls), 4)

    def test_current_activation_errors_block_even_when_ss_still_listens(self):
        for fatal in ('TCP thread did not terminate in time. Forcing shutdown...',
                      'TCP server error', 'bind failed: EADDRINUSE (Address already in use)'):
            with self.subTest(fatal=fatal):
                self.states = iter([LISTEN])
                self.pids = iter(['6257', '6257'])
                self.logcat = CLEAN + fatal + '\n'
                with self.assertRaisesRegex(receiver.ReceiverError, 'lifecycle failed'):
                    self.check()

    def test_old_error_is_ignored_after_a_clean_latest_activation(self):
        old = CLEAN + 'TCP server error\nEADDRINUSE\nTCP thread finished\n'
        self.logcat = old + CLEAN
        self.assertEqual(self.check(), 12345)
        self.assertEqual(receiver.lifecycle_status(self.logcat, 12345), 'verified')

    def test_device_wall_clock_does_not_determine_activation_freshness(self):
        output = CLEAN.replace('05-01', '12-31') + 'EADDRINUSE\n' + CLEAN
        self.assertEqual(receiver.lifecycle_status(output, 12345), 'verified')

    def test_missing_lifecycle_markers_warns_and_only_certifies_listener(self):
        self.logcat = 'old error without activation marker: EADDRINUSE\n'
        warning = io.StringIO()
        with patch.object(receiver.sys, 'stderr', warning):
            self.assertEqual(self.check(), 12345)
        self.assertIn('sólo se verifica LISTEN', warning.getvalue())
        self.assertEqual(receiver.lifecycle_status(self.logcat, 12345), 'unavailable')

    def test_pid_is_discovered_fresh_and_changed_pid_rejects_mixed_evidence(self):
        self.pids = iter(['6257', '7001'])
        with self.assertRaisesRegex(receiver.ReceiverError, 'restarted during'):
            self.check()

    def test_only_latest_activation_port_is_accepted(self):
        with self.assertRaisesRegex(receiver.ReceiverError, 'different camera port'):
            receiver.lifecycle_status(CLEAN + 'StartListen port:23456\n', 12345)


if __name__ == '__main__':
    unittest.main()
