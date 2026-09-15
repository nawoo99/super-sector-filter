#!/usr/bin/env python3
"""Separate source-FoV seed1 F/S/A smoke. Retain every outcome; no auto retry."""
import argparse
import csv
import fcntl
import json
import os
from pathlib import Path
import re
import time

import psutil
import event_recovery_seed1_smoke as previous
import normal_cpu_gpu_diagnostic as diagnostic
from analyze_cylinder_only_stress_full_gate import quality_valid

BACKUP = 'results/sensor_acquisition_v2_backup_20260916_fsDc9a/runtime_before.tar.gz'


def audit_source(folder, run, mode):
    log = (folder/f'seed1_run{run}_{mode}.attempt1.stack.log').read_text(errors='replace')
    pattern = (r'\[SENSOR_ACQUISITION_FRAME\] frame=(\d+) cycle=(\d+) full=(\d+) '
               r'stamp_ns=(\d+) width=(\d+) height=(\d+) readback_pixels=(\d+) '
               r'conversion_rays=(\d+) generated_points=(\d+) bytes=(\d+) half_angle_deg=([\d.]+)')
    fields = ('frame','cycle','full','stamp_ns','width','height','readback_pixels',
              'conversion_rays','generated_points','bytes','half_angle_deg')
    frames = [dict(zip(fields, [*map(int,m[:-1]),float(m[-1])])) for m in re.findall(pattern,log)]
    if mode == 'full':
        return dict(checks={
            'full_source_always_360': bool(frames) and all(f['full'] and f['width']==900 for f in frames),
            'full_readback_size': all(f['readback_pixels']==2*900*f['height'] for f in frames),
            'full_ray_count': all(f['conversion_rays']==128*900 for f in frames),
        }, frames=frames)
    stats = json.loads((folder/f'seed1_run{run}_{mode}.attempt1.filt_stats.json').read_text())
    checks = {
        'source_mode_enabled': stats.get('sensor_acquisition_enabled') is True,
        'source_frames_observed': bool(frames),
        'initially_sector': bool(frames) and frames[0]['full'] == 0,
        'near_field_exception_disabled': stats.get('near_field_radius_m') == 0,
        'quarter_width_before_cloud': all(f['width'] == (900 if f['full'] else 225) for f in frames),
        'actual_depth_readback_narrowed': all(f['readback_pixels'] == 2*f['width']*f['height'] for f in frames),
        'only_acquired_rays_converted': all(f['conversion_rays'] == 128*f['width'] for f in frames),
        'source_cloud_byte_counts': all(f['bytes'] == 32*f['generated_points'] for f in frames),
        'fixed_sector_never_full': mode != 'sector' or all(not f['full'] for f in frames),
    }
    if mode == 'adaptive':
        event = previous.audit_recovery(folder,run)
        checks.update(event['checks'])
        full_stamps = {f['stamp_ns']:f for f in frames if f['full']}
        checks['every_recovery_ack_from_generated_full'] = all(
            c['stamp_ns'] in full_stamps for c in event['certificates'])
    else:
        event = None
    return dict(checks=checks, frames=frames, frontend_stats=stats, event_recovery=event)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--run',type=int,default=9201)
    args=parser.parse_args()
    root=args.output;root.mkdir(parents=True,exist_ok=False)
    campaign=diagnostic.search.campaign
    lock=open(campaign.LOCK_PATH,'a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    for p in psutil.process_iter(['cmdline']):
        cmd=p.info['cmdline'] or []
        if cmd and Path(cmd[0]).name in ('fsm_node','perfect_drone_node','perfect_drone_full_node','perfect_drone_frontend_node','source_acquisition_test'):
            raise RuntimeError('Concurrent renderer/flight forbidden')
    if previous.sha(previous.NORMAL)!=previous.NORMAL_SHA:
        raise RuntimeError('Frozen Normal data changed')
    runtime=Path('/root/super_ws/src/SUPER')
    assets=[runtime/'super_planner/config'/previous.PROFILE,
            runtime/'mission_planner/Apps/native_sector_cpp.cpp',
            runtime/'mission_planner/include/mission_planner/sensor_acquisition.hpp',
            runtime/'mars_uav_sim/marsim_render/include/marsim_render/marsim_render.hpp',
            runtime/'mars_uav_sim/marsim_render/src/marsim_render.cpp',
            runtime/'mars_uav_sim/marsim_render/config/pattern/360camera.vs',
            runtime/'mars_uav_sim/marsim_render/config/pattern/camera.fs',
            runtime/'mars_uav_sim/marsim_render/include/marsim_render/config.hpp',
            runtime/'mars_uav_sim/perfect_drone_sim/config/seed1.yaml',
            runtime/'mars_uav_sim/perfect_drone_sim/pcd/seed_maps/seed1.pcd',
            runtime/'mission_planner/data/loop24.txt',
            Path('/root/super_ws/install/marsim_render/lib/libmarsim_render.so'),
            Path('/root/super_ws/install/mission_planner/lib/libnative_sector_cpp_component.so'),
            Path(__file__).resolve(),Path(previous.__file__),Path(diagnostic.__file__)]
    policy=diagnostic.search.frozen_policy()
    hashes={str(p):previous.sha(p) for p in assets}
    diagnostic.RUN=args.run
    profiler=diagnostic.Profiler(root/'telemetry.jsonl')
    diagnostic.save(root/'plan.json',dict(schema='sensor-acquisition-v2-seed1-n1',
        map='seed1',run=args.run,modes=diagnostic.MODES,backup=BACKUP,
        logical_cpus=os.cpu_count(),runtime_policy=policy,asset_sha256=hashes,
        no_near_field_exception=True,raw_sensor_unchanged=False,
        scope='simulated steerable sensor azimuth; Sector225 vs Full900 columns at0.4deg,10Hz; raw Full cloud never built during Sector',
        no_physical_sensor_claim=True,baseline_seconds=12,not_pooled_with_previous_results=True))
    campaign.install_campaign_signal_handlers();profiler.thread.start()
    results=[]
    try:
        with (root/'raw.csv').open('x',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=campaign.FIELDS,extrasaction='ignore')
            writer.writeheader();stream.flush()
            for mode in diagnostic.MODES:
                profiler.mode=mode;profiler.phase='baseline'
                diagnostic.save(root/'status.json',dict(pid=os.getpid(),state='RUNNING',mode=mode,phase='baseline'))
                time.sleep(12)
                options=dict(diagnostic.search.OPTIONS)
                options.update(sensor_acquisition=True,adaptive_event_recovery=mode=='adaptive')
                profile=previous.PROFILE if mode=='adaptive' else diagnostic.search.PROFILES[mode]
                profiler.phase='flight'
                diagnostic.save(root/'status.json',dict(pid=os.getpid(),state='RUNNING',mode=mode,phase='flight'))
                row=campaign.run_one('seed1',mode,args.run,**options,
                    artifacts_dir=str(root/'artifacts'),seedmap_super_config_override=profile)
                writer.writerow(row);stream.flush()
                if not quality_valid(row):raise RuntimeError('Quality-invalid result retained; stop, no automatic retry')
                if profiler.error:raise RuntimeError(profiler.error)
                if diagnostic.search.frozen_policy()!=policy or any(previous.sha(p)!=h for p,h in hashes.items()):
                    raise RuntimeError('Runtime changed during smoke')
                result=diagnostic.summarize(profiler,row)
                result['source_acquisition']=audit_source(root/'artifacts',args.run,mode)
                diagnostic.save(root/f'{mode}_summary.json',result)
                if not all(result['source_acquisition']['checks'].values()):
                    raise RuntimeError('Source acquisition contract failed; evidence preserved')
                results.append(result)
                print('RESULT',json.dumps({k:result[k] for k in ('mode','success','safety_collisions','mission_time_s','experiment_host_capacity_pct','end_to_end_cpu_core_s')}),flush=True)
        if previous.sha(previous.NORMAL)!=previous.NORMAL_SHA:raise RuntimeError('Legacy Normal changed')
        diagnostic.save(root/'summary.json',dict(results=results,diagnostic_only=True))
        diagnostic.save(root/'status.json',dict(pid=os.getpid(),state='COMPLETE',completed=len(results)))
    except BaseException as e:
        diagnostic.save(root/'status.json',dict(pid=os.getpid(),state='STOPPED_FOR_DIAGNOSIS',error=repr(e)))
        raise
    finally:
        profiler.close();campaign.cleanup_active_process_groups()


if __name__=='__main__':main()
