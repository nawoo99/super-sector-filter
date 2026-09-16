#!/usr/bin/env python3
"""C20 bounded-certificate-refresh validation, frozen before the first flight.

Renew transport/RViz evidence, one ON triplet then five rotated OFF triplets.
No retry/tuning, no pooling with old C19. Stop on safety/completion failure.
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
import static_latched_preflight as static


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=True)
    if (root / 'plan.json').exists():
        raise RuntimeError('No overwriting/retries')
    for name in ('time_reference', 'static_preflight', 'repeats'):
        (root / name).mkdir(exist_ok=False)
    for mode, path in REFERENCE_SOURCES.items():
        shutil.copyfile(path, root / 'time_reference' / f'{mode}_summary.json')
    base = common_args(root)
    base[base.index('--candidate') + 1] = 'c20_bounded_certificate_refresh'
    acceptance = root / 'static_preflight/acceptance.json'
    base[base.index('--static-latched-preflight') + 1] = str(acceptance)
    commands = []
    transport = []
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
    on = root / 'profile_preflight_run9600'
    commands.append(dict(name='profile_on', cohort='profile_preflight', run=9600, path=str(on),
        command=base + ['--output', str(on), '--run', '9600', '--profile-cpu',
                        '--modes', 'full', 'sector', 'adaptive']))
    for index, order in enumerate(ORDERS, 1):
        run = 9600 + index
        folder = root / 'repeats' / f'r{index:02d}_run{run}'
        commands.append(dict(name=f'off_{index}', cohort='unprofiled_validation', run=run, path=str(folder),
            command=base + ['--output', str(folder), '--run', str(run),
                           '--small-pool-profile-reference', str(on), '--modes', *order]))
    old = json.loads((ROOT / 'results/c19_cpu_attribution_20260916/profile_preflight_run9500/plan.json').read_text())
    paths = {p for p in old['asset_sha256'] if p.startswith('/root/super_ws/')}
    paths.update(old['runtime_policy']['sha256'])
    frozen = {p: sha(p) for p in paths}
    save(root / 'plan.json', dict(schema='c20-certificate-refresh-v1', created_local=time.strftime('%Y-%m-%dT%H:%M:%S%z'),
        commands=commands, runtime_sha256=frozen, controller_sha256=sha(__file__),
        map='seed1', profile_preflight_runs_per_mode=1, unprofiled_runs_per_mode=5,
        execution_orders=ORDERS, maximum_extra_validation_attempts=1,
        cooperative_retry_deadline_ms_from_refresh_entry=4,
        hard_realtime_deadline_guarantee=False, geometry_first_pass_unchanged=True,
        automatic_retry=False, all_attempts_retained=True, runtime_changes_forbidden=True,
        no_historical_pooling=True, no_generalization_or_population_guarantee=True,
        same_full_adaptive_mission_time_ratio_limit=1.10,
        engineering_mean_cpu_reduction_target_pct=30, initial_cpu40_target_not_redefined=True,
        primary_cpu_scope='all experiment processes/threads including simulator, external observer excluded',
        cumulative_cpu_also_reported=True, cpu_window_slightly_wider_than_mission=True))
    history = []
    try:
        for item in commands:
            if any(sha(p) != value for p, value in frozen.items()):
                raise RuntimeError('Runtime changed during frozen verification')
            save(root / 'status.json', dict(state='RUNNING', current=item['name'], completed=history, pid=os.getpid()))
            print('START', item['name'], flush=True)
            env = dict(os.environ)
            env.pop('SUPER_CPU_PROFILE', None)
            if 'domain' in item:
                env['ROS_DOMAIN_ID'] = item['domain']
            with (root / (item['name'] + '.log')).open('x') as log:
                done = subprocess.run(item['command'], env=env, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            history.append(dict(name=item['name'], returncode=done.returncode))
            print('FINISH', history[-1], flush=True)
            if done.returncode:
                raise RuntimeError('Stopped without retry: ' + item['name'])
            if 'cohort' in item:
                for mode in ('full','sector','adaptive'):
                    row = json.loads((Path(item['path']) / f'{mode}_summary.json').read_text())
                    if row.get('success') is not True or row.get('safety_collisions') != 0:
                        raise RuntimeError(f'{mode}: safety/completion failure, retained')
        save(root / 'status.json', dict(state='COMPLETE', completed=history,
            note='Execution complete is not acceptance; use comparison gates'))
    except BaseException as exc:
        save(root / 'status.json', dict(state='STOPPED_FOR_DIAGNOSIS', completed=history, error=repr(exc)))
        raise


if __name__ == '__main__':
    main()
