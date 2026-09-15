#!/usr/bin/env python3
"""Offline timing evidence only: no ROS, subscriptions, or runtime changes.

Usage: python3 analyze_timing.py CAMPAIGN_DIR [CAMPAIGN_DIR ...]
Prints JSON; redirect to a new artifact file. Requires the existing strict audit.
"""
import argparse
from collections import defaultdict
from decimal import Decimal
import json
from pathlib import Path
import re
import statistics
import sys

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'scripts/native_campaign'))
from audit_cpu40_recovery import PATTERNS, ROS_TIME, audit_text  # noqa: E402

PROFILE = re.compile(
    r'\[THREAD_CPU_PROFILE\].*?steady_ns=(\d+).*?stage=(\w+) calls=(\d+)')


def distribution(values):
    ordered = sorted(values)
    if not ordered:
        return dict(count=0)

    def percentile(q):
        position = (len(ordered) - 1) * q
        lower = int(position)
        upper = min(lower + 1, len(ordered) - 1)
        return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)

    return dict(count=len(ordered), min=min(ordered), mean=statistics.fmean(ordered),
                p50=percentile(.5), p95=percentile(.95), p99=percentile(.99), max=max(ordered))


def analyze(log_path, monitor_path, mode):
    text = log_path.read_text(errors='replace')
    evidence = audit_text(text, mode)
    records = defaultdict(list)
    profile = defaultdict(list)
    for line in text.splitlines():
        for kind, pattern in PATTERNS.items():
            match = pattern.search(line)
            if not match:
                continue
            row = {key: int(value) for key, value in match.groupdict().items()
                   if key != 'half_angle_deg'}
            timestamp = ROS_TIME.search(line)
            row['time_ns'] = int(Decimal(timestamp.group(1)) * 10**9) if timestamp else None
            records[kind].append(row)
        match = PROFILE.search(line)
        if match:
            stamp, stage, count = match.groups()
            profile[stage].append((int(stamp), int(count)))

    frames = sorted(records['source'], key=lambda row: row['frame'])
    intervals = [(b['stamp_ns'] - a['stamp_ns']) / 1e6 for a, b in zip(frames, frames[1:])]
    missing_frames = sum(max(0, b['frame'] - a['frame'] - 1) for a, b in zip(frames, frames[1:]))
    sources = {row['stamp_ns']: row for row in frames}
    cycles = []

    def unique(kind, predicate):
        selected = [row for row in records[kind] if predicate(row)]
        return selected[0] if len(selected) == 1 else None

    for verified in evidence['completed_cycles']:
        if not verified['valid']:
            continue
        cycle, stamp, map_id = verified['cycle'], verified['stamp_ns'], verified['ack_map']
        opened = unique('open', lambda row: row['cycle'] == cycle)
        frontend_ack = unique('ack', lambda row: row['cycle'] == cycle)
        path = unique('path', lambda row: row['stamp_ns'] == stamp and row['ack_map'] == map_id)
        closed = unique('close', lambda row: row['cycle'] == cycle)
        fsm_ack = unique('fsm_ack', lambda row: row['stamp_ns'] == stamp and row['map'] == map_id
                         and row['request_seq'] == path['request_seq'] and row['committed'] == 1)
        times = dict(open=opened['time_ns'], source=sources[stamp]['stamp_ns'],
                     frontend_ack=frontend_ack['time_ns'],
                     fsm_ack=fsm_ack['time_ns'] if fsm_ack else None,
                     path=path['time_ns'], close=closed['time_ns'])
        latency = {}
        for begin, end in [('open', 'source'), ('source', 'frontend_ack'), ('source', 'fsm_ack'),
                           ('fsm_ack', 'path'), ('frontend_ack', 'path'),
                           ('path', 'close'), ('open', 'close')]:
            latency[f'{begin}_to_{end}_ms'] = ((times[end] - times[begin]) / 1e6
                                              if times[begin] is not None and times[end] is not None
                                              else None)
        cycles.append(dict(cycle=cycle, frame=sources[stamp]['frame'], map_id=map_id, **latency))

    callback_windows = {}
    for stage in ('fsm_main_callback', 'fsm_command_callback', 'fsm_replan_callback'):
        samples = sorted(set(profile[stage]))
        windows = [dict(span_s=(b[0] - a[0]) / 1e9,
                        completed_calls=b[1] - a[1],
                        completed_calls_per_s=(b[1] - a[1]) * 1e9 / (b[0] - a[0]))
                   for a, b in zip(samples, samples[1:]) if b[0] > a[0] and b[1] >= a[1]]
        callback_windows[stage] = dict(
            report_windows=windows,
            completed_calls_per_s=distribution([row['completed_calls_per_s'] for row in windows]),
            interpretation='Approximate finished callback count per profiler reporting window; '
                           'not callback start jitter, timer lateness, or published-message rate.')

    monitor = json.loads(monitor_path.read_text()) if monitor_path.exists() else {}
    duration = monitor.get('mission_time_s')
    odom_count = monitor.get('samples')
    return dict(
        mode=mode, stack_log=str(log_path), monitor_json=str(monitor_path),
        strict_recovery_audit_valid=evidence['valid'], strict_audit_errors=evidence['errors'],
        acquisition_stamp_intervals_ms=distribution(intervals),
        acquisition_missing_frame_numbers=missing_frames,
        acquisition_first_to_last_hz=((len(frames) - 1) * 1e9 / (frames[-1]['stamp_ns'] - frames[0]['stamp_ns'])
                                    if len(frames) > 1 and frames[-1]['stamp_ns'] > frames[0]['stamp_ns'] else None),
        recovery_cycles=cycles,
        recovery_latency_distributions_ms={key: distribution([row[key] for row in cycles if row[key] is not None])
                                          for key in cycles[0] if key.endswith('_ms')} if cycles else {},
        callback_count_windows=callback_windows,
        observed_odom_count=odom_count, rounded_monitor_duration_s=duration,
        observed_odom_count_per_rounded_duration_s=(odom_count / duration if duration and odom_count is not None else None),
        unavailable=['Per-message odometry stamp/receipt interval distribution',
                     'PositionCommand publication or receipt count and interval distribution',
                     'Timer callback start lateness/execution wall time',
                     'Actual map-commit timestamp or ACK publication→subscriber scheduling latency'],
        limitations=['Source stamps and ROS log stamps assume the unchanged system/ROS clock used in these runs.',
                     'Recovery ACK times are subscriber processing/log times, not exact commit times.',
                     'Frontend ACK may legitimately arrive after FSM PATH_READY; its signed delta is not a safety failure.',
                     'Whole startup→shutdown source coverage differs from monitor mission and profiler report windows.',
                     'Monitor odom count/duration is only a rounded mission-wide receive-rate approximation.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('campaign', type=Path, nargs='+')
    args = parser.parse_args()
    runs = []
    for campaign in args.campaign:
        for mode in ('full', 'adaptive'):
            for log_path in sorted((campaign / 'artifacts').glob(f'*_{mode}.attempt*.stack.log')):
                monitor_path = log_path.with_name(log_path.name.split('.attempt')[0] + '.json')
                runs.append(dict(campaign=campaign.name, **analyze(log_path, monitor_path, mode)))
    print(json.dumps(dict(schema='executor-preflight-existing-log-timing-v1', runs=runs), indent=2))


if __name__ == '__main__':
    main()
