#!/usr/bin/env python3
"""One exploratory flight per selected mode/candidate; never discard outcomes.

The objective is >=40% reduction in experiment-cgroup mean used CPUs, with
contact-free completion and no artificial long-hold gain. Integrated CPU time
is reported separately. This is seed1 tuning, not confirmatory evidence.
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
from analyze_cylinder_only_stress_full_gate import quality_valid

BACKUP = 'results/adaptive_cpu40_backup_20260916_aloDDu/runtime_before.tar.gz'
FLIGHT_NAMES = {'fsm_node', 'perfect_drone_node', 'perfect_drone_full_node',
                'perfect_drone_frontend_node', 'perfect_drone_adaptive_node',
                'source_acquisition_test'}


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
    'snapshot_neighbor_cache', 'static_pc_poll_ms', 'side_executor_threads',
    'monitor_intervals', 'guarded_demand_replan', 'dedicated_static_pc_executor',
    'optimizer_phase_memory_trace', 'time_reference_folder',
    'max_same_mode_reference_time_ratio', 'max_mission_time_ratio',
    'logical_cpus', 'frozen_normal_sha256')


def small_pool_profile_reference_audit(plan, reference_plan, summaries):
    """Match a small-pool unprofiled pair to a passed profiled timing preflight.

    No CPU-reduction threshold is required of the preflight. Run identifiers,
    output/evidence paths and mode order may differ; runtime inputs may not.
    """
    modes = {'full', 'adaptive'}
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
        full_adaptive_pair=(len(plan.get('modes', [])) == 2 and
                            set(plan.get('modes', [])) == modes and
                            len(reference_plan.get('modes', [])) == 2 and
                            set(reference_plan.get('modes', [])) == modes),
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
            not row.get('cpu_comparison_instrumented', False))
        checks[mode + '_profile_timing'] = (
            timing.get('valid') is True and
            timing.get('callback_counts_instrumented') is True and
            all(timing_checks.get(k) is True for k in required_timing))
        checks[mode + '_reference_time'] = (
            row.get('reference_comparison', {}).get('mission_time_guardrail_pass') is True)
        checks[mode + '_demand_exercised'] = (
            not plan.get('guarded_demand_replan') or
            row.get('demand_replan_exercised') is True)
    ftime = summaries.get('full', {}).get('mission_time_s')
    atime = summaries.get('adaptive', {}).get('mission_time_s')
    checks['paired_mission_time'] = (
        all(isinstance(t, (int, float)) and math.isfinite(t) and t > 0
            for t in (ftime, atime)) and atime / ftime <= 1.10)
    return dict(valid=all(checks.values()), checks=checks,
                scope='Matched profiled finite-run timing preflight; not a real-time or safety guarantee')


def reference_comparison(result, reference):
    ratio = result['mission_time_s'] / reference['mission_time_s']
    return dict(mission_time_ratio=ratio, mission_time_guardrail_pass=ratio <= 1.10,
                mean_cpu_reduction_pct=100 * (1 - result['end_to_end_cpu_cores_mean'] /
                                               reference['end_to_end_cpu_cores_mean']),
                cumulative_cpu_reduction_pct=100 * (1 - result['end_to_end_cpu_core_s'] /
                                                     reference['end_to_end_cpu_core_s']),
                scope='Same-mode predeclared exploratory reference; not an isolated causal ablation')


def comparison(results):
    modes = {r['mode']: r for r in results}
    if not {'full', 'adaptive'} <= modes.keys():
        return dict(target_met=False, reason='Full/Adaptive pair incomplete')
    f, a = modes['full'], modes['adaptive']
    out = {}
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
    out['measured_threshold_pass'] = bool(safe and out['mission_time_guardrail_pass']
                                         and out['per_mode_reference_time_guardrail_pass']
                                         and out['common_demand_exercise_pass']
                                         and not out['cpu_comparison_instrumented']
                                         and reduction is not None and reduction >= 40.)
    out['target_met'] = (out['measured_threshold_pass']
                         and not out['requires_unprofiled_confirmation'])
    out['exploratory_n1_only'] = True
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--run', type=int, required=True)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--modes', nargs='+', choices=('full', 'sector', 'adaptive'),
                        default=['full', 'adaptive'])
    parser.add_argument('--compose', action='store_true')
    parser.add_argument('--profile-cpu', action='store_true')
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
    parser.add_argument('--side-executor-threads', type=int, choices=range(2, 17), default=10)
    parser.add_argument('--monitor-intervals', action='store_true',
                        help='Bounded received-message interval statistics on existing monitor subscriptions')
    parser.add_argument('--guarded-demand-replan', action='store_true')
    parser.add_argument('--dedicated-static-pc-executor', action='store_true')
    parser.add_argument('--no-optimizer-phase-memory-trace', action='store_true',
                        help='Disable per-solve diagnostic /proc reads and logs equally in both modes; retain external resource guards')
    parser.add_argument('--time-reference-folder', type=Path,
                        help='Predeclare same-mode <=1.10 mission-time guard and CPU reference')
    parser.add_argument('--small-pool-profile-reference', type=Path,
                        help='Passed matching Full/Adaptive profiled preflight required for unprofiled pools below4')
    parser.add_argument('--full-config', default=diagnostic.search.PROFILES['full'])
    parser.add_argument('--sector-config', default=diagnostic.search.PROFILES['sector'])
    parser.add_argument('--adaptive-config', default=event.PROFILE)
    args = parser.parse_args()
    if len(set(args.modes)) != len(args.modes):
        parser.error('Each mode may run only once per candidate')
    if args.compare_occupied_box_scan and not args.fast_occupied_box_scan:
        parser.error('--compare-occupied-box-scan requires --fast-occupied-box-scan')
    if args.snapshot_neighbor_cache and not args.snapshot_line_query:
        parser.error('--snapshot-neighbor-cache requires --snapshot-line-query')
    if args.guarded_demand_replan and not args.time_reference_folder:
        parser.error('--guarded-demand-replan requires --time-reference-folder')
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
            if reference.get('success') is not True or any(
                    not isinstance(reference.get(key), (int, float)) or
                    not math.isfinite(reference[key]) or reference[key] <= 0
                    for key in ('mission_time_s', 'end_to_end_cpu_cores_mean', 'end_to_end_cpu_core_s')):
                parser.error(f'Invalid successful reference: {path}')
            references[mode] = reference
            reference_files.append(path)
    profile_reference_plan = None
    profile_reference_summaries = {}
    if args.small_pool_profile_reference:
        for name in ('plan.json', 'full_summary.json', 'adaptive_summary.json'):
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
    os.environ['SUPER_SKIP_BACKUP_DIAGNOSTIC_REPLAY'] = (
        '1' if args.skip_backup_diagnostic_replay else '0')
    os.environ['SUPER_SKIP_UNOBSERVED_PATH_PUBLICATION'] = (
        '1' if args.skip_unobserved_path_publication else '0')
    os.environ['SUPER_FAST_OCCUPIED_BOX_SCAN'] = '1' if args.fast_occupied_box_scan else '0'
    os.environ['SUPER_COMPARE_OCCUPIED_BOX_SCAN'] = '1' if args.compare_occupied_box_scan else '0'
    os.environ['SUPER_SNAPSHOT_LINE_QUERY'] = '1' if args.snapshot_line_query else '0'
    os.environ['SUPER_SNAPSHOT_NEIGHBOR_CACHE'] = '1' if args.snapshot_neighbor_cache else '0'
    os.environ['SUPER_STATIC_PC_POLL_MS'] = str(args.static_pc_poll_ms)
    os.environ['SUPER_SIDE_EXECUTOR_THREADS'] = str(args.side_executor_threads)
    os.environ['SUPER_MONITOR_INTERVALS'] = '1' if args.monitor_intervals else '0'
    os.environ['SUPER_GUARDED_DEMAND_REPLAN'] = '1' if args.guarded_demand_replan else '0'
    os.environ['SUPER_STATIC_PC_DEDICATED_EXECUTOR'] = (
        '1' if args.dedicated_static_pc_executor else '0')
    os.environ['SUPER_OPTIMIZER_PHASE_MEMORY_TRACE'] = (
        '0' if args.no_optimizer_phase_memory_trace else '1')
    runtime = Path('/root/super_ws/src/SUPER')
    profiles = {'full': args.full_config, 'sector': args.sector_config,
                'adaptive': args.adaptive_config}
    files = {runtime / 'super_planner/config' / name for name in profiles.values()}
    files.update(reference_files)
    files.update({runtime / 'mars_uav_sim/perfect_drone_sim/config/seed1.yaml',
                  runtime / 'mars_uav_sim/perfect_drone_sim/pcd/seed_maps/seed1.pcd',
                  runtime / 'mission_planner/data/loop24.txt',
                  Path('/root/super_ws/install/marsim_render/lib/libmarsim_render.so'),
                  Path('/root/super_ws/install/mission_planner/lib/libnative_sector_cpp_component.so'),
                  Path('/root/super_ws/install/perfect_drone_sim/lib/perfect_drone_sim/perfect_drone_full_node'),
                  Path('/root/super_ws/install/rog_map/lib/librog_map.a'),
                  Path('/root/super_ws/install/super_planner/lib/libsuper.a'),
                  Path(recovery_audit.__file__).resolve(),
                  Path(stage_profile.__file__).resolve(),
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
    hashes = {str(p): event.sha(p) for p in sorted(files)}
    frozen_policy = diagnostic.search.frozen_policy()
    diagnostic.RUN = args.run
    profiler = diagnostic.Profiler(root / 'telemetry.jsonl')
    effective_options = {
        mode: dict(diagnostic.search.OPTIONS,
                   optimizer_phase_memory_trace=not args.no_optimizer_phase_memory_trace,
                   sensor_acquisition=True,
                   sensor_planner_intra_process=args.compose,
                   adaptive_event_recovery=mode == 'adaptive') for mode in args.modes}
    plan = dict(
        schema='adaptive-cpu40-seed1-exploratory-v1', candidate=args.candidate,
        map='seed1', run=args.run, modes=args.modes, profiles=profiles,
        backup=BACKUP, mean_cpu_reduction_target_pct=40,
        cumulative_cpu_also_reported=True, max_mission_time_ratio=1.10,
        compose=args.compose, cpu_profile=args.profile_cpu,
        skip_backup_diagnostic_replay=args.skip_backup_diagnostic_replay,
        skip_unobserved_path_publication=args.skip_unobserved_path_publication,
        fast_occupied_box_scan=args.fast_occupied_box_scan,
        compare_occupied_box_scan=args.compare_occupied_box_scan,
        snapshot_line_query=args.snapshot_line_query,
        snapshot_neighbor_cache=args.snapshot_neighbor_cache,
        static_pc_poll_ms=args.static_pc_poll_ms,
        side_executor_threads=args.side_executor_threads,
        monitor_intervals=args.monitor_intervals,
        guarded_demand_replan=args.guarded_demand_replan,
        dedicated_static_pc_executor=args.dedicated_static_pc_executor,
        optimizer_phase_memory_trace=not args.no_optimizer_phase_memory_trace,
        time_reference_folder=str(args.time_reference_folder) if args.time_reference_folder else None,
        max_same_mode_reference_time_ratio=1.10 if references else None,
        effective_run_options=effective_options,
        runtime_policy_note='Inherited base policy only; effective_run_options and profiles override it. Source acquisition follows native 10Hz cadence, not inherited filter-rate hint.',
        logical_cpus=os.cpu_count(), runtime_policy=frozen_policy,
        asset_sha256=hashes, baseline_seconds=12,
        common_parameters_unchanged='seed1/loop24/v7,45deg-half-angle,0.4deg/10Hz sensor',
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
                profiler.mode, profiler.phase = mode, 'baseline'
                diagnostic.save(root / 'status.json', dict(pid=os.getpid(), state='RUNNING',
                    candidate=args.candidate, mode=mode, phase='baseline'))
                time.sleep(12)
                options = effective_options[mode]
                profiler.phase = 'flight'
                diagnostic.save(root / 'status.json', dict(pid=os.getpid(), state='RUNNING',
                    candidate=args.candidate, mode=mode, phase='flight'))
                row = campaign.run_one('seed1', mode, args.run, **options,
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
                result['source_acquisition'] = source.audit_source(root / 'artifacts', args.run, mode)
                result['strict_recovery_audit'] = recovery_audit.audit_file(
                    root / 'artifacts' / f'seed1_run{args.run}_{mode}.attempt1.stack.log', mode)
                result['source_acquisition']['checks']['strict_source_recovery_audit'] = (
                    result['strict_recovery_audit']['valid'])
                stack = (root / 'artifacts' /
                    f'seed1_run{args.run}_{mode}.attempt1.stack.log').read_text(errors='replace')
                result['source_acquisition']['checks']['optimizer_phase_trace_setting'] = (
                    row.get('optimizer_phase_trace_enabled') is
                    (not args.no_optimizer_phase_memory_trace))
                result['source_acquisition']['checks']['static_pc_poll_setting'] = (
                    f'[STATIC_PC_POLL_SETTINGS] poll_ms={args.static_pc_poll_ms} '
                    f'bootstrap_once={int(args.static_pc_poll_ms == 100)}' in stack)
                if args.compose or mode == 'full':
                    result['source_acquisition']['checks']['side_executor_setting'] = (
                        f'[COMMON_EXECUTOR_SETTINGS] side_threads={args.side_executor_threads} ' in stack)
                    result['source_acquisition']['checks']['static_pc_executor_setting'] = (
                        '[STATIC_PC_EXECUTOR_SETTINGS] '
                        f'dedicated={int(args.dedicated_static_pc_executor)} ' in stack)
                if args.monitor_intervals:
                    monitor_result = json.loads((root / 'artifacts' /
                        f'seed1_run{args.run}_{mode}.json').read_text())
                    intervals = monitor_result.get('message_intervals', {})
                    result['message_intervals'] = intervals
                    result['source_acquisition']['checks']['message_interval_audit_present'] = (
                        set(intervals) == {'command', 'odometry'} and all(
                            x.get('messages', 0) > 1 and x.get('intervals_dropped', 1) == 0
                            and x.get('backward_receipts', 1) == 0
                            for x in intervals.values()))
                if args.guarded_demand_replan:
                    result['source_acquisition']['checks']['guarded_demand_replan_active'] = (
                        '[GUARDED_DEMAND_REPLAN] enabled=true max_dispatch_interval=0.25 ' in stack)
                    reports = re.findall(r'\[DEMAND_REPLAN\] checks=(\d+) skips=(\d+) renewals=(\d+)', stack)
                    result['demand_replan_reports'] = reports
                    result['demand_replan_exercised'] = bool(reports) and max(int(r[1]) for r in reports) > 0
                if args.side_executor_threads < 4:
                    result['small_pool_timing'] = small_pool_timing_audit(
                        result.get('message_intervals', {}), row.get('sensor_hz'),
                        stage_profile.summarize(root, mode, args.run) if args.profile_cpu else None)
                    result['source_acquisition']['checks']['small_pool_timing'] = result['small_pool_timing']['valid']
                    if not args.profile_cpu:
                        result['small_pool_profile_reference'] = profile_reference_audit
                        result['source_acquisition']['checks']['small_pool_profile_reference'] = (
                            profile_reference_audit is not None and profile_reference_audit['valid'])
                if args.skip_backup_diagnostic_replay or args.fast_occupied_box_scan or args.snapshot_line_query:
                    stack = (root / 'artifacts' /
                        f'seed1_run{args.run}_{mode}.attempt1.stack.log').read_text(errors='replace')
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
                result['cpu_comparison_instrumented'] = args.compare_occupied_box_scan
                result['compose'] = args.compose
                result['dds_cloud_payload_mib_s'] = row.get('dds_cloud_payload_mib_s')
                result['algorithm_cpu_scope'] = row.get('algorithm_cpu_scope')
                diagnostic.save(root / f'{mode}_summary.json', result)
                results.append(result)
                diagnostic.save(root / 'summary.json', dict(results=results, comparison=comparison(results)))
                print('RESULT', json.dumps({k: result[k] for k in (
                    'mode', 'success', 'safety_collisions', 'mission_time_s',
                    'end_to_end_cpu_cores_mean', 'end_to_end_cpu_core_s')}), flush=True)
                if not all(result['source_acquisition']['checks'].values()):
                    raise RuntimeError('Source/recovery contract failure; stop for diagnosis')
        if event.sha(event.NORMAL) != event.NORMAL_SHA:
            raise RuntimeError('Frozen Normal data changed')
        comp = comparison(results)
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
