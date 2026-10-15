#!/usr/bin/env python3
"""Offline inspection of all retained C21 slots, plus timestamp-linked spans."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import statistics
from adaptive_cpu40_seed1 import comparison


def audit(root):
    plan = json.loads((root / 'plan.json').read_text())
    rows, pairs = [], []
    for item in plan['commands']:
        if 'modes' not in item:
            continue
        folder = Path(item['path'])
        summaries = []
        for mode in item['modes']:
            path = folder / f'{mode}_summary.json'
            if not path.exists():
                continue
            s = json.loads(path.read_text())
            summaries.append(s)
            intervals = s.get('message_intervals', {}).get('odometry', {})
            stack_path = folder / 'artifacts' / f'seed1_run{s["run"]}_{mode}.attempt1.stack.log'
            stack = stack_path.read_text(errors='replace')
            spans = [dict(re.findall(r'(\w+)=([^\s]+)', line)) for line in stack.splitlines()
                     if '[CALLBACK_TIMING]' in line]
            for span in spans:
                for key in ('begin_ns', 'end_ns', 'epoch_begin_ns', 'epoch_end_ns',
                            'previous_begin_ns', 'previous_end_ns', 'tid'):
                    span[key] = int(span[key])
                for key in ('start_gap_ms', 'duration_ms'):
                    span[key] = float(span[key])
            contexts = []
            for event in intervals.get('gap_events', []):
                # MONOTONIC shared host clock; receipt includes transport delay.
                lo, hi = event['previous_receipt_ns'], event['receipt_ns']
                overlaps = [span for span in spans
                            if span['end_ns'] >= lo - 1000000 and span['begin_ns'] <= hi + 1000000]
                nearby_odom = [span for span in spans if span['name'] == 'SimOdom'
                               and abs(span['begin_ns'] - hi) <= 5000000]
                contexts.append(dict(event=event, overlapping_reported_spans=overlaps,
                                     nearby_odom_start_gap_spans=nearby_odom))
            checks = dict(completed=s.get('success') is True, zero_contact=s.get('safety_collisions') == 0,
                run_valid=s.get('run_valid') is True, resource=s.get('resource_valid') is True,
                speed=s.get('speed_limit_valid') is True,
                source=bool(s.get('source_acquisition', {}).get('checks')) and
                       all(v is True for v in s['source_acquisition']['checks'].values()),
                recovery=s.get('strict_recovery_audit', {}).get('valid') is True,
                timing=s.get('small_pool_timing', {}).get('valid') is True,
                expected_profile=s.get('cpu_profile') == (not item['name'].startswith('off_')),
                expected_trace=s.get('callback_trace') == (plan['phase'] == 'diagnosis'),
                untraced_logs_clean=plan['phase'] == 'diagnosis' or not spans)
            rows.append(dict(run=s['run'], mode=mode, cohort=item['name'], checks=checks,
                mission_time_s=s['mission_time_s'], mean_cpu_cores=s['end_to_end_cpu_cores_mean'],
                cumulative_cpu_core_s=s['end_to_end_cpu_core_s'],
                recovery_cycles=s['strict_recovery_audit'].get('opened_cycles'),
                closed_recovery_cycles=len(s['strict_recovery_audit'].get('completed_cycles', [])),
                odometry_hz=intervals.get('mean_received_hz'),
                header_interval=intervals.get('header_interval'), receipt_interval=intervals.get('receipt_interval'),
                max_header_context=intervals.get('max_header_context'),
                max_receipt_context=intervals.get('max_receipt_context'), gap_contexts=contexts,
                reported_spans=spans, evidence=str(path),
                evidence_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        if plan['phase'] == 'validation':
            pairs.append(dict(cohort=item['name'], complete=len(summaries) == 3,
                comparison=comparison(summaries, 30) if len(summaries) == 3 else None))
    off = [r for r in rows if r['cohort'].startswith('off_')]
    aggregates = {}
    for mode in ('full', 'sector', 'adaptive'):
        group = [r for r in off if r['mode'] == mode]
        aggregates[mode] = dict(n=len(group), completed=sum(r['checks']['completed'] for r in group),
            zero_contact_runs=sum(r['checks']['zero_contact'] for r in group),
            timing_passes=sum(r['checks']['timing'] for r in group),
            **{key: statistics.mean(r[key] for r in group) if group else None
               for key in ('mission_time_s', 'mean_cpu_cores', 'cumulative_cpu_core_s', 'recovery_cycles')})
    reductions = {mode: {key: 100*(1-aggregates[mode][key]/aggregates['full'][key])
                             if aggregates[mode][key] is not None and aggregates['full'][key] else None
                        for key in ('mean_cpu_cores', 'cumulative_cpu_core_s')}
                  for mode in ('sector', 'adaptive')}
    status = json.loads((root / 'status.json').read_text())
    gates = dict(validation_not_diagnostic=plan['phase'] == 'validation',
        controller_complete=status['state'] == 'COMPLETE',
        exact_off_5_each=all(v['n'] == 5 for v in aggregates.values()),
        all_slots_complete=bool(pairs) and all(p['complete'] for p in pairs),
        all_flight_checks=bool(rows) and all(all(r['checks'].values()) for r in rows),
        all_paired_time_and_reference_guards=bool(pairs) and all(p['comparison'] and
            p['comparison']['mission_time_guardrail_pass'] and
            p['comparison']['per_mode_reference_time_guardrail_pass'] for p in pairs),
        runtime_hashes_unchanged=all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == v
                                   for p, v in plan['runtime_sha256'].items()))
    report = dict(checks=gates, all_verification_gates_pass=all(gates.values()), rows=rows,
        triplets=pairs, unprofiled_aggregates=aggregates, unprofiled_reductions_pct=reductions,
        mean_cpu30_observed=reductions['adaptive']['mean_cpu_cores'] is not None and reductions['adaptive']['mean_cpu_cores'] >= 30,
        mean_cpu40_observed=reductions['adaptive']['mean_cpu_cores'] is not None and reductions['adaptive']['mean_cpu_cores'] >= 40,
        caveats=['Diagnostic trace logs only gaps/durations over20ms, not every active callback.',
                 'Overlap is evidence of concurrency, not by itself causal proof.',
                 'ON/OFF/diagnostic/historical results are never pooled.',
                 'Finite tuned-seed1 validation, not population or generalization guarantee.'])
    (root / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('checks', 'unprofiled_aggregates', 'unprofiled_reductions_pct')}, indent=2))
    for r in rows:
        print(r['run'], r['mode'], r['mission_time_s'], r['header_interval']['max_ms'],
              r['receipt_interval']['max_ms'], 'failed:', [k for k,v in r['checks'].items() if not v])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('campaign', type=Path)
    audit(parser.parse_args().campaign.resolve())
