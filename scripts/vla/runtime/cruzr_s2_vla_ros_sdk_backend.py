#!/usr/bin/env python3
"""ROS 2 backend for the bounded E6.0R SDK transport core.

Importing this module does not initialize ROS and does not create a publisher.
Only explicit construction with an existing rclpy node creates the SDK command
publisher.  There is intentionally no CLI or auto-start path in E6.0R.
"""

from __future__ import annotations

import threading
from typing import Any, Mapping


class RosSdkRobotCommandBackend:
    kind = "ros2_sdk_robot_command"

    def __init__(self, node: Any) -> None:
        from mc_task_msgs.msg import JointCmd, RobotCommand
        from rclpy.qos import (
            DurabilityPolicy,
            HistoryPolicy,
            QoSProfile,
            ReliabilityPolicy,
        )

        self._node = node
        self._joint_cmd_type = JointCmd
        self._robot_command_type = RobotCommand
        self._lock = threading.Lock()
        self._stopped = False
        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=5,
            durability=DurabilityPolicy.VOLATILE,
        )
        self._publisher = node.create_publisher(
            RobotCommand, "/mc/sdk/robot_command", qos
        )

    def publish(self, frame: Mapping[str, Any]) -> None:
        with self._lock:
            if self._stopped or self._publisher is None:
                raise RuntimeError("ros_backend:stopped")
            message = self._robot_command_type()
            message.header.stamp = self._node.get_clock().now().to_msg()
            message.header.frame_id = ""
            for value in frame["joint_cmd"]:
                command = self._joint_cmd_type()
                command.name = value["name"]
                command.control_mode = int(value["control_mode"])
                command.position = float(value["position"])
                command.velocity = float(value["velocity"])
                command.effort = float(value["effort"])
                command.v1 = float(value["v1"])
                command.v2 = float(value["v2"])
                command.v3 = float(value["v3"])
                message.joint_cmd.append(command)
            self._publisher.publish(message)

    def stop(self) -> None:
        """Purge future output by destroying the publisher, once.

        This is a software dispatch STOP, not a hardware E-stop, torque-off or
        certified safe stop.  It sends no extra hold/motion command.
        """

        with self._lock:
            if self._stopped:
                return
            self._stopped = True
            publisher = self._publisher
            self._publisher = None
            if publisher is not None:
                self._node.destroy_publisher(publisher)
