#!/usr/bin/env python3
"""Pure in-memory temporal contract for Cruzr S2 VLA chunks.

This module deliberately has no ROS, network, process-control or hardware
dependency.  It schedules opaque point indexes into Python dictionaries only.
It is a project-side fail-closed candidate, not a reproduction or approval of
the supplied physical executor.
"""

from __future__ import annotations

import json
import math
import pathlib
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


TERMINAL_STATES = {"CANCELED", "STOPPED", "TIMED_OUT", "FAULTED", "COMPLETED"}


@dataclass
class TemporalDecision:
    event: str
    accepted: bool
    state: str
    reasons: list[str] = field(default_factory=list)
    emitted: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "event": self.event,
            "accepted": self.accepted,
            "state": self.state,
            "reasons": list(self.reasons),
            "emitted": list(self.emitted),
        }


def load_contract(path: pathlib.Path | str) -> dict[str, Any]:
    contract_path = pathlib.Path(path)
    with contract_path.open("r", encoding="utf-8") as source:
        contract = json.load(source)
    required_positive = (
        "action_horizon",
        "point_dt_seconds",
        "point_time_tolerance_seconds",
        "max_dispatch_lateness_seconds",
        "max_interchunk_gap_seconds",
        "max_session_duration_seconds",
        "continuous_end_chunk_num",
    )
    for key in required_positive:
        value = float(contract[key])
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{key} must be finite and positive")
    threshold = float(contract["end_threshold"])
    if not math.isfinite(threshold) or not 0.0 <= threshold <= 1.0:
        raise ValueError("end_threshold must be within [0, 1]")
    if int(contract["action_horizon"]) != 10:
        raise ValueError("E3.3 contract requires exactly 10 points")
    if int(contract["continuous_end_chunk_num"]) != 5:
        raise ValueError("E3.3 candidate requires exactly five consecutive end chunks")
    if contract.get("physical_executor_authorized") is not False:
        raise ValueError("physical_executor_authorized must remain false")
    return contract


class ConsecutiveEndPolicy:
    """Project candidate; the supplied runtime does not implement this rule."""

    def __init__(self, *, threshold: float, required: int) -> None:
        self.threshold = float(threshold)
        self.required = int(required)
        self.consecutive = 0

    def observe(self, flag_pred: float) -> bool:
        value = float(flag_pred)
        if not math.isfinite(value):
            raise ValueError("flag_pred must be finite")
        if value > self.threshold:
            self.consecutive += 1
        else:
            self.consecutive = 0
        return self.consecutive >= self.required


class VendorObservedEndPolicy:
    """Static behavior observed in supplied Vision source: one threshold hit."""

    def __init__(self, *, threshold: float) -> None:
        self.threshold = float(threshold)

    def observe(self, flag_pred: float) -> bool:
        value = float(flag_pred)
        if not math.isfinite(value):
            raise ValueError("flag_pred must be finite")
        return value > self.threshold


class OfflineTemporalGate:
    """Deterministic fail-closed scheduler with no physical output path."""

    def __init__(self, contract: Mapping[str, Any], *, started_at: float) -> None:
        self.contract = dict(contract)
        self.started_at = self._finite(started_at, "started_at")
        self.last_clock = self.started_at
        self.state = "ACTIVE"
        self.reason: str | None = None
        self.last_chunk_id: int | None = None
        self.pending: list[dict[str, Any]] = []
        self.waiting_since: float | None = None
        self.finish_after_current_chunk = False
        self.emission_log: list[dict[str, Any]] = []
        self.end_policy = ConsecutiveEndPolicy(
            threshold=float(self.contract["end_threshold"]),
            required=int(self.contract["continuous_end_chunk_num"]),
        )

    @staticmethod
    def _finite(value: Any, label: str) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{label}:not_numeric") from exc
        if not math.isfinite(parsed):
            raise ValueError(f"{label}:non_finite")
        return parsed

    @property
    def physical_publisher_count(self) -> int:
        return 0

    def _terminal(self) -> bool:
        return self.state in TERMINAL_STATES

    def _set_clock(self, now: Any) -> tuple[float | None, list[str]]:
        try:
            timestamp = self._finite(now, "clock")
        except ValueError as exc:
            return None, [str(exc)]
        if timestamp < self.last_clock:
            return None, [f"clock:regressive:{timestamp}<{self.last_clock}"]
        self.last_clock = timestamp
        return timestamp, []

    def _latch(self, state: str, reason: str) -> None:
        self.pending.clear()
        self.finish_after_current_chunk = False
        self.state = state
        self.reason = reason

    def _deadline_reason(self, now: float, *, check_gap: bool = True) -> str | None:
        session_deadline = self.started_at + float(
            self.contract["max_session_duration_seconds"]
        )
        if now >= session_deadline:
            return "session:duration_timeout"
        if check_gap and self.waiting_since is not None:
            gap_deadline = self.waiting_since + float(
                self.contract["max_interchunk_gap_seconds"]
            )
            if now > gap_deadline:
                return "chunk:interchunk_timeout"
        return None

    def submit(
        self,
        *,
        chunk_id: int,
        point_times: Sequence[Any],
        flag_pred: Any,
        now: Any,
    ) -> TemporalDecision:
        timestamp, reasons = self._set_clock(now)
        if reasons:
            return TemporalDecision("submit", False, self.state, reasons)
        assert timestamp is not None
        if self._terminal():
            return TemporalDecision("submit", False, self.state, [f"session:{self.state.lower()}"])
        deadline_reason = self._deadline_reason(timestamp)
        if deadline_reason:
            self._latch("TIMED_OUT", deadline_reason)
            return TemporalDecision("submit", False, self.state, [deadline_reason])
        if self.pending:
            self._latch("FAULTED", "chunk:overlap_pending_points")
            return TemporalDecision(
                "submit", False, self.state, ["chunk:overlap_pending_points"]
            )
        if type(chunk_id) is not int or chunk_id < 0:
            return TemporalDecision("submit", False, self.state, ["chunk_id:invalid"])
        if self.last_chunk_id is not None and chunk_id <= self.last_chunk_id:
            return TemporalDecision(
                "submit",
                False,
                self.state,
                [f"chunk_id:not_increasing:{chunk_id}<={self.last_chunk_id}"],
            )
        if not isinstance(point_times, Sequence) or isinstance(point_times, (str, bytes)):
            return TemporalDecision("submit", False, self.state, ["point_times:not_sequence"])
        horizon = int(self.contract["action_horizon"])
        if len(point_times) != horizon:
            return TemporalDecision(
                "submit", False, self.state, [f"point_times:horizon:{len(point_times)}!={horizon}"]
            )
        parsed_times: list[float] = []
        previous_time: float | None = None
        dt = float(self.contract["point_dt_seconds"])
        tolerance = float(self.contract["point_time_tolerance_seconds"])
        for index, value in enumerate(point_times):
            try:
                parsed = self._finite(value, f"point:{index}:time")
            except ValueError as exc:
                reasons.append(str(exc))
                continue
            if previous_time is not None and parsed <= previous_time:
                reasons.append(f"point:{index}:time:not_monotonic")
            if abs(parsed - index * dt) > tolerance:
                reasons.append(f"point:{index}:time:off_schedule")
            parsed_times.append(parsed)
            previous_time = parsed
        try:
            flag = self._finite(flag_pred, "flag_pred")
        except ValueError as exc:
            reasons.append(str(exc))
            flag = 0.0
        if not 0.0 <= flag <= 1.0:
            reasons.append("flag_pred:outside_0_1")
        if reasons:
            return TemporalDecision("submit", False, self.state, sorted(set(reasons)))
        self.pending = [
            {
                "chunk_id": chunk_id,
                "point_index": index,
                "due_at": timestamp + point_time,
            }
            for index, point_time in enumerate(parsed_times)
        ]
        self.last_chunk_id = chunk_id
        self.waiting_since = None
        self.finish_after_current_chunk = self.end_policy.observe(flag)
        return TemporalDecision("submit", True, self.state)

    def advance(self, now: Any) -> TemporalDecision:
        timestamp, reasons = self._set_clock(now)
        if reasons:
            return TemporalDecision("advance", False, self.state, reasons)
        assert timestamp is not None
        if self._terminal():
            return TemporalDecision("advance", False, self.state, [f"session:{self.state.lower()}"])
        deadline_reason = self._deadline_reason(timestamp)
        if deadline_reason:
            self._latch("TIMED_OUT", deadline_reason)
            return TemporalDecision("advance", False, self.state, [deadline_reason])
        emitted: list[dict[str, Any]] = []
        lateness_limit = float(self.contract["max_dispatch_lateness_seconds"])
        while self.pending and self.pending[0]["due_at"] <= timestamp + 1e-12:
            point = self.pending[0]
            lateness = timestamp - float(point["due_at"])
            if lateness > lateness_limit:
                reason = (
                    f"dispatch:late:chunk:{point['chunk_id']}:point:{point['point_index']}:"
                    f"{lateness:.6f}>{lateness_limit:.6f}"
                )
                self._latch("FAULTED", reason)
                return TemporalDecision("advance", False, self.state, [reason])
            self.pending.pop(0)
            event = {
                "chunk_id": point["chunk_id"],
                "point_index": point["point_index"],
                "scheduled_at": point["due_at"],
                "observed_at": timestamp,
                "physical_publisher_count": 0,
            }
            emitted.append(event)
            self.emission_log.append(event)
        if not self.pending and emitted:
            self.waiting_since = float(emitted[-1]["scheduled_at"])
            if self.finish_after_current_chunk:
                self.state = "COMPLETED"
                self.reason = "end:five_consecutive_chunks"
                self.finish_after_current_chunk = False
        return TemporalDecision("advance", True, self.state, emitted=emitted)

    def cancel(self, now: Any) -> TemporalDecision:
        timestamp, reasons = self._set_clock(now)
        if reasons:
            return TemporalDecision("cancel", False, self.state, reasons)
        if self.state == "CANCELED":
            return TemporalDecision("cancel", True, self.state)
        if self._terminal():
            return TemporalDecision("cancel", True, self.state)
        self._latch("CANCELED", "control:cancel")
        return TemporalDecision("cancel", True, self.state)

    def stop(self, now: Any) -> TemporalDecision:
        timestamp, reasons = self._set_clock(now)
        if reasons:
            return TemporalDecision("stop", False, self.state, reasons)
        if self.state == "STOPPED":
            return TemporalDecision("stop", True, self.state)
        if self._terminal():
            return TemporalDecision("stop", True, self.state)
        self._latch("STOPPED", "control:stop")
        return TemporalDecision("stop", True, self.state)

    def sensor_fault(self, sensor: str, now: Any) -> TemporalDecision:
        timestamp, reasons = self._set_clock(now)
        if reasons:
            return TemporalDecision("sensor_fault", False, self.state, reasons)
        if sensor not in {"state", "image"}:
            return TemporalDecision("sensor_fault", False, self.state, ["sensor:invalid"])
        if self._terminal():
            return TemporalDecision(
                "sensor_fault", True, self.state, [f"session:{self.state.lower()}"]
            )
        reason = f"sensor:{sensor}:lost"
        self._latch("FAULTED", reason)
        return TemporalDecision("sensor_fault", True, self.state, [reason])


def nominal_point_times(contract: Mapping[str, Any]) -> list[float]:
    return [
        index * float(contract["point_dt_seconds"])
        for index in range(int(contract["action_horizon"]))
    ]
