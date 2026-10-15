#!/usr/bin/env python3
"""Fresh, fail-closed C24 Normal campaign: 15 ON preflights then 75 OFF runs.

Five maps x three modes x five independent OFF repetitions. All attempts remain;
no automatic retry, failure replacement, old preflight reuse, or n20 expansion.
The existing child runs three modes per invocation, preserving its common
evidence inventory and exact mode-set profile matching. A Full/Adaptive outcome
failure stops this controller AFTER that triplet (at most two further simulated
flights); the child stops measurement/source failures immediately.

Fresh static DDS/RViz verification, actual timing, source/recovery, speed and
resource gates are never relaxed. Mission duration is reported, not the former
paired +10% time gate. Optional explicit runner flags/environment are frozen;
this controller defines no new runtime policy or runtime flag itself.
"""
import argparse
from collections import Counter
import csv
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time
import psutil

from run_c22_normal_campaign import (
    ROOT, MAPS, MODES, ORDERS, PROBE, TESTS, common_args, save, read, sha,
    frozen_policy, make_references, static_commands, static, stages, reports, event,
)


PHASES = ("preflight", "validation5")
COUNTS = {"preflight": 1, "validation5": 5}
MEMORY_RUNAWAY_MIB = 4608
MEMORY_POLL_S = 1.0
GDB_TIMEOUT_S = 20
COMPOSED_NAMES = {'perfect_drone_full_node', 'perfect_drone_adaptive_node'}
TIMING_CHECKS = (
    "sensor_cadence", "odometry_cadence", "odometry_header_p99", "odometry_header_max",
    "odometry_receipt_p99", "odometry_receipt_max", "odometry_order",
)
PROFILE_TIMING_CHECKS = ("fsm_main_callback", "fsm_command_callback", "profile_callback_coverage")
SOURCE_CHECKS = (
    "telemetry_map_scope", "strict_source_recovery_audit", "heading_policy",
    "optimizer_phase_trace_setting", "optimizer_clearance_gate_first", "static_pc_poll_setting",
    "static_pc_durable_setting", "side_executor_setting", "static_pc_executor_setting",
    "static_latched_runtime", "static_latched_delivery", "message_interval_audit_present",
    "guarded_demand_replan_active", "goal_identity_audit", "headless_parameter_settings",
    "small_pool_timing", "backup_replay_skip_active", "fast_occupied_box_scan_active",
    "box_scan_no_mismatch", "snapshot_line_query_active", "snapshot_neighbor_cache_active",
)


def explicit_true_checks(value, required=()):
    return (isinstance(value, dict) and bool(value)
            and all(item is True for item in value.values())
            and all(value.get(key) is True for key in required))


def number(value):
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def boolean(value):
    return True if value is True or value == "True" else False if value is False or value == "False" else None


def load_document(path):
    try:
        value = read(path)
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def extension_options(runner_flags=(), runtime_env=()):
    protected = {part for part in common_args(Path('/unused')) if part.startswith('--')}
    protected.update(('--output', '--map', '--run', '--modes', '--profile-cpu', '--callback-trace',
                      '--small-pool-profile-reference', '--event-body-heading', '--mission-time-as-metric',
                      '--async-certified-recovery', '--sector-outcomes-as-metrics'))
    flags, values = [], {}
    for flag in runner_flags:
        if not re.fullmatch(r'--[a-z][a-z0-9-]*', flag) or flag in protected or flag in flags:
            raise ValueError('Extra runner flag must be a unique, non-controller boolean option: ' + repr(flag))
        flags.append(flag)
    for item in runtime_env:
        key, separator, value = item.partition('=')
        if (not separator or not re.fullmatch(r'SUPER_[A-Z][A-Z0-9_]*', key)
                or key in ('SUPER_CPU_PROFILE', 'SUPER_CALLBACK_TRACE') or key in values
                or not value or any(c in value for c in '\n\r\0')):
            raise ValueError('Expected a unique explicit SUPER_NAME=value, excluding profiling controls: ' + repr(item))
        values[key] = value
    return flags, values


def build_plan(root, base_run=18000, candidate=None, runner_flags=(), async_certified_recovery=False):
    if type(base_run) is not int or base_run < 1:
        raise ValueError('Positive integer base-run required')
    candidate = candidate or 'c24_' + root.name
    flags, _ = extension_options(runner_flags)
    commands = []
    for map_name in MAPS:
        for item in static_commands(root, map_name):
            commands.append(dict(item, map=map_name))
    for phase in PHASES:
        for repeat in range(COUNTS[phase]):
            for map_name in MAPS[repeat:] + MAPS[:repeat]:
                index = MAPS.index(map_name)
                run = base_run + (0 if phase == 'preflight' else 100) + repeat * 10 + index
                folder = root / phase / map_name / f'r{repeat+1:02d}_run{run}'
                reference = root / 'preflight' / map_name / f'r01_run{base_run+index}'
                command = common_args(root)
                command.remove('--extended-demand-lease')
                for flag, value in {
                    '--candidate': candidate,
                    '--side-executor-threads': '3',
                    '--static-latched-preflight': str(root / 'static_preflight' / map_name / 'acceptance.json'),
                    '--time-reference-folder': str(root / 'references' / map_name),
                }.items():
                    command[command.index(flag)+1] = value
                order = ORDERS[(repeat + index) % len(ORDERS)]
                command += ['--event-body-heading', '--mission-time-as-metric', '--sector-outcomes-as-metrics', *flags,
                            '--map', map_name, '--run', str(run), '--output', str(folder)]
                if async_certified_recovery:
                    command.append('--async-certified-recovery')
                command += ['--profile-cpu'] if phase == 'preflight' else [
                    '--small-pool-profile-reference', str(reference)]
                command += ['--modes', *order]
                commands.append(dict(name=f'{phase}_{map_name}_r{repeat+1:02d}', phase=phase,
                    map=map_name, run=run, repeat=repeat+1, modes=list(order), path=str(folder),
                    candidate=candidate, async_certified_recovery=async_certified_recovery, command=command))
    return commands


def flight_checks(row, mode, profile, sector_outcomes_as_metrics=False):
    source = row.get('source_acquisition', {}).get('checks', {})
    specific = ('full_source_always_360', 'full_readback_size', 'full_ray_count') if mode == 'full' else (
        'source_mode_enabled', 'quarter_width_before_cloud', 'actual_depth_readback_narrowed',
        'only_acquired_rays_converted', 'source_cloud_byte_counts', 'fixed_sector_never_full')
    required = SOURCE_CHECKS + specific + (() if profile else ('small_pool_profile_reference',))
    if mode == 'adaptive':
        required += ('event_mode_enabled', 'raw_risk_worker_disabled')
    if mode == 'sector' and sector_outcomes_as_metrics is True:
        required += ('goal_identity_consistency',)
    timing = row.get('small_pool_timing', {})
    timing_required = TIMING_CHECKS + (PROFILE_TIMING_CHECKS if profile else ())
    collision = number(row.get('safety_collisions'))
    checks = dict(
        run_valid=row.get('run_valid') is True,
        resource=row.get('resource_valid') is True,
        speed=row.get('speed_limit_valid') is True,
        source=explicit_true_checks(source, required),
        recovery=row.get('strict_recovery_audit', {}).get('valid') is True
                 and row.get('strict_recovery_audit', {}).get('mode') == mode,
        timing=timing.get('valid') is True and explicit_true_checks(timing.get('checks'), timing_required),
        timing_instrumentation=timing.get('callback_counts_instrumented') is profile,
        cpu_profile=row.get('cpu_profile') is profile,
        trace_off=row.get('callback_trace') is False and row.get('cpu_comparison_instrumented') is False,
        demand_exercised=row.get('demand_replan_exercised') is True,
        goal_identity=row.get('goal_retransmit_exercised') is True
                      and row.get('goal_identity_audit', {}).get('valid') is True,
        static_delivery=row.get('static_pc_delivery_validated') is True
                        and row.get('static_latched_audit', {}).get('valid') is True,
        known_outcome=type(row.get('success')) is bool and collision is not None
                      and collision >= 0 and collision.is_integer(),
        cpu_measured=all(number(row.get(key)) is not None and number(row.get(key)) > 0
                         for key in ('end_to_end_cpu_cores_mean', 'end_to_end_cpu_core_s')),
    )
    # Sector safety/completion remain observations in ON and OFF; accepting only
    # a clean Sector preflight would select evidence by comparison outcome.
    if mode in ('full', 'adaptive'):
        checks.update(completed=row.get('success') is True, zero_contact=collision == 0)
    if mode == 'sector' and sector_outcomes_as_metrics is True:
        checks['identity_consistency'] = (
            row.get('goal_identity_audit', {}).get('identity_consistency_valid') is True)
    return checks


def triplet_audit(folder, map_name, run, profile, candidate=None, expected_order=None,
                  async_certified_recovery=False):
    checks, rows, errors = {}, [], []
    plan, status = load_document(folder/'plan.json'), load_document(folder/'status.json')
    checks['plan_identity'] = (plan.get('map') == map_name and type(plan.get('run')) is int
        and plan.get('run') == run and plan.get('cpu_profile') is profile
        and isinstance(plan.get('modes'), list) and len(plan['modes']) == 3
        and set(plan['modes']) == set(MODES) and (candidate is None or plan.get('candidate') == candidate))
    checks['declared_common_policy'] = (plan.get('side_executor_threads') == 3
        and plan.get('extended_demand_lease') is False and plan.get('guarded_demand_replan') is True
        and plan.get('event_body_heading') is True and plan.get('mission_time_as_metric') is True
        and plan.get('sector_outcomes_as_metrics') is True)
    checks['async_policy_identity'] = plan.get('async_certified_recovery') is async_certified_recovery
    marker_path = folder/'diagnostic_contamination.json'
    checks['not_diagnostic_contaminated'] = not marker_path.exists()
    checks['runner_complete'] = (status.get('state') == 'COMPLETE' and status.get('completed') == 3
        and (candidate is None or status.get('candidate') == candidate))
    try:
        with (folder/'raw.csv').open(newline='') as stream:
            raw = list(csv.DictReader(stream))
    except (OSError, ValueError, csv.Error) as exc:
        raw = []
        errors.append(repr(exc))
    expected = {(map_name, str(run), mode) for mode in MODES}
    actual = [(r.get('map'), r.get('run'), r.get('mode')) for r in raw]
    checks['raw_exact_identity_coverage'] = len(actual) == 3 and set(actual) == expected
    checks['mode_order'] = (expected_order is None or
        (plan.get('modes') == list(expected_order) and [r.get('mode') for r in raw] == list(expected_order)))
    for mode in MODES:
        row = load_document(folder/f'{mode}_summary.json')
        rows.append(row)
        checks[mode+':identity'] = (row.get('map') == map_name and type(row.get('run')) is int
            and row.get('run') == run and row.get('mode') == mode
            and (candidate is None or row.get('candidate') == candidate))
        checks.update({mode+':'+key: value for key, value in flight_checks(
            row, mode, profile, plan.get('sector_outcomes_as_metrics') is True).items()})
        checks[mode+':async_policy_identity'] = row.get('async_certified_recovery') is async_certified_recovery
        if async_certified_recovery:
            checks[mode+':async_setting_audit'] = (row.get('async_recovery_setting_audit', {}).get('valid') is True
                and row.get('source_acquisition', {}).get('checks', {}).get('async_certified_recovery_setting') is True)
        records = [r for r in raw if r.get('mode') == mode]
        r = records[0] if len(records) == 1 else {}
        checks[mode+':raw_quality_no_retry'] = (
            all(boolean(r.get(key)) is True for key in ('run_valid','resource_valid','speed_limit_valid'))
            and boolean(r.get('infrastructure_failure')) is False
            and number(r.get('attempt_count')) == 1 and number(r.get('retry_count')) == 0
            and number(r.get('cgroup_cpu_duration_s')) is not None and number(r.get('cgroup_cpu_duration_s')) > 0)
        contacts = number(r.get('safety_collisions'))
        checks[mode+':raw_summary_outcome_match'] = (
            boolean(r.get('success')) is not None and boolean(r.get('success')) is row.get('success')
            and contacts is not None and contacts == number(row.get('safety_collisions')))
        checks[mode+':raw_summary_cpu_match'] = all(
            number(r.get(key)) is not None and number(r.get(key)) == number(row.get(key))
            for key in ('end_to_end_cpu_cores_mean', 'end_to_end_cpu_core_s'))
        checks[mode+':static_contact_evidence'] = (
            boolean(r.get('static_pcd_enabled')) is True and r.get('safety_contact_source') == 'static_pcd'
            and contacts is not None and contacts == number(r.get('static_pcd_collisions')))
    outcomes = {mode: dict(success=row.get('success'), safety_collisions=row.get('safety_collisions'))
                for mode, row in zip(MODES, rows)}
    # Preserve strict exercise observations in checks and in original summary
    # fields. A genuinely blocked Sector need not have an optimization chance;
    # its explicit identity-consistency and all measurement gates still apply.
    acceptance_checks = {key: value for key, value in checks.items()
                         if not (plan.get('sector_outcomes_as_metrics') is True and key in (
                             'sector:demand_exercised', 'sector:goal_identity'))}
    return dict(schema='c24-triplet-audit-v1', valid=explicit_true_checks(acceptance_checks), checks=checks,
        acceptance_checks=acceptance_checks,
        map=map_name, run=run, profiled=profile, candidate=candidate, outcomes=outcomes, errors=errors,
        mission_time_as_metric=True, cpu_reduction_is_descriptive_not_gate=True,
        sector_outcome_required_safe=False,
        outcome_failures={mode: data for mode, data in outcomes.items()
                          if data['success'] is not True or data['safety_collisions'] != 0})


def phase_gate(commands, phase):
    planned = [c for c in commands if c['phase'] == phase]
    expected = {(m, repeat, mode) for m in MAPS for repeat in range(1, COUNTS[phase]+1) for mode in MODES}
    actual = [(c.get('map'), c.get('repeat'), mode) for c in planned for mode in c.get('modes', [])]
    identities = [(c.get('map'), c.get('run'), mode) for c in planned for mode in c.get('modes', [])]
    records = []
    for item in planned:
        folder = Path(item['path'])
        fresh = triplet_audit(folder, item['map'], item['run'], phase == 'preflight',
                              item.get('candidate'), item['modes'], item.get('async_certified_recovery', False))
        stored = load_document(folder/'triplet_verification.json')
        stored_valid = (stored.get('schema') == 'c24-triplet-audit-v1' and stored.get('valid') is True
            and stored.get('map') == item['map'] and stored.get('run') == item['run']
            and stored.get('profiled') is (phase == 'preflight')
            and stored.get('checks') == fresh['checks']
            and stored.get('acceptance_checks') == fresh['acceptance_checks'])
        records.append(dict(name=item['name'], valid=fresh['valid'] and stored_valid,
                            audit_present=(folder/'triplet_verification.json').is_file()))
    checks = dict(exact_planned_coverage=len(actual) == len(expected) and set(actual) == expected,
                  unique_identities=len(identities) == len(set(identities)),
                  all_evidence_present=bool(records) and all(r['audit_present'] for r in records),
                  all_fresh_audits_pass=bool(records) and all(r['valid'] for r in records))
    return dict(valid=explicit_true_checks(checks), phase=phase, checks=checks,
                planned_triplets=len(planned), expected_flights=len(expected), records=records)


def changed_inputs(frozen):
    changed = []
    for path, digest in frozen.items():
        try:
            if sha(path) != digest:
                changed.append(path)
        except OSError:
            changed.append(path)
    return changed


def freeze_files(frozen, paths):
    for path in paths:
        key, digest = str(Path(path).resolve()), sha(path)
        if key in frozen and frozen[key] != digest:
            raise RuntimeError('Previously frozen input/evidence changed: ' + key)
        frozen[key] = digest


def report_partial(root):
    """Never replace failed rows, and do not let report failure hide run failure."""
    attempts = []
    for phase in PHASES:
        folder = root/phase
        if not any(folder.rglob('raw.csv')):
            attempts.append(dict(phase=phase, state='NO_RAW_ROWS'))
            continue
        try:
            reports.main(['--campaign', str(folder), '--output', str(root/('report_'+phase))])
            attempts.append(dict(phase=phase, state='WRITTEN'))
        except BaseException as exc:
            attempts.append(dict(phase=phase, state='REPORT_ERROR', error=repr(exc)))
    save(root/'report_status.json', dict(updated_local=time.strftime('%Y-%m-%dT%H:%M:%S%z'), reports=attempts))
    return attempts


class MemoryRunawayError(RuntimeError):
    pass


def owned_composed_nodes(child_pid):
    """Read-only exact descendants, never global name matching or unrelated PIDs."""
    try:
        children = psutil.Process(child_pid).children(recursive=True)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return []
    result = []
    for proc in children:
        try:
            argv = proc.cmdline()
            executable = proc.exe()
            if (not argv or Path(argv[0]).name not in COMPOSED_NAMES
                    or Path(executable).name not in COMPOSED_NAMES):
                continue
            result.append(dict(pid=proc.pid, create_time=proc.create_time(), executable=executable,
                               argv0=argv[0], rss_mib=proc.memory_info().rss/2**20, owned_descendant=True))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return result


def select_memory_runaway(nodes, threshold_mib=MEMORY_RUNAWAY_MIB):
    eligible = [n for n in nodes if n.get('owned_descendant') is True
                and Path(n.get('executable', '')).name in COMPOSED_NAMES
                and Path(n.get('argv0', '')).name in COMPOSED_NAMES
                and number(n.get('rss_mib')) is not None and number(n['rss_mib']) > threshold_mib]
    return max(eligible, key=lambda n: n['rss_mib']) if eligible else None


def capture_runaway(item, child_pid, target):
    folder = Path(item['path'])
    diagnostic = folder/'memory_runaway_diagnostic'
    diagnostic.mkdir(parents=True, exist_ok=False)
    marker = dict(schema='c24-diagnostic-contamination-v1', contaminated=True,
        reason='memory_runaway_stack_capture', cpu_performance_valid=False,
        threshold_mib=MEMORY_RUNAWAY_MIB, observed_rss_mib=target['rss_mib'],
        pid=target['pid'], create_time=target['create_time'], executable=target['executable'],
        child_pid=child_pid, gdb_timeout_s=GDB_TIMEOUT_S,
        diagnostic_log=str(diagnostic/'gdb_backtrace.txt'),
        created_local=time.strftime('%Y-%m-%dT%H:%M:%S%z'),
        scope='Entire current triplet cost metrics contaminated; retain every original attempt/outcome; no retry')
    # Marker precedes permission checks and ptrace; even a denied capture is
    # diagnostically selected and never becomes accepted CPU evidence.
    save(folder/'diagnostic_contamination.json', marker)
    result = dict(marker, capture_attempts=1, returncode=None, error=None)
    try:
        matches = [n for n in owned_composed_nodes(child_pid)
                   if n['pid'] == target['pid'] and n['create_time'] == target['create_time']]
        if len(matches) != 1:
            raise RuntimeError('Target exited or is no longer the same owned descendant; no ptrace performed')
        debugger = shutil.which('gdb')
        if not debugger:
            raise RuntimeError('gdb unavailable; threshold evidence retained without backtrace')
        command = [debugger, '-batch', '-nx', '-p', str(target['pid']), '-ex', 'set pagination off',
                   '-ex', 'thread apply all bt 24', '-ex', 'detach']
        result['command'] = command
        with (diagnostic/'gdb_backtrace.txt').open('x') as stream:
            completed = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT,
                                       timeout=GDB_TIMEOUT_S, check=False)
        result['returncode'] = completed.returncode
        if completed.returncode:
            result['error'] = 'gdb nonzero return; inspect preserved output (permission failure included)'
    except Exception as exc:
        result['error'] = repr(exc)
    save(diagnostic/'result.json', result)
    return result


def execute(item, root, base_env):
    env = dict(base_env)
    if 'domain' in item:
        env['ROS_DOMAIN_ID'] = item['domain']
    with (root/(item['name']+'.log')).open('x') as log:
        child = subprocess.Popen(item['command'], cwd=ROOT, env=env, stdout=log,
                                 stderr=subprocess.STDOUT, start_new_session=True)
        try:
            while True:
                try:
                    return child.wait(timeout=MEMORY_POLL_S)
                except subprocess.TimeoutExpired:
                    if 'path' not in item:
                        continue
                    target = select_memory_runaway(owned_composed_nodes(child.pid))
                    if target is not None:
                        capture_runaway(item, child.pid, target)
                        raise MemoryRunawayError('Owned composed node exceeded predeclared 4608 MiB; capture attempted; original trial retained')
        except BaseException:
            # Only this controller-owned child process group is targeted.
            for sig, timeout in ((signal.SIGINT, 20), (signal.SIGTERM, 10), (signal.SIGKILL, 5)):
                if child.poll() is not None:
                    break
                try:
                    os.killpg(child.pid, sig)
                    child.wait(timeout=timeout)
                except ProcessLookupError:
                    break
                except subprocess.TimeoutExpired:
                    continue
            raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New iteration directory; existing paths refused')
    parser.add_argument('--base-run', type=int, default=18000)
    parser.add_argument('--candidate', help='Fixed candidate label for this iteration')
    parser.add_argument('--async-certified-recovery', action='store_true',
                        help='Apply the existing explicit runner opt-in identically to all flight modes')
    parser.add_argument('--runner-flag', action='append', default=[],
                        help='Explicit future boolean option, e.g. --runner-flag=--documented-option; not invented by controller')
    parser.add_argument('--runtime-env', action='append', default=[],
                        help='Explicit optional SUPER_NAME=value applied identically to all children and frozen in plan')
    args = parser.parse_args(argv)
    try:
        flags, overrides = extension_options(args.runner_flag, args.runtime_env)
    except ValueError as exc:
        parser.error(str(exc))
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    started, history, current, frozen = time.monotonic(), [], None, {}
    base_env = dict(os.environ, SUPER_CPU_PROFILE='0', SUPER_CALLBACK_TRACE='0', **overrides)
    def status(state, **extra):
        save(root/'status.json', dict(state=state, pid=os.getpid(), current=current, completed=history,
            elapsed_s=time.monotonic()-started, updated_local=time.strftime('%Y-%m-%dT%H:%M:%S%z'),
            requested_off_flights=75, requested_on_flights=15, automatic_retry=False,
            attempted_off_triplets=sum(x.get('phase') == 'validation5' for x in history),
            **extra))
    previous_handlers = {}
    def interrupted(signum, _frame):
        raise InterruptedError('Controller interrupted by signal ' + str(signum))
    for sig in (signal.SIGTERM, signal.SIGINT):
        previous_handlers[sig] = signal.signal(sig, interrupted)
    try:
        status('PREPARING')
        make_references(root)
        commands = build_plan(root, args.base_run, args.candidate, flags, args.async_certified_recovery)
        for phase, count in COUNTS.items():
            save(root/phase/'plan.json', dict(maps=list(MAPS), phase=phase, independent_cohort=True,
                profile_preflight_runs_per_mode=count if phase == 'preflight' else 0,
                unprofiled_runs_per_mode=count if phase == 'validation5' else 0,
                parent_plan=str(root/'plan.json')))
        frozen.update(frozen_policy()['sha256'])
        paths = list((ROOT/'scripts/native_campaign').glob('*.py'))
        paths += [PROBE, TESTS/'static_pc_late_subscriber_test.py', TESTS/'static_map_rviz_reconnect_test.py', event.NORMAL]
        paths += [p for m in MAPS for p in static.map_context(m)['paths'].values()]
        paths += list((root/'references').rglob('*.json'))
        paths += [root/phase/'plan.json' for phase in PHASES]
        paths += [Path('/root/super_ws/install/marsim_render/lib/libmarsim_render.so'),
                  Path('/root/super_ws/install/super_planner/lib/libsuper.a'),
                  Path('/root/super_ws/install/rog_map/lib/librog_map.a'),
                  Path('/root/super_ws/install/mission_planner/lib/mission_planner/waypoint_mission')]
        freeze_files(frozen, paths)
        save(root/'plan.json', dict(schema='c24-normal-validation-v1', maps=list(MAPS), modes=list(MODES),
            map_labels=dict(zip(MAPS, ('N1','N2','N3','N4','N5'))), commands=commands,
            created_local=time.strftime('%Y-%m-%dT%H:%M:%S%z'), frozen_sha256=frozen,
            profiled_preflight_flights=15, unprofiled_primary_flights=75, total_flights=90,
            fresh_static_transport_cases=30, fresh_actual_rviz_cases=5, fresh_time_references=True,
            old_evidence_reused=False, independent_cohorts=True, no_retry=True, no_replacement=True,
            automatic_n20=False, all_failures_retained=True, changes_require_new_iteration=True,
            side_executor_threads=3, common_dispatch_lease_s=.25, event_body_heading=True,
            async_certified_recovery=args.async_certified_recovery,
            mission_time_as_metric=True, paired_time_gate_applied=False,
            on_requires_full_adaptive_safe_complete=True, off_requires_full_adaptive_safe_complete=True,
            sector_outcomes_as_metrics=True, on_and_off_sector_outcomes_retained=True,
            stop_on_measurement_source_recovery_timing_failure=True,
            full_adaptive_outcome_stop_boundary='After current three-mode triplet; at most two remaining simulated modes',
            extra_runner_flags=flags, runtime_environment_overrides=overrides,
            inherited_super_environment={k:v for k,v in base_env.items() if k.startswith('SUPER_')},
            memory_runaway_sentinel=dict(enabled=True, threshold_mib=MEMORY_RUNAWAY_MIB,
                poll_s=MEMORY_POLL_S, owned_descendants_only=True, executable_names=sorted(COMPOSED_NAMES),
                capture_once=True, debugger_timeout_s=GDB_TIMEOUT_S, backtrace_frames_per_thread=24,
                action='mark contaminated, capture bounded stack, SIGINT owned child group, stop for diagnosis',
                raw_attempts_and_outcomes_preserved=True, contaminated_costs_never_valid=True),
            cpu_scope='Experiment cgroup including simulator; external observer excluded; ON and OFF separate',
            original_cpu40_not_redefined=True, cpu_reduction_is_reported_not_gate=True,
            finite_simulation_not_population_guarantee=True))
        freeze_files(frozen, [root/'plan.json'])
        save(root/'frozen_inputs_and_evidence.json', frozen)
        previous_phase = 'static'
        for item in commands:
            current = {k:v for k,v in item.items() if k != 'command'}
            changed = changed_inputs(frozen)
            if changed:
                raise RuntimeError('Frozen inputs changed: ' + repr(changed))
            if item['phase'] != previous_phase:
                if previous_phase == 'static':
                    validations = {m: static.validate_manifest(root/'static_preflight'/m/'acceptance.json', static.map_context(m)) for m in MAPS}
                    save(root/'static_gate.json', validations)
                    if not all(v.get('valid') is True for v in validations.values()):
                        raise RuntimeError('Fresh map-bound static/RViz preflight failed')
                else:
                    gate = phase_gate(commands, previous_phase)
                    save(root/(previous_phase+'_gate.json'), gate)
                    report_partial(root)
                    if gate['valid'] is not True:
                        raise RuntimeError('Cannot start OFF: fresh ON coverage/gates incomplete')
                previous_phase = item['phase']
            status('RUNNING')
            print('START', item['name'], flush=True)
            try:
                code = execute(item, root, base_env)
            except MemoryRunawayError:
                history.append(dict(name=item['name'], phase=item['phase'], returncode=None,
                    valid=False, diagnostic_contaminated=True,
                    contamination_marker=str(Path(item['path'])/'diagnostic_contamination.json')))
                raise
            entry = dict(name=item['name'], phase=item['phase'], returncode=code)
            history.append(entry)
            if 'path' in item:
                folder = Path(item['path'])
                audit = triplet_audit(folder, item['map'], item['run'], item['phase']=='preflight',
                    item['candidate'], item['modes'], item['async_certified_recovery'])
                save(folder/'triplet_verification.json', audit)
                entry.update(valid=audit['valid'], outcome_failures=audit['outcome_failures'])
                # Analyze any preserved ON modes even when another mode failed.
                if item['phase'] == 'preflight':
                    try:
                        save(folder/'thread_cpu_summary.json', {m:stages.summarize(folder,m,item['run'],item['map'])
                            for m in MODES if (folder/f'{m}_summary.json').is_file()})
                    except Exception as exc:
                        save(folder/'stage_analysis_error.json', dict(error=repr(exc)))
                if code or audit['valid'] is not True:
                    raise RuntimeError('Flight gate failed; all attempts retained: ' + item['name'])
                freeze_files(frozen, [folder/'plan.json', folder/'raw.csv', folder/'status.json',
                    folder/'triplet_verification.json', *(folder/f'{m}_summary.json' for m in MODES)])
            elif code:
                raise RuntimeError('Static preflight failed; evidence retained: ' + item['name'])
            elif item['name'].startswith('accept_'):
                manifest = root/'static_preflight'/item['map']/'acceptance.json'
                validation = static.validate_manifest(manifest, static.map_context(item['map']))
                if validation.get('valid') is not True:
                    raise RuntimeError('Static manifest validation failed: ' + item['map'])
                freeze_files(frozen, [manifest, *map(Path, validation.get('evidence_sha256', {}))])
            save(root/'frozen_inputs_and_evidence.json', frozen)
            print('FINISH', json.dumps(entry), flush=True)
            status('RUNNING')
        gate = phase_gate(commands, 'validation5')
        save(root/'validation5_gate.json', gate)
        if gate['valid'] is not True or changed_inputs(frozen) or sha(event.NORMAL) != event.NORMAL_SHA:
            raise RuntimeError('Final exact coverage/frozen-evidence/Normal preservation gate failed')
        report_status = report_partial(root)
        if any(item['state'] != 'WRITTEN' for item in report_status):
            raise RuntimeError('Flights complete but automatic reports incomplete; do not claim final handoff')
        status('COMPLETE', completed_off_flights=75, completed_on_flights=15,
               outcome_failures=[h for h in history if h.get('outcome_failures')])
    except BaseException as exc:
        status('STOPPED_FOR_DIAGNOSIS', error=repr(exc))
        report_partial(root)
        raise
    finally:
        for sig, handler in previous_handlers.items():
            signal.signal(sig, handler)


if __name__ == '__main__':
    main()
