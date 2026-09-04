# Pre-commit viability guard + CIRI avoidance-zone fix (2026-08-15)

## Scope

This continues directly from `docs/v7_topology_certified_stop_reroute_2026-08-14.md`,
which left `full_guard_reroute_v7` at 1/5 seed6 completion with 1/5 contact, and
concluded the remaining architectural requirement was: "before publishing
motion, every reachable command state must retain a freshness-qualified,
dynamically feasible stop or alternate route" — either a full invariant-backup
policy, or a local speed governor that slows down whenever that contingency
set would be empty.

This note implements the speed-governor option and fixes two bugs found while
validating it. It is still experimental and has not passed a full campaign
gate; see "Current status" below before using any of this as a claim.

## 1. Pre-commit viability / speed-governor guard

Added to `SuperPlanner` (`super_core/super_planner.h`/`.cpp`), gated by new
config `super_planner/guard_viability/*`:

- `certifiedStopExistsFrom(state, ...)`: mirrors the runtime emergency brake
  (`activateEmergencyBrake` in `fsm_ros2.hpp`) — builds a min-jerk stop
  trajectory from a given state, growing duration up to
  `guard_viability_brake_max_duration_s`, and checks it with the same
  `validatePositionTrajectory` the runtime brake uses.
- `candidateStopsViable(pos_traj, ...)`: samples states every
  `guard_viability_sample_dt_s` along a just-generated candidate, out to
  `guard_viability_horizon_s`, and requires a certified stop to exist from
  each sampled state.
- `timeScaleTrajectory(traj, k)`: returns the *same spatial path*, slowed by
  factor `k` (duration `*= k`, coefficient of `t^j` divided by `k^j`). Used
  as the remedy: if a just-generated candidate is not viable,
  `commitTrajectoryCandidate` time-scales the whole candidate (position, yaw,
  and the appended/carried backup time markers) by
  `guard_viability_speed_scale_step` repeatedly, up to
  `guard_viability_speed_scale_max`, re-validating geometric safety at each
  step, before falling back to the existing rejection path.

New profile: `super_planner/config/static_seedmaps_guard_viability_v7.yaml`
(built on `static_seedmaps_guard_reroute_v7.yaml`).

## 2. Bug found and fixed: CLEARANCE_MARGIN, not OCCUPIED

First smoke tests of the guard above showed near-total throughput loss
(average speed ~1.1-1.6 m/s of a 7.0 m/s cruise cap, 0/5 gate passes across
several parameter sweeps of `guard_viability_horizon_s` and the topology
zone's `max_radius_m`). Instrumenting `certifiedStopExistsFrom`
(`TRAJ_GUARD_VIABILITY_STOP_FAIL`, env `VIABILITY_DEBUG=1`) showed ~80% of
stop-viability failures were `CLEARANCE_MARGIN`, not `OCCUPIED`, across
speeds from 2.9 to 6.7 m/s — i.e. not fixed by slowing down.

Root cause: `rog_map`'s `isOccupiedInflate` (used for `CLEARANCE_MARGIN`)
inflates by `inflation_step * inflation_resolution = 3 * 0.1 = 0.3 m` in this
profile, a full 0.1 m more than the true physical `robot_r = 0.2 m` used for
`OCCUPIED`. The independent straight-line brake trajectory routinely grazed
that extra 0.1 m conservative buffer without ever touching a real obstacle.

Fix: `certifiedStopExistsFrom` now accepts a `CLEARANCE_MARGIN` result (not
just `SAFE`) as a viable stop; only true physical contact (`OCCUPIED`) or map
problems (`OUT_OF_MAP`/`MAP_STALE`/etc.) still fail it. Rationale: an
emergency stop is exactly the situation where trading the extra conservative
buffer for having a certified fallback at all is the right call.

A single-run diagnostic after this fix dropped `TRAJ_GUARD_VIABILITY_STOP_FAIL`
occurrences from 21 to 4 (the remaining 4 were pure dynamics infeasibility,
not margin).

**Caveat**: this deliberately narrows the safety margin used specifically for
brake-viability prediction from 0.3 m to 0.2 m. It does not touch the margin
used for normal candidate validation or A*.

## 3. Bug found and fixed: avoidance zones never reached CIRI/MINCO

Even after the fix above, seed6 gates still occasionally deadlocked
completely (e.g. 1/5 waypoints, 120 s timeout). Log inspection of one such
run showed the same `collision_p` recurring 98 times across consecutive
`PlanFromRest` attempts, with the topology-reroute avoidance zone (see the
2026-08-14 doc) already saturated at its configured `max_radius_m`.

Root cause, found by reading `astar.cpp`: the avoidance zones are passed to
`Astar::pointToPointPathSearch` and correctly exclude grid nodes from the
A* search (`topology_excluded` in the neighbor-expansion loop). But they were
never passed to `CorridorGenerator` (CIRI) or the MINCO trajectory optimizer.
A*'s new guide path detours around the zone at the grid level, but CIRI
builds the corridor from raw obstacle points only, and the smooth trajectory
optimized inside that corridor can curve right back through the "excluded"
region — because nothing downstream of A* enforces the exclusion.

Fix, in `corridor_generator.h`/`.cpp`:

- `CorridorGenerator::appendAvoidanceZonePoints(box_min, box_max,
  avoidance_centers, avoidance_radii, pc)`: for each avoidance sphere that
  overlaps the box CIRI is about to search, appends synthetic obstacle-point
  samples on a shell at `radius - robot_r_` from the center (a 16-point ring
  plus two polar points) into the local point cloud `pc`. CIRI then places
  its usual `robot_r_`-based tangent planes against these points the same as
  real obstacles, so the corridor itself also respects the exclusion sphere.
- `SearchPolytopeOnPath`/`GeneratePolytopeFromPoint`/`GeneratePolytopeFromLine`
  gained optional `avoidance_centers`/`avoidance_radii` parameters (default
  empty, so every other call site is unaffected).
- `super_planner.cpp`'s EXP corridor-generation call site now passes
  `guard_topology_avoidance_centers_`/`guard_topology_avoidance_radii_`
  through.

After this fix, the exact-same-point-recurring deadlock pattern was not
observed again in subsequent testing; the one remaining seed6 5-run gate
failure (below) showed constantly-changing rejection points and increasing
generation numbers instead — a slow grind through a difficult region, not a
hard deadlock.

## 4. Results progression (all seed6, `loop24.txt`, v=7, 120 s timeout)

| Variant | Gate (5/5 waypoints + 0 contact, out of 5 runs) | Contact (any run) | Notes |
|---|---:|---:|---|
| `guard_reroute_v7` (2026-08-14, no viability guard) | n/a (step29: 4/5 completion) | 2/5 | prior doc's baseline |
| viability guard, `horizon_s=2.0`, `max_radius_m=3.5` | 0/5 | 0/5 | waypoints 3,3,3,4,3; avg speed 1.34-1.56 m/s |
| viability guard, `horizon_s=2.0`, `max_radius_m=1.0` | 0/5 | 0/5 | waypoints 3,3,2,4,3; avg speed 1.10-1.64 m/s (radius change alone did not move throughput) |
| viability guard, `horizon_s=0.8`, `max_radius_m=1.0` | 0/5 | 0/5 | waypoints 3,3,0,4,2; avg speed 0.15-1.66 m/s (worse) |
| + CLEARANCE_MARGIN fix (§2), `horizon_s=2.0`, `max_radius_m=1.0` | **3/5** | 0/5 | waypoints 5,1,5,4,5; passing runs' avg speed 2.09-2.33 m/s |
| + CIRI avoidance-zone fix (§3), same config | **4/5** | 0/5 | waypoints 1,5,5,5,5; passing runs' avg speed 2.01-2.82 m/s; the exact-point-recurring deadlock pattern did not reappear |

Broader seed1-10 sweep (n=1 per seed, **not a gate**), with both fixes:

| Seed | Waypoints | Collisions | Avg speed | min_clearance |
|---|---:|---:|---:|---:|
| 1 | 5/5 | 0 | 2.55 m/s | 0.361 m |
| 2 | 5/5 | 0 | 2.94 m/s | 0.412 m |
| 3 | 5/5 | 0 | 2.14 m/s | 0.428 m |
| 4 | 5/5 | 0 | 2.13 m/s | 0.366 m |
| 5 | 1/5 | 0 | 0.71 m/s | 0.425 m |
| 6 | 3/5 | 0 | 1.51 m/s | 0.333 m |
| 7 | 2/5 | 0 | 0.95 m/s | 0.360 m |
| 8 | 1/5 | 0 | 0.42 m/s | 0.584 m |
| 9 | 4/5 | 0 | 1.86 m/s | 0.374 m |
| 10 | 2/5 | 0 | 1.06 m/s | 0.360 m |

Before the CIRI avoidance-zone fix, the same seed1-10 sweep (CLEARANCE_MARGIN
fix only) had contact on seed9 (min_clearance 0.006 m) and seed10
(min_clearance 0.172 m). With both fixes, **0/10 seeds showed any contact**,
including seed9/10 — the two tightest maps in the seed1-10 set. This suggests
the earlier seed9/10 contacts were at least partly caused by the unstable
topology-reroute retry cycling (§3), not purely by the CLEARANCE_MARGIN
trade-off (§2).

## 5. Bug found and fixed: symmetric avoidance-ring caused CIRI NaN/Inf deadlocks

The seed1-10 sweep above still had seeds stall for extended periods (e.g.
seed8: 1/5 waypoints, 0.42 m/s average). Log inspection of that specific
seed8 run found `FIRI WARNING: The function value became NaN or Inf`
occurring exactly 136 times, matching exactly 136 consecutive
`SearchPolytopeOnPath for new path failed` messages, all for the same A*
start point — an **84.7-second continuous stall out of a 120 s mission**
(from the first to the last occurrence of that exact start coordinate).

Root cause: `appendAvoidanceZonePoints`'s 16-point ring (§3) is perfectly
rotationally symmetric. For some seed-line geometries this drives CIRI's
ellipsoid-fitting math into a degenerate/singular case, returning NaN/Inf
forever for that specific corridor request, with no way to escape since
nothing about the request changes between retries.

Fix: added a small deterministic per-point radius jitter
(`0.03 * sample_r * sin(7k + 1)`) to break the exact symmetry without
materially changing the intended exclusion radius. A repeat of the same
seed8 scenario after this fix showed 0 NaN/Inf warnings and 0
`SearchPolytopeOnPath` failures — confirmed fixed. Completion was still poor
in that particular verification run (1/5, 0.34 m/s), but for an unrelated
reason (§6); a later fresh seed8 run with identical code got 5/5, 0 contact,
confirming this bug is no longer the blocker it was.

## 6. Why completion rate is poor: three separate causes

Asked to explain the seed1-10 sweep's uneven completion, three distinct
causes were found by instrumenting and reading logs from several stalled
runs:

1. **Chronic MAP_STALE reactive braking (dominant, pre-existing, not fixed
   today).** Every seed's run — completing or not — showed frequent
   `TRAJ_GUARD_BRAKE` events (12-35 per run) triggered by `map_age` sitting
   right at or above `brake_trigger_map_age_s` (0.55 s in this profile), plus
   `TRAJ_GUARD_BRAKE_REJECTED` events (4-107 per run) where even the reactive
   brake failed to certify. Measuring the achieved map-commit rate directly
   from `TRAJ_GUARD_CERT` log lines (max map version / mission duration) gave
   **2.85 Hz average** against `sensing_rate: 10` declared in the drone
   config — consistent with, though somewhat better than, the ~1.8 Hz Codex
   measured on 2026-08-14. The `map_age` distribution is bursty, not
   uniformly slow: median 0.018 s (very fresh most of the time) but p90
   0.558 s and max 3.067 s — a long tail of multi-second stalls. This is the
   same issue `docs/loop_guard_snapshot_recovery_steps_6_to_22_2026-08-14.md`
   already flagged and did not resolve; it is not something today's fixes
   touched.

   **2026-08-15 correction:** the "map commits and planning share a
   callback group" explanation above (and in §7's conclusion) is **wrong
   for the current code** and should not be cited further. Verified two
   independent mechanisms that already rule this out:
   - `fsm_ros2.hpp` constructs distinct `MutuallyExclusive` callback groups
     for the FSM timer, replan timer, command publisher, goal callback, and
     the map (`map_cbk_group_` is passed into `ROGMapROS` separately from
     `exec_cbk_group_`/`replan_cbk_group_`/`cmd_cbk_group_`), and
     `Apps/fsm_node_ros2.cpp:97` runs an 8-thread `MultiThreadedExecutor` —
     Codex's 2026-08-14 Step 1 work, already merged, already in the commit
     history at the point today's guard code was built on.
   - For every rog_map config used in today's tests (`map_sliding.enable:
     false`, `raycasting.enable: false`, `unk_inflation_en: false`),
     `rog_map.cpp:32-34` evaluates `immutable_snapshot_enabled_ = true`.
     Under that flag `acquireMapReadTransaction()`
     (`rog_map.h:213-231`) returns an *empty* transaction — planner reads
     take **no lock at all** and can never block on, or be blocked by, a
     map commit. This is a stronger guarantee than callback-group
     separation and is already active.

   Moreover `fsm.cpp:307-312` defines `map_age_s` (the value that trips
   `MAP_STALE`) as `now - health.latest_scan_process_time` whenever the
   immutable snapshot is active — i.e. time since a scan was last
   *processed*, not time spent waiting on any lock. A 3 s `map_age` burst
   therefore means no scan was processed for 3 s, which is upstream of
   ROG-map's locking/scheduling entirely.

   Traced one call further upstream: `perfect_drone_sim`'s `publishPC()`
   (`ros2_perfect_drone_model.hpp:163-173`, the sim's own wall-timer
   callback) calls `renderOnceInWorld` → `render_pointcloud`
   (`marsim_render.cpp`), a synchronous OpenGL depth-render per frame
   (`glClear` → draw → `glfwSwapBuffers` → `glReadPixels` readback) on a
   single thread, with no batching or double-buffering across calls. A
   real NVIDIA GPU is present in this environment (confirmed via
   `nvidia-smi`/`glxinfo`, RTX 3050 Ti Laptop, not software/llvmpipe
   rendering), so this is plausible as the source of frame-to-frame
   burstiness rather than a GPU-availability problem. This is also
   consistent with §7's already-rejected `sensing_rate: 3` experiment:
   lowering the requested rate made throughput worse, which fits a
   per-call-cost-dominated bottleneck (each call still pays the same
   synchronous render+readback cost, just less often) rather than a
   starvation/contention bottleneck (which a lower requested rate would
   have relieved). Not yet instrumented with per-call timing to confirm
   directly — this is the next concrete step if cause 1 is pursued
   further, and it points at `mars_uav_sim` (the simulator), not at
   `super_planner`/`rog_map`.
2. **The NaN/Inf CIRI degeneracy (§5).** Found and fixed today.
3. **Occasional topology-reroute-zone insufficiency.** One seed6 run and one
   seed8 run showed the exact-collision-point-recurring deadlock pattern
   (§3/§4) even after the CIRI avoidance-zone fix, with the zone already at
   its configured `max_radius_m`. Re-running the identical seed8 scenario
   with `AVOIDANCE_DEBUG=1` logging showed the injection mechanism firing
   correctly (107 successful injections, geometrically consistent placement)
   and, on that specific re-run, no deadlock at all (5/5, 0 contact) — the
   failure could not be reproduced on demand. This looks less like a
   software bug than an inherent limitation of routing around a single fixed
   sphere: a small local exclusion zone is not guaranteed to have an escape
   route in every possible surrounding obstacle configuration.

## 7. Tried and rejected: lowering the declared sensing_rate

Given cause 1 above, tested whether declaring a lower, more "honest"
`sensing_rate` (drone config, `mars_uav_sim/perfect_drone_sim`) would let the
simulator actually keep up, on the theory that requesting an unsustainable
10 Hz might itself be causing overload. Tried `sensing_rate: 10 -> 3` for
seed8 only (`seed8_slowsense.yaml`, not the shared `seed8.yaml`).

Result: **clearly worse, not better.**

| | `sensing_rate=10` (baseline) | `sensing_rate=3` |
|---|---:|---:|
| Achieved map-commit rate | 2.85 Hz | **0.82 Hz** |
| `map_age` median | 0.018 s | **0.551 s** |
| `map_age` p90 | 0.558 s | 0.918 s |
| `map_age` max | 3.067 s | **5.814 s** |
| `TRAJ_GUARD_BRAKE` count | ~12 | 34 |

Working hypothesis: the LiDAR simulator likely renders/publishes a point
cloud sized to however much time has elapsed since the last publish, so a
lower declared rate means each call does proportionally more work, not less
— concentrating cost into larger, less frequent, more blocking bursts rather
than reducing total work. `seed8_slowsense.yaml` is kept only as a record of
this negative result; `seed8.yaml` itself was never modified and the
`sensing_rate: 10` default remains in use everywhere else.

This means cause 1 is not fixable by simply retuning the publish rate.
**2026-08-15 correction:** it is also not a callback-group/scheduling
problem — see the correction note under §6 item 1. The map-write/planning
separation this paragraph used to point at was already implemented by
2026-08-14 and verified still in place; the render/readback cost inside
`perfect_drone_sim`'s own publish timer is the current leading suspect and
has not yet been fixed or even directly timed.

## 8. 2026-08-17/18: executor threading fix, unknown-space tracking, and the real completion bottleneck

Picked back up from §6 item 1's "render/readback cost inside
`perfect_drone_sim`'s own publish timer" lead.

### 8.1 Root cause of cause 1: perfect_drone_sim's own executor, not rendering cost

`ros2_perfect_drone_node.cpp`'s `main()` called `rclcpp::spin(node)` --
the default **single-threaded** executor. The node splits cmd/odom/
global_pc/local_pc into separate `MutuallyExclusive` callback groups (as
if for a multi-threaded executor), but a single-threaded spin serializes
all of them onto one thread anyway. `odom_pub_timer_` fires at 100 Hz and
`global_pc_pub_timer_` at **1000 Hz** (mostly a no-op body, but still a
scheduler turn every time); both were starving `local_pc_pub_timer_`
(`publishPC()`, the actual LiDAR render+publish), which is why the
achieved point-cloud rate never matched the declared `sensing_rate` and
why lowering it (§7) made things worse, not better -- the bottleneck was
executor contention, not per-call render cost.

Fix: split the node across two executors instead of one. cmd/odom/
global_pc run on a 3-thread `MultiThreadedExecutor` on a side thread;
`local_pc_pub_cbk_group_` (the renderer) keeps the main thread to itself
via a dedicated `SingleThreadedExecutor`, spun after starting the side
thread. This was necessary, not just a nice-to-have: the renderer's
GLFW/OpenGL context is only valid on the thread that created it, so it
can't simply move to the shared pool -- the first attempt (give
`local_pc_pub_cbk_group_` to the shared `MultiThreadedExecutor` too)
produced `"OpenGL context is not current."` on essentially every render
call and froze the mission entirely (0 progress for the full timeout).
`marsim_render.cpp`'s `render_pointcloud()` also gained a defensive
`glfwMakeContextCurrent(window)` at its top, documenting the invariant
even though the dedicated-thread fix is what actually makes it hold.

Single-run result on this fix alone (seed6, before any of the changes
below): 5/5 waypoints, 0 contact, `map_age` p90 0.558s -> 0.198s, max
3.067s -> 1.979s, 0 OpenGL errors (vs. 13123 with the broken variant).

### 8.2 rog_map has no way to represent "confirmed empty" in this profile

Separately, re-examined the seed9 sweep's one real contact (not from
today's fixes -- inherited from before): a certified emergency brake made
contact mid-execution (`trajectory_flag=3`), `min_clearance_m` down to
0.003-0.2 m, `path_status=SAFE` at certification time. Root cause: this
profile's `raycasting.enable: false` (a **pre-existing, deliberate**
choice already present in the base `static_seedmaps.yaml`, predating this
whole guard investigation -- see that file's own comment: "if disable,
the map will only maintain occupied information, and all other grid will
be considered as unknown"). With raycasting off, `rog_map`'s immutable
snapshot only ever tracks *occupied* cells; `isUnknownInflate()` was
hardcoded to always return `false` and `isKnownFree()` to always return
`false` too. There is no way to distinguish "swept and confirmed clear"
from "never looked at" -- both read as "not occupied" -- so the guard
could certify a stop through space nobody had actually observed.

Fix, scoped narrowly: added a `known_pages` bit to the raw-resolution
snapshot grid (`rog_map.h`'s `SnapshotGrid`), populated in
`publishCommittedSnapshot` from whether each dirty cell's probability has
left the unknown band. A single LiDAR return only marks a thin ray-line
of cells, so `prob_map.cpp`'s `raycastProcess()` (`!raycasting_en`
branch) now also does a short backward ray-march from each accepted hit
point (bounded by the new `observed_mark_range_max`, default 10 m, kept
separate from `raycast_range_max` so this doesn't scale with full sensor
range) marking traversed cells as observed-free via the existing
`missPointUpdate` pipeline -- no new probabilistic machinery, just
feeding it more geometry. `ROGMap::isUnknown()` reads `known_pages` with
a small (3-cell, 0.15 m) neighbor tolerance to bridge gaps between
individual sparse ray lines at raw (0.05 m) resolution.

A new `TrajectorySafetyStatus::UNOBSERVED` (distinct from
`CLEARANCE_MARGIN`, which stays reserved for a real nearby obstacle) is
produced when `validatePositionTrajectory`'s new `unknown_as_occupied`
parameter is true and a sampled point is unknown; it's a hard rejection
with no escape allowed (unlike `CLEARANCE_MARGIN`, which does get an
escape window). Wired to **`true` only for the brake candidate** in
`activateEmergencyBrake` (`fsm_ros2.hpp`) via
`fsm/trajectory_guard/unknown_as_occupied` (default `false`); normal
EXP/backup candidates keep `false`, since they must be allowed to plan
into never-yet-observed space -- that's inherent to exploring with a live
sensor. First tried applying it everywhere: caused total liveness loss,
since the area around the spawn point is almost entirely unobserved at
t=0.

**Causally verified, not just correlated:** re-ran seed9 five times with
`unknown_as_occupied` forced back to `false` (executor fix from 8.1 kept
active) -- run 2 reproduced a contact (`min_clearance_m=0.199`,
`trajectory_flag=3`, `path_status=SAFE`, all four brake conditions
including path_status showed `SAFE` for every one of that run's brakes).
With the flag on, 0 contact across that same isolation test and every
other run today. The executor fix alone was necessary but not
sufficient; `UNOBSERVED` is the specific mechanism that closes this gap.

### 8.3 Two plausible-sounding follow-on ideas, both net negative -- reverted

1. **Widen the neighbor tolerance further** (radius 3 -> 6 cells, both at
   read time in `isUnknown()` and, in a second attempt, moved to write
   time as a splat in `publishCommittedSnapshot` from each newly-free
   dirty cell). Both regressed the seed1-10 sweep (radius-6 read: far
   more brake attempts/rejections and worse `map_age` for the same
   21/25 gate result; write-side splat radius 6 and then 3: 41-37/50 vs
   the working config's 41-42/50, with 3-5x more brake churn). The
   per-check neighbor search competes with scan-processing thread time;
   the write-side splat scatters writes across many 32 KB snapshot pages
   that get copy-on-write'd in full, and the vehicle keeps generating
   newly-free dirty cells throughout a mission, not just at start, so
   the cost never amortizes down. Reverted to the plain 3-cell read-time
   search, which remains the best of the variants tried.
2. **Arm a topology-avoidance zone from a brake's `UNOBSERVED` failure
   point too** (mirroring the existing mechanism that arms one from a
   rejected, stopped `PlanFromRest` candidate). Refactored the existing
   logic into `SuperPlanner::armTopologyAvoidanceZone()` and called it
   from `activateEmergencyBrake`'s failure path, speed-gated the same way
   the original call site is. Net negative on the seed1-10 sweep (34/50
   vs. baseline 41-42/50; two previously-reliable seeds dropped to 1-2/5).
   Reason: a rejected *stopped* candidate's collision point is a stable,
   meaningful obstacle location, but a *moving* vehicle's failed-brake
   collision point is just wherever it happened to be, projected forward
   along its current heading -- arming zones from it walls off the
   vehicle's own flight path, not a real obstacle. Reverted the call
   site; kept the harmless refactor (the original candidate-rejection
   call site behaves identically through the extracted method).

### 8.4 Tried to match the SUPER paper's actual backup-trajectory mechanism, three times, all reverted

Traced through `misc/scirobotics.ado6187.pdf` (the actual SUPER paper) to
see how it establishes the backup trajectory's known-free guarantee
without raycasting: not a raw occupancy grid at all, but Theorem 1
(Supplementary Methods) -- a convex polytope built by CIRI, seeded on a
line from the current position to the furthest point visible along the
exploratory trajectory, that excludes every point in a "sufficiently
dense" input point cloud is known-free by construction. To make single
scans dense enough, the paper explicitly accumulates 1-2 s of recent
LIDAR scans as CIRI's input, rather than reading from a committed map.

Three attempts to actually build this for `activateEmergencyBrake`, each
worse than the last:

1. Reused the existing map-backed `CorridorGenerator::GeneratePolytopeFromLine`
   (a shortcut -- read from `map_ptr_->boxSearch`, not from accumulated
   raw scans, despite the paper specifically calling out map-commit
   staleness as the problem raycasting-free methods have to solve).
   Result: **an actual collision** on seed9 (`min_clearance_m=0.112`,
   inside a brake certified `path_status=SAFE` by *both* the grid check
   and this new corridor check) -- the map source has the same
   commit-lag gap as the original raw-grid approach, so this added a
   second, differently-shaped way to hit the identical bug it was
   supposed to fix.
2. Built a proper ~1-2 s raw-scan accumulator (`fsm_ros2.hpp`'s
   `raw_cloud_window_`/`getAccumulatedRawCloud()`, reusing the existing
   but previously-disabled `guard_cloud_sub_` raw-cloud subscription) and
   a new `CorridorGenerator::GeneratePolytopeFromLineAndCloud()` that
   takes an external point cloud instead of querying the map. First
   version treated an empty point cloud within the search box as
   *failure* (reasoning: a sparse point list, unlike a map, can't
   distinguish "confirmed empty" from "never observed"). Result: **17/50
   waypoints** (near-total liveness collapse) and a collision *still* got
   through elsewhere in the same sweep -- wrong, because LiDAR only
   returns points where a beam hits a surface, so genuinely open air is
   *also* empty of points in any small box. There's no "this space is
   empty" observation a raw point list can record, unlike an occupancy
   grid; treating sparse-by-geometry the same as unswept broke normal
   flight almost everywhere.
3. Reverted just the empty-cloud handling back to "empty = open box"
   (matching the map-backed version's semantics), keeping the raw-scan
   accumulator. Result: **12/50 waypoints**, worse still, and the new
   `guard_cloud_sub_` subscription's sequence counter stayed at 0 for the
   entire mission in the logs checked -- it never received a single
   message despite reusing the map's own topic and QoS pattern -- while
   separately the map's own commits also froze for 8+ seconds during
   dense replan-retry activity. Root cause of either symptom not found.

All of 8.4 was reverted in full: `SuperPlanner::buildEmergencyStopPolytope()`,
`SuperPlanner::cg_brake_ptr_`, `CorridorGenerator::GeneratePolytopeFromLineAndCloud()`,
and `fsm_ros2.hpp`'s raw-scan accumulator are gone; `activateEmergencyBrake`
is back to the 8.2 `unknown_as_occupied` grid check;
`fsm/trajectory_guard/raw_cloud/enable` is back to `false`. Revert verified
against a fresh seed1-10 sweep (38/50, 0 contact -- consistent with the
8.2 baseline's known run-to-run range).

**This direction is not closed, just not worth re-attempting live without
more isolation.** If revisited: instrument *why* `guard_cloud_sub_` saw
zero messages before touching anything else, and consider testing the
raw-scan accumulator completely independently of the CIRI corridor change
(e.g. just log accumulated-cloud size over time) before wiring it into
anything safety-critical.

### 8.5 The actual dominant completion bottleneck: EMER_STOP unconditionally discards the goal

Asked to explain *why* seed9 stayed stuck instead of assuming an
unverified "occlusion" theory from collision-point coordinates alone
(they turned out to be a red herring -- see below). Properly re-examined
by cross-referencing `TRAJ_GUARD_REJECT`/`TRAJ_GUARD_COMMIT` line-by-line
instead of grepping rejections in isolation, and by counting brake
outcomes and FSM state samples directly:

- The seed9 `CLEARANCE_MARGIN` rejections that looked clustered at one
  coordinate (misread earlier as "same wall, occlusion, needs a new
  vantage point") in fact each resolved within 1-2 retries via the
  existing topology-reroute mechanism working as designed -- only 17
  `TRAJ_GUARD_REJECT`s and 13 `TRAJ_GUARD_REROUTE_ARM`s in the whole 120 s
  run, with long normal-flight stretches (8+ consecutive successful
  commits, 8+ seconds) in between. Not the bottleneck.
- The real number: **98 `TRAJ_GUARD_BRAKE_REJECTED`** in that same run
  (61 `MAP_STALE`, 37 `UNOBSERVED`), each entering `EMER_STOP`. Sampling
  `Fsm::callMainFsmOnce()`'s periodic state print (105 one-second
  samples) gave `WAIT_GOAL` 63 (60%), `GENERATE_TRAJ` 16 (15%),
  `FOLLOW_TRAJ` 20 (19%), `EMER_STOP` 6 (6%) -- the vehicle spent most of
  the mission simply idle, not flying.
- `Fsm::callMainFsmOnce()`'s `EMER_STOP` case (`fsm.cpp`) was
  unconditional: `ChangeState("MainFsmCallback", WAIT_GOAL); break;` --
  discarding `gi_.goal_p`/`gi_.goal_yaw` (still valid; nothing had
  cleared them) and falling back to `WAIT_GOAL`, which only resumes once
  `mission_planner` re-enqueues a goal. `mission_planner`'s
  `GoalPubTimerCallback()` only republishes the *unchanged* current
  waypoint once per `waypoint.yaml`'s `publish_dt` (1.0 s) unless the
  waypoint itself switches. So every one of those 98 failures paid up to
  ~1 s waiting on an external 1 Hz timer for information the FSM already
  had, instead of retrying at its own ~15 Hz replan rate.

Fix: `case EMER_STOP` now checks `started_`; if true, sets
`gi_.new_goal = true` and transitions straight to `GENERATE_TRAJ` with
the already-known goal, instead of bouncing through `WAIT_GOAL`. If the
goal was already reached, `GENERATE_TRAJ`'s existing `closeToGoal(0.1)`
check sends it back to `WAIT_GOAL` immediately anyway, so no separate
case is needed for that.

Result on seed9 (single run): `WAIT_GOAL` samples 63 -> **0**;
`FOLLOW_TRAJ` 20 -> 45 (19% -> 53% of ticks); completion 1/5 -> 3/5, 0
contact. **Seed1-10 sweep (n=1 each): 48/50 waypoints, 0/10 contact** --
9 of 10 seeds at a clean 5/5. Only seed7 (3/5) fell short; not yet
investigated separately. This is a large jump from every other
configuration tried today or in the preceding two days (best prior:
seed6 5-run gate 4/5; various seed1-10 n=1 sweeps in the 33-42/50 range).

### 8.6 Correction: the seed9 "occlusion" theory was wrong, twice over

Worth recording precisely, since it was asserted fairly confidently
before being checked:

- First claim: "the vehicle sits at a fixed vantage point and a rotation
  would reveal more of the scene." Checked `seed9.yaml`/`marsim_render`
  config: `is_360lidar: true`, `vertical_fov: 178`, `lidar_type: 2`
  (`GENERAL_360`) -- this sensor already samples the full horizontal
  360° every single scan call, so rotation cannot reveal anything new.
  The claim was made without checking the sensor's actual FOV config
  first.
- Second, revised claim (after being pushed on the first): "genuine
  line-of-sight occlusion, unresolvable without translating to a new
  position, since 26 map commits passed without the collision-point
  coordinates changing." This was still wrong, for a more basic reason:
  the recurring collision-point coordinates were `TRAJ_GUARD_REJECT`
  (candidate) rejections, which -- as 8.5 shows -- were resolving
  normally within 1-2 retries the whole time; `TRAJ_GUARD_COMMIT` lines
  interspersed between them were never checked. The actual dominant
  failure (`TRAJ_GUARD_BRAKE_REJECTED`, 98 occurrences) was a completely
  different log line that had already been found and quantified in an
  earlier pass of this same session, then not connected to the
  `WAIT_GOAL` question when re-investigating.

### 8.7 2026-08-19: seed7's 3/5 diagnosed -- a razor-thin corridor pinch, not a new bug class

Diagnosed by cross-referencing `sweep_emerfix/seed7.launch.log` against
`scripts/native_campaign/seed7_static.csv` (the seed's raw obstacle list).
This is a pure liveness/completion failure, not a safety regression:
`min_clearance_m=0.441` for the whole run, 0 contact.

- seed7 reached wp1/wp2/wp3 normally (`waypoints_reached` in the monitor
  JSON only increments when odom actually comes within `switch_dist` of a
  waypoint, so this is not in doubt). En route from wp3(-24,-24) to
  wp4(24,-24), at t~58s it braked to `CLEARANCE_MARGIN` at
  `(-16.434, -22.203)` and never moved again: `final_x/final_y` in
  `seed7.json` match this point exactly, and the log's last
  `TRAJ_GUARD_REJECT` line at t=120.0s still shows the same replan
  generation, `gen=252`, that first appeared at t~58s -- 65 seconds, ~98
  `PlanFromRest` attempts, and it never advanced to `gen=253`.
- The geometric cause is directly confirmable from `seed7_static.csv`: the
  stop point sits almost exactly between two obstacles at
  `(-15.642,-21.552) r=0.525` and `(-17.013,-23.082) r=0.525`, whose
  surface-to-surface gap is **1.004 m** -- essentially the v6 map design's
  guaranteed *minimum* gap (1.00 m) everywhere on the field, i.e. the
  single tightest passage seed7 has. The guard needs
  `robot_r(0.2) + hard_clearance(0.3) = 0.5 m` clearance on each side, so a
  1.004 m gap leaves ~4 mm of slack -- in practice zero, since each
  `PlanFromRest` retry's candidate corridor jitters sub-centimeter
  (confirmed from the `collision_p` values across the 98 rejects) and
  essentially never lands dead-center.
- **This exact failure mode is not unique to seed7.** seed3's log shows an
  even longer run of identical-generation `CLEARANCE_MARGIN` rejects at a
  single point (110 straight rejects, ~10.4 s) at a different pinch, and
  seed3 still finished 5/5 -- it broke free once a fresh map update shifted
  the local occupancy enough to let one retry through (the very next
  `TRAJ_GUARD_CERT` after that streak reports `MAP_STALE`, i.e. new data
  had just arrived). The topology-reroute zone (`armTopologyAvoidanceZone`,
  radius capped at `max_radius_m=1.0`) re-armed the same zone every retry
  in both cases but did not by itself change the outcome -- it is too small
  to enclose *both* flanking obstacles of a two-obstacle pinch (recall
  8-14's finding that widening it to 3.5 m was net-negative elsewhere), so
  A* keeps re-deriving the same razor-thin topology as "shortest."
- **Conclusion: whether a same-generation retry deadlock resolves before
  the mission timeout is effectively stochastic**, not something the
  current recovery mechanism guarantees. seed7 landed on the field's single
  tightest gap on its direct route and the loop didn't break in time;
  seed3 hit a similar deadlock elsewhere and got lucky. This is a real,
  distinct gap in the topology-reroute design (separate from 8.5's
  EMER_STOP fix and 8.2's UNOBSERVED fix) -- not yet fixed. A natural next
  step would be detecting a stalled generation (same `gen` across N
  consecutive `PlanFromRest` rejects, or elapsed stall time past a
  threshold) and escalating -- e.g. temporarily accepting a `CLEARANCE_MARGIN`
  *moving* candidate the way `certifiedStopExistsFrom()` already accepts
  one for a certified *stop* -- rather than retrying the identical corridor
  indefinitely. Not attempted yet; flagging for a future session.

### 8.8 2026-08-19: seed1-10 x n=10 (100 runs) -- the n=1 headline was optimistic, but 0 contact holds at scale

Ran the full seed1-10 sweep at n=10 per seed (100 runs total, same
`static_seedmaps_guard_viability_tight_v7.yaml`, `loop24.txt`,
`switch_dist=1.5`, `timeout=120.0s` as every prior sweep) to get a real
distribution instead of one sample per seed. Raw JSON/logs are in
`sweep_emerfix_n10/` (not committed -- see note below).

| seed | 5/5 runs | waypoints | contact | worst min_clearance_m |
|-----:|:--------:|:---------:|:-------:|:----------------------:|
| 1  | 10/10 | 50/50 | 0 | 0.365 |
| 2  | 10/10 | 50/50 | 0 | 0.409 |
| 3  |  9/10 | 49/50 | 0 | 0.369 |
| 4  | 10/10 | 50/50 | 0 | 0.357 |
| 5  |  9/10 | 47/50 | 0 | 0.348 |
| 6  |  8/10 | 48/50 | 0 | 0.372 |
| 7  |  4/10 | 43/50 | 0 | 0.326 |
| 8  |  8/10 | 43/50 | 0 | 0.323 |
| 9  |  3/10 | 40/50 | 0 | 0.306 |
| 10 |  3/10 | 37/50 | 0 | 0.327 |
| **total** | **74/100** | **457/500 (91.4%)** | **0/100** | 0.306 |

Two things this settles:

- **Safety holds up at scale.** 0/100 contact, worst-case clearance
  0.306 m (still a healthy margin, no near-miss tighter than that across
  100 independent runs). The 8.2/8.5 fixes are not fragile to sample size.
- **The n=1 headline (48/50, 9/10 seeds clean) was an optimistic single
  draw, not the true rate.** At n=10 the true full-completion rate is
  74/100 runs, and it is very uneven across seeds: 1-4 are solid (9-10/10),
  but 7/9/10 fail more often than they succeed (3-4/10). Do not cite the
  48/50 number as representative going forward -- use this table.

To check whether 8.7's diagnosis (a `PlanFromRest` same-generation retry
deadlock) generalizes beyond seed7's one run, every failed run's log was
scanned for the longest run of consecutive identical-`gen`
`CLEARANCE_MARGIN` rejects under `phase=PlanFromRest`:

| | max same-gen streak (consecutive rejects) | total `PlanFromRest` rejects |
|---|:---:|:---:|
| successful runs (n=74) | median 2, mean 4.8, max 116 | median 14, mean 22.0, max 138 |
| failed runs (n=26) | median 4, mean 25.5, max 273 | median 59, mean 73.4, max 296 |

Failed runs have ~4x the median `PlanFromRest`-reject volume of successful
ones and a much heavier tail on worst-case streak length, but the
distributions overlap substantially (one successful run survived a
116-long streak and 138 total rejects and still finished before the
timeout). This confirms 8.7's framing rather than replacing it: **the same
retry-deadlock mechanism drives essentially all of these failures, not
just seed7's**, and whether a given run finishes in time is a race between
that mechanism eventually re-finding a passable corridor (usually via a
map update shifting the local geometry, per 8.7) and the 120 s timeout --
not something the current recovery guarantees. seed7/9/10's higher failure
rate most likely reflects those seeds' specific obstacle layouts putting
more near-design-floor (1.0 m) pinches on the direct loop route, not a
seed-specific bug.

This raises the priority of 8.7's proposed next step (detect a stalled
generation and escalate -- e.g. accept a `CLEARANCE_MARGIN` *moving*
`PlanFromRest` candidate after N consecutive same-gen rejects, mirroring
what `certifiedStopExistsFrom()` already does for a certified *stop*)
from "flag for later" to "the next thing worth trying," since this is now
confirmed as a frequent (26/100), not rare, failure mode. Still not
attempted as of this writing.

Note: `sweep_emerfix_n10/`'s ~100 launch logs (tens of MB) were not copied
into this repo -- the aggregate numbers and the streak/reject-count
analysis above are the durable record. Reproduce with a 10x loop over the
existing `run_sweep_emerfix.sh` pattern if the raw logs are needed again.

### 8.9 2026-08-19: guard-corridor retry de-stickying -- one wrong attempt, one that helped

Went after 8.8's proposed next step by reading `commitTrajectoryCandidate`
and `GenerateExpTrajectory` closely instead of guessing. Two corrections to
8.8's own framing came out of that reading, worth recording plainly since
they contradict what was said at the time:

- **The 1.004 m seed7 gap is not actually tight.** Re-deriving the guard's
  clearance math from `super_planner.cpp:67-92` (not from the earlier,
  wrong, from-memory `robot_r+hard_clearance=0.5m` claim in 8.7): with
  `additional_clearance_m=0`, `trajectory_guard_clearance_offsets_` is
  *empty*, so `CLEARANCE_MARGIN` is triggered by `isOccupiedInflate` alone
  -- a flat 0.3 m band from the raw surface, not 0.5 m. A clean pass through
  a two-obstacle pinch needs only a 0.6 m total gap, not 1.0 m. seed7's
  1.004 m gap has ~0.2 m of lateral slack on each side that was never being
  used -- this was a placement/strategy problem, not a genuine geometric
  squeeze. 8.7's diagnosis of *what* was happening (a stuck same-generation
  retry loop) stands; its explanation of *why the gap itself was hard*
  does not, and should not be re-cited.
- **The real mechanism: once `guard_corridor_retry_pending_` is set (on
  the first `CLEARANCE_MARGIN` reject), it stays set until a candidate
  finally commits, and every corridor search in between permanently uses
  `cg_guard_retry_ptr_` (inflated obstacles, ~0.005 m CIRI margin) instead
  of the normal `cg_ptr_` (raw obstacles, 0.2/0.3 m margin). The guide path
  feeding both is identical (a single upstream A* search), so once locked
  into retry mode the system reproduces nearly the same corridor every
  attempt -- explaining why 65-second, 98-attempt streaks (8.7) converged
  on the same collision point instead of exploring anything different.

**First attempt (reverted): also widen the retry corridor's own margin**
from `0.1x resolution` (0.005 m, smaller than one voxel at this map's
0.05 m resolution) to `2x resolution` (0.10 m), reasoning that 0.005 m left
no slack over CIRI's known margin non-uniformity (documented back in the
2026-08-13 audit, `docs/연구일지.md`). Wrong: `cg_guard_retry_ptr_` exists
specifically to find *some* corridor in a spot already too tight for the
normal generator, and demanding a bigger margin from it just makes it more
often find none. Confirmed directly: `SearchPolytopeOnPath for new path
failed` went from 11,033 occurrences across the 8.8 100-run baseline to
139,478 across just 45 runs of a seed1-10 x n=5 sweep with this change
(~28x more per run) -- and completion cratered to 14/45 (31%) before the
sweep was stopped early. Reverted the margin back to 0.005 m; kept the
second change below, which does not touch this margin at all.

**Kept: de-stickying the retry-mode lock.** Added
`guard_corridor_retry_attempts_` (reset whenever
`guard_corridor_retry_pending_` clears on a successful commit) and a new
`guard_corridor_retry_alternate_every` config (default 4): every Nth
consecutive retry-mode corridor search now falls back to the normal
generator instead, so a stall is no longer permanently locked into one
corridor-generation strategy for its whole duration. This never changes
what the guard accepts -- `validatePositionTrajectory` checks whichever
candidate comes out exactly the same way either way, so the change is
safety-neutral by construction. `guard_corridor_retry_alternate_every: 4`
set in `static_seedmaps_guard_viability_tight_v7.yaml`.

Reran the same seed1-10 sweep at n=5 (50 runs) after reverting the margin:

| | 8.8 baseline (n=10, 100 runs) | 8.9 with alternation (n=5, 50 runs) |
|---|:---:|:---:|
| full completion | 74/100 (74.0%) | 41/50 (82.0%) |
| waypoints | 457/500 (91.4%) | 227/250 (90.8%) |
| contact | 0/100 | 0/50 |
| worst clearance | 0.306 m | 0.304 m |

Per-seed, the three worst seeds from 8.8 each moved in the right direction
(seed7 4/10->3/5, seed9 3/10->3/5, seed10 3/10->2/5 -- i.e. 40%/30%/30% ->
60%/60%/40%), though at n=5-10 per seed none of these individual deltas are
individually conclusive. **The aggregate 74%->82% run-level improvement is
not statistically significant at this sample size** (two-sided Fisher exact
on 74/100 vs 41/50: p=0.31) -- do not cite it as a proven fix, only as a
promising, directionally-consistent result.

What *is* solid evidence the mechanism is working as intended: the
catastrophic single-stall deadlocks are gone. The longest same-generation
`PlanFromRest` reject streak among all 50 new runs (success and failure
combined) was 112; the 8.8 baseline had streaks of 116, 138, 273 and six
separate failed runs with a streak >=20. Failed-run median
`PlanFromRest`-reject volume also dropped (59 -> 40). The multi-hundred-
attempt, single-location deadlocks that motivated this whole line of
investigation (seed7's original 98-attempt/65 s stall, 8.8's worst case at
273) did not recur in this sweep. Contact remains 0 across every run of
this fix, on top of the already-clean 8.2/8.5/8.8 record.

**Conclusion: keep the alternation change (safety-neutral, mechanistically
validated, plausibly helping), do not claim the completion-rate improvement
is proven, and do not re-attempt widening `cg_guard_retry_ptr_`'s own
margin** without first checking `SearchPolytopeOnPath` failure counts the
way this attempt should have from the start. A larger sweep (n=20-30 per
seed) would be needed to actually confirm or reject the 74%->82% delta.

### 8.10 2026-08-19: a 4th paper-reproduction attempt, shadow-only this time -- real progress, real remaining blocker

User directly instructed a 4th attempt at the paper's actual backup-
trajectory mechanism (theorem 1, accumulated raw-scan CIRI) after the three
in 8.4 all regressed live behavior. This time it was built and tested
**shadow-only**: the accumulated-cloud CIRI check is computed and logged
(`ciri_shadow=SAFE|UNSAFE|INSUFFICIENT_DATA|DISABLED` in the
`TRAJ_GUARD_BRAKE`/`TRAJ_GUARD_BRAKE_REJECTED` lines) but its result is
never read by any accept/reject branch, so it cannot change flight
behavior by construction -- the goal was to actually get comparison data
against the live grid-based check without repeating 8.4's pattern of
finding out live that something was wrong.

**Before writing any code**, re-read `misc/scirobotics.ado6187.pdf`
directly (not from memory) to re-verify the mechanism. Two corrections to
earlier (this session's own, and 8.4's) understanding came out of that:

- The exact quote (Materials and Methods, "Backup corridor generation"):
  theorem 1 states a CIRI-extracted polyhedron is known-free "if the input
  point cloud makes a **sufficiently dense** depth image," and "we
  accumulate recent LIDAR scans (**for example, 1 to 2 s**) and input them
  to CIRI." The "1-2s" figure cited throughout this project is accurate,
  not a misremembering.
- A previously-unimplemented detail: Fig. 8C(iii) shows the backup
  corridor is *also* cut by the current LIDAR FOV, not just bounded by the
  accumulated cloud. None of the four attempts (8.4's three, or this one)
  implement this FOV cut. Flagging as a known fidelity gap, not attempted.

**New code, all shadow-scoped:**
- `corridor_generator.{h,cpp}`: `GeneratePolytopeFromLineAndCloud(Line&,
  const vec_Vec3f&, Polytope&)` -- mirrors `GeneratePolytopeFromLine`
  exactly except the point cloud comes from an external cloud instead of
  `map_ptr_->boxSearch`. An empty local box is treated as open space
  (matching the map-backed convention), which is only a sound reading of
  theorem 1 if the caller already verified "sufficiently dense" upstream.
- `super_planner.{h,cpp}`: new `cg_brake_ptr_` (separate `CorridorGenerator`
  instance -- deliberately not a reuse of `cg_ptr_`, to avoid sharing
  mutable CIRI state between the emergency-brake callback group and
  whatever thread runs normal replanning) and
  `checkKnownFreeViaCloud(seed_near, seed_far, cloud, candidate,
  checked_from_tt, &violation_pos)`, which builds the polytope and checks
  every sample of `candidate` against `Polytope::PointIsInside`.
- `fsm_ros2.hpp`: `raw_cloud_window_` (a pruned `deque` of timestamped
  point-cloud batches, populated alongside the existing single-snapshot
  `raw_cloud_snapshot_` in `guardCloudCallback` -- purely additive, the
  existing `trajectory_guard_raw_cloud_en` path is untouched),
  `getAccumulatedCloudForShadow` (voxel-downsampled read of the window,
  see below), `fetchCiriShadowCloudSnapshot` /
  `checkBrakeCandidateAgainstCiriShadow` (the shadow check itself, wired
  into `activateEmergencyBrake`'s existing candidate loop, log-only). New
  config: `fsm/trajectory_guard/raw_cloud/{ciri_shadow_en,
  accum_window_s, ciri_min_points, ciri_voxel_m}`, all under the
  already-existing (previously dead) `raw_cloud` block. New test-only
  profile `static_seedmaps_guard_viability_tight_v7_cirishadow.yaml`.
- Also added, independent of the CIRI work: `TRAJ_GUARD_RAW_DEBUG`
  periodic logging of `raw_cloud_snapshot_.sequence`/age in
  `mainFsmTimerCallback`, gated only on the subscription existing (not on
  any feature flag) -- kept in permanently as cheap, always-available
  diagnostics; see the reception-gap finding below.

**Finding 1 (positive): the mechanism works end to end.** First seed9
smoke test produced real, distinct verdicts (`SAFE` x3, `UNSAFE` x16,
`INSUFFICIENT_DATA` x17 in one run) with zero crashes and contact still at
0. The `INSUFFICIENT_DATA` health gate (checks recency against
`raw_cloud_max_age_s` and point count against `ciri_min_points` *before*
trusting an empty/sparse local box as "confirmed open") is doing real work,
not just a formality: cross-referencing timestamps against the
`TRAJ_GUARD_RAW_DEBUG` log showed essentially every `INSUFFICIENT_DATA`
event lines up with a raw-cloud reception gap -- one as long as **17s**
during a high-load retry burst (worse than the ~14s gap found in 8.1-era
step-1 instrumentation of the older single-snapshot path). The subscription
itself does receive messages now (unlike 8.4 attempt 3's "zero forever"
finding) -- fsm_node's `MultiThreadedExecutor` uses 8 threads across all of
its node's callback groups via a single `add_node()`, so `guard_cloud_sub_`
is not structurally starved the way the old perfect_drone_sim bug (8.1) was
-- but reception is bursty under load, and the health gate correctly
declines to certify during those gaps rather than guessing.

**Finding 2 (negative, root-caused and fixed twice, still not fully
resolved): synchronous CIRI shadow work does not fit in this codebase's
timing budget.** A seed1-10 x n=2 sweep (20 runs) with shadow enabled
showed seed1-2 fine (5/5 both) but seed3-6 catastrophically worse than
their established baselines (seed3 9-10/10 baseline -> 3/5 both shadow
runs; seed4 8-10/10 -> 0/5, 1/5; seed5 9-10/10 -> 1/5 both; seed6 8/10 ->
1/5 both) -- despite the shadow result being provably unable to affect any
accept/reject decision. Two real, sequential causes were found and fixed,
but completion still did not recover:

1. **Uncontrolled cloud size.** `getAccumulatedCloudForShadow` originally
   concatenated every raw point in the 1.5s window with no downsampling.
   Measured directly: 30,000-80,000 points per call (vs. the map path's
   resolution-gridded few hundred), with CIRI decomposition cost spiking
   to 15-40ms on some calls. Fixed with a voxel-grid hash-set downsample
   (`ciri_voxel_m`, default 0.1m) in `getAccumulatedCloudForShadow` itself
   -- cut typical counts to 8,000-30,000 and decomposition cost to
   consistently <1.2ms. Re-verified directly (not assumed) before moving
   on.
2. **30x redundant work per brake activation.** The shadow check was
   called inside `activateEmergencyBrake`'s existing 30-attempt
   duration-retry loop, so the *entire* fetch-plus-voxelize pipeline (not
   just the CIRI call) reran up to 30 times per single brake activation,
   measured at ~0.8-1ms/call even after fix 1 -- up to ~24-30ms added per
   activation, repeated every time the vehicle braked. Fixed by hoisting
   the fetch to once per `activateEmergencyBrake` call
   (`fetchCiriShadowCloudSnapshot`, called once; `CiriShadowCloudSnapshot`
   passed into the per-attempt `checkBrakeCandidateAgainstCiriShadow`).
   Verified the call-count ratio directly: exactly 1 accumulation per
   `TRAJ_GUARD_BRAKE`/`TRAJ_GUARD_BRAKE_REJECTED` line (793 and 793 in one
   seed9 run) after the fix, vs. up to 30:1 before.

**Both fixes were real and independently verified, but a re-run of the
seed5-10 x n=1 verification after fix 2 still showed 0-2/5 across the
board** (seed5 2/5, seed6 0/5, seed7 1/5, seed8 0/5, seed9 0/5, seed10
0/5) -- essentially unchanged from before fix 2. Root cause of *this*:
`activateEmergencyBrake` is called from `mainFsmTimerCallback`, which runs
on a **10ms (100Hz)** `wall_timer` (`execution_timer_`, `exec_cbk_group_`,
`MutuallyExclusive`). Even the single, downsampled shadow computation
(~0.8-15ms measured) is large relative to a 10ms budget, and a
`MutuallyExclusive` group cannot start the next tick until the current one
returns -- so on ticks where a brake is active (i.e. exactly the
highest-stress, most-timing-sensitive moments), the shadow overhead can
by itself exceed the entire budget for that tick, and does so repeatedly
during a stall. This is a materially different problem than either of the
two fixes above and was not resolved this session.

**The correct fix (not implemented): move the shadow computation off the
100Hz synchronous path entirely**, e.g. an async, latest-only background
worker that computes at its own pace and lets `activateEmergencyBrake`
read whatever the most recent finished result is (or `DISABLED`/stale if
none is ready yet). This project already used exactly this pattern once
before for an analogous problem -- see `docs/연구일지.md`'s "Shadow 후속"
section (2026-08-13 era): a synchronous shadow trajectory validator was
found to add real cost to the planning loop, and was fixed by moving it to
"비동기 latest-only worker로 commit 지연을 제거" (an async latest-only
worker). Re-implementing that same pattern for the CIRI shadow check is a
substantially larger change than anything else in this section and was not
attempted -- flagged as the clear next step rather than guessed at.

**Current state:** `trajectory_guard_raw_cloud_ciri_shadow_en` defaults to
`false` and is not set in `static_seedmaps_guard_viability_tight_v7.yaml`
(the actual best-known-good profile) -- only the dedicated
`_cirishadow.yaml` test profile turns it on. Contact stayed at 0 across
every run of every sweep in this section; the regression is completion-
rate only, confined to that one test profile, and does not affect the
project's actual current baseline. Safe to leave in place as-is (inert by
default). The async-worker rework proposed here was subsequently implemented
and measured in §8.11.

### 8.11 2026-08-19: async latest-only CIRI shadow worker restores completion throughput

Implemented the async rework identified at the end of 8.10. The final
architecture has three relevant boundaries:

1. `activateEmergencyBrake()` does only cheap work for this diagnostic. It
   retains one representative dynamically-valid brake candidate, overwrites
   the single pending job (latest-only), and reads the latest *completed*
   cached result. No result is reported as current before one completes
   (`STALE`), old completed results age to `STALE`, and the result remains
   structurally absent from every brake accept/reject branch.
2. A dedicated `ciriShadowWorkerLoop()` owns the expensive path: accumulated
   scan snapshot, PointCloud2-to-PCL conversion, voxel downsampling, CIRI
   decomposition, candidate containment check, and result publication. The
   worker is stopped and joined before `FsmRos2` destruction.
3. Shadow-only mode no longer creates a second DDS subscription to the large
   `/cloud_registered` message. `ROGMapROS` now exposes an optional in-process
   observer for the exact scan its existing subscription accepted. The
   observer stores only the shared message pointer and receive time; conversion
   stays in the worker. The observer is guarded by an atomic fast path and is
   inert when unset. The live raw-cloud guard, if explicitly enabled, retains
   its independent subscription/KD-tree path.

That third boundary was required, not incidental. The first async build still
got only 2/5 waypoints in a seed5 smoke while a same-session shadow-off control
completed 5/5 in 67.9 s. Inspection found that `guardCloudCallback()` built a
KD-tree for every scan even though `_cirishadow.yaml` has
`raw_cloud/enable: false`; avoiding that and moving PCL conversion into the
worker improved a second seed5 smoke only to 3/5. The remaining duplicated DDS
delivery was removed with the map observer above. The next seed5 run then
completed 5/5 in 69.9 s. In other words, moving only the explicit CIRI call was
not enough: shadow-only scan capture also had to leave the extra
subscription/callback path.

The final seed5-10 smoke used the campaign-derived 95.714 s timeout. It reached
28/30 waypoints with 4/6 full completions and zero contacts; seed7 and seed9
both stopped at 4/5. Those two are timeout artifacts relative to the earlier
120 s baseline protocol (seed7 subsequently completed at 98.24 s), so the
formal comparison below reran every seed under the same 120 s condition used
in 8.8/8.9.

Final seed1-10 x n=2 result (`loop24.txt`, switch distance 1.5 m, timeout
120 s, `static_seedmaps_guard_viability_tight_v7_cirishadow.yaml`):

| seed | 5/5 runs | waypoints | contact |
|-----:|:--------:|:---------:|:-------:|
| 1 | 2/2 | 10/10 | 0 |
| 2 | 2/2 | 10/10 | 0 |
| 3 | 2/2 | 10/10 | 0 |
| 4 | 2/2 | 10/10 | 0 |
| 5 | 2/2 | 10/10 | 0 |
| 6 | 2/2 | 10/10 | 0 |
| 7 | 2/2 | 10/10 | 0 |
| 8 | 2/2 | 10/10 | 0 |
| 9 | 2/2 | 10/10 | 0 |
| 10 | 1/2 | 7/10 | 0 |
| **total** | **19/20 (95%)** | **97/100 (97%)** | **0/20** |

The one failure was seed10 run1 (2/5 at 120 s). This is consistent with the
large established liveness variance on seed10 (8.9's shadow-off profile was
2/5 full completions), not evidence that the shadow diagnostic improves
planning. Conversely, n=2 is far too small to claim 95% as a new completion
rate. The defensible conclusion is narrower: 8.10's catastrophic
shadow-specific 0-2/5 waypoint regression is gone and the result is back in
the shadow-off distribution. The small committed aggregate is
`results/ciri_shadow_async_n2_20260819.csv`; raw JSON/stack logs remain in
`/tmp/ciri_async_n2_seed1_10/` and are not committed.

Across those 20 runs the worker completed 812 jobs: SAFE 211, UNSAFE 238, and
INSUFFICIENT_DATA 363. There were zero old synchronous CIRI log paths and all
20 startup logs reported `source=map_observer`. Worker total time was mean
5.138 ms, median 3.925 ms, p95 13.628 ms, p99 18.108 ms, max 22.706 ms;
enqueue-to-worker-start queue delay was mean 0.096 ms and p95 0.141 ms. No latest-only
replacement occurred in this cohort because each worker job completed before
the next brake request, but the single-slot overwrite path remains bounded if
that ordering reverses on a slower machine. Main-FSM brake logs observed the
latest cached result as SAFE/UNSAFE/INSUFFICIENT_DATA when fresh and STALE
otherwise, without waiting for any of the 0-22.7 ms work above.

Scope remains unchanged: this is still a **shadow-only theorem-1 diagnostic**,
not a brake policy. `trajectory_guard_raw_cloud_ciri_shadow_en` still defaults
to `false`; `static_seedmaps_guard_viability_tight_v7.yaml` still does not set
it; only `_cirishadow.yaml` enables it. No result is connected to live flight
decisions, and the Fig. 8C(iii) FOV cut noted in 8.10 remains unimplemented.

### 8.12 2026-08-20: certified stop-and-reroute removes the seed10 same-topology deadlock

The one failure in 8.11 was not random CIRI-shadow worker overhead. Its raw
stack log showed a single `PlanFromRest/with_backup` generation repeatedly
rejected **110 times over 75.404 s**, while the first collision stayed near
`[5.115, 23.098, 2.671]` and the map continued advancing from version 109 to
478. In other words, neither a stale map nor the shadow diagnostic was holding
the planner: a stopped vehicle kept generating the same unsafe topology until
the 120 s mission timeout. The successful second seed10 run (5/5 in 77.17 s)
did not "improve" the first run; it was an independent run that happened not
to enter that long-lived generation.

The existing topology-zone implementation did not guarantee an escape. It
centred a 3-D sphere on the first collision, and in the reproduced seed10
stall that centre was only about 6.2 cm from the stopped start. A* could start
inside it, change altitude, or return to the same horizontal passage. A second
layer mismatch made this worse: A* tested a solid 3-D sphere, while CIRI saw
only 16 points on one horizontal ring plus two poles. Even when the discrete
A* guide path moved around the zone, the continuous optimized trajectory could
pass above, below, or between those sparse CIRI samples.

The recovery was therefore changed from "retry another candidate" to a
bounded, certified **stop-and-reroute** transition:

1. `FsmRos2::tryRecoverFromEmergencyBrake()` now tells `SuperPlanner` when
   the existing emergency brake has finished, the map is fresh, odometry is
   current, and the terminal pose has remained stable for 0.25 s. A new brake
   clears that certificate. This removes the former disagreement in which the
   FSM had a valid zero-speed terminal certificate but the planner's separately
   sampled scalar speed gate declined to arm recovery.
2. `PlanFromRest` geometric rejects are grouped by candidate generation and
   XY collision cluster (`collision_merge_m: 0.5`). The first reject of a new
   generation and then every third matching reject place another blocker, up
   to six. The first cylinder starts one radius plus 0.05 m ahead of the
   stopped pose, and later
   cylinders extend the rejected route in 1.0 m steps. EXP collisions supply
   the preferred route direction; initial EXP displacement/velocity and goal
   direction are bounded fallbacks. A successful commit or a new goal clears
   the entire recovery state.
3. A* and CIRI now use the same vertical-XY-cylinder intent across the flyable
   height range. A* uses an exact XY-distance test and permits
   only monotonically outward grid steps if quantization puts the start inside
   a new cylinder. CIRI encodes its boundary with 16-point rings at no more
   than 0.25 m vertical spacing throughout each local search box. The
   deterministic radius jitter
   retained from section 6 prevents the old symmetric-sample NaN/Inf failure.
   Thus changing altitude is no longer misclassified as a topology change.

The generic `growth_m`/`max_radius_m` parameters remain functional for other
profiles: later cylinders may grow with escalation. The validated tight-v7
profiles explicitly use `growth_m: 0.0`, `max_radius_m: 0.8`, because this
campaign tested a chain of equal 0.8 m cylinders. This avoids leaving the old
growth parameters as silent no-ops while keeping the recorded configuration
identical to the measured one.

Seed10 was first run five consecutive times with
`static_seedmaps_guard_viability_tight_v7_cirishadow.yaml`, `loop24.txt`, and
the same 120 s timeout. All five completed with zero contact:

| run | waypoints | mission time (s) | static PCD min distance (m) | contact |
|----:|:---------:|-----------------:|----------------------------:|:-------:|
| 1 | 5/5 | 78.09 | 0.372 | 0 |
| 2 | 5/5 | 90.97 | 0.449 | 0 |
| 3 | 5/5 | 94.85 | 0.442 | 0 |
| 4 | 5/5 | 96.15 | 0.480 | 0 |
| 5 | 5/5 | 90.78 | 0.434 | 0 |
| **total/mean** | **25/25** | **90.17 mean** | **0.372 worst** | **0/5** |

The longest same-generation `PlanFromRest` reject span in these five runs was
1.755 s, versus the reproduced 75.404 s failure. The result is not merely a
timeout improvement: run path lengths varied from 232.225 to 252.254 m, which
is consistent with genuinely different detours rather than resubmission of one
candidate. After making the legacy growth parameters explicit without changing
this profile's 0.8 m radius, a final seed10 smoke also completed 5/5 in 89.37 s
with zero contact and 0.428 m static-PCD minimum distance.

The broader seed1-10 x n=2 regression used the same CIRI-shadow test profile
and protocol. Seed10 rows below are runs 1-2 of the five-run gate above:

| seed | 5/5 runs | times (s) | contact | worst static PCD distance (m) | longest same-gen reject span (s) |
|-----:|:--------:|:---------:|:-------:|:-----------------------------:|:--------------------------------:|
| 1 | 2/2 | 58.89 / 63.24 | 0 | 0.384 | 0.000 |
| 2 | 2/2 | 59.12 / 64.70 | 0 | >=0.500 | 0.000 |
| 3 | 2/2 | 64.06 / 75.31 | 0 | 0.429 | 0.000 |
| 4 | 2/2 | 68.11 / 80.32 | 0 | 0.420 | 0.296 |
| 5 | 2/2 | 73.96 / 61.99 | 0 | 0.378 | 0.809 |
| 6 | 2/2 | 78.80 / 77.19 | 0 | 0.443 | 1.377 |
| 7 | 2/2 | 82.90 / 71.60 | 0 | 0.462 | 0.193 |
| 8 | 2/2 | 77.65 / 86.18 | 0 | 0.463 | 0.000 |
| 9 | 2/2 | 92.57 / 81.37 | 0 | 0.387 | 1.467 |
| 10 | 2/2 | 78.09 / 90.97 | 0 | 0.372 | 0.782 |
| **total** | **20/20** | **74.35 mean** | **0/20** | **0.372 worst** | **1.467 max** |

Seed2's raw JSON contains `null` rather than an exact static-PCD distance. Its
PCD loaded correctly (241,490 points); the monitor intentionally searches only
the 0.5 m neighborhood and records no exact value when no point ever enters
that neighborhood. The defensible value is therefore `>=0.500 m`, not missing
safety data. The committed per-run aggregate is
`results/topology_cylinder_reroute_cirishadow_n2_20260820.csv`; raw logs remain
in `/tmp/cylinder_route_block_seeds1_9_n2/`,
`/tmp/cylinder_route_block_seed10_smoke/`, and
`/tmp/cylinder_route_block_seed10_final_smoke/`.

This is strong evidence that the specific same-generation seed10 deadlock was
removed, and it passes a five-consecutive-run local gate. It is still only n=2
per seed for the broader population and does not establish a 100% population
completion rate or flight readiness. The CIRI raw-cloud result remains strictly
shadow-only and off by default; this section changes the live topology-recovery
path after an independently certified stop, not the shadow result's authority.

### 8.13 Guarded v7 full/sector/adaptive seed1-10 × n=5 (2026-08-20)

A 150-run comparison used the normal shadow-off tight-v7 guard with a common
filtered input profile, v=7, `loop24.txt`, and a 120 s timeout. Mode order was
rotated by run. The planner and guard were identical across modes: full was a
passthrough, sector used body-yaw ±60 degrees, and adaptive used velocity-yaw
±60 degrees plus stall opening. Both filtered modes retained the existing
replan-failure safety valve (five failures open, 15 successes close).

| mode | completion | waypoint | mean time | weighted point reduction | replan-open duty | mapping total reduction |
|:---|---:|---:|---:|---:|---:|---:|
| full | 48/50 (96%) | 245/250 | 77.43 s | 0% | 0% | 0% |
| sector | 46/50 (92%) | 236/250 | 80.59 s | 2.72% | 91.48% | 6.44% |
| adaptive | 47/50 (94%) | 243/250 | 80.56 s | 2.54% | 91.54% | 6.36% |

The completion differences are descriptive, not statistically established:
paired exact McNemar was `p=0.6875` for full-sector and `p=1.0` for
full-adaptive. Mean mission time increased 4.07%/4.04% versus full even though
ROG mapping total time fell about 6.4%. The efficiency result is dominated by
the safety valve: approximately 68% of replan status messages were failures,
so sector/adaptive were full-open for roughly 91.5% of frames. This is the
honest result for the current canonical modes, not a strict closed-sector
ablation.

Completion was 5/5 for every mode on seed1-3 and seed5-8. Seed4 sector was
4/5. Seed9 was full 4/5, sector 3/5, adaptive 2/5. Seed10 was full 4/5, sector
4/5, adaptive 5/5. Thus 8.12's seed10 full 5/5 local gate did not reproduce as
a deterministic guarantee in this longer, interleaved campaign. The new
topology recovery removed the specific 75.404 s same-generation deadlock, but
the guarded planner still has stochastic liveness failures.

One measurement defect was found only after the run. `native_campaign.py`
placed the requested `--static-pcd` option after argparse's `--` positional
delimiter, so the loop monitor ignored it. All `static_pcd_*` zero/null fields
in this cohort are invalid, and this cohort must not be added to the earlier
0/170 static-PCD contact total. The option order is now fixed, and the monitor
emits `static_pcd_enabled`/`static_pcd_point_count`; a requested static-PCD run
is invalid and retried unless both prove the index is active. The measured,
mode-dependent live clouds produced one contact marker in sector and one in
adaptive on seed9. Because the common static reference was absent, neither a
zero-contact claim nor a physical-contact comparison is defensible. The
0.20 m marker radius also equals `robot_r` and certifies no positive margin.
A separate post-fix seed1 full smoke verified the repaired full launch path:
5/5 waypoints in 57.42 s, `run_valid=true`, 241,490 static points loaded, and
zero static marker. That smoke is not part of the n=5 table.

Full tables, failure rows, protocol, and caveats are in
`docs/guarded_v7_full_sector_adaptive_n5_20260820.md`. Raw and derived data are
`results/guarded_v7_full_sector_adaptive_seed1_10_n5_20260820.csv` and
`results/guarded_v7_full_sector_adaptive_seed1_10_n5_summary_20260820.csv`.

### 8.14 Seed9/10 full failure mechanism and static-PCD repair (2026-08-20)

The two full failures in 8.13 were inspected against the four successful runs
of the same seed. They are a new unreachable-recovery case, not a return of the
map-freeze bug. Seed9 run4 held generation 177 for 314 rejects/30.614 s; seed10
run2 held generation 71 for 314 rejects/98.871 s. Every rejection was a
`PlanFromRest/with_backup` EXP `CLEARANCE_MARGIN`. Map versions still advanced
317->401 and 44->465, respectively.

Both final loops attempted 314 emergency brakes, accepted zero, and therefore
never reached a certified stable hold. More importantly, every retry reused
one cached brake speed: 2.813 m/s for seed9 and 0.741 m/s for seed10.
`fsm_ros2.hpp` stores `last_published_cmd_` behind a boolean validity flag but
does not timestamp it. Once guard suppression stops command publication, that
cached state remains valid forever and `activateEmergencyBrake()` continues
to prefer it over a fresh trajectory sample or odometry.

This interacts with the deliberately strict topology gate. A rejected
PlanFromRest route may arm a blocker only when odometry speed is <=0.2 m/s or
the FSM has supplied a certified-stop flag. `activateEmergencyBrake()` clears
that flag before each new attempt, while a rejected brake never becomes active
and can never finish the stable-hold checks. Both failed runs consequently had
zero `TRAJ_GUARD_REROUTE_ARM` and zero `TRAJ_GUARD_REROUTE_SEARCH` events. By
contrast, the four successful seed9 runs recorded 79/126 arm/search events and
the four successful seed10 runs recorded 82/144.

Seed10 also had 475 EXP/frontend failures after the stall began, including 460
0.1 s replan-budget overruns and 14 FIRI NaN/Inf failures. Those failures slow
the retry loop but are secondary: the same guard/brake deadlock began before
them and seed9 reproduces the primary mechanism without FIRI warnings.

The static-PCD campaign runner defect described in 8.13 is fixed. Monitor
options now precede argparse's `--`; `static_pcd_enabled` and
`static_pcd_point_count` are emitted; and a requested seedmap static-PCD run is
invalid/retried unless the index is provably active. The native-campaign unit
suite passes 12/12, and a separate seed1 full-stack smoke loaded 241,490 points
and completed 5/5. This does not retroactively repair 8.13's missing static-PCD
measurements.

The next implementation should timestamp and consistency-check the cached
command, acquire a fresh actual recovery state, and add a bounded fail-closed
state for repeated brake/candidate rejection. Topology blockers must remain
gated on a certified actual stop; the previously reverted moving-brake
collision arming should not be restored. Full evidence is in
`docs/guarded_v7_full_seed9_seed10_failure_analysis_20260820.md` and
`results/guarded_v7_full_seed9_seed10_log_analysis_20260820.csv`.

### 8.15 Seed9/10 recovery completion, map-cadence repair, and local n=5 gate (2026-08-20)

Section 8.14 correctly identified the stale `last_published_cmd_` lifetime,
but one important detail in its proposed remedy was wrong: the ROS2 ROG odom
callback had never populated `RobotState.v/a/j`. Those fields were also not
initialized. Treating `robot_state_.v` as measured odometry therefore produced
invalid diagnostics, and an attempted direct propagation of simulator twist
caused an actual seed10 static/live contact. That attempt was fully reverted.
The retained fix explicitly zero-initializes the legacy fields and estimates
motion from consecutive fresh odometry positions only inside serialized brake
selection.

The final recovery changes are:

1. Cached position commands now carry a wall-time stamp and are usable as a
   brake initial state only for 0.10 s while position and, when available,
   velocity consistency checks pass. Otherwise brake selection uses the fresh
   position-derived motion estimate, then the live trajectory state. Brake
   selection is mutex-serialized across main/replan callback groups.
2. Topology blockers are tracked per outgoing XY branch. A new direction gets
   a blocker next to the certified stop instead of inheriting an unrelated
   branch's forward chain index. Three consecutive A* `NO_PATH` results reset
   the finite blocker epoch while the vehicle remains on its certified hold.
3. An appended backup or EXP-to-backup stitch rejection no longer poisons EXP
   topology. If only that segment fails, an EXP-only candidate may commit only
   after the normal full geometric guard and sampled stop-viability checks.
4. `fsm.map_readiness` is enabled in the three tight-v7 profiles so
   `PlanFromRest` does not spin on a stale map and starve the callback needed to
   refresh it.
5. The simulator declared a 10 Hz GENERAL_360 LiDAR but the full-stack logs
   often committed only about 1 scan/s. The renderer now precomputes angular
   ray terms, iterates only the 128 active rings, vectorizes depth conversion,
   skips disabled depth-image construction and an unused duplicate point
   vector, and disables hidden-window vsync. Angular resolution, FoV, 128-ring
   selection, sensing horizon, and published point representation are
   unchanged; this is not sensor downsampling.
6. A final short-connection failure mode was observed after the vehicle had
   reached a certified stop about 1.8 m from the last waypoint: MINCO failed
   more than 60 consecutive times, with no A* `NO_PATH` or guard rejection for
   the topology logic to consume. A default-off
   `guard_direct_goal_fallback` now allows one rest-to-rest minimum-jerk
   candidate only from an FSM-certified stop and only within 3 m. It goes
   through `commitTrajectoryCandidate`, including the full geometric guard and
   every sampled stop-viability check; rejection leaves the certified hold in
   place. The local candidate start must also remain within 0.15 m of a fresh
   mutex-protected odometry snapshot. The final random gate did not exercise
   this branch, so it is bounded hardening based on the reproduced stall, not a
   separately demonstrated success mechanism.

Several tempting alternatives were explicitly rejected:

- Increasing map freshness to 1.50 s with a 1.25 s early-brake threshold made
  the first repeated seed9 run complete faster but caused two static-PCD
  contacts (minimum centre distance 0.142 m, body clearance -0.058 m). The
  tested profiles remain at 0.75/0.55 s.
- Feeding simulator twist globally into ROG state caused a seed10 contact and
  was reverted.
- Per-frame KD-tree culling made scan cadence worse, and lowering only the
  optimizer from 15 to 10 Hz increased completion time without reducing stale
  events. Both were reverted.

The final gate used v=7, full mode, `loop24.txt`,
`static_seedmaps_guard_viability_tight_v7_filtered.yaml`, a 140 s timeout, and
the repaired static-PCD monitor. Each run loaded exactly 1,042,220 reference
points.

| seed | completion | waypoint | mean time | time range | worst centre distance | worst body clearance | contact |
|:---:|---:|---:|---:|---:|---:|---:|---:|
| 9 | 5/5 | 25/25 | 93.95 s | 84.66-117.59 s | 0.420 m | 0.220 m | 0/5 |
| 10 | 5/5 | 25/25 | 99.09 s | 89.94-109.12 s | 0.332 m | 0.132 m | 0/5 |
| **total** | **10/10** | **50/50** | **96.52 s** | **84.66-117.59 s** | **0.332 m** | **0.132 m** | **0/10** |

The committed row-level result is
`results/guarded_v7_full_seed9_seed10_recovery_n5_20260820.csv`. Raw logs were
kept under `/tmp/full_recovery_directgoal_smoke_artifacts/`,
`/tmp/full_recovery_directgoal_repeat_artifacts/`, and
`/tmp/full_recovery_directgoal_seed10_final_artifacts/` during the session.
After adding the final 0.15 m start-consistency condition, a separate seed10
smoke on the rebuilt binary completed 5/5 waypoints in 83.92 s with zero
contacts and 0.262 m static-PCD body clearance. Its raw row and artifact are
`/tmp/full_recovery_post_tighten_seed10.csv` and
`/tmp/full_recovery_post_tighten_seed10_artifacts/`; the concise retained row is
`results/guarded_v7_full_seed10_post_tighten_smoke_20260820.csv`. It is
intentionally not folded into the predeclared n=5 aggregate above.

This is a local regression gate, not proof of a 100% population completion
rate or flight readiness. Seed10's worst positive body clearance was only
0.132 m, and the final cohort still contained many fail-closed stale-map
events. The paper-faithful accumulated raw-cloud CIRI result remains
shadow-only/default false and has no authority over live brake decisions.

### 8.16 Full/sector/adaptive paired n=5 after recovery changes (2026-08-21)

The larger paired regression requested at the end of 8.15 is now complete.
Seeds 1-10 were run five times in each of full, sector, and adaptive mode with
rotated mode ordering, v=7, `loop24.txt`, the same rebuilt binary,
`static_seedmaps_guard_viability_tight_v7_filtered.yaml`, and a 140 s timeout.
All 150 rows were valid and all 150 loaded the independently monitored static
PCD.

| mode | completion | all-run mean | success-only mean | map commit | cloud callback | point reduction | mapping/update | static contact | worst body clearance |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| full | 46/50 (92%) | 81.38 s | 76.28 s | 3.94 Hz | 6.51 Hz | 0% | 131.65 ms | 0/50 | 0.129 m |
| sector | 49/50 (98%) | 76.12 s | 74.81 s | 4.13 Hz | 6.82 Hz | 2.97% | 124.97 ms | 0/50 | 0.109 m |
| adaptive | 50/50 (100%) | 75.57 s | 75.57 s | 4.04 Hz | 6.63 Hz | 3.01% | 125.29 ms | 0/50 | 0.079 m |

The LiDAR target (10 Hz), replan target (15 Hz), main FSM timer (100 Hz), and
command timer (100 Hz) were identical in all modes. Only achieved cadence
changed. Sector/adaptive were full-open about 91% of wall time and removed only
about 3% of points, yet mapping cost per update fell about 5% and aggregate map
commit cadence rose 4.93%/2.47%. The effect varied strongly by seed and is not
a frequency guarantee. The apparent 6-7% all-run mission-time improvement is
mostly the four full timeouts; success-only improvement is only 1.93%/0.94%.

Exact paired McNemar tests do not establish a completion difference at this
sample size: full/sector `p=0.375`, full/adaptive `p=0.125`, and
sector/adaptive `p=1.0`. Adaptive's 50/50 must therefore not be presented as a
population guarantee, especially because its worst positive static clearance
was only 0.079 m.

The failures were full seed3 run4, seed6 run5, seed7 run4, and seed9 run3,
plus sector seed9 run1. Three full failures were dominated by thousands of
MINCO/EXP failures; seed7 was dominated by thousands of corridor/polytope
failures; and the sector seed9 failure churned through 38 topology arms,
27 `NO_PATH` results, and nine epoch resets near waypoint 5. No direct-goal
fallback commit or rejection marker appeared in any of the 150 runs, so the
8.15 bounded branch did not cover these residual failures.

Static-PCD collision was 0/150. One live-cloud-only marker occurred in seed5
run2 sector, but static PCD independently measured 0.309 m centre distance,
+0.109 m body clearance, and zero contact. Full tables, definitions, caveats,
failure marker counts, and statistics are in
`docs/guarded_v7_3mode_recovery_n5_20260821.md`; machine-readable results are
`results/guarded_v7_3mode_recovery_n5_raw_20260821.csv` and
`results/guarded_v7_3mode_recovery_n5_summary_20260821.csv`.

This broad result supersedes the 8.15 local seed9/10 10/10 headline as the
current liveness estimate. It confirms that the recovered build is materially
better than the stale-command deadlock state, but it is still not flight-ready
and does not have a universal completion guarantee.

### 8.17 Strict filter semantics and direct-Full n=5 gate (2026-08-22)

Section 8.16 did not test the intended ablation: sector/adaptive were full-open
for about 91% of wall time, so they removed only about 3% of input points. A
new `strict-burst` profile now keeps fixed Sector closed, gives Adaptive only
bounded 0.6 s full-cloud bursts with a 1.4 s cooldown, and adds a
speed-dependent omnidirectional near-field halo. The filter cloud subscription
and publication are best-effort/depth 1 so an expensive filtered frame cannot
create a stale backlog. The campaign runner now records the profile and obeys
an explicit timeout override after applying mode defaults. Full bypasses the
Python filter entirely and uses the direct `/cloud_registered` path.

The static-PCD monitor was also repaired. Its old fixed 0.5 m nearest search
serialized a clear run as a missing value whenever no point was inside that
radius. The first query now performs an exact expanding-cell search and later
queries use the current run minimum as a safe bound. This preserves exact
minimum-distance and body-contact episode tracking without a global nearest
query at every odometry sample.

The planner-side retained changes for this gate include a command-velocity
freshness fallback usable through the configured brake-trigger map-age window,
`brake_trigger_high_speed_map_age_s: 0.50`, coalesced same-voxel scan hits, and
sparse observed-free rays matched to the three-cell observed-neighbor query.
A bounded one-attempt vertical recovery was added for horizontal topology
saturation, but its marker count was zero in the final 150 valid runs. It is
therefore unvalidated and cannot explain the result.

At v=7 on `loop24.txt`, timeout 240 s, seed1-10 x n=5 per mode, the final
result was:

| mode | raw complete | safe complete | live contact run/episode | static contact run/episode | processed points/update | mapping/update |
|---|---:|---:|---:|---:|---:|---:|
| Full direct | **50/50** | **50/50** | **0/50, 0** | **0/50, 0** | 27,158.8 | 22.972 ms |
| fixed Sector | **50/50** | **46/50** | **4/50, 6** | **4/50, 4** | 12,928.7 (-52.40%) | 9.869 ms (-57.04%) |
| Adaptive | **49/50** | **49/50** | **0/50, 0** | **0/50, 0** | 16,149.3 (-40.54%) | 12.132 ms (-47.19%) |

Safe completion means 5/5 waypoints and zero static-PCD contact. All four
Sector contact runs were independently confirmed by both live-cloud and
static-PCD monitors (seed7 run2/run4, seed8 run3, seed10 run5). Adaptive
removed all four contacts, recovering safe completion from 92% to 98%, while
retaining a large compute reduction. It did not improve raw completion:
Adaptive seed9 run1 timed out at waypoint 4/5 with positive 0.173 m body
clearance. Its map and planner kept progressing, so this was cumulative
stop/recovery/topology churn rather than the old single-generation freeze.

The configured rates were identical in every mode (LiDAR 10 Hz, replan 15 Hz,
FSM 100 Hz, command 100 Hz). Observed map commit was 2.977/3.216/2.816 Hz for
Full/Sector/Adaptive. Filter-observed cloud callback was 4.070/3.982 Hz for
Sector/Adaptive; Full direct deliberately had no observer, so its callback
rate is unmeasured rather than 10 Hz.

Sector/Adaptive paired exact McNemar tests remain underpowered: safe
completion `p=0.375`, static contact `p=0.125`, raw completion `p=1.0`.
Full was a separate campaign and is not part of those paired tests. This is an
observed 50-run-per-mode cohort, not a universal safety or completion proof.
The full table, failure forensics, metric definitions, and caveats are in
`docs/strict_v7_3mode_n5_20260822.md`; raw and summary CSVs are under
`results/strict_v7_*_20260822.csv`. This section supersedes 8.16 as the current
configuration result. Raw-cloud CIRI remains shadow-only/default false.

### 8.18 Adaptive one-shot replan recovery and publication cap (2026-08-22)

Section 8.17 left one Adaptive seed9 liveness failure. A 0.25 s one-shot
full-cloud burst after three consecutive failed replans removed the old
nearly-continuous replan guard, but a new seed1-10 x n=5 run still finished
49/50. Its seed9 run5 stopped at waypoint 3/5 at
`(18.633, -24.281, 1.332)` with positive 0.091 m static body clearance.
Repeated `PlanFromRest` CIRI construction then reported an approximately
0.182 m nearest obstacle and rejected every EXP/backup fallback immediately;
the certified stop was safe by the independent contact metric but no longer
had a feasible local corridor. This is a terminal stop placement/liveness
failure, not a collision or frozen map.

A 0.6 s one-shot burst with 1.4 s cooldown had already observed 50/50, but
without a rate cap its 94.25 kpts/s processed throughput exceeded Full by
16.56%. Adaptive now keeps that bounded recovery width and limits only
filtered-cloud publication to 5 Hz. Input callbacks and recovery-state updates
remain latest-only and unthrottled. The limiter advances an ideal accumulated
deadline, avoiding the first implementation's phase-quantization bug that
turned a requested 4 Hz into only 2.65 Hz publication. The 4 Hz candidate was
also rejected because map commit fell to 1.97 Hz on its first seed9 run.

The accepted 5 Hz candidate passed seed9 targeted n=5 and then a separate
seed1-10 x n=5 gate. The final broad cohort observed **50/50 raw completion,
50/50 static-contact-free completion, zero live contact, and zero static-PCD
contact**. Every seed was 5/5. Mean/max mission time was 88.845/133.50 s,
worst positive static body clearance was 0.100 m, and maximum speed was
7.102 m/s (one run above 7.1 m/s). The accepted seed9 observations were 10/10
when the targeted and broad cohorts are reported separately; they are not a
population guarantee.

Observed filter input callback, filtered publication, and map commit rates
were 6.509, 4.188, and 3.132 Hz. Against the unchanged 8.17 Full baseline,
processed points/update fell 29.22%, processed throughput fell 25.55%,
mapping time/update fell 32.40%, and cumulative mapping work/mission fell
46.29%. The final mapping position is therefore between Full and fixed
Sector as intended. However, measured FSM plus Python-filter CPU-work was
64.09 CPU-s/mission versus Full's 55.92 CPU-s/mission, 14.61% higher. This
prototype establishes a mapping-work reduction, not an end-to-end CPU-work
reduction. A native filter implementation and a new CPU gate are required
before making the latter claim.

The new Adaptive gate was a separate campaign from the 8.17 Full/Sector
cohorts, so same-numbered seed/run rows are not paired statistical trials and
no McNemar claim is made. The observed 50/50 is neither a universal completion
proof nor flight readiness. Raw-cloud CIRI remains shadow-only/default false.
Full details and caveats are in the follow-up section of
`docs/strict_v7_3mode_n5_20260822.md`; raw/summary files are
`results/adaptive_replan025_strict_v7_n5_raw_20260822.csv`,
`results/adaptive_replan060_cap5_strict_v7_n5_raw_20260822.csv`, and
`results/strict_v7_adaptive_recovery_n5_summary_20260822.csv`.

### 8.19 Native C++ Adaptive filter smoke and CPU gate (2026-08-23)

The Python strict-Adaptive cloud path was ported without changing its policy
parameters to a standalone ROS2 C++ node, `native_sector_cpp`. It implements
the velocity-aligned sector, speed halo, adaptive arm/stall/resume state,
bounded one-shot replan guard, accumulated-deadline 5 Hz cap, state topics,
and compatible stats JSON. The campaign defaults to Python and selects the
new node only with `--filter-backend cpp`. Dynamic seed12-15 trap-event
instrumentation is not yet ported; the runner rejects that combination rather
than silently omitting it.

Synthetic PointCloud2 comparison matched Python/C++ retained points, dense
flag, and frame/point counters. The first real-cloud pilot nevertheless found
an important representation mismatch: MARSIM input has a 32-byte point stride
while its declared x/y/z/intensity fields end at byte 20. Python
`create_cloud()` repacks that record to 20 bytes, while the first C++ version
copied all 32 bytes. That pilot completed seeds 1-3 but seed4's `fsm_node`
reached about 9.1 GiB RSS and was OOM-killed. The C++ output now uses the same
20-byte packed field layout. A seed4 smoke and two subsequent seed1-10
cohorts did not reproduce the OOM. This before/after is strong diagnostic
evidence, but one failed pilot is not enough to attribute every RSS change
universally to point stride alone. The runner also now retries if the FSM or
filter exits during a mission.

Two independent seed1-10 x n=1 C++ cohorts both observed 10/10 raw completion
and 10/10 static-PCD-contact-free completion. The first functional cohort had
zero live and static contact. Its C++ CPU values were not used because the
meter selected a `ros2 run` wrapper for seeds 7 and 8. The corrected meter
matches `/proc/<pid>/cmdline` argv0 to the actual executable. The second CPU
cohort recorded a nonzero 2.32-3.16% filter CPU for every seed and again had
zero static contact. It had one live-only seed10 event: centre distance
0.1995 m at 2.7325 s and 0.627 m/s, while the fixed static PCD reported a
minimum centre distance of 0.321 m, positive 0.121 m body clearance, and zero
contact. It is not classified as physical static-map penetration, but the CPU
cohort must not be described as zero on every detector.

Time/update-weighted results for the corrected n=10 cohort were: input,
publication, and map rates 5.577/3.725/2.998 Hz; 19,978 points/update;
59.900 kpts/s; 16.385 ms mapping/update; and 4.488 s mapping work/mission.
FSM/filter/combined CPU-work was 52.037/2.522/54.559 CPU-s/mission. Against
the unchanged 8.17 Full n=50 baseline, processed points, throughput, mapping
time/update, and mapping work/mission fell 26.44%, 25.92%, 28.67%, and 44.21%;
combined CPU-work was 2.44% lower. Against the 8.18 Python Adaptive n=50
cohort, filter and total CPU-work fell 76.17% and 14.88%.

These are unpaired, different-sized, different-session cohorts. The native
result is an n=1-per-seed architecture/CPU smoke, not an n=50 replacement or
population claim. It supports proceeding to a seed1-10 x n=5 native gate;
until that passes, section 8.18 remains the broader Adaptive safety/liveness
result and section 8.19 only removes the immediate Python-CPU objection at
smoke scale. Full details are in `docs/adaptive_cpp_v7_n1_20260823.md`; raw
and summary files are `results/adaptive_cpp_strict_v7_*_20260823.csv` and
`results/adaptive_cpp_strict_v7_n1_summary_20260823.csv`. Raw-cloud CIRI
remains shadow-only/default false.

### 8.20 Stopped A* timeout recovery and native n=5 gate (2026-08-23)

The same-session pre-patch seed1-10 x n=5 gates reproduced the remaining
liveness defect without any measured contact. Full completed 49/50 and native
Adaptive completed 48/50. All three failures were seed9 stopped-state planning
loops: Full seed9 run2 stopped at waypoint 4/5, while Adaptive seed9 run2 never
left the start and run4 stopped at waypoint 2/5. The repeated search result was
bounded A* `TIME_OUT`, but the topology-recovery code admitted only `NO_PATH`.
In addition, `PlanFromRest()` did not publish `/planning/replan_status`, so an
Adaptive run that never entered `FOLLOW_TRAJ` could not arm the sensing-side
one-shot full-cloud recovery.

`fsm.cpp` now publishes the `PlanFromRest()` result through the existing replan
status topic. `super_planner.cpp` treats `TIME_OUT` as recovery evidence only
when `planning_from_rest=true` and the topology guard is enabled. This reuses
the existing bounded base-vertical, blocker-clear, and certified-stop epoch
reseed paths. Moving-state timeouts remain excluded because the committed
trajectory is still authoritative there. No clearance threshold, collision
rule, sector geometry, or raw-CIRI authority changed.

The patched seed9 targeted gates were 5/5 Full and 5/5 native Adaptive. The
seed1-10 x n=1 regression was then 10/10 for both. Finally, independent
seed1-10 x n=5 campaigns observed **50/50 Full and 50/50 native Adaptive raw
and static-safe completion**, with zero live and static contact in both modes.
Worst static body clearance was +0.155 m Full and +0.139 m Adaptive; seed9 and
seed10 were each 5/5 in both modes. Adaptive's final logs contain five actual
`reason=astar_timeout` recovery actions across seeds 6, 7, and 9, and every
affected run completed. Full needed no timeout recovery in its final 50 rows;
one existing `astar_no_path` recovery ran on seed10 and completed.

The final n=50 workload comparison retained the intended map-side reduction:
Adaptive used 25.58% fewer processed points/update, 32.53% less processed
throughput, 29.62% less mapping time/update, and 48.39% less accumulated
mapping work/mission than Full. Do not use this particular n=50 pair to claim
end-to-end CPU reduction. The later Full campaign had one infrastructure
retry and then ran while the host had about 4.38 GiB FSM RSS and all 2 GiB of
swap occupied; its wall-time and CPU percentage were visibly distorted.
Adaptive combined CPU-work was therefore 5.41% above this contaminated Full
measurement, while the earlier clean patched n=1 smoke measured it 15.62%
below Full. A clean order-crossed repetition is required for an n=50 CPU claim.

The Full and Adaptive cohorts were sequential and unpaired, so no McNemar test
is reported. The observed 50/50 is not a population or flight-readiness proof.
Raw-cloud CIRI remains shadow-only/default false. Full tables and artifacts are
in `docs/native_cpp_timeout_recovery_v7_20260823.md` and
`results/full_adaptive_timeoutfix_summary_20260823.csv`.

### 8.21 Bounded memory and valid three-mode n=1 regression (2026-08-23)

The memory/swap contamination in 8.20 had two independent sources. First,
`detailed_log_en=true` retained every replan record's complete SFC point cloud
in an unbounded `replan_logs_` vector. One failing Full seed5 attempt reached
about 7.09 GiB FSM RSS with host swap exhausted before a kernel OOM kill. The
normal campaign profile now disables detailed cloud retention, replan records
are held in a deque capped at 64, and the corridor cloud is consumed by move.
Scalar/trajectory/timing records remain; full cloud debug logs require an
explicit opt-in and a deliberately selected cap.

Second, the fixed-map profile has `raycasting_en=false` but ROG-Map still
allocated two map-volume `uint16_t` counter arrays. At 491 x 491 x 981 cells
these reserved about 0.88 GiB. The no-raycasting path now stores only per-batch
touched voxel counters in an `unordered_map`; the existing dense fast path is
unchanged for `raycasting_en=true`. A bounded-log, pre-sparse seed6/10 x n=3
diagnostic reached 4383.98 MiB peak FSM RSS. The comparable post-sparse Full
gate peaked at 3472.67 MiB.

The campaign runner now records per-attempt memory traces, FSM RSS/PSS/swap,
host and cgroup memory/swap, PSI, retry reason, and cgroup OOM-kill delta. It
also found an experiment-validity bug in this session: an initial
Sector/Adaptive diagnostic used the direct-Full YAML, so the planner consumed
`/cloud_registered` rather than the filter's `/cloud_sector`. Those rows are
excluded from mode comparison. A Sector/Adaptive config override is now
rejected unless its parsed ROG-Map `cloud_topic` is `/cloud_sector`; a direct
Full override no longer launches an unused pass-through filter.

The final valid smoke uses v=7, `loop24.txt`, timeout 240 s, static PCD,
seed1-10 x n=1. Full uses the direct tight-v7 config and Sector/Adaptive use
the filtered tight-v7 config with the C++ strict-burst filter. Both configs
disable detailed SFC-cloud retention and use the same 64-record bound. Raw
completion was **10/10 in all three modes**. Static-safe completion was Full
**10/10**, Sector **9/10**, Adaptive **10/10**. Sector seed7 completed the
loop but had two contact events, one static contact episode, and -0.007 m worst
body clearance. Full and Adaptive had zero live/static contact; their worst
body clearances were +0.208 and +0.216 m.

The C++ filter now counts the exact combined output state transition rather
than trying to infer it from overlapping causes. Adaptive observed **321
effective full-open and 320 full-close transitions** (per-run opens 23-45),
with a time-weighted full-open duty of 23.38%. Seed5 ended while open, which
explains the one-count difference. The separate component counters were 7/2
stall-recovery entry/exit and 248/248 replan-guard open/close; they cannot be
added because a recovery episode can pulse repeatedly and causes can overlap.

Relative to Full, Sector reduced processed points/update 51.39%, throughput
54.00%, mapping/update 60.73%, and mapping work/mission 61.12%. Adaptive
reduced them 28.33%, 57.09%, 43.55%, and 58.64%. The observed combined
FSM+filter CPU-work reductions were 9.38% and 9.74%, respectively, but these
are sequential n=1 arms without order crossing, not an end-to-end population
claim. Mean mission time was 73.87 s Full, 77.30 s Sector, and 90.41 s
Adaptive.

All final rows had retry count 0, OOM delta 0, and FSM swap 0 MiB. One Sector
seed1 sample observed a brief host-wide memory PSI `some/full avg10` value of
0.18; every other row was 0. Peak FSM RSS across the 30 rows was 3455.69 MiB.
The host still had nearly 2 GiB swap occupied by its broader environment, but
the FSM did not use swap and there was no retry/OOM increment, so the 8.20
sustained pressure did not recur in this cohort.

One invalid raw-input diagnostic also exposed a stopped `PlanFromRest` EXP
`OCCUPIED` loop. A certified stopped EXP rejection with either `OCCUPIED` or
`CLEARANCE_MARGIN` can now arm the existing bounded topology recovery;
`MAP_STALE`, `UNOBSERVED`, and moving-state behavior remain excluded. Targeted
post-change runs passed, but the rare branch did not reoccur, so it is not
execution-proven by the valid final cohort.

The final fair rerun's sampled maxima were 7.004 m/s Full, 7.014 m/s Sector,
and 7.006 m/s Adaptive. A preliminary Adaptive row from the superseded
mixed-logging comparison reported 9.842 m/s, but a dedicated repeat and the
final fair seed3 rerun both reported about 7.000 m/s; it is excluded from the
final table. This entire section is an unpaired n=1 smoke, no McNemar test is
reported, and 10/10 is not a population or flight-readiness guarantee.
Raw-cloud CIRI remains default false. Full details and tables are in
`docs/memory_bounded_3mode_v7_20260823.md` and
`results/final_postopt_3mode_*_20260823.csv`.

### 8.22 Order-crossed Full/Sector/Adaptive n=5 gate (2026-08-23)

The clean broad comparison requested by 8.21 ran Full, fixed Sector, and native
Adaptive inside one interleaved campaign: `loop24.txt`, v=7, static PCD,
timeout 240 s, seeds 1-10 x n=5, 150 rows. Full consumed
`/cloud_registered`; Sector/Adaptive consumed `/cloud_sector` through the C++
strict-burst filter. The runner now accepts and validates separate direct and
filtered configs, continues mode rotation across seed boundaries, and records
global sequence plus order position. Position counts were balanced to
17/16/17 Full, 17/17/16 Sector, and 16/17/17 Adaptive.

All 150 rows were valid, completed the five-waypoint loop, and required one
attempt. Raw completion was therefore 50/50 for every mode. Static-safe
completion was Full **49/50**, Sector **48/50**, Adaptive **50/50**.
All-detector-safe completion, which also includes live-cloud-only threshold
events, was **49/50, 47/50, 50/50**. Contact runs/events were Full 1/2,
Sector 3/6, Adaptive 0/0. Worst static body clearance was -0.146 m, -0.027 m,
and +0.141 m.

The Full event was seed7 run1, not a spawn artifact. A generation-7 tail ended
at approximately `[11.950,12.850,1.050]`; the guard repeatedly certified its
short remainder `SAFE` while CIRI warned that corridor decomposition was
infeasible at 0.0179 m obstacle distance. Two `no_backup` tails then committed,
the trajectory finished inside the obstacle envelope, and static/live monitors
both reported contact. Topology reroute recovered liveness only after contact.
This is a current/terminal-pose clearance hole in short-tail/stationary-hold
certification, not the already-fixed same-topology or stopped-timeout loop.

Sector contacts were seed8 run1 (live-only center distance 0.194 m) and seed10
runs 2 and 4 (live plus static, worst static clearances -0.007/-0.027 m).
They occurred once in each order position; the Full event occurred in position
1. The crossed order does not show a single order-position cause. Exact paired
McNemar tests are now defined: Full/Sector p=0.625 (discordances 3 vs 1),
Sector/Adaptive p=0.250 (0 vs 3), and Full/Adaptive p=1.000 (0 vs 1).
The descriptive safety ordering is not significant at 0.05.

Adaptive recorded **1518 effective full-open and 1512 full-close edges**,
30.36 +/- 9.81 opens/run (range 19-62), and a 22.43% time-weighted open duty.
Six runs ended while open. Component counts were 36/13 stall-recovery
entry/exit and 1201/1201 replan-guard open/close, which are not additive
substitutes for the effective output edges.

The order-crossed workload result is clean. Relative to Full, Sector reduced
map commits 11.60%, points/update 51.15%, throughput 56.82%, mapping/update
59.93%, mapping work/mission 61.97%, and combined CPU-work/mission 11.62%.
Adaptive reductions were 46.15%, 32.61%, 63.71%, 44.23%, 63.25%, and 16.13%.
Mean mission time increased 7.35% Sector and 22.35% Adaptive. Compared directly
with Sector, Adaptive processed 37.96% more points/update during open bursts
but had 15.95% lower throughput, 3.38% lower mapping work/mission, 5.11% lower
combined CPU-work, and 13.98% longer mission time.

Every row had retry 0, OOM delta 0, FSM swap 0, and memory PSI some/full max 0.
Peak FSM RSS/PSS was 3474.36/3451.11 MiB. Host swap remained near 2 GiB used
and available memory fell to 3351.88 MiB late in seed10, but there was no FSM
swap, retry, OOM, or PSI response. The old unbounded growth did not recur.

Exact two-sided 95% Clopper-Pearson intervals for all-detector safety are
89.35-99.95% Full, 83.45-98.75% Sector, and 92.89-100% Adaptive. Thus Adaptive
50/50 is not population-level 100%, and the requested Full 100% target is not
even met descriptively in this cohort. The next safety implementation should
fail closed on current and terminal stop-pose clearance before accepting a
short tail/hold, followed by a seed7 Full repetition gate and another crossed
three-mode gate. Raw-cloud CIRI remains default false. Full tables are in
`docs/order_crossed_3mode_strict_v7_n5_20260823.md` and
`results/order_crossed_3mode_strict_v7_n5_*_20260823.csv`.

### 8.23 Full endpoint hard guard and Adaptive commit-aware refresh n=1 gate (2026-08-23)

The 8.22 Full failure exposed a narrow but hard safety hole: the inflated-grid
continuous certificate could accept a very short tail whose endpoint disagreed
with the raw occupied grid, after which the endpoint became a stationary hold.
`validatePositionTrajectory()` now treats the actual current odometry pose, the
first checked trajectory pose, and the terminal pose as mandatory raw-grid body
queries. It searches raw OCCUPIED voxel centres within `robot_r`, checks virtual
ground/ceiling body clearance, and returns `OCCUPIED` before considering the
initial-clearance escape exception. Only these two or three poses pay the raw
box-search cost; the existing inflated-grid DDA remains the continuous-path
certificate. Commit and viability-rescale validation both carry the same actual
current-pose snapshot.

The Adaptive timing diagnosis also showed that the 5 Hz publication cap had no
feedback from whether ROG-Map had actually committed the most recent cloud.
ROG-Map now publishes `/rog_map/commit_version` after a committed update. If
the normal cap is blocking, the Adaptive C++ filter may send one sector-only
latest refresh when the ACK is at least 0.12 s old, with a 0.10 s minimum
interval. A depth-1 QoS queue retains latest-only behavior. Effective full-open
frames keep every sector and near-field point but deterministically sample at
most 6,000 additional far-field points; commit refreshes never use the full-open
extra budget. The fixed Sector path is unchanged.

All three changed packages built successfully. Synthetic C++ filtering and the
campaign/monitor checks passed. A Full seed7 smoke completed 5/5 with contact 0
and +0.230 m static body clearance. An Adaptive seed9 smoke completed in 126.57
s with contact 0, 60 refresh frames and 4.06 commit ACK/s; its `MAP_STALE`/brake
counts fell to 23/29, although optimizer/topology retries still kept the time in
the prior range.

The requested main gate used v=7, `loop24.txt`, static PCD, timeout 240 s,
seed1-10 x n=1 x Full/Sector/Adaptive, with order rotation continuing across
seed boundaries. Every row was valid and required one attempt. Raw and
all-detector-safe completion was Full **10/10**, Sector **9/10**, Adaptive
**10/10**. All 30 runs had zero live contact events and zero static-PCD contact
episodes. Worst static body clearance was +0.252/+0.108/+0.174 m. Sector seed10
alone stopped at waypoint 4 and timed out safely at 240.01 s; Full and Adaptive
seed10 completed in 85.39/118.91 s.

Mean mission time was 72.679/92.820/85.875 s; Sector's completed-only mean was
76.466 s. Full-relative Adaptive reductions were 40.56% map commits, 36.30%
points/update, 62.13% throughput, 47.66% mapping/update, 63.24% mapping
work/mission, and 15.08% combined CPU-work/mission. Adaptive time remained
18.16% longer than Full. Adaptive emitted 289 effective full-open and 289
full-close edges, 20.97% mean open duty, 309 commit-refresh frames, and 2,889
commit ACKs (3.364 ACK/s by total mission time).

Against the larger 8.22 n=5 reference, Adaptive map commits rose 2.944 -> 3.336
Hz (+13.33%); `MAP_STALE` fell 70.86 -> 61.30/run (-13.49%), successful brakes
45.84 -> 38.80/run (-15.36%), and mean mission time 92.122 -> 85.875 s
(-6.78%). Full also varied 75.292 -> 72.679 s, so this is directional n=1
evidence rather than a paired effect estimate. On seed9, stale/brake counts fell
118.8/74.6 -> 84/59, but topology arm/search rose 11.0/14.4 -> 19/25. Seed10
also recorded 11/24 arm/search events. Commit starvation was real, but the
remaining late-seed delay is now principally the geometric topology/optimizer
recovery workload.

No Full log in this gate executed a new `status=OCCUPIED` endpoint rejection.
The seed7 smoke plus campaign and all ten main Full rows were safe, so the patch
is regression-clean and closes the identified code path, but the rare rejection
branch is not execution-proven. This n=1 cannot establish population 100%; even
10/10 has an exact two-sided 95% lower bound of about 69.15%. A repeated seed7
and broad crossed gate remain required for a safety claim.

Every row had retry 0, OOM delta 0, and FSM swap 0. Peak FSM RSS/PSS was
3476.25/3452.99 MiB and minimum available host memory 4821.88 MiB. Host swap was
already near 2 GiB used. Sector seed10 briefly recorded host-wide PSI some/full
0.12 during its long stall, but no FSM swap, OOM, or infrastructure retry
occurred. Raw-cloud CIRI remains default false. Detailed tables are in
`docs/endpoint_guard_commit_refresh_3mode_v7_n1_20260823.md` and
`results/endpoint_commitrefresh_3mode_strict_v7_n1_*_20260823.csv`.

### 8.24 Direct guard-state Adaptive refresh and bounded local escape (2026-08-24)

The repeated gate requested by 8.23 first exposed two separate failure classes.
The seed7 Full n=10 gate completed 10/10 with zero live/static contact. A
bounded stopped-state topology fallback was added for the earlier same-route
stall: after a certified stop and `A* NO_PATH`, one 0.6 m horizontal
minimum-jerk candidate is armed opposite the rejected route, followed by the
already bounded vertical candidate. Both candidates pass the unchanged
trajectory guard and viability checks, and the vertical saturation counter is
now advanced on the `NO_PATH` path instead of being re-armed forever. The Full
gate did not execute the new local-escape branch, so it is a bounded fallback,
not branch proof.

The subsequent order-crossed seed1-10 x n=5 x three-mode campaign had all 150
valid rows, one attempt per row, retry 0 and FSM swap 0. Raw completion and
contact runs were:

| mode | completion | live/static contact runs | mean time (s) |
|---|---:|---:|---:|
| Full | 50/50 | 0 | 71.039 |
| fixed Sector | 50/50 | 3 | 73.816 |
| Adaptive | 49/50 | 1 | 86.634 |

Adaptive's only failure was seed7 run2: it contacted twice while executing
trajectory-guard emergency brakes, then stopped at 3/5 waypoints with static
body clearance -0.054 m. Replan-failure bursts were an indirect signal: the
filter could close between repeated guard brakes even though that interval was
exactly when lateral obstacle evidence was needed. `FsmRos2` therefore now
publishes a reliable transient-local
`/planning/trajectory_guard_recovery_active` Boolean directly on guard
activation/recovery. Only Adaptive subscribes. It keeps its effective full-open
state for 2.5 s after recovery; fixed Sector remains closed and Full remains a
direct raw-cloud input. The state is latched across rejected brake construction
and retry, so a failed brake cannot silently close sensing.

The first implementation passed seed7 Adaptive 10/10 with zero contact, but a
2.5 s hold merged 41-75 guard episodes into only 2-5 open edges. It also meant
that the intended immediate safety refresh ran only on an open edge rather
than on every guard event. A later seed6 smoke reproduced the consequence:
contact stayed zero, but the vehicle stopped at 2/5 waypoints with +0.077 m
static body clearance, after which every outgoing candidate was `OCCUPIED` in
the updated voxel map. Local/vertical escape were correctly bounded but could
not certify motion from that start.

The final design treats every guard `false -> true episode` as a new sensing
event even when the 2.5 s open hold is already active. The next cloud bypasses
the 5 Hz publication cap once and is passed without the 6,000-point far-field
limit. All later open frames retain the 6,000-point bound. This produced 32
refreshes for 33 seed6 guard episodes in the first smoke (the final episode
ended with a pending refresh), then completed seed6/7 at 5/5 each with zero
contact. A separate post-patch Adaptive seed1-10 n=1 sweep also completed
10/10 with zero contact.

Removing the 5 Hz cap was explicitly rejected. It completed seed7 5/5 and
reduced mean time 99.10 -> 94.29 s, but raised kept points 63.75% -> 80.53%,
FSM CPU 57.07% -> 61.58%, and reduced the worst static clearance from +0.205
to +0.138 m. The final profile therefore retains the cap and uses only the
one-frame guard-edge exemption.

The final n=1 comparison combines the post-patch Adaptive seed1-10 sweep with
the unaffected Full/fixed-Sector rows. All inputs used static PCD validation,
v=7, `loop24.txt`, strict-burst C++ filtering and timeout 240 s:

| mode | completion | contact runs | mean time (s) | worst clearance (m) | points/update | map total/update (ms) | FSM CPU (%) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Full | 10/10 | 0 | 71.748 | +0.213 | 29,113 | 35.728 | 95.94 |
| fixed Sector | 10/10 | 2 | 75.805 | -0.161 | 14,388 | 13.871 | 76.62 |
| Adaptive | 10/10 | 0 | 80.920 | +0.157 | 22,304 | 27.449 | 71.86 |

Against Full, Adaptive reduced weighted points/update 23.39%, map total/update
23.17%, map update time 16.29%, and FSM CPU 25.10%. Mean mission time remained
12.78% longer. Fixed Sector reduced points/update 50.58% and map total/update
61.18%, but contacted on seeds9 and 10. This is the intended descriptive
trade-off: Adaptive recovered the observed Sector safety/completion result
while retaining a smaller, but material, compute reduction relative to Full.

Adaptive activation telemetry for that final sweep was:

| seed | effective open edges | direct guard episodes | full refresh frames | direct-guard open duty (%) |
|---:|---:|---:|---:|---:|
| 1 | 13 | 9 | 9 | 43.736 |
| 2 | 14 | 19 | 19 | 57.602 |
| 3 | 7 | 32 | 32 | 72.180 |
| 4 | 13 | 25 | 25 | 59.960 |
| 5 | 9 | 41 | 41 | 75.877 |
| 6 | 2 | 42 | 42 | 90.042 |
| 7 | 4 | 46 | 46 | 96.903 |
| 8 | 4 | 41 | 41 | 89.030 |
| 9 | 8 | 50 | 50 | 82.991 |
| 10 | 3 | 63 | 63 | 95.019 |

The direct signal is highly active on late dense seeds; this explains the
remaining Adaptive time penalty and is the next efficiency target. It must not
be shortened blindly because the pre-patch contact occurred in the gaps
between emergency-brake episodes. The current evidence is a same-code local
gate, not a population 100% guarantee: the final three arms were completed in
split follow-up sweeps after the first combined campaign was stopped for the
seed6 diagnosis, and no McNemar test was performed on n=1. Raw-cloud CIRI
remains default false and non-authoritative.

Primary raw results are
`results/local_escape_order_crossed_3mode_strict_v7_n5_raw_20260824.csv`,
`results/guard_signal_bounded_seed7_adaptive_n10_raw_20260824.csv`,
`results/guard_signal_uncapped_seed7_adaptive_n5_raw_20260824.csv`,
`results/guard_edge_refresh_seed6_seed7_adaptive_n5_raw_20260824.csv`,
`results/guard_edge_refresh_adaptive_seed1_10_n1_raw_20260824.csv`, and
`results/guard_edge_refresh_full_sector_seed6_10_n1_raw_20260824.csv`.

### 8.25 Guard duty attribution, rejected 6 Hz candidate, and the first-brake hole (2026-08-24)

The direct-guard open metric was split into actual `active` and post-recovery
`hold-only` frames without changing the established 5 Hz, 2.5 s hold, and
6,000-extra-point behavior.  A seed6-10 Adaptive diagnostic completed 5/5 with
zero contact.  Mean direct-active/hold-only duty was 59.42%/32.86%, proving
that late-map cost is not caused by the hold alone: actual guard recurrence is
the larger component.

Raising the cap to 6 Hz only while the direct guard was active was tested on
the same five maps and rejected.  It also completed 5/5 with zero contact, but
mean mission time increased 133.02 -> 163.89 s (+23.20%) and map total/update
increased 26.26 -> 29.45 ms (+12.14%).  Only seed8 improved in time.  The new
option is disabled by default (`0`, so the base 5 Hz cap remains authoritative)
and exists only to reproduce the diagnostic.

The final order-crossed seed1-10 x n=1 x three-mode gate had 30/30 valid rows,
one attempt each, retry/FSM-swap/OOM all zero, and peak FSM RSS 3453.69 MiB.
All modes completed 10/10.  Full had zero live/static contact.  Fixed Sector
had one live contact on seed10.  Adaptive had one live contact on seed7, so the
new gate does not satisfy the Adaptive contact-zero target.  All static-PCD
contact counts were zero, but Adaptive seed7's static body clearance was only
+0.036 m.

| mode | completion | contact runs | mean time (s) | worst static clearance (m) | points/update | map total/update (ms) | FSM CPU (%) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Full | 10/10 | 0 | 79.843 | +0.203 | 27,995 | 40.990 | 91.40 |
| fixed Sector | 10/10 | 1 | 82.621 | +0.069 | 14,075 | 15.013 | 76.91 |
| Adaptive | 10/10 | 1 | 97.550 | +0.036 | 22,554 | 31.376 | 64.10 |

Against Full, Adaptive reduced update-weighted points 19.43%, map total/update
23.45%, map update time 15.37%, and time-weighted FSM CPU 29.87%; mean mission
time was 22.18% longer.  Across the ten Adaptive rows, direct-active and
hold-only duty averaged 33.68% and 36.17%, with 340 direct guard episodes and
339 edge-refresh frames.

The Adaptive seed7 contact happened 4.8221 s after mission start while a guard
brake was ending at 0.2229 m/s.  The live nearest point was 0.19861 m from the
vehicle, while the common static PCD measured a 0.236 m minimum.  At epoch
1787565836.311 the guard had detected `MAP_STALE` (age 0.558 s), emitted the
direct true edge, and certified a 0.529 s brake ending near
`[6.886, 7.880, 1.208]` as `SAFE` against the stale map.  The contact followed
0.440 s later near that endpoint.  The true-edge scan updates only a subsequent
map and therefore cannot revise the already executing first brake.

This moves the next Adaptive safety target earlier than the post-guard hold:
one bounded, ACK/version-gated full refresh should be evaluated before the
guard's 0.50-0.55 s stale threshold.  Do not shorten the hold or enable the
rejected 6 Hz candidate as a substitute.  The complete map-by-map tables and
forensics are in `docs/guard_duty_3mode_v7_n1_20260824.md`; primary raw inputs
are `results/guard_duty_attribution_adaptive_seed6_10_n1_raw_20260824.csv`,
`results/guard_active6_adaptive_seed6_10_n1_raw_20260824.csv`, and
`results/guard_duty_final_order_crossed_3mode_v7_n1_raw_20260824.csv`.  This is
n=1, no McNemar test was performed, and raw-cloud CIRI remains default false.

### 8.26 Pre-stale full refresh closes the observed first-brake hole, with a large time cost (2026-08-25)

The next §8.25 action was implemented in the native C++ filter.  Adaptive can
now send one complete cloud per acknowledged map version once the observed map
commit age crosses a configurable pre-stale threshold.  This frame bypasses
the normal publication cap and bounded far-field path.  The source version is
latched, so a stalled map worker cannot receive repeated full scans for the
same version.  A later `commit_version > source_version` is recorded as a
version-advance ACK proxy with latency telemetry.  It is not a content-specific
acknowledgement or formal freshness certificate.  The executable default is
zero/off; the strict campaign runner uses 0.25 s.  Raw-cloud CIRI remains off.

Seed7 Adaptive threshold gates at 0.35 and 0.25 s both completed 3/3 with zero
contact.  The 0.35 s gate triggered at an observed mean age of 0.488 s and took
132.52 s/run.  The selected 0.25 s gate triggered at 0.403 s, reduced mean ACK
latency from 0.311 to 0.175 s and mean mission time to 102.68 s, at the cost of
more full refresh frames and a small map-cost increase.

The final order-crossed seed1-10 x n=3 x three-mode campaign produced 90/90
valid, one-attempt completions with retry/OOM/FSM-swap/PSI all zero.  Full and
Adaptive were each 30/30 with zero contact.  Fixed Sector completed 30/30 but
had two contact runs: one 6.08 m/s event on seed9 and two 6.98/6.90 m/s events
on seed10.  The paired Full and Adaptive rows on both maps had zero contact.

| mode | completion | contact runs (events) | mean time (s) | worst static clearance (m) | points/update | map total/update (ms) | FSM CPU (%) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Full | 30/30 | 0 (0) | 76.63 | +0.128 | 28,612 | 41.282 | 97.75 |
| fixed Sector | 30/30 | 2 (3) | 83.55 | +0.014 | 13,638 | 14.837 | 72.54 |
| Adaptive | 30/30 | 0 (0) | 103.26 | +0.195 | 23,204 | 31.434 | 62.35 |

Against Full, Adaptive reduced update-weighted points/update 18.90%, map
total/update 23.86%, and map update time 15.12%, but mean mission time grew
34.75%.  The 30 Adaptive rows emitted 2,369 pre-stale full frames and observed
2,369 version advances with no final pending ACK.  Frame-weighted trigger age
was 0.386 s and ACK latency 0.207 s, but maxima were 3.150 and 11.245 s.
Time-weighted direct guard duty rose from 33.8% on seed1 to 92.2% on seed10.
This long-tail ACK/guard behavior, not another lower threshold or higher
publication cap, is the next efficiency target.

The next design should attach a request/generation token to the full refresh,
close guard only after its content-specific ACK plus a successful fresh-map
replan, and use certified stop plus one topology-changing reroute when that ACK
misses a bounded SLA.  Do not blindly shorten the hold or flood repeated full
frames.  This is a local n=3 gate, not population 100% or flight-ready proof.
No McNemar test was performed; with only two discordant contact pairs, this
gate is descriptive and underpowered.  Complete map-level tables, contact forensics, memory interpretation,
and commands are in `docs/pre_stale_refresh_3mode_v7_n3_20260825.md`; raw inputs
are `results/prestale_seed7_adaptive_n3_raw_20260825.csv`,
`results/prestale025_seed7_adaptive_n3_raw_20260825.csv`, and
`results/prestale025_order_crossed_3mode_v7_n3_raw_20260825.csv`.

### 8.27 Exact generation ACK, certified resume, and bounded ACK-SLA stop (2026-08-25)

Section 8.26's version-advance proxy could not prove that the requested full
cloud was processed.  The native Adaptive filter now publishes a reliable
request token containing a monotonically increasing request sequence, the
exact `PointCloud2` source stamp, and the refresh kind.  ROG-Map publishes a
reliable processing ACK containing its scan sequence, that exact source stamp,
the map version after processing, and whether the scan changed the map.  An ACK
is emitted after every accepted scan, including a processed scan with no map
delta.  The filter executable defaults this handshake to off; the strict
Adaptive campaign enables it.

At a trajectory-guard edge, planner recovery now selects a post-edge full
request and refuses to leave the certified terminal hold until the exact
generation is ACKed, its map version is available, the map and odometry are
fresh, physical stop stability has held for 0.25 s, and a new `PlanFromRest`
candidate passes the existing trajectory certificate.  A best-effort cloud
can be lost after its reliable token arrives, so an unACKed target may be
superseded by the next full generation; pending state remains latest-only and
bounded.  A 0.75 s oldest-unresolved-request SLA enters the same certified
brake boundary instead of continuing normal publication.  A geometrically
rejected fresh candidate then arms the existing route blocker and searches a
different topology.  ACK loss alone does not invent an unsupported obstacle.
Planner and filter defaults remain off, and fixed Sector never advertises the
startup marker, so its runtime behavior is not gated.

The final seed6-10 x n=1 x three-mode gate produced 15/15 valid,
first-attempt completions with zero live contact and zero static-PCD collision.
Retry, OOM delta, FSM swap and memory PSI were all zero; minimum available host
memory was 4,138 MiB.

| mode | completion | contact | mean time (s) | worst static clearance (m) | points/update | map total/update (ms) | observed map Hz | FSM CPU (%) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Full | 5/5 | 0 | 84.00 | +0.214 | 36,973 | 35.713 | 4.71 | 82.71 |
| fixed Sector | 5/5 | 0 | 89.72 | +0.157 | 18,696 | 14.285 | 4.13 | 64.67 |
| Adaptive | 5/5 | 0 | 96.41 | +0.217 | 31,011 | 30.171 | 3.18 | 62.30 |

Against Full, Adaptive reduced update-weighted points/update 16.12%, map
total/update 15.52%, observed map update rate 32.47%, and time-weighted FSM CPU
24.68%, while mean mission time was 14.77% longer.  Across the same five maps,
total mapping point work and mapping wall work were 34.99% and 34.52% lower.
Adaptive effective full-open transitions were 28; direct guard transitions
were 22.  Guard duty nevertheless remained 79.60-94.68%, so this change fixes
freshness semantics and bounded failure behavior, not the repeated-guard cost.

Of 582 pre-stale full generations, 512 received their own exact ACK and 70 were
superseded, with final pending zero.  Exact delivered-generation ACK latency
was 0.0436 s count-weighted mean and 0.1034 s maximum.  Therefore 8.26's
11.245 s version-proxy tail was not the processing latency of a particular
full cloud; it mixed later/unrelated version progress with missing cloud
generations.  The old proxy still counted 582/582 version advances while exact
generation ACK counted only 512/582.  The SLA emitted 26 timeout markers for
unresolved chains.  All five runs
completed and all 225 armed recovery gates observed an exact ACK before
resume.  The Adaptive logs contained 41 topology arms and 54 topology
searches, but these are total guard-rejection recovery counts, not proof that
every ACK timeout needed a topology change.

The implementation was built sequentially after a parallel build filled the
2 GiB host swap and left only about 442 MiB available.  That event happened
during compilation, not the campaign.  The final campaign itself had zero
retry/swap/PSI/OOM.  A synthetic ROS smoke also proved that a wrong stamp does
not clear pending state and the exact stamp does.  This late-map n=1 gate is
descriptive only: it is not population 100%, flight-ready, or hard real-time
proof, and no McNemar test was performed.  Raw-cloud CIRI remains default
false and non-authoritative.  Full map tables and implementation details are
in `docs/generation_ack_certified_resume_v7_seed6_10_n1_20260825.md`; primary
raw input is
`results/generation_ack_final_3mode_seed6_10_n1_raw_20260825.csv`.

### 8.28 Reliable depth-1 filtered link reduces loss-driven guard work (2026-08-26)

Section 8.27 showed that delivered full generations ACKed within 0.1034 s but
70/582 generations were superseded without an exact ACK and 26 oldest-request
SLA timeouts occurred. Log attribution found 184 `main_pre MAP_STALE` events
and 225 guard/recovery episodes totalling 247.457 s. These events were not a
reason to weaken the freshness certificate. They identified loss on the
native filter-to-ROG-Map best-effort cloud hop.

A bounded retransmission candidate sent one newer full generation after a
missing ACK. Seed6-10 Adaptive n=1 remained 5/5 with zero contact and timeout
markers fell from 26 to 5, but full generations rose from 582 to 657, guard
gates from 225 to 258, stale detections from 184 to 223, active recovery time
from 247.457 to 291.722 s, and mean mission time from 96.408 to 104.306 s.
The extra scans increased map-worker contention, so the option remains
default zero/off and was not used in the final gate.

The adopted candidate instead makes only the internal `/cloud_sector` hop
reliable depth-1. ROG-Map's `cloud_reliable` and the native filter's
`--reliable-output` both default false. A new explicit
`_filtered_reliable.yaml` profile and runner flag enable them together; the
simulator-to-filter input remains best-effort. Fixed Sector and Adaptive use
the same link QoS. Existing profiles, full-refresh rate, exact ACK SLA,
certified resume conditions, and raw-CIRI's non-authoritative default-off
status are unchanged.

The fresh seed6-10 x n=1 x three-mode gate was 15/15 valid and first attempt.
Full and Adaptive were each 5/5 with zero live contact and zero static-PCD
collision. Fixed Sector completed 5/5 but had one live/static-PCD contact on
seed8; paired Full and Adaptive were contact-free.

| mode | completion | contact | mean time (s) | worst static clearance (m) | points/update | map total/update (ms) | observed map Hz | FSM CPU (%) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Full | 5/5 | 0 | 84.16 | +0.177 | 37,568 | 36.234 | 4.60 | 80.14 |
| fixed Sector | 5/5 | 1 | 83.94 | -0.079 | 19,497 | 14.330 | 4.53 | 71.33 |
| Adaptive | 5/5 | 0 | 86.02 | +0.193 | 31,040 | 30.981 | 3.39 | 67.90 |

Against Full, Adaptive reduced update-weighted points/update 17.38%, map
total/update 14.50%, map-update compute 6.93%, observed update rate 26.32%, and
time-weighted FSM CPU 15.28%; mean mission time was only 2.21% longer. Across
the five maps, mapping point work, mapping wall work, and FSM+filter
core-seconds were 37.78%, 35.61%, and 9.59% lower.

All 393 pre-stale full generations received their exact ACK, with zero
supersede, zero timeout, and final pending zero. ACK latency was 0.0468 s
count-weighted mean and 0.1357 s maximum. Versus the previous best-effort n=1
cohort, Adaptive mean time fell 10.78%, guard gates fell 225 to 195, stale
detections fell 184 to 164, and active recovery time fell 16.90%; Full's mean
time changed only +0.18%. This is directional, unpaired n=1 evidence, not a
population estimate or causal timing proof.

All final rows had retry/OOM/FSM-swap/PSI zero. The result is a local
regression gate, not population 100%, flight-ready, or hard real-time proof;
no McNemar test was performed. Detailed map tables, guard attribution, and
the rejected retry are in
`docs/reliable_filtered_link_guard_duty_v7_seed6_10_n1_20260826.md`. Primary
raw inputs are
`results/reliable_link_final_3mode_seed6_10_n1_raw_20260826.csv`,
`results/reliable_link_adaptive_seed6_10_n1_raw_20260826.csv`, and
`results/ack_retry_adaptive_seed6_10_n1_raw_20260825.csv`.

### 8.29 Reliable-link n=3 repetition, guard attribution, and rejected stationary defer (2026-08-26)

The reliable-link profile was repeated on seed6-10 x n=3 x all three modes.
All 45 rows were valid under the current runner, first-attempt, and free of
retry/OOM/FSM swap/memory PSI. Full and Adaptive were each 15/15 complete with
zero live contact and zero static-PCD collision. Fixed Sector was 13/15
complete with three contact runs and five contact events: seed7 run3 completed
with two events, while seed10 run1/run2 contacted and timed out. Mean mission
times were 84.85/101.57/82.31 s for Full/Sector/Adaptive; the Sector mean
includes both 240 s timeouts.

| mode | completion | contact runs/events | mean time (s) | worst static clearance (m) | points/update | map total/update (ms) | FSM CPU (%) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Full | 15/15 | 0/0 | 84.85 | +0.151 | 37,114 | 36.127 | 80.50 |
| fixed Sector | 13/15 | 3/5 | 101.57 | -0.188 | 32,689 | 12.055 | 58.98 |
| Adaptive | 15/15 | 0/0 | 82.31 | +0.160 | 31,610 | 30.655 | 73.75 |

Against Full, Adaptive reduced points/update 14.83%, map total/update 15.15%,
map-update compute 7.44%, observed map rate 22.49%, and time-weighted FSM CPU
8.38%. Across the 15 runs it reduced total mapping point work 35.97%, mapping
wall work 36.20%, and FSM+filter core-seconds 7.46%; mean mission time was
3.00% shorter in this cohort.

Adaptive emitted 1,274 pre-stale generations and received 1,273 exact ACKs,
with zero supersede and zero timeout. One seed6 generation remained pending at
shutdown. All 502 recovery gates received an ACK. The logs still contained
906 brake-rejection markers and 514.205 s of recovery-active time. Attribution
found 683 `emergency_stop_retry`, 168 `main_pre`, 44
`candidate_without_safe_follow`, 8 `main_post`, and 3 `replan_post` markers.
Using speed <=0.05 m/s only as a diagnostic proxy, 707/906 (78.0%) occurred
while stationary.

A fail-closed stationary fast-defer candidate skipped redundant map/grid work
for a zero-displacement candidate before the 0.25 s passive-stop stability
window elapsed. Three seed9 Adaptive samples remained contact-free but averaged
152.23 s versus the same-day baseline cohort's 85.64 s, so no benefit was
demonstrated. A fully reverted isolated smoke was also long at 213.05 s,
showing that the post-build isolated execution regime confounded causal
attribution. The candidate was conservatively rejected, its planner source was
restored byte-identical to the tracked baseline, and the installed binary was
rebuilt. Only the parser field for the rejected marker remains for
reproducibility.

One Full seed7 run reported 10.027 m/s despite the v=7 configuration. The
PerfectDrone copies planner command velocity into odometry, so this is not
just a monitor-side scalar artifact. Current `run_valid` does not enforce a
velocity bound. Therefore 15/15 is a completion/contact statement, not a
speed-constraint-valid or population-level guarantee. The next target is
context-rich speed-bound telemetry and a validated publication invariant,
followed by the same three-mode gate with speed-qualified validity. No
McNemar test was performed. Raw-cloud CIRI remains default false and
non-authoritative. Full tables and candidate/revert evidence are in
`docs/reliable_link_n3_and_stationary_defer_rejection_20260826.md`; primary raw
input is
`results/reliable_link_repeated_3mode_seed6_10_n3_raw_20260826.csv`.

### 8.30 Hard v7 publication bound, recovery-only ACK retry, and bounded multi-exit reroute (2026-08-26)

The speed-qualified follow-up to 8.29 found that its completion/contact-valid
headline was not velocity-valid. In Full seed7 run3, a fresh 6.323 m/s command
was first rejected as `UNOBSERVED`; 5.2 ms later the retry divided two odometry
positions by callback-selection time rather than their odometry receive time.
This fabricated `odom_motion=10.055 m/s`, certified a brake from that false
state, and published an observed 10.027 m/s command. PerfectDrone copies
`PositionCommand.velocity` into odometry, so this was not monitor
differentiation noise.

The fix establishes three publication boundaries:

- guarded candidates use the polynomial's exact maximum velocity before
  commit; finite over-limit candidates are time-scaled without changing the
  spatial path and checked again;
- emergency motion estimation uses `robot_state_.rcv_time`, and every brake is
  checked for exact maximum velocity plus sampled acceleration/jerk;
- polynomial and individual `PositionCommand` publication recheck the limit;
  a normal candidate violation enters the existing certified recovery instead
  of being published.

The old direct odometry-twist assignment remains reverted because 8.15 showed
that it caused a real seed10 contact. Runtime exact checks allow 0.1% numerical
slack and the monitor allows 0.01 m/s. Thus the gate is explicit and
speed-qualified, but it is not a mathematical claim that every message is
`<=7.000000` with zero tolerance.

The first seed6-10 x three-mode n=3 speed gate was 45/45 speed-valid and had
zero Full/Adaptive contact, but it exposed two independent liveness tails.
One Full seed10 run timed out after a certified stop because corridor failure
cleared its temporary zones and reseeded the same route. One Adaptive seed8
run took 166.68 s because the post-guard full generation was not taken by the
depth-1 subscriber and the next exact request arrived 84 s later. A
recovery-only, default-off `trajectory_guard_ack_retry_age_s` now resends one
latest full generation at a stop-and-wait cadence while the guard is already
fail-closed. It does not alter normal flight or pre-stale retry behavior.

A subsequent seed8 Adaptive n=5 received every exact ACK promptly but still
contained a 151.77 s run. The full ACK arrived in 0.042 s; the actual long
interval was 59.69 s of repeated stopped `PlanFromRest` topology. The single
stored `away-from-latest-collision` direction was unstable because optimizer
jitter moved the reported collision across the vehicle. The bounded local
recovery now enumerates the stored direction, its opposite, and the two
perpendicular horizontal exits exactly once. Every exit is passed through the
unchanged velocity, geometric, map-freshness, and viability commit gates; only
the first certified direction can be published, otherwise the existing
vertical/certified reroute continues.

After that change, seed8 Adaptive n=5 completed 5/5 with zero contact/static
collision and 5/5 speed-valid. Time was 70.40-91.47 s (mean 81.21 s) and the
maximum continuous recovery interval was 2.52 s. The four-way branch did not
execute in those five samples, so this is regression evidence, not branch
proof.

The final same-binary map1-10 x Full/Sector/Adaptive x n=1 gate completed all
30/30 runs on the first attempt. Live contact, static-PCD collision, speed
invalid, OOM, and infrastructure retry were all zero. Mode means were:

| Mode | Complete | Contact | Speed-valid | Mean time (s) | Worst static body clearance (m) | Max command (m/s) |
|---|---:|---:|---:|---:|---:|---:|
| Full | 10/10 | 0 | 10/10 | 71.04 | +0.174 | 7.005352 |
| fixed Sector | 10/10 | 0 | 10/10 | 72.05 | +0.196 | 7.005983 |
| Adaptive | 10/10 | 0 | 10/10 | 78.89 | +0.175 | 7.005280 |

Update-weighted points/update were 28,793/14,797/25,083 and update time was
13.57/4.76/11.39 ms for Full/Sector/Adaptive. In this n=1 descriptive cohort,
Adaptive reduced Full points/update by 12.88%, total/update by 22.91%, map
update time by 16.09%, and FSM+filter core-seconds by 8.86%, while taking
11.04% longer. Adaptive entered effective full view 123 times across 241 guard
episodes. Its 241/241 recovery full generations received exact ACK, with zero
supersede/retry/abandon and maximum ACK latency 0.101465 s.

The corridor-failure epoch-reset branch executed once in map7 Adaptive and a
new trajectory committed about 0.64 s later. The event was not start-adjacent,
so the new four-way local-exit branch did not execute. Likewise the 0.75 s ACK
retry never triggered because every exact ACK arrived earlier. These two paths
therefore have build and broad non-regression evidence but no live trigger
proof in the final cohort.

Source changes are mirrored under `super_patches/native_seedmap_campaign/` for
`super_planner.h`, `super_planner.cpp`, `fsm_ros2.hpp`, and
`native_sector_cpp.cpp`. The campaign runner now parses the configured maximum
velocity, records 3-D command/odometry context, and makes speed validity part
of `run_valid` rather than masking it as infrastructure retry. The ROS build
passed with only the pre-existing constructor reorder warning; 12 Python tests
and `py_compile` passed. Full details and map-labelled tables are in
`docs/guarded_velocity_bound_v7_20260826.md`; final raw data is
`results/final_multiexit_3mode_seed1_10_n1_raw_20260826.csv`.

This section does not claim population 100%, hardware/flight readiness, or a
zero-tolerance velocity theorem. McNemar was not run, and the final n=1 cohort
cannot establish the intended population difference between Sector and
Adaptive. Raw-cloud CIRI remains default false and non-authoritative. The known
handoff corrections also remain in force: `obs_skip_num` is operationally a
no-op in the investigated path, NaN handling and clearance-penalty design
issues are not evidence for this result, `BackupTrajOpt` must not be described
as fully covered by an EXP-only argument, and `DRONE_R=robot_r` alone is not a
sufficient clearance metric.

## Current status — final three-mode DDA gate passed locally

- **Section 8.32 is the newest broad evidence and measurement correction.** On
  the final DDA/body-coordinate binary, map1-10 x Full/Sector/Adaptive x n=3
  gave Full 30/30 and Adaptive 30/30 with zero live/static contact, while fixed
  Sector was 29/30 with three contact runs and 27/30 safety-qualified
  completions. All 90 rows were speed-valid and first-attempt. Adaptive reduced
  Full points/update 17.22% and total/update 20.70% over 29 matched metric pairs,
  and time-integrated FSM+filter CPU work 11.66% over all 30 runs, while mean
  mission time increased 5.91%. A large-map performance-log generation race
  was fixed and directly revalidated on map10; it affected one computation
  row, not flight outcome. This is still local n=3 evidence, not population or
  flight-readiness proof.

- **Section 8.31 is the newest code and local regression evidence.** The
  recovery-only ACK retry, four-way local escape, and initial-footprint egress
  now have deterministic fault-injection branch proof. A pre-fix n=5 campaign
  exposed one Adaptive timeout, and a later natural map8 failure identified a
  coordinate bug: inflated-grid DDA cell centres were being reused as robot
  centres for the raw physical-body test. Physical clearance now uses the
  closest polynomial-chord projection, while the DDA coordinate remains the
  inflated-map query. The final map8-10 Full/Adaptive n=3 gate passed 18/18,
  contact 0, speed-valid 18/18, retry 0. This supersedes 8.30's statement that
  those rare branches lack direct execution proof, but still is not a
  population or flight-readiness guarantee.

- **Section 8.30 is the newest same-binary speed-qualified gate.** Map1-10
  Full/Sector/Adaptive completed 30/30 with zero live/static contact and 30/30
  speed-valid. The targeted seed8 Adaptive follow-up was also 5/5 with a
  2.52 s maximum recovery interval. This is a local regression result, not a
  population guarantee.
- **The stationary fast-defer candidate is rejected and fully reverted.** It
  did not demonstrate an efficiency benefit, and a reverted isolated smoke
  exposed a confounded guard long tail. Keep the existing certificate ordering
  until the execution regime is controlled.
- **The observed v7 publication hole is closed locally.** Exact candidate and
  brake velocity checks, odometry receive-time motion estimation, publish
  boundary checks, and speed-qualified `run_valid` are implemented. The next
  blocker is live trigger proof for the recovery-only ACK retry and four-way
  local escape, followed by repeated population evidence.

- **Section 8.28 remains the reliable-link n=1 adoption gate.** Full and Adaptive
  each passed seed6-10 5/5 with zero contact; fixed Sector completed 5/5 but
  contacted seed8 once. Reliable depth-1 on the filtered internal hop removed
  all 8.27-style generation loss in this sample without increasing cloud
  publication count.
- **The pre-stale retransmission approach is rejected.** It reduced timeout markers but
  increased scans, stale detections, guard episodes, recovery time, and mission
  time. Keep its age at default 0/off; do not use scan flood to mask link loss.
  Section 8.30's separate recovery-only stop-and-wait option is also default
  off; it was enabled at 0.75 s for the final gate but never triggered because
  exact ACK latency stayed below 0.102 s.
- **The repeated-evidence and first attribution steps are complete.** Section
  8.29 found 906 rejection markers, 78.0% at diagnostic stationary speed, but
  also showed that changing this timing-sensitive path without a controlled
  execution regime is not justified. Guard efficiency remains a later target
  after velocity validity.

- **Section 8.27 remains the exact freshness/certified-resume mechanism.** Its
  best-effort transport gate passed all three modes 5/5 with zero contact.
  Exact generation ACK, certified fresh-map resume, and a bounded ACK-SLA stop
  remain implemented and unchanged by 8.28. Its 70 superseded generations and
  26 SLA timeouts are the counterexample that motivated the reliable internal
  link, not current reliable-profile counts.

- **Section 8.26 remains the larger n=3 comparison.** Full and Adaptive each passed
  30/30 with zero contact; fixed Sector completed 30/30 with contact on seed9
  and seed10.  The §8.25 Adaptive seed7 first-brake contact did not recur.
- **Section 8.24 remains the direct-edge mechanism and its earlier local gate.**
  It closed the observed gap between repeated guard episodes, but section 8.25
  supplies a new first-brake counterexample and supersedes the claim that the
  remaining issue was efficiency only. Section 8.26 adds the earlier sensing
  action that closes that observed counterexample in the current local sample;
  section 8.27 then makes that sensing evidence generation-specific.
- **The local horizontal escape is bounded and has deterministic execution
  proof.** Section 8.31 forced one first-direction skip and committed a
  remaining certified direction successfully. It may be tried once after a
  certified stop and A* `NO_PATH`; it never bypasses the existing
  guard/viability commit checks. It had zero natural commits in 8.32.

- **Section 8.23 remains the endpoint-invariant smoke gate:** the current/first/terminal
  pose raw-body invariant is implemented, and Full/Adaptive were both 10/10
  safe while Sector was 9/10 safe with one non-contact timeout. The rare Full
  endpoint reject did not execute, so 8.23 is not population or branch proof.
- **Section 8.22 remains the larger order-crossed n=50 reference:** Adaptive
  reduces Full points/update 32.61%, throughput 63.71%, mapping/update 44.23%,
  mapping work/mission 63.25%, and combined CPU-work/mission 16.13%, with a
  22.35% time penalty. Section 8.23's n=1 directionally narrowed that penalty
  to 18.16%, 8.27's late-map-only n=1 measured 14.77%, and the newest 8.28
  reliable-link n=1 measured 2.21%; none supersedes the n=50 estimate.
- **The memory fix now has broad evidence:** all 150 rows have one attempt,
  FSM swap 0, retry 0, OOM delta 0, and PSI max 0; peak FSM RSS is 3474.36 MiB.
  Host-wide swap was still occupied, but it did not recreate the prior FSM
  pressure or contaminate the crossed comparison.
- **The earlier broad repetition remains §8.26:** seed7 targeted n=3 and a new
  order-crossed seed1-10 x three-mode n=3 both completed. Section 8.27
  implements its generation-specific acknowledgement target on the harder
  seed6-10 subset. Section 8.28 removes the observed filtered-hop loss locally
  and shows that blind retransmission makes guard work worse. Section 8.29
  repeats that adopted link and rejects an unproven guard micro-optimization.
  Section 8.30 then adds speed-qualified publication and bounded stopped
  recovery. Section 8.31 supplies direct trigger proof and 8.32 supplies the
  final-binary repeated local gate. The remaining target is independent
  repetition with varied maps/noise, not a higher publication rate or weaker
  ACK SLA.

- **Executor threading (8.1), unknown-space tracking scoped to the brake
  (8.2), the EMER_STOP fix (8.5), guard-corridor retry alternation (8.9),
  async CIRI shadow capture (8.11), and certified stop-and-reroute (8.12)
  are all in place in the current configuration.** 8.3 and 8.4's variants
  are fully reverted; do not re-apply the write-side splat, the old
  collision-centred/brake-triggered sphere arming, or an authoritative
  raw-CIRI brake policy. Section 8.12's live recovery is materially different:
  it arms only after the existing brake, fresh-map, odometry, and stable-hold
  checks certify a stopped recovery boundary. 8.9's rejected attempt to widen
  `cg_guard_retry_ptr_`'s CIRI margin also remains reverted.
- **The 8.8 n=10 table (100 runs, 74/100) measures the pre-8.9
  configuration** -- it does not have the guard-corridor retry alternation.
  8.9's n=5 sweep (50 runs, on top of the 8.9 config) got 41/50 (82.0%),
  directionally better but *not* statistically distinguishable from 8.8's
  74/100 at this sample size (p=0.31) -- see 8.9 before citing either
  number as "the" completion rate. Do not re-cite the earlier 48/50 n=1
  headline as representative either way.
- **Safety remains the strongest result in the earlier validated cohorts:
  0/170 contact across the three
  committed aggregate cohorts** (100 runs in 8.8, 50 in 8.9, and 20 in
  8.12). Section 8.12's worst static-PCD centre distance was 0.372 m. These
  are different configurations and should not be pooled for a completion
  estimate, but none traded the liveness work for measured contact.
  **Do not add 8.13's 150 runs to this safety total:** its requested static-PCD
  option was inactive due to a command-line delimiter bug, and two
  mode-dependent live-cloud contact markers were observed.
- **The requested local gate passed once but did not reproduce as a
  deterministic guarantee:** 8.12 had 5/5 consecutive seed10 full
  completions and the broader seed1-10 n=2 check was 20/20. In 8.13's longer
  interleaved campaign, seed10 full was 4/5 and total full was 48/50. Section
  8.15 then passed seed9/10 at 10/10, but the same-code 8.16 regression found
  full failures on seeds 3, 6, 7, and 9 and one sector failure on seed9. The
  specific stale-command deadlock is fixed, but population liveness is not.
- The frequent same-generation `PlanFromRest` deadlock diagnosed in 8.7/8.8
  has an implemented recovery after a certified stop, but 8.14 proves that
  this recovery is unreachable when every brake attempt itself is rejected.
  The old reproduced seed10 failure held one generation for 75.404 s; section
  8.12's seed1-10 n=2 maximum was 1.467 s, while 8.14 found new 30.614 s and
  98.871 s stalls with zero topology-arm events. The new state transition
  changes XY topology after a certified stop; it does not solve acquisition of
  that stop from a stale cached command.
- **4th paper-reproduction attempt (8.10), with the async completion in
  8.11, now works without the earlier shadow-specific throughput collapse.**
  `trajectory_guard_raw_cloud_ciri_shadow_en` (off by default, only on in
  `_cirishadow.yaml`) computes and logs what the paper's actual theorem-1
  mechanism would conclude, with zero ability to affect flight behavior.
  The accumulated-cloud fetch, conversion/downsampling, CIRI decomposition,
  and containment check now run on a latest-only worker, and shadow-only scan
  capture reuses ROG-Map's already-accepted message instead of adding a second
  DDS subscription. Section 8.11's 19/20 result establishes removal of the
  8.10 performance regression. Section 8.12 then fixes that cohort's one
  remaining seed10 liveness failure in the live topology-recovery layer; it
  still does not grant the shadow result any authority over brake decisions.
- **Section 8.15 supersedes 8.14's unresolved stale-command status; section
  8.17 supersedes both its local completion headline and 8.16's broad but
  non-strict ablation, while section 8.18 supersedes only 8.17's Adaptive
  liveness result.** The stale
  command is freshness/consistency gated, recovery uses a brake-local
  position-derived motion estimate, blockers are branch-aware and epoch
  bounded, backup-only rejections do not corrupt EXP topology, and stale-map
  replanning is readiness-gated. The final same-code local gate completed
  seed9 and seed10 5/5 each with 0/10 measured static-PCD contact. The broader
  strict baseline plus follow-up result is now 50/50 Full, 50/50 fixed Sector,
  and 50/50 Adaptive in raw completion, or 50/50, 46/50, and 50/50 in
  safety-qualified completion. Adaptive is a separate follow-up campaign,
  not a paired third arm of the original cohort.
  This does not retroactively repair 8.13's missing static-PCD data and must
  not be presented as population or hardware proof.
- Section 8.17's time-weighted FSM CPU was 47.55% Full, 47.11% Sector, and
  42.06% Adaptive on the current machine. The filter added 11.00%/11.36% for
  Sector/Adaptive. These figures are cohort- and machine-specific, not a
  guaranteed scheduler budget.
- The `VIABILITY_DEBUG` and `AVOIDANCE_DEBUG` diagnostic logging left in
  `super_planner.cpp`/`corridor_generator.cpp` is harmless when the env
  vars are unset but has not been cleaned up.

Do not describe `static_seedmaps_guard_viability_v7.yaml` or any of its
`_wide`/`_tight`/`_tight_h08` variants as flight-ready. The current strict
baseline and section 8.22 establish the intended descriptive
safety/mapping-work pattern and a clean order-crossed CPU/workload reduction,
but not population completion or flight readiness. Sections 8.23 and 8.24 close
the observed Full endpoint and between-episode guard-gap holes, while section
8.25 exposes the distinct first stale-map brake timing hole. Section 8.26's
pre-stale refresh closes that observed contact in the current seed7 and n=3
local gates. Section 8.27 replaces its version proxy with exact generation ACK,
requires a fresh certified replan before resume, and enters certified stop on a
bounded ACK miss. It also proves that the old 11.245 s tail was not exact cloud
processing latency, while exposing real best-effort cloud loss and persistent
79.60-94.68% late-map guard duty. Section 8.28 closes that observed filtered-hop
loss in a local n=1 gate with an opt-in reliable depth-1 link; it does not
replace the larger repeated evidence. The next target is a repeated
map-labelled gate, then bounded reduction of guard rejection and stop/replan
work without weakening the ACK gate or safety certificate. Retain the
static-PCD monitor, live-cloud forensics, fixed-Sector control, and CIRI
shadow's non-authoritative default-off status.

### 8.31 Deterministic recovery proof and DDA/body-coordinate correction (2026-08-26)

The recovery-only exact-generation retry and stopped four-way local escape
were first made directly testable. A native C++ test flag drops one requested
trajectory-guard full cloud exactly once; map8 Adaptive then completed in
72.76 s with drop/retry 1/1, exact ACK commit 32, supersede 1, abandon 0,
contact 0 and valid v7 speed. A separate environment fault arms one stopped
local escape and skips its first direction; the remaining certified direction
committed, and map8 completed in 86.45 s with contact 0 and +0.261 m static
clearance. Both hooks are default-off and have no production authority.

The following same-binary map1-10 x Full/Sector/Adaptive x n=5 campaign
completed Full 50/50, fixed Sector 50/50 and Adaptive 49/50. Full had zero
live/static contact. Fixed Sector had 4 live-contact runs (10 events), 3
static-collision runs (3 events), and 46/50 safety-qualified completions.
Adaptive had zero contact but one map10 run4 timeout at waypoint 0/5, despite
+0.041 m static clearance; it issued 16 topology arms and 440 reroute searches.
The corresponding mean times were 73.22/74.69/81.29 s. This was the desired
Sector safety degradation, but not yet acceptable Adaptive liveness.

The campaign also had one infrastructure-contaminated Full map2 row: two
`no odom samples` retries while host available memory fell to 390 MiB, swap
occupancy reached 2 GiB, cgroup swap reached 1.53 GiB and memory PSI was high.
The accepted planner attempt had no OOM delta and zero FSM swap. Inspection
found 17,452 stale Fast-DDS shared-memory files occupying about 4.5 GiB in
`/dev/shm`; removing only entries older than ten minutes restored launch
reliability. The final post-fix gate had retry 0, so this is classified as
accumulated test-infrastructure state rather than a Full algorithm failure.

The first validator correction replaced robot-radius shell voxel lookup with
direct occupied-voxel-centre distance, matching the static-PCD contact oracle.
Map10 Adaptive passed 5/5 afterward, but a broad n=1 run still left map9
Adaptive stopped at waypoint 4/5 with contact 0 and +0.108 m static clearance.
An initial-footprint egress exception then passed forced injection and map9
3/3, but a new map8 Adaptive run reproduced a 240 s stop at waypoint 2/5. Its
online live-cloud marker reported one contact while static PCD reported no
collision and +0.074 m clearance. All four local directions were rejected.

The exact root cause was that one `map_queries` stream mixed polynomial robot
centres with inflated-grid DDA cell centres. The latter were passed to the raw
body-distance query as though the robot actually occupied that cell centre,
adding an artificial half-voxel displacement. Each query now carries both the
map coordinate and the closest projection on the sampled polynomial chord.
Inflated occupancy uses the DDA coordinate; physical body clearance uses the
projected trajectory centre. The initial-footprint mask additionally requires
the candidate not to move closer to any cell already inside the stopped body,
and all existing bounded-window, continuous-free-tail, version, velocity and
commit checks remain authoritative.

Forced footprint injection then passed map8 1/1 with injection/egress commit
1/1, contact 0, +0.273 m static clearance and valid speed. Natural map8
Adaptive repetition passed 5/5, contact 0, mean 86.32 s and minimum static
clearance +0.227 m. The final order-rotated map8-10 Full/Adaptive n=3 gate
passed all 18/18 on the first attempt with contact 0 and valid speed:

| Map | Mode | Complete | Mean time (s) | Worst static clearance (m) | Points/update | Total/update (ms) | FSM CPU (%) | Adaptive arm/open |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 8 | Full | 3/3 | 70.04 | +0.244 | 34,514 | 41.39 | 103.19 | 0/0 |
| 8 | Adaptive | 3/3 | 81.29 | +0.256 | 28,554 | 32.17 | 72.60 | 2/1 |
| 9 | Full | 3/3 | 91.91 | +0.204 | 41,873 | 36.40 | 79.75 | 0/0 |
| 9 | Adaptive | 3/3 | 92.11 | +0.197 | 36,667 | 30.62 | 70.42 | 1/3 |
| 10 | Full | 3/3 | 93.63 | +0.150 | 41,867 | 36.63 | 74.12 | 0/0 |
| 10 | Adaptive | 3/3 | 91.84 | +0.178 | 36,070 | 31.21 | 73.89 | 1/0 |

Across those dense maps, Adaptive reduced Full points/update 14.34%, map
total/update 17.85%, and FSM CPU 15.62%, while mean mission time increased
3.78%. Mean kept percentage was 63.96%, and full-view arm/open transitions
were 4/4. The ROS build passed with only the pre-existing constructor reorder
warning; source/mirror pairs are byte-identical; `py_compile` and 13 Python
tests pass.

Full implementation notes, the complete pre-fix map-labelled n=5 table and
claim boundaries are in
`docs/guard_recovery_egress_projection_v7_20260826.md`. Final raw data is
`results/dda_projection_dense_full_adaptive_n3_raw_20260826.csv`; focused and
forced raws use the matching `dda_projection_*` names. Raw-cloud CIRI remains
default false, shadow-only and non-authoritative. McNemar was not run, and
this local n=3 result does not establish population 100% or flight readiness.

### 8.32 Final map1-10 three-mode n=3 gate and performance-generation fix (2026-08-26)

The fresh final-binary, order-rotated map1-10 x Full/Sector/Adaptive x n=3
campaign completed 90 rows. Full and Adaptive each completed 30/30 with zero
live contact, zero static-PCD collision and 30/30 valid v7 speed. Fixed Sector
completed 29/30, had live contact on 3 runs/6 events and static collision on
3 runs/3 events, and was safety-qualified on 27/30. Its map9 run2 contacted
and timed out at 300 s. The corresponding mean times, including that timeout,
were 71.67/79.41/75.91 s.

The paired map9 evidence was especially direct. Run1 Sector completed with
-0.160 m static clearance, while Adaptive completed in 84.73 s with contact 0
and +0.282 m clearance. Run2 Sector contacted and timed out, while Adaptive
completed in 89.74 s with contact 0 and +0.265 m clearance. Full remained
30/30 and contact-free, so the requested Full baseline, degraded fixed-Sector
control, and Adaptive recovery pattern all occurred in the same cohort.

One Full map10 computation row was empty although its flight evidence was
valid: `perf_row_start=472` and `perf_row_end=446`. ROG-Map opens the shared
performance CSV with truncation during initialization, and the large map can
finish initialization after the runner's fixed four-second delay. The runner
now waits for a changed performance-log generation with a valid header,
requires a positive row window, and snapshots the per-attempt CSV before
teardown. A post-fix map10 three-mode n=1 gate had generation/window valid
3/3, completion 3/3, contact 0 and speed-valid 3/3.

Over the 29 matched broad rows with complete per-update data, Adaptive reduced
Full points/update 17.22%, map total/update 20.70%, update time 13.03% and FSM
CPU 19.12%. Over all 30 runs, time-integrated FSM+filter CPU work fell 11.66%
and mean mission time increased 5.91%. Adaptive retained 58.80% of input
points and recorded 321 effective full-view opens. The fixed instrumentation
smoke independently measured map10 point/update and total/update reductions of
11.98% and 10.75%; its n=1 time/CPU observation does not replace the n=3
estimate.

All broad and instrumentation rows were first-attempt, retry 0, OOM delta 0
and FSM swap 0. `py_compile` and all 19 native-campaign tests pass. Detailed
map-labelled tables, transition definitions, measurement analysis and raw
paths are in `docs/final_dda_projection_3mode_n3_20260826.md`.

This local result does not establish population 100%, hardware flight
readiness or formal collision freedom. McNemar was not run. Raw-cloud CIRI
remains default false, shadow-only and non-authoritative. The `obs_skip_num`
no-op, NaN/clearance-penalty design defects, BackupTrajOpt coverage limitation
and `DRONE_R=robot_r` metric limitation remain outside this correction.

### 8.33 Independent final-binary n=5 generalization gate (2026-08-27)

A fresh order-rotated map1-10 x Full/fixed-Sector/Adaptive x n=5 campaign
completed all 150 requested rows. It reused neither the preceding n=3 rows nor
their broken computation window. Every row was first-attempt, speed-valid,
performance-generation-ready and performance-window-valid.

Full completed 50/50 with zero live/static contact. Fixed Sector completed
49/50, had one live-contact run/two events, one static-collision run/one event,
and was safety-qualified on 48/50. Adaptive completed 50/50 with zero
live/static contact. Mean times including the Sector timeout were
76.26/75.50/75.10 s; medians were 70.76/71.02/74.56 s. Full's mean contains a
293.79 s long tail, while Adaptive's maximum was 96.30 s.

The paired mechanism evidence occurred on two different maps. Map7 run1
Sector stopped after waypoint 4/5 and timed out at 300.01 s with no contact;
paired Adaptive completed in 80.80 s and opened full view ten times. Map8 run1
Sector completed but made two live contact events and one static collision,
with -0.170 m worst static clearance; paired Adaptive completed in 69.67 s,
contact-free at +0.286 m, with 13 effective opens. The prior n=3 map9 contact
did not repeat in this n=5 cohort, so the degradation is trajectory-dependent
rather than deterministic per seed.

All 50 Full/Adaptive computation pairs are valid. Adaptive reduced Full
points/update 16.41%, map total/update 19.31%, occupancy update time 11.74%,
FSM CPU 17.49%, and time-integrated FSM+filter CPU work 13.33%. It retained
59.73% of points and made 534 effective full-view transitions (10.68/run).
Underlying stall, replan-guard and trajectory-guard counters overlap and must
not be summed. Exact-generation delivery remained closed: trajectory-guard
ACK commit was 1,336/1,336 and pre-stale ACK commit 3,656/3,656, with zero
retry, pending, supersede, abandon or timeout.

One separate Full liveness tail remains. Map8 run2 repeatedly received guarded
A* `NO_PATH` while stopped, accumulated 154 topology arms and 363 searches,
then recovered and finished in 293.79 s, 6.21 s before timeout. Paired Adaptive
finished in 81.30 s after two arms/two searches. This did not lower Full's
observed completion rate, but it prevents describing Full timing as robust and
is the next engineering target.

This section also corrects the earlier "McNemar not run" gap. In the
independent n=5 cohort, exact paired safety discordance was 2:0 with two-sided
`p=0.5`. Supplementarily pooling the same-binary n=3+n=5 cohorts gives Full
80/80, Sector 75/80 and Adaptive 80/80 safety-qualified completion; exact
discordance 5:0 gives `p=0.0625`. The direction is consistent but not yet
significant at 0.05. Full/Adaptive 50/50 has a 95% Wilson lower bound of
92.87%, not population 100%.

There was no infrastructure retry or OOM, accepted FSM swap stayed 0, minimum
available host memory was 4.65 GiB, and sampled memory PSI was 0. `py_compile`,
13 unittest cases and 19 pytest cases pass. Full map tables, intervals,
transition accounting, paired counterexamples and claim boundaries are in
`docs/final_generalization_n5_20260827.md`; raw data is
`results/final_generalization_3mode_seed1_10_n5_raw_20260827.csv`.

The next engineering step is to bound or reuse certified topology information
in the stopped Full search without weakening the certificate. The next
experimental step is a preregistered held-out map/noise cohort. Raw-cloud CIRI
remains default false/non-authoritative, and the `obs_skip_num` no-op,
NaN/clearance-penalty defects, BackupTrajOpt gap and `DRONE_R=robot_r` metric
limitation remain unchanged.

### 8.34 Goal-ordered bounded recovery and final three-mode n=3 regression (2026-08-27)

The map8 Full 293.79 s tail was traced to recovery-state lifetime rather than
an unsafe certificate: every short certified escape commit cleared the entire
topology state and re-armed the same local/vertical recovery budgets. Recovery
budgets now belong to a stopped-location episode. A short commit clears only
pose-specific blockers and pending actions; budgets reset for a new mission
goal or after 2.0 m horizontal progress. Local escape enumerates eight
horizontal alternatives in current-waypoint progress order, and local versus
vertical arming is mutually exclusive. The existing trajectory and sampled
stop-viability certificates remain authoritative.

An intermediate maps7-10 Full/Adaptive n=3 gate rejected the first version:
map10 Adaptive run3 timed out at 300.01 s after a safe but goal-opposed local
step, 121 arms, 357 searches and 116 epoch resets. After goal ordering and
sequential budget consumption, a focused map10 Adaptive n=5 gate completed
5/5 first-attempt and contact-free, with maximum 98.61 s, 12 arms and 26
searches. The final maps7-10 Full/Adaptive n=3 gate completed 24/24
first-attempt, contact-free and speed-valid.

The final order-rotated map1-10 x Full/fixed-Sector/Adaptive x n=3 campaign
completed all 90 rows on the first attempt, with retry/OOM 0 and speed-valid
90/90. Full and Adaptive were safety-qualified 30/30. Fixed Sector was 29/30:
map9 run1 completed but recorded two live contacts, one static collision and
-0.107 m static clearance. Full and Adaptive had zero live/static contact and
worst static clearances of +0.195/+0.188 m.

Adaptive versus Full reduced points/update 14.52%, map total/update 21.68%,
occupancy update time 14.60% and FSM CPU 19.48%; mean mission time increased
7.93%. Adaptive made 323 effective full-view opens (10.77/run). Fixed Sector
reduced points/update 47.74% and map total/update 62.42%, but supplied the one
unsafe run. The current n=3 paired safety discordance is only 1:0, so exact
two-sided McNemar is `p=1.0`; 30/30 has a 95% Wilson lower bound of 88.65%, not
population 100%.

One infrastructure anomaly occurred in the preceding map8 Full n=10 gate: a
single process grew from about 3.0 to 9.1 GiB RSS while host swap was full and
was OOM-killed, then its retry completed normally. Other attempts stayed near
3.3-3.5 GiB and the final 90-run campaign had OOM/retry 0. The allocation
source remains unresolved, but neither batch accumulation nor topology count
explains it directly.

The final build, `compileall`, 13 unittest cases and 19 pytest cases pass.
Detailed chronological evidence, map-labelled tables and raw paths are in
`docs/goal_ordered_recovery_final_n3_20260827.md`; the final raw campaign is
`results/goal_ordered_final_3mode_seed1_10_n3_raw_20260827.csv`. Raw-cloud CIRI
remains default false/non-authoritative. The `obs_skip_num` no-op,
NaN/clearance-penalty defects, BackupTrajOpt coverage gap and
`DRONE_R=robot_r` metric limitation remain outside this change.

### 8.35 Native-filter async scheduling optimization and threshold rejection (2026-08-27)

The remaining Adaptive time tail on maps9-10 was concentrated in repeated
`MAP_STALE -> certified brake -> fresh-map replan` cycles. A direct attempt to
shorten the trajectory-guard hold from 2.5 s to 0.5 s was rejected: map9
completed 3/3 without contact, but the first map10 run completed with two live
contacts, one static-PCD collision and -0.157 m static clearance. The first
contact occurred 1.676 s after the shortened hold closed. No safety profile or
default contains that candidate value.

The accepted change preserves all hold, FOV, clearance, exact-generation ACK,
certified-resume and velocity thresholds. The native C++ filter's DDS input
callback now only replaces a bounded pending cloud and returns. A dedicated
worker performs point filtering, state update and reliable publication. Its
pending queue is latest-only, shutdown drops the pending item and joins the
worker, and all mutable filter/guard/ACK state remains serialized under one
mutex. New counters expose input callbacks and worker overwrites.

A maps9-10 Adaptive n=3 gate completed 6/6 first-attempt, contact-free and
speed-valid. Relative to the preceding same-config n=3 observation, mean time
fell from 102.87 to 88.01 s (-14.45%), brake count from 51.50 to 35.17 per run
(-31.72%), and recovery-active duration from 54.60 to 41.08 s (-24.77%). The
minimum static clearance was +0.193 m. Trajectory-guard ACK was 211/211 and
pre-stale ACK 522/522, with zero timeout, abandon, supersede or retry.

The subsequent map1-10 x Full/fixed-Sector/Adaptive x n=1 regression completed
all 30 rows on the first attempt. Every row was live/static-contact-free and
speed-valid. Mean Full/Sector/Adaptive times were 72.08/70.85/72.86 s. In this
small broad gate, Adaptive versus Full reduced points/update 13.72%, map
total/update 18.76%, occupancy update time 10.49%, FSM CPU 15.23% and
time-integrated planner-plus-filter CPU work 10.92%, while mission time rose
1.09%. Adaptive opened full view 108 times. The preceding n=3 Sector map9
contact remains the fixed-Sector control evidence; this clean n=1 does not
reclassify Sector as safe.

Input callbacks equalled processed frames and worker overwrites were zero in
all accepted filter rows. The observed gain therefore cannot be attributed to
discarding large numbers of scans; it is consistent with changing the
scheduling boundary around DDS input and reliable output. Because the old and
new n=3 cohorts were not interleaved paired A/B, the 14.45% wall-time change is
not claimed as a precise causal effect. Map8 Adaptive also remained 17.07 s
slower than Full in the broad n=1 run, so timing variance is not eliminated.

The ROS build, synthetic Python/C++ geometry equivalence, `compileall`, 13
unittest cases and 19 pytest cases pass; source and mirror are byte-identical.
There was no retry, OOM, FSM swap or memory PSI in the accepted 36 runs. Full
tables and claim boundaries are in
`docs/native_filter_async_latest_optimization_20260827.md`; raw files are
`results/adaptive_async_latest_seed9_10_n3_raw_20260827.csv`,
`results/async_latest_3mode_seed1_10_n1_raw_20260827.csv`, and the rejected
`results/adaptive_hold05_seed9_10_n3_raw_20260827.csv`.

This evidence does not establish population 100%, formal collision freedom or
hardware flight readiness. Raw-cloud CIRI remains default false and
non-authoritative. The `obs_skip_num` no-op, NaN/clearance-penalty defects,
BackupTrajOpt coverage gap and `DRONE_R=robot_r` metric limitation remain
unchanged.

### 8.36 Processed-payload bandwidth and base-NO_PATH local escape (2026-08-27)

ROG-Map now records the `PointCloud2.data.size()` and `point_step` of every
frame selected for a map update. The campaign runner derives update frames/s,
points/s, MiB/s and Mbit/s over the mission window. This is processed
application-payload throughput: it excludes DDS/RTPS overhead, retransmission,
metadata and latest-only frames overwritten before map update, and must not be
described as host-NIC or wireless-link bandwidth.

A map1-10 x Full/fixed-Sector/Adaptive x n=1 baseline gave mean processed
payloads of 5.077/1.977/2.748 MiB/s. Equal-weight per-map reductions versus
Full were 64.44% for Sector and 49.02% for Adaptive. Full completed 10/10 and
was contact-free; Sector completed/contact-free 9/10; Adaptive completed 9/10
but was contact-free 10/10. Map9 Sector contacted and timed out, while map9
Adaptive timed out without contact. The latter stayed full-open for 92.19% of
the run and reached 7.324 MiB/s, so its high payload was a consequence of the
long recovery rather than evidence of bandwidth starvation.

The map9 Adaptive failure stopped after waypoint 2/5 with +0.141 m static
clearance. All 13 full-refresh generations were exact-ACKed. After one
certified horizontal escape, base A* returned `NO_PATH`; the one vertical lift
was rejected by the unchanged clearance guard; then the old state machine
entered permanent certified hold despite remaining horizontal escape budget.
It repeated the same A* failure 13,355 times over 140 seconds.

After base vertical budget exhaustion, the planner now uses the remaining
per-episode local-escape budget. The current waypoint direction only orders
the existing eight horizontal alternatives; a candidate is still constructed
only from rest and must pass the unchanged trajectory and stop-viability
certificates. Distance, four-attempt episode budget, 2 m episode reset and all
safety thresholds are unchanged.

Natural map9 Adaptive post-patch n=3+n=5 completed 8/8 first-attempt,
contact-free and speed-valid, with mean 87.30 s, range 69.55-96.61 s and
minimum +0.234 m static clearance. Those runs did not enter the new branch.
An explicit default-off one-shot fault hook then forced three base-NO_PATH
results on map1. Two independent smokes each armed one base local escape and
committed a 0.6 m/1.0 s move after 202 guard samples. Both completed 5/5
waypoints in 65.75/60.19 s with contact 0, valid speed and worst +0.311 m
static clearance. The second CSV directly records injection 1, forced failure
3, base escape arm 1 and local commit 1.

The ROS build, seven bandwidth parser tests and Python compileall pass, and
source/mirror C++ files are byte-identical. Full tables, the measurement
boundary, raw paths and log chronology are in
`docs/payload_bandwidth_and_base_no_path_escape_20260827.md`. Primary raws are
`results/bandwidth_3mode_seed1_10_n1_raw_20260827.csv`,
`results/base_no_path_escape_seed9_adaptive_n3_raw_20260827.csv`,
`results/base_no_path_escape_seed9_adaptive_n5_raw_20260827.csv` and
`results/base_no_path_fault_seed1_adaptive_v2_raw_20260827.csv`.

The next gate is final-binary map1-10 x three modes x n=3 with payload and
effective-transition metrics in the same cohort. Population 100%, formal
collision freedom and hardware readiness are not established. Raw-cloud CIRI
remains default false/non-authoritative; the known `obs_skip_num`, NaN,
clearance-penalty, BackupTrajOpt and `DRONE_R=robot_r` limitations are
unchanged.

### 8.37 Base-NO_PATH focused n=20 and final payload-aware three-mode n=3 gate (2026-08-27)

The post-patch map9 Adaptive focused gate was extended from ten to twenty runs
because the natural base-NO_PATH local-escape branch did not occur. All 20
runs completed on the first attempt, contact/static-collision-free and
speed-valid. Mean/range time was 90.07/76.71-122.25 s, minimum static
clearance was +0.190 m and mean processed payload was 3.280 MiB/s. The runs
made 165 effective full-view opens and 691 certified brakes but zero natural
base local-escape arms or commits. This is regression and liveness evidence;
the prior two default-off forced-fault smokes remain the direct branch proof.

The same final binary then completed map1-10 x Full/fixed-Sector/Adaptive x
n=3, 90/90 on the first attempt with zero timeout, retry or OOM and all rows
speed-valid. Full and Adaptive were safety-qualified 30/30. Fixed Sector
completed 30/30 but was safety-qualified 26/30: contact/static collision
occurred once on map7, twice on map9 and once on map10, for four runs, nine live
events and four static-PCD collision episodes. Adaptive was safe in each
matching map/run block. Mean Full/Sector/Adaptive times were
71.43/71.53/74.39 s and worst static clearances were
+0.193/-0.181/+0.210 m.

Mean processed payloads were 5.069/1.569/2.351 MiB/s. Equal-weight per-map
payload reductions versus Full were 69.43% for Sector and 54.24% for Adaptive.
Using the ratio of all 30-run mode means, Adaptive also reduced points/update
15.68%, map total/update 21.80%, occupancy update time 15.09%, FSM CPU 14.62%
and time-integrated planner-plus-filter CPU work 8.65%; mean mission time rose
4.14%. Adaptive made 372 effective full-view opens, or 12.4/run. Input
callbacks equalled processed filter frames 26,430/26,430 with zero worker
overwrite, so this reduction is not attributed to silently discarding frames.

Trajectory-guard and pre-stale full-refresh ACKs were 712/712 and
2,131/2,131, with zero timeout, retry, supersede, abandon or final pending.
The campaign reached a maximum FSM RSS/PSS of 3,472/3,450 MiB, zero FSM swap,
minimum system available memory of 5,228 MiB and zero memory-PSI avg10. Host
swap was already nearly full and peaked at 2,043 MiB, but the earlier isolated
9.1-GiB RSS/OOM event did not recur; its allocation source remains unresolved.

For safety-qualified completion, matched-block discordance was 4:0 for Full
versus Sector and 0:4 for Sector versus Adaptive; both exact two-sided McNemar
values are `p=0.125`. Full versus Adaptive had zero discordance and `p=1.0`.
Because every block used fixed Full->Sector->Adaptive order, these are
exploratory matched-block statistics rather than randomized causal evidence.
The Wilson 95% lower bound for 30/30 is 88.65%, and for Sector 26/30 it is
70.32%, so population 100% is not established.

Full map-labelled safety, time, switching, CPU and payload tables are in
`docs/final_payload_base_no_path_n3_20260827.md`. Primary raw files are
`results/final_base_no_path_seed9_adaptive_n10a_raw_20260827.csv`,
`results/final_base_no_path_seed9_adaptive_n10b_raw_20260827.csv` and
`results/final_payload_base_no_path_3mode_seed1_10_n3_raw_20260827.csv`.
Campaign tests pass 20/20 and the six runtime/mirror C++ pairs are
byte-identical.

The processed-payload measurement boundary remains unchanged: this is not
NIC/wireless/DDS wire bandwidth. Raw-cloud CIRI remains default false and
non-authoritative. The `obs_skip_num` no-op, NaN and clearance-penalty defects,
BackupTrajOpt coverage gap and `DRONE_R=robot_r` metric limitation also remain.

### 8.38 Crossed-order n=10, map-update worker memory fix and 100/100 cohort (2026-08-28)

The final candidate was first exercised with continuous order rotation rather
than fixed Full->Sector->Adaptive order.  A 150-row n=5 gate completed every
mission with zero source-static-PCD body intersection.  Legacy rendered-cloud
events were retained separately, and event-level source-PCD corroboration
confirmed that they were outside the common physical safety boundary.  The
monitor and runner now record `safety_contact_source`, source-PCD distance at
the first live event, live-only events and static-confirmed live events without
overwriting the historical detector fields.

Two n=10 attempts were rejected before the final gate.  The first stopped at
132 rows after map5 Full run4 timed out at 180 s.  Three degenerate
collision-away local-escape branches gained a goal-direction ordering fallback
while retaining the same stop-only eight-direction trajectory and viability
certificates.  Focused map5 Full n=3+n=5 completed 8/8 first-attempt and
static-contact-free.  No natural `direction_source=goal_fallback` event
occurred, so this is regression evidence and not direct proof of that branch's
effect.

The second attempt saved 277 rows before map10 run3 Full's `fsm_node` was
kernel-OOM-killed.  Its trace grew from 3.23 to 8.43 GiB RSS in 150.5 s and
`dmesg` reported about 8.47 GiB anonymous RSS; normal attempts remained near
3.3--3.5 GiB.  The ROG-Map DDS cloud callback had been doing PCL conversion,
map update, copy-on-write snapshot publication and ACK synchronously on
executor threads.  The accepted architecture makes that callback enqueue-only
and moves all heavy work to one dedicated latest-only worker.  Pending input
is bounded to one immutable ROS message; shutdown clears it, notifies and
joins the worker.  Safety/FOV/clearance/ACK/recovery parameters are unchanged.

Focused map10 Full n=3 and Adaptive n=3 both completed 3/3 first-attempt,
static-contact-free and without retry/OOM.  Peak Full/Adaptive RSS stayed below
3,237/3,233 MiB.  The fresh corrected-binary map1-10 x three-mode x n=10
campaign then completed 300/300 rows with process exit code 0.  All rows were
first-attempt, run-valid, speed-valid and source-static-PCD-enabled.  Full and
Adaptive each completed and were safety-qualified 100/100.  Fixed Sector
completed 100/100 but was safety-qualified 94/100: maps7, 8 and 9 each had two
separate static-PCD collision runs.  Adaptive was safe in all six matching
blocks.

Mean Full/Sector/Adaptive mission times were 71.61/70.05/74.33 s, and worst
static clearances were +0.157/-0.189/+0.146 m.  Adaptive made 1,160 effective
full-view transitions (11.60/run).  Relative to Full run means, Adaptive
reduced map update frequency 33.08%, points/update 16.68%, map total/update
20.63%, occupancy update time 13.05%, processed payload 56.08% and FSM CPU
17.05%, while mean mission time rose 3.80%.  Update-weighted point, total and
occupancy reductions were 15.47%, 20.36% and 12.75%.  Sector reduced points
48.50% and map total time 63.26%, but supplied all six unsafe runs.  The
payload remains processed ROG-Map application payload rather than NIC/DDS wire
bandwidth.

Accepted Sector/Adaptive filter rows processed 43,628/43,628 and
44,776/44,776 input callbacks with worker overwrite zero.  Final rows had no
trajectory-guard ACK timeout, retry, supersede, abandon or pending generation.
Global order rotation placed each mode in each order position 33 or 34 times.
Matched safety discordance was 6:0 for Full versus Sector and 0:6 for Sector
versus Adaptive; exact two-sided McNemar is `p=0.03125` for both.  Full versus
Adaptive had no discordance (`p=1.0`).

The final campaign had retry/OOM zero, maximum FSM RSS 3,263.95 MiB, minimum
host available memory 3,862.91 MiB and sampled memory-PSI avg10 zero.  Host
swap remained nearly full and peaked near 2,048 MiB, but the earlier unbounded
RSS event did not recur; the formerly failing map10 run3 Full completed on its
first attempt.

Detailed chronology, map-labelled tables and raw paths are in
`docs/counterbalanced_n5_n10_validation_20260828.md`.  The final raw is
`results/counterbalanced_map_worker_3mode_seed1_10_n10_raw_20260828.csv`.
The 95% Wilson lower bound for Full/Adaptive 100/100 is 96.30%, and for Sector
94/100 it is 87.52%; this is observed cohort performance, not a population
100% or formal collision-freedom guarantee.  Raw-cloud CIRI remains default
false/non-authoritative.  The `obs_skip_num` no-op, NaN/clearance-penalty
defects, BackupTrajOpt gap and `DRONE_R=robot_r` metric limitation are
unchanged.

### 8.39 Bounded same-map replan coalescing and rejected standard-profile adoption (2026-08-29)

The n=10 timing decomposition showed that Adaptive's extra time on maps5, 8
and 9 was dominated by additional freshness brakes and recovery-active time,
while exact full-refresh ACK latency stayed near 0.05 s with no loss or
timeout. Successful `ReplanOnce` calls also produced multiple trajectory
generations from one immutable map version. A default-off guard option was
therefore added to coalesce a successful replan only when both map version and
committed trajectory generation are unchanged.

The first candidate skipped all further successful replans until a new map
commit. It was rejected at row 27/30 of a seed5/8/9 crossed A/B: seed9 run4
Adaptive stopped at waypoint 2/5 and timed out at 180 s. Static collision was
zero, but clearance was +0.076 m and the stopped planner repeated 250 reroute
searches from an immediately occupied fallback start. This proved that no new
map information does not imply that progress-driven replanning can be
suppressed indefinitely.

The revised candidate forces a same-map replan again after 0.10 s. Seed9
smoke was 3/3 complete/static-safe. A same-binary crossed A/B on maps5/8/9 was
15/15 complete/static-safe for both baseline and candidate. Candidate time
changed from 82.25 to 79.35 s, brakes from 34.33 to 28.93/run and recovery from
34.06 to 30.39 s/run, while skipping 91.4 immediate duplicate timer ticks per
run. The paired time 95% interval [-7.072,+1.280] s included zero, so this is
not evidence of a uniform speedup.

The map1-10 x Full/Sector/Adaptive x n=3 gate completed 90/90 rows, all
run/speed-valid with retry/OOM zero. Full and Adaptive were each 30/30
complete and source-static-PCD-safe. Sector was 30/30 complete but had one
seed8 static collision; matching Adaptive was safe. Mean times were
69.86/72.19/75.21 s and worst clearances +0.219/-0.169/+0.043 m. Adaptive
reduced Full's map frequency 35.08%, points/update 15.76%, total/update 20.72%,
occupancy update 13.13%, processed payload 56.98% and FSM CPU 21.37%, while
mission time rose 7.65%. It made 344 effective full-view transitions.

Although the bounded candidate eliminated the observed timeout, Adaptive
seed9 averaged 95.62 s versus Full 83.55 s, used 41.3 brakes/run and reached
only +0.043 m source-PCD clearance in run3. Consequently the standard
`tight_v7` profiles were restored to the validated default-off behavior. The
byte-identical tested candidate is preserved only in explicit
`*_replan_coalesce_bounded.yaml` profiles. Max FSM RSS was 3,251.68 MiB; host
swap remained near 2,048 MiB, but there was no infrastructure retry or OOM
recurrence.

Detailed tables, commands, raw paths, claim boundaries and remaining
seed9-focused work are in
`docs/bounded_same_map_replan_coalesce_20260829.md`. Raw-cloud CIRI remains
default false/non-authoritative. The `obs_skip_num` no-op, NaN and
clearance-penalty defects, BackupTrajOpt coverage gap and
`DRONE_R=robot_r` metric limitation remain unchanged.

### 8.40 Hysteretic slowdown one-shot Full refresh and final n=10 (2026-08-29)

Source-PCD minimum context showed that the remaining seed9 Adaptive contact
occurred at 5.893 s, 0.083 m/s and -0.009641 m body clearance. Sector map
commits continued about every 0.2 s, keeping map age below the 0.25 s
pre-stale threshold. Replanning succeeded, so the failure guard stayed
closed, while the old stall state armed and opened too late. The root cause
was therefore a successful-replan high-to-low-speed blind-sector transition,
not ACK loss or same-map replan coalescing.

The native C++ filter now has a default-off hysteretic one-shot. Adaptive
arms above 3.0 m/s and, after slowing below 1.5 m/s, sends the next latest
cloud uncropped and uncapped through the existing generation/process ACK
path. It disarms immediately and cannot fire again until speed exceeds the
re-arm threshold, so stop jitter cannot create continuous Full traffic. The
runner records trigger/frame/pending/ACK/latency counters, and the source-PCD
monitor records time, pose, velocity, nearest point and waypoint index for
every new minimum.

A focused seed9 Adaptive n=10 completed 10/10, static-contact-free and
speed-valid with minimum clearance +0.179 m. The final rotating-order
map1-10 x Full/Sector/Adaptive x n=10 campaign then completed all 300 rows on
the first attempt with retry/OOM zero. Full and Adaptive were each
safety-qualified 100/100. Sector completed 100/100 but had one source-PCD
collision on seed9, so it was safety-qualified 99/100. Mean
Full/Sector/Adaptive times were 70.97/71.49/75.81 s and worst clearances were
+0.150/-0.175/+0.038 m.

Adaptive reduced Full's run-mean points/update 14.94%, map update frequency
30.50%, processed payload 52.25%, map total/update 19.10% and FSM CPU 17.66%,
while mean mission time rose 6.81%. It made 1,198 effective Full-view opens.
The new slowdown path triggered 4,816 times, sent 4,711 Full frames and had
4,706 committed ACKs. Five final frames were still pending exactly at mission
statistics shutdown; all five runs completed without contact and supersede
was zero. This is recorded as mission-end right censoring, not runtime ACK
loss.

Actual exact paired McNemar values for safety-qualified completion are
`p=1.0` for Full-Sector (one discordant block), Sector-Adaptive (one
discordant block) and Full-Adaptive (zero discordance). Wilson 95% lower
bounds are 96.30% for Full/Adaptive 100/100 and 94.55% for Sector 99/100, so
population 100% and formal collision freedom are not established.

The campaign had maximum FSM RSS 3,270.30 MiB, minimum host available memory
4,576.53 MiB, zero memory-PSI avg10 and no infrastructure retry. Detailed
cause analysis, map-labelled tables, command and claim boundaries are in
`docs/adaptive_slowdown_full_refresh_final_n10_20260829.md`. Primary results
are `results/final_slowdown_refresh_3mode_seed1_10_n10_raw_20260829.csv` and
its `_summary_20260829.csv` companion. The verified 1.5/3.0 values remain an
explicit profile; global CLI defaults remain off to preserve old ablations.
Raw-cloud CIRI remains default false/non-authoritative, and the known
`obs_skip_num`, NaN/clearance-penalty, BackupTrajOpt and `DRONE_R=robot_r`
limitations remain.

### 8.41 Low-speed nearest-face clearance shaping and n=3 gate (2026-08-30)

The final n=10 Adaptive map10 `+0.038 m` minimum was reconstructed at low
speed in a terminal/backup segment. Map freshness and exact ACK were normal,
and the generated short tails were trajectory-guard safe. A hard `0.10 m`
terminal-clearance gate was attempted first. It was reverted because repeated
candidate rejection created a certified-stop liveness trap; the low-speed
hard variant timed out on map10 run2.

The retained candidate corrects the old clearance cost rather than adding a
new hard rejection. Each quadrature sample uses the normalized nearest CIRI
face only, eliminating face-count-dependent summed penalties. The same term
now covers `BackupTrajOpt`, which was previously unprotected. With
`penna_clr=1e6` and `clearance_margin=0.10 m`, the weight is full below
1.5 m/s, fades with a cubic smoothstep to zero at 2.0 m/s, and contributes its
speed-envelope derivative to the velocity gradient. Missing parameters still
leave the feature globally off. The two `tight_v7` validation profiles carry
the candidate explicitly.

Ungated `2e6` completed maps9-10 n=10 each but raised their mean times to
103.97/99.78 s, +9.3/+15.5% versus the previous final cohort, and was
rejected. Ungated `1e6` produced a 141.01 s recovery tail. Speed-gated `1e6`
passed maps9-10 n=3 each, 6/6 safety-qualified with worst +0.233 m. Combining
that focused cohort with the subsequent same-binary regression gives map9 and
map10 6/6 each, worst +0.172/+0.225 m; this sequential aggregate is not a
pre-randomized experiment.

The rotating-order map1-10 x three-mode x n=3 regression was 90/90
first-attempt, run/speed/performance-valid with retry/OOM zero. Full and
Adaptive were each complete and safety-qualified 30/30. Sector completed
29/30 and was safety-qualified 27/30: map7 had one timeout plus one completed
collision, and map10 had one completed collision. Matching Adaptive rows were
all safe. Mean Full/Sector/Adaptive times, including the Sector timeout, were
73.33/75.64/76.02 s; worst clearances were +0.145/-0.172/+0.153 m.

Adaptive reduced Full's points/update 15.79%, map frequency 28.80%, processed
payload 52.14%, total map time/update 19.65%, occupancy update time 13.67% and
FSM CPU 16.53%, while mission time rose 3.67%. It made 348 effective Full-view
opens, 11.6/run. Map10 Adaptive improved from the prior final `+0.038 m` to
`+0.225 m` without increasing its cohort mean time, but map9's worst value
fell from the prior `+0.210 m` to `+0.172 m`; the soft corridor objective is
therefore not monotonic physical-clearance control.

Matched safety discordances are 3:0, 0:3 and 0:0 for Full-Sector,
Sector-Adaptive and Full-Adaptive; exact two-sided McNemar values are
0.25/0.25/1.0. The 30/30 Wilson 95% lower bound is 88.65%, so this is a
candidate n=3 gate, not population 100% or formal collision freedom. Host swap
remained near 2,047 MiB but FSM swap, memory PSI, OOM and infrastructure retry
were all zero; minimum available memory was 5,561.98 MiB and maximum FSM RSS
3,274.52 MiB.

Build, 20 campaign pytest cases, diff checks and seven source/mirror byte
comparisons pass. Detailed map-labelled tables and raw paths are in
`docs/speed_gated_nearest_face_clearance_n3_20260830.md`. Final adoption still
requires the same rotating-order 300-row n=10 campaign. This work repairs the
old face-summed clearance design and BackupTrajOpt coverage gap; the separate
NaN bug, `obs_skip_num` no-op and `DRONE_R=robot_r` metric limitation remain.
Raw-cloud CIRI remains default false/non-authoritative.

### 8.42 Cgroup-accounted speed-gated final n=10 and blind-footprint counterexample (2026-08-31)

The retained speed-gated nearest-face candidate was tested on the same binary
over maps1-10 x Full/Sector/Adaptive x n=10 with rotating mode order. The
runner now places `fsm_node` plus the optional native filter in an algorithm
cgroup and the simulator/mission stack in a sibling; hierarchical cgroup-v2
`cpu.stat:usage_usec` provides end-to-end CPU. Process PSS is sampled from
member PIDs because the host does not delegate the memory controller.

All 300 unique rows were first-attempt, run/speed/performance-valid and had
valid cgroup accounting; retry, OOM kill and speed exceedance were zero. Full,
Sector and Adaptive completed 100/99/100 rows and were source-static-PCD safe
on 99/100/100 rows. Mean times were 73.892/72.723/73.815 s and worst static
clearances were -0.144/+0.047/+0.106 m. Adaptive made 1,736 effective Full
opens, 17.36/run.

Mean algorithm core-seconds were 90.175/75.633/78.249 and end-to-end
core-seconds were 106.278/91.946/94.226. Relative to Full, Adaptive reduced
algorithm CPU 13.226%, end-to-end CPU 11.340%, processed payload 56.346%,
points/update 17.481% and map time/update 25.591%; mean mission time changed
-0.104%. Its algorithm/end-to-end interval-weighted p95 was 1.359/1.572 cores
versus Full's 1.611/1.824. Peak-PSS p95 remained approximately 3.2/3.6 GiB in
all modes, so this is not a memory reduction result.

The Sector miss on map3 run7 was contaminated by a singular memory event:
FSM PSS 8.22 GiB, host available 462 MiB, full swap and memory-PSI avg10
93.34/87.66%. A healthy targeted replay completed in 61.20 s with 3.19 GiB
algorithm PSS and no contact. The raw miss remains in the intention-to-run
statistics, but it is classified as infrastructure pressure rather than a
planner liveness counterexample.

Full map7 run4 completed but made one real static contact at 6.121 s and
0.01155 m/s. Its centre was 0.0563 m from the obstacle surface point while the
simulated LiDAR blind range was 0.1 m. Just 21 ms before contact a short
`ReplanOnce/no_backup` tail committed as guard-SAFE on the current map. The
low-speed nearest-face cost was at full weight, but the blind local map had no
face to penalize. A targeted replay was safe, so this is a stochastic 1/10
counterexample, not an every-run failure. The next correction must latch a
bounded recent raw near-field witness and hard-gate body/tail entry, with only
monotonic egress allowed if already inside; a static-PCD oracle must not be fed
to the planner.

Sector map9 run9's generic `collisions=1` was a live-cloud-only candidate:
source-static clearance was +0.094 m at the event and
`safety_collisions=0`. It is not an authoritative safety failure. This is why
campaign claims must use `safety_collisions`, not the generic contact counter.

Adaptive's 100/100 Wilson 95% lower bound is 96.301%. Adaptive-Full safety and
Adaptive-Sector completion each have only one matched discordance, so exact
two-sided McNemar is p=1.0. The cohort therefore establishes a repeatable CPU
and processed-payload reduction, but neither a population-level 100% safety
guarantee nor a statistically significant safety advantage. It also fails to
reproduce the intended Sector safety degradation in this n=10 cohort.

Detailed map-labelled tables, claim boundaries and forensic evidence are in
`docs/final_speedgated_cgroup_n10_and_failure_forensics_20260831.md`. Raw and
summary files are
`results/final_speedgated_cgroup_3mode_seed1_10_n10_{raw,summary}_20260831.csv`.
Raw-cloud CIRI remains default false/non-authoritative. The separate NaN bug,
`obs_skip_num` no-op and `DRONE_R=robot_r` metric limitation remain.

### 8.43 Recent-hit near-field shadow, Map7 n=20 and RViz path bias (2026-08-31)

The Full Map7 blind-footprint counterexample motivated a separate default-off
raw-hit witness. Accepted raw scans are retained for 1.5 s through ROG-Map's
existing in-process observer. Each newly committed trajectory queues one
latest-only asynchronous job with an as-of-enqueue cutoff. The worker checks
the current body plus a 1.0 s tail at 0.01 s spacing and an exact 0.20 m
radius. It never participates in accept/reject, braking or recovery. A clear
query is called `NO_HIT`, not `SAFE`, because observed-hit absence is not a
known-free certificate.

The first worker version converted the whole 300,000-660,000-point window
into a KD-tree, completing 102 jobs, replacing 35 and costing mean/max
154.96/291.49 ms. Exact AABB cropping around the sampled body spheres retains
every point capable of intersecting the test. A crop smoke completed 93/93
without replacement at 10.56/25.20 ms mean/max.

Map7 Full n=20 then completed and was source-static-PCD safe on 20/20 runs,
with no speed violation. Mean time was 80.463 s and worst static clearance was
+0.200003 m. The shadow completed 2,305 jobs, all no-hit, with zero replacement;
mean/max work was 9.979/42.228 ms, mean queue delay 0.046 ms, and mean
source/cropped point counts 442,259/3,597. Its smallest raw-hit distance was
0.2976 m, so the old stochastic contact did not recur and actual r=0.20
contact detection is not yet established.

A shadow-only r=0.40 sensitivity run completed safely in 78.49 s while
reporting 7 OCCUPIED and 97 no-hit results with zero replacement. This proves
the end-to-end witness path and confirms it is non-authoritative, but cannot
substitute for a contact-correlated r=0.20 run. A same-host shadow-off smoke
reported FSM CPU 144.44% and PSS 3,225.93 MiB versus shadow n=20 means
145.50% and 3,289.25 MiB; the one-run control is diagnostic, not a paired
performance claim.

The user's RViz observation that the vehicle passes close to the left obstacle
despite right-side free space is a separate path-quality issue. Full sensing
does not impose a passage-centre objective. The retained nearest-face cost has
full weight only at <=1.5 m/s, fades through 2.0 m/s and is zero above it.
A*/JPS chooses one guide seed, CIRI builds a corridor around it, and the back
end then prioritizes time, dynamics and smoothness. Cruise-speed right-side
slack therefore has no reward. Generic ungated clearance is not the answer:
earlier variants caused 9.3/15.5% Map9/10 time inflation, a 141 s tail, or hard
gate liveness traps. Bilateral left/right clearance should be instrumented
first, followed only if confirmed by a bounded face-balance/medial-axis term
inside genuine two-sided passages.

Before hard promotion, the witness must also run at a bounded new-scan cadence
for long-lived trajectories and capture either an actual r=0.20
contact-correlated result or a deterministic raw replay. Only then should a
generation-matched fresh OCCUPIED result hard-gate body/tail entry, with
distance-monotonic egress for an already-inside body. Detailed evidence and
paths are in
`docs/near_field_shadow_map7_n20_and_path_bias_20260831.md` and
`results/near_field_shadow_map7_summary_20260831.csv`. Raw-cloud CIRI remains
false/non-authoritative; static PCD remains evaluation-only.

### 8.44 Scan-cadence near-field hard gate and obstacle-provenance passage balance (2026-08-31)

The recent-hit worker now rechecks a long-lived committed trajectory on new
accepted raw-cloud sequences at a bounded 0.10 s cadence as well as on every
new trajectory generation. A new generation bypasses the cadence limit. The
raw sequence becomes visible only after its batch is present in the window;
jobs and results carry both generation and cloud sequence. Map7 Full completed
safely in 99.81 s while processing 331 results: 183 new-scan and 148
new-generation triggers, zero skip, with mean/max worker time 5.601/23.933 ms.

A test-only one-shot replay inserts a witness into the worker-private cropped
cloud after real freshness and density checks. It never changes the subscribed
cloud, ROG-Map or flight decision. The future-tail replay produced exactly one
r=0.20 OCCUPIED result at minimum KD distance 0.1904 m and then 393 NO_HIT
results while the shadow-only flight completed safely. This establishes the
detection path deterministically, not an actual stochastic contact capture.

The default-off enforce path consumes only an OCCUPIED result whose committed
generation matches, age is at most 0.20 s, cloud-sequence lag is at most one,
and checked trajectory-time range covers the current time. An OCCUPIED result
is latched until the FSM can consume it. A future-tail replay triggered exactly
one hard brake and recovered to generation 2; the run completed safely in
106.17 s. If the current body begins inside the witness sphere, the accepted
path must increase distance while inside, make at least 0.02 m progress, exit
clearance+0.005 m and never re-enter. The corrected body replay was classified
EGRESS, made zero near-field brake and completed safely in 72.90 s. A no-replay
real-cloud enforce smoke completed safely in 113.93 s with 308 NO_HIT and no
false brake. These are functional n=1 proofs, not population safety evidence.

The RViz left-hugging investigation added bilateral passage instrumentation.
CIRI now tags each final polytope face as boundary-derived or obstacle-derived,
and `Polytope` preserves that provenance. Passage candidates require two
obstacle-derived predominantly horizontal faces with opposing normals and a
combined width at most 3.0 m. Pair candidates are precomputed once per
polytope. ExpTrajOpt and BackupTrajOpt both implement a deadbanded squared
left/right-clearance balance cost and emit sampled/active, imbalance, width,
minimum-side and directional left/right statistics.

Without provenance, ordinary corridor bounding faces were mislabeled as
passages and many trajectories were active on 100% of samples; that design was
rejected. With provenance, the Map7 Full baseline had 11.89% active Exp samples
and mean absolute imbalance 0.3508 m. Strong Exp+Backup weights of 2e6 and 2e5
timed out at waypoint 3/5 and 2/5; precomputing pairs did not rescue the 2e5
candidate, which still timed out at 3/5. This demonstrates an objective/liveness
interaction rather than only pair-search overhead.

A conservative Exp-only 2e4 candidate (Backup cost disabled, although code
coverage remains) completed one Full smoke in 76.79 s with no contact. Its
diagnostic mean imbalance was 0.3051 m, 13.0% below the independent baseline,
but guard-brake logs rose 17 to 23 and physical minimum clearance fell +0.263
to +0.198 m. It is therefore not adopted. A final Map7 three-mode smoke with
the same experimental profile produced Full/Sector/Adaptive completion 1/1
each, static contacts 0/1/0, times 99.06/81.31/103.72 s, clearances
+0.268/-0.094/+0.264 m and processed payload 5.563/1.907/2.795 MiB/s. Adaptive
made four effective Full opens. This n=1 result is functional only and cannot
support a mode-level safety claim.

All new near-field and passage options remain default-off; standard tight_v7
and its live filtered profile are unchanged, and raw-cloud CIRI remains false.
Release build and 23 campaign tests pass. Detailed implementation, rejection
history and claim boundaries are in
`docs/near_field_hard_gate_and_passage_centering_20260831.md`; the compact
result index is
`results/near_field_hard_gate_and_passage_centering_summary_20260831.csv`.

A requested follow-up ran the same conservative Exp-only 2e4 passage profile
on Map7 Full/Sector/Adaptive ten times each with rotating order and cgroup-v2
accounting. All 30 rows were first-attempt, run/speed/performance/cgroup-valid;
each mode completed and was static-PCD safe on 10/10, with retry zero. Mean
times were 85.030/88.114/88.130 s and worst clearances were
+0.205/+0.000905/+0.233 m. Sector had two live-cloud-only generic contact
candidates, one at the nearly zero positive static margin above, but no
authoritative contact. This is a Sector risk signal, not a reproduced
collision. Ten successes have a Wilson 95% lower bound of only about 72.25%.

Mean Full/Sector/Adaptive algorithm core-seconds were
73.455/62.793/67.237 and end-to-end core-seconds were
89.699/80.104/84.317. Adaptive reduced Full's algorithm CPU 8.465%,
end-to-end CPU 6.000%, processed payload 47.538%, map frequency 26.076%,
points/s 36.401% and FSM CPU 15.939%, while mean mission time rose 3.646%.
Adaptive made 87 effective Full-open transitions, 8.7/run. Maximum algorithm
PSS was 3,252.2 MiB, minimum host available memory 6,327.2 MiB, and swap,
memory PSI, OOM and infrastructure retry were zero.

Weighted passage mean absolute imbalance was 0.3244/0.3254/0.3195 m, with
active Exp sample fractions 16.034/14.431/15.576%. Cohort-wide directional
left/right means were close, but maximum instantaneous imbalance still reached
about 2.0-2.27 m. There is no same-binary default-off n=10 control, so this is
not causal evidence that centering improved path quality and the candidate
remains unadopted. Raw/summary paths are
`results/passage_center_exp_w2e4_seed7_three_mode_n10_cgroup_{raw,summary}_20260831.csv`.

### 8.45 Pre-filter raw witness enforce and final n=10 (2026-09-01)

The Map7 Sector run7 forensic localized the earlier near-contact to a lateral
obstacle approximately +92.2 degrees from velocity; the live candidate was
about +70.1 degrees, outside the +/-60 degree sector. Passage balance could
shape only faces already represented in CIRI and Backup was not costed in that
campaign, so the missing pre-filter witness was the primary issue.

A configurable `fsm/trajectory_guard/raw_cloud/source_topic` now lets an
experimental filtered profile keep ROG-Map on `/cloud_sector` while a dedicated
callback feeds `/cloud_registered` only to the asynchronous recent-hit worker.
Empty/default source retains the existing map observer and no standard
`tight_v7` profile changed. Raw CIRI remains false and passage balance remains
off. The new profile is
`static_seedmaps_guard_viability_tight_v7_filtered_reliable_nearfield_enforce.yaml`.

Before promotion, Map7 Full enforce n=20 completed and was source-static-PCD
safe on 20/20 rows, with retry and speed violation zero. It processed 8,152
NO_HIT results, made no near-field brake, and had mean/p95/max worker time
8.367/15.314/52.291 ms. A pre-filter Adaptive smoke confirmed
`source=dedicated_pre_filter_subscription`. The maps7/9/10 three-mode n=3 gate
was 27/27 complete and safe with retry zero; Sector consumed 18 OCCUPIED
results and still completed all nine rows safely.

The rotating-order maps1-10 x three-mode x n=10 final campaign then produced
Full/Sector/Adaptive completion 100/99/100 and source-static-PCD safety
100/98/100. All 300 final rows were speed-valid. Sector made completed contacts
on map7 run10 (-0.168 m clearance) and map10 run4 (-0.051 m), plus a contact-free
map8 run8 timeout at waypoint 1/5. Full and Adaptive had no completion or safety
failure. Mean times were 78.640/77.061/81.769 s and worst clearances were
+0.101/-0.168/+0.117 m.

Mean Full/Sector/Adaptive algorithm CPU was 0.929/0.856/0.846 cores and mean
algorithm core-seconds 73.338/65.817/69.608. End-to-end means were
1.112/1.041/1.032 cores and 88.209/80.586/85.323 core-seconds. Adaptive reduced
Full's ROG-Map processed payload 45.746%, FSM CPU 12.172%, algorithm core use
8.962%, algorithm core-seconds 5.086%, end-to-end core use 7.215% and
end-to-end core-seconds 3.271%, while mission time rose 3.979%. Algorithm peak
PSS mean increased 1.028%, so this is not a memory reduction. Adaptive made
999 effective Full opens (9.99/run), 546 trajectory-guard opens and 5,101
slowdown refresh triggers.

Accepted Full/Sector/Adaptive logs contained 2/147/6 near-field OCCUPIED
results and the same numbers of enforce brakes. Worker mean/p95/max was
4.091/8.511/38.632, 3.831/8.049/60.550 and 3.776/8.173/31.380 ms. Sector's
remaining two contacts show that an observed-hit hard gate is useful but not a
formal collision-freedom mechanism.

One map5 Adaptive first attempt was killed by the global Linux OOM killer and
then succeeded in 79.77 s on automatic retry. At kill time FSM anon RSS was
about 6.60 GiB, sampled PSS 6.42 GiB, host swap was full and an unrelated host
Node process used about 4.9 GiB RSS. Final planner rows are 300, but
infrastructure first-attempt stability is therefore 299/300. The causal split
between transient FSM growth, raw witness retention and host co-tenancy is not
resolved.

The bandwidth claim is deliberately narrower than prior processed-payload
tables: `map_payload_mib_s` covers only the ROG-Map input. The experimental FSM
also directly subscribes to full `/cloud_registered`, which adds DDS delivery
and deserialization not counted there. Thus this establishes lower ROG-Map
input and CPU, not lower total communication bandwidth. The next architecture
should replace the full raw subscription with a small bounded near-field
witness side-channel (or an in-filter verdict) and meter total source and
subscriber bytes.

Full/Adaptive 100/100 has a Wilson 95% lower bound near 96.30%. The two paired
Sector-unsafe/Adaptive-safe rows give exact two-sided McNemar p=0.5; the single
Sector-incomplete/Adaptive-complete row gives p=1.0. This is observed goal
alignment, not a population guarantee or statistically significant safety
advantage. Detailed map tables, claim boundaries and evidence paths are in
`docs/nearfield_prefilter_raw_final_20260901.md`; raw/summary are
`results/nearfield_prefilter_raw_final_seed1_10_three_mode_n10_cgroup_{raw,summary}_20260901.csv`.

### 8.46 In-process zero-copy raw guard handoff and maps7/9/10 n=3 (2026-09-01)

The bounded witness follow-up first implemented an optional 360-degree radius
crop in the native C++ filter. It was functionally safe, but an 8 m witness
retained about 93.5% of points and a 5 m witness about 80.7%; the latter still
added roughly 3.0-3.4 MiB/s in Adaptive smokes. Moving that witness into a
composed process removed its DDS hop but not the large logical cloud. The
external bounded-witness design was therefore rejected.

The final architecture composes the native filter and FSM with intra-process
communications and hands the exact raw `PointCloud2::SharedPtr` received by the
filter directly to the FSM raw-window ingest path. Adaptive alone enables this
observer; Sector remains a pure angular-cut ablation. The FSM creates no
dedicated raw subscriber in injection mode, no cropped witness is repacked or
published, and the existing asynchronous latest-only worker still performs all
window accumulation, crop and KD-tree work. Standard tight_v7 profiles remain
unchanged and all experimental options remain explicit/default-off.

The runner now supports separate Full, Sector and Adaptive configs plus
`cpp-intra`, and reports source/filter/witness, DDS, intra-process and logical
planner payloads separately. Release build, 24 campaign pytest cases and the
standalone C++ equivalence test passed.

The first rotating campaign exposed four accidentally omitted tail parameters
in the new witness YAML (`p_hit`, `p_max`, `unk_thresh` and its comment). Full
and Sector used separate complete profiles and were unaffected. After restoring
the file, Adaptive was rerun three times per map with the established complete
raw-enforce profile and the same in-process injection. The final comparison is
the original Full/Sector 18 rows plus the corrected Adaptive nine rows. All 27
were first-attempt, run/performance/cgroup-valid with no retry, OOM or speed
violation. Full/Sector/Adaptive completion was 9/9, 9/9, 9/9 and source-static-
PCD safety was 9/9, 8/9, 9/9. Sector Map10 run3 completed but contacted the
source map at clearance -0.065 m; Full and Adaptive had zero contact. Adaptive
made 42 effective Full opens and 31 trajectory-guard opens. It passed 3,764 raw
SharedPtrs in process and externally published zero witness frames.

Mean Full/Sector/Adaptive times were 93.802/93.427/104.551 s and worst
clearances +0.189/-0.065/+0.123 m. Adaptive versus Full reduced ROG-Map payload
48.107%, algorithm mean cores 22.492%, algorithm core-seconds 13.003%,
end-to-end mean cores 17.642% and end-to-end core-seconds 7.842%, while time
rose 11.459%. Mean algorithm peak PSS changed only -0.122%, so there is no
material memory-reduction claim.

Measured DDS cloud rate was 16.575% below Full in this sample, but source bytes
per scan were nearly equal and the rate includes simulator cadence variation.
The defensible architecture claim is removal of the second full-raw DDS hop,
not fewer raw sensor bytes per scan. Logical planner ingress is 35.465% higher
because it counts both the zero-copy safety consumption and filtered ROG input;
it must not be presented as wire traffic.

The corrected Map9 Adaptive 127.39 s tail had 73 guard recoveries and 83.615 s
of recovery-active time. Across nine Adaptive rows, mission time and accumulated
recovery-active time correlated at 0.978, pointing to repeated certified
stop-and-reroute rather than CPU starvation. The next efficiency work should
coalesce same-obstacle/generation recovery or reuse bounded topology results
without weakening the safety gate. Population claims still require the planned
Map1-10 n=10 regression. Full details are in
`docs/inprocess_raw_guard_handoff_20260901.md`; Full/Sector raw and the combined
summary are `results/inprocess_raw_handoff_seed7_9_10_three_mode_n3_{raw,summary}_20260901.csv`,
and corrected Adaptive raw is
`results/inprocess_raw_handoff_corrected_adaptive_seed7_9_10_n3_raw_20260901.csv`.

### 8.47 Sensor-front-end filtering and compact risk verdict (2026-09-01)

The filter was moved across the remaining sensor DDS boundary. A new composed
`perfect_drone_frontend_node` passes the renderer's raw `PointCloud2::SharedPtr`
directly to the native filter and does not create a `/cloud_registered`
publisher in Sector or Adaptive mode. Sector publishes only the filtered map
cloud. Adaptive additionally publishes a compact trajectory-risk verdict. Full
retains the original raw cloud publisher and serves as the reference mode.

This is more than relocating the angular crop. `PolynomialTrajectory` now
carries an exact 64-bit generation in addition to the legacy controller ID.
`TrajectoryRiskVerdict` returns that generation, raw-cloud sequence and stamp,
checked trajectory-time interval, result/source ages, witness data and status.
The FSM accepts an OCCUPIED result for enforcement only when generation,
freshness and checked-range gates all pass. Shadow logging is enabled only in a
new experimental profile; enforcement and all standard `tight_v7` profiles
remain off and unchanged.

The raw callback only stores SharedPtrs/latest jobs. Angular filtering and risk
evaluation run in independent latest-only workers. The risk worker uses a 1.5 s
raw window, trajectory-tail AABB crop and KD-tree nearest-hit/egress test. A
planner-free runtime contract smoke observed no `/cloud_registered` publisher,
one filtered-cloud publisher, one verdict publisher, and 203/203/203 raw input,
filtered output and verdict events with zero worker overwrite. Actual RMW CDR
serialization was measured rather than estimated: each verdict is 180 bytes.

Release build, 24 campaign pytest cases and the standalone native geometry/
stats/witness equivalence test passed. The v=7 Map7/9/10 three-mode n=1 rotating
gate produced nine first-attempt completions, nine source-static-PCD-safe rows,
and no retry, OOM or speed invalidation. Mean Full/Sector/Adaptive mission times
were 97.927/69.343/66.097 s. Adaptive versus Full reduced mean DDS map-cloud
rate by 18.085%; verdict traffic averaged 0.001815 MiB/s, about 0.044% of total
algorithm DDS. Adaptive emitted 2,096 verdicts (377,280 bytes), with 5.201 ms
mean risk compute time, 16.924 ms worst run maximum and zero overwrite. It made
71 effective Full openings.

This gate does **not** establish a computation reduction. Mean Adaptive FSM
load was 1.112 cores versus Full 0.679, and FSM core-seconds were 73.496 versus
66.406 (+10.677%). A separate Map7 CPU boundary run measured simulator/front-
end mean cores of 0.140/0.165/0.270 for Full/Sector/Adaptive; Adaptive front-end
cloud and risk workers accounted for about 0.0118 and 0.0529 cores. The primary
confound is cadence: Full ROG processing ran at 3.82--4.49 Hz while front-end
Sector reached 10.20--10.34 Hz. Removing raw DDS restored callback throughput,
so the planner processed more generations. The result supports a communication
architecture contribution, but CPU savings must not yet be claimed.

The next optimization must meter and match source-publish, accepted-generation
and ROG-commit cadence, then cap front-end cloud publication at the lowest rate
that preserves completion and contact safety. Only after a cadence-matched CPU
gate should verdict enforcement receive separate fault-replay and repeated
Map7/9/10 testing; Map1--10 n=10 remains the final regression rather than the
next debugging step. Full tables and claim boundaries are in
`docs/sensor_frontend_risk_verdict_20260901.md`. Raw evidence is in
`results/frontend_risk_shadow_map7_n1_raw_20260901.csv`,
`results/frontend_risk_shadow_maps7_9_10_three_mode_n1_raw_20260901.csv`, and
`results/frontend_risk_cpu_map7_three_mode_n1_raw_20260901.csv`, with matching
artifact directories.

### 8.48 Cadence cap, bounded optimizer, verdict enforcement and final n=10 (2026-09-02)

Source/filter publish, ROG commit and trajectory cadence were added to the
simulator, native front end and campaign CSV. Adaptive filtered-cloud publication
and heavy future-tail risk evaluation were capped independently at 5 Hz while the
source remained about 10 Hz. A 4.5 Hz candidate was rejected. Map7/9/10 three-mode
n=3 then completed 27/27 with collision, retry and OOM zero.

The remaining rare memory growth was traced to upstream L-BFGS having no
iteration limit when `max_iterations=0`. A 256 candidate interrupted ordinary
plans and was rejected; 2,048 bounded the pathological path while preserving
smoke completion. The final 300 rows had average algorithm PSS about 3.18--3.19
GiB, optimizer-cap hits Full/Sector/Adaptive 348/339/290, and OOM/retry zero.

A new experimental enforcement profile kept every standard `tight_v7` profile
unchanged. Wrong-generation and stale injected OCCUPIED results were ignored;
a fresh injected result published a 0.680 s certified brake and recovered. A
Map7/9/10 natural n=1 gate completed 3/3 safely. This proved gate wiring, not
universal timely detection.

The rotating Map1--10 × Full/Sector/Adaptive × n=10 campaign contains exactly
300 unique, run/speed/performance/cgroup-valid rows. Completion was 99/100/99 and
source-static-PCD collisions were 0/0/1. Mean times were 79.951/63.135/64.054 s,
algorithm core-seconds 72.073/69.934/70.473, end-to-end core-seconds
88.973/83.895/90.664 and planner ingress 4.558/3.131/2.300 MiB/s. Adaptive versus
Full reduced mission time 19.883%, planner ingress 49.547% and algorithm
core-seconds 2.219%, but increased end-to-end core-seconds 1.900%. Effective
Full-open and trajectory-guard-open totals were 1,900 and 320. Therefore the
communication reduction is strong, the algorithm-work reduction is small and
the end-to-end computation claim still does not hold.

Map7 run1 Full/Adaptive timed out at waypoint 2/5 under host available memory
230.75/289.13 MiB and PSI-full 53.55/64.20%, with an external VS Code extension
host near 8 GiB and swap full. Logs show a real stationary topology trap
(optimizer overtime, exclusion zones, A* NO_PATH and epoch resets) amplified by
memory reclaim. After the extension host restarted and available memory returned
to about 3.5 GiB, Map7 run2--10 completed Full/Sector/Adaptive 9/9 each. The raw
failures remain failures; this is only a resource-sensitivity split.

Map10 run6 Adaptive completed but contacted the static PCD at first clearance
-0.119 m and worst -0.149 m. The first OCCUPIED verdict arrived 99 ms after the
contact. It belonged to gen36, but gen37 committed before consumption so exact-
generation enforcement ignored it; gen37 OCCUPIED braked only after contact.
Host PSI was zero, so this is a genuine coverage gap between 5 Hz heavy-risk
cadence and endpoint generation churn. The next fix is a cheap current-body/very-
short-horizon tier at every approximately 10 Hz sensor frame, with a source-fresh
generation-independent certified hold, while retaining the existing 5 Hz exact-
generation future-tail tier. Raising the whole heavy worker back to 10 Hz is not
the preferred fix.

Full and Adaptive completion/safety 99/100 have Wilson 95% lower bounds about
94.55%; Sector 100/100 has a lower bound about 96.30%. The one-sided paired
discordances against Sector have exact two-sided McNemar p=1.0. This campaign
does not establish population 100%, a significant safety advantage, or intended
Sector degradation. Full tables and timestamp-level failure analysis are in
`docs/frontend_risk_enforce_final_20260902.md`; raw and summaries are
`results/final_frontend_enforce_map1_10_three_mode_n10_cgroup_{raw_20260901,summary_20260902,reductions_20260902}.csv`.

### 8.49 Current-body tier, active-brake replacement and n=3 regression (2026-09-02)

The Map10 generation/cadence coverage gap was addressed without raising the
entire heavy risk worker back to 10 Hz. `TrajectoryRiskVerdict` now separates
`FUTURE_TRAJECTORY` and `CURRENT_BODY` scopes. The future tier remains a 5 Hz
raw-window/KD-tree check with exact-generation, freshness and checked-time
gates. The current-body tier runs on every approximately 10 Hz sensor frame,
checks a measured-position/velocity segment over 0.15 s directly against the
fresh raw scan, and is generation-independent but has tighter result/source
freshness limits of 0.15/0.20 s.

The FSM keeps independent pending slots and request-id watermarks for the two
scopes. Duplicate occupied messages are idempotent. A fresh predicted-ahead
current-body result may replace an already-active brake once per episode; this
closes the prior case in which the FSM returned early while executing an older
brake. A deterministic Map1 fault gate first activated a future brake, then
sent a deliberately generation-mismatched current-body result 99 ms later. It
produced exactly one `frontend_body_active_brake` replacement, recovered and
completed without contact. A 1.491 s stale body result was ignored. All new
options are default-off, the standard tight_v7 profiles remain unchanged, and
only the experimental front-end enforcement profile enables this tier.

Map10 Adaptive n=30 was 30/30 complete, source-static-PCD safe, valid and
first-attempt, with retry/OOM zero. Mean time was 72.506 s, worst clearance
+0.131 m, body OCCUPIED/brakes 7/5 and natural active-brake replacements zero.
Body checking averaged 0.394 ms and the worst per-row maximum was 2.361 ms.
The rare replacement path is therefore covered by the deterministic gate, not
claimed as a common natural event.

A resource-normal Map7 Full/Adaptive n=20 rerun was complete and safe 20/20 for
both modes with no retry, OOM or PSI-full pressure. Full/Adaptive mean times
were 86.952/67.730 s and worst clearances +0.021/+0.128 m. This does not erase
the prior timeout rows; it supports the interpretation that real topology
sensitivity was amplified by severe host reclaim.

The final same-profile Map1--10 n=3 regression produced Full/Sector/Adaptive
completion and source-static-PCD safety of 30/30 for every mode. Mean times
were 77.908/63.625/63.270 s and worst clearances +0.166/+0.180/+0.121 m.
Full/Adaptive were first-attempt 30/30. Sector was 29/30 first-attempt because
Map6 run1 attempt1 had `oom_kill_delta=1`; it then succeeded on retry. That
attempt's FSM PSS rose from about 3.14 to 6.31 GiB, swap was full and cgroup
memory peaked near 10.50 GiB. Sector does not enable the new risk/body tier, so
this is residual planner/optimizer memory instability rather than evidence of
body-tier overhead.

Adaptive versus Full reduced measured planner DDS cloud+verdict rate 49.405%,
ROG input 49.464%, ROG per-frame compute 32.474% and algorithm core-seconds
1.975%. It nevertheless increased mean algorithm cores 17.122% and end-to-end
core-seconds 1.348%; PSS was effectively unchanged. The body tier itself used
about 0.00340 core and 0.001829 MiB/s. Thus communication and ROG-work
reductions hold, but total-computation and memory reductions do not.

Sector also completed safely 30/30 and used slightly less total work than
Adaptive. The current +/-60 degree condition is therefore not a discriminating
ablation and cannot support an Adaptive-over-Sector safety claim. A
pre-registered paired half-angle operating-envelope test on the same maps is
needed; post-hoc tuning to manufacture collisions is not acceptable. Each
mode's 30/30 result has a Wilson 95% lower bound of only 88.65%, so none is a
population guarantee. Full implementation, per-map tables, OOM evidence and
claim boundaries are in `docs/frontend_body_active_brake_final_20260902.md`;
summary CSVs are
`results/frontend_body_map1_10_three_mode_n3_{summary,reductions}_20260902.csv`.

### 8.50 Paired half-angle screen and optimizer phase memory trace (2026-09-02)

The planned operating-envelope screen parameterized one common nominal
half-angle for Sector and Adaptive. `native_campaign.py` now accepts
`--filter-half-angle-deg` for every native-filter backend; its default remains
60 degrees. An independent `--optimizer-phase-memory-trace` switch exports a
default-off environment flag. When enabled, ExpTrajOpt and BackupTrajOpt log
begin/end, duration, iteration count, process RSS/swap and RSS delta around
each L-BFGS call. The runner aggregates every attempt and preserves an
unmatched begin marker if an OOM kills the process inside an optimizer. No
standard `tight_v7` profile changed.

Release build, eight campaign parser tests and a Map1 45-degree Sector/Adaptive
gate passed. The pre-declared reduced screen then ran 60, 45 and 30 degree
half-angles on Map7/9/10, Sector/Adaptive, n=3 with rotating order. All 54 rows
completed on their first attempt with source-static-PCD collision, speed
invalidation, retry and OOM all zero. Sector/Adaptive mean times were
73.280/71.323 s at 60 degrees, 76.611/72.436 s at 45 degrees and
73.750/70.831 s at 30 degrees. Corresponding measured DDS rates were
4.536/3.364, 4.145/3.262 and 3.623/3.074 MiB/s.

There was a secondary clearance signal but no primary safety-rate separation.
At 60 degrees both modes had zero rows below descriptive clearance 0.20 m. At
45 degrees Sector had 2/9 (worst +0.173 m) and Adaptive 0/9 (worst +0.226 m).
At 30 degrees Sector again had 2/9 (worst +0.186 m) and Adaptive 0/9 (worst
+0.226 m). Adaptive's same-angle DDS reduction versus Sector was
25.852/21.313/15.133%, but algorithm and end-to-end CPU reductions were not
consistent. The 0.20 m cutoff is descriptive, not a collision or certification
threshold.

Adaptive main-open/trajectory-guard-open/effective-Full-open totals were
5/55/169 at 60 degrees, 2/54/178 at 45 degrees and 4/52/157 at 30 degrees.
These are overlapping state counters, not unique episodes. Only one natural
current-body brake occurred and no active-brake replacement occurred.

All Exp begin/end markers matched 23,847/23,847 and all Backup markers matched
41,100/41,100. Maximum optimizer-observed process RSS was 3,282.7 MiB,
end-to-end sampled RSS 3,723.9 MiB and whole-benchmark cgroup memory
9,597.2 MiB. The largest one-call RSS deltas were 7.766 MiB Exp and 8.871 MiB
Backup, although latency tails reached 803.407 and 944.891 ms. This campaign did
not reproduce the earlier Map6 OOM, so it does not identify that failure's
cause; it makes the phase of a future recurrence observable.

The decision is that no tested angle is a completion/contact discriminator:
Sector and Adaptive were both 27/27 complete and collision-free. With no
discordant primary pairs, no McNemar test was performed. The 45-degree result
is the strongest descriptive margin/time condition, but selecting it as proof
of an Adaptive safety-rate advantage would be post-hoc overclaiming. Further
discrimination should use a pre-declared topology or sensor-latency condition,
not more tuning of these same angles. Full details and map-labelled tables are
in `docs/half_angle_operating_envelope_20260902.md`; compact evidence is in
`results/half_angle_sweep_maps7_9_10_sector_adaptive_n3_{summary,reductions}_20260902.csv`
and the three angle-specific raw CSVs.

### 8.51 Frozen 45-degree side-entry topology v1--v4 and n=3 gate (2026-09-03)

The 45-degree half-angle was fixed from the prior exploratory screen because
it gave the best secondary balance, not because it proved a safety-rate
advantage. At 45 degrees, Sector/Adaptive low-clearance rows below the
descriptive 0.20 m cutoff were 2/9 versus 0/9, Adaptive improved worst
clearance by 0.053 m and time by 5.450%, and reduced DDS by 21.313%. The
separate preregistration record is
`docs/half_angle_45_selection_preregistration_20260903.md`.

A default-off common-source side-entry cylinder and an analytic solid-cylinder
collision oracle were implemented. The cylinder is appended inside
PerfectDrone before the Full DDS versus Sector/Adaptive in-process split, and
the monitor checks a 0.20 m body sphere independently of rendered points or
raw DDS. V1 and v2 used mode-dependent PVAJ centres and proved infeasible. V3
fixed the centre at `(22.5, 23.0)` but retained a mode-dependent velocity-
sector spawn predicate, so Sector did not receive the treatment. All failed
and invalid rows were retained.

V4 preserved the v3 centre, radius 0.25 m, height 3.0 m, 47-degree body inner-
edge requirement, zero nudge, trigger thresholds and 0.015 s hold, changing
only `require_velocity_inside` to false. This matches the architecture:
Sector loses the body-fixed cropped cloud while Adaptive's safety worker has
an independent 360-degree raw input. Release build, 19 campaign unit tests,
profile/source-separation validation and source/mirror byte comparison passed
before flight. All standard tight_v7 profiles remain unchanged.

The Map7 treatment gate was valid and complete with zero contact in all three
modes. The rotating Map7/Map9/Map10 n=3 campaign then produced 27 rows and 26
validator-passing events. Map10 Full run 1 completed without a spawn because
its two geometry-valid samples spanned 0.009911 s, shorter than the frozen
0.015 s hold; that row is invalid for side-entry inference. Among valid rows,
Full/Sector/Adaptive completion was 7/8, 9/9 and 9/9, with zero static-PCD or
side-entry contacts in every mode. Sector therefore still did not exhibit the
intended primary degradation.

Full's Map9 run 2 failure was a real 180 s liveness timeout at waypoint 3/5,
not infrastructure or side-entry contact. It stopped near `(0.15, -20.16)`
with +0.720 m side-entry clearance. The trace contained 218 PlanFromRest
failures, 193 polytope-line failures and 190 failed backup generations. Reroute
zones and one certified vertical recovery kept proposing start-adjacent CIRI-
infeasible segments; no OOM kill, swap growth or PSI pressure occurred.

Across the nine valid Sector/Adaptive pairs, mean side-entry clearance was
0.553/0.597 m. The Adaptive minus Sector map changes were +0.162, -0.138 and
+0.108 m on Map7/Map9/Map10, so the margin direction was not map-consistent.
Adaptive completed every row but cannot claim a completion/contact improvement
when Sector also completed every row without contact.

On the seven valid-complete three-mode triples, Adaptive versus Full reduced
external DDS cloud+verdict rate 29.983%, ROG per-frame compute 26.009% and
delivered point count 22.093%. Mean algorithm and end-to-end CPU cores instead
increased 57.465% and 55.166%; total CPU savings are not supported. Adaptive
effective-Full-open and trajectory-guard-open totals over all nine runs were
175 and 60.

V4 should not be expanded to n=10. The next priority is the independent Full
certified-stop liveness loop. A later side-entry version must first add closest-
approach context, declare one fixed location from the v4 exploratory paths,
replace the fragile time hold with a fixed sample-count rule, freeze, and then
use new repetitions. Detailed tables and raw paths are in the 45-degree record
and `results/side_entry_v4_maps7_9_10_three_mode_n3_{raw,summary}_20260903.csv`
plus
`results/side_entry_v4_maps7_9_10_three_mode_n3_paired_reductions_20260903.csv`.

### 8.52 Full viability egress fix and in-process raw-map delivery (2026-09-03)

Full was isolated before any further Sector/Adaptive tuning. Two guard defects
were corrected. A trajectory accepted through the configured initial-footprint
egress mask did not pass that same start context into its derived viability
brakes, so safe brakes could be rejected by points in the footprint being
exited. The egress origin and synthetic regression hook now propagate through
`candidateStopsViable()` and `certifiedStopExistsFrom()`. The viability
slowdown loop also applied a cumulative scale to an already scaled trajectory;
each retry now applies only the incremental step while retaining the cumulative
scale for limits and diagnostics. Release build, all 29 campaign unit tests and
a forced Map8 initial-footprint gate passed.

Map9 then exposed a separate transport problem. Changing the standalone raw
publisher to best-effort/keep-last-1 prevented a DDS backlog but did not restore
delivery: the seven preserved valid rows averaged only 2.758 ROG frames/s,
55.14 stale-map detections/run and 89.61 s recovery-active time. Six of seven
completed and one low-speed static-PCD contact occurred; the scheduled ten-row
campaign was interrupted after those seven rows, which are retained rather
than presented as an n=10 result.

An opt-in `perfect_drone_full_node` now composes PerfectDrone and SUPER. It
passes the unchanged complete `PointCloud2::SharedPtr` through
`FsmRos2::injectMapCloud()` to `ROGMapROS::injectCloud()`. The latter invokes
the same enqueue-only/latest-only admission path and existing map worker. PCL
conversion, ray casting, inflation, commits, planner and guard are unchanged;
only the large raw-cloud DDS serialization/transport boundary is removed. The
standard tight_v7 profile and default launch path remain unchanged. The
campaign runner exposes this only with `--full-intra-process` and records raw
DDS versus in-process logical bytes separately.

Map9 in-process n=10 was 10/10 complete, collision-free and speed-valid. ROG
input was 10.106 Hz, stale count was zero and recovery-active time averaged
19.85 s; mission time averaged 76.16 s. Map compute increased from the DDS
sample's 27.22 to 36.56 ms, consistent with processing more actual Full frames
rather than skipping computation. `fsm_cpu_pct` is now a combined
simulator+planner process measurement: its 145.78% means 1.46 logical cores and
must not be compared with the old FSM-only percentage.

The cross-map gate was then expanded to ten runs per map. Its final CSV has
exactly 100 unique `(map, run, mode)` keys, all run-valid, complete, contact-free
and speed-valid, with zero stale detections, retries, OOM kills or PSI pressure.
Map1--10 mean times were 59.82/55.57/58.61/64.92/64.13/65.58/70.08/65.36/
76.16/76.48 s. Worst per-map clearances were +0.244/+0.217/+0.218/+0.222/
+0.225/+0.175/+0.247/+0.184/+0.232/+0.185 m. The overall sensor/map rates were
10.001/10.145 Hz, map compute was 36.23 ms and Full logical planner ingress
remained 9.43 MiB/s. Raw-cloud DDS was zero because delivery was in-process,
not because points were removed.

This is an observed 100/100 regression pass, not a population-level 100%
guarantee; its Wilson 95% lower bound is about 96.30%. Full is now frozen for
the current ten maps/profile. A later three-mode CPU comparison must use the
same cgroup accounting boundary for all modes and report logical ingress
separately from external DDS. Full should be changed again only if new Full
failure evidence appears. Detailed tables, caveats and raw-file manifest are in
`docs/full_inprocess_control_20260903.md`; the compact table is
`results/full_inprocess_control_map_summary_20260903.csv` and the final raw
cohort is `results/full_intra_map1_10_n10_raw_20260903.csv`.

### 8.53 Frozen-Full three-mode hard-map gate and CPU-scope correction (2026-09-03)

The frozen in-process Full was used as the paired control on Map7/9/10 for
Full/Sector/Adaptive, three rotated-order repetitions per map and mode. All 27
unique rows completed on their first attempt, were static-PCD contact-free and
run/speed/performance/cgroup-valid, with zero retry and OOM. Full was 9/9 on
the maps that previously exposed its liveness tail. Sector and Adaptive were
also 9/9 and contact-free.

Adaptive effective Full-open totals were 64/68/59 on Map7/9/10, or 191 total.
The overlapping trigger counters were six stall opens, 250 replan-guard opens
and 54 trajectory-guard opens. Adaptive worst clearance was +0.214 m versus
Sector's +0.174 m, but there are no discordant completion/contact pairs, so
this gate does not establish a Sector safety-rate degradation or an Adaptive
rate improvement.

The campaign exposed a measurement-composition issue before interpretation:
an integrated Full process cannot place its simulator and planner in separate
cgroups, while cpp-frontend places simulator+filter together and the planner
separately. Consequently `algorithm_cpu_*` is simulator+planner for Full but
planner-only for Sector/Adaptive and is not cross-mode comparable. The runner
now emits explicit CPU-scope metadata. The common parent `end_to_end` scope
contains simulator+frontend+planner+mission for every mode and is the primary
total-compute measure.

Across nine rows per mode, Adaptive versus Full reduced logical planner
ingress 74.669%, map-compute core equivalent 64.857%, mean end-to-end cores
11.300% and end-to-end core-seconds 16.689%; mission time fell 6.044%.
Adaptive versus Sector reduced logical ingress 21.050% and external DDS
20.984%, but used 5.303% more end-to-end cores and 4.077% more core-seconds.
Peak PSS was not reduced. Integrated Full external raw DDS is structurally
zero, so Adaptive cannot claim a DDS reduction against this Full topology;
logical ROG ingress is the appropriate processing-volume comparison.

The next paired gate is Map1--6/8 n=3 with the same frozen profiles and
accounting, completing the ten-map table without changing Full. Detailed map
tables and raw paths are in `docs/full_inprocess_control_20260903.md` and
`results/full_control_three_mode_map7_9_10_n3_{raw,summary,reductions}_20260903.csv`.

### 8.54 Frozen-Full ten-map paired n=3 completion (2026-09-03)

The remaining Map1--6/8 campaign added 63 rows under the identical frozen
profiles and accounting. All rows completed on their first attempt without
static-PCD contact, speed invalidation, retry or OOM. Combined with §8.53, the
cohort has exactly 90 unique map/run/mode keys: 30/30 complete and zero contact
for each of Full, Sector and Adaptive. Full therefore remained 30/30 in the
new paired experiment without further tuning.

Adaptive effective Full-open totals by Map1--10 were 47/61/63/55/52/69/64/
67/68/59, or 605 total and 20.17/run. Its overlapping trigger totals were
eight stall, 762 replan-guard and 122 trajectory-guard opens. Mission-time
means were 65.366/64.794/63.445 s for Full/Sector/Adaptive.

Using only the common end-to-end cgroup scope, Adaptive versus Full reduced
logical planner ingress 75.876%, map-compute core equivalent 66.862%, mean CPU
cores 13.001% and CPU core-seconds 15.373%. Against Sector it reduced logical
ingress 19.178% and external DDS 19.081%, but increased map-compute core
equivalent 13.900%, mean end-to-end cores 4.950% and core-seconds 2.879%.
Peak PSS was essentially unchanged versus Full and 1.187% higher than Sector.

Adaptive's mean/worst clearance was +0.249/+0.173 m, versus Sector
+0.262/+0.174 m and Full +0.260/+0.179 m. The Adaptive minimum occurred on
Map6 run1 at 1.46 m/s and cannot be excluded as an initial-pose or stopped
sample; the following two Map6 Adaptive repetitions were +0.248/+0.243 m and
all were contact-free. Thus zero observed contact does not imply that a
0.20 m clearance contract held on every run.

No prior Map6 OOM recurred. The minimum system-available memory was about
3.86 GiB, maximum swap use was about 1,022 MiB and all `oom_kill_delta` values
were zero. One Map3 Adaptive row briefly recorded memory PSI some/full 0.69
with 4.51 GiB available and completed first-attempt, so it is not classified
as an infrastructure failure.

These static maps support a processing-efficiency result at equal observed
completion/contact outcomes, but still do not identify the separate claim
that Adaptive recovers a Sector completion/contact degradation: Sector itself
was 30/30 and contact-free. The combined raw preserves the two execution
cohorts explicitly. Full remains frozen. Detailed results are in
`docs/full_inprocess_control_20260903.md` and
`results/full_control_three_mode_map1_10_n3_{raw,summary,reductions}_20260903.csv`.

### 8.55 Frozen-profile paired n=5 checkpoint (2026-09-03)

Runs 4--5 added 60 rows without changing any profile. The resulting 150-key
cohort is run/speed/performance/cgroup-valid throughout, with zero retry, OOM
or static-PCD contact. Full and Adaptive completed 50/50; Sector completed
49/50. Map10 run4 is the first paired degradation/recovery observation:
Sector reached four waypoints and timed out at 180 s, while Full and Adaptive
completed in 86.70 and 68.96 s.

The Sector failure is a planner liveness event rather than infrastructure
noise. It retained a certified stop near `[19.525,-19.425,1.925]`, saturated
six exclusion zones and retried near-identical short candidates that CIRI
immediately rejected more than 100 times. The row had retry/OOM/PSI all zero
and 2.12 GiB system-available memory. Adaptive's corresponding run used 19
effective Full opens and completed without contact, although its minimum
clearance was only +0.178 m.

Across 50 Adaptive runs, effective Full-open totaled 1,031 (20.62/run), with
11 runs entering the stall-open condition, 1,266 replan-guard opens, 198
trajectory-guard opens and 21/3 future-tail/current-body OCCUPIED verdicts.
Against Full, Adaptive reduced logical planner ingress 76.220%, map-compute
core equivalent 67.734%, end-to-end mean cores 13.378% and core-seconds
16.323%. Against Sector it reduced ingress/DDS by about 21.4/21.3%, while
using 5.483% more mean cores and 0.742% more core-seconds.

Zero failures in 50 Full and Adaptive trials gives a Wilson 95% completion
lower bound of 92.87%, not a population-level 100% guarantee. Sector 49/50
has a lower bound of 89.50%. The profiles remain frozen and the next step is
to add runs 6--10. Detailed tables are in
`docs/full_inprocess_control_20260903.md`; checkpoint data are
`results/full_control_three_mode_map1_10_n5_{raw,summary,reductions}_20260903.csv`.

### 8.56 Frozen-profile paired n=10 and memory-pressure audit (2026-09-04)

Runs 6--10 were added without changing the frozen profiles. The final primary
cohort contains exactly 300 unique Map1--10 by Full/Sector/Adaptive by run
keys. Every row is run-, speed-, performance- and cgroup-valid, with zero
retry, OOM kill or static-PCD contact. Nominal completion is 99/100 in each
mode. Maps 1--9 are 10/10 in every mode; each mode has one Map10 failure.

The original Sector Map10 run 4 failure remains the clean planner-liveness
event: four waypoints, 180 s, +0.021 m clearance and zero PSI/OOM/retry. Full
and Adaptive completed the paired run, so this is one observed Sector-fail /
Adaptive-pass recovery.

Map10 run 8 is confounded by severe host-memory pressure. Sector completed in
85.50 s before the pressure spike. Adaptive stopped after three waypoints at
187.70 s and Full after two waypoints at 201.20 s with monitor HUNG. Their
minimum available memory was about 249 MiB with 2 GiB swap saturated. Peak
memory PSI some/full was 55.87/52.89 for Adaptive and 64.26/60.66 for Full;
Full already started at PSI some 28.43. There was no OOM kill. Adaptive still
showed repeated A-star/optimizer timeout at a certified stop, while Full's
planner log stopped advancing after roughly 90 s. The evidence supports a
planner-liveness and host-pressure interaction, not either factor as a proven
sole cause.

After reclaiming the unrelated host load, a separate Map10 clean audit ran
Full and Adaptive twice each. All four rows completed without contact,
retry, OOM or PSI. This non-reproduction is supporting evidence only and does
not replace the primary run 8 failures. A session-interrupted orphan Map10
run 9 Adaptive attempt was also retained separately: the runner died before
CSV/performance finalization, while its launch remained alive for more than
three hours. The six missing primary keys were then collected using
`--resume-existing`; all completed. The interrupted attempt is excluded as an
incomplete infrastructure row rather than silently treated as a success.

Primary all-run time for Full/Sector/Adaptive is 67.356/65.884/64.472 s;
successful-row time is 66.004/64.731/63.227 s. Adaptive reduces Full logical
planner ingress by 75.903%, map-compute core equivalent by 67.254%, end-to-end
mean cores by 13.362% and end-to-end core-seconds by 16.948%. Against Sector,
ingress and external DDS fall by 20.502% and 20.405%, while mean cores and
core-seconds rise by 6.175% and 6.193%.

Adaptive made 2,009 effective Full-open transitions (20.09/run), with 23 runs
showing a stall-open, 2,591 replan-guard opens, 390 trajectory-guard opens and
35/6 future-tail/current-body OCCUPIED verdicts. Clearance below 0.20 m occurs
in 6/11/8 Full/Sector/Adaptive rows, so contact-free operation remains distinct
from the clearance contract.

Adaptive versus Sector has one discordant completion in each direction;
two-sided exact McNemar p=1.0. The Wilson 95% completion lower bound for
99/100 is 94.55%. The enlarged campaign therefore supports the Full-relative
compute and ingress reductions, but not population-level 100% completion or
an Adaptive success-rate advantage over Sector. Detailed per-map results and
the exact resource audit are in `docs/full_inprocess_control_20260903.md` and
`results/full_control_three_mode_map1_10_n10_{raw,summary,reductions}_20260903.csv`.

### 8.57 Failure reclassification and default campaign resource gate (2026-09-04)

The n=10 runner collected memory telemetry but did not use it in `run_valid` or
retry decisions. The two Map10 run-8 rows therefore have legacy
`run_valid=True` values that do not establish planner-valid trials. Adaptive
started with only 581 MiB available, fell to 249 MiB, saturated the 2 GiB swap,
and reached memory PSI some/full 55.87/52.89 before timing out at three
waypoints. Full started at 842 MiB with PSI already 28.43/26.79, fell to 249
MiB, reached PSI 64.26/60.66, and its planner log stopped advancing before the
monitor reported HUNG at two waypoints. These are resource-confounded attempts
and must not be used as independent planner failures in a future success-rate
denominator.

This correction does not remove the separate Map10 run-4 Sector failure. That
row had 2.12 GiB available, zero PSI/OOM/retry, retained a certified stop,
saturated six exclusion zones, and rejected over 100 near-identical candidates.
It remains a valid Sector topology/liveness failure. Sector also completed run
8 with only 340 MiB available but PSI at 1.89, showing that low
`MemAvailable` alone is not a causal failure threshold. The strong run-8
discriminator is severe sustained PSI. Four clean Map10 Full/Adaptive audit
runs at 6.42--6.54 GiB minimum available and PSI zero all completed; this
supports, but does not prove, the resource explanation because Adaptive still
showed a genuine recovery loop during the confounded attempt.

Excluding only the two resource-confounded rows yields 99/99 planner-valid
completions for Full, 99/100 for Sector and 99/99 for Adaptive. This is a
post-hoc diagnostic view, not a replacement headline rate: the exclusion rule
was introduced after observing the campaign and requires prospective
confirmation with the gate enabled from the first run.

`native_campaign.py` now enables a fail-closed resource-quality policy by
default. Before every attempt, 8192 MiB available and PSI some/full avg10 at or
below 10/5 must remain stable for five seconds. During the attempt, available
memory below 2048 MiB or either PSI violation must persist for five seconds
before the stack is terminated and retried. A preflight that cannot recover
within 600 seconds exits without writing the pending key, allowing an explicit
`--resume-existing` after host cleanup. The 2 GiB floor is deliberately an
experimental-quality margin, not a retroactive causal classifier.

New CSV fields record resource validity, infrastructure failure, thresholds,
preflight wait, abort count and reasons; resource validity is combined with
`run_valid`. Every subprocess is also started through a registered independent
process group, and SIGINT/SIGTERM/SIGHUP plus normal exit clean all groups. This
closes the lifecycle defect that left the interrupted Map10 run-9 Adaptive ROS
stack alive for hours. `--no-resource-guard` is retained only for historical
reproduction; any machine-specific threshold change must be frozen before a
new cohort and held identical across modes.

All 33 native-campaign tests pass. A forced insufficient-memory preflight
exited non-zero before launch and produced a header-only CSV. An actual Map10
smoke is intentionally deferred: the current VS Code extension host uses about
6.3 GiB RSS and leaves only about 5.0 GiB available, so the new 8 GiB gate
correctly refuses to start. Freeing that unrelated load and rerunning Map10
Full/Adaptive under the unchanged planner profiles is the next validation;
planner tuning is justified only if a failure reproduces under a resource-valid
run.
