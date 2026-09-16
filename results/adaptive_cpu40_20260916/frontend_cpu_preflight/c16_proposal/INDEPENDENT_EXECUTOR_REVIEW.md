# Independent C16 executor source review

Read-only review by cpu_hotspot_instrumentation. Verdict: **GO for parent-authorized
apply, compile and focused lifecycle/protocol tests; not flight/adoption proof**.
No runtime files were edited and no build/ROS test was run by this reviewer.

Reviewed draft SHA-256:

- `frontend_executor_policy.hpp`: `33d9ab8167e2e79af321ab60dc884e7646ef57760aced757555a0c4a1516290d`
- `ros2_perfect_drone_adaptive_node.cpp`: `57742ae1172226b8a1b13cd4f5a02173c8cba02febf58ccf0ac1ffd833a957ed`

Reviewed the draft helper and full Adaptive binding against current runtime,
plus actual NativeSectorCpp construction/destruction, cloud-worker, acquisition,
direct SharedPtr sink and Full request/ACK flow.

Resolved during draft review:

- Immediate stop before executor.spin could lose cancel. Helper now waits with
  a sleeping startup-only handshake for actual is_spinning or worker_finished,
  then cancels and joins. Every normal/caught worker exit sets finished.
- New thread diagnostics/shutdown could throw out of the thread. Actual TID
  reporting is now inside the try, and failure reporting/shutdown is best-effort
  noexcept. Null-node input is rejected before dereference.
- New startup failure while legacy threads are joinable could terminate during
  unwinding. All registration is completed before spawning, threads are initially
  nonjoinable, frontend starts first, and main catches lead through shutdown and
  joins. Catch logging/shutdown and side/static cancel cleanup are guarded so an
  exception does not bypass the joins.

Ownership and teardown:

- Dedicated branch registers filter.node only in its own STE; disabled branch
  registers it only in the existing shared executor. No migration after spin.
- The new helper retains node ownership until callbacks stop and its thread joins.
- Normal/partial-start cleanup cancels executors, joins successful threads, then
  destroys frontend executor ownership while the filter handle is still alive.
- Simulator destruction then releases acquisition/submission closures; clearing
  the filter handle stops/joins its existing latest-only cloud worker. Its sink
  retains FSM/map ownership until that join. FSM/map is released afterwards.

Protocol scope is unchanged: same immutable acquired mode/cycle metadata, same
latest-only cloud worker, same stale-Sector rejection, exact Full request publish
before same SharedPtr map enqueue, and same committed exact ACK plus close latch.
The dedicated executor changes relative scheduling, so either ACK/close arrival
order and stale prior-cycle inputs still need the actual-component harness.

Required focused lifecycle evidence: destroy without start, immediate start/stop
repeatedly under an outer timeout, already-invalid context, context shutdown while
spinning, callback exception while context valid, duplicate registration and null
node rejection. Thread-allocation failure is source-reviewed unless explicitly
injected; do not claim that path was dynamically tested without evidence.

Limits: the composing thread must own start/stop/destruction (no self-join).
This does not repair the existing shared side-thread uncaught spin exception or
all static-executor diagnostic exception paths. Those unchanged legacy paths
must not be presented as fixed. Middleware progress and every shutdown exception
are not mathematically guaranteed by this source review.
