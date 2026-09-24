"""Scenario cohorts stay separate in offline summaries and detailed reports."""
import csv
import json
from pathlib import Path
import statistics
import sys

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import run_scenario7_n10 as runner


def observation(name, mode, cost, **updates):
    value = dict(map=name, mode=mode, costs_valid=True, contact_known=True,
                 analytic_contact_episodes=0, safe_complete=True, success='True',
                 mission_time_s=cost, end_to_end_cpu_cores_mean=cost,
                 end_to_end_cpu_core_s=cost, map_payload_mib_s=cost,
                 input_mib_per_run=cost, total_ms_mean=cost)
    value.update(updates)
    return value


def read_csv(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def sample_records():
    g1, g2 = runner.MAPS[:2]
    urban, forest = runner.MAPS[-2:]
    return [observation(g1, 'full', 2), observation(g1, 'full', 4), observation(g2, 'full', 12),
            observation(g1, 'sector', 3), observation(urban, 'full', 100),
            observation(urban, 'sector', 25), observation(forest, 'full', 1000),
            observation(forest, 'sector', 900),
            observation(g1, 'full', 999999, costs_valid=False, success='False',
                        safe_complete=False, analytic_contact_episodes=2)]


def test_group_means_keep_urban_and_forest_outliers_out_of_normal():
    rows = runner.grouped_rows(sample_records())
    lookup = {(row['group'], row['mode']): row for row in rows}
    normal = lookup['normal', 'full']
    assert len(rows) == 9
    assert normal['cpu_cores_mean'] == 6
    assert normal['cpu_cores_n'] == normal['performance_valid_runs'] == 3
    assert normal['cpu_cores_sd'] == pytest.approx(statistics.stdev([2, 4, 12]))
    assert normal['planned'] == 50 and normal['recorded_runs'] == 4
    assert normal['contact_runs'] == 1 and normal['contact_episodes'] == 2
    assert normal['goal_reached'] == normal['safe_completed'] == 3
    assert normal['cost_weighting'].endswith('not_equal_map_weighting')
    assert json.loads(normal['performance_valid_runs_by_map'])[runner.MAPS[0]] == 2
    assert json.loads(normal['performance_valid_runs_by_map'])[runner.MAPS[1]] == 1
    assert lookup['urban', 'full']['cpu_cores_mean'] == 100
    assert lookup['forest', 'full']['cpu_cores_mean'] == 1000
    assert all(row['map'] != 'ALL' for row in rows)


def test_reductions_use_full_from_the_same_group_and_missing_stays_missing():
    lookup = {(row['group'], row['mode']): row for row in runner.grouped_rows(sample_records())}
    for group, expected in (('normal', 50), ('urban', 75), ('forest', 10)):
        sector = lookup[group, 'sector']
        for metric in ('cpu_cores', 'cpu_core_s', 'input_mib_s', 'input_mib_per_run', 'map_ms'):
            assert sector[metric + '_reduction_vs_full_pct'] == pytest.approx(expected)
        adaptive = lookup[group, 'adaptive']
        assert adaptive['cpu_cores_n'] == 0
        assert adaptive['cpu_cores_mean'] is adaptive['cpu_cores_sd'] is None
        assert adaptive['cpu_cores_reduction_vs_full_pct'] is None
        assert adaptive['contact_episodes'] is None
    forest_only = runner.grouped_rows([observation(runner.MAPS[-1], 'sector', 5)], (runner.MAPS[-1],))
    assert all(row['cpu_cores_reduction_vs_full_pct'] is None for row in forest_only)


def test_subset_outputs_exclude_other_maps_and_alias_has_only_group_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, 'observations', lambda _: sample_records())
    selected = (runner.MAPS[1], runner.MAPS[-2])
    map_rows = runner.write_progress(tmp_path, selected)
    assert len(map_rows) == 6 and {row['map'] for row in map_rows} == set(selected)
    grouped = read_csv(tmp_path / 'summary_by_group.csv')
    assert grouped == read_csv(tmp_path / 'summary_overall.csv')
    assert len(grouped) == 6 and {row['group'] for row in grouped} == {'normal', 'urban'}
    assert all(row['planned'] == '10' for row in grouped)
    assert all(row['map'] != 'ALL' for row in grouped)
    normal = next(row for row in grouped if row['group'] == 'normal' and row['mode'] == 'full')
    assert float(normal['cpu_cores_mean']) == 12
    assert normal['cpu_cores_n'] == '1' and normal['cpu_cores_sd'] == ''
    assert normal['maps_in_group'] == runner.MAPS[1]
    transitions = read_csv(tmp_path / 'adaptive_transitions_by_map.csv')
    assert len(transitions) == 2 and {row['map'] for row in transitions} == set(selected)
    assert (tmp_path / 'summary_by_group.md').is_file()


def test_empty_full_suite_keeps_21_map_rows_and_9_group_rows_without_zero_cost(tmp_path):
    rows = runner.write_progress(tmp_path)
    groups = read_csv(tmp_path / 'summary_by_group.csv')
    assert len(rows) == 21 and len(groups) == 9
    assert {row['group']: row['planned'] for row in groups} == {'normal': '50', 'urban': '10', 'forest': '10'}
    assert all(row['cpu_cores_mean'] == '' and row['cpu_cores_n'] == '0' for row in groups)
    assert all(row['contact_episodes'] == '' for row in groups)
    assert (tmp_path / 'summary_by_group.csv').read_bytes() == (tmp_path / 'summary_overall.csv').read_bytes()


def test_partial_unknown_contacts_and_missing_metric_are_never_fabricated_zero():
    name = runner.MAPS[-2]
    records = [observation(name, 'full', None, contact_known=False, analytic_contact_episodes=None,
                           success='False', safe_complete=False)]
    row = next(row for row in runner.grouped_rows(records, (name,)) if row['mode'] == 'full')
    assert row['recorded_runs'] == 1 and row['contact_unknown_runs'] == 1
    assert row['contact_episodes'] is None and row['cpu_cores_mean'] is None
    assert row['cpu_cores_n'] == 0 and row['safe_completed'] == row['goal_reached'] == 0


def make_raw_roots(root, maps):
    for phase in runner.PHASES:
        for name in maps:
            folder = root / phase / name / 'run1'
            folder.mkdir(parents=True)
            (folder / 'raw.csv').write_text('map,mode,run\n')


def test_detailed_reports_use_group_member_roots_and_keep_outcome_quality_loader(tmp_path, monkeypatch):
    make_raw_roots(tmp_path, runner.MAPS)
    calls = []
    original_fp, original_load = runner.base.reports.protocol_fingerprint, runner.base.reports.load_runs
    def load_runs(roots, repo):
        name = roots[0].name
        return [dict(map=name, metrics={'success': 0, 'end_to_end_cpu_cores_mean': None},
                     cost_comparison_admission={'valid': False})], ['failed outcome retained; cost N/A']
    monkeypatch.setattr(runner.previous, 'report_load_runs', load_runs)
    def detailed(arguments):
        roots = [Path(arguments[index + 1]) for index, value in enumerate(arguments) if value == '--campaign']
        output = Path(arguments[arguments.index('--output') + 1])
        runs, warnings = runner.base.reports.load_runs(roots, runner.REPO)
        assert runs[0]['metrics']['success'] == 0
        assert runs[0]['metrics']['end_to_end_cpu_cores_mean'] is None
        assert runs[0]['cost_comparison_admission']['valid'] is False
        assert warnings == ['failed outcome retained; cost N/A']
        assert runner.base.reports.protocol_fingerprint is runner.previous.report_protocol_fingerprint
        calls.append((roots, output))
    monkeypatch.setattr(runner.base.reports, 'main', detailed)
    records = runner.reports(tmp_path)
    assert len(calls) == len(records) == 6
    assert all(record['state'] == 'WRITTEN' for record in records)
    for roots, output in calls:
        group = output.name
        phase = output.parent.name.removeprefix('report_')
        assert roots == [tmp_path / phase / name for name in runner.report_groups()[group]]
        assert output == tmp_path / ('report_' + phase) / group
        assert all(path != tmp_path / phase for path in roots)
    assert runner.base.reports.protocol_fingerprint is original_fp
    assert runner.base.reports.load_runs is original_load


def test_detailed_reports_subset_missing_data_and_errors_stay_separate(tmp_path, monkeypatch):
    selected = (runner.MAPS[0], runner.MAPS[-2])
    make_raw_roots(tmp_path, (runner.MAPS[-2],))
    calls = []
    def failing(arguments):
        calls.append(arguments)
        raise SystemExit('synthetic unreadable report')
    monkeypatch.setattr(runner.base.reports, 'main', failing)
    records = runner.reports(tmp_path, selected)
    assert len(records) == 4 and len(calls) == 2
    assert all(record['state'] == ('NO_RAW_ROWS' if record['group'] == 'normal' else 'REPORT_ERROR') for record in records)
    assert {record['group'] for record in records} == {'normal', 'urban'}
    assert all(runner.MAPS[-1] not in str(arguments) for arguments in calls)


def test_detailed_loader_rejects_out_of_group_rows(monkeypatch):
    monkeypatch.setattr(runner.previous, 'report_load_runs', lambda *_: ([dict(map=runner.MAPS[-1])], []))
    with pytest.raises(ValueError, match='outside'):
        runner._group_report_load_runs([], runner.REPO, runner.MAPS[:5])
