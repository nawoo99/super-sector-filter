"""Descriptive failure signatures for map-only redesign, not causal proofs."""
import csv
import json
from pathlib import Path

import confirm_cylinder_search_n20 as confirmation
from cylinder_background_diagnostic import gap_metrics
from audit_cylinder_flight_segments import segments


def audit_row(row):
    path=Path(row['solid_report_json']);folder=path.parent.parent
    stem=f"{row['map']}_run{row['run']}_{row['mode']}"
    report=json.loads(path.read_text())
    with path.with_suffix('.poses.csv').open() as stream:poses=list(csv.DictReader(stream))
    log=(folder/'artifacts'/f'{stem}.attempt1.stack.log').read_text(errors='replace')
    counts={p:log.count(p) for p in ('MAP_STALE','Empty or non-dense point cloud',
                                    '0.1 seconds time limit exceeded','REROUTE_EPOCH_RESET')}
    ack_path=folder/'ack'/f'{stem}.json';ack_gap=None
    if ack_path.exists():
        ack=json.loads(ack_path.read_text())
        end=report['waypoint_epoch_s'][-1] if report.get('success') else ack['last_odom_epoch_s']
        ack_gap=gap_metrics([s['receive_epoch_s'] for s in ack['samples']],ack['first_odom_epoch_s']+10,end)['max_gap_s']
    stats_path=folder/'artifacts'/f'{stem}.attempt1.filt_stats.json'
    stats=json.loads(stats_path.read_text()) if stats_path.exists() else {}
    pending=bool(stats.get('trajectory_guard_full_refresh_pending_ack') or stats.get('pre_stale_full_refresh_pending_ack'))
    parts=segments(path)
    longest=max((s['longest_pose_hold_s'] for s in parts),default=0.)
    position=[float(poses[-1][k]) for k in ('x','y','z')]
    contacted=not confirmation.contact_free(row) or int(row['solid_collision_episodes'])>0
    if contacted:
        signature='CONTACT'
        if report.get('first_contact'):position=report['first_contact']['position']
    elif confirmation.safe(row):signature='SAFE_COMPLETE'
    elif counts['Empty or non-dense point cloud']>=100 and longest>=20 and (ack_gap is None or ack_gap>5):
        signature='EMPTY_INPUT_STALL'
    elif pending:signature='PENDING_REFRESH_ACK'
    elif counts['0.1 seconds time limit exceeded']>=30:signature='PATH_SEARCH_STALL'
    else:signature='OTHER_NONCOMPLETION'
    return dict(map=row['map'],run=int(row['run']),mode=row['mode'],signature=signature,
                diagnostic_not_causal_proof=True,position=position,complete=confirmation.boolean(row['success']),
                solid_contacts=int(row['solid_collision_episodes']),log_counts=counts,
                ack_gap_s=ack_gap,ack_instrumented=ack_path.exists(),pending_refresh_ack=pending,
                longest_actual_pose_hold_s=longest,segments=parts,solid_report=str(path),
                max_position_step_m=report.get('max_position_step_m'),
                limitation='Sampled-pose contacts; no continuous swept/dynamics guarantee. Without ACK observer, empty-input classification is a log/hold proxy.')


def audit_failures(rows):
    return [audit_row(r) for r in rows if not confirmation.safe(r)]


def meaningful_sector_difference(rows,audits):
    # Do not select the old all-timeout/empty-cloud stall phenotype as a win.
    return (any(r['mode']=='sector' and confirmation.boolean(r['success']) for r in rows)
            and any(a['mode']=='sector' and a['signature'] not in
                    ('EMPTY_INPUT_STALL','PENDING_REFRESH_ACK','SAFE_COMPLETE') for a in audits))


def feedback_recipe(name,parent,index,audits):
    reference=[a for a in audits if a['mode'] in ('full','adaptive')]
    failures=reference or audits
    if failures:
        a=failures[0];position=a['position'][:2]
        if a['signature'] in ('EMPTY_INPUT_STALL','PENDING_REFRESH_ACK'):
            return dict(name=name,parent=parent,action='add_observability',position=position)
        return dict(name=name,parent=parent,action='open_escape',position=position,escape_radius=4.)
    return dict(name=name,parent=parent,action='harden',iteration=index)


if __name__=='__main__':
    import argparse
    from gen_cylinder_only_stress import sha256
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('raw',type=Path,nargs='+');parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();results=[]
    for path in args.raw:
        with path.open() as stream:rows=list(csv.DictReader(stream))
        results.extend(audit_failures(rows))
    output=dict(schema='descriptive-map-feedback-audit-v1',causal_proof=False,
                sources={str(p):sha256(p) for p in args.raw},failures=results)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(dict(failures=len(results),output=str(args.out))))
