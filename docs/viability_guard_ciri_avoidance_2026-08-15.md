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

## Current status — not flight-ready, but no longer failing for the original reason

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
- **Safety remains the strongest result: 0/170 contact across the three
  committed aggregate cohorts** (100 runs in 8.8, 50 in 8.9, and 20 in
  8.12). Section 8.12's worst static-PCD centre distance was 0.372 m. These
  are different configurations and should not be pooled for a completion
  estimate, but none traded the liveness work for measured contact.
- **The requested local gate now passes on the formerly unstable seed10:**
  5/5 consecutive full completions, 25/25 waypoints, contact 0/5. The broader
  seed1-10 n=2 check was 20/20, but n=2 is not a population-rate estimate and
  does not by itself make the planner flight-ready.
- The frequent same-generation `PlanFromRest` deadlock diagnosed in 8.7/8.8
  now has an implemented recovery rather than only a proposed escalation.
  The reproduced seed10 failure held one generation for 75.404 s; section
  8.12's seed1-10 n=2 maximum was 1.467 s, and the seed10 five-run maximum was
  1.755 s. The new state transition changes XY topology after a certified
  stop; it does not accept a guard-rejected moving candidate.
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
- FSM CPU usage has not been measured for any run across either day.
- The `VIABILITY_DEBUG` and `AVOIDANCE_DEBUG` diagnostic logging left in
  `super_planner.cpp`/`corridor_generator.cpp` is harmless when the env
  vars are unset but has not been cleaned up.

Do not describe `static_seedmaps_guard_viability_v7.yaml` or any of its
`_wide`/`_tight`/`_tight_h08` variants as flight-ready. The former prerequisite
for a larger campaign (one 5/5, zero-contact gate) is now satisfied on seed10;
the next defensible step is a larger paired topology-recovery ablation under
the normal shadow-off `tight_v7` profile, not connecting CIRI shadow to the
brake decision.
