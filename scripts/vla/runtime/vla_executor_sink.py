#!/usr/bin/env python3
"""Pure in-memory safety sink for Cruzr S2 VLA chunks.

This module has no ROS, network, process-control or hardware dependency.  It
validates and serializes an effective 10x20 command only into Python data.  A
separate, future physical executor must not be inferred from this sink.
"""

from __future__ import annotations

import json
import math
import pathlib
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


AXIS_PROFILES: dict[str, tuple[str, ...]] = {
    "P14_A": ("A",),
    "P15_AW": ("A", "W"),
    "P16_AH": ("A", "H"),
    "P17_AL": ("A", "L"),
    "P17_AHW": ("A", "H", "W"),
    "P18_ALW": ("A", "L", "W"),
    "P19_AHL": ("A", "H", "L"),
    "P20_AHLW": ("A", "H", "L", "W"),
}

GROUP_INDICES: dict[str, tuple[int, ...]] = {
    "A": tuple(range(0, 14)),
    "H": tuple(range(14, 16)),
    "L": tuple(range(16, 19)),
    "W": (19,),
}

VALID_TASK_IDS = (0, 1, 2, 3)
VALID_FIXTURES = ("low", "middle")


@dataclass
class SinkDecision:
    event: str
    accepted: bool
    reasons: list[str] = field(default_factory=list)
    command: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "event": self.event,
            "accepted": self.accepted,
            "reasons": list(self.reasons),
            "command": self.command,
        }


def load_profile(path: pathlib.Path | str) -> dict[str, Any]:
    profile_path = pathlib.Path(path)
    with profile_path.open("r", encoding="utf-8") as source:
        profile = json.load(source)
    dim = int(profile["action_dim"])
    if dim != 20:
        raise ValueError(f"profile action_dim must be 20, got {dim}")
    if int(profile["action_horizon"]) != 10:
        raise ValueError("profile action_horizon must be 10")
    for key in (
        "joint_names",
        "lower_boundary",
        "upper_boundary",
        "max_interpoint_speed",
        "max_first_point_delta",
    ):
        if len(profile[key]) != dim:
            raise ValueError(f"{key} length must be {dim}")
    if len(set(profile["joint_names"])) != dim:
        raise ValueError("joint_names must be unique")
    return profile


def enabled_indices(axis_profile: str) -> tuple[int, ...]:
    try:
        groups = AXIS_PROFILES[axis_profile]
    except KeyError as exc:
        raise ValueError(f"unknown axis profile: {axis_profile}") from exc
    return tuple(index for group in groups for index in GROUP_INDICES[group])


def synthetic_fixture_hold(profile: Mapping[str, Any], fixture: str) -> list[float]:
    """Return a deterministic mock pose; this is not a physical VLA-ready pose."""

    if fixture not in VALID_FIXTURES:
        raise ValueError(f"unknown fixture: {fixture}")
    fraction = 0.50 if fixture == "low" else 0.55
    return [
        float(low) + fraction * (float(high) - float(low))
        for low, high in zip(profile["lower_boundary"], profile["upper_boundary"])
    ]


def _finite_float(value: Any, label: str, reasons: list[str]) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        reasons.append(f"{label}:not_numeric")
        return None
    if not math.isfinite(result):
        reasons.append(f"{label}:non_finite")
        return None
    return result


def _finite_vector(
    values: Any,
    expected: int,
    label: str,
    reasons: list[str],
) -> list[float] | None:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        reasons.append(f"{label}:not_sequence")
        return None
    if len(values) != expected:
        reasons.append(f"{label}:dimension:{len(values)}!=expected:{expected}")
        return None
    result: list[float] = []
    for index, value in enumerate(values):
        parsed = _finite_float(value, f"{label}:{index}", reasons)
        if parsed is None:
            return None
        result.append(parsed)
    return result


class VlaExecutorSink:
    """Stateful fail-closed validator whose only output is a Python dictionary."""

    def __init__(
        self,
        *,
        profile: Mapping[str, Any],
        axis_profile: str,
        fixture: str,
        runtime_id: str,
        checkpoint_id: str,
    ) -> None:
        if fixture not in VALID_FIXTURES:
            raise ValueError(f"unknown fixture: {fixture}")
        self.profile = dict(profile)
        self.axis_profile = axis_profile
        self.fixture = fixture
        self.runtime_id = runtime_id
        self.checkpoint_id = checkpoint_id
        self.enabled = enabled_indices(axis_profile)
        self.enabled_set = set(self.enabled)
        self.hold_state = synthetic_fixture_hold(profile, fixture)
        self.active_client: str | None = None
        self.deadman_active = False
        self.deadman_refreshed_at: float | None = None
        self.canceled = False
        self.stopped = False
        self.last_chunk_id: int | None = None
        self.accepted_chunks = 0
        self.rejected_chunks = 0

    @property
    def physical_publisher_count(self) -> int:
        return 0

    def acquire_client(self, client_id: str) -> SinkDecision:
        if not client_id:
            return SinkDecision("acquire_client", False, ["client_id:empty"])
        if self.active_client is None:
            self.active_client = client_id
            return SinkDecision("acquire_client", True)
        if self.active_client == client_id:
            return SinkDecision("acquire_client", True)
        return SinkDecision("acquire_client", False, ["client:already_owned"])

    def refresh_deadman(self, client_id: str, now: float) -> SinkDecision:
        reasons = self._client_reasons(client_id)
        timestamp = _finite_float(now, "deadman_time", reasons)
        if self.canceled:
            reasons.append("session:canceled")
        if self.stopped:
            reasons.append("session:stopped")
        if reasons:
            return SinkDecision("refresh_deadman", False, reasons)
        self.deadman_active = True
        self.deadman_refreshed_at = timestamp
        return SinkDecision("refresh_deadman", True)

    def cancel(self, client_id: str) -> SinkDecision:
        reasons = self._client_reasons(client_id)
        if reasons:
            return SinkDecision("cancel", False, reasons)
        self.canceled = True
        self.deadman_active = False
        return SinkDecision("cancel", True)

    def stop(self) -> SinkDecision:
        self.stopped = True
        self.deadman_active = False
        return SinkDecision("stop", True)

    def poll(self, now: float) -> SinkDecision:
        reasons: list[str] = []
        timestamp = _finite_float(now, "poll_time", reasons)
        if reasons:
            return SinkDecision("poll", False, reasons)
        if (
            self.deadman_active
            and self.deadman_refreshed_at is not None
            and timestamp - self.deadman_refreshed_at
            > float(self.profile.get("max_deadman_gap_seconds", 0.50))
        ):
            self.stopped = True
            self.deadman_active = False
            return SinkDecision("poll", False, ["deadman:timeout_stop_latched"])
        return SinkDecision("poll", True)

    def _client_reasons(self, client_id: str) -> list[str]:
        if self.active_client is None:
            return ["client:not_acquired"]
        if client_id != self.active_client:
            return ["client:mismatch"]
        return []

    def submit(self, message: Mapping[str, Any], *, now: float) -> SinkDecision:
        reasons: list[str] = []
        timestamp = _finite_float(now, "receive_time", reasons)
        client_id = message.get("client_id")
        reasons.extend(self._client_reasons(client_id if isinstance(client_id, str) else ""))
        if self.canceled:
            reasons.append("session:canceled")
        if self.stopped:
            reasons.append("session:stopped")
        if not self.deadman_active:
            reasons.append("deadman:not_active")
        elif self.deadman_refreshed_at is None:
            reasons.append("deadman:missing_timestamp")
        elif timestamp is not None and timestamp - self.deadman_refreshed_at > float(
            self.profile.get("max_deadman_gap_seconds", 0.50)
        ):
            self.stopped = True
            self.deadman_active = False
            reasons.append("deadman:timeout_stop_latched")

        expected_scalars = {
            "runtime_id": self.runtime_id,
            "checkpoint_id": self.checkpoint_id,
            "axis_profile": self.axis_profile,
            "fixture": self.fixture,
        }
        for key, expected in expected_scalars.items():
            if message.get(key) != expected:
                reasons.append(f"{key}:mismatch")
        task_id = message.get("task_id")
        if type(task_id) is not int or task_id not in VALID_TASK_IDS:
            reasons.append("task_id:invalid")

        chunk_id_value = message.get("chunk_id")
        chunk_id: int | None = None
        if type(chunk_id_value) is not int or chunk_id_value < 0:
            reasons.append("chunk_id:invalid")
        else:
            chunk_id = chunk_id_value
            if self.last_chunk_id is not None and chunk_id <= self.last_chunk_id:
                reasons.append(f"chunk_id:not_increasing:{chunk_id}<={self.last_chunk_id}")

        sent_at = _finite_float(message.get("sent_monotonic"), "chunk_time", reasons)
        if timestamp is not None and sent_at is not None:
            age = timestamp - sent_at
            if age < -0.05:
                reasons.append("chunk_time:from_future")
            if age > float(self.profile.get("max_chunk_age_seconds", 0.50)):
                reasons.append("chunk_time:stale")

        names = message.get("joint_names")
        if (list(names) if isinstance(names, (list, tuple)) else None) != list(
            self.profile["joint_names"]
        ):
            reasons.append("joint_names:order_or_membership_mismatch")

        dim = int(self.profile["action_dim"])
        state_names = message.get("state_joint_names")
        if (list(state_names) if isinstance(state_names, (list, tuple)) else None) != list(
            self.profile["joint_names"]
        ):
            reasons.append("state_joint_names:order_or_membership_mismatch")
        state = _finite_vector(message.get("state_positions"), dim, "state_positions", reasons)
        state_at = _finite_float(message.get("state_monotonic"), "state_time", reasons)
        image_at = _finite_float(message.get("image_monotonic"), "image_time", reasons)
        if timestamp is not None and state_at is not None:
            state_age = timestamp - state_at
            if state_age < -0.05:
                reasons.append("state_time:from_future")
            if state_age > float(self.profile["max_state_age_seconds"]):
                reasons.append("state_time:stale")
        if timestamp is not None and image_at is not None:
            image_age = timestamp - image_at
            if image_age < -0.05:
                reasons.append("image_time:from_future")
            if image_age > float(self.profile.get("max_image_age_seconds", 1.0)):
                reasons.append("image_time:stale")

        points_value = message.get("points")
        if not isinstance(points_value, Sequence) or isinstance(points_value, (str, bytes)):
            reasons.append("points:not_sequence")
            points: list[Any] = []
        else:
            points = list(points_value)
        horizon = int(self.profile["action_horizon"])
        if len(points) != horizon:
            reasons.append(f"points:horizon:{len(points)}!=expected:{horizon}")

        rows: list[list[float] | None] = []
        point_times: list[float | None] = []
        for index, point in enumerate(points):
            if not isinstance(point, Mapping):
                reasons.append(f"point:{index}:not_mapping")
                rows.append(None)
                point_times.append(None)
                continue
            rows.append(_finite_vector(point.get("positions"), dim, f"point:{index}:positions", reasons))
            point_times.append(
                _finite_float(point.get("time_from_start"), f"point:{index}:time", reasons)
            )

        complete_rows = len(rows) == horizon and all(row is not None for row in rows)
        complete_times = len(point_times) == horizon and all(value is not None for value in point_times)
        if complete_times:
            expected_dt = float(self.profile["point_dt_seconds"])
            tolerance = float(self.profile["point_dt_tolerance_seconds"])
            finite_times = [float(value) for value in point_times if value is not None]
            for index, value in enumerate(finite_times):
                expected = index * expected_dt
                if index and value <= finite_times[index - 1]:
                    reasons.append(f"point:{index}:time:not_monotonic")
                if abs(value - expected) > tolerance:
                    reasons.append(f"point:{index}:time:off_schedule")

        if complete_rows:
            finite_rows = [row for row in rows if row is not None]
            lower = [float(value) for value in self.profile["lower_boundary"]]
            upper = [float(value) for value in self.profile["upper_boundary"]]
            range_tolerance = float(self.profile["range_tolerance"])
            for point_index, row in enumerate(finite_rows):
                for joint_index, value in enumerate(row):
                    if value < lower[joint_index] - range_tolerance or value > upper[joint_index] + range_tolerance:
                        reasons.append(
                            f"point:{point_index}:range:{self.profile['joint_names'][joint_index]}"
                        )
            if state is not None:
                delta_limits = [float(value) for value in self.profile["max_first_point_delta"]]
                for joint_index in self.enabled:
                    if abs(finite_rows[0][joint_index] - state[joint_index]) > delta_limits[joint_index]:
                        reasons.append(f"first_point_delta:{self.profile['joint_names'][joint_index]}")
            if complete_times:
                finite_times = [float(value) for value in point_times if value is not None]
                speed_limits = [float(value) for value in self.profile["max_interpoint_speed"]]
                for point_index in range(1, horizon):
                    delta_time = finite_times[point_index] - finite_times[point_index - 1]
                    if delta_time <= 0:
                        continue
                    for joint_index in self.enabled:
                        speed = abs(
                            finite_rows[point_index][joint_index]
                            - finite_rows[point_index - 1][joint_index]
                        ) / delta_time
                        if speed > speed_limits[joint_index]:
                            reasons.append(
                                f"interpoint_speed:{self.profile['joint_names'][joint_index]}"
                            )

        if reasons:
            self.rejected_chunks += 1
            return SinkDecision("submit_chunk", False, sorted(set(reasons)))

        assert chunk_id is not None
        assert complete_rows
        finite_rows = [row for row in rows if row is not None]
        effective_rows = [
            [
                row[index] if index in self.enabled_set else self.hold_state[index]
                for index in range(dim)
            ]
            for row in finite_rows
        ]
        command = {
            "schema": "cruzr-s2-vla-sink-command-v1",
            "sink_only": True,
            "runtime_id": self.runtime_id,
            "checkpoint_id": self.checkpoint_id,
            "task_id": task_id,
            "axis_profile": self.axis_profile,
            "fixture": self.fixture,
            "chunk_id": chunk_id,
            "joint_names": list(self.profile["joint_names"]),
            "enabled_joint_names": [self.profile["joint_names"][index] for index in self.enabled],
            "effective_points": effective_rows,
            "locked_hold_state": list(self.hold_state),
            "physical_publisher_count": 0,
        }
        self.last_chunk_id = chunk_id
        self.accepted_chunks += 1
        return SinkDecision("submit_chunk", True, command=command)


def valid_message(sink: VlaExecutorSink, *, chunk_id: int, now: float) -> dict[str, Any]:
    return {
        "runtime_id": sink.runtime_id,
        "checkpoint_id": sink.checkpoint_id,
        "task_id": 0,
        "axis_profile": sink.axis_profile,
        "fixture": sink.fixture,
        "client_id": sink.active_client,
        "chunk_id": chunk_id,
        "sent_monotonic": now - 0.02,
        "joint_names": list(sink.profile["joint_names"]),
        "state_joint_names": list(sink.profile["joint_names"]),
        "state_positions": list(sink.hold_state),
        "state_monotonic": now - 0.05,
        "image_monotonic": now - 0.05,
        "points": [
            {
                "positions": list(sink.hold_state),
                "time_from_start": index * float(sink.profile["point_dt_seconds"]),
            }
            for index in range(int(sink.profile["action_horizon"]))
        ],
    }
