#!/usr/bin/env python3
"""Bounded sequential diagnostics for five fixed-background cylinder maps.

First finish one three-mode block on each map, then extend reference-safe maps
to three blocks. Full/Adaptive failures stop that candidate only at a block
boundary. Extra read-only ACK instrumentation is not standard n20 evidence.
"""
import csv
import fcntl
import json
import os
from pathlib import Path
import time

import cylinder_background_variants as variants
import cylinder_background_diagnostic as diagnostic
import analyze_cylinder_background_diagnostic as analysis
import cylinder_solid_campaign as solid
import confirm_cylinder_search_n20 as confirmation
from analyze_cylinder_only_stress_full_gate import quality_valid
from audit_cylinder_flight_segments import segments

ROOT=variants.search.ROOT/'results/cylinder_background_five_20260915'
MODES=('full','sector','adaptive')


def read_rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def validate(rows,name):
    keys={(int(r['run']),r['mode']) for r in rows}
    allowed={(n,m) for n in range(1,4) for m in MODES}
    if (len(keys)!=len(rows) or not keys <= allowed or
            any(r['map']!=name or not quality_valid(r) or not confirmation.known_outcome(r) for r in rows)):
        raise RuntimeError('Invalid/duplicate evidence retained; diagnosis required')


def reference_failed(rows):
    return any(r['mode'] in ('full','adaptive') and not confirmation.safe(r) for r in rows)


def may_start_or_finish_block(rows,run):
    return run==1 or any(int(r['run'])==run for r in rows) or not reference_failed(rows)


def ack_observer_valid(ack):
    # A live observer with zero ACKs is legitimate starvation evidence, not
    # automatically an instrumentation failure that may be discarded.
    return (ack['malformed']==0 and ack['first_odom_epoch_s'] is not None
            and ack['last_odom_epoch_s'] is not None)


def save(path,value):
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(path)


def summarize(folder):
    result=analysis.analyze(folder)
    rows=read_rows(folder/'diagnostic_raw.csv')
    sector=[r for r in result['rows'] if r['mode']=='sector']
    separation=any(not confirmation.safe(r) for r in rows if r['mode']=='sector')
    ref_failure=reference_failed(rows)
    result['reference_failure']=ref_failure
    result['sector_observed_failure']=separation
    result['sector_long_map_ack_gap']=any(r['goal_bounded_window']['max_gap_s']>1.0 for r in sector)
    result['decision']=('REJECT_REFERENCE_FAILURE' if ref_failure else
        'INCOMPLETE_DIAGNOSTIC' if not result['all_nine_unique_rows'] else
        'NO_OBSERVED_OUTCOME_SEPARATION' if not separation else
        'INPUT_LIVENESS_DIAGNOSIS_REQUIRED' if result['sector_long_map_ack_gap'] else
        'OUTCOME_SEPARATION_REQUIRES_CAUSAL_AUDIT')
    result['automatically_qualified_for_n20']=False
    result['failure_segments']=[dict(run=r['run'],mode=r['mode'],segments=segments(Path(r['solid_report_json'])))
                                for r in rows if not confirmation.safe(r)]
    save(folder/'summary.json',result)
    return {k:result[k] for k in ('counts','all_nine_unique_rows','decision',
                                 'reference_failure','sector_observed_failure','sector_long_map_ack_gap')}


def verify_assets(plan):
    g=variants.search.geometry
    if variants.search.frozen_policy()!=plan['runtime_policy']:
        raise RuntimeError('Runtime policy changed')
    for p,h in {**plan['instrumentation_sha256'],**plan['manifest_sha256']}.items():
        if g.sha256(Path(p))!=h: raise RuntimeError('Frozen research helper or manifest changed')


def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    lock=(ROOT/'controller.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    g=variants.search.geometry
    files=[Path(__file__).resolve(),Path(variants.__file__),Path(diagnostic.__file__),
           Path(analysis.__file__),Path(solid.__file__),solid.OBSERVER,Path(confirmation.__file__)]
    plan=dict(schema='five-map-background-diagnostic-v1',recipes=variants.RECIPES,
        first_sweep_blocks=1,maximum_blocks_per_map=3,maximum_flights=45,
        mode_order='F/S/A, S/A/F, A/F/S; complete block before candidate futility stop',
        stopping_rule='after first sweep, do not extend maps with any Full/Adaptive unsafe completion',
        no_parallel_flights=True,extra_read_only_ack_observer=True,not_standard_n20=True,
        no_automatic_confirmation=True,no_runtime_changes=True,preserves_all_outcomes=True,
        selection='exploratory related family; no population or blind-generalization claim',
        runtime_policy=variants.search.frozen_policy(),
        instrumentation_sha256={str(p):g.sha256(p) for p in files},
        manifest_sha256={str(variants.search.OUT/r['name']/'manifest.json'):
                         g.sha256(variants.search.OUT/r['name']/'manifest.json') for r in variants.RECIPES})
    freeze=ROOT/'plan.json'
    if freeze.exists() and json.loads(freeze.read_text())!=plan:
        raise RuntimeError('Frozen five-map plan changed')
    if not freeze.exists(): save(freeze,plan)
    verify_assets(plan)
    state=dict(pid=os.getpid(),state='RUNNING',completed=0,maximum_flights=45,maps={})
    rows_by_map={}
    for recipe in variants.RECIPES:
        name=recipe['name'];folder=ROOT/name;folder.mkdir(exist_ok=True)
        raw=folder/'diagnostic_raw.csv';rows=read_rows(raw) if raw.exists() else []
        validate(rows,name);rows_by_map[name]=rows
        if rows: state['maps'][name]=summarize(folder)
    def checkpoint():
        state['completed']=sum(len(rows) for rows in rows_by_map.values())
        state['updated_epoch_s']=time.time();save(ROOT/'status.json',state)
    checkpoint();solid.search.campaign.install_campaign_signal_handlers()
    try:
        # All five maps receive their first block before any candidate repeats.
        for run in range(1,4):
            for recipe in variants.RECIPES:
                name=recipe['name'];folder=ROOT/name;raw=folder/'diagnostic_raw.csv'
                rows=rows_by_map[name]
                if not may_start_or_finish_block(rows,run): continue
                existing={(int(r['run']),r['mode']) for r in rows}
                with raw.open('a',newline='') as stream:
                    writer=csv.DictWriter(stream,fieldnames=solid.FIELDS,extrasaction='ignore',lineterminator='\n')
                    if not rows: writer.writeheader();stream.flush()
                    offset=run-1
                    for mode in MODES[offset:]+MODES[:offset]:
                        if (run,mode) in existing: continue
                        state.update(map=name,run=run,mode=mode,phase='initial_five_map_sweep' if run==1 else 'repeat_reference_safe_maps')
                        checkpoint();verify_assets(plan)
                        row,ack=diagnostic.trial(name,mode,run,folder)
                        writer.writerow(row);stream.flush();rows.append(row)
                        checkpoint();validate(rows,name)
                        if not ack_observer_valid(ack):
                            raise RuntimeError('Invalid ACK observer evidence retained')
                        verify_assets(plan)
                        state['maps'][name]=summarize(folder)
                        state['last']=dict(map=name,run=run,mode=mode,success=row['success'],
                            solid_contacts=row['solid_collision_episodes'],mission_time_s=row['mission_time_s'])
                        checkpoint();print('FIVE_MAP_RESULT '+json.dumps(state['last']),flush=True)
        state.update(state='FIVE_MAP_DIAGNOSTICS_COMPLETE',phase='analysis_ready')
    except BaseException as error:
        state.update(state='STOPPED_FOR_DIAGNOSIS',error=str(error));raise
    finally:
        checkpoint();solid.search.campaign.cleanup_active_process_groups()


if __name__=='__main__':main()
