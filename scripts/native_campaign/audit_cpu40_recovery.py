#!/usr/bin/env python3
"""Strict, read-only source/recovery audit; log line order is not event order.

This checks completed recovery episodes. An open episode at shutdown is reported
separately, not silently counted as a completed recovery or an invalid closure.
It is not a substitute for contact, flight completion, or impossible-path tests.
"""
import argparse
from collections import defaultdict
from decimal import Decimal
import json
from pathlib import Path
import re


PATTERNS = {
    'source': re.compile(
        r'\[SENSOR_ACQUISITION_FRAME\] frame=(?P<frame>\d+) cycle=(?P<cycle>\d+) '
        r'full=(?P<full>\d+) stamp_ns=(?P<stamp_ns>\d+) width=(?P<width>\d+) '
        r'height=(?P<height>\d+) readback_pixels=(?P<readback_pixels>\d+) '
        r'conversion_rays=(?P<conversion_rays>\d+) generated_points=(?P<generated_points>\d+) '
        r'bytes=(?P<bytes>\d+) half_angle_deg=(?P<half_angle_deg>\S+)'),
    'open': re.compile(r'\[EVENT_RECOVERY_FULL\] cycle=(?P<cycle>\d+) input_boundary=(?P<input_boundary>\d+)'),
    'ack': re.compile(r'\[EVENT_RECOVERY_MAP_ACK\] cycle=(?P<cycle>\d+) stamp_ns=(?P<stamp_ns>\d+) map=(?P<map>\d+)'),
    'path': re.compile(
        r'\[EVENT_RECOVERY_PATH_READY\] request_seq=(?P<request_seq>\d+) '
        r'stamp_ns=(?P<stamp_ns>\d+) ack_map=(?P<ack_map>\d+) '
        r'certified_map=(?P<certified_map>\d+) generation_before=(?P<generation_before>\d+) '
        r'generation_after=(?P<generation_after>\d+)'),
    'close': re.compile(
        r'\[EVENT_RECOVERY_SECTOR\] cycle=(?P<cycle>\d+) stamp_ns=(?P<stamp_ns>\d+) '
        r'map=(?P<map>\d+) committed=(?P<committed>\d+) planner_release=(?P<planner_release>\d+)'),
    'fsm_ack': re.compile(
        r'\[FULL_REFRESH_RECOVERY_ACK\] request_seq=(?P<request_seq>\d+) '
        r'stamp_ns=(?P<stamp_ns>\d+) map=(?P<map>\d+) committed=(?P<committed>\d+)'),
}
MARKERS = {
    'source': '[SENSOR_ACQUISITION_FRAME]', 'open': '[EVENT_RECOVERY_FULL]',
    'ack': '[EVENT_RECOVERY_MAP_ACK]', 'path': '[EVENT_RECOVERY_PATH_READY]',
    'close': '[EVENT_RECOVERY_SECTOR]', 'fsm_ack': '[FULL_REFRESH_RECOVERY_ACK]',
}
ROS_TIME = re.compile(r'\[(?:INFO|WARN|ERROR|DEBUG|FATAL)\]\s+\[(\d+(?:\.\d+)?)\]')


def audit_text(text, mode='adaptive', require_all_closed=False):
    """Return JSON-compatible evidence and fail-closed checks for completed cycles."""
    if mode not in ('full', 'sector', 'adaptive'):
        raise ValueError('mode must be full, sector, or adaptive')
    records = {key: [] for key in PATTERNS}
    checks = dict(records_well_formed=True, source_records_present=True,
                  source_half_angle_45=True, source_shape_valid=True,
                  source_identity_unique=True, source_initial_mode_valid=True,
                  completed_cycles_one_to_one=True,
                  completed_cycles_fresh_full_source=True,
                  completed_cycles_exact_committed_ack=True,
                  completed_cycles_new_certified_path=True,
                  completed_cycles_timestamp_order=True)
    errors = []

    def fail(check, code, cycle=None, **details):
        checks[check] = False
        errors.append(dict(code=code, cycle=cycle, **details))

    for line_number, line in enumerate(text.splitlines(), 1):
        for kind, marker in MARKERS.items():
            if marker not in line:
                continue
            match = PATTERNS[kind].search(line)
            if not match:
                fail('records_well_formed', 'malformed_record', kind=kind,
                     line=line_number)
                continue
            record = {key: int(value) for key, value in match.groupdict().items()
                      if key != 'half_angle_deg'}
            if kind == 'source':
                angle = match.group('half_angle_deg')
                try:
                    valid_angle = Decimal(angle).is_finite() and Decimal(angle) == 45
                except ArithmeticError:
                    valid_angle = False
                record['half_angle_deg'] = angle
                if not valid_angle:
                    fail('source_half_angle_45', 'source_angle_not_45',
                         record['cycle'], frame=record['frame'], value=angle)
            timestamp = ROS_TIME.search(line)
            record['ros_time_ns'] = (int(Decimal(timestamp.group(1)) * 10**9)
                                     if timestamp else None)
            record['line'] = line_number
            records[kind].append(record)

    frames = records['source']
    if not frames:
        fail('source_records_present', 'no_source_records')
    frames_by_stamp = defaultdict(list)
    frame_ids = set()
    for frame in frames:
        frames_by_stamp[frame['stamp_ns']].append(frame)
        if frame['frame'] in frame_ids or len(frames_by_stamp[frame['stamp_ns']]) > 1:
            fail('source_identity_unique', 'duplicate_source_identity',
                 frame['cycle'], frame=frame['frame'], stamp_ns=frame['stamp_ns'])
        frame_ids.add(frame['frame'])
        width = 900 if frame['full'] else 225
        if not (frame['full'] in (0, 1) and frame['width'] == width and
                frame['height'] == 445 and frame['readback_pixels'] == 2 * width * 445 and
                frame['conversion_rays'] == width * 128 and
                frame['bytes'] == 32 * frame['generated_points']):
            fail('source_shape_valid', 'source_shape_mismatch', frame['cycle'],
                 frame=frame['frame'])
    if frames:
        first = min(frames, key=lambda frame: frame['frame'])
        if (mode == 'adaptive' and first['full'] != 0) or (
                mode == 'sector' and any(frame['full'] for frame in frames)) or (
                mode == 'full' and any(not frame['full'] for frame in frames)):
            fail('source_initial_mode_valid', 'unexpected_source_mode')

    by_cycle = {key: defaultdict(list) for key in ('open', 'ack', 'close')}
    for kind in by_cycle:
        for record in records[kind]:
            by_cycle[kind][record['cycle']].append(record)
    for kind in ('open', 'close'):
        for cycle, entries in by_cycle[kind].items():
            if cycle == 0 or len(entries) != 1:
                fail('completed_cycles_one_to_one', 'duplicate_or_zero_cycle',
                     cycle, kind=kind, count=len(entries))

    completed = []
    used_paths = set()
    timestamp_observed = 0
    for cycle, closures in sorted(by_cycle['close'].items()):
        error_start = len(errors)
        if len(closures) != 1:
            continue
        close = closures[0]
        opens = by_cycle['open'].get(cycle, [])
        acks = by_cycle['ack'].get(cycle, [])
        sources = frames_by_stamp.get(close['stamp_ns'], [])
        paths = [path for path in records['path']
                 if path['stamp_ns'] == close['stamp_ns'] and
                 path['ack_map'] == close['map']]
        if len(opens) != 1 or len(acks) != 1 or len(sources) != 1 or len(paths) != 1:
            fail('completed_cycles_one_to_one', 'missing_or_ambiguous_episode_record',
                 cycle, opens=len(opens), acks=len(acks), sources=len(sources),
                 paths=len(paths))
            completed.append(dict(cycle=cycle, valid=False, stamp_ns=close['stamp_ns']))
            continue
        opened, ack, source, path = opens[0], acks[0], sources[0], paths[0]
        if path['line'] in used_paths:
            fail('completed_cycles_one_to_one', 'path_certificate_reused', cycle)
        used_paths.add(path['line'])
        if not (source['full'] == 1 and source['cycle'] == cycle and
                source['frame'] > opened['input_boundary']):
            fail('completed_cycles_fresh_full_source', 'stale_or_wrong_cycle_source',
                 cycle, frame=source['frame'], source_cycle=source['cycle'],
                 input_boundary=opened['input_boundary'], full=source['full'])
        if not (close['committed'] == 1 and close['planner_release'] == 1 and
                close['map'] > 0 and ack['stamp_ns'] == close['stamp_ns'] and
                ack['map'] == close['map']):
            fail('completed_cycles_exact_committed_ack', 'ack_or_release_mismatch', cycle)
        if not (path['generation_after'] > path['generation_before'] and
                path['certified_map'] >= path['ack_map'] > 0):
            fail('completed_cycles_new_certified_path', 'invalid_new_path_certificate', cycle)

        def ordered(earlier, later, reason):
            if earlier is not None and later is not None and earlier > later:
                fail('completed_cycles_timestamp_order', reason, cycle,
                     earlier_ns=earlier, later_ns=later)

        # Render log lines may be flushed later; use acquisition stamp, NOT
        # source printf position/time, to establish the observation boundary.
        ordered(opened['ros_time_ns'], source['stamp_ns'], 'source_before_full_open')
        ordered(source['stamp_ns'], ack['ros_time_ns'], 'ack_before_observation')
        ordered(ack['ros_time_ns'], close['ros_time_ns'], 'sector_before_frontend_ack')
        ordered(path['ros_time_ns'], close['ros_time_ns'], 'sector_before_path')
        # Frontend ACK and FSM ACK subscriptions can be delivered in either
        # order. An exact committed FSM ACK can establish ACK-before-path even
        # when the frontend's own MAP_ACK log is later than PATH_READY.
        fsm_acks = [item for item in records['fsm_ack']
                    if item['request_seq'] == path['request_seq'] and
                    item['stamp_ns'] == path['stamp_ns'] and
                    item['map'] == path['ack_map'] and item['committed'] == 1]
        known_ack_times = [item['ros_time_ns'] for item in [ack, *fsm_acks]
                           if item['ros_time_ns'] is not None]
        earliest_ack = min(known_ack_times) if known_ack_times else None
        ordered(source['stamp_ns'], earliest_ack, 'committed_ack_before_observation')
        ordered(earliest_ack, path['ros_time_ns'], 'path_before_committed_ack')
        have_times = all(item['ros_time_ns'] is not None
                         for item in (opened, ack, path, close))
        timestamp_observed += int(have_times)
        completed.append(dict(cycle=cycle, valid=len(errors) == error_start,
                              source_frame=source['frame'], stamp_ns=source['stamp_ns'],
                              ack_map=ack['map'], certified_map=path['certified_map'],
                              generation_before=path['generation_before'],
                              generation_after=path['generation_after'],
                              timestamps_observed=have_times,
                              fsm_ack_evidence_count=len(fsm_acks)))

    outstanding = sorted(set(by_cycle['open']) - set(by_cycle['close']))
    if require_all_closed:
        checks['all_requested_cycles_closed'] = not outstanding
        if outstanding:
            errors.append(dict(code='outstanding_recovery_cycles', cycles=outstanding))
    return dict(schema='cpu40-source-recovery-audit-v1', mode=mode,
                valid=all(checks.values()), checks=checks, errors=errors,
                source_frames=len(frames), opened_cycles=len(by_cycle['open']),
                completed_cycles=completed, outstanding_cycles=outstanding,
                timestamp_observed_completed_cycles=timestamp_observed,
                unmatched_path_records=len(records['path']) - len(used_paths),
                require_all_closed=require_all_closed,
                scope='Source metadata and completed log episodes only; not physical safety proof')


def audit_file(path, mode='adaptive', require_all_closed=False):
    return audit_text(Path(path).read_text(errors='replace'), mode, require_all_closed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stack_log', type=Path)
    parser.add_argument('--mode', choices=('full', 'sector', 'adaptive'), default='adaptive')
    parser.add_argument('--require-all-closed', action='store_true')
    args = parser.parse_args()
    result = audit_file(args.stack_log, args.mode, args.require_all_closed)
    print(json.dumps(result, indent=2))
    return 0 if result['valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
