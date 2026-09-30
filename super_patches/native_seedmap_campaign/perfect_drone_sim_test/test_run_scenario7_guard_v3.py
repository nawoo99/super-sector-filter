"""Offline v3 isolation, near-hit profile and actual-runtime identity checks."""
import ast
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import run_scenario7_guard_v3 as guard
import scenario7_guard_v3_cpu_compare as child


def markers():
    return ('[ASYNC_GENERATE_TRAJ] enabled=true executor=existing_replan '
            'main_finalization=true default_off=true\n'
            '[OCCUPANCY_ONLY_RANGE] enabled=1 hit_min=0.1 free_ray_min=0.5 startup_clear_radius=0.5\n'
            'Load param super_planner/guard_topology_reroute/local_escape_max_distance_m success: 1.2\n'
            'Load param super_planner/guard_topology_reroute/local_escape_distance_steps success: 2\n')


@pytest.mark.parametrize('rounds', [1, 3, 10])
def test_plan_counts_profiles_fresh_references_and_v2_isolation(tmp_path, rounds):
    runner = guard.build_namespace(rounds)
    with mock.patch.object(runner.base, 'static_commands', return_value=[]):
        commands = runner.build_plan(tmp_path)
    assert len(commands) == 7 * (rounds + 1)
    assert len({(row['map'], row['run'], mode) for row in commands for mode in row['modes']}) == 21 * (rounds + 1)
    for item in commands:
        command = item['command']
        assert command[1].endswith('scenario7_guard_v3_cpu_compare.py')
        assert command[command.index('--candidate') + 1] == guard.CANDIDATE
        assert command[command.index('--side-executor-threads') + 1] == '3'
        assert '--extended-demand-lease' not in command
        assert item['async_generate_trajectory'] and item['mission']['goal_count'] == 5
        assert item['run'] >= 80000
        for mode, profile in child.PROFILES.items():
            assert command[command.index('--' + mode + '-config') + 1] == profile
        if item['phase'] == 'preflight':
            assert '--profile-cpu' in command and '--small-pool-profile-reference' not in command
        else:
            reference = command[command.index('--small-pool-profile-reference') + 1]
            assert reference.startswith(str(tmp_path / 'preflight' / item['map']))
            assert 'run8000' in reference and '--profile-cpu' not in command
    assert runner.CANDIDATE == 'c28_observed_nearfield_async_generate'
    assert runner.base.MEMORY_RUNAWAY_MIB == 4608
    assert runner.repair_runtime.install == guard.DEFAULT_INSTALL
    assert guard.previous.CANDIDATE == 'c27_guard_contract_v2'
    assert guard.previous.PRIOR_ROOT != guard.PRIOR_ROOT
    assert guard.previous.ADDED_CPP != guard.ADDED_CPP


@pytest.mark.parametrize('install', [child.runtime.BASE_INSTALL, child.runtime.DEFAULT_INSTALL,
                                     child.previous.DEFAULT_INSTALL, child.previous.DEFAULT_INSTALL / 'subdir',
                                     Path('relative/install')])
def test_no_preserved_or_relative_install(install):
    with pytest.raises(ValueError):
        guard.selected_install(install)
    with pytest.raises(ValueError):
        child.selected_install(install)


def test_exact_source_change_allowlist_and_preserved_v2_inventory():
    assert set(guard.MODIFIED_CPP) - set(guard.previous.MODIFIED_CPP) == {
        'rog_map/include/rog_map/rog_map_core/config.hpp',
        'super_planner/include/fsm/fsm.h', 'super_planner/src/super_core/fsm.cpp'}
    adapted = guard.private_previous().private_previous()
    assert adapted.PRIOR_INVENTORY == guard.PRIOR_INVENTORY
    assert adapted.PRIOR_INVENTORY_SHA256 == guard.PRIOR_INVENTORY_SHA256
    assert adapted.MODIFIED_CPP == guard.MODIFIED_CPP
    assert 'super_planner/test/async_from_rest_source_contract_test.py' in guard.ADDED_TEST_SCRIPTS
    assert len(adapted.admitted_cpp_paths()) == 18
    assert str(child.previous.DEFAULT_INSTALL) not in '\n'.join(adapted.admitted_cpp_paths())


def test_execute_keeps_memory_sentinel_and_overrides_stale_environment(tmp_path, monkeypatch):
    calls = []
    original_clone = child.runtime.clone_module
    def clone(module):
        value = original_clone(module)
        if module.__name__ == 'run_c24_normal_validation':
            value.execute = lambda item, root, env: calls.append((item, root, env)) or 0
        return value
    monkeypatch.setattr(child.runtime, 'clone_module', clone)
    runner = guard.build_namespace(1)
    runner.base.execute({'name': 'only_mock'}, tmp_path,
                        {'SCENARIO7_REPAIR_INSTALL': str(child.previous.DEFAULT_INSTALL), 'SUPER_ASYNC_GENERATE_TRAJ': '0'})
    assert calls[0][2]['SCENARIO7_REPAIR_INSTALL'] == str(guard.DEFAULT_INSTALL)
    assert calls[0][2]['SUPER_ASYNC_GENERATE_TRAJ'] == '1'
    assert runner.base.static.map_context('seed1')['paths']['binary_adaptive'].is_relative_to(guard.DEFAULT_INSTALL)


def profile_text():
    return ('rog_map:\n  raycasting:\n    enable: false\n    ray_range: [0.5, 100 ]\n'
            'super_planner:\n  guard_topology_reroute:\n    local_escape_distance_m: 0.60\n'
            '  robot_r: 0.2\n')


def new_profile_text():
    return profile_text().replace(
        '    ray_range:', '    occupancy_only_min_range: 0.1\n    ray_range:').replace(
        '    local_escape_distance_m: 0.60\n',
        '    local_escape_distance_m: 0.60\n'
        '    local_escape_max_distance_m: 1.20\n'
        '    local_escape_distance_steps: 2\n')


def test_only_exact_nearhit_addition_is_admitted():
    assert child.validate_profile_pair(profile_text(), new_profile_text())
    assert child.validate_profile_pair(profile_text(), new_profile_text().replace(
        'min_range: 0.1\n', 'min_range: 0.1 # One new configuration key.\n'))
    for value in (profile_text(), new_profile_text().replace('robot_r: 0.2', 'robot_r: 0.1'),
                  new_profile_text().replace('min_range: 0.1', 'min_range: 0.2'),
                  new_profile_text().replace('ray_range: [0.5', 'ray_range: [0.1'),
                  new_profile_text() + '    occupancy_only_min_range: 0.1\n'):
        with pytest.raises(ValueError):
            child.validate_profile_pair(profile_text(), value)


def make_profile_assets(tmp_path):
    source, mirror, install = (tmp_path / name for name in ('source', 'mirror', 'install'))
    for mode, name in child.PROFILES.items():
        old = source / 'super_planner/config' / child.BASE_PROFILES[mode]
        old.parent.mkdir(parents=True, exist_ok=True)
        old.write_text(profile_text())
        for path in (old.with_name(name), mirror / 'super_planner_config' / name,
                     install / 'super_planner/share/super_planner/config' / name):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(new_profile_text())
    sensor = source / 'mars_uav_sim/perfect_drone_sim/config/urban_blocks_u01.yaml'
    sensor.parent.mkdir(parents=True)
    sensor.write_text('sensing_blind: 0.1\n')
    return source, mirror, install, sensor


def test_profile_admission_binds_all_copies_and_sensor_and_is_json_safe(tmp_path):
    source, mirror, install, sensor = make_profile_assets(tmp_path)
    admit = lambda: child.profile_admission(child.PROFILES, 'urban_blocks_u01', install, source=source, mirror=mirror)
    value = admit()
    json.dumps(value)
    assert len(value['assets_sha256']) == 13
    assert value['async_generate_trajectory'] and value['legacy_ray_range_min_m'] == 0.5
    installed = install / 'super_planner/share/super_planner/config' / child.PROFILES['full']
    installed.write_text('stale')
    with pytest.raises(ValueError, match='runtime/mirror/install'):
        admit()
    installed.write_text(new_profile_text())
    sensor.write_text('sensing_blind: 0.5\n')
    with pytest.raises(ValueError, match='sensor blind'):
        admit()
    with pytest.raises(ValueError, match='exact three'):
        child.profile_admission(child.BASE_PROFILES, 'urban_blocks_u01', install, source=source, mirror=mirror)


def test_actual_repository_profile_deltas_are_only_nearhit():
    for mode, name in child.PROFILES.items():
        folder = child.SOURCE / 'super_planner/config'
        assert child.validate_profile_pair((folder / child.BASE_PROFILES[mode]).read_text(), (folder / name).read_text())


def test_runtime_markers_exact_once_and_finite_numeric_equivalence():
    assert child.runtime_audit(markers())['valid']
    equivalent = markers().replace('hit_min=0.1', 'hit_min=1e-1').replace('free_ray_min=0.5', 'free_ray_min=0.500')
    assert child.runtime_audit('\x1b[32m' + equivalent + '\x1b[0m')['valid']


@pytest.mark.parametrize('mutation', ['missing_async', 'missing_near', 'disabled', 'wrong_executor',
    'not_finalized', 'not_default_off', 'duplicate_async', 'duplicate_near', 'wrong_hit', 'wrong_ray',
    'wrong_clear', 'nan', 'infinity', 'duplicate_field', 'missing_escape', 'wrong_escape_max'])
def test_invalid_runtime_markers_fail(mutation):
    async_line, near_line, max_line, steps_line = markers().splitlines()
    altered = {
        'missing_async': '\n'.join((near_line, max_line, steps_line)),
        'missing_near': '\n'.join((async_line, max_line, steps_line)),
        'disabled': markers().replace('enabled=true', 'enabled=false'),
        'wrong_executor': markers().replace('existing_replan', 'main'),
        'not_finalized': markers().replace('main_finalization=true', 'main_finalization=false'),
        'not_default_off': markers().replace('default_off=true', 'default_off=false'),
        'duplicate_async': markers() + async_line,
        'duplicate_near': markers() + near_line,
        'wrong_hit': markers().replace('hit_min=0.1', 'hit_min=0.5'),
        'wrong_ray': markers().replace('free_ray_min=0.5', 'free_ray_min=0.1'),
        'wrong_clear': markers().replace('startup_clear_radius=0.5', 'startup_clear_radius=0.1'),
        'nan': markers().replace('hit_min=0.1', 'hit_min=nan'),
        'infinity': markers().replace('hit_min=0.1', 'hit_min=inf'),
        'duplicate_field': markers().replace('hit_min=0.1', 'hit_min=0.1 hit_min=0.1'),
        'missing_escape': '\n'.join((async_line, near_line, max_line)),
        'wrong_escape_max': markers().replace('max_distance_m success: 1.2',
                                              'max_distance_m success: 0.6'),
    }[mutation]
    assert child.runtime_audit(altered)['valid'] is False


def test_actual_adapted_source_keeps_v2_conditions_and_runtime_checks():
    v2_source = child.previous.adapt_main(child.previous.previous.adapted_main_source())
    source = child.adapt_main(v2_source)
    tests = lambda text: [ast.dump(node.test) for node in ast.walk(ast.parse(text)) if isinstance(node, ast.If)]
    assert tests(v2_source) == tests(source)
    assert "os.environ['SUPER_ASYNC_GENERATE_TRAJ'] = '1'" in source
    assert "result['source_acquisition']['checks']['guard_contract_revision_2']" in source
    assert "result['source_acquisition']['checks']['nearfield_async_revision_3']" in source
    assert 'nearfield_async_revision=v3_admission' in source
    assert source.index("result['nearfield_async_audit']") < source.index("diagnostic.save(root / f'{mode}_summary.json', result)")
    main = child.build_main()
    assert main.__globals__['V3_PROFILES'] == child.PROFILES
    assert main.__globals__['repair_runtime'].install == child.DEFAULT_INSTALL
    assert main.__globals__['policy_audit'].__code__ is child.previous.policy_audit.__code__
    assert 'V3_PROFILES' not in child.previous.build_main().__globals__


def test_v2_or_missing_profile_runtime_identity_cannot_be_reused(monkeypatch):
    monkeypatch.setattr(child.runtime.RuntimeBinding, 'profile_reference_audit',
        lambda *_: dict(valid=True, checks={'legacy': True}, acceptance_checks={'legacy': True}))
    audit = child.build_main().__globals__['small_pool_profile_reference_audit']
    identity = dict(schema='scenario7-nearfield-async-inputs-v3', async_generate_trajectory=True,
                    occupancy_only_min_range_m=0.1)
    plan = dict(guard_contract_revision=2, guard_contract_stop_policy=child.previous.STOP_POLICY,
                nearfield_async_revision=identity, modes=['full', 'sector', 'adaptive'])
    summaries = {mode: dict(guard_contract_audit={'valid': True}, nearfield_async_audit={'valid': True})
                 for mode in plan['modes']}
    assert audit(plan, plan, summaries)['valid']
    old = copy.deepcopy(plan)
    old.pop('nearfield_async_revision')
    assert not audit(plan, old, summaries)['valid']
    mismatched = copy.deepcopy(plan)
    mismatched['nearfield_async_revision']['occupancy_only_min_range_m'] = 0.5
    assert not audit(plan, mismatched, summaries)['valid']
    for mode in plan['modes']:
        altered = copy.deepcopy(summaries)
        altered[mode]['nearfield_async_audit']['valid'] = False
        assert not audit(plan, plan, altered)['valid']
    summaries['full']['guard_contract_audit']['valid'] = False
    assert not audit(plan, plan, summaries)['valid']


def test_actual_child_retains_structured_missing_reference_no_flight(tmp_path, monkeypatch):
    main = child.build_main()
    ns = main.__globals__
    monkeypatch.setitem(ns, 'profile_admission', lambda *_: {})
    monkeypatch.setitem(ns, 'register_maps', lambda: {})
    monkeypatch.setitem(ns, 'static_latched_preflight', SimpleNamespace(map_context=lambda _: {}))
    monkeypatch.setitem(ns, 'mission_runtime', SimpleNamespace(mission_context=lambda _: {}))
    output = tmp_path / 'blocked'
    monkeypatch.setattr(sys, 'argv', ['child', '--output', str(output), '--run', '1', '--candidate', guard.CANDIDATE,
        '--map', 'urban_blocks_u01', '--modes', 'adaptive', 'sector', 'full', '--side-executor-threads', '3',
        '--dedicated-static-pc-executor', '--monitor-intervals', '--small-pool-profile-reference', str(tmp_path / 'missing')])
    with mock.patch.object(ns['diagnostic'], 'Profiler') as profiler:
        assert main() == 2
    profiler.assert_not_called()
    status = json.loads((output / 'status.json').read_text())
    assert status['state'] == 'BLOCKED_BY_PREFLIGHT' and status['flights_started'] is False


def test_mocked_root_dry_run_never_executes_and_binds_new_schema(tmp_path, monkeypatch):
    runner = guard.build_namespace(1)
    output = tmp_path / 'new'
    monkeypatch.setattr(runner.support, 'register_maps', lambda: {'valid': True})
    monkeypatch.setattr(runner, 'freeze_sources', lambda *_: ({}, {'control_revision': 3}))
    monkeypatch.setattr(runner.base, 'static_commands', lambda *_: [])
    with mock.patch.object(runner.base, 'execute') as execute:
        assert runner.main(['--output', str(output), '--dry-run', '--maps', runner.MAPS[0], runner.MAPS[3], runner.MAPS[5]]) == 0
    execute.assert_not_called()
    plan = json.loads((output / 'plan.json').read_text())
    assert plan['schema'] == guard.SCHEMA and plan['candidate'] == guard.CANDIDATE
    assert plan['profiled_preflight_flights'] == plan['unprofiled_primary_flights'] == 9
    assert plan['no_retry'] and plan['no_replacement'] and plan['old_cohorts_not_pooled']


def test_launcher_environment_passes_real_top_level_admission(tmp_path, monkeypatch):
    launcher = (guard.SCRIPTS / 'run_scenario7_guard_v3.sh').read_text()
    dispatch = ('exec python3 -u /root/super_ws/src/SUPER/mars_uav_sim/'
                'perfect_drone_sim/scripts/run_scenario7_guard_v3.py "$@"')
    assert launcher.count(dispatch) == 1
    # Execute the real shell preamble. Only ROS setup sourcing is stubbed, so
    # this regression stays offline and also works before an overlay is built.
    shell = 'source() { return 0; }\n' + launcher.replace(dispatch, '/usr/bin/env -0')
    clean = {key: value for key, value in os.environ.items()
             if not key.startswith('SUPER_') and key != 'SCENARIO7_GUARD_V3_INSTALL'}
    captured = subprocess.run(['bash', '-c', shell], env=clean, check=True,
                              capture_output=True).stdout
    environment = dict(item.decode().split('=', 1) for item in captured.split(b'\0') if item)
    assert environment['SCENARIO7_REPAIR_INSTALL'] == str(guard.DEFAULT_INSTALL)
    assert not any(key.startswith('SUPER_') for key in environment)
    runner = guard.build_namespace(1)
    monkeypatch.setattr(guard, 'build_namespace', lambda *_: runner)
    monkeypatch.setattr(runner.support, 'register_maps', lambda: {'valid': True})
    monkeypatch.setattr(runner, 'freeze_sources', lambda *_: ({}, {'control_revision': 3}))
    monkeypatch.setattr(runner.base, 'static_commands', lambda *_: [])
    output = tmp_path / 'launcher_dry'
    with mock.patch.dict(os.environ, environment, clear=True), \
            mock.patch.object(runner.base, 'execute') as execute:
        assert guard.main(['--rounds', '1', '--output', str(output), '--dry-run',
                           '--maps', runner.MAPS[0]]) == 0
    execute.assert_not_called()
    plan = json.loads((output / 'plan.json').read_text())
    assert plan['schema'] == guard.SCHEMA and plan['rounds'] == 1
    assert plan['profiled_preflight_flights'] == plan['unprofiled_primary_flights'] == 3


def test_real_top_level_still_rejects_inherited_async_override(tmp_path, monkeypatch, capsys):
    runner = guard.build_namespace(1)
    monkeypatch.setattr(guard, 'build_namespace', lambda *_: runner)
    output = tmp_path / 'inherited_refused'
    with mock.patch.dict(os.environ, {'SUPER_ASYNC_GENERATE_TRAJ': '1'}, clear=True), \
            mock.patch.object(runner.base, 'execute') as execute:
        with pytest.raises(SystemExit) as error:
            guard.main(['--rounds', '1', '--output', str(output), '--dry-run',
                        '--maps', runner.MAPS[0]])
    assert error.value.code == 2
    assert 'Unexpected inherited SUPER_* overrides' in capsys.readouterr().err
    assert not output.exists()
    execute.assert_not_called()


def test_v2_report_rejected_and_v3_stored_rounds_required(tmp_path):
    (tmp_path / 'plan.json').write_text(json.dumps(dict(schema=guard.previous.SCHEMA, rounds=1)))
    with pytest.raises(SystemExit):
        guard.main(['--report', str(tmp_path)])
    (tmp_path / 'plan.json').write_text(json.dumps(dict(schema=guard.SCHEMA, rounds=1)))
    with pytest.raises(SystemExit):
        guard.main(['--report', str(tmp_path), '--rounds', '2'])


def test_frozen_v2_controller_and_child_hashes_are_required(tmp_path, monkeypatch):
    changed = tmp_path / 'changed.py'
    changed.write_text('# changed')
    monkeypatch.setattr(guard.previous, '__file__', str(changed))
    with pytest.raises(ValueError, match='Frozen guard-v2 controller'):
        guard.private_previous()
    monkeypatch.setattr(child.previous, '__file__', str(changed))
    with pytest.raises(ValueError, match='Frozen guard-v2 child'):
        child.build_main()
