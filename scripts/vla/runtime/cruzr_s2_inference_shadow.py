#!/usr/bin/env python3
"""Inference-only Cruzr S2 adapter for the v0.2.0 state stream.

UBTECH's supplied inference node waits for /mc/sdk/robot_state, which is
advertised but does not emit samples on the tested v0.2.0 installation.  This
adapter additionally consumes /mc/whole_joint_states, reorders its joints to
the checkpoint's 20-dimensional layout, and feeds only the inference buffer.
It inherits the vendor chunk publisher and action server, but imports no robot
command type and exposes no physical actuator path.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import pathlib
import sys
import time

import cv2


VENDOR_SOURCE = pathlib.Path("/home/ubt/additional/vla-onboard/src/gr00t_control")
VENDOR_OVERRIDE_ROOT = pathlib.Path("/home/ubt/additional/safe-runtime/vendor-overrides")
sys.path.insert(0, str(VENDOR_OVERRIDE_ROOT))
sys.path.insert(0, str(VENDOR_SOURCE))

import rclpy
from loguru import logger
from sensor_msgs.msg import JointState

import gr00t_inference
import gr00t
from image_processor import process_image_msg

if not pathlib.Path(gr00t.__file__).resolve().is_relative_to(VENDOR_OVERRIDE_ROOT):
    raise ImportError(f"The UBTECH GR00T overlay is not active: {gr00t.__file__}")


STATE_FALLBACK_TOPIC = "/mc/whole_joint_states"


class CruzrS2InferenceShadowNode(gr00t_inference.Gr00tControllerROS2Node):
    def __init__(self) -> None:
        super().__init__()
        self.fallback_state_count = 0
        self.shadow_input_dir = pathlib.Path(
            os.environ.get(
                "CRUZR_SHADOW_INPUT_DIR",
                "/home/ubt/additional/safe-runtime-logs/shadow-inputs",
            )
        )
        self.shadow_input_dir.mkdir(parents=True, exist_ok=True)
        self.create_subscription(
            JointState,
            STATE_FALLBACK_TOPIC,
            self.whole_joint_state_callback,
            self.qos_sub_sensor,
        )
        logger.info(
            "Cruzr S2 v0.2.0 inference adapter ready: fallback state source {}",
            STATE_FALLBACK_TOPIC,
        )

    def whole_joint_state_callback(self, message: JointState) -> None:
        try:
            if len(message.name) != len(message.position):
                raise ValueError(
                    f"joint state names/positions mismatch: {len(message.name)} != {len(message.position)}"
                )
            positions_by_name = dict(zip(message.name, message.position))
            target_names = list(self.config["states"]["joints"]["names"])
            missing = [name for name in target_names if name not in positions_by_name]
            if missing:
                raise ValueError(f"missing required joints: {missing}")

            reordered = JointState()
            reordered.header = copy.deepcopy(message.header)
            reordered.name = target_names
            reordered.position = [float(positions_by_name[name]) for name in target_names]
            reordered.velocity = [0.0] * len(target_names)
            reordered.effort = [0.0] * len(target_names)
            self.joint_buffer.append(reordered)
            self.fallback_state_count += 1
            if self.fallback_state_count == 1:
                logger.info(
                    "INFERENCE_STATE_READY source={} joints={}",
            STATE_FALLBACK_TOPIC,
            len(target_names),
        )
        except Exception as exc:
            logger.error("Fallback joint state rejected: {}", exc)

    @staticmethod
    def _sha256(path: pathlib.Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    def _record_synchronized_input(self, input_data) -> None:
        """Persist the exact RGB/state pair handed to one shadow inference."""
        index = int(self.chunk_id)
        stem = f"input-{index:06d}"
        final_png = self.shadow_input_dir / f"{stem}.png"
        final_json = self.shadow_input_dir / f"{stem}.json"
        # OpenCV selects the encoder from the final suffix. Keep .png last
        # while writing atomically, otherwise imwrite treats .tmp as a codec.
        temporary_png = self.shadow_input_dir / f".{stem}.tmp.png"
        temporary_json = self.shadow_input_dir / f".{stem}.json.tmp"

        image = process_image_msg(input_data["stereo_images"])
        if image is None or getattr(image, "size", 0) == 0:
            raise ValueError("shadow input image could not be decoded")
        if not cv2.imwrite(str(temporary_png), image):
            raise OSError(f"could not write shadow image: {temporary_png}")

        expected_names = list(self.config["states"]["joints"]["names"])
        positions_by_name = {}
        for component in ("left_arm", "right_arm", "head", "lifter", "waist"):
            message = input_data[f"{component}_joints"]
            positions_by_name.update(
                {name: float(value) for name, value in zip(message.name, message.position)}
            )
        missing = [name for name in expected_names if name not in positions_by_name]
        if missing:
            temporary_png.unlink(missing_ok=True)
            raise ValueError(f"shadow evidence is missing joints: {missing}")
        positions = [positions_by_name[name] for name in expected_names]

        image_message = input_data["stereo_images"]
        image_timestamp = self.get_timestamp_sec(image_message.header.stamp)
        metadata = {
            "schema": "cruzr-s2-vla-shadow-input-evidence-v1",
            "input_index": index,
            "recorded_at_unix": time.time(),
            "task_id": int(self.task_id),
            "image": {
                "topic": gr00t_inference.SUB_TOPIC_MAP["rgb_image"],
                "source_timestamp_unix": image_timestamp,
                "frame_id": image_message.header.frame_id,
                "source_width": int(image_message.width),
                "source_height": int(image_message.height),
                "source_encoding": image_message.encoding,
                "decoded_shape": list(image.shape),
                "png_file": final_png.name,
                "png_sha256": self._sha256(temporary_png),
                "decoded_bytes_sha256": hashlib.sha256(image.tobytes()).hexdigest(),
            },
            "state": {
                "joint_names": expected_names,
                "positions_rad": positions,
                "image_to_state_time_differences_seconds": input_data["time_differences"],
            },
            "physical_command_publisher_created": False,
        }
        temporary_json.write_text(
            json.dumps(metadata, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary_png, final_png)
        os.replace(temporary_json, final_json)
        logger.info(
            "SHADOW_INPUT_EVIDENCE index={} image={} state_joints={}",
            index,
            final_png,
            len(positions),
        )

    def get_synchronized_data(self):
        input_data = super().get_synchronized_data()
        if input_data is not None:
            self._record_synchronized_input(input_data)
        return input_data


def main() -> None:
    rclpy.init()
    node = CruzrS2InferenceShadowNode()
    try:
        logger.info("Starting Cruzr S2 inference-only shadow node")
        rclpy.spin(node)
    except KeyboardInterrupt:
        logger.info("Inference-only shadow node interrupted")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
