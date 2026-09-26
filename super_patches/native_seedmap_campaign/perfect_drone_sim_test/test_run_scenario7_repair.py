"""No-ROS repair-controller isolation, planning, reporting and admission tests."""
import csv
import json
from pathlib import Path
import sys
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import run_scenario7_repair as repair
import run_scenario7_n10 as original


@pytest.mark.parametrize('rounds', [1, 3, 10])
def test_round_counts_and_independent_child_cohorts(tmp_path, rounds):
    runner = repair.build_namespace(rounds)
    with mock.patch.object(runner.base, 'static_commands', return_value=[]):
        commands = runner.build_plan(tmp_path)
    on = [item for item in commands if item['phase'] == 'preflight']
    off = [item for item in commands if item['phase'] == 'test10']
    assert len(on) == 7 and len(off) == rounds * 7
    assert len({(item['map'], item['run'], mode) for item in commands for mode in item['modes']}) == 21 * (rounds + 1)
    assert {item['repeat'] for item in off} == set(range(1, rounds + 1))
    for item in commands:
        command = item['command']
        assert command[1].endswith('scenario7_cpu_compare_v3.py')
        assert command[command.index('--candidate') + 1] == repair.CANDIDATE
        assert ('--profile-cpu' in command) == (item['phase'] == 'preflight')
        assert ('--small-pool-profile-reference' in command) == (item['phase'] == 'test10')
        assert '--async-certified-recovery' in command
        assert '--extended-demand-lease' not in command
    assert original.COUNTS == {'preflight': 1, 'test10': 10}
    assert original.CANDIDATE == 'c24_scenario7_n10_missions_v2'
    assert runner.base is not original.base
    assert runner.base.static is not original.base.static
    assert runner.base.MEMORY_RUNAWAY_MIB == original.base.MEMORY_RUNAWAY_MIB == 4608
    assert runner.base.execute.__code__ is original.base.execute.__code__


def test_static_commands_bind_only_new_overlay_wrappers(tmp_path):
    runner = repair.build_namespace(1)
    fixture = [dict(name='static_x_full_late', phase='static', command=['python', 'old_fixture.py', '--config', 'x.yaml']),
               dict(name='rviz_x', phase='static', command=['python', 'old_rviz.py', '--config', 'x.yaml']),
               dict(name='accept_x', phase='static', command=['python', 'old_static.py', 'create', '--map', 'x'])]
    with mock.patch.object(runner.base, 'static_commands', side_effect=lambda *_: fixture):
        commands = runner.build_plan(tmp_path, (runner.MAPS[0],))
    assert [item['command'][2] for item in commands[:3]] == ['transport', 'rviz', 'static']
    assert all(item['command'][1].endswith('scenario7_repair_runtime.py') for item in commands[:3])
    assert commands[2]['command'][3:] == ['create', '--map', 'x']


@pytest.mark.parametrize('rounds', [1, 10])
def test_grouped_reports_use_actual_rounds_without_all_seven_pool(tmp_path, rounds):
    runner = repair.build_namespace(rounds)
    rows = runner.write_progress(tmp_path)
    assert len(rows) == 21 and {row['planned'] for row in rows} == {rounds}
    with (tmp_path / 'summary_by_group.csv').open() as stream:
        grouped = list(csv.DictReader(stream))
    assert len(grouped) == 9
    assert {row['group']: int(row['planned']) for row in grouped} == {
        'normal': 5 * rounds, 'urban': rounds, 'forest': rounds}
    assert all(row['cpu_cores_mean'] == '' for row in grouped)
    text = (tmp_path / 'summary_by_map.md').read_text()
    assert f'× {rounds}회 = {21 * rounds}회' in text
    assert f'모드별 계획 {5 * rounds}회' in (tmp_path / 'summary_by_group.md').read_text()


def test_subset_counts_and_mission_binding(tmp_path):
    runner = repair.build_namespace(1)
    maps = (runner.MAPS[0], runner.MAPS[3], runner.MAPS[5])
    with mock.patch.object(runner.base, 'static_commands', return_value=[]):
        commands = runner.build_plan(tmp_path, maps)
    assert len(commands) == 6
    assert all(item['mission']['goal_count'] == 5 for item in commands)
    rows = runner.grouped_rows([], maps)
    assert {row['group']: row['planned'] for row in rows} == {'normal': 2, 'urban': 1}


def test_dry_run_never_executes_and_freezes_actual_counts(tmp_path, monkeypatch):
    runner = repair.build_namespace(1)
    output = tmp_path / 'new_repair'
    monkeypatch.setattr(runner.support, 'register_maps', lambda: {'valid': True})
    monkeypatch.setattr(runner, 'freeze_sources', lambda *_: ({}, {'new_candidate': True}))
    monkeypatch.setattr(runner.base, 'static_commands', lambda *_: [])
    with mock.patch.object(runner.base, 'execute') as execute:
        assert runner.main(['--output', str(output), '--dry-run']) == 0
    execute.assert_not_called()
    plan = json.loads((output / 'plan.json').read_text())
    status = json.loads((output / 'status.json').read_text())
    phase = json.loads((output / 'test10/plan.json').read_text())
    assert plan['rounds'] == 1 and plan['schema'] == repair.SCHEMA
    assert plan['candidate'] == repair.CANDIDATE
    assert plan['profiled_preflight_flights'] == plan['unprofiled_primary_flights'] == 21
    assert phase['unprofiled_runs_per_mode'] == 1
    assert status['requested_off_flights'] == 21 and status['planned_flights'] == 42
    assert status['actual_flights_started'] == 0 and status['automatic_retry'] is False


def test_early_report_uses_stored_rounds_without_admission_or_execution(tmp_path, monkeypatch):
    runner = repair.build_namespace(1)
    (tmp_path / 'plan.json').write_text(json.dumps(dict(schema=repair.SCHEMA, rounds=1, maps=list(runner.MAPS))))
    factory = mock.Mock(return_value=runner)
    monkeypatch.setattr(repair, 'build_namespace', factory)
    with mock.patch.object(runner, 'reports') as reports, mock.patch.object(runner.support, 'register_maps') as admission, mock.patch.object(runner.base, 'execute') as execute:
        assert repair.main(['--report=' + str(tmp_path)]) == 0
    factory.assert_called_once_with(1)
    reports.assert_called_once()
    admission.assert_not_called()
    execute.assert_not_called()
    with pytest.raises(SystemExit):
        repair.main(['--report', str(tmp_path), '--rounds', '10'])


@pytest.mark.parametrize('value', [0, -1, 11, True, 1.5])
def test_invalid_rounds_rejected(value):
    with pytest.raises(ValueError):
        repair.build_namespace(value)


def test_existing_output_refused_without_execution(tmp_path):
    runner = repair.build_namespace(1)
    with mock.patch.object(runner.base, 'execute') as execute, pytest.raises(SystemExit):
        runner.main(['--output', str(tmp_path)])
    execute.assert_not_called()


def test_exact_source_allowlist_does_not_admit_binary_map_or_result_changes(tmp_path):
    source = tmp_path / 'allowed.cpp'
    binary = tmp_path / 'old_binary'
    pcd = tmp_path / 'map.pcd'
    result = tmp_path / 'old_raw.csv'
    files = (source, binary, pcd, result)
    for path in files:
        path.write_text('original')
    inventory = {str(path): repair.sha(path) for path in files}
    source.write_text('repair')
    changes = repair.verify_prior_inventory(inventory, allowed={str(source)})
    assert len(changes) == 1 and changes[0]['path'] == str(source)
    for path in files[1:]:
        path.write_text('changed')
        with pytest.raises(ValueError, match='Unadmitted'):
            repair.verify_prior_inventory(inventory, allowed={str(source)})
        path.write_text('original')
    source.unlink()
    with pytest.raises(ValueError, match='missing'):
        repair.verify_prior_inventory(inventory, allowed={str(source)})


def test_frozen_v2_hash_and_checked_adaptations_fail_closed(tmp_path, monkeypatch):
    source = tmp_path / 'controller.py'
    source.write_text(repair.PREVIOUS.read_text().replace('planned_flights=33*len(maps)', 'planned_flights=999'))
    monkeypatch.setattr(repair, 'PREVIOUS', source)
    with pytest.raises(ValueError, match='Frozen v2'):
        repair.build_namespace(1)
    monkeypatch.setattr(repair, 'PREVIOUS_SHA256', repair.sha(source))
    with pytest.raises(ValueError, match='adaptation changed'):
        repair.build_namespace(1)


def test_unlisted_new_production_header_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(repair, 'SOURCE', tmp_path)
    header = tmp_path / 'super_planner/include/unapproved.hpp'
    header.parent.mkdir(parents=True)
    header.write_text('// Not admitted')
    with pytest.raises(ValueError, match='Unadmitted new production'):
        repair.verify_production_additions({})
    assert repair.verify_production_additions({str(header): repair.sha(header)}) == []


def test_contact_cache_binds_current_and_recorded_index_dependencies(tmp_path, monkeypatch):
    runner = repair.build_namespace(1)
    name = runner.MAPS[-2]
    package = tmp_path / 'package'
    directory = package / 'pcd/seed_maps'
    directory.mkdir(parents=True)
    audit = tmp_path / f'{name}_run1_full.attempt1.solid_audit.json'
    pcd = directory / f'{name}.pcd'
    solid = directory / f'{name}_geometry.json'
    native = tmp_path / f'{name}_run1_full.attempt1.json'
    odometry = tmp_path / f'{name}_run1_full.attempt1.odometry.csv'
    dependencies = [pcd, solid, native, odometry]
    document = dict(map=name, contact_episodes=0, pcd_path=str(pcd), geometry_path=str(solid))
    for label in ('base_monitor', 'observer_code', 'geometry_code', 'adapter_code', 'index_code'):
        path = tmp_path / (label + '.py')
        document[label + '_path'] = str(path)
        dependencies.append(path)
    current_index = tmp_path / 'current_index.py'
    dependencies.append(current_index)
    for path in dependencies:
        path.write_text('original')
    audit.write_text(json.dumps(document))
    monkeypatch.setattr(runner.support, 'PACKAGE', package)
    monkeypatch.setattr(repair.pcd_index, '__file__', str(current_index))
    validator = mock.Mock(side_effect=lambda *_: all(path.is_file() for path in dependencies))
    monkeypatch.setattr(runner.geometry, 'validate_evidence', validator)
    assert runner.geometry is repair.observer
    assert runner.contact_evidence(audit, name)[1]
    assert runner.contact_evidence(audit, name)[1]
    assert validator.call_count == 1
    for path in (Path(document['index_code_path']), current_index):
        calls = validator.call_count
        path.write_text('modified')
        assert runner.contact_evidence(audit, name)[1]
        assert validator.call_count == calls + 1
        assert runner.contact_evidence(audit, name)[1]
        assert validator.call_count == calls + 1
    current_index.unlink()
    assert not runner.contact_evidence(audit, name)[1]
