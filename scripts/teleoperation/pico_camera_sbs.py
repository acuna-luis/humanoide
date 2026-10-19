"""Convert a mono HTTP-FLV camera into identical ZEDMINI eye images.

This optional video-only pipeline fits the complete image inside each 1280x720
eye, with borders preserving its aspect ratio, and outputs 2560x720 AVC-in-FLV.
It has no robot-control connections or publishers.
"""
from __future__ import annotations

import argparse
import io
import math
import os
import select
import shutil
import subprocess
import sys
from typing import BinaryIO
from urllib.parse import urlsplit


PLUGINS = (
    'souphttpsrc', 'flvdemux', 'avdec_h264', 'videoconvert', 'videoscale',
    'tee', 'queue', 'compositor', 'x264enc', 'flvmux', 'fdsink',
)


def check_dependencies() -> None:
    """Fail before opening a robot stream if required GStreamer plugins lack."""
    for executable in ('gst-launch-1.0', 'gst-inspect-1.0'):
        if shutil.which(executable) is None:
            raise OSError('Missing GStreamer executable: ' + executable)
    missing = []
    for plugin in PLUGINS:
        result = subprocess.run(
            ['gst-inspect-1.0', plugin], stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=5, check=False,
        )
        if result.returncode:
            missing.append(plugin)
    if missing:
        raise OSError('Missing GStreamer plugins: ' + ', '.join(missing))


def _pipeline(source: list[str]) -> list[str]:
    # AVC caps let x264enc link directly to flvmux; h264parse is not required.
    # Drop only decoded images. Dropping arbitrary H.264 access units breaks
    # inter-frame references. Keep the eye branches paired, with one slot each.
    return ['gst-launch-1.0', '-q', *source,
            '!', 'queue', 'name=latest_image', 'max-size-buffers=1',
            'max-size-bytes=0', 'max-size-time=0', 'leaky=downstream',
            '!', 'videoconvert', '!', 'videoscale', 'add-borders=true',
            '!', 'video/x-raw,format=I420,width=1280,height=720,pixel-aspect-ratio=1/1',
            '!', 'tee', 'name=t',
            'compositor', 'name=c', 'latency=0',
            'sink_0::xpos=0', 'sink_1::xpos=1280',
            '!', 'video/x-raw,format=I420,width=2560,height=720,pixel-aspect-ratio=1/1',
            '!', 'x264enc', 'tune=zerolatency', 'speed-preset=ultrafast',
            'bitrate=4000', 'key-int-max=6', 'byte-stream=false',
            'bframes=0', 'rc-lookahead=0', 'sync-lookahead=0',
            'threads=2', 'sliced-threads=true', 'vbv-buf-capacity=100',
            '!', 'video/x-h264,stream-format=avc,alignment=au,profile=constrained-baseline',
            '!', 'flvmux', 'streamable=true', 'latency=0',
            '!', 'fdsink', 'fd=1', 'sync=false',
            't.', '!', 'queue', 'max-size-buffers=1',
            'max-size-bytes=0', 'max-size-time=0', '!', 'c.sink_0',
            't.', '!', 'queue', 'max-size-buffers=1',
            'max-size-bytes=0', 'max-size-time=0', '!', 'c.sink_1']


class _PipelineStream(io.RawIOBase):
    """A pipe reader with a bounded inactivity wait and owned child process."""

    def __init__(self, command: list[str], timeout: float):
        super().__init__()
        self.timeout = timeout
        # GStreamer diagnostics inherit stderr; stdout contains only FLV bytes.
        self.process = subprocess.Popen(command, stdout=subprocess.PIPE, bufsize=0)
        assert self.process.stdout is not None

    def readable(self) -> bool:
        return True

    def _read_once(self, size: int) -> bytes:
        self._checkClosed()
        assert self.process.stdout is not None
        fd = self.process.stdout.fileno()
        ready, _, _ = select.select([fd], [], [], self.timeout)
        if not ready:
            raise TimeoutError('GStreamer SBS video produced no bytes within the source timeout')
        data = os.read(fd, size)
        if not data:
            try:
                code = self.process.wait(timeout=0.2)
            except subprocess.TimeoutExpired:
                code = None
            if code not in (None, 0):
                raise OSError('GStreamer SBS video exited with status ' + str(code))
        return data

    def read(self, size: int = -1) -> bytes:
        self._checkClosed()
        if size == 0:
            return b''
        if size > 0:
            return self._read_once(size)
        chunks = []
        while True:
            data = self._read_once(65536)
            if not data:
                return b''.join(chunks)
            chunks.append(data)

    def close(self) -> None:
        if self.closed:
            return
        try:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=2)
            if self.process.stdout is not None:
                self.process.stdout.close()
        finally:
            super().close()


def open_sbs_source(url: str, timeout: float) -> BinaryIO:
    """Return readable FLV bytes; the caller must close the owned pipeline."""
    if urlsplit(url).scheme not in ('http', 'https'):
        raise ValueError('SBS source must be an HTTP or HTTPS FLV URL')
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('SBS source timeout must be finite and positive')
    check_dependencies()
    source = ['souphttpsrc', 'location=' + url, 'timeout=' + str(math.ceil(timeout)),
              'is-live=true',
              '!', 'flvdemux', '!', 'video/x-h264,stream-format=avc,alignment=au',
              # Auto frame threading holds multiple frames before output. At
              # 12 fps it added ~1.27 s in the local live-source benchmark.
              '!', 'avdec_h264', 'max-threads=1', 'thread-type=slice']
    print('SBS_VIDEO_LAYOUT=mono-duplicated,2560x720; encoder=x264; bitrate=4000kbps; '
          'latency=low; decoder-threads=1; latest-raw-frame=1; gop=6',
          file=sys.stderr, flush=True)
    return _PipelineStream(_pipeline(source), timeout)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', required=True,
                        help='Check local GStreamer dependencies without opening video')
    parser.parse_args()
    try:
        check_dependencies()
    except (OSError, subprocess.TimeoutExpired) as error:
        print('SBS_DEPENDENCY_ERROR=' + str(error), file=sys.stderr)
        return 1
    print('SBS_GSTREAMER_DEPENDENCIES_OK=1')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
