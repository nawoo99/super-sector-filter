#!/usr/bin/env python3
"""Gated, append-preserving Forest n10 then fresh seven-map n10 candidate trial."""
import argparse
import csv
import json
import math
import os
from pathlib import Path
import signal
import statistics
import subprocess
import sys
import time

sys.path.insert(0, '/root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/scripts')

from audit_forest_stopped_topology_diagnostic import audit
from audit_goal_change_full_refresh_v8 import audit as goal_audit
from scenario7_geometry import sha256


REPO = Path('/root/super-sector-filter')
SOURCE = Path('/root/super_ws/src/SUPER')
INSTALL = Path('/root/super_ws/forest_liveness_trial_v4_20261006/install')
DIAGNOSTICS = REPO / 'results/topology_stopped_diagnostic_20261006'
LAUNCHER = SOURCE / 'mars_uav_sim/perfect_drone_sim/scripts/run_topology_liveness_v4_trial.sh'
MAPS = tuple(f'gapfree_d1_m{i:02d}' for i in range(1, 5)) + (
    'gapfree_d1_m05r2', 'urban_blocks_u01', 'forest_cluster_f01')
MODES = ('full', 'sector', 'adaptive')
LABELS = dict(zip(MAPS, ('Map1', 'Map2', 'Map3', 'Map4', 'Map5', 'Urban', 'Forest')))


def numeric(value):
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError('Missing/negative/nonfinite metric: ' + str(value))
    return number


def inspect_flights(directory, planned):
    summary = json.loads((directory / 'summary.json').read_text())
    plan = json.loads((directory / 'plan.json').read_text())
    with (directory / 'raw.csv').open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    results = summary['results']
    if len(rows) != 3 or [r['mode'] for r in results] != planned['modes']:
        raise ValueError('Incomplete three-mode group')
    flights = []
    for result, row in zip(results, rows):
        if (result['map'] != planned['map'] or int(result['run']) != planned['run']
                or row['mode'] != result['mode'] or row['attempt_count'] != '1'
                or row['retry_count'] != '0'):
            raise ValueError('Flight identity/attempt mismatch')
        stack = directory / 'artifacts' / (
            f"{planned['map']}_run{planned['run']}_{result['mode']}.attempt1.stack.log")
        text = stack.read_text(errors='replace')
        solid = result['solid_obstacle_audit']
        quality = (all(result[k] is True for k in ('run_valid', 'resource_valid', 'speed_limit_valid'))
            and all(value is True for value in result['source_acquisition']['checks'].values())
            and result['strict_recovery_audit']['valid'] is True
            and solid['audit_valid'] is True
            and solid['coverage']['all_received_samples_recorded'] is True
            and solid['contact_episodes'] == result['safety_collisions']
            and solid['completion'] == result['success']
            and goal_audit(text, result['mode'])['valid'] is True
            and '[TEST_FOREST_TOPOLOGY_STATE]' not in text)
        flight = dict(stage=planned['stage'], map=result['map'], mode=result['mode'],
            run=result['run'], success=bool(result['success']), contacts=int(result['safety_collisions']),
            quality_valid=quality, time_s=numeric(result['mission_time_s']),
            cpu_cores=numeric(result['end_to_end_cpu_cores_mean']),
            cpu_core_s=numeric(result['end_to_end_cpu_core_s']),
            input_mib_s=numeric(row['planner_ingress_payload_mib_s']),
            input_mib_run=numeric(row['map_payload_bytes_total']) / 2**20,
            map_ms=numeric(result['total_ms_mean']),
            full_transitions=numeric(row['filter_effective_full_open_transitions'] or 0),
            zone_disconnects=text.count('[TRAJ_GUARD_ZONE_DISCONNECT]'),
            connected_retries=text.count('[TRAJ_GUARD_CONNECTED_RETRY]'),
            exhaustions=text.count('[TRAJ_GUARD_RECOVERY_EXHAUSTED]'),
            stack_sha256=sha256(stack), raw_sha256=sha256(directory / 'raw.csv'))
        flights.append(flight)
    return flights, plan['asset_sha256']


def save_tables(root, flights):
    if not flights:
        return
    with (root / 'flights.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(flights[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(flights)
    lines = ['# V4 candidate: observed results, not a promoted baseline', '',
        'Forest pilot and common seven-map campaign are separate cohorts. Failed runs are retained.', '',
        '|Stage|Map|Mode|n|Complete|Contact trials|Time, complete only (s)|CPU (cores)|CPU (core-s)|Input (MiB/s)|Payload (MiB/run)|Map (ms/frame)|Full transitions, sum|',
        '|---|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for stage in ('forest_n10', 'seven_map_n10'):
        for name in MAPS:
            for mode in MODES:
                group = [f for f in flights if f['stage'] == stage and f['map'] == name and f['mode'] == mode]
                if not group:
                    continue
                completed = [f['time_s'] for f in group if f['success']]
                values = [statistics.mean(f[k] for f in group) for k in (
                    'cpu_cores', 'cpu_core_s', 'input_mib_s', 'input_mib_run', 'map_ms')]
                lines.append('|'+ '|'.join([stage, LABELS[name], mode, str(len(group)),
                    f"{sum(f['success'] for f in group)}/{len(group)}",
                    f"{sum(f['contacts'] > 0 for f in group)}/{len(group)}",
                    f'{statistics.mean(completed):.2f}' if completed else 'NA',
                    *(f'{v:.3f}' for v in values),
                    str(int(sum(f['full_transitions'] for f in group)))])+'|')
    (root / 'summary_by_map.md').write_text('\n'.join(lines)+'\n')


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    checks = [audit(DIAGNOSTICS / name) for name in ('v4_control', 'v4_available', 'v4_exhausted')]
    if not all(check['criterion_met'] and check['evidence_valid'] for check in checks):
        raise RuntimeError('V4 targeted recovery did not pass; broad regression forbidden')
    for name in ('v4_available', 'v4_exhausted'):
        protocol = json.loads((DIAGNOSTICS / name / 'protocol.json').read_text())
        if protocol['install_root'] != str(INSTALL) or not protocol['expect_connected_recovery']:
            raise RuntimeError('Wrong candidate/primary-goal recovery protocol')
    args.output.mkdir(parents=True, exist_ok=False)
    planned = []
    for repeat in range(1, 11):
        modes = list(MODES[(repeat-1)%3:] + MODES[:(repeat-1)%3])
        planned.append(dict(stage='forest_n10', map='forest_cluster_f01', run=99100+repeat,
            repeat=repeat, modes=modes, directory=f'forest_n10/r{repeat:02d}'))
    for repeat in range(1, 11):
        for index, name in enumerate(MAPS):
            rotation = (repeat-1+index)%3
            planned.append(dict(stage='seven_map_n10', map=name, run=99200+(repeat-1)*7+index+1,
                repeat=repeat, modes=list(MODES[rotation:] + MODES[:rotation]),
                directory=f'seven_map_n10/{name}/r{repeat:02d}'))
    inputs = (Path(__file__).resolve(), LAUNCHER,
        SOURCE / 'super_planner/src/super_core/super_planner.cpp',
        SOURCE / 'super_planner/include/super_core/super_planner.h',
        *(INSTALL / 'perfect_drone_sim/lib/perfect_drone_sim' / name for name in (
            'perfect_drone_full_node', 'perfect_drone_adaptive_node')))
    hashes = {str(path): sha256(path) for path in inputs}
    protocol = dict(schema='topology-liveness-v4-campaign-v1', install_root=str(INSTALL),
        repetitions_per_map_per_mode=10, forest_flights=30, common_seven_map_flights=210,
        total_planned_physical_flights=240, planned=planned, hashes=hashes,
        diagnostic_audits=checks, global_mission_cutoff_s=None,
        terminal_no_progress_s=60, terminal_no_progress_radius_m=0.02,
        no_automatic_retry_or_result_replacement=True, canonical_baseline_promoted=False,
        stop_after_any_full_adaptive_failure=True, sector_failures_retained_as_metrics=True,
        mode_order='predefined cyclic rotation', frozen_c41_replaced=False)
    (args.output / 'protocol.json').write_text(json.dumps(protocol, indent=2)+'\n')
    state = dict(schema=protocol['schema'], pid=os.getpid(), started_epoch_s=time.time(),
                 state='RUNNING', groups_completed=0, observed_flights=0, total_planned=240)
    flights, common_hashes = [], {}
    child = None

    def status():
        state['updated_epoch_s'] = time.time()
        (args.output / 'status.json').write_text(json.dumps(state, indent=2)+'\n')
        save_tables(args.output, flights)

    def interrupted(signum, frame):
        raise InterruptedError(f'Controller signal {signum}')

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        for planned_run in planned:
            if not all(sha256(path) == expected for path, expected in hashes.items()):
                raise RuntimeError('Candidate inputs changed during campaign')
            state['current'] = planned_run
            status()
            directory = args.output / planned_run['directory']
            directory.parent.mkdir(parents=True, exist_ok=True)
            with directory.with_suffix('.controller.log').open('x') as stream:
                child = subprocess.Popen(['bash', str(LAUNCHER), str(directory), planned_run['map'],
                    str(planned_run['run']), *planned_run['modes']], cwd=REPO,
                    stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
                state['child_pid'] = child.pid
                status()
                returncode = child.wait()
            group, assets = inspect_flights(directory, planned_run)
            flights.extend(group)
            state['observed_flights'] = len(flights)
            for path, expected in assets.items():
                if common_hashes.get(path, expected) != expected:
                    raise RuntimeError('Campaign input drift: '+path)
                common_hashes[path] = expected
            state['groups_completed'] += 1
            status()
            if returncode or not all(f['quality_valid'] for f in group):
                raise RuntimeError('Child/runtime/evidence gate failure; inspect retained group')
            failures = [f for f in group if f['mode'] in ('full', 'adaptive')
                        and (not f['success'] or f['contacts'])]
            if failures:
                state['failed_flights'] = failures
                raise RuntimeError('Actual Full/Adaptive failure; no replacement or further flight')
            if state['groups_completed'] == 10:
                state['forest_gate_passed'] = True
                status()
        state['state'] = 'COMPLETE'
        state['completed_epoch_s'] = time.time()
        status()
        return 0
    except Exception as error:
        if child and child.poll() is None:
            os.killpg(child.pid, signal.SIGINT)
            try:
                child.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGTERM)
                child.wait(timeout=5)
        state.update(state='STOPPED_FOR_DIAGNOSIS', error=str(error))
        status()
        print(json.dumps(state), flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
