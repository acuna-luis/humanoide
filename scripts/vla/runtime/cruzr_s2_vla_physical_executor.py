#!/usr/bin/env python3
"""Transport-neutral E6.0 one-point canary control core.

Despite the compatibility filename used by the E6.0 readiness auditor, this
module deliberately contains no robot transport.  It can turn one previously
guarded preview into one in-memory dispatch *intent* and then latches.  It
cannot publish, call an action, open a socket or authorize physical movement.
"""

from __future__ import annotations

import json
import math
import pathlib
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


EXPECTED_SCHEMA = "cruzr-s2-vla-one-point-canary-contract-e6.0l-v1"
TERMINAL_STATES = {"CANCELED", "STOPPED", "FAULTED", "TIMED_OUT", "COMPLETED"}


def _finite(value: Any, label: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label}:not_numeric") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"{label}:non_finite")
    return parsed


def load_contract(path: pathlib.Path | str) -> dict[str, Any]:
    with pathlib.Path(path).open("r", encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise ValueError("contract:not_object")
    if value.get("schema") != EXPECTED_SCHEMA:
        raise ValueError("contract:schema")
    exact = {
        "task_id": 0,
        "axis_profile": "P14_A",
        "scenario": "NO_BOX_READY",
        "source_chunk_point_count": 10,
        "accepted_source_point_indices": [0],
        "maximum_accepted_chunk_count": 1,
        "maximum_dispatch_intent_count": 1,
        "completion_policy": "single_point_zero_is_consumed_once_then_session_latches_complete",
        "gap_policy": "emit_nothing_and_never_replay",
        "end_flag_policy": "ignored_for_e6_0_one_point_canary",
        "physical_execution_enabled": False,
        "physical_transport_implemented": False,
        "physical_stop_transport_implemented": False,
    }
    for key, expected in exact.items():
        if value.get(key) != expected:
            raise ValueError(f"contract:{key}")
    for key in (
        "maximum_preview_age_seconds",
        "maximum_state_age_seconds",
        "maximum_image_age_seconds",
        "maximum_armed_duration_seconds",
        "ready_arm_tolerance_rad",
        "stationary_velocity_tolerance_rad_s",
    ):
        if _finite(value.get(key), f"contract:{key}") <= 0:
            raise ValueError(f"contract:{key}:not_positive")
    claims = value.get("required_preflight_claims")
    if not isinstance(claims, list) or len(claims) != len(set(claims)) or not claims:
        raise ValueError("contract:required_preflight_claims")
    return value


@dataclass
class CoreDecision:
    event: str
    accepted: bool
    state: str
    reasons: list[str] = field(default_factory=list)
    preview_intents: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "event": self.event,
            "accepted": self.accepted,
            "state": self.state,
            "reasons": list(self.reasons),
            "preview_intents": list(self.preview_intents),
            "physical_execution_authorized": False,
            "physical_publisher_count": 0,
        }


class OnePointCanaryControlCore:
    """Fail-closed state machine for one transport-neutral preview intent."""

    def __init__(self, contract: Mapping[str, Any], *, started_at: Any) -> None:
        self.contract = dict(contract)
        self.started_at = _finite(started_at, "started_at")
        self.last_clock = self.started_at
        self.state = "CREATED"
        self.pending_preview: dict[str, Any] | None = None
        self.accepted_chunks = 0
        self.preview_intent_count = 0

    @property
    def physical_publisher_count(self) -> int:
        return 0

    @property
    def physical_execution_authorized(self) -> bool:
        return False

    def _clock(self, now: Any) -> tuple[float | None, list[str]]:
        try:
            timestamp = _finite(now, "clock")
        except ValueError as exc:
            return None, [str(exc)]
        if timestamp < self.last_clock:
            return None, ["clock:regressive"]
        self.last_clock = timestamp
        return timestamp, []

    def _terminal(self) -> bool:
        return self.state in TERMINAL_STATES

    def _latch(self, state: str) -> None:
        self.pending_preview = None
        self.state = state

    def arm(self, claims: Mapping[str, Any], *, now: Any) -> CoreDecision:
        timestamp, reasons = self._clock(now)
        if reasons:
            return CoreDecision("arm", False, self.state, reasons)
        if self.state != "CREATED":
            return CoreDecision("arm", False, self.state, ["session:not_created"])
        if not isinstance(claims, Mapping):
            return CoreDecision("arm", False, self.state, ["preflight:not_mapping"])
        for claim in self.contract["required_preflight_claims"]:
            if claims.get(claim) is not True:
                reasons.append(f"preflight:{claim}:not_true")
        identity = {
            "task_id": self.contract["task_id"],
            "axis_profile": self.contract["axis_profile"],
            "scenario": self.contract["scenario"],
        }
        for key, expected in identity.items():
            if claims.get(key) != expected:
                reasons.append(f"preflight:{key}:mismatch")
        if claims.get("physical_execution_requested") is not False:
            reasons.append("preflight:physical_execution_requested")
        reasons = sorted(set(reasons))
        if reasons:
            self._latch("FAULTED")
            return CoreDecision("arm", False, self.state, reasons)
        assert timestamp is not None
        self.state = "ARMED_PREVIEW_ONLY"
        return CoreDecision("arm", True, self.state)

    def accept_guarded_preview(
        self, decision: Mapping[str, Any], *, now: Any
    ) -> CoreDecision:
        timestamp, reasons = self._clock(now)
        if reasons:
            return CoreDecision("accept_guarded_preview", False, self.state, reasons)
        if self.state != "ARMED_PREVIEW_ONLY":
            return CoreDecision(
                "accept_guarded_preview", False, self.state,
                ["session:not_armed_preview_only"],
            )
        assert timestamp is not None
        if timestamp - self.started_at > float(
            self.contract["maximum_armed_duration_seconds"]
        ):
            self._latch("TIMED_OUT")
            return CoreDecision(
                "accept_guarded_preview", False, self.state,
                ["session:armed_timeout"],
            )
        if decision.get("preview_accepted") is not True:
            reasons.append("guard:preview_not_accepted")
        if decision.get("physical_execution_authorized") is not False:
            reasons.append("guard:unexpected_physical_authorization")
        preview = decision.get("preview")
        if not isinstance(preview, Mapping):
            reasons.append("guard:preview_missing")
        else:
            expected = {
                "task_id": self.contract["task_id"],
                "axis_profile": self.contract["axis_profile"],
                "scenario": self.contract["scenario"],
                "physical_execution_authorized": False,
                "physical_publisher_count": 0,
            }
            for key, value in expected.items():
                if preview.get(key) != value:
                    reasons.append(f"preview:{key}:mismatch")
            points = preview.get("preview_point")
            if not isinstance(points, Sequence) or isinstance(points, (str, bytes)):
                reasons.append("preview:point:not_sequence")
            elif len(points) != 20:
                reasons.append("preview:point:dimension")
            else:
                for index, value in enumerate(points):
                    try:
                        _finite(value, f"preview:point:{index}")
                    except ValueError as exc:
                        reasons.append(str(exc))
        if self.accepted_chunks >= int(self.contract["maximum_accepted_chunk_count"]):
            reasons.append("session:chunk_already_consumed")
        reasons = sorted(set(reasons))
        if reasons:
            self._latch("FAULTED")
            return CoreDecision("accept_guarded_preview", False, self.state, reasons)
        assert isinstance(preview, Mapping)
        self.pending_preview = dict(preview)
        self.accepted_chunks += 1
        self.state = "ONE_PREVIEW_PENDING"
        return CoreDecision("accept_guarded_preview", True, self.state)

    def consume_preview_once(self, *, now: Any) -> CoreDecision:
        _, reasons = self._clock(now)
        if reasons:
            return CoreDecision("consume_preview_once", False, self.state, reasons)
        if self.state != "ONE_PREVIEW_PENDING" or self.pending_preview is None:
            return CoreDecision(
                "consume_preview_once", False, self.state,
                ["session:no_pending_preview"],
            )
        if self.preview_intent_count >= int(
            self.contract["maximum_dispatch_intent_count"]
        ):
            self._latch("FAULTED")
            return CoreDecision(
                "consume_preview_once", False, self.state,
                ["session:preview_intent_limit"],
            )
        preview = self.pending_preview
        intent = {
            "schema": "cruzr-s2-vla-transport-neutral-preview-intent-e6.0l-v1",
            "task_id": preview["task_id"],
            "axis_profile": preview["axis_profile"],
            "scenario": preview["scenario"],
            "sequence_id": preview["sequence_id"],
            "source_point_index": 0,
            "joint_names": list(preview["joint_names"]),
            "positions": list(preview["preview_point"]),
            "physical_execution_authorized": False,
            "physical_transport": None,
            "physical_publisher_count": 0,
        }
        self.preview_intent_count += 1
        self._latch("COMPLETED")
        return CoreDecision(
            "consume_preview_once", True, self.state,
            preview_intents=[intent],
        )

    def cancel(self, *, now: Any) -> CoreDecision:
        _, reasons = self._clock(now)
        if reasons:
            return CoreDecision("cancel", False, self.state, reasons)
        if self.state == "CANCELED":
            return CoreDecision("cancel", True, self.state)
        if self._terminal():
            return CoreDecision("cancel", False, self.state, ["session:terminal"])
        self._latch("CANCELED")
        return CoreDecision("cancel", True, self.state)

    def stop(self, *, now: Any) -> CoreDecision:
        _, reasons = self._clock(now)
        if reasons:
            return CoreDecision("stop", False, self.state, reasons)
        if self.state == "STOPPED":
            return CoreDecision("stop", True, self.state)
        if self._terminal():
            return CoreDecision("stop", False, self.state, ["session:terminal"])
        self._latch("STOPPED")
        return CoreDecision("stop", True, self.state)

    def fault(self, reason: str, *, now: Any) -> CoreDecision:
        _, reasons = self._clock(now)
        if reasons:
            return CoreDecision("fault", False, self.state, reasons)
        if self._terminal():
            return CoreDecision("fault", False, self.state, ["session:terminal"])
        self._latch("FAULTED")
        return CoreDecision("fault", True, self.state, [f"fault:{reason}"])
