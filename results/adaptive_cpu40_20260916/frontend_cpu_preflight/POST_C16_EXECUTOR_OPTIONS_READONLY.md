# After C16: remaining executor CPU options (read-only)

Prepared during C16 build/flight freeze. No runtime, runner, config, ROS process,
compiler, or benchmark was changed/launched. No change to static-PC/RViz delivery,
sensor cadence, command cadence, or the current .5 s lease is proposed here.

## Recommendation

Do not collapse the side pool to one thread or replace the complete side MTE
with one STE. The next defensible *small* experiment is replacing only already
single-threaded, fixed-entity executor domains with Humble's installed
StaticSingleThreadedExecutor, keeping thread count, ownership, callbacks, timer
periods and QoS unchanged. Treat each domain as a separate ablation, not a promise
of 40%. A broad side-pool redesign has substantially more concurrency/liveness
risk for a limited remaining CPU component.

The largest already-STE opportunity is its existing dedicated static-PC executor
loop. This would be **only an executor-class substitution**, not moving RViz,
changing 1 ms polling, subscriber-count behavior, payloads or bootstrap/late
delivery. Because the user-facing static/RViz decision is pending, do not act on
even this option without root explicitly confirming its executor-only scope.
Mission STE and the C16 frontend STE are independent lower-risk alternatives;
renderer STE has essentially no measurable framework residual to remove.

## C15 evidence and ceiling

Sources: `c15_headless_parameters_profile/{full,adaptive}_summary.json` and
`thread_cpu_summary.json`. Cgroup means cover whole experiment; stage and thread
windows differ slightly, so these are ceiling estimates, not exact accounting.

| C15 CPU item (used cores) | Full | Adaptive |
|---|---:|---:|
| Whole-experiment mean | .579887 | .393000 |
| Two likely side-pool thread means, sum | .136934 | .161549 |
| Replan + main + command + simulator-odom inclusive callbacks | .093898 | .095835 |
| Difference, containing real unprofiled callbacks too | .043036 | .065715 |
| Dedicated static-PC thread, matched profile window | .047341 | .045041 |
| Static-PC callback CPU | .016213 | .015089 |
| Static-PC thread minus callback | .031128 | .029952 |
| Renderer thread minus callback | .000329 | .000605 |
| Entire mission process, including actual work/DDS | .023472 | .024492 |

The two side-pool TIDs are inferred by the actual executor construction/thread
layout and exclusion of recorded static/render roles; they lack direct pool-role
markers. Their difference includes map odometry, goal/ACK work and middleware,
not just scanning/locking waste. New measured thread-role evidence would improve
attribution before any broad scheduler claim.

With unchanged Full cost, Adaptive needs another .045068 core reduction to reach
40%. Removing the *same* common cost from both requires .112671 core per mode.
Deleting even ALL static-PC thread-minus-callback cost projects only 33.84%
relative reduction. RCL waiting, timer dispatch and context switches remain, so
an actual static-executor gain must be smaller than that deletion thought
experiment. Renderer conversion work cannot be called executor overhead.

Deleting both entire side-pool residuals AND entire static-PC residuals projects
about 41.21%, but that unrealistically deletes useful callbacks and all waiting
overhead. It shows how close the target is to the extreme accounting ceiling,
not a feasible prediction. C16's possible Adaptive benefit is already inside
the pre-C16 side residual; do NOT add it again as an independent opportunity.
Re-estimate after the actual C16 pair. Faster mission completion may help
cumulative CPU, but must not be substituted for the requested mean-CPU metric.

## Installed Humble support, verified rather than assumed

Installed package is `ros-humble-rclcpp 16.0.11-1jammy.20241128.012309`.
Local headers at `/opt/ros/humble/include/rclcpp/rclcpp/executors/` declare
StaticSingleThreadedExecutor `add_node` **and** `add_callback_group`; the installed
`librclcpp.so` exports both. The exact 16.0.11 implementation forwards manual
groups to its collector, caches entity lists, and refreshes ready handles each
wait. It executes ready subscriptions before timers, so it is not guaranteed to
preserve ordinary STE callback ordering. These are real APIs, not an invented
StaticMultiThreadedExecutor or a claim about a different ROS release.
[Executor source](https://raw.githubusercontent.com/ros2/rclcpp/16.0.11/rclcpp/src/rclcpp/executors/static_single_threaded_executor.cpp),
[collector source](https://raw.githubusercontent.com/ros2/rclcpp/16.0.11/rclcpp/src/rclcpp/executors/static_executor_entities_collector.cpp).

Existing eligible domains:

- Static-PC and renderer use **manual callback-group registration** on the
  simulator node; keep that exact group, never add the entire simulator node to
  either executor. Manual collector registration does not automatically take
  the other simulator groups. Their callbacks/entities are constructed before
  spinning. The static-PC domain has only its existing timer in current config.
- Mission identity mode already serializes all four groups in one STE. A class
  substitution keeps serialization, but subscription-before-timer order can
  affect goal-switch/odom observations; replay the actual identity fixture.
- C16 frontend already has one node/STE and fixed subscriptions/timers. Retain
  its reviewed ownership/cancel handshake and all cloud worker/ACK semantics;
  rerun the actual component protocol/lifecycle fixture with the new class.

Static executor is not a cure for slow callbacks, long locks or dynamic lifetime
bugs. All nodes/groups must remain alive through cancellation/join. Its collector
and ordinary executor must never both own the same group. No dynamic migration
or callback creation during the trial; graph discovery is not permission to
mutate the registered entity ownership while spinning.

## Why a single control executor is not yet a safe shortcut

`FsmRos2` has distinct mutually-exclusive main, command, replan, goal, map and
refresh-ACK groups. The current two-worker pool permits overlap across them.
Both main FSM and replan can do synchronous safety/solver work; even the command
callback can synchronously call `activateEmergencyBrake("command_velocity_limit")`.
Combining these with simulator odometry into one STE can stall 100 Hz commands
or odometry precisely on exceptional paths, even if ordinary seed1 looks cheap.

Separating replan into one STE and putting all remaining callbacks into another
does not remove the main-brake/command/odom contention. A genuinely isolated
design would need separate main, replan, command and odom/event domains or a
reviewed asynchronous brake dispatch redesign. That adds threads/lock overlap,
changes scheduling, and may expose latent races beyond the existing two-worker
concurrency. There is no installed StaticMultiThreadedExecutor to simply select.
I would not bundle that architecture change into the next CPU trial.

## Required gates for an authorized existing-STE substitution

1. Default off, explicit marker naming executor class/domain; apply common
   domains identically to Full/Adaptive, and frontend domain only where it
   actually exists. No dummy Full work or denominator changes.
2. Actual installed-library test: manual-only group registration does not execute
   another group from the same node; duplicate ownership is rejected; fixed node
   subscriptions/timers run; cancel-before-spin/context shutdown/exception paths
   terminate under outer timeout. Retain C16 lifetime protections.
3. For static-PC, preserve identical 1 ms callback opportunities, bootstrap,
   subscriber-count transitions, geometry SHA and late/reconnect behavior under
   the established reference gate—no claim that an executor change fixes DDS
   delivery. Root must first resolve whether this executor-only scope is allowed.
4. Run the relevant mission identity / frontend exact ACK+close-order fixtures.
   Keep 10 Hz source, 100 Hz command/main/odom, .5 s demand policy and all callback
   counts/time/collision/complete gates. Recheck exception-path timing, not only
   average seed1 callbacks.
5. Compare process/cgroup mean and cumulative CPU, as well as actual domain-TID
   CPU. Reject mere cost migration or delayed/missing work. Do not add overlapping
   inferred residuals across C15/C16. Rebuild/freeze and obtain an unprofiled
   confirmation before any adoption or 40% claim.
