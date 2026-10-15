#!/usr/bin/env python3
"""One diagnostic ON triplet and one OFF triplet; no tuning/retry/campaign.

Renew all static-map transport/RViz evidence for the diagnostic-only rebuild.
OFF is a smoke comparison, not a statistically isolated overhead estimate.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from run_c19_frozen_validation import ROOT, common_args, REFERENCE_SOURCES, save, sha
import static_latched_preflight as static

RUNTIME = Path('/root/super_ws/src/SUPER')
TESTS = RUNTIME / 'mars_uav_sim/perfect_drone_sim/test'
PROBE = Path('/tmp/super-rviz-static-test.1LtVI4/static_map_rviz_probe')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=True)
    if (root / 'plan.json').exists():
        raise RuntimeError('No overwrite or automatic retry')
    for name in ('time_reference', 'static_preflight', 'repeats'):
        (root / name).mkdir(exist_ok=False)
    for mode, source in REFERENCE_SOURCES.items():
        shutil.copyfile(source, root / 'time_reference' / f'{mode}_summary.json')
    base = common_args(root)
    base[base.index('--candidate') + 1] = 'c19_diagnostic_attribution'
    acceptance = root / 'static_preflight/acceptance.json'
    base[base.index('--static-latched-preflight') + 1] = str(acceptance)
    on = root / 'profile_preflight_run9500'
    off = root / 'repeats/r01_run9501'
    commands = []
    transport_paths = []
    for composition in ('standalone', 'full', 'adaptive'):
        for sequence in ('reader-first', 'late'):
            name = f'{composition}_{sequence}_attempt1'
            out = root / 'static_preflight' / name
            transport_paths.append(out / 'result.json')
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
        *[v for path in transport_paths for v in ('--transport', str(path))],
        '--rviz', str(rviz), '--output', str(acceptance)]))
    commands.append(dict(name='profile_on', command=base + ['--output', str(on),
        '--run', '9500', '--profile-cpu', '--modes', 'full', 'sector', 'adaptive']))
    commands.append(dict(name='profile_off', command=base + ['--output', str(off),
        '--run', '9501', '--small-pool-profile-reference', str(on),
        '--modes', 'adaptive', 'sector', 'full']))
    source_paths = [RUNTIME / p for p in (
        'rog_map/include/super_utils/thread_cpu_profile.hpp',
        'rog_map/include/rog_map_ros/rog_map_ros2.hpp',
        'mission_planner/Apps/native_sector_cpp.cpp', 'mission_planner/CMakeLists.txt')]
    binaries = [Path('/root/super_ws/install/perfect_drone_sim/lib/perfect_drone_sim') / p
                for p in ('perfect_drone_node', 'perfect_drone_full_node', 'perfect_drone_adaptive_node')]
    binaries.append(Path('/root/super_ws/install/mission_planner/lib/libnative_sector_cpp_component.so'))
    frozen = {str(p): sha(p) for p in source_paths + binaries}
    save(root / 'plan.json', dict(schema='c19-cpu-attribution-v1', commands=commands,
        runtime_sha256=frozen, controller_sha256=sha(__file__),
        purpose='diagnostic attribution, not an optimized candidate or final campaign',
        algorithm_or_safety_change=False, all_attempts_retained=True, automatic_retry=False,
        on_runs_per_mode=1, off_runs_per_mode=1, modes=['full', 'sector', 'adaptive'],
        overhead_causality_not_identified_by_single_pair=True,
        historical_off_n5_not_pooled=True, no_map_qualification_claim=True))
    history = []
    try:
        for command in commands:
            if any(sha(p) != value for p, value in frozen.items()):
                raise RuntimeError('Runtime changed during diagnostic verification')
            save(root / 'status.json', dict(state='RUNNING', current=command['name'], completed=history))
            print('START', command['name'], flush=True)
            env = dict(os.environ)
            env.pop('SUPER_CPU_PROFILE', None)
            if 'domain' in command:
                env['ROS_DOMAIN_ID'] = command['domain']
            with (root / (command['name'] + '.log')).open('x') as log:
                result = subprocess.run(command['command'], env=env, cwd=ROOT,
                                        stdout=log, stderr=subprocess.STDOUT)
            history.append(dict(name=command['name'], returncode=result.returncode))
            print('FINISH', history[-1], flush=True)
            if result.returncode:
                raise RuntimeError('Stopped for diagnosis: ' + command['name'])
            if command['name'] in ('profile_on', 'profile_off'):
                folder = on if command['name'] == 'profile_on' else off
                for mode in ('full', 'sector', 'adaptive'):
                    summary = json.loads((folder / f'{mode}_summary.json').read_text())
                    if summary.get('success') is not True or summary.get('safety_collisions') != 0:
                        raise RuntimeError(f'{mode}: safety/completion failure, retained without retry')
        save(root / 'status.json', dict(state='COMPLETE', completed=history))
    except BaseException as error:
        save(root / 'status.json', dict(state='STOPPED_FOR_DIAGNOSIS', completed=history, error=repr(error)))
        raise


if __name__ == '__main__':
    main()
