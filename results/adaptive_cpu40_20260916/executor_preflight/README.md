# Common executor/static-map polling preflight — 2026-09-16

Artifact-only proposals; no runtime, launch, runner, QoS, LiDAR data or safety
policy change has been made by this preflight work.

### Later authorized integration status

After C5 finished, root authorized C6 implementation. The runtime helper is now
`perfect_drone_sim/include/perfect_drone_sim/common_execution_policy.hpp`.
`SUPER_STATIC_PC_POLL_MS` accepts only `1` (also unset default) or `100`;
`SUPER_SIDE_EXECUTOR_THREADS` defaults to 10 and validates decimal integers
4–16. C6 will opt into static100 only, keeping 10 executor threads; executor4 is
separate. Effective settings have explicit runtime log records. Original static
publication code remains the default branch; no QoS/geometry/source change.

The standalone runtime C++ test compiled and passed with:

```bash
c++ -std=c++17 -O2 -Wall -Wextra -Werror \
  -I /root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/include \
  /root/super_ws/src/SUPER/mars_uav_sim/perfect_drone_sim/test/common_execution_policy_test.cpp \
  -o results/adaptive_cpu40_20260916/executor_preflight/common_execution_policy_test
```

`common_execution_policy_test.log` records PASS. A simulator-only ROS test is
prepared as `perfect_drone_sim/test/static_pc_late_subscriber_test.py`, but must
wait for the rebuilt installed binary and an authorized GPU window. It launches
no FSM/commands and checks complete identical static geometry at late consumer
transitions. Unit policy retries apply when the caller remains alive and a
publication is not acknowledged; they do not guarantee DDS delivery or recover
from an uncaught simulator exception.

## Existing evidence and its limits

`analyze_timing.py` reads finished campaign logs/monitor JSON and produces
`c01_c02_c03_timing.json`. It first uses the strict source/recovery auditor.
Log line order is not timing order; ROS timestamps use Decimal nanoseconds.

| Existing artifact | What it measures | What it cannot establish |
|---|---|---|
| SENSOR_ACQUISITION_FRAME stamp_ns | Actual source acquisition-stamp intervals, exact recovery source identity | Command/odom callback jitter |
| EVENT_RECOVERY_FULL / MAP_ACK / PATH_READY / SECTOR + FSM ACK | Matched-cycle log latency, source→processed ACK→new certified path→closure | Exact map commit instant, DDS ACK delivery latency, executor queue time |
| THREAD_CPU_PROFILE cumulative stage call count + steady_ns | Approximate completed callback rate over ~5 s report windows | Timer start lateness, individual interval tails, actual published command rate |
| native_loop_monitor `samples` / rounded mission time | Approximate whole-mission odometry receive rate | Odom timestamp/receive interval distribution or missed burst patterns |
| telemetry.jsonl / performance.csv | ~1 s CPU accounting / per-map update cost | 100 Hz command/odom scheduling |

Command callbacks contain safety-related early returns: callback count must
**not** be called command publication rate. Existing monitor command records
only the latest state/max speed, without cumulative count or sample stamps.
No retrospective command/odom interval distribution can be reconstructed.

All six C1–C3 logs pass the strict audit. Source intervals average approximately
100 ms. Mission-wide observed odom count/time is 99.98–100.00/s. Command callback
count report-window averages are approximately 100/s; individual intervals are
unknown. Adaptive recovery processed FSM ACK→path maxima: C1 2028.83 ms,
C2 525.25 ms, C3 1044.62 ms. These include planning and gates, not just scheduling.
These profiled n=1 runs are descriptive baselines, not latency guarantees.

## Measuring an executor change fairly

Both composed node files currently construct a side MultiThreadedExecutor with
10 threads. The main-thread renderer, map worker and adaptive frontend worker
remain separate. The side pool still handles main FSM, commands, odometry,
replanning, ACK and other callbacks. Four threads may reduce wakeup/lock cost,
but could also increase command/ACK queueing; residual CPU is not proof of cause.

Use one common bounded opt-in parameter, default 10, setting 4 in both matched
Full/Adaptive runs; preserve callback groups and all independent workers. Do not
combine this initially with a different planner policy. Keep strict recovery,
contact, completion, speed and map freshness checks. Report cumulative CPU and
mean CPU separately, and obtain unprofiled confirmation after exploration.

For actual message intervals, the least intrusive extra observer is an opt-in
extension to the **already subscribed** native_loop_monitor callbacks: record
each command/odom header stamp and local monotonic receipt time in bounded
arrays/histograms; emit once after the mission. Preserve the existing QoS and
do not add a second ROS subscription. Include message counts, stamp and receipt
interval min/p50/p95/p99/max, repeated/backward stamps and dropped-buffer count.
Compare identical instrumentation in both modes. Receive jitter includes
observer scheduling and DDS; it is not producer callback jitter. In particular,
intentional certified-hold command suppression must not be labeled timer loss.

To isolate producer timer lateness, add an opt-in bounded in-process counter at
command/odom/FSM callback entry with steady-clock timestamps, and publish-entry
counters after guards. This is a separate instrumented validation run; no
per-tick logging. Fixed expected periods alone do not prove actual schedule.

## Separate candidate: static /global_pc polling

`ros2_perfect_drone_model.hpp:499` schedules publishGlobalPC every 1 ms.
The callback (`:1122`) queries subscriber count and ROS time each tick. It
publishes complete global geometry on every nonzero count change, or repeatedly
while 5.0 < elapsed < 5.1 s. This includes count decreases such as 2→1. The
publisher has best-effort, volatile QoS. It is separate from acquired scans and
direct map input; no /global_pc reference was found in planner/map/mission source.

Propose a separate opt-in actual **100 ms timer**, not a 1 ms callback that merely
returns early. Retain complete static geometry and existing QoS. Per-instance
policy publishes on every observed nonzero subscriber-count change and performs
one unconditional bootstrap publication at the first tick with elapsed >=5 s.
The >= check avoids missing bootstrap if scheduling jumps across the old narrow
window. Coalesce simultaneous reasons. Mark completion only after publishing;
retry on a failed publication attempt. Existing behavior remains default.

`static_pc_policy_prototype.py` models only these decisions. Its ten tests cover
early/late consumers, count changes including decreases, reconnect after zero,
one-shot bootstrap, missed bootstrap window, coalescing, retry and independent
instances. This is not a ROS publication test or a performance measurement.

Deliberate behavior differences: subscriber discovery can be delayed by one
100 ms polling period **plus scheduling jitter**; the redundant ~100 ms startup
burst is removed. A subscriber that connects/disconnects entirely between polls
can be missed. Equal-count replacement between polls is not detected by either
count-only design. Best-effort/volatile publication does not guarantee delivery;
do not silently claim a one-shot message is reliable or change QoS in this patch.
If guaranteed late-reader delivery is required, bounded retry or a separately
reviewed transient-local design is needed. It is outside the planner safety path.

Future ROS integration validation: retain bootstrap with zero listeners; attach
a persistent RViz/global-PC subscriber after 5 s and verify complete geometry;
exercise 0→1→2→1→0→1 counts; verify source acquisition cadence/data unchanged;
check shutdown cleanup and both mode effective settings. First measure static
polling alone, then executor4 alone or clearly label a combined candidate.

## Commands

```bash
python3 results/adaptive_cpu40_20260916/executor_preflight/analyze_timing.py \
  results/adaptive_cpu40_20260916/c01_composed_profile \
  results/adaptive_cpu40_20260916/c02_common_overhead_profile \
  results/adaptive_cpu40_20260916/c03_fast_box_profile
python3 -m unittest discover \
  -s results/adaptive_cpu40_20260916/executor_preflight \
  -p 'test_static_pc_policy_prototype.py' -v
```
