#!/usr/bin/env python3
"""Offline evidence timing only; standard library, no subprocess/network/control.

Run after the observer/cycle has stopped. Absolute PC and Motion timestamps are
never subtracted. SDK action durations always use the worker's inner timestamps.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path


PHASE_DIR = {
    'pickup_to_put1': 'pickup', 'approach': 'approach',
    'precontact': 'precontact', 'support': 'support',
    'pin_relief': 'pin-relief', 'lateral_open': 'open', 'home': 'home',
}
TERMINAL = {'succeeded', 'interrupted', 'failed', 'paused', 'checked', 'installation_pending'}


class Reader:
    def __init__(self):
        self.hashes = {}
        self.warnings = []

    def read(self, path, lines=False):
        path = Path(path)
        if not path.is_file():
            return [] if lines else None
        raw = path.read_bytes()
        if len(raw) > 128 * 1024 * 1024:
            raise ValueError('Evidence file exceeds 128 MiB: ' + str(path))
        self.hashes[str(path.resolve())] = hashlib.sha256(raw).hexdigest()
        if not lines:
            return json.loads(raw)
        output = []
        for number, line in enumerate(raw.decode().splitlines(), 1):
            if not line.strip():
                continue
            try:
                output.append(json.loads(line))
            except json.JSONDecodeError as exc:
                self.warnings.append(f'{path}:{number}: malformed JSONL retained as missing evidence: {exc}')
        return output


def seconds(first, last):
    if type(first) is not int or type(last) is not int or last < first:
        return None
    return (last-first)/1e9


def event_ns(row):
    value = row.get('time_ns')
    return value if type(value) is int else None


def extract_actions(events):
    """Pair one accepted/result per goal using inner worker timestamps only."""
    goals = {}
    for row in events:
        detail = row.get('detail', {})
        if row.get('event') != 'action' or not isinstance(detail, dict):
            continue
        goal = detail.get('goal_id')
        if not goal:
            continue
        record = goals.setdefault(goal, dict(goal_id=goal, kind=row.get('kind'), events={}))
        typ = detail.get('event')
        if typ in ('dispatched', 'accepted', 'result', 'cancel_request', 'cancel_response'):
            record['events'].setdefault(typ, []).append(detail)
    output = []
    for goal, record in goals.items():
        pairs = record.pop('events')
        a, r, d = (pairs.get(key, []) for key in ('accepted', 'result', 'dispatched'))
        record.update(accepted_event_count=len(a), result_event_count=len(r),
            dispatched_event_count=len(d), timestamp_clock='Motion worker detail.time_ns',
            accepted_ns=a[0].get('time_ns') if len(a) == 1 else None,
            result_ns=r[0].get('time_ns') if len(r) == 1 else None,
            status=r[0].get('status') if len(r) == 1 else None,
            accepted_to_result_s=None,
            cancel_observed=bool(pairs.get('cancel_request') or pairs.get('cancel_response')))
        if len(a) == 1 and len(r) == 1 and a[0].get('accepted') is True:
            record['accepted_to_result_s'] = seconds(record['accepted_ns'], record['result_ns'])
        record['identified_terminal_success'] = (
            record['accepted_to_result_s'] is not None and record['status'] == 4)
        output.append(record)
    return sorted(output, key=lambda row: row.get('accepted_ns') or 0)


def summarize_events(reader, path):
    rows = reader.read(path, lines=True)
    if not rows:
        return None
    stamp_rows = [row for row in rows if event_ns(row) is not None]
    actions = extract_actions(rows)
    stage_rows = []
    for index, row in enumerate(rows):
        if row.get('event') != 'stage_complete':
            continue
        elapsed = row.get('elapsed_s')
        end = event_ns(row)
        start = end-round(elapsed*1e9) if end is not None and type(elapsed) in (int, float) else None
        included = [action for action in actions if type(action.get('accepted_ns')) is int
            and start is not None and start-10_000_000 <= action['accepted_ns'] <= end]
        stage_rows.append(dict(stage=row.get('stage'), completed=True,
            elapsed_s=elapsed, elapsed_measurement='stage_complete.elapsed_s; monotonic rounded to milliseconds',
            estimated_window_start_motion_ns=start, window_end_motion_ns=end,
            logical_assumption=row.get('logical_assumption'),
            native_actions=included,
            action_window_attribution='accepted within reconstructed stage window; boundary rounded to milliseconds'))
    ready = next((row for row in rows if row.get('event') == 'ready'), None)
    timings = [dict(operation=row.get('operation'), stage=row.get('stage'), elapsed_s=row.get('elapsed_s'))
        for row in rows if row.get('event') == 'timing']
    dependency = next((row for row in rows if row.get('event') == 'timing' and row.get('operation') == 'dependencies'), None)
    health = next((row for row in rows if row.get('event') == 'timing' and row.get('operation') == 'health'), None)
    sps_gap = None
    if dependency is not None and health is not None:
        health_start = health['time_ns']-round(health['elapsed_s']*1e9)
        sps_gap = seconds(dependency['time_ns'], health_start)
    result = dict(file=str(path.resolve()), event_count=len(rows), clock='Motion runtime',
        first_event_ns=event_ns(stamp_rows[0]) if stamp_rows else None,
        last_event_ns=event_ns(stamp_rows[-1]) if stamp_rows else None,
        event_span_s=seconds(event_ns(stamp_rows[0]), event_ns(stamp_rows[-1])) if stamp_rows else None,
        first_event_to_ready_s=seconds(event_ns(stamp_rows[0]), event_ns(ready)) if stamp_rows and ready else None,
        actions=actions, completed_stages=stage_rows, timing_events=timings,
        sps_discovery_gap_estimated_s=sps_gap,
        sps_gap_attribution='untimed gap between dependencies completion and health start, sequential Runtime.run',
        session_finishing_observed=any(row.get('event') == 'session_finishing' for row in rows),
        errors=[dict(time_ns=row.get('time_ns'), reason=row.get('reason')) for row in rows if row.get('event') == 'error'])
    alignment=[{key:value for key,value in row.items()
        if type(value) in (str,int,float,bool) or value is None}
        for row in rows if row.get('event')=='box_alignment']
    if alignment:
        in_flight=[row for row in alignment if row.get('phase')=='in_flight']
        result['box_alignment']=dict(events=alignment,
            configured_maximum_observed=next((row.get('max_corrections') for row in in_flight
                if type(row.get('max_corrections')) is int),None),
            actual_correction_dispatches=len(in_flight),
            ready=any(row.get('phase')=='ready' for row in alignment),
            note='Configured maximum and observed correction count are distinct; no unused attempt is charged.')
    return result


def observer_windows(reader, observer, cycle):
    rows = reader.read(observer, lines=True) if observer else []
    snapshots = {}
    for row in rows:
        snap = row.get('cycle')
        if not isinstance(snap, dict):
            continue
        stamp = snap.get('updated_ns')
        if type(stamp) is int and cycle['created_ns'] <= stamp <= cycle['updated_ns']:
            snapshots.setdefault(stamp, dict(snapshot=snap, observed_pc_ns=row.get('time_ns')))
    ordered = [(stamp, row) for stamp, row in sorted(snapshots.items())]
    starts = []
    previous = None
    for stamp, row in ordered:
        flight = row['snapshot'].get('in_flight')
        if flight and flight != previous:
            starts.append(dict(phase=flight, start_ns=stamp,
                observed_pc_ns=row['observed_pc_ns'], matching_completed_ns=None))
        if previous and not flight and starts:
            last = starts[-1]
            if last['phase'] == previous and last['matching_completed_ns'] is None:
                last['matching_completed_ns'] = stamp
        previous = flight
    if not starts:
        return [], dict(used=False, reason='No observed in_flight journal transitions')
    windows = []
    if starts[0]['start_ns'] > cycle['created_ns']:
        windows.append(dict(phase='initial_coordination', start_pc_ns=cycle['created_ns'],
            end_pc_ns=starts[0]['start_ns'], duration_s=seconds(cycle['created_ns'], starts[0]['start_ns']),
            measurement='PC cycle.created_ns to first observed journal in_flight updated_ns'))
    for index, item in enumerate(starts):
        end = starts[index+1]['start_ns'] if index+1 < len(starts) else cycle['updated_ns']
        windows.append(dict(phase=item['phase'], start_pc_ns=item['start_ns'], end_pc_ns=end,
            duration_s=seconds(item['start_ns'], end),
            measurement='PC journal in_flight start updated_ns to next phase start updated_ns, or last cycle.updated_ns',
            includes_interphase_coordination=True,
            matching_completed_pc_ns=item['matching_completed_ns'],
            start_to_matching_completion_s=seconds(item['start_ns'], item['matching_completed_ns']),
            observation_delay_s=seconds(item['start_ns'], item['observed_pc_ns']),
            completion_captured=item['matching_completed_ns'] is not None))
    return windows, dict(used=True, unique_snapshots=len(ordered), raw_records=len(rows),
        clock='PC cycle.updated_ns; observer time_ns used only for polling delay',
        note='Windows conserve total exactly; if a transient completed state was missed, its small coordination gap remains assigned to preceding phase.')


def recipe_windows(reader, evidence, cycle):
    marks = []
    initial_label=('initial_coordination' if set(cycle.get('skipped_stages',[])) >= {'pickup_to_put1','approach'}
        else 'initial_pickup_and_approach')
    for token, label in [('HUECO19', initial_label), ('HUECO5', 'precontact'),
                         ('APOYADA', 'support'), ('PINES_LIBRES', 'pin_relief'), ('LIBRE', 'lateral_open')]:
        row = reader.read(evidence/f'recipe-{token}.json')
        if row and type(row.get('recorded_ns')) is int:
            marks.append((row['recorded_ns'], label, token))
    output = []
    start = cycle['created_ns']
    for end, phase, token in marks:
        if not start <= end <= cycle['updated_ns']:
            reader.warnings.append('Out-of-order recipe marker ignored: ' + token)
            continue
        output.append(dict(phase=phase, start_pc_ns=start, end_pc_ns=end,
            duration_s=seconds(start, end), measurement='adjacent PC recipe receipt timestamps',
            completion_marker=token))
        start = end
    if start < cycle['updated_ns']:
        output.append(dict(phase='home' if marks and marks[-1][2] == 'LIBRE' else 'remaining_or_interrupted',
            start_pc_ns=start, end_pc_ns=cycle['updated_ns'], duration_s=seconds(start, cycle['updated_ns']),
            measurement='last available PC marker to cycle.updated_ns',
            completed=cycle.get('status') == 'succeeded'))
    return output


def home_details(reader, evidence):
    root = evidence/'home'
    home = reader.read(root/'home.json')
    if home is None:
        return None
    output = dict(phase=home.get('phase'), measured_home=home.get('measured_home'),
        goal_id=(home.get('result') or {}).get('goal_id'),
        intent_to_finished_pc_s=seconds(home.get('intent_ns'), home.get('finished_ns')),
        native_accepted_to_result_s=None,
        native_timing_limitation='HOME native-result.json contains no accepted/result timestamps; duration not invented.',
        query_rounds={})
    for prefix in ('immediate', 'postflight'):
        queries = []
        for path in sorted(root.glob(prefix+'-*.json')):
            obj = reader.read(path)
            row = obj.get('result') if isinstance(obj, dict) else None
            if isinstance(row, dict) and seconds(row.get('start_ns'), row.get('finished_ns')) is not None:
                queries.append(dict(file=path.name, start_motion_ns=row['start_ns'],
                    finished_motion_ns=row['finished_ns'], duration_s=seconds(row['start_ns'], row['finished_ns'])))
        if queries:
            first=min(row['start_motion_ns'] for row in queries)
            last=max(row['finished_motion_ns'] for row in queries)
            output['query_rounds'][prefix] = dict(start_motion_ns=first, finished_motion_ns=last,
                wall_s=seconds(first, last), queries=queries,
                note='Health batch runs in parallel; individual durations must not be summed as wall time.')
    verified = reader.read(root/'postflight-verified.json')
    if verified:
        output['postflight_classifications'] = verified.get('classifications')
    return output


def analyze(evidence, observer):
    reader=Reader()
    cycle=reader.read(evidence/'cycle.json')
    if not isinstance(cycle, dict) or seconds(cycle.get('created_ns'), cycle.get('updated_ns')) is None:
        raise ValueError('Valid cycle.json with PC created_ns/updated_ns is required')
    windows, observation=observer_windows(reader, observer, cycle)
    if not windows:
        windows=recipe_windows(reader, evidence, cycle)
    total=seconds(cycle['created_ns'], cycle['updated_ns'])
    for row in windows:
        row['percent_recorded_cycle']=100*row['duration_s']/total if total else None
    details={}
    for phase, directory in PHASE_DIR.items():
        events=evidence/directory/('events.jsonl' if directory == 'pickup' else 'physical-run/events.jsonl')
        record=summarize_events(reader, events)
        if record:
            details[phase]=record
    home=home_details(reader,evidence)
    home_window=next((row for row in windows if row['phase']=='home'),None)
    if home is not None and home_window is not None:
        journal=reader.read(evidence/'home/home.json')
        home['phase_window_start_to_intent_pc_s']=seconds(home_window['start_pc_ns'],journal.get('intent_ns'))
        home['journal_finish_to_phase_window_end_pc_s']=seconds(journal.get('finished_ns'),home_window['end_pc_ns'])
    command=reader.read(evidence.parent/'command-result.json')
    wrapper=None
    if command:
        wrapper=dict(returncode=command.get('returncode'),command=command.get('command'),
            elapsed_monotonic_s=command.get('command_elapsed_s'),
            elapsed_wall_s=seconds(command.get('started_ns'),command.get('finished_ns')),
            setup_before_cycle_pc_s=seconds(command.get('started_ns'),cycle['created_ns']),
            cleanup_after_cycle_pc_s=seconds(cycle['updated_ns'],command.get('finished_ns')),
            source_commit=command.get('source_commit'),
            note='Wrapper monotonic total includes launcher work outside cycle.created_ns/updated_ns; separate readonly preflight excluded.')
    missing=[phase for phase in PHASE_DIR if phase not in details and phase!='home']
    observed_phases = {row['phase'] for row in windows}
    expected_phases = set(PHASE_DIR)-set(cycle.get('skipped_stages', []))
    missing_boundaries = sorted(expected_phases-observed_phases)
    if missing_boundaries:
        reader.warnings.append('Phase boundaries not captured separately: '+', '.join(missing_boundaries)+
            '; accounting can balance while windows contain unobserved work.')
    return dict(version=1,evidence=str(evidence.resolve()),
        scope='Single local recorded cycle; no stitching, remote connections, or movement',
        cycle_status=cycle.get('status'),cycle_terminal=cycle.get('status') in TERMINAL,
        full_cycle_succeeded=cycle.get('status')=='succeeded' and home is not None
            and home.get('phase')=='succeeded' and home.get('measured_home') is True,
        last_phase_boundary=cycle.get('phase_boundary'),in_flight=cycle.get('in_flight'),
        error=cycle.get('error'),pc_created_ns=cycle['created_ns'],pc_updated_ns=cycle['updated_ns'],
        pc_recorded_total_s=total,pc_windows=windows,
        pc_windows_sum_s=sum(row['duration_s'] for row in windows),
        pc_accounting_residual_s=total-sum(row['duration_s'] for row in windows),
        observer=observation,phase_event_details=details,home=home,wrapper=wrapper,
        phases_without_separate_pc_window=missing_boundaries,
        phases_without_event_evidence=missing, warnings=reader.warnings,source_sha256=reader.hashes,
        caveats=['Only PC timestamp pairs are used for PC windows; only Motion timestamp pairs for SDK/action and query durations.',
            'SDK durations use inner detail.time_ns, never outer reception timestamps.',
            'SDK accepted-to-result measures the native action, not instrumented physical onset/end.',
            'Timing events and stages can be nested or parallel; do not add them without an exclusive interval model.',
            'Failed/incomplete cycles are reported as such. Missing phases and HOME timing remain missing.',
            'Observer phase windows include interphase coordination. Exact matching completion is given separately when captured.',
            'Recipe support/pins remain assumptions, not fresh measurements.'])


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--observer',type=Path)
    args=parser.parse_args(argv)
    report=analyze(args.evidence,args.observer)
    args.output.mkdir(parents=True,exist_ok=False,mode=0o700)
    (args.output/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    with (args.output/'pc-phases.csv').open('w',newline='') as stream:
        keys=['phase','duration_s','percent_recorded_cycle','measurement','start_pc_ns','end_pc_ns']
        writer=csv.DictWriter(stream,fieldnames=keys,extrasaction='ignore')
        writer.writeheader();writer.writerows(report['pc_windows'])
    print(json.dumps(dict(status=report['cycle_status'],complete=report['full_cycle_succeeded'],
        pc_total_s=report['pc_recorded_total_s'],accounting_residual_s=report['pc_accounting_residual_s'],
        report=str((args.output/'summary.json').resolve())),ensure_ascii=False,indent=2))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
