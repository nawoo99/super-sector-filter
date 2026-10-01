#!/usr/bin/env python3
"""Complete only the unflown slots of the preserved c39 campaign."""
from datetime import datetime
import csv
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

import run_scenario7_v7_n10 as base
import run_scenario7_v13_n10 as v13


ORIGINAL = Path('/root/super-sector-filter/results/scenario7_bounded_recovery_v13_n10_v2_20260930')
COMPLETION = Path('/root/super-sector-filter/results/scenario7_bounded_recovery_v13_n10_v2_completion_20261001')
AUDITOR = Path('/root/super-sector-filter/scripts/native_campaign/audit_cpu40_recovery.py')
THIS_FILE = Path(__file__).resolve()
PROTOCOL = COMPLETION / 'protocol.json'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def csv_rows(path):
    if not path.is_file():
        return []
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def frozen_inputs():
    original = json.loads((ORIGINAL / 'frozen_identity.json').read_text())
    extra = {str(path): digest(path) for path in (THIS_FILE, AUDITOR, PROTOCOL)}
    return original | extra


def check_frozen(expected):
    changes = [path for path, hexdigest in expected.items()
               if not Path(path).is_file() or digest(path) != hexdigest]
    if changes:
        raise RuntimeError('frozen input changed: ' + ', '.join(changes))


def worklist():
    plan = json.loads((ORIGINAL / 'plan.json').read_text())['commands']
    work = []
    original_flights = 0
    for item in plan:
        actual = csv_rows(Path(item['output']) / 'raw.csv')
        modes = [row['mode'] for row in actual]
        if modes != item['modes'][:len(modes)]:
            raise RuntimeError(f'existing mode order differs from protocol: {item}')
        for mode in modes:
            path = Path(item['output']) / 'artifacts' / (
                f"{item['map']}_run{item['run']}_{mode}.attempt1.stack.log")
            if not path.is_file():
                raise RuntimeError(f'existing flight log missing: {path}')
        original_flights += len(modes)
        remaining = item['modes'][len(modes):]
        if remaining:
            output = COMPLETION / item['stage'] / item['map'] / Path(item['output']).name
            work.append(item | {'modes': remaining, 'output': str(output)})
    if original_flights != 173 or len(work) != 13 or sum(len(item['modes']) for item in work) != 37:
        raise RuntimeError('preserved flight count or completion worklist changed')
    if work[0]['run'] != 96292 or work[0]['modes'] != ['full']:
        raise RuntimeError('first completion slot is not the unflown Map3 Full')
    return work


def verify_original():
    if json.loads((ORIGINAL / 'stage1_gate.json').read_text())['valid'] is not True:
        raise RuntimeError('original stage1 gate was not valid')
    report = json.loads((ORIGINAL / 'posthoc_recovery_audit_v2.json').read_text())
    if report['flight_count'] != 173 or report['reaudit_valid_count'] != 173:
        raise RuntimeError('preserved recovery logs did not all pass re-audit')
    frozen = frozen_inputs()
    check_frozen(frozen)
    v13.verify_runtime_install()
    protocol = json.loads(PROTOCOL.read_text())
    if protocol['candidate'] != v13.CANDIDATE or protocol['remaining_flights'] != 37:
        raise RuntimeError('completion protocol does not match campaign')
    return frozen


def command(item):
    # v12 removes event-body-heading from the inherited v7 command. The
    # selected v6 child, profiles and all other arguments remain identical.
    common = [arg for arg in base.COMMON if arg != '--event-body-heading']
    return [sys.executable, '-u', str(base.WRAPPER), '--candidate', v13.CANDIDATE,
            *common, '--map', item['map'], '--run', str(item['run']),
            '--output', item['output'], '--modes', *item['modes']]


def validate(item, returncode):
    output = Path(item['output'])
    rows = csv_rows(output / 'raw.csv')
    errors = []
    if len(rows) != len(item['modes']) or [row['mode'] for row in rows] != item['modes']:
        errors.append('expected exactly one flight row per remaining mode, in order')
    by_mode = {row.get('mode'): row for row in rows}
    findings = {}
    for mode in item['modes']:
        row = by_mode.get(mode, {})
        summary_path = output / f'{mode}_summary.json'
        summary = json.loads(summary_path.read_text()) if summary_path.is_file() else {}
        stack_path = output / 'artifacts' / (
            f"{item['map']}_run{item['run']}_{mode}.attempt1.stack.log")
        stack = stack_path.read_text(errors='replace') if stack_path.is_file() else ''
        counts = base.log_counts(stack)
        common = (base.truth(row.get('run_valid')) is True and
                  base.truth(row.get('resource_valid')) is True and
                  base.truth(row.get('speed_limit_valid')) is True and
                  base.truth(row.get('infrastructure_failure')) is False and
                  base.number(row.get('attempt_count')) == 1 and
                  base.number(row.get('retry_count')) == 0)
        source_scope = (counts['enabled_true'] == int(mode == 'adaptive') and
                        counts['enabled_false'] == int(mode != 'adaptive') and
                        counts['requests'] == (4 if mode == 'adaptive' else 0))
        source_checks = summary.get('source_acquisition', {}).get('checks', {})
        source = bool(source_checks) and all(value is True for value in source_checks.values())
        recovery = summary.get('strict_recovery_audit', {}).get('valid') is True
        bounded = v13.bounded_recovery_runtime_audit(stack)['valid']
        heading = True
        if mode in ('sector', 'adaptive'):
            policy = 'body_aligned_event=0 velocity_center=' + ('0' if mode == 'sector' else '1')
            heading = len(re.findall(r'\[SECTOR_HEADING_POLICY\][^\r\n]*' + policy, stack)) == 1
        complete = (base.truth(row.get('success')) is True and
                    row.get('waypoints_reached') == row.get('n_waypoints') and
                    base.number(row.get('n_waypoints')) == 5)
        contact = base.number(row.get('safety_collisions'))
        safe = complete and contact == 0
        findings[mode] = dict(common=common, source_scope=source_scope,
                              source=source, recovery=recovery, bounded=bounded,
                              heading=heading, complete=complete,
                              contact=contact, safe=safe)
        if not all((common, source_scope, source, recovery, bounded, heading)):
            errors.append(mode + ': source/resource/runtime audit failed')
        if mode in ('full', 'adaptive') and not safe:
            errors.append(mode + ': required safe completion failed')
    if returncode != 0:
        errors.append('child returned ' + str(returncode))
    result = dict(item=item, returncode=returncode, valid=not errors,
                  errors=errors, findings=findings)
    base.atomic_json(output / 'continuation_validation.json', result)
    return result


def main():
    dry_run = '--dry-run' in sys.argv[1:]
    if any(arg != '--dry-run' for arg in sys.argv[1:]):
        raise SystemExit('only --dry-run is accepted')
    frozen = verify_original()
    work = worklist()
    if dry_run:
        print(json.dumps(dict(items=len(work), flights=sum(len(item['modes']) for item in work),
                              first=work[0], last=work[-1], frozen_files=len(frozen)), indent=2))
        return 0
    if (COMPLETION / 'status.json').exists():
        raise RuntimeError('existing completion status refused; no implicit retry')
    lock = open('/tmp/super_sector_filter_scenario7_v7_n10.lock', 'a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    base.atomic_json(COMPLETION / 'frozen_identity.json', frozen)
    base.atomic_json(COMPLETION / 'worklist.json', work)
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
                raise RuntimeError(f'completion output already exists: {output}')
            output.parent.mkdir(parents=True, exist_ok=True)
            status('RUNNING')
            print('START', item['map'], item['repeat'], item['run'], item['modes'], flush=True)
            with output.with_suffix('.controller.log').open('x', buffering=1) as stream:
                process = subprocess.Popen(command(item), cwd=base.REPO, env=env,
                                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                           text=True, bufsize=1)
                assert process.stdout is not None
                for line in process.stdout:
                    stream.write(line)
                    if line.startswith(('RESULT ', 'COMPARISON ', 'STOPPED:')):
                        print(line, end='', flush=True)
                returncode = process.wait()
            result = validate(item, returncode)
            completed.append(dict(run=item['run'], map=item['map'], repeat=item['repeat'],
                                  modes=item['modes'], valid=result['valid'],
                                  errors=result['errors']))
            print('FINISH', json.dumps(completed[-1]), flush=True)
            if not result['valid']:
                raise RuntimeError('blocking completion failure: ' + repr(completed[-1]))
        status('COMPLETE', completed_flights=sum(len(item['modes']) for item in work))
        return 0
    except BaseException as error:
        status('STOPPED_FOR_DIAGNOSIS', error=repr(error))
        print('STOPPED:', repr(error), file=sys.stderr, flush=True)
        raise
    finally:
        lock.close()


if __name__ == '__main__':
    raise SystemExit(main())
