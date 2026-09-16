#!/usr/bin/env python3
"""Frozen Normal N1-N5: map-bound preflights, n5 gate, then separate n20.

No automatic flight retries or failure replacement. Stop for diagnosis; any
runtime fix must start a new, independently preserved iteration from n5.
"""
import argparse
import csv
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from run_c19_frozen_validation import ROOT, common_args, sha, REFERENCE_SOURCES
from run_c19_cpu_attribution import TESTS, PROBE
from cylinder_map_search import frozen_policy
from adaptive_cpu40_seed1 import comparison
import static_latched_preflight as static
import event_recovery_seed1_smoke as event
import analyze_thread_cpu_profile as stages
import summarize_cpu_validation as reports

MAPS = ('seed1', 'seed3', 'seed5', 'seed7', 'seed9')
MODES = ('full', 'sector', 'adaptive')
ORDERS = tuple(itertools.permutations(MODES))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def read(path):
    return json.loads(Path(path).read_text())


def flight_checks(row, profile):
    source = row.get('source_acquisition', {}).get('checks', {})
    return dict(completed=row.get('success') is True, zero_contact=row.get('safety_collisions') == 0,
        run_valid=row.get('run_valid') is True, resource=row.get('resource_valid') is True,
        speed=row.get('speed_limit_valid') is True,
        source=bool(source) and all(v is True for v in source.values()),
        recovery=row.get('strict_recovery_audit', {}).get('valid') is True,
        timing=row.get('small_pool_timing', {}).get('valid') is True,
        cpu_profile=row.get('cpu_profile') is profile,
        trace_off=row.get('callback_trace') is False,
        historical_time=row.get('reference_comparison', {}).get('mission_time_guardrail_pass') is True)


def triplet_audit(folder, map_name, run, profile):
    rows, checks = [], {}
    for mode in MODES:
        path = folder / f'{mode}_summary.json'
        if not path.exists():
            checks[mode + ':present'] = False
            continue
        row = read(path)
        rows.append(row)
        checks[mode + ':identity'] = row.get('map') == map_name and row.get('run') == run and row.get('mode') == mode
        checks.update({mode + ':' + k: v for k, v in flight_checks(row, profile).items()})
    paired = comparison(rows, 30) if len(rows) == 3 else None
    checks['three_modes'] = len(rows) == 3
    checks['paired_mission_time'] = bool(paired and paired['mission_time_guardrail_pass'])
    checks['common_demand_exercised'] = bool(paired and paired['common_demand_exercise_pass'])
    checks['common_goal_identity'] = bool(paired and paired['common_goal_identity_exercise_pass'])
    return dict(valid=bool(checks) and all(checks.values()), checks=checks, comparison=paired,
                map=map_name, run=run, profiled=profile,
                primary_cpu_target_scope='Report cohort mean30%; not every-run threshold or a safety gate')


def static_commands(root, map_name):
    folder = root / 'static_preflight' / map_name
    folder.mkdir(parents=True)
    geometry = static.map_context(map_name)['geometry']
    commands, paths = [], []
    for composition in ('standalone', 'full', 'adaptive'):
        for sequence in ('reader-first', 'late'):
            name = f'{composition}_{sequence}'
            out = folder / name
            paths.append(out / 'result.json')
            commands.append(dict(name=f'static_{map_name}_{name}', phase='static', domain='190',
                command=[sys.executable, str(TESTS / 'static_pc_late_subscriber_test.py'),
                         '--out-dir', str(out), '--config', map_name + '.yaml',
                         '--expected-points', str(geometry['points']),
                         '--poll-ms', '1', '--durable', '--latched-once', '--reader-qos', 'durable',
                         '--composition', composition, '--sequence', sequence,
                         '--expected-sha256', geometry['sha256']]))
    rviz = folder / 'actual_rviz/result.json'
    commands.append(dict(name=f'rviz_{map_name}', phase='static', domain='191', command=[sys.executable,
        str(TESTS / 'static_map_rviz_reconnect_test.py'), '--out-dir', str(rviz.parent),
        '--probe-binary', str(PROBE), '--config', map_name + '.yaml',
        '--expected-points', str(geometry['points']), '--expected-sha256', geometry['sha256']]))
    commands.append(dict(name=f'accept_{map_name}', phase='static', command=[sys.executable,
        str(ROOT / 'scripts/native_campaign/static_latched_preflight.py'), 'create', '--map', map_name,
        *[v for p in paths for v in ('--transport', str(p))], '--rviz', str(rviz),
        '--output', str(folder / 'acceptance.json')]))
    return commands


def make_references(root):
    if sha(event.NORMAL) != event.NORMAL_SHA:
        raise RuntimeError('Historical Normal changed')
    with event.NORMAL.open() as stream:
        old = list(csv.DictReader(stream))
    for map_name in MAPS:
        dest = root / 'references' / map_name
        dest.mkdir(parents=True)
        for mode in MODES:
            if map_name == 'seed1':
                row = read(REFERENCE_SOURCES[mode])
                provenance = dict(source=str(REFERENCE_SOURCES[mode]), sha256=sha(REFERENCE_SOURCES[mode]))
            else:
                choices = [(i, r) for i, r in enumerate(old) if r['map'] == map_name and r['mode'] == mode]
                # Historical rows supply a time ceiling, not safety acceptance.
                # Keep all rows, including historic Sector contact; do not
                # cherry-pick a clean historical subset for the timing median.
                if len(choices) != 10 or any(r['success'] != 'True' for _, r in choices):
                    raise RuntimeError('Historical reference inventory incomplete')
                index, selected = sorted(choices, key=lambda v: float(v[1]['mission_time_s']))[len(choices)//2]
                row = dict(map=map_name, mode=mode, success=True,
                    **{k: float(selected[k]) for k in ('mission_time_s', 'end_to_end_cpu_cores_mean', 'end_to_end_cpu_core_s')})
                provenance = dict(source=str(event.NORMAL), sha256=event.NORMAL_SHA, zero_based_row=index,
                    historical_contact_runs=sum(float(r['safety_collisions']) > 0 for _, r in choices),
                    selected_historical_contacts=float(selected['safety_collisions']),
                    rule='upper median mission-time row among all10 physical-map/mode historical observations; not best run')
            row.update(time_only=True, reference_provenance=provenance)
            save(dest / f'{mode}_summary.json', row)


def build_plan(root, base_run):
    commands = [c for map_name in MAPS for c in static_commands(root, map_name)]
    for stage in ('preflight', 'pilot5', 'confirm20'):
        count = 1 if stage == 'preflight' else 5 if stage == 'pilot5' else 20
        for repeat in range(count):
            ordered_maps = MAPS[repeat % 5:] + MAPS[:repeat % 5]
            for map_name in ordered_maps:
                index = MAPS.index(map_name)
                run = base_run + (0 if stage == 'preflight' else 100 if stage == 'pilot5' else 1000) + repeat*10 + index
                folder = root / stage / map_name / f'r{repeat+1:02d}_run{run}'
                on = root / 'preflight' / map_name / f'r01_run{base_run+index}'
                base = common_args(root)
                base[base.index('--candidate') + 1] = f'c22_{root.name}_{stage}'
                base[base.index('--side-executor-threads') + 1] = '3'
                base[base.index('--static-latched-preflight') + 1] = str(root / 'static_preflight' / map_name / 'acceptance.json')
                base[base.index('--time-reference-folder') + 1] = str(root / 'references' / map_name)
                base += ['--map', map_name, '--output', str(folder), '--run', str(run)]
                base += ['--profile-cpu'] if stage == 'preflight' else ['--small-pool-profile-reference', str(on)]
                order = ORDERS[(repeat + index) % len(ORDERS)]
                commands.append(dict(name=f'{stage}_{map_name}_r{repeat+1:02d}', phase=stage, map=map_name,
                    run=run, repeat=repeat+1, modes=list(order), path=str(folder), command=base + ['--modes', *order]))
    return commands


def campaign_gate(root, commands, phase):
    planned = [c for c in commands if c['phase'] == phase]
    records = []
    for item in planned:
        path = Path(item['path']) / 'triplet_verification.json'
        document = read(path) if path.exists() else {}
        identity = (document.get('map') == item['map'] and document.get('run') == item['run']
                    and document.get('profiled') is (phase == 'preflight'))
        checks = document.get('checks', {})
        accepted = bool(identity and checks and all(v is True for v in checks.values())
                        and document.get('valid') is True)
        records.append(dict(name=item['name'], present=path.exists(), valid=accepted,
                            sha256=sha(path) if path.exists() else None))
    return dict(valid=bool(records) and all(r['valid'] for r in records), phase=phase,
                maps=list(MAPS), planned_triplets=len(planned), records=records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--base-run', type=int, default=10000)
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    make_references(root)
    commands = build_plan(root, args.base_run)
    for phase, count in (('preflight', 1), ('pilot5', 5), ('confirm20', 20)):
        save(root / phase / 'plan.json', dict(maps=list(MAPS), phase=phase,
             profile_preflight_runs_per_mode=count if phase == 'preflight' else 0,
             unprofiled_runs_per_mode=0 if phase == 'preflight' else count,
             independent_cohort=True, parent_plan=str(root / 'plan.json')))
    frozen = frozen_policy()['sha256']
    script_names = ('run_c22_normal_campaign.py', 'adaptive_cpu40_seed1.py', 'normal_cpu_gpu_diagnostic.py',
        'sensor_acquisition_seed1_smoke.py', 'event_recovery_seed1_smoke.py', 'static_latched_preflight.py',
        'native_loop_monitor.py', 'message_intervals.py', 'audit_cpu40_recovery.py',
        'analyze_thread_cpu_profile.py', 'summarize_cpu_validation.py', 'run_c19_frozen_validation.py')
    paths = [ROOT / 'scripts/native_campaign' / name for name in script_names]
    paths += [PROBE, TESTS / 'static_pc_late_subscriber_test.py', TESTS / 'static_map_rviz_reconnect_test.py',
        Path('/root/super_ws/install/perfect_drone_sim/lib/perfect_drone_sim/perfect_drone_adaptive_node')]
    paths += [p for m in MAPS for p in static.map_context(m)['paths'].values()]
    paths += list((root / 'references').rglob('*.json'))
    paths += [root / phase / 'plan.json' for phase in ('preflight', 'pilot5', 'confirm20')]
    frozen.update({str(p): sha(p) for p in paths})
    save(root / 'plan.json', dict(schema='c22-normal-five-v1', maps=list(MAPS), map_labels=dict(zip(MAPS, ('N1','N2','N3','N4','N5'))),
        created_local=time.strftime('%Y-%m-%dT%H:%M:%S%z'), commands=commands, frozen_sha256=frozen,
        pilot_runs_per_map_mode=5, independent_confirmation_runs_per_map_mode=20,
        profiled_preflight_runs_per_map_mode=1, initial_total_flights=390,
        static_no_flight_tests_per_map=7, mode_orders=ORDERS, side_executor_threads=3,
        pilot_and_confirmation_not_pooled=True, old_normal_or_c21_not_pooled=True,
        no_automatic_retry=True, stop_on_any_contract_safety_completion_or_paired_time_failure=True,
        modifications_require_new_iteration_from_pilot=True, discard_failed_attempts=False,
        odometry_max_ms=50, odometry_p99_ms=20, source_hz_range=[9.5,10.5], odometry_hz_range=[98,102],
        paired_adaptive_full_time_ratio_max=1.10, mean_cpu30_descriptive_cohort_target=True,
        original_cpu40_not_redefined=True, cumulative_cpu_recorded=True,
        gpu_scope='device-wide, not attributed', payload_scope='logical edge, not physical link bandwidth',
        cpu_scope='experiment cgroup including simulator, external observer excluded; ON separate',
        missing_is_not_zero=True, resource_scope='RSS/PSS/swap/PSI with identical admission checks',
        map_generation_and_planner_initially_unchanged=True, finite_simulation_not_population_guarantee=True))
    history = []
    current = None
    def status(state, **extra):
        save(root / 'status.json', dict(state=state, current=current, completed=history,
             pid=os.getpid(), updated_local=time.strftime('%Y-%m-%dT%H:%M:%S%z'), **extra))
    try:
        previous_phase = 'static'
        for item in commands:
            current = {k:v for k,v in item.items() if k != 'command'}
            if any(sha(p) != value for p,value in frozen.items()):
                raise RuntimeError('Frozen source/config/binary/evidence changed')
            if item['phase'] != previous_phase and previous_phase in ('preflight', 'pilot5'):
                gate = campaign_gate(root, commands, previous_phase)
                save(root / (previous_phase + '_gate.json'), gate)
                reports.main(['--campaign', str(root / previous_phase), '--output', str(root / ('comparison_' + previous_phase))])
                if not gate['valid']:
                    raise RuntimeError('Cannot expand: ' + previous_phase + ' did not pass')
            previous_phase = item['phase']
            status('RUNNING')
            print('START', item['name'], flush=True)
            env = dict(os.environ)
            env['SUPER_CPU_PROFILE'] = '0'
            env['SUPER_CALLBACK_TRACE'] = '0'
            if 'domain' in item:
                env['ROS_DOMAIN_ID'] = item['domain']
            with (root / (item['name'] + '.log')).open('x') as log:
                result = subprocess.run(item['command'], env=env, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            entry = dict(name=item['name'], phase=item['phase'], returncode=result.returncode)
            history.append(entry)
            print('FINISH', entry, flush=True)
            if 'path' in item:
                folder = Path(item['path'])
                audit = triplet_audit(folder, item['map'], item['run'], item['phase'] == 'preflight')
                save(folder / 'triplet_verification.json', audit)
                if result.returncode or not audit['valid']:
                    raise RuntimeError('Flight failed; retained for analysis: ' + item['name'])
                if item['phase'] == 'preflight':
                    save(folder / 'thread_cpu_summary.json', {m:stages.summarize(folder,m,item['run'],item['map']) for m in MODES})
            elif result.returncode:
                raise RuntimeError('Static preflight failed: ' + item['name'])
        gate = campaign_gate(root, commands, 'confirm20')
        save(root / 'confirm20_gate.json', gate)
        reports.main(['--campaign', str(root / 'confirm20'), '--output', str(root / 'comparison_confirm20')])
        if not gate['valid'] or sha(event.NORMAL) != event.NORMAL_SHA:
            raise RuntimeError('Final gate or Normal preservation check failed')
        status('COMPLETE')
    except BaseException as exc:
        status('STOPPED_FOR_DIAGNOSIS', error=repr(exc))
        raise


if __name__ == '__main__':
    main()
