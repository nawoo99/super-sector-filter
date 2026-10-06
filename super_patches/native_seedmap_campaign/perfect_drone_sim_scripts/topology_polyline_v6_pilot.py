#!/usr/bin/env python3
"""Predefined nine-flight smoke, admitted only after all V6 stopped cases pass."""
import argparse
import csv
import json
import math
import os
from pathlib import Path
import signal
import statistics
import subprocess
import time

from audit_forest_stopped_topology_diagnostic import audit
from audit_goal_change_full_refresh_v8 import audit as goal_audit
from scenario7_geometry import sha256

REPO = Path('/root/super-sector-filter')
SOURCE = Path('/root/super_ws/src/SUPER')
INSTALL = Path('/root/super_ws/forest_liveness_trial_v6_20261006/install')
DIAGNOSTICS = REPO / 'results/topology_capture_polyline_20261006'
LAUNCHER = Path(__file__).with_name('run_topology_liveness_v6_trial.sh')
PLANNED = (
    ('forest_full_r01', 'forest_cluster_f01', 99301, ['full']),
    ('forest_sector_adaptive_r01', 'forest_cluster_f01', 99302, ['sector', 'adaptive']),
    ('forest_full_r02', 'forest_cluster_f01', 99303, ['full']),
    ('forest_adaptive_r02', 'forest_cluster_f01', 99304, ['adaptive']),
    ('forest_full_r03', 'forest_cluster_f01', 99305, ['full']),
    ('map1_three_modes', 'gapfree_d1_m01', 99306, ['adaptive', 'full', 'sector']),
)


def number(value):
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError('Invalid/missing metric: ' + str(value))
    return result


def inspect(directory, name, run, modes):
    summary = json.loads((directory / 'summary.json').read_text())
    with (directory / 'raw.csv').open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    results = summary['results']
    if len(rows) != len(results):
        raise ValueError('Summary/raw count disagreement')
    flights = []
    for result, row in zip(results, rows):
        if (result['map'] != name or int(result['run']) != run or
                result['mode'] != row['mode'] or row['attempt_count'] != '1' or
                row['retry_count'] != '0'):
            raise ValueError('Identity/retry disagreement')
        stack = directory / 'artifacts' / f"{name}_run{run}_{result['mode']}.attempt1.stack.log"
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
            and '[TEST_FOREST_TOPOLOGY_STATE]' not in text
            and '[PLANNER_INPUT_CAPTURE]' not in text)
        flights.append(dict(map=name, run=run, mode=result['mode'],
            success=bool(result['success']), contacts=int(result['safety_collisions']),
            quality_valid=quality, time_s=number(result['mission_time_s']),
            cpu_cores=number(result['end_to_end_cpu_cores_mean']),
            cpu_core_s=number(result['end_to_end_cpu_core_s']),
            input_mib_s=number(row['planner_ingress_payload_mib_s']),
            input_mib_run=number(row['map_payload_bytes_total']) / 2**20,
            map_ms=number(result['total_ms_mean']),
            full_transitions=(number(row['filter_effective_full_open_transitions'])
                              if result['mode'] == 'adaptive' else None),
            zone_disconnects=text.count('[TRAJ_GUARD_ZONE_DISCONNECT]'),
            connected_retries=text.count('[TRAJ_GUARD_CONNECTED_RETRY]'),
            exhaustions=text.count('[TRAJ_GUARD_RECOVERY_EXHAUSTED]'),
            polyline_commits=text.count('[TRAJ_GUARD_POLYLINE_RECOVERY]'),
            directory=str(directory), stack_sha256=sha256(stack),
            raw_sha256=sha256(directory / 'raw.csv')))
    return flights, [r['mode'] for r in results] == modes


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--resume-from', type=Path,
                        help='Preserve completed prefix; run only previously unexecuted groups')
    args = parser.parse_args()
    checks = [audit(DIAGNOSTICS / name) for name in ('v6_control', 'v6_available', 'v6_exhausted')]
    if not all(c['criterion_met'] and c['evidence_valid'] for c in checks):
        raise RuntimeError('Stopped-state V6 criteria failed; broad smoke forbidden')
    for name in ('v6_control', 'v6_available', 'v6_exhausted'):
        protocol = json.loads((DIAGNOSTICS / name / 'protocol.json').read_text())
        if protocol['install_root'] != str(INSTALL) or not protocol['polyline_recovery']:
            raise RuntimeError('Wrong diagnostic candidate')
    for key, value in os.environ.items():
        if key.startswith('SUPER_TEST_') and value not in ('', '0'):
            raise RuntimeError('Fault hooks forbidden in pilot')
    if os.environ.get('SUPER_PLANNER_FAILURE_CAPTURE_DIR'):
        raise RuntimeError('Capture forbidden in performance pilot')
    preserved, prefix_count = [], 0
    if args.resume_from:
        original = json.loads((args.resume_from / 'protocol.json').read_text())
        if original['planned'] != [list(row) for row in PLANNED]:
            raise RuntimeError('Prior planned inventory differs')
        for path, expected in original['hashes'].items():
            archive = DIAGNOSTICS / 'source_v6_pilot_v1' / Path(path).name
            if sha256(path) != expected and (not archive.is_file() or sha256(archive) != expected):
                raise RuntimeError('Prior input evidence changed: '+path)
        for directory, name, run, modes in PLANNED:
            previous = args.resume_from / directory
            if not previous.exists():
                break
            group, complete = inspect(previous, name, run, modes)
            if not complete or not all(f['quality_valid'] for f in group):
                raise RuntimeError('Prior incomplete/invalid physical group; no replacement allowed')
            if any(f['mode'] in ('full','adaptive') and (not f['success'] or f['contacts']) for f in group):
                raise RuntimeError('Prior actual reference failure; expansion forbidden')
            preserved.extend(group); prefix_count += 1
        if any((args.resume_from / row[0]).exists() for row in PLANNED[prefix_count:]):
            raise RuntimeError('Existing non-prefix evidence; manual reconciliation required')
    args.output.mkdir(parents=True, exist_ok=False)
    inputs = (Path(__file__), LAUNCHER,
        SOURCE / 'super_planner/src/super_core/certified_polyline_recovery.cpp',
        SOURCE / 'super_planner/src/super_core/astar.cpp',
        SOURCE / 'super_planner/include/path_search/recovery_line_certificate.hpp',
        *(INSTALL / 'perfect_drone_sim/lib/perfect_drone_sim' / n for n in
          ('perfect_drone_full_node', 'perfect_drone_adaptive_node')))
    hashes = {str(path): sha256(path) for path in inputs}
    protocol = dict(schema='certified-polyline-v6-nine-flight-pilot-v1',
        install_root=str(INSTALL), planned=PLANNED, diagnostic_audits=checks, hashes=hashes,
        planned_flights=9, mission_cutoff_s=None, observer_stall_s=60, observer_radius_m=0.02,
        retries=0, capture=False, fault_hooks=False, canonical_promoted=False,
        frozen_c41_replaced=False, safety_profiles_unchanged=True,
        purpose='unequal-count regression smoke, not replacement performance cohort',
        preserved_prefix_directory=str(args.resume_from) if args.resume_from else None,
        preserved_prefix_groups=prefix_count,
        new_planned_flights=sum(len(row[3]) for row in PLANNED[prefix_count:]))
    (args.output / 'protocol.json').write_text(json.dumps(protocol, indent=2)+'\n')
    state = dict(state='RUNNING', pid=os.getpid(), observed_flights=len(preserved),
                 completed_groups=prefix_count, new_physical_flights=0)
    flights, child = list(preserved), None

    def save():
        state['updated_epoch_s'] = time.time()
        (args.output / 'status.json').write_text(json.dumps(state, indent=2)+'\n')
        if not flights:
            return
        with (args.output / 'flights.csv').open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(flights[0]), lineterminator='\n')
            writer.writeheader(); writer.writerows(flights)
        lines = ['# V6: separate, unequal-count nine-flight smoke', '',
            '|Map|Mode|n|Complete|Contact trials|Time (s), complete only|CPU (cores)|CPU (core-s)|Input (MiB/s)|Payload (MiB/run)|Map (ms/frame)|Full transitions, sum|',
            '|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|']
        for name in ('forest_cluster_f01', 'gapfree_d1_m01'):
            for mode in ('full', 'sector', 'adaptive'):
                group = [f for f in flights if f['map'] == name and f['mode'] == mode]
                if not group:
                    continue
                complete = [f['time_s'] for f in group if f['success']]
                values = [statistics.mean(f[k] for f in group) for k in
                          ('cpu_cores', 'cpu_core_s', 'input_mib_s', 'input_mib_run', 'map_ms')]
                lines.append('|'+ '|'.join([name, mode, str(len(group)),
                    f"{sum(f['success'] for f in group)}/{len(group)}",
                    f"{sum(f['contacts'] > 0 for f in group)}/{len(group)}",
                    f'{statistics.mean(complete):.2f}' if complete else 'NA',
                    *(f'{v:.3f}' for v in values),
                    (str(int(sum(f['full_transitions'] for f in group)))
                     if mode == 'adaptive' else 'NA')])+'|')
        (args.output / 'summary_by_map.md').write_text('\n'.join(lines)+'\n')

    def interrupt(signum, frame):
        raise InterruptedError('Pilot interrupted: '+str(signum))
    signal.signal(signal.SIGINT, interrupt)
    signal.signal(signal.SIGTERM, interrupt)
    try:
        for directory, name, run, modes in PLANNED[prefix_count:]:
            if any(sha256(path) != expected for path, expected in hashes.items()):
                raise RuntimeError('Candidate drift')
            state['current'] = directory; save()
            output = args.output / directory
            with output.with_suffix('.controller.log').open('x') as stream:
                child = subprocess.Popen(['bash', str(LAUNCHER), str(output), name,
                    str(run), *modes], cwd=REPO, stdout=stream, stderr=subprocess.STDOUT,
                    start_new_session=True)
                state['child_pid'] = child.pid; save()
                rc = child.wait()
            group, complete = inspect(output, name, run, modes)
            flights.extend(group); state['observed_flights'] = len(flights)
            state['new_physical_flights'] = len(flights)-len(preserved)
            state['completed_groups'] += int(complete); save()
            if rc or not complete or not all(f['quality_valid'] for f in group):
                raise RuntimeError('Runtime/evidence gate failure; retained without retry')
            if any(f['mode'] in ('full', 'adaptive') and
                   (not f['success'] or f['contacts']) for f in group):
                raise RuntimeError('Actual Full/Adaptive failure; retained without replacement')
        state.update(state='COMPLETE', all_quality_valid=True,
            safe_complete=sum(f['success'] and f['contacts'] == 0 for f in flights))
        save(); return 0
    except Exception as error:
        if child and child.poll() is None:
            os.killpg(child.pid, signal.SIGINT)
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGTERM); child.wait(timeout=5)
        state.update(state='STOPPED_FOR_DIAGNOSIS', error=str(error)); save()
        print(json.dumps(state), flush=True); return 1


if __name__ == '__main__':
    raise SystemExit(main())
