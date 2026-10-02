#!/usr/bin/env python3
"""Complete the 39 unflown c41 triplets without changing 93 preserved flights."""
from datetime import datetime
import csv
import fcntl
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time

import audit_goal_change_full_refresh_v8 as event_audit
import run_scenario7_v7_n10 as base
import run_scenario7_v13_n10 as v13
import run_scenario7_v14_n10 as v14
import run_scenario7_v15_fresh_n10 as v15


ORIGINAL = base.REPO / 'results/scenario7_no_cutoff_v15_n10_20261002'
CONTINUATION = base.REPO / 'results/scenario7_no_cutoff_v16_completion_20261002'
THIS_FILE = Path(__file__).resolve()
PROTOCOL = CONTINUATION / 'protocol.json'
AUDITOR = THIS_FILE.with_name('audit_goal_change_full_refresh_v8.py')


def digest(path):
    return base.sha256(Path(path))


def check_hashes(expected):
    changed = [path for path, value in expected.items()
               if not Path(path).is_file() or digest(path) != value]
    if changed:
        raise RuntimeError('frozen file changed: ' + ', '.join(changed))


def plan_and_work():
    original_plan = json.loads((ORIGINAL / 'plan.json').read_text())['commands']
    status = json.loads((ORIGINAL / 'status.json').read_text())
    preserved = status['completed']
    if (len(original_plan) != 70 or status['state'] != 'STOPPED_FOR_DIAGNOSIS'
            or len(preserved) != 31 or preserved[-1]['run'] != 97056
            or preserved[-1]['errors'] !=
            ['adaptive: flight quality/source/event/no-cutoff audit failed']):
        raise RuntimeError('original c41 stop or plan differs from declared event')
    if any(not row['valid'] for row in preserved[:-1]):
        raise RuntimeError('earlier original c41 triplet failed')
    if [row['run'] for row in preserved] != [item['run'] for item in original_plan[:31]]:
        raise RuntimeError('preserved run order differs from plan')
    work = []
    for item in original_plan[31:]:
        output = CONTINUATION / item['stage'] / item['map'] / Path(item['output']).name
        work.append(item | {'output': str(output)})
    if len(work) != 39 or sum(len(item['modes']) for item in work) != 117:
        raise RuntimeError('remaining flight count differs from protocol')
    return original_plan, work


def preserved_hashes(plan):
    paths = []
    for item in plan[:31]:
        output = Path(item['output'])
        paths.append(output / 'raw.csv')
        for mode in item['modes']:
            paths.append(v15.corrected.stack_path(item, mode))
    if len(paths) != 124 or any(not path.is_file() for path in paths):
        raise RuntimeError('preserved raw or stack log missing')
    return {str(path): digest(path) for path in paths}


def posthoc_audit(plan):
    v15.corrected.goal_audit = event_audit
    findings = [v15.validate_triplet(item, write=False) for item in plan[:31]]
    if not all(result['valid'] for result in findings):
        raise RuntimeError('preserved 93 flights fail corrected read-only audit')
    return findings


def command(item):
    common = [arg for arg in base.COMMON if arg != '--event-body-heading']
    return [sys.executable, '-u', str(v14.WRAPPER), '--candidate', v15.CANDIDATE,
            *common, '--map', item['map'], '--run', str(item['run']),
            '--output', item['output'], '--modes', *item['modes']]


def combined_validations(original_findings, work, completed):
    result = list(original_findings)
    for item in work[:len(completed)]:
        path = Path(item['output']) / 'v7_triplet_validation.json'
        if not path.is_file():
            raise RuntimeError('completion validation missing: ' + str(path))
        result.append(json.loads(path.read_text()))
    return result


def write_combined_summary(original_findings, work, completed):
    findings = combined_validations(original_findings, work, completed)
    rows = []
    for name in base.MAPS:
        for mode in base.MODES:
            samples = [item['outcomes'][mode] for item in findings if item['map'] == name]
            row = dict(map=name, mode=mode, recorded=len(samples), planned=10,
                       complete=sum(bool(x['complete']) for x in samples),
                       contact_runs=sum((x['safety_collisions'] or 0) > 0 for x in samples),
                       contact_episodes=sum(x['safety_collisions'] or 0 for x in samples),
                       quality_valid=sum(bool(x['quality_valid']) for x in samples))
            for label, field in (
                    ('mission_time_s', 'mission_time_s'),
                    ('cpu_cores', 'end_to_end_cpu_cores_mean'),
                    ('cpu_core_s', 'end_to_end_cpu_core_s'),
                    ('input_mib_s', 'map_payload_mib_s'),
                    ('input_mib_run', 'map_payload_bytes_total'),
                    ('map_ms', 'map_update_ms_mean'),
                    ('full_open', 'full_open_transitions')):
                values = [x[field] for x in samples if x[field] is not None]
                if label == 'input_mib_run':
                    values = [value / 1048576 for value in values]
                row[label + '_mean'] = statistics.mean(values) if values else None
            rows.append(row)
    path = CONTINUATION / 'combined_summary_by_map.csv'
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    fmt = lambda x: 'N/A' if x is None else f'{x:.3f}'
    lines = ['# c41 fresh n10 combined progress', '',
             'The first 93 flights are preserved in v15; later flights are in v16.', '',
             '| Map | Mode | Recorded/10 | Complete | Contact runs | Mean time s | CPU cores | Input MiB/s | Map ms | Full opens |',
             '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for row in rows:
        lines.append(f"| {row['map']} | {row['mode']} | {row['recorded']}/10 | "
                     f"{row['complete']} | {row['contact_runs']} | "
                     f"{fmt(row['mission_time_s_mean'])} | {fmt(row['cpu_cores_mean'])} | "
                     f"{fmt(row['input_mib_s_mean'])} | {fmt(row['map_ms_mean'])} | "
                     f"{fmt(row['full_open_mean'])} |")
    (CONTINUATION / 'combined_summary_by_map.md').write_text('\n'.join(lines) + '\n')
    return findings


def main():
    if any(arg != '--dry-run' for arg in sys.argv[1:]):
        raise SystemExit('only --dry-run is accepted')
    dry_run = '--dry-run' in sys.argv[1:]
    protocol = json.loads(PROTOCOL.read_text())
    if (protocol['candidate'] != v15.CANDIDATE or
            protocol['preserved_flights'] != 93 or
            protocol['remaining_flights'] != 117):
        raise RuntimeError('completion protocol mismatch')
    original_frozen = json.loads((ORIGINAL / 'frozen_identity.json').read_text())
    check_hashes(original_frozen)
    v13.verify_runtime_install()
    plan, work = plan_and_work()
    archive_hashes = preserved_hashes(plan)
    original_findings = posthoc_audit(plan)
    frozen = original_frozen | {str(path): digest(path)
                                for path in (THIS_FILE, AUDITOR, PROTOCOL)}
    if dry_run:
        print(json.dumps(dict(preserved_flights=93, remaining_flights=117,
                              remaining_triplets=len(work), first=work[0], last=work[-1],
                              preserved_audit_valid=True), indent=2))
        return 0
    if (CONTINUATION / 'status.json').exists() or any(
            Path(item['output']).exists() for item in work):
        raise RuntimeError('continuation already started; no implicit rerun')
    lock = open('/tmp/super_sector_filter_scenario7_v7_n10.lock', 'a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    base.atomic_json(CONTINUATION / 'frozen_identity.json', frozen)
    base.atomic_json(CONTINUATION / 'preserved_identity.json', archive_hashes)
    base.atomic_json(CONTINUATION / 'worklist.json', work)
    base.atomic_json(CONTINUATION / 'posthoc_event_audit_v8.json',
                     dict(preserved_flights=93, valid_flights=93,
                          runs=[dict(run=x['run'], map=x['map'], valid=x['valid'])
                                for x in original_findings]))
    started = time.monotonic()
    completed = []
    current = None

    def status(state, **extra):
        base.atomic_json(CONTINUATION / 'status.json',
                         dict(state=state, pid=os.getpid(), current=current,
                              completed=completed, elapsed_s=time.monotonic()-started,
                              updated_local=datetime.now().astimezone().isoformat(), **extra))

    env = {key: value for key, value in os.environ.items() if not key.startswith('SUPER_')}
    env['PYTHONNOUSERSITE'] = '1'
    try:
        status('RUNNING')
        for item in work:
            check_hashes(frozen)
            check_hashes(archive_hashes)
            current = item
            output = Path(item['output'])
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
            finding = v15.validate_triplet(item)
            entry = dict(run=item['run'], map=item['map'], repeat=item['repeat'],
                         modes=item['modes'], returncode=returncode,
                         valid=returncode == 0 and finding['valid'],
                         errors=finding['errors'])
            completed.append(entry)
            write_combined_summary(original_findings, work, completed)
            print('FINISH', json.dumps(entry), flush=True)
            if not entry['valid']:
                raise RuntimeError('blocking completion failure: ' + repr(entry))
        check_hashes(archive_hashes)
        if len(write_combined_summary(original_findings, work, completed)) != 70:
            raise RuntimeError('combined cohort does not contain 70 triplets')
        status('COMPLETE', completed_flights=117, total_flights=210)
        return 0
    except BaseException as error:
        status('STOPPED_FOR_DIAGNOSIS', error=repr(error))
        print('STOPPED:', repr(error), file=sys.stderr, flush=True)
        raise
    finally:
        lock.close()


if __name__ == '__main__':
    raise SystemExit(main())
