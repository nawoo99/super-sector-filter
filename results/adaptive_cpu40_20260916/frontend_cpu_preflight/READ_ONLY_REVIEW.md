# C12 Adaptive frontend CPU residual: bounded read-only audit

Date: 2026-09-16. No runtime edits, builds, parameter changes, or flights were performed for this audit. This is source/telemetry attribution, not an optimization result.

## Finding

The unexplained Adaptive CPU is concentrated in the two likely side-executor worker threads, not in the acquired-cloud frontend worker. The most plausible avoidable cost is extra callback dispatch/entity-management work from adding the frontend ROS node to the shared executor, plus unmeasured frontend odometry/ACK/status/statistics callbacks. The existing evidence does **not** identify any one of those as the proven cause.

There is no hidden full-cloud filtering, extra CIRI/risk evaluation, or busy-waiting cloud worker in the measured source/event-recovery path. Optimizing its already tiny cloud body cannot plausibly close the 40% target gap.

## Evidence and measurement boundaries

Inputs: `../c12_extended_lease_profile/telemetry.jsonl`, `thread_cpu_summary.json`, and `artifacts/seed1_run9313_adaptive.attempt1.filt_stats.json`.

For each mode, select telemetry intervals entirely within that mode's first/last CPU-profiler report timestamps, then integrate `cpu_pct_one_core / 100 * interval_s`. This yields 29 wholly enclosed intervals: Full 29.184889844 s; Adaptive 29.192175471 s. Profiler stages cover 30.039761376 s and approximately 30.03 s, respectively. Thus stage/thread subtractions below are **approximate**, not exact CPU conservation identities. `/proc` tick quantization also affects individual small threads.

| Thread role | Full TID(s) | Full mean cores | Adaptive TID(s) | Adaptive mean cores | Identity evidence |
|---|---:|---:|---:|---:|---|
| Render executor | 2935116 | 0.048998 | 2936017 | 0.023294 | Actual `THREAD_CPU_ROLE` marker |
| Static-cloud executor | 2935222 | 0.048313 | 2936092 | 0.049328 | Actual `THREAD_CPU_ROLE` marker |
| Side-executor pool, combined | 2935221, 2935223 | 0.165497 | 2936091, 2936093 | 0.202452 | Inferred from construction order, thread population, and CPU; needs explicit markers |
| Map worker | 2935172 | 0.286107 | 2936063 | 0.114414 | Inferred; closely matches map-exclusive scopes |
| Additional frontend cloud worker | absent | — | 2936084 | 0.000343 | Inferred; only 0.01 CPU-s in the sampled window |
| Small auxiliary thread | 2935148 | 0.001028 | 2936049 | 0.001028 | Identity unassigned |

Other observed threads in the composed processes accumulated zero **measured ticks** in these intervals; this is not a proof of exactly zero work.

The inferred pool rises by 0.036955 cores. Its measured non-map/non-render/non-static scopes rise only from 0.120261 to 0.123839 cores (+0.003578). Approximate pool residuals are therefore 0.045235 Full / 0.078613 Adaptive: +0.033377 cores, close to the previously observed +0.03476 whole-process unexplained difference. This narrows where to instrument, but does not prove that all of the difference is removable frontend overhead.

## What actually runs in the Adaptive frontend

Source: `/root/super_ws/src/SUPER/mission_planner/Apps/native_sector_cpp.cpp`.

| Work | Actual C12 behavior | Source location / constraint |
|---|---|---|
| Cloud subscription | Not created: `direct_input=true` | Constructor, around line 506 |
| Filtered-cloud publisher | Not created: direct sink supplied | Constructor, around line 564 |
| Angular crop/copy | None on acquired-source path; same `SharedPtr` forwarded | `publishFilteredCloud(SharedPtr)`, `processCloud`, around 2356–2449 |
| Cloud worker | One condition-variable waiter, latest-only queue; no polling | `cloudWorkerLoop`, around 2148 |
| Risk worker / trajectory subscription | Not created; risk topic empty | Constructor, around 569, 645 |
| Risk accumulation / body risk | Immediate return: no risk publisher | `enqueueRiskCloud`, `publishCurrentBodyRiskVerdict`, around 1603, 1969 |
| Static probe / witness point traversal | Disabled; immediate return | `observeStaticProbe`; C12 stats `static_probe_enabled=false`, witness counts zero |
| Odometry | Extra frontend subscription at source 100 Hz; yaw, velocity heading, stall latch | `odomCallback`, around 1160; preserve cadence and behavior |
| Replan status | 158 received messages over the whole recorded frontend lifetime | `replanCallback`, around 1272; no routine-success recovery release |
| Map-process ACK | 395 messages; exact identity check retained | `mapProcessAckCallback`, around 984 |
| Guard state | 3 messages; 1 recovery cycle, completed | `trajectoryGuardCallback`, around 1336 |
| Map-commit subscription | Not created for C12: max publication cap and age thresholds zero | Constructor, around 532; stats count zero |
| Statistics | 1 Hz state timer plus 5 s report timer and guard-edge writes | Constructor 601–607, `writeStats`/`report` 3067–3099 |
| ROS bookkeeping | Extra frontend node, normal node services/publishers/subscription waitables in shared pool | Adaptive composed entrypoint adds `filter.node` to side executor |

C12 frontend processed and forwarded 395/395 frames, no overwrites, no stale-source drops. Of these, 385 were acquired Sector passthrough and 10 Full recovery frames. Whole-run `cloud_compute_ms_mean=0.0176658227848`: approximately **6.978 ms elapsed total**, including the worker's acquisition of `state_mutex_` and direct enqueue. It is not thread CPU time and does not include all work outside that timed body, but is strong evidence against a large hidden point-processing workload.

`writeStats` formats a few hundred fields with string streams, truncates/writes a temporary JSON file, closes it, then renames it. It executes while holding `state_mutex_`. This is avoidable diagnostic work and could add latency, but its CPU cost has not been measured; roughly 1.2 periodic calls/s is not evidence for 0.035 cores by itself. Do not remove or reduce safety telemetry before measuring it.

## ROS/executor hypothesis supported by installed source

The Adaptive composition adds the frontend to the same two-thread `MultiThreadedExecutor` servicing FSM, command, and odometry callbacks. All frontend subscriptions/timers use its default callback group, with a further state mutex shared with the cloud worker and acquisition provider.

Installed Humble headers show that `AllocatorMemoryStrategy::collect_entities` traverses callback groups and collects subscriptions, services, clients, timers, and waitables; adding handles to a wait set then iterates those handles. `MultiThreadedExecutor` has a shared wait mutex. These are real places where an extra node can increase work outside existing application scopes. The headers do **not** measure the frequency/cost of those operations in this run.

`NodeOptions` defaults `start_parameter_services=true` and `start_parameter_event_publisher=true`. `NativeSectorCpp` takes its configuration from `Options`, not ROS parameter declarations. Its unused remote parameter-service entities are therefore a small candidate for an explicit opt-in experiment, after measuring. Disabling services changes remote introspection/control availability and must not be described as fully behavior-identical. Do not globally change ROS clock/parameter-event behavior or weaken callbacks just to lower CPU.

Relevant installed references:

- `/opt/ros/humble/include/rclcpp/rclcpp/strategies/allocator_memory_strategy.hpp:154`
- `/opt/ros/humble/include/rclcpp/rclcpp/executor.hpp:522`
- `/opt/ros/humble/include/rclcpp/rclcpp/executors/multi_threaded_executor.hpp:84`
- `/opt/ros/humble/include/rclcpp/rclcpp/node_options.hpp:400`

## Smallest useful next instrumentation

1. Emit `THREAD_CPU_ROLE` once **inside** the frontend cloud-worker function and map-worker function. This resolves the inferred TIDs above. Retain zero/inactive-risk markers as explicit state, not invented absent CPU samples.
2. Mark every actual shared-pool worker on its first executed known pooled callback, using one shared thread-local once guard. Label it `side_executor_shared`, not `frontend_thread`: callbacks migrate across these threads. Do not mark only the creator thread and assume it identifies the entire pool.
3. Add opt-in exclusive thread-CPU scopes around frontend odom, replan status, map ACK, guard state, cloud body, and statistics serialization/write. Put `writeStats` under its own nested scope so enclosing callback statistics do not double-count it. Count state/report callbacks separately if needed. Preserve existing default-off `SUPER_CPU_PROFILE` semantics.
4. Acquisition-provider/enqueue scopes may be nested in `SimRender`; frontend direct sink's `MapCloudEnqueue` may be nested in frontend-cloud scope. Use the same active-scope registry and sum **exclusive** stages only.
5. Append stage IDs; rebuild every consumer of `thread_cpu_profile.hpp`. The frontend currently has no declared `rog_map` dependency: use an explicit CMake/package dependency or factor a properly exported common profiler package/header. Do not add a fragile relative include or silently create a second registry in the component shared library. Verify one registry/report stream and known nested CPU totals in a tiny cross-shared-library test before trusting a flight profile.
6. If frontend bodies remain tiny and pool residual stays large, compare an explicit dedicated frontend executor or unused-parameter-services option in a fresh matched candidate. Keep source 10 Hz, ±45°/.4°, control/odom 100 Hz, exact Full request/ACK/path/release, fail-closed holds, and event retry behavior unchanged. Executor relocation is an architecture change requiring timing/recovery tests; it is not guaranteed to reduce CPU.

No direct-odom shortcut is recommended before this attribution: reducing receive rate, bypassing serialized latch state, or dropping map ACK messages could change risk/recovery timing. Likewise, replacing the tiny condition-variable cloud queue solely for CPU savings is a low-priority optimization.

## Realistic ceiling

C12 whole-flight mean cores are Full 0.60714838 / Adaptive 0.44755306, a 26.286% reduction. A 40% reduction at that Full cost needs Adaptive <=0.36428903 cores: another **0.08326404 cores** must be removed.

Even the optimistic, unproven assumption that **all** of the ~0.03476 extra residual can be removed only moves the saving to about **32.0%**, not 40%. The observed cloud body is around 0.00018 elapsed-seconds per wall-second; its elimination would be negligible and is not a valid safety trade. Thus frontend attribution is worthwhile, but it should not displace the higher-level ordinary-replan/goal-identity optimization currently under test.

One Full/Adaptive pair is insufficient to infer stable small overhead differences; preserve this as an attribution hypothesis and confirm in a fresh matched pair. Do not subtract measured diagnostic overhead from published CPU totals.

## Audit fingerprints

- `native_sector_cpp.cpp`: `ddf2c3b006d9de7b53a4331525223cd13e50c176276c798f228fddb8500a7ef8`
- `ros2_perfect_drone_adaptive_node.cpp`: `2b22b5c89542c8a6e0e2dc057f24337a921c920414830b68bce3f728d08d9ef6`
- C12 `telemetry.jsonl`: `eebf76f4434aac63df94296c4a14eb7413d53d886ec08501239345e64e93b6b3`
- C12 `thread_cpu_summary.json`: `5bfa6cd653740adf4c77191c17400179d34620b656c6d3a08b2a976633283be7`
