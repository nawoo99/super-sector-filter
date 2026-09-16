# C16 dedicated frontend executor: applied, helper preflight passed

2026-09-16. Initially staged outside runtime; root subsequently authorized runtime-first application, mirroring, and the focused helper preflight. **No simulator-package build or flight was run by this subtask.** Production files were frozen after the tests for root's separately coordinated build.

## Implementation

- New `perfect_drone_sim/frontend_executor_policy.hpp`: strict default-off `SUPER_FRONTEND_DEDICATED_EXECUTOR`; scoped owner of one ordinary `SingleThreadedExecutor` and the existing frontend node.
- Adaptive entrypoint only: frontend node goes to exactly one executor (existing shared pool when off; dedicated STE when on). Full entrypoint is unchanged from C15; no dummy executor or artificial Full work.
- C15 headless NodeOptions remain in place. This option does not change callbacks, QoS, timer periods, source geometry/cadence, latest-only cloud worker, or Full request/map ACK/path-release logic.
- Startup marker `[FRONTEND_EXECUTOR_SETTINGS]`; actual new-thread profile marker `role=frontend_event_executor` emitted from its running thread.
- The owner waits for `is_spinning()` or worker completion before cancelling, avoiding a lost-cancel race when stop immediately follows start. The handshake sleeps on a condition variable at up to 1 ms intervals and is used only during teardown; no new ROS timer or periodic flight callback is introduced.
- New spin/cancel errors while the context is valid set a failure flag and request context shutdown. Logging/shutdown are best-effort and cannot escape that error handler. Normal context-invalid shutdown is not treated as an application error.
- All node/group registration precedes thread creation. The composing path catches partial startup/render errors, cancels all executors with no-throw wrappers, joins successfully created threads, resets the frontend executor while the filter is alive, then preserves simulator -> filter/cloud-worker -> FSM/map teardown ordering.

Independent review by `/root/cpu_hotspot_instrumentation` identified the initial lost-cancel and no-throw-cleanup issues; both were corrected before application/testing. Existing side-thread/static callback exception behavior is not claimed to be repaired or fully verified by this helper. Catastrophic middleware shutdown failure is best-effort, not a formal shutdown guarantee.

## Real-component tests

`frontend_executor_test.cpp` derives the pointer/payload/stamp and explicit stale-metadata checks from existing `mission_planner/test/native_direct_sink_test.cpp`. It links the actual `mission_planner::native_sector_cpp_component`, not a reimplementation. The event handshake cases reuse the two arrival-order checks from `scripts/native_campaign/test_event_recovery_transport.py`, now against that component under the actual candidate executor ownership.

Control uses a real two-worker `MultiThreadedExecutor`; candidate uses the new dedicated owner. An observer-only STE pumps test publications and witnesses. Headless parameter options are enabled in both component cases. These are protocol/lifetime tests, not simulated flight, cadence benchmarking, or planner safety certificates.

| Case | First execution | Checks |
|---|---|---|
| `shared` | PASS, exit 0 | Actual component on two-worker MTE; direct payload identity, exact stamps, explicit stale mode/cycle/untyped rejection, no cloud DDS, exact Full requests, invalid ACK holds, both ACK/close orders |
| `dedicated` | PASS, exit 0 | Same component checks on the new actual dedicated STE; actual thread-role markers present |
| `lifecycle` | PASS, exit 0 | Strict parser; null node; construct/destroy without start; duplicate executor ownership rejected; 32 immediate start/stop iterations |
| `invalid-context` | PASS, exit 0 | Context invalid before worker starts; stop/join returns normally |
| `context-shutdown` | PASS, exit 0 | Context shutdown immediately after start; stop/join returns normally |
| `callback-throw` | PASS, exit 0 | Intentional callback exception sets failure, invalidates context, and permits join |

Each case ran once, sequentially, with a 30 s outer timeout. No ROS execution retry occurred. The intentional error line in `callback-throw_run1.log` is the expected injected exception, not a failed preflight.

Direct/event statistics JSON files were copied from the helper's retained temporary directories into `shared_evidence/` and `dedicated_evidence/`. Test binaries/build files remain outside the repository at `/tmp/super-frontend-executor-test.402Cwy`.

Not tested here: injected OS thread-allocation failure, a full planner/FSM recovery certificate, 100 Hz flight timing, long-run CPU reduction, or population-level safety. Those require the root's simulator build/flight gates. A pending old-cycle ACK was not separately fault-injected in the two-cycle event test; exact-stamp rejection, invalid map versions/commit flags, and wrong metadata cycles were tested as stated above.

## Build attempts retained

1. Configure failed because standalone CMake mixed plain and keyword `target_link_libraries` forms through `ament_target_dependencies`; build could not start.
2. C++ compiled, link failed because the exported component's PCL/VTK/FLANN/Qhull imported targets had not been discovered by the standalone CMake project.
3. Added consistent `PUBLIC` dependency syntax, C-language enablement, and `find_package(PCL REQUIRED)`. Configure/build passed. The retained unused legacy-test function produces one harmless unused-function warning; it is not executed by this new harness.

All attempt logs remain named `configure_attemptN.log` / `build_attemptN.log`. Neither infrastructure correction changed production runtime code.

Reproduction after sourcing ROS/workspace:

```bash
cmake -S /root/super-sector-filter/results/adaptive_cpu40_20260916/frontend_cpu_preflight/c16_proposal \
  -B /tmp/super-frontend-executor-test.402Cwy \
  -DCMAKE_BUILD_TYPE=Release -DPython3_EXECUTABLE=/usr/bin/python3
cmake --build /tmp/super-frontend-executor-test.402Cwy --parallel 1
ROS_DOMAIN_ID=198 ROS_LOCALHOST_ONLY=1 SUPER_CPU_PROFILE=1 timeout 30s \
  /tmp/super-frontend-executor-test.402Cwy/frontend_executor_test dedicated
```

Use fresh log names for any rerun. Other case arguments are listed in the table above.

## Frozen source fingerprints

- Runtime helper: `33d9ab8167e2e79af321ab60dc884e7646ef57760aced757555a0c4a1516290d`
- Runtime test: `479d434736f744545e5cecada01ddbdfcd5275c075db3efd03e1443686c2f688`
- Runtime Adaptive entrypoint: `57742ae1172226b8a1b13cd4f5a02173c8cba02febf58ccf0ac1ffd833a957ed`

All three runtime files match their repository mirrors byte for byte. The root owns the next full simulator build and matched flight comparison. No CPU benefit is claimed from these helper results.
