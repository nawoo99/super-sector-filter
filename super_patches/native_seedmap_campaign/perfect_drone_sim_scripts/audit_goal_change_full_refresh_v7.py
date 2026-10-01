#!/usr/bin/env python3
"""Audit new goals against Full observation, including an already-open cycle.

The older campaign verifier required four *new* goal-change Full requests.
That is too strict when a new waypoint arrives during an already-armed Full
cycle.  This verifier requires a complete matching Full/ACK/path/sector chain
for every one of the four later waypoint identities instead.
"""
import re


TAGS = {
    'setting': re.compile(r'\[GOAL_CHANGE_FULL_REFRESH_V6\][^\r\n]*enabled=(true|false)'),
    'identity': re.compile(r'\[MISSION_GOAL_IDENTITY\][^\r\n]*new_intent=1 new_identity=1[^\r\n]*waypoint=(\d+)'),
    'request': re.compile(r'\[GOAL_CHANGE_FULL_REFRESH_REQUEST\] request=(\d+)\b'),
    'arm': re.compile(r'\[FULL_REFRESH_RECOVERY_GATE_ARM\] min_request_seq=(\d+)\b'),
    'full': re.compile(r'\[EVENT_RECOVERY_FULL\] cycle=(\d+)\b'),
    'ack': re.compile(r'\[FULL_REFRESH_RECOVERY_ACK\] request_seq=(\d+)\b[^\r\n]*committed=1\b'),
    'path': re.compile(r'\[EVENT_RECOVERY_PATH_READY\] request_seq=(\d+)\b'),
    'sector': re.compile(r'\[EVENT_RECOVERY_SECTOR\] cycle=(\d+)\b[^\r\n]*planner_release=1\b'),
}


def events(stack):
    found = {name: [] for name in TAGS}
    received = []
    for index, line in enumerate(stack.splitlines()):
        for name, expression in TAGS.items():
            match = expression.search(line)
            if match:
                found[name].append((index, match.group(1)))
        if 'Receive click goal at:' in line:
            received.append(index)
    found['received'] = received
    return found


def audit(stack, mode):
    if mode not in ('full', 'sector', 'adaptive'):
        raise ValueError('unknown mode: ' + repr(mode))
    found = events(stack)
    expected = 'true' if mode == 'adaptive' else 'false'
    errors = []
    if [value for _, value in found['setting']] != [expected]:
        errors.append('one correct runtime setting required')
    request_numbers = [int(number) for _, number in found['request']]
    if request_numbers != list(range(1, len(request_numbers) + 1)):
        errors.append('goal-change request sequence is not unique and monotonic')
    if mode != 'adaptive':
        if request_numbers:
            errors.append('non-Adaptive mode emitted goal-change Full requests')
        return dict(valid=not errors, errors=errors, mode=mode,
                    request_count=len(request_numbers), covered_goals=[])
    identities = [(line, int(number)) for line, number in found['identity']]
    if [number for _, number in identities] != [0, 1, 2, 3, 4]:
        errors.append('expected exactly one ordered identity for waypoints 0..4')
        return dict(valid=False, errors=errors, mode=mode,
                    request_count=len(request_numbers), covered_goals=[])

    def lines(name, sequence):
        return [line for line, number in found[name] if int(number) == sequence]

    covered = []
    claimed_requests = []
    for goal in range(1, 5):
        start = identities[goal][0]
        prior = identities[goal - 1][0]
        stop = identities[goal + 1][0] if goal < 4 else len(stack.splitlines())
        in_span = [(line, int(number)) for line, number in found['request']
                   if start < line < stop]
        if len(in_span) > 1:
            errors.append(f'waypoint {goal}: multiple goal-change requests')
            continue
        if in_span:
            request_line, request_number = in_span[0]
            claimed_requests.append(request_line)
            candidates = [(line, int(number)) for line, number in found['arm']
                          if request_line < line < stop]
            candidates = [(line, number) for line, number in candidates
                          if (any(line < full < stop for full in lines('full', number))
                              and any(line < ack < stop for ack in lines('ack', number)))]
            method = 'new_goal_change_request'
        else:
            candidates = [(line, int(number)) for line, number in found['arm']
                          if prior < line < start]
            candidates = [(line, number) for line, number in candidates
                          if (any(line < full < start for full in lines('full', number))
                              and not any(line < sector < start
                                          for sector in lines('sector', number))
                              and any(start < ack < stop
                                      for ack in lines('ack', number)))]
            method = 'already_open_full_refresh'
        if not candidates:
            errors.append(f'waypoint {goal}: missing {method} Full cycle')
            continue
        # Additional obstacle-triggered cycles can occur before the *next*
        # waypoint.  The goal request owns the first subsequent arm; an
        # already-open goal is covered by the latest arm still open at arrival.
        arm_line, sequence = (candidates[0] if in_span else candidates[-1])
        full = lines('full', sequence)
        ack = lines('ack', sequence)
        path = lines('path', sequence)
        sector = lines('sector', sequence)
        if (len(full) != 1 or len(ack) != 1 or not path or len(sector) != 1
                or not arm_line < full[0] < ack[0] < path[-1] < sector[0] < stop
                or not start < ack[0]
                or not any(start < receive < path[-1] for receive in found['received'])):
            errors.append(f'waypoint {goal}: Full/ACK/new-goal/path/sector chain incomplete')
            continue
        if method == 'new_goal_change_request' and not start < request_line < arm_line:
            errors.append(f'waypoint {goal}: new request/arm ordering invalid')
            continue
        if method == 'already_open_full_refresh' and not full[0] < start:
            errors.append(f'waypoint {goal}: Full was not open before goal arrival')
            continue
        covered.append(dict(waypoint=goal, method=method, cycle=sequence))
    if sorted(claimed_requests) != sorted(line for line, _ in found['request']):
        errors.append('unmatched goal-change request')
    if len(covered) != 4:
        errors.append('not all four later waypoints received certified Full coverage')
    return dict(valid=not errors, errors=errors, mode=mode,
                request_count=len(request_numbers), covered_goals=covered)
