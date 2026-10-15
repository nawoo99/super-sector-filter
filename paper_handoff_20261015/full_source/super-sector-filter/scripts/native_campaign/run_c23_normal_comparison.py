#!/usr/bin/env python3
"""Prospective N1-N5, three modes, n=5 comparison. No automatic n20 or retries.

Runtime is unchanged from C22 iteration04. Reuse hash-valid static tests and
profiled timing evidence; duration is a measured outcome, not a +10% stop gate.
"""
import argparse
import os
from pathlib import Path
import subprocess
import time

from run_c22_normal_campaign import (ROOT, MAPS, MODES, ORDERS, common_args,
    save, read, sha, frozen_policy, triplet_audit, stages, reports, event, static)


def comparison_audit(folder, map_name, run, profile):
    original = triplet_audit(folder, map_name, run, profile)
    outcome_keys = ('completed', 'zero_contact', 'historical_time')
    checks = {k: v for k, v in original['checks'].items()
              if k != 'paired_mission_time' and not k.endswith(outcome_keys)}
    return dict(original, valid=all(checks.values()), acceptance_checks=checks,
                original_strict_gate_valid=original['valid'], mission_time_as_metric=True,
                outcome_failures={k: v for k, v in original['checks'].items()
                                  if k.endswith(('completed', 'zero_contact')) and not v})


def build_commands(root, evidence, base_run):
    references = {m: evidence/'preflight'/m/f'r01_run{14000+i}'
                  for i, m in enumerate(MAPS)}
    references['seed9'] = root/'profiled_preflight'/'seed9'
    slots = [('preflight', 'seed9', 0, base_run, references['seed9'])]
    for repeat in range(5):
        for m in MAPS[repeat:] + MAPS[:repeat]:
            run = base_run + 100 + repeat*10 + MAPS.index(m)
            slots.append(('comparison5', m, repeat+1, run,
                          root/'comparison5'/m/f'r{repeat+1:02d}_run{run}'))
    commands = []
    for phase, m, repeat, run, folder in slots:
        base = common_args(root)
        base.remove('--extended-demand-lease')
        overrides = {'--candidate': 'c23_normal_comparison_' + phase,
                     '--side-executor-threads': '3',
                     '--static-latched-preflight': str(evidence/'static_preflight'/m/'acceptance.json'),
                     '--time-reference-folder': str(evidence/'references'/m)}
        for flag, value in overrides.items():
            base[base.index(flag)+1] = value
        order = ORDERS[((repeat-1 if repeat else 0)+MAPS.index(m)) % len(ORDERS)]
        base += ['--event-body-heading', '--mission-time-as-metric', '--map', m,
                 '--run', str(run), '--output', str(folder)]
        base += (['--profile-cpu'] if phase == 'preflight' else
                 ['--small-pool-profile-reference', str(references[m])])
        commands.append(dict(name=f'{phase}_{m}_r{repeat:02d}', phase=phase, map=m,
            run=run, repeat=repeat, path=str(folder), modes=list(order),
            command=base+['--modes', *order]))
    return commands, references


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--evidence', required=True, type=Path)
    parser.add_argument('--base-run', type=int, default=15000)
    parser.add_argument('--ready-maps-only', action='store_true',
                        help='Execute N1-N4 only while N5 failed timing preflight remains unresolved; never claim75')
    args = parser.parse_args()
    root, evidence = args.output.resolve(), args.evidence.resolve()
    root.mkdir(parents=True, exist_ok=False)
    commands, references = build_commands(root, evidence, args.base_run)
    if args.ready_maps_only:
        commands = [c for c in commands if c['phase']=='comparison5' and c['map']!='seed9']
    validations = {m: static.validate_manifest(evidence/'static_preflight'/m/'acceptance.json',
                   static.map_context(m)) for m in MAPS}
    save(root/'reused_static_validation.json', validations)
    if not all(v['valid'] for v in validations.values()):
        raise RuntimeError('Current static delivery evidence invalid')
    frozen = frozen_policy()['sha256']
    paths = list((ROOT/'scripts/native_campaign').glob('*.py'))
    paths += [p for m in MAPS for p in static.map_context(m)['paths'].values()]
    paths += list((evidence/'references').rglob('*.json'))
    paths += [evidence/'static_preflight'/m/'acceptance.json' for m in MAPS]
    for m in MAPS[:-1]:
        paths += [references[m]/name for name in ('plan.json', *(f'{v}_summary.json' for v in MODES))]
    frozen.update({str(p): sha(p) for p in paths})
    save(root/'comparison5'/'plan.json', dict(maps=list(MAPS), unprofiled_runs_per_mode=5,
         profile_preflight_runs_per_mode=0, independent_cohort=True))
    save(root/'plan.json', dict(schema='c23-normal-comparison-v1', commands=commands,
         maps=list(MAPS), modes=list(MODES), requested_comparison_flights=75,
         comparison_flights=sum(c['phase']=='comparison5' for c in commands)*3,
         new_profiled_flights=0 if args.ready_maps_only else 3,
         pending_maps=['seed9'] if args.ready_maps_only else [],
         reused_profiled_flights=12, no_retry=True, automatic_n20=False,
         frozen_sha256=frozen, profile_reference_folders={k:str(v) for k,v in references.items()},
         mission_time_as_metric=True, old_strict_gates_unchanged=True,
         valid_safety_failures_retained_as_outcomes=True,
         stop_on_measurement_source_recovery_or_timing_failure=True,
         created_local=time.strftime('%Y-%m-%dT%H:%M:%S%z'),
         cpu_scope='Experiment cgroup including simulator, external observer excluded; ON separate',
         original_cpu40_not_redefined=True, common_dispatch_lease_s=0.25,
         event_body_heading=True, side_executor_threads=3))
    history, current = [], None
    started = time.monotonic()
    def status(state, **extra):
        save(root/'status.json', dict(state=state, current=current, completed=history,
             pid=os.getpid(), elapsed_s=time.monotonic()-started,
             updated_local=time.strftime('%Y-%m-%dT%H:%M:%S%z'), **extra))
    try:
        for item in commands:
            current = {k:v for k,v in item.items() if k != 'command'}
            if any(sha(p) != digest for p,digest in frozen.items()):
                raise RuntimeError('Frozen source/config/binary/evidence changed')
            status('RUNNING')
            print('START', item['name'], flush=True)
            env = dict(os.environ, SUPER_CPU_PROFILE='0', SUPER_CALLBACK_TRACE='0')
            with (root/(item['name']+'.log')).open('x') as log:
                result = subprocess.run(item['command'], cwd=ROOT, env=env,
                                        stdout=log, stderr=subprocess.STDOUT)
            folder = Path(item['path'])
            audit = comparison_audit(folder, item['map'], item['run'], item['phase']=='preflight')
            save(folder/'triplet_verification.json', audit)
            history.append(dict(name=item['name'], phase=item['phase'], returncode=result.returncode,
                                valid=audit['valid'], outcome_failures=audit['outcome_failures']))
            print('FINISH', history[-1], flush=True)
            if result.returncode or not audit['valid']:
                raise RuntimeError('Measurement/contract failure retained: '+item['name'])
            if item['phase'] == 'preflight':
                save(folder/'thread_cpu_summary.json', {m:stages.summarize(folder,m,item['run'],item['map']) for m in MODES})
                for name in ('plan.json', *(f'{m}_summary.json' for m in MODES)):
                    path = folder/name
                    frozen[str(path)] = sha(path)
                save(root/'profiled_reference_frozen.json', {str(folder/name):sha(folder/name)
                     for name in ('plan.json', *(f'{m}_summary.json' for m in MODES))})
            status('RUNNING')
        reports.main(['--campaign', str(root/'comparison5'), '--output', str(root/'report')])
        if sha(event.NORMAL) != event.NORMAL_SHA:
            raise RuntimeError('Frozen Normal data changed')
        status('PARTIAL_PENDING_N5_TIMING_DECISION' if args.ready_maps_only else 'COMPLETE',
               comparison_flights=sum(c['phase']=='comparison5' for c in commands)*3,
               requested_comparison_flights=75,
               pending_flights=15 if args.ready_maps_only else 0,
               outcome_failures=[r for r in history if r['outcome_failures']])
    except BaseException as exc:
        status('STOPPED_FOR_DIAGNOSIS', error=repr(exc))
        raise


if __name__ == '__main__':
    main()
