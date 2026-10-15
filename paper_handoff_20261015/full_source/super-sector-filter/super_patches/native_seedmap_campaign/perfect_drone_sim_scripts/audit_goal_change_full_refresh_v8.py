#!/usr/bin/env python3
"""Extend v7 for a goal request made during an already ACKed Full cycle.

The overlap is accepted only if Full sensing continues after the new goal,
the new goal is received, and a newer certified map is used for a path before
Sector release. This is a read-only log audit; it changes no flight behavior.
"""
import re

import audit_goal_change_full_refresh_v7 as v7


FRAME = re.compile(r'\[SENSOR_ACQUISITION_FRAME\][^\r\n]*\bfull=1\b')
PATH_MAP = re.compile(
    r'\[EVENT_RECOVERY_PATH_READY\] request_seq=(\d+)\b[^\r\n]*'
    r'ack_map=(\d+)\b[^\r\n]*certified_map=(\d+)\b')


def audit(stack, mode):
    result = v7.audit(stack, mode)
    if result['valid'] or mode != 'adaptive':
        return result
    # Never relax source, identity, sequence, or any unrelated failure.
    missing = [re.fullmatch(
        r'waypoint ([1-4]): missing new_goal_change_request Full cycle', error)
        for error in result['errors']]
    matches = [match for match in missing if match is not None]
    if (len(matches) != 1 or len(result['errors']) != 2 or
            'not all four later waypoints received certified Full coverage'
            not in result['errors']):
        return result

    goal = int(matches[0].group(1))
    found = v7.events(stack)
    lines = stack.splitlines()
    identities = [(line, int(number)) for line, number in found['identity']]
    start = identities[goal][0]
    stop = identities[goal + 1][0] if goal < 4 else len(lines)
    requests = [(line, int(number)) for line, number in found['request']
                if start < line < stop]
    if len(requests) != 1:
        return result
    request_line, _ = requests[0]
    # The latest Full cycle must still be open at goal arrival; its ACK may
    # predate the goal, but its certified reroute must not.
    candidates = []
    for arm_line, sequence_text in found['arm']:
        sequence = int(sequence_text)
        full = [line for line, number in found['full']
                if int(number) == sequence]
        ack = [line for line, number in found['ack']
               if int(number) == sequence]
        sector = [line for line, number in found['sector']
                  if int(number) == sequence]
        if (arm_line < start and len(full) == len(ack) == len(sector) == 1
                and arm_line < full[0] < ack[0] < start < sector[0] < stop):
            candidates.append((arm_line, sequence, ack[0], sector[0]))
    if not candidates:
        return result
    arm_line, sequence, ack_line, sector_line = max(candidates)
    path_lines = [(line, match) for line, text in enumerate(lines)
                  if (match := PATH_MAP.search(text)) and
                  int(match.group(1)) == sequence and
                  request_line < line < sector_line]
    if len(path_lines) != 1:
        return result
    path_line, path = path_lines[0]
    if (int(path.group(3)) <= int(path.group(2)) or
            not any(request_line < line < path_line for line in found['received']) or
            not any(request_line < line < path_line and FRAME.search(lines[line])
                    for line in range(request_line + 1, path_line))):
        return result
    result['errors'] = []
    result['valid'] = True
    result['covered_goals'].append(dict(
        waypoint=goal, method='request_during_open_acked_full', cycle=sequence,
        post_goal_full_frame=True, certified_map=int(path.group(3)),
        acknowledged_map=int(path.group(2))))
    result['covered_goals'].sort(key=lambda entry: entry['waypoint'])
    return result
