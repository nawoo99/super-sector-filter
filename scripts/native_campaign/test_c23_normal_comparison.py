import copy
from pathlib import Path
from run_c23_normal_comparison import build_commands, comparison_audit, MAPS
from test_adaptive_cpu40_seed1 import three_mode_profile_reference_fixture
from adaptive_cpu40_seed1 import small_pool_profile_reference_audit


def test_exact_75_comparison_flights_and_three_extra_profiled(tmp_path):
    commands, refs = build_commands(tmp_path, Path('/evidence'), 15000)
    assert len(commands) == 26
    flights = [c for c in commands if c['phase'] == 'comparison5']
    assert len(flights)*3 == 75
    assert len({c['run'] for c in commands}) == 26
    for m in MAPS:
        assert len([c for c in flights if c['map'] == m]) == 5
    for c in commands:
        assert set(c['modes']) == {'full','sector','adaptive'}
        assert '--event-body-heading' in c['command']
        assert '--mission-time-as-metric' in c['command']
        assert '--extended-demand-lease' not in c['command']
        assert '--profile-cpu' in c['command'] if c['phase']=='preflight' else '--small-pool-profile-reference' in c['command']


def test_time_as_metric_does_not_relax_safety_runtime_or_callback_gates():
    plan, ref, rows = three_mode_profile_reference_fixture()
    rows['adaptive']['mission_time_s'] = rows['full']['mission_time_s']*1.5
    rows['adaptive']['reference_comparison']['mission_time_guardrail_pass'] = False
    assert not small_pool_profile_reference_audit(plan, ref, rows)['valid']
    plan['mission_time_as_metric'] = True
    audit = small_pool_profile_reference_audit(plan, ref, rows)
    assert audit['valid']
    assert audit['checks']['paired_mission_time'] is False
    assert audit['checks']['adaptive_reference_time'] is False
    for key, val in [('success',False),('safety_collisions',1),('small_pool_timing',{})]:
        bad = copy.deepcopy(rows); bad['adaptive'][key] = val
        assert not small_pool_profile_reference_audit(plan, ref, bad)['valid']
    plan['side_executor_threads'] = 3
    assert not small_pool_profile_reference_audit(plan, ref, rows)['valid']


def test_missing_flights_cannot_be_accepted(tmp_path):
    assert not comparison_audit(tmp_path, 'seed1', 1, False)['valid']
