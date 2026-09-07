#!/usr/bin/env python3
"""Offline contact timeline. Verifies sealed logs; never connects to a robot.

Events are excerpts, not a causal verdict. Repeated messages remain in raw logs.
Robot wall clock is explicitly interpreted as Asia/Shanghai; correlation with
PC captures still requires measuring historical clock skew.
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo

STAMP = re.compile(r'(2026-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2}(?:\.\d+)?)')
ANSI = re.compile(r'\x1b\[[0-9;]*m')
RULES = {
    'task_start': r"BTree task:.*is start",
    'joint_target': r'Now move .* in joint space',
    'force': r'Excessive force detected',
    'force_halt': r'BTree task is halted because ft wrench',
    'task_result': r'BTree tick.*(?:succeed|fail)',
    'estop': r'onEstopState',
    'startmotion': r'StartMotion\(',
    'limb': r'LimbMotion\(',
    'selfcheck': r'passed.*true',
    'mode': r'(?:enter|Enter|->|state:).*?(?:Fault|JoystickMode|Shutdown|SelfChecking|WaitEStopRelease)',
    'servo_fault': r'(?:4003|4004).*0x(?:1003|2006)',
    'ethercat': r'SAFEOP.*ERROR',
    'joint_limit': r'(?:over(?: of)? range|out of.*range|out of.*limit)',
    'collision': r'[Cc]ollision',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    evidence = args.evidence.resolve()
    # Validate all original artifacts, not just selected excerpts.
    verified = 0
    for line in (evidence / 'evidence.sha256').read_text().splitlines():
        expected, relative = line.split('  ', 1)
        source = (evidence / relative).resolve()
        if not source.is_relative_to(evidence) or digest(source) != expected:
            raise SystemExit(f'Integrity failure: {relative}')
        verified += 1
    events, counts = [], {}
    compiled = {k: re.compile(v) for k, v in RULES.items()}
    for host in ('motion', 'vision'):
        entries = json.loads((evidence / host / 'remote-manifest.json').read_text())
        for entry in entries:
            path = evidence / host / entry['path'].lstrip('/')
            if digest(path) != entry['sha256']:
                raise SystemExit(f'Remote manifest mismatch: {path}')
            per_file = {}
            for number, raw in enumerate(path.read_text(errors='replace').splitlines(), 1):
                text = ANSI.sub('', raw)
                categories = [k for k, rule in compiled.items() if rule.search(text)]
                match = STAMP.search(text)
                if not categories or not match:
                    continue
                instant = dt.datetime.fromisoformat('T'.join(match.groups()))
                instant = instant.replace(tzinfo=ZoneInfo('Asia/Shanghai'))
                for category in categories:
                    per_file[category] = per_file.get(category, 0) + 1
                    # Bound noisy diagnostic excerpts; counts include all hits.
                    if category in ('joint_limit', 'collision', 'ethercat') and per_file[category] > 3:
                        continue
                    events.append(dict(
                        utc=instant.astimezone(dt.timezone.utc).isoformat(),
                        madrid=instant.astimezone(ZoneInfo('Europe/Madrid')).isoformat(),
                        robot_time=instant.isoformat(), host=host, category=category,
                        source=str(path.relative_to(evidence)), line=number,
                        source_sha256=entry['sha256'], excerpt=text))
            counts[str(path.relative_to(evidence))] = per_file
    events.sort(key=lambda e: (e['utc'], e['source'], e['line'], e['category']))
    args.output.mkdir(parents=True, exist_ok=False)
    fields = ['utc', 'madrid', 'robot_time', 'host', 'category', 'source', 'line', 'source_sha256', 'excerpt']
    with (args.output / 'timeline.tsv').open('x') as out:
        writer = csv.DictWriter(out, fieldnames=fields, delimiter='\t')
        writer.writeheader()
        writer.writerows(events)
    (args.output / 'event_counts.json').write_text(json.dumps(counts, indent=2) + '\n')
    summary = dict(evidence=str(evidence), verified_artifacts=verified, events=len(events),
                   raw_timezone_assumption='Asia/Shanghai', pc_clock_skew_not_corrected=True,
                   remote_connections=0, robot_commands=0)
    (args.output / 'analysis.json').write_text(json.dumps(summary, indent=2) + '\n')
    (args.output / 'analyzer.py').write_bytes(Path(__file__).read_bytes())
    files = sorted(p for p in args.output.iterdir() if p.is_file())
    (args.output / 'analysis.sha256').write_text(''.join(f'{digest(p)}  {p.name}\n' for p in files))
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
