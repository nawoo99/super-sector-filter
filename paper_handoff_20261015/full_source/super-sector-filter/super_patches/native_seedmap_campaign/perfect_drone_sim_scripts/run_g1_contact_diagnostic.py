#!/usr/bin/env python3
"""Exactly one selected-map Adaptive diagnostic flight; never primary evidence.

The failed run's options and environment are replayed unchanged. Only reviewed
logging hooks, a separate binary overlay, and external recording are admitted.
No baseline manifest is rewritten or claimed to certify the new binary.
"""
from __future__ import annotations

import argparse
import csv
import fcntl
import json
import math
import os
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import tempfile
import threading
import time

import psutil

import gapfree_campaign_support as support
import gapfree_cpu_compare as adapter
import adaptive_cpu40_seed1 as legacy

RUNTIME = Path('/root/super_ws/src/SUPER')
INSTALL = Path('/root/super_ws/install')
SCRIPTS = support.PACKAGE / 'scripts'
BASELINE = support.REPO / 'results/gapfree_n5_20260918_110107_690945/preflight/gapfree_d1_m01/r01_run30000'
DIAGNOSTIC_INSTALL = Path('/root/super_ws/g1_contact_diag_20260918/install')
MAP = 'gapfree_d1_m01'
MODE = 'adaptive'
TRACE_SOURCE_PATHS = tuple(RUNTIME / p for p in (
    'rog_map/include/rog_map/diagnostic_trace.hpp',
    'rog_map/src/rog_map/rog_map.cpp',
    'rog_map/src/rog_map/prob_map.cpp',
    'super_planner/src/super_core/super_planner.cpp',
    'super_planner/include/ros_interface/ros2/fsm_ros2.hpp',
    'super_planner/CMakeLists.txt',
    'mars_uav_sim/perfect_drone_sim/include/perfect_drone_sim/ros2_perfect_drone_model.hpp',
    'mars_uav_sim/perfect_drone_sim/CMakeLists.txt',
))
BOOL_ENV_FIELDS = {
    'SUPER_CPU_PROFILE': 'cpu_profile',
    'SUPER_CALLBACK_TRACE': 'callback_trace',
    'SUPER_EVENT_BODY_ALIGNED_SECTOR': 'event_body_heading',
    'SUPER_ASYNC_CERTIFIED_RECOVERY': 'async_certified_recovery',
    'SUPER_SKIP_BACKUP_DIAGNOSTIC_REPLAY': 'skip_backup_diagnostic_replay',
    'SUPER_SKIP_UNOBSERVED_PATH_PUBLICATION': 'skip_unobserved_path_publication',
    'SUPER_FAST_OCCUPIED_BOX_SCAN': 'fast_occupied_box_scan',
    'SUPER_COMPARE_OCCUPIED_BOX_SCAN': 'compare_occupied_box_scan',
    'SUPER_SNAPSHOT_LINE_QUERY': 'snapshot_line_query',
    'SUPER_SNAPSHOT_NEIGHBOR_CACHE': 'snapshot_neighbor_cache',
    'SUPER_STATIC_PC_TWO_PHASE': 'static_pc_two_phase',
    'SUPER_STATIC_PC_DURABLE': 'static_pc_durable',
    'SUPER_STATIC_PC_LATCHED_ONCE': 'static_pc_latched_once',
    'SUPER_MONITOR_INTERVALS': 'monitor_intervals',
    'SUPER_GUARDED_DEMAND_REPLAN': 'guarded_demand_replan',
    'SUPER_GUARDED_DEMAND_EXTENDED_LEASE': 'extended_demand_lease',
    'SUPER_GOAL_RETRANSMIT_IDENTITY': 'goal_retransmit_identity',
    'SUPER_HEADLESS_PARAMETER_SERVICES': 'headless_parameter_services',
    'SUPER_STATIC_PC_CACHED_EXECUTOR': 'static_pc_cached_executor',
    'SUPER_STATIC_PC_DEDICATED_EXECUTOR': 'dedicated_static_pc_executor',
    'SUPER_OPTIMIZER_PHASE_MEMORY_TRACE': 'optimizer_phase_memory_trace',
    'SUPER_OPT_CLEARANCE_GATE_FIRST': 'optimizer_clearance_gate_first',
}


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def replay_environment(plan, trace_directory, trace_center_x=-28.591183,
                       trace_center_y=-4.598807):
    if not math.isfinite(trace_center_x) or not math.isfinite(trace_center_y):
        raise ValueError('Trace center must be finite')
    environment = {}
    for key, field in BOOL_ENV_FIELDS.items():
        value = plan[field]
        if not isinstance(value, bool):
            raise ValueError(f'Expected original boolean {field}')
        environment[key] = str(int(value))
    environment.update({
        'SUPER_STATIC_PC_POLL_MS': str(plan['static_pc_poll_ms']),
        'SUPER_SIDE_EXECUTOR_THREADS': str(plan['side_executor_threads']),
        'SUPER_FRONTEND_DEDICATED_EXECUTOR': str(int(plan['effective_frontend_executor'][MODE])),
        'SUPER_G1_CONTACT_TRACE_DIR': str(Path(trace_directory).resolve()),
        'SUPER_CONTACT_TRACE_CENTER_X': format(trace_center_x, '.17g'),
        'SUPER_CONTACT_TRACE_CENTER_Y': format(trace_center_y, '.17g'),
        'GAPFREE_BASE_MONITOR': str(support.LEGACY_DIR / 'native_loop_monitor.py'),
    })
    return environment


def replay_options(plan, map_name=MAP):
    if plan['map'] != map_name or MODE not in plan['modes']:
        raise ValueError('The baseline must describe the selected map and Adaptive mode')
    options = dict(plan['effective_run_options'][MODE])
    required = dict(attempt_max=1, loop_timeout_override=180,
                    sensor_acquisition=True, sensor_planner_intra_process=True,
                    adaptive_event_recovery=True, cgroup_cpu_accounting=True,
                    seedmap_static_pcd=True, filter_half_angle_deg=45)
    if any(options.get(k) != v for k, v in required.items()):
        raise ValueError('Baseline no longer describes the authorized one-flight setup')
    if options.get('resource_guard_enabled', True) is not True:
        raise ValueError('Resource guards must remain enabled')
    return options


def baseline_hashes(plan):
    result = dict(plan['runtime_policy']['sha256'])
    for path, digest in plan['asset_sha256'].items():
        if path in result and result[path] != digest:
            raise ValueError('Conflicting historical hashes: ' + path)
        result[path] = digest
    return result


def verify_baseline(plan):
    """Only listed logging-hook sources may differ; normal binaries cannot."""
    historical = baseline_hashes(plan)
    source_deltas = []
    current = {}
    for name, before in historical.items():
        path = Path(name)
        if not path.is_file():
            raise RuntimeError('Missing baseline asset: ' + name)
        after = support.sha256(path)
        if before != after:
            if path not in TRACE_SOURCE_PATHS:
                raise RuntimeError('Unexpected baseline change: ' + name)
            source_deltas.append(dict(path=name, baseline_sha256=before,
                                      diagnostic_sha256=after,
                                      admission='Explicit logging-hook source allowlist; not an algorithm-equivalence proof'))
        current[name] = after
    for path in TRACE_SOURCE_PATHS:
        if path.exists():
            current[str(path)] = support.sha256(path)
            if str(path) not in historical:
                source_deltas.append(dict(path=str(path), baseline_sha256=None,
                                          diagnostic_sha256=current[str(path)],
                                          admission='New diagnostic-only header'))
    return current, source_deltas


def ros_environment(prefix):
    prefix = Path(prefix).resolve()
    if prefix == INSTALL or INSTALL in prefix.parents:
        raise ValueError('Diagnostic install must be separate from the original install')
    setup = prefix / 'local_setup.bash'
    binary = prefix / 'perfect_drone_sim/lib/perfect_drone_sim/perfect_drone_adaptive_node'
    if not setup.is_file() or not binary.is_file():
        raise RuntimeError('Diagnostic overlay is not built: ' + str(prefix))
    command = ('source /opt/ros/humble/setup.bash && '
               'source /root/super_ws/install/setup.bash && source ' + shlex.quote(str(setup)))
    return command, binary


def verify_package_prefix(ros_env, prefix):
    result = subprocess.run(['bash', '-c', ros_env + ' && ros2 pkg prefix perfect_drone_sim'],
                            text=True, capture_output=True, timeout=30, check=True)
    found = Path(result.stdout.strip()).resolve()
    expected = (Path(prefix) / 'perfect_drone_sim').resolve()
    if found != expected:
        raise RuntimeError(f'Wrong ROS package overlay: {found}, expected {expected}')
    return str(found)


def ensure_no_flights():
    names = set(legacy.FLIGHT_NAMES) | {'waypoint_mission', 'native_sector_cpp'}
    for process in psutil.process_iter(['pid', 'cmdline']):
        command = process.info['cmdline'] or []
        if command and (Path(command[0]).name in names or
                        any(Path(arg).name in {'native_loop_monitor.py', 'gapfree_native_loop_monitor.py'}
                            for arg in command[1:])):
            raise RuntimeError('Existing flight/monitor: ' + str(process.info['pid']))


def unchanged(hashes):
    return [p for p, expected in hashes.items()
            if not Path(p).is_file() or support.sha256(p) != expected]


def terminate_observer(process):
    if process is None or process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGINT)
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5)
    except ProcessLookupError:
        pass


class OwnedRssGuard:
    """The original controller's 4608 MiB owned-tree cap, outside flight logic."""
    def __init__(self, campaign):
        self.campaign = campaign
        self.stop = threading.Event()
        self.error = None
        self.maximum_mib = 0.
        self.thread = threading.Thread(target=self.loop, daemon=True, name='diagnostic_owned_rss_guard')

    def loop(self):
        while not self.stop.wait(.5):
            try:
                pids = set()
                for pid in list(self.campaign._ACTIVE_PROCESS_GROUPS):
                    try:
                        process = psutil.Process(pid)
                        pids.add(pid)
                        pids.update(child.pid for child in process.children(recursive=True))
                    except psutil.NoSuchProcess:
                        pass
                rss = 0
                for pid in pids:
                    try:
                        rss += psutil.Process(pid).memory_info().rss
                    except psutil.NoSuchProcess:
                        pass
                self.maximum_mib = max(self.maximum_mib, rss / 2**20)
                if rss > 4608 * 2**20:
                    self.error = f'Owned experiment RSS exceeded 4608 MiB: {rss / 2**20:.1f}'
                    self.campaign.cleanup_active_process_groups()
                    return
            except Exception as error:
                self.error = 'Owned RSS guard failed: ' + repr(error)
                self.campaign.cleanup_active_process_groups()
                return

    def close(self):
        self.stop.set()
        if self.thread.is_alive():
            self.thread.join(timeout=2)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, default=BASELINE)
    parser.add_argument('--diagnostic-install', type=Path, default=DIAGNOSTIC_INSTALL)
    parser.add_argument('--run-id', type=int, default=31000)
    parser.add_argument('--trace-center-x', type=float, default=-28.591183)
    parser.add_argument('--trace-center-y', type=float, default=-4.598807)
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument('--prepare-only', action='store_true')
    operation.add_argument('--run', action='store_true')
    args = parser.parse_args(argv)
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    baseline_file = args.baseline / 'plan.json'
    plan = json.loads(baseline_file.read_text())
    map_name = plan['map']
    admission = support.register_maps()
    if map_name not in admission['maps']:
        raise RuntimeError('Selected baseline map is not registered: ' + map_name)
    options = replay_options(plan, map_name)
    hashes, deltas = verify_baseline(plan)
    ros_env, binary = ros_environment(args.diagnostic_install)
    prefix = verify_package_prefix(ros_env, args.diagnostic_install)
    recorder_script = SCRIPTS / 'g1_contact_topic_recorder.py'
    if not recorder_script.is_file():
        raise RuntimeError('Missing diagnostic topic recorder')
    for path in (baseline_file, Path(__file__), recorder_script, binary,
                 args.diagnostic_install / 'local_setup.bash'):
        hashes[str(path.resolve())] = support.sha256(path)
    trace = root / 'cpp_trace'
    trace.mkdir()
    environment = replay_environment(plan, trace, args.trace_center_x,
                                     args.trace_center_y)
    foreign = {key: value for key, value in os.environ.items()
               if key.startswith('SUPER_') and key not in environment}
    if foreign:
        raise RuntimeError('Unbound inherited SUPER_* settings: ' + ', '.join(foreign))
    campaign = legacy.diagnostic.search.campaign
    scratch = tempfile.mkdtemp(prefix='gapfree_contact_diagnostic_', dir='/tmp')
    record = dict(schema='g1-contact-diagnostic-v1', baseline_folder=str(args.baseline),
                  map=map_name, mode=MODE, run=args.run_id, planned_flights=1,
                  trace_center_x=args.trace_center_x,
                  trace_center_y=args.trace_center_y,
                  diagnostic_only=True, primary_comparison_eligible=False,
                  CPU_comparison_eligible=False, no_automatic_retry=True,
                  copied_effective_options=options, environment=environment,
                  baseline_seconds=plan['baseline_seconds'],
                  original_baseline_sha256=support.sha256(baseline_file),
                  historical_static_preflight_sha256=plan['static_latched_preflight_sha256'],
                  static_preflight_scope='Historical evidence only; does not certify diagnostic overlay',
                  expected_geometry=admission['maps'][map_name]['geometry'],
                  diagnostic_install=str(args.diagnostic_install.resolve()),
                  resolved_perfect_drone_prefix=prefix, overlay_binary=str(binary),
                  overlay_binary_sha256=support.sha256(binary), source_deltas=deltas,
                  current_sha256=hashes, scratch_directory=scratch,
                  observer_scope='External process, outside experiment cgroup; logging overhead changes timing',
                  owned_rss_limit_mib=4608,
                  source_equivalence_scope='Logging-only change must be reviewed; hash allowlist is not semantic proof')
    save(root / 'plan.json', record)
    if args.prepare_only:
        save(root / 'status.json', dict(state='PREPARED_ONLY', actual_flights=0, diagnostic_only=True))
        print(json.dumps(dict(state='PREPARED_ONLY', output=str(root), actual_flights=0)), flush=True)
        return 0

    profiler = observer = observer_log = guard = None
    prior_environment = dict(os.environ)
    old_globals = {name: getattr(campaign, name) for name in ('ROS_ENV', 'TMPDIR', 'LOOP_MON', 'kill_all')}
    old_handlers = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)}
    lock = open(campaign.LOCK_PATH, 'a')
    flight_calls = 0
    campaign_configured = False
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        ensure_no_flights()
        campaign.ROS_ENV = ros_env
        campaign.TMPDIR = scratch
        campaign.LOOP_MON = str(adapter.MONITOR)
        campaign_configured = True

        def owned_cleanup(settle_s=1.5):
            campaign.cleanup_active_process_groups()
            if settle_s > 0:
                time.sleep(settle_s)
            campaign.clean_fastdds_zombies()

        campaign.kill_all = owned_cleanup
        os.environ.update(environment)
        campaign.install_campaign_signal_handlers()
        artifacts = root / 'artifacts'
        artifacts.mkdir()
        perf = Path(campaign.PERF_LOG)
        if perf.exists():
            shutil.copy2(perf, artifacts / 'preexisting_rm_performance_log.csv')
        legacy.diagnostic.RUN = args.run_id
        profiler = legacy.diagnostic.Profiler(root / 'telemetry.jsonl', map_name=map_name)
        profiler.mode, profiler.phase = MODE, 'baseline'
        profiler.thread.start()
        save(root / 'status.json', dict(state='RUNNING', phase='baseline', actual_flights=0))
        time.sleep(plan['baseline_seconds'])
        observer_log = (root / 'topic_recorder.log').open('x')
        observer_cmd = (ros_env + ' && exec python3 ' + shlex.quote(str(recorder_script)) +
                        ' --output ' + shlex.quote(str(root / 'topic_recording')) + ' --duration-s 240')
        observer = subprocess.Popen(['bash', '-c', observer_cmd], start_new_session=True,
                                    stdout=observer_log, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 15
        while not (root / 'topic_recording/ready.json').exists():
            if observer.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError('Topic recorder did not become READY; no flight launched')
            time.sleep(.1)
        if profiler.error:
            raise RuntimeError(profiler.error)
        if unchanged(hashes):
            raise RuntimeError('Inputs changed before diagnostic flight')
        guard = OwnedRssGuard(campaign)
        guard.thread.start()
        profiler.phase = 'flight'
        save(root / 'status.json', dict(state='RUNNING', phase='flight', actual_flights=1))
        flight_calls = 1
        row = campaign.run_one(map_name, MODE, args.run_id, **options,
                               artifacts_dir=str(artifacts),
                               seedmap_super_config_override=plan['profiles'][MODE])
        with (root / 'raw.csv').open('x', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=campaign.FIELDS, extrasaction='ignore')
            writer.writeheader()
            writer.writerow(row)
        observer_alive_until_flight_end = observer.poll() is None
        terminate_observer(observer)
        observer = None
        solid = adapter.copy_supplemental_artifacts(
                root, map_name, args.run_id, MODE, campaign)
        stem = f'{map_name}_run{args.run_id}_{MODE}.attempt1'
        stack = (artifacts / (stem + '.stack.log')).read_text(errors='replace')
        static_audit = legacy.static_latched_audit(stack, geometry=record['expected_geometry'])
        source = legacy.source.audit_source(artifacts, args.run_id, MODE, map_name)
        recovery = legacy.recovery_audit.audit_file(artifacts / (stem + '.stack.log'), MODE)
        changed = unchanged(hashes)
        trace_files = [dict(path=str(p.relative_to(root)), bytes=p.stat().st_size,
                            sha256=support.sha256(p)) for p in trace.rglob('*') if p.is_file()]
        checks = dict(original_assets_and_overlay_unchanged=not changed,
                      one_attempt=row.get('attempt_count') == 1 and row.get('retry_count') == 0,
                      resource_and_measurement_valid=legacy.quality_valid(row),
                      solid_cylinder_observation_valid=solid.get('audit_valid') is True,
                      static_latched_runtime=static_audit['valid'],
                      source_contract=all(source['checks'].values()),
                      recovery_contract=recovery['valid'],
                      telemetry_valid=not profiler.error,
                      external_recorder_alive_until_flight_end=observer_alive_until_flight_end,
                      nonempty_cpp_trace=any(item['bytes'] > 0 for item in trace_files),
                      owned_rss_guard=guard.error is None)
        result = dict(diagnostic_only=True, primary_comparison_eligible=False,
                      CPU_comparison_eligible=False, row=row, checks=checks,
                      changed_inputs=changed, solid_cylinder_audit=solid,
                      static_latched_runtime=static_audit, source_acquisition=source,
                      strict_recovery_audit=recovery, owned_rss_max_mib=guard.maximum_mib,
                      owned_rss_error=guard.error, profiler_error=profiler.error,
                      trace_files=trace_files)
        if legacy.quality_valid(row):
            result['diagnostic_telemetry_summary'] = legacy.diagnostic.summarize(profiler, row)
        save(root / 'diagnostic_summary.json', result)
        state = ('DIAGNOSTIC_CONTACT' if solid.get('contact_episodes', 0) > 0
                 else 'DIAGNOSTIC_NO_CONTACT') if all(checks.values()) else 'DIAGNOSTIC_INVALID'
        save(root / 'status.json', dict(state=state, actual_flights=flight_calls,
                                      diagnostic_only=True, checks=checks,
                                      contact_episodes=solid.get('contact_episodes'),
                                      completion=solid.get('completion'),
                                      no_automatic_retry=True))
        print(json.dumps(dict(state=state, contact_episodes=solid.get('contact_episodes'),
                              completion=solid.get('completion'), output=str(root))), flush=True)
        return 0 if all(checks.values()) else 2
    except BaseException as error:
        save(root / 'status.json', dict(state='DIAGNOSTIC_STOPPED', actual_flights=flight_calls,
                                      diagnostic_only=True, error=repr(error), no_automatic_retry=True))
        raise
    finally:
        terminate_observer(observer)
        if observer_log is not None:
            observer_log.close()
        if guard is not None:
            guard.close()
        if profiler is not None:
            profiler.close()
        if campaign_configured:
            campaign.cleanup_active_process_groups()
            adapter.preserve_supplemental_artifacts(root, campaign)
        for name, value in old_globals.items():
            setattr(campaign, name, value)
        for sig, handler in old_handlers.items():
            signal.signal(sig, handler)
        os.environ.clear()
        os.environ.update(prior_environment)
        lock.close()


if __name__ == '__main__':
    raise SystemExit(main())
