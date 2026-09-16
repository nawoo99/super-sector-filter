import copy
from adaptive_cpu40_seed1 import (SMALL_POOL_MATCH_FIELDS, comparison,
                                 reference_comparison, small_pool_timing_audit,
                                 small_pool_profile_reference_audit,
                                 DEMAND_REASONS, demand_reason_audit,
                                 static_two_phase_audit, goal_identity_audit,
                                 headless_parameter_audit)


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


def test_small_pool_timing_guards_are_not_timer_setting_claims():
    intervals = {'odometry': dict(mean_received_hz=100., header_interval=dict(p99_ms=11., max_ms=20.),
                                  receipt_interval=dict(p99_ms=12., max_ms=25.),
                                  backward_stamps=0, repeated_stamps=0, intervals_dropped=0)}
    profile = dict(processes=[dict(duration_s=10., stages=[
        dict(stage=s, calls=1000, clock_errors=0) for s in
        ('fsm_main_callback', 'fsm_command_callback')])])
    assert small_pool_timing_audit(intervals, 10., profile)['valid']
    for sensor_hz in (9., float('nan'), None):
        assert not small_pool_timing_audit(intervals, sensor_hz, profile)['valid']
    profile['processes'][0]['stages'][0]['calls'] = 900
    assert not small_pool_timing_audit(intervals, 10., profile)['valid']
    intervals['odometry']['header_interval']['max_ms'] = 80.
    assert not small_pool_timing_audit(intervals, 10.)['valid']
    assert not small_pool_timing_audit({}, 10., {})['valid']


def test_unprofiled_timing_audit_does_not_claim_callback_counts():
    out = small_pool_timing_audit({}, 10.)
    assert out['callback_counts_instrumented'] is False
    assert out['callback_hz'] == {}


def test_small_pool_receipt_jitter_is_checked_separately_from_headers():
    odom = dict(mean_received_hz=100., header_interval=dict(p99_ms=10., max_ms=10.),
                receipt_interval=dict(p99_ms=12., max_ms=25.),
                backward_stamps=0, repeated_stamps=0, intervals_dropped=0)
    assert small_pool_timing_audit({'odometry': odom}, 10.)['valid']
    for bad_receipt in (None, {}, dict(p99_ms=21., max_ms=25.),
                        dict(p99_ms=12., max_ms=51.)):
        changed = dict(odom, receipt_interval=bad_receipt)
        assert not small_pool_timing_audit({'odometry': changed}, 10.)['valid']
    assert not small_pool_timing_audit({'odometry': dict(odom, header_interval=None)}, 10.)['valid']


def profile_reference_fixture():
    plan = dict.fromkeys(SMALL_POOL_MATCH_FIELDS, False)
    plan.update(cpu_profile=False, modes=['full', 'adaptive'], side_executor_threads=2,
                dedicated_static_pc_executor=True, monitor_intervals=True, compose=True,
                guarded_demand_replan=True, profiles={'full': 'f.yaml', 'adaptive': 'a.yaml'},
                effective_run_options={'full': {'rate': 10}, 'adaptive': {'rate': 10}},
                runtime_policy={'sha256': {
                    '/root/super_ws/src/SUPER/mission_planner/launch/benchmark_seedmap.launch.py': 'c' * 64}},
                asset_sha256={
                    '/root/super_ws/install/perfect_drone_sim/lib/perfect_drone_sim/' + name: 'a' * 64
                    for name in ('perfect_drone_full_node', 'perfect_drone_adaptive_node')})
    reference = copy.deepcopy(plan)
    reference['cpu_profile'] = True
    intervals = {'odometry': dict(mean_received_hz=100., header_interval=dict(p99_ms=11., max_ms=20.),
                                  receipt_interval=dict(p99_ms=12., max_ms=25.),
                                  backward_stamps=0, repeated_stamps=0, intervals_dropped=0)}
    profile = dict(processes=[dict(duration_s=10., stages=[
        dict(stage=s, calls=1000, clock_errors=0) for s in
        ('fsm_main_callback', 'fsm_command_callback')])])
    summaries = {}
    for row in pair():
        summaries[row['mode']] = dict(row, cpu_profile=True,
            small_pool_timing=small_pool_timing_audit(intervals, 10., profile),
            strict_recovery_audit={'valid': True}, demand_replan_exercised=True,
            reference_comparison={'mission_time_guardrail_pass': True})
    return plan, reference, summaries


def test_profile_reference_allows_reverse_order_and_separate_evidence_paths():
    plan, reference, summaries = profile_reference_fixture()
    plan['modes'].reverse()
    plan['asset_sha256']['/root/super-sector-filter/results/reference/plan.json'] = 'b' * 64
    assert small_pool_profile_reference_audit(plan, reference, summaries)['valid']


def test_profile_reference_rejects_changed_runtime_binary_options_or_profiles():
    for kind in ('binary', 'options', 'profiles', 'threads', 'missing_field', 'wrong_pair', 'launch', 'lease', 'static_phase'):
        plan, reference, summaries = profile_reference_fixture()
        if kind == 'binary':
            reference['asset_sha256'][next(iter(reference['asset_sha256']))] = 'b' * 64
        elif kind == 'options':
            reference['effective_run_options']['adaptive']['rate'] = 5
        elif kind == 'profiles':
            reference['profiles']['full'] = 'other.yaml'
        elif kind == 'threads':
            reference['side_executor_threads'] = 3
        elif kind == 'missing_field':
            del reference['snapshot_neighbor_cache']
        elif kind == 'wrong_pair':
            reference['modes'] = ['full']
        elif kind == 'lease':
            reference['extended_demand_lease'] = not plan['extended_demand_lease']
        elif kind == 'static_phase':
            reference['static_pc_two_phase'] = not plan['static_pc_two_phase']
        else:
            reference['runtime_policy']['sha256'][next(iter(reference['runtime_policy']['sha256']))] = 'd' * 64
        assert not small_pool_profile_reference_audit(plan, reference, summaries)['valid'], kind
    plan, reference, summaries = profile_reference_fixture()
    plan['runtime_policy'] = reference['runtime_policy'] = {'sha256': {}}
    assert not small_pool_profile_reference_audit(plan, reference, summaries)['valid']


def test_profile_reference_rejects_missing_or_failed_mode_checks():
    for mode in ('full', 'adaptive'):
        for key, value in [('success', False), ('safety_collisions', 1), ('cpu_profile', False),
                           ('resource_valid', False), ('cpu_comparison_instrumented', True),
                           ('small_pool_timing', {}), ('source_acquisition', {'checks': {}}),
                           ('strict_recovery_audit', {'valid': False}),
                           ('demand_replan_exercised', False), ('reference_comparison', {})]:
            plan, reference, summaries = profile_reference_fixture()
            summaries[mode][key] = value
            assert not small_pool_profile_reference_audit(plan, reference, summaries)['valid'], (mode, key)
    plan, reference, summaries = profile_reference_fixture()
    del summaries['adaptive']
    assert not small_pool_profile_reference_audit(plan, reference, summaries)['valid']


def test_profile_reference_requires_callback_and_receipt_coverage_and_time_guard():
    for key in ('odometry_receipt_p99', 'odometry_receipt_max', 'profile_callback_coverage'):
        plan, reference, summaries = profile_reference_fixture()
        del summaries['adaptive']['small_pool_timing']['checks'][key]
        assert not small_pool_profile_reference_audit(plan, reference, summaries)['valid']
    plan, reference, summaries = profile_reference_fixture()
    summaries['adaptive']['mission_time_s'] = 100.
    assert not small_pool_profile_reference_audit(plan, reference, summaries)['valid']
    plan, reference, summaries = profile_reference_fixture()
    reference['cpu_profile'] = False
    assert not small_pool_profile_reference_audit(plan, reference, summaries)['valid']


def demand_log(n=10, skips=7, cap='0.5'):
    counts = dict.fromkeys(DEMAND_REASONS, 0)
    counts.update(SKIP=skips, DISPATCH_DEADLINE=n - skips)
    fields = ','.join(f'{k}={v}' for k, v in counts.items())
    return (f'[DEMAND_REPLAN] checks={n} skips={skips} renewals=6\n'
            f'[DEMAND_REPLAN_REASONS] checks={n} counted={n} '
            f'max_dispatch_interval={cap} final_counts={fields}\n')


def test_demand_histogram_requires_matched_complete_monotonic_accounting():
    out = demand_reason_audit(demand_log() + demand_log(20, 14), .5)
    assert out['valid'] and out['reports'][-1]['counts']['SKIP'] == 14
    assert demand_reason_audit(demand_log(cap='0.25'), .25)['valid']
    for text in ('', demand_log(cap='nan'), demand_log(cap='0.25'),
                 demand_log().replace('counted=10', 'counted=11'),
                 demand_log().replace('skips=7', 'skips=6'),
                 demand_log().replace('DISABLED=0,', ''),
                 demand_log().replace('DISABLED=0,', 'DISABLED=0,DISABLED=0,'),
                 demand_log().replace('DISABLED=0', 'DISABLED=-1'),
                 demand_log().replace('DISABLED=0', 'UNKNOWN=0'),
                 demand_log().replace('DISABLED=0', 'DISABLED=oops'),
                 demand_log() + demand_log(),
                 demand_log() + demand_log(20, 5)):
        assert not demand_reason_audit(text, .5)['valid'], text


def test_static_phase_requires_actual_cancel_post_bootstrap_and_no_fallback():
    stack = ('[STATIC_PC_TWO_PHASE] enabled=true phase=fast initial_poll_ms=1 \n'
             '[STATIC_PC_TWO_PHASE] enabled=true phase=coarse poll_ms=100 '
             'ros_elapsed_s=5.100001 fast_timer_canceled=1\n')
    assert static_two_phase_audit(stack)['valid']
    assert not static_two_phase_audit(stack)['callback_counts_instrumented']
    for bad in ('', stack + stack, stack.replace('5.100001', '5.09'),
                stack.replace('5.100001', 'nan'), stack.replace('5.100001', 'bad'),
                stack.replace('canceled=1', 'canceled=0'),
                stack + '[STATIC_PC_TWO_PHASE] enabled=true phase=legacy_fallback poll_ms=1'):
        assert not static_two_phase_audit(bad)['valid'], bad
    profile = dict(processes=[dict(duration_s=30., stages=[dict(
        stage='sim_static_cloud_callback', calls=300, clock_errors=0)])])
    assert static_two_phase_audit(stack, profile)['valid']
    profile['processes'][0]['stages'][0]['calls'] = 30000
    assert not static_two_phase_audit(stack, profile)['valid']
    assert not static_two_phase_audit(stack, {})['valid']


def test_unresolved_static_delivery_cannot_claim_target_or_bless_reference():
    rows = pair()
    rows[1]['static_pc_two_phase'] = True
    out = comparison(rows)
    assert out['safety_and_quality_pass']
    assert not out['static_delivery_preservation_pass'] and not out['target_met']
    plan, reference, summaries = profile_reference_fixture()
    plan['static_pc_two_phase'] = reference['static_pc_two_phase'] = True
    assert not small_pool_profile_reference_audit(plan, reference, summaries)['valid']


def goal_identity_log():
    return ('[MISSION_GOAL_IDENTITY_SETTINGS] enabled=1 executor=single callbacks_serialized=1 timers_qos_unchanged=1\n'
            '[GOAL_RETRANSMIT_IDENTITY] enabled=true role=receiver guarded_demand=true identity=creation_stamp_raw_pose_frame default_off=true\n'
            '[MISSION_GOAL_IDENTITY] stamp_ns=100 new_intent=1 new_identity=1 supported=1 waypoint=0\n'
            '[MISSION_GOAL_IDENTITY] stamp_ns=100 new_intent=0 new_identity=0 supported=1 waypoint=0\n'
            '[GOAL_RETRANSMIT_COALESCED] stamp_ns=100 generation=5 map=6 queued_revision=1 accepted_revision=1 coalesced_total=1\n')


def test_goal_identity_requires_explicit_repeated_identity_and_actual_coverage():
    log = goal_identity_log()
    assert goal_identity_audit(log)['valid']
    assert goal_identity_audit(log)['coalesced'] == 1
    for bad in ('', log.replace('supported=1', 'supported=0'),
                log.replace('new_intent=0', 'new_intent=1'),
                log.replace('COALESCED] stamp_ns=100', 'COALESCED] stamp_ns=101'),
                log.replace('generation=5', 'generation=0'),
                log.replace('coalesced_total=1', 'coalesced_total=2'),
                log.replace('executor=single', 'executor=multi'),
                log.replace('stamp_ns=100 new_intent=0', 'stamp_ns=101 new_intent=0')):
        assert not goal_identity_audit(bad)['valid'], bad


def test_goal_coalescing_must_be_exercised_in_both_compared_modes():
    rows = pair()
    for row in rows:
        row['goal_retransmit_identity'] = True
        row['goal_retransmit_exercised'] = True
    assert comparison(rows)['target_met']
    rows[0]['goal_retransmit_exercised'] = False
    assert not comparison(rows)['target_met']


def test_headless_effective_settings_require_all_composed_nodes_and_one_marker():
    for mode, count in [('full', 3), ('adaptive', 4)]:
        log = (f'[HEADLESS_PARAMETER_SETTINGS] enabled=1 mode={mode} nodes={count} '
               'parameter_services_nodes=0 parameter_event_publisher_nodes=0 '
               'local_parameters_preserved=1 default_off=1')
        assert headless_parameter_audit(log, mode)['valid']
        for bad in ('', log + '\n' + log, log.replace('enabled=1', 'enabled=0'),
                    log.replace('services_nodes=0', 'services_nodes=1'),
                    log.replace('publisher_nodes=0', 'publisher_nodes=1'),
                    log.replace(f'nodes={count} ', 'nodes=2 '),
                    log.replace('local_parameters_preserved=1', 'local_parameters_preserved=0')):
            assert not headless_parameter_audit(bad, mode)['valid'], bad


def test_headless_profile_reference_needs_effective_setting_evidence():
    plan, reference, summaries = profile_reference_fixture()
    plan['headless_parameter_services'] = reference['headless_parameter_services'] = True
    assert not small_pool_profile_reference_audit(plan, reference, summaries)['valid']
    for row in summaries.values():
        row['headless_parameter_audit'] = dict(valid=True)
    assert small_pool_profile_reference_audit(plan, reference, summaries)['valid']
