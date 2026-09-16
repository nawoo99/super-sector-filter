#!/usr/bin/env python3
"""Summarize opt-in CPU counters over common report boundaries during flight.

Stage CPU excludes sleeping. Sum exclusive, never inclusive, stages. This
profile window lies inside the observer's flight window and is not exactly the
whole-flight cgroup CPU window. Uninstrumented worker CPU remains unaccounted.
"""
import argparse
import json
import math
from pathlib import Path
import re

PATTERN = re.compile(
    r'\[THREAD_CPU_PROFILE\] version=1 pid=(\d+) steady_ns=(\d+) '
    r'final=([01]) stage=(\w+) calls=(\d+) inclusive_cpu_s=([\d.]+) '
    r'exclusive_cpu_s=([\d.]+) clock_errors=(\d+)')

ROLE_PATTERN = re.compile(
    r'\[THREAD_CPU_ROLE\] version=1 pid=(\d+) tid=(\d+) role=(\w+)')


def role_cpu_summary(log, telemetry, mode, pid, start_s, end_s):
    """Use actual role/TID markers, never thread creation order or names.

    /proc intervals must lie wholly within the stage-profile window. Boundary
    intervals are excluded, so these averages are not exact stage residuals.
    """
    roles = {}
    for process, tid, role in ROLE_PATTERN.findall(log):
        if int(process) == pid:
            roles.setdefault(role, set()).add(int(tid))
    rows = [r for r in telemetry if r.get('mode') == mode and
            r.get('campaign_active') and r.get('interval_s', 0) > 0 and
            r['monotonic_s'] <= end_s and
            r['monotonic_s'] - r['interval_s'] >= start_s]
    duration = sum(r['interval_s'] for r in rows)
    result = []
    for role, tids in sorted(roles.items()):
        item = dict(role=role, tids=sorted(tids), unambiguous=len(tids) == 1,
                    eligible_interval_s=duration, observed_interval_s=0.,
                    sampled_cpu_core_s=0., mean_used_cores=None, samples=0)
        if len(tids) == 1:
            tid = next(iter(tids))
            for row in rows:
                matched = [t for t in row.get('experiment_threads', [])
                           if t.get('pid') == pid and t.get('tid') == tid]
                if len(matched) != 1:
                    continue
                pct = matched[0].get('cpu_pct_one_core')
                if not isinstance(pct, (int, float)) or not math.isfinite(pct) or pct < 0:
                    continue
                item['samples'] += 1
                item['observed_interval_s'] += row['interval_s']
                item['sampled_cpu_core_s'] += pct / 100 * row['interval_s']
            if item['observed_interval_s'] > 0:
                item['mean_used_cores'] = item['sampled_cpu_core_s'] / item['observed_interval_s']
        result.append(item)
    return dict(roles=result, interval_scope='Wholly enclosed /proc sample intervals; not exact stage boundaries or whole-flight cgroup window')


def summarize(folder, mode, run, map_name='seed1'):
    folder = Path(folder)
    telemetry = [json.loads(line) for line in (folder / 'telemetry.jsonl').read_text().splitlines()]
    times = [r['monotonic_s'] for r in telemetry
             if r['mode'] == mode and r['campaign_active']]
    if not times:
        return {'available': False, 'reason': 'no observed flight interval'}
    log = (folder / 'artifacts' / f'{map_name}_run{run}_{mode}.attempt1.stack.log').read_text(errors='replace')
    reports = {}
    for match in PATTERN.finditer(log):
        pid, ns, final, stage, calls, inclusive, exclusive, errors = match.groups()
        seconds = int(ns) / 1e9
        if not min(times) <= seconds <= max(times):
            continue
        reports.setdefault((int(pid), int(ns)), {})[stage] = dict(
            calls=int(calls), inclusive_cpu_s=float(inclusive),
            exclusive_cpu_s=float(exclusive), clock_errors=int(errors))
    pids = sorted({p for p, _ in reports})
    result = []
    for pid in pids:
        boundaries = sorted(ns for p, ns in reports if p == pid)
        if len(boundaries) < 2:
            continue
        first, last = boundaries[0], boundaries[-1]
        a, b = reports[(pid, first)], reports[(pid, last)]
        duration = (last - first) / 1e9
        stages = []
        for stage in b:
            old = a.get(stage, dict(calls=0, inclusive_cpu_s=0., exclusive_cpu_s=0.))
            row = {'stage': stage}
            for key in ('calls', 'inclusive_cpu_s', 'exclusive_cpu_s'):
                row[key] = b[stage][key] - old[key]
            row['mean_used_cores_exclusive'] = row['exclusive_cpu_s'] / duration
            row['inclusive_cpu_ms_per_call'] = (
                row['inclusive_cpu_s'] * 1000 / row['calls'] if row['calls'] else None)
            row['clock_errors'] = b[stage]['clock_errors']
            stages.append(row)
        result.append(dict(pid=pid, duration_s=duration,
            first_report_monotonic_s=first / 1e9, last_report_monotonic_s=last / 1e9,
            sum_exclusive_mean_cores=sum(r['mean_used_cores_exclusive'] for r in stages),
            thread_roles=role_cpu_summary(log, telemetry, mode, pid, first / 1e9, last / 1e9),
            stages=sorted(stages, key=lambda r: r['exclusive_cpu_s'], reverse=True)))
    return dict(available=bool(result), mode=mode, processes=result,
        scope='thread CPU in instrumented stages only; common periodic report window within flight; not full cgroup window')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    args = parser.parse_args()
    plan = json.loads((args.folder / 'plan.json').read_text())
    report = {mode: summarize(args.folder, mode, plan['run'], plan.get('map', 'seed1')) for mode in plan['modes']}
    (args.folder / 'thread_cpu_summary.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
