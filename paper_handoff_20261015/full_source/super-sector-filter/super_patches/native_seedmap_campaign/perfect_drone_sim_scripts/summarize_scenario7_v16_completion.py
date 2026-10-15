#!/usr/bin/env python3
"""Generate the provenance-explicit 210-flight c41 result manifest."""
import csv
import json
from pathlib import Path

import run_scenario7_v16_completion as campaign


def main():
    status = json.loads((campaign.CONTINUATION / 'status.json').read_text())
    if (status['state'] != 'COMPLETE' or len(status['completed']) != 39 or
            any(not item['valid'] for item in status['completed'])):
        raise RuntimeError('c41 continuation is not cleanly complete')
    campaign.check_hashes(json.loads(
        (campaign.CONTINUATION / 'frozen_identity.json').read_text()))
    campaign.check_hashes(json.loads(
        (campaign.CONTINUATION / 'preserved_identity.json').read_text()))
    plan, work = campaign.plan_and_work()
    campaign.posthoc_audit(plan)
    if len(work) != 39:
        raise RuntimeError('remaining plan changed')
    records = []
    for index, original_item in enumerate(plan):
        item = original_item if index < 31 else work[index - 31]
        archive = 'original' if index < 31 else 'continuation'
        output = Path(item['output'])
        finding = campaign.v15.validate_triplet(item, write=False)
        if not finding['valid']:
            raise RuntimeError('posthoc triplet audit failed: ' + str(item['run']))
        with (output / 'raw.csv').open(newline='') as stream:
            raw = list(csv.DictReader(stream))
        if [row['mode'] for row in raw] != item['modes']:
            raise RuntimeError('mode order differs from plan: ' + str(item['run']))
        for row in raw:
            mode = row['mode']
            outcome = finding['outcomes'][mode]
            stack_path = campaign.v15.corrected.stack_path(item, mode)
            flight_path = output / 'artifacts' / (
                f"{item['map']}_run{item['run']}_{mode}.attempt1.json")
            flight = json.loads(flight_path.read_text())
            records.append(dict(
                map=item['map'], repeat=item['repeat'], run=item['run'],
                mode=mode, archive=archive, output=str(output),
                complete=outcome['complete'],
                safety_collisions=int(outcome['safety_collisions']),
                safe_complete=outcome['safe_complete'],
                mission_time_s=outcome['mission_time_s'],
                terminal_condition=flight.get('terminal_condition') or '',
                end_to_end_cpu_cores_mean=outcome['end_to_end_cpu_cores_mean'],
                end_to_end_cpu_core_s=outcome['end_to_end_cpu_core_s'],
                map_payload_mib_s=outcome['map_payload_mib_s'],
                map_payload_mib_run=outcome['map_payload_bytes_total'] / 1048576,
                map_update_ms_mean=outcome['map_update_ms_mean'],
                full_open_transitions=outcome['full_open_transitions'],
                quality_valid=outcome['quality_valid'],
                stack_sha256=campaign.digest(stack_path),
                flight_sha256=campaign.digest(flight_path)))
    identities = [(row['map'], row['repeat'], row['mode']) for row in records]
    if (len(records) != 210 or len(set(identities)) != 210 or
            sum(row['archive'] == 'original' for row in records) != 93 or
            sum(row['archive'] == 'continuation' for row in records) != 117 or
            not all(row['quality_valid'] for row in records)):
        raise RuntimeError('210-flight cohort is incomplete or duplicated')
    output = campaign.CONTINUATION / 'final_flight_manifest.csv'
    with output.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]),
                                lineterminator='\n')
        writer.writeheader()
        writer.writerows(records)
    print('MANIFEST:', output)


if __name__ == '__main__':
    main()
