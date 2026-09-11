#!/usr/bin/env python3
"""Exercise evidence serialization without loading ROS, CUDA or vendor models."""
import ast
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest


SOURCE = Path(__file__).with_name("cruzr_s2_inference_shadow.py")


def evidence_code():
    tree = ast.parse(SOURCE.read_text())
    helper = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "message_text")
    node = next(n for n in tree.body if isinstance(n, ast.ClassDef))
    methods = [n for n in node.body if isinstance(n, ast.FunctionDef)
               and n.name in {"_sha256", "_record_synchronized_input"}]
    # Execute the production evidence methods; exclude ROS and model startup.
    cls = ast.ClassDef(name="Recorder", bases=[], keywords=[], body=methods, decorator_list=[])
    module = ast.fix_missing_locations(ast.Module(body=[helper, cls], type_ignores=[]))
    def write_image(path, image):
        Path(path).write_bytes(image.tobytes())
        return True
    scope = dict(pathlib=__import__('pathlib'), hashlib=hashlib, json=json,
                 os=os, time=time, cv2=SimpleNamespace(imwrite=write_image),
                 process_image_msg=lambda _: SimpleNamespace(size=3, shape=(1, 1, 3),
                                                              tobytes=lambda: b'RGB'),
                 gr00t_inference=SimpleNamespace(SUB_TOPIC_MAP={"rgb_image": "/camera"}),
                 logger=SimpleNamespace(info=lambda *args: None))
    exec(compile(module, str(SOURCE), "exec"), scope)
    return scope


class InferenceEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.code = evidence_code()

    def test_native_and_ros_text(self):
        for value in ("bgr8", SimpleNamespace(data="bgr8")):
            self.assertEqual(self.code['message_text'](value), "bgr8")

    def test_shm_size_excludes_unused_nonzero_bytes(self):
        value = SimpleNamespace(data=b"bgr8\x00junk", size=4)
        self.assertEqual(self.code['message_text'](value), "bgr8")

    def test_invalid_size_and_encoding_fail(self):
        for size in (-1, 2, 0.5):
            with self.assertRaises(ValueError):
                self.code['message_text'](SimpleNamespace(data=b"a", size=size))
        with self.assertRaises(UnicodeDecodeError):
            self.code['message_text'](SimpleNamespace(data=b"\xff", size=1))

    def test_full_record_with_shm_header_and_encoding(self):
        with tempfile.TemporaryDirectory() as directory:
            recorder = self.code['Recorder']()
            recorder.shadow_input_dir = Path(directory)
            recorder.chunk_id = 7
            recorder.task_id = 0
            names = [f"joint_{i}" for i in range(20)]
            recorder.config = {"states": {"joints": {"names": names}}}
            recorder.get_timestamp_sec = lambda stamp: stamp.sec + stamp.nanosec / 1e9
            image = SimpleNamespace(
                header=SimpleNamespace(frame_id=SimpleNamespace(data=b"opticalTRAIL", size=7),
                                       stamp=SimpleNamespace(sec=42, nanosec=0)),
                encoding=SimpleNamespace(data=b"bgr8\x001", size=4), width=1, height=1)
            inputs = {"stereo_images": image, "time_differences": {"left_arm": 0.001}}
            for i, component in enumerate(("left_arm", "right_arm", "head", "lifter", "waist")):
                inputs[component + "_joints"] = SimpleNamespace(
                    name=names[i*4:(i+1)*4], position=[float(j) / 100 for j in range(i*4,(i+1)*4)])
            recorder._record_synchronized_input(inputs)
            result = json.loads((Path(directory) / "input-000007.json").read_text())
            self.assertEqual(result['image']['frame_id'], 'optical')
            self.assertEqual(result['image']['source_encoding'], 'bgr8')
            self.assertEqual(result['state']['positions_rad'], [i/100 for i in range(20)])
            self.assertFalse(result['physical_command_publisher_created'])
            self.assertEqual(result['image']['png_sha256'], hashlib.sha256(b'RGB').hexdigest())
            self.assertFalse(list(Path(directory).glob('.*.tmp*')))


if __name__ == '__main__':
    unittest.main()
