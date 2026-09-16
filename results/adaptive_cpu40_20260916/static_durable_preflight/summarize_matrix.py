#!/usr/bin/env python3
"""Offline only; does not run or retry experiments."""
import json
from pathlib import Path
import re

base = Path(__file__).resolve().parent
names = [
    'ros_control_reader_first_attempt1', 'ros_control_late_attempt1',
    'ros_durable_legacy_reader_first_attempt1', 'ros_durable_legacy_late_attempt1',
    'ros_durable_reader_first_attempt1', 'ros_durable_late_attempt1',
]
rows = []
for name in names:
    directory = base / name
    if not (directory / 'result.json').exists():
        rows.append({'case': name, 'complete': False})
        continue
    data = json.loads((directory / 'result.json').read_text())
    log = (directory / 'simulator.log').read_text(errors='replace')
    cadence = [float(value) for value in re.findall(
        r'\[SENSOR_CADENCE_SUMMARY\].*? hz=([0-9.]+)', log)]
    rows.append(dict(
        case=name, complete=True, valid=data['valid'],
        durable_publisher=data['durable'], reader_qos=data['reader_qos'],
        sequence=data['sequence'], phases=data['phases'], error=data.get('error'),
        received={label: len(clouds) for label, clouds in data.get('clouds', {}).items()},
        geometry_sha256=data.get('geometry_sha256'),
        geometry_validated_clouds=data.get('geometry_validated_clouds', 0),
        publisher_actual_qos=data.get('publisher_actual_qos'),
        graph_qos=data.get('offered_qos'), graph_qos_verified=data.get('graph_qos_verified'),
        source_cadence_hz_last=cadence[-1] if cadence else None,
        source_cadence_pass=bool(cadence) and 9.5 <= cadence[-1] <= 10.5,
        clean_exit=data.get('simulator_exit_code') == 0 and
                   data.get('exact_child_reaped', False) and not data.get('forced_cleanup', False),
        elapsed_s=data.get('elapsed_s'),
        global_pc_publish_log_count=log.count('Publish global map size:'),
    ))
report = dict(scope='Actual static-PC no-flight transport matrix; no automatic retries',
              legacy_reader_candidate_pass=all(
                  row.get('valid', False) for row in rows
                  if row['case'].startswith('ros_durable_legacy_')),
              all_cases_complete=all(row['complete'] for row in rows), cases=rows)
destination = base / 'matrix_summary.json'
if destination.exists():
    raise SystemExit('refusing to overwrite a prior final matrix summary')
destination.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
