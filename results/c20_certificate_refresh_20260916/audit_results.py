#!/usr/bin/env python3
"""Offline C20 verification; retain every slot and keep ON/OFF separate."""
import collections
import csv
import hashlib
import json
from pathlib import Path
import re
import statistics
import sys

ROOT = Path('/root/super-sector-filter')
sys.path.insert(0, str(ROOT / 'scripts/native_campaign'))
from adaptive_cpu40_seed1 import comparison

HERE = Path(__file__).resolve().parent
CAMPAIGN = HERE / 'validation'
MODES = ('full', 'sector', 'adaptive')


def read(path):
    return json.loads(path.read_text())


def main():
    plan = read(CAMPAIGN / 'plan.json')
    rows = []
    triplets = []
    for command in plan['commands']:
        if 'cohort' not in command:
            continue
        folder = Path(command['path'])
        summaries = []
        for mode in MODES:
            path = folder / f'{mode}_summary.json'
            if not path.exists():
                continue
            s = read(path)
            summaries.append(s)
            stack_path = folder / 'artifacts' / f'seed1_run{command["run"]}_{mode}.attempt1.stack.log'
            stack = stack_path.read_text(errors='replace')
            outcomes = collections.Counter(re.findall(r'\[TRAJ_GUARD_REFRESH\] trigger=\S+ outcome=(\S+)', stack))
            terminal = collections.Counter(re.findall(r'\[TRAJ_GUARD_CERT\] trigger=main_pre status=(VERSION_CHANGED|VALIDATION_TIMEOUT)', stack))
            checks = dict(completed=s.get('success') is True, zero_contact=s.get('safety_collisions') == 0,
                run_valid=s.get('run_valid') is True, resource=s.get('resource_valid') is True,
                speed=s.get('speed_limit_valid') is True,
                source=bool(s.get('source_acquisition', {}).get('checks')) and all(s['source_acquisition']['checks'].values()),
                recovery=s.get('strict_recovery_audit', {}).get('valid') is True,
                timing=s.get('small_pool_timing', {}).get('valid') is True,
                profile_setting=s.get('cpu_profile') == (command['cohort'] == 'profile_preflight'))
            rows.append(dict(run=command['run'], mode=mode, cohort=command['cohort'], checks=checks,
                mission_time_s=s['mission_time_s'], mean_cpu_cores=s['end_to_end_cpu_cores_mean'],
                cumulative_cpu_core_s=s['end_to_end_cpu_core_s'],
                recovery_cycles=s['strict_recovery_audit'].get('opened_cycles'),
                certified_recovery_closures=len(s['strict_recovery_audit'].get('completed_cycles', [])),
                refresh_outcomes=dict(outcomes), main_pre_terminal_version_or_timeout=dict(terminal),
                evidence=str(stack_path), evidence_sha256=hashlib.sha256(stack_path.read_bytes()).hexdigest()))
        paired = comparison(summaries, 30) if len(summaries) == 3 else None
        triplets.append(dict(run=command['run'], cohort=command['cohort'], complete=len(summaries) == 3,
                             comparison=paired))
    primary = [r for r in rows if r['cohort'] == 'unprofiled_validation']
    aggregates = {}
    for mode in MODES:
        group = [r for r in primary if r['mode'] == mode]
        aggregates[mode] = dict(n=len(group), successes=sum(r['checks']['completed'] for r in group),
            zero_contact_runs=sum(r['checks']['zero_contact'] for r in group),
            **{key: dict(mean=statistics.mean(r[key] for r in group), min=min(r[key] for r in group),
                         max=max(r[key] for r in group)) if group else None
               for key in ('mission_time_s', 'mean_cpu_cores', 'cumulative_cpu_core_s', 'recovery_cycles')})
    reductions = {}
    for mode in ('sector','adaptive'):
        reductions[mode] = {key: 100 * (1 - aggregates[mode][key]['mean'] / aggregates['full'][key]['mean'])
            if aggregates[mode][key] and aggregates['full'][key] else None
            for key in ('mission_time_s','mean_cpu_cores','cumulative_cpu_core_s')}
    checks = dict(execution_complete=read(CAMPAIGN / 'status.json')['state'] == 'COMPLETE',
        all_planned_triplets_complete=all(t['complete'] for t in triplets),
        exact_off_5_per_mode=all(a['n'] == 5 for a in aggregates.values()),
        all_run_safety_source_timing_checks=bool(rows) and all(all(r['checks'].values()) for r in rows),
        all_paired_time_guards=all(t['comparison'] is not None and t['comparison']['mission_time_guardrail_pass'] for t in triplets),
        all_reference_time_guards=all(t['comparison'] is not None and t['comparison']['per_mode_reference_time_guardrail_pass'] for t in triplets),
        runtime_hashes_unchanged=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==v for p,v in plan['runtime_sha256'].items()))
    report = dict(checks=checks, all_verification_gates_pass=all(checks.values()), rows=rows, triplets=triplets,
        unprofiled_aggregates=aggregates, unprofiled_reductions_pct=reductions,
        mean_cpu30_observed=reductions['adaptive']['mean_cpu_cores'] is not None and reductions['adaptive']['mean_cpu_cores'] >= 30,
        mean_cpu40_observed=reductions['adaptive']['mean_cpu_cores'] is not None and reductions['adaptive']['mean_cpu_cores'] >= 40,
        warnings=['Finite seed1 result, not population/generalization guarantee.',
                  'Logged refresh outcomes are callback events, not avoided-collision counts.',
                  'ON and OFF are not pooled. Old C19 is not pooled.',
                  'One preflight launch-environment failure occurred before any flight; retained at parent root.',
                  'CPU includes simulator; mean cores and accumulated core-s use the cgroup observation window.'])
    stopped = CAMPAIGN / 'repeats/r03_run9603'
    failing = stopped / 'full_summary.json'
    if failing.exists():
        s = read(failing)
        memory_path = stopped / 'artifacts/seed1_run9603_full.attempt1.memory.csv'
        with memory_path.open() as stream:
            memory = list(csv.DictReader(stream))
        resource_samples = {}
        for key in ('system_available_kib', 'fsm_rss_kib', 'fsm_swap_kib', 'psi_some_avg10', 'psi_full_avg10'):
            values = [float(r[key]) for r in memory if r.get(key) not in ('', 'nan', None)]
            resource_samples[key] = dict(min=min(values), max=max(values)) if values else None
        report['stopped_run_diagnostic'] = dict(run=9603, mode='full',
            timing=s['small_pool_timing'], intervals=s['message_intervals'],
            resource_samples=resource_samples, resource_valid=s['resource_valid'],
            header_gap_occurrence_timestamp_recorded=False,
            causal_alignment_with_replan_or_external_cpu_available=False,
            extra_geometry_retry_logged=bool(re.search(r'\[TRAJ_GUARD_REFRESH\][^\n]*retry=1',
                (stopped / 'artifacts/seed1_run9603_full.attempt1.stack.log').read_text(errors='replace'))),
            important='No memory-pressure evidence in retained samples is not proof against every transient stall.')
    (HERE / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(checks=checks, unprofiled_aggregates=aggregates,
                         unprofiled_reductions_pct=reductions), indent=2))


if __name__ == '__main__':
    main()
