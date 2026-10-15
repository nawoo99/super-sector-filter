#!/usr/bin/env python3
"""Three-mode n3 diagnostic with a tiny read-only map-process ACK observer.

Flight policy and the solid observer are unchanged. Extra instrumentation means
these rows are diagnostic only, never pooled into standard n20 comparisons.
"""
import argparse
import csv
import json
import os
from pathlib import Path
import shlex
import signal
import time


def gap_metrics(epochs,start,end):
    if end <= start:
        return dict(samples=0,max_gap_s=None,hz=None)
    samples=sorted(t for t in epochs if start <= t <= end)
    edges=[start,*samples,end]
    return dict(samples=len(samples),max_gap_s=max(b-a for a,b in zip(edges,edges[1:])),
                hz=len(samples)/(end-start))


def observe(output,ready):
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import QoSProfile,ReliabilityPolicy
    from nav_msgs.msg import Odometry
    from std_msgs.msg import UInt64MultiArray
    if output.exists() or ready.exists(): raise RuntimeError("Observer evidence exists")
    rclpy.init(); node=Node('cylinder_map_ack_observer')
    stopped=False; first_odom=None; last_odom=None; samples=[]; malformed=0
    def stop(*_):
        nonlocal stopped
        stopped=True
    signal.signal(signal.SIGINT,stop); signal.signal(signal.SIGTERM,stop)
    def odom(msg):
        nonlocal first_odom,last_odom
        now=time.time(); last_odom=now
        if first_odom is None: first_odom=now
    def ack(msg):
        nonlocal malformed
        if len(msg.data)<4:
            malformed+=1; return
        samples.append(dict(receive_epoch_s=time.time(),scan_seq=int(msg.data[0]),
                            source_stamp_ns=int(msg.data[1]),map_version=int(msg.data[2]),
                            committed=bool(msg.data[3])))
    node.create_subscription(Odometry,'/lidar_slam/odom',odom,
        QoSProfile(depth=20,reliability=ReliabilityPolicy.BEST_EFFORT))
    node.create_subscription(UInt64MultiArray,'/rog_map/cloud_process_ack',ack,
        QoSProfile(depth=100,reliability=ReliabilityPolicy.RELIABLE))
    ready.write_text(json.dumps(dict(ready_epoch_s=time.time(),subscriptions_created=True))+"\n")
    started=time.time()
    try:
        while not stopped and rclpy.ok() and time.time()-started<300:
            rclpy.spin_once(node,timeout_sec=.05)
    finally:
        start=first_odom+10 if first_odom is not None else started+300
        end=last_odom if last_odom is not None else started
        metrics=gap_metrics([s['receive_epoch_s'] for s in samples],start,end)
        output.write_text(json.dumps(dict(schema='read-only-map-ack-diagnostic-v1',
            publishes_nothing=True,extra_observer_not_standard_n20=True,warmup_excluded_s=10.,
            first_odom_epoch_s=first_odom,last_odom_epoch_s=last_odom,
            malformed=malformed,total_ack_samples=len(samples),post_warmup=metrics,samples=samples),indent=2)+"\n")
        node.destroy_node()
        if rclpy.ok(): rclpy.shutdown()


def trial(name,mode,run,output):
    import cylinder_solid_campaign as solid
    campaign=solid.search.campaign
    stem=output/'ack'/f'{name}_run{run}_{mode}'
    stem.parent.mkdir(parents=True,exist_ok=True)
    report=stem.with_suffix('.json'); ready=stem.with_suffix('.ready.json')
    if report.exists() or ready.exists(): raise RuntimeError('Diagnostic trial exists')
    original=campaign.spawn_process_group; probe=None
    log=stem.with_suffix('.log').open('x')
    def spawn(*args,**kwargs):
        nonlocal probe
        command=' '.join(map(str,args[0])) if args else str(kwargs.get('args',''))
        if 'ros2 launch mission_planner benchmark_seedmap.launch.py' in command:
            if probe is not None: raise RuntimeError('Unexpected second simulator')
            cmd=(f'{campaign.ROS_ENV} && exec python3 {shlex.quote(str(Path(__file__).resolve()))}'
                 f' --observe --output {shlex.quote(str(report))} --ready {shlex.quote(str(ready))}')
            probe=original(['bash','-c',cmd],stdout=log,stderr=log)
            deadline=time.monotonic()+20
            while not ready.exists():
                if probe.poll() is not None or time.monotonic()>deadline:
                    raise RuntimeError('ACK observer startup failed')
                time.sleep(.05)
        return original(*args,**kwargs)
    campaign.spawn_process_group=spawn
    try:
        row=solid.run_trial(name,mode,run,output)
    finally:
        campaign.spawn_process_group=original
        campaign.terminate_group(probe,grace_s=3.)
        campaign.cleanup_active_process_groups(); log.close()
    return row,json.loads(report.read_text())


def run_campaign(name):
    import cylinder_solid_campaign as solid
    from confirm_cylinder_search_n20 import known_outcome
    from analyze_cylinder_only_stress_full_gate import quality_valid
    if not name.startswith('cyl2_') or not name.replace('_','').isalnum():
        raise ValueError('Use emitted map name')
    root=solid.search.ROOT/'results/cylinder_background_diagnostic_20260915'/name
    root.mkdir(parents=True,exist_ok=True)
    raw=root/'diagnostic_raw.csv'
    rows=list(csv.DictReader(raw.open())) if raw.exists() else []
    keys={(int(r['run']),r['mode']) for r in rows}
    if len(keys)!=len(rows): raise RuntimeError('Duplicate evidence')
    if any(not quality_valid(r) or not known_outcome(r) for r in rows):
        raise RuntimeError('Existing invalid evidence requires diagnosis')
    plan=dict(map=name,repetitions=3,modes=['full','sector','adaptive'],extra_ack_observer=True,
              comparison_rows=False,runtime_policy=solid.search.frozen_policy(),
              candidate_manifest_sha256=solid.search.geometry.sha256(solid.search.OUT/name/'manifest.json'),
              diagnostic_script_sha256=solid.search.geometry.sha256(Path(__file__)),
              stop_on_invalid_measurement=True,retain_all_reference_failures=True)
    freeze=root/'freeze.json'
    if freeze.exists() and json.loads(freeze.read_text())!=plan: raise RuntimeError('Diagnostic freeze changed')
    if not freeze.exists(): freeze.write_text(json.dumps(plan,indent=2)+"\n")
    state=dict(pid=os.getpid(),state='RUNNING',map=name,completed=len(rows),planned=9)
    def save_state():
        state['updated_epoch_s']=time.time()
        temporary=root/'status.json.tmp'
        temporary.write_text(json.dumps(state,indent=2)+"\n"); temporary.replace(root/'status.json')
    save_state(); solid.search.campaign.install_campaign_signal_handlers()
    try:
        with raw.open('a',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=solid.FIELDS,extrasaction='ignore',lineterminator='\n')
            if not rows: writer.writeheader(); stream.flush()
            for run in range(1,4):
                modes=['full','sector','adaptive']; offset=run-1
                for mode in modes[offset:]+modes[:offset]:
                    if (run,mode) in keys: continue
                    state.update(run=run,mode=mode);save_state()
                    row,ack=trial(name,mode,run,root)
                    writer.writerow(row);stream.flush();rows.append(row)
                    state.update(completed=len(rows),last=dict(mode=mode,run=run,success=row['success'],
                        solid_contacts=row['solid_collision_episodes'],mission_time_s=row['mission_time_s'],
                        map_ack=ack['post_warmup']))
                    save_state(); print('BACKGROUND_RESULT '+json.dumps(state['last']),flush=True)
                    if not quality_valid(row) or not known_outcome(row) or ack['malformed'] or ack['total_ack_samples']<10:
                        raise RuntimeError('Invalid measurement retained; stop for diagnosis')
        state['state']='DIAGNOSTIC_COMPLETE'
    except BaseException as error:
        state.update(state='STOPPED_FOR_DIAGNOSIS',error=str(error));raise
    finally:
        save_state(); solid.search.campaign.cleanup_active_process_groups()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map',nargs='?');parser.add_argument('--observe',action='store_true')
    parser.add_argument('--output',type=Path);parser.add_argument('--ready',type=Path)
    args=parser.parse_args()
    if args.observe:
        if args.output is None or args.ready is None: parser.error('Observer paths required')
        observe(args.output,args.ready)
    else:
        if not args.map: parser.error('Map name required')
        run_campaign(args.map)
