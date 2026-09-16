import copy
from adaptive_cpu40_seed1 import comparison, reference_comparison


def pair():
    common = dict(success=True, run_valid=True, resource_valid=True,
                  speed_limit_valid=True, safety_collisions=0,
                  source_acquisition={'checks': {'valid': True}})
    return [dict(common, mode='full', end_to_end_cpu_cores_mean=2.,
                 end_to_end_cpu_core_s=120., mission_time_s=60.),
            dict(common, mode='adaptive', end_to_end_cpu_cores_mean=1.1,
                 end_to_end_cpu_core_s=70., mission_time_s=62.)]


def test_mean_target_and_cumulative_are_distinct():
    result = comparison(pair())
    assert result['target_met']
    assert round(result['end_to_end_cpu_cores_mean_reduction_pct']) == 45
    assert round(result['end_to_end_cpu_core_s_reduction_pct'], 2) == 41.67


def test_low_cpu_due_to_long_stationary_hold_does_not_pass():
    rows = pair()
    rows[1]['mission_time_s'] = 150.
    assert not comparison(rows)['target_met']


def test_collision_failure_and_contract_failure_never_pass():
    for key, value in [('safety_collisions', 1), ('success', False),
                       ('speed_limit_valid', False), ('resource_valid', False),
                       ('source_acquisition', {'checks': {'valid': False}})]:
        rows = copy.deepcopy(pair())
        rows[1][key] = value
        assert not comparison(rows)['target_met']


def test_missing_mode_cannot_pass():
    assert not comparison(pair()[:1])['target_met']


def test_dual_query_probe_cannot_claim_cpu_target():
    rows = pair()
    rows[0]['cpu_comparison_instrumented'] = True
    assert not comparison(rows)['target_met']


def test_profiled_threshold_requires_unprofiled_confirmation():
    rows = pair()
    rows[0]['cpu_profile'] = rows[1]['cpu_profile'] = True
    out = comparison(rows)
    assert out['measured_threshold_pass']
    assert out['requires_unprofiled_confirmation']
    assert not out['target_met']


def test_both_modes_slowing_together_cannot_pass_reference_guard():
    rows = pair()
    for row in rows:
        reference = dict(row, mission_time_s=row['mission_time_s'] / 1.2)
        row['reference_comparison'] = reference_comparison(row, reference)
    out = comparison(rows)
    assert out['mission_time_guardrail_pass']
    assert not out['per_mode_reference_time_guardrail_pass']
    assert not out['target_met']


def test_reference_mean_and_total_cpu_are_reported_independently():
    full, adaptive = pair()
    out = reference_comparison(adaptive, full)
    assert round(out['mean_cpu_reduction_pct']) == 45
    assert round(out['cumulative_cpu_reduction_pct'], 2) == 41.67
    assert out['mission_time_guardrail_pass']


def test_common_demand_optimization_requires_execution_in_both_modes():
    rows = copy.deepcopy(pair())
    for row in rows:
        row['source_acquisition']['checks']['guarded_demand_replan_active'] = True
        row['demand_replan_exercised'] = True
    assert comparison(rows)['target_met']
    rows[0]['demand_replan_exercised'] = False
    out = comparison(rows)
    assert not out['common_demand_exercise_pass']
    assert not out['target_met']
    assert out['safety_and_quality_pass']
