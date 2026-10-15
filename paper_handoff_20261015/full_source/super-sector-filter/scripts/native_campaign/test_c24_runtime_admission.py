from adaptive_cpu40_seed1 import async_recovery_setting_audit, small_pool_profile_reference_audit
from test_adaptive_cpu40_seed1 import three_mode_profile_reference_fixture


def test_async_recovery_runtime_marker_is_exact_and_unique():
    on = '[ASYNC_CERTIFIED_RECOVERY] enabled=true'
    off = '[ASYNC_CERTIFIED_RECOVERY] enabled=false'
    assert async_recovery_setting_audit(on, True)['valid']
    assert async_recovery_setting_audit(off, False)['valid']
    for value, expected in [('', True),('',False),(on,False),(off,True),(on+'\n'+on,True)]:
        assert not async_recovery_setting_audit(value, expected)['valid']


def test_async_option_must_match_instrumented_preflight():
    plan, reference, summaries = three_mode_profile_reference_fixture()
    assert small_pool_profile_reference_audit(plan, reference, summaries)['valid']
    plan['async_certified_recovery'] = True
    assert not small_pool_profile_reference_audit(plan, reference, summaries)['valid']
    reference['async_certified_recovery'] = True
    assert not small_pool_profile_reference_audit(plan, reference, summaries)['valid']
    for row in summaries.values():
        row['async_certified_recovery'] = True
        row['async_recovery_setting_audit'] = {'valid':True}
        row['source_acquisition']['checks']['async_certified_recovery_setting'] = True
    assert small_pool_profile_reference_audit(plan, reference, summaries)['valid']


def test_sector_outcomes_never_relax_full_adaptive_or_measurement_guards():
    import copy
    plan, ref, rows = three_mode_profile_reference_fixture()
    rows['sector']['success'] = False
    rows['sector']['safety_collisions'] = 1
    rows['sector']['goal_identity_audit'] = {'valid': True, 'identity_consistency_valid': True}
    rows['sector']['source_acquisition']['checks']['goal_identity_consistency'] = True
    assert not small_pool_profile_reference_audit(plan, ref, rows)['valid']
    plan['sector_outcomes_as_metrics'] = True
    audit = small_pool_profile_reference_audit(plan, ref, rows)
    assert audit['valid'] and audit['checks']['sector_safe_source'] is False
    for mode, key, value in [('full','success',False),('adaptive','safety_collisions',1),
                             ('sector','resource_valid',False),('sector','small_pool_timing',{})]:
        bad = copy.deepcopy(rows); bad[mode][key] = value
        assert not small_pool_profile_reference_audit(plan, ref, bad)['valid']
