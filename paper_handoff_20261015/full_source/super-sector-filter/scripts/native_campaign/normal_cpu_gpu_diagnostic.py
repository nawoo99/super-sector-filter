#!/usr/bin/env python3
"""Read-only 1 Hz host/process/thread/GPU profiling around frozen seed1 flights.

Separate diagnostic cohort: never merge additional-observer runs into n20.
GPU utilization is device-wide, NOT attribution to the flight process.
"""
import csv
import ctypes as C
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import statistics as st
import subprocess
import threading
import time

import psutil
import cylinder_map_search as search
from analyze_cylinder_only_stress_full_gate import quality_valid

ROOT = search.ROOT / 'results/normal_cpu_gpu_diagnostic_20260916'
RUN = 9001
MODES = ('full', 'sector', 'adaptive')


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def distribution(values):
    vals = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    if not vals:
        return dict(n=0, mean=None, p95=None, max=None)
    return dict(n=len(vals), mean=st.mean(vals),
                p95=sorted(vals)[math.ceil(.95*len(vals))-1], max=max(vals))


def cpu_busy(before, after):
    # guest/guest_nice are already included in user/nice: do not double count.
    fields = ('user', 'nice', 'system', 'idle', 'iowait', 'irq', 'softirq', 'steal')
    delta = {k: max(0., getattr(after, k, 0.)-getattr(before, k, 0.)) for k in fields}
    total = sum(delta.values())
    if total <= 0:
        return None
    return 100*(total-delta['idle']-delta['iowait'])/total


def timed_process_iter():
    """Bracket the existing process_iter read, without a second CPU read.

    psutil fills proc.info while advancing this iterator. Timing inside the
    ordinary for-loop body would start too late to bracket that CPU read.
    """
    iterator = iter(psutil.process_iter(['pid', 'name', 'create_time', 'cpu_times']))
    while True:
        before = time.monotonic()
        try:
            proc = next(iterator)
        except StopIteration:
            return
        after = time.monotonic()
        yield proc, before, after


class GPU:
    class Util(C.Structure):
        _fields_ = [('gpu', C.c_uint), ('memory', C.c_uint)]

    class Memory(C.Structure):
        _fields_ = [('total', C.c_ulonglong), ('free', C.c_ulonglong), ('used', C.c_ulonglong)]

    def __init__(self):
        self.lib = C.CDLL('libnvidia-ml.so.1')
        self.check(self.lib.nvmlInit_v2())
        self.handle = C.c_void_p()
        self.check(self.lib.nvmlDeviceGetHandleByIndex_v2(C.c_uint(0), C.byref(self.handle)))
        name = C.create_string_buffer(128)
        self.check(self.lib.nvmlDeviceGetName(self.handle, name, C.c_uint(len(name))))
        self.name = name.value.decode()

    @staticmethod
    def check(code):
        if code:
            raise RuntimeError(f'NVML error {code}')

    def sample(self):
        util, mem, power = self.Util(), self.Memory(), C.c_uint()
        self.check(self.lib.nvmlDeviceGetUtilizationRates(self.handle, C.byref(util)))
        self.check(self.lib.nvmlDeviceGetMemoryInfo(self.handle, C.byref(mem)))
        code = self.lib.nvmlDeviceGetPowerUsage(self.handle, C.byref(power))
        return dict(gpu_device_util_pct=util.gpu, gpu_memory_util_pct=util.memory,
                    gpu_memory_mib=mem.used/2**20,
                    gpu_power_w=None if code else power.value/1000)


class Profiler:
    def __init__(self, output, map_name='seed1'):
        self.output = output
        self.map_name = map_name
        self.gpu = GPU()
        self.phase = 'baseline'
        self.mode = None
        self.rows = []
        self.previous_processes = {}
        self.previous_threads = {}
        self.previous_groups = {}
        self.previous_cpus = psutil.cpu_times(percpu=True)
        self.previous_time = time.monotonic()
        self.stop_event = threading.Event()
        self.error = None
        self.thread = threading.Thread(target=self.loop, name='read_only_profiler', daemon=True)

    def sample(self):
        now = time.monotonic()
        dt = now-self.previous_time
        cpus = psutil.cpu_times(percpu=True)
        if len(cpus) != len(self.previous_cpus):
            raise RuntimeError('Logical CPU topology changed during diagnostic')
        core_busy = [cpu_busy(a,b) for a,b in zip(self.previous_cpus, cpus)]
        groups = list(Path('/sys/fs/cgroup').glob(f'super_sector_filter_{os.getpid()}_{self.map_name}_run{RUN}_*'))
        members, counters = {}, {}
        group_cumulative = []
        for group in groups:
            try:
                read_before = time.monotonic()
                counters[str(group)] = search.campaign.read_cpu_usage_usec(str(group))
                read_after = time.monotonic()
                group_cumulative.append(dict(
                    path=str(group), usage_usec=counters[str(group)],
                    read_monotonic_start_s=read_before,
                    read_monotonic_end_s=read_after))
                for p in group.rglob('cgroup.procs'):
                    for text in p.read_text().split():
                        members[int(text)] = p.parent.name
            except FileNotFoundError:
                continue
        procs, threads = {}, {}
        process_values, thread_values, process_cumulative = [], [], []
        for proc, read_before, read_after in timed_process_iter():
            try:
                v = proc.info
                key = (v['pid'], v['create_time'])
                if v['cpu_times'] is None:
                    continue
                seconds = v['cpu_times'].user + v['cpu_times'].system
                previous = self.previous_processes.get(key)
                pct = None if previous is None else max(0., seconds-previous)/dt*100
                procs[key] = seconds
                item = dict(pid=v['pid'], name=v['name'], cpu_pct_one_core=pct,
                            scope=members.get(v['pid'], 'outside_experiment'),
                            create_time=v['create_time'],
                            cpu_user_s=v['cpu_times'].user,
                            cpu_system_s=v['cpu_times'].system,
                            cpu_total_s=seconds,
                            read_monotonic_start_s=read_before,
                            read_monotonic_end_s=read_after)
                if pct is not None:
                    process_values.append(item)
                if v['pid'] not in members:
                    continue
                # Include first observations even though the legacy percentage
                # list correctly omits them until a previous reading exists.
                process_cumulative.append({k: value for k, value in item.items()
                                           if k != 'cpu_pct_one_core'})
                for t in proc.threads():
                    tk = (v['pid'], v['create_time'], t.id)
                    seconds_t = t.user_time+t.system_time
                    old = self.previous_threads.get(tk)
                    threads[tk] = seconds_t
                    if old is None:
                        continue
                    comm = Path(f'/proc/{v["pid"]}/task/{t.id}/comm')
                    try:
                        name = comm.read_text().strip()
                    except FileNotFoundError:
                        name = ''
                    thread_values.append(dict(pid=v['pid'], tid=t.id, name=name,
                        process=v['name'], cpu_pct_one_core=max(0., seconds_t-old)/dt*100))
            except (psutil.NoSuchProcess, psutil.AccessDenied, ProcessLookupError):
                continue
        group_cores = 0.
        group_valid = False
        for path, counter in counters.items():
            old = self.previous_groups.get(path)
            if old is not None and counter is not None:
                group_cores += max(0, counter-old)/1e6/dt
                group_valid = True
        scope = [p for p in process_values if p['pid'] in members]
        row = dict(epoch_s=time.time(), monotonic_s=now, interval_s=dt,
            mode=self.mode, phase=self.phase, campaign_active=bool(members),
            host_cpu_pct=st.mean(core_busy), host_per_logical_cpu_pct=core_busy,
            cgroup_paths=list(counters), cgroup_interval_cores=group_cores if group_valid else None,
            experiment_processes=scope, experiment_threads=thread_values,
            raw_cpu_counters_version=1,
            cgroup_cpu_cumulative=group_cumulative,
            experiment_process_cumulative=process_cumulative,
            experiment_proc_sum_cores=sum(p['cpu_pct_one_core'] for p in scope)/100,
            visible_process_top10=sorted(process_values, key=lambda p:p['cpu_pct_one_core'], reverse=True)[:10],
            available_memory_mib=psutil.virtual_memory().available/2**20,
            observer_process_cpu_pct=next((p['cpu_pct_one_core'] for p in process_values if p['pid']==os.getpid()),None),
            **self.gpu.sample())
        self.rows.append(row)
        with self.output.open('a') as stream:
            stream.write(json.dumps(row)+'\n')
        self.previous_time, self.previous_cpus = now, cpus
        self.previous_processes, self.previous_threads, self.previous_groups = procs, threads, counters

    def loop(self):
        try:
            while not self.stop_event.wait(1.):
                self.sample()
        except BaseException as error:
            self.error = repr(error)

    def close(self):
        self.stop_event.set()
        self.thread.join(timeout=5)
        self.gpu.lib.nvmlShutdown()


def summarize(profiler, row):
    selected = [s for s in profiler.rows if s['mode']==row['mode'] and s['campaign_active']]
    baseline = [s for s in profiler.rows if s['mode']==row['mode'] and s['phase']=='baseline']
    out = {k:row.get(k) for k in ('map','mode','run','success','run_valid','resource_valid',
        'speed_limit_valid','safety_collisions','mission_time_s','end_to_end_cpu_cores_mean',
        'end_to_end_cpu_core_s','end_to_end_cpu_cores_p95_1s','end_to_end_cpu_cores_max_1s',
        'total_ms_mean','map_frames_s','filter_risk_compute_ms_mean','filter_cloud_compute_ms_mean')}
    out['experiment_host_capacity_pct'] = 100*row['end_to_end_cpu_cores_mean']/os.cpu_count()
    for key in ('host_cpu_pct','gpu_device_util_pct','gpu_memory_mib','gpu_power_w',
                'observer_process_cpu_pct','cgroup_interval_cores','experiment_proc_sum_cores'):
        out[key] = distribution(s[key] for s in selected)
    out['baseline_host_cpu_pct'] = distribution(s['host_cpu_pct'] for s in baseline)
    out['baseline_gpu_device_util_pct'] = distribution(s['gpu_device_util_pct'] for s in baseline)
    by_thread = {}
    for s in selected:
        for t in s['experiment_threads']:
            key = (t['pid'],t['tid'],t['name'],t['process'])
            by_thread.setdefault(key,[]).append(t['cpu_pct_one_core'])
    out['threads_sorted_by_mean'] = sorted(
        [dict(pid=k[0],tid=k[1],name=k[2],process=k[3],cpu_pct_one_core=distribution(v))
         for k,v in by_thread.items()], key=lambda t:t['cpu_pct_one_core']['mean'],reverse=True)
    per_process = {}
    for s in selected:
        for p in s['experiment_processes']:
            per_process.setdefault((p['pid'],p['name']),[]).append(p['cpu_pct_one_core'])
    out['processes'] = [dict(pid=k[0],name=k[1],cpu_pct_one_core=distribution(v)) for k,v in per_process.items()]
    with Path(row['perf_trace_csv']).open() as stream:
        table = list(csv.reader(stream))
    columns = [c.strip() for c in table[0]]
    data = [r for r in table[1:] if len(r)==len(columns) and r[0].strip()]
    data = data[row['perf_row_start']:row['perf_row_end']]
    for metric in ('Total','Raycast','Update_cache','Inflation'):
        out[f'map_{metric}_ms'] = distribution(float(r[columns.index(metric)])*1000 for r in data)
    out['gpu_scope'] = 'Whole GPU including background. Per-flight GPU attribution unavailable; baseline subtraction is not causal attribution.'
    out['diagnostic_only'] = True
    return out


def main():
    ROOT.mkdir(parents=True, exist_ok=False)
    campaign = search.campaign
    lock = open(campaign.LOCK_PATH, 'a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    for proc in psutil.process_iter(['name','cmdline']):
        args = proc.info['cmdline'] or []
        if args and Path(args[0]).name in ('fsm_node','perfect_drone_full_node','perfect_drone_frontend_node','perfect_drone_node'):
            raise RuntimeError('Existing flight: refuse concurrent diagnostic')
    policy = search.frozen_policy()
    paths = [search.geometry.SUPER_ROOT/'mars_uav_sim/perfect_drone_sim/config/seed1.yaml',
             search.geometry.SUPER_ROOT/'mars_uav_sim/perfect_drone_sim/pcd/seed_maps/seed1.pcd',
             search.geometry.SUPER_ROOT/'mission_planner/data/loop24.txt',Path(__file__).resolve()]
    hashes = {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    profiler = Profiler(ROOT/'telemetry.jsonl')
    save(ROOT/'plan.json',dict(schema='normal-read-only-cpu-gpu-diagnostic-v1',map='seed1',
        run=RUN,modes=MODES,extra_observer_hz=1,baseline_s_per_mode=12,
        logical_cpus=os.cpu_count(),affinity=list(os.sched_getaffinity(0)),
        cpu_max=Path('/sys/fs/cgroup/cpu.max').read_text().strip(),gpu=profiler.gpu.name,
        runtime_policy=policy,asset_sha256=hashes,no_runtime_changes=True,
        primary_cpu='native cgroup; host /proc and thread counters are independent cross-checks',
        gpu_scope='whole device, background included, per-process utilization unavailable',
        preserves_old_normal_results=True,additional_observer_not_part_of_old_n20=True))
    campaign.install_campaign_signal_handlers()
    profiler.thread.start()
    results=[]
    try:
        with (ROOT/'raw.csv').open('x',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=campaign.FIELDS,extrasaction='ignore')
            writer.writeheader();stream.flush()
            for mode in MODES:
                profiler.mode=mode;profiler.phase='baseline'
                save(ROOT/'status.json',dict(pid=os.getpid(),state='RUNNING',mode=mode,phase='baseline'))
                time.sleep(12)
                if profiler.error:raise RuntimeError(profiler.error)
                profiler.phase='flight'
                save(ROOT/'status.json',dict(pid=os.getpid(),state='RUNNING',mode=mode,phase='flight'))
                row=campaign.run_one('seed1',mode,RUN,**search.OPTIONS,
                    artifacts_dir=str(ROOT/'artifacts'),seedmap_super_config_override=search.PROFILES[mode])
                writer.writerow(row);stream.flush()
                if not quality_valid(row):
                    raise RuntimeError('Invalid trial retained; stop for infrastructure diagnosis')
                if profiler.error:raise RuntimeError(profiler.error)
                if search.frozen_policy()!=policy:raise RuntimeError('Runtime changed')
                if any(hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h for p,h in hashes.items()):
                    raise RuntimeError('Frozen asset changed')
                result=summarize(profiler,row);results.append(result)
                save(ROOT/f'{mode}_summary.json',result)
                print('DIAGNOSTIC_RESULT '+json.dumps({k:result[k] for k in ('mode','success','mission_time_s','experiment_host_capacity_pct','host_cpu_pct','gpu_device_util_pct')}),flush=True)
        save(ROOT/'summary.json',dict(results=results,diagnostic_only=True,not_merged_into_n20=True))
        save(ROOT/'status.json',dict(pid=os.getpid(),state='COMPLETE',completed=len(results)))
    except BaseException as error:
        save(ROOT/'status.json',dict(pid=os.getpid(),state='STOPPED_FOR_DIAGNOSIS',error=repr(error)))
        raise
    finally:
        profiler.close()
        campaign.cleanup_active_process_groups()


if __name__=='__main__':
    main()
