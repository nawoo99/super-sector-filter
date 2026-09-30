#!/usr/bin/env python3
"""Urban canonical Active-Yaw Sector, n=10, no mission cutoff or retry."""
from datetime import datetime
import csv
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parent
CHILD = ROOT / 'run_no_timeout_child.py'
SUPER_SCRIPTS = Path(
    '/root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/scripts'
)
sys.path.insert(0, str(SUPER_SCRIPTS))
import scenario7_guard_v6_cpu_compare as canonical


RUNS = tuple(range(94501, 94511))


def save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=True) + '\n')
    temporary.replace(path)


def command(run, output):
    return [
        sys.executable, str(CHILD),
        '--output', str(output), '--run', str(run),
        '--candidate', 'canonical_active_yaw_sector_urban_no_timeout_n10',
        '--mean-cpu-reduction-target-pct', '30',
        '--map', 'urban_blocks_u01', '--modes', 'sector',
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
        '--full-config',
        'static_seedmaps_guard_viability_tight_v7_nearhit_v3.yaml',
        '--sector-config',
        'static_seedmaps_guard_viability_tight_v7_filtered_reliable_nearhit_v3.yaml',
        '--adaptive-config',
        'static_seedmaps_guard_viability_tight_v7_event_recovery_v1_nearhit_v3.yaml',
    ]


def verify_flight(output, run):
    raw_path = output / 'raw.csv'
    with raw_path.open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 1:
        raise RuntimeError(f'run{run}: expected exactly one raw row')
    row = rows[0]
    summary = json.loads((output / 'sector_summary.json').read_text())
    audit = summary.get('active_yaw_scan_v1_audit') or {}
    checks = {
        'mode_sector': row.get('mode') == 'sector',
        'run_id': row.get('run') == str(run),
        'run_valid': row.get('run_valid') == 'True',
        'resource_valid': row.get('resource_valid') == 'True',
        'no_infrastructure_failure':
            row.get('infrastructure_failure') == 'False',
        'attempt_once': row.get('attempt_count') == '1',
        'no_retry': row.get('retry_count') == '0',
        'active_yaw_runtime_marker': audit.get('valid') is True,
        'active_yaw_expected_enabled':
            audit.get('expected_enabled') == 'true',
        'active_yaw_single_contract_record':
            len(audit.get('records') or []) == 1,
        'source_contracts': all(
            (summary.get('source_acquisition') or {}).get('checks', {}).values()
        ),
    }
    result = {'run': run, 'checks': checks, 'valid': all(checks.values())}
    save(output / 'canonical_active_yaw_verification.json', result)
    if not result['valid']:
        raise RuntimeError(f'run{run}: canonical Active-Yaw audit failed: {checks}')
    return result


def main():
    os.chdir('/root/super-sector-filter')
    lock = open('/tmp/super_sector_filter_gapfree_n5.lock', 'a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    preflight = canonical.verify_default_sector_contract()
    env = {
        key: value for key, value in os.environ.items()
        if not key.startswith('SUPER_')
    }
    completed = []
    started = time.monotonic()
    save(ROOT / 'protocol.json', {
        'campaign': ROOT.name,
        'map': 'urban_blocks_u01',
        'mode': 'Sector (canonical Active-Yaw)',
        'active_yaw_scan': True,
        'empty_scan_heartbeat': True,
        'default_sector': True,
        'run_ids': list(RUNS),
        'repeats': 10,
        'attempts_per_flight': 1,
        'retry': False,
        'replacement_run': False,
        'mission_time_cutoff_s': None,
        'event_terminal': {
            'window_s': 60.0,
            'position_radius_m': 0.02,
            'planner_effect': False,
        },
        'preflight': preflight,
        'status': 'running',
    })
    for index, run in enumerate(RUNS, 1):
        # Revalidate immediately before every flight.  A wrong install or
        # missing marker therefore stops the campaign before launching ROS.
        canonical.verify_default_sector_contract()
        output = ROOT / f'r{index:02d}_run{run}'
        if output.exists():
            raise RuntimeError(f'Existing output refused: {output}')
        current = {
            'index': index,
            'run': run,
            'output': str(output),
            'started_local': datetime.now().astimezone().isoformat(),
        }
        save(ROOT / 'status.json', {
            'state': 'RUNNING', 'current': current,
            'completed': completed, 'elapsed_s': time.monotonic() - started,
        })
        print(f'START {index}/10 run{run}', flush=True)
        with (ROOT / f'r{index:02d}_run{run}.driver.log').open('x') as log:
            result = subprocess.run(
                command(run, output), env=env,
                stdout=log, stderr=subprocess.STDOUT,
            )
        entry = dict(
            current,
            returncode=result.returncode,
            finished_local=datetime.now().astimezone().isoformat(),
        )
        if result.returncode == 0:
            entry['verification'] = verify_flight(output, run)
        completed.append(entry)
        print(f'FINISH {index}/10 run{run} rc={result.returncode}', flush=True)
        save(ROOT / 'status.json', {
            'state': 'RUNNING', 'current': None,
            'completed': completed, 'elapsed_s': time.monotonic() - started,
        })
        if result.returncode != 0:
            save(ROOT / 'status.json', {
                'state': 'STOPPED_INFRASTRUCTURE_FAILURE', 'current': None,
                'completed': completed, 'elapsed_s': time.monotonic() - started,
            })
            return result.returncode
    protocol = json.loads((ROOT / 'protocol.json').read_text())
    protocol['status'] = 'complete'
    protocol['observed_flights'] = len(completed)
    save(ROOT / 'protocol.json', protocol)
    save(ROOT / 'status.json', {
        'state': 'COMPLETE', 'current': None,
        'completed': completed, 'elapsed_s': time.monotonic() - started,
    })
    print('COMPLETE 10/10 scheduled flights', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
