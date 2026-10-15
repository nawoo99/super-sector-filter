#!/usr/bin/env python3
"""Independent read-only evidence audit; never imports the supplement builder.

Only independent_validation.json is written. Original logs, telemetry, CSVs,
and runtime files are read-only. No flight, subprocess, or profiler execution.
"""
import argparse
import collections
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import statistics


SIMULATOR = {'sim_static_cloud_callback', 'sim_odom_callback', 'sim_render_callback'}
DIAGNOSTIC = {'frontend_report', 'frontend_stats', 'planner_visualize_path'}
CHECKS = collections.Counter()


def expect(condition, label):
    CHECKS[label] += 1
    if not condition:
        raise AssertionError(label)


def match(actual, expected, label):
    if expected is None:
        expect(actual in ('', None), label)
    elif isinstance(expected, bool):
        expect(actual is expected or actual == str(expected), label)
    elif isinstance(expected, (int, float)):
        expect(actual not in ('', None) and math.isfinite(float(actual)) and
               math.isclose(float(actual), expected, rel_tol=2e-10, abs_tol=2e-9), label)
    else:
        expect(actual == expected, label)


def csv_rows(path):
    with path.open(newline='') as source:
        return list(csv.DictReader(source))


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def category(name):
    if name in SIMULATOR:
        return 'simulator_sensor_measured'
    if name in DIAGNOSTIC:
        return 'diagnostic_visualization_measured'
    if name.startswith(('map_', 'frontend_', 'fsm_', 'guard_', 'planner_')):
        return 'autonomy_measured_subtotal'
    return 'unclassified_measured'


def quantile(values, probability):
    values = sorted(values)
    index = probability * (len(values) - 1)
    lower, upper = math.floor(index), math.ceil(index)
    return values[lower] + (values[upper] - values[lower]) * (index - lower)


def stats(values):
    if not values:
        return dict(n=0, **{key: None for key in ('mean', 'median', 'sd_sample',
                                                'minimum', 'maximum', 'p05', 'p95', 'sum')})
    return dict(n=len(values), mean=statistics.mean(values), median=statistics.median(values),
                sd_sample=statistics.stdev(values) if len(values) > 1 else None,
                minimum=min(values), maximum=max(values), p05=quantile(values, .05),
                p95=quantile(values, .95), sum=sum(values))


def by_flight(rows):
    result = collections.defaultdict(list)
    for row in rows:
        result[row['flight_id']].append(row)
    return result


def flight_identity(row):
    return '/'.join(row[key] for key in ('stage', 'map', 'repeat', 'mode'))


def audit(folder):
    package = folder.parent
    originals_path = package / 'data/04_run_level_210.csv'
    manifest_path = package / 'data/source_frozen/source_manifest.json'
    original_rows = csv_rows(originals_path)
    originals = {flight_identity(row): row for row in original_rows}
    manifest = json.loads(manifest_path.read_text())['sha256']
    runs = csv_rows(folder / 'run_cpu_210.csv')
    stages = csv_rows(folder / 'stage_cpu_210.csv')
    raw = csv_rows(folder / 'raw_profile_reports.csv')
    role_markers = csv_rows(folder / 'thread_roles.csv')
    roles = csv_rows(folder / 'thread_role_cpu_210.csv')
    evidence = json.loads((folder / 'coverage_evidence.json').read_text())
    result = json.loads((folder / 'result.json').read_text())
    expect(len(originals) == len(original_rows) == len(runs) == 210, '210 original and result runs')
    expect({row['flight_id'] for row in runs} == set(originals), 'all original run identities retained')
    expect(len({row['flight_id'] for row in runs}) == len(runs), 'no duplicated run identity')
    expect(collections.Counter(row['mode'] for row in runs) == dict(full=70, sector=70, adaptive=70), '70 runs each mode')
    expect(len(stages) == 8190 and len(raw) == 88136 and len(role_markers) == len(roles) == 770,
           'all declared detail row counts')
    raw_groups, stage_groups = by_flight(raw), by_flight(stages)
    role_groups, role_cpu_groups = by_flight(role_markers), by_flight(roles)
    for grouped in (raw_groups, stage_groups, role_groups, role_cpu_groups):
        expect(set(grouped) == set(originals), 'detail covers exactly original flights')
    hashes = {}
    total_outside = zero_starts = alias_count = duplicate_reports = 0
    stage_universe = set()
    fractional_coverage = []
    for run in runs:
        fid = run['flight_id']
        original = originals[fid]
        for field in ('map', 'map_label', 'environment', 'mode', 'mode_label', 'run', 'repeat', 'stage'):
            match(run[field], original[field], f'run metadata {field}')
        directory = Path(original['directory'])
        log_path = directory / 'artifacts' / f"{original['map']}_run{original['run']}_{original['mode']}.attempt1.stack.log"
        telemetry_path = directory / 'telemetry.jsonl'
        raw_path = directory / 'raw.csv'
        summary_path = directory / f"{original['mode']}_summary.json"
        expect(run['source_log'] == str(log_path) and run['telemetry_file'] == str(telemetry_path), 'canonical source paths')
        for path in (log_path, telemetry_path, raw_path, summary_path):
            hashes[str(path)] = sha(path)
            expect(str(path) in manifest and hashes[str(path)] == manifest[str(path)], 'frozen manifest source hash')
        match(run['source_log_sha256'], hashes[str(log_path)], 'run log hash')
        match(original['stack_sha256'], hashes[str(log_path)], 'original run log hash')
        match(original['raw_sha256'], hashes[str(raw_path)], 'original raw hash')
        alias = log_path.with_name(log_path.name.replace('.attempt1.', '.'))
        if alias.exists():
            alias_count += 1
            expect(sha(alias) == hashes[str(log_path)], 'legacy stack alias byte-identical, not counted twice')
        summary = json.loads(summary_path.read_text())
        expect(summary.get('cpu_profile') is True, 'source mode summary CPU profiling enabled')
        original_raw = csv_rows(raw_path)
        expect(len(original_raw) == 1, 'one original raw row per run')
        for target, source, raw_key in (
                ('experiment_cpu_mean_cores', 'cpu_cores', 'end_to_end_cpu_cores_mean'),
                ('experiment_cpu_core_s', 'cpu_core_s', 'end_to_end_cpu_core_s'),
                ('cgroup_cpu_duration_s', 'cgroup_cpu_duration_s', 'cgroup_cpu_duration_s'),
                ('mission_time_s', 'time_s', 'mission_time_s')):
            match(run[target], float(original[source]), f'primary retained {target}')
            match(run[target], float(original_raw[0][raw_key]), f'primary raw source {target}')
        match(run['experiment_cpu_mean_cores'], float(run['experiment_cpu_core_s']) / float(run['cgroup_cpu_duration_s']), 'whole experiment same-window ratio')
        for field in ('measured_functional_scope_complete', 'mission_cpu_in_measured_functional_subtotal',
                      'complete_simulator_excluded_cpu_available'):
            match(run[field], False, f'honest incomplete subtotal {field}')
        telemetry = [json.loads(line) for line in telemetry_path.read_text().splitlines() if line.strip()]
        flight_times = [row['monotonic_s'] for row in telemetry if row.get('mode') == run['mode'] and row.get('campaign_active')]
        lo, hi = min(flight_times), max(flight_times)
        match(run['telemetry_flight_start_monotonic_s'], lo, 'flight window start')
        match(run['telemetry_flight_end_monotonic_s'], hi, 'flight window end')
        match(run['telemetry_flight_span_s'], hi - lo, 'flight window duration')
        profiles, actual_roles = [], []
        for line_no, line in enumerate(log_path.read_text(errors='replace').splitlines(), 1):
            for tag in ('THREAD_CPU_PROFILE', 'THREAD_CPU_ROLE'):
                marker = '[' + tag + ']'
                if marker not in line:
                    continue
                text = line.split(marker, 1)[1]
                fields = dict(re.findall(r'(\w+)=([^\s]+)', text))
                expect(fields.get('version') == '1', 'known raw marker version')
                fields.update(source_line=line_no, raw_line=line)
                if tag == 'THREAD_CPU_PROFILE':
                    for key in ('pid', 'steady_ns', 'final', 'calls', 'clock_errors'):
                        fields[key] = int(fields[key])
                    for key in ('inclusive_cpu_s', 'exclusive_cpu_s'):
                        fields[key] = float(fields[key])
                    expect(fields['clock_errors'] == 0, 'raw profiler clock errors zero')
                    expect(0 <= fields['exclusive_cpu_s'] <= fields['inclusive_cpu_s'] + 1e-9, 'raw exclusive bounded by inclusive')
                    profiles.append(fields)
                    stage_universe.add(fields['stage'])
                else:
                    fields['pid'], fields['tid'] = int(fields['pid']), int(fields['tid'])
                    actual_roles.append(fields)
        expect(len(profiles) == len(raw_groups[fid]), 'all raw profile records retained')
        expect(len(actual_roles) == len(role_groups[fid]), 'all raw role records retained')
        match(run['raw_profile_records'], len(profiles), 'run raw profile count')
        match(run['raw_role_records'], len(actual_roles), 'run raw role count')
        pid = int(run['pid'])
        expect({item['pid'] for item in profiles} == {pid}, 'one actual profiler PID')
        reports = collections.defaultdict(dict)
        for item in profiles:
            ns, name = item['steady_ns'], item['stage']
            if name in reports[ns]:
                duplicate_reports += 1
            expect(name not in reports[ns], 'no duplicate PID/report/stage counter')
            reports[ns][name] = item
        selected = sorted(ns for ns in reports if lo <= ns / 1e9 <= hi)
        expect(len(selected) >= 2, 'two or more report boundaries inside telemetry flight')
        first, last = selected[0], selected[-1]
        duration = (last - first) / 1e9
        for key, value in (('profile_start_steady_ns', first), ('profile_end_steady_ns', last),
                           ('profile_start_monotonic_s', first / 1e9), ('profile_end_monotonic_s', last / 1e9),
                           ('profile_duration_s', duration), ('selected_report_boundaries', len(selected)),
                           ('profile_coverage_fraction', duration / (hi - lo)),
                           ('cropped_start_s', first / 1e9 - lo), ('cropped_end_s', hi - last / 1e9)):
            match(run[key], value, f'selected window {key}')
        fractional_coverage.append(duration / (hi - lo))
        for item, exported in zip(profiles, raw_groups[fid]):
            for key in ('pid', 'steady_ns', 'final', 'calls', 'inclusive_cpu_s', 'exclusive_cpu_s', 'clock_errors', 'source_line', 'raw_line'):
                match(exported[key], item[key], f'raw retained {key}')
            match(exported['function_stage'], item['stage'], 'raw function name')
            match(exported['source_log'], str(log_path), 'raw source path')
            match(exported['category'], category(item['stage']), 'raw category')
            match(exported['monotonic_s'], item['steady_ns'] / 1e9, 'raw exact monotonic conversion')
            within = lo <= item['steady_ns'] / 1e9 <= hi
            total_outside += not within
            for key, value in (('in_window', within), ('in_selected_profile_window', first <= item['steady_ns'] <= last),
                               ('first_profile_boundary', item['steady_ns'] == first), ('last_profile_boundary', item['steady_ns'] == last)):
                match(exported[key], value, f'raw boundary membership {key}')
        accumulated = collections.defaultdict(float)
        counts = collections.Counter()
        start, end = reports[first], reports[last]
        expected_names = {item['function_stage'] for item in stage_groups[fid]}
        expect(len(stage_groups[fid]) == len(expected_names) == 39, '39 unique stage availability rows per run')
        for exported in stage_groups[fid]:
            name = exported['function_stage']
            present = name in end
            match(exported['category'], category(name), 'stage ownership category')
            for key, value in (('profile_stage_available', present), ('stage_present_at_start', name in start),
                               ('stage_present_at_end', present), ('start_counter_inferred_zero', present and name not in start),
                               ('stage_reported_anywhere_in_log', any(name in r for r in reports.values()))):
                match(exported[key], value, f'stage availability {key}')
            for key in ('profile_start_steady_ns', 'profile_end_steady_ns', 'profile_duration_s', 'pid'):
                match(exported[key], float(run[key]), f'stage shared boundary {key}')
            if not present:
                for key in ('delta_calls', 'delta_inclusive_cpu_s', 'delta_exclusive_cpu_s', 'exclusive_mean_cores',
                            'start_calls', 'end_calls', 'inclusive_cpu_ms_per_call'):
                    match(exported[key], None, 'unavailable stage blank not zero')
                continue
            a, b = start.get(name, dict(calls=0, inclusive_cpu_s=0., exclusive_cpu_s=0., clock_errors=0)), end[name]
            zero_starts += name not in start
            if name not in start:
                expect(all(name not in report for ns, report in reports.items() if ns <= first),
                       'zero baseline never previously reported, not dropped counter')
            for key, suffix in (('calls', 'calls'), ('inclusive_cpu_s', 'inclusive_cpu_s'), ('exclusive_cpu_s', 'exclusive_cpu_s')):
                delta = b[key] - a[key]
                expect(delta >= -1e-9, 'nondecreasing selected stage counter')
                match(exported['start_' + suffix], a[key] if name in start else None, f'stage starting {key}')
                match(exported['end_' + suffix], b[key], f'stage ending {key}')
                match(exported['delta_' + suffix], delta, f'stage delta {key}')
            calls, inclusive, exclusive = b['calls'] - a['calls'], b['inclusive_cpu_s'] - a['inclusive_cpu_s'], b['exclusive_cpu_s'] - a['exclusive_cpu_s']
            match(exported['exclusive_mean_cores'], exclusive / duration, 'exclusive CPU divided by own profile duration')
            match(exported['inclusive_cpu_ms_per_call'], 1000 * inclusive / calls if calls else None, 'inclusive per-call diagnostic only')
            match(exported['clock_errors_at_start'], a['clock_errors'] if name in start else None, 'stage clock errors start')
            match(exported['clock_errors_at_end'], b['clock_errors'], 'stage clock errors end')
            match(exported['negative_delta'], False, 'no negative delta flag')
            accumulated[category(name)] += exclusive
            counts[category(name)] += 1
        required = {'map_odom_callback', 'sim_render_callback'}
        if run['mode'] != 'full':
            required |= {'frontend_cloud', 'frontend_acquisition', 'frontend_enqueue', 'frontend_odom', 'frontend_stats'}
        if run['mode'] == 'adaptive':
            required.add('frontend_map_ack')
        expect(required <= end.keys(), 'required stage availability independent rule')
        expect(set(run['required_stages'].split('|')) == required, 'required stage list')
        match(run['stage_count'], len(end), 'available end stages')
        for prefix, group in (('autonomy', 'autonomy_measured_subtotal'), ('simulator', 'simulator_sensor_measured'),
                              ('diagnostic', 'diagnostic_visualization_measured'), ('unclassified', 'unclassified_measured')):
            base = 'instrumented_' + prefix
            count = counts[group]
            match(run[base + '_available'], bool(count), 'bucket availability')
            match(run[base + '_stage_count'], count, 'bucket stage count')
            match(run[base + '_cpu_core_s'], accumulated[group] if count else None, 'exclusive-only bucket CPU')
            match(run[base + '_mean_cores'], accumulated[group] / duration if count else None, 'exclusive-only bucket cores')
        match(run['instrumented_total_cpu_core_s'], sum(accumulated.values()), 'total sum exclusive never inclusive')
        match(run['instrumented_total_mean_cores'], sum(accumulated.values()) / duration, 'total divided by profile duration')
        roles_by_name = collections.defaultdict(set)
        for item, exported in zip(actual_roles, role_groups[fid]):
            for key in ('pid', 'tid', 'role', 'source_line', 'raw_line'):
                match(exported[key], item[key], f'raw role retained {key}')
            match(exported['in_window'], None, 'role window remains unavailable')
            match(exported['window_membership_available'], False, 'role marker has no timestamp')
            if item['pid'] == pid:
                roles_by_name[item['role']].add(item['tid'])
        expect(len(role_cpu_groups[fid]) == len(roles_by_name), 'one role summary per actual role')
        eligible = [r for r in telemetry if r.get('mode') == run['mode'] and r.get('campaign_active') and
                    r.get('interval_s', 0) > 0 and r['monotonic_s'] <= last / 1e9 and
                    r['monotonic_s'] - r['interval_s'] >= first / 1e9]
        for exported in role_cpu_groups[fid]:
            tids = roles_by_name[exported['role']]
            expect(set(map(int, exported['tids'].split('|'))) == tids, 'actual role TID identity')
            duration_eligible = sum(r['interval_s'] for r in eligible)
            observed = cpu = 0.
            samples = 0
            if len(tids) == 1:
                tid = next(iter(tids))
                for row in eligible:
                    entries = [t for t in row.get('experiment_threads', []) if t.get('pid') == pid and t.get('tid') == tid]
                    if len(entries) != 1:
                        continue
                    value = entries[0].get('cpu_pct_one_core')
                    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                        continue
                    observed += row['interval_s']
                    cpu += value * row['interval_s'] / 100
                    samples += 1
            for key, value in (('eligible_interval_s', duration_eligible), ('observed_interval_s', observed),
                               ('samples', samples), ('sampled_cpu_core_s', cpu),
                               ('mean_used_cores', cpu / observed if observed else None),
                               ('unambiguous', len(tids) == 1), ('available', observed > 0)):
                match(exported[key], value, f'role independent telemetry {key}')
    expect(stage_universe == {r['function_stage'] for r in stages}, 'stage universe retained without fabricated names')
    expect(len(stage_universe) == 39, '39 actually observed unique stage names')
    source_table_digest = sha(originals_path)
    match(evidence['source_table_sha256'], source_table_digest, 'frozen package run table hash')
    match(evidence['source_manifest_sha256'], sha(manifest_path), 'frozen package manifest hash')
    evidence_paths = set()
    for item in evidence['source_evidence']:
        path = Path(item['path'])
        actual = hashes.get(str(path)) or sha(path)
        expect(str(path) not in evidence_paths, 'no duplicate source evidence identity')
        evidence_paths.add(str(path))
        expect(actual == manifest[item['manifest_key']] == item['sha256'] == item['expected_sha256'], 'all declared source evidence hashes')
        match(item['verified'], True, 'evidence verified flag')
    expect(set(hashes) <= evidence_paths, 'every original CPU evidence file retained')
    for path, digest in evidence['source_hashes'].items():
        match(sha(Path(path)), digest, 'additional source provenance hash')
    for filename, grouping, expected_count, json_key in (
            ('summary_by_map_21.csv', 'map_label', 21, 'map_summaries'),
            ('summary_by_environment_9.csv', 'environment', 9, 'environment_summaries')):
        table = csv_rows(folder / filename)
        expect(len(table) == expected_count, 'summary complete row count')
        expect(len({(r['group'], r['mode']) for r in table}) == expected_count, 'summary unique group/mode')
        for exported in table:
            selected = [r for r in runs if r[grouping] == exported['group'] and r['mode'] == exported['mode']]
            expect(bool(selected), 'summary references existing group')
            match(exported['grouping'], grouping, 'summary grouping label')
            match(exported['n_runs'], len(selected), 'summary run count')
            match(exported['n_profile_available'], sum(r['profile_available'] == 'True' for r in selected), 'summary available count')
            metrics = [key[:-2] for key in exported if key.endswith('_n')]
            for metric in metrics:
                values = [float(r[metric]) for r in selected if r[metric] != '']
                for name, value in stats(values).items():
                    match(exported[metric + '_' + name], value, f'summary independent {metric} {name}')
        expect(len(result[json_key]) == len(table), 'JSON summary same row count')
        for exported, obj in zip(table, result[json_key]):
            for key, value in obj.items():
                match(exported[key], value, 'JSON/CSV summary parity')
    reductions = csv_rows(folder / 'full_baseline_reductions.csv')
    expect(len(reductions) == 80, 'all 80 Full comparisons')
    expect(len({(r['grouping'], r['group'], r['comparison_mode'], r['metric']) for r in reductions}) == 80,
           'no duplicate Full comparisons')
    for row in reductions:
        eligible = [r for r in runs if r[row['grouping']] == row['group']]
        key = lambda r: (r['stage'], r['map'], r['repeat'])
        full = {key(r): r for r in eligible if r['mode'] == 'full'}
        other = {key(r): r for r in eligible if r['mode'] == row['comparison_mode']}
        metric = row['metric']
        pairs = [(float(full[k][metric]), float(other[k][metric])) for k in sorted(full.keys() & other.keys())
                 if full[k][metric] != '' and other[k][metric] != '']
        match(row['matched_pairs'], len(pairs), 'paired complete matches')
        match(row['missing_pairs'], len(full.keys() | other.keys()) - len(pairs), 'paired missing count')
        avg_full, avg_other = statistics.mean(x for x, _ in pairs), statistics.mean(y for _, y in pairs)
        for field, value in (('full_mean', avg_full), ('comparison_mean', avg_other),
                             ('ratio_of_means_reduction_pct', 100 * (1 - avg_other / avg_full))):
            match(row[field], value, 'Full independent ratio of arithmetic means')
        for prefix, values in (('paired_absolute_difference', [y - x for x, y in pairs]),
                               ('paired_reduction_pct', [100 * (1 - y / x) for x, y in pairs])):
            for name, value in stats(values).items():
                match(row[prefix + '_' + name], value, f'paired independent {prefix} {name}')
        match(row['baseline_mode'], 'full', 'Full comparison baseline label')
        measured = metric.startswith('instrumented_')
        match(row['window'], 'in_flight_common_profile_report_window' if measured else 'original_cgroup_window', 'comparison window label')
    for exported, obj in zip(runs, result['run_metrics']):
        for key, value in obj.items():
            match(exported[key], value, 'JSON/CSV run parity')
    for exported, obj in zip(reductions, result['full_baseline_reductions']):
        for key, value in obj.items():
            match(exported[key], value, 'JSON/CSV Full reduction parity')
    expect('NOT complete autonomy CPU' in result['definitions']['additional_scope'], 'additional scope correctly qualified')
    expect('exclusive' in result['definitions']['additional_core_s'], 'CPU numerator explicitly exclusive')
    expect('not whole-flight' in result['definitions']['cumulative_warning'], 'profile window not whole flight warning')
    return dict(schema='final210-cpu-independent-validation-v1', status='PASS',
                validator='Independent regex/key-value raw parser and counter/statistic arithmetic; supplement builder not imported or executed',
                checked_runs=len(runs), checked_stage_rows=len(stages), checked_raw_profiles=len(raw),
                checked_raw_role_markers=len(role_markers), checked_role_summaries=len(roles),
                checked_map_summaries=21, checked_environment_summaries=9, checked_full_reductions=80,
                frozen_source_files_checked=len(hashes), all_source_evidence_hashes_checked=len(evidence_paths),
                outside_window_profile_records_preserved=total_outside,
                byte_identical_legacy_log_aliases_not_double_counted=alias_count,
                duplicate_raw_report_stage_keys=duplicate_reports, inferred_zero_start_counters_explicit=zero_starts,
                profile_coverage_fraction_range=[min(fractional_coverage), max(fractional_coverage)],
                assertions=sum(CHECKS.values()), checks=dict(CHECKS),
                source_table_sha256=source_table_digest, source_manifest_sha256=sha(manifest_path),
                output_artifact_sha256={p.name: sha(p) for p in sorted(folder.iterdir())
                    if p.is_file() and p.suffix in ('.csv', '.json') and p.name != 'independent_validation.json'},
                validator_sha256=sha(Path(__file__)),
                label_caveats=[
                    'instrumented_autonomy_* is a functional exclusive-stage subtotal, not complete autonomy CPU.',
                    'All run means use their own common stage-report window; different modes/runs need not share equal duration.',
                    'Cumulative profile core-s excludes cropped start/end and must not be treated as whole-flight CPU.',
                    'Raw thread roles lack timestamp; whole renderer role contains nested functional callbacks and is not subtracted.',
                    '39 stage availability rows per run include blank unavailable entries, not 39 nonzero measured stages.',
                    'Live stage report counters are independently loaded and scope-completion-attributed, not an exact atomic physical-window integral.'],
                new_flight_launched=False, runtime_modified=False, original_artifacts_modified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', nargs='?', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    try:
        report = audit(args.folder)
    except Exception as error:
        report = dict(schema='final210-cpu-independent-validation-v1', status='FAIL',
                      error=repr(error), assertions=sum(CHECKS.values()), checks=dict(CHECKS))
        (args.folder / 'independent_validation.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
        raise
    (args.folder / 'independent_validation.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('checks', 'output_artifact_sha256')}, indent=2))


if __name__ == '__main__':
    main()
