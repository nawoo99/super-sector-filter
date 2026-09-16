# C19 computational-metric scope audit (2026-09-16)

Read-only review of the frozen C19 implementation and existing run 9320. This
document does not add flights, alter runtime code, or certify the upcoming
validation result. Its purpose is to prevent apparently similar counters from
being interpreted as the same quantity.

## Primary comparison and measurement windows

- Use the experimental parent cgroup for comparable total CPU. It includes all
  assigned simulator, frontend, planner, mission, and launch processes/threads.
  The external monitor/profiler is outside this group. Host background CPU is
  separate; subtracting a baseline is not a substitute for cgroup accounting.
- Mean used cores = cgroup CPU seconds / `cgroup_cpu_duration_s`. Whole-machine
  capacity percentage = mean cores / 20 logical CPUs * 100 on this host. A
  relative reduction in this percentage is identical to that in mean cores.
- The CPU observation window starts before launching the mission observer and
  ends after it exits. It is slightly wider than the waypoint mission. Therefore
  `end_to_end_cpu_core_s` is measurement-window CPU, not an exactly clipped
  waypoint-flight CPU integral. Show both durations and never divide these CPU
  seconds by `mission_time_s` to recreate the existing mean.
- Run 9320 Full: mission 37.61 s, CPU window 39.375403 s. Adaptive: mission 39.00 s,
  CPU window 40.448236 s. These differences are present in the raw record.
- `algorithm_cpu_scope` is `simulator+planner` for composed Full and
  `simulator+frontend+planner` for composed Sector/Adaptive. Both include the
  simulator. This is not an independently measured autonomy-only process group.
  Do not label the raw `algorithm_*` columns as pure planner CPU or subtract a
  device-wide GPU counter to estimate autonomy CPU.
- `fsm_cpu_pct` uses one core = 100% and measures the composed process in this
  configuration, not just the FSM callback. It overlaps the cgroup total.
  Never sum it with the encompassing CPU scope.
- The cgroup p95/max fields are extrema of sampled intervals, nominally about
  one second, not instantaneous hardware maxima. The last interval can be shorter.

Implementation evidence: `native_campaign.py`, `CgroupRunMeter.start/sample/
summary`, meter startup before monitor launch, and the `algorithm_cpu_scope`
record. The independent observer is in `normal_cpu_gpu_diagnostic.py`.

## Point counts, data volume, and timing

- `sensor_hz` is the reported acquisition cadence. Sensor totals are the latest
  periodic report, not necessarily the complete flight: run 9320 Full records
  350 frames over 34.896868 s; Adaptive records 400 over 39.898022 s.
- ROG map CSV slicing begins before the mission observer and ends after it.
  Nevertheless historical `map_frames_s`, `map_points_s`, and `map_payload_mib_s`
  divide this sliced work by `mission_time_s`. Label them mission-normalized
  processing amounts, not exact sensor or worker frequencies. For example,
  Full's 393 / 37.61 = 10.44935 map frames/s does not contradict its actual
  10.000897 Hz sensor. A `/cgroup_duration` alternative is closer in window but
  also not an exactly clipped map window; do not silently replace the raw metric.
- For a clean per-operation comparison, present map points/frame, logical
  bytes/frame, and ms/frame with their sample counts. Preserve the total bytes
  and their observation-window description.
- Cloud byte counts are logical `PointCloud2.data` payloads, excluding transport
  framing and serialization overhead. They are not measured wire traffic.
- In the composed direct-sink configuration, cloud DDS payload is zero in all
  modes. This does not mean the entire application sends zero DDS traffic:
  control/status/odometry traffic is outside that cloud metric.
- `algorithm_delivery_payload_mib_s` adds frontend ingress and planner ingress.
  The same shared cloud may be counted at both boundaries. Do not call this
  unique sensor bandwidth, network bandwidth, or actual memory-copy bandwidth.
  Show each edge separately, especially map/planner ingress.
- `Total`, `Raycast`, `Update_cache`, and `Inflation` in the ROG CSV use elapsed
  wall timers. They are not CPU seconds. Raycast and update are inside Total;
  inflation is nested in cache updating. Never add all four as disjoint work.
- ROG Total stops before optional ESDF work and does not cover later snapshot
  commit, map ACK, the entire worker callback, or the planner. Thus it is not
  total autonomy latency even though the CSV header is named `Total`.
- `filter_*_compute_core_equivalent` is wall milliseconds times calls divided
  by mission time. Despite its name, it is a wall-time duty estimate, not a
  measured CPU-core consumption. Do not merge it into CPU accounting.

Implementation evidence: `native_campaign.py::slice_perf` and payload-rate
formulas; `rog_map/src/rog_map/prob_map.cpp::updateProbMap`; inflation calls in
`inf_map.cpp`; `super_utils/scope_timer.hpp::TimeConsuming`.

## Memory and GPU

- Parent-process RSS/PSS/swap sums are sampled approximately every 10 seconds
  plus start/end. Label their maxima sampled peaks, not guaranteed true peaks.
  PSS avoids much of the shared-page double counting in a summed RSS figure.
- Keep host minimum available RAM, host swap use, and memory-pressure readings
  as infrastructure diagnostics. They are not memory allocated by the planner.
- NVML GPU utilization, memory allocation, and power readings cover the entire
  GPU, including unrelated graphics/background work. Baseline readings should
  be displayed separately; baseline subtraction does not establish causal
  flight attribution. GPU memory-utilization percentage, if shown, refers to
  device activity and is not the same as allocated-VRAM percentage.
- These CPU and GPU counters do not measure total system energy or demonstrate
  performance on another CPU/GPU platform.

## Profile-only detail and aggregation

- Keep the new unprofiled repeated cohort as the primary performance comparison.
  Use a separately labeled profiled preflight for map, FSM, guard, planner,
  solver, and simulator stage CPU. Never pool profile-ON and profile-OFF runs.
- Stage scopes use `CLOCK_THREAD_CPUTIME_ID`. Inclusive stages include their
  nested same-thread scopes; only exclusive values may be added. Spawned
  worker CPU is not included merely because its parent stage waits for it.
- Profile summaries use first/last periodic report boundaries inside the
  observer window. They are not identical to the whole cgroup measurement
  window. Report the stage window and calls when showing per-call CPU.
- Stage counters are updated at scope completion and read independently while
  other threads run. Subtracting them from process CPU produces an accounting
  remainder, not an exact physical measurement of removable overhead.
- Unprofiled per-stage CPU must be unavailable, not reconstructed from prior
  profiling or wall times. Inactive/missing frontend fields are not observed
  zero CPU. Preserve that distinction in tables and machine-readable output.
- Repeated flights, not one-second samples, are the independent units for
  between-run dispersion. State whether reported reductions use ratios of
  per-run means, pooled CPU/pooled window, or paired-run reductions. Preserve
  every failure and do not mix incomplete-run cheap CPU with successful-run
  cost without clearly separated outcome strata.
- Seed1 was used for tuning. Its five repeats assess repeatability on seed1,
  not unseen-map generalization. Historical Normal/Stress flights use another
  version and must not be pooled with this frozen candidate.

Implementation evidence: `analyze_thread_cpu_profile.py`,
`analyze_cpu_window_alignment.py`, and
`rog_map/include/super_utils/thread_cpu_profile.hpp`.
