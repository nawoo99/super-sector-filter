import copy
from adaptive_cpu40_seed1 import comparison


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
