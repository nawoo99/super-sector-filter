#!/usr/bin/env python3
"""Frozen V6: Forest 30 flights, then an independent seven-map 210 flights.

One child per physical flight permits an immediate reference/evidence gate.
Background execution is local, durable, and never sends email or promotes V6.
"""
import argparse
import csv
from datetime import datetime
import json
import math
import os
from pathlib import Path
import signal
import statistics
import subprocess
import sys
import time
from zoneinfo import ZoneInfo

from audit_forest_stopped_topology_diagnostic import audit
from scenario7_geometry import load_geometry, SampledSolidAudit, sha256
from topology_polyline_v6_pilot import inspect, SOURCE, INSTALL, DIAGNOSTICS, LAUNCHER

REPO = Path('/root/super-sector-filter')
MAPS = tuple(f'gapfree_d1_m{i:02d}' for i in range(1,5)) + (
    'gapfree_d1_m05r2', 'urban_blocks_u01', 'forest_cluster_f01')
MODES = ('full','sector','adaptive')
LABELS = dict(zip(MAPS, ('Map1','Map2','Map3','Map4','Map5','Urban','Forest')))


def plan():
    rows = []
    for stage, maps, first in (('forest_n10',MAPS[-1:],99401),
                               ('seven_map_n10',MAPS,99501)):
        for repeat in range(1,11):
            for index,name in enumerate(maps):
                rotation = (repeat-1+index)%3
                run = first + (repeat-1)*len(maps)+index
                for mode in MODES[rotation:] + MODES[:rotation]:
                    rows.append(dict(stage=stage,map=name,mode=mode,repeat=repeat,run=run,
                        directory=f'{stage}/{name}/r{repeat:02d}/{mode}'))
    assert len(rows)==240 and len({(r['stage'],r['map'],r['run'],r['mode']) for r in rows})==240
    return rows


def reference_failure(flight):
    return flight['mode'] in ('full','adaptive') and (
        not flight['success'] or flight['contacts']>0)


def artifact_folder(value):
    path=Path(value)
    return path if path.is_absolute() else REPO/path


def json_write(path,document,exclusive=False):
    with path.open('x' if exclusive else 'w') as stream:
        json.dump(document,stream,indent=2); stream.write('\n')


def verify_hashes(hashes):
    for path,expected in hashes.items():
        if sha256(path)!=expected:
            raise ValueError('Frozen input changed: '+path)


def replay_solid(folder,flight):
    stem=folder/'artifacts'/f"{flight['map']}_run{flight['run']}_{flight['mode']}.attempt1"
    report=json.loads(Path(str(stem)+'.solid_audit.json').read_text())
    geometry=load_geometry(report['pcd_path'])
    if sha256(report['geometry_path'])!=report['geometry_sha256']:
        raise ValueError('Solid geometry changed')
    observer=SampledSolidAudit(geometry)
    odometry=Path(str(stem)+'.odometry.csv')
    with odometry.open(newline='') as stream:
        for index,row in enumerate(csv.DictReader(stream),1):
            if int(row['sample'])!=index:
                raise ValueError('Unordered received odometry')
            clearance=observer.observe([float(row[k]) for k in ('x_m','y_m','z_m')],
                [float(row[k]) for k in ('vx_mps','vy_mps','vz_mps')],
                int(row['header_ns']),int(row['receipt_monotonic_ns']),float(row['elapsed_s']))
            if clearance is None or not math.isclose(clearance,float(row['clearance_m']),abs_tol=1e-12):
                raise ValueError('Independent clearance disagreement')
    observed=observer.summary()
    if any(report[key]!=value for key,value in observed.items()):
        raise ValueError('Independent solid summary disagreement')
    return dict(samples=observed['samples'],contact_episodes=observed['contact_episodes'],
        min_body_clearance_m=observed['min_clearance_m'],
        max_receipt_interval_s=observed['max_receipt_interval_s'],
        odometry_sha256=sha256(odometry),received_samples_only=True,swept_collision_check=False)


def admission():
    for key,value in os.environ.items():
        if key.startswith('SUPER_TEST_') and value not in ('','0'):
            raise ValueError('Fault hook forbidden: '+key)
    if os.environ.get('SUPER_PLANNER_FAILURE_CAPTURE_DIR'):
        raise ValueError('Diagnostic capture forbidden in performance campaign')
    checks=[audit(DIAGNOSTICS/name) for name in ('v6_control','v6_available','v6_exhausted')]
    if not all(row['evidence_valid'] and row['criterion_met'] for row in checks):
        raise ValueError('Targeted V6 admission failed')
    validation=json.loads((DIAGNOSTICS/'validation_v6.json').read_text())
    for name in ('perfect_drone_full_node','perfect_drone_adaptive_node'):
        binary=INSTALL/'perfect_drone_sim/lib/perfect_drone_sim'/name
        if sha256(binary)!=validation[name+'_sha256']:
            raise ValueError('Not the physically validated V6 binary')
    smoke=json.loads((DIAGNOSTICS/'audit_pilot_v6.json').read_text())
    if smoke['physical_flights']!=9 or smoke['safe_complete']!=9 or not smoke['all_quality_valid']:
        raise ValueError('Nine-flight admission failed')
    verify_hashes(smoke['input_sha256'])
    for flight,solid in zip(smoke['flights'],smoke['solid_replays']):
        folder=artifact_folder(flight['directory'])
        current,complete=inspect(folder,flight['map'],flight['run'],[r['mode'] for r in
            json.loads((folder/'summary.json').read_text())['results']])
        matching=[r for r in current if r['mode']==flight['mode']]
        if not complete or len(matching)!=1 or not matching[0]['quality_valid'] or reference_failure(matching[0]):
            raise ValueError('Preserved smoke no longer passes')
        if matching[0]['stack_sha256']!=flight['stack_sha256']:
            raise ValueError('Preserved smoke log changed')
        for filename,key in (('raw.csv','raw_sha256'),):
            if sha256(folder/filename)!=flight[key]:
                raise ValueError('Preserved smoke evidence changed')
        stem=f"{flight['map']}_run{flight['run']}_{flight['mode']}.attempt1"
        if sha256(folder/'artifacts'/(stem+'.odometry.csv'))!=solid['odometry_sha256']:
            raise ValueError('Preserved smoke odometry changed')
    return checks,smoke


def prepare(root):
    if root.exists():
        raise ValueError('Refusing existing campaign directory')
    checks,smoke=admission()
    inputs={Path(__file__).resolve(),LAUNCHER,
        Path(__file__).with_name('scenario7_topology_liveness_v6_cpu_compare.py'),
        Path(__file__).with_name('topology_polyline_v6_pilot.py'),
        Path(__file__).with_name('audit_forest_stopped_topology_diagnostic.py'),
        Path(__file__).with_name('audit_goal_change_full_refresh_v8.py'),
        Path(__file__).with_name('scenario7_geometry.py')}
    inputs.update(Path(path) for path in smoke['input_sha256'])
    for name in MAPS:
        pcd=SOURCE/'mars_uav_sim/perfect_drone_sim/pcd/seed_maps'/(name+'.pcd')
        inputs.update((pcd,load_geometry(pcd).geometry_path,
            SOURCE/'mars_uav_sim/perfect_drone_sim/config'/(name+'.yaml')))
    inputs.update(SOURCE/'mission_planner/data'/name for name in
        ('loop24.txt','forest_wide_zigzag_v2.txt','urban_building_corners_v3.txt'))
    hashes={str(path):sha256(path) for path in sorted(inputs)}
    protocol=dict(schema='certified-polyline-v6-forest-then-seven-map-n10-v1',
        install_root=str(INSTALL),candidate='topology_liveness_trial_v6_20261006',
        created_at_kst=datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),
        planned=plan(),forest_flights=30,seven_map_flights=210,total_planned_flights=240,
        repetitions_per_map_per_mode=10,mode_order='cyclic rotation per map/repeat',
        distinct_cohorts=True,global_mission_cutoff_s=None,
        terminal_no_progress_s=60,terminal_no_progress_radius_m=0.02,
        terminal_policy='measurement-only, no planner feedback; not a mission duration limit',
        capture=False,fault_hooks=False,retries=0,stop_before_next_flight_after_reference_failure=True,
        sector_outcomes_retained=True,all_mode_evidence_required=True,
        independent_received_odometry_replay_per_flight=True,
        canonical_promoted=False,frozen_c41_replaced=False,hashes=hashes,
        targeted_admission=checks,smoke_audit_sha256=sha256(DIAGNOSTICS/'audit_pilot_v6.json'),
        estimated_forest_minutes=[50,70],estimated_seven_map_hours=[5,6],
        estimated_total_hours=[6,7],estimate_excludes_bug_fixes=True)
    root.mkdir(parents=True,exist_ok=False)
    json_write(root/'protocol.json',protocol,True)
    json_write(root/'status.json',dict(state='READY',observed_flights=0,
        total_planned_flights=240,forest_gate_passed=False,canonical_promoted=False),True)
    return protocol


def tables(root,flights):
    if not flights:
        return
    with (root/'flights.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(flights[0]),lineterminator='\n')
        writer.writeheader(); writer.writerows(flights)
    lines=['# Frozen V6: separate Forest pilot and seven-map campaign','',
        'Failed outcomes retained; time-to-terminal and completion-only time are distinct.','',
        '|Stage|Map|Mode|n|Complete|Contact runs|Safe complete|Quality valid|Observed time(s)|Complete-only time(s)|CPU(cores)|CPU(core-s/run)|Input(MiB/s)|Payload(MiB/run)|Map(ms/frame)|Adaptive Full transitions, sum|',
        '|---|---|---|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for stage in ('forest_n10','seven_map_n10'):
        for name in MAPS:
            for mode in MODES:
                group=[f for f in flights if f['stage']==stage and f['map']==name and f['mode']==mode]
                if not group:
                    continue
                n=len(group); completed=[f['time_s'] for f in group if f['success']]
                means=[statistics.mean(f[k] for f in group) for k in
                    ('time_s','cpu_cores','cpu_core_s','input_mib_s','input_mib_run','map_ms')]
                lines.append('|'+ '|'.join([stage,LABELS[name],mode,str(n),
                    f"{sum(f['success'] for f in group)}/{n}",f"{sum(f['contacts']>0 for f in group)}/{n}",
                    f"{sum(f['success'] and f['contacts']==0 for f in group)}/{n}",
                    f"{sum(f['quality_valid'] and f['solid_replay_valid'] for f in group)}/{n}",f'{means[0]:.2f}',
                    f'{statistics.mean(completed):.2f}' if completed else 'NA',
                    *(f'{v:.3f}' for v in means[1:]),
                    str(int(sum(f['full_transitions'] for f in group))) if mode=='adaptive' else 'NA'])+'|')
    (root/'summary_by_map.md').write_text('\n'.join(lines)+'\n')


def execute(root):
    protocol=json.loads((root/'protocol.json').read_text())
    state=json.loads((root/'status.json').read_text())
    if state['state']!='READY' or protocol['planned']!=plan():
        raise ValueError('No implicit resume/retry; expected untouched READY plan')
    verify_hashes(protocol['hashes'])
    state.update(state='RUNNING',pid=os.getpid(),started_epoch_s=time.time(),
        launch_requests=0,observed_flights=0,current=None)
    flights,assets,child=[],{},None

    def save():
        state['updated_epoch_s']=time.time()
        json_write(root/'status.json',state); tables(root,flights)
    def interrupt(signum,frame):
        raise InterruptedError('Campaign interrupted by signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupt); signal.signal(signal.SIGINT,interrupt)
    save()
    try:
        for item in protocol['planned']:
            verify_hashes(protocol['hashes'])
            state['current']=item; save()
            folder=root/item['directory']; folder.parent.mkdir(parents=True,exist_ok=True)
            with folder.with_suffix('.controller.log').open('x') as log:
                child=subprocess.Popen(['bash',str(LAUNCHER),str(folder),item['map'],
                    str(item['run']),item['mode']],cwd=REPO,stdout=log,stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,start_new_session=True)
                state['child_pid']=child.pid; state['launch_requests']+=1; save()
                code=child.wait()
            group,complete=inspect(folder,item['map'],item['run'],[item['mode']])
            if not complete or len(group)!=1:
                raise ValueError('Incomplete single-flight evidence; no replacement')
            flight=group[0]; flight.update(stage=item['stage'],repeat=item['repeat'],
                solid_replay_valid=False)
            flights.append(flight); state['observed_flights']=len(flights); save()
            replay=replay_solid(folder,flight)
            json_write(folder/'independent_solid_replay.json',replay,True)
            flight['solid_replay_valid']=True
            with (folder/'raw.csv').open(newline='') as stream:
                raw=list(csv.DictReader(stream))
            if len(raw)!=1 or raw[0]['map']!=item['map'] or int(raw[0]['run'])!=item['run']:
                raise ValueError('Raw flight identity disagreement')
            result=json.loads((folder/'summary.json').read_text())['results'][0]
            if result['candidate']!=protocol['candidate']:
                raise ValueError('Wrong candidate result')
            for path,digest in json.loads((folder/'plan.json').read_text())['asset_sha256'].items():
                if assets.get(path,digest)!=digest or sha256(path)!=digest:
                    raise ValueError('Child asset drift: '+path)
                assets[path]=digest
            save()
            print(json.dumps(dict(event='flight_verified',observed_flights=len(flights),
                stage=item['stage'],map=item['map'],mode=item['mode'],repeat=item['repeat'],
                success=flight['success'],contacts=flight['contacts'],time_s=flight['time_s'])),flush=True)
            if reference_failure(flight):
                state['failed_reference']=flight
                raise ValueError('Actual Full/Adaptive failure; no replacement or expansion')
            if code or not flight['quality_valid']:
                raise ValueError('Runtime/quality failure; retain and stop before next flight')
            if len(flights)==30:
                if len({(f['repeat'],f['mode']) for f in flights})!=30:
                    raise ValueError('Forest inventory incomplete')
                state['forest_gate_passed']=True; state['forest_completed_epoch_s']=time.time(); save()
                json_write(root/'forest_gate.json',dict(passed=True,flights=30,
                    full_safe_complete=sum(f['success'] and f['contacts']==0 for f in flights if f['mode']=='full'),
                    adaptive_safe_complete=sum(f['success'] and f['contacts']==0 for f in flights if f['mode']=='adaptive'),
                    sector_safe_complete=sum(f['success'] and f['contacts']==0 for f in flights if f['mode']=='sector'),
                    all_evidence_valid=True,source_hashes_verified=True),True)
        if len(flights)!=240 or len({(f['stage'],f['map'],f['run'],f['mode']) for f in flights})!=240:
            raise ValueError('Final physical inventory mismatch')
        verify_hashes(protocol['hashes'])
        json_write(root/'final_audit.json',dict(valid=True,unique_flights=240,
            forest_flights=30,seven_map_flights=210,retries=0,all_solid_replays_valid=True,
            canonical_promoted=False,frozen_c41_replaced=False,input_sha256=assets),True)
        state.update(state='COMPLETE',completed_epoch_s=time.time(),current=None); save()
        print(json.dumps(state),flush=True); return 0
    except Exception as error:
        if child and child.poll() is None:
            os.killpg(child.pid,signal.SIGINT)
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid,signal.SIGTERM); child.wait(timeout=5)
        state.update(state='STOPPED_FOR_DIAGNOSIS',error=str(error)); save()
        print(json.dumps(state),flush=True); return 1


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--output',type=Path,required=True)
    action=parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--prepare-only',action='store_true')
    action.add_argument('--execute',action='store_true')
    action.add_argument('--background',action='store_true')
    action.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    args.output=args.output.resolve()
    if args.dry_run:
        print(json.dumps(dict(planned_flights=len(plan()),forest_flights=30,seven_map_flights=210,
            global_mission_cutoff_s=None,observer_stall_s=60,output=str(args.output))))
        return 0
    if args.execute:
        return execute(args.output)
    prepare(args.output)
    if args.prepare_only:
        print(json.dumps(dict(state='READY',output=str(args.output),planned_flights=240)))
        return 0
    with (args.output/'controller.log').open('x') as log:
        child=subprocess.Popen([sys.executable,'-u',str(Path(__file__).resolve()),
            '--output',str(args.output),'--execute'],cwd=REPO,stdin=subprocess.DEVNULL,
            stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    print(json.dumps(dict(state='BACKGROUND_REQUESTED',pid=child.pid,output=str(args.output))))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
