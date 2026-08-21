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
import pathlib
import sys


VENDOR_SOURCE = pathlib.Path("/home/ubt/additional/vla-onboard/src/gr00t_control")
VENDOR_OVERRIDE_ROOT = pathlib.Path("/home/ubt/additional/safe-runtime/vendor-overrides")
sys.path.insert(0, str(VENDOR_OVERRIDE_ROOT))
sys.path.insert(0, str(VENDOR_SOURCE))

import rclpy
from loguru import logger
from sensor_msgs.msg import JointState

import gr00t_inference
import gr00t

if not pathlib.Path(gr00t.__file__).resolve().is_relative_to(VENDOR_OVERRIDE_ROOT):
    raise ImportError(f"The UBTECH GR00T overlay is not active: {gr00t.__file__}")


STATE_FALLBACK_TOPIC = "/mc/whole_joint_states"


class CruzrS2InferenceShadowNode(gr00t_inference.Gr00tControllerROS2Node):
    def __init__(self) -> None:
        super().__init__()
        self.fallback_state_count = 0
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
