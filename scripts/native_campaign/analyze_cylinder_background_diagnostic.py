#!/usr/bin/env python3
"""Offline diagnostic summary, preserving original observation-end gap metrics.

The first Sector run exposed a cleanup tail after goal completion. Report both
the original observer window and a post-hoc, goal-bounded flight window; never
replace the underlying data or use cleanup as evidence of in-flight starvation.
"""
import argparse
import csv
import json
import statistics
from pathlib import Path

from cylinder_background_diagnostic import gap_metrics
from confirm_cylinder_search_n20 import known_outcome, safe
from analyze_cylinder_only_stress_full_gate import quality_valid, boolean


def analyze(root):
    rows=list(csv.DictReader((root/'diagnostic_raw.csv').open()))
    details=[]
    for row in rows:
        name,run,mode=row['map'],row['run'],row['mode']
        prefix=f'{name}_run{run}_{mode}'
        ack=json.loads((root/'ack'/f'{prefix}.json').read_text())
        solid=json.loads((root/'solid'/f'{prefix}.json').read_text())
        finish=(solid['waypoint_epoch_s'][-1] if solid.get('success')
                else ack['last_odom_epoch_s'])
        start=ack['first_odom_epoch_s']+10
        metrics=gap_metrics([s['receive_epoch_s'] for s in ack['samples']],start,finish)
        log=(root/'artifacts'/f'{prefix}.attempt1.stack.log').read_text(errors='replace')
        details.append(dict(map=name,run=int(run),mode=mode,complete=boolean(row['success']),
            safe_complete=safe(row),quality_valid=quality_valid(row) and known_outcome(row),
            mission_time_s=float(row['mission_time_s']),solid_contacts=int(row['solid_collision_episodes']),
            minimum_solid_clearance_m=float(row['solid_min_clearance_m']),
            original_observer_window=ack['post_warmup'],goal_bounded_window=metrics,
            flight_window_end_kind='solid_fifth_waypoint' if solid.get('success') else 'last_odom_includes_cleanup',
            log_counts={k:log.count(k) for k in ['MAP_STALE','Empty or non-dense point cloud']},
            raw_solid_report=row['solid_report_json']))
    summary={}
    for mode in ('full','sector','adaptive'):
        rr=[r for r in details if r['mode']==mode]
        if not rr: continue
        summary[mode]=dict(runs=len(rr),complete=sum(r['complete'] for r in rr),
            contact_trials=sum(r['solid_contacts']>0 for r in rr),
            contact_episodes=sum(r['solid_contacts'] for r in rr),
            all_quality_valid=all(r['quality_valid'] for r in rr),
            mission_time_mean_s=statistics.mean(r['mission_time_s'] for r in rr),
            minimum_solid_clearance_m=min(r['minimum_solid_clearance_m'] for r in rr),
            goal_bounded_ack_gap_max_s=max(r['goal_bounded_window']['max_gap_s'] for r in rr),
            original_observer_ack_gap_max_s=max(r['original_observer_window']['max_gap_s'] for r in rr))
    return dict(schema='cylinder-background-diagnostic-analysis-v1',diagnostic_only=True,
        analysis_boundary_amendment='Post-hoc after first Sector run: additionally bound completed flights at solid-observed WP5; original tail-inclusive metrics retained',
        extra_ack_observer=True,not_standard_n20=True,not_cpu_comparison=True,
        all_nine_unique_rows=len(details)==9 and {(r['run'],r['mode']) for r in details}==
            {(run,mode) for run in range(1,4) for mode in ('full','sector','adaptive')},
        counts=summary,rows=details)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root',type=Path);parser.add_argument('--out',type=Path)
    args=parser.parse_args();result=analyze(args.root)
    if args.out: args.out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({'all_nine_unique_rows':result['all_nine_unique_rows'],'counts':result['counts']},indent=2))
