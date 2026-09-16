#!/usr/bin/env python3
"""Diagnostic exclusive-stage groups. Never claim complete autonomy ownership."""
import argparse
import csv
import json
import math
from pathlib import Path

import analyze_cpu_window_alignment as alignment

SIM = {'sim_static_cloud_callback', 'sim_odom_callback', 'sim_render_callback'}
COMMON = {'frontend_report', 'frontend_stats', 'planner_visualize_path'}


def category(name):
    if name in SIM:
        return 'simulator_sensor_measured'
    if name in COMMON:
        return 'diagnostic_visualization_measured'
    if name.startswith(('map_', 'frontend_', 'fsm_', 'guard_', 'planner_')):
        return 'autonomy_measured_subtotal'
    return 'unclassified_measured'


def group(stages):
    result = {name: 0.0 for name in ('simulator_sensor_measured',
        'diagnostic_visualization_measured', 'autonomy_measured_subtotal', 'unclassified_measured')}
    seen = set()
    for item in stages:
        name = item['stage']
        cpu = float(item['exclusive_cpu_core_s'])
        if name in seen or not math.isfinite(cpu) or cpu < 0:
            raise ValueError('Duplicate stage or invalid exclusive CPU')
        seen.add(name)
        result[category(name)] += cpu
    return result


def required_stages(mode):
    required = {'map_odom_callback', 'sim_render_callback'}
    if mode != 'full':
        required |= {'frontend_cloud', 'frontend_acquisition', 'frontend_enqueue',
                     'frontend_odom', 'frontend_stats'}
    # The fixed-sector policy does not subscribe to recovery map ACKs.
    # Inactive callbacks must not be confused with missing instrumentation.
    if mode == 'adaptive':
        required.add('frontend_map_ack')
    return required


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('campaign', type=Path)
    args = parser.parse_args()
    root = args.campaign
    output = root / 'attribution'
    output.mkdir(exist_ok=False)
    report = alignment.analyze(root / 'profile_preflight_run9500')
    (output / 'alignment.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    rows = []
    for mode, data in report['modes'].items():
        if not data['available'] or len(data['processes']) != 1:
            raise ValueError('Expected exactly one composed profiler process')
        process = data['processes'][0]
        stage = process['stage_profile']
        names = {item['stage'] for item in stage['stages']}
        required = required_stages(mode)
        if not required <= names:
            raise ValueError(f'{mode}: missing new diagnostic scopes {required - names}')
        groups = group(stage['stages'])
        residual = process['scopes']['composed_process']['read_bracket_conservative'][
            'stage_subtracted_accounting_residual']
        other = process['scopes']['noncomposed_processes']['read_bracket_conservative']
        rows.append(dict(mode=mode, profile_window_s=stage['duration_s'],
            **{key + '_cores': value / stage['duration_s'] for key, value in groups.items()},
            residual_accounting_lower_cores=residual['lower_accounting_mean_cores'],
            residual_accounting_upper_cores=residual['upper_accounting_mean_cores'],
            noncomposed_lower_cores=other['lower_mean_cores'],
            noncomposed_upper_cores=other['upper_mean_cores']))
    with (output / 'groups.csv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    lines = ['# Seed1 C19 diagnostic CPU attribution', '',
        'ON n=1 per mode, exclusive thread CPU only. 1 core = 100% of one logical CPU.', '',
        '| Mode | Window s | Autonomy measured subtotal (cores) | Simulator callbacks | Diagnostic/visualization | Composed accounting residual range | Other experiment processes |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for row in rows:
        upper = row['residual_accounting_upper_cores']
        residual = f"{row['residual_accounting_lower_cores']:.6f} to " + (
            f'{upper:.6f}' if upper is not None else 'unknown')
        other_upper = row['noncomposed_upper_cores']
        other = f"{row['noncomposed_lower_cores']:.6f} to " + (
            f'{other_upper:.6f}' if other_upper is not None else 'unknown')
        lines.append(f"| {row['mode']} | {row['profile_window_s']:.3f} | "
            f"{row['autonomy_measured_subtotal_cores']:.6f} | "
            f"{row['simulator_sensor_measured_cores']:.6f} | "
            f"{row['diagnostic_visualization_measured_cores']:.6f} | {residual} | {other} |")
    lines += ['', 'The subtotal is NOT full autonomy CPU. Residual includes executor/DDS, '
        'uninstrumented work, profiling cost and completion/report boundary error. '
        'It is an accounting range, not a physical bound or avoidable waste. '
        'Noncomposed launcher/mission CPU remains included in primary cgroup metrics '
        'and is separately bounded in alignment.json. GPU work is not CPU work.', '',
        '## New ON/OFF smoke runs (not pooled with original OFF n=5)', '',
        '| Arm | Mode | Complete | Contacts | Mission s | Experiment mean cores | Experiment CPU core-s |',
        '|---|---|---:|---:|---:|---:|---:|']
    for arm, path in [('ON', 'profile_preflight_run9500'), ('OFF', 'repeats/r01_run9501')]:
        for mode in ('full', 'sector', 'adaptive'):
            summary = json.loads((root / path / f'{mode}_summary.json').read_text())
            lines.append(f"| {arm} | {mode} | {summary['success']} | "
                f"{summary['safety_collisions']} | {summary['mission_time_s']:.3f} | "
                f"{summary['end_to_end_cpu_cores_mean']:.6f} | {summary['end_to_end_cpu_core_s']:.6f} |")
    lines += ['', 'One reversed-order ON/OFF pair per mode does not isolate profiler overhead '
        'from scheduling/trajectory variability. Old frozen C19 n=5 remains the main '
        'performance evidence; these runs verify diagnostic coverage and regressions. '
        'No 40% acceptance selection or automatic retries.', '']
    (output / 'README.md').write_text('\n'.join(lines))
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
