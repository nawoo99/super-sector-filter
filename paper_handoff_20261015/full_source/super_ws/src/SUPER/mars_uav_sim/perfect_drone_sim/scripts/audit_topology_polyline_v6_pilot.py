#!/usr/bin/env python3
"""Read-only audit of all nine unique flights, including the preserved prefix."""
import argparse
import csv
import json
import math
from pathlib import Path

from scenario7_geometry import load_geometry, SampledSolidAudit, sha256
from topology_polyline_v6_pilot import inspect, PLANNED, DIAGNOSTICS


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    protocol = json.loads((args.root / 'protocol.json').read_text())
    status = json.loads((args.root / 'status.json').read_text())
    if status['state'] != 'COMPLETE' or protocol['planned_flights'] != 9:
        raise ValueError('Incomplete pilot; no final nine-flight claim')
    for path, expected in protocol['hashes'].items():
        if sha256(path) != expected:
            raise ValueError('Pilot candidate changed: '+path)
    prefix = protocol['preserved_prefix_groups']
    prefix_root = Path(protocol['preserved_prefix_directory']) if prefix else args.root
    if prefix:
        old = json.loads((prefix_root / 'protocol.json').read_text())
        for path, expected in old['hashes'].items():
            archive = DIAGNOSTICS / 'source_v6_pilot_v1' / Path(path).name
            if sha256(path) != expected and (not archive.is_file() or sha256(archive) != expected):
                raise ValueError('Preserved original input changed: '+path)
    flights, assets, replay_reports = [], {}, []
    for index, (directory, name, run, modes) in enumerate(PLANNED):
        folder = (prefix_root if index < prefix else args.root) / directory
        group, complete = inspect(folder, name, run, modes)
        if not complete or not all(f['quality_valid'] for f in group):
            raise ValueError('Incomplete/invalid group: '+directory)
        plan = json.loads((folder / 'plan.json').read_text())
        for path, expected in plan['asset_sha256'].items():
            if assets.get(path, expected) != expected or sha256(path) != expected:
                raise ValueError('Asset drift: '+path)
            assets[path] = expected
        for flight in group:
            stem = folder / 'artifacts' / f"{name}_run{run}_{flight['mode']}.attempt1"
            saved = json.loads(Path(str(stem)+'.solid_audit.json').read_text())
            geometry = load_geometry(saved['pcd_path'])
            if sha256(saved['geometry_path']) != saved['geometry_sha256']:
                raise ValueError('Solid geometry hash disagreement')
            replay = SampledSolidAudit(geometry)
            odometry = Path(str(stem)+'.odometry.csv')
            with odometry.open(newline='') as stream:
                for index, row in enumerate(csv.DictReader(stream), 1):
                    if int(row['sample']) != index:
                        raise ValueError('Unordered actual odometry')
                    clearance = replay.observe(
                        [float(row[k]) for k in ('x_m','y_m','z_m')],
                        [float(row[k]) for k in ('vx_mps','vy_mps','vz_mps')],
                        int(row['header_ns']), int(row['receipt_monotonic_ns']),
                        float(row['elapsed_s']))
                    if clearance is None or not math.isclose(clearance,float(row['clearance_m']),abs_tol=1e-12):
                        raise ValueError('Actual solid-clearance replay disagreement')
            observed = replay.summary()
            if any(saved[key] != value for key,value in observed.items()):
                raise ValueError('Actual odometry summary disagreement')
            replay_reports.append(dict(map=name, run=run, mode=flight['mode'],
                samples=observed['samples'], contact_episodes=observed['contact_episodes'],
                min_body_clearance_m=observed['min_clearance_m'],
                max_receipt_interval_s=observed['max_receipt_interval_s'],
                odometry_sha256=sha256(odometry)))
        flights.extend(group)
    if len(flights) != 9 or len({(f['map'],f['run'],f['mode']) for f in flights}) != 9:
        raise ValueError('Non-unique/incomplete flight inventory')
    report = dict(schema='certified-polyline-v6-independent-pilot-audit-v1',
        physical_flights=9, preserved_prefix_flights=1 if prefix else 0,
        new_flights=8 if prefix else 9, all_quality_valid=True,
        safe_complete=sum(f['success'] and f['contacts']==0 for f in flights),
        contact_trials=sum(f['contacts']>0 for f in flights),
        polyline_commits=sum(f['polyline_commits'] for f in flights),
        same_original_state_replayed=False, canonical_promoted=False,
        frozen_c41_replaced=False, received_samples_only=True,
        flights=flights, solid_replays=replay_reports, input_sha256=assets)
    with args.output.open('x') as stream:
        json.dump(report,stream,indent=2); stream.write('\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('flights','solid_replays','input_sha256')}))


if __name__ == '__main__':
    main()
