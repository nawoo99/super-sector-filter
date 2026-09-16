#!/usr/bin/env python3
"""Separate seed1 F/S/event-A n1; preserve all legacy observations and failures."""
import argparse
import csv
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import time

import psutil
import normal_cpu_gpu_diagnostic as diagnostic
from analyze_cylinder_only_stress_full_gate import quality_valid

PROFILE = 'static_seedmaps_guard_viability_tight_v7_event_recovery_v1.yaml'
NORMAL = Path('/root/share/here/90_raw_normal_300_rows.csv')
NORMAL_SHA = 'b40f880271a52f4b3332bfe67afe3d489cf8c6d444ac0c72ed30d9e9cd445ec5'
BACKUP = 'results/event_recovery_v1_backup_20260916_kblK04/runtime_before.tar.gz'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit_recovery(folder, run, map_name='seed1'):
    files = list(folder.glob(f'{map_name}_run{run}_adaptive*.filt_stats.json'))
    if len(files) != 1:
        raise RuntimeError(f'Expected one frontend statistics file, got {files}')
    stats = json.loads(files[0].read_text())
    stack = folder / f'{map_name}_run{run}_adaptive.attempt1.stack.log'
    text = stack.read_text(errors='replace')
    pattern = (r'\[EVENT_RECOVERY_PATH_READY\] request_seq=(\d+) stamp_ns=(\d+) '
               r'ack_map=(\d+) certified_map=(\d+) generation_before=(\d+) generation_after=(\d+)')
    certificates = [dict(zip(('request','stamp_ns','ack_map','certified_map','generation_before','generation_after'),
                            map(int,m))) for m in re.findall(pattern,text)]
    checks = {
        'event_mode_enabled': stats.get('event_recovery_enabled') is True,
        'raw_risk_worker_disabled': (stats.get('risk_verdict_messages', 0) == 0
                                     and not stats.get('risk_verdict_topic')),
        'no_pre_stale_full_refresh': stats.get('pre_stale_full_refresh_frames', 0) == 0,
        'no_timed_replan_open': stats.get('replan_guard_open_transitions', 0) == 0,
        'path_certificates_have_new_generation': all(c['generation_after'] > c['generation_before'] for c in certificates),
        'path_certificates_use_committed_map': all(c['ack_map'] > 0 and c['certified_map'] >= c['ack_map'] for c in certificates),
        'closures_have_path_certificates': stats.get('event_recovery_completed', 0) <= len(certificates),
    }
    return dict(checks=checks,certificates=certificates,frontend_stats=stats,
                exercised=stats.get('event_recovery_cycles',0)>0)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=diagnostic.search.ROOT/'results/event_recovery_seed1_n1_20260916')
    parser.add_argument('--run',type=int,default=9101)
    args=parser.parse_args()
    root=args.output
    root.mkdir(parents=True,exist_ok=False)
    campaign=diagnostic.search.campaign
    lock=open(campaign.LOCK_PATH,'a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    for proc in psutil.process_iter(['cmdline']):
        cmd=proc.info['cmdline'] or []
        if cmd and Path(cmd[0]).name in ('fsm_node','perfect_drone_node','perfect_drone_full_node','perfect_drone_frontend_node'):
            raise RuntimeError('Refuse concurrent flight')
    if sha(NORMAL)!=NORMAL_SHA:
        raise RuntimeError('Legacy Normal dataset hash changed')
    diagnostic.RUN=args.run
    profiler=diagnostic.Profiler(root/'telemetry.jsonl')
    runtime=Path('/root/super_ws/src/SUPER')
    assets=[runtime/'super_planner/config'/PROFILE,
            runtime/'mission_planner/Apps/native_sector_cpp.cpp',
            runtime/'mission_planner/include/mission_planner/event_recovery_latch.hpp',
            runtime/'super_planner/include/fsm/config.hpp',
            runtime/'super_planner/include/ros_interface/ros2/fsm_ros2.hpp',
            runtime/'mars_uav_sim/perfect_drone_sim/config/seed1.yaml',
            runtime/'mars_uav_sim/perfect_drone_sim/pcd/seed_maps/seed1.pcd',
            runtime/'mission_planner/data/loop24.txt',
            Path('/root/super_ws/install/mission_planner/lib/libnative_sector_cpp_component.so'),
            Path(__file__).resolve()]
    policy=diagnostic.search.frozen_policy()
    hashes={str(p):sha(p) for p in assets}
    diagnostic.save(root/'plan.json',dict(
        schema='event-recovery-v1-seed1-n1',map='seed1',run=args.run,
        modes=diagnostic.MODES,profile=PROFILE,legacy_backup=BACKUP,
        logical_cpus=os.cpu_count(),runtime_policy=policy,asset_sha256=hashes,
        legacy_normal_sha256=NORMAL_SHA,baseline_seconds=12,
        algorithm_change='event-only Adaptive; exact Full-commit and new safe path before closing',
        trigger_policy='initial no-path failure streak, persistent observed stall, or map-based safety stop; never routine optimizer failures after a successful plan',
        raw_sensor_unchanged=True,adaptive_follows_sensor_cadence=True,
        not_merged_into_existing_results=True))
    campaign.install_campaign_signal_handlers()
    profiler.thread.start()
    results=[]
    try:
        with (root/'raw.csv').open('x',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=campaign.FIELDS,extrasaction='ignore')
            writer.writeheader();stream.flush()
            for mode in diagnostic.MODES:
                profiler.mode=mode;profiler.phase='baseline'
                diagnostic.save(root/'status.json',dict(pid=os.getpid(),state='RUNNING',mode=mode,phase='baseline'))
                time.sleep(12)
                if profiler.error:raise RuntimeError(profiler.error)
                options=dict(diagnostic.search.OPTIONS)
                if mode=='adaptive':options['adaptive_event_recovery']=True
                profile=PROFILE if mode=='adaptive' else diagnostic.search.PROFILES[mode]
                profiler.phase='flight'
                diagnostic.save(root/'status.json',dict(pid=os.getpid(),state='RUNNING',mode=mode,phase='flight'))
                row=campaign.run_one('seed1',mode,args.run,**options,
                    artifacts_dir=str(root/'artifacts'),seedmap_super_config_override=profile)
                writer.writerow(row);stream.flush()
                if not quality_valid(row):raise RuntimeError('Infrastructure/quality-invalid result retained; no automatic retry')
                if profiler.error:raise RuntimeError(profiler.error)
                if diagnostic.search.frozen_policy()!=policy or any(sha(p)!=h for p,h in hashes.items()):
                    raise RuntimeError('Runtime changed during smoke')
                result=diagnostic.summarize(profiler,row)
                if mode=='adaptive':
                    result['event_recovery']=audit_recovery(root/'artifacts',args.run)
                    if not all(result['event_recovery']['checks'].values()):
                        diagnostic.save(root/'failed_event_audit.json',result)
                        raise RuntimeError('Event recovery invariant failed; preserve trial and diagnose')
                results.append(result)
                diagnostic.save(root/f'{mode}_summary.json',result)
                print('RESULT',json.dumps({k:result[k] for k in ('mode','success','safety_collisions','mission_time_s','experiment_host_capacity_pct','end_to_end_cpu_core_s')}),flush=True)
        if sha(NORMAL)!=NORMAL_SHA:raise RuntimeError('Legacy result changed')
        diagnostic.save(root/'summary.json',dict(results=results,diagnostic_only=True))
        diagnostic.save(root/'status.json',dict(pid=os.getpid(),state='COMPLETE',completed=len(results)))
    except BaseException as error:
        diagnostic.save(root/'status.json',dict(pid=os.getpid(),state='STOPPED_FOR_DIAGNOSIS',error=repr(error)))
        raise
    finally:
        profiler.close()
        campaign.cleanup_active_process_groups()


if __name__=='__main__':main()
