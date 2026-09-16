# Prospective Adaptive frontend dedicated-executor experiment

2026-09-16, while C15 builds. **Design only; no runtime edits, compilation, ROS processes, or flights for this proposal.** Review C15 results before deciding whether to implement.

## Proposed change and hypothesis

Introduce explicit `SUPER_FRONTEND_DEDICATED_EXECUTOR=1`, default off, for the composed Adaptive executable. Move the existing `filter.node` from the shared two-worker `MultiThreadedExecutor` to one ordinary `SingleThreadedExecutor` on its own thread. Do not create a second node or duplicate subscriptions. Do not use `StaticSingleThreadedExecutor` or assume unsupported callback-group APIs.

The potential benefit is removing frontend entities and readiness scanning from the executor that handles the 100 Hz FSM/command/odometry work. The dedicated executor still does real frontend work, whose CPU remains included in the same experiment cgroup. The extra thread has a cost, so total CPU might be unchanged or worse.

Full has no frontend node. Leave its existing execution path unchanged; do not create dummy work, sleeps, or a no-op executor to manufacture equal thread counts. The algorithm-specific infrastructure cost belongs to Adaptive. Common optimizations already enabled in both modes stay identical. Runner records this as an Adaptive-specific feature rather than a common optimization that must execute in Full.

Suggested strict parser: unset, empty, `0` -> false; exactly `1` -> true; other nonempty strings -> startup error. An explicit implementation marker in Adaptive should say:

```text
[FRONTEND_EXECUTOR_SETTINGS] dedicated=1 executor=single node=native_sector_cpp existing_default_group=1 callbacks_qos_cadence_unchanged=1
```

When profiling is enabled, invoke the existing `reportThreadRole("frontend_event_executor")` **inside the new thread**, immediately before its `spin()`. The emitted `[THREAD_CPU_ROLE]` PID/TID is an actual executor-thread identity. Do not report the thread creator's TID. When disabled, report `dedicated=0 executor=shared` and preserve the original `side_executor.add_node(filter.node)` path with no extra thread.

## Existing execution and metadata flow

Source anchor: `mars_uav_sim/perfect_drone_sim/src/ros2_perfect_drone_adaptive_node.cpp`.

Current thread ownership:

```text
main/render STE ── acquisitionRequest() ── frontend state mutex
       │
       └─ acquire selected angular window → submitAcquiredCloud()
                                            │
                               existing latest-only cloud queue
                                            │
                               existing frontend cloud worker
                                            │
                               metadata mode/cycle verification
                                            │
                      exact Full request publish, when required
                                            │
                                  same SharedPtr map enqueue
                                            │
                                   existing ROG-Map worker

shared two-worker executor:
  FSM/control/odom callbacks + frontend's default callback group
```

The proposal changes only the last frontend callback-group ownership to a dedicated STE. It does not move acquisition to that executor, does not move point processing to an executor callback, and does not merge/delete either latest-only worker.

Frontend callbacks already share the node's default callback group: subscriptions and timers are created without an explicit group. That group is MutuallyExclusive in the current node model. Moving the node to STE therefore preserves one-at-a-time execution **within the frontend**, but changes scheduling relative to FSM callbacks. No ordering between different ROS topics may be assumed just because the frontend is now single-threaded; that ordering was not guaranteed before either.

Observed C12 enabled work: odom at 100 Hz; replan-status subscription; exact map-process ACK subscription; transient-local guard-state subscription; state timer at 1 Hz and report timer at 0.2 Hz. No cloud DDS subscription/output, risk worker, raw-risk trajectory subscription, static-probe traversal, or map-commit-age subscription is active. C15 may remove unused remote parameter entities before this experiment.

### Exact recovery invariants retained

1. `acquisitionRequest()` captures `{enabled, full, cycle, heading, half_angle}` under `state_mutex_` before render.
2. The acquired frame carries that immutable metadata into the existing latest-only queue.
3. `processCloud` holds `state_mutex_` and rejects a frame whose mode/cycle no longer matches current recovery state. Old Sector data cannot stand in for a fresh Full scan.
4. `EventRecoveryLatch::fresh` requires sequence and source stamp later than the recovery boundary.
5. On an eligible Full frame, exact refresh-request publication occurs before invoking the direct map sink. Both remain within the same cloud-worker critical section and the same source path.
6. ROG-Map's `injectCloud` stays admission/enqueue-only; its worker performs conversion/update/commit and publishes the exact source-stamp ACK.
7. The frontend latch closes only after matching committed ACK **and** planner close request. `EventRecoveryLatch` explicitly supports either arrival order. A separate FSM subscriber to the same ACK still validates planner-side recovery and new-path conditions.
8. New executor scheduling is not permission to weaken any exact stamp, sequence, cycle, generation, map freshness, stop certificate, or new-path requirement.

The source ±45° half-angle, 0.4° resolution, 10 Hz acquisition, 100 Hz odometry/command/FSM timers, QoS, retry policy, callbacks, and counters stay unchanged.

## Locking and lifetime review

Relevant sources: `mission_planner/Apps/native_sector_cpp.cpp`, `mission_planner/include/mission_planner/event_recovery_latch.hpp`, `rog_map/include/rog_map_ros/rog_map_ros2.hpp`, and `super_planner/include/ros_interface/ros2/fsm_ros2.hpp`.

| Path | Existing lock/order | Effect of dedicated STE |
|---|---|---|
| Frontend odom/ACK/replan/guard/state/report | Default callback-group exclusion, then `state_mutex_` | Same local serialization; dedicated thread can contend with render/cloud worker sooner |
| Render acquisition query | `state_mutex_` only | Unchanged; may still wait behind statistics I/O or another callback |
| Acquired-cloud enqueue | `cloud_queue_mutex_`; notify condition variable | Unchanged; no new executor lock taken by producer |
| Frontend cloud worker | Pop job under queue mutex, release it, then take `state_mutex_` | Unchanged; never hold queue mutex while waiting for state mutex |
| Cloud worker direct sink | Frontend state mutex, then existing map admission/state/queue locks | Unchanged; map worker releases queue lock before heavy update |
| Full/event request publication | Existing frontend state mutex, ROS publish; selected publishers explicitly disable intra-process delivery | Unchanged protocol; no new direct call into FSM or synchronous service wait |
| ACK/release reception | ROS callback on new executor, then frontend state mutex | Delivery timing changes; latch already supports ACK/release order reversal |
| Filter destructor | Stop/join cloud worker before final state-locked statistics write | Must remain after all executor callbacks and render closures stop |

No source path was found that synchronously calls back into the frontend while holding the map enqueue mutex. The proposed ownership change introduces no new application mutex or lock-order edge. This is a bounded source audit, not a complete middleware deadlock proof. In particular, `writeStats` still performs file I/O under `state_mutex_`; executor isolation does not solve that latency source.

### Required normal teardown order

1. Stop/cancel render and all side/static/frontend executors as appropriate; request cancellation before joining any executor thread.
2. Join the frontend executor thread while the frontend, simulator, and FSM are still alive. Also join existing side/static threads.
3. Remove/reset the dedicated frontend executor while `filter.node` is still valid, so executor-held resources cannot retain callbacks past teardown.
4. Preserve the existing order: report sensor cadence; `simulator.reset()` releases acquisition/submission closures; `filter = {}` stops and joins the frontend cloud worker; only then release FSM/map ownership.
5. Do not release the filter before stopping its new executor, and do not release the map while a frontend cloud job can still invoke its sink.

Register each node with **exactly one** executor before starting threads. Conditional ownership must not call both `add_node` paths or dynamically migrate a spinning node. Prefer completing all executor/group construction before spawning the new thread, so initialization errors do not strand it.

The new spin wrapper should use the existing static-executor pattern: catch a non-shutdown `std::exception`, set an atomic failure flag, log it, call `rclcpp::shutdown()` to stop the rest of the process, join, and return nonzero. An already-invalid context during signal shutdown is ordinary teardown. Catch-all protection/RAII for the added thread is advisable to prevent `std::terminate` on an unjoined new thread; do not claim that this alone repairs all existing side-thread exception paths.

## Tests before claiming a benefit

### 1. Lightweight real-component executor harness, no GPU/FSM

Instantiate the actual `native_sector_cpp` component with the existing source/event-recovery arguments and a recording direct sink. Exercise both shared-pool control and dedicated-STE candidate in separate preserved attempts on an unused ROS domain.

- Confirm exactly one executor owns the frontend; all its subscription/timer callbacks execute, and the dedicated TID marker corresponds to its running thread.
- Feed fake odom at 100 Hz and source frames at 10 Hz; verify heading/source-window behavior, payload identity, same `SharedPtr` direct handoff, no unintended DDS cloud publisher/subscriber, and one output per admitted frame.
- Inject guard-true, then a queued pre-transition Sector frame: it must not be accepted as fresh Full evidence.
- Submit fresh correctly tagged Full frames, capture exact request stamp/sequence, and inject wrong-stamp, zero-version, and uncommitted ACKs; none may release Full.
- Test close-before-ACK and ACK-before-close: only the matching committed ACK plus close permit Sector. These harness closes are synthetic protocol tests, **not** planner safety certificates.
- Exercise a second recovery cycle and stale prior-cycle metadata/ACK; no prior evidence may close it.
- Verify cloud worker remains condition-variable/latest-only, statistics callbacks still run, and normal cancellation/context shutdown with a pending cloud terminates within a bounded timeout without use-after-free or deadlock.

No artificial executor load belongs in the performance baseline. A separate bounded synthetic scheduling-stress test can validate responsiveness, but cannot be used for CPU-savings claims.

### 2. Real matched seed1 profile pair

Keep Full unchanged and all common C15 settings matched. Run Full and Adaptive once each with fresh result paths; no automatic retry. Require the existing resource, source-cadence, speed, complete/contact-zero, exact-recovery, goal-identity exercise, and mission-time gates.

Keep current two-worker timing gates: source 9.5–10.5 Hz; main/command and odom about 100 Hz; odom header/receipt p99 <=20 ms and max <=50 ms; no backward/repeated timestamps. Check actual callback counts as well as message cadence. Audit Full-open observation -> exact committed map -> newly certified path -> Sector ordering by timestamps, not log-line order. Preserve all held-stop/failure behavior.

Use actual `frontend_event_executor` TID CPU **in addition to**, not instead of, shared-pool/process/cgroup CPU. A drop in shared-pool CPU accompanied by equal new-thread CPU is migration, not a saving. Compare total experiment mean cores and cumulative core-seconds. Check recovery request/ACK/path/release latency and outstanding cycles; do not accept a CPU gain achieved by delayed or missing work.

If an eligible profiled pair reaches the target, perform the required matched unprofiled confirmation, preferably reversed mode order, under the existing frozen-source/binary/reference contract.

## Benefit ceiling and decision rule

The C12 approximate extra pooled residual was ~0.0334 cores and whole-process difference ~0.03476 cores. Even eliminating all of that at C12 costs would only move relative saving from 26.29% to roughly 32%, not 40%. The new STE itself consumes CPU, so expected net benefit is smaller and could be negative.

C15 targets part of the same entity-management work. Its saving and the old C12 residual cannot be added as independent opportunities. Re-estimate the residual after C15 before implementation. C14's goal-identity change achieved 26.98% mean CPU reduction but did not meet the target; it does not establish a different frontend ceiling.

Proceed only if C15 leaves a meaningful pooled residual or timing evidence worth investigating. Keep the feature default off, preserve a no-dedicated-executor control, and reject a candidate that regresses timing/protocol or merely shifts CPU between threads. This is a plausible small architecture experiment, not a credible stand-alone guarantee of 40% savings.
