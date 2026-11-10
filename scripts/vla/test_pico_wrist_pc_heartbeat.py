"""Nonce heartbeat tests with real pipes; no ROS, network or robot actions."""
import json
import os
import queue
import threading
import time
import tempfile
import unittest

import pico_wrist_pc_heartbeat as heartbeat
import arm_native_lease_bridge as bridge


class HeartbeatTests(unittest.TestCase):
    def test_response_sender_loss_expires_without_rearm(self):
        read_fd, write_fd = os.pipe()
        sender = heartbeat.PcHeartbeatPump(write_fd, 'a'*32)
        def send(row): sender.submit(row); return True
        receiver = heartbeat.PcHeartbeat(read_fd, 'a'*32, send)
        try:
            receiver.await_ready(2)
            time.sleep(.25)
            self.assertTrue(receiver.alive())
            sender.close()
            time.sleep(heartbeat.MAX_GAP_S+.2)
            self.assertFalse(receiver.alive())
            self.assertIsNotNone(receiver.failure)
        finally:
            sender.close(); receiver.close(); os.close(read_fd); os.close(write_fd)

    def test_buffered_old_response_cannot_answer_new_nonce(self):
        read_fd, write_fd = os.pipe(); challenges=queue.Queue()
        receiver = heartbeat.PcHeartbeat(read_fd, 'a'*32, lambda row:(challenges.put(row),True)[1])
        try:
            first = challenges.get(timeout=1)
            old = dict(first, event='pc_pong')
            os.write(write_fd, (json.dumps(old)+'\n').encode())
            receiver.await_ready(2)
            second = challenges.get(timeout=2)
            self.assertNotEqual(first['nonce'], second['nonce'])
            os.write(write_fd, (json.dumps(old)+'\n').encode())
            deadline=time.monotonic()+1
            while receiver.failure is None and time.monotonic()<deadline: time.sleep(.01)
            self.assertFalse(receiver.alive())
            self.assertIn('invalid_or_expired', receiver.failure)
        finally:
            receiver.close(); os.close(read_fd); os.close(write_fd)

    def test_wrong_session_response_and_stalled_reader_fail_closed(self):
        for mode in ('wrong_session','no_reply'):
            with self.subTest(mode=mode):
                read_fd, write_fd = os.pipe(); challenges=queue.Queue()
                receiver = heartbeat.PcHeartbeat(read_fd, 'a'*32, lambda row:(challenges.put(row),True)[1])
                try:
                    challenge=challenges.get(timeout=1)
                    if mode == 'wrong_session':
                        bad=dict(challenge,event='pc_pong',session_id='b'*32)
                        os.write(write_fd,(json.dumps(bad)+'\n').encode())
                    with self.assertRaises(RuntimeError): receiver.await_ready(2)
                    self.assertFalse(receiver.alive())
                finally:
                    receiver.close(); os.close(read_fd); os.close(write_fd)

    def test_sender_detects_full_pipe_with_bounded_timeout(self):
        read_fd, write_fd = os.pipe(); os.set_blocking(write_fd, False)
        try:
            while True:
                try: os.write(write_fd, b'x'*4096)
                except BlockingIOError: break
            sender = heartbeat.PcHeartbeatPump(write_fd, 'a'*32)
            try:
                sender.submit({'event':'pc_ping','session_id':'a'*32,'sequence':0,'nonce':'c'*32})
                self.assertTrue(sender.failed.wait(1))
                self.assertIn('timeout', sender.failure.lower())
            finally: sender.close()
        finally: os.close(read_fd); os.close(write_fd)

    def test_closed_pipe_is_observed(self):
        read_fd, write_fd = os.pipe()
        receiver = heartbeat.PcHeartbeat(read_fd, 'a'*32, lambda row:True)
        os.close(write_fd)
        try:
            self.assertTrue(receiver.ready.wait(1))
            self.assertFalse(receiver.alive())
            self.assertIn('eof', receiver.failure)
        finally: receiver.close(); os.close(read_fd)

    def test_pc_loss_revokes_simulated_action_and_cancels_exact_uuid(self):
        read_fd, write_fd = os.pipe(); session='a'*32; goal='12345678-1234-1234-1234-123456789abc'
        sender=heartbeat.PcHeartbeatPump(write_fd, session)
        receiver=heartbeat.PcHeartbeat(read_fd, session, lambda row:(sender.submit(row),True)[1])
        stopper=None; stop=threading.Event()
        try:
            receiver.await_ready(2)
            with tempfile.TemporaryDirectory() as directory:
                lease=bridge.GuardLease(directory, dict(bridge.arm.BODY), receiver.alive)
                def renew():
                    while not stop.wait(.03):
                        now=time.monotonic()
                        row={'event':'telemetry','goal_uuid':'b'*32,'monotonic':now,
                             'position':dict(bridge.arm.BODY),
                             'velocity':{n:0.0 for n in bridge.arm.BODY}, 'estop':0,'servo_stop':0}
                        try: lease.heartbeat(row)
                        except Exception: return
                stopper=threading.Thread(target=renew); stopper.start()
                deadline=time.monotonic()+2
                while time.monotonic()<deadline:
                    try:
                        bridge.native.check_lease(lease.path, time.monotonic())
                        break
                    except RuntimeError:
                        time.sleep(.01)
                else:
                    self.fail('simulated guard did not produce a current lease')
                class Transport:
                    goal_id=None
                    def __init__(self): self.pending=[]; self.cancelled=[]; self.lost=False
                    def ready(self): return True
                    def send(self, _goal): self.goal_id=goal; self.pending.append({'event':'accepted','goal_id':goal}); return goal
                    def spin(self):
                        time.sleep(.02)
                        if self.goal_id and not self.lost:
                            self.lost=True; sender.close()
                    def drain(self): rows,self.pending=self.pending,[]; return rows
                    def cancel(self): self.cancelled.append(self.goal_id)
                transport=Transport(); rows=[]
                rc=bridge.native.run_action(transport,'motion',{'task_name':'probe','yaml_args':'{}'},
                    3.0,lambda **row:rows.append(row),lease_file=lease.path,cancel_grace=.1)
                self.assertEqual(rc,3)
                self.assertEqual(transport.cancelled,[goal])
                self.assertFalse(rows[-1]['physical_stop_verified'])
                stop.set(); stopper.join(2); stopper=None
        finally:
            stop.set()
            sender.close(); receiver.close(); os.close(read_fd); os.close(write_fd)
            if stopper is not None: stopper.join(2)


if __name__ == '__main__':
    unittest.main()
