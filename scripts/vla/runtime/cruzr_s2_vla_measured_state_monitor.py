#!/usr/bin/env python3
"""ROS-free measured-state guard for the E6.0 one-point canary.

The monitor consumes normalized named joint-state samples.  It never imports
ROS or creates a subscriber/publisher.  A caller must inject one synchronous
software-STOP callback; the first fault invokes it exactly once and latches.
"""

from __future__ import annotations

import json
import math
import pathlib
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence


MONITOR_SCHEMA = "cruzr-s2-vla-measured-state-monitor-contract-e6.0u-v1"
LIMITS_SCHEMA = "cruzr-s2-vla-canary-engineering-limits-e6.0s-v1"
SAMPLE_SCHEMA = "cruzr-s2-vla-normalized-joint-state-e6.0u-v1"


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


def load_monitor_contract(path: pathlib.Path | str) -> dict[str, Any]:
    value = _load_object(path)
    exact = {
        "schema": MONITOR_SCHEMA,
        "task_id": 0,
        "axis_profile": "P14_A",
        "scenario": "NO_BOX_READY",
        "source_selection_policy": "first_complete_fresh_sample_before_arm_then_latched_no_failover",
        "velocity_field_required": True,
        "acceleration_method": "finite_difference_of_named_reported_velocity_over_sample_monotonic_time",
        "stop_policy": "synchronous_once_on_first_fault_or_explicit_stop_then_latched_no_resume",
        "software_stop_is_hardware_estop_equivalent": False,
        "physical_execution_default": False,
        "active_launcher_implemented": False,
        "physical_execution_authorized": False,
    }
    for key, expected in exact.items():
        if value.get(key) != expected:
            raise ValueError(f"contract:{key}")
    sources = value.get("allowed_state_sources")
    if not isinstance(sources, list) or len(sources) != 2:
        raise ValueError("contract:allowed_state_sources")
    expected_sources = {
        ("/mc/sdk/robot_state", "mc_state_msgs/msg/RobotState", "joint_states"),
        ("/mc/whole_joint_states", "sensor_msgs/msg/JointState", "."),
    }
    observed_sources = {
        (item.get("topic"), item.get("message_type"), item.get("joint_state_field"))
        for item in sources
        if isinstance(item, Mapping)
    }
    if observed_sources != expected_sources:
        raise ValueError("contract:allowed_state_sources:content")
    commanded = value.get("commanded_joint_names")
    locked = value.get("locked_joint_names")
    if not isinstance(commanded, list) or len(commanded) != 14 or len(set(commanded)) != 14:
        raise ValueError("contract:commanded_joint_names")
    if not isinstance(locked, list) or len(locked) != 6 or len(set(locked)) != 6:
        raise ValueError("contract:locked_joint_names")
    if set(commanded) & set(locked):
        raise ValueError("contract:joint_sets_overlap")
    _vector(value.get("ready_arm_positions"), 14, "contract:ready_arm_positions")
    positive = (
        "ready_arm_tolerance_rad",
        "initial_stationary_velocity_rad_s",
        "maximum_state_age_seconds",
        "maximum_future_skew_seconds",
        "minimum_acceleration_interval_seconds",
        "maximum_acceleration_interval_seconds",
        "locked_maximum_position_drift_rad",
        "locked_maximum_velocity_rad_s",
    )
    for key in positive:
        if _finite(value.get(key), f"contract:{key}") <= 0:
            raise ValueError(f"contract:{key}:not_positive")
    if float(value["minimum_acceleration_interval_seconds"]) >= float(
        value["maximum_acceleration_interval_seconds"]
    ):
        raise ValueError("contract:acceleration_interval_order")
    return value


def load_limits(path: pathlib.Path | str) -> dict[str, Any]:
    value = _load_object(path)
    if value.get("schema") != LIMITS_SCHEMA:
        raise ValueError("limits:schema")
    for key in ("maximum_velocity_rad_s", "maximum_acceleration_rad_s2"):
        parsed = _vector(value.get(key), 14, f"limits:{key}")
        if min(parsed) <= 0:
            raise ValueError(f"limits:{key}:not_positive")
    if value.get("physical_execution_authorized") is not False:
        raise ValueError("limits:physical_execution_authorized")
    return value


@dataclass
class MonitorDecision:
    event: str
    accepted: bool
    state: str
    reasons: list[str] = field(default_factory=list)
    source_topic: str | None = None
    checked_acceleration: bool = False
    maximum_arm_velocity_rad_s: float = 0.0
    maximum_arm_acceleration_rad_s2: float = 0.0
    maximum_locked_velocity_rad_s: float = 0.0
    maximum_locked_position_drift_rad: float = 0.0
    stop_invocations: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "event": self.event,
            "accepted": self.accepted,
            "state": self.state,
            "reasons": list(self.reasons),
            "source_topic": self.source_topic,
            "checked_acceleration": self.checked_acceleration,
            "maximum_arm_velocity_rad_s": self.maximum_arm_velocity_rad_s,
            "maximum_arm_acceleration_rad_s2": self.maximum_arm_acceleration_rad_s2,
            "maximum_locked_velocity_rad_s": self.maximum_locked_velocity_rad_s,
            "maximum_locked_position_drift_rad": self.maximum_locked_position_drift_rad,
            "stop_invocations": self.stop_invocations,
            "physical_execution_authorized": False,
        }


class MeasuredStateMonitor:
    """Monitor one latched named-state source and fail closed synchronously."""

    def __init__(
        self,
        *,
        contract: Mapping[str, Any],
        limits: Mapping[str, Any],
        stop_callback: Callable[[], None],
    ) -> None:
        self.contract = dict(contract)
        self.limits = dict(limits)
        self.stop_callback = stop_callback
        if self.contract["commanded_joint_names"] != self.limits.get("joint_names"):
            raise ValueError("contract_limits:joint_order")
        self.state = "CREATED"
        self.source_topic: str | None = None
        self.stop_invocations = 0
        self._stop_attempted = False
        self._locked_reference: list[float] = []
        self._acceleration_time: float | None = None
        self._acceleration_velocity: list[float] = []

    @property
    def allowed_topics(self) -> set[str]:
        return {item["topic"] for item in self.contract["allowed_state_sources"]}

    def _invoke_stop_once(self) -> str | None:
        if self._stop_attempted:
            return None
        self._stop_attempted = True
        self.stop_invocations += 1
        try:
            self.stop_callback()
        except Exception as exc:  # STOP failure remains terminal and visible
            return f"stop_callback:{type(exc).__name__}:{exc}"
        return None

    def _fault(self, reasons: list[str] | str) -> MonitorDecision:
        if isinstance(reasons, str):
            reason_list = [reasons]
        else:
            reason_list = list(reasons)
        stop_error = self._invoke_stop_once()
        if stop_error:
            reason_list.append(stop_error)
        self.state = "FAULTED"
        return MonitorDecision(
            "fault",
            False,
            self.state,
            sorted(set(reason_list)),
            self.source_topic,
            stop_invocations=self.stop_invocations,
        )

    def _normalize(
        self, sample: Mapping[str, Any], now_seconds: Any
    ) -> tuple[dict[str, Any] | None, list[str]]:
        reasons: list[str] = []
        if not isinstance(sample, Mapping):
            return None, ["sample:not_mapping"]
        if sample.get("schema") != SAMPLE_SCHEMA:
            reasons.append("sample:schema")
        topic = sample.get("source_topic")
        if topic not in self.allowed_topics:
            reasons.append("sample:source_topic")
        try:
            now = _finite(now_seconds, "now_seconds")
            sample_time = _finite(sample.get("sample_time_seconds"), "sample_time_seconds")
            received = _finite(sample.get("received_time_seconds"), "received_time_seconds")
        except ValueError as exc:
            reasons.append(str(exc))
            now = math.inf
            sample_time = math.inf
            received = math.inf
        age = now - received
        if age < -float(self.contract["maximum_future_skew_seconds"]):
            reasons.append("sample:received_in_future")
        if age > float(self.contract["maximum_state_age_seconds"]):
            reasons.append("sample:stale")
        if received + float(self.contract["maximum_future_skew_seconds"]) < sample_time:
            reasons.append("sample:time_after_receive")
        names = sample.get("joint_names")
        positions = sample.get("positions")
        velocities = sample.get("velocities")
        if not isinstance(names, Sequence) or isinstance(names, (str, bytes)):
            reasons.append("sample:joint_names:not_sequence")
            names = []
        elif len(names) != len(set(names)):
            reasons.append("sample:joint_names:duplicate")
        if not isinstance(positions, Sequence) or isinstance(positions, (str, bytes)):
            reasons.append("sample:positions:not_sequence")
            positions = []
        if not isinstance(velocities, Sequence) or isinstance(velocities, (str, bytes)):
            reasons.append("sample:velocities:not_sequence")
            velocities = []
        if len(positions) != len(names):
            reasons.append("sample:positions:length")
        if len(velocities) != len(names):
            reasons.append("sample:velocities:length")
        required = [
            *self.contract["commanded_joint_names"],
            *self.contract["locked_joint_names"],
        ]
        indices: dict[str, int] = {}
        if not reasons:
            indices = {str(name): index for index, name in enumerate(names)}
            missing = [name for name in required if name not in indices]
            if missing:
                reasons.append("sample:required_joint_missing:" + ",".join(missing))
        if reasons:
            return None, sorted(set(reasons))
        assert isinstance(positions, Sequence) and isinstance(velocities, Sequence)
        try:
            arm_positions = [
                _finite(positions[indices[name]], f"position:{name}")
                for name in self.contract["commanded_joint_names"]
            ]
            arm_velocities = [
                _finite(velocities[indices[name]], f"velocity:{name}")
                for name in self.contract["commanded_joint_names"]
            ]
            locked_positions = [
                _finite(positions[indices[name]], f"position:{name}")
                for name in self.contract["locked_joint_names"]
            ]
            locked_velocities = [
                _finite(velocities[indices[name]], f"velocity:{name}")
                for name in self.contract["locked_joint_names"]
            ]
        except ValueError as exc:
            return None, [str(exc)]
        return {
            "source_topic": str(topic),
            "sample_time_seconds": sample_time,
            "arm_positions": arm_positions,
            "arm_velocities": arm_velocities,
            "locked_positions": locked_positions,
            "locked_velocities": locked_velocities,
        }, []

    def arm(self, sample: Mapping[str, Any], *, now_seconds: Any) -> MonitorDecision:
        if self.state != "CREATED":
            return MonitorDecision(
                "arm", False, self.state, ["monitor:not_created"], self.source_topic,
                stop_invocations=self.stop_invocations,
            )
        normalized, reasons = self._normalize(sample, now_seconds)
        if reasons or normalized is None:
            return self._fault(reasons)
        ready = [float(value) for value in self.contract["ready_arm_positions"]]
        tolerance = float(self.contract["ready_arm_tolerance_rad"])
        for index, (actual, expected) in enumerate(zip(normalized["arm_positions"], ready)):
            if abs(actual - expected) > tolerance:
                reasons.append(f"arm:not_ready:{index}")
        stationary = float(self.contract["initial_stationary_velocity_rad_s"])
        for index, velocity in enumerate(normalized["arm_velocities"]):
            if abs(velocity) > stationary:
                reasons.append(f"arm:not_stationary:{index}")
        for index, velocity in enumerate(normalized["locked_velocities"]):
            if abs(velocity) > stationary:
                reasons.append(f"locked:not_stationary:{index}")
        if reasons:
            return self._fault(reasons)
        self.source_topic = normalized["source_topic"]
        self._locked_reference = list(normalized["locked_positions"])
        self._acceleration_time = float(normalized["sample_time_seconds"])
        self._acceleration_velocity = list(normalized["arm_velocities"])
        self.state = "MONITORING"
        return MonitorDecision(
            "arm", True, self.state, source_topic=self.source_topic,
            stop_invocations=self.stop_invocations,
        )

    def observe(self, sample: Mapping[str, Any], *, now_seconds: Any) -> MonitorDecision:
        if self.state != "MONITORING":
            return MonitorDecision(
                "observe", False, self.state, ["monitor:not_monitoring"], self.source_topic,
                stop_invocations=self.stop_invocations,
            )
        normalized, reasons = self._normalize(sample, now_seconds)
        if reasons or normalized is None:
            return self._fault(reasons)
        if normalized["source_topic"] != self.source_topic:
            return self._fault("sample:source_changed")
        maximum_arm_velocity = max(abs(value) for value in normalized["arm_velocities"])
        maximum_locked_velocity = max(abs(value) for value in normalized["locked_velocities"])
        maximum_locked_drift = max(
            abs(actual - reference)
            for actual, reference in zip(
                normalized["locked_positions"], self._locked_reference
            )
        )
        velocity_limits = [float(value) for value in self.limits["maximum_velocity_rad_s"]]
        for index, (actual, limit) in enumerate(zip(normalized["arm_velocities"], velocity_limits)):
            if abs(actual) > limit:
                reasons.append(f"arm:velocity_limit:{index}")
        if maximum_locked_velocity > float(self.contract["locked_maximum_velocity_rad_s"]):
            reasons.append("locked:velocity_limit")
        if maximum_locked_drift > float(self.contract["locked_maximum_position_drift_rad"]):
            reasons.append("locked:position_drift")

        checked_acceleration = False
        maximum_acceleration = 0.0
        assert self._acceleration_time is not None
        sample_time = float(normalized["sample_time_seconds"])
        elapsed = sample_time - self._acceleration_time
        if elapsed <= 0:
            reasons.append("sample:time_not_increasing")
        elif elapsed > float(self.contract["maximum_acceleration_interval_seconds"]):
            reasons.append("sample:acceleration_interval_too_large")
        elif elapsed >= float(self.contract["minimum_acceleration_interval_seconds"]):
            checked_acceleration = True
            accelerations = [
                (actual - previous) / elapsed
                for actual, previous in zip(
                    normalized["arm_velocities"], self._acceleration_velocity
                )
            ]
            maximum_acceleration = max(abs(value) for value in accelerations)
            acceleration_limits = [
                float(value) for value in self.limits["maximum_acceleration_rad_s2"]
            ]
            for index, (actual, limit) in enumerate(zip(accelerations, acceleration_limits)):
                if abs(actual) > limit:
                    reasons.append(f"arm:acceleration_limit:{index}")
            self._acceleration_time = sample_time
            self._acceleration_velocity = list(normalized["arm_velocities"])
        if reasons:
            decision = self._fault(reasons)
            decision.checked_acceleration = checked_acceleration
            decision.maximum_arm_velocity_rad_s = maximum_arm_velocity
            decision.maximum_arm_acceleration_rad_s2 = maximum_acceleration
            decision.maximum_locked_velocity_rad_s = maximum_locked_velocity
            decision.maximum_locked_position_drift_rad = maximum_locked_drift
            return decision
        return MonitorDecision(
            "observe",
            True,
            self.state,
            source_topic=self.source_topic,
            checked_acceleration=checked_acceleration,
            maximum_arm_velocity_rad_s=maximum_arm_velocity,
            maximum_arm_acceleration_rad_s2=maximum_acceleration,
            maximum_locked_velocity_rad_s=maximum_locked_velocity,
            maximum_locked_position_drift_rad=maximum_locked_drift,
            stop_invocations=self.stop_invocations,
        )

    def stop(self) -> MonitorDecision:
        if self.state == "STOPPED":
            return MonitorDecision(
                "stop", True, self.state, source_topic=self.source_topic,
                stop_invocations=self.stop_invocations,
            )
        stop_error = self._invoke_stop_once()
        self.state = "STOPPED" if stop_error is None else "FAULTED"
        return MonitorDecision(
            "stop",
            stop_error is None,
            self.state,
            [] if stop_error is None else [stop_error],
            self.source_topic,
            stop_invocations=self.stop_invocations,
        )

    def fault(self, reason: str) -> MonitorDecision:
        """Latch an external runtime fault and invoke software STOP once."""

        if self.state in {"FAULTED", "STOPPED"}:
            return MonitorDecision(
                "fault", False, self.state, ["monitor:terminal"], self.source_topic,
                stop_invocations=self.stop_invocations,
            )
        return self._fault(reason)
