#!/usr/bin/env python3
"""Relay an SRS HTTP-FLV H.264 stream to XRoboToolkit's TCP decoder.

XRoboToolkit-PICO 1.1.1 opens a TCP listener (normally port 12345) for
``MediaDecoder``.  It expects each H.264 access unit as an unsigned 32-bit
big-endian length followed by Annex-B data.  Cruzr's SRS server exposes the
robot camera as AVC inside FLV, so this relay only demultiplexes and converts
AVCC NAL lengths to Annex-B start codes.  It never sends robot-control data.
"""

from __future__ import annotations

import argparse
import os
import socket
import struct
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from typing import BinaryIO


MAX_TAG_BYTES = 16 * 1024 * 1024
MAX_ACCESS_UNIT_BYTES = 16 * 1024 * 1024
START_CODE = b"\x00\x00\x00\x01"


class RelayError(RuntimeError):
    """Expected transport or stream error."""


def log(message: str) -> None:
    stamp = time.strftime("%H:%M:%S")
    print(f"[{stamp}] CAMERA: {message}", flush=True)


def read_exact(stream: BinaryIO, length: int) -> bytes:
    chunks: list[bytes] = []
    remaining = length
    while remaining:
        chunk = stream.read(remaining)
        if not chunk:
            raise EOFError(f"FLV terminó con {remaining} bytes pendientes")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def uint24(data: bytes) -> int:
    if len(data) != 3:
        raise RelayError("uint24 requiere exactamente tres bytes")
    return int.from_bytes(data, "big")


@dataclass
class AvcFlvDemuxer:
    """Minimal AVC-in-FLV demultiplexer."""

    nalu_length_size: int = 4
    parameter_sets: list[bytes] = field(default_factory=list)
    header_read: bool = False

    def read_header(self, stream: BinaryIO) -> None:
        header = read_exact(stream, 9)
        if header[:3] != b"FLV" or header[3] != 1:
            raise RelayError("la fuente no es FLV versión 1")
        data_offset = int.from_bytes(header[5:9], "big")
        if data_offset < 9 or data_offset > 4096:
            raise RelayError(f"cabecera FLV inválida (offset={data_offset})")
        if data_offset > 9:
            read_exact(stream, data_offset - 9)
        previous_tag_size = read_exact(stream, 4)
        if previous_tag_size != b"\0\0\0\0":
            raise RelayError("PreviousTagSize0 FLV inválido")
        self.header_read = True

    def _parse_decoder_config(self, payload: bytes) -> None:
        if len(payload) < 7 or payload[0] != 1:
            raise RelayError("AVCDecoderConfigurationRecord inválido")
        self.nalu_length_size = (payload[4] & 0x03) + 1
        if self.nalu_length_size not in (1, 2, 4):
            raise RelayError(
                f"tamaño AVCC no soportado: {self.nalu_length_size}"
            )
        cursor = 6
        parameter_sets: list[bytes] = []
        sps_count = payload[5] & 0x1F
        for _ in range(sps_count):
            if cursor + 2 > len(payload):
                raise RelayError("SPS truncado en configuración AVC")
            length = int.from_bytes(payload[cursor : cursor + 2], "big")
            cursor += 2
            if not length or cursor + length > len(payload):
                raise RelayError("longitud SPS inválida")
            parameter_sets.append(payload[cursor : cursor + length])
            cursor += length
        if cursor >= len(payload):
            raise RelayError("configuración AVC sin contador PPS")
        pps_count = payload[cursor]
        cursor += 1
        for _ in range(pps_count):
            if cursor + 2 > len(payload):
                raise RelayError("PPS truncado en configuración AVC")
            length = int.from_bytes(payload[cursor : cursor + 2], "big")
            cursor += 2
            if not length or cursor + length > len(payload):
                raise RelayError("longitud PPS inválida")
            parameter_sets.append(payload[cursor : cursor + length])
            cursor += length
        if not parameter_sets:
            raise RelayError("configuración AVC sin SPS/PPS")
        self.parameter_sets = parameter_sets

    def _avcc_to_annex_b(self, payload: bytes, keyframe: bool) -> bytes:
        cursor = 0
        nal_units: list[bytes] = []
        nal_types: set[int] = set()
        while cursor < len(payload):
            end_of_length = cursor + self.nalu_length_size
            if end_of_length > len(payload):
                raise RelayError("longitud NAL truncada")
            length = int.from_bytes(payload[cursor:end_of_length], "big")
            cursor = end_of_length
            if not length or length > MAX_ACCESS_UNIT_BYTES:
                raise RelayError(f"longitud NAL inválida: {length}")
            end = cursor + length
            if end > len(payload):
                raise RelayError("NAL truncada")
            nal = payload[cursor:end]
            cursor = end
            nal_units.append(nal)
            nal_types.add(nal[0] & 0x1F)
        if not nal_units:
            return b""

        output: list[bytes] = []
        # Android MediaCodec needs codec configuration before the first IDR.
        # Repeat it on every FLV keyframe so a decoder reconnect can recover.
        if keyframe and self.parameter_sets and not ({7, 8} <= nal_types):
            output.extend(START_CODE + item for item in self.parameter_sets)
        output.extend(START_CODE + item for item in nal_units)
        access_unit = b"".join(output)
        if len(access_unit) > MAX_ACCESS_UNIT_BYTES:
            raise RelayError(
                f"unidad H.264 demasiado grande: {len(access_unit)} bytes"
            )
        return access_unit

    def next_access_unit(self, stream: BinaryIO) -> tuple[bytes, bool] | None:
        if not self.header_read:
            self.read_header(stream)
        while True:
            tag_header = read_exact(stream, 11)
            tag_type = tag_header[0]
            data_size = uint24(tag_header[1:4])
            if data_size > MAX_TAG_BYTES:
                raise RelayError(f"tag FLV demasiado grande: {data_size} bytes")
            data = read_exact(stream, data_size)
            previous_size = int.from_bytes(read_exact(stream, 4), "big")
            if previous_size != 11 + data_size:
                raise RelayError("PreviousTagSize FLV no coincide")
            if tag_type != 9 or len(data) < 5:
                continue
            frame_type = data[0] >> 4
            codec_id = data[0] & 0x0F
            if codec_id != 7:
                raise RelayError(f"códec FLV no soportado: {codec_id} (se exige AVC)")
            avc_packet_type = data[1]
            if avc_packet_type == 0:
                self._parse_decoder_config(data[5:])
                continue
            if avc_packet_type == 2:
                raise EOFError("fin de secuencia AVC")
            if avc_packet_type != 1:
                continue
            keyframe = frame_type == 1
            access_unit = self._avcc_to_annex_b(data[5:], keyframe)
            if access_unit:
                return access_unit, keyframe


def connect_pico(host: str, port: int, wait_seconds: int) -> socket.socket:
    deadline = time.monotonic() + wait_seconds
    last_error: OSError | None = None
    next_notice = 0.0
    while time.monotonic() < deadline:
        try:
            sock = socket.create_connection((host, port), timeout=2)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            sock.settimeout(5)
            return sock
        except OSError as exc:
            last_error = exc
            now = time.monotonic()
            if now >= next_notice:
                remaining = max(0, int(deadline - now))
                log(
                    f"esperando que XRoboToolkit abra {host}:{port} "
                    f"({remaining}s)"
                )
                next_notice = now + 5
            time.sleep(0.5)
    raise RelayError(
        f"XRoboToolkit no abrió {host}:{port} en {wait_seconds}s"
        + (f": {last_error}" if last_error else "")
    )


def open_source(url: str, timeout: int) -> BinaryIO:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Humanoide-PICO-camera-relay/1.0"},
    )
    response = urllib.request.urlopen(request, timeout=timeout)
    content_type = response.headers.get_content_type()
    if response.status != 200:
        response.close()
        raise RelayError(f"SRS respondió HTTP {response.status}")
    if content_type not in {"video/x-flv", "application/octet-stream"}:
        response.close()
        raise RelayError(f"SRS devolvió Content-Type inesperado: {content_type}")
    return response


def relay(args: argparse.Namespace) -> int:
    log(f"destino PICO={args.pico_ip}:{args.port}")
    pico = connect_pico(args.pico_ip, args.port, args.wait_seconds)
    log("PICO_CAMERA_LISTENER_CONNECTED=1")
    source: BinaryIO | None = None
    frames = 0
    keyframes = 0
    started = time.monotonic()
    last_report = started
    ready_written = False
    last_ready_update = 0.0
    try:
        source = open_source(args.source, args.source_timeout)
        log(f"fuente SRS conectada: {args.source}")
        demuxer = AvcFlvDemuxer()
        while True:
            item = demuxer.next_access_unit(source)
            if item is None:
                continue
            access_unit, keyframe = item
            pico.sendall(struct.pack(">I", len(access_unit)))
            pico.sendall(access_unit)
            frames += 1
            keyframes += int(keyframe)
            if not ready_written and keyframe:
                if args.ready_file:
                    with open(args.ready_file, "w", encoding="utf-8") as ready:
                        ready.write("PICO_CAMERA_LIVE=1\n")
                ready_written = True
                log("PICO_CAMERA_LIVE=1")
            now = time.monotonic()
            if (
                ready_written
                and args.ready_file
                and now - last_ready_update >= 1
            ):
                os.utime(args.ready_file)
                last_ready_update = now
            if now - last_report >= 5:
                elapsed = max(now - started, 0.001)
                log(
                    f"PICO_CAMERA_FRAMES={frames} KEYFRAMES={keyframes} "
                    f"FPS={frames / elapsed:.1f}"
                )
                last_report = now
    except (BrokenPipeError, ConnectionResetError) as exc:
        raise RelayError(f"el PICO cerró la cámara: {exc}") from exc
    finally:
        if source is not None:
            source.close()
        pico.close()


def inspect_file(path: str) -> int:
    frames = 0
    keyframes = 0
    total = 0
    demuxer = AvcFlvDemuxer()
    with open(path, "rb") as stream:
        try:
            while True:
                access_unit, keyframe = demuxer.next_access_unit(stream)  # type: ignore[misc]
                frames += 1
                keyframes += int(keyframe)
                total += len(access_unit)
        except EOFError:
            pass
    if not frames or not keyframes or not demuxer.parameter_sets:
        raise RelayError(
            "la muestra no contiene SPS/PPS, keyframe y frames AVC suficientes"
        )
    print(f"FLV_AVC_OK=frames:{frames},keyframes:{keyframes},bytes:{total}")
    print(
        "AVC_CONFIG_OK="
        f"nal_length:{demuxer.nalu_length_size},parameter_sets:{len(demuxer.parameter_sets)}"
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reenvía H.264/FLV de SRS al decodificador TCP del PICO"
    )
    parser.add_argument("--source", help="URL HTTP-FLV de SRS")
    parser.add_argument("--pico-ip", help="IP Wi-Fi del PICO")
    parser.add_argument("--port", type=int, default=12345)
    parser.add_argument("--wait-seconds", type=int, default=60)
    parser.add_argument("--source-timeout", type=int, default=10)
    parser.add_argument("--ready-file")
    parser.add_argument("--inspect-flv", metavar="FILE")
    args = parser.parse_args()
    if args.inspect_flv:
        return args
    if not args.source or not args.pico_ip:
        parser.error("--source y --pico-ip son obligatorios para retransmitir")
    if not 1 <= args.port <= 65535:
        parser.error("--port debe estar entre 1 y 65535")
    if not 1 <= args.wait_seconds <= 600:
        parser.error("--wait-seconds debe estar entre 1 y 600")
    return args


def main() -> int:
    args = parse_args()
    try:
        if args.inspect_flv:
            return inspect_file(args.inspect_flv)
        return relay(args)
    except (RelayError, EOFError, OSError) as exc:
        print(f"CAMERA_RELAY_ERROR={exc}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
