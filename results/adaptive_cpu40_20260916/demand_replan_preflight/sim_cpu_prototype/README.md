# Composed simulator thread-CPU instrumentation proposal

Status: staged outside runtime during C11 flight freeze. Not applied, compiled,
or flown. `git apply --check sim_cpu_runtime_proposal.patch` passes against the
current runtime. Root approval is required before applying with `apply_patch`.

## Measurement scope

Append stage IDs 27/28/29; historical IDs 0..26 stay unchanged. Measure the
calling thread's CPU with the existing opt-in `SUPER_CPU_PROFILE=1`, never wall
time. Registry Count changes from 27 to 30, so rebuild all consumers together:
rog_map, then super_planner, then perfect_drone_sim. Mixing the old/new inline
Registry definition between shared-library and executable objects is invalid.

| New stage | Actual callback / dispatch | Included work |
| --- | --- | --- |
| sim_static_cloud_callback | publishGlobalPC; current legacy 1 ms poll; optional dedicated SingleThreadedExecutor | count_subscribers, early returns, and actual PCD conversion/publication when applicable |
| sim_odom_callback | publishOdom; 10 ms timer on side executor | odometry, pose, TF, mesh and lower-rate growing path publication |
| sim_render_callback | publishPC; sensing timer, currently 10 Hz, main/render SingleThreadedExecutor | render driver CPU, cloud conversion, telemetry, acquisition observer and direct map/frontend handoff |

Render CPU excludes GPU device execution and blocked waiting; this is not a GPU
cost estimate or rendering wall-time metric. Nested same-thread map enqueue is
subtracted from exclusive render CPU. Sum exclusive stage totals only. Initial
constructor/setup, command callback, middleware workers, executor scheduling and
other uninstrumented paths may still contribute residual CPU.

Markers `[THREAD_CPU_ROLE] version=1 pid=... tid=... role=...` are emitted only
when profiling is enabled and on Linux with a valid actual gettid result. The
static marker runs inside the dedicated static thread lambda; it is absent when
that thread does not exist. The render marker runs in the actual thread calling
render_executor.spin(). No inferred side-pool worker identities are reported.
Role markers do not imply all CPU of a shared pool belongs to one callback.

## Dependency / behavioral containment

The common simulator header also builds standalone/frontend targets which do
not inherit rog_map includes. A dedicated target compile definition
SUPER_SIM_CPU_PROFILE_SUPPORT enables the new include/scopes only for composed
Full and Adaptive, which already link super_planner/rog_map. No additional
standalone dependencies, callback periods, QoS, acquisition policy, publications
or flight decisions change. Both compared modes use the identical instrumentation.
Default-off scopes read no clocks/counters; startup markers are silent when off.

## Tests after freeze ends

The staged profiler test adds compile-time old/new stage-ID assertions, runtime
new-stage count/leaf accounting, and exact new name checks. Existing disabled,
nested, sleep-exclusion, and 4,000-call multithread tests remain. Run the test in
separate unset/enabled processes because opt-in is cached on first use:

```sh
g++ -std=c++17 -O2 -Wall -Wextra -pedantic -pthread -Irog_map/include rog_map/test/thread_cpu_profile_test.cpp -o /tmp/sim_cpu_profile_test
env -u SUPER_CPU_PROFILE /tmp/sim_cpu_profile_test
env SUPER_CPU_PROFILE=1 /tmp/sim_cpu_profile_test
```

Repeat with AddressSanitizer/UndefinedBehaviorSanitizer before the full rebuild.
Check disabled output has no THREAD_CPU markers. Check enabled role pid/tid are
positive, and the main-thread test marker has tid == pid. After rebuild, actual
flight must show the three callback stages and, with dedicated static enabled,
two distinct valid role TIDs. No claim of actual ROS callback integration is made
by the standalone profiler test; the subsequent matched flight checks that.
