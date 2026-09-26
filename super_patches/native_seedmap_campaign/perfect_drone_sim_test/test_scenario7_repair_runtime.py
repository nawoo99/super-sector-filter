"""No-build/no-ROS tests for private overlay selection and source binding."""
import inspect
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import scenario7_repair_runtime as runtime
import scenario7_cpu_compare_v3 as child


def test_overlay_maps_only_the_three_rebuilt_packages(tmp_path):
    binding = runtime.RuntimeBinding(tmp_path)
    assert binding.select_path(runtime.BASE_INSTALL / 'perfect_drone_sim/lib/node') == tmp_path / 'perfect_drone_sim/lib/node'
    assert binding.select_path(runtime.BASE_INSTALL / 'mission_planner/lib/frontend') == runtime.BASE_INSTALL / 'mission_planner/lib/frontend'
    original = dict(runtime.previous.inherited.static_latched_preflight.BINDING_PATHS)
    context = binding.map_context('seed1')
    assert context['paths']['binary_full'].is_relative_to(tmp_path)
    assert context['paths']['frontend_component'] == original['frontend_component']
    assert runtime.previous.inherited.static_latched_preflight.BINDING_PATHS == original


def test_private_campaign_profiler_and_search_leave_legacy_globals_unchanged(tmp_path):
    original = runtime.previous.inherited.diagnostic
    original_env = original.search.campaign.ROS_ENV
    original_run = original.RUN
    namespace = runtime.RuntimeBinding(tmp_path).namespace()
    diagnostic = namespace['diagnostic']
    campaign = diagnostic.search.campaign
    assert campaign is not original.search.campaign
    assert campaign.run_one.__globals__ is vars(campaign)
    assert campaign.spawn_process_group.__globals__ is vars(campaign)
    assert campaign.campaign_signal_handler.__globals__ is vars(campaign)
    assert campaign._ACTIVE_PROCESS_GROUPS is not original.search.campaign._ACTIVE_PROCESS_GROUPS
    assert str(tmp_path / 'local_setup.bash') in campaign.ROS_ENV
    assert campaign.ROS_ENV.startswith(original_env + ' && ')
    assert inspect.signature(campaign.run_one) == inspect.signature(original.search.campaign.run_one)
    assert diagnostic.Profiler.sample.__globals__ is vars(diagnostic)
    diagnostic.RUN = 54321
    assert original.RUN == original_run and original.search.campaign.ROS_ENV == original_env


def test_overlay_inventory_refuses_missing_build(tmp_path):
    with pytest.raises(ValueError, match='incomplete'):
        runtime.RuntimeBinding(tmp_path).asset_paths()
    with pytest.raises(ValueError, match='separate'):
        runtime.RuntimeBinding(runtime.BASE_INSTALL)
    with pytest.raises(ValueError, match='separate'):
        runtime.RuntimeBinding(runtime.BASE_INSTALL / '../install')
    with pytest.raises(ValueError, match='absolute'):
        runtime.RuntimeBinding(Path('relative/install'))


def test_actual_ament_prefix_must_match_declared_overlay(tmp_path):
    binding = runtime.RuntimeBinding(tmp_path)
    runtime.verify_package_selection(binding, lambda package: str(tmp_path / package))
    with pytest.raises(ValueError, match='resolution mismatch'):
        runtime.verify_package_selection(binding, lambda package: str(runtime.BASE_INSTALL / package))


def test_runtime_policy_keeps_underlay_and_binds_overlay_inventory(tmp_path, monkeypatch):
    path = tmp_path / 'binary'
    path.write_bytes(b'new revision')
    binding = runtime.RuntimeBinding(tmp_path)
    monkeypatch.setattr(binding, 'asset_paths', lambda: {path})
    # Avoid reading hundreds of MB of unchanged real binaries in this unit test.
    original_clone = runtime.clone_module
    def clone(module):
        result = original_clone(module)
        if module.__name__ == 'cylinder_map_search':
            result.frozen_policy = lambda: dict(sha256={'old-binary': 'old'}, options={'attempt_max': 1})
        return result
    monkeypatch.setattr(runtime, 'clone_module', clone)
    policy = binding.namespace()['diagnostic'].search.frozen_policy()
    assert policy['sha256']['old-binary'] == 'old'
    assert policy['sha256'][str(path)] == runtime.previous.support.sha256(path)
    assert policy['options']['attempt_max'] == 1


def test_child_revision_is_explicit_and_source_bound():
    identity = child.revision_identity()
    assert len(identity['source_sha256']) == 4
    assert identity['not_pooled_with_previous_results'] is True
    assert identity['timing_thresholds_unchanged'] is True
    main = child.build_main()
    assert main.__globals__ is not runtime.previous.inherited.main.__globals__
    assert main.__globals__['small_pool_timing_audit'] is runtime.previous.inherited.small_pool_timing_audit


def test_reference_cannot_match_an_old_or_different_repair_revision(monkeypatch):
    # Keep the real new wrapper/revision checks but isolate the old comprehensive
    # gate function so this test specifically exercises the new identity gate.
    old = runtime.inspect.getsource
    def source(function):
        text = old(function)
        if function is runtime.previous.inherited.legacy.small_pool_profile_reference_audit:
            return ("def small_pool_profile_reference_audit(plan, reference_plan, summaries):\n"
                    "    required = '/root/super_ws/install/perfect_drone_sim/lib/perfect_drone_sim/'\n"
                    "    return dict(valid=True, checks={}, acceptance_checks={})\n")
        return text
    monkeypatch.setattr(runtime.inspect, 'getsource', source)
    plan = {key: 'same' for key in runtime.previous.MAP_MATCH_FIELDS}
    plan.update(scenario7_control_revision={'version': 3}, scenario7_repair_runtime={'install': 'overlay'})
    binding = runtime.RuntimeBinding()
    assert binding.profile_reference_audit(plan, dict(plan), {})['valid']
    for key in ('scenario7_control_revision', 'scenario7_repair_runtime'):
        wrong = dict(plan)
        del wrong[key]
        audit = binding.profile_reference_audit(plan, wrong, {})
        assert not audit['valid'] and not audit['acceptance_checks'][key + '_match']
