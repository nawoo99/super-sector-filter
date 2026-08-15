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
   0.558 s and max 3.067 s — a long tail of multi-second stalls, consistent
   with Codex's prior finding that map commits and planning share a
   mutually-exclusive callback group, so expensive planning work can starve
   map updates for seconds at a time. This is the same issue
   `docs/loop_guard_snapshot_recovery_steps_6_to_22_2026-08-14.md` already
   flagged and did not resolve; it is not something today's fixes touched.
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

This means cause 1 is not fixable by simply retuning the publish rate. It
most likely needs the scheduling/architecture change Codex's prior docs
already pointed at (decouple the map-write and planning callback groups so
expensive planning cannot starve map commits), which has not been attempted.

## Current status — not flight-ready

- Best formal result: seed6 5-run gate 4/5 (waypoints 1,5,5,5,5), 0/5 contact.
  The required gate (5/5 completion, 0 contact) has **not** been passed.
- Contact has been 0 across every run today (5-run gates, 10-seed sweep, and
  all follow-up diagnostic runs combined, ~40+ runs) after the CIRI
  avoidance-zone fix. This is the strongest evidence so far in the whole
  guard investigation, but it is still far short of a formal 50-run
  campaign.
- Completion is still highly variable run-to-run on an identical
  configuration and map (seed6 alone ranged 1/5 to 5/5 across five runs, and
  seed8 ranged 1/5 to 5/5 across two otherwise-identical re-runs). §6
  attributes this to a combination of chronic map-staleness braking (dominant,
  unresolved) and residual topology-reroute-zone insufficiency (rare,
  probably inherent to the single-sphere strategy).
- FSM CPU usage has not been measured for any of today's runs.
- The `VIABILITY_DEBUG` and `AVOIDANCE_DEBUG` diagnostic logging left in
  `super_planner.cpp`/`corridor_generator.cpp` is harmless when the env vars
  are unset but has not been cleaned up.
- None of today's or the prior two days' guard/viability code was committed
  before this note; see the accompanying commit for what is now mirrored
  into `super_patches/`.

Do not describe `static_seedmaps_guard_viability_v7.yaml` or any of its
`_wide`/`_tight`/`_tight_h08` variants as flight-ready. Do not run a 50-run
campaign on this configuration before a full 5/5, zero-contact gate is
recorded on at least one seed.
