#!/usr/bin/env python3
"""Explicit failure retention for the separate scenario7 repair revision.

No timing, safety, retry, or admission threshold is changed here. A failed
measurement remains failed even when another independent mode can be observed.
"""
from __future__ import annotations

import json
import os
from pathlib import Path


SCHEMA = 'scenario7-preflight-control-v1'
RECEIVED_ODOMETRY_CHECKS = frozenset({
    'odometry_cadence', 'odometry_header_p99', 'odometry_header_max',
    'odometry_receipt_p99', 'odometry_receipt_max',
})


def failed_checks(checks):
    return sorted(key for key, value in checks.items() if value is not True)


def inspect_profile_reference(folder, modes):
    """Collect every missing/unreadable/malformed document without launching."""
    documents, errors = {}, []
    for name in ('plan.json', *(f'{mode}_summary.json' for mode in modes)):
        path = (Path(folder) / name).resolve()
        try:
            value = json.loads(path.read_text())
            if not isinstance(value, dict):
                raise ValueError('Expected a JSON object')
            documents[name] = value
        except (OSError, ValueError) as error:
            errors.append(dict(file=str(path), reason=(
                'missing_reference_document' if isinstance(error, FileNotFoundError)
                else 'invalid_reference_document'), detail=str(error)))
    return dict(valid=not errors, folder=str(Path(folder).resolve()), errors=errors,
                documents=documents)


def blocked_reference(args, reasons, save, *, output_exists=False):
    """Retain a structured non-flight outcome; never manufacture raw rows."""
    root = Path(args.output)
    if not output_exists:
        root.mkdir(parents=True, exist_ok=False)
    status = dict(schema=SCHEMA, state='BLOCKED_BY_PREFLIGHT', pid=os.getpid(),
                  candidate=args.candidate, map=args.map, run=args.run,
                  requested_modes=list(args.modes), unexecuted_modes=list(args.modes),
                  completed=0, flights_started=False, preflight_valid=False,
                  off_eligible=False, no_automatic_retry=True, reasons=reasons)
    save(root / 'preflight_blocked.json', status)
    save(root / 'status.json', status)
    print('BLOCKED_BY_PREFLIGHT', json.dumps(status), flush=True)
    return 2


def timing_diagnosis(result):
    timing = result.get('small_pool_timing', {})
    odom = result.get('message_intervals', {}).get('odometry', {})
    return dict(
        failed_checks=failed_checks(timing.get('checks', {})),
        received_odometry_hz=odom.get('mean_received_hz'),
        header_p99_ms=odom.get('header_interval', {}).get('p99_ms'),
        producer_fsm_callback_hz=timing.get('callback_hz', {}),
        thresholds_unchanged=True, all_observed_intervals_retained=True,
        scope='Received odometry includes producer, transport and observer effects; '
              'FSM callback counts are separate measurements, not odometry publisher counts.',
        root_cause='unresolved_without_producer_transport_observer_evidence')


def continuation_allowed(result, *, profile_cpu):
    """Only received-odometry timing failures may continue ON observations.

    Callback/source/resource/order/geometry failures are deliberately not
    catch-all recoverable exceptions. Full and Adaptive must also have completed
    without contact; Sector outcomes retain their predeclared metric semantics.
    """
    checks = result.get('source_acquisition', {}).get('checks', {})
    timing = result.get('small_pool_timing', {})
    failures = set(failed_checks(timing.get('checks', {})))
    solid = result.get('solid_obstacle_audit', {})
    mode = result.get('mode')
    safe = (mode == 'sector' or (
        result.get('success') is True and result.get('safety_collisions') == 0
        and solid.get('completion') is True and solid.get('contact_episodes') == 0))
    return (profile_cpu is True and result.get('cpu_profile') is True
            and mode in ('full', 'sector', 'adaptive')
            and all(result.get(key) is True for key in
                    ('run_valid', 'resource_valid', 'speed_limit_valid'))
            and solid.get('audit_valid') is True and safe
            and failed_checks(checks) == ['small_pool_timing']
            and timing.get('valid') is False
            and bool(failures) and failures <= RECEIVED_ODOMETRY_CHECKS
            and timing.get('callback_counts_instrumented') is True
            and all(timing.get('checks', {}).get(key) is True for key in
                    ('sensor_cadence', 'odometry_order', 'fsm_main_callback',
                     'fsm_command_callback', 'profile_callback_coverage')))


def retain_mode_failure(result, *, profile_cpu, campaign, process_iter, flight_names):
    """Check classification and teardown before permitting a subsequent mode."""
    if not continuation_allowed(result, profile_cpu=profile_cpu):
        raise RuntimeError('Source/recovery contract failure; stop for diagnosis')
    campaign.cleanup_active_process_groups()
    if campaign._ACTIVE_PROCESS_GROUPS:
        raise RuntimeError('Cannot continue: campaign process groups remain active')
    for proc in process_iter(['cmdline']):
        command = proc.info.get('cmdline') or []
        if command and Path(command[0]).name in set(flight_names) | {'waypoint_mission'}:
            raise RuntimeError('Cannot continue: a flight process remains active')
    return dict(mode=result['mode'], reason='received_odometry_timing_failed',
                checks=failed_checks(result['source_acquisition']['checks']),
                diagnosis=timing_diagnosis(result), failure_retained=True,
                preflight_valid=False, off_eligible=False, teardown_verified=True)


def final_status(args, results, retained, comparison):
    return dict(schema=SCHEMA, pid=os.getpid(),
                state='COMPLETE_WITH_RETAINED_FAILURES' if retained else 'COMPLETE',
                candidate=args.candidate, completed=len(results),
                observed_modes=[row['mode'] for row in results],
                unexecuted_modes=[mode for mode in args.modes
                                  if mode not in {row['mode'] for row in results}],
                retained_failures=retained, comparison=comparison,
                # Full reference acceptance still requires every inherited gate.
                preflight_valid=False if retained else None,
                off_eligible=False if retained else None,
                no_automatic_retry=True)
