#!/usr/bin/env python3
"""Resume only unflown c40 slots after correcting the log-only source audit.

The 72 original physical flights and their frozen files are never rewritten.
No planner, simulation, timeout, mode, or map setting is changed here.
"""
import csv
from datetime import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

import audit_goal_change_full_refresh_v7 as goal_audit
import run_scenario7_v7_n10 as base
import run_scenario7_v13_n10 as v13
import run_scenario7_v14_n10 as v14


ORIGINAL = Path('/root/super-sector-filter/results/scenario7_no_mission_cutoff_v14_n10_20261001')
COMPLETION = Path('/root/super-sector-filter/results/scenario7_no_mission_cutoff_v14_n10_completion_20261001')
THIS_FILE = Path(__file__).resolve()
PROTOCOL = COMPLETION / 'protocol.json'
AUDITOR = THIS_FILE.with_name('audit_goal_change_full_refresh_v7.py')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rows(path):
    if not path.is_file():
        return []
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def frozen_inputs():
    original = json.loads((ORIGINAL / 'frozen_identity.json').read_text())
    extra = {str(path): digest(path) for path in (THIS_FILE, AUDITOR, PROTOCOL)}
    return original | extra


def check_frozen(expected):
    changed = [path for path, expected_hash in expected.items()
               if not Path(path).is_file() or digest(path) != expected_hash]
    if changed:
        raise RuntimeError('frozen input changed: ' + ', '.join(changed))


def stack_path(item, mode):
    return Path(item['output']) / 'artifacts' / (
        f"{item['map']}_run{item['run']}_{mode}.attempt1.stack.log")


def worklist():
    plan = json.loads((ORIGINAL / 'plan.json').read_text())['commands']
    if len(plan) != 70:
        raise RuntimeError('original 70-triplet plan missing')
    work = []
    preserved = 0
    preserved_items = []
    for item in plan:
        actual = rows(Path(item['output']) / 'raw.csv')
        modes = [row['mode'] for row in actual]
        if modes != item['modes'][:len(modes)]:
            raise RuntimeError('original mode order differs from plan: ' + str(item))
        for mode in modes:
            if not stack_path(item, mode).is_file():
                raise RuntimeError('preserved log missing: ' + str(stack_path(item, mode)))
        preserved += len(modes)
        if modes:
            preserved_items.append(item)
        missing = item['modes'][len(modes):]
        if missing:
            output = COMPLETION / item['stage'] / item['map'] / Path(item['output']).name
            work.append(item | {'modes': missing, 'output': str(output)})
    if preserved != 72 or len(preserved_items) != 24 or len(work) != 46 \
            or sum(len(item['modes']) for item in work) != 138:
        raise RuntimeError('preserved count or remaining work changed')
    if work[0]['run'] != 96446 or work[0]['modes'] != ['full', 'sector', 'adaptive']:
        raise RuntimeError('first unflown slot differs from original plan')
    return plan, work


def flight_audit(item, mode, row):
    output = Path(item['output'])
    stack = stack_path(item, mode).read_text(errors='replace')
    summary_path = output / f'{mode}_summary.json'
    summary = json.loads(summary_path.read_text()) if summary_path.is_file() else {}
    checks = summary.get('source_acquisition', {}).get('checks', {})
    common = (base.truth(row.get('run_valid')) is True and
              base.truth(row.get('resource_valid')) is True and
              base.truth(row.get('speed_limit_valid')) is True and
              base.truth(row.get('infrastructure_failure')) is False and
              base.number(row.get('attempt_count')) == 1 and
              base.number(row.get('retry_count')) == 0)
    source = bool(checks) and all(value is True for value in checks.values())
    recovery = summary.get('strict_recovery_audit', {}).get('valid') is True
    bounded = v13.bounded_recovery_runtime_audit(stack)['valid']
    heading = True
    if mode in ('sector', 'adaptive'):
        policy = 'body_aligned_event=0 velocity_center=' + ('0' if mode == 'sector' else '1')
        heading = len(re.findall(r'\[SECTOR_HEADING_POLICY\][^\r\n]*' + policy, stack)) == 1
    complete = (base.truth(row.get('success')) is True and
                row.get('waypoints_reached') == row.get('n_waypoints') and
                base.number(row.get('n_waypoints')) == 5)
    contacts = base.number(row.get('safety_collisions'))
    event = goal_audit.audit(stack, mode)
    no_cutoff = v14.no_cutoff_audit(item, mode)
    result = dict(common=common, source=source, recovery=recovery, bounded=bounded,
                  heading=heading, goal_change_event_audit=event,
                  no_mission_cutoff_audit=no_cutoff, complete=complete,
                  contacts=contacts, safe_complete=complete and contacts == 0)
    result['valid'] = all((common, source, recovery, bounded, heading,
                           event['valid'], no_cutoff['valid'])) and (
        mode == 'sector' or result['safe_complete'])
    return result


def validate(item, returncode, write=True):
    output = Path(item['output'])
    actual = rows(output / 'raw.csv')
    errors = []
    if len(actual) != len(item['modes']) or [row['mode'] for row in actual] != item['modes']:
        errors.append('exact mode count/order mismatch')
    findings = {}
    for row in actual:
        mode = row.get('mode')
        if mode not in item['modes'] or mode in findings:
            errors.append('unexpected or duplicate mode: ' + str(mode))
            continue
        try:
            finding = flight_audit(item, mode, row)
        except (OSError, ValueError, KeyError, TypeError) as error:
            finding = dict(valid=False, error=repr(error))
        findings[mode] = finding
        if not finding['valid']:
            errors.append(mode + ': source/resource/runtime or safe-completion audit failed')
    if returncode != 0:
        errors.append('child returned ' + str(returncode))
    report = dict(item=item, returncode=returncode, valid=not errors,
                  errors=errors, findings=findings)
    if write:
        base.atomic_json(output / 'continuation_validation.json', report)
    return report


def verify_original(plan):
    status = json.loads((ORIGINAL / 'status.json').read_text())
    completed = status.get('completed', [])
    if status.get('state') != 'STOPPED_FOR_DIAGNOSIS' or len(completed) != 24:
        raise RuntimeError('original stop/flight count changed')
    if any(not item['valid'] for item in completed[:23]):
        raise RuntimeError('original earlier triplets were not valid')
    if (completed[-1]['run'] != 96445 or completed[-1]['returncode'] != 0 or
            completed[-1]['errors'] != ['adaptive: v6 source-scope audit failed']):
        raise RuntimeError('original stop reason differs from audited one')
    findings = []
    for item in plan[:24]:
        finding = validate(item, 0, write=False)
        findings.append(dict(run=item['run'], map=item['map'],
                             valid=finding['valid'], findings=finding['findings'],
                             errors=finding['errors']))
    if len(findings) != 24 or not all(item['valid'] for item in findings):
        raise RuntimeError('preserved 72 flights fail corrected posthoc audit')
    return findings


def command(item):
    common = [arg for arg in base.COMMON if arg != '--event-body-heading']
    return [sys.executable, '-u', str(v14.WRAPPER), '--candidate', v14.CANDIDATE,
            *common, '--map', item['map'], '--run', str(item['run']),
            '--output', item['output'], '--modes', *item['modes']]


def main():
    if any(arg != '--dry-run' for arg in sys.argv[1:]):
        raise SystemExit('only --dry-run is accepted')
    dry_run = '--dry-run' in sys.argv[1:]
    frozen = frozen_inputs()
    check_frozen(frozen)
    v13.verify_runtime_install()
    protocol = json.loads(PROTOCOL.read_text())
    if (protocol['candidate'] != v14.CANDIDATE or
            protocol['preserved_flights'] != 72 or
            protocol['remaining_flights'] != 138):
        raise RuntimeError('completion protocol mismatch')
    plan, work = worklist()
    original_findings = verify_original(plan)
    if dry_run:
        print(json.dumps(dict(preserved_flights=72, remaining_flights=138,
                              items=len(work), first=work[0], last=work[-1],
                              frozen_files=len(frozen)), indent=2))
        return 0
    if (COMPLETION / 'status.json').exists():
        raise RuntimeError('completion already started; no implicit rerun')
    if any(Path(item['output']).exists() for item in work):
        raise RuntimeError('a completion output path already exists')
    lock = open('/tmp/super_sector_filter_scenario7_v7_n10.lock', 'a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    base.atomic_json(COMPLETION / 'frozen_identity.json', frozen)
    base.atomic_json(COMPLETION / 'worklist.json', work)
    base.atomic_json(COMPLETION / 'posthoc_goal_change_audit_v1.json',
                     dict(preserved_flights=72, valid_flights=72, triplets=original_findings,
                          original_archive=str(ORIGINAL), original_archive_modified=False))
    started = time.monotonic()
    completed = []
    current = None

    def status(state, **extra):
        base.atomic_json(COMPLETION / 'status.json',
                         dict(state=state, pid=os.getpid(), current=current,
                              completed=completed, elapsed_s=time.monotonic()-started,
                              updated_local=datetime.now().astimezone().isoformat(), **extra))

    env = {key: value for key, value in os.environ.items() if not key.startswith('SUPER_')}
    env['PYTHONNOUSERSITE'] = '1'
    try:
        status('RUNNING')
        for item in work:
            check_frozen(frozen)
            current = item
            output = Path(item['output'])
            if output.exists():
                raise RuntimeError('completion output already exists: ' + str(output))
            output.parent.mkdir(parents=True, exist_ok=True)
            status('RUNNING')
            print('START', item['map'], item['repeat'], item['run'], item['modes'], flush=True)
            with output.with_suffix('.controller.log').open('x', buffering=1) as stream:
                child = subprocess.Popen(command(item), cwd=base.REPO, env=env,
                                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                         text=True, bufsize=1)
                assert child.stdout is not None
                for line in child.stdout:
                    stream.write(line)
                    if line.startswith(('RESULT ', 'COMPARISON ', 'STOPPED:')):
                        print(line, end='', flush=True)
                returncode = child.wait()
            result = validate(item, returncode)
            completed.append(dict(run=item['run'], map=item['map'], repeat=item['repeat'],
                                  modes=item['modes'], valid=result['valid'],
                                  errors=result['errors']))
            print('FINISH', json.dumps(completed[-1]), flush=True)
            if not result['valid']:
                raise RuntimeError('blocking completion failure: ' + repr(completed[-1]))
        status('COMPLETE', completed_flights=138, total_flights=210)
        return 0
    except BaseException as error:
        status('STOPPED_FOR_DIAGNOSIS', error=repr(error))
        print('STOPPED:', repr(error), file=sys.stderr, flush=True)
        raise
    finally:
        lock.close()


if __name__ == '__main__':
    raise SystemExit(main())
