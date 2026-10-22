"""Summarize passive telemetry without certifying posture or protection."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

if __package__:
    from .collect_empty_arm_trace_readonly import validate
else:
    from collect_empty_arm_trace_readonly import validate


def analyze(path):
    counts = Counter()
    topics = Counter()
    invalid = []
    nonjson = []
    axes = {}
    joints = {}
    stops = {}
    first_nonzero_stop = None
    source_previous = {}
    source_checks = Counter()
    receipt_start = receipt_end = None
    protocol_end = None
    publishers = []
    for line_number, line in enumerate(Path(path).open(), 1):
        counts['lines'] += 1
        try:
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError('Non-object JSON')
        except (ValueError, TypeError):
            counts['non_json_lines'] += 1
            if len(nonjson) < 10:
                nonjson.append(dict(line=line_number, text=line.rstrip()[:250]))
            continue
        counts[row.get('kind', 'unknown')] += 1
        if row.get('kind') == 'end':
            protocol_end = row
        if row.get('kind') == 'publishers':
            publishers.append(dict(received_ns=row.get('received_ns'), counts=row.get('counts')))
        if row.get('kind') == 'validation_error':
            invalid.append(dict(line=line_number, topic=row.get('topic'), reason=row.get('reason')))
        if row.get('kind') != 'message':
            continue
        topic = row.get('topic')
        topics[topic] += 1
        received = row.get('received_ns')
        if type(received) is not int or received <= 0:
            invalid.append(dict(line=line_number, topic=topic, reason='Invalid receipt timestamp'))
            continue
        receipt_start = received if receipt_start is None else min(receipt_start, received)
        receipt_end = received if receipt_end is None else max(receipt_end, received)
        try:
            derived = validate(topic, row['message'])
        except (ValueError, TypeError, KeyError, OverflowError) as exc:
            invalid.append(dict(line=line_number, topic=topic, reason=type(exc).__name__+': '+str(exc)))
            continue
        source = derived['source_stamp_ns']
        if source is not None:
            previous = source_previous.get(topic)
            if previous is not None:
                source_checks['repeated' if source == previous else 'regressing' if source < previous else 'advancing'] += 1
            source_previous[topic] = source
            source_checks['future' if source > received else 'older_than_500ms' if received-source > 500_000_000 else 'within_500ms'] += 1
        if topic.startswith('/emb/'):
            value = derived['stop_value']
            history = stops.setdefault(topic, [])
            if not history or history[-1]['value'] != value:
                history.append(dict(value=value, received_ns=received, line=line_number, source_stamp_ns=None))
            if value and first_nonzero_stop is None:
                first_nonzero_stop = dict(topic=topic, value=value, received_ns=received, line=line_number)
        elif topic == '/mc/actuator_state':
            for item in derived['body']:
                axis = axes.setdefault(str(item['id']), dict(name=item['name'], samples=0,
                    position_min=item['position'], position_max=item['position'],
                    max_abs_command_error_rad=0., max_abs_velocity=0., max_abs_current=0.,
                    fault_or_disabled_samples=0, peak_command_error=None))
                axis['samples'] += 1
                axis['position_min'] = min(axis['position_min'], item['position'])
                axis['position_max'] = max(axis['position_max'], item['position'])
                axis['max_abs_velocity'] = max(axis['max_abs_velocity'], abs(item['velocity']))
                axis['max_abs_current'] = max(axis['max_abs_current'], abs(item['current']))
                if item['error_code'] or item['status'] & 8 or item['status'] & 7 != 7:
                    axis['fault_or_disabled_samples'] += 1
                if abs(item['command_error_rad']) >= axis['max_abs_command_error_rad']:
                    axis['max_abs_command_error_rad'] = abs(item['command_error_rad'])
                    axis['peak_command_error'] = dict(item, received_ns=received, source_stamp_ns=source,
                                                      line=line_number)
                axis['last'] = dict(item, received_ns=received, source_stamp_ns=source, line=line_number)
        elif topic == '/mc/whole_joint_states':
            message = row['message']
            for name, position in zip(message['name'], message['position']):
                joint = joints.setdefault(name, dict(samples=0, position_min=position, position_max=position))
                joint['samples'] += 1
                joint['position_min'] = min(joint['position_min'], position)
                joint['position_max'] = max(joint['position_max'], position)
                joint['last_position'] = position
    return dict(schema='passive-empty-arm-trace-summary-v1', created_utc=datetime.now(timezone.utc).isoformat(),
        source_path=str(Path(path).resolve()), source_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),
        counts=dict(counts), topic_messages=dict(topics), receipt_start_ns=receipt_start, receipt_end_ns=receipt_end,
        receipt_span_s=None if receipt_start is None else (receipt_end-receipt_start)/1e9,
        protocol_end=protocol_end, validation_errors=invalid, non_json_examples=nonjson,
        source_timestamp_checks=dict(source_checks), publisher_observations=publishers,
        stop_changes=stops, first_nonzero_stop=first_nonzero_stop, body_axes=axes, joints=joints,
        passive_evidence_only=True, active_protection_claimed=False,
        limitations=['Peaks cover retained samples only (maximum 32 Hz), not every servo update.',
            'UInt8 stops have receipt timestamps only; no source time is invented.',
            'Telemetry cannot establish physical contact, mechanical health, clearance or safe movement.',
            'No complete or usable safety classification is emitted.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    text = json.dumps(analyze(args.trace), indent=2, allow_nan=False)+'\n'
    if args.output:
        with args.output.open('x') as stream:
            stream.write(text)
        print(args.output)
    else:
        print(text, end='')


if __name__ == '__main__':
    main()
