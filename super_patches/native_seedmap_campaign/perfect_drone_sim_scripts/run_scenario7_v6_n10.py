#!/usr/bin/env python3
"""Run the frozen c31 seven-map triplet campaign in two five-run stages."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import statistics
import subprocess
import sys
import time


REPO = Path('/root/super-sector-filter')
SOURCE = Path('/root/super_ws/src/SUPER')
WRAPPER = SOURCE / 'mars_uav_sim/perfect_drone_sim/scripts/scenario7_guard_v6_cpu_compare.py'
PROTOCOL_NAME = 'protocol.json'
CANDIDATE = 'c31_goal_change_full_refresh_v6_n10'
MAPS = (
    'gapfree_d1_m01', 'gapfree_d1_m02', 'gapfree_d1_m03',
    'gapfree_d1_m04', 'gapfree_d1_m05r2',
    'urban_blocks_u01', 'forest_cluster_f01',
)
MODES = ('full', 'sector', 'adaptive')
ORDERS = (
    ('full', 'sector', 'adaptive'),
    ('sector', 'adaptive', 'full'),
    ('adaptive', 'full', 'sector'),
)
BASE_RUN = 82000
COMMON = (
    '--mean-cpu-reduction-target-pct', '30', '--compose',
    '--skip-backup-diagnostic-replay', '--skip-unobserved-path-publication',
    '--fast-occupied-box-scan', '--snapshot-line-query', '--snapshot-neighbor-cache',
    '--side-executor-threads', '3', '--monitor-intervals', '--guarded-demand-replan',
    '--goal-retransmit-identity', '--headless-parameter-services',
    '--dedicated-static-pc-executor', '--no-optimizer-phase-memory-trace',
    '--optimizer-clearance-gate-first', '--event-body-heading',
    '--mission-time-as-metric', '--sector-outcomes-as-metrics',
    '--async-certified-recovery', '--profile-cpu',
)


def atomic_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    temporary.replace(path)


def truth(value) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value.lower() == 'true':
            return True
        if value.lower() == 'false':
            return False
    return None


def number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def schedule(root: Path):
    rows = []
    for repeat in range(1, 11):
        stage = 'stage1' if repeat <= 5 else 'stage2'
        shift = (repeat - 1) % len(MAPS)
        map_order = MAPS[shift:] + MAPS[:shift]
        for name in map_order:
            index = MAPS.index(name)
            run = BASE_RUN + repeat * 10 + index
            order = ORDERS[(repeat + index - 1) % len(ORDERS)]
            output = root / stage / name / f'r{repeat:02d}_run{run}'
            rows.append(dict(stage=stage, repeat=repeat, map=name, run=run,
                             modes=list(order), output=str(output)))
    return rows


def command(item):
    return [sys.executable, '-u', str(WRAPPER), '--candidate', CANDIDATE,
            *COMMON, '--map', item['map'], '--run', str(item['run']),
            '--output', item['output'], '--modes', *item['modes']]


def log_counts(stack: str):
    return dict(
        enabled_true=len(re.findall(r'\[GOAL_CHANGE_FULL_REFRESH_V6\][^\r\n]*enabled=true', stack)),
        enabled_false=len(re.findall(r'\[GOAL_CHANGE_FULL_REFRESH_V6\][^\r\n]*enabled=false', stack)),
        requests=len(re.findall(r'\[GOAL_CHANGE_FULL_REFRESH_REQUEST\]', stack)),
        distinct_goals=len(re.findall(
            r'\[MISSION_GOAL_IDENTITY\][^\r\n]*new_intent=1 new_identity=1', stack)),
        path_ready=len(re.findall(r'\[EVENT_RECOVERY_PATH_READY\]', stack)),
        astar_timeouts=len(re.findall(r'Astar search timeout', stack)),
    )


def validate_triplet(item):
    root = Path(item['output'])
    raw = root / 'raw.csv'
    errors = []
    if not raw.is_file():
        return dict(valid=False, blocking=True, errors=['missing raw.csv'], outcomes={})
    with raw.open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    by_mode = {row.get('mode'): row for row in rows}
    if len(rows) != 3 or set(by_mode) != set(MODES):
        errors.append('expected exactly one row per mode')
    outcomes = {}
    for mode in MODES:
        row = by_mode.get(mode, {})
        stack_path = root / 'artifacts' / f"{item['map']}_run{item['run']}_{mode}.attempt1.stack.log"
        stack = stack_path.read_text(errors='replace') if stack_path.is_file() else ''
        counts = log_counts(stack)
        common_ok = (
            truth(row.get('run_valid')) is True and
            truth(row.get('resource_valid')) is True and
            truth(row.get('speed_limit_valid')) is True and
            truth(row.get('infrastructure_failure')) is False and
            number(row.get('attempt_count')) == 1 and
            number(row.get('retry_count')) == 0
        )
        expected_true = mode == 'adaptive'
        source_ok = (counts['enabled_true'] == (1 if expected_true else 0) and
                     counts['enabled_false'] == (0 if expected_true else 1) and
                     counts['requests'] == (4 if expected_true else 0))
        success = truth(row.get('success')) is True
        contacts = number(row.get('safety_collisions'))
        complete = (row.get('waypoints_reached') == row.get('n_waypoints') and
                    number(row.get('n_waypoints')) == 5)
        safe_complete = common_ok and success and complete and contacts == 0
        outcomes[mode] = dict(
            common_valid=common_ok, source_valid=source_ok,
            success=success, complete=complete, safety_collisions=contacts,
            mission_time_s=number(row.get('mission_time_s')),
            body_clearance_m=number(row.get('static_pcd_clearance_m')),
            end_to_end_cpu_cores_mean=number(row.get('end_to_end_cpu_cores_mean')),
            end_to_end_cpu_core_s=number(row.get('end_to_end_cpu_core_s')),
            map_payload_mib_s=number(row.get('map_payload_mib_s')),
            map_update_ms_mean=number(row.get('total_ms_mean')),
            full_open_transitions=number(row.get('filter_trajectory_guard_open_transitions')),
            full_close_transitions=number(row.get('filter_trajectory_guard_close_transitions')),
            full_refresh_acks=number(row.get('filter_full_refresh_request_count')),
            log_counts=counts,
        )
        if not common_ok:
            errors.append(mode + ': run/resource/speed/infrastructure validity failed')
        if not source_ok:
            errors.append(mode + ': v6 source-scope audit failed')
        if mode in ('full', 'adaptive') and not safe_complete:
            errors.append(mode + ': required safe completion failed')
    result = dict(valid=not errors, blocking=bool(errors), errors=errors,
                  map=item['map'], run=item['run'], repeat=item['repeat'],
                  stage=item['stage'], mode_order=item['modes'], outcomes=outcomes)
    atomic_json(root / 'v6_triplet_validation.json', result)
    return result


def all_validations(root: Path):
    result = []
    for path in sorted(root.glob('stage*/*/r*_run*/v6_triplet_validation.json')):
        result.append(json.loads(path.read_text()))
    return result


def metric(values, key):
    numbers = [value for row in values if (value := row.get(key)) is not None]
    return dict(n=len(numbers), mean=statistics.mean(numbers) if numbers else None,
                sd=statistics.stdev(numbers) if len(numbers) > 1 else None)


def write_progress(root: Path):
    validations = all_validations(root)
    csv_rows = []
    for name in MAPS:
        for mode in MODES:
            values = [v['outcomes'][mode] for v in validations if v['map'] == name]
            row = dict(map=name, mode=mode, planned=10, recorded=len(values),
                       completed=sum(v['success'] and v['complete'] for v in values),
                       contact_runs=sum((v['safety_collisions'] or 0) > 0 for v in values),
                       contact_episodes=sum((v['safety_collisions'] or 0) for v in values),
                       valid_runs=sum(v['common_valid'] and v['source_valid'] for v in values))
            for label, key in (
                ('mission_time_s', 'mission_time_s'), ('cpu_cores', 'end_to_end_cpu_cores_mean'),
                ('cpu_core_s', 'end_to_end_cpu_core_s'), ('input_mib_s', 'map_payload_mib_s'),
                ('map_ms', 'map_update_ms_mean'), ('full_open', 'full_open_transitions')):
                stats = metric(values, key)
                row.update({label + '_n': stats['n'], label + '_mean': stats['mean'],
                            label + '_sd': stats['sd']})
            csv_rows.append(row)
    csv_path = root / 'summary_by_map.csv'
    with csv_path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(csv_rows[0]), lineterminator='\n')
        writer.writeheader(); writer.writerows(csv_rows)
    lines = ['# Scenario7 v6 n10 progress', '',
             '| Map | Mode | Recorded/10 | Complete | Contact runs | Contacts | CPU cores | Input MiB/s | Map ms | Full opens |',
             '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    fmt = lambda value, digits=3: 'N/A' if value is None else f'{value:.{digits}f}'
    for row in csv_rows:
        lines.append(f"| {row['map']} | {row['mode']} | {row['recorded']}/10 | {row['completed']} | "
                     f"{row['contact_runs']} | {fmt(row['contact_episodes'],0)} | {fmt(row['cpu_cores_mean'])} | "
                     f"{fmt(row['input_mib_s_mean'])} | {fmt(row['map_ms_mean'])} | {fmt(row['full_open_mean'],2)} |")
    (root / 'summary_by_map.md').write_text('\n'.join(lines) + '\n')
    return validations


def stage_gate(root: Path, stage: str):
    rows = [row for row in all_validations(root) if row['stage'] == stage]
    expected = 5 * len(MAPS)
    valid = len(rows) == expected and all(row['valid'] for row in rows)
    result = dict(stage=stage, expected_triplets=expected, observed_triplets=len(rows),
                  valid=valid, blocking_failures=[row for row in rows if not row['valid']])
    atomic_json(root / (stage + '_gate.json'), result)
    return result


def frozen_identity(root: Path):
    paths = [WRAPPER,
             SOURCE / 'super_planner/include/fsm/fsm.h',
             SOURCE / 'super_planner/src/super_core/fsm.cpp',
             SOURCE / 'super_planner/include/ros_interface/ros2/fsm_ros2.hpp',
             Path(__file__).resolve(), root / PROTOCOL_NAME]
    for name in MAPS:
        paths.extend((SOURCE / f'mars_uav_sim/perfect_drone_sim/config/{name}.yaml',
                      SOURCE / f'mars_uav_sim/perfect_drone_sim/pcd/seed_maps/{name}.pcd'))
    return {str(path): sha256(path) for path in paths}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args(argv)
    root = args.output.resolve()
    protocol = root / PROTOCOL_NAME
    if not protocol.is_file():
        parser.error('A committed protocol.json must exist before flight')
    plan = schedule(root)
    if args.dry_run:
        print(json.dumps(dict(candidate=CANDIDATE, triplets=len(plan), flights=3*len(plan),
                              stage1_triplets=35, stage2_triplets=35,
                              first=plan[0], last=plan[-1]), indent=2))
        return 0
    lock = open('/tmp/super_sector_filter_scenario7_v6_n10.lock', 'a')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        parser.error('Another v6 n10 campaign is running')
    if (root / 'status.json').exists():
        parser.error('Existing campaign status refused; no implicit resume or overwrite')
    started = time.monotonic()
    frozen = frozen_identity(root)
    atomic_json(root / 'frozen_identity.json', frozen)
    atomic_json(root / 'plan.json', dict(schema='scenario7-v6-n10-two-stage-v1',
                candidate=CANDIDATE, maps=MAPS, modes=MODES, base_run=BASE_RUN,
                no_retry=True, no_replacement=True, stage1_repeats=[1,2,3,4,5],
                stage2_repeats=[6,7,8,9,10], commands=plan, frozen_sha256=frozen))
    completed = []
    current = None
    def status(state, **extra):
        atomic_json(root / 'status.json', dict(state=state, pid=os.getpid(), current=current,
                    completed=completed, elapsed_s=time.monotonic()-started,
                    updated_local=datetime.now().astimezone().isoformat(), **extra))
    def interrupted(signum, _frame):
        raise InterruptedError('signal ' + str(signum))
    handlers = {sig: signal.signal(sig, interrupted) for sig in (signal.SIGINT, signal.SIGTERM)}
    env = {key: value for key, value in os.environ.items() if not key.startswith('SUPER_')}
    env['PYTHONNOUSERSITE'] = '1'
    controller = (root / 'controller.log').open('a', buffering=1)
    try:
        status('RUNNING_STAGE1')
        for item in plan:
            if item['stage'] == 'stage2' and not (root / 'stage1_gate.json').is_file():
                gate = stage_gate(root, 'stage1')
                if not gate['valid']:
                    raise RuntimeError('stage1 gate failed; stage2 not started')
                status('RUNNING_STAGE2', stage1_gate=gate)
            if frozen_identity(root) != frozen:
                raise RuntimeError('frozen input changed')
            current = {key: value for key, value in item.items() if key != 'output'} | {'output': item['output']}
            status('RUNNING_' + item['stage'].upper())
            print('START', item['stage'], item['map'], item['repeat'], item['run'], flush=True)
            Path(item['output']).parent.mkdir(parents=True, exist_ok=True)
            child_log = Path(item['output']).parent / (Path(item['output']).name + '.controller.log')
            with child_log.open('x', buffering=1) as child_stream:
                process = subprocess.Popen(command(item), cwd=REPO, env=env,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
                assert process.stdout is not None
                for line in process.stdout:
                    child_stream.write(line); controller.write(line)
                    if line.startswith('[native_campaign') or line.startswith('RESULT ') or line.startswith('COMPARISON '):
                        print(line, end='', flush=True)
                returncode = process.wait()
            validation = validate_triplet(item)
            entry = dict(stage=item['stage'], map=item['map'], repeat=item['repeat'],
                         run=item['run'], returncode=returncode, valid=validation['valid'],
                         errors=validation['errors'])
            completed.append(entry)
            write_progress(root)
            print('FINISH', json.dumps(entry), flush=True)
            if returncode != 0 or not validation['valid']:
                raise RuntimeError('blocking triplet failure: ' + repr(entry))
        gate2 = stage_gate(root, 'stage2')
        if not gate2['valid']:
            raise RuntimeError('stage2 gate failed')
        validations = write_progress(root)
        status('COMPLETE', stage1_gate=json.loads((root/'stage1_gate.json').read_text()),
               stage2_gate=gate2, recorded_triplets=len(validations), recorded_flights=3*len(validations))
        print('FINISHED:', root / 'summary_by_map.md', flush=True)
        return 0
    except BaseException as exc:
        write_progress(root)
        status('STOPPED_FOR_DIAGNOSIS', error=repr(exc))
        print('STOPPED:', repr(exc), file=sys.stderr, flush=True)
        raise
    finally:
        for sig, handler in handlers.items():
            signal.signal(sig, handler)
        controller.close(); lock.close()


if __name__ == '__main__':
    raise SystemExit(main())
