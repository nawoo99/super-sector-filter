#!/usr/bin/env python3
"""Make one provenance-explicit c40 report from 72 preserved + 138 new flights."""
import csv
import json
import math
from pathlib import Path

import run_scenario7_v14_completion as campaign
import summarize_scenario7_v14_no_cutoff as tables


def finite(row, key):
    value = float(row[key])
    if not math.isfinite(value):
        raise ValueError(f'non-finite {key}: {row[key]}')
    return value


def load_combined():
    original = json.loads((campaign.ORIGINAL / 'status.json').read_text())
    resumed = json.loads((campaign.COMPLETION / 'status.json').read_text())
    if original['state'] != 'STOPPED_FOR_DIAGNOSIS' or len(original['completed']) != 24:
        raise RuntimeError('original c40 provenance changed')
    if resumed['state'] != 'COMPLETE' or len(resumed['completed']) != 46 \
            or any(not item['valid'] for item in resumed['completed']):
        raise RuntimeError('c40 continuation has not completed cleanly')
    frozen = json.loads((campaign.COMPLETION / 'frozen_identity.json').read_text())
    campaign.check_frozen(frozen)
    plan, work = campaign.worklist()
    if len(work) != 46:
        raise RuntimeError('unexpected worklist length')
    audit = json.loads((campaign.COMPLETION / 'posthoc_goal_change_audit_v1.json').read_text())
    if audit['preserved_flights'] != 72 or audit['valid_flights'] != 72:
        raise RuntimeError('preserved-flight re-audit missing')
    records = []
    manifest = []
    for item in plan:
        original_rows = campaign.rows(Path(item['output']) / 'raw.csv')
        remaining = item['modes'][len(original_rows):]
        if remaining:
            output = campaign.COMPLETION / item['stage'] / item['map'] / Path(item['output']).name
            continuation_item = item | {'output': str(output), 'modes': remaining}
            new_rows = campaign.rows(output / 'raw.csv')
            validation = json.loads((output / 'continuation_validation.json').read_text())
            if validation['valid'] is not True or [r['mode'] for r in new_rows] != remaining:
                raise RuntimeError('invalid continuation triplet: ' + str(output))
        else:
            continuation_item = None
            new_rows = []
        if [row['mode'] for row in original_rows + new_rows] != item['modes']:
            raise RuntimeError('planned flight ID/order missing: ' + str(item))
        for origin, source_item, selected in (
                ('original', item, original_rows),
                ('continuation', continuation_item, new_rows)):
            if source_item is None:
                continue
            for row in selected:
                mode = row['mode']
                finding = campaign.flight_audit(source_item, mode, row)
                if not finding['valid']:
                    raise RuntimeError('fresh flight audit rejected ' + origin + ' ' +
                                       str((item['run'], mode, finding)))
                solid_path = Path(source_item['output']) / 'artifacts' / (
                    f"{item['map']}_run{item['run']}_{mode}.attempt1.solid_audit.json")
                solid = json.loads(solid_path.read_text())
                terminal = solid.get('terminal_stall_event')
                measurements = {}
                for key in tables.METRICS:
                    measurements[key] = (0.0 if key ==
                                         'filter_trajectory_guard_open_transitions'
                                         and mode == 'full' else finite(row, key))
                records.append(dict(map=item['map'], repeat=item['repeat'], run=item['run'],
                                    mode=mode,
                                    complete=(row['success'] == 'True' and
                                              row['waypoints_reached'] == row['n_waypoints']),
                                    contacts=int(finite(row, 'safety_collisions')),
                                    mission_time_s=finite(row, 'mission_time_s'),
                                    terminal_event=terminal['kind'] if terminal else '',
                                    **measurements))
                manifest.append(dict(map=item['map'], repeat=item['repeat'],
                                     run=item['run'], mode=mode, archive=origin,
                                     output=str(source_item['output']),
                                     stack_sha256=campaign.digest(campaign.stack_path(source_item, mode)),
                                     solid_audit_sha256=campaign.digest(solid_path),
                                     audit_valid=True))
    identities = [(row['map'], row['repeat'], row['mode']) for row in records]
    if len(records) != 210 or len(set(identities)) != 210 \
            or sum(item['archive'] == 'original' for item in manifest) != 72:
        raise RuntimeError('combined 210-flight manifest is not unique/complete')
    return records, manifest


def main():
    records, manifest = load_combined()
    output = campaign.COMPLETION
    with (output / 'final_flight_manifest.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(manifest[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(manifest)
    tables.ROOT = output
    tables.load = lambda: records
    tables.main()
    report = output / 'summary_no_cutoff.md'
    report.write_text(
        report.read_text().replace(
            '# c40 no-mission-cutoff seven-map results',
            '# c40 no-mission-cutoff seven-map results\n\n'
            'Provenance: 72 preserved original flights plus 138 unflown slots '
            'completed in a separate session; the original run96445 fixed-count '
            'audit verdict remains untouched. The corrected event-chain audit '
            'passes all 210 physical flights. There were no retries or replacements.', 1))
    print('MANIFEST:', output / 'final_flight_manifest.csv')


if __name__ == '__main__':
    main()
