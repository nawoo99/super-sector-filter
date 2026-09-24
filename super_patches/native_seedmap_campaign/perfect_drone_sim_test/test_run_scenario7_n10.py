"""Offline coverage, reporting semantics and manual controller isolation."""
import csv
from pathlib import Path
import sys
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import run_scenario7_n10 as runner


def test_210_primary_flights_and_separate_21_preflight(tmp_path):
    # Map contexts normally register at CLI admission; don't raycast or run ROS.
    with mock.patch.object(runner.base, 'static_commands', return_value=[]):
        commands = runner.build_plan(tmp_path)
    primary = [c for c in commands if c['phase'] == 'test10']
    preflight = [c for c in commands if c['phase'] == 'preflight']
    assert len(primary) == 70 and len(preflight) == 7
    assert sum(len(c['modes']) for c in primary) == 210
    assert sum(len(c['modes']) for c in preflight) == 21
    identities = {(c['map'], c['run'], mode) for c in commands for mode in c['modes']}
    assert len(identities) == 231
    for name in runner.MAPS:
        selected = [c for c in primary if c['map'] == name]
        assert {c['repeat'] for c in selected} == set(range(1, 11))
        assert len({tuple(c['modes']) for c in selected}) == 6
        for item in selected:
            cmd = item['command']
            assert cmd[1].endswith('scenario7_cpu_compare.py')
            assert '--profile-cpu' not in cmd
            assert '--small-pool-profile-reference' in cmd
            assert '--time-reference-folder' not in cmd
            assert '--async-certified-recovery' in cmd
            assert '--extended-demand-lease' not in cmd
            assert cmd[cmd.index('--side-executor-threads')+1] == '3'


def test_map_subset_and_rejection(tmp_path):
    with mock.patch.object(runner.base, 'static_commands', return_value=[]):
        plan = runner.build_plan(tmp_path, maps=(runner.MAPS[-2], runner.MAPS[-1]))
    assert len(plan) == 22
    assert {c['map'] for c in plan} == set(runner.MAPS[-2:])
    for bad in ((), (runner.MAPS[0], runner.MAPS[0]), ('seed1',)):
        with pytest.raises(ValueError):
            runner.build_plan(tmp_path, maps=bad)


def test_full_transition_is_source_edge_not_initial_state_or_recovery_count():
    summary = {'source_acquisition': {'frames': [dict(frame=i+1, full=v) for i, v in enumerate((1, 1, 0, 1, 0, 0, 1))]}}
    assert runner.source_transitions(summary, 'adaptive') == 2
    assert runner.source_transitions(summary, 'sector') is None
    assert runner.source_transitions({}, 'adaptive') is None
    summary['source_acquisition']['frames'][2]['frame'] = 1
    assert runner.source_transitions(summary, 'adaptive') is None


def test_contact_completion_and_unknown_are_distinct():
    row = dict(success='True', contact_known=True, analytic_contact_episodes=1,
               safe_complete=False, costs_valid=True, mission_time_s=50,
               end_to_end_cpu_cores_mean=.5, end_to_end_cpu_core_s=25,
               map_payload_mib_s=4, input_mib_per_run=200, total_ms_mean=10)
    contact = runner.summarize_rows([row], 'U1', runner.MAPS[-2], 'sector', 10)
    assert (contact['goal_reached'], contact['safe_completed'], contact['contact_runs']) == (1, 0, 1)
    unknown = runner.summarize_rows([dict(row, contact_known=False, analytic_contact_episodes=None)], 'U1', runner.MAPS[-2], 'sector', 10)
    assert unknown['contact_unknown_runs'] == 1
    assert unknown['contact_episodes'] is None
    assert unknown['safe_completed'] == 0


def test_invalid_cost_excluded_not_failed_outcome():
    row = dict(success='False', contact_known=True, analytic_contact_episodes=1,
               safe_complete=False, costs_valid=False, end_to_end_cpu_cores_mean=9)
    result = runner.summarize_rows([row], 'G1', runner.MAPS[0], 'full', 10)
    assert result['recorded_runs'] == 1 and result['contact_runs'] == 1
    assert result['performance_valid_runs'] == 0 and result['cpu_cores_mean'] is None


def test_empty_progress_has_21_rows_and_no_fabricated_zero(tmp_path):
    result = runner.write_progress(tmp_path)
    assert len(result) == 21
    assert all(r['planned'] == 10 and r['recorded_runs'] == 0 for r in result)
    assert all(r['cpu_cores_mean'] is None and r['contact_episodes'] is None for r in result)
    with (tmp_path/'summary_overall.csv').open() as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 3 and all(r['planned'] == '70' for r in rows)
    assert (tmp_path/'adaptive_transitions_by_map.csv').is_file()


def test_report_path_never_launches_or_validates_current_transport(tmp_path):
    runner.base.save(tmp_path/'plan.json', dict(schema=runner.SCHEMA, maps=list(runner.MAPS)))
    with mock.patch.object(runner, 'reports') as reports, mock.patch.object(runner.base, 'execute') as execute, mock.patch.object(runner.support, 'register_maps') as register:
        assert runner.main(['--report', str(tmp_path)]) == 0
    reports.assert_called_once()
    execute.assert_not_called()
    register.assert_not_called()


def test_existing_result_directory_never_overwritten(tmp_path):
    with mock.patch.object(runner.base, 'execute') as execute:
        with pytest.raises(SystemExit):
            runner.main(['--output', str(tmp_path)])
    execute.assert_not_called()


def _cached_contact_fixture(tmp_path, monkeypatch):
    """Isolate expensive replay while exercising its complete file dependency key."""
    import json
    name = runner.MAPS[-2]
    package = tmp_path / 'package'
    map_dir = package / 'pcd/seed_maps'
    map_dir.mkdir(parents=True)
    audit = tmp_path / f'{name}_run1_full.attempt1.solid_audit.json'
    pcd = map_dir / f'{name}.pcd'
    solid = map_dir / f'{name}_geometry.json'
    native = tmp_path / f'{name}_run1_full.attempt1.json'
    odometry = tmp_path / f'{name}_run1_full.attempt1.odometry.csv'
    dependencies = [pcd, solid, native, odometry]
    document = dict(map=name, contact_episodes=0, pcd_path=str(pcd), geometry_path=str(solid),
                    odometry_csv=str(tmp_path / 'old_scratch' / odometry.name),
                    native_monitor_json=str(tmp_path / 'old_scratch' / native.name))
    for label in ('base_monitor', 'observer_code', 'geometry_code', 'adapter_code'):
        path = tmp_path / (label + '.py')
        document[label + '_path'] = str(path)
        dependencies.append(path)
    for path in dependencies:
        path.write_text('first')
    audit.write_text(json.dumps(document))
    monkeypatch.setattr(runner.support, 'PACKAGE', package)
    runner._CONTACT_EVIDENCE_CACHE.clear()
    validator = mock.Mock(side_effect=lambda *_: all(path.is_file() for path in dependencies))
    monkeypatch.setattr(runner.geometry, 'validate_evidence', validator)
    return name, audit, dependencies, validator


def test_contact_cache_reuses_only_unchanged_complete_dependencies(tmp_path, monkeypatch):
    import os
    name, audit, dependencies, validator = _cached_contact_fixture(tmp_path, monkeypatch)
    assert runner.contact_evidence(audit, name)[1]
    assert runner.contact_evidence(audit, name)[1]
    assert validator.call_count == 1
    # Each relocated sidecar, map asset and recorded code file invalidates the
    # successful replay, even for equal-length edits with restored mtime.
    for path in dependencies:
        original = path.stat()
        path.write_text('other')
        os.utime(path, ns=(original.st_atime_ns, original.st_mtime_ns))
        calls = validator.call_count
        assert runner.contact_evidence(audit, name)[1]
        assert validator.call_count == calls + 1
        assert runner.contact_evidence(audit, name)[1]
        assert validator.call_count == calls + 1


def test_contact_cache_missing_recreated_and_retargeted_inputs_revalidate(tmp_path, monkeypatch):
    name, audit, dependencies, validator = _cached_contact_fixture(tmp_path, monkeypatch)
    assert runner.contact_evidence(audit, name)[1]
    missing = dependencies[2]  # Relocated native result, not old scratch provenance.
    missing.unlink()
    assert not runner.contact_evidence(audit, name)[1]
    assert validator.call_count == 2
    missing.write_text('first')
    assert runner.contact_evidence(audit, name)[1]
    assert validator.call_count == 3
    target = tmp_path / 'replacement_native.json'
    target.write_text('first')
    missing.unlink()
    missing.symlink_to(target)
    assert runner.contact_evidence(audit, name)[1]
    assert validator.call_count == 4
    audit.unlink()
    assert not runner.contact_evidence(audit, name)[1]
    assert not runner._CONTACT_EVIDENCE_CACHE


def test_contact_cache_detects_current_code_changes_and_changes_during_replay(tmp_path, monkeypatch):
    name, audit, dependencies, validator = _cached_contact_fixture(tmp_path, monkeypatch)
    current_code = tmp_path / 'current_observer.py'
    current_code.write_text('first')
    monkeypatch.setattr(runner.geometry, '__file__', str(current_code))
    assert runner.contact_evidence(audit, name)[1]
    current_code.write_text('other')
    assert runner.contact_evidence(audit, name)[1]
    assert validator.call_count == 2
    runner._CONTACT_EVIDENCE_CACHE.clear()
    def changing_validator(*_):
        dependencies[3].write_text('modified during analytic replay')
        return True
    validator.side_effect = changing_validator
    assert not runner.contact_evidence(audit, name)[1]
    assert not runner._CONTACT_EVIDENCE_CACHE


def test_contact_cache_is_bounded(tmp_path, monkeypatch):
    name, audit, dependencies, validator = _cached_contact_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(runner, '_CONTACT_EVIDENCE_CACHE_LIMIT', 2)
    runner._CONTACT_EVIDENCE_CACHE[('older', name)] = ('old snapshot',)
    runner._CONTACT_EVIDENCE_CACHE[('recent', name)] = ('another snapshot',)
    assert runner.contact_evidence(audit, name)[1]
    assert len(runner._CONTACT_EVIDENCE_CACHE) == 2
    assert ('older', name) not in runner._CONTACT_EVIDENCE_CACHE
