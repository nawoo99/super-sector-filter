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
import time

import psutil
import normal_cpu_gpu_diagnostic as diagnostic
import event_recovery_seed1_smoke as event
import sensor_acquisition_seed1_smoke as source
from analyze_cylinder_only_stress_full_gate import quality_valid

BACKUP = 'results/adaptive_cpu40_backup_20260916_aloDDu/runtime_before.tar.gz'
FLIGHT_NAMES = {'fsm_node', 'perfect_drone_node', 'perfect_drone_full_node',
                'perfect_drone_frontend_node', 'perfect_drone_adaptive_node',
                'source_acquisition_test'}


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
    out['target_met'] = bool(safe and out['mission_time_guardrail_pass']
                             and reduction is not None and reduction >= 40.)
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
    parser.add_argument('--full-config', default=diagnostic.search.PROFILES['full'])
    parser.add_argument('--sector-config', default=diagnostic.search.PROFILES['sector'])
    parser.add_argument('--adaptive-config', default=event.PROFILE)
    args = parser.parse_args()
    if len(set(args.modes)) != len(args.modes):
        parser.error('Each mode may run only once per candidate')
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
    runtime = Path('/root/super_ws/src/SUPER')
    profiles = {'full': args.full_config, 'sector': args.sector_config,
                'adaptive': args.adaptive_config}
    files = {runtime / 'super_planner/config' / name for name in profiles.values()}
    files.update({runtime / 'mars_uav_sim/perfect_drone_sim/config/seed1.yaml',
                  runtime / 'mars_uav_sim/perfect_drone_sim/pcd/seed_maps/seed1.pcd',
                  runtime / 'mission_planner/data/loop24.txt',
                  Path('/root/super_ws/install/marsim_render/lib/libmarsim_render.so'),
                  Path('/root/super_ws/install/mission_planner/lib/libnative_sector_cpp_component.so'),
                  Path(__file__).resolve()})
    if args.compose:
        files.add(Path('/root/super_ws/install/perfect_drone_sim/lib/perfect_drone_sim/perfect_drone_adaptive_node'))
    hashes = {str(p): event.sha(p) for p in sorted(files)}
    frozen_policy = diagnostic.search.frozen_policy()
    diagnostic.RUN = args.run
    profiler = diagnostic.Profiler(root / 'telemetry.jsonl')
    diagnostic.save(root / 'plan.json', dict(
        schema='adaptive-cpu40-seed1-exploratory-v1', candidate=args.candidate,
        map='seed1', run=args.run, modes=args.modes, profiles=profiles,
        backup=BACKUP, mean_cpu_reduction_target_pct=40,
        cumulative_cpu_also_reported=True, max_mission_time_ratio=1.10,
        compose=args.compose, cpu_profile=args.profile_cpu,
        logical_cpus=os.cpu_count(), runtime_policy=frozen_policy,
        asset_sha256=hashes, baseline_seconds=12,
        common_parameters_unchanged='seed1/loop24/v7,45deg-half-angle,0.4deg/10Hz sensor',
        frozen_normal_sha256=event.NORMAL_SHA, no_automatic_retry=True,
        exploratory_tuning=True, not_pooled_with_previous_results=True))
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
                options = dict(diagnostic.search.OPTIONS)
                options.update(sensor_acquisition=True,
                    sensor_planner_intra_process=args.compose,
                    adaptive_event_recovery=mode == 'adaptive')
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
                result['source_acquisition'] = source.audit_source(root / 'artifacts', args.run, mode)
                if args.compose and mode != 'full':
                    stats = result['source_acquisition']['frontend_stats']
                    result['source_acquisition']['checks'].update({
                        'direct_output_enabled': stats.get('direct_output_enabled') is True,
                        'direct_output_exercised': stats.get('direct_output_events', 0) > 0,
                        'cloud_dds_zero': row.get('dds_cloud_payload_mib_s') == 0.,
                    })
                result['candidate'] = args.candidate
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
