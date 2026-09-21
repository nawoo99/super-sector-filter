#!/usr/bin/env python3
"""G1–G4 + G5-R2 child adapter, preserving legacy flight/measurement gates.

The main function is an explicit isolated copy of adaptive_cpu40_seed1.main at
SHA256 954876f41d60d5ce76cb5b0742b6da826daca2a4e7f0b355e0b3878e1b77dac3.
Changes are limited to map admission, no-history duration-as-outcome admission,
binding this adapter's assets, and an additional independent geometry observer.
Helper behavior remains imported from that hash-pinned legacy implementation.
"""
import shutil
import tempfile

import gapfree_campaign_support as support
from gapfree_campaign_support import LEGACY_DIR, LEGACY_CHILD, MANIFEST, MAPS, PACKAGE, register_maps
import adaptive_cpu40_seed1 as legacy
from adaptive_cpu40_seed1 import *  # Existing tested helpers; legacy files remain unchanged.

MONITOR = PACKAGE / 'scripts/gapfree_native_loop_monitor.py'
MAP_MATCH_FIELDS = ('gapfree_manifest_sha256', 'gapfree_geometry', 'gapfree_adapter_baseline_sha256')


def small_pool_profile_reference_audit(plan, reference_plan, summaries):
    audit = legacy.small_pool_profile_reference_audit(plan, reference_plan, summaries)
    match = all(key in plan and key in reference_plan and plan[key] == reference_plan[key]
                for key in MAP_MATCH_FIELDS)
    audit['checks']['gapfree_frozen_map_match'] = match
    audit['acceptance_checks']['gapfree_frozen_map_match'] = match
    audit['valid'] = audit['valid'] and match
    return audit


def copy_supplemental_artifacts(root, map_name, run, mode, campaign):
    """Keep full odometry and the independent cylinder audit beside raw evidence."""
    stem = f'{map_name}_run{run}_{mode}.attempt1'
    dest = root / 'artifacts'
    dest.mkdir(parents=True, exist_ok=True)
    for suffix in ('cylinder_audit.json', 'odometry.csv'):
        origin = Path(campaign.TMPDIR) / f'{stem}.{suffix}'
        target = dest / origin.name
        if target.exists():
            raise RuntimeError('Supplemental evidence overwrite refused: ' + str(target))
        shutil.copy2(origin, target)
    result = json.loads((dest / f'{stem}.cylinder_audit.json').read_text())
    result['artifact_path'] = str(dest / f'{stem}.cylinder_audit.json')
    return result


def preserve_supplemental_artifacts(root, campaign):
    """Retain partial observer files even when no usable flight row returns."""
    dest = root / 'artifacts'
    dest.mkdir(parents=True, exist_ok=True)
    records = []
    for pattern in ('*.cylinder_audit.json', '*.odometry.csv'):
        for origin in sorted(Path(campaign.TMPDIR).glob(pattern)):
            target = dest / origin.name
            try:
                if target.exists():
                    if support.sha256(target) != support.sha256(origin):
                        raise RuntimeError('Existing supplemental evidence differs; overwrite refused')
                    state = 'ALREADY_PRESERVED'
                else:
                    shutil.copy2(origin, target)
                    state = 'COPIED'
                records.append(dict(source=str(origin), target=str(target), state=state))
            except Exception as error:
                # Never mask the original failure or delete the source evidence.
                records.append(dict(source=str(origin), target=str(target),
                                    state='PRESERVED_IN_SCRATCH', error=repr(error)))
    diagnostic.save(root / 'supplemental_preservation.json', dict(
        scratch_directory=campaign.TMPDIR, scratch_retained=True, files=records))


def main():
    map_admission = register_maps()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--run', type=int, required=True)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--map', choices=MAPS, default=MAPS[0])
    parser.add_argument('--mean-cpu-reduction-target-pct', type=float, default=40.,
                        help='Predeclared engineering threshold, not statistical significance (default40)')
    parser.add_argument('--modes', nargs='+', choices=('full', 'sector', 'adaptive'),
                        default=['full', 'adaptive'])
    parser.add_argument('--compose', action='store_true')
    parser.add_argument('--event-body-heading', action='store_true',
                        help='Opt-in event Adaptive body-forward center matching Fixed Sector')
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
    parser.add_argument('--async-certified-recovery', action='store_true',
                        help='Move certified-stop planning compute off the100Hz main callback; retain main safety finalization')
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
    parser.add_argument('--mission-time-as-metric', action='store_true',
                        help='Comparison-only admission: retain time checks as outcomes, not preflight gates')
    parser.add_argument('--sector-outcomes-as-metrics', action='store_true',
                        help='Fixed Sector completion/contact remain outcomes; require its source/resource/timing evidence')
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
    if args.guarded_demand_replan and not args.time_reference_folder and not args.mission_time_as_metric:
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
    campaign.LOOP_MON = str(MONITOR)
    campaign.TMPDIR = tempfile.mkdtemp(prefix='gapfree_n5_', dir='/tmp')
    os.environ['GAPFREE_BASE_MONITOR'] = str(LEGACY_DIR / 'native_loop_monitor.py')
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
    os.environ['SUPER_EVENT_BODY_ALIGNED_SECTOR'] = '1' if args.event_body_heading else '0'
    os.environ['SUPER_ASYNC_CERTIFIED_RECOVERY'] = '1' if args.async_certified_recovery else '0'
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
                  runtime / 'mission_planner/launch/benchmark_seedmap.launch.py',
                  Path('/root/super_ws/install/marsim_render/lib/libmarsim_render.so'),
                  Path('/root/super_ws/install/mission_planner/lib/libnative_sector_cpp_component.so'),
                  Path('/root/super_ws/install/mission_planner/lib/mission_planner/waypoint_mission'),
                  runtime / 'mission_planner/Apps/ros2_waypoint_mission.cpp',
                  runtime / 'mission_planner/Apps/native_sector_cpp.cpp',
                  runtime / 'mission_planner/include/mission_planner/sector_heading_policy.hpp',
                  Path('/root/super_ws/install/perfect_drone_sim/lib/perfect_drone_sim/perfect_drone_full_node'),
                  Path('/root/super_ws/install/rog_map/lib/librog_map.a'),
                  Path('/root/super_ws/install/super_planner/lib/libsuper.a'),
                  Path(recovery_audit.__file__).resolve(),
                  Path(stage_profile.__file__).resolve(),
                  Path(diagnostic.__file__).resolve(),
                  LEGACY_DIR / 'native_loop_monitor.py',
                  LEGACY_DIR / 'message_intervals.py',
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
    files.update({MANIFEST, LEGACY_CHILD, Path(support.__file__).resolve(), MONITOR})
    files.update(Path(path) for path in map_admission['assets_sha256'])
    hashes = {str(p): event.sha(p) for p in sorted(files)}
    frozen_policy = diagnostic.search.frozen_policy()
    diagnostic.RUN = args.run
    profiler = diagnostic.Profiler(root / 'telemetry.jsonl', map_name=args.map)
    effective_options = {
        mode: dict(diagnostic.search.OPTIONS,
                   optimizer_phase_memory_trace=not args.no_optimizer_phase_memory_trace,
                   sensor_acquisition=True,
                   sensor_planner_intra_process=args.compose,
                   observer_ready_before_mission=True,
                   adaptive_event_recovery=mode == 'adaptive') for mode in args.modes}
    plan = dict(
        gapfree_scratch_directory=campaign.TMPDIR,
        gapfree_manifest_sha256=map_admission['manifest_sha256'],
        gapfree_geometry=map_admission['maps'][args.map]['geometry'],
        gapfree_adapter_baseline_sha256=support.LEGACY_CHILD_SHA256,
        schema='adaptive-cpu40-seed1-exploratory-v1', candidate=args.candidate,
        map=args.map, run=args.run, modes=args.modes, profiles=profiles,
        backup=BACKUP, mean_cpu_reduction_target_pct=args.mean_cpu_reduction_target_pct,
        threshold_scope='Predeclared engineering objective; not statistical significance',
        cumulative_cpu_also_reported=True, max_mission_time_ratio=1.10,
        compose=args.compose, cpu_profile=args.profile_cpu, callback_trace=args.callback_trace,
        event_body_heading=args.event_body_heading,
        async_certified_recovery=args.async_certified_recovery,
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
        observer_ready_before_mission=True,
        observer_ready_definition=(
            'gapfree observer recorded its first valid odometry sample before '
            'waypoint_mission process creation'
        ),
        common_parameters_unchanged=f'{args.map}/loop24/v7,45deg-half-angle,0.4deg/10Hz sensor',
        frozen_normal_sha256=event.NORMAL_SHA, no_automatic_retry=True,
        exploratory_tuning=True, not_pooled_with_previous_results=True)
    profile_reference_audit = None
    plan['mission_time_as_metric'] = args.mission_time_as_metric
    plan['sector_outcomes_as_metrics'] = args.sector_outcomes_as_metrics
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
                solid_cylinder_audit = copy_supplemental_artifacts(root, args.map, args.run, mode, campaign)
                if not quality_valid(row):
                    raise RuntimeError('Invalid attempt retained; diagnose before retry')
                if profiler.error:
                    raise RuntimeError(profiler.error)
                if diagnostic.search.frozen_policy() != frozen_policy or any(
                        event.sha(p) != digest for p, digest in hashes.items()):
                    raise RuntimeError('Source/config/binary changed during candidate')
                result = diagnostic.summarize(profiler, row)
                result['solid_cylinder_audit'] = solid_cylinder_audit
                if references:
                    result['reference_comparison'] = reference_comparison(result, references[mode])
                result['source_acquisition'] = source.audit_source(root / 'artifacts', args.run, mode, args.map)
                result['source_acquisition']['checks']['solid_cylinder_observation_valid'] = (
                    solid_cylinder_audit.get('audit_valid') is True)
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
                result['event_body_heading'] = args.event_body_heading
                result['async_certified_recovery'] = args.async_certified_recovery
                if args.async_certified_recovery or '[ASYNC_CERTIFIED_RECOVERY]' in stack:
                    result['async_recovery_setting_audit'] = async_recovery_setting_audit(
                        stack, args.async_certified_recovery)
                    result['source_acquisition']['checks']['async_certified_recovery_setting'] = (
                        result['async_recovery_setting_audit']['valid'])
                if args.event_body_heading or '[SECTOR_HEADING_POLICY]' in stack:
                    result['heading_policy_audit'] = heading_policy_audit(stack, mode, args.event_body_heading)
                    result['source_acquisition']['checks']['heading_policy'] = result['heading_policy_audit']['valid']
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
                        goal_identity_admission_valid(result['goal_identity_audit'], mode,
                                                      args.sector_outcomes_as_metrics))
                    if mode == 'sector' and args.sector_outcomes_as_metrics:
                        result['source_acquisition']['checks']['goal_identity_consistency'] = (
                            result['goal_identity_audit']['identity_consistency_valid'])
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
        preserve_supplemental_artifacts(root, campaign)


if __name__ == '__main__':
    main()
