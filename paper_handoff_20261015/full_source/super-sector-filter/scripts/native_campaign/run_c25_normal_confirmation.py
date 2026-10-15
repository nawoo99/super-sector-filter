#!/usr/bin/env python3
"""Frozen C24 candidate: fresh static/ON checks, then independent Normal OFF300.

No runtime edits, flight retry, failure replacement, pilot pooling, or stress
experiment. C24's controller and its frozen evidence remain byte-for-byte intact.
"""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import signal
import time

import run_c24_normal_validation as base


PHASES = ('preflight', 'confirmation20')
COUNTS = {'preflight': 1, 'confirmation20': 20}
PREVIOUS = base.ROOT / 'results/c24_normal_validation_20260917/iteration01'
PROTOCOL = base.ROOT / 'docs/c25_normal_confirmation_20260917.md'


def admit_previous(previous):
    """Require the exact successful pilot, unchanged inputs AND saved evidence."""
    previous = Path(previous).resolve()
    plan = base.load_document(previous / 'plan.json')
    status = base.load_document(previous / 'status.json')
    frozen = base.load_document(previous / 'frozen_inputs_and_evidence.json')
    checks = dict(
        schema=plan.get('schema') == 'c24-normal-validation-v1',
        maps=plan.get('maps') == list(base.MAPS),
        modes=plan.get('modes') == list(base.MODES),
        complete=status.get('state') == 'COMPLETE',
        exact_off=status.get('completed_off_flights') == 75,
        exact_on=status.get('completed_on_flights') == 15,
        async_enabled=plan.get('async_certified_recovery') is True,
        no_extra_flags=plan.get('extra_runner_flags') == [],
        no_environment_overrides=plan.get('runtime_environment_overrides') == {},
        frozen_inventory=bool(frozen) and all(isinstance(v, str) and len(v) == 64 for v in frozen.values()),
    )
    changed = base.changed_inputs(frozen) if checks['frozen_inventory'] else ['missing frozen inventory']
    checks['all_frozen_files_unchanged'] = not changed
    commands = plan.get('commands', [])
    gates = {}
    for phase in base.PHASES:
        gates[phase] = base.phase_gate(commands, phase)
        saved = base.load_document(previous / (phase + '_gate.json'))
        checks[phase + '_fresh_gate'] = gates[phase]['valid'] is True
        checks[phase + '_saved_gate_matches'] = saved == gates[phase]
    candidates = {c.get('candidate') for c in commands if 'path' in c}
    checks['single_candidate'] = len(candidates) == 1 and None not in candidates
    inherited = {k: v for k, v in os.environ.items() if k.startswith('SUPER_')}
    expected_environment = plan.get('inherited_super_environment', {})
    checks['no_unexpected_super_environment'] = all(
        expected_environment.get(k) == v for k, v in inherited.items()
        if k not in ('SUPER_CPU_PROFILE', 'SUPER_CALLBACK_TRACE'))
    return dict(valid=base.explicit_true_checks(checks), checks=checks, changed_files=changed,
                previous=str(previous), candidate=next(iter(candidates)) if len(candidates) == 1 else None,
                frozen_files_verified=len(frozen), fresh_gates=gates,
                frozen_sha256=frozen, previous_rows_not_pooled=True)


def build_plan(root, candidate, base_run=21000):
    if type(base_run) is not int or base_run < 1:
        raise ValueError('Positive integer base-run required')
    if not isinstance(candidate, str) or not candidate:
        raise ValueError('Exact frozen pilot candidate label required')
    commands = [dict(c, map=m) for m in base.MAPS for c in base.static_commands(root, m)]
    for phase in PHASES:
        for repeat in range(COUNTS[phase]):
            shift = repeat % len(base.MAPS)
            for map_name in base.MAPS[shift:] + base.MAPS[:shift]:
                index = base.MAPS.index(map_name)
                run = base_run + (0 if phase == 'preflight' else 1000) + repeat * 10 + index
                folder = root / phase / map_name / f'r{repeat+1:02d}_run{run}'
                reference = root / 'preflight' / map_name / f'r01_run{base_run+index}'
                command = base.common_args(root)
                command.remove('--extended-demand-lease')
                for flag, value in {
                    '--candidate': candidate, '--side-executor-threads': '3',
                    '--static-latched-preflight': str(root / 'static_preflight' / map_name / 'acceptance.json'),
                    '--time-reference-folder': str(root / 'references' / map_name),
                }.items():
                    command[command.index(flag)+1] = value
                order = base.ORDERS[(repeat + index) % len(base.ORDERS)]
                command += ['--event-body-heading', '--mission-time-as-metric', '--sector-outcomes-as-metrics',
                            '--async-certified-recovery', '--map', map_name, '--run', str(run),
                            '--output', str(folder)]
                command += ['--profile-cpu'] if phase == 'preflight' else [
                    '--small-pool-profile-reference', str(reference)]
                command += ['--modes', *order]
                commands.append(dict(name=f'{phase}_{map_name}_r{repeat+1:02d}', phase=phase,
                    map=map_name, run=run, repeat=repeat+1, modes=list(order), path=str(folder),
                    candidate=candidate, async_certified_recovery=True, command=command))
    return commands


def phase_gate(commands, phase):
    if phase not in PHASES:
        raise ValueError('Unknown confirmation phase')
    planned = [c for c in commands if c.get('phase') == phase]
    expected = {(m, r, mode) for m in base.MAPS for r in range(1, COUNTS[phase]+1) for mode in base.MODES}
    actual = [(c.get('map'), c.get('repeat'), mode) for c in planned for mode in c.get('modes', [])]
    identities = [(c.get('map'), c.get('run'), mode) for c in planned for mode in c.get('modes', [])]
    records = []
    for item in planned:
        folder = Path(item['path'])
        audit = base.triplet_audit(folder, item['map'], item['run'], phase == 'preflight',
            item['candidate'], item['modes'], True)
        stored = base.load_document(folder / 'triplet_verification.json')
        records.append(dict(name=item['name'], audit_present=(folder/'triplet_verification.json').is_file(),
                            valid=audit['valid'] is True and stored == audit))
    checks = dict(exact_planned_coverage=len(actual) == len(expected) and set(actual) == expected,
                  unique_identities=len(identities) == len(set(identities)),
                  all_evidence_present=bool(records) and all(r['audit_present'] for r in records),
                  all_fresh_audits_pass=bool(records) and all(r['valid'] for r in records))
    return dict(valid=base.explicit_true_checks(checks), phase=phase, checks=checks,
                planned_triplets=len(planned), expected_flights=len(expected), records=records)


def report_partial(root):
    records = []
    for phase in PHASES:
        if not any((root/phase).rglob('raw.csv')):
            records.append(dict(phase=phase, state='NO_RAW_ROWS'))
            continue
        try:
            base.reports.main(['--campaign', str(root/phase), '--output', str(root/('report_'+phase))])
            records.append(dict(phase=phase, state='WRITTEN'))
        except Exception as exc:
            records.append(dict(phase=phase, state='REPORT_ERROR', error=repr(exc)))
    base.save(root/'report_status.json', dict(updated_local=time.strftime('%Y-%m-%dT%H:%M:%S%z'), reports=records))
    return records


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New confirmation directory only')
    parser.add_argument('--previous', type=Path, default=PREVIOUS)
    parser.add_argument('--base-run', type=int, default=21000)
    args = parser.parse_args(argv)
    if args.output.resolve().exists():
        parser.error('Existing campaign path refused; no overwrite, resume or flight replacement')
    if args.base_run < 1:
        parser.error('Positive base-run required')
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    started, history, current, frozen = time.monotonic(), [], None, {}
    env = dict(os.environ, SUPER_CPU_PROFILE='0', SUPER_CALLBACK_TRACE='0')

    def status(state, **extra):
        base.save(root/'status.json', dict(schema='c25-status-v1', state=state, pid=os.getpid(),
            current=current, completed=history, elapsed_s=time.monotonic()-started,
            updated_local=time.strftime('%Y-%m-%dT%H:%M:%S%z'),
            requested_off_flights=300, requested_on_flights=15, automatic_retry=False,
            audited_off_flights=3*sum(x.get('phase') == 'confirmation20' and x.get('valid') is True for x in history),
            attempted_off_triplets=sum(x.get('phase') == 'confirmation20' for x in history), **extra))

    def interrupted(signum, _frame):
        raise InterruptedError('Controller interrupted by signal ' + str(signum))

    handlers = {sig: signal.signal(sig, interrupted) for sig in (signal.SIGTERM, signal.SIGINT)}
    try:
        status('ADMITTING_FROZEN_PILOT')
        admission = admit_previous(args.previous)
        base.save(root/'pilot_admission.json', admission)
        if admission['valid'] is not True:
            raise RuntimeError('Pilot evidence/runtime admission failed: ' + repr(admission['checks']))
        base.make_references(root)
        commands = build_plan(root, admission['candidate'], args.base_run)
        for phase in PHASES:
            base.save(root/phase/'plan.json', dict(maps=list(base.MAPS), phase=phase, independent_cohort=True,
                profile_preflight_runs_per_mode=COUNTS[phase] if phase == 'preflight' else 0,
                unprofiled_runs_per_mode=COUNTS[phase] if phase != 'preflight' else 0,
                parent_plan=str(root/'plan.json')))
        previous = Path(admission['previous'])
        # Keep exact original runtime/scripts/maps and pilot provenance frozen.
        # Historical raw evidence was independently hashed in admission; it is
        # not a flight reference and is never pooled into the new OFF300.
        frozen.update({p: h for p, h in admission['frozen_sha256'].items()
                       if not Path(p).is_relative_to(previous)})
        paths = list((base.ROOT/'scripts/native_campaign').glob('*.py'))
        paths += list((root/'references').rglob('*.json'))
        paths += [PROTOCOL, root/'pilot_admission.json', *(root/p/'plan.json' for p in PHASES)]
        paths += [previous/'plan.json', previous/'status.json', previous/'frozen_inputs_and_evidence.json',
                  previous/'preflight_gate.json', previous/'validation5_gate.json']
        base.freeze_files(frozen, paths)
        base.save(root/'plan.json', dict(schema='c25-normal-confirmation-v1', maps=list(base.MAPS),
            modes=list(base.MODES), map_labels=dict(zip(base.MAPS, ('N1','N2','N3','N4','N5'))),
            candidate=admission['candidate'], commands=commands, frozen_sha256=frozen,
            created_local=time.strftime('%Y-%m-%dT%H:%M:%S%z'),
            pilot=str(previous), pilot_admission=str(root/'pilot_admission.json'), pilot_rows_pooled=False,
            profiled_preflight_flights=15, unprofiled_primary_flights=300, total_flights=315,
            fresh_static_transport_cases=30, fresh_actual_rviz_cases=5, old_on_evidence_reused=False,
            independent_cohorts=True, no_retry=True, no_replacement=True, all_failures_retained=True,
            runtime_changes_forbidden=True, maps_and_algorithm_unchanged=True, no_stress_experiment=True,
            side_executor_threads=3, common_dispatch_lease_s=.25, event_body_heading=True,
            async_certified_recovery=True, mission_time_as_metric=True, paired_time_gate_applied=False,
            sector_outcomes_as_metrics=True, full_adaptive_required_safe_complete=True,
            full_adaptive_outcome_stop_boundary='After current triplet; at most two remaining simulated modes',
            stop_on_measurement_source_recovery_timing_resource_failure=True,
            inherited_super_environment={k:v for k,v in env.items() if k.startswith('SUPER_')},
            memory_runaway_sentinel=dict(threshold_mib=base.MEMORY_RUNAWAY_MIB, poll_s=base.MEMORY_POLL_S,
                owned_descendants_only=True, bounded_stack_capture=True, timeout_s=base.GDB_TIMEOUT_S,
                contaminated_costs_never_valid=True),
            cpu_scope='Experiment cgroup including simulator; external observer excluded; ON and OFF separate',
            original_cpu40_not_redefined=True, cpu_reduction_is_reported_not_gate=True,
            finite_simulation_not_population_guarantee=True))
        base.freeze_files(frozen, [root/'plan.json'])
        base.save(root/'frozen_inputs_and_evidence.json', frozen)
        previous_phase = 'static'
        for item in commands:
            current = {k:v for k,v in item.items() if k != 'command'}
            changed = base.changed_inputs(frozen)
            if changed:
                raise RuntimeError('Frozen inputs changed: ' + repr(changed))
            if item['phase'] != previous_phase:
                if previous_phase == 'static':
                    manifests = {m: base.static.validate_manifest(root/'static_preflight'/m/'acceptance.json',
                        base.static.map_context(m)) for m in base.MAPS}
                    base.save(root/'static_gate.json', manifests)
                    if not all(v.get('valid') is True for v in manifests.values()):
                        raise RuntimeError('Fresh map-bound static/RViz gate failed')
                else:
                    gate = phase_gate(commands, previous_phase)
                    base.save(root/(previous_phase+'_gate.json'), gate)
                    report_partial(root)
                    if gate['valid'] is not True:
                        raise RuntimeError('Cannot start OFF300: fresh ON15 gate incomplete')
                previous_phase = item['phase']
            status('RUNNING')
            print('START', item['name'], flush=True)
            try:
                code = base.execute(item, root, env)
            except base.MemoryRunawayError:
                history.append(dict(name=item['name'], phase=item['phase'], returncode=None,
                    valid=False, diagnostic_contaminated=True,
                    contamination_marker=str(Path(item['path'])/'diagnostic_contamination.json')))
                raise
            entry = dict(name=item['name'], phase=item['phase'], returncode=code)
            history.append(entry)
            if 'path' in item:
                folder = Path(item['path'])
                audit = base.triplet_audit(folder, item['map'], item['run'], item['phase']=='preflight',
                    item['candidate'], item['modes'], True)
                base.save(folder/'triplet_verification.json', audit)
                entry.update(valid=audit['valid'], outcome_failures=audit['outcome_failures'])
                if item['phase'] == 'preflight':
                    try:
                        base.save(folder/'thread_cpu_summary.json', {m:base.stages.summarize(folder,m,item['run'],item['map'])
                            for m in base.MODES if (folder/f'{m}_summary.json').is_file()})
                    except Exception as exc:
                        base.save(folder/'stage_analysis_error.json', dict(error=repr(exc)))
                if code or audit['valid'] is not True:
                    raise RuntimeError('Flight gate failed; original attempts retained: ' + item['name'])
                base.freeze_files(frozen, [folder/'plan.json', folder/'raw.csv', folder/'status.json',
                    folder/'triplet_verification.json', *(folder/f'{m}_summary.json' for m in base.MODES)])
            elif code:
                raise RuntimeError('Static preflight failed; evidence retained: ' + item['name'])
            elif item['name'].startswith('accept_'):
                manifest = root/'static_preflight'/item['map']/'acceptance.json'
                validation = base.static.validate_manifest(manifest, base.static.map_context(item['map']))
                if validation.get('valid') is not True:
                    raise RuntimeError('Fresh static manifest validation failed: ' + item['map'])
                base.freeze_files(frozen, [manifest, *map(Path, validation.get('evidence_sha256', {}))])
            base.save(root/'frozen_inputs_and_evidence.json', frozen)
            print('FINISH', json.dumps(entry), flush=True)
            status('RUNNING')
        gate = phase_gate(commands, 'confirmation20')
        base.save(root/'confirmation20_gate.json', gate)
        if gate['valid'] is not True or base.changed_inputs(frozen) or base.sha(base.event.NORMAL) != base.event.NORMAL_SHA:
            raise RuntimeError('Final exact OFF300/frozen-input/historical-Normal gate failed')
        if any(r['state'] != 'WRITTEN' for r in report_partial(root)):
            raise RuntimeError('Flights finished but report incomplete; do not claim final completion')
        status('COMPLETE', completed_off_flights=300, completed_on_flights=15,
               outcome_failures=[h for h in history if h.get('outcome_failures')])
    except BaseException as exc:
        status('STOPPED_FOR_DIAGNOSIS', error=repr(exc))
        report_partial(root)
        raise
    finally:
        for sig, handler in handlers.items():
            signal.signal(sig, handler)


if __name__ == '__main__':
    main()
