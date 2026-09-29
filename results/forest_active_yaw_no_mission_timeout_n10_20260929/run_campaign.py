#!/usr/bin/env python3
"""Forest Active-Yaw Sector n=10 with no mission-time cutoff and no retry."""
from datetime import datetime
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parent
CHILD = ROOT / 'run_no_timeout_child.py'
SUPER_SCRIPTS = Path('/root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/scripts')
RUNS = tuple(range(94201, 94211))


def save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=True) + '\n')
    temporary.replace(path)


def command(run, output):
    return [
        sys.executable, str(CHILD),
        '--output', str(output), '--run', str(run),
        '--candidate', 'sector_active_yaw_scan_v1_no_mission_timeout',
        '--mean-cpu-reduction-target-pct', '30',
        '--map', 'forest_cluster_f01', '--modes', 'sector',
        '--compose', '--profile-cpu', '--async-certified-recovery',
        '--skip-backup-diagnostic-replay',
        '--skip-unobserved-path-publication', '--fast-occupied-box-scan',
        '--snapshot-line-query', '--snapshot-neighbor-cache',
        '--side-executor-threads', '3', '--monitor-intervals',
        '--guarded-demand-replan', '--goal-retransmit-identity',
        '--headless-parameter-services', '--dedicated-static-pc-executor',
        '--no-optimizer-phase-memory-trace',
        '--optimizer-clearance-gate-first', '--mission-time-as-metric',
        '--sector-outcomes-as-metrics',
        '--full-config', 'static_seedmaps_guard_viability_tight_v7_nearhit_v3.yaml',
        '--sector-config', 'static_seedmaps_guard_viability_tight_v7_filtered_reliable_nearhit_v3.yaml',
        '--adaptive-config', 'static_seedmaps_guard_viability_tight_v7_event_recovery_v1_nearhit_v3.yaml',
    ]


def main():
    lock = open('/tmp/super_sector_filter_gapfree_n5.lock', 'a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    env = {key: value for key, value in os.environ.items()
           if not key.startswith('SUPER_')}
    completed = []
    started = time.monotonic()
    save(ROOT / 'protocol.json', {
        'campaign': ROOT.name,
        'map': 'forest_cluster_f01',
        'mode': 'Sector (Active-Yaw)',
        'run_ids': list(RUNS),
        'repeats': 10,
        'attempts_per_flight': 1,
        'retry': False,
        'replacement': False,
        'mission_time_cutoff_s': None,
        'monitor_encoding': 'positive infinity; completion remains the mission terminal condition',
        'resource_and_process_integrity_guards': True,
        'status': 'running',
    })
    for index, run in enumerate(RUNS, 1):
        output = ROOT / f'r{index:02d}_run{run}'
        if output.exists():
            raise RuntimeError(f'Existing output refused: {output}')
        current = {'index': index, 'run': run, 'output': str(output),
                   'started_local': datetime.now().astimezone().isoformat()}
        save(ROOT / 'status.json', {'state': 'RUNNING', 'current': current,
             'completed': completed, 'elapsed_s': time.monotonic() - started})
        print(f'START {index}/10 run{run}', flush=True)
        with (ROOT / f'r{index:02d}_run{run}.driver.log').open('x') as log:
            result = subprocess.run(command(run, output), env=env,
                                    stdout=log, stderr=subprocess.STDOUT)
        entry = dict(current, returncode=result.returncode,
                     finished_local=datetime.now().astimezone().isoformat())
        completed.append(entry)
        print(f'FINISH {index}/10 run{run} rc={result.returncode}', flush=True)
        save(ROOT / 'status.json', {'state': 'RUNNING', 'current': None,
             'completed': completed, 'elapsed_s': time.monotonic() - started})
        if result.returncode != 0:
            save(ROOT / 'status.json', {'state': 'STOPPED_INFRASTRUCTURE_FAILURE',
                 'current': None, 'completed': completed,
                 'elapsed_s': time.monotonic() - started})
            return result.returncode
    protocol = json.loads((ROOT / 'protocol.json').read_text())
    protocol['status'] = 'complete'
    protocol['observed_flights'] = len(completed)
    save(ROOT / 'protocol.json', protocol)
    save(ROOT / 'status.json', {'state': 'COMPLETE', 'current': None,
         'completed': completed, 'elapsed_s': time.monotonic() - started})
    print('COMPLETE 10/10 scheduled flights', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
