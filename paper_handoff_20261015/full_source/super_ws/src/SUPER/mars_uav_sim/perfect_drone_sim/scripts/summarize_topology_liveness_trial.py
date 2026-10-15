#!/usr/bin/env python3
"""Audit every predefined v2 smoke outcome and retain the rejected v1 pilot.

Generated CSV/JSON are derived evidence, never replacements for raw flights.
"""
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path('/root/super-sector-filter/results/topology_liveness_trial_20261006')
SOURCE = Path('/root/super_ws/src/SUPER')
sys.path.insert(0, str(SOURCE / 'mars_uav_sim/perfect_drone_sim/scripts'))
from audit_goal_change_full_refresh_v8 import audit as audit_goal_refresh


def sha256(path):
    with path.open('rb') as stream:
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    protocol = json.loads((ROOT / 'protocol_v2.json').read_text())
    build = json.loads((ROOT / 'validation_v2.json').read_text())
    install = Path(protocol['install_root'])
    for name, expected in build['sha256'].items():
        path = (SOURCE / name if '/' in name else
                install / 'perfect_drone_sim/lib/perfect_drone_sim' / name)
        assert sha256(path) == expected, f'Candidate changed: {path}'
    flights = []
    common_hashes = {}
    for planned in protocol['planned_runs']:
        directory = ROOT / planned['directory']
        status = json.loads((directory / 'status.json').read_text())
        assert status['state'] == 'COMPLETE', (directory, status)
        summary = json.loads((directory / 'summary.json').read_text())
        assert [r['mode'] for r in summary['results']] == planned['modes']
        with (directory / 'raw.csv').open(newline='') as stream:
            rows = list(csv.DictReader(stream))
        assert len(rows) == len(planned['modes'])
        plan = json.loads((directory / 'plan.json').read_text())
        for name, digest in plan['asset_sha256'].items():
            assert common_hashes.get(name, digest) == digest, f'Input drift: {name}'
            common_hashes[name] = digest
        for result, row in zip(summary['results'], rows):
            assert result['map'] == row['map'] == planned['map']
            assert int(result['run']) == int(row['run']) == planned['run']
            assert result['mode'] == row['mode']
            assert result['candidate'] == protocol['candidate']
            assert row['attempt_count'] == '1' and row['retry_count'] == '0'
            assert all(result[k] is True for k in
                       ('run_valid', 'resource_valid', 'speed_limit_valid'))
            assert all(value is True for value in
                       result['source_acquisition']['checks'].values())
            assert result['strict_recovery_audit']['valid'] is True
            solid = result['solid_obstacle_audit']
            assert solid['audit_valid'] is True
            assert solid['coverage']['all_received_samples_recorded'] is True
            assert solid['contact_episodes'] == result['safety_collisions']
            assert solid['completion'] == result['success']
            for metric in ('mission_time_s', 'end_to_end_cpu_cores_mean',
                           'end_to_end_cpu_core_s', 'total_ms_mean'):
                assert math.isfinite(result[metric]) and result[metric] >= 0, metric
            for metric in ('planner_ingress_payload_mib_s', 'map_payload_bytes_total'):
                assert math.isfinite(float(row[metric])) and float(row[metric]) >= 0, metric
            stack = directory / 'artifacts' / (
                f"{planned['map']}_run{planned['run']}_{result['mode']}.attempt1.stack.log")
            text = stack.read_text(errors='replace')
            goal_audit = audit_goal_refresh(text, result['mode'])
            assert goal_audit['valid'], (planned['run'], result['mode'], goal_audit)
            flight = {k: result[k] for k in (
                'map', 'run', 'mode', 'success', 'safety_collisions',
                'mission_time_s', 'end_to_end_cpu_cores_mean',
                'end_to_end_cpu_core_s', 'total_ms_mean')}
            flight.update(directory=planned['directory'],
                          run_valid=result['run_valid'],
                          resource_valid=result['resource_valid'],
                          speed_limit_valid=result['speed_limit_valid'],
                          goal_refresh_v8_valid=goal_audit['valid'],
                          waypoint_count=row['waypoints_reached'],
                          input_mib_s=row['planner_ingress_payload_mib_s'],
                          input_mib_run=float(row['map_payload_bytes_total']) / 2**20,
                          full_transitions=row['filter_effective_full_open_transitions'],
                          zone_disconnects=text.count('[TRAJ_GUARD_ZONE_DISCONNECT]'),
                          recovery_exhaustions=text.count('[TRAJ_GUARD_RECOVERY_EXHAUSTED]'),
                          local_escape_commits=text.count('[TRAJ_GUARD_LOCAL_ESCAPE]'),
                          stack_sha256=sha256(stack),
                          raw_csv_sha256=sha256(directory / 'raw.csv'))
            flights.append(flight)
    assert len(flights) == 9
    assert len({(f['run'], f['mode']) for f in flights}) == len(flights)
    with (ROOT / 'v2_flights.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(flights[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(flights)
    rejected = json.loads((ROOT / 'forest_full_r01/summary.json').read_text())['results'][0]
    report = {
        'schema': 'topology-liveness-v2-predefined-smoke-audit',
        'candidate': protocol['candidate'], 'predefined_flights': 9,
        'observed_flights': len(flights), 'all_quality_valid': True,
        'safe_complete': sum(f['success'] and f['safety_collisions'] == 0 for f in flights),
        'contact_trials': sum(f['safety_collisions'] > 0 for f in flights),
        'zone_disconnects_exercised': sum(f['zone_disconnects'] for f in flights),
        'recovery_exhaustions_exercised': sum(f['recovery_exhaustions'] for f in flights),
        'same_original_state_replayed': False,
        'baseline_promoted': False,
        'frozen_reference_results_replaced': False,
        'rejected_v1_preserved': {k: rejected[k] for k in (
            'run', 'mode', 'success', 'mission_time_s', 'safety_collisions')},
        'input_sha256': common_hashes, 'flights': flights,
    }
    (ROOT / 'audit_v2.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ('input_sha256', 'flights')}, indent=2))


if __name__ == '__main__':
    main()
