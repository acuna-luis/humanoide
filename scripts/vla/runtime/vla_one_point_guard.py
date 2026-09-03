#!/usr/bin/env python3
"""Fail-closed offline guard for the Cruzr S2 E6.0 one-point preview.

The module deliberately has no ROS, network, subprocess or hardware API.  It
can accept a structurally valid preview into an in-memory dictionary, but it
cannot authorize or emit physical execution.
"""

from __future__ import annotations

import json
import math
import pathlib
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


EXPECTED_CONTRACT_SCHEMA = "cruzr-s2-vla-offline-executor-guard-contract-e6.0d-v1"
EXPECTED_MESSAGE_SCHEMA = "cruzr-s2-vla-one-point-preview-e6.0e-v1"
OFFLINE_READY_TOLERANCE_RAD = 1e-9
LOCKED_HOLD_TOLERANCE_RAD = 1e-12


@dataclass
class GuardDecision:
    event: str
    preview_accepted: bool
    physical_execution_authorized: bool = False
    reasons: list[str] = field(default_factory=list)
    physical_blockers: list[str] = field(default_factory=list)
    preview: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "event": self.event,
            "preview_accepted": self.preview_accepted,
            "physical_execution_authorized": False,
            "reasons": list(self.reasons),
            "physical_blockers": list(self.physical_blockers),
            "preview": self.preview,
        }


def _load_json(path: pathlib.Path | str) -> dict[str, Any]:
    with pathlib.Path(path).open("r", encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise ValueError("expected JSON object")
    return value


def _finite(value: Any, label: str, reasons: list[str]) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        reasons.append(f"{label}:not_numeric")
        return None
    if not math.isfinite(parsed):
        reasons.append(f"{label}:non_finite")
        return None
    return parsed


def _vector(
    value: Any,
    expected: int,
    label: str,
    reasons: list[str],
) -> list[float] | None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        reasons.append(f"{label}:not_sequence")
        return None
    if len(value) != expected:
        reasons.append(f"{label}:dimension:{len(value)}!=expected:{expected}")
        return None
    result: list[float] = []
    for index, item in enumerate(value):
        parsed = _finite(item, f"{label}:{index}", reasons)
        if parsed is None:
            return None
        result.append(parsed)
    return result


def validate_guard_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    contract = dict(value)
    if contract.get("schema") != EXPECTED_CONTRACT_SCHEMA:
        raise ValueError("guard contract schema mismatch")
    if contract.get("state") != "SPECIFICATION_ONLY_FAIL_CLOSED":
        raise ValueError("guard contract must remain specification-only")
    if contract.get("physical_execution_enabled") is not False:
        raise ValueError("physical execution must remain disabled")
    if contract.get("publisher_or_command_topic") is not None:
        raise ValueError("guard contract must not name a command topic")
    if contract.get("maximum_canary_point_count") != 1:
        raise ValueError("guard contract must allow exactly one preview point")
    if contract.get("maximum_acceleration_rad_s2") is not None:
        raise ValueError("E6.0D evidence unexpectedly contains acceleration limits")
    if contract.get("required_physical_clearance_m") is not None:
        raise ValueError("E6.0D evidence unexpectedly certifies physical clearance")
    if contract.get("continuous_path_certified") is not False:
        raise ValueError("continuous path must remain uncertified")
    if contract.get("installed_passive_clamp_geometry_present") is not False:
        raise ValueError("passive clamp geometry must remain absent")
    blockers = contract.get("hard_fail_conditions")
    if not isinstance(blockers, list) or not blockers:
        raise ValueError("guard contract must retain hard fail conditions")
    for key in (
        "commanded_joint_names",
        "locked_joint_names",
        "derived_effective_first_delta_rad_not_certified",
    ):
        if not isinstance(contract.get(key), list):
            raise ValueError(f"guard contract missing list: {key}")
    if len(contract["commanded_joint_names"]) != 14:
        raise ValueError("guard contract must command 14 arm joints")
    if len(contract["locked_joint_names"]) != 6:
        raise ValueError("guard contract must lock six joints")
    if len(contract["derived_effective_first_delta_rad_not_certified"]) != 14:
        raise ValueError("guard contract must define 14 preview delta bounds")
    return contract


def load_guard_contract(path: pathlib.Path | str) -> dict[str, Any]:
    return validate_guard_contract(_load_json(path))


def load_profile(path: pathlib.Path | str) -> dict[str, Any]:
    profile = _load_json(path)
    if profile.get("action_dim") != 20 or profile.get("action_horizon") != 10:
        raise ValueError("unexpected profile dimensions")
    for key in ("joint_names", "lower_boundary", "upper_boundary"):
        if not isinstance(profile.get(key), list) or len(profile[key]) != 20:
            raise ValueError(f"invalid profile field: {key}")
    if len(set(profile["joint_names"])) != 20:
        raise ValueError("profile joint names are not unique")
    return profile


class OnePointGuard:
    """Validate one in-memory P14 preview and latch after the first acceptance."""

    def __init__(
        self,
        *,
        contract: Mapping[str, Any],
        profile: Mapping[str, Any],
        ready_arm_state: Sequence[Any],
        runtime_id: str,
        checkpoint_id: str,
    ) -> None:
        self.contract = dict(contract)
        self.profile = dict(profile)
        reasons: list[str] = []
        parsed_ready = _vector(ready_arm_state, 14, "ready_arm_state", reasons)
        if reasons or parsed_ready is None:
            raise ValueError(";".join(reasons))
        self.ready_arm_state = parsed_ready
        self.runtime_id = runtime_id
        self.checkpoint_id = checkpoint_id
        self.consumed = False
        self.last_sequence_id: int | None = None

        profile_names = list(self.profile["joint_names"])
        if profile_names[:14] != list(self.contract["commanded_joint_names"]):
            raise ValueError("commanded joint order mismatch")
        if profile_names[14:] != list(self.contract["locked_joint_names"]):
            raise ValueError("locked joint order mismatch")

    @property
    def physical_publisher_count(self) -> int:
        return 0

    @property
    def physical_blockers(self) -> list[str]:
        return sorted(set([
            *self.contract["hard_fail_conditions"],
            "ready_state_physical_tolerance_rad",
            "s2_ready_task_installed_and_registered",
            "fresh_physical_preflight",
        ]))

    def evaluate(self, message: Mapping[str, Any], *, now: Any) -> GuardDecision:
        reasons: list[str] = []
        timestamp = _finite(now, "receive_time", reasons)
        if self.consumed:
            reasons.append("session:one_point_already_consumed")

        expected = {
            "schema": EXPECTED_MESSAGE_SCHEMA,
            "mode": "offline_preview_only",
            "runtime_id": self.runtime_id,
            "checkpoint_id": self.checkpoint_id,
            "task_id": 0,
            "axis_profile": "P14_A",
            "scenario": "NO_BOX_READY",
        }
        for key, value in expected.items():
            if message.get(key) != value:
                reasons.append(f"{key}:mismatch")
        if message.get("physical_execution_requested") is not False:
            reasons.append("physical_execution_requested:must_be_false")
        client_id = message.get("client_id")
        if not isinstance(client_id, str) or not client_id.strip():
            reasons.append("client_id:invalid")
        sequence_id = message.get("sequence_id")
        if type(sequence_id) is not int or sequence_id < 0:
            reasons.append("sequence_id:invalid")
        elif self.last_sequence_id is not None and sequence_id <= self.last_sequence_id:
            reasons.append("sequence_id:not_increasing")

        sent = _finite(message.get("sent_monotonic"), "sent_time", reasons)
        state_at = _finite(message.get("state_monotonic"), "state_time", reasons)
        image_at = _finite(message.get("image_monotonic"), "image_time", reasons)
        if timestamp is not None:
            freshness_limits = (
                ("sent_time", sent, 0.50),
                ("state_time", state_at, float(self.contract["maximum_state_age_seconds"])),
                ("image_time", image_at, 1.0),
            )
            for label, observed, maximum_age in freshness_limits:
                if observed is None:
                    continue
                age = timestamp - observed
                if age < -0.05:
                    reasons.append(f"{label}:from_future")
                if age > maximum_age:
                    reasons.append(f"{label}:stale")

        names = message.get("joint_names")
        if (list(names) if isinstance(names, (list, tuple)) else None) != list(
            self.profile["joint_names"]
        ):
            reasons.append("joint_names:order_or_membership_mismatch")
        state = _vector(message.get("state_positions"), 20, "state_positions", reasons)

        points_value = message.get("points")
        if not isinstance(points_value, Sequence) or isinstance(points_value, (str, bytes)):
            reasons.append("points:not_sequence")
            points: list[Any] = []
        else:
            points = list(points_value)
        if len(points) != 1:
            reasons.append(f"points:count:{len(points)}!=expected:1")
        point: list[float] | None = None
        if len(points) == 1 and isinstance(points[0], Mapping):
            point = _vector(points[0].get("positions"), 20, "point:positions", reasons)
            point_time = _finite(points[0].get("time_from_start"), "point:time", reasons)
            if point_time is not None and abs(point_time) > 1e-12:
                reasons.append("point:time:must_be_zero_for_one_point_preview")
        elif len(points) == 1:
            reasons.append("point:not_mapping")

        if state is not None:
            for index, expected_ready in enumerate(self.ready_arm_state):
                if abs(state[index] - expected_ready) > OFFLINE_READY_TOLERANCE_RAD:
                    reasons.append(f"state:not_exact_offline_ready:{self.profile['joint_names'][index]}")

        lower = [float(value) for value in self.profile["lower_boundary"]]
        upper = [float(value) for value in self.profile["upper_boundary"]]
        tolerance = float(self.profile["range_tolerance"])
        for label, vector in (("state", state), ("point", point)):
            if vector is None:
                continue
            for index, value in enumerate(vector):
                if value < lower[index] - tolerance or value > upper[index] + tolerance:
                    reasons.append(f"{label}:range:{self.profile['joint_names'][index]}")

        if state is not None and point is not None:
            delta_limits = [
                float(value)
                for value in self.contract[
                    "derived_effective_first_delta_rad_not_certified"
                ]
            ]
            for index, limit in enumerate(delta_limits):
                if abs(point[index] - state[index]) > limit + 1e-12:
                    reasons.append(f"first_point_delta:{self.profile['joint_names'][index]}")
            for index in range(14, 20):
                if abs(point[index] - state[index]) > LOCKED_HOLD_TOLERANCE_RAD:
                    reasons.append(f"locked_axis_changed:{self.profile['joint_names'][index]}")

        reasons = sorted(set(reasons))
        if reasons:
            return GuardDecision(
                "evaluate_one_point", False, reasons=reasons,
                physical_blockers=self.physical_blockers,
            )

        assert state is not None and point is not None and type(sequence_id) is int
        preview = {
            "schema": "cruzr-s2-vla-one-point-in-memory-preview-e6.0e-v1",
            "sink_only": True,
            "mode": "offline_preview_only",
            "sequence_id": sequence_id,
            "task_id": 0,
            "axis_profile": "P14_A",
            "scenario": "NO_BOX_READY",
            "joint_names": list(self.profile["joint_names"]),
            "state_positions": state,
            "preview_point": point,
            "locked_joint_names": list(self.contract["locked_joint_names"]),
            "physical_publisher_count": 0,
            "publisher_or_command_topic": None,
            "physical_execution_authorized": False,
        }
        self.consumed = True
        self.last_sequence_id = sequence_id
        return GuardDecision(
            "evaluate_one_point", True, physical_execution_authorized=False,
            physical_blockers=self.physical_blockers, preview=preview,
        )


def nominal_message(
    guard: OnePointGuard,
    *,
    now: float,
    sequence_id: int = 1,
) -> dict[str, Any]:
    lower = [float(value) for value in guard.profile["lower_boundary"]]
    upper = [float(value) for value in guard.profile["upper_boundary"]]
    state = [(low + high) / 2.0 for low, high in zip(lower, upper)]
    state[:14] = guard.ready_arm_state
    return {
        "schema": EXPECTED_MESSAGE_SCHEMA,
        "mode": "offline_preview_only",
        "physical_execution_requested": False,
        "runtime_id": guard.runtime_id,
        "checkpoint_id": guard.checkpoint_id,
        "task_id": 0,
        "axis_profile": "P14_A",
        "scenario": "NO_BOX_READY",
        "client_id": "e6.0e-offline-primary",
        "sequence_id": sequence_id,
        "sent_monotonic": now - 0.02,
        "state_monotonic": now - 0.05,
        "image_monotonic": now - 0.05,
        "joint_names": list(guard.profile["joint_names"]),
        "state_positions": state,
        "points": [{"positions": list(state), "time_from_start": 0.0}],
    }
