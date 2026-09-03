#!/usr/bin/env python3
"""Bounded P14 one-point transport core for the Cruzr S2 SDK command API.

This module is deliberately ROS-free.  It validates one E6.0L intent, creates
a minimum-jerk transition from a fresh measured READY state, and dispatches it
through an injected backend.  The default/test backend is memory-only.  ROS
message construction lives in ``cruzr_s2_vla_ros_sdk_backend.py`` and is not
instantiated by this module.
"""

from __future__ import annotations

import json
import math
import pathlib
from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, Sequence


CONTRACT_SCHEMA = "cruzr-s2-vla-sdk-transport-contract-e6.0r-v1"
LIMITS_SCHEMA = "cruzr-s2-vla-canary-engineering-limits-e6.0s-v1"
TERMINAL_STATES = {"COMPLETED", "STOPPED", "FAULTED"}


def _finite(value: Any, label: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label}:not_numeric") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"{label}:non_finite")
    return parsed


def _vector(value: Any, size: int, label: str) -> list[float]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{label}:not_sequence")
    if len(value) != size:
        raise ValueError(f"{label}:dimension:{len(value)}!=expected:{size}")
    return [_finite(item, f"{label}:{index}") for index, item in enumerate(value)]


def _load_object(path: pathlib.Path | str) -> dict[str, Any]:
    with pathlib.Path(path).open("r", encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise ValueError("json:not_object")
    return value


def load_transport_contract(path: pathlib.Path | str) -> dict[str, Any]:
    value = _load_object(path)
    exact = {
        "schema": CONTRACT_SCHEMA,
        "task_id": 0,
        "axis_profile": "P14_A",
        "scenario": "NO_BOX_READY",
        "input_intent_schema": "cruzr-s2-vla-transport-neutral-preview-intent-e6.0l-v1",
        "accepted_source_point_indices": [0],
        "maximum_source_point_count": 1,
        "command_topic": "/mc/sdk/robot_command",
        "command_message_type": "mc_task_msgs/msg/RobotCommand",
        "state_topic": "/mc/sdk/robot_state",
        "state_message_type": "mc_state_msgs/msg/RobotState",
        "joint_command_type": "mc_task_msgs/msg/JointCmd",
        "position_control_mode": 2,
        "software_stop_semantics": "latch_stop_purge_pending_destroy_publisher_no_hold_no_replay",
        "hardware_estop_equivalent": False,
        "physical_execution_default": False,
        "active_launcher_implemented": False,
        "physical_execution_authorized": False,
    }
    for key, expected in exact.items():
        if value.get(key) != expected:
            raise ValueError(f"contract:{key}")
    names = value.get("commanded_joint_names")
    locked = value.get("locked_joint_names")
    if not isinstance(names, list) or len(names) != 14 or len(set(names)) != 14:
        raise ValueError("contract:commanded_joint_names")
    if not isinstance(locked, list) or len(locked) != 6 or set(names) & set(locked):
        raise ValueError("contract:locked_joint_names")
    _vector(value.get("ready_arm_positions"), 14, "contract:ready_arm_positions")
    for key in ("ready_tolerance_rad", "maximum_state_age_seconds"):
        if _finite(value.get(key), f"contract:{key}") <= 0:
            raise ValueError(f"contract:{key}:not_positive")
    qos = value.get("qos")
    if qos != {
        "reliability": "BEST_EFFORT",
        "history": "KEEP_LAST",
        "depth": 5,
        "durability": "VOLATILE",
    }:
        raise ValueError("contract:qos")
    return value


def load_engineering_limits(path: pathlib.Path | str) -> dict[str, Any]:
    value = _load_object(path)
    exact = {
        "schema": LIMITS_SCHEMA,
        "scope": "NO_BOX_READY_P14_A_ONE_SOURCE_POINT_ONLY",
        "trajectory_law": "quintic_minimum_jerk_10s3_minus_15s4_plus_6s5",
        "manufacturer_certified": False,
        "owner_acceptance_required": True,
        "owner_accepted": False,
        "physical_execution_authorized": False,
    }
    for key, expected in exact.items():
        if value.get(key) != expected:
            raise ValueError(f"limits:{key}")
    names = value.get("joint_names")
    if not isinstance(names, list) or len(names) != 14 or len(set(names)) != 14:
        raise ValueError("limits:joint_names")
    for key in (
        "maximum_target_delta_rad",
        "maximum_velocity_rad_s",
        "maximum_acceleration_rad_s2",
    ):
        vector = _vector(value.get(key), 14, f"limits:{key}")
        if min(vector) <= 0:
            raise ValueError(f"limits:{key}:not_positive")
    for key in (
        "sample_period_seconds",
        "minimum_transition_duration_seconds",
        "maximum_transition_duration_seconds",
        "analytic_peak_velocity_factor",
        "analytic_peak_acceleration_factor",
    ):
        if _finite(value.get(key), f"limits:{key}") <= 0:
            raise ValueError(f"limits:{key}:not_positive")
    if float(value["minimum_transition_duration_seconds"]) > float(
        value["maximum_transition_duration_seconds"]
    ):
        raise ValueError("limits:duration_order")
    return value


class RobotCommandBackend(Protocol):
    kind: str

    def publish(self, frame: Mapping[str, Any]) -> None: ...

    def stop(self) -> None: ...


class MemoryRobotCommandBackend:
    """Nonphysical backend used by the exhaustive transport audit."""

    kind = "memory_only"

    def __init__(self, *, fail_after: int | None = None) -> None:
        self.frames: list[dict[str, Any]] = []
        self.stopped = False
        self.stop_count = 0
        self.fail_after = fail_after

    def publish(self, frame: Mapping[str, Any]) -> None:
        if self.stopped:
            raise RuntimeError("backend:stopped")
        if self.fail_after is not None and len(self.frames) >= self.fail_after:
            raise RuntimeError("backend:injected_publish_failure")
        self.frames.append(dict(frame))

    def stop(self) -> None:
        if not self.stopped:
            self.stop_count += 1
            self.stopped = True


@dataclass
class TransportDecision:
    event: str
    accepted: bool
    state: str
    reasons: list[str] = field(default_factory=list)
    frames_published: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "event": self.event,
            "accepted": self.accepted,
            "state": self.state,
            "reasons": list(self.reasons),
            "frames_published": self.frames_published,
        }


def _minimum_jerk(scale: float) -> tuple[float, float, float]:
    """Return normalized position, first and second derivative."""

    s = min(1.0, max(0.0, scale))
    position = 10.0 * s**3 - 15.0 * s**4 + 6.0 * s**5
    velocity = 30.0 * s**2 - 60.0 * s**3 + 30.0 * s**4
    acceleration = 60.0 * s - 180.0 * s**2 + 120.0 * s**3
    return position, velocity, acceleration


def plan_minimum_jerk(
    start: Sequence[Any],
    target: Sequence[Any],
    limits: Mapping[str, Any],
) -> list[dict[str, Any]]:
    q0 = _vector(start, 14, "start")
    q1 = _vector(target, 14, "target")
    delta = [end - begin for begin, end in zip(q0, q1)]
    max_delta = [float(item) for item in limits["maximum_target_delta_rad"]]
    max_velocity = [float(item) for item in limits["maximum_velocity_rad_s"]]
    max_acceleration = [
        float(item) for item in limits["maximum_acceleration_rad_s2"]
    ]
    for index, amount in enumerate(delta):
        if abs(amount) > max_delta[index] + 1e-12:
            raise ValueError(f"target_delta:{index}")

    velocity_factor = float(limits["analytic_peak_velocity_factor"])
    acceleration_factor = float(limits["analytic_peak_acceleration_factor"])
    required = float(limits["minimum_transition_duration_seconds"])
    for amount, velocity_limit, acceleration_limit in zip(
        delta, max_velocity, max_acceleration
    ):
        required = max(
            required,
            velocity_factor * abs(amount) / velocity_limit,
            math.sqrt(acceleration_factor * abs(amount) / acceleration_limit),
        )
    dt = float(limits["sample_period_seconds"])
    steps = max(1, math.ceil(required / dt))
    duration = steps * dt
    if duration > float(limits["maximum_transition_duration_seconds"]) + 1e-12:
        raise ValueError("transition_duration:exceeds_maximum")

    trajectory: list[dict[str, Any]] = []
    for step in range(steps + 1):
        elapsed = step * dt
        position_scale, velocity_scale, acceleration_scale = _minimum_jerk(
            elapsed / duration
        )
        trajectory.append({
            "index": step,
            "elapsed_seconds": elapsed,
            "duration_seconds": duration,
            "positions": [begin + amount * position_scale for begin, amount in zip(q0, delta)],
            "velocities": [amount * velocity_scale / duration for amount in delta],
            "accelerations": [
                amount * acceleration_scale / (duration * duration) for amount in delta
            ],
        })
    trajectory[0]["positions"] = list(q0)
    trajectory[-1]["positions"] = list(q1)
    return trajectory


class OnePointSdkTransportAdapter:
    """Dispatch one guarded source point through one explicitly injected backend."""

    def __init__(
        self,
        *,
        contract: Mapping[str, Any],
        limits: Mapping[str, Any],
        backend: RobotCommandBackend,
        dispatch_enabled: bool = False,
    ) -> None:
        self.contract = dict(contract)
        self.limits = dict(limits)
        self.backend = backend
        self.dispatch_enabled = dispatch_enabled
        self.state = "CREATED"
        self.trajectory: list[dict[str, Any]] = []
        self.next_index = 0
        self.frames_published = 0
        self.source_sequence_id: int | None = None
        if self.contract["commanded_joint_names"] != self.limits["joint_names"]:
            raise ValueError("contract_limits:joint_order")

    def _fault(self, reason: str) -> TransportDecision:
        self.trajectory = []
        self.state = "FAULTED"
        self.backend.stop()
        return TransportDecision(
            "fault", False, self.state, [reason], self.frames_published
        )

    def arm(
        self,
        intent: Mapping[str, Any],
        *,
        measured_arm_positions: Sequence[Any],
        state_age_seconds: Any,
    ) -> TransportDecision:
        if self.state != "CREATED":
            return TransportDecision("arm", False, self.state, ["session:not_created"])
        if not self.dispatch_enabled:
            return self._fault("dispatch:not_enabled")
        if not isinstance(intent, Mapping):
            return self._fault("intent:not_mapping")
        expected = {
            "schema": self.contract["input_intent_schema"],
            "task_id": self.contract["task_id"],
            "axis_profile": self.contract["axis_profile"],
            "scenario": self.contract["scenario"],
            "source_point_index": 0,
            "physical_execution_authorized": False,
            "physical_transport": None,
            "physical_publisher_count": 0,
        }
        reasons = [
            f"intent:{key}:mismatch"
            for key, value in expected.items()
            if intent.get(key) != value
        ]
        names = intent.get("joint_names")
        expected_names = [
            *self.contract["commanded_joint_names"],
            *self.contract["locked_joint_names"],
        ]
        if names != expected_names:
            reasons.append("intent:joint_names")
        sequence_id = intent.get("sequence_id")
        if type(sequence_id) is not int or sequence_id < 0:
            reasons.append("intent:sequence_id")
        try:
            all_positions = _vector(intent.get("positions"), 20, "intent:positions")
            measured = _vector(measured_arm_positions, 14, "measured_arm_positions")
            state_age = _finite(state_age_seconds, "state_age_seconds")
        except ValueError as exc:
            reasons.append(str(exc))
            all_positions = []
            measured = []
            state_age = math.inf
        if state_age < 0 or state_age > float(self.contract["maximum_state_age_seconds"]):
            reasons.append("state:stale")
        if measured:
            ready = [float(item) for item in self.contract["ready_arm_positions"]]
            tolerance = float(self.contract["ready_tolerance_rad"])
            for index, (actual, expected_ready) in enumerate(zip(measured, ready)):
                if abs(actual - expected_ready) > tolerance:
                    reasons.append(f"state:not_ready:{index}")
        if reasons:
            return self._fault(";".join(sorted(set(reasons))))
        try:
            self.trajectory = plan_minimum_jerk(measured, all_positions[:14], self.limits)
        except ValueError as exc:
            return self._fault(str(exc))
        self.source_sequence_id = sequence_id
        self.state = "ARMED"
        return TransportDecision("arm", True, self.state)

    def step(self) -> TransportDecision:
        if self.state != "ARMED":
            return TransportDecision("step", False, self.state, ["session:not_armed"])
        if self.next_index >= len(self.trajectory):
            self.state = "COMPLETED"
            return TransportDecision(
                "step", True, self.state, frames_published=self.frames_published
            )
        point = self.trajectory[self.next_index]
        frame = {
            "schema": "cruzr-s2-vla-sdk-robot-command-frame-e6.0r-v1",
            "topic": self.contract["command_topic"],
            "message_type": self.contract["command_message_type"],
            "source_sequence_id": self.source_sequence_id,
            "source_point_index": 0,
            "transport_frame_index": point["index"],
            "elapsed_seconds": point["elapsed_seconds"],
            "joint_cmd": [
                {
                    "name": name,
                    "control_mode": self.contract["position_control_mode"],
                    "position": position,
                    "velocity": velocity,
                    "effort": 0.0,
                    "v1": 0.0,
                    "v2": 0.0,
                    "v3": 0.0,
                    "planned_acceleration": acceleration,
                }
                for name, position, velocity, acceleration in zip(
                    self.contract["commanded_joint_names"],
                    point["positions"],
                    point["velocities"],
                    point["accelerations"],
                )
            ],
        }
        try:
            self.backend.publish(frame)
        except Exception as exc:  # backend boundary must fail closed
            return self._fault(f"backend:publish:{type(exc).__name__}:{exc}")
        self.next_index += 1
        self.frames_published += 1
        if self.next_index >= len(self.trajectory):
            self.state = "COMPLETED"
        return TransportDecision(
            "step", True, self.state, frames_published=self.frames_published
        )

    def run_to_completion(self) -> TransportDecision:
        while self.state == "ARMED":
            decision = self.step()
            if not decision.accepted:
                return decision
        return TransportDecision(
            "run_to_completion",
            self.state == "COMPLETED",
            self.state,
            frames_published=self.frames_published,
        )

    def stop(self) -> TransportDecision:
        if self.state == "STOPPED":
            return TransportDecision(
                "stop", True, self.state, frames_published=self.frames_published
            )
        self.trajectory = []
        self.backend.stop()
        self.state = "STOPPED"
        return TransportDecision(
            "stop", True, self.state, frames_published=self.frames_published
        )
