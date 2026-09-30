#!/usr/bin/env python3
"""Audit the Urban no-cutoff Sector cohort and build replacement tables."""
from __future__ import annotations

import csv
import json
import math
import statistics
from collections import Counter
from pathlib import Path

import mpmath


ROOT = Path(__file__).resolve().parent
V12_AUDIT = Path(
    '/root/super-sector-filter/results/'
    'scenario7_velocity_centered_v12_n10_20260928/'
    'paper_audit_20260929'
)
EXPECTED_RUNS = tuple(range(94401, 94411))
LOGICAL_CPUS = 20
METRICS = (
    ('mission_time_s', 's/run'),
    ('mean_cpu_cores', 'cores'),
    ('host_capacity_pct', '% of host'),
    ('total_cpu_core_s', 'core-s/run'),
    ('input_bandwidth_mib_s', 'MiB/s'),
    ('total_input_mib_run', 'MiB/run'),
    ('map_computation_ms_frame', 'ms/frame'),
)


def truth(value):
    return str(value).strip().lower() in {'1', 'true', 'yes'}


def save_json(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def beta_cdf(value, alpha, beta):
    return float(mpmath.betainc(alpha, beta, 0, value, regularized=True))


def beta_quantile(probability, alpha, beta):
    low, high = 0.0, 1.0
    for _ in range(90):
        middle = (low + high) / 2.0
        if beta_cdf(middle, alpha, beta) < probability:
            low = middle
        else:
            high = middle
    return (low + high) / 2.0


def clopper_pearson(successes, trials):
    lower = 0.0 if successes == 0 else beta_quantile(
        0.025, successes, trials - successes + 1
    )
    upper = 1.0 if successes == trials else beta_quantile(
        0.975, successes + 1, trials - successes
    )
    return [lower, upper]


def load_new_sector():
    rows = []
    errors = []
    for index, run in enumerate(EXPECTED_RUNS, 1):
        output = ROOT / f'r{index:02d}_run{run}'
        raw_path = output / 'raw.csv'
        with raw_path.open(newline='') as stream:
            raw_rows = list(csv.DictReader(stream))
        if len(raw_rows) != 1:
            errors.append(f'{raw_path}: expected one row, found {len(raw_rows)}')
            continue
        raw = raw_rows[0]
        monitor_path = next((output / 'artifacts').glob('*.attempt1.json'))
        audit_path = next((output / 'artifacts').glob('*.solid_audit.json'))
        monitor = json.loads(monitor_path.read_text())
        audit = json.loads(audit_path.read_text())
        expected = {
            'map': 'urban_blocks_u01',
            'mode': 'sector',
            'run': str(run),
            'run_valid': 'True',
            'resource_valid': 'True',
            'infrastructure_failure': 'False',
            'resource_guard_triggered': 'False',
            'speed_limit_valid': 'True',
            'perf_window_valid': 'True',
            'attempt_count': '1',
            'retry_count': '0',
        }
        for field, value in expected.items():
            if raw.get(field) != value:
                errors.append(
                    f'run{run} {field}: expected {value}, got {raw.get(field)}'
                )
        complete = truth(raw['success'])
        contacts = int(raw['safety_collisions'])
        if monitor.get('success') is not complete:
            errors.append(f'run{run}: monitor success mismatch')
        if int(monitor.get('safety_collisions', -1)) != contacts:
            errors.append(f'run{run}: monitor contact mismatch')
        if audit.get('completion') is not True or audit.get('audit_valid') is not True:
            errors.append(f'run{run}: solid audit incomplete/invalid')
        if audit.get('success') is not complete:
            errors.append(f'run{run}: solid audit success mismatch')
        if int(audit.get('contact_episodes', -1)) != contacts:
            errors.append(f'run{run}: solid audit contact mismatch')
        terminal = monitor.get('terminal_condition') or 'mission_complete'
        if complete and terminal != 'mission_complete':
            errors.append(f'run{run}: completed run has a failure terminal')
        if not complete and terminal not in {
            'persistent_contact_stall', 'persistent_no_progress_stall'
        }:
            errors.append(f'run{run}: missing declared failure terminal')
        rows.append({
            'map': 'urban_blocks_u01',
            'run': run,
            'mode': 'sector',
            'complete': complete,
            'contact': contacts > 0,
            'contact_episodes': contacts,
            'safe_complete': complete and contacts == 0,
            'mission_time_s': float(raw['mission_time_s']),
            'waypoints_reached': int(float(raw['waypoints_reached'])),
            'n_waypoints': int(float(raw['n_waypoints'])),
            'terminal_condition': terminal,
            'static_pcd_clearance_m': float(raw['static_pcd_clearance_m']),
            'mean_cpu_cores': float(raw['end_to_end_cpu_cores_mean']),
            'host_capacity_pct': (
                100.0 * float(raw['end_to_end_cpu_cores_mean']) / LOGICAL_CPUS
            ),
            'total_cpu_core_s': float(raw['end_to_end_cpu_core_s']),
            'input_bandwidth_mib_s':
                float(raw['planner_ingress_payload_mib_s']),
            'total_input_mib_run':
                float(raw['map_payload_bytes_total']) / (1024.0**2),
            'map_computation_ms_frame': float(raw['total_ms_mean']),
            'raw_path': str(raw_path),
            'monitor_path': str(monitor_path),
            'solid_audit_path': str(audit_path),
        })
    if errors:
        raise RuntimeError('\n'.join(errors))
    if [row['run'] for row in rows] != list(EXPECTED_RUNS):
        raise RuntimeError('Unexpected or duplicate run IDs')
    return rows


def load_v12_rows():
    with (V12_AUDIT / 'canonical_210_rows.csv').open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        row['run'] = int(row['run'])
        for field in ('complete', 'contact', 'safe_complete'):
            row[field] = truth(row[field])
        for metric, _ in METRICS:
            row[metric] = float(row[metric])
    return rows


def outcome(rows, field):
    successes = sum(bool(row[field]) for row in rows)
    interval = clopper_pearson(successes, len(rows))
    return {
        'successes': successes,
        'trials': len(rows),
        'pct': 100.0 * successes / len(rows),
        'ci95_pct': [100.0 * interval[0], 100.0 * interval[1]],
    }


def metric_summary(rows, metric, full_mean=None):
    values = [float(row[metric]) for row in rows]
    result = {
        'n': len(values),
        'mean': statistics.fmean(values),
        'sd': statistics.stdev(values) if len(values) > 1 else 0.0,
        'median': statistics.median(values),
        'min': min(values),
        'max': max(values),
    }
    result['reduction_vs_full_pct'] = (
        None if full_mean is None
        else 100.0 * (full_mean - result['mean']) / full_mean
    )
    return result


def write_csv(path, rows, fields):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def main():
    sector = load_new_sector()
    v12 = load_v12_rows()
    urban = {
        'full': [row for row in v12
                 if row['map'] == 'urban_blocks_u01' and row['mode'] == 'full'],
        'sector': sector,
        'adaptive': [row for row in v12
                     if row['map'] == 'urban_blocks_u01'
                     and row['mode'] == 'adaptive'],
    }
    if any(len(rows) != 10 for rows in urban.values()):
        raise RuntimeError('Expected ten Urban rows per mode')

    outcomes = {}
    metrics = {}
    for mode, rows in urban.items():
        outcomes[mode] = {
            'completion': outcome(rows, 'complete'),
            'contact_runs': outcome(rows, 'contact'),
            'safe_completion': outcome(rows, 'safe_complete'),
        }
    for metric, unit in METRICS:
        full_mean = statistics.fmean(row[metric] for row in urban['full'])
        metrics[metric] = {'unit': unit}
        for mode, rows in urban.items():
            metrics[metric][mode] = metric_summary(rows, metric, full_mean)

    completed_sector = [row for row in sector if row['complete']]
    sector_terminals = Counter(row['terminal_condition'] for row in sector)

    # Requested replacement view: retain every original v12 row except Urban
    # Sector, which is replaced by this independently numbered no-cutoff cohort.
    overall_rows = [
        row for row in v12
        if not (row['map'] == 'urban_blocks_u01' and row['mode'] == 'sector')
    ] + sector
    overall = {}
    for mode in ('full', 'sector', 'adaptive'):
        mode_rows = [row for row in overall_rows if row['mode'] == mode]
        overall[mode] = {
            'rows': len(mode_rows),
            'completion': outcome(mode_rows, 'complete'),
            'contact_runs': outcome(mode_rows, 'contact'),
            'safe_completion': outcome(mode_rows, 'safe_complete'),
            'metrics': {},
        }
        full_rows = [row for row in overall_rows if row['mode'] == 'full']
        for metric, unit in METRICS:
            full_mean = statistics.fmean(row[metric] for row in full_rows)
            overall[mode]['metrics'][metric] = {
                'unit': unit,
                **metric_summary(mode_rows, metric, full_mean),
            }

    result = {
        'schema': 'urban-sector-no-mission-cutoff-replacement-v1',
        'audit': {
            'passed': True,
            'new_sector_rows': len(sector),
            'unique_run_ids': len({row['run'] for row in sector}),
            'attempt_count_each': 1,
            'retry_count_total': 0,
            'infrastructure_failure_rows': 0,
            'invalid_rows': 0,
            'frozen_asset_verification': json.loads(
                (ROOT / 'frozen_asset_verification.json').read_text()
            ),
        },
        'replacement_policy': {
            'urban_full_source': str(V12_AUDIT / 'canonical_210_rows.csv'),
            'urban_adaptive_source': str(V12_AUDIT / 'canonical_210_rows.csv'),
            'urban_sector_source': str(ROOT),
            'urban_sector_mission_time_cutoff_s': None,
            'urban_sector_event_terminal': {
                'stationary_window_s': 60.0,
                'position_radius_m': 0.02,
            },
            'paired_tests_valid_after_replacement': False,
            'reason':
                'The replacement Sector run IDs are not paired with the retained '
                'Full/Adaptive triplets and use a different terminal protocol.',
        },
        'urban': {
            'outcomes': outcomes,
            'metrics': metrics,
            'sector_terminal_counts': dict(sector_terminals),
            'sector_completed_mission_time_s': metric_summary(
                completed_sector, 'mission_time_s'
            ),
        },
        'overall_replacement_view': overall,
    }
    save_json(ROOT / 'replacement_summary.json', result)

    write_csv(
        ROOT / 'canonical_sector_rows.csv',
        sector,
        list(sector[0]),
    )
    comparison_rows = []
    for mode in ('full', 'sector', 'adaptive'):
        entry = {
            'mode': mode,
            'completion': outcomes[mode]['completion']['successes'],
            'trials': 10,
            'contact_runs': outcomes[mode]['contact_runs']['successes'],
            'safe_completion': outcomes[mode]['safe_completion']['successes'],
        }
        for metric, _ in METRICS:
            entry[metric] = metrics[metric][mode]['mean']
            entry[metric + '_reduction_vs_full_pct'] = (
                metrics[metric][mode]['reduction_vs_full_pct']
            )
        comparison_rows.append(entry)
    write_csv(
        ROOT / 'urban_replacement_table.csv',
        comparison_rows,
        list(comparison_rows[0]),
    )

    lines = [
        '# Urban Fixed Sector 무제한 재시험 및 교체 결과',
        '',
        '## 감사 판정',
        '',
        '- **PASS**: 새 Fixed Sector 10개 행, 고유 run ID 10개',
        '- 각 비행 attempt 1회, retry 0, infrastructure failure 0',
        '- 모든 행에서 run/resource/speed/performance/solid-audit 유효',
        '- 플래너·알고리즘·맵은 v12와 동일하며 전체 미션 제한시간만 제거',
        '- 비완주는 60초 연속 2 cm 이내 무이동 사건으로 종단했으며, 이는 플래너 입력을 바꾸지 않는 관측기 판정',
        '',
        '## 도심지 결과표',
        '',
        '| 모드 | 완주율 | 접촉 주행 | 안전 완주 | 관측시간 평균 | 완주 run 주행시간 평균 |',
        '|---|---:|---:|---:|---:|---:|',
    ]
    for mode, label in (
        ('full', 'Full'), ('sector', 'Fixed Sector'), ('adaptive', 'Adaptive')
    ):
        complete = outcomes[mode]['completion']
        contact = outcomes[mode]['contact_runs']
        safe = outcomes[mode]['safe_completion']
        all_time = metrics['mission_time_s'][mode]['mean']
        completed = [row['mission_time_s'] for row in urban[mode] if row['complete']]
        completed_text = f'{statistics.fmean(completed):.2f} s' if completed else 'N/A'
        lines.append(
            f"| {label} | {complete['successes']}/10 ({complete['pct']:.0f}%) "
            f"| {contact['successes']}/10 ({contact['pct']:.0f}%) "
            f"| {safe['successes']}/10 ({safe['pct']:.0f}%) "
            f"| {all_time:.2f} s | {completed_text} |"
        )
    lines += [
        '',
        '> Fixed Sector의 전체 10회 평균 76.67초는 비행시간 평균이 아니라 '
        '완주 또는 사건 기반 stall 판정까지의 관측시간이다.',
        '',
        '### 새 Fixed Sector 종단 구성',
        '',
        f"- 완주: {sector_terminals['mission_complete']}/10",
        f"- 지속 접촉 정지: {sector_terminals['persistent_contact_stall']}/10",
        f"- 비접촉 무진행 정지: {sector_terminals['persistent_no_progress_stall']}/10",
        '',
        '## 도심지 연산량',
        '',
        '| 지표 | Full | Fixed Sector (새 값) | Adaptive | Sector 감소율 | Adaptive 감소율 |',
        '|---|---:|---:|---:|---:|---:|',
    ]
    for metric, unit in METRICS[1:]:
        values = metrics[metric]
        lines.append(
            f"| {metric} ({unit}) | {values['full']['mean']:.3f} "
            f"| {values['sector']['mean']:.3f} "
            f"| {values['adaptive']['mean']:.3f} "
            f"| {values['sector']['reduction_vs_full_pct']:.1f}% "
            f"| {values['adaptive']['reduction_vs_full_pct']:.1f}% |"
        )
    lines += [
        '',
        '## 교체 적용 후 전체 70회/모드 기술값',
        '',
        '| 모드 | 완주 | 접촉 주행 | 안전 완주 |',
        '|---|---:|---:|---:|',
    ]
    for mode, label in (
        ('full', 'Full'), ('sector', 'Fixed Sector'), ('adaptive', 'Adaptive')
    ):
        item = overall[mode]
        lines.append(
            f"| {label} | {item['completion']['successes']}/70 "
            f"| {item['contact_runs']['successes']}/70 "
            f"| {item['safe_completion']['successes']}/70 |"
        )
    lines += [
        '',
        '## 해석 제한',
        '',
        '- 이 표에서는 요청에 따라 기존 v12 Urban Sector를 새 무제한 cohort로 교체했다.',
        '- Full/Adaptive는 기존 v12 run이고 Sector는 새 run이므로 세 모드가 같은 반복쌍이 아니다.',
        '- 따라서 이 교체 표에 기존 paired McNemar p-value를 재사용하면 안 된다.',
        '- 원본 v12 데이터와 paired 통계는 수정하지 않고 별도로 보존한다.',
        '- 비완주 Sector의 관측시간은 주행시간 성능 비교에 사용하지 않는다.',
        '- 결과는 이 고정 도심지 맵의 유한 반복 관측이며 population guarantee가 아니다.',
        '',
        '## Fixed Sector 개별 실행',
        '',
        '| run | 완주 | WP | 접촉 | 종단 | 시간(s) | 최소 clearance(m) |',
        '|---:|---:|---:|---:|---|---:|---:|',
    ]
    for row in sector:
        lines.append(
            f"| {row['run']} | {'O' if row['complete'] else 'X'} "
            f"| {row['waypoints_reached']}/{row['n_waypoints']} "
            f"| {row['contact_episodes']} | {row['terminal_condition']} "
            f"| {row['mission_time_s']:.2f} | {row['static_pcd_clearance_m']:.3f} |"
        )
    (ROOT / 'replacement_summary.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps({
        'audit': 'PASS',
        'sector_completion': outcomes['sector']['completion']['successes'],
        'sector_contact_runs': outcomes['sector']['contact_runs']['successes'],
        'sector_safe_completion': outcomes['sector']['safe_completion']['successes'],
        'terminal_counts': dict(sector_terminals),
        'output': str(ROOT / 'replacement_summary.md'),
    }, indent=2))


if __name__ == '__main__':
    main()
