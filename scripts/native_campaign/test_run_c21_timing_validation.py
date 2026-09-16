from copy import deepcopy
from run_c21_timing_validation import only_timing_failure


def test_diagnostic_continue_is_only_for_retained_timing_failure():
    row = dict(success=True, run_valid=True, resource_valid=True, speed_limit_valid=True,
               safety_collisions=0, source_acquisition=dict(checks=dict(
                   small_pool_timing=False, sensor=True, recovery=True)))
    assert only_timing_failure(row)
    for key, value in [('success', False), ('run_valid', False), ('resource_valid', False),
                       ('speed_limit_valid', False), ('safety_collisions', 1)]:
        assert not only_timing_failure(dict(row, **{key: value}))
    changed = deepcopy(row)
    changed['source_acquisition']['checks']['recovery'] = False
    assert not only_timing_failure(changed)
    changed['source_acquisition']['checks'] = {}
    assert not only_timing_failure(changed)
    assert not only_timing_failure({})
