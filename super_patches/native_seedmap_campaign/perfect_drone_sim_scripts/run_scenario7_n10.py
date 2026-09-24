#!/usr/bin/env python3
"""Manual seven-map campaign: independent ON preflight and 210 OFF flights.

No flight is started by --dry-run or --report. Existing experiments, policies,
and the gapfree n5 controller are reused without modifying their files.
"""
from __future__ import annotations

import argparse
import contextlib
import csv
from datetime import datetime
import fcntl
import json
import os
from pathlib import Path
import signal
import statistics
import sys
import time

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import run_gapfree_n5 as previous
import scenario7_campaign_support as support
import scenario7_native_loop_monitor as geometry
import scenario7_missions as missions
import scenario7_mission_runtime as mission_runtime

base = previous.base
REPO = previous.REPO
MAPS = support.MAPS
MODES = ('full', 'sector', 'adaptive')
PHASES = ('preflight', 'test10')
COUNTS = {'preflight': 1, 'test10': 10}
CANDIDATE = 'c24_scenario7_n10_missions_v2'
SCHEMA = 'scenario7-n10-manual-v2'
PROTOCOL = REPO / 'docs/scenario7_n10_grouped_missions_20260924.md'


def aggregation_policy(maps=MAPS):
    groups = {'normal': MAPS[:5], 'urban': (MAPS[5],), 'forest': (MAPS[6],)}
    return dict(groups={group: [name for name in members if name in maps]
                        for group, members in groups.items() if any(name in maps for name in members)},
                all_seven_pooling=False, profile_preflight_pooled=False,
                cost_mean='Arithmetic mean of valid observed runs within each group and mode; n and SD reported',
                reduction_baseline='Full mean within the same group',
                missing_values_are_not_zero=True)


def selected_maps(values):
    values = tuple(values)
    if not values or len(values) != len(set(values)) or not set(values) <= set(MAPS):
        raise ValueError('Expected nonempty unique map names from the seven-map suite')
    return values


def build_plan(root, maps=MAPS, base_run=40000):
    maps = selected_maps(maps)
    if type(base_run) is not int or base_run < 1:
        raise ValueError('base_run must be a positive integer')
    commands = []
    for name in maps:
        for original in base.static_commands(root, name):
            item = dict(original, map=name)
            if item['name'].startswith('accept_'):
                item['command'] = [sys.executable, str(SCRIPTS / 'scenario7_campaign_support.py'),
                                   'static', *item['command'][2:]]
            commands.append(item)
    for phase in PHASES:
        for repeat in range(COUNTS[phase]):
            shift = repeat % len(maps)
            for name in maps[shift:] + maps[:shift]:
                index = MAPS.index(name)
                run = base_run + (0 if phase == 'preflight' else 100) + repeat * 10 + index
                folder = root / phase / name / f'r{repeat+1:02d}_run{run}'
                reference = root / 'preflight' / name / f'r01_run{base_run+index}'
                command = base.common_args(root)
                command[1] = str(SCRIPTS / 'scenario7_cpu_compare.py')
                command.remove('--extended-demand-lease')
                i = command.index('--time-reference-folder')
                del command[i:i+2]
                for flag, value in {
                    '--candidate': CANDIDATE, '--side-executor-threads': '3',
                    '--static-latched-preflight': str(root / 'static_preflight' / name / 'acceptance.json'),
                }.items():
                    command[command.index(flag)+1] = value
                order = base.ORDERS[(repeat+index) % len(base.ORDERS)]
                command += ['--event-body-heading', '--mission-time-as-metric', '--sector-outcomes-as-metrics',
                            '--async-certified-recovery', '--map', name, '--run', str(run), '--output', str(folder)]
                command += ['--profile-cpu'] if phase == 'preflight' else [
                    '--small-pool-profile-reference', str(reference)]
                command += ['--modes', *order]
                commands.append(dict(name=f'{phase}_{name}_r{repeat+1:02d}', phase=phase,
                    map=name, run=run, repeat=repeat+1, modes=list(order), path=str(folder),
                    candidate=CANDIDATE, async_certified_recovery=True,
                    mission=mission_runtime.mission_binding(missions.mission_context(name)), command=command))
    return commands


def contact_file(folder, name, run, mode):
    return folder / 'artifacts' / f'{name}_run{run}_{mode}.attempt1.solid_audit.json'


_CONTACT_EVIDENCE_CACHE = {}
_CONTACT_EVIDENCE_CACHE_LIMIT = 256


def _contact_file_fingerprint(path):
    """Track replacement, symlink retargeting, and edits with restored mtime."""
    path = Path(path).absolute()
    resolved = path.resolve(strict=True)
    link_stat, target_stat = path.lstat(), resolved.stat()
    fields = lambda value: (value.st_dev, value.st_ino, value.st_mode, value.st_size,
                            value.st_mtime_ns, value.st_ctime_ns)
    return str(path), str(resolved), fields(link_stat), fields(target_stat)


def _contact_input_fingerprint(path, pcd, doc):
    """Snapshot every file consumed by validation, including relocated sidecars."""
    import scenario7_geometry as solids
    resolved_pcd = pcd.resolve(strict=True)
    sidecar_suffix = '_cylinders.csv' if resolved_pcd.stem in solids.LEGACY_MAPS else '_geometry.json'
    prefix = path.name.removesuffix('.solid_audit.json')
    paths = [path, path.with_name(prefix + '.odometry.csv'), path.with_name(prefix + '.json'),
             pcd, resolved_pcd.with_name(resolved_pcd.stem + sidecar_suffix),
             Path(__file__), Path(previous.__file__), Path(base.__file__),
             Path(geometry.__file__), Path(solids.__file__), Path(geometry.frozen_adapter.__file__)]
    paths += [Path(doc[key]) for key in ('pcd_path', 'geometry_path', 'base_monitor_path',
                                        'observer_code_path', 'geometry_code_path', 'adapter_code_path')]
    return (id(geometry.validate_evidence), geometry.BASE_SHA256,
            tuple(_contact_file_fingerprint(item) for item in dict.fromkeys(paths)))


def contact_evidence(path, name):
    # Cache only successful complete replays. Stat snapshots avoid replaying all
    # completed flights on every progress update; nanosecond ctime also catches
    # same-size edits whose mtime has been deliberately restored. Changed or
    # missing inputs force validation again and cannot inherit a cached success.
    path = Path(path)
    pcd = support.PACKAGE / 'pcd/seed_maps' / (name + '.pcd')
    cache_key = (str(path.absolute()), name)
    try:
        audit_before_read = _contact_file_fingerprint(path)
    except (OSError, ValueError, RuntimeError):
        _CONTACT_EVIDENCE_CACHE.pop(cache_key, None)
        return base.load_document(path), False
    doc = base.load_document(path)
    before = None
    try:
        before = _contact_input_fingerprint(path, pcd, doc)
        if before[2][0] != audit_before_read:
            _CONTACT_EVIDENCE_CACHE.pop(cache_key, None)
            return doc, False
        if (_CONTACT_EVIDENCE_CACHE.get(cache_key) == before
                and before == _contact_input_fingerprint(path, pcd, doc)):
            return doc, True
    except (OSError, ValueError, KeyError, TypeError, RuntimeError):
        pass
    _CONTACT_EVIDENCE_CACHE.pop(cache_key, None)
    try:
        validation = geometry.validate_evidence(path, pcd)
        valid = validation.get('valid') is True if isinstance(validation, dict) else validation is True
        valid = valid and doc.get('map') == name and previous.contact_count(doc) is not None
        if before is not None:
            valid = valid and before == _contact_input_fingerprint(path, pcd, doc)
        if valid and before is not None:
            if len(_CONTACT_EVIDENCE_CACHE) >= _CONTACT_EVIDENCE_CACHE_LIMIT:
                _CONTACT_EVIDENCE_CACHE.pop(next(iter(_CONTACT_EVIDENCE_CACHE)))
            _CONTACT_EVIDENCE_CACHE[cache_key] = before
    except (OSError, ValueError, KeyError, TypeError, RuntimeError):
        valid = False
    return doc, valid


def triplet_audit(item):
    folder = Path(item['path'])
    audit = base.triplet_audit(folder, item['map'], item['run'], item['phase'] == 'preflight',
                              CANDIDATE, item['modes'], True)
    checks = dict(audit['acceptance_checks'])
    child_plan = base.load_document(folder / 'plan.json')
    expected_mission = item.get('mission', {})
    checks['mission_binding'] = (bool(expected_mission)
        and child_plan.get('scenario7_mission') == expected_mission)
    contacts = {}
    for mode in MODES:
        native = base.load_document(folder / 'artifacts' / f"{item['map']}_run{item['run']}_{mode}.json")
        count_goals = expected_mission.get('goal_count')
        reached = native.get('waypoints_reached')
        checks[mode+':mission_goal_count'] = (type(count_goals) is int and count_goals > 0
            and type(native.get('n_waypoints')) is int and native['n_waypoints'] == count_goals
            and type(reached) is int and 0 <= reached <= count_goals
            and (native.get('success') is not True or reached == count_goals))
        doc, valid = contact_evidence(contact_file(folder, item['map'], item['run'], mode), item['map'])
        contacts[mode] = doc
        checks[mode+':solid_contact_evidence'] = valid
        count = previous.contact_count(doc) if valid else None
        outcome = audit['outcomes'][mode]
        outcome['analytic_contact_episodes'] = count
        outcome['safe_complete'] = outcome.get('success') is True and valid and count == 0
        if count is None or count > 0 or outcome.get('success') is not True:
            audit['outcome_failures'][mode] = dict(outcome)
        if mode in ('full', 'adaptive'):
            checks[mode+':solid_zero_contact'] = valid and count == 0
    audit.update(schema='scenario7-triplet-v1', solid_contacts=contacts,
                 acceptance_checks=checks, valid=base.explicit_true_checks(checks))
    return audit


def phase_gate(commands, phase, maps):
    planned = [c for c in commands if c['phase'] == phase]
    expected = {(m, r, mode) for m in maps for r in range(1, COUNTS[phase]+1) for mode in MODES}
    actual = [(c['map'], c['repeat'], m) for c in planned for m in c['modes']]
    identities = [(c['map'], c['run'], m) for c in planned for m in c['modes']]
    records = []
    for item in planned:
        fresh = triplet_audit(item)
        stored = base.load_document(Path(item['path']) / 'triplet_verification.json')
        records.append(dict(name=item['name'], valid=fresh.get('valid') is True and stored == fresh))
    checks = dict(exact_coverage=len(actual) == len(expected) and set(actual) == expected,
                  unique_identities=len(identities) == len(set(identities)),
                  fresh_stored_audits_pass=bool(records) and all(r['valid'] for r in records))
    return dict(valid=base.explicit_true_checks(checks), phase=phase, checks=checks,
                expected_flights=len(expected), records=records)


def source_transitions(summary, mode):
    if mode != 'adaptive':
        return None
    source = summary.get('source_acquisition', {})
    frames = source.get('frames')
    if not isinstance(frames, list) or len(frames) < 2:
        return None
    if any(type(f.get('full')) is not int or f['full'] not in (0, 1) for f in frames):
        return None
    identifiers = [f.get('frame') for f in frames]
    if any(type(n) is not int for n in identifiers) or any(b != a+1 for a, b in zip(identifiers, identifiers[1:])):
        return None
    return sum(a['full'] == 0 and b['full'] == 1 for a, b in zip(frames, frames[1:]))


METRICS = {
    'mission_time_s': 'mission_time_s', 'cpu_cores': 'end_to_end_cpu_cores_mean',
    'cpu_core_s': 'end_to_end_cpu_core_s', 'input_mib_s': 'map_payload_mib_s',
    'input_mib_per_run': 'input_mib_per_run', 'map_ms': 'total_ms_mean',
    'host_cpu_pct': 'host_cpu_pct', 'full_transitions': 'full_transitions',
    'certified_recoveries': 'certified_recoveries',
}


def observations(root):
    result = []
    for raw_path in sorted((root / 'test10').rglob('raw.csv')):
        with raw_path.open(newline='') as stream:
            rows = list(csv.DictReader(stream))
        identities = [(r.get('map'), r.get('run'), r.get('mode')) for r in rows]
        for row in rows:
            name, mode, run = row.get('map'), row.get('mode'), row.get('run')
            if name not in MAPS or mode not in MODES:
                continue
            summary = base.load_document(raw_path.parent / f'{mode}_summary.json')
            doc, contact_known = contact_evidence(contact_file(raw_path.parent, name, run, mode), name)
            duration = base.number(row.get('cgroup_cpu_duration_s'))
            unique = identities.count((name, run, mode)) == 1
            costs_valid = (unique and not (raw_path.parent / 'diagnostic_contamination.json').exists()
                and all(base.boolean(row.get(k)) is True for k in ('run_valid', 'resource_valid', 'speed_limit_valid'))
                and base.boolean(row.get('infrastructure_failure')) is False
                and base.number(row.get('attempt_count')) == 1 and base.number(row.get('retry_count')) == 0
                and duration is not None and duration > 0)
            payload = base.number(row.get('map_payload_bytes_total'))
            cycles = summary.get('strict_recovery_audit', {}).get('completed_cycles')
            count = previous.contact_count(doc) if contact_known else None
            result.append(dict(row, contact_known=contact_known, analytic_contact_episodes=count,
                safe_complete=contact_known and count == 0 and base.boolean(row.get('success')) is True,
                costs_valid=costs_valid, host_cpu_pct=summary.get('host_cpu_pct', {}).get('mean'),
                input_mib_per_run=payload / 2**20 if payload is not None else None,
                full_transitions=source_transitions(summary, mode),
                certified_recoveries=len(cycles) if isinstance(cycles, list) else None,
                raw_source=str(raw_path)))
    return result


def summarize_rows(rows, label, name, mode, planned):
    known = [r for r in rows if r['contact_known']]
    row = dict(map_label=label, map=name, mode=mode, planned=planned, recorded_runs=len(rows),
        goal_reached=sum(base.boolean(r.get('success')) is True for r in rows),
        safe_completed=sum(r['safe_complete'] for r in rows),
        contact_known_runs=len(known), contact_unknown_runs=len(rows)-len(known),
        contact_runs=sum(r['analytic_contact_episodes'] > 0 for r in known),
        contact_episodes=sum(r['analytic_contact_episodes'] for r in known) if known else None,
        performance_valid_runs=sum(r['costs_valid'] for r in rows))
    row['goal_reached_pct_observed'] = 100 * row['goal_reached'] / len(rows) if rows else None
    row['safe_completed_pct_observed'] = 100 * row['safe_completed'] / len(rows) if rows else None
    for prefix, key in METRICS.items():
        values = [base.number(r.get(key)) for r in rows if r['costs_valid'] or prefix in ('full_transitions', 'certified_recoveries')]
        values = [n for n in values if n is not None]
        row.update({prefix+'_n': len(values), prefix+'_mean': statistics.mean(values) if values else None,
                    prefix+'_sd': statistics.stdev(values) if len(values) > 1 else None})
        if prefix in ('full_transitions', 'certified_recoveries'):
            row[prefix+'_total'] = sum(values) if values else None
    return row


REPORT_GROUP_MAPS = {'normal': MAPS[:5], 'urban': (MAPS[5],), 'forest': (MAPS[6],)}
REPORT_GROUP_LABELS = {'normal': 'Normal (G1–G4, G5-R2)', 'urban': 'Urban', 'forest': 'Forest'}


def report_groups(maps=MAPS):
    maps = selected_maps(maps)
    return {group: tuple(name for name in members if name in maps)
            for group, members in REPORT_GROUP_MAPS.items() if any(name in maps for name in members)}


def grouped_rows(records, maps=MAPS):
    """Pool observed trials only within one scenario group and one mode."""
    result = []
    for group, members in report_groups(maps).items():
        for mode in MODES:
            selected = [r for r in records if r['map'] in members and r['mode'] == mode]
            row = summarize_rows(selected, REPORT_GROUP_LABELS[group], group, mode, 10 * len(members))
            row.update(group=group, maps_in_group=';'.join(members),
                aggregation_scope='observed_trials_within_group_and_mode',
                cost_weighting='arithmetic_mean_of_valid_observed_trials_not_equal_map_weighting',
                recorded_runs_by_map=json.dumps({name: sum(r['map'] == name for r in selected)
                                                for name in members}, sort_keys=True),
                performance_valid_runs_by_map=json.dumps({name: sum(r['map'] == name and r['costs_valid']
                                                                   for r in selected)
                                                         for name in members}, sort_keys=True))
            result.append(row)
    add_reductions(result, scope_key='group')
    return result


def add_reductions(rows, scope_key='map'):
    for row in rows:
        full = next((r for r in rows if r[scope_key] == row[scope_key] and r['mode'] == 'full'), None)
        for metric in ('cpu_cores', 'cpu_core_s', 'input_mib_s', 'input_mib_per_run', 'map_ms'):
            f, v = full[metric+'_mean'] if full else None, row[metric+'_mean']
            row[metric+'_reduction_vs_full_pct'] = 100 * (1-v/f) if f and v is not None else None


def write_csv(path, rows):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def fmt(value, digits=2):
    return 'N/A' if value is None else f'{value:.{digits}f}'


def _group_metric(row, metric, digits=2):
    return f"{fmt(row[metric+'_mean'], digits)} ± {fmt(row[metric+'_sd'], digits)} [n={row[metric+'_n']}]"


def write_group_markdown(root, rows, maps):
    lines = ['# Scenario-group results', '',
        '본시험은 normal(G1–G4, G5-R2), urban, forest를 각각 집계한다. 세 그룹을 합친 평균은 만들지 않는다.',
        'Normal은 선택된 normal 맵의 관측 회차를 합친다. 비용 평균은 유효 회차의 산술평균이며, 맵별 관측 수가 다르면 맵 균등 평균이 아니다.',
        '각 값은 평균 ± 표본 표준편차 [n]다. 표본이 없으면 N/A, n=1의 표준편차도 N/A다. 누락 회차와 누락 지표를 0으로 채우지 않는다.',
        '경유점 도달·접촉·실패 결과는 비용 유효 여부와 별도로 보존한다. profiler ON 예비주행은 본시험 평균에 포함하지 않는다.',
        'Full 대비 감소율은 같은 그룹의 Full 평균을 기준으로 한다. detailed report는 report_test10/{normal,urban,forest}, report_preflight/{normal,urban,forest}에 분리한다.',
        'summary_overall.csv는 summary_by_group.csv의 호환용 별칭이며 동일한 그룹별 행을 가진다.', '']
    for group, members in report_groups(maps).items():
        lines.append(f"- {group}: {', '.join(support.MAP_LABELS[name] for name in members)}; 모드별 계획 {10*len(members)}회")
    lines += ['', '| 그룹 | 모드 | 기록/계획 | 경유점 도달 | 무접촉 완주 | 접촉 주행/확인 | 미확인 | 비용 유효 회차 |',
              '|---|---|---:|---:|---:|---:|---:|---:|']
    for row in rows:
        lines.append(f"| {row['group']} | {row['mode']} | {row['recorded_runs']}/{row['planned']} | {row['goal_reached']} | {row['safe_completed']} | {row['contact_runs']}/{row['contact_known_runs']} | {row['contact_unknown_runs']} | {row['performance_valid_runs']} |")
    lines += ['', '| 그룹 | 모드 | 시간(s) | CPU(cores) | CPU(core-s/run) | 입력(MiB/s) | 입력(MiB/run) | 맵(ms/frame) | CPU 감소(%) | 입력률 감소(%) |',
              '|---|---|---|---|---|---|---|---|---:|---:|']
    for row in rows:
        values = [_group_metric(row, metric, 3 if metric in ('cpu_cores', 'input_mib_s') else 2)
                  for metric in ('mission_time_s', 'cpu_cores', 'cpu_core_s', 'input_mib_s', 'input_mib_per_run', 'map_ms')]
        lines.append(f"| {row['group']} | {row['mode']} | " + ' | '.join(values)
                     + f" | {fmt(row['cpu_cores_reduction_vs_full_pct'])} | {fmt(row['input_mib_s_reduction_vs_full_pct'])} |")
    lines += ['', '맵별 기록 수와 비용 유효 수는 CSV의 recorded_runs_by_map / performance_valid_runs_by_map에 기록한다.',
              'Full 전환 및 복구 횟수는 유효한 해당 관측값의 n·합계·평균·표준편차를 별도로 제공하며, 비용 유효성으로 관측된 사건을 지우지 않는다.']
    (root / 'summary_by_group.md').write_text('\n'.join(lines) + '\n')


def write_progress(root, maps=MAPS):
    maps = selected_maps(maps)
    records = observations(root)
    rows = [summarize_rows([r for r in records if r['map'] == name and r['mode'] == mode],
                          support.MAP_LABELS[name], name, mode, 10) for name in maps for mode in MODES]
    add_reductions(rows)
    write_csv(root / 'summary_by_map.csv', rows)
    pooled = grouped_rows(records, maps)
    write_csv(root / 'summary_by_group.csv', pooled)
    write_csv(root / 'summary_overall.csv', pooled)
    write_group_markdown(root, pooled, maps)
    lines = ['# Seven-map n10 results', '',
        f'본시험만 집계: {len(maps)}개 맵 × 3모드 × 10회 = {30*len(maps)}회. profiler ON 예비주행은 별도.',
        '경유점 도달과 무접촉 완주를 분리한다. 접촉 미확인은 안전0회가 아니다. 접촉은 수신 pose 표본의 기체 구-고체 교차다.',
        'CPU는 실험 cgroup(시뮬레이터 포함, 외부 관측기 제외). 입력량은 논리 payload. 맵 시간은 경과시간.',
        '각 비용은 유효한 회차의 산술평균이며 미완주 비용도 원본에 보존한다. 세부 표본수·표준편차·감소율은 CSV 참고.', '',
        '| 맵 | 모드 | 기록/목표 | 경유점 도달 | 무접촉 완주 | 접촉 주행/확인 | 미확인 | 시간(s) | CPU(cores) | CPU(core-s/run) | 입력(MiB/s) | 입력(MiB/run) | 맵(ms/frame) | Full전환 합계 |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        lines.append(f"| {r['map_label']} | {r['mode']} | {r['recorded_runs']}/{r['planned']} | {r['goal_reached']} | {r['safe_completed']} | {r['contact_runs']}/{r['contact_known_runs']} | {r['contact_unknown_runs']} | {fmt(r['mission_time_s_mean'])} | {fmt(r['cpu_cores_mean'],3)} | {fmt(r['cpu_core_s_mean'])} | {fmt(r['input_mib_s_mean'],3)} | {fmt(r['input_mib_per_run_mean'])} | {fmt(r['map_ms_mean'])} | {fmt(r['full_transitions_total'],0)} |")
    lines += ['', 'Full전환은 실제 source frame의 Sector→Full 관측 edge 수이며 초기 Full 상태는 전환으로 세지 않는다.',
              'report_test10/{normal,urban,forest}에는 그룹별 GPU/메모리/수신주파수/계측 상세를 저장한다. 그 legacy 접촉값은 sampled-PCD 보조 지표다.',
              'summary_by_group.csv/.md는 normal·urban·forest를 분리 집계한다. summary_overall.csv도 동일한 그룹별 행의 별칭이다. 7개 맵 전체 평균은 만들지 않는다.',
              'Normal 비용은 관측된 유효 회차의 산술평균이며 맵별 표본수가 다르면 맵 균등 평균과 다를 수 있다.']
    (root / 'summary_by_map.md').write_text('\n'.join(lines)+'\n')
    transitions = [{k: r[k] for k in ('map_label', 'map', 'mode', 'recorded_runs', 'full_transitions_n',
                    'full_transitions_total', 'full_transitions_mean', 'full_transitions_sd',
                    'certified_recoveries_total')} for r in rows if r['mode'] == 'adaptive']
    write_csv(root / 'adaptive_transitions_by_map.csv', transitions)
    return rows


def _group_report_load_runs(campaign_roots, repo, members):
    runs, warnings = previous.report_load_runs(campaign_roots, repo)
    if any(run.get('map') not in members for run in runs):
        raise ValueError('Detailed report contains a map outside its selected scenario group')
    return runs, warnings


def reports(root, maps=MAPS):
    maps = selected_maps(maps)
    write_progress(root, maps)
    records = []
    for phase in PHASES:
        for group, members in report_groups(maps).items():
            campaign_roots = [root / phase / name for name in members]
            output = root / ('report_' + phase) / group
            record = dict(phase=phase, group=group, maps=list(members), output=str(output))
            if not any(path for folder in campaign_roots for path in folder.rglob('raw.csv')):
                records.append(dict(record, state='NO_RAW_ROWS'))
                continue
            original_fp, original_load = base.reports.protocol_fingerprint, base.reports.load_runs
            try:
                base.reports.protocol_fingerprint = previous.report_protocol_fingerprint
                base.reports.load_runs = lambda roots, repo, members=members: _group_report_load_runs(roots, repo, members)
                arguments = [argument for folder in campaign_roots for argument in ('--campaign', str(folder))]
                base.reports.main([*arguments, '--output', str(output)])
                records.append(dict(record, state='WRITTEN'))
            except (Exception, SystemExit) as exc:
                records.append(dict(record, state='REPORT_ERROR', error=repr(exc)))
            finally:
                base.reports.protocol_fingerprint, base.reports.load_runs = original_fp, original_load
    base.save(root / 'report_status.json', dict(reports=records))
    return records


def freeze_sources(root, admission):
    frozen, prior = previous.freeze_sources(root)
    for name, digest in admission['assets_sha256'].items():
        if base.sha(name) != digest:
            raise RuntimeError('Scenario map evidence changed: '+name)
        base.freeze_files(frozen, [Path(name)])
    mission_admission = missions.validate_missions()
    if mission_admission.get('valid') is not True:
        raise RuntimeError('Mission registry admission failed')
    for name, digest in mission_admission['assets_sha256'].items():
        if base.sha(name) != digest:
            raise RuntimeError('Scenario mission evidence changed: '+name)
        base.freeze_files(frozen, [Path(name)])
    paths = [PROTOCOL, support.MANIFEST, *SCRIPTS.glob('*scenario7*.py'), SCRIPTS / 'run_scenario7_n10.sh',
             REPO / 'scripts/native_campaign/run_scenario7_n10.sh',
             *(REPO / 'super_patches/native_seedmap_campaign/perfect_drone_sim_scripts').glob('*scenario7*'),
             *(SCRIPTS.parent / 'test').glob('test*scenario7*.py')]
    base.freeze_files(frozen, paths)
    return frozen, dict(prior, scenario7=admission, scenario7_missions=mission_admission,
                        no_planner_algorithm_change=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--maps', nargs='+', choices=MAPS, default=list(MAPS))
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--report', type=Path)
    parser.add_argument('--continue-after-failure', action='store_true',
                        help='Retain failed/contact/incomplete/invalid attempts and advance scheduled triplets')
    args = parser.parse_args(argv)
    try:
        maps = selected_maps(args.maps)
    except ValueError as exc:
        parser.error(str(exc))
    if args.report:
        if args.output or args.dry_run:
            parser.error('--report cannot be combined with --output or --dry-run')
        plan = base.load_document(args.report / 'plan.json')
        if plan.get('schema') != SCHEMA:
            parser.error('Not a scenario7-n10 campaign directory')
        reports(args.report.resolve(), selected_maps(plan['maps']))
        return 0
    root = (args.output or REPO / 'results' / ('scenario7_n10_'+datetime.now().strftime('%Y%m%d_%H%M%S')+f'_{os.getpid()}')).resolve()
    if root.exists():
        parser.error('Existing output refused; earlier experiments are never overwritten or resumed')
    if any(k.startswith('SUPER_') and k not in ('SUPER_CPU_PROFILE', 'SUPER_CALLBACK_TRACE') for k in os.environ):
        parser.error('Unexpected inherited SUPER_* overrides; use a clean campaign terminal')
    # Share the existing manual-suite lock so old and new suites cannot overlap.
    lock = open('/tmp/super_sector_filter_gapfree_n5.lock', 'a')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        parser.error('Another gapfree/scenario7 campaign is running')
    root.mkdir(parents=True, exist_ok=False)
    logfile = (root / 'controller.log').open('x')
    original_stdout, original_stderr = sys.stdout, sys.stderr
    class Tee:
        def __init__(self, stream): self.stream = stream
        def write(self, value):
            self.stream.write(value)
            result = logfile.write(value)
            logfile.flush()
            return result
        def flush(self): self.stream.flush(); logfile.flush()
    sys.stdout, sys.stderr = Tee(original_stdout), Tee(original_stderr)
    started, history, current, frozen = time.monotonic(), [], None, {}
    env = dict(os.environ, SUPER_CPU_PROFILE='0', SUPER_CALLBACK_TRACE='0')
    def status(state, **extra):
        base.save(root / 'status.json', dict(state=state, pid=os.getpid(), current=current, completed=history,
            requested_off_flights=30*len(maps), requested_on_flights=3*len(maps),
            automatic_retry=False, continue_after_failure=args.continue_after_failure,
            elapsed_s=time.monotonic()-started, updated_local=datetime.now().astimezone().isoformat(), **extra))
    def interrupted(signum, _frame):
        raise InterruptedError('Interrupted by signal '+str(signum))
    handlers = {sig: signal.signal(sig, interrupted) for sig in (signal.SIGINT, signal.SIGTERM)}
    def safe_reports():
        try:
            return reports(root, maps)
        except Exception as exc:
            base.save(root / 'report_error.json', dict(error=repr(exc)))
            return [dict(phase='all', state='REPORT_ERROR', error=repr(exc))]
    try:
        print('RESULT DIRECTORY:', root, flush=True)
        status('PREPARING')
        admission = support.register_maps()
        frozen, provenance = freeze_sources(root, admission)
        base.save(root / 'admission.json', provenance)
        commands = build_plan(root, maps)
        selected_missions = {name: mission_runtime.mission_binding(missions.mission_context(name))
                             for name in maps}
        phase_plan_paths = []
        for phase in PHASES:
            phase_plan = dict(maps=list(maps), phase=phase,
                independent_cohort=True, parent_plan=str(root / 'plan.json'),
                missions=selected_missions, aggregation=aggregation_policy(maps),
                profile_preflight_runs_per_mode=1 if phase == 'preflight' else 0,
                unprofiled_runs_per_mode=10 if phase == 'test10' else 0)
            path = root / phase / 'plan.json'
            base.save(path, phase_plan)
            phase_plan_paths.append(path)
            for name in maps:
                path = root / phase / name / 'plan.json'
                base.save(path, dict(phase_plan, map=name, maps=[name],
                    missions={name: selected_missions[name]}, aggregation=aggregation_policy((name,))))
                phase_plan_paths.append(path)
        base.save(root / 'plan.json', dict(schema=SCHEMA, maps=list(maps), modes=list(MODES),
            map_labels={m: support.MAP_LABELS[m] for m in maps}, candidate=CANDIDATE, commands=commands,
            missions=selected_missions, aggregation=aggregation_policy(maps),
            profiled_preflight_flights=3*len(maps), unprofiled_primary_flights=30*len(maps),
            no_retry=True, no_replacement=True, all_failures_retained=True, old_cohorts_not_pooled=True,
            continue_after_failure=args.continue_after_failure,
            primary_contact_scope='Received-pose sphere intersections with solid cylinders/boxes; not swept proof',
            completion_definition='goal_reached; safe_complete additionally requires known zero solid contact',
            frozen_sha256=frozen))
        base.freeze_files(frozen, [root / 'plan.json', root / 'admission.json', *phase_plan_paths])
        base.save(root / 'frozen_inputs_and_evidence.json', frozen)
        write_progress(root, maps)
        if args.dry_run:
            status('DRY_RUN_ONLY', actual_flights_started=0, planned_flights=33*len(maps))
            print(f'DRY RUN PASS: independent ON{3*len(maps)} + primary OFF{30*len(maps)}; no ROS launched', flush=True)
            return 0
        previous_phase = 'static'
        for item in commands:
            current = {k: v for k, v in item.items() if k != 'command'}
            changed = base.changed_inputs(frozen)
            if changed:
                raise RuntimeError('Frozen source/map/evidence changed: '+repr(changed))
            if item['phase'] != previous_phase:
                try:
                    if previous_phase == 'static':
                        checks = {m: base.static.validate_manifest(root/'static_preflight'/m/'acceptance.json', base.static.map_context(m)) for m in maps}
                        gate = dict(valid=all(v.get('valid') is True for v in checks.values()), checks=checks)
                    else:
                        gate = phase_gate(commands, previous_phase, maps)
                        safe_reports()
                except Exception as exc:
                    gate = dict(valid=False, error=repr(exc))
                base.save(root / (previous_phase+'_gate.json'), gate)
                if not gate['valid'] and not args.continue_after_failure:
                    raise RuntimeError(previous_phase+' gate failed; evidence preserved')
                previous_phase = item['phase']
            status('RUNNING')
            print('START', item['name'], flush=True)
            entry = dict(name=item['name'], phase=item['phase'], map=item['map'], returncode=None)
            history.append(entry)
            try:
                with contextlib.ExitStack() as stack:
                    if item['phase'] == 'static':
                        common = stack.enter_context(open(base.event.diagnostic.search.campaign.LOCK_PATH, 'a'))
                        fcntl.flock(common, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    entry['returncode'] = base.execute(item, root, env)
                evidence = []
                if 'path' in item:
                    folder = Path(item['path'])
                    audit = triplet_audit(item)
                    base.save(folder / 'triplet_verification.json', audit)
                    entry.update(valid=audit['valid'], outcome_failures=audit['outcome_failures'])
                    if item['phase'] == 'preflight':
                        base.save(folder / 'thread_cpu_summary.json', {m: base.stages.summarize(folder, m, item['run'], item['map'])
                                  for m in MODES if (folder / f'{m}_summary.json').is_file()})
                    evidence = [folder/'plan.json', folder/'raw.csv', folder/'status.json', folder/'triplet_verification.json',
                        *(folder/f'{m}_summary.json' for m in MODES),
                        *(contact_file(folder,item['map'],item['run'],m) for m in MODES),
                        *(folder/'artifacts'/f"{item['map']}_run{item['run']}_{m}.attempt1.odometry.csv" for m in MODES)]
                elif item['name'].startswith('accept_'):
                    path = root / 'static_preflight' / item['map'] / 'acceptance.json'
                    audit = base.static.validate_manifest(path, base.static.map_context(item['map']))
                    entry['valid'] = audit.get('valid') is True
                    evidence = [path, *map(Path, audit.get('evidence_sha256', {}))]
                else:
                    entry['valid'] = entry['returncode'] == 0
                base.freeze_files(frozen, [p for p in evidence if p.is_file()])
                if (entry['returncode'] or not entry['valid']) and not args.continue_after_failure:
                    raise RuntimeError('Step failed: '+item['name'])
            except InterruptedError:
                raise
            except Exception as exc:
                entry.update(valid=False, execution_error=repr(exc),
                             diagnostic_contaminated=isinstance(exc, base.MemoryRunawayError))
                if not args.continue_after_failure:
                    raise
            try:
                write_progress(root, maps)
            except Exception as exc:
                entry['progress_error'] = repr(exc)
                if not args.continue_after_failure:
                    raise
            base.save(root / 'frozen_inputs_and_evidence.json', frozen)
            print('FINISH', json.dumps(entry), flush=True)
            status('RUNNING')
        try:
            gate = phase_gate(commands, 'test10', maps)
        except Exception as exc:
            gate = dict(valid=False, error=repr(exc))
        base.save(root / 'test10_gate.json', gate)
        changed = base.changed_inputs(frozen)
        if changed:
            raise RuntimeError('Frozen evidence changed: '+repr(changed))
        report_records = safe_reports()
        retained = (not gate['valid'] or any(r['state'] != 'WRITTEN' for r in report_records)
                    or any(e.get('valid') is not True or e.get('returncode') != 0
                           or bool(e.get('outcome_failures')) for e in history))
        status('COMPLETE_WITH_RETAINED_FAILURES' if retained else 'COMPLETE', retained_failures=retained,
               scheduled_off_flights=30*len(maps), recorded_off_rows=len(observations(root)))
        print('FINISHED:', root / 'summary_by_map.md', flush=True)
        return 0
    except BaseException as exc:
        status('STOPPED_FOR_DIAGNOSIS', error=repr(exc))
        safe_reports()
        print('STOPPED; preserved results:', root, repr(exc), file=sys.stderr, flush=True)
        raise
    finally:
        for sig, handler in handlers.items():
            signal.signal(sig, handler)
        lock.close()
        sys.stdout, sys.stderr = original_stdout, original_stderr
        logfile.close()


if __name__ == '__main__':
    raise SystemExit(main())
