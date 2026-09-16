#!/usr/bin/env python3
"""Prospectively frozen seed1 validation; no tuning or automatic retry.

Separate one profiled three-mode preflight from five unprofiled triplets.
Every attempted flight is retained. Runtime code/config/binary hashes are bound
by the existing per-triplet runner and by the prior C19 source manifest.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
PREVIOUS = ROOT / 'results/adaptive_cpu40_20260916/c19_clearance_gate_profile_run9320'
ORDERS = [('full', 'sector', 'adaptive'), ('sector', 'adaptive', 'full'),
          ('adaptive', 'full', 'sector'), ('adaptive', 'sector', 'full'),
          ('sector', 'full', 'adaptive')]
REFERENCE_SOURCES = {
    'full': ROOT / 'results/adaptive_cpu40_20260916/c05_neighbor_cache_profile/full_summary.json',
    'adaptive': ROOT / 'results/adaptive_cpu40_20260916/c05_neighbor_cache_profile/adaptive_summary.json',
    'sector': ROOT / 'results/sensor_acquisition_seed1_n1_20260916/sector_summary.json',
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def common_args(root):
    return [sys.executable, str(ROOT / 'scripts/native_campaign/adaptive_cpu40_seed1.py'),
            '--candidate', 'c19_frozen_validation', '--mean-cpu-reduction-target-pct', '30',
            '--compose', '--skip-backup-diagnostic-replay',
            '--skip-unobserved-path-publication', '--fast-occupied-box-scan',
            '--snapshot-line-query', '--snapshot-neighbor-cache',
            '--static-pc-latched-once', '--static-latched-preflight',
            str(ROOT / 'results/adaptive_cpu40_20260916/c19_static_latched_preflight/acceptance.json'),
            '--side-executor-threads', '2', '--monitor-intervals',
            '--guarded-demand-replan', '--extended-demand-lease',
            '--goal-retransmit-identity', '--headless-parameter-services',
            '--dedicated-static-pc-executor', '--no-optimizer-phase-memory-trace',
            '--optimizer-clearance-gate-first', '--time-reference-folder', str(root / 'time_reference')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    (root / 'time_reference').mkdir()
    (root / 'repeats').mkdir()
    original_plan = json.loads((PREVIOUS / 'plan.json').read_text())
    runtime_hashes = {p: value for p, value in original_plan['asset_sha256'].items()
                      if p.startswith('/root/super_ws/')}
    changed = [p for p, value in runtime_hashes.items() if sha(p) != value]
    if changed:
        raise RuntimeError('Frozen C19 runtime changed: ' + repr(changed))
    reference_provenance = {}
    for mode, source in REFERENCE_SOURCES.items():
        destination = root / 'time_reference' / f'{mode}_summary.json'
        shutil.copyfile(source, destination)
        reference_provenance[mode] = dict(source=str(source), sha256=sha(source),
            purpose='Predeclared no-long-hold timing reference, NOT comparative CPU evidence')
    save(root / 'time_reference/provenance.json', reference_provenance)
    preflight = root / 'profile_preflight_run9400'
    commands = [dict(cohort='profile_preflight', run=9400, path=str(preflight),
        command=common_args(root) + ['--output', str(preflight), '--run', '9400',
                                   '--profile-cpu', '--modes', 'full', 'sector', 'adaptive'])]
    for index, modes in enumerate(ORDERS, 1):
        run = 9400 + index
        path = root / 'repeats' / f'r{index:02d}_run{run}'
        commands.append(dict(cohort='unprofiled_validation', run=run, path=str(path),
            command=common_args(root) + ['--output', str(path), '--run', str(run),
                '--small-pool-profile-reference', str(preflight), '--modes', *modes]))
    save(root / 'plan.json', dict(schema='c19-frozen-seed1-validation-v1',
        created_local=time.strftime('%Y-%m-%dT%H:%M:%S%z'), map='seed1',
        seed1_is_previous_tuning_map=True, no_generalization_claim=True,
        frozen_runtime_reference=str(PREVIOUS), runtime_sha256=runtime_hashes,
        profile_preflight_runs_per_mode=1, unprofiled_runs_per_mode=5,
        execution_orders=ORDERS, order_note='Rotated, near-balanced positions; not perfectly balanced at n=5',
        engineering_mean_cpu_reduction_target_pct=30, target_is_not_publication_threshold=True,
        cumulative_cpu_also_reported=True, same_full_adaptive_mission_time_ratio_limit=1.10,
        require_full_adaptive_completion_and_zero_contact_for_expansion=True,
        no_automatic_retry=True, all_failures_retained=True, runtime_changes_forbidden=True,
        reference_provenance=reference_provenance,
        primary_cpu_scope='All experiment-cgroup processes/threads including simulator, excluding external observer',
        cpu_time_scope='Cgroup measurement window, slightly wider than waypoint mission',
        autonomy_only_cpu_unavailable_from_composed_process=True,
        gpu_scope='Device-wide samples; not algorithm attribution',
        payload_scope='Logical PointCloud2 payload, not physical wire bytes; do not sum overlapping edges',
        profile_stage_scope='Separate profiled preflight only; do not pool with primary OFF cohort',
        never_pool_historical_normal_or_stress=True, commands=commands,
        controller_sha256=sha(__file__)))
    history = []
    try:
        for item in commands:
            if any(sha(p) != value for p, value in runtime_hashes.items()):
                raise RuntimeError('Frozen runtime changed before run')
            save(root / 'status.json', dict(state='RUNNING', pid=os.getpid(), current=item,
                                           completed=history))
            print('START', item['cohort'], item['run'], flush=True)
            with (root / f'run{item["run"]}.log').open('x') as log:
                completed = subprocess.run(item['command'], cwd=ROOT, stdout=log,
                                           stderr=subprocess.STDOUT, check=False)
            entry = dict(run=item['run'], cohort=item['cohort'], returncode=completed.returncode)
            history.append(entry)
            print('FINISH', json.dumps(entry), flush=True)
            if completed.returncode:
                raise RuntimeError(f'Run {item["run"]} stopped; retained for diagnosis, no retry')
            folder = Path(item['path'])
            summaries = {mode: json.loads((folder / f'{mode}_summary.json').read_text())
                         for mode in ('full', 'sector', 'adaptive')}
            unsafe = [mode for mode in ('full', 'adaptive')
                      if summaries[mode].get('success') is not True
                      or summaries[mode].get('safety_collisions') != 0]
            if unsafe:
                raise RuntimeError(f'Full/Adaptive safety/completion failure in {unsafe}; no tuning/retry')
        save(root / 'status.json', dict(state='COMPLETE', pid=os.getpid(), completed=history))
    except BaseException as exc:
        save(root / 'status.json', dict(state='STOPPED_FOR_DIAGNOSIS', pid=os.getpid(),
                                       completed=history, error=repr(exc)))
        raise


if __name__ == '__main__':
    main()
