# Normal seed1 CPU / thread / GPU diagnostic (2026-09-16)

## Outcome

Three new flights completed: Full / Sector / Adaptive each 1/1 completion,
authoritative static-PCD contact0, valid speed and resource gates, first attempt,
no retries. These are additional-instrumentation diagnostics, NOT replacements
or additions to the saved Normal300 / reporting-tier n20 cohort.

The previous approximately7--8% figure is the **experiment process group's
share of20 logical CPUs**, not the observed busy percentage of the whole PC.
The independently observed whole-PC CPU was approximately20--22% during these
flights, including background software, the native flight monitor, and the
diagnostic controller/profiler. Baseline whole-PC CPU was approximately11%.
Background subtraction is not an exact workload-attribution method.

## Setup and boundaries

- Physical layout: `seed1.yaml` / `seed1.pcd`, one representative layout from
  Normal R1, not all five Normal tiers. Mission `loop24.txt`, v7, fixed half-angle
 45deg, deployed Full / reliable Sector / enforced Adaptive profiles unchanged.
- Native MARSIM perfect-tracking setup, no RViz added, no PX4/Gazebo dynamics or
  SLAM/VIO workload added. Existing CPU/GPU applications were not closed.
- Host reports20 online/available logical CPUs, process affinity0--19,
  root `cpu.max = max 100000`. GPU: RTX3050 Ti Laptop GPU.
- New run identifier9001 for each mode avoids replacing existing run files.
  Order Full→Sector→Adaptive, one run/mode,12 s no-flight baseline before each.
- Read-only profiler: nominal1 Hz `/proc`/psutil CPU counters, process/thread
  CPU time and NVML utilization/memory/power. GPU figures are **whole-device**;
  per-process GPU utilization is unavailable in this diagnostic.
- Primary experiment CPU remains the unchanged native parent cgroup containing
  simulator + frontend + planner + mission (+launch wrapper). CPU utilization
  is scheduled CPU time, not frequency-adjusted throughput or reserved capacity.
- The extra profiler shares the campaign controller process. Its recorded
  `observer_process_cpu_pct` includes the runner and profiler together, not the
  incremental cost of the new profiler in isolation. This was about0.32--0.33%
  of host CPU capacity during each flight and is outside experiment cgroup CPU.
- CPU/GPU/thread maxima below are sample-window maxima (~1 s), not instantaneous
  microburst maxima. Map times are per-update wall times from ROG `Total`, not
  sensor-to-command end-to-end latency or CPU time. Frontend times are separate.

## Measurements

Except the explicitly labelled thread row, CPU percentages use **all20 logical
CPUs =100%**. GPU percentages use the GPU's own utilization scale, not CPU scale.

| Metric | Full | Sector | Adaptive |
|---|---:|---:|---:|
| Completion / static-PCD contacts | 1/1 /0 | 1/1 /0 | 1/1 /0 |
| Mission time (s) | 59.12 | 62.55 | 59.88 |
| Pre-flight whole-PC CPU mean (%) | 10.89 | 11.21 | 10.61 |
| In-flight whole-PC CPU mean (%) | 21.81 | 19.83 | 20.69 |
| In-flight whole-PC CPU p95 (%) | 27.28 | 21.75 | 23.93 |
| In-flight whole-PC CPU sample max (%) | 27.85 | 26.11 | 25.36 |
| Experiment cgroup CPU / host capacity (%) | 8.03 | 6.77 | 7.13 |
| Experiment mean logical CPU equivalents | 1.606 | 1.355 | 1.426 |
| Experiment CPU time (core-s) | 99.51 | 88.19 | 89.78 |
| Pre-flight GPU-device utilization mean (%) | 45.82 | 49.92 | 49.92 |
| In-flight GPU-device utilization mean (%) | 46.69 | 49.31 | 49.52 |
| In-flight GPU-device utilization sample max (%) | 51 | 56 | 56 |
| Maximum thread utilization across all threads (% of ONE logical CPU) | 63.47 | 59.47 | 69.43 |
| Mean utilization of hottest-by-mean thread (% of ONE logical CPU) | 42.53 | 14.07 | 15.14 |
| ROG map Total mean (ms/update) | 36.98 | 10.32 | 22.37 |
| ROG map Total p95 (ms/update) | 51.40 | 16.41 | 49.83 |
| ROG map Total maximum (ms/update) | 87.19 | 25.90 | 64.92 |
| Frontend cloud compute mean (ms/frame) | not separate | 0.746 | 0.905 |
| Frontend risk-check compute mean (ms/check) | not enabled | not enabled | 2.799 |

Adaptive vs Full is11.22% lower experiment mean CPU and39.50% lower map Total
in this single diagnostic run. Do not replace the saved Normal300 estimates
(12.75% CPU /39.28% map Total) with these one-run numbers. Whole-PC CPU/GPU
differences cannot be used as causal mode reductions because background loads
and fixed sequential ordering are not controlled by this n1 diagnostic.

## Independent counter checks and integrity

| CPU calculation (logical CPU equivalents) | Full | Sector | Adaptive |
|---|---:|---:|---:|
| Native integrated cgroup mean | 1.60590 | 1.35473 | 1.42577 |
| Independent sampled process-time sum mean | 1.61422 | 1.36084 | 1.43128 |
| Relative process-vs-native difference (%) | +0.518 | +0.451 | +0.386 |

The secondary sampler's window is not exactly coextensive with the native
integrated window, and /proc process times are quantized. These small differences
do not indicate the large missing workload needed to turn8% into40--70%.
The observer saw the expected four Full processes and five filtered processes:
launch shell, ROS launch, waypoint mission, composed Full simulator/planner;
or composed simulator/frontend plus separate planner. Their threads were sampled.
The old Full `monitor_cpu_pct` field is missing in this new row; it is **not0**.
This is ancillary outside-cgroup monitor accounting, not missing experiment CPU;
whole-PC counters still include its CPU. No per-process identity is inferred from
the GPU-device percentage, and no GPU bottleneck has been demonstrated.

There are3 unique raw rows and61/64/62 in-flight host/GPU samples. All primary
CPU values and ROG mean times passed independent arithmetic checks. All279 frozen
source/config/binary/map/mission/helper hashes remained unchanged. Unit tests7/7,
plus a real NVML/host sampling smoke, passed before launch. Minimum available
memory during flights:5444.9 /5556.6 /5504.1 MiB; resource aborts0.

Implementation: `scripts/native_campaign/normal_cpu_gpu_diagnostic.py`.
Raw evidence: `results/normal_cpu_gpu_diagnostic_20260916/` contains `plan.json`,
`raw.csv`, `telemetry.jsonl`, mode summaries, `summary.json`, and native artifacts.
The three-flight process2531057 exited normally and status is `COMPLETE`.

Separate stress search was already stopped at23:10:48 KST on Sep15 due to
L0010 Adaptive run3 infrastructure memory pressure (MemAvailable1331.7 MiB
below2048 MiB). It was not resumed or modified during this CPU diagnostic.

## Interpretation

The measurement does not support “all of autonomous driving costs only7% CPU.”
It supports “this simulated planner/frontend stack used about1.4--1.6 logical
CPU equivalents on this host, or7--8% of its logical CPU-time capacity.” A real
SLAM/vehicle-control stack and GPU compute require their own accounting. Nor do
these sampled means/maxima prove absence of sub-second scheduling or deadline
bottlenecks. Existing algorithm, planner, map and sensor settings were not changed
to increase reported utilization.
