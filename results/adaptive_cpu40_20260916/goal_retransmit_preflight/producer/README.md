# Producer command identity proposal

Status: producer-only applied after explicit parent approval; built and
no-flight actual ROS producer preflight passed on 2026-09-16. Paired exact
opt-in is `SUPER_GOAL_RETRANSMIT_IDENTITY=1`; receiver additionally requires the
guarded-demand feature. Invalid option strings fail startup; unset/0 preserve
the existing behavior. No flight or real receiver run is covered by this producer test.

## Files and application

- Install `goal_retransmit_identity.hpp` as
  `mission_planner/include/waypoint_mission/goal_retransmit_identity.hpp`.
- `producer_binding.patch` changes only
  `mission_planner/Apps/ros2_waypoint_mission.cpp` and
  `mission_planner/include/waypoint_mission/ros2_waypoint_planner.hpp`.
  `git apply --check` passed against the unchanged runtime on 2026-09-16.
- Pure test stays beside the helper here; when moved to the runtime test tree,
  change its include to `<waypoint_mission/goal_retransmit_identity.hpp>`.

The paired feature uses a SingleThreadedExecutor for the mission node ONLY
while enabled. Default remains its existing MultiThreadedExecutor. This is
required serialization of four previously separate callback groups, not a
claim those groups already executed serially. It also changes mission executor
CPU overhead, so the later ablation is a combined command-identity/serialization
candidate, not an isolated dedup-only causal estimate.

All callbacks were read: odometry stores pose/time; click/RC reset mission
trigger/index; timer checks odometry, advances waypoints, and publishes. There
are no sleeps, spin calls, synchronous service/future waits, or blocking queue
waits. Console and DDS publishing / marker generation can still take time; no
hard real-time bound is claimed. Existing goal timer10ms, odom source100Hz,
goal retransmission period1s, QoS and waypoint switch thresholds are untouched.

## Identity semantics

The mission already has semantic `new_goal=true` edges for initial mission,
waypoint advancement, RViz mission retrigger, and RC restart. The producer
captures that boolean before clearing it on publication. Periodic retransmits
retain the original identity only if every finite raw xyz/quaternion scalar and
frame still matches exactly; any changed field defensively creates a new ID
even if a semantic flag was accidentally absent.

The PoseStamped header stamp is retained command-creation identity, NOT each
retry's send time. New intents use current positive node time when possible;
same-tick/backward-positive-clock new intents use `last_issued+1ns`. This makes
the header an opaque creation identity with a monotonic tie-break, not a sensor
timing sample. It never exceeds ROS builtin Time's int32 sec / valid nanosecond
range. Invalid/nonpositive creation time, malformed raw payload/frame, or
identity exhaustion emits stamp0 and invalidates the identity cache. The goal
is still published on the original schedule; receiver must treat that stamp
as noncoalescible and use ordinary admission. No wrap/reused supported ID.

There is no identity-generated drop at the publisher. Intentional external
same-pose commands with fresh stamps remain new receiver commands. Repeats with
the same supported identity are only candidates for the receiver's separate
healthy/current-SAFE own-commit token; blocked/recovery retries are retained.
No old raw-to-map behavior-equivalence claim is made merely from identity.

## Evidence markers and capture

Startup: `[MISSION_GOAL_IDENTITY_SETTINGS] enabled=1 executor=single callbacks_serialized=1 timers_qos_unchanged=1`

Each unchanged-rate publication: `[MISSION_GOAL_IDENTITY] stamp_ns=... new_intent=... new_identity=... supported=... waypoint=...`

`benchmark_seedmap.launch.py` configures mission output as `log`. C12's stack
omits the old `std::cout` goal lines but DOES contain the mission RCLCPP_WARN
initialization lines. New RCLCPP_INFO markers may therefore already appear in
the stack through stderr handling. Keep launch output unchanged first; verify
this with the real producer preflight. If markers are missing, archive the
exact mission PID's ROS log instead. Missing stack markers alone do not prove
feature activation or nonactivation.

## Tests actually run

Both pure commands completed exit0 with 94 checks before runtime application.
The compiled test binaries were subsequently moved out of the repository to
`/tmp/super-goal-identity-tests.8cvtTm/`; only source, proposal and logs remain here.

```sh
g++ -std=c++17 -O2 -Wall -Wextra -Werror -pedantic goal_retransmit_identity_test.cpp -o producer_identity_test
./producer_identity_test
g++ -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer -Wall -Wextra -Werror -pedantic goal_retransmit_identity_test.cpp -o producer_identity_asan_test
ASAN_OPTIONS=detect_leaks=1 ./producer_identity_asan_test
```

Coverage: option parsing, identical retransmits, same-pose new intents,
same-tick/backward-time uniqueness, every raw component change, frame and signed
zero changes, every component NaN/+Inf/-Inf, unsupported-ID normal-admission
fallback, int32-time range exhaustion, five-waypoint/retransmit/retrigger
synthetic sequence. These prove only helper semantics, not actual ROS callback
serialization, first-goal delivery, receiver acceptance, live map projection,
or recovery safety. The following actual producer fixture adds bounded ROS
coverage; combined real-FSM integration and later flight protocol audits remain required.

## Actual producer build and ROS preflight

Runtime changes are exactly the three producer files listed above, mirrored to
`mission_planner_Apps/` and `mission_planner_include/waypoint_mission/`.
Corrected single-job Release/ccache `mission_planner` build passed in 27.5s.
The first invocation's unsupported colcon `--make-args` syntax was rejected
before compilation and is preserved in `build_attempt1.md`.

```sh
source /opt/ros/humble/setup.bash
source /root/super_ws/install/setup.bash
CMAKE_BUILD_PARALLEL_LEVEL=1 MAKEFLAGS=-j1 colcon build --packages-select mission_planner --executor sequential --parallel-workers 1 --allow-overriding mission_planner --cmake-args -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER_LAUNCHER=ccache
ROS_DOMAIN_ID=189 /usr/bin/python3 producer_ros_preflight.py --mode legacy --output ros_legacy_attempt1
ROS_DOMAIN_ID=189 /usr/bin/python3 producer_ros_preflight.py --mode identity --output ros_identity_attempt1
```

Both first attempts passed. The fixture ran the actual installed waypoint
executable with `waypoint.yaml` / `loop24.txt`, fake 100Hz odometry, and unchanged
best-effort volatile QoS. No FSM, GPU, simulator or flight was launched.
Each attempt retained nine exact raw goal messages and monotonic receipt times.

| Actual opt-in stage | Command identity (nanoseconds) | Messages |
|---|---:|---:|
| Initial waypoint | 1789522850381600552 | 3, same ID |
| Same-pose `/goal` retrigger | 1789522852411356758 | 3, fresh ID then unchanged |
| Next waypoint | 1789522854431286550 | 3, fresh ID then unchanged |

Legacy control used a new header stamp for every message, preserving prior
behavior. Within-stage receipt intervals were 1.00938–1.01036s for legacy and
1.00045–1.01001s for opt-in. Raw position/quaternion/frame stayed exact on
retransmission; next-waypoint raw x changed from +24 to -24 as configured.
Actual RCLCPP startup marker and all nine per-publication identity markers were
captured in the opt-in `mission.log`; legacy had no identity marker.

Both exact child process groups were stopped with SIGINT, exited 0 and reaped
(PIDs2958120 and2958593 absent in a subsequent `ps` check). Attempt JSON and
full logs are under the two output directories. No retry was necessary.
This tests producer serialization/identity/publication, not receiver
coalescing or proof that arbitrary external clock changes are safe for flight.

### Launch-style marker capture confirmed

A separate `ros_identity_launchstyle_attempt1` passed the message/marker checks using
`--launch-style`. This launches the actual ROS node with `output='log'`, matching
the benchmark mission's output policy. The captured launch stdout/stderr log
contains the producer settings marker and all nine RCLCPP_INFO identity lines
prefixed `[waypoint_mission-1]`. No launch output configuration change or ROS
log fallback is necessary for this setup. Stable/retrigger/next-waypoint IDs
were respectively 1789522972669776588, 1789522974699626238, and
1789522976729396721; receipt intervals were 1.00045–1.01016s. The launch process
exited 0, but the waypoint child exited -2: group SIGINT reached the node both
directly and through launch forwarding. This cleanup failure was caught on
the manual log audit, after the original JSON's `valid=true` was written by a
too-shallow parent-exit check. The original JSON/log are preserved unchanged;
see `launchstyle_attempt1_audit.md`. No producer or fixture process remained.
The harness now sends SIGINT only to the launch parent and checks child-error
log lines for future runs. No automatic retry was performed. Marker visibility
is established, but this attempt must not be called an entirely clean preflight.
