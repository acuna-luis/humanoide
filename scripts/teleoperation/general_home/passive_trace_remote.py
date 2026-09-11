"""Bounded native subscriptions, streamed via stdin; no services or publishers.

Stdlib-only, compatible with the robot's Python. Nothing is installed remotely.
The only subprocesses are fixed `rosa topic echo` subscriptions owned here.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import sys
import time

TOPICS = ['/mc/actuator_state', '/emb/estop_key_state', '/emb/servo_estop_key_state']


def parse_line(topic, line):
    """JSON object; ROS 2 UInt8 YAML only for the two fixed stops."""
    value = line.decode('utf-8').strip()
    if not value or (topic in TOPICS[1:] and value == '---'):
        return None
    if topic in TOPICS[1:]:
        match = re.fullmatch(r'data:\s*([01])', value)
        if match:
            return {'data': int(match.group(1))}
    message = json.loads(value)
    if not isinstance(message, dict):
        raise ValueError('Message is not an object')
    return message


class NativeMessages:
    """Frame the native default JSON, whose root closing brace is unindented.

    Native --print-compact emits Python-like field text, NOT JSON. The default
    formatter was captured on this runtime and produces indented JSON objects.
    Parse once per complete object, rather than reparsing every partial line on
    the Motion computer. An unknown format, bad object or partial end rejects.
    """
    def __init__(self):
        self.lines = []
        self.size = 0

    def feed(self, line):
        if not self.lines:
            if line.strip() != b'{':
                return parse_line(TOPICS[0], line)
        self.lines.append(line)
        self.size += len(line)+1
        if self.size > 2_000_000:
            raise ValueError('Native JSON message exceeds limit')
        if line.rstrip(b'\r') != b'}':
            return None
        raw = b'\n'.join(self.lines)
        self.lines = []; self.size = 0
        return parse_line(TOPICS[0], raw)


def subscription(topic, motion_container, ros_container, seconds):
    # docker exec's client can die without terminating the container command.
    # The timeout inside each container also bounds a lost SSH connection.
    limit = str(int(seconds)+3)+'s '
    if topic == TOPICS[0]:
        container = motion_container
        shell = ('source /opt/walker/setup.bash; export ROS2CLI_DISABLE_DAEMON=1; '
                 'exec timeout --signal=TERM --kill-after=1s '+limit+'rosa topic echo --no-daemon '
                 '--qos-reliability best_effort --qos-durability volatile '+topic)
    elif topic in TOPICS[1:]:
        container = ros_container
        shell = ('source /opt/ros/humble/setup.bash; export ROS2CLI_DISABLE_DAEMON=1; '
                 'exec timeout --signal=TERM --kill-after=1s '+limit+'ros2 topic echo --no-daemon --qos-reliability best_effort '
                 '--qos-durability volatile '+topic)
    else:
        raise ValueError('Unknown subscription')
    return ['docker', 'exec', container, 'bash', '-lc', shell]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds',type=float,required=True)
    parser.add_argument('--motion-container', required=True)
    parser.add_argument('--ros-container', required=True)
    args=parser.parse_args()
    if not 1 <= args.seconds <= 120:parser.error('seconds must be in [1,120]')
    started=time.monotonic_ns(); deadline=time.monotonic()+args.seconds
    selector=selectors.DefaultSelector();children=[];counts={topic:0 for topic in TOPICS};errors=[]
    total_bytes=0; error_count=0; done=False
    native_messages = NativeMessages()
    def error(message):
        nonlocal error_count
        error_count += 1
        if len(errors) < 30: errors.append(message[:600])
    def emit(record):
        print(json.dumps(dict(received_monotonic_ns=time.monotonic_ns(),**record),allow_nan=False,separators=(',',':')),flush=True)
    emit(dict(kind='start',schema='cruzr-passive-motion-trace-v1',
        started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        seconds=args.seconds,topics=TOPICS,movement_commands=0))
    try:
        for topic in TOPICS:
            proc=subprocess.Popen(subscription(topic, args.motion_container, args.ros_container, args.seconds),
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
            children.append(proc)
            for stream,is_error in [(proc.stdout,False),(proc.stderr,True)]:
                os.set_blocking(stream.fileno(),False)
                selector.register(stream,selectors.EVENT_READ,[topic,is_error,bytearray()])
        while not done and selector.get_map():
            now = time.monotonic()
            partial_native = bool(native_messages.lines) or any(
                k.data[0] == TOPICS[0] and not k.data[1] and k.data[2]
                for k in selector.get_map().values())
            # Finish only the in-flight native object at the requested cutoff.
            # Never wait indefinitely for a broken/truncated stream.
            if now >= deadline and (not partial_native or now >= deadline+.5):
                break
            for key,_ in selector.select(timeout=min(.1,max(0,deadline+.5-now))):
                topic,is_error,buffer=key.data
                chunk=os.read(key.fd,65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    if buffer:error(topic+': incomplete final line')
                    continue
                total_bytes+=len(chunk)
                if total_bytes>160_000_000:raise ValueError('Capture size limit reached')
                buffer.extend(chunk)
                if len(buffer)>2_000_000:raise ValueError('Unbounded message line')
                while b'\n' in buffer:
                    line,_,remaining=buffer.partition(b'\n');buffer[:]=remaining
                    if not line.strip():continue
                    if is_error:
                        error(topic+': '+line.decode(errors='replace'));continue
                    try:
                        msg=native_messages.feed(line) if topic == TOPICS[0] else parse_line(topic, line)
                    except (ValueError,UnicodeError) as exc:
                        error(topic+': '+str(exc)+'; input='+line.decode(errors='replace')[:300]);continue
                    if msg is None:continue
                    counts[topic]+=1
                    emit(dict(kind='message',topic=topic,message=msg))
                    if topic == TOPICS[0] and time.monotonic() >= deadline:
                        done = True
                        break
                if done:break
    finally:
        raw_partial = not done and any(k.data[0] == TOPICS[0] and not k.data[1] and k.data[2]
                                     for k in selector.get_map().values())
        if native_messages.lines or raw_partial:
            error('Incomplete native JSON object at capture end')
        for proc in children:
            if proc.poll() is not None:
                error('Subscription ended before capture: exit='+str(proc.returncode))
            if proc.poll() is None:
                try:os.killpg(proc.pid,signal.SIGTERM)
                except ProcessLookupError:pass
        for proc in children:
            try:proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=1)
        selector.close()
        emit(dict(kind='end',elapsed_seconds=(time.monotonic_ns()-started)/1e9,
            counts=counts,errors=errors,error_count=error_count,movement_commands=0))


if __name__=='__main__':main()
