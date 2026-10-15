from types import SimpleNamespace
import copy
import json
import math
import pytest
import normal_cpu_gpu_diagnostic as d


def test_cpu_host_denominator_excludes_guest_double_count():
    a=SimpleNamespace(user=0,nice=0,system=0,idle=0,iowait=0,irq=0,softirq=0,steal=0,guest=0)
    b=SimpleNamespace(user=20,nice=0,system=10,idle=65,iowait=5,irq=0,softirq=0,steal=0,guest=8)
    assert d.cpu_busy(a,b)==30


def test_no_elapsed_cpu_time_is_missing_not_zero():
    a=SimpleNamespace(user=1,idle=9)
    assert d.cpu_busy(a,a) is None


def test_distribution_missing_and_nearest_rank():
    assert d.distribution([None,float('nan')])['mean'] is None
    assert d.distribution(range(1,21))==dict(n=20,mean=10.5,p95=19,max=20)


def test_cpu_single_busy_logical_processor_on_twenty():
    idle=SimpleNamespace(user=0,idle=0)
    busy=SimpleNamespace(user=1,idle=0)
    free=SimpleNamespace(user=0,idle=1)
    metrics=[d.cpu_busy(idle,busy)]+[d.cpu_busy(idle,free)]*19
    assert sum(metrics)/20==5


def test_timed_process_iter_brackets_existing_next_not_loop_body(monkeypatch):
    events = []
    def monotonic():
        events.append("clock")
        return float(len(events))
    def processes(attrs):
        assert attrs == ['pid', 'name', 'create_time', 'cpu_times']
        for pid in (42, 43):
            events.append(f"read{pid}")
            yield SimpleNamespace(info=dict(pid=pid))
    monkeypatch.setattr(d.time, "monotonic", monotonic)
    monkeypatch.setattr(d.psutil, "process_iter", processes)
    values = list(d.timed_process_iter())
    assert [(p.info['pid'], first, last) for p, first, last in values] == [(42, 1., 3.), (43, 4., 6.)]
    assert events == ["clock", "read42", "clock", "clock", "read43", "clock", "clock"]


def test_sample_additive_raw_counters_leave_legacy_arithmetic_unchanged(monkeypatch, tmp_path):
    group_path = "/sys/fs/cgroup/experiment"
    class Group:
        def __str__(self):
            return group_path
        def rglob(self, pattern):
            assert pattern == "cgroup.procs"
            return [SimpleNamespace(parent=SimpleNamespace(name="algorithm"), read_text=lambda: "42 43")]
    def fake_path(path):
        assert path == "/sys/fs/cgroup"
        return SimpleNamespace(glob=lambda pattern: [Group()])
    monkeypatch.setattr(d, "Path", fake_path)
    monkeypatch.setattr(d.os, "getpid", lambda: 99)
    times = iter([10., 10.01, 10.02, 10.03, 10.04, 10.05, 10.06, 10.07, 10.08, 10.09,
                  11., 11.01, 11.02, 11.03, 11.04, 11.05, 11.06, 11.07, 11.08, 11.09])
    monkeypatch.setattr(d.time, "monotonic", lambda: next(times))
    monkeypatch.setattr(d.time, "time", lambda: 1000.)
    monkeypatch.setattr(d.psutil, "virtual_memory", lambda: SimpleNamespace(available=123 * 2**20))
    cpu_reads = iter([SimpleNamespace(user=10., idle=90.), SimpleNamespace(user=20., idle=180.)])
    monkeypatch.setattr(d.psutil, "cpu_times", lambda percpu: [next(cpu_reads)])
    group_reads = []
    counters = iter([2000000, 2300000])
    def read_group(path):
        group_reads.append(path)
        return next(counters)
    monkeypatch.setattr(d.search.campaign, "read_cpu_usage_usec", read_group)
    def process(pid, created, user, system):
        return SimpleNamespace(info=dict(pid=pid, name=f"p{pid}", create_time=created,
                                        cpu_times=SimpleNamespace(user=user, system=system)), threads=lambda: [])
    snapshots = iter([[process(42, 100., 1.25, .25), process(43, 101., .1, 0.), process(99, 99., .2, 0.)],
                      [process(42, 100., 1.45, .25), process(43, 101., .2, 0.), process(99, 99., .3, 0.)]])
    calls = []
    def process_iter(attrs):
        calls.append(attrs)
        return iter(next(snapshots))
    monkeypatch.setattr(d.psutil, "process_iter", process_iter)
    profiler = d.Profiler.__new__(d.Profiler)
    profiler.output = tmp_path / "telemetry.jsonl"
    profiler.gpu = SimpleNamespace(sample=lambda: dict(gpu_device_util_pct=0, gpu_memory_mib=10., gpu_power_w=1.))
    profiler.phase, profiler.mode, profiler.rows = "flight", "full", []
    profiler.previous_processes = {(42, 100.): 1., (99, 99.): .1}
    profiler.previous_threads = {}
    profiler.previous_groups = {group_path: 1000000}
    profiler.previous_time = 9.
    profiler.previous_cpus = [SimpleNamespace(user=0., idle=0.)]
    profiler.sample()
    profiler.sample()
    first, second = profiler.rows
    assert len(calls) == 2 and group_reads == [group_path, group_path]  # no extra CPU reads
    assert [r['interval_s'] for r in profiler.rows] == [1., 1.]
    assert [r['host_cpu_pct'] for r in profiler.rows] == [10., 10.]
    assert first['experiment_proc_sum_cores'] == .5
    assert second['experiment_proc_sum_cores'] == pytest.approx(.3)
    assert [r['cgroup_interval_cores'] for r in profiler.rows] == [1., .3]
    assert [r['observer_process_cpu_pct'] for r in profiler.rows] == pytest.approx([10., 10.])
    assert [p['pid'] for p in first['experiment_processes']] == [42]
    assert [p['pid'] for p in first['experiment_process_cumulative']] == [42, 43]
    assert first['raw_cpu_counters_version'] == 1
    assert first['cgroup_cpu_cumulative'] == [dict(path=group_path, usage_usec=2000000,
        read_monotonic_start_s=10.01, read_monotonic_end_s=10.02)]
    item = first['experiment_process_cumulative'][0]
    assert item == dict(pid=42, name="p42", scope="algorithm", create_time=100.,
                       cpu_user_s=1.25, cpu_system_s=.25, cpu_total_s=1.5,
                       read_monotonic_start_s=10.03, read_monotonic_end_s=10.04)
    assert profiler.previous_processes[(42, 100.)] == 1.7
    assert profiler.previous_groups[group_path] == 2300000
    assert [json.loads(line) for line in profiler.output.read_text().splitlines()] == profiler.rows


def test_summary_additive_fields_do_not_change_existing_output(monkeypatch, tmp_path):
    perf = tmp_path / "perf.csv"
    perf.write_text("Total,Raycast,Update_cache,Inflation\n0.004,0.003,0.002,0.001\n")
    base = dict(mode='full', campaign_active=True, phase='flight', host_cpu_pct=12.,
                gpu_device_util_pct=1., gpu_memory_mib=10., gpu_power_w=2.,
                observer_process_cpu_pct=.1, cgroup_interval_cores=.5,
                experiment_proc_sum_cores=.4, experiment_threads=[],
                experiment_processes=[dict(pid=42, name="sim", cpu_pct_one_core=40.)])
    extended = copy.deepcopy(base)
    extended.update(raw_cpu_counters_version=1, cgroup_cpu_cumulative=[], experiment_process_cumulative=[])
    extended['experiment_processes'][0].update(create_time=100., cpu_user_s=1., cpu_system_s=0.,
        cpu_total_s=1., read_monotonic_start_s=10.01, read_monotonic_end_s=10.02)
    row = dict(mode='full', end_to_end_cpu_cores_mean=.5, perf_trace_csv=str(perf),
               perf_row_start=0, perf_row_end=1)
    monkeypatch.setattr(d.os, "cpu_count", lambda: 20)
    assert d.summarize(SimpleNamespace(rows=[base]), row) == d.summarize(SimpleNamespace(rows=[extended]), row)
