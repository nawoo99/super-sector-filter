#!/usr/bin/env python3
"""Fresh seven-map n10 campaign with the corrected c40 event-chain audit.

The planner, sensor, maps, missions, and 60 s/2 cm no-progress observer are the
frozen c40 configuration. Unlike the historical c40 controller, this driver
does not reject a valid Adaptive Full cycle for having fewer than four new
requests; every new goal is checked against the corrected event-chain audit.
Flight outcomes are recorded, not used to select or replace trials.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import run_scenario7_v7_n10 as base
import run_scenario7_v13_n10 as v13
import run_scenario7_v14_n10 as v14
import run_scenario7_v14_completion as corrected


THIS_FILE = Path(__file__).resolve()
ORIGINAL_IDENTITY = (
    base.REPO / 'results/scenario7_no_mission_cutoff_v14_n10_20261001/'
    'frozen_identity.json'
)
CANDIDATE = 'c41_fresh_no_cutoff_v15_n10'
BASE_RUN = 97000


def verify_original_identity():
    expected = json.loads(ORIGINAL_IDENTITY.read_text())
    changed = [path for path, digest in expected.items()
               if not path.endswith('/protocol.json') and
               (not Path(path).is_file() or base.sha256(Path(path)) != digest)]
    if changed:
        raise RuntimeError('c40 physical inputs changed: ' + ', '.join(changed))


def frozen_identity(root):
    hashes = original_frozen_identity(root)
    for path in (THIS_FILE, v14.WRAPPER, v13.RUNTIME_BINARY,
                 corrected.THIS_FILE, corrected.AUDITOR):
        hashes[str(path)] = base.sha256(path)
    return hashes


def validate_triplet(item, write=True):
    output = Path(item['output'])
    raw = output / 'raw.csv'
    errors = []
    outcomes = {}
    if not raw.is_file():
        errors.append('missing raw.csv')
        rows = []
    else:
        with raw.open(newline='') as stream:
            rows = list(csv.DictReader(stream))
    if [row.get('mode') for row in rows] != item['modes']:
        errors.append('missing, duplicate, or out-of-order mode row')
    for row in rows:
        mode = row.get('mode')
        if mode not in base.MODES or mode in outcomes:
            errors.append('unexpected or duplicate mode: ' + str(mode))
            continue
        try:
            finding = corrected.flight_audit(item, mode, row)
            quality_valid = all((
                finding['common'], finding['source'], finding['recovery'],
                finding['bounded'], finding['heading'],
                finding['goal_change_event_audit']['valid'],
                finding['no_mission_cutoff_audit']['valid'],
            ))
        except (OSError, ValueError, KeyError, TypeError) as error:
            finding = {'error': repr(error)}
            quality_valid = False
        complete = (base.truth(row.get('success')) is True and
                    row.get('waypoints_reached') == row.get('n_waypoints') and
                    base.number(row.get('n_waypoints')) == 5)
        contacts = base.number(row.get('safety_collisions'))
        outcome = dict(
            common_valid=finding.get('common') is True,
            source_valid=finding.get('source') is True,
            quality_valid=quality_valid,
            success=base.truth(row.get('success')) is True,
            complete=complete,
            safe_complete=complete and contacts == 0,
            safety_collisions=contacts,
            mission_time_s=base.number(row.get('mission_time_s')),
            body_clearance_m=base.number(row.get('static_pcd_clearance_m')),
            end_to_end_cpu_cores_mean=base.number(row.get('end_to_end_cpu_cores_mean')),
            end_to_end_cpu_core_s=base.number(row.get('end_to_end_cpu_core_s')),
            map_payload_mib_s=base.number(row.get('map_payload_mib_s')),
            map_payload_bytes_total=base.number(row.get('map_payload_bytes_total')),
            map_update_ms_mean=base.number(row.get('total_ms_mean')),
            full_open_transitions=base.number(row.get('filter_trajectory_guard_open_transitions')),
            full_close_transitions=base.number(row.get('filter_trajectory_guard_close_transitions')),
            full_refresh_acks=base.number(row.get('filter_full_refresh_request_count')),
            audit=finding,
            log_counts=base.log_counts(corrected.stack_path(item, mode).read_text(
                errors='replace')) if corrected.stack_path(item, mode).is_file() else {},
        )
        outcomes[mode] = outcome
        if not quality_valid:
            errors.append(mode + ': flight quality/source/event/no-cutoff audit failed')
        for key in ('safety_collisions', 'mission_time_s',
                    'end_to_end_cpu_cores_mean', 'end_to_end_cpu_core_s',
                    'map_payload_mib_s', 'map_payload_bytes_total',
                    'map_update_ms_mean'):
            value = outcome[key]
            if value is None or not math.isfinite(value):
                errors.append(mode + ': missing/nonfinite ' + key)
    result = dict(valid=not errors, blocking=bool(errors), errors=errors,
                  map=item['map'], run=item['run'], repeat=item['repeat'],
                  stage=item['stage'], mode_order=item['modes'], outcomes=outcomes,
                  policy='All three mode outcomes retained; no success/contact censoring')
    if write:
        base.atomic_json(output / 'v7_triplet_validation.json', result)
    return result


def write_progress(root):
    validations = original_write_progress(root)
    report = Path(root) / 'summary_by_map.md'
    report.write_text(report.read_text().replace(
        '# Scenario7 c32 n10 progress',
        '# Scenario7 c41 fresh no-cutoff n10 progress', 1))
    return validations


def main():
    global original_frozen_identity, original_write_progress
    verify_original_identity()
    v13.verify_runtime_install()
    original_frozen_identity = base.frozen_identity
    original_write_progress = base.write_progress
    old = (base.CANDIDATE, base.BASE_RUN, base.WRAPPER, base.COMMON,
           base.frozen_identity, base.validate_triplet, base.write_progress)
    base.CANDIDATE = CANDIDATE
    base.BASE_RUN = BASE_RUN
    base.WRAPPER = v14.WRAPPER
    base.COMMON = tuple(arg for arg in base.COMMON
                        if arg != '--event-body-heading')
    base.frozen_identity = frozen_identity
    base.validate_triplet = validate_triplet
    base.write_progress = write_progress
    try:
        return base.main()
    finally:
        (base.CANDIDATE, base.BASE_RUN, base.WRAPPER, base.COMMON,
         base.frozen_identity, base.validate_triplet, base.write_progress) = old


if __name__ == '__main__':
    raise SystemExit(main())
