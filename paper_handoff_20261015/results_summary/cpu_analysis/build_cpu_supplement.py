#!/usr/bin/env python3
"""Derive an auditable CPU supplement from the existing frozen 210 flights.

No simulation, runtime change, outcome change, or write to original evidence.
The additional functional CPU metric is a measured exclusive-stage SUBTOTAL,
not complete autonomy CPU, and uses a shorter in-flight profile window.
"""

import argparse
import collections
import csv
import datetime
import hashlib
import importlib
import json
import math
from pathlib import Path
import statistics
import sys

sys.dont_write_bytecode = True

DEFAULT_PACKAGE = Path('/root/share/codex_final_results_20261014_all')
TOOLS = Path('/root/super-sector-filter/scripts/native_campaign')
MODES = ('full', 'sector', 'adaptive')
BUCKET_FIELDS = {
    'autonomy_measured_subtotal': 'instrumented_autonomy',
    'simulator_sensor_measured': 'instrumented_simulator',
    'diagnostic_visualization_measured': 'instrumented_diagnostic',
    'unclassified_measured': 'instrumented_unclassified',
}
IDENTITY_FIELDS = ('map', 'map_label', 'environment', 'mode', 'mode_label',
                   'run', 'repeat', 'stage')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def read_csv(path):
    with Path(path).open(newline='') as stream:
        return list(csv.DictReader(stream))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def write_csv(path, rows, fields=None):
    if fields is None:
        fields = list(dict.fromkeys(key for row in rows for key in row))
    with Path(path).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def same(actual, expected, label):
    require(math.isclose(float(actual), float(expected), rel_tol=1e-11,
                         abs_tol=1e-11), f'{label}: {actual} != {expected}')


def identity(raw):
    out = {key: raw[key] for key in IDENTITY_FIELDS}
    out['run'] = int(out['run'])
    out['repeat'] = int(out['repeat'])
    out['flight_id'] = '/'.join(str(out[key]) for key in
                              ('stage', 'map', 'repeat', 'mode'))
    return out


def verify_source(path, manifest, evidence, kind):
    path = Path(path)
    manifest_key = str(path.resolve())
    expected = manifest.get(manifest_key)
    require(expected is not None, f'Not in frozen manifest: {path}')
    actual = sha(path)
    require(actual == expected, f'Frozen source hash mismatch: {path}')
    item = dict(kind=kind, path=str(path), manifest_key=manifest_key,
                sha256=actual, expected_sha256=expected, verified=True)
    evidence.append(item)
    return item


def quantile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    offset = (len(ordered) - 1) * fraction
    lo = math.floor(offset)
    hi = math.ceil(offset)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (offset - lo)


def stats(values):
    values = [float(x) for x in values if x is not None]
    require(all(math.isfinite(x) for x in values), 'Non-finite summary input')
    if not values:
        return dict(n=0, mean=None, median=None, sd_sample=None, minimum=None,
                    maximum=None, p05=None, p95=None, sum=None)
    return dict(n=len(values), mean=statistics.mean(values),
                median=statistics.median(values),
                sd_sample=statistics.stdev(values) if len(values) > 1 else None,
                minimum=min(values), maximum=max(values),
                p05=quantile(values, 0.05), p95=quantile(values, 0.95),
                sum=math.fsum(values))


METRICS = (
    'experiment_cpu_mean_cores', 'experiment_cpu_core_s',
    'instrumented_autonomy_mean_cores', 'instrumented_autonomy_cpu_core_s',
    'instrumented_simulator_mean_cores', 'instrumented_simulator_cpu_core_s',
    'instrumented_diagnostic_mean_cores', 'instrumented_diagnostic_cpu_core_s',
    'instrumented_unclassified_mean_cores', 'instrumented_unclassified_cpu_core_s',
    'instrumented_total_mean_cores', 'instrumented_total_cpu_core_s',
    'profile_duration_s', 'telemetry_flight_span_s', 'profile_coverage_fraction',
    'cropped_start_s', 'cropped_end_s', 'mission_time_s', 'cgroup_cpu_duration_s',
)


def summarize_runs(runs, group_field):
    result = []
    for group_name in sorted({row[group_field] for row in runs}):
        for mode in MODES:
            selected = [r for r in runs if r[group_field] == group_name and r['mode'] == mode]
            out = dict(grouping=group_field, group=group_name, mode=mode,
                       n_runs=len(selected), n_profile_available=sum(r['profile_available'] for r in selected))
            for metric in METRICS:
                for statistic, value in stats([r[metric] for r in selected]).items():
                    out[f'{metric}_{statistic}'] = value
            result.append(out)
    return result


def paired_reductions(runs):
    result = []
    for group_field in ('map_label', 'environment'):
        for group_name in sorted({r[group_field] for r in runs}):
            selected = [r for r in runs if r[group_field] == group_name]
            full = {(r['stage'], r['map'], r['repeat']): r for r in selected if r['mode'] == 'full'}
            for mode in ('sector', 'adaptive'):
                other = {(r['stage'], r['map'], r['repeat']): r for r in selected if r['mode'] == mode}
                require(full.keys() == other.keys(), 'Unpaired mode identities')
                keys = sorted(full)
                for scope, scope_metrics, window in (
                        ('experiment_including_simulator',
                         ('experiment_cpu_mean_cores', 'experiment_cpu_core_s'), 'original_cgroup_window'),
                        ('instrumented_functional_subtotal_excluding_simulator',
                         ('instrumented_autonomy_mean_cores', 'instrumented_autonomy_cpu_core_s'),
                         'in_flight_common_profile_report_window')):
                    for metric in scope_metrics:
                        baseline = [full[k][metric] for k in keys]
                        comparison = [other[k][metric] for k in keys]
                        require(all(x is not None and x > 0 for x in baseline), 'Invalid Full baseline')
                        require(all(x is not None and x >= 0 for x in comparison), 'Unavailable comparison')
                        mean_full = statistics.mean(baseline)
                        mean_other = statistics.mean(comparison)
                        out = dict(grouping=group_field, group=group_name, comparison_mode=mode,
                                   baseline_mode='full', scope=scope, metric=metric,
                                   window=window, matched_pairs=len(keys),
                                   missing_pairs=0, full_mean=mean_full,
                                   comparison_mean=mean_other,
                                   ratio_of_means_reduction_pct=100 * (1 - mean_other / mean_full))
                        for label, values in (
                                ('paired_absolute_difference', [b - a for a, b in zip(baseline, comparison)]),
                                ('paired_reduction_pct', [100 * (1 - b / a) for a, b in zip(baseline, comparison)])):
                            for key, value in stats(values).items():
                                out[f'{label}_{key}'] = value
                        result.append(out)
    return result


def build(package, output):
    data = package / 'data'
    require(output.name == 'cpu_analysis', 'Output must be named cpu_analysis')
    require(output.parent == package, 'Output must be inside the new supplement package')
    require(package != Path('/root/share/codex_final_results_20261014'),
            'Never write the original package')
    output.mkdir(parents=True, exist_ok=True)
    source_table = data / '04_run_level_210.csv'
    source_table_sha = sha(source_table)
    frozen_manifest_path = data / 'source_frozen/source_manifest.json'
    frozen_manifest = read_json(frozen_manifest_path)['sha256']
    originals = read_csv(source_table)
    require(len(originals) == 210, 'Expected precisely 210 frozen main flights')
    require(collections.Counter(r['mode'] for r in originals) == dict(full=70, sector=70, adaptive=70),
            'Expected 70 runs per mode')
    require(len({identity(r)['flight_id'] for r in originals}) == 210, 'Duplicate identity')

    sys.path.insert(0, str(TOOLS))
    profile = importlib.import_module('analyze_thread_cpu_profile')
    attribution = importlib.import_module('summarize_cpu_attribution')
    evidence = []
    verify_source(TOOLS / 'analyze_thread_cpu_profile.py', frozen_manifest,
                  evidence, 'frozen_pure_profile_analyzer')
    category_hash = sha(TOOLS / 'summarize_cpu_attribution.py')
    runs, raw_reports, raw_roles, role_cpu, run_details = [], [], [], [], []
    stage_universe = set()
    profile_line_count = role_line_count = 0
    for index, raw in enumerate(originals):
        ident = identity(raw)
        folder = Path(raw['raw_file']).parent
        stem = f'{raw["map"]}_run{raw["run"]}_{raw["mode"]}.attempt1'
        log_path = folder / 'artifacts' / f'{stem}.stack.log'
        log_evidence = verify_source(log_path, frozen_manifest, evidence, 'actual_attempt1_stack_log')
        require(log_evidence['sha256'] == raw['stack_sha256'], 'Frozen row stack hash differs')
        raw_evidence = verify_source(folder / 'raw.csv', frozen_manifest, evidence, 'original_raw_csv')
        require(raw_evidence['sha256'] == raw['raw_sha256'], 'Frozen row raw hash differs')
        telemetry_path = folder / 'telemetry.jsonl'
        verify_source(telemetry_path, frozen_manifest, evidence, 'original_telemetry')
        summary_path = folder / f'{raw["mode"]}_summary.json'
        verify_source(summary_path, frozen_manifest, evidence, 'original_mode_summary')
        summary = read_json(summary_path)
        require(summary.get('cpu_profile') is True, 'Missing enabled profiling flag')
        telemetry = [json.loads(line) for line in telemetry_path.read_text().splitlines()]
        active = [r['monotonic_s'] for r in telemetry if r.get('mode') == raw['mode'] and r.get('campaign_active')]
        require(len(active) >= 2 and all(math.isfinite(x) for x in active), 'Invalid telemetry flight window')
        flight_start, flight_end = min(active), max(active)
        require(flight_end > flight_start, 'Empty telemetry flight window')
        derived = profile.summarize(folder, raw['mode'], int(raw['run']), raw['map'])
        require(derived.get('available') and len(derived['processes']) == 1,
                'Expected exactly one available composed profile process')
        process = derived['processes'][0]
        pid = process['pid']
        start, end = process['first_report_monotonic_s'], process['last_report_monotonic_s']
        duration = process['duration_s']
        require(duration > 0 and flight_start <= start < end <= flight_end,
                'Profile window is not within flight')
        stages = {s['stage']: s for s in process['stages']}
        require(len(stages) == len(process['stages']), 'Duplicate derived stage')
        required = attribution.required_stages(raw['mode'])
        require(required <= stages.keys(), 'Missing required instrumentation scopes')
        parsed_reports = collections.defaultdict(dict)
        roles_for_run = []
        line_report_count = line_role_count = 0
        log = log_path.read_text(errors='replace')
        for line_number, line in enumerate(log.splitlines(), 1):
            if '[THREAD_CPU_PROFILE]' in line:
                profile_line_count += 1
                line_report_count += 1
                match = profile.PATTERN.search(line)
                require(match is not None, f'Malformed raw profile record: {log_path}:{line_number}')
                process_id, ns, final, stage, calls, inclusive, exclusive, errors = match.groups()
                process_id, ns, calls, errors = map(int, (process_id, ns, calls, errors))
                inclusive, exclusive = float(inclusive), float(exclusive)
                require(errors == 0, 'Raw profile clock errors')
                require(process_id == pid, 'Unexpected profile PID')
                require(math.isfinite(inclusive) and math.isfinite(exclusive), 'Non-finite raw CPU')
                require(inclusive >= 0 and exclusive >= 0, 'Negative raw CPU')
                key = (process_id, ns)
                require(stage not in parsed_reports[key], 'Duplicate stage within report boundary')
                values = dict(calls=calls, inclusive_cpu_s=inclusive,
                              exclusive_cpu_s=exclusive, clock_errors=errors)
                parsed_reports[key][stage] = values
                seconds = ns / 1e9
                raw_reports.append(dict(**ident, source_log=str(log_path), source_line=line_number,
                                        pid=process_id, steady_ns=ns, monotonic_s=seconds,
                                        final=int(final), function_stage=stage,
                                        category=attribution.category(stage), **values,
                                        in_window=flight_start <= seconds <= flight_end,
                                        in_selected_profile_window=start <= seconds <= end,
                                        first_profile_boundary=seconds == start,
                                        last_profile_boundary=seconds == end, raw_line=line))
                stage_universe.add(stage)
            if '[THREAD_CPU_ROLE]' in line:
                role_line_count += 1
                line_role_count += 1
                match = profile.ROLE_PATTERN.search(line)
                require(match is not None, f'Malformed raw role record: {log_path}:{line_number}')
                process_id, tid, role = match.groups()
                require(int(process_id) == pid, 'Unexpected role PID')
                role_record = dict(**ident, source_log=str(log_path), source_line=line_number,
                                   pid=int(process_id), tid=int(tid), role=role,
                                   in_window=None, window_membership_available=False,
                                   unavailable_reason='role_marker_has_no_monotonic_timestamp',
                                   raw_line=line)
                raw_roles.append(role_record)
                roles_for_run.append(role_record)
        require(line_report_count > 0 and line_role_count > 0, 'Missing raw instrumentation')
        selected = sorted(ns for process_id, ns in parsed_reports if
                          process_id == pid and flight_start <= ns / 1e9 <= flight_end)
        require(len(selected) >= 2, 'Fewer than two in-flight report boundaries')
        same(selected[0] / 1e9, start, 'first report boundary')
        same(selected[-1] / 1e9, end, 'last report boundary')
        initial = parsed_reports[(pid, selected[0])]
        terminal = parsed_reports[(pid, selected[-1])]
        require(initial.keys() <= terminal.keys(), 'A cumulative stage disappears at final selected boundary')
        bucket_values = collections.defaultdict(list)
        clock_errors = negative_deltas = 0
        for name, item in stages.items():
            clock_errors += item['clock_errors']
            for field in ('calls', 'inclusive_cpu_s', 'exclusive_cpu_s'):
                negative_deltas += item[field] < 0
                expected = terminal[name][field] - initial.get(name, {}).get(field, 0)
                same(item[field], expected, f'{ident["flight_id"]}/{name}/{field}')
            bucket_values[attribution.category(name)].append(item['exclusive_cpu_s'])
        require(clock_errors == 0 and negative_deltas == 0, 'Invalid derived counters')
        total = math.fsum(s['exclusive_cpu_s'] for s in stages.values())
        same(total / duration, process['sum_exclusive_mean_cores'], 'Analyzer exclusive sum')
        require(not bucket_values['unclassified_measured'], 'Unclassified measured stage')
        run = dict(**ident, profile_available=True, profile_process_count=1, pid=pid,
                   original_raw_file=str(folder / 'raw.csv'), source_log=str(log_path),
                   source_log_sha256=log_evidence['sha256'], source_log_hash_verified=True,
                   telemetry_file=str(telemetry_path), source_cpu_profile_enabled=True,
                   telemetry_flight_start_monotonic_s=flight_start,
                   telemetry_flight_end_monotonic_s=flight_end,
                   telemetry_flight_span_s=flight_end - flight_start,
                   profile_start_monotonic_s=start, profile_end_monotonic_s=end,
                   profile_start_steady_ns=selected[0], profile_end_steady_ns=selected[-1],
                   profile_duration_s=duration,
                   profile_coverage_fraction=duration / (flight_end - flight_start),
                   cropped_start_s=start - flight_start, cropped_end_s=flight_end - end,
                   selected_report_boundaries=len(selected), raw_profile_records=line_report_count,
                   raw_role_records=line_role_count,
                   stage_count=len(stages), required_stages_available=True,
                   required_stages='|'.join(sorted(required)), clock_errors=clock_errors,
                   negative_counter_deltas=negative_deltas, unclassified_stage_count=0,
                   experiment_cpu_available=True,
                   experiment_cpu_mean_cores=float(raw['cpu_cores']),
                   experiment_cpu_core_s=float(raw['cpu_core_s']),
                   cgroup_cpu_duration_s=float(raw['cgroup_cpu_duration_s']),
                   mission_time_s=float(raw['time_s']),
                   experiment_scope=raw['end_to_end_cpu_scope'],
                   original_algorithm_cpu_scope=raw['algorithm_cpu_scope'],
                   instrumented_total_cpu_core_s=total,
                   instrumented_total_mean_cores=total / duration,
                   measured_functional_scope_complete=False,
                   mission_cpu_in_measured_functional_subtotal=False,
                   complete_simulator_excluded_cpu_available=False)
        for bucket, prefix in BUCKET_FIELDS.items():
            values = bucket_values[bucket]
            available = bool(values)
            run[prefix + '_available'] = available
            run[prefix + '_stage_count'] = len(values)
            run[prefix + '_cpu_core_s'] = math.fsum(values) if available else None
            run[prefix + '_mean_cores'] = math.fsum(values) / duration if available else None
        require(run['instrumented_autonomy_available'], 'No functional CPU subtotal')
        same(math.fsum(run[p + '_cpu_core_s'] or 0 for p in BUCKET_FIELDS.values()),
             total, 'Category partition')
        runs.append(run)
        run_details.append(dict(identity=ident, initial=initial, terminal=terminal,
                                stages=stages, run=run, all_reported_stages=set().union(
                                    *(r.keys() for r in parsed_reports.values()))))
        for role in process['thread_roles']['roles']:
            role_cpu.append(dict(**ident, pid=pid, role=role['role'],
                                 tids='|'.join(map(str, role['tids'])),
                                 unambiguous=role['unambiguous'],
                                 eligible_interval_s=role['eligible_interval_s'],
                                 observed_interval_s=role['observed_interval_s'],
                                 samples=role['samples'],
                                 available=role['mean_used_cores'] is not None,
                                 sampled_cpu_core_s=role['sampled_cpu_core_s'] if role['samples'] else None,
                                 mean_used_cores=role['mean_used_cores'],
                                 scope=process['thread_roles']['interval_scope'],
                                 warning='Do not subtract entire renderer role: nested non-simulator callbacks share it'))
        if (index + 1) % 30 == 0:
            print(f'Validated existing frozen profiles: {index + 1}/210', flush=True)

    stage_rows = []
    for detail in run_details:
        run = detail['run']
        for name in sorted(stage_universe):
            initial, terminal = detail['initial'].get(name), detail['terminal'].get(name)
            item = detail['stages'].get(name)
            available = item is not None
            out = dict(**detail['identity'], pid=run['pid'], function_stage=name,
                       category=attribution.category(name), profile_stage_available=available,
                       stage_reported_anywhere_in_log=name in detail['all_reported_stages'],
                       stage_present_at_start=initial is not None,
                       stage_present_at_end=terminal is not None,
                       start_counter_inferred_zero=available and initial is None,
                       availability_reason='observed_selected_report_delta' if available else
                       'not_reported_at_selected_end; inactive_or_unavailable_not_invented_zero',
                       zero_start_policy='existing_analyzer_infers_zero_for_never_before_reported_cumulative_stage' if available and initial is None else None,
                       profile_start_steady_ns=run['profile_start_steady_ns'],
                       profile_end_steady_ns=run['profile_end_steady_ns'],
                       profile_start_monotonic_s=run['profile_start_monotonic_s'],
                       profile_end_monotonic_s=run['profile_end_monotonic_s'],
                       profile_duration_s=run['profile_duration_s'])
            for field in ('calls', 'inclusive_cpu_s', 'exclusive_cpu_s'):
                out['start_' + field] = initial[field] if initial else None
                out['end_' + field] = terminal[field] if terminal else None
                out['delta_' + field] = item[field] if available else None
            out['exclusive_mean_cores'] = item['mean_used_cores_exclusive'] if available else None
            out['inclusive_cpu_ms_per_call'] = item['inclusive_cpu_ms_per_call'] if available else None
            out['clock_errors_at_start'] = initial['clock_errors'] if initial else None
            out['clock_errors_at_end'] = terminal['clock_errors'] if terminal else None
            out['negative_delta'] = any(item[x] < 0 for x in ('calls', 'inclusive_cpu_s', 'exclusive_cpu_s')) if available else None
            stage_rows.append(out)

    map_summary = summarize_runs(runs, 'map_label')
    environment_summary = summarize_runs(runs, 'environment')
    reductions = paired_reductions(runs)
    require(len(map_summary) == 21 and len(environment_summary) == 9, 'Unexpected aggregate count')
    require(len(raw_reports) == profile_line_count and len(raw_roles) == role_line_count,
            'Raw marker preservation failed')
    require(sum(x['kind'] == 'actual_attempt1_stack_log' for x in evidence) == 210,
            'Not all 210 actual logs were verified')
    artifact_rows = {
        'run_cpu_210.csv': runs,
        'stage_cpu_210.csv': stage_rows,
        'raw_profile_reports.csv': raw_reports,
        'thread_roles.csv': raw_roles,
        'thread_role_cpu_210.csv': role_cpu,
        'summary_by_map_21.csv': map_summary,
        'summary_by_environment_9.csv': environment_summary,
        'full_baseline_reductions.csv': reductions,
    }
    for filename, rows in artifact_rows.items():
        write_csv(output / filename, rows)

    definitions = dict(
        primary_scope='Original whole-experiment cgroup CPU including simulator, frontend, planner, mission and launch helpers; observer/background excluded',
        primary_mean_cores='Original end_to_end_cpu_cores_mean, preserved without recomputation or subtraction',
        additional_scope='Instrumented functional exclusive-stage subtotal, excluding measured simulator and diagnostic/visualization stages; NOT complete autonomy CPU',
        additional_core_s='Sum of end-minus-start exclusive_cpu_s counters in the functional category over common report boundaries within observed flight',
        additional_mean_cores='Additional profile-window CPU core-s divided by that exact profile duration, then arithmetic mean across runs',
        categories=dict(simulator=sorted(attribution.SIM), diagnostic=sorted(attribution.COMMON),
                        functional_prefixes=['map_', 'frontend_', 'fsm_', 'guard_', 'planner_'],
                        precedence='Exact simulator, then exact diagnostic, then functional prefix, otherwise unclassified'),
        missing='Unavailable stage/counter/bucket values are null in JSON and blank in CSV, not invented zero. A first absent cumulative counter uses the existing analyzer zero-baseline rule and is flagged separately.',
        inactive='Absence of a function stage does not establish zero CPU for an uninstrumented function. Full has no frontend component; unused callbacks may produce no records.',
        reductions='Ratio-of-arithmetic-means reduction and paired per-run reduction are distinct columns; Full pairs use (campaign stage, map, repeat)',
        cumulative_warning='Profile-window core-s is not whole-flight core-s; never multiply profile mean cores by mission/cgroup duration',
        summary_statistics='Sample SD (n-1), arithmetic mean, median, min/max, linearly interpolated p05/p95, sum and available n',
        residual='Uninstrumented executor/DDS/background threads, profiler overhead and separately running mission CPU are outside the additional subtotal; do not label the residual avoidable waste',
        renderer_role_warning='Whole renderer thread may execute nested acquisition/map/frontend handoff work. Role CPU is diagnostic and must not replace exclusive-stage ownership.',
        raw_in_window='True exactly when report monotonic timestamp is within min/max campaign_active telemetry timestamps; RAW CSV preserves records outside this interval too',
        role_in_window='Unavailable: role markers contain no monotonic timestamp. Raw line and source line are retained instead of inventing timing',
        no_new_experiment=True, no_runtime_change=True, no_original_result_change=True,
    )
    stage_coverage = []
    for mode in MODES:
        for name in sorted(stage_universe):
            selected = [r for r in stage_rows if r['mode'] == mode and r['function_stage'] == name]
            stage_coverage.append(dict(mode=mode, function_stage=name,
                                       runs=len(selected), available=sum(r['profile_stage_available'] for r in selected),
                                       unavailable=sum(not r['profile_stage_available'] for r in selected)))
    source_files = [source_table, frozen_manifest_path, Path(__file__),
                    TOOLS / 'analyze_thread_cpu_profile.py', TOOLS / 'summarize_cpu_attribution.py']
    coverage = dict(
        schema='final210-cpu-supplement-evidence-v1',
        created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        source_package=str(package), source_table_sha256=source_table_sha,
        source_manifest_sha256=sha(frozen_manifest_path),
        source_hashes={str(p): sha(p) for p in source_files},
        category_source_sha256=category_hash,
        category_source_in_frozen_manifest=False,
        classification_preserved_explicitly_in_result_definitions=True,
        main_runs=210, mode_counts=dict(collections.Counter(r['mode'] for r in runs)),
        profiles_available=210, actual_attempt1_log_hashes_verified=210,
        source_evidence_files_verified=len(evidence), source_evidence=evidence,
        raw_profile_records=len(raw_reports), raw_role_records=len(raw_roles),
        raw_periodic_records=sum(r['final'] == 0 for r in raw_reports),
        raw_final_records=sum(r['final'] == 1 for r in raw_reports),
        raw_records_outside_flight_window=sum(not r['in_window'] for r in raw_reports),
        raw_records_outside_selected_profile_window=sum(not r['in_selected_profile_window'] for r in raw_reports),
        raw_records_preserved_without_window_filter=True,
        all_required_stages_available=True, unexpected_pids=0, clock_errors=0,
        negative_counter_deltas=0, unclassified_stages=[],
        stage_universe=sorted(stage_universe), stage_availability=stage_coverage,
        timing={key: stats([r[key] for r in runs]) for key in
                ('profile_duration_s', 'profile_coverage_fraction', 'cropped_start_s', 'cropped_end_s')},
        artifacts={name: dict(rows=len(rows), sha256=sha(output / name)) for name, rows in artifact_rows.items()},
    )
    write_json(output / 'coverage_evidence.json', coverage)
    result = dict(schema='final210-cpu-supplement-v1', definitions=definitions,
                  run_count=210, map_mode_count=21, environment_mode_count=9,
                  run_metrics=runs, map_summaries=map_summary,
                  environment_summaries=environment_summary,
                  full_baseline_reductions=reductions,
                  detail_artifacts={name: dict(rows=len(rows), path=name) for name, rows in artifact_rows.items()},
                  evidence_path='coverage_evidence.json')
    write_json(output / 'result.json', result)

    # Re-read generated files and independently reconstruct published sums,
    # means, pair counts, and reductions before declaring the supplement ready.
    loaded_runs = read_csv(output / 'run_cpu_210.csv')
    loaded_stages = read_csv(output / 'stage_cpu_210.csv')
    require(len(loaded_runs) == 210, 'Output row count mismatch')
    for run in loaded_runs:
        measured = [s for s in loaded_stages if s['flight_id'] == run['flight_id'] and
                    s['profile_stage_available'] == 'True']
        functional = [s for s in measured if s['category'] == 'autonomy_measured_subtotal']
        cpu = math.fsum(float(s['delta_exclusive_cpu_s']) for s in functional)
        same(cpu, run['instrumented_autonomy_cpu_core_s'], 'Re-read functional CPU')
        same(cpu / float(run['profile_duration_s']), run['instrumented_autonomy_mean_cores'], 'Re-read functional mean')
        for mean_field, cpu_field in (
                ('experiment_cpu_mean_cores', 'experiment_cpu_core_s'),
                ('instrumented_autonomy_mean_cores', 'instrumented_autonomy_cpu_core_s'),
                ('instrumented_simulator_mean_cores', 'instrumented_simulator_cpu_core_s'),
                ('instrumented_diagnostic_mean_cores', 'instrumented_diagnostic_cpu_core_s')):
            require(run[mean_field] != '' and run[cpu_field] != '', 'Unexpected missing run metric')
    for name, group_field in (('summary_by_map_21.csv', 'map_label'),
                              ('summary_by_environment_9.csv', 'environment')):
        for row in read_csv(output / name):
            selected = [r for r in loaded_runs if r[group_field] == row['group'] and r['mode'] == row['mode']]
            require(len(selected) == int(row['n_runs']), 'Re-read group n mismatch')
            for field in METRICS:
                values = [float(r[field]) for r in selected if r[field] != '']
                require(len(values) == int(row[field + '_n']), 'Re-read metric n mismatch')
                if values:
                    same(statistics.mean(values), row[field + '_mean'], 'Re-read aggregate mean')
                    same(statistics.median(values), row[field + '_median'], 'Re-read aggregate median')
                    if len(values) > 1:
                        same(statistics.stdev(values), row[field + '_sd_sample'], 'Re-read aggregate sample SD')
    for row in read_csv(output / 'full_baseline_reductions.csv'):
        same(100 * (1 - float(row['comparison_mean']) / float(row['full_mean'])),
             row['ratio_of_means_reduction_pct'], 'Re-read reduction')
        expected_pairs = 50 if row['grouping'] == 'environment' and row['group'] == 'Normal1-5' else 10
        require(int(row['matched_pairs']) == expected_pairs, 'Unexpected pair count')
    for name in ('coverage_evidence.json', 'result.json'):
        json.loads((output / name).read_text(), parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    require(sha(source_table) == source_table_sha, 'Original result table changed')
    validation = dict(schema='final210-cpu-supplement-validation-v1', status='PASS',
                      run_rows=210, map_rows=21, environment_rows=9,
                      checked_log_hashes=210, raw_records_preserved=len(raw_reports),
                      role_markers_preserved=len(raw_roles), derived_stage_rows=len(stage_rows),
                      all_required_profiles_present=True, unexpected_pids=0,
                      clock_errors=0, negative_deltas=0, unclassified_stages=0,
                      missing_stages_represented_as_unavailable=True,
                      output_csv_sum_mean_median_sd_checks=True,
                      full_baseline_reduction_checks=True, paired_counts_checked=True,
                      strict_json_valid=True, source_table_unchanged=True,
                      new_flight_launched=False, runtime_modified=False,
                      complete_simulator_excluded_cpu_claim=False)
    write_json(output / 'validation.json', validation)
    print(json.dumps(validation, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, default=DEFAULT_PACKAGE)
    args = parser.parse_args()
    package = args.package.resolve()
    build(package, package / 'cpu_analysis')
