#!/usr/bin/env python3
"""Read-only independent replay of the diagnostic's received odometry/logs."""
import argparse
import csv
import json
import math
from pathlib import Path
import re

from scenario7_geometry import SampledSolidAudit, load_geometry, sha256


def audit(directory):
    report = json.loads((directory / 'result.json').read_text())
    protocol = json.loads((directory / 'protocol.json').read_text())
    errors = []
    for name, expected in report['hashes'].items():
        if sha256(directory / name) != expected:
            errors.append('artifact_hash:' + name)
    for name, expected in protocol['hashes'].items():
        if sha256(name) != expected:
            errors.append('input_hash:' + name)
    geometry = load_geometry(protocol['geometry']['pcd_path'])
    sampled = SampledSolidAudit(geometry)
    with (directory / 'odometry.csv').open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    for index, row in enumerate(rows, 1):
        if int(row['sample']) != index:
            errors.append('unordered_sample')
        position = [float(row[name]) for name in ('x', 'y', 'z')]
        velocity = [float(row[name]) for name in ('vx', 'vy', 'vz')]
        clearance = sampled.observe(position, velocity, int(row['header_ns']),
                                    int(row['receipt_ns']), float(row['elapsed_s']))
        if clearance is None or not math.isclose(clearance, float(row['clearance_m']), abs_tol=1e-12):
            errors.append('clearance_replay')
    replay = sampled.summary()
    if replay != report['solid_audit']:
        errors.append('solid_summary_replay')
    if not replay['audit_valid'] or replay['contact_episodes']:
        errors.append('invalid_or_contact')
    stack = (directory / 'stack.log').read_text(errors='replace')
    for marker, count in report['markers'].items():
        if stack.count('[' + marker + ']') != count:
            errors.append('marker_count:' + marker)
    evidence_errors = list(errors)
    variant = protocol['variant']
    goal = protocol['reset_goal'] if variant == 'exhausted' else protocol['goal']
    max_goal_distance = 0.2 if variant == 'exhausted' else 1.5
    if not rows or math.dist([float(rows[-1][k]) for k in ('x', 'y', 'z')], goal) > max_goal_distance:
        errors.append('goal_not_reached')
    if variant != 'control':
        if not re.search(r'\[TEST_FOREST_TOPOLOGY_STATE\] variant=' + variant +
                         r'.*historical_map_replay=false forced_search_result=false', stack):
            errors.append('state_injection_contract')
        if not re.search(r'\[TRAJ_GUARD_ZONE_DISCONNECT\].*action=rollback_latest_zone_and_recover', stack):
            errors.append('real_astar_branch_unexercised')
    if variant == 'available':
        if not re.search(r'\[TRAJ_GUARD_LOCAL_ESCAPE\] action=commit', stack):
            errors.append('no_certified_escape_commit')
    if variant == 'exhausted':
        holds = [row for row in rows if row['phase'] == 'exhausted_hold']
        if not holds or float(holds[-1]['elapsed_s']) - float(holds[0]['elapsed_s']) < 2.9:
            errors.append('hold_not_observed')
        elif max(math.dist([float(row[k]) for k in ('x', 'y', 'z')],
                          [float(holds[0][k]) for k in ('x', 'y', 'z')]) for row in holds) > 0.02:
            errors.append('hold_moved')
        if stack.count('[TRAJ_GUARD_RECOVERY_EXHAUSTED]') != 1:
            errors.append('exhaustion_not_idempotent')
    return dict(directory=str(directory), variant=variant, valid=not errors,
                evidence_valid=not evidence_errors, evidence_errors=evidence_errors,
                criterion_met=not errors and report['passed'],
                errors=errors, reported_passed=report['passed'], status=report['status'],
                contact_episodes=replay['contact_episodes'], samples=replay['samples'],
                min_body_clearance_m=replay['min_clearance_m'],
                max_receipt_interval_s=replay['max_receipt_interval_s'],
                max_pose_step_m=replay['max_pose_step_m'],
                historical_map_replay=False, canonical_mission=False)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('directories', type=Path, nargs='+')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    reports = [audit(path) for path in args.directories]
    if args.output:
        with args.output.open('x') as stream:
            stream.write(json.dumps(reports, indent=2) + '\n')
    print(json.dumps(reports, indent=2))
    return 0 if all(report['valid'] for report in reports) else 1


if __name__ == '__main__':
    raise SystemExit(main())
