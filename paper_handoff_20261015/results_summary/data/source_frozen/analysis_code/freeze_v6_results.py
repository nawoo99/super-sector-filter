#!/usr/bin/env python3
"""Read-only flight analysis and a content-hashed V6 result release.

Never launches ROS, edits experiment inputs, retries flights, or promotes a runtime.
Build refuses existing output. Seal is one-shot; verify never modifies artifacts.
"""
import argparse
import csv
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import statistics
from zoneinfo import ZoneInfo

REPO = Path('/root/super-sector-filter')
SOURCE = REPO / 'results/topology_polyline_v6_n10_completion_20261007'
MODES = ('full', 'sector', 'adaptive')
MAPS = ('gapfree_d1_m01', 'gapfree_d1_m02', 'gapfree_d1_m03',
        'gapfree_d1_m04', 'gapfree_d1_m05r2', 'urban_blocks_u01', 'forest_cluster_f01')
LABELS = dict(zip(MAPS, ('Map1', 'Map2', 'Map3', 'Map4', 'Map5', 'Urban', 'Forest')))
METRICS = ('cpu_cores', 'cpu_core_s', 'input_mib_s', 'input_mib_run', 'map_ms')
CASES = (('forest_cluster_f01', 3), ('forest_cluster_f01', 4),
         ('forest_cluster_f01', 5), ('gapfree_d1_m01', 6))


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def json_write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def write_csv(path, rows):
    if not rows:
        raise ValueError('Empty result table')
    with Path(path).open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def boolean(value):
    if value not in ('True', 'False'):
        raise ValueError('Non-boolean result: ' + str(value))
    return value == 'True'


def count(value):
    """CSV allows 8.0, but never fractional, missing, negative or NaN counts."""
    number = float(value)
    if not math.isfinite(number) or not number.is_integer() or number < 0:
        raise ValueError('Invalid count: ' + str(value))
    return int(number)


def validate_audits(summary):
    acquisition = summary['source_acquisition']
    checks = acquisition.get('checks')
    if (not isinstance(checks, dict) or not checks or
            any(value is not True for value in checks.values()) or not acquisition.get('frames')):
        raise ValueError('Missing or invalid acquisition audit')
    recovery = summary['strict_recovery_audit']
    required = ('records_well_formed', 'source_records_present',
                'completed_cycles_fresh_full_source', 'completed_cycles_exact_committed_ack',
                'completed_cycles_new_certified_path', 'completed_cycles_timestamp_order')
    if (recovery.get('valid') is not True or recovery.get('mode') != summary['mode'] or
            recovery.get('schema') != 'cpu40-source-recovery-audit-v1' or
            any(recovery.get('checks', {}).get(k) is not True for k in required)):
        raise ValueError('Missing or invalid recovery audit')
    yaw = summary['active_yaw_scan_v1_audit']
    if (yaw.get('valid') is not True or not yaw.get('records') or
            yaw.get('expected_enabled') != ('true' if summary['mode'] == 'sector' else 'false')):
        raise ValueError('Missing or invalid active-yaw audit')


def validate_inventory(rows):
    keys = [(r['stage'], r['map'], int(r['repeat']), r['mode']) for r in rows]
    expected = {('seven_map_n10', m, n, mode) for m in MAPS
                for n in range(1, 11) for mode in MODES}
    expected |= {('forest_n10', MAPS[-1], n, mode)
                 for n in range(1, 11) for mode in MODES}
    if len(rows) != 240 or len(set(keys)) != 240 or set(keys) != expected:
        raise ValueError('Expected exact 210 main plus 30 separate gate flights')
    for row in rows:
        if not boolean(row['quality_valid']) or not boolean(row['solid_replay_valid']):
            raise ValueError('Invalid evidence row')
        boolean(row['success'])
        for metric in ('time_s',) + METRICS:
            value = float(row[metric])
            if not math.isfinite(value) or value <= 0:
                raise ValueError('Invalid metric ' + metric)
        if int(row['contacts']) < 0:
            raise ValueError('Negative contacts')
        if row['mode'] != 'sector' and (not boolean(row['success']) or int(row['contacts'])):
            raise ValueError('Reference failure must not be hidden by freeze')


def aggregate(rows, group):
    result = dict(group=group, mode=rows[0]['mode'], n=len(rows),
                  complete=sum(boolean(r['success']) for r in rows),
                  contact_runs=sum(int(r['contacts']) > 0 for r in rows),
                  contact_episodes=sum(int(r['contacts']) for r in rows),
                  safe_complete=sum(boolean(r['success']) and not int(r['contacts']) for r in rows))
    result['observed_time_s_mean'] = statistics.mean(float(r['time_s']) for r in rows)
    completed = [float(r['time_s']) for r in rows if boolean(r['success'])]
    result['complete_time_s_mean'] = statistics.mean(completed) if completed else None
    result['complete_time_s_median'] = statistics.median(completed) if completed else None
    for metric in METRICS + ('host_cpu_pct_mean', 'baseline_host_cpu_pct_mean',
                             'experiment_host_capacity_pct', 'map_frames_s'):
        result[metric] = statistics.mean(float(r[metric]) for r in rows)
    result['adaptive_full_transitions_sum'] = (sum(count(r['full_transitions']) for r in rows)
                                               if rows[0]['mode'] == 'adaptive' else None)
    return result


def summary_markdown(per_map, groups, counts):
    lines = ['# V6 동결 실험 결과', '',
             '본실험은 7맵 × 3모드 × 각10회인 210회다. 별도 숲 사전시험30회는 합산하지 않는다.', '',
             '|모드|완주|접촉 주행|무접촉 완주|', '|---|---:|---:|---:|']
    for mode in MODES:
        c = counts[mode]
        lines.append(f"|{'Active-Yaw Sector' if mode == 'sector' else mode.title()}|"
                     f"{c['complete']}/70|{c['contact_runs']}/70|{c['safe_complete']}/70|")
    lines += ['', '## 맵별 결과', '',
              '|맵|모드|완주|접촉 주행|무접촉 완주|완주 평균시간 s|실패 포함 관측시간 s|CPU cores|CPU core-s/run|입력 MiB/s|입력 MiB/run|맵 ms/frame|Adaptive Full 전환 합계|',
              '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in per_map:
        values = [f'{r[k]:.3f}' if r[k] is not None else 'NA'
                  for k in ('complete_time_s_mean', 'observed_time_s_mean') + METRICS]
        lines.append('|'+ '|'.join([r['group'], r['mode'], f"{r['complete']}/10",
                                   f"{r['contact_runs']}/10", f"{r['safe_complete']}/10"] + values +
                                  [str(r['adaptive_full_transitions_sum']) if r['mode'] == 'adaptive' else 'NA'])+'|')
    lines += ['', '## 환경별 연산량', '',
              '맵1~5는 50회/모드의 비행별 산술평균, 도심지와 숲은 각각10회/모드의 평균이다. '
              '실패 비행의 관측·CPU·입력량도 제외하지 않는다.', '',
              '|환경|모드|CPU cores|CPU core-s/run|입력 MiB/s|입력 MiB/run|맵 ms/frame|컴퓨터 전체 CPU %|실험 CPU 전체용량 %|사전 호스트 CPU %|',
              '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in groups:
        vals = [f'{r[k]:.3f}' for k in METRICS + ('host_cpu_pct_mean',
                     'experiment_host_capacity_pct', 'baseline_host_cpu_pct_mean')]
        lines.append('|'+ '|'.join([r['group'], r['mode']] + vals)+'|')
    lines += ['', '## Adaptive의 Full 대비 감소율', '',
              '|환경|평균 CPU %|누적 CPU %|입력률 %|입력량 %|맵 갱신시간 %|',
              '|---|---:|---:|---:|---:|---:|']
    for group in ('Normal1-5', 'Urban', 'Forest'):
        base = next(r for r in groups if r['group'] == group and r['mode'] == 'full')
        ad = next(r for r in groups if r['group'] == group and r['mode'] == 'adaptive')
        vals = [f'{100*(1-ad[k]/base[k]):.2f}' for k in METRICS]
        lines.append('|'+ '|'.join([group]+vals)+'|')
    lines += ['', '## 지표와 주장 범위', '',
              '- 完주와 접촉은 독립 지표다. 접촉 후 목표에 도착하면 완주지만 무접촉 완주는 아니다.',
              '- CPU cores와core-s는 cgroup v2의 simulator+frontend+planner+mission 합계이며 '
              '관측기와 배경 프로세스를 제외한다. 컴퓨터 전체 CPU와 사전 기준치는 별도로 기록하며 차감하지 않는다.',
              '- 누적 CPU는 cgroup usage 증가량, 평균 CPU는 그 증가량/cgroup 측정기간이다. '
              '측정기간은 주행시간보다 약1.2~2.8초 길어 평균CPU×주행시간으로 누적CPU를 역산하지 않는다.',
              '- 입력률·입력량은 frontend→planner 맵 갱신 입력의 application payload다. '
              '네트워크 wire bandwidth나 raw sensor 전체 출력으로 해석하지 않는다.',
              '- 맵 계산시간은 프레임당 ms, 입력 데이터 총량은 비행당 MiB다.',
              '- 총 미션시간 상한은 없다. 동일 waypoint에서 3D 기준점 반경2cm 내60초 정체하면 '
              '종료하는 기존 관측 전용 규칙은 유지했다. '
              '미완주는 무한시간 불가능의 증명이 아니라 이 규칙에서 관측된 종료다.',
              '- 접촉은 수신 odometry의 반경0.2m 구체와 정적 solid 교차 감사다. '
              '연속 swept-volume 보장이나 실기체 충돌시험은 아니다.',
              '- Full과Adaptive의70/70 무접촉 완주는 이 시뮬레이션 표본에서의 결과이며 모집단 보장이 아니다.',
              '- CPU 목표값 추가 튜닝은 종료한다. 안전성·완주율의 통계적 우위 또는 시야만의 인과 효과를 '
              '이 소수 실패 건수로 확정하지 않는다.', '']
    return '\n'.join(lines).replace('完주', '완주')


def plot_case(output, map_name, repeat, rows, summaries):
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle
    colors = dict(full='#2864a5', sector='#d86b20', adaptive='#248b63')
    fig, axes = plt.subplots(2, 2, figsize=(13, 10))
    ax, clear, speed, aperture = axes.flat
    case_records = []
    for mode in MODES:
        row = next(r for r in rows if r['stage'] == 'seven_map_n10' and
                   r['map'] == map_name and int(r['repeat']) == repeat and r['mode'] == mode)
        folder = Path(row['directory'])
        stem = f'{map_name}_run{row["run"]}_{mode}.attempt1'
        odom = list(csv.DictReader((folder/'artifacts'/f'{stem}.odometry.csv').open()))
        solid = read_json(folder/'artifacts'/f'{stem}.solid_audit.json')
        summary = summaries[(row['stage'], row['map'], row['repeat'], row['mode'])]
        if mode == 'full':
            geom_path = Path(solid['geometry_path'])
            if geom_path.suffix == '.csv':
                cylinders = list(csv.DictReader(geom_path.open()))
                for c in cylinders:
                    ax.add_patch(Circle((float(c['x']), float(c['y'])), float(c['r']),
                                        color='#b3b8bc', alpha=.5))
            else:
                geom = read_json(geom_path)
                for c in geom['cylinders']:
                    ax.add_patch(Circle((c['x'], c['y']), c['r'], color='#b3b8bc', alpha=.5))
                for b in geom['boxes']:
                    ax.add_patch(Rectangle((b['cx']-b['size_x']/2, b['cy']-b['size_y']/2),
                                          b['size_x'], b['size_y'], color='#b3b8bc', alpha=.5))
            goals = summary['scenario7_mission']['waypoints_xyz']
            ax.scatter([p[0] for p in goals], [p[1] for p in goals], marker='*',
                       s=85, color='#606060', label='Mission goals', zorder=4)
        samples = odom[::10] + odom[-1:]
        t = [float(p['elapsed_s']) for p in samples]
        ax.plot([float(p['x_m']) for p in samples], [float(p['y_m']) for p in samples],
                color=colors[mode], label=f'{mode}: {row["time_s"]} s', lw=1.7)
        ax.scatter(float(odom[-1]['x_m']), float(odom[-1]['y_m']),
                   marker='s' if boolean(row['success']) else 'X', color=colors[mode], s=45, zorder=5)
        clear.plot(t, [float(p['clearance_m']) for p in samples], color=colors[mode], label=mode)
        speed.plot(t, [math.sqrt(sum(float(p[k])**2 for k in ('vx_mps', 'vy_mps', 'vz_mps')))
                       for p in samples], color=colors[mode], label=mode)
        origin = int(odom[0]['header_ns'])/1e9-float(odom[0]['elapsed_s'])
        frames = summary['source_acquisition']['frames']
        aperture.step([int(f['stamp_ns'])/1e9-origin for f in frames],
                      [360 if int(f['full']) else 2*float(f['half_angle_deg']) for f in frames],
                      where='post', color=colors[mode], alpha=.85, label=mode)
        for event in solid['events']:
            if event['kind'] == 'enter':
                ax.scatter(*event['position_m'][:2], marker='x', s=100, color=colors[mode], zorder=6)
                clear.scatter(event['elapsed_s'], event['clearance_m'], marker='x', s=45, color=colors[mode])
        case_records.append(dict(map=map_name, repeat=repeat, mode=mode, run=int(row['run']),
            directory=str(folder), success=boolean(row['success']), contacts=int(row['contacts']),
            time_s=float(row['time_s']), polyline_commits=int(row['polyline_commits']),
            solid=solid, active_yaw_audit=summary['active_yaw_scan_v1_audit'],
            strict_recovery_audit=summary['strict_recovery_audit']))
    ax.set(xlabel='x (m)', ylabel='y (m)', title='Received XY traces on static ground-truth geometry')
    ax.set_aspect('equal'); ax.legend(fontsize=8)
    clear.axhline(0, color='black', ls='--', lw=.8)
    clear.set(xlabel='Elapsed observation time (s)', ylabel='Body clearance (m)', title='Received-sample solid clearance')
    speed.set(xlabel='Elapsed observation time (s)', ylabel='Speed (m/s)', title='Measured speed')
    aperture.set(xlabel='Elapsed observation time (s)', ylabel='Acquisition aperture (deg)',
                 title='Recorded instantaneous aperture, not visible occupancy', yticks=[90, 360], ylim=(50, 400))
    for panel in (clear, speed, aperture):
        panel.legend(fontsize=8); panel.grid(alpha=.2)
    fig.suptitle(f'{LABELS[map_name]} repetition {repeat}: three independent flights')
    fig.text(.5, .01, 'Square = mission complete; X = failed terminal / contact. '
             'Aperture metadata is not a reconstruction of rays, occlusion, yaw or the planner map.',
             ha='center', fontsize=8)
    fig.tight_layout(rect=(0, .035, 1, .965))
    target = output/f'case_{LABELS[map_name].lower()}_r{repeat:02d}'
    fig.savefig(target.with_suffix('.png'), dpi=160)
    fig.savefig(target.with_suffix('.pdf'))
    plt.close(fig)
    return case_records


def build(source, output):
    if output.exists():
        raise ValueError('Existing output refused; frozen or partial results are never overwritten')
    state = read_json(source/'status.json'); audit = read_json(source/'final_audit.json')
    proof = read_json(source/'protocol.json')
    if state['state'] != 'COMPLETE' or not audit['valid'] or audit['retries'] != 0:
        raise ValueError('Only a complete, valid, unretried cohort may be frozen')
    rows = list(csv.DictReader((source/'flights.csv').open()))
    validate_inventory(rows)
    hashes = dict(proof['hashes'])
    for path, expected in hashes.items():
        if sha(path) != expected:
            raise ValueError('Experiment input/preserved evidence hash changed: ' + path)
    summaries, extended, audits = {}, [], []
    for row in rows:
        folder = Path(row['directory'])
        raw = folder/'raw.csv'
        stem = f'{row["map"]}_run{row["run"]}_{row["mode"]}.attempt1'
        stack = folder/'artifacts'/f'{stem}.stack.log'
        if sha(raw) != row['raw_sha256'] or sha(stack) != row['stack_sha256']:
            raise ValueError('Flight raw/stack hash changed')
        summary = read_json(folder/'summary.json')['results']
        if len(summary) != 1:
            raise ValueError('Single-flight summary expected')
        summary = summary[0]
        if (summary['success'] != boolean(row['success']) or summary['map'] != row['map'] or
                summary['mode'] != row['mode'] or summary['run'] != int(row['run'])):
            raise ValueError('Flight identity/outcome mismatch')
        for csv_key, summary_key in (('time_s', 'mission_time_s'),
                ('cpu_cores', 'end_to_end_cpu_cores_mean'), ('cpu_core_s', 'end_to_end_cpu_core_s'),
                ('map_ms', 'total_ms_mean')):
            if float(row[csv_key]) != summary[summary_key]:
                raise ValueError('Measured metric mismatch: ' + csv_key)
        if summary['solid_obstacle_audit']['contact_episodes'] != int(row['contacts']):
            raise ValueError('Solid contact count mismatch')
        for required in ('run_valid', 'resource_valid', 'speed_limit_valid'):
            if summary[required] is not True:
                raise ValueError('Invalid flight ' + required)
        validate_audits(summary)
        summaries[(row['stage'], row['map'], row['repeat'], row['mode'])] = summary
        extra = dict(row, host_cpu_pct_mean=summary['host_cpu_pct']['mean'],
                     baseline_host_cpu_pct_mean=summary['baseline_host_cpu_pct']['mean'],
                     experiment_host_capacity_pct=summary['experiment_host_capacity_pct'],
                     map_frames_s=summary['map_frames_s'])
        for field in ('host_cpu_pct_mean', 'baseline_host_cpu_pct_mean',
                      'experiment_host_capacity_pct', 'map_frames_s'):
            if not math.isfinite(float(extra[field])) or float(extra[field]) < 0:
                raise ValueError('Invalid telemetry ' + field)
        extended.append(extra)
        audits.append(dict(identity=[row['stage'], row['map'], int(row['repeat']), row['mode']],
            algorithm_cpu_scope=summary['algorithm_cpu_scope'],
            host_cpu_pct=summary['host_cpu_pct'], baseline_host_cpu_pct=summary['baseline_host_cpu_pct'],
            processes=summary['processes'],
            source_checks=summary['source_acquisition']['checks'],
            active_yaw_scan=summary['active_yaw_scan_v1_audit'],
            strict_recovery=summary['strict_recovery_audit']))
        for file in folder.rglob('*'):
            if file.is_file():
                hashes[str(file.resolve())] = sha(file)
        controller = folder.with_suffix('.controller.log')
        hashes[str(controller)] = sha(controller)
    for name in ('status.json', 'final_audit.json', 'flights.csv', 'summary_by_map.md',
                 'protocol.json', 'prefix_reaudit.json', 'controller.log'):
        path = source/name; hashes[str(path)] = sha(path)
    hashes[str(Path(__file__).resolve())] = sha(__file__)
    main = [r for r in extended if r['stage'] == 'seven_map_n10']
    gate = [r for r in extended if r['stage'] == 'forest_n10']
    per_map = [aggregate([r for r in main if r['map'] == m and r['mode'] == mode], LABELS[m])
               for m in MAPS for mode in MODES]
    groups = [aggregate([r for r in main if r['map'] in selected and r['mode'] == mode], label)
              for label, selected in (('Normal1-5', MAPS[:5]), ('Urban', MAPS[5:6]), ('Forest', MAPS[6:]))
              for mode in MODES]
    counts = {mode: aggregate([r for r in main if r['mode'] == mode], 'All7') for mode in MODES}
    output.mkdir(parents=True)
    write_csv(output/'main_210.csv', main); write_csv(output/'forest_gate_30.csv', gate)
    write_csv(output/'summary_by_map.csv', per_map); write_csv(output/'summary_by_environment.csv', groups)
    json_write(output/'audit_records.json', audits)
    json_write(output/'counts.json', counts)
    json_write(output/'source_manifest.json', dict(schema='v6-result-sources-v1',
        campaign=str(source), candidate=proof['candidate'], sha256=hashes,
        parent_physical_flights=113, suffix_physical_flights=127, main_flights=210, gate_flights=30,
        retries=0, original_failures_retained=True, canonical_promoted=False,
        historical_c41_files_replaced=False, observation='received_odometry_samples_only',
        global_mission_cutoff_s=None, terminal_no_progress_s=60, terminal_no_progress_radius_m=.02))
    (output/'summary_final.md').write_text(summary_markdown(per_map, groups, counts))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors = ('#2864a5', '#d86b20', '#248b63')
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    for ax, group in zip(axes, ('Normal1-5', 'Urban', 'Forest')):
        base = next(r for r in groups if r['group'] == group and r['mode'] == 'full')
        for index, mode in enumerate(MODES):
            row = next(r for r in groups if r['group'] == group and r['mode'] == mode)
            ax.bar([i+(index-1)*.25 for i in range(5)], [row[k]/base[k]*100 for k in METRICS],
                   width=.24, label=mode, color=colors[index])
        ax.set(title=group, ylabel='Full-normalized cost (%)', xticks=range(5),
               xticklabels=['CPU\nmean', 'CPU\ntime', 'Input\nrate', 'Input\npayload', 'Map\ntime'])
        ax.axhline(100, color='gray', ls='--', lw=.7); ax.legend(fontsize=8)
    fig.suptitle('All outcomes retained; arithmetic mean of per-flight metrics')
    fig.tight_layout(); fig.savefig(output/'compute_comparison.png', dpi=160)
    fig.savefig(output/'compute_comparison.pdf'); plt.close(fig)
    cases = []
    for map_name, repeat in CASES:
        cases.extend(plot_case(output, map_name, repeat, rows, summaries))
    json_write(output/'case_records.json', cases)
    json_write(output/'build_complete.json', dict(state='BUILT_NOT_SEALED', main=210, gate=30,
        sha256={p.name: sha(p) for p in sorted(output.iterdir()) if p.is_file()}))
    print(json.dumps(dict(state='BUILT_NOT_SEALED', main=210, gate=30,
                         source_files=len(hashes), output=str(output))))


def seal(output):
    manifest = output/'freeze_manifest.json'
    if manifest.exists():
        raise ValueError('Already sealed; do not reseal edited results')
    complete = read_json(output/'build_complete.json')
    if complete.get('state') != 'BUILT_NOT_SEALED' or (complete.get('main'), complete.get('gate')) != (210, 30):
        raise ValueError('Incomplete analysis build cannot be frozen')
    for name, expected in complete['sha256'].items():
        if sha(output/name) != expected:
            raise ValueError('Build artifact changed before seal: ' + name)
    source = read_json(output/'source_manifest.json')
    for name, expected in source['sha256'].items():
        if sha(name) != expected:
            raise ValueError('Source changed before seal: ' + name)
    assets = {str(p.relative_to(output)): sha(p) for p in sorted(output.rglob('*')) if p.is_file()}
    json_write(manifest, dict(schema='v6-result-freeze-v1', state='FROZEN',
        frozen_at=datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),
        version=output.name, primary_cohort='main_210.csv', separate_gate='forest_gate_30.csv',
        sha256=assets, cpu_target_tuning_closed=True, sector_comparator_changes_closed=True,
        canonical_promoted=False, historical_results_overwritten=False,
        scope='Versioned result release only, not a runtime promotion or population safety guarantee'))
    verify(output)


def verify(output):
    manifest = read_json(output/'freeze_manifest.json')
    if manifest['state'] != 'FROZEN':
        raise ValueError('Unsealed release')
    files = {str(p.relative_to(output)) for p in output.rglob('*') if p.is_file()}
    if files != set(manifest['sha256']) | {'freeze_manifest.json'}:
        raise ValueError('Missing or unexpected release asset')
    for name, expected in manifest['sha256'].items():
        if sha(output/name) != expected:
            raise ValueError('Frozen asset changed: ' + name)
    sources = read_json(output/'source_manifest.json')['sha256']
    for name, expected in sources.items():
        if sha(name) != expected:
            raise ValueError('Frozen source changed: ' + name)
    print(json.dumps(dict(state='VERIFIED', assets=len(manifest['sha256']), sources=len(sources),
                         manifest_sha256=sha(output/'freeze_manifest.json'))))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('build', 'seal', 'verify'))
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.stage == 'build':
        build(args.source.resolve(), args.output.resolve())
    elif args.stage == 'seal':
        seal(args.output.resolve())
    else:
        verify(args.output.resolve())


if __name__ == '__main__':
    main()
