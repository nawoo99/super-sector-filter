#!/usr/bin/env python3
"""Summarize only a complete, audited no-mission-cutoff c40 campaign."""
import csv
import json
import math
from pathlib import Path
import statistics


ROOT = Path('/root/super-sector-filter/results/scenario7_no_mission_cutoff_v14_n10_20261001')
MAPS = (
    'gapfree_d1_m01', 'gapfree_d1_m02', 'gapfree_d1_m03',
    'gapfree_d1_m04', 'gapfree_d1_m05r2',
    'urban_blocks_u01', 'forest_cluster_f01',
)
MODES = ('full', 'sector', 'adaptive')
METRICS = (
    'end_to_end_cpu_cores_mean', 'end_to_end_cpu_core_s',
    'map_payload_mib_s', 'map_payload_bytes_total', 'total_ms_mean',
    'filter_trajectory_guard_open_transitions',
)


def value(row, key):
    result = float(row[key])
    if not math.isfinite(result):
        raise ValueError(f'non-finite {key}')
    return result


def load():
    status = json.loads((ROOT / 'status.json').read_text())
    if status['state'] != 'COMPLETE' or status['recorded_flights'] != 210:
        raise ValueError('c40 campaign is not complete')
    plan = json.loads((ROOT / 'plan.json').read_text())['commands']
    if len(plan) != 70:
        raise ValueError('expected exactly 70 planned triplets')
    manifest = []
    for item in plan:
        output = Path(item['output'])
        with (output / 'raw.csv').open(newline='') as stream:
            rows = list(csv.DictReader(stream))
        if [row['mode'] for row in rows] != item['modes']:
            raise ValueError('missing or out-of-order flight: ' + str(output))
        validation = json.loads((output / 'v7_triplet_validation.json').read_text())
        if validation['valid'] is not True:
            raise ValueError('invalid triplet: ' + str(output))
        for row in rows:
            mode = row['mode']
            cutoff = validation['outcomes'][mode]['no_mission_cutoff_audit']
            if cutoff['valid'] is not True:
                raise ValueError('finite or unaudited flight: ' + str(output))
            if (row['run_valid'] != 'True' or row['resource_valid'] != 'True'
                    or row['speed_limit_valid'] != 'True'
                    or value(row, 'attempt_count') != 1
                    or value(row, 'retry_count') != 0):
                raise ValueError('flight quality/attempt gate failed: ' + str(output))
            solid_path = output / 'artifacts' / (
                f"{item['map']}_run{item['run']}_{mode}.attempt1.solid_audit.json")
            solid = json.loads(solid_path.read_text())
            if solid['terminal_stall_policy']['mission_time_cutoff_s'] is not None:
                raise ValueError('observer had a finite mission cutoff')
            event = solid.get('terminal_stall_event')
            manifest.append(dict(
                map=item['map'], repeat=item['repeat'], run=item['run'], mode=mode,
                complete=(row['success'] == 'True' and
                          row['waypoints_reached'] == row['n_waypoints']),
                contacts=int(value(row, 'safety_collisions')),
                mission_time_s=value(row, 'mission_time_s'),
                terminal_event=event['kind'] if event else '',
                **{key: value(row, key) for key in METRICS},
            ))
    identities = [(r['map'], r['repeat'], r['mode']) for r in manifest]
    if len(manifest) != 210 or len(set(identities)) != 210:
        raise ValueError('expected 210 unique no-cutoff flights')
    return manifest


def summarize(rows):
    completed = [row['mission_time_s'] for row in rows if row['complete']]
    mean = lambda key: statistics.mean(row[key] for row in rows)
    return dict(
        n=len(rows), complete=len(completed), contact_runs=sum(r['contacts'] > 0 for r in rows),
        contact_episodes=sum(r['contacts'] for r in rows),
        completed_time_mean_s=statistics.mean(completed) if completed else None,
        completed_time_median_s=statistics.median(completed) if completed else None,
        all_outcome_time_mean_s=mean('mission_time_s'),
        nonprogress_terminals=sum(bool(r['terminal_event']) for r in rows),
        cpu_cores=mean('end_to_end_cpu_cores_mean'),
        cpu_core_s=mean('end_to_end_cpu_core_s'),
        input_mib_s=mean('map_payload_mib_s'),
        input_mib_run=mean('map_payload_bytes_total') / 1024**2,
        map_ms=mean('total_ms_mean'),
        adaptive_full_opens=mean('filter_trajectory_guard_open_transitions'),
    )


def main():
    rows = load()
    by_map = [dict(map=name, mode=mode, **summarize(
        [row for row in rows if row['map'] == name and row['mode'] == mode]))
        for name in MAPS for mode in MODES]
    with (ROOT / 'summary_no_cutoff_by_map.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(by_map[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(by_map)
    lines = [
        '# c40 no-mission-cutoff seven-map results', '',
        'All 210 planned flights used an infinite mission horizon. A declared,',
        'measurement-only 60 s/2 cm no-progress event terminates absorbing stalls',
        'as failures. Completion time below uses completed flights only; outcome',
        'time includes any no-progress terminal and is not traversal time.', '',
        '| Map | Mode | Complete | Contact runs | Completed time mean/median (s) | Outcome time mean (s) | No-progress terminal | CPU cores | CPU core-s/run | Input MiB/s | Input MiB/run | Map ms/frame | Full opens |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for row in by_map:
        time = ('—' if row['completed_time_mean_s'] is None else
                f"{row['completed_time_mean_s']:.2f}/{row['completed_time_median_s']:.2f}")
        opens = f"{row['adaptive_full_opens']:.2f}" if row['mode'] == 'adaptive' else '—'
        lines.append(f"| {row['map']} | {row['mode']} | {row['complete']}/{row['n']} | "
                     f"{row['contact_runs']}/{row['n']} | {time} | "
                     f"{row['all_outcome_time_mean_s']:.2f} | {row['nonprogress_terminals']} | "
                     f"{row['cpu_cores']:.3f} | {row['cpu_core_s']:.2f} | "
                     f"{row['input_mib_s']:.3f} | {row['input_mib_run']:.2f} | "
                     f"{row['map_ms']:.2f} | {opens} |")
    lines.extend(['', '## Cohorts', ''])
    for label, names in (
            ('Normal Map1–5', MAPS[:5]), ('Urban', MAPS[5:6]),
            ('Forest', MAPS[6:]), ('All seven maps', MAPS)):
        lines.extend([f'### {label}', '',
                      '| Mode | Complete | Contact runs | Completed time mean/median (s) | Outcome time mean (s) | CPU cores | CPU core-s/run | Input MiB/s | Input MiB/run | Map ms/frame |',
                      '|---|---:|---:|---:|---:|---:|---:|---:|---:|'])
        for mode in MODES:
            stat = summarize([row for row in rows if row['map'] in names and row['mode'] == mode])
            time = ('—' if stat['completed_time_mean_s'] is None else
                    f"{stat['completed_time_mean_s']:.2f}/{stat['completed_time_median_s']:.2f}")
            lines.append(f"| {mode} | {stat['complete']}/{stat['n']} | "
                         f"{stat['contact_runs']}/{stat['n']} | {time} | "
                         f"{stat['all_outcome_time_mean_s']:.2f} | "
                         f"{stat['cpu_cores']:.3f} | {stat['cpu_core_s']:.2f} | "
                         f"{stat['input_mib_s']:.3f} | {stat['input_mib_run']:.2f} | "
                         f"{stat['map_ms']:.2f} |")
        lines.append('')
    (ROOT / 'summary_no_cutoff.md').write_text('\n'.join(lines).rstrip() + '\n')
    print(ROOT / 'summary_no_cutoff.md')


if __name__ == '__main__':
    main()
