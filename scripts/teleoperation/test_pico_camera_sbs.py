"""Offline SBS video and child-process lifecycle checks; no robot/PICO access."""
import functools
from http.server import BaseHTTPRequestHandler, SimpleHTTPRequestHandler, ThreadingHTTPServer
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from scripts.teleoperation import pico_camera_sbs as sbs
from scripts.teleoperation.pico_camera_relay import AvcFlvDemuxer


class PipelineReaderTests(unittest.TestCase):
    def test_timeout_is_bounded_and_close_reaps_child(self):
        stream = sbs._PipelineStream([sys.executable, '-c', 'import time;time.sleep(30)'], .05)
        started = time.monotonic()
        try:
            with self.assertRaises(TimeoutError):
                stream.read(9)
            self.assertLess(time.monotonic() - started, 1)
        finally:
            stream.close()
        self.assertTrue(stream.closed)
        self.assertIsNotNone(stream.process.poll())
        stream.close()

    def test_invalid_source_cannot_launch_process(self):
        with patch.object(sbs.subprocess, 'Popen') as launch:
            for url, timeout in (('file:///tmp/example.flv', 5), ('http://localhost/x', 0)):
                with self.assertRaises(ValueError):
                    sbs.open_sbs_source(url, timeout)
        launch.assert_not_called()

    def test_missing_plugin_is_reported_before_start(self):
        def inspect(command, **kwargs):
            return subprocess.CompletedProcess(command, 1 if command[-1] == 'compositor' else 0)
        with patch.object(sbs.shutil, 'which', return_value='/usr/bin/tool'), \
             patch.object(sbs.subprocess, 'run', side_effect=inspect), \
             patch.object(sbs.subprocess, 'Popen') as launch:
            with self.assertRaisesRegex(OSError, 'compositor'):
                sbs.open_sbs_source('http://127.0.0.1/example.flv', 5)
        launch.assert_not_called()


class VideoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            sbs.check_dependencies()
        except (OSError, subprocess.TimeoutExpired) as error:
            raise unittest.SkipTest(str(error))

    def test_live_source_first_image_does_not_wait_for_frame_threads(self):
        # The previous auto-thread decoder withheld ~15 frames (~1.27 s at
        # 12 fps). A real-time producer catches this; a finite file at EOS does not.
        source_started = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-Type', 'video/x-flv')
                self.end_headers()
                source_started.append(time.monotonic())
                process = subprocess.Popen([
                    'gst-launch-1.0', '-q', 'videotestsrc', 'is-live=true',
                    'num-buffers=36', '!',
                    'video/x-raw,format=I420,width=640,height=400,framerate=12/1',
                    '!', 'x264enc', 'tune=zerolatency', 'speed-preset=ultrafast',
                    'byte-stream=false', '!', 'video/x-h264,stream-format=avc,alignment=au',
                    '!', 'flvmux', 'streamable=true', '!', 'fdsink', 'fd=1',
                ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0)
                try:
                    while True:
                        block = process.stdout.read(65536)
                        if not block:
                            break
                        self.wfile.write(block)
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                finally:
                    process.terminate()
                    process.wait(timeout=3)
                    process.stdout.close()

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            with sbs.open_sbs_source('http://127.0.0.1:%s/live.flv' % server.server_port, 3) as stream:
                unit, keyframe = AvcFlvDemuxer().next_access_unit(stream)
                delay = time.monotonic() - source_started[0]
                self.assertTrue(keyframe)
                self.assertTrue(unit)
                self.assertLess(delay, 1, 'Live decoder is buffering multiple input frames')
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=2)

    def test_real_http_flv_keeps_full_identical_images_for_both_eyes(self):
        # Generate only a synthetic local source; its aspect ratio needs borders.
        original = subprocess.run([
            'gst-launch-1.0', '-q', 'videotestsrc', 'num-buffers=6', 'pattern=smpte',
            '!', 'video/x-raw,format=I420,width=640,height=400,framerate=12/1',
            '!', 'x264enc', 'tune=zerolatency', 'byte-stream=false',
            '!', 'video/x-h264,stream-format=avc,alignment=au',
            '!', 'flvmux', 'streamable=true', '!', 'fdsink', 'fd=1',
        ], capture_output=True, timeout=15, check=True).stdout

        class QuietHandler(SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'source.flv').write_bytes(original)
            handler = functools.partial(QuietHandler, directory=directory)
            server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = 'http://127.0.0.1:%s/source.flv' % server.server_port
                with sbs.open_sbs_source(url, 5) as stream:
                    output = stream.read()
                    process = stream.process
                self.assertIsNotNone(process.poll())
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

            self.assertEqual(output[:3], b'FLV')
            decoder = AvcFlvDemuxer()
            data = io.BytesIO(output)
            frames = keyframes = 0
            try:
                while True:
                    _, keyframe = decoder.next_access_unit(data)
                    frames += 1
                    keyframes += int(keyframe)
            except EOFError:
                pass
            # The latest-image queue intentionally drops images when a file
            # arrives faster than it can be converted. Validate decoded content.
            self.assertGreaterEqual(frames, 1)
            self.assertGreaterEqual(keyframes, 1)
            self.assertTrue(decoder.parameter_sets)

            (path / 'sbs.flv').write_bytes(output)
            decoded = subprocess.run([
                'gst-launch-1.0', '-q', 'filesrc', 'location=' + str(path / 'sbs.flv'),
                '!', 'flvdemux', '!', 'video/x-h264,stream-format=avc,alignment=au',
                '!', 'avdec_h264', '!', 'videoconvert',
                '!', 'video/x-raw,format=GRAY8', '!', 'fdsink', 'fd=1',
            ], capture_output=True, timeout=15, check=True).stdout
            frame_size = 2560 * 720
            self.assertEqual(len(decoded) % frame_size, 0)
            self.assertGreaterEqual(len(decoded), frame_size)
            image = memoryview(decoded)[-frame_size:]
            # Compare every row: each eye receives the whole image, not a crop.
            differences = []
            for row in range(720):
                pixels = image[row * 2560:(row + 1) * 2560]
                differences.extend(abs(left - right) for left, right in zip(pixels[:1280], pixels[1280:]))
            self.assertLess(sum(differences) / len(differences), 2)
            # 640:400 content fits 1152x720, leaving black side borders per eye.
            middle = image[360 * 2560:361 * 2560]
            self.assertLess(max(middle[:40]), 25)
            self.assertLess(max(middle[1240:1280]), 25)
            self.assertGreater(max(middle[64:1216]) - min(middle[64:1216]), 100)


if __name__ == '__main__':
    unittest.main()
