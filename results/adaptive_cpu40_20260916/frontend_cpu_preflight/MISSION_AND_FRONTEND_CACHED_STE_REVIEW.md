# Optional cached mission/frontend STEs after C17

Read-only proposal; no implementation/build/ROS/flight. C17 remains a separate
static-PC executor-only experiment. No static delivery, cadence or lease change.

## C16 measurement and priority

Source: `c16_frontend_executor_profile/{full,adaptive}_summary.json` and
`thread_cpu_summary.json`. Whole-experiment means were Full .599322 / Adaptive
.402191 cores (32.8923% reduction). Adaptive's absolute mean exceeded C15's
.393000, so a net benefit from C16 has not been demonstrated.

| C16 estimate (cores) | Full | Adaptive |
|---|---:|---:|
| Inferred two-worker pool total | .145346 | .155214 |
| Named replan/main/command/simulator-odom callbacks | .093709 | .106686 |
| Difference, including unprofiled useful work | .051637 | .048528 |
| Actual dedicated frontend role | absent | .014028 |
| Mission main-thread CPU | .018106 | .017507 |

Pool identities are inferred; stage/thread windows differ slightly. Relative to
C15, Adaptive's pool residual fell about .01719 core but its new frontend thread
cost .01403: the rough net is only .00316, within single-flight variability.
Full's own pool residual grew about .00860, reinforcing the need not to call
these differences an isolated deterministic saving.

Deleting the **entire** frontend thread—not achievable because real callbacks
remain—projects only 35.23% reduction using C16 means. Its resulting Adaptive
mean would be .388163, merely .00484 below C15. Deleting both entire mission
main threads plus that entire frontend thread projects 36.23%. These are loose
component ceilings, not speedup predictions; cached entity handling can remove
only a fraction. Do not stack C15 pool residual, C16 isolation, and C17 changes
as independent savings. Neither optional change is a credible standalone path
to 40%.

## Mission-only option: simpler and common

Under a new default-off flag, replace only the already-serialized STE branch in
`mission_planner/Apps/ros2_waypoint_mission.cpp` with the installed Humble static
STE. Require existing goal identity mode; leave the legacy MTE branch unchanged.
Apply identically to Full and Adaptive. The complete node and all four groups
already exist before `add_node`/spin, with no live ownership migration. The
executor's scope ends before WaypointPlanner/node destruction. Keep 100 Hz
mission checks/odom, 1 Hz retransmission rules, exact stamp allocation, marker
subscriber handling, all QoS and callbacks unchanged.

Actual class marker and producer fixture must reflect the new class; repeat the
real waypoint/odom/retrigger identity test. Static STE executes ready subscriptions
before timers, so expect preserved serialization but not bit-identical scheduling.
The entire main-thread cost is only about .018 core; expected saving is a subset.
This is the lower-risk of these two optional code changes, not a target solution.

## Frontend option: only if measured net benefit justifies it

Require existing C16 dedicated frontend mode plus a separate default-off cached
flag; reject cached-with-shared ownership. Replace only the helper's executor
storage/factory with `unique_ptr<rclcpp::Executor>`, preserving node context,
actual TID reporting, spin-entry/finished cancel handshake, no-throw failure
handling, join, and reset-before-filter teardown. Keep full-node registration on
exactly that executor and every cloud-worker/request/ACK/close callback unchanged.
Full has no frontend and must not acquire dummy work.

Replay all six C16 lifecycle/component cases including both exact ACK/close
orders, stale frame/ACK rejection, same SharedPtr/no cloud DDS, and context
shutdown. A cached executor cannot eliminate frontend odom/state/stats work.
Compare against both C16 dedicated ordinary control and the C15 shared baseline;
adopt only if absolute Adaptive/cgroup CPU improves without timing/protocol
regression, not because Full varied upward. New runtime tests and a matched
unprofiled confirmation remain necessary.
