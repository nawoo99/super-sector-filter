# Guarded v7 `full` seed9/10 liveness failure analysis (2026-08-20)

## Conclusion

The two `full` failures in the seed1-10 x mode x n=5 campaign were not
ordinary long missions and were not caused by a frozen map. Both entered a
fail-closed recovery loop in which the next `PlanFromRest` generation was
rejected hundreds of times, every emergency-brake attempt was also rejected,
and the certified topology reroute was therefore never armed.

The immediate architectural defect is the recovery start state. Once a
`PositionCommand` has been published, `fsm_ros2.hpp` keeps
`last_published_cmd_valid_ == true` indefinitely. `activateEmergencyBrake()`
prefers that cached command without an age or odometry-consistency check. When
normal publication is suppressed after a guard failure, the cache stops
advancing, yet every later brake retry continues to use it. In the two failed
runs, all 314 final-loop brake attempts reused exactly the same logged initial
speed: 2.813 m/s on seed9 and 0.741 m/s on seed10.

Those brake candidates never became safe, so no brake command was published
and `tryRecoverFromEmergencyBrake()` could never certify a terminal stable
hold. The topology reroute is deliberately gated on either odometry speed <=
0.2 m/s or that certified-stop flag. Consequently the recovery that should
change XY topology was unreachable: both failures logged zero
`TRAJ_GUARD_REROUTE_ARM` and zero `TRAJ_GUARD_REROUTE_SEARCH` events.

## Static-PCD monitor repair

The preceding 150-run campaign placed `--static-pcd` after argparse's `--`
delimiter, so the monitor treated the option as a ROS argument and never
loaded it. The runner now places monitor options before `--`. The monitor also
emits `static_pcd_enabled` and `static_pcd_point_count`, and a requested
seedmap static-PCD run is invalid/retried unless the former is true and the
latter is positive.

The repair is covered by the native-campaign unit suite (12/12 passing). A
separate full-stack seed1 smoke loaded 241,490 points, reported
`static_pcd_enabled=true`, completed 5/5 waypoints in 57.42 s, and reported no
static-PCD contact. This proves that the repaired path is active; it does not
retroactively validate the 150-run campaign's `static_pcd_*` fields.

## Failure evidence

| metric | seed9 run4 | seed10 run2 |
|:---|---:|---:|
| campaign result | 4/5, timeout | 1/5, timeout |
| final position | (14.075, -15.207, 2.111) | (18.267, 25.249, 1.694) |
| affected mission leg | (24,-24) -> (0,0) | (24,24) -> (-24,24) |
| last committed generation | 176 | 70 |
| permanently rejected generation | 177 | 71 |
| same-generation reject count | 314 | 314 |
| reject span | 30.614 s | 98.871 s |
| reject class | 314 EXP `CLEARANCE_MARGIN` | 314 EXP `CLEARANCE_MARGIN` |
| collision minus checked-from time | median 0.000 s | median 0.085 s |
| brake retries in final loop | 314 rejected / 0 accepted | 314 rejected / 0 accepted |
| cached brake initial speed | 2.813 m/s every retry | 0.741 m/s every retry |
| brake rejection reason | 251 margin, 63 stale map | 291 unobserved, 23 stale map |
| topology arm / search | 0 / 0 | 0 / 0 |
| map version during loop | 317 -> 401 | 44 -> 465 |
| EXP success after loop began | 313 | 315 |
| EXP/frontend failure after loop began | 3 | 475 |
| replan-budget overtime after loop began | 3 | 460 |
| FIRI NaN/Inf after loop began | 0 | 14 |

Seed9 is the cleaner reproduction. Almost every new plan was generated, then
the trajectory guard rejected its first checked EXP sample at approximately
`(14.067, -15.220, 2.125)`. In 311/314 cases the collision time was within
10 ms of the validation start. The planner therefore kept proposing a route
that began inside the inflated clearance boundary.

Seed10 entered the same unreachable recovery state much earlier in the
mission, but planning at that location was also numerically and temporally
fragile. In addition to the 314 guard rejections, 475 attempts failed before
reaching the guard; 460 exceeded the 0.1 s replan budget. Fourteen FIRI
NaN/Inf warnings led to `GeneratePolytopeFromLine` and
`SearchPolytopeOnPath` failures. These are a secondary amplifier, not the
trigger: the generation-71 guard/brake loop began before the late FIRI
warnings and persisted for 98.9 s.

Map versions advanced by 84 and 421 respectively during the stuck intervals.
This rules out the earlier map-commit freeze mechanism. It also shows why
repeating the same candidate was insufficient: new map commits did not change
the recovery topology or refresh the cached brake start command.

## Why seed9 and seed10 expose it

All ten maps contain 410 cylinders in the same 64 x 64 m field and preserve a
minimum 1.0 m obstacle-surface gap. The controlled difficulty axis is cylinder
radius. Seed9/10 use the largest radius, 0.65 m (1.30 m diameter), and each PCD
contains 1,042,220 surface samples. Seed1/2 use radius 0.15 m and 241,490
samples. `full` forwards every sample, so seed9/10 combine the largest obstacle
footprint, the most constrained turns, and the heaviest map input.

The guard was rejecting a conservative clearance boundary rather than
reporting raw physical occupancy. As an offline geometry check, the mean
rejected candidate point was 0.461 m from the seed9 static PCD and 0.498 m from
the seed10 PCD. With `robot_r=0.2 m`, those mean points are outside the physical
body radius, consistent with the logged `CLEARANCE_MARGIN` status. The exact
inflated-grid decision also includes voxel quantization, so these distances
must not be presented as flight-clearance measurements.

The n=5 outcome is therefore a stress signal, not proof that each map has a
true 80% population completion probability. Seed9/10 each failed once, while
the other four full runs completed. The successful seed9 runs did arm 79
topology blockers and execute 126 reroute searches in total; their longest
same-generation reject span was 4.531 s. Successful seed10 runs armed 82
blockers and ran 144 searches; their maximum span was 2.235 s. The failed runs
are categorically different: not a single topology attempt was reached.

## Recommended next implementation

1. Timestamp `last_published_cmd_` and reject it as a brake initial state when
   it is stale or inconsistent with current odometry. Log command age and
   position/velocity disagreement on every brake activation.
2. Construct the recovery state from a fresh, mutually consistent source:
   current evaluated command when it is current, otherwise the current tracked
   odometry state with an explicitly handled continuity boundary. Certify the
   resulting brake before publication exactly as today.
3. Add a bounded repeated-reject state instead of cycling
   `EMER_STOP -> GENERATE_TRAJ` indefinitely. It may enable topology reroute
   only after a fresh actual-state stop/hold is certified; do not restore the
   previously reverted moving-brake collision blockers.
4. After that primary fix, separately harden seed10's FIRI input validation and
   replan-budget handling. Tuning FIRI first would leave seed9's deterministic
   stale-command/certification deadlock unchanged.

Per-run counts are preserved in
`results/guarded_v7_full_seed9_seed10_log_analysis_20260820.csv`. The two raw
failure monitor JSON files remain under
`results/guarded_v7_full_sector_adaptive_seed1_10_n5_failures_20260820/`.
