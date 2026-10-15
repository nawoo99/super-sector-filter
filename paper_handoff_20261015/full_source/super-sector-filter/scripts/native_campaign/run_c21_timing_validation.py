#!/usr/bin/env python3
"""Prospective timestamp diagnostics or frozen three-mode seed1 validation.

Diagnosis: three traced/profiled Full flights, retain timing failures and continue
the predeclared diagnostic series. Other failures stop. Validation: tracing OFF,
one ON triplet then five OFF triplets, stop at any contract/safety failure.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from run_c19_frozen_validation import ROOT, ORDERS, REFERENCE_SOURCES, common_args, save, sha
from run_c19_cpu_attribution import TESTS, PROBE
from cylinder_map_search import frozen_policy
import static_latched_preflight as static


def only_timing_failure(row):
    checks = row.get('source_acquisition', {}).get('checks', {})
    return (all(row.get(k) is True for k in ('success', 'run_valid', 'resource_valid', 'speed_limit_valid'))
            and row.get('safety_collisions') == 0 and checks
            and {k for k, v in checks.items() if v is not True} == {'small_pool_timing'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--phase', required=True, choices=('diagnosis', 'validation'))
    parser.add_argument('--base-run', required=True, type=int)
    parser.add_argument('--side-threads', default=2, choices=(2, 3), type=int)
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    for name in ('time_reference', 'static_preflight', 'repeats'):
        (root / name).mkdir()
    for mode, path in REFERENCE_SOURCES.items():
        shutil.copyfile(path, root / 'time_reference' / f'{mode}_summary.json')
    save(root / 'time_reference/provenance.json', {m: dict(source=str(p), sha256=sha(p),
         purpose='Historical no-long-hold timing reference only, never pooled CPU')
         for m, p in REFERENCE_SOURCES.items()})
    base = common_args(root)
    base[base.index('--candidate') + 1] = f'c21_timing_{args.phase}_{args.side_threads}workers'
    base[base.index('--side-executor-threads') + 1] = str(args.side_threads)
    acceptance = root / 'static_preflight/acceptance.json'
    base[base.index('--static-latched-preflight') + 1] = str(acceptance)
    commands, transport = [], []
    for composition in ('standalone', 'full', 'adaptive'):
        for sequence in ('reader-first', 'late'):
            name = f'{composition}_{sequence}_attempt1'
            out = root / 'static_preflight' / name
            transport.append(out / 'result.json')
            commands.append(dict(name=name, domain='190', command=[sys.executable,
                str(TESTS / 'static_pc_late_subscriber_test.py'), '--out-dir', str(out),
                '--poll-ms', '1', '--durable', '--latched-once', '--reader-qos', 'durable',
                '--composition', composition, '--sequence', sequence,
                '--expected-sha256', static.EXPECTED_GEOMETRY['sha256']]))
    rviz = root / 'static_preflight/actual_rviz_attempt1/result.json'
    commands.append(dict(name='actual_rviz_attempt1', domain='191', command=[sys.executable,
        str(TESTS / 'static_map_rviz_reconnect_test.py'), '--out-dir', str(rviz.parent),
        '--probe-binary', str(PROBE), '--expected-sha256', static.EXPECTED_GEOMETRY['sha256']]))
    commands.append(dict(name='acceptance', command=[sys.executable,
        str(ROOT / 'scripts/native_campaign/static_latched_preflight.py'), 'create',
        *[v for path in transport for v in ('--transport', str(path))],
        '--rviz', str(rviz), '--output', str(acceptance)]))
    if args.phase == 'diagnosis':
        for i in range(3):
            run = args.base_run + i
            folder = root / f'diagnostic_run{run}'
            commands.append(dict(name=f'diagnostic_{i+1}', modes=['full'], path=str(folder),
                command=base + ['--output', str(folder), '--run', str(run),
                                '--profile-cpu', '--callback-trace', '--modes', 'full']))
    else:
        on = root / f'profile_preflight_run{args.base_run}'
        commands.append(dict(name='profile_on', modes=['full', 'sector', 'adaptive'], path=str(on),
            command=base + ['--output', str(on), '--run', str(args.base_run), '--profile-cpu',
                            '--modes', 'full', 'sector', 'adaptive']))
        for index, order in enumerate(ORDERS, 1):
            run = args.base_run + index
            folder = root / 'repeats' / f'r{index:02d}_run{run}'
            commands.append(dict(name=f'off_{index}', modes=list(order), path=str(folder),
                command=base + ['--output', str(folder), '--run', str(run),
                               '--small-pool-profile-reference', str(on), '--modes', *order]))
    frozen = frozen_policy()['sha256']
    frozen.update({str(p): sha(p) for p in (
        Path('/root/super_ws/install/perfect_drone_sim/lib/perfect_drone_sim/perfect_drone_adaptive_node'),
        ROOT / 'scripts/native_campaign/adaptive_cpu40_seed1.py',
        ROOT / 'scripts/native_campaign/native_loop_monitor.py',
        ROOT / 'scripts/native_campaign/message_intervals.py')})
    save(root / 'plan.json', dict(schema='c21-timing-v1', phase=args.phase,
        created_local=time.strftime('%Y-%m-%dT%H:%M:%S%z'), commands=commands,
        runtime_sha256=frozen, controller_sha256=sha(__file__), map='seed1',
        profile_preflight_runs_per_mode=1 if args.phase == 'validation' else 0,
        unprofiled_runs_per_mode=5 if args.phase == 'validation' else 0,
        trace_on_only_diagnostic=args.phase == 'diagnosis', side_executor_threads=args.side_threads,
        all_attempts_retained=True, automatic_retry=False, no_historical_pooling=True,
        runtime_changes_forbidden=True, no_population_or_generalization_guarantee=True,
        odometry_p99_limit_ms=20, odometry_max_limit_ms=50,
        same_full_adaptive_mission_time_ratio_limit=1.10,
        engineering_mean_cpu_reduction_target_pct=30, initial_cpu40_target_not_redefined=True,
        primary_cpu_scope='All experiment processes including simulator; external observer excluded',
        cumulative_cpu_also_reported=True))
    history = []
    try:
        for item in commands:
            if any(sha(p) != value for p, value in frozen.items()):
                raise RuntimeError('Frozen runtime changed')
            save(root / 'status.json', dict(state='RUNNING', current=item['name'], completed=history, pid=os.getpid()))
            print('START', item['name'], flush=True)
            env = dict(os.environ)
            env.pop('SUPER_CPU_PROFILE', None)
            env.pop('SUPER_CALLBACK_TRACE', None)
            if 'domain' in item:
                env['ROS_DOMAIN_ID'] = item['domain']
            with (root / (item['name'] + '.log')).open('x') as log:
                done = subprocess.run(item['command'], env=env, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            entry = dict(name=item['name'], returncode=done.returncode)
            history.append(entry)
            print('FINISH', entry, flush=True)
            rows = [json.loads((Path(item['path']) / f'{m}_summary.json').read_text())
                    for m in item.get('modes', []) if (Path(item['path']) / f'{m}_summary.json').exists()]
            if done.returncode:
                if args.phase == 'diagnosis' and len(rows) == 1 and only_timing_failure(rows[0]):
                    entry['retained_timing_failure_not_acceptance'] = True
                    continue
                raise RuntimeError('Stopped for diagnosis: ' + item['name'])
            if len(rows) != len(item.get('modes', [])):
                raise RuntimeError('Missing flight evidence')
            if any(r.get('success') is not True or r.get('safety_collisions') != 0 for r in rows):
                raise RuntimeError('Safety/completion failure retained')
        save(root / 'status.json', dict(state='COMPLETE', completed=history,
             note='Execution complete is not acceptance; review all comparative gates'))
    except BaseException as exc:
        save(root / 'status.json', dict(state='STOPPED_FOR_DIAGNOSIS', completed=history, error=repr(exc)))
        raise


if __name__ == '__main__':
    main()
