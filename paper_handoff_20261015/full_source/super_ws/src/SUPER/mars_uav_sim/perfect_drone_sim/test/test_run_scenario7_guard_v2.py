"""Offline-only guard-v2 controller isolation and exact admission tests."""
import ast
import copy
import json
from pathlib import Path
import sys
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import run_scenario7_guard_v2 as guard
import run_scenario7_repair as previous
import scenario7_guard_v2_cpu_compare as child


@pytest.mark.parametrize('rounds', [1, 3, 10])
def test_counts_modes_thresholds_and_new_candidate_without_mutating_v1(tmp_path, rounds):
    runner = guard.build_namespace(rounds)
    with mock.patch.object(runner.base, 'static_commands', return_value=[]):
        commands = runner.build_plan(tmp_path)
    on = [item for item in commands if item['phase'] == 'preflight']
    off = [item for item in commands if item['phase'] == 'test10']
    assert len(on) == 7 and len(off) == rounds * 7
    assert len({(item['map'], item['run'], mode) for item in commands for mode in item['modes']}) == 21 * (rounds + 1)
    for item in commands:
        command = item['command']
        assert command[command.index('--candidate') + 1] == 'c27_guard_contract_v2'
        assert command[1].endswith('scenario7_guard_v2_cpu_compare.py')
        assert command[command.index('--side-executor-threads') + 1] == '3'
        assert ('--profile-cpu' in command) == (item['phase'] == 'preflight')
        assert ('--small-pool-profile-reference' in command) == (item['phase'] == 'test10')
        assert '--extended-demand-lease' not in command
        assert item['mission']['goal_count'] == 5
    assert runner.base.MEMORY_RUNAWAY_MIB == 4608
    assert runner.CANDIDATE == guard.CANDIDATE and runner.SCHEMA == guard.SCHEMA
    assert runner.repair_runtime.install == guard.DEFAULT_INSTALL
    assert previous.CANDIDATE == 'c26_scenario7_repair_v1'
    assert previous.SCHEMA == 'scenario7-repair-manual-v1'
    assert previous.PRIOR_ROOT != guard.PRIOR_ROOT
    assert previous.MODIFIED_CPP != guard.MODIFIED_CPP


def test_subset_keeps_separate_groups_and_round_counts(tmp_path):
    runner = guard.build_namespace(2)
    maps = (runner.MAPS[0], runner.MAPS[5])
    with mock.patch.object(runner.base, 'static_commands', return_value=[]):
        commands = runner.build_plan(tmp_path, maps)
    assert len(commands) == 6
    grouped = runner.grouped_rows([], maps)
    assert {row['group']: row['planned'] for row in grouped} == {'normal': 2, 'urban': 2}


def test_only_declared_six_sources_can_change_and_v1_install_cannot(tmp_path):
    adapted = guard.private_previous()
    assert len(adapted.MODIFIED_CPP) == 6
    assert set(adapted.MODIFIED_CPP) - set(previous.MODIFIED_CPP) == {
        'rog_map/src/rog_map/prob_map.cpp', 'super_planner/include/ros_interface/ros2/fsm_ros2.hpp'}
    assert len(adapted.admitted_cpp_paths()) == 12
    assert str(guard.DEFAULT_INSTALL) not in '\n'.join(adapted.admitted_cpp_paths())
    source, binary, data = (tmp_path / name for name in ('prob_map.cpp', 'v1_node', 'old_raw.csv'))
    for path in (source, binary, data):
        path.write_text('original')
    inventory = {str(path): previous.sha(path) for path in (source, binary, data)}
    source.write_text('approved change')
    assert len(adapted.verify_prior_inventory(inventory, allowed={str(source)})) == 1
    for path in (binary, data):
        path.write_text('unapproved')
        with pytest.raises(ValueError, match='Unadmitted'):
            adapted.verify_prior_inventory(inventory, allowed={str(source)})
        path.write_text('original')


def test_expected_new_helpers_and_tests_are_exactly_named():
    added = set(guard.ADDED_CPP) - set(previous.ADDED_CPP)
    assert added == {
        'super_planner/include/fsm/stop_margin_certificate.hpp',
        'super_planner/test/stop_margin_certificate_test.cpp',
        'super_planner/test/stop_margin_demand_policy_test.cpp',
        'super_planner/test/stop_margin_validator_integration_test.cpp',
        'rog_map/test/occupancy_hit_multiplicity_test.cpp'}
    assert guard.ADDED_TEST_SCRIPTS == ('super_planner/test/stop_margin_validator_integration_test.py',)


@pytest.mark.parametrize('install', [previous.runtime.BASE_INSTALL, previous.runtime.DEFAULT_INSTALL,
                                     previous.runtime.DEFAULT_INSTALL / '../install', Path('relative/install')])
def test_old_or_relative_install_is_rejected(install):
    with pytest.raises(ValueError):
        guard.selected_install(install)


def test_static_bindings_and_child_execution_use_v2_overlay(tmp_path, monkeypatch):
    calls = []
    original_clone = previous.runtime.clone_module
    def clone(module):
        value = original_clone(module)
        if module.__name__ == 'run_c24_normal_validation':
            value.execute = lambda item, root, env: calls.append((item, root, env)) or 0
        return value
    monkeypatch.setattr(previous.runtime, 'clone_module', clone)
    runner = guard.build_namespace(1)
    runner.base.execute({'name': 'test'}, tmp_path, {'SCENARIO7_REPAIR_INSTALL': str(previous.runtime.DEFAULT_INSTALL)})
    assert calls[0][2]['SCENARIO7_REPAIR_INSTALL'] == str(guard.DEFAULT_INSTALL)
    paths = runner.base.static.map_context('seed1')['paths']
    assert paths['binary_adaptive'].is_relative_to(guard.DEFAULT_INSTALL)
    assert previous.runtime.DEFAULT_INSTALL not in paths['binary_adaptive'].parents


def test_dry_run_metadata_has_new_cohort_without_execution(tmp_path, monkeypatch):
    runner = guard.build_namespace(1)
    output = tmp_path / 'guard_v2'
    monkeypatch.setattr(runner.support, 'register_maps', lambda: {'valid': True})
    monkeypatch.setattr(runner, 'freeze_sources', lambda *_: ({}, {'contract_revision': 2}))
    monkeypatch.setattr(runner.base, 'static_commands', lambda *_: [])
    with mock.patch.object(runner.base, 'execute') as execute:
        assert runner.main(['--output', str(output), '--dry-run']) == 0
    execute.assert_not_called()
    plan = json.loads((output / 'plan.json').read_text())
    assert plan['schema'] == guard.SCHEMA and plan['candidate'] == guard.CANDIDATE
    assert plan['rounds'] == 1 and plan['profiled_preflight_flights'] == 21
    assert plan['unprofiled_primary_flights'] == 21
    assert plan['no_retry'] and plan['no_replacement'] and plan['old_cohorts_not_pooled']


def test_v1_controller_hash_mismatch_is_not_admitted(tmp_path, monkeypatch):
    changed = tmp_path / 'run_scenario7_repair.py'
    changed.write_text('# changed')
    monkeypatch.setattr(previous, '__file__', str(changed))
    with pytest.raises(ValueError, match='Frozen repair-v1'):
        guard.private_previous()


def test_report_rejects_v1_and_uses_stored_rounds(tmp_path, monkeypatch):
    (tmp_path / 'plan.json').write_text(json.dumps(dict(schema=previous.SCHEMA, rounds=1)))
    with pytest.raises(SystemExit):
        guard.main(['--report', str(tmp_path)])
    runner = guard.build_namespace(1)
    (tmp_path / 'plan.json').write_text(json.dumps(dict(schema=guard.SCHEMA, rounds=1, maps=list(runner.MAPS))))
    monkeypatch.setattr(guard, 'build_namespace', lambda rounds: runner)
    with mock.patch.object(runner, 'reports') as reports, mock.patch.object(runner.base, 'execute') as execute:
        assert guard.main(['--report', str(tmp_path)]) == 0
    reports.assert_called_once()
    execute.assert_not_called()
    with pytest.raises(SystemExit):
        guard.main(['--report', str(tmp_path), '--rounds', '10'])


def startup_marker():
    return ('[GUARDED_DEMAND_REPLAN] enabled=true max_dispatch_interval=0.25 '
            'demand_timer_hz=15 guard_command_hz=100 legacy_coalescer=bypassed '
            f'stop_policy={child.STOP_POLICY} stop_policy_revision=2')


def test_exact_runtime_marker_extracted_into_actual_child_source_check():
    source = child.adapt_main(child.previous.adapted_main_source())
    tree = ast.parse(source)
    assignments = [node for node in ast.walk(tree) if isinstance(node, ast.Assign)
                   and any('guard_contract' in ast.unparse(target) for target in node.targets)]
    assert len(assignments) == 2
    code = compile(ast.Module(body=assignments, type_ignores=[]), '<actual-policy-audit>', 'exec')
    for stack, valid in [(startup_marker(), True), ('legacy startup', False)]:
        result = {'source_acquisition': {'checks': {'legacy_gate': True}}}
        exec(code, dict(result=result, stack=stack, policy_audit=child.policy_audit))
        assert result['guard_contract_audit']['valid'] is valid
        assert result['source_acquisition']['checks'] == {
            'legacy_gate': True, 'guard_contract_revision_2': valid}
    # The added identity gate is persisted before unchanged failure handling.
    assert source.index("result['guard_contract_audit']") < source.index("diagnostic.save(root / f'{mode}_summary.json', result)")
    assert 'files.add(GUARD_CHILD_SOURCE)' in source
    assert 'guard_contract_revision=POLICY_REVISION' in source


@pytest.mark.parametrize('change', ['missing', 'old', 'wrong_revision', 'duplicate',
                                  'mixed', 'duplicate_policy', 'disabled', 'conflicting_enabled'])
def test_old_missing_or_ambiguous_runtime_marker_is_not_accepted(change):
    marker = startup_marker()
    old = marker.replace(child.STOP_POLICY, 'sampled_unknown_allowed_clearance_margin_allowed')
    stack = {
        'missing': 'startup without identity',
        'old': old,
        'wrong_revision': marker.replace('revision=2', 'revision=1'),
        'duplicate': marker + '\n' + marker,
        'mixed': marker + '\n' + old,
        'duplicate_policy': marker + f' stop_policy={child.STOP_POLICY}',
        'disabled': marker.replace('enabled=true', 'enabled=false'),
        'conflicting_enabled': marker + ' enabled=false',
    }[change]
    assert child.policy_audit(stack)['valid'] is False


def test_new_child_preserves_all_existing_options_gate_expressions_and_no_retry():
    old = ast.parse(child.previous.adapted_main_source())
    new = ast.parse(child.adapt_main(child.previous.adapted_main_source()))
    def conditions(tree):
        return [ast.dump(node.test) for node in ast.walk(tree) if isinstance(node, ast.If)]
    def parser_calls(tree):
        return [ast.dump(node) for node in ast.walk(tree) if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute) and node.func.attr in ('add_argument', 'error')]
    assert conditions(old) == conditions(new)
    assert parser_calls(old) == parser_calls(new)
    main = child.build_main()
    assert main.__globals__['repair_runtime'].install == guard.DEFAULT_INSTALL
    assert main.__globals__['GUARD_CHILD_SOURCE'] == Path(child.__file__).resolve()
    assert child.previous.previous.inherited.diagnostic.search.OPTIONS['attempt_max'] == 1
    assert 'GUARD_CHILD_SOURCE' not in child.previous.build_main().__globals__


def test_profile_reference_requires_both_new_identity_and_valid_runtime_marker(monkeypatch):
    monkeypatch.setattr(child.previous.runtime.RuntimeBinding, 'profile_reference_audit',
        lambda *_: dict(valid=True, checks={'legacy': True}, acceptance_checks={'legacy': True}))
    audit = child.build_main().__globals__['small_pool_profile_reference_audit']
    plan = dict(guard_contract_revision=2, guard_contract_stop_policy=child.STOP_POLICY,
                modes=['adaptive', 'sector', 'full'])
    summaries = {mode: {'guard_contract_audit': child.policy_audit(startup_marker())}
                 for mode in plan['modes']}
    assert audit(plan, plan, summaries)['valid']
    old = copy.deepcopy(plan)
    old.pop('guard_contract_revision')
    assert not audit(plan, old, summaries)['valid']
    assert not audit(old, plan, summaries)['valid']
    for mode in plan['modes']:
        altered = copy.deepcopy(summaries)
        altered[mode]['guard_contract_audit']['valid'] = False
        report = audit(plan, plan, altered)
        assert not report['valid']
        assert report['checks']['legacy'] and report['acceptance_checks']['legacy']
        assert report['acceptance_checks']['guard_contract_revision_2_match'] is False


@pytest.mark.parametrize('install', [previous.runtime.BASE_INSTALL, previous.runtime.DEFAULT_INSTALL,
                                     previous.runtime.DEFAULT_INSTALL / '../install', Path('relative/install')])
def test_child_rejects_preserved_or_relative_install(install):
    with pytest.raises(ValueError):
        child.build_main(install_root=install)


def test_child_frozen_v1_hash_is_mandatory(tmp_path, monkeypatch):
    changed = tmp_path / 'scenario7_cpu_compare_v3.py'
    changed.write_text('# changed')
    monkeypatch.setattr(child.previous, '__file__', str(changed))
    with pytest.raises(ValueError, match='Frozen repair-v1 child'):
        child.build_main()
