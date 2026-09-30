#!/usr/bin/env python3
"""Urban legacy Fixed Sector n=10 without a mission-time cutoff or retry."""
from datetime import datetime
import csv
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parent
CHILD = ROOT / 'run_no_timeout_child.py'
REFERENCE_PLAN = Path(
    '/root/super-sector-filter/results/'
    'scenario7_velocity_centered_v12_n10_20260928/stage1/'
    'urban_blocks_u01/r01_run92115/plan.json'
)
RUNS = tuple(range(94401, 94411))
CRITICAL_ASSET_MARKERS = (
    'urban_blocks_u01',
    'urban_building_corners_v3',
    'static_seedmaps_guard_viability_tight_v7_filtered_reliable_nearhit_v3.yaml',
)


def save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=True) + '\n')
    temporary.replace(path)


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def verify_frozen_assets():
    plan = json.loads(REFERENCE_PLAN.read_text())
    expected = plan['scenario7_repair_runtime']['assets_sha256']
    selected = dict(expected)
    for raw_path, digest in plan['asset_sha256'].items():
        if any(marker in raw_path for marker in CRITICAL_ASSET_MARKERS):
            selected[raw_path] = digest
    failures = []
    for raw_path, expected_digest in selected.items():
        path = Path(raw_path)
        if not path.is_file():
            failures.append({'path': raw_path, 'reason': 'missing'})
            continue
        actual_digest = sha256(path)
        if actual_digest != expected_digest:
            failures.append({
                'path': raw_path,
                'reason': 'sha256_mismatch',
                'expected': expected_digest,
                'actual': actual_digest,
            })
    result = {
        'reference_plan': str(REFERENCE_PLAN),
        'checked_files': len(selected),
        'failures': failures,
        'passed': not failures,
    }
    save(ROOT / 'frozen_asset_verification.json', result)
    if failures:
        raise RuntimeError('Frozen v12 asset verification failed')
    return result


def verify_existing_flight(output, run):
    """Admit a flown row only when its independent evidence is complete.

    Run 94401 completed before a post-flight summary opened a valid relative
    artifact path from the wrong working directory. Re-flying would be a retry,
    so preserve the original observation after strict evidence checks instead.
    """
    raw_path = output / 'raw.csv'
    if not raw_path.is_file():
        return None
    with raw_path.open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 1:
        raise RuntimeError(f'Existing output has {len(rows)} rows: {output}')
    row = rows[0]
    expected = {
        'map': 'urban_blocks_u01',
        'mode': 'sector',
        'run': str(run),
        'run_valid': 'True',
        'resource_valid': 'True',
        'infrastructure_failure': 'False',
        'perf_window_valid': 'True',
        'speed_limit_valid': 'True',
    }
    mismatches = {
        key: {'expected': value, 'actual': row.get(key)}
        for key, value in expected.items() if row.get(key) != value
    }
    monitor_path = output / 'artifacts' / (
        f'urban_blocks_u01_run{run}_sector.attempt1.json'
    )
    audit_path = output / 'artifacts' / (
        f'urban_blocks_u01_run{run}_sector.attempt1.solid_audit.json'
    )
    performance_path = Path('/root/super-sector-filter') / row['perf_trace_csv']
    monitor = json.loads(monitor_path.read_text())
    audit = json.loads(audit_path.read_text())
    checks = {
        'row_fields_match': not mismatches,
        'monitor_success_matches_row':
            bool(monitor.get('success')) == (row.get('success') == 'True'),
        'monitor_contact_matches_row':
            int(monitor.get('safety_collisions', -1))
            == int(row.get('safety_collisions', -2)),
        'solid_audit_complete': audit.get('completion') is True,
        'solid_audit_valid': audit.get('audit_valid') is True,
        'solid_audit_success_matches_row':
            bool(audit.get('success')) == (row.get('success') == 'True'),
        'solid_audit_contact_matches_row':
            int(audit.get('contact_episodes', -1))
            == int(row.get('safety_collisions', -2)),
        'performance_trace_present': performance_path.is_file(),
    }
    result = {
        'run': run,
        'output': str(output),
        'checks': checks,
        'row_mismatches': mismatches,
        'accepted': all(checks.values()) and not mismatches,
        'reason':
            'original flight preserved after cwd-only post-flight summary failure',
    }
    save(output / 'existing_flight_verification.json', result)
    if not result['accepted']:
        raise RuntimeError(f'Existing flight evidence rejected: {output}')
    return result


def command(run, output):
    return [
        sys.executable, str(CHILD),
        '--output', str(output), '--run', str(run),
        '--candidate', 'v12_urban_fixed_sector_no_mission_timeout_n10',
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


def main():
    os.chdir('/root/super-sector-filter')
    lock = open('/tmp/super_sector_filter_gapfree_n5.lock', 'a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    verification = verify_frozen_assets()
    env = {
        key: value for key, value in os.environ.items()
        if not key.startswith('SUPER_')
    }
    completed = []
    started = time.monotonic()
    save(ROOT / 'protocol.json', {
        'campaign': ROOT.name,
        'reference_campaign':
            'scenario7_velocity_centered_v12_n10_20260928',
        'replacement_scope': 'urban_blocks_u01 / sector only',
        'map': 'urban_blocks_u01',
        'mode': 'Fixed Sector (legacy body-forward +/-45 deg)',
        'active_yaw_scan': False,
        'run_ids': list(RUNS),
        'repeats': 10,
        'attempts_per_flight': 1,
        'retry': False,
        'replacement_run': False,
        'mission_time_cutoff_s': None,
        'event_terminal': {
            'kind': 'persistent stationary state at one unreached waypoint',
            'window_s': 60.0,
            'position_radius_m': 0.02,
            'contact_classification':
                'persistent_contact_stall when exact solid clearance <= 0 '
                'throughout the stationary window; otherwise '
                'persistent_no_progress_stall',
            'planner_effect': False,
        },
        'monitor_encoding':
            'positive infinity; mission completion remains the flight terminal condition',
        'resource_and_process_integrity_guards': True,
        'frozen_asset_verification': verification,
        'analysis_warning':
            'This no-timeout Sector cohort is not timeout-matched to the retained '
            'v12 Full and Adaptive cohorts, which used a 180 s mission cutoff.',
        'existing_flight_policy':
            'Never re-fly a completed observation after a post-flight-only '
            'infrastructure failure; admit it only after raw/monitor/solid-audit/'
            'performance evidence checks all pass.',
        'status': 'running',
    })
    for index, run in enumerate(RUNS, 1):
        output = ROOT / f'r{index:02d}_run{run}'
        if output.exists():
            verification = verify_existing_flight(output, run)
            entry = {
                'index': index,
                'run': run,
                'output': str(output),
                'returncode': 0,
                'preserved_existing_flight': True,
                'verification': verification,
            }
            completed.append(entry)
            print(
                f'PRESERVE {index}/10 run{run}: verified completed flight',
                flush=True,
            )
            save(ROOT / 'status.json', {
                'state': 'RUNNING',
                'current': None,
                'completed': completed,
                'elapsed_s': time.monotonic() - started,
            })
            continue
        current = {
            'index': index,
            'run': run,
            'output': str(output),
            'started_local': datetime.now().astimezone().isoformat(),
        }
        save(ROOT / 'status.json', {
            'state': 'RUNNING',
            'current': current,
            'completed': completed,
            'elapsed_s': time.monotonic() - started,
        })
        print(f'START {index}/10 run{run}', flush=True)
        with (ROOT / f'r{index:02d}_run{run}.driver.log').open('x') as log:
            result = subprocess.run(
                command(run, output),
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
        entry = dict(
            current,
            returncode=result.returncode,
            finished_local=datetime.now().astimezone().isoformat(),
        )
        completed.append(entry)
        print(f'FINISH {index}/10 run{run} rc={result.returncode}', flush=True)
        save(ROOT / 'status.json', {
            'state': 'RUNNING',
            'current': None,
            'completed': completed,
            'elapsed_s': time.monotonic() - started,
        })
        if result.returncode != 0:
            save(ROOT / 'status.json', {
                'state': 'STOPPED_INFRASTRUCTURE_FAILURE',
                'current': None,
                'completed': completed,
                'elapsed_s': time.monotonic() - started,
            })
            return result.returncode
    protocol = json.loads((ROOT / 'protocol.json').read_text())
    protocol['status'] = 'complete'
    protocol['observed_flights'] = len(completed)
    save(ROOT / 'protocol.json', protocol)
    save(ROOT / 'status.json', {
        'state': 'COMPLETE',
        'current': None,
        'completed': completed,
        'elapsed_s': time.monotonic() - started,
    })
    print('COMPLETE 10/10 scheduled flights', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
