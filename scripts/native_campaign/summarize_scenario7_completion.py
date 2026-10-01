#!/usr/bin/env python3
"""Merge the preserved c39 flights with their documented unflown-slot completion."""
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics


ORIGINAL = Path('/root/super-sector-filter/results/scenario7_bounded_recovery_v13_n10_v2_20260930')
COMPLETION = Path('/root/super-sector-filter/results/scenario7_bounded_recovery_v13_n10_v2_completion_20261001')
MODES = ('full', 'sector', 'adaptive')
MAPS = ('gapfree_d1_m01', 'gapfree_d1_m02', 'gapfree_d1_m03', 'gapfree_d1_m04',
        'gapfree_d1_m05r2', 'urban_blocks_u01', 'forest_cluster_f01')


def read_rows(path):
    if not path.is_file():
        return []
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def number(row, key):
    if row.get(key) in (None, ''):
        return None
    value = float(row[key])
    if not math.isfinite(value):
        raise ValueError(f'non-finite {key} in a flight row')
    return value


def mean(rows, key):
    values = [number(row, key) for row in rows]
    if any(value is None for value in values):
        raise ValueError(f'missing {key} in a flight row')
    return statistics.mean(values)


def results():
    original_status = json.loads((ORIGINAL / 'status.json').read_text())
    completed_status = json.loads((COMPLETION / 'status.json').read_text())
    reaudit = json.loads((ORIGINAL / 'posthoc_recovery_audit_v2.json').read_text())
    if (original_status['state'] != 'STOPPED_FOR_DIAGNOSIS' or
            completed_status['state'] != 'COMPLETE' or
            reaudit['flight_count'] != 173 or reaudit['reaudit_valid_count'] != 173 or
            len(completed_status['completed']) != 13 or
            not all(item['valid'] for item in completed_status['completed'])):
        raise ValueError('one of the preserved or completion gates is not satisfied')
    frozen = json.loads((ORIGINAL / 'frozen_identity.json').read_text())
    changed = [path for path, expected in frozen.items()
               if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected]
    if changed:
        raise ValueError('original runtime identity changed: ' + ', '.join(changed))
    plan = json.loads((ORIGINAL / 'plan.json').read_text())['commands']
    manifest = []
    for item in plan:
        original = Path(item['output'])
        added = COMPLETION / item['stage'] / item['map'] / original.name
        sources = ((original, 'original'), (added, 'completion'))
        rows = [(row, root, origin) for root, origin in sources
                for row in read_rows(root / 'raw.csv')]
        if [row['mode'] for row, _, _ in rows] != item['modes']:
            raise ValueError(f'wrong flight count or order for run {item["run"]}')
        for row, root, origin in rows:
            mode = row['mode']
            log = root / 'artifacts' / (
                f"{item['map']}_run{item['run']}_{mode}.attempt1.stack.log")
            if not log.is_file():
                raise ValueError(f'missing flight log: {log}')
            if row['run'] != str(item['run']) or row['map'] != item['map']:
                raise ValueError(f'flight identity mismatch in {root}')
            if row['run_valid'] != 'True' or row['resource_valid'] != 'True' or row['speed_limit_valid'] != 'True':
                raise ValueError(f'invalid flight quality in {root}: {mode}')
            if number(row, 'attempt_count') != 1 or number(row, 'retry_count') != 0:
                raise ValueError(f'attempt or retry mismatch in {root}: {mode}')
            manifest.append({
                'map': item['map'], 'repeat': item['repeat'], 'run': item['run'],
                'mode': mode, 'origin': origin, 'raw_csv': str(root / 'raw.csv'),
                'log_sha256': hashlib.sha256(log.read_bytes()).hexdigest(),
                'success': row['success'], 'waypoints_reached': row['waypoints_reached'],
                'n_waypoints': row['n_waypoints'], 'safety_collisions': row['safety_collisions'],
                'mission_time_s': row['mission_time_s'],
                'end_to_end_cpu_cores_mean': row['end_to_end_cpu_cores_mean'],
                'end_to_end_cpu_core_s': row['end_to_end_cpu_core_s'],
                'map_payload_mib_s': row['map_payload_mib_s'],
                'map_payload_bytes_total': row['map_payload_bytes_total'],
                'total_ms_mean': row['total_ms_mean'],
                'filter_trajectory_guard_open_transitions':
                    row['filter_trajectory_guard_open_transitions'],
            })
    identities = [(row['map'], row['repeat'], row['mode']) for row in manifest]
    if len(manifest) != 210 or len(set(identities)) != 210:
        raise ValueError('not exactly 210 unique planned flights')
    return manifest


def summary(rows):
    complete = sum(row['success'] == 'True' and
                   row['waypoints_reached'] == row['n_waypoints'] for row in rows)
    contacts = sum(number(row, 'safety_collisions') > 0 for row in rows)
    opens = [number(row, 'filter_trajectory_guard_open_transitions') for row in rows]
    return dict(n=len(rows), complete=complete, contact_runs=contacts,
                mission_time_s=mean(rows, 'mission_time_s'),
                cpu_cores=mean(rows, 'end_to_end_cpu_cores_mean'),
                cpu_core_s=mean(rows, 'end_to_end_cpu_core_s'),
                input_mib_s=mean(rows, 'map_payload_mib_s'),
                input_mib_run=mean(rows, 'map_payload_bytes_total') / (1024 ** 2),
                map_ms=mean(rows, 'total_ms_mean'),
                adaptive_full_opens=(statistics.mean(opens)
                                     if all(value is not None for value in opens)
                                     else None))


def main():
    manifest = results()
    with (COMPLETION / 'final_flight_manifest.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(manifest[0]))
        writer.writeheader(); writer.writerows(manifest)
    by_map = []
    for map_name in MAPS:
        for mode in MODES:
            rows = [row for row in manifest if row['map'] == map_name and row['mode'] == mode]
            if len(rows) != 10:
                raise ValueError(f'{map_name} {mode} has {len(rows)} flights, expected 10')
            by_map.append(dict(map=map_name, mode=mode, **summary(rows)))
    with (COMPLETION / 'final_by_map.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(by_map[0]))
        writer.writeheader(); writer.writerows(by_map)
    lines = [
        '# c39 seven-map result: documented interrupted-campaign completion', '',
        'The first session retained 173 unique flights, then stopped after a recovery',
        'log audit rejected two distinct certified paths in one Full interval. A revised',
        'strict audit of those unchanged logs passed 173/173. The second session ran',
        'the 37 unflown slots once each. The combined evidence is 210 unique planned',
        'flights, with no replacement attempts. This was not one uninterrupted run.', '',
        '| Map | Mode | Complete | Contact runs | Time s | CPU cores | CPU core-s | Input MiB/s | Input MiB/run | Map ms/frame | Adaptive Full opens |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for row in by_map:
        opens = f"{row['adaptive_full_opens']:.2f}" if row['mode'] == 'adaptive' else '—'
        lines.append(f"| {row['map']} | {row['mode']} | {row['complete']}/{row['n']} | "
                     f"{row['contact_runs']}/{row['n']} | {row['mission_time_s']:.2f} | "
                     f"{row['cpu_cores']:.3f} | {row['cpu_core_s']:.2f} | "
                     f"{row['input_mib_s']:.3f} | {row['input_mib_run']:.2f} | "
                     f"{row['map_ms']:.2f} | {opens} |")
    lines.extend(['', '## Separate aggregate groups', '',
                  '| Group | Mode | Complete | Contact runs | Time s | CPU cores | CPU core-s | Input MiB/s | Input MiB/run | Map ms/frame |',
                  '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|'])
    for group, names in (('Normal Map1–5', MAPS[:5]), ('Urban', MAPS[5:6]),
                         ('Forest', MAPS[6:])):
        for mode in MODES:
            row = summary([item for item in manifest if item['map'] in names and item['mode'] == mode])
            lines.append(f"| {group} | {mode} | {row['complete']}/{row['n']} | "
                         f"{row['contact_runs']}/{row['n']} | {row['mission_time_s']:.2f} | "
                         f"{row['cpu_cores']:.3f} | {row['cpu_core_s']:.2f} | "
                         f"{row['input_mib_s']:.3f} | {row['input_mib_run']:.2f} | "
                         f"{row['map_ms']:.2f} |")
    (COMPLETION / 'final_combined_summary.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps({'flights': len(manifest), 'by_map': by_map}, indent=2))


if __name__ == '__main__':
    main()
