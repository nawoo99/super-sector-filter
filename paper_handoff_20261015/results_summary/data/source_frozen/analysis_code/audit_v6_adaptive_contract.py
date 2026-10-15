#!/usr/bin/env python3
"""Read-only runtime-log audit of V6's Full/map/path/Sector recovery contract.

This analysis never launches ROS or changes runtime state.  It reads the frozen
campaign inventory and stack logs, then creates one *new* audit artifact.  It
does not establish continuous collision freedom or causal superiority of a mode.
"""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import sys


DEFAULT_CSV = Path('/root/super-sector-filter/results/'
                   'topology_polyline_v6_n10_completion_20261007/flights.csv')
DEFAULT_OUTPUT = Path('/root/super-sector-filter/results/'
                      'v6_frozen_20261008/adaptive_contract_audit.json')
MAIN_MAPS = {'gapfree_d1_m01', 'gapfree_d1_m02',
             'gapfree_d1_m03', 'gapfree_d1_m04',
             'gapfree_d1_m05r2', 'urban_blocks_u01', 'forest_cluster_f01'}
STAGES = {'seven_map_n10': MAIN_MAPS, 'forest_n10': {'forest_cluster_f01'}}
MODES = {'full', 'sector', 'adaptive'}
EVENT_TAGS = {'EVENT_RECOVERY_FULL', 'EVENT_RECOVERY_MAP_ACK',
              'EVENT_RECOVERY_PATH_READY', 'EVENT_RECOVERY_SECTOR',
              'SENSOR_ACQUISITION_FRAME'}
ANSI = re.compile(r'\x1b\[[0-9;]*[A-Za-z]')
TIME = re.compile(r'\[([0-9]+)\.([0-9]{1,9})\]')
FIELD = re.compile(r'(?<!\S)([A-Za-z_][A-Za-z0-9_]*)=([^\s]+)')


class AuditError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise AuditError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def positive(fields, name, zero=False):
    require(name in fields, 'missing field: ' + name)
    text = fields[name]
    require(re.fullmatch(r'[0-9]+', text) is not None,
            'non-integer field: ' + name)
    number = int(text)
    require(number >= (0 if zero else 1), 'invalid field: ' + name)
    return number


def parse_events(lines):
    events = []
    for line_number, raw_line in enumerate(lines, 1):
        line = ANSI.sub('', raw_line)
        present = [tag for tag in EVENT_TAGS if '[' + tag + ']' in line]
        if not present:
            continue
        require(len(present) == 1, f'ambiguous event at line {line_number}')
        tag = present[0]
        timestamp = TIME.search(line)
        require(timestamp is not None, f'missing log time at line {line_number}')
        log_ns = int(timestamp[1]) * 10**9 + int(timestamp[2].ljust(9, '0'))
        tail = line.split('[' + tag + ']', 1)[1]
        pairs = FIELD.findall(tail)
        fields = dict(pairs)
        require(len(fields) == len(pairs), f'duplicate field at line {line_number}')
        events.append({'tag': tag, 'log_time_ns': log_ns,
                       'line': line_number, 'fields': fields})
    return events


def audit_log(lines):
    events = parse_events(lines)
    full, ack, ready, sector = {}, {}, {}, {}
    source_frames, source_frame_ids = {}, set()
    for event in events:
        tag, fields = event['tag'], event['fields']
        if tag == 'SENSOR_ACQUISITION_FRAME':
            stamp = positive(fields, 'stamp_ns')
            frame = positive(fields, 'frame')
            positive(fields, 'cycle', zero=True)
            require(fields.get('full') in {'0', '1'}, 'invalid source Full flag')
            require(stamp not in source_frames and frame not in source_frame_ids,
                    'duplicate source frame or acquisition stamp')
            source_frames[stamp] = event
            source_frame_ids.add(frame)
            continue
        cycle_field = 'request_seq' if tag == 'EVENT_RECOVERY_PATH_READY' else 'cycle'
        cycle = positive(fields, cycle_field)
        table = {'EVENT_RECOVERY_FULL': full, 'EVENT_RECOVERY_MAP_ACK': ack,
                 'EVENT_RECOVERY_PATH_READY': ready,
                 'EVENT_RECOVERY_SECTOR': sector}[tag]
        require(cycle not in table, f'duplicate {tag} cycle {cycle}')
        table[cycle] = event
        if tag == 'EVENT_RECOVERY_FULL':
            positive(fields, 'input_boundary', zero=True)
        else:
            positive(fields, 'stamp_ns')
            if tag == 'EVENT_RECOVERY_PATH_READY':
                for name in ('ack_map', 'certified_map', 'generation_after'):
                    positive(fields, name)
                positive(fields, 'generation_before', zero=True)
            else:
                positive(fields, 'map')

    require(full, 'no Full recovery cycles observed')
    expected = set(range(1, len(full) + 1))
    require(set(full) == expected, 'non-contiguous Full cycle identifiers')
    require(set(ack) == set(ready) == set(sector) == expected,
            'missing, outstanding, or unsolicited cycle evidence')
    cycles = []
    for cycle in sorted(expected):
        f, a, r, s = full[cycle], ack[cycle], ready[cycle], sector[cycle]
        af, rf, sf = a['fields'], r['fields'], s['fields']
        stamp = int(af['stamp_ns'])
        acquisition = source_frames.get(stamp)
        require(acquisition is not None, f'no actual acquisition for cycle {cycle}')
        acquisition_fields = acquisition['fields']
        require(acquisition_fields['full'] == '1' and
                int(acquisition_fields['cycle']) == cycle,
                f'acknowledgement is not for a fresh Full frame: cycle {cycle}')
        require(stamp <= acquisition['log_time_ns'],
                f'acquisition stamp is later than acquisition log: cycle {cycle}')
        require(f['log_time_ns'] <= stamp <= acquisition['log_time_ns'] <=
                a['log_time_ns'] <= r['log_time_ns'] <= s['log_time_ns'],
                f'Full/acquisition/ack/path/Sector order violation: cycle {cycle}')
        if cycle > 1:
            require(sector[cycle - 1]['log_time_ns'] <= f['log_time_ns'],
                    f'overlapping or out-of-order Full cycles: cycle {cycle}')
        require(af['stamp_ns'] == rf['stamp_ns'] == sf['stamp_ns'],
                f'acquisition stamp identity mismatch: cycle {cycle}')
        require(af['map'] == rf['ack_map'] == sf['map'],
                f'acknowledged map identity mismatch: cycle {cycle}')
        require(int(rf['certified_map']) >= int(af['map']),
                f'path certificate predates acknowledged map: cycle {cycle}')
        require(int(rf['generation_after']) > int(rf['generation_before']),
                f'no new path generation: cycle {cycle}')
        require(sf.get('committed') == '1' and sf.get('planner_release') == '1',
                f'Sector return without committed/released path: cycle {cycle}')
        cycles.append({
            'cycle': cycle,
            'full_log_line': f['line'], 'full_log_time_ns': f['log_time_ns'],
            'input_boundary': int(f['fields']['input_boundary']),
            'source_full_frame': int(acquisition_fields['frame']),
            'source_full_frame_log_line': acquisition['line'],
            'source_full_frame_log_time_ns': acquisition['log_time_ns'],
            'acquisition_stamp_ns': stamp,
            'map_ack_log_line': a['line'], 'map_ack_log_time_ns': a['log_time_ns'],
            'ack_map': int(af['map']),
            'path_ready_log_line': r['line'], 'path_ready_log_time_ns': r['log_time_ns'],
            'certified_map': int(rf['certified_map']),
            'generation_before': int(rf['generation_before']),
            'generation_after': int(rf['generation_after']),
            'sector_return_log_line': s['line'],
            'sector_return_log_time_ns': s['log_time_ns'],
            'full_to_sector_s': (s['log_time_ns'] - f['log_time_ns']) / 1e9,
            'valid': True,
        })
    return {'valid': True, 'full_cycles': len(full), 'source_full_frame_matches': len(cycles),
            'map_acknowledgements': len(ack), 'path_ready': len(ready),
            'sector_returns': len(sector), 'outstanding_cycles': 0,
            'cycles': cycles}


def build_audit(csv_path):
    csv_path = csv_path.resolve(strict=True)
    csv_data = csv_path.read_bytes()
    rows = list(csv.DictReader(io.StringIO(csv_data.decode('utf-8'))))
    expected = {(stage, map_name, repeat, mode)
                for stage, maps in STAGES.items() for map_name in maps
                for repeat in range(1, 11) for mode in MODES}
    identities = set()
    physical_ids = set()
    for row in rows:
        require({'stage', 'map', 'repeat', 'mode', 'run', 'directory',
                 'stack_sha256', 'full_transitions'} <= row.keys(), 'missing CSV columns')
        identity = (row['stage'], row['map'], int(row['repeat']), row['mode'])
        require(identity in expected and identity not in identities,
                'unexpected or duplicated logical flight: ' + repr(identity))
        physical = (row['map'], int(row['run']), row['mode'])
        require(physical not in physical_ids, 'duplicate physical flight: ' + repr(physical))
        identities.add(identity)
        physical_ids.add(physical)
    require(identities == expected, 'campaign inventory is incomplete')

    hashes = {str(csv_path): sha256(csv_data)}
    groups = {stage: {'flights': 0, 'full_cycles': 0,
                     'source_full_frame_matches': 0, 'map_acknowledgements': 0,
                     'path_ready': 0, 'sector_returns': 0, 'outstanding_cycles': 0,
                     'valid': True} for stage in STAGES}
    audits = []
    for row in rows:
        if row['mode'] != 'adaptive':
            continue
        folder = Path(row['directory']).resolve(strict=True)
        require(folder.name == 'adaptive' and folder.parent.name == f"r{int(row['repeat']):02}",
                'flight folder identity mismatch')
        require(folder.parent.parent.name == row['map'], 'map folder identity mismatch')
        stack = folder / 'artifacts' / f"{row['map']}_run{row['run']}_adaptive.attempt1.stack.log"
        data = stack.read_bytes()
        digest = sha256(data)
        require(digest == row['stack_sha256'], 'stack hash mismatch: ' + str(stack))
        try:
            audited = audit_log(data.decode('utf-8').splitlines())
        except AuditError as error:
            raise AuditError(str(stack) + ': ' + str(error)) from error
        count_text = row['full_transitions']
        require(re.fullmatch(r'[0-9]+(?:\.0+)?', count_text) is not None,
                'invalid campaign Full transition count')
        require(int(count_text.split('.', 1)[0]) == audited['full_cycles'],
                'logged Full count disagrees with campaign inventory')
        hashes[str(stack)] = digest
        audited.update({'stage': row['stage'], 'map': row['map'],
                        'repeat': int(row['repeat']), 'run': int(row['run']),
                        'mode': row['mode'], 'stack_path': str(stack), 'stack_sha256': digest})
        audits.append(audited)
        group = groups[row['stage']]
        group['flights'] += 1
        for field in ('full_cycles', 'source_full_frame_matches', 'map_acknowledgements',
                      'path_ready', 'sector_returns', 'outstanding_cycles'):
            group[field] += audited[field]
    # Detect any concurrent evidence rewrite rather than freezing a mixed read.
    for path, digest in hashes.items():
        require(sha256(Path(path).read_bytes()) == digest, 'input changed during analysis: ' + path)
    script = Path(__file__).resolve()
    return {
        'schema': 'v6-adaptive-actual-log-contract-audit-v1',
        'valid': True,
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'analysis_only': True, 'simulation_launched': False, 'runtime_modified': False,
        'script_path': str(script), 'script_sha256': sha256(script.read_bytes()),
        'campaign_csv': str(csv_path), 'campaign_unique_physical_flights': len(physical_ids),
        'main_dataset_stage': 'seven_map_n10',
        'separate_gate_stage': 'forest_n10',
        'groups': groups, 'flight_audits': audits, 'input_sha256': hashes,
        'checks': [
            'Exact 210 MAIN plus 30 separate-gate logical and physical inventory',
            'Saved stack SHA256 equals actual attempt1 stack bytes',
            'No duplicate cycle/event fields, source frames, or acquisition stamps',
            'Contiguous Full cycles and exactly one matching ACK/PATH_READY/SECTOR per cycle',
            'Actual source full=1 acquisition has matching cycle and stamp_ns',
            'Full <= acquisition stamp <= acquisition log <= map ACK <= path ready <= Sector',
            'Previous Sector return precedes next Full cycle',
            'Matching cycle/request sequence, acquisition stamp, and acknowledged map',
            'Path certificate map >= ACK map and generation_after > generation_before',
            'Sector return has committed=1 and planner_release=1',
            'No missing, unsolicited, or outstanding cycles',
            'Inputs unchanged throughout analysis',
        ],
        'limitations': [
            'Evidence is actual runtime instrumentation and its event identities, not an independent physical sensor oracle.',
            'Event ordering does not establish continuous swept-volume collision freedom or population guarantees.',
            'No exclusive limited-FOV causal attribution of Sector failures is established.',
            'The separate Forest gate is not pooled into MAIN performance estimates.',
        ],
    }


def self_test():
    good = [
        '[INFO] [10.000000001] [EVENT_RECOVERY_FULL] cycle=1 input_boundary=5',
        '[INFO] [10.000000003] [SENSOR_ACQUISITION_FRAME] frame=6 cycle=1 full=1 stamp_ns=10000000002',
        '[INFO] [10.000000004] [EVENT_RECOVERY_MAP_ACK] cycle=1 stamp_ns=10000000002 map=6',
        '[INFO] [10.000000005] [EVENT_RECOVERY_PATH_READY] request_seq=1 stamp_ns=10000000002 ack_map=6 certified_map=7 generation_before=2 generation_after=3',
        '[INFO] [10.000000006] [EVENT_RECOVERY_SECTOR] cycle=1 stamp_ns=10000000002 map=6 committed=1 planner_release=1',
    ]
    require(audit_log(good)['full_cycles'] == 1, 'positive fixture failed')
    bad = [
        good + [good[0]],  # Duplicate Full announcement.
        good[:2] + good[3:],  # Missing ACK.
        good[:-1],  # Full cycle is left outstanding.
        [line.replace('full=1', 'full=0') for line in good],
        [line.replace('map=6 committed', 'map=8 committed') for line in good],
        [line.replace('ack_map=6', 'ack_map=8') for line in good],
        [line.replace('generation_after=3', 'generation_after=2') for line in good],
        [line.replace('planner_release=1', 'planner_release=0') for line in good],
        good[:4] + [good[4].replace('[10.000000006]', '[10.000000004]')],
        good + [good[1]],  # Duplicate acquisition frame/stamp.
        [good[0] + ' cycle=1'] + good[1:],  # Ambiguous repeated field.
        [good[0].replace('[10.000000001]', '[bad]')] + good[1:],
    ]
    for index, fixture in enumerate(bad, 1):
        try:
            audit_log(fixture)
        except AuditError:
            continue
        raise AuditError(f'negative fixture {index} was accepted')
    print(json.dumps({'self_test_valid': True, 'positive_fixtures': 1,
                      'negative_fixtures_rejected': len(bad)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--flights-csv', type=Path, default=DEFAULT_CSV)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    require(args.output.parent.is_dir(), 'output directory is not ready; no directory is created')
    require(not args.output.exists(), 'refusing to overwrite existing audit artifact')
    audit = build_audit(args.flights_csv)
    # Exclusive creation makes a race with another writer fail without overwrite.
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(audit, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({'valid': audit['valid'], 'output': str(args.output.resolve()),
                      'groups': audit['groups']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (AuditError, OSError, UnicodeError, KeyError, ValueError) as error:
        print('AUDIT FAILED: ' + str(error), file=sys.stderr)
        sys.exit(1)
