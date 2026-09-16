#!/usr/bin/env python3
"""One exploratory flight per selected mode/candidate; never discard outcomes.

The default objective is >=40% reduction in experiment-cgroup mean used CPUs, with
contact-free completion and no artificial long-hold gain. Integrated CPU time
is reported separately. A different engineering threshold must be declared before
launch. Each invocation is n1; an external prospective campaign can freeze and
repeat it, but the per-invocation output is not statistical confirmation.
"""
import argparse
import csv
import fcntl
import json
import math
import os
from pathlib import Path
import re
import time

import psutil
import normal_cpu_gpu_diagnostic as diagnostic
import event_recovery_seed1_smoke as event
import sensor_acquisition_seed1_smoke as source
import audit_cpu40_recovery as recovery_audit
import analyze_thread_cpu_profile as stage_profile
import static_latched_preflight
from analyze_cylinder_only_stress_full_gate import quality_valid

BACKUP = 'results/adaptive_cpu40_backup_20260916_aloDDu/runtime_before.tar.gz'
FLIGHT_NAMES = {'fsm_node', 'perfect_drone_node', 'perfect_drone_full_node',
                'perfect_drone_frontend_node', 'perfect_drone_adaptive_node',
                'source_acquisition_test'}


def latched_preflight_asset_paths(validation, context=None):
    """The validator's runtime hashes use binding names; evidence uses paths."""
    return ({static_latched_preflight.spec(context)['paths'][name]
             for name in validation['runtime_sha256']} |
            {Path(path) for path in validation['evidence_sha256']})


def small_pool_timing_audit(intervals, sensor_hz, profile=None):
    """Prospective engineering gates for <4 workers, not real-time proof."""
    odom = intervals.get('odometry', {})
    header = odom.get('header_interval') or {}
    receipt = odom.get('receipt_interval') or {}
    def finite_between(value, lower, upper):
        return (isinstance(value, (int, float)) and math.isfinite(value)
                and lower <= value <= upper)
    checks = dict(
        sensor_cadence=finite_between(sensor_hz, 9.5, 10.5),
        odometry_cadence=finite_between(odom.get('mean_received_hz'), 98., 102.),
        odometry_header_p99=finite_between(header.get('p99_ms'), 0., 20.),
        odometry_header_max=finite_between(header.get('max_ms'), 0., 50.),
        odometry_receipt_p99=finite_between(receipt.get('p99_ms'), 0., 20.),
        odometry_receipt_max=finite_between(receipt.get('max_ms'), 0., 50.),
        odometry_order=all(odom.get(k, 1) == 0 for k in
                           ('backward_stamps', 'repeated_stamps', 'intervals_dropped')))
    rates = {}
    if profile is not None:
        processes = profile.get('processes', [])
        if len(processes) == 1 and processes[0].get('duration_s', 0) >= 5:
            p = processes[0]
            for s in p['stages']:
                if s['stage'] in ('fsm_main_callback', 'fsm_command_callback'):
                    rates[s['stage']] = s['calls'] / p['duration_s']
                    checks[s['stage']] = finite_between(rates[s['stage']], 98., 102.) and s['clock_errors'] == 0
        checks['profile_callback_coverage'] = len(rates) == 2
    return dict(valid=all(checks.values()), checks=checks, callback_hz=rates,
                callback_counts_instrumented=profile is not None,
                scope='Finite-run engineering guard; command message gaps include intentional holds and are not callback gaps')


SMALL_POOL_MATCH_FIELDS = (
    'schema', 'map', 'profiles', 'compose', 'effective_run_options',
    'skip_backup_diagnostic_replay', 'skip_unobserved_path_publication',
    'fast_occupied_box_scan', 'compare_occupied_box_scan', 'snapshot_line_query',
    'snapshot_neighbor_cache', 'static_pc_poll_ms', 'static_pc_two_phase', 'side_executor_threads',
    'monitor_intervals', 'guarded_demand_replan', 'extended_demand_lease', 'goal_retransmit_identity',
    'dedicated_static_pc_executor', 'headless_parameter_services', 'static_pc_durable',
    'frontend_dedicated_executor', 'effective_frontend_executor', 'static_pc_cached_executor',
    'static_pc_latched_once', 'static_latched_preflight_sha256',
    'optimizer_phase_memory_trace', 'optimizer_clearance_gate_first', 'time_reference_folder',
    'max_same_mode_reference_time_ratio', 'max_mission_time_ratio',
    'logical_cpus', 'frozen_normal_sha256', 'callback_trace')


def small_pool_profile_reference_audit(plan, reference_plan, summaries):
    """Match every selected mode to its own passed profiled timing preflight.

    No CPU-reduction threshold is required of the preflight. Run identifiers,
    output/evidence paths and mode order may differ; runtime inputs may not.
    """
    selected = plan.get('modes', [])
    reference_modes = reference_plan.get('modes', [])
    modes = set(selected)
    same_fields = all(k in plan and k in reference_plan and
                      plan[k] == reference_plan[k] for k in SMALL_POOL_MATCH_FIELDS)
    def runtime_hashes(value):
        return {k: v for k, v in value.get('asset_sha256', {}).items()
                if k.startswith('/root/super_ws/')}
    current_hashes = runtime_hashes(plan)
    required_binaries = {
        '/root/super_ws/install/perfect_drone_sim/lib/perfect_drone_sim/' + name
        for name in ('perfect_drone_full_node', 'perfect_drone_adaptive_node')}
    checks = dict(
        unprofiled_confirmation=plan.get('cpu_profile') is False,
        profiled_preflight=reference_plan.get('cpu_profile') is True,
        matching_mode_set=(bool(modes) and modes <= {'full', 'sector', 'adaptive'} and
                           len(selected) == len(modes) and
                           len(reference_modes) == len(modes) and
                           set(reference_modes) == modes),
        matching_runtime_options=same_fields,
        matching_runtime_hashes=(required_binaries <= current_hashes.keys() and
                                 current_hashes == runtime_hashes(reference_plan)),
        matching_frozen_runtime_policy=(
            bool(plan.get('runtime_policy', {}).get('sha256')) and
            plan.get('runtime_policy') == reference_plan.get('runtime_policy')),
        small_pool_configuration=(plan.get('side_executor_threads') in (2, 3) and
                                  plan.get('dedicated_static_pc_executor') is True and
                                  plan.get('monitor_intervals') is True and
                                  plan.get('compose') is True))
    required_timing = ('sensor_cadence', 'odometry_cadence', 'odometry_header_p99',
                       'odometry_header_max', 'odometry_receipt_p99',
                       'odometry_receipt_max', 'odometry_order', 'fsm_main_callback',
                       'fsm_command_callback', 'profile_callback_coverage')
    for mode in sorted(modes):
        row = summaries.get(mode, {})
        source_checks = row.get('source_acquisition', {}).get('checks', {})
        timing = row.get('small_pool_timing', {})
        timing_checks = timing.get('checks', {})
        checks[mode + '_safe_source'] = (
            row.get('mode') == mode and row.get('cpu_profile') is True and
            all(row.get(k) is True for k in
                ('success', 'run_valid', 'resource_valid', 'speed_limit_valid')) and
            row.get('safety_collisions') == 0 and bool(source_checks) and
            all(v is True for v in source_checks.values()) and
            row.get('strict_recovery_audit', {}).get('valid') is True and
            row.get('strict_recovery_audit', {}).get('mode') == mode and
            not row.get('cpu_comparison_instrumented', False))
        if mode == 'sector':
            checks['sector_fixed_source'] = source_checks.get('fixed_sector_never_full') is True
        checks[mode + '_profile_timing'] = (
            timing.get('valid') is True and
            timing.get('callback_counts_instrumented') is True and
            all(timing_checks.get(k) is True for k in required_timing))
        checks[mode + '_reference_time'] = (
            row.get('reference_comparison', {}).get('mission_time_guardrail_pass') is True)
        checks[mode + '_demand_exercised'] = (
            not plan.get('guarded_demand_replan') or
            row.get('demand_replan_exercised') is True)
        checks[mode + '_static_delivery_preservation'] = (
            not (plan.get('static_pc_two_phase') or plan.get('static_pc_latched_once')) or
            row.get('static_pc_delivery_validated') is True)
        checks[mode + '_static_latched_runtime'] = (
            not plan.get('static_pc_latched_once') or
            row.get('static_latched_audit', {}).get('valid') is True)
        checks[mode + '_goal_identity_exercised'] = (
            not plan.get('goal_retransmit_identity') or
            row.get('goal_retransmit_exercised') is True)
        checks[mode + '_headless_parameter_settings'] = (
            not plan.get('headless_parameter_services') or
            row.get('headless_parameter_audit', {}).get('valid') is True)
        checks[mode + '_frontend_executor'] = (
            not plan.get('frontend_dedicated_executor') or mode == 'full' or
            row.get('frontend_executor_audit', {}).get('valid') is True)
        checks[mode + '_static_cached_executor'] = (
            not plan.get('static_pc_cached_executor') or
            row.get('static_cached_executor_audit', {}).get('valid') is True)
        checks[mode + '_optimizer_clearance_gate_first'] = (
            not plan.get('optimizer_clearance_gate_first') or
            row.get('optimizer_clearance_gate_audit', {}).get('valid') is True)
    if {'full', 'adaptive'} <= modes:
        ftime = summaries.get('full', {}).get('mission_time_s')
        atime = summaries.get('adaptive', {}).get('mission_time_s')
        checks['paired_mission_time'] = (
            all(isinstance(t, (int, float)) and math.isfinite(t) and t > 0
                for t in (ftime, atime)) and atime / ftime <= 1.10)
    return dict(valid=all(checks.values()), checks=checks,
                modes_audited=sorted(modes),
                paired_mission_time_applicable={'full', 'adaptive'} <= modes,
                scope='Matched profiled finite-run timing preflight; not a real-time or safety guarantee')


def reference_comparison(result, reference):
    ratio = result['mission_time_s'] / reference['mission_time_s']
    if reference.get('time_only') is True:
        return dict(mission_time_ratio=ratio, mission_time_guardrail_pass=ratio <= 1.10,
                    mean_cpu_reduction_pct=None, cumulative_cpu_reduction_pct=None,
                    scope='Historical same-map/mode timing ceiling only; older policy CPU is not a comparison control')
    return dict(mission_time_ratio=ratio, mission_time_guardrail_pass=ratio <= 1.10,
                mean_cpu_reduction_pct=100 * (1 - result['end_to_end_cpu_cores_mean'] /
                                               reference['end_to_end_cpu_cores_mean']),
                cumulative_cpu_reduction_pct=100 * (1 - result['end_to_end_cpu_core_s'] /
                                                     reference['end_to_end_cpu_core_s']),
                scope='Same-mode predeclared exploratory reference; not an isolated causal ablation')


DEMAND_REASONS = (
    'DISABLED', 'INVALID_POLICY', 'NOT_ORDINARY', 'NEW_GOAL', 'RECOVERY_PENDING',
    'SAFETY_PENDING', 'FAILURE_OR_REJECTION', 'NO_SUCCESSFUL_LEASE',
    'STALE_OR_UNCERTIFIED_MAP', 'TRAJECTORY_MISMATCH', 'CLOCK_INVALID',
    'DISPATCH_DEADLINE', 'ON_BACKUP', 'INSUFFICIENT_GEOMETRY',
    'INSUFFICIENT_MOTION_HORIZON', 'NEED_VIABILITY_RENEWAL',
    'VIABILITY_RENEWAL_REJECTED', 'EVIDENCE_CHANGED', 'SKIP')


def demand_reason_audit(stack, max_dispatch_interval):
    """Check final-outcome accounting, not a continuous-safety certificate."""
    aggregate = {int(n): (int(skips), int(renewals)) for n, skips, renewals in
                 re.findall(r'\[DEMAND_REPLAN\] checks=(\d+) skips=(\d+) renewals=(\d+)', stack)}
    reports = []
    valid = True
    previous = None
    for match in re.finditer(
            r'\[DEMAND_REPLAN_REASONS\] checks=(\d+) counted=(\d+) '
            r'max_dispatch_interval=([^\s]+) final_counts=([^\s]+)', stack):
        checks, counted, cap, fields = match.groups()
        entries = [field.split('=') for field in fields.split(',')]
        if any(len(p) != 2 or not p[1].isdigit() for p in entries):
            valid = False
            continue
        counts = {key: int(value) for key, value in entries}
        try:
            cap_matches = float(cap) == max_dispatch_interval
        except ValueError:
            cap_matches = False
        n, total = int(checks), int(counted)
        row_valid = (len(entries) == len(counts) == len(DEMAND_REASONS) and
                     set(counts) == set(DEMAND_REASONS) and
                     n == total == sum(counts.values()) and n in aggregate and
                     counts.get('SKIP') == aggregate.get(n, (None, None))[0] and
                     cap_matches)
        if previous is not None:
            row_valid = row_valid and n > previous['checks'] and all(
                counts.get(k, -1) >= v for k, v in previous['counts'].items())
        row = dict(checks=n, counted=total, counts=counts, valid=row_valid)
        reports.append(row)
        previous = row
        valid = valid and row_valid
    return dict(valid=bool(reports) and valid, reports=reports,
                max_dispatch_interval_s=max_dispatch_interval,
                scope='Cumulative final outcomes after renewal; early-gated ticks and final partial report interval excluded')


def static_two_phase_audit(stack, profile=None):
    """Confirm bootstrap-preserving handoff; not late DDS delivery proof."""
    handoffs = re.findall(
        r'\[STATIC_PC_TWO_PHASE\] enabled=true phase=coarse poll_ms=100 '
        r'ros_elapsed_s=([^\s]+) fast_timer_canceled=([01])', stack)
    valid_handoff = False
    if len(handoffs) == 1:
        try:
            elapsed = float(handoffs[0][0])
            valid_handoff = math.isfinite(elapsed) and elapsed >= 5.1 and handoffs[0][1] == '1'
        except ValueError:
            pass
    checks = dict(
        startup_fast=('[STATIC_PC_TWO_PHASE] enabled=true phase=fast initial_poll_ms=1 ' in stack),
        single_post_bootstrap_handoff=valid_handoff,
        no_clock_fallback=('[STATIC_PC_TWO_PHASE] enabled=true phase=legacy_fallback ' not in stack))
    callback_hz = None
    if profile is not None:
        processes = profile.get('processes', [])
        checks['profile_static_callback_rate'] = False
        if len(processes) == 1 and processes[0].get('duration_s', 0) >= 10:
            p = processes[0]
            stages = [s for s in p['stages'] if s['stage'] == 'sim_static_cloud_callback']
            if len(stages) == 1:
                callback_hz = stages[0]['calls'] / p['duration_s']
                checks['profile_static_callback_rate'] = (
                    math.isfinite(callback_hz) and 5 <= callback_hz <= 20 and
                    stages[0]['clock_errors'] == 0)
    return dict(valid=all(checks.values()), checks=checks, callback_hz=callback_hz,
                callback_counts_instrumented=profile is not None,
                scope='Stable-clock startup/handoff and reduced callback rate only; no late-reader delivery guarantee')


def goal_identity_audit(stack):
    """Check explicit producer identities and actual healthy receiver coalescing.

    Geometry/health concurrency is tested separately in the receiver; these logs
    establish exercised identity linkage, not a continuous-safety certificate.
    """
    publications = [tuple(map(int, row)) for row in re.findall(
        r'\[MISSION_GOAL_IDENTITY\] stamp_ns=(\d+) new_intent=([01]) '
        r'new_identity=([01]) supported=([01]) waypoint=(\d+)', stack)]
    coalesced = [tuple(map(int, row)) for row in re.findall(
        r'\[GOAL_RETRANSMIT_COALESCED\] stamp_ns=(\d+) generation=(\d+) '
        r'map=(\d+) queued_revision=(\d+) accepted_revision=(\d+) '
        r'coalesced_total=(\d+)', stack)]
    consistent = bool(publications)
    previous = None
    issued = set()
    repeated = set()
    for row in publications:
        stamp, intent, new, supported, waypoint = row
        consistent = consistent and supported == 1 and stamp > 0
        if new:
            consistent = consistent and stamp not in issued and (
                previous is None or stamp > previous[0])
            issued.add(stamp)
        else:
            consistent = consistent and intent == 0 and previous is not None and (
                stamp == previous[0] and waypoint == previous[4])
            repeated.add(stamp)
        if intent:
            consistent = consistent and new == 1
        previous = row
    checks = dict(
        producer_serialized=('[MISSION_GOAL_IDENTITY_SETTINGS] enabled=1 executor=single '
                             'callbacks_serialized=1 timers_qos_unchanged=1' in stack),
        receiver_enabled=('[GOAL_RETRANSMIT_IDENTITY] enabled=true role=receiver guarded_demand=true '
                          'identity=creation_stamp_raw_pose_frame default_off=true' in stack),
        producer_identity_consistent=bool(consistent),
        actual_retransmissions=bool(repeated),
        actual_receiver_coalescing=bool(coalesced),
        coalesced_identity_linkage=bool(coalesced) and all(
            stamp in repeated and all(v > 0 for v in (gen, version, queued, accepted))
            for stamp, gen, version, queued, accepted, total in coalesced),
        coalesced_counter=bool(coalesced) and
            [row[-1] for row in coalesced] == list(range(1, len(coalesced) + 1)))
    return dict(valid=all(checks.values()), checks=checks,
                publications=len(publications), creation_identities=len(issued),
                repeated_identities=len(repeated), coalesced=len(coalesced),
                scope='Explicit creation-ID linkage and exercised coverage; not proof that every repeat may safely be suppressed')


def headless_parameter_audit(stack, mode):
    """Effective constructed-node settings; local parameter semantics tested separately."""
    rows = re.findall(
        r'\[HEADLESS_PARAMETER_SETTINGS\] enabled=([01]) mode=(full|adaptive) '
        r'nodes=(\d+) parameter_services_nodes=(\d+) '
        r'parameter_event_publisher_nodes=(\d+) local_parameters_preserved=([01]) '
        r'default_off=([01])', stack)
    expected_mode = 'full' if mode == 'full' else 'adaptive'
    expected = ('1', expected_mode, '3' if mode == 'full' else '4', '0', '0', '1', '1')
    return dict(valid=rows == [expected], settings=rows,
                scope='Composed nodes only; remote parameter services/events unavailable under opt-in; external mission node unchanged')


def frontend_executor_audit(stack, profile=None):
    marker = ('[FRONTEND_EXECUTOR_SETTINGS] dedicated=1 executor=single '
              'node=native_sector_cpp existing_default_group=1 callbacks_qos_cadence_unchanged=1')
    checks = dict(single_dedicated_marker=stack.count(marker) == 1,
                  no_shared_marker='[FRONTEND_EXECUTOR_SETTINGS] dedicated=0 ' not in stack)
    role = None
    if profile is not None:
        roles = [r for process in profile.get('processes', [])
                 for r in process.get('thread_roles', {}).get('roles', [])
                 if r.get('role') == 'frontend_event_executor']
        checks['actual_profiled_executor_thread'] = False
        if len(roles) == 1:
            role = roles[0]
            cpu = role.get('mean_used_cores')
            eligible = role.get('eligible_interval_s', 0)
            observed = role.get('observed_interval_s', 0)
            checks['actual_profiled_executor_thread'] = (
                role.get('unambiguous') is True and len(role.get('tids', [])) == 1 and
                isinstance(cpu, (int, float)) and math.isfinite(cpu) and cpu >= 0 and
                isinstance(eligible, (int, float)) and math.isfinite(eligible) and eligible >= 5 and
                isinstance(observed, (int, float)) and math.isfinite(observed) and
                .9 * eligible <= observed <= eligible + 1e-6)
    return dict(valid=all(checks.values()), checks=checks, actual_thread=role,
                thread_cpu_measured=profile is not None,
                scope='Adaptive-specific executor; its CPU remains included in the experiment total, never subtracted')


def static_cached_executor_audit(stack, profile=None):
    marker = ('[STATIC_PC_EXECUTOR_KIND] cached_entities=1 executor=static_single '
              'callbacks_qos_cadence_unchanged=1')
    checks = dict(single_effective_marker=stack.count(marker) == 1,
                  no_default_marker='[STATIC_PC_EXECUTOR_KIND] cached_entities=0 ' not in stack,
                  legacy_timer='[STATIC_PC_POLL_SETTINGS] poll_ms=1 bootstrap_once=0' in stack,
                  legacy_qos='[STATIC_PC_DURABLE_SETTINGS] enabled=0 ' in stack)
    role = None
    hz = None
    if profile is not None:
        roles = [r for p in profile.get('processes', [])
                 for r in p.get('thread_roles', {}).get('roles', [])
                 if r.get('role') == 'sim_static_cloud_executor']
        checks['actual_profiled_executor_thread'] = False
        if len(roles) == 1:
            role = roles[0]
            cpu, eligible, observed = (role.get(k) for k in
                ('mean_used_cores', 'eligible_interval_s', 'observed_interval_s'))
            checks['actual_profiled_executor_thread'] = (
                role.get('unambiguous') is True and len(role.get('tids', [])) == 1 and
                all(isinstance(v, (int, float)) and math.isfinite(v)
                    for v in (cpu, eligible, observed)) and
                cpu >= 0 and eligible >= 5 and .9 * eligible <= observed <= eligible + 1e-6)
        stages = [(p.get('duration_s'), s) for p in profile.get('processes', [])
                  for s in p.get('stages', []) if s.get('stage') == 'sim_static_cloud_callback']
        checks['legacy_callback_cadence'] = False
        if len(stages) == 1:
            duration, stage = stages[0]
            calls = stage.get('calls')
            if (isinstance(duration, (int, float)) and math.isfinite(duration) and duration >= 5 and
                    isinstance(calls, int) and calls >= 0 and stage.get('clock_errors') == 0):
                hz = calls / duration
                checks['legacy_callback_cadence'] = 980 <= hz <= 1020
    return dict(valid=all(checks.values()), checks=checks, actual_thread=role,
                callback_hz=hz, thread_cpu_measured=profile is not None,
                scope='Executor class only; unchanged legacy 1ms timer and QoS; full thread CPU included')


def static_latched_audit(stack, profile=None, geometry=None):
    """Actual one-shot counters plus the retained executor's full thread CPU.

    This is a per-flight schedule audit; delivery additionally needs the bound
    six-arm/actual-RViz preflight. The idle executor is never subtracted.
    """
    geometry = geometry or static_latched_preflight.EXPECTED_GEOMETRY
    def records(marker):
        out = []
        for line in stack.splitlines():
            if marker not in line:
                continue
            prefix, body = line.split(marker, 1)
            row = dict(re.findall(r'(\w+)=([^\s]+)', body))
            stamps = re.findall(r'\[(\d+)\.(\d{1,9})\]', prefix)
            if stamps:
                sec, fraction = stamps[-1]
                row['_ns'] = int(sec) * 10**9 + int(fraction.ljust(9, '0'))
            out.append(row)
        return out

    initial = records('[STATIC_PC_LATCHED_PUBLICATION]')
    reports = records('[STATIC_PC_LATCHED_SUMMARY]')
    checks = dict(single_publication=len(initial) == 1,
                  cumulative_reports=len(reports) >= 2,
                  no_legacy_publication=('[STATIC_PC_PUBLICATION]' not in stack and
                                         'Publish global map size:' not in stack),
                  static_timer_disabled='[STATIC_PC_POLL_SETTINGS] poll_ms=0 bootstrap_once=1' in stack,
                  actual_durable_qos=('[STATIC_PC_DURABLE_SETTINGS] enabled=1 actual_qos=1 reliability=reliable '
                                      'durability=transient_local history=keep_last depth=1 intra_process=disabled '
                                      'publication_schedule=latched_once other_qos_unchanged=1' in stack),
                  deterministic_padding=('[STATIC_PC_LATCHED_SERIALIZATION] point_step=32 tail_zeroed_bytes=12 '
                                         'declared_fields_and_homogeneous_bytes_unchanged=1' in stack),
                  unchanged_counters=False, steady_span=False)
    baseline = None
    span = None
    fields = ('publications', 'points', 'bytes', 'stamp_ns', 'timers_created', 'poll_callbacks')
    if len(initial) == 1 and len(reports) >= 2:
        try:
            baseline = {k: int(initial[0][k]) for k in fields}
            checks['unchanged_counters'] = (
                initial[0].get('complete_geometry') == '1' and
                baseline['publications'] == 1 and baseline['points'] == geometry['points'] and
                baseline['bytes'] == geometry['bytes'] and baseline['stamp_ns'] > 0 and
                baseline['timers_created'] == baseline['poll_callbacks'] == 0 and
                all(r.get('enabled') == '1' and
                    {k: int(r[k]) for k in fields} == baseline for r in reports))
            stamps = [r['_ns'] for r in reports]
            span = (stamps[-1] - stamps[0]) / 1e9
            checks['steady_span'] = span >= 5 and all(b >= a for a, b in zip(stamps, stamps[1:]))
        except (KeyError, ValueError, TypeError):
            pass
    role = None
    if profile is not None:
        roles = [r for p in profile.get('processes', [])
                 for r in p.get('thread_roles', {}).get('roles', [])
                 if r.get('role') == 'sim_static_cloud_executor']
        checks['actual_profiled_executor_thread'] = False
        if len(roles) == 1:
            role = roles[0]
            cpu, eligible, observed = (role.get(k) for k in
                ('mean_used_cores', 'eligible_interval_s', 'observed_interval_s'))
            checks['actual_profiled_executor_thread'] = (
                role.get('unambiguous') is True and len(role.get('tids', [])) == 1 and
                all(isinstance(v, (int, float)) and math.isfinite(v) for v in (cpu, eligible, observed)) and
                cpu >= 0 and eligible >= 5 and .9 * eligible <= observed <= eligible + 1e-6)
        stages = [s for p in profile.get('processes', []) for s in p.get('stages', [])
                  if s.get('stage') == 'sim_static_cloud_callback']
        checks['no_profiled_poll_callbacks'] = all(
            s.get('calls') == 0 and s.get('clock_errors') == 0 for s in stages)
    return dict(valid=all(checks.values()), checks=checks, initial=baseline,
                summary_count=len(reports), steady_summary_span_s=span, actual_thread=role,
                thread_cpu_measured=profile is not None,
                scope='No static timer/poll; retained executor CPU remains in total; separate bound delivery preflight required')


def optimizer_clearance_gate_audit(stack, enabled):
    """Require both actual optimizer settings and exercised zero-gate branches.

    This verifies code-path coverage, not numerical equivalence or safety;
    those require the separate production-bound corpus and flight guards.
    """
    settings = re.findall(
        r'\[OPT_CLEARANCE_GATE_FIRST\] optimizer=(\w+) enabled=([01]) '
        r'objective_unchanged=([01])(?:\s|$)', stack)
    skips = re.findall(r'\[OPT_CLEARANCE_GATE_SKIP\] optimizer=(\w+) gate=0(?:\s|$)', stack)
    expected = {'exp', 'backup'}
    checks = dict(
        both_settings_once=(len(settings) == 2 and {s[0] for s in settings} == expected),
        effective_settings=bool(settings) and all(
            flag == str(int(enabled)) and unchanged == '1'
            for _, flag, unchanged in settings),
        both_zero_gate_branches=(len(skips) == 2 and set(skips) == expected)
            if enabled else not skips)
    return dict(valid=all(checks.values()), enabled=enabled, checks=checks,
                settings=settings, skipped_optimizers=skips,
                scope='One-time branch coverage; objective equivalence is tested separately')


def comparison(results, mean_cpu_reduction_target_pct=40.):
    if (not isinstance(mean_cpu_reduction_target_pct, (int, float)) or
            not math.isfinite(mean_cpu_reduction_target_pct) or
            not 0 <= mean_cpu_reduction_target_pct <= 100):
        raise ValueError('Mean CPU engineering target must be finite and within [0,100]')
    modes = {r['mode']: r for r in results}
    if not {'full', 'adaptive'} <= modes.keys():
        return dict(target_met=False, reason='Full/Adaptive pair incomplete',
                    mean_cpu_reduction_target_pct=mean_cpu_reduction_target_pct)
    f, a = modes['full'], modes['adaptive']
    out = dict(mean_cpu_reduction_target_pct=mean_cpu_reduction_target_pct,
               threshold_scope='Predeclared engineering objective; not statistical significance')
    for metric in ('end_to_end_cpu_cores_mean', 'end_to_end_cpu_core_s'):
        fv, av = f.get(metric), a.get(metric)
        out[metric + '_reduction_pct'] = (
            100 * (1 - av / fv)
            if isinstance(fv, (int, float)) and isinstance(av, (int, float))
            and math.isfinite(fv) and math.isfinite(av) and fv > 0 else None)
    out['mission_time_ratio'] = a['mission_time_s'] / f['mission_time_s']
    safe = all(r.get('success') is True and r.get('run_valid') is True
               and r.get('resource_valid') is True
               and r.get('speed_limit_valid') is True
               and r.get('safety_collisions') == 0
               and all(r['source_acquisition']['checks'].values()) for r in (f, a))
    reduction = out['end_to_end_cpu_cores_mean_reduction_pct']
    # A fixed declared guardrail prevents counting lower CPU rate caused by
    # protracted stationary operation as the requested performance success.
    out['safety_and_quality_pass'] = safe
    out['mission_time_guardrail_pass'] = out['mission_time_ratio'] <= 1.10
    out['per_mode_reference_time_guardrail_pass'] = all(
        r.get('reference_comparison', {}).get('mission_time_guardrail_pass', True)
        for r in (f, a))
    out['cpu_comparison_instrumented'] = any(
        r.get('cpu_comparison_instrumented', False) for r in (f, a))
    out['requires_unprofiled_confirmation'] = any(
        r.get('cpu_profile', False) for r in (f, a))
    demand_requested = any('guarded_demand_replan_active' in
                           r['source_acquisition']['checks'] for r in (f, a))
    # Coverage, not a safety certificate: a sticky recovery state prevented
    # every Full lease in C7. Do not accept that as the intended common-policy
    # comparison even if its numerical threshold were to pass.
    out['common_demand_exercise_pass'] = not demand_requested or all(
        r.get('demand_replan_exercised') is True for r in (f, a))
    # The two-phase prototype preserves startup truth delivery, but both it and
    # legacy still fail the declared late-reader preservation test. Measure its
    # CPU effect without promoting an unresolved delivery prototype to success.
    out['static_delivery_preservation_pass'] = all(
        not (r.get('static_pc_two_phase', False) or r.get('static_pc_latched_once', False)) or
        r.get('static_pc_delivery_validated') is True for r in (f, a))
    out['common_goal_identity_exercise_pass'] = all(
        not r.get('goal_retransmit_identity', False) or
        r.get('goal_retransmit_exercised') is True for r in (f, a))
    out['measured_threshold_pass'] = bool(safe and out['mission_time_guardrail_pass']
                                         and out['per_mode_reference_time_guardrail_pass']
                                         and out['common_demand_exercise_pass']
                                         and out['static_delivery_preservation_pass']
                                         and out['common_goal_identity_exercise_pass']
                                         and not out['cpu_comparison_instrumented']
                                         and reduction is not None
                                         and reduction >= mean_cpu_reduction_target_pct)
    out['target_met'] = (out['measured_threshold_pass']
                         and not out['requires_unprofiled_confirmation'])
    out['exploratory_n1_only'] = True
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--run', type=int, required=True)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--map', choices=tuple(static_latched_preflight.MAP_GEOMETRIES), default='seed1')
    parser.add_argument('--mean-cpu-reduction-target-pct', type=float, default=40.,
                        help='Predeclared engineering threshold, not statistical significance (default40)')
    parser.add_argument('--modes', nargs='+', choices=('full', 'sector', 'adaptive'),
                        default=['full', 'adaptive'])
    parser.add_argument('--compose', action='store_true')
    parser.add_argument('--profile-cpu', action='store_true')
    parser.add_argument('--callback-trace', action='store_true',
                        help='Diagnostic wall-time callback spans; separate from untraced CPU evidence')
    parser.add_argument('--skip-backup-diagnostic-replay', action='store_true',
                        help='Skip discarded optimizer replay equally in all modes')
    parser.add_argument('--skip-unobserved-path-publication', action='store_true',
                        help='Retain path poses but avoid publishing without subscribers')
    parser.add_argument('--fast-occupied-box-scan', action='store_true')
    parser.add_argument('--compare-occupied-box-scan', action='store_true',
                        help='Dual-query correctness probe; never eligible for CPU target')
    parser.add_argument('--snapshot-line-query', action='store_true')
    parser.add_argument('--snapshot-neighbor-cache', action='store_true',
                        help='Exact snapshot-scoped neighborhood cache; requires line query')
    parser.add_argument('--static-pc-poll-ms', type=int, choices=(1, 100), default=1)
    parser.add_argument('--static-pc-two-phase', action='store_true',
                        help='Preserve legacy1ms startup; after5.1s use100ms subscriber polling')
    parser.add_argument('--static-pc-latched-once', action='store_true',
                        help='Opt-in publisher AND reader contract: durable complete map once, no static timer')
    parser.add_argument('--static-latched-preflight', type=Path,
                        help='Current six-arm plus actual-RViz accepted evidence manifest required for latched mode')
    parser.add_argument('--side-executor-threads', type=int, choices=range(2, 17), default=10)
    parser.add_argument('--monitor-intervals', action='store_true',
                        help='Bounded received-message interval statistics on existing monitor subscriptions')
    parser.add_argument('--guarded-demand-replan', action='store_true')
    parser.add_argument('--extended-demand-lease', action='store_true',
                        help='Opt in to 0.5s maximum dispatch age; rolling safety evidence and timer cadence unchanged')
    parser.add_argument('--goal-retransmit-identity', action='store_true',
                        help='Paired mission creation-ID retransmission and healthy receiver coalescing')
    parser.add_argument('--headless-parameter-services', action='store_true',
                        help='Disable unused remote parameter services/events in all composed nodes; retain local startup parameters')
    parser.add_argument('--frontend-dedicated-executor', action='store_true',
                        help='Move existing composed frontend callbacks to one dedicated executor; Full has no frontend and gets no dummy work')
    parser.add_argument('--dedicated-static-pc-executor', action='store_true')
    parser.add_argument('--static-pc-cached-executor', action='store_true',
                        help='Cache executable entities only in existing static-PC executor, preserving legacy 1ms timer and QoS')
    parser.add_argument('--no-optimizer-phase-memory-trace', action='store_true',
                        help='Disable per-solve diagnostic /proc reads and logs equally in both modes; retain external resource guards')
    parser.add_argument('--optimizer-clearance-gate-first', action='store_true',
                        help='Skip only an unused nearest-face calculation when its existing speed gate is zero; common to both optimizers/modes')
    parser.add_argument('--time-reference-folder', type=Path,
                        help='Predeclare same-mode <=1.10 mission-time guard and CPU reference')
    parser.add_argument('--small-pool-profile-reference', type=Path,
                        help='Passed matching same-mode-set profiled preflight required for unprofiled pools below4')
    parser.add_argument('--full-config', default=diagnostic.search.PROFILES['full'])
    parser.add_argument('--sector-config', default=diagnostic.search.PROFILES['sector'])
    parser.add_argument('--adaptive-config', default=event.PROFILE)
    args = parser.parse_args()
    map_context = static_latched_preflight.map_context(args.map)
    if (not math.isfinite(args.mean_cpu_reduction_target_pct) or
            not 0 <= args.mean_cpu_reduction_target_pct <= 100):
        parser.error('--mean-cpu-reduction-target-pct must be finite and within [0,100]')
    if len(set(args.modes)) != len(args.modes):
        parser.error('Each mode may run only once per candidate')
    if args.compare_occupied_box_scan and not args.fast_occupied_box_scan:
        parser.error('--compare-occupied-box-scan requires --fast-occupied-box-scan')
    if args.snapshot_neighbor_cache and not args.snapshot_line_query:
        parser.error('--snapshot-neighbor-cache requires --snapshot-line-query')
    if args.guarded_demand_replan and not args.time_reference_folder:
        parser.error('--guarded-demand-replan requires --time-reference-folder')
    if args.extended_demand_lease and not args.guarded_demand_replan:
        parser.error('--extended-demand-lease requires --guarded-demand-replan')
    if args.goal_retransmit_identity and not args.guarded_demand_replan:
        parser.error('--goal-retransmit-identity requires --guarded-demand-replan')
    if args.headless_parameter_services and not args.compose:
        parser.error('--headless-parameter-services requires --compose')
    if args.frontend_dedicated_executor and not args.compose:
        parser.error('--frontend-dedicated-executor requires --compose')
    if args.static_pc_cached_executor and not (
            args.compose and args.dedicated_static_pc_executor and args.static_pc_poll_ms == 1
            and not args.static_pc_two_phase):
        parser.error('--static-pc-cached-executor requires composed dedicated legacy 1ms static-PC executor')
    if args.static_pc_two_phase and (args.static_pc_poll_ms != 1 or not args.compose):
        parser.error('--static-pc-two-phase requires --static-pc-poll-ms 1 and --compose')
    latched_preflight = None
    if args.static_pc_latched_once:
        if not (args.compose and args.dedicated_static_pc_executor and args.static_pc_poll_ms == 1
                and not args.static_pc_two_phase and not args.static_pc_cached_executor
                and args.static_latched_preflight):
            parser.error('Latched mode requires composed dedicated executor, requested poll1, no two-phase/cache, and preflight')
        latched_preflight = static_latched_preflight.validate_manifest(args.static_latched_preflight, map_context)
        if not latched_preflight['valid']:
            parser.error('Latched delivery preflight invalid: ' + json.dumps(latched_preflight))
    elif args.static_latched_preflight:
        parser.error('--static-latched-preflight requires --static-pc-latched-once')
    if args.side_executor_threads < 4 and not (
            args.dedicated_static_pc_executor and args.monitor_intervals):
        parser.error('Pools below4 require --dedicated-static-pc-executor and --monitor-intervals')
    if args.side_executor_threads < 4 and not args.profile_cpu and not args.small_pool_profile_reference:
        parser.error('Unprofiled pools below4 require --small-pool-profile-reference')
    if args.small_pool_profile_reference and (args.side_executor_threads >= 4 or args.profile_cpu):
        parser.error('--small-pool-profile-reference is only for unprofiled pools below4')
    references = {}
    reference_files = []
    if args.time_reference_folder:
        for mode in args.modes:
            path = (args.time_reference_folder / f'{mode}_summary.json').resolve()
            reference = json.loads(path.read_text())
            if reference.get('map') != args.map or reference.get('mode') != mode or reference.get('success') is not True or any(
                    not isinstance(reference.get(key), (int, float)) or
                    not math.isfinite(reference[key]) or reference[key] <= 0
                    for key in ('mission_time_s', 'end_to_end_cpu_cores_mean', 'end_to_end_cpu_core_s')):
                parser.error(f'Invalid successful reference: {path}')
            references[mode] = reference
            reference_files.append(path)
    profile_reference_plan = None
    profile_reference_summaries = {}
    if args.small_pool_profile_reference:
        for name in ('plan.json', *(f'{mode}_summary.json' for mode in args.modes)):
            path = (args.small_pool_profile_reference / name).resolve()
            value = json.loads(path.read_text())
            reference_files.append(path)
            if name == 'plan.json':
                profile_reference_plan = value
            else:
                profile_reference_summaries[name.removesuffix('_summary.json')] = value
    root = args.output
    root.mkdir(parents=True, exist_ok=False)
    campaign = diagnostic.search.campaign
    lock = open(campaign.LOCK_PATH, 'a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    for p in psutil.process_iter(['cmdline']):
        cmd = p.info['cmdline'] or []
        if cmd and Path(cmd[0]).name in FLIGHT_NAMES:
            raise RuntimeError('Concurrent flight/renderer forbidden')
    if event.sha(event.NORMAL) != event.NORMAL_SHA:
        raise RuntimeError('Frozen Normal observations changed')
    os.environ['SUPER_CPU_PROFILE'] = '1' if args.profile_cpu else '0'
    os.environ['SUPER_CALLBACK_TRACE'] = '1' if args.callback_trace else '0'
    os.environ['SUPER_SKIP_BACKUP_DIAGNOSTIC_REPLAY'] = (
        '1' if args.skip_backup_diagnostic_replay else '0')
    os.environ['SUPER_SKIP_UNOBSERVED_PATH_PUBLICATION'] = (
        '1' if args.skip_unobserved_path_publication else '0')
    os.environ['SUPER_FAST_OCCUPIED_BOX_SCAN'] = '1' if args.fast_occupied_box_scan else '0'
    os.environ['SUPER_COMPARE_OCCUPIED_BOX_SCAN'] = '1' if args.compare_occupied_box_scan else '0'
    os.environ['SUPER_SNAPSHOT_LINE_QUERY'] = '1' if args.snapshot_line_query else '0'
    os.environ['SUPER_SNAPSHOT_NEIGHBOR_CACHE'] = '1' if args.snapshot_neighbor_cache else '0'
    os.environ['SUPER_STATIC_PC_POLL_MS'] = str(args.static_pc_poll_ms)
    os.environ['SUPER_STATIC_PC_TWO_PHASE'] = '1' if args.static_pc_two_phase else '0'
    os.environ['SUPER_STATIC_PC_DURABLE'] = '1' if args.static_pc_latched_once else '0'
    os.environ['SUPER_STATIC_PC_LATCHED_ONCE'] = '1' if args.static_pc_latched_once else '0'
    os.environ['SUPER_SIDE_EXECUTOR_THREADS'] = str(args.side_executor_threads)
    os.environ['SUPER_MONITOR_INTERVALS'] = '1' if args.monitor_intervals else '0'
    os.environ['SUPER_GUARDED_DEMAND_REPLAN'] = '1' if args.guarded_demand_replan else '0'
    os.environ['SUPER_GUARDED_DEMAND_EXTENDED_LEASE'] = '1' if args.extended_demand_lease else '0'
    os.environ['SUPER_GOAL_RETRANSMIT_IDENTITY'] = '1' if args.goal_retransmit_identity else '0'
    os.environ['SUPER_HEADLESS_PARAMETER_SERVICES'] = '1' if args.headless_parameter_services else '0'
    os.environ['SUPER_FRONTEND_DEDICATED_EXECUTOR'] = '0'  # Set explicitly per mode below.
    os.environ['SUPER_STATIC_PC_CACHED_EXECUTOR'] = '1' if args.static_pc_cached_executor else '0'
    os.environ['SUPER_STATIC_PC_DEDICATED_EXECUTOR'] = (
        '1' if args.dedicated_static_pc_executor else '0')
    os.environ['SUPER_OPTIMIZER_PHASE_MEMORY_TRACE'] = (
        '0' if args.no_optimizer_phase_memory_trace else '1')
    os.environ['SUPER_OPT_CLEARANCE_GATE_FIRST'] = (
        '1' if args.optimizer_clearance_gate_first else '0')
    runtime = Path('/root/super_ws/src/SUPER')
    profiles = {'full': args.full_config, 'sector': args.sector_config,
                'adaptive': args.adaptive_config}
    files = {runtime / 'super_planner/config' / name for name in profiles.values()}
    files.update(reference_files)
    if latched_preflight:
        files.add(args.static_latched_preflight.resolve())
        files.add(Path(static_latched_preflight.__file__).resolve())
        files.update(latched_preflight_asset_paths(latched_preflight, map_context))
    files.update({runtime / f'mars_uav_sim/perfect_drone_sim/config/{args.map}.yaml',
                  runtime / f'mars_uav_sim/perfect_drone_sim/pcd/seed_maps/{args.map}.pcd',
                  runtime / 'mission_planner/data/loop24.txt',
                  Path('/root/super_ws/install/marsim_render/lib/libmarsim_render.so'),
                  Path('/root/super_ws/install/mission_planner/lib/libnative_sector_cpp_component.so'),
                  Path('/root/super_ws/install/mission_planner/lib/mission_planner/waypoint_mission'),
                  runtime / 'mission_planner/Apps/ros2_waypoint_mission.cpp',
                  Path('/root/super_ws/install/perfect_drone_sim/lib/perfect_drone_sim/perfect_drone_full_node'),
                  Path('/root/super_ws/install/rog_map/lib/librog_map.a'),
                  Path('/root/super_ws/install/super_planner/lib/libsuper.a'),
                  Path(recovery_audit.__file__).resolve(),
                  Path(stage_profile.__file__).resolve(),
                  Path(diagnostic.__file__).resolve(),
                  Path(__file__).resolve().with_name('native_loop_monitor.py'),
                  Path(__file__).resolve().with_name('message_intervals.py'),
                  Path(__file__).resolve()})
    if args.compose:
        files.add(Path('/root/super_ws/install/perfect_drone_sim/lib/perfect_drone_sim/perfect_drone_adaptive_node'))
    if args.fast_occupied_box_scan or args.compare_occupied_box_scan:
        files.add(runtime / 'rog_map/include/rog_map/occupied_box_scan.hpp')
    if args.snapshot_line_query:
        files.add(runtime / 'rog_map/include/rog_map/snapshot_line_query.hpp')
    if args.snapshot_neighbor_cache:
        files.add(runtime / 'rog_map/include/rog_map/snapshot_neighborhood_cache.hpp')
    if args.optimizer_clearance_gate_first:
        files.update({runtime / 'super_planner/include/traj_opt/clearance_gate_policy.hpp',
                      runtime / 'super_planner/src/traj_opt/exp_traj_optimizer_s4.cpp',
                      runtime / 'super_planner/src/traj_opt/backup_traj_optimizer_s4.cpp'})
    hashes = {str(p): event.sha(p) for p in sorted(files)}
    frozen_policy = diagnostic.search.frozen_policy()
    diagnostic.RUN = args.run
    profiler = diagnostic.Profiler(root / 'telemetry.jsonl', map_name=args.map)
    effective_options = {
        mode: dict(diagnostic.search.OPTIONS,
                   optimizer_phase_memory_trace=not args.no_optimizer_phase_memory_trace,
                   sensor_acquisition=True,
                   sensor_planner_intra_process=args.compose,
                   adaptive_event_recovery=mode == 'adaptive') for mode in args.modes}
    plan = dict(
        schema='adaptive-cpu40-seed1-exploratory-v1', candidate=args.candidate,
        map=args.map, run=args.run, modes=args.modes, profiles=profiles,
        backup=BACKUP, mean_cpu_reduction_target_pct=args.mean_cpu_reduction_target_pct,
        threshold_scope='Predeclared engineering objective; not statistical significance',
        cumulative_cpu_also_reported=True, max_mission_time_ratio=1.10,
        compose=args.compose, cpu_profile=args.profile_cpu, callback_trace=args.callback_trace,
        skip_backup_diagnostic_replay=args.skip_backup_diagnostic_replay,
        skip_unobserved_path_publication=args.skip_unobserved_path_publication,
        fast_occupied_box_scan=args.fast_occupied_box_scan,
        compare_occupied_box_scan=args.compare_occupied_box_scan,
        snapshot_line_query=args.snapshot_line_query,
        snapshot_neighbor_cache=args.snapshot_neighbor_cache,
        static_pc_poll_ms=args.static_pc_poll_ms,
        static_pc_two_phase=args.static_pc_two_phase,
        static_pc_durable=args.static_pc_latched_once,
        static_pc_latched_once=args.static_pc_latched_once,
        static_latched_preflight_sha256=(latched_preflight['manifest_sha256'] if latched_preflight else None),
        static_pc_delivery_scope=('New durable reader contract, validated six-arm transport and actual RViz; legacy volatile reader NOT supported'
                                  if args.static_pc_latched_once else
                                  'Startup-ready CPU diagnostic only; late-reader preservation unresolved'
                                  if args.static_pc_two_phase else 'Legacy static publication'),
        side_executor_threads=args.side_executor_threads,
        monitor_intervals=args.monitor_intervals,
        guarded_demand_replan=args.guarded_demand_replan,
        extended_demand_lease=args.extended_demand_lease,
        goal_retransmit_identity=args.goal_retransmit_identity,
        headless_parameter_services=args.headless_parameter_services,
        frontend_dedicated_executor=args.frontend_dedicated_executor,
        effective_frontend_executor={mode: bool(args.frontend_dedicated_executor and mode != 'full')
                                     for mode in args.modes},
        dedicated_static_pc_executor=args.dedicated_static_pc_executor,
        static_pc_cached_executor=args.static_pc_cached_executor,
        optimizer_phase_memory_trace=not args.no_optimizer_phase_memory_trace,
        optimizer_clearance_gate_first=args.optimizer_clearance_gate_first,
        time_reference_folder=str(args.time_reference_folder) if args.time_reference_folder else None,
        max_same_mode_reference_time_ratio=1.10 if references else None,
        effective_run_options=effective_options,
        runtime_policy_note='Inherited base policy only; effective_run_options and profiles override it. Source acquisition follows native 10Hz cadence, not inherited filter-rate hint.',
        logical_cpus=os.cpu_count(), runtime_policy=frozen_policy,
        asset_sha256=hashes, baseline_seconds=12,
        common_parameters_unchanged=f'{args.map}/loop24/v7,45deg-half-angle,0.4deg/10Hz sensor',
        frozen_normal_sha256=event.NORMAL_SHA, no_automatic_retry=True,
        exploratory_tuning=True, not_pooled_with_previous_results=True)
    profile_reference_audit = None
    if profile_reference_plan is not None:
        profile_reference_audit = small_pool_profile_reference_audit(
            plan, profile_reference_plan, profile_reference_summaries)
        plan['small_pool_profile_reference'] = dict(
            folder=str(args.small_pool_profile_reference.resolve()), audit=profile_reference_audit)
    diagnostic.save(root / 'plan.json', plan)
    if profile_reference_audit is not None and not profile_reference_audit['valid']:
        raise RuntimeError('Small-pool profiled preflight mismatch or failed gates: ' +
                           json.dumps(profile_reference_audit['checks']))
    campaign.install_campaign_signal_handlers()
    profiler.thread.start()
    results = []
    try:
        with (root / 'raw.csv').open('x', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=campaign.FIELDS,
                                    extrasaction='ignore')
            writer.writeheader()
            stream.flush()
            for mode in args.modes:
                os.environ['SUPER_FRONTEND_DEDICATED_EXECUTOR'] = (
                    '1' if args.frontend_dedicated_executor and mode != 'full' else '0')
                profiler.mode, profiler.phase = mode, 'baseline'
                diagnostic.save(root / 'status.json', dict(pid=os.getpid(), state='RUNNING',
                    candidate=args.candidate, mode=mode, phase='baseline'))
                time.sleep(12)
                options = effective_options[mode]
                profiler.phase = 'flight'
                diagnostic.save(root / 'status.json', dict(pid=os.getpid(), state='RUNNING',
                    candidate=args.candidate, mode=mode, phase='flight'))
                row = campaign.run_one(args.map, mode, args.run, **options,
                    artifacts_dir=str(root / 'artifacts'),
                    seedmap_super_config_override=profiles[mode])
                writer.writerow(row)
                stream.flush()
                if not quality_valid(row):
                    raise RuntimeError('Invalid attempt retained; diagnose before retry')
                if profiler.error:
                    raise RuntimeError(profiler.error)
                if diagnostic.search.frozen_policy() != frozen_policy or any(
                        event.sha(p) != digest for p, digest in hashes.items()):
                    raise RuntimeError('Source/config/binary changed during candidate')
                result = diagnostic.summarize(profiler, row)
                if references:
                    result['reference_comparison'] = reference_comparison(result, references[mode])
                result['source_acquisition'] = source.audit_source(root / 'artifacts', args.run, mode, args.map)
                result['source_acquisition']['checks']['telemetry_map_scope'] = (
                    bool(result.get('processes')) and bool(result.get('threads_sorted_by_mean')) and
                    result.get('cgroup_interval_cores', {}).get('n', 0) >= 5 and
                    result.get('cgroup_interval_cores', {}).get('mean', 0) > 0)
                result['strict_recovery_audit'] = recovery_audit.audit_file(
                    root / 'artifacts' / f'{args.map}_run{args.run}_{mode}.attempt1.stack.log', mode)
                result['source_acquisition']['checks']['strict_source_recovery_audit'] = (
                    result['strict_recovery_audit']['valid'])
                stack = (root / 'artifacts' /
                    f'{args.map}_run{args.run}_{mode}.attempt1.stack.log').read_text(errors='replace')
                result['source_acquisition']['checks']['optimizer_phase_trace_setting'] = (
                    row.get('optimizer_phase_trace_enabled') is
                    (not args.no_optimizer_phase_memory_trace))
                # Older binaries predate this marker. Once present, check OFF
                # as well as ON; an accidental opt-in must not become control.
                if args.optimizer_clearance_gate_first or '[OPT_CLEARANCE_GATE_FIRST]' in stack:
                    result['optimizer_clearance_gate_audit'] = optimizer_clearance_gate_audit(
                        stack, args.optimizer_clearance_gate_first)
                    result['source_acquisition']['checks']['optimizer_clearance_gate_first'] = (
                        result['optimizer_clearance_gate_audit']['valid'])
                result['source_acquisition']['checks']['static_pc_poll_setting'] = (
                    f'[STATIC_PC_POLL_SETTINGS] poll_ms={0 if args.static_pc_latched_once else args.static_pc_poll_ms} '
                    f'bootstrap_once={int(args.static_pc_latched_once or args.static_pc_poll_ms == 100)}' in stack)
                result['source_acquisition']['checks']['static_pc_durable_setting'] = (
                    f'[STATIC_PC_DURABLE_SETTINGS] enabled={int(args.static_pc_latched_once)} ' in stack)
                if args.compose or mode == 'full':
                    result['source_acquisition']['checks']['side_executor_setting'] = (
                        f'[COMMON_EXECUTOR_SETTINGS] side_threads={args.side_executor_threads} ' in stack)
                    result['source_acquisition']['checks']['static_pc_executor_setting'] = (
                        '[STATIC_PC_EXECUTOR_SETTINGS] '
                        f'dedicated={int(args.dedicated_static_pc_executor)} ' in stack)
                if args.static_pc_two_phase:
                    result['static_pc_two_phase'] = True
                    result['static_pc_delivery_validated'] = False
                    result['static_pc_two_phase_audit'] = static_two_phase_audit(
                        stack, stage_profile.summarize(root, mode, args.run, args.map) if args.profile_cpu else None)
                    result['source_acquisition']['checks']['static_pc_two_phase'] = (
                        result['static_pc_two_phase_audit']['valid'])
                if args.static_pc_latched_once:
                    result['static_pc_latched_once'] = True
                    result['static_latched_audit'] = static_latched_audit(
                        stack, stage_profile.summarize(root, mode, args.run, args.map) if args.profile_cpu else None,
                        geometry=map_context['geometry'])
                    result['static_latched_preflight'] = static_latched_preflight.validate_manifest(
                        args.static_latched_preflight, map_context)
                    result['static_pc_delivery_validated'] = result['static_latched_preflight']['valid']
                    result['source_acquisition']['checks']['static_latched_runtime'] = result['static_latched_audit']['valid']
                    result['source_acquisition']['checks']['static_latched_delivery'] = result['static_pc_delivery_validated']
                if args.static_pc_cached_executor:
                    result['static_pc_cached_executor'] = True
                    result['static_cached_executor_audit'] = static_cached_executor_audit(
                        stack, stage_profile.summarize(root, mode, args.run, args.map) if args.profile_cpu else None)
                    result['source_acquisition']['checks']['static_cached_executor_settings'] = (
                        result['static_cached_executor_audit']['valid'])
                if args.monitor_intervals:
                    monitor_result = json.loads((root / 'artifacts' /
                        f'{args.map}_run{args.run}_{mode}.json').read_text())
                    intervals = monitor_result.get('message_intervals', {})
                    result['message_intervals'] = intervals
                    result['source_acquisition']['checks']['message_interval_audit_present'] = (
                        set(intervals) == {'command', 'odometry'} and all(
                            x.get('messages', 0) > 1 and x.get('intervals_dropped', 1) == 0
                            and x.get('backward_receipts', 1) == 0
                            for x in intervals.values()))
                if args.guarded_demand_replan:
                    demand_cap = 0.5 if args.extended_demand_lease else 0.25
                    result['source_acquisition']['checks']['guarded_demand_replan_active'] = (
                        f'[GUARDED_DEMAND_REPLAN] enabled=true max_dispatch_interval={demand_cap:g} ' in stack)
                    reports = re.findall(r'\[DEMAND_REPLAN\] checks=(\d+) skips=(\d+) renewals=(\d+)', stack)
                    result['demand_replan_reports'] = reports
                    result['demand_replan_exercised'] = bool(reports) and max(int(r[1]) for r in reports) > 0
                    if args.extended_demand_lease:
                        result['demand_reason_audit'] = demand_reason_audit(stack, demand_cap)
                        result['source_acquisition']['checks']['demand_reason_accounting'] = (
                            result['demand_reason_audit']['valid'])
                if args.goal_retransmit_identity:
                    result['goal_retransmit_identity'] = True
                    result['goal_identity_audit'] = goal_identity_audit(stack)
                    result['goal_retransmit_exercised'] = result['goal_identity_audit']['valid']
                    result['source_acquisition']['checks']['goal_identity_audit'] = (
                        result['goal_identity_audit']['valid'])
                if args.headless_parameter_services:
                    result['headless_parameter_services'] = True
                    result['headless_parameter_audit'] = headless_parameter_audit(stack, mode)
                    result['source_acquisition']['checks']['headless_parameter_settings'] = (
                        result['headless_parameter_audit']['valid'])
                if args.frontend_dedicated_executor and mode != 'full':
                    result['frontend_dedicated_executor'] = True
                    result['frontend_executor_audit'] = frontend_executor_audit(
                        stack, stage_profile.summarize(root, mode, args.run, args.map) if args.profile_cpu else None)
                    result['source_acquisition']['checks']['frontend_executor_settings'] = (
                        result['frontend_executor_audit']['valid'])
                if args.side_executor_threads < 4:
                    result['small_pool_timing'] = small_pool_timing_audit(
                        result.get('message_intervals', {}), row.get('sensor_hz'),
                        stage_profile.summarize(root, mode, args.run, args.map) if args.profile_cpu else None)
                    result['source_acquisition']['checks']['small_pool_timing'] = result['small_pool_timing']['valid']
                    if not args.profile_cpu:
                        result['small_pool_profile_reference'] = profile_reference_audit
                        result['source_acquisition']['checks']['small_pool_profile_reference'] = (
                            profile_reference_audit is not None and profile_reference_audit['valid'])
                if args.skip_backup_diagnostic_replay or args.fast_occupied_box_scan or args.snapshot_line_query:
                    stack = (root / 'artifacts' /
                        f'{args.map}_run{args.run}_{mode}.attempt1.stack.log').read_text(errors='replace')
                if args.skip_backup_diagnostic_replay:
                    result['source_acquisition']['checks']['backup_replay_skip_active'] = (
                        '[BACKUP_DIAGNOSTIC_REPLAY] skip=true' in stack)
                if args.fast_occupied_box_scan:
                    compare_label = 'true' if args.compare_occupied_box_scan else 'false'
                    result['source_acquisition']['checks']['fast_occupied_box_scan_active'] = (
                        f'[ROG_MAP_OCCUPIED_BOX_SCAN] fast=true compare={compare_label} immutable=true' in stack)
                    result['source_acquisition']['checks']['box_scan_no_mismatch'] = (
                        '[ROG_MAP_OCCUPIED_BOX_SCAN_MISMATCH]' not in stack)
                    if args.compare_occupied_box_scan:
                        counters = re.findall(r'\[ROG_MAP_OCCUPIED_BOX_SCAN_COMPARE\] checks=(\d+) mismatches=(\d+)', stack)
                        result['source_acquisition']['checks']['box_scan_comparison_exercised'] = (
                            bool(counters) and max(int(c[0]) for c in counters) > 0
                            and all(int(c[1]) == 0 for c in counters))
                        result['box_scan_comparison_reports'] = counters
                if args.snapshot_line_query:
                    result['source_acquisition']['checks']['snapshot_line_query_active'] = (
                        '[ROG_MAP_SNAPSHOT_LINE_QUERY] enabled=true immutable=true active=true' in stack)
                if args.snapshot_neighbor_cache:
                    result['source_acquisition']['checks']['snapshot_neighbor_cache_active'] = (
                        '[ROG_MAP_SNAPSHOT_NEIGHBOR_CACHE] enabled=true immutable=true line_query=true active=true' in stack)
                if args.compose and mode != 'full':
                    stats = result['source_acquisition']['frontend_stats']
                    result['source_acquisition']['checks'].update({
                        'direct_output_enabled': stats.get('direct_output_enabled') is True,
                        'direct_output_exercised': stats.get('direct_output_events', 0) > 0,
                        'cloud_dds_zero': row.get('dds_cloud_payload_mib_s') == 0.,
                    })
                result['candidate'] = args.candidate
                result['cpu_profile'] = args.profile_cpu
                result['callback_trace'] = args.callback_trace
                result['cpu_comparison_instrumented'] = args.compare_occupied_box_scan or args.callback_trace
                result['compose'] = args.compose
                result['dds_cloud_payload_mib_s'] = row.get('dds_cloud_payload_mib_s')
                result['algorithm_cpu_scope'] = row.get('algorithm_cpu_scope')
                diagnostic.save(root / f'{mode}_summary.json', result)
                results.append(result)
                diagnostic.save(root / 'summary.json', dict(results=results,
                    comparison=comparison(results, args.mean_cpu_reduction_target_pct)))
                print('RESULT', json.dumps({k: result[k] for k in (
                    'mode', 'success', 'safety_collisions', 'mission_time_s',
                    'end_to_end_cpu_cores_mean', 'end_to_end_cpu_core_s')}), flush=True)
                if not all(result['source_acquisition']['checks'].values()):
                    raise RuntimeError('Source/recovery contract failure; stop for diagnosis')
        if event.sha(event.NORMAL) != event.NORMAL_SHA:
            raise RuntimeError('Frozen Normal data changed')
        comp = comparison(results, args.mean_cpu_reduction_target_pct)
        diagnostic.save(root / 'status.json', dict(pid=os.getpid(), state='COMPLETE',
            candidate=args.candidate, completed=len(results), comparison=comp))
        print('COMPARISON', json.dumps(comp), flush=True)
    except BaseException as error:
        diagnostic.save(root / 'status.json', dict(pid=os.getpid(), state='STOPPED_FOR_DIAGNOSIS',
            candidate=args.candidate, completed=len(results), error=repr(error)))
        raise
    finally:
        profiler.close()
        campaign.cleanup_active_process_groups()


if __name__ == '__main__':
    main()
