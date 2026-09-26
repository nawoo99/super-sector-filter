# Urban Sector v2 ON timing diagnosis

Date: 2026-09-26. Read-only evidence/source audit; no flights, production edits, or timing-threshold changes.

## Finding

The measured bottleneck is repeated **synchronous A* path searches inside the main FSM callback**, not the odometry observer or the command timer. Sector spends most of its late run in `GENERATE_TRAJ`, repeatedly calling `PlanFromRest`; each failed search consumes approximately its 100 ms timeout budget. Its late main-callback rate is about **9.96 Hz**. Earlier faster periods raise the finite-window average to **19.7567806255 Hz**, still a genuine failure of the unchanged 98–102 Hz gate.

This explains the main-callback cadence failure. It does **not** establish why A* cannot find a route, why the initial contact occurred, or that the new guard-v2 stop-policy checks caused the failure. Contact entry predates the sustained timeout loop.

Evidence directory: [Urban ON r01/run70005](/root/super-sector-filter/results/scenario7_guard_contract_smoke_20260926_v2b/preflight/urban_blocks_u01/r01_run70005).

## Measured evidence

[sector_summary.json](/root/super-sector-filter/results/scenario7_guard_contract_smoke_20260926_v2b/preflight/urban_blocks_u01/r01_run70005/sector_summary.json) reports mission timeout at 180 s, native contact count 1, and only `fsm_main_callback=false` among the small-pool timing checks. Sensor cadence, received-odometry cadence/interval/order checks, command callback, and profile coverage all pass.

[thread_cpu_summary.json](/root/super-sector-filter/results/scenario7_guard_contract_smoke_20260926_v2b/preflight/urban_blocks_u01/r01_run70005/thread_cpu_summary.json), Sector PID 3930949, uses a 175.63590272 s first-to-last profile-report window:

| Stage | Completed calls in window | Inclusive CPU-s | Exclusive CPU-s | Meaning |
| --- | ---: | ---: | ---: | --- |
| `fsm_main_callback` | 3470 | 155.217371 | 0.013969 | `3470/175.63590272 = 19.7567806255 Hz`; nested work dominates |
| `fsm_main_core` | 2972 | 155.160295 | 0.076433 | Main state-machine work contains the expensive computation |
| `planner_path_search` | 1610 | 157.089976 | 157.089976 | 97.5714 CPU-ms/call; 0.894407 mean cores |
| `fsm_replan_callback` | 2656 | 2.531106 | 0.050269 | Separate replan callback is not the dominant Sector CPU consumer |
| `map_prob_update` | 1756 | 6.470582 | 6.470582 | 3.68484 CPU-ms/call |
| `fsm_command_callback` | 17564 | 0.162126 | 0.162126 | `17564/175.63590272 = 100.002332826 Hz` |

Inclusive scopes contain child scopes: these totals must **not** be added together. Path search accounts for approximately 92% of the profile's summed exclusive mean CPU use. The composed process averages 99.52% of one core in the external samples; three executor threads share most of that work. Thread migration across executor workers is not evidence of three independent path searches or proof of machine-wide CPU saturation.

Differencing consecutive cumulative `THREAD_CPU_PROFILE` records in the Sector stack gives main-callback rates 99.60, 92.80, 82.28, 83.84, and 33.59 Hz in the first five report intervals, then approximately 9.964 Hz per interval for the long tail. Main-callback inclusive CPU use in that tail is approximately 0.99 core. This is prolonged callback work, not merely a misleading whole-run average caused by startup or a missing report. Counters record completed scopes, so they are not exact callback start timestamps; that distinction cannot explain an approximately tenfold sustained reduction.

## Stack chronology and source path

All stack line references below point into [Sector attempt1.stack.log](/root/super-sector-filter/results/scenario7_guard_contract_smoke_20260926_v2b/preflight/urban_blocks_u01/r01_run70005/artifacts/urban_blocks_u01_run70005_sector.attempt1.stack.log).

1. Analytic contact enters at header time `1790429495.514220511`, observed elapsed 6.404 s, near `building_10`, position `[-3.833237,3.342918,2.121759]`; the [solid audit](/root/super-sector-filter/results/scenario7_guard_contract_smoke_20260926_v2b/preflight/urban_blocks_u01/r01_run70005/artifacts/urban_blocks_u01_run70005_sector.attempt1.solid_audit.json) provides this event. This is not merely a brief touch: the audit records 17361 contact samples and `in_contact_at_end=true`. The first logged A* `TIME_OUT` is later, at `1790429497.353725086` (line 1235).
2. A final successful certified local escape is committed as generation 24 around `1790429511.5727` (lines 2213–2217), followed by approximately one second in `FOLLOW_TRAJ`.
3. The short trajectory ends; `PubCmdCallback` transitions `FOLLOW_TRAJ -> GENERATE_TRAJ` at line 2255, bracketed by timestamped records near `1790429512.6054` and `1790429512.6918`.
4. Path search then repeatedly returns `TIME_OUT`; `PlanFromRest` fails and remains in `GENERATE_TRAJ`. Line 2279 records `TRAJ_GUARD_BASE_NO_PATH_EXHAUSTED`, start `[-9.325,10.525,2.575]`, but does not terminate the repeated planning loop. There are 1604 `Path search failed with [TIME_OUT]` records and 1590 `PlanFromRest failed, try replan` records across the full log. The last timeout is `1790429669.517200558` at line 17008.
5. Across the final 120 seconds, 1195 consecutive timeout-record gaps have median 100.338936 ms, minimum 100.149632 ms, and maximum 100.653648 ms. This matches the approximately 100 ms search budget and the observed late 9.96 Hz main-callback rate.

The source directly explains that execution path:

- [fsm_ros2.hpp:4080](/root/super_ws/src/SUPER/super_planner/include/ros_interface/ros2/fsm_ros2.hpp:4080) creates the main timer at 10 ms in its own mutually exclusive callback group; the command timer also has a 10 ms period but a **different** mutually exclusive group. A long main invocation therefore serializes subsequent main invocations without requiring the command callback to stall.
- [fsm_ros2.hpp:4898](/root/super_ws/src/SUPER/super_planner/include/ros_interface/ros2/fsm_ros2.hpp:4898) calls `callMainFsmOnce()` synchronously under `FsmMainCore`.
- [fsm.cpp:169](/root/super_ws/src/SUPER/super_planner/src/super_core/fsm.cpp:169) handles ordinary `GENERATE_TRAJ` by synchronously calling `PlanFromRest`. Failure logs a retry and leaves the same state; there is no active retry backoff in that branch.
- [super_planner.cpp:4213](/root/super_ws/src/SUPER/super_planner/src/super_core/super_planner.cpp:4213) scopes `PlannerPathSearch`, and [super_planner.cpp:4275](/root/super_ws/src/SUPER/super_planner/src/super_core/super_planner.cpp:4275) invokes A*. The default timeout is 0.1 s in [astar.h:156](/root/super_ws/src/SUPER/super_planner/include/path_search/astar.h:156); [astar.cpp:581](/root/super_ws/src/SUPER/super_planner/src/super_core/astar.cpp:581) returns `TIME_OUT` after this elapsed-time budget.

The commanded timer period remains 10 ms; it was not configured to 20 Hz. Nor is the failure evidence a command-message frequency proxy: [adaptive_cpu40_seed1.py:42](/root/super-sector-filter/scripts/native_campaign/adaptive_cpu40_seed1.py:42) computes callback Hz from actual profile counter differences divided by the report window. The profile scope increments completed-call counters at destruction in [thread_cpu_profile.hpp:167](/root/super_ws/src/SUPER/rog_map/include/super_utils/thread_cpu_profile.hpp:167).

## Adaptive contrast and limits

Urban Adaptive also times out and records contact; its passing timing audit is **not** a safety/completion success. It averages main 98.8483 Hz and command 100.0011 Hz. Its 364 path-search calls consume 32.6345 CPU-s, while main-callback inclusive CPU is only 2.5011 s and replan-core inclusive CPU is 30.9664 s. Its late main rate returns to approximately 100 Hz, and late timeout-record gaps are approximately 528 ms rather than 100 ms.

This is consistent with a different recovery state/execution path: certified-stop asynchronous recovery performs `PlanFromRest` under `FsmReplanCore` in [fsm_ros2.hpp:3117](/root/super_ws/src/SUPER/super_planner/include/ros_interface/ros2/fsm_ros2.hpp:3117), serviced by the separate replan callback at [fsm_ros2.hpp:4483](/root/super_ws/src/SUPER/super_planner/include/ros_interface/ros2/fsm_ros2.hpp:4483). Ordinary `GENERATE_TRAJ` planning still executes synchronously on the main callback despite async recovery being enabled. The measured stage distribution and logs support this distinction; it is not evidence that the Sector configuration disables the async option.

The proximal cadence cause is well supported. The deeper reason for repeated search timeout—observed/free topology, search complexity, recovery position, or other map/search conditions—is not established by these aggregate records. A timeout does not prove no physical route exists. In particular, the early contact cannot be explained solely by a sustained retry loop beginning later. No extra threshold relaxation, retry allowance, executor change, or planner repair is implemented by this report; this ON timing failure remains an admission failure.

## Evidence integrity

The current `fsm_ros2.hpp`, `fsm.cpp`, `astar.cpp`, `super_planner.cpp`, and `thread_cpu_profile.hpp` SHA-256 values were checked against this smoke's root `frozen_inputs_and_evidence.json`; all match. The child plan also directly binds the FSM ROS2 header. Evidence SHA-256 values:

| File under the evidence directory | SHA-256 |
| --- | --- |
| `sector_summary.json` | `ec0ed4c302ec79848961aea07a4dbc93c5a12dfdf5eee61f9be02c2819b33c07` |
| `adaptive_summary.json` | `88a20da9a846eab0de8ac4a3aba7640f91587fa4f0eb64c762c3e6f2330f7921` |
| `thread_cpu_summary.json` | `547deb236cf76bc6fedebdda2209f6f09d4bf4f5557a611bae6c320b127f665c` |
| `artifacts/urban_blocks_u01_run70005_sector.attempt1.stack.log` | `0dff4f576309524e6908a3050d4c4e83628a3e2fbb83a17cb1c1f5d6229d5827` |
| `artifacts/urban_blocks_u01_run70005_sector.attempt1.solid_audit.json` | `f0a1e198f975e881aeae0a20b0e77f837e434c4e791eeccbae30a70911fd4c45` |
| `artifacts/urban_blocks_u01_run70005_adaptive.attempt1.stack.log` | `649a3fd1c28e27b915a7ee6a5ca0bef4940d0f991ba45b19ca6c8302834af4f3` |
