#!/usr/bin/env python3
"""Summarize opt-in CPU counters over common report boundaries during flight.

Stage CPU excludes sleeping. Sum exclusive, never inclusive, stages. This
profile window lies inside the observer's flight window and is not exactly the
whole-flight cgroup CPU window. Uninstrumented worker CPU remains unaccounted.
"""
import argparse
import json
from pathlib import Path
import re

PATTERN = re.compile(
    r'\[THREAD_CPU_PROFILE\] version=1 pid=(\d+) steady_ns=(\d+) '
    r'final=([01]) stage=(\w+) calls=(\d+) inclusive_cpu_s=([\d.]+) '
    r'exclusive_cpu_s=([\d.]+) clock_errors=(\d+)')


def summarize(folder, mode, run):
    folder = Path(folder)
    telemetry = [json.loads(line) for line in (folder / 'telemetry.jsonl').read_text().splitlines()]
    times = [r['monotonic_s'] for r in telemetry
             if r['mode'] == mode and r['campaign_active']]
    if not times:
        return {'available': False, 'reason': 'no observed flight interval'}
    log = (folder / 'artifacts' / f'seed1_run{run}_{mode}.attempt1.stack.log').read_text(errors='replace')
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
            stages=sorted(stages, key=lambda r: r['exclusive_cpu_s'], reverse=True)))
    return dict(available=bool(result), mode=mode, processes=result,
        scope='thread CPU in instrumented stages only; common periodic report window within flight; not full cgroup window')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    args = parser.parse_args()
    plan = json.loads((args.folder / 'plan.json').read_text())
    report = {mode: summarize(args.folder, mode, plan['run']) for mode in plan['modes']}
    (args.folder / 'thread_cpu_summary.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
