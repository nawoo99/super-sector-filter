#!/usr/bin/env python3
"""Independently validate the 2026-10-12 result package against frozen evidence.

This script does not import the package builder. It reads the original frozen
cohort and raw artifacts, reconstructs all mapping windows and grouped results,
and writes only the JSON report explicitly requested with --output. It never
launches a simulation or changes source evidence. Requires build_complete.json.
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
from datetime import datetime, timezone


FROZEN = Path('/root/share/here/v6_frozen_20261008')
MAP_SOURCE = Path('/root/share/map_visualizations_20261010')
LABELS = {
    'gapfree_d1_m01': 'Map1',
    'gapfree_d1_m02': 'Map2',
    'gapfree_d1_m03': 'Map3',
    'gapfree_d1_m04': 'Map4',
    'gapfree_d1_m05r2': 'Map5-R2',
    'urban_blocks_u01': 'Urban',
    'forest_cluster_f01': 'Forest',
}
MODES = ('full', 'sector', 'adaptive')
PERF_COLUMNS = {
    'Total': 'mapping_elapsed_s',
    'Raycast': 'mapping_raycast_elapsed_s',
    'Update_cache': 'mapping_cache_update_elapsed_s',
    'Inflation': 'mapping_inflation_elapsed_s',
}
PRIMARY_METRICS = (
    'cpu_cores', 'cpu_core_s', 'input_mib_s', 'input_mib_run', 'map_ms',
    'mapping_elapsed_s', 'mapping_frames', 'mapping_mean_ms_from_log',
    'map_frames_s', 'mapping_points_total', 'mapping_points_mean',
    'mapping_points_s', 'mapping_max_ms', 'mapping_p95_ms', 'mapping_raycast_elapsed_s',
    'mapping_cache_update_elapsed_s', 'mapping_inflation_elapsed_s',
    'host_cpu_pct_mean', 'baseline_host_cpu_pct_mean', 'experiment_host_capacity_pct',
)
SUPPLEMENTARY_METRICS = (
    'end_to_end_cpu_cores_p95_1s', 'end_to_end_cpu_cores_max_1s', 'cgroup_cpu_duration_s',
    'end_to_end_peak_rss_mib', 'end_to_end_peak_pss_mib', 'end_to_end_peak_swap_mib',
    'trajectory_commit_unique_generations', 'trajectory_commit_span_s', 'trajectory_commit_hz',
    'sensor_hz', 'filter_frames', 'filter_cloud_input_callbacks', 'filter_cloud_input_hz',
    'filter_cloud_publish_hz', 'filter_map_commit_hz', 'filter_cloud_compute_ms_mean',
    'filter_cloud_compute_ms_max', 'filter_frontend_compute_core_equivalent',
    'filter_input_points', 'filter_kept_points', 'filter_kept_pct', 'filter_open_duty_pct',
    'guard_recoveries', 'guard_recovery_active_duration_s', 'guard_recovery_active_duration_mean_s',
    'guard_recovery_active_duration_max_s', 'path_length_m', 'max_odom_speed_3d_mps',
    'filter_trajectory_guard_full_refresh_ack_count',
    'filter_trajectory_guard_full_refresh_ack_latency_mean_s',
    'filter_trajectory_guard_full_refresh_ack_latency_max_s',
    'filter_slowdown_full_refresh_ack_count', 'filter_slowdown_full_refresh_ack_latency_mean_s',
    'filter_slowdown_full_refresh_ack_latency_max_s',
    'filter_pre_stale_full_refresh_ack_count', 'filter_pre_stale_full_refresh_ack_latency_mean_s',
    'filter_pre_stale_full_refresh_ack_latency_max_s',
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline='', encoding='utf-8-sig') as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        if not fields or len(set(fields)) != len(fields):
            raise ValueError(f'Absent or duplicate CSV columns: {path}')
        rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError(f'CSV row length differs from header: {path}')
    return fields, rows


def read_json(path: Path):
    with path.open(encoding='utf-8') as stream:
        return json.load(stream)


def number(value) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f'Nonfinite number: {value!r}')
    return result


def integer(value) -> int:
    value = number(value)
    if value != int(value):
        raise ValueError(f'Nonintegral number: {value!r}')
    return int(value)


def optional_number(value) -> float | None:
    """Recorded-unavailable numeric fields remain unavailable, never zero."""
    if value is None or isinstance(value, bool):
        return None
    if str(value).strip().lower() in ('', 'none', 'nan', 'null', 'true', 'false'):
        return None
    try:
        return number(value)
    except (ValueError, TypeError):
        return None


def numeric_stats(values) -> dict:
    available = [parsed for value in values if (parsed := optional_number(value)) is not None]
    return {
        'n': len(available),
        'mean': statistics.mean(available) if available else None,
        'median': statistics.median(available) if available else None,
        'sd': statistics.stdev(available) if len(available) > 1 else None,
        'min': min(available) if available else None,
        'max': max(available) if available else None,
    }


def percentile_linear(values: list[float], percentile: float) -> float:
    """Standard linear empirical percentile, independent of NumPy/builder."""
    ordered = sorted(values)
    if not ordered:
        raise ValueError('Percentile requires nonempty values')
    position = (len(ordered) - 1) * percentile / 100
    lower, upper = math.floor(position), math.ceil(position)
    weight = position - lower
    return ordered[lower] + weight * (ordered[upper] - ordered[lower])


def boolean(value) -> bool:
    if isinstance(value, bool):
        return value
    value = str(value).strip().lower()
    if value in ('true', '1'):
        return True
    if value in ('false', '0'):
        return False
    raise ValueError(f'Invalid boolean: {value!r}')


def identity(row) -> tuple[str, str, int, str]:
    return row['stage'], row['map'], integer(row['repeat']), row['mode']


def raw_identity(row) -> tuple[str, int, str]:
    return row['map'], integer(row['run']), row['mode']


def environment(map_id: str) -> str:
    return 'Normal1-5' if map_id.startswith('gapfree_d1_') else LABELS[map_id]


def derive(row: dict[str, str]) -> dict:
    result = dict(row)
    complete = boolean(row['success'])
    contact = integer(row['contacts']) > 0
    result.update(goal_complete=complete, contact_run=contact,
                  safe_complete=complete and not contact,
                  mission_failure=contact or not complete,
                  map_label=LABELS[row['map']], environment=environment(row['map']))
    return result


class Validator:
    def __init__(self, package: Path):
        self.package = package
        self.errors: list[str] = []
        self.counts = collections.Counter()
        self.sections: dict[str, bool] = {}
        self.details: dict = {}
        self.frozen_fields: list[str] = []
        self.original: list[dict] = []
        self.gate: list[dict] = []
        self.source_hashes: dict[str, str] = {}
        self.reconstructed: dict[tuple, dict] = {}
        self.original_raw: dict[tuple, dict[str, str]] = {}

    def check(self, condition: bool, message: str):
        self.counts['assertions'] += 1
        if not condition:
            self.errors.append(message)

    def equal(self, actual, expected, message: str):
        self.check(actual == expected, f'{message}: got {actual!r}, expected {expected!r}')

    def close(self, actual, expected, message: str):
        if expected is None:
            self.check(actual in ('', None), f'{message}: expected an empty unavailable statistic')
            return
        try:
            parsed = number(actual)
        except (ValueError, TypeError):
            self.check(False, f'{message}: invalid numeric value {actual!r}')
            return
        self.check(math.isclose(parsed, expected, rel_tol=1e-10, abs_tol=1e-10),
                   f'{message}: got {parsed!r}, recomputed {expected!r}')

    def phase(self, name: str, action):
        before = len(self.errors)
        try:
            action()
        except Exception as exc:
            self.errors.append(f'{name}: {type(exc).__name__}: {exc}')
        self.sections[name] = len(self.errors) == before

    def packaged(self, relative: str) -> Path:
        path = (self.package / relative).resolve()
        if not path.is_relative_to(self.package):
            raise ValueError(f'Package-relative path escapes package: {relative}')
        return path

    def frozen_sources(self):
        manifest = read_json(FROZEN / 'freeze_manifest.json')
        self.equal(manifest['state'], 'FROZEN', 'Original freeze state')
        for relative, expected in manifest['sha256'].items():
            original = FROZEN / relative
            self.equal(sha256(original), expected, f'Original frozen hash {relative}')
            copy = self.package / 'source_frozen' / relative
            self.equal(sha256(copy), expected, f'Packaged frozen hash {relative}')
            self.counts['frozen_files'] += 1
        self.equal(sha256(self.package / 'source_frozen' / 'freeze_manifest.json'),
                   sha256(FROZEN / 'freeze_manifest.json'), 'Frozen manifest copy')
        self.frozen_fields, self.original = read_csv(FROZEN / 'main_210.csv')
        _, self.gate = read_csv(FROZEN / 'forest_gate_30.csv')
        self.source_hashes = read_json(FROZEN / 'source_manifest.json')['sha256']
        expected_keys = {('seven_map_n10', map_id, repeat, mode)
                         for map_id in LABELS for repeat in range(1, 11) for mode in MODES}
        keys = [identity(row) for row in self.original]
        self.equal(len(keys), 210, 'Original main row count')
        self.equal(set(keys), expected_keys, 'Original main complete inventory')
        self.equal(len(set(keys)), len(keys), 'Original main unique identity count')
        self.equal(len(self.gate), 30, 'Separate gate original count')
        self.equal({identity(row) for row in self.gate},
                   {('forest_n10', 'forest_cluster_f01', repeat, mode)
                    for repeat in range(1, 11) for mode in MODES}, 'Separate gate inventory')
        self.counts['original_main_rows'] = len(self.original)
        self.counts['original_gate_rows'] = len(self.gate)

    def mapping_artifact(self, frozen: dict, packaged: dict, gate=False) -> dict:
        key = identity(frozen)
        folder = Path(frozen['directory'])
        raw_path = folder / 'raw.csv'
        raw_hash = sha256(raw_path)
        self.equal(raw_hash, frozen['raw_sha256'], f'{key} original raw hash')
        self.equal(raw_hash, self.source_hashes[str(raw_path)], f'{key} raw frozen source hash')
        raw_fields, raw_rows = read_csv(raw_path)
        self.equal(len(raw_rows), 1, f'{key} original raw single-row inventory')
        raw = raw_rows[0]
        self.equal(raw_identity(raw), raw_identity(frozen), f'{key} raw identity')
        self.original_raw[key] = raw
        stem = f'{frozen["map"]}_run{frozen["run"]}_{frozen["mode"]}.attempt1'
        stack_path = folder / 'artifacts' / (stem + '.stack.log')
        self.equal(sha256(stack_path), frozen['stack_sha256'], f'{key} original stack hash')
        perf_path = folder / 'artifacts' / Path(raw['perf_trace_csv']).name
        perf_hash = sha256(perf_path)
        self.equal(perf_hash, self.source_hashes[str(perf_path)], f'{key} performance frozen source hash')
        self.check(boolean(raw['perf_window_valid']), f'{key} original valid mapping window')
        with perf_path.open(newline='', encoding='utf-8-sig') as stream:
            csv_rows = list(csv.reader(stream))
        header = [field.strip() for field in csv_rows[0]]
        # The original measurement rule filters before applying data-row offsets.
        data = [row for row in csv_rows[1:] if len(row) == len(header) and row[0].strip()]
        start, end = integer(raw['perf_row_start']), integer(raw['perf_row_end'])
        self.check(0 <= start < end <= len(data), f'{key} mapping window bounds')
        selected = [[number(cell) for cell in row] for row in data[start:end]]
        columns = {field: index for index, field in enumerate(header)}
        self.check(len(selected) > 0, f'{key} nonempty mapping window')
        self.check(all(row[columns['Total']] >= 0 for row in selected), f'{key} nonnegative Total elapsed')
        sums = {target: math.fsum(row[columns[source]] for row in selected)
                for source, target in PERF_COLUMNS.items()}
        totals = [row[columns['Total']] for row in selected]
        points = [row[columns['PointCloudNumber']] for row in selected]
        payload = [row[columns['PointCloudPayloadBytes']] for row in selected]
        mean_ms = statistics.mean(totals) * 1000
        expected = derive(frozen)
        # Supplementary run fields may also be reported. Their independent
        # baseline is the original raw row, never the new run-level CSV.
        for field, value in raw.items():
            expected.setdefault(field, value)
        expected.update(sums, mapping_frames=len(selected), mapping_mean_ms_from_log=mean_ms,
                        mapping_perf_row_start=start, mapping_perf_row_end=end,
                        mapping_max_ms=max(totals) * 1000,
                        mapping_p95_ms=percentile_linear(totals, 95) * 1000,
                        mapping_points_total=math.fsum(points),
                        mapping_points_mean=statistics.mean(points),
                        mapping_points_s=math.fsum(points) / number(frozen['time_s']),
                        mapping_payload_bytes_total=math.fsum(payload))
        for field in SUPPLEMENTARY_METRICS:
            value = optional_number(raw.get(field))
            if '_ack_latency_' in field:
                ack_field = field.split('_ack_latency_')[0] + '_ack_count'
                ack_count = optional_number(raw.get(ack_field))
                if ack_count is None or ack_count <= 0:
                    value = None
            expected[field] = value
            self.check(field in packaged, f'{key} required supplementary field {field}')
            if field in packaged:
                self.close(packaged[field], value, f'{key} independently preserved/suppressed {field}')
                self.counts['run_supplementary_numeric_fields'] += 1
        for field in ('algorithm_cpu_scope', 'end_to_end_cpu_scope'):
            self.equal(packaged[field], raw.get(field, ''), f'{key} original CPU scope {field}')
        self.equal(len(selected), integer(raw['map_perf_frames']), f'{key} raw mapping frame count')
        self.close(mean_ms, number(raw['total_ms_mean']), f'{key} raw Total mean (ms)')
        self.close(mean_ms, number(frozen['map_ms']), f'{key} frozen map_ms')
        for column, raw_mean in [('Raycast', 'raycast_ms_mean'),
                                 ('Update_cache', 'update_ms_mean'),
                                 ('Inflation', 'inflation_ms_mean')]:
            self.close(statistics.mean(row[columns[column]] for row in selected) * 1000,
                       number(raw[raw_mean]), f'{key} raw {column} mean (ms)')
        for field in (*sums, 'mapping_frames', 'mapping_mean_ms_from_log',
                      'mapping_perf_row_start', 'mapping_perf_row_end',
                      'mapping_max_ms', 'mapping_p95_ms', 'mapping_points_total',
                      'mapping_points_mean', 'mapping_points_s', 'mapping_payload_bytes_total'):
            self.check(field in packaged, f'{key} required mapping field {field}')
            if field in packaged:
                self.close(packaged[field], expected[field], f'{key} packaged {field}')
        self.close(expected['mapping_payload_bytes_total'] / 2**20, number(frozen['input_mib_run']),
                   f'{key} independently summed payload MiB')
        self.close(len(selected) / number(frozen['time_s']), number(frozen['map_frames_s']),
                   f'{key} independently counted mapping frame rate')
        copy_relative = packaged['mapping_performance_file']
        copy_path = self.packaged(copy_relative)
        expected_relative = ('mapping_performance/separate_gate/' if gate else 'mapping_performance/')
        expected_relative += f'{frozen["map"]}/r{integer(frozen["repeat"]):02d}/{frozen["mode"]}.csv'
        self.equal(copy_relative, expected_relative, f'{key} performance copy path')
        self.equal(sha256(copy_path), perf_hash, f'{key} preserved performance copy bytes')
        self.equal(packaged['mapping_performance_sha256'], perf_hash, f'{key} recorded performance hash')
        if 'raw_file' in packaged:
            self.equal(packaged['raw_file'], str(raw_path), f'{key} recorded original raw path')
        self.counts['gate_mapping_artifacts' if gate else 'main_mapping_artifacts'] += 1
        self.counts['mapping_window_frames'] += len(selected)
        self.counts['gate_mapping_window_frames' if gate else 'main_mapping_window_frames'] += len(selected)
        self.counts['raw_original_fields_checked'] += len(raw_fields)
        return expected

    def run_level(self):
        fields, rows = read_csv(self.package / '04_run_level_210.csv')
        self.equal(len(rows), 210, 'Packaged main row count')
        self.check(set(self.frozen_fields).issubset(fields), '04 preserves every original frozen column')
        packaged_keys = [identity(row) for row in rows]
        self.equal(len(set(packaged_keys)), 210, '04 unique stage/map/repeat/mode')
        self.equal(set(packaged_keys), {identity(row) for row in self.original}, '04 exact original inventory')
        by_key = {identity(row): row for row in rows}
        for original in self.original:
            key = identity(original)
            row = by_key[key]
            for field in self.frozen_fields:
                self.equal(row.get(field), original[field], f'{key} preserved frozen field {field}')
            expected = self.mapping_artifact(original, row)
            for field in ('goal_complete', 'contact_run', 'safe_complete', 'mission_failure'):
                self.equal(boolean(row[field]), expected[field], f'{key} derived {field}')
            self.equal(row['map_label'], expected['map_label'], f'{key} map label')
            self.equal(row['environment'], expected['environment'], f'{key} environment')
            self.reconstructed[key] = expected
            self.counts['main_run_rows'] += 1
        self.equal({row['stage'] for row in rows}, {'seven_map_n10'}, 'Gate excluded from main04')
        exceptions = [row for row in self.reconstructed.values() if row['mission_failure']]
        self.equal({(row['map'], integer(row['repeat']), row['mode']) for row in exceptions},
                   {('forest_cluster_f01', 4, 'sector'), ('forest_cluster_f01', 5, 'sector'),
                    ('gapfree_d1_m01', 6, 'sector')}, 'Three preserved main failure cases')
        forest_r05 = self.reconstructed[('seven_map_n10', 'forest_cluster_f01', 5, 'sector')]
        self.check(not forest_r05['contact_run'] and not forest_r05['goal_complete']
                   and forest_r05['mission_failure'], 'Forest r05 no-contact incomplete failure retained')

    def all_raw_fields(self):
        fields, rows = read_csv(self.package / '05_all_recorded_fields_210.csv')
        self.equal(len(rows), 210, 'All-recorded-fields main count')
        expected_raw = {raw_identity(row): (key, row) for key, row in self.original_raw.items()
                        if key[0] == 'seven_map_n10'}
        self.equal(len(expected_raw), 210, 'Original raw main identities available')
        keys = [raw_identity(row) for row in rows]
        self.equal(len(set(keys)), 210, '05 unique map/run/mode')
        self.equal(set(keys), set(expected_raw), '05 exact original raw inventory')
        union_fields = set().union(*(set(row) for _, row in expected_raw.values()))
        self.equal({field for field in fields if not field.startswith('package_')},
                   union_fields, '05 exactly original raw field union plus prefixed metadata')
        frozen_by_key = {identity(row): row for row in self.original}
        for row in rows:
            key, original = expected_raw[raw_identity(row)]
            for field in union_fields:
                self.equal(row[field], original.get(field, ''), f'{key} unchanged raw field {field}')
            frozen = frozen_by_key[key]
            self.equal(row['package_map_label'], LABELS[frozen['map']], f'{key} raw package map label')
            self.equal(row['package_environment'], environment(frozen['map']), f'{key} raw package environment')
            self.equal(row['package_raw_file'], str(Path(frozen['directory']) / 'raw.csv'),
                       f'{key} raw package source path')
            self.equal(row['package_raw_sha256'], frozen['raw_sha256'], f'{key} raw package source hash')
            self.counts['full_raw_rows'] += 1
        self.counts['full_raw_original_columns'] = len(union_fields)

    @staticmethod
    def summary_expected(rows: list[dict]) -> dict:
        n = len(rows)
        expected = {'n': n, 'contact_episode_count': sum(integer(row['contacts']) for row in rows)}
        for field in ('goal_complete', 'contact_run', 'safe_complete', 'mission_failure'):
            count = sum(row[field] for row in rows)
            expected[field + '_count'] = count
            expected[field + '_rate_pct'] = 100 * count / n
        selections = {
            'observed_time_s': rows,
            'goal_time_s': [row for row in rows if row['goal_complete']],
            'safe_time_s': [row for row in rows if row['safe_complete']],
        }
        for prefix, selected in selections.items():
            values = [number(row['time_s']) for row in selected]
            expected[prefix + '_n'] = len(values)
            expected[prefix + '_mean'] = statistics.mean(values) if values else None
            expected[prefix + '_median'] = statistics.median(values) if values else None
            expected[prefix + '_min'] = min(values) if values else None
            expected[prefix + '_max'] = max(values) if values else None
            sd = statistics.stdev(values) if len(values) > 1 else None
            for suffix in ('sample_sd', 'sd', 'sd_sample', 'std', 'stddev', 'stdev'):
                expected[prefix + '_' + suffix] = sd
        for field in PRIMARY_METRICS + SUPPLEMENTARY_METRICS:
            metric_stats = numeric_stats(row.get(field) for row in rows)
            expected[field + '_mean'] = metric_stats['mean']
            expected[field + '_n_available'] = metric_stats['n']
        cycles = sum(integer(row['full_transitions']) for row in rows if row['full_transitions'])
        for field in ('adaptive_full_transitions_sum', 'full_transitions_sum'):
            expected[field] = cycles if rows[0]['mode'] == 'adaptive' else None
        transition_stats = numeric_stats(row['full_transitions'] for row in rows)
        expected['adaptive_full_transitions_mean'] = transition_stats['mean']
        expected['adaptive_full_transitions_median'] = transition_stats['median']
        for field in ('zone_disconnects', 'connected_retries', 'exhaustions', 'polyline_commits'):
            expected[field + '_sum'] = sum(integer(row[field]) for row in rows)
        return expected

    def grouped_summaries(self):
        all_rows = list(self.reconstructed.values())
        self.equal(len(all_rows), 210, 'All independently reconstructed runs available')
        count_fields = ('n', 'goal_complete_count', 'contact_run_count',
                        'safe_complete_count', 'mission_failure_count', 'contact_episode_count')
        rate_fields = tuple(field + '_rate_pct' for field in
                            ('goal_complete', 'contact_run', 'safe_complete', 'mission_failure'))
        required_means = ('observed_time_s_mean', 'goal_time_s_mean', 'safe_time_s_mean',
                          'cpu_cores_mean', 'cpu_core_s_mean', 'input_mib_s_mean',
                          'input_mib_run_mean', 'map_ms_mean', 'mapping_elapsed_s_mean',
                          'mapping_frames_mean')
        for filename, field, groups, row_count in [
            ('02_summary_by_map.csv', 'map_label', set(LABELS.values()), 21),
            ('03_summary_by_environment.csv', 'environment', {'Normal1-5', 'Urban', 'Forest'}, 9),
        ]:
            fields, published = read_csv(self.package / filename)
            self.equal(len(published), row_count, f'{filename} row count')
            expected_keys = {(group, mode) for group in groups for mode in MODES}
            keys = [(row['group'], row['mode']) for row in published]
            self.equal(set(keys), expected_keys, f'{filename} complete group/mode inventory')
            self.equal(len(set(keys)), row_count, f'{filename} unique group/mode inventory')
            self.check(set((*count_fields, *rate_fields, *required_means)).issubset(fields),
                       f'{filename} required count/rate/mean fields')
            for row in published:
                subset = [run for run in all_rows if run[field] == row['group'] and run['mode'] == row['mode']]
                expected = self.summary_expected(subset)
                context = f'{filename} {row["group"]}/{row["mode"]}'
                for column, value in expected.items():
                    if column in row:
                        self.close(row[column], value, f'{context} {column}')
                        self.counts['grouped_numeric_fields'] += 1
                # A directly named <run-field>_mean must not go unchecked.
                for column in fields:
                    if column.endswith('_mean') and column not in expected:
                        run_field = column[:-5]
                        if not all(run_field in run for run in subset):
                            # Existing per-run mean fields can retain their name
                            # when the summary reports their mean across runs.
                            run_field = column
                        if all(run_field in run for run in subset):
                            self.close(row[column], numeric_stats(run[run_field] for run in subset)['mean'],
                                       f'{context} independent extra mean {column}')
                        else:
                            self.check(False, f'{context} unknown/unverifiable mean column {column}')
                self.counts['map_summary_rows' if field == 'map_label' else 'environment_summary_rows'] += 1
        self.details['main_outcomes'] = {mode: self.summary_expected(
            [row for row in all_rows if row['mode'] == mode]) for mode in MODES}

    def supplementary_statistics(self):
        fields, published = read_csv(self.package / '07_supplementary_numeric_summary.csv')
        metrics = PRIMARY_METRICS + SUPPLEMENTARY_METRICS
        expected_keys = {(level, group, mode, metric)
                         for level, groups in [('map', set(LABELS.values())),
                                               ('environment', {'Normal1-5', 'Urban', 'Forest'})]
                         for group in groups for mode in MODES for metric in metrics}
        keys = [(row['level'], row['group'], row['mode'], row['metric']) for row in published]
        self.equal(len(published), len(expected_keys), '07 exact supplementary-statistic row count')
        self.equal(set(keys), expected_keys, '07 complete level/group/mode/metric inventory')
        self.equal(len(set(keys)), len(keys), '07 unique supplementary-statistic keys')
        self.check({'n_runs', 'n_available', 'n_missing', 'mean', 'median', 'sd', 'min', 'max'}.issubset(fields),
                   '07 required availability and sample-statistic fields')
        all_rows = list(self.reconstructed.values())
        for row in published:
            group_field = 'map_label' if row['level'] == 'map' else 'environment'
            subset = [run for run in all_rows if run[group_field] == row['group'] and run['mode'] == row['mode']]
            expected = numeric_stats(run.get(row['metric']) for run in subset)
            context = f'07 {row["level"]}/{row["group"]}/{row["mode"]}/{row["metric"]}'
            self.equal(integer(row['n_runs']), len(subset), context + ' n_runs')
            self.equal(integer(row['n_available']), expected['n'], context + ' n_available')
            self.equal(integer(row['n_missing']), len(subset) - expected['n'], context + ' n_missing')
            for column in ('mean', 'median', 'sd', 'min', 'max'):
                self.close(row[column], expected[column], context + ' ' + column)
                self.counts['supplementary_statistic_values'] += 1
            self.counts['supplementary_statistic_rows'] += 1

    def separate_gate(self):
        path = self.package / 'separate_gate' / 'forest_gate_run_level_30.csv'
        fields, rows = read_csv(path)
        self.equal(len(rows), 30, 'Separate gate run-level count')
        by_key = {identity(row): row for row in rows}
        self.equal(len(by_key), 30, 'Separate gate unique identity count')
        self.equal(set(by_key), {identity(row) for row in self.gate}, 'Separate gate exact source identities')
        reconstructed = []
        for original in self.gate:
            key = identity(original)
            row = by_key[key]
            for field, value in original.items():
                self.equal(row.get(field), value, f'{key} preserved gate frozen field {field}')
            expected = self.mapping_artifact(original, row, gate=True)
            reconstructed.append(expected)
            for field in ('goal_complete', 'contact_run', 'safe_complete', 'mission_failure'):
                self.equal(boolean(row[field]), expected[field], f'{key} gate derived {field}')
            self.counts['gate_run_rows'] += 1
        self.details['separate_gate_outcomes'] = {mode: self.summary_expected(
            [row for row in reconstructed if row['mode'] == mode]) for mode in MODES}

    def adaptive_contract(self):
        audit = read_json(self.package / 'source_frozen' / 'adaptive_contract_audit.json')
        self.check(audit['valid'] is True, 'Frozen adaptive actual-log contract valid')
        for stage, expected_flights, expected_cycles, source_rows in [
            ('seven_map_n10', 70, 509, self.original), ('forest_n10', 10, 109, self.gate),
        ]:
            rows = [row for row in audit['flight_audits'] if row['stage'] == stage]
            self.equal(len(rows), expected_flights, f'{stage} adaptive audit flight count')
            self.equal(sum(row['full_cycles'] for row in rows), expected_cycles,
                       f'{stage} independently summed full cycles')
            source = {identity(row): row for row in source_rows if row['mode'] == 'adaptive'}
            self.equal({identity(row) for row in rows}, set(source), f'{stage} adaptive audited inventory')
            for row in rows:
                original = source[identity(row)]
                self.equal(row['full_cycles'], integer(original['full_transitions']), 'Per-flight cycle CSV match')
                self.equal(row['stack_sha256'], original['stack_sha256'], 'Per-flight cycle stack hash match')
                self.equal(len(row['cycles']), row['full_cycles'], 'Per-flight complete cycle records')
                self.check(row['valid'] and all(cycle['valid'] for cycle in row['cycles']),
                           'Per-flight and individual-cycle audit validity')
            for metric in ('source_full_frame_matches', 'map_acknowledgements', 'path_ready', 'sector_returns'):
                self.equal(sum(row[metric] for row in rows), expected_cycles, f'{stage} summed {metric}')
            self.equal(sum(row['outstanding_cycles'] for row in rows), 0, f'{stage} outstanding cycles')
            self.counts['main_adaptive_cycles' if stage == 'seven_map_n10' else 'gate_adaptive_cycles'] = expected_cycles

    def map_assets(self):
        asset_dir = self.package / 'environment_maps'
        source_files = sorted(path for path in MAP_SOURCE.iterdir() if path.is_file())
        for source in source_files:
            self.equal(sha256(asset_dir / source.name), sha256(source), f'Unaltered map asset {source.name}')
            self.counts['map_source_files'] += 1
            if source.suffix in ('.png', '.svg', '.pdf'):
                self.counts['map_visual_files'] += 1
        source = read_json(asset_dir / 'map_sources.json')
        self.equal({row['map'] for row in source['maps']}, set(LABELS), 'Map-source record covers exact seven IDs')
        self.equal(len(source['maps']), 7, 'Map-source record count')
        self.check(all(value is True for value in source['checks'].values()), 'All recorded visualization checks true')
        self.equal(source['source_registries']['/root/super-sector-filter/results/v6_frozen_20261008/main_210.csv'],
                   sha256(FROZEN / 'main_210.csv'), 'Map provenance exact frozen main hash')
        self.equal(source['source_registries']['/root/super-sector-filter/results/v6_frozen_20261008/source_manifest.json'],
                   sha256(FROZEN / 'source_manifest.json'), 'Map provenance exact frozen source-manifest hash')
        for row in source['maps']:
            self.equal(row['cohort_runs_per_mode'], dict.fromkeys(MODES, 10), 'Map provenance cohort repetitions')
            for prefix in ('geometry', 'mission'):
                self.equal(sha256(Path(row[prefix + '_file'])), row[prefix + '_sha256'],
                           f'{row["map"]} exact source {prefix} hash')
        r2 = next(row for row in source['maps'] if row['map'] == 'gapfree_d1_m05r2')
        self.equal(r2['title'], 'Map 5 (R2)', 'Explicit Map5 R2 title')
        self.equal(r2['file_stem'], 'map5_r2', 'Explicit Map5 R2 file stem')
        self.equal(r2['geometry_sha256'],
                   'e31ec7536dd13d3b4f5baff5633d996997d873efce7c97951b0dd6a2414a0116', 'Correct R2 geometry')
        self.equal(len(r2['cylinders']), 410, 'Map5 R2 obstacle count')

    def run(self) -> dict:
        marker = self.package / 'build_complete.json'
        if not marker.is_file():
            self.errors.append('build_complete.json absent; unfinished package validation refused')
        else:
            self.phase('build_complete_marker', lambda: read_json(marker))
            self.phase('frozen_sources', self.frozen_sources)
            self.phase('main_run_level_and_mapping_windows', self.run_level)
            self.phase('main_all_recorded_raw_fields', self.all_raw_fields)
            self.phase('grouped_summaries', self.grouped_summaries)
            self.phase('supplementary_numeric_statistics', self.supplementary_statistics)
            self.phase('separate_gate', self.separate_gate)
            self.phase('adaptive_actual_log_contract', self.adaptive_contract)
            self.phase('unchanged_map_assets_and_provenance', self.map_assets)
        return {
            'schema': 'results-package-independent-validation-v1',
            'created_utc': datetime.now(timezone.utc).isoformat(),
            'package': str(self.package), 'original_frozen_source': str(FROZEN),
            'valid': not self.errors, 'simulation_launched': False,
            'source_files_modified': False, 'builder_imported': False,
            'checked_counts': dict(self.counts), 'sections': self.sections,
            'errors': self.errors, 'recomputed_results': self.details,
            'definitions': {
                'goal_complete': 'Frozen mission completion independently of contact',
                'contact_run': 'At least one received-sample independent-solid contact episode',
                'safe_complete': 'goal_complete AND NOT contact_run',
                'mission_failure': 'contact_run OR NOT goal_complete; union, not arithmetic sum',
                'sample_sd': 'Sample standard deviation with denominator n-1',
                'mapping_elapsed_s': 'Sum of recorded Total elapsed seconds in filtered [perf_row_start:perf_row_end)',
                'mapping_mean': 'Unweighted arithmetic mean across runs; not pooled-frame mean',
                'mapping_p95_ms': 'Linear empirical 95th percentile of per-frame Total, in milliseconds',
                'mapping_window_frames_checked': 'main_mapping_window_frames excludes gate; gate_mapping_window_frames separate; mapping_window_frames is their sum',
                'unavailable_optional_metrics': 'Blank unavailable means and n_available=0, not substituted zero',
                'ack_latency_availability': 'Latency suppressed when corresponding raw ACK count is missing or zero; raw05 remains unchanged',
                'separate_gate': '30 prerelease forest-gate flights excluded from main210 and main509 cycles',
            },
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    validator = Validator(args.package.resolve())
    report = validator.run()
    # Only the caller-selected report is written; no source/package inputs change.
    with args.output.open('w', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'valid': report['valid'], 'checked_counts': report['checked_counts'],
                      'error_count': len(report['errors']), 'output': str(args.output)}, ensure_ascii=False))
    if not report['valid']:
        for error in report['errors'][:20]:
            print(error, file=sys.stderr)
    return 0 if report['valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
