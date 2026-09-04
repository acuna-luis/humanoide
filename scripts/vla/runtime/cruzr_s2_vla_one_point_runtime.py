#!/usr/bin/env python3
"""Transport/runtime coordinator for exactly one E6.0 checkpoint point.

This module is ROS-free and uses injected state and command backends.  The
versioned activation template is disabled.  Tests may supply a synthetic
enabled grant in memory; production code must receive a run-specific grant.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence


ACTIVATION_SCHEMA = "cruzr-s2-vla-one-point-activation-e6.0w-v1"
CHUNK_SCHEMA = "cruzr-s2-vla-normalized-checkpoint-chunk-e6.0w-v1"


@dataclass
class RuntimeDecision:
    event: str
    accepted: bool
    state: str
    reasons: list[str] = field(default_factory=list)
    frames_published: int = 0
    physical_execution_authorized: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "event": self.event,
            "accepted": self.accepted,
            "state": self.state,
            "reasons": list(self.reasons),
            "frames_published": self.frames_published,
            "physical_execution_authorized": self.physical_execution_authorized,
        }


def _finite(value: Any, label: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label}:not_numeric") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"{label}:non_finite")
    return parsed


def validate_activation_template(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("activation:not_mapping")
    result = dict(value)
    expected = {
        "schema": ACTIVATION_SCHEMA,
        "task_id": 0,
        "axis_profile": "P14_A",
        "scenario": "NO_BOX_READY",
        "selected_state_topic": "/mc/whole_joint_states",
        "chunk_topic": "/vla_inference_result",
        "source_chunk_point_count": 10,
        "accepted_source_point_index": 0,
        "software_stop_is_hardware_estop_equivalent": False,
        "requires_person_at_hardware_estop": True,
        "requires_run_specific_fresh_preflight": True,
        "requires_deterministic_ready_and_recovery": True,
        "requires_static_empty_scene_during_inference": True,
    }
    for key, expected_value in expected.items():
        if result.get(key) != expected_value:
            raise ValueError(f"activation:{key}")
    for key in (
        "maximum_chunk_receipt_age_seconds",
        "maximum_wait_for_chunk_seconds",
        "maximum_dispatch_seconds",
        "maximum_total_runtime_seconds",
    ):
        if _finite(result.get(key), f"activation:{key}") <= 0:
            raise ValueError(f"activation:{key}:not_positive")
    for key in (
        "owner_accepted_engineering_limits",
        "active_launcher_enabled",
        "physical_execution_authorized",
    ):
        if type(result.get(key)) is not bool:
            raise ValueError(f"activation:{key}:not_bool")
    return result


def activation_is_enabled(value: Mapping[str, Any]) -> bool:
    activation = validate_activation_template(value)
    required = (
        activation["owner_accepted_engineering_limits"],
        activation["active_launcher_enabled"],
        activation["physical_execution_authorized"],
        isinstance(activation.get("authorization_scope"), str),
        bool(activation.get("authorization_scope")),
        isinstance(activation.get("authorization_run_id"), str),
        bool(activation.get("authorization_run_id")),
        isinstance(activation.get("authorization_issued_at"), str),
        bool(activation.get("authorization_issued_at")),
        isinstance(activation.get("authorization_expires_at"), str),
        bool(activation.get("authorization_expires_at")),
        type(activation.get("authorization_valid_seconds")) is int,
        30 <= int(activation.get("authorization_valid_seconds", 0)) <= 180,
        all(
            isinstance(activation.get(key), str) and len(activation[key]) == 64
            for key in (
                "authorization_preflight_sha256",
                "authorization_ready_sha256",
                "authorization_acceptance_sha256",
                "authorization_limits_sha256",
            )
        ),
    )
    return all(required)


class OnePointCanaryRuntime:
    """Join measured-state monitoring to one bounded SDK trajectory."""

    def __init__(
        self,
        *,
        activation: Mapping[str, Any],
        monitor_contract: Mapping[str, Any],
        transport_contract: Mapping[str, Any],
        limits: Mapping[str, Any],
        profile: Mapping[str, Any],
        monitor_type: Any,
        transport_type: Any,
        backend_factory: Callable[[], Any],
    ) -> None:
        self.activation = validate_activation_template(activation)
        if not activation_is_enabled(self.activation):
            raise PermissionError("activation:not_enabled")
        if self.activation["selected_state_topic"] not in {
            item["topic"] for item in monitor_contract["allowed_state_sources"]
        }:
            raise ValueError("activation:selected_state_topic")
        expected_names = [
            *transport_contract["commanded_joint_names"],
            *transport_contract["locked_joint_names"],
        ]
        if profile.get("joint_names") != expected_names:
            raise ValueError("profile:joint_names")
        if profile.get("action_dim") != 20 or profile.get("action_horizon") != 10:
            raise ValueError("profile:dimensions")
        self.monitor_contract = dict(monitor_contract)
        self.transport_contract = dict(transport_contract)
        self.limits = dict(limits)
        self.profile = dict(profile)
        self.monitor_type = monitor_type
        self.transport_type = transport_type
        self.backend_factory = backend_factory
        self.backend: Any | None = None
        self.adapter: Any | None = None
        self.state = "WAITING_FOR_READY_STATE"
        self.started_at: float | None = None
        self.dispatch_started_at: float | None = None
        self.last_state_received: float | None = None
        self.latest_positions: list[float] = []
        self.latest_arm_positions: list[float] = []
        self.accepted_chunk_id: int | None = None
        self.monitor = monitor_type.MeasuredStateMonitor(
            contract=monitor_contract,
            limits=limits,
            stop_callback=self._stop_transport,
        )

    @property
    def frames_published(self) -> int:
        return 0 if self.adapter is None else int(self.adapter.frames_published)

    def _stop_transport(self) -> None:
        if self.adapter is not None:
            self.adapter.stop()
        elif self.backend is not None:
            self.backend.stop()

    def _fault(self, reason: str) -> RuntimeDecision:
        monitor_decision = self.monitor.fault(reason)
        self.state = "FAULTED"
        return RuntimeDecision(
            "fault", False, self.state,
            [reason, *monitor_decision.reasons], self.frames_published,
        )

    def _ordered_state(self, sample: Mapping[str, Any]) -> list[float]:
        names = sample.get("joint_names")
        positions = sample.get("positions")
        if not isinstance(names, Sequence) or isinstance(names, (str, bytes)):
            raise ValueError("state:joint_names")
        if not isinstance(positions, Sequence) or isinstance(positions, (str, bytes)):
            raise ValueError("state:positions")
        if len(names) != len(positions) or len(names) != len(set(names)):
            raise ValueError("state:shape")
        indices = {str(name): index for index, name in enumerate(names)}
        result = []
        for name in self.profile["joint_names"]:
            if name not in indices:
                raise ValueError(f"state:missing:{name}")
            result.append(_finite(positions[indices[name]], f"state:{name}"))
        return result

    def receive_state(
        self, sample: Mapping[str, Any], *, now_seconds: Any
    ) -> RuntimeDecision:
        try:
            now = _finite(now_seconds, "now_seconds")
            ordered = self._ordered_state(sample)
        except ValueError as exc:
            return self._fault(str(exc))
        if sample.get("source_topic") != self.activation["selected_state_topic"]:
            return self._fault("state:unexpected_source")
        if self.started_at is None:
            self.started_at = now
        if now - self.started_at > float(self.activation["maximum_total_runtime_seconds"]):
            return self._fault("runtime:timeout")
        if (
            self.state == "WAITING_FOR_ONE_CHUNK"
            and now - self.started_at > float(self.activation["maximum_wait_for_chunk_seconds"])
        ):
            return self._fault("runtime:chunk_wait_timeout")
        if self.monitor.state == "CREATED":
            decision = self.monitor.arm(sample, now_seconds=now)
        else:
            decision = self.monitor.observe(sample, now_seconds=now)
        if not decision.accepted:
            self.state = "FAULTED"
            return RuntimeDecision(
                "state", False, self.state, decision.reasons,
                self.frames_published,
            )
        self.last_state_received = now
        self.latest_positions = ordered
        self.latest_arm_positions = ordered[:14]
        if self.state == "WAITING_FOR_READY_STATE":
            self.state = "WAITING_FOR_ONE_CHUNK"
        return RuntimeDecision(
            "state", True, self.state, frames_published=self.frames_published,
            physical_execution_authorized=True,
        )

    def receive_chunk(
        self, chunk: Mapping[str, Any], *, now_seconds: Any
    ) -> RuntimeDecision:
        if self.state != "WAITING_FOR_ONE_CHUNK":
            return self._fault("chunk:unexpected_runtime_state")
        try:
            now = _finite(now_seconds, "now_seconds")
        except ValueError as exc:
            return self._fault(str(exc))
        if self.last_state_received is None or now - self.last_state_received > float(
            self.monitor_contract["maximum_state_age_seconds"]
        ):
            return self._fault("chunk:state_stale")
        expected = {
            "schema": CHUNK_SCHEMA,
            "source_topic": self.activation["chunk_topic"],
            "status_code": 1,
        }
        reasons = [
            f"chunk:{key}"
            for key, value in expected.items()
            if chunk.get(key) != value
        ]
        chunk_id = chunk.get("chunk_id")
        if type(chunk_id) is not int or chunk_id < 0:
            reasons.append("chunk:id")
        received = chunk.get("received_time_seconds")
        try:
            received_time = _finite(received, "chunk:received_time")
            inference_time = _finite(chunk.get("inference_time_seconds"), "chunk:inference_time")
        except ValueError as exc:
            reasons.append(str(exc))
            received_time = -math.inf
            inference_time = -math.inf
        if inference_time < 0:
            reasons.append("chunk:inference_time:negative")
        age = now - received_time
        if age < -0.005 or age > float(self.activation["maximum_chunk_receipt_age_seconds"]):
            reasons.append("chunk:stale_or_future")
        points = chunk.get("points")
        if not isinstance(points, Sequence) or isinstance(points, (str, bytes)):
            reasons.append("chunk:points:not_sequence")
            points = []
        if len(points) != int(self.activation["source_chunk_point_count"]):
            reasons.append("chunk:point_count")
        parsed_points: list[list[float]] = []
        point_times: list[float] = []
        if not reasons:
            for point_index, point in enumerate(points):
                if not isinstance(point, Mapping):
                    reasons.append(f"chunk:point:{point_index}:not_mapping")
                    break
                positions = point.get("positions")
                if not isinstance(positions, Sequence) or isinstance(positions, (str, bytes)) or len(positions) != 20:
                    reasons.append(f"chunk:point:{point_index}:dimension")
                    break
                try:
                    parsed_points.append([
                        _finite(value, f"chunk:point:{point_index}:{axis}")
                        for axis, value in enumerate(positions)
                    ])
                    point_times.append(_finite(point.get("time_from_start_seconds"), f"chunk:time:{point_index}"))
                except ValueError as exc:
                    reasons.append(str(exc))
                    break
        if point_times:
            if abs(point_times[0]) > 1e-12:
                reasons.append("chunk:first_time_not_zero")
            if any(second <= first for first, second in zip(point_times, point_times[1:])):
                reasons.append("chunk:times_not_increasing")
        if reasons:
            return self._fault(";".join(sorted(set(reasons))))
        point = parsed_points[int(self.activation["accepted_source_point_index"])]
        lower = [float(value) for value in self.profile["lower_boundary"]]
        upper = [float(value) for value in self.profile["upper_boundary"]]
        range_tolerance = float(self.profile["range_tolerance"])
        for index, value in enumerate(point[:14]):
            if value < lower[index] - range_tolerance or value > upper[index] + range_tolerance:
                reasons.append(f"chunk:range:{index}")
        if reasons:
            return self._fault(";".join(reasons))
        # P14 commands arms only.  Checkpoint values for H/L/W are deliberately
        # discarded and replaced with the fresh measured hold before the
        # transport-neutral intent is constructed.
        point[14:] = self.latest_positions[14:]
        intent = {
            "schema": self.transport_contract["input_intent_schema"],
            "task_id": 0,
            "axis_profile": "P14_A",
            "scenario": "NO_BOX_READY",
            "sequence_id": chunk_id,
            "source_point_index": 0,
            "joint_names": list(self.profile["joint_names"]),
            "positions": point,
            "physical_execution_authorized": False,
            "physical_transport": None,
            "physical_publisher_count": 0,
        }
        # Validate the complete trajectory before constructing the ROS backend.
        # Backend construction creates the SDK command publisher, so even a
        # target-delta rejection must remain publisher-free.
        try:
            self.transport_type.plan_minimum_jerk(
                self.latest_arm_positions, point[:14], self.limits
            )
        except ValueError as exc:
            return self._fault(f"transport:preflight:{exc}")
        try:
            self.backend = self.backend_factory()
            self.adapter = self.transport_type.OnePointSdkTransportAdapter(
                contract=self.transport_contract,
                limits=self.limits,
                backend=self.backend,
                dispatch_enabled=True,
            )
            decision = self.adapter.arm(
                intent,
                measured_arm_positions=self.latest_arm_positions,
                state_age_seconds=now - self.last_state_received,
            )
        except Exception as exc:
            return self._fault(f"transport:create:{type(exc).__name__}:{exc}")
        if not decision.accepted:
            return self._fault("transport:arm:" + ";".join(decision.reasons))
        self.accepted_chunk_id = chunk_id
        self.dispatch_started_at = now
        self.state = "DISPATCHING_ONE_POINT"
        return RuntimeDecision(
            "chunk", True, self.state, frames_published=self.frames_published,
            physical_execution_authorized=True,
        )

    def tick(self, *, now_seconds: Any) -> RuntimeDecision:
        if self.state != "DISPATCHING_ONE_POINT" or self.adapter is None:
            return RuntimeDecision(
                "tick", False, self.state, ["runtime:not_dispatching"],
                self.frames_published,
            )
        try:
            now = _finite(now_seconds, "now_seconds")
        except ValueError as exc:
            return self._fault(str(exc))
        if self.started_at is None or now - self.started_at > float(
            self.activation["maximum_total_runtime_seconds"]
        ):
            return self._fault("runtime:timeout")
        if self.dispatch_started_at is None or now - self.dispatch_started_at > float(
            self.activation["maximum_dispatch_seconds"]
        ):
            return self._fault("runtime:dispatch_timeout")
        if self.last_state_received is None or now - self.last_state_received > float(
            self.monitor_contract["maximum_state_age_seconds"]
        ):
            return self._fault("runtime:state_stale")
        decision = self.adapter.step()
        if not decision.accepted:
            return self._fault("transport:step:" + ";".join(decision.reasons))
        if self.adapter.state == "COMPLETED":
            self.monitor.stop()
            self.state = "COMPLETED"
        return RuntimeDecision(
            "tick", True, self.state, frames_published=self.frames_published,
            physical_execution_authorized=True,
        )

    def stop(self) -> RuntimeDecision:
        self.monitor.stop()
        self.state = "STOPPED"
        return RuntimeDecision(
            "stop", True, self.state, frames_published=self.frames_published,
        )
