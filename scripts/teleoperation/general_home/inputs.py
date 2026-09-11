"""Strict archived state/scene input; never infers physical permission."""
from datetime import datetime, timezone
import json
from pathlib import Path

from .geometry import finite_vector
from cruzr_pico_to_home_owner_gate import JOINT_ORDER


def load_json(path):
    def reject_constant(value):
        raise ValueError('Nonfinite JSON constant: '+value)

    def unique_object(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON key: '+key)
            result[key] = value
        return result

    return json.loads(Path(path).read_text(), parse_constant=reject_constant, object_pairs_hook=unique_object)


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError('captured_at must include date/time and timezone')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('captured_at needs timezone')
    age = (datetime.now(timezone.utc)-parsed).total_seconds()
    if age < -1.:
        raise ValueError('Capture is in the future')
    return age


def load_state(path):
    data = load_json(path)
    if not isinstance(data, dict) or data.get('schema') != 'cruzr-general-home-state-v1':
        raise ValueError('Expected cruzr-general-home-state-v1')
    age = timestamp(data.get('captured_at'))
    if data.get('empty_clamps') is not True:
        raise ValueError('Empty clamps not established: use cargo/contact recovery')
    if data.get('actuators_healthy') is not True or data.get('controller_idle') is not True:
        raise ValueError('Healthy actuators and idle controller required')
    raw = data.get('joint_state', {})
    names = raw.get('name')
    if not isinstance(names, list) or len(names) != 20 or any(not isinstance(n, str) for n in names):
        raise ValueError('Expected 20 named joints')
    if len(set(names)) != 20 or set(names) != set(JOINT_ORDER):
        raise ValueError('Duplicate/missing/unknown controlled joint')
    position = finite_vector(raw.get('position'), 20, 'position')
    velocity = finite_vector(raw.get('velocity'), 20, 'velocity')
    if abs(velocity).max() > .002:
        raise ValueError('State is moving; no stationary HOME plan')
    order = [names.index(n) for n in JOINT_ORDER]
    return position[order], dict(captured_at=data['captured_at'], age_seconds=age,
        source=data.get('source', 'unspecified'), assertions_from_input_only=True,
        live_authorization=False), data.get('auxiliary_joint_positions', {})
