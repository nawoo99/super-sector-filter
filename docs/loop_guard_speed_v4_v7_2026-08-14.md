# Loop guard speed check: v4 and v7 (2026-08-14)

## Scope

This check tests whether lowering the common maximum speed resolves the
seed6 loop safety/liveness conflict observed with `full_guard_v10`.

- Course: seed6 `loop24.txt` (five waypoint completion events)
- Planner/filter mode: guarded full cloud, direct `/cloud_registered`
- Profiles: `static_seedmaps_guard_v4.yaml` and
  `static_seedmaps_guard_v7.yaml`
- Controlled difference from `static_seedmaps_guard_v10.yaml`:
  `traj_opt/boundary/max_vel` only (4.0 or 7.0 m/s)
- All guard, map, acceleration, jerk, corridor, and retry settings remain
  unchanged.
- Speed-scaled campaign timeout: 122.5 s at v4 and 95.71 s at v7.

The campaign modes are named `full_guard_v4` and `full_guard_v7`. They must not
be confused with the unguarded paper-ablation modes `full_v4` and `full_v7`.

## Results

The formal five-run cohorts are:

- v4: the v4 row in `step23` plus four additional rows in `step25`;
- v7: the five rows in `step24`.

| Speed | Success | Contact runs | Waypoints reached | Minimum clearance | Mean clearance | Mean FSM CPU |
|---:|---:|---:|---|---:|---:|---:|
| 4 m/s | 0/5 | 0/5 | `[0, 0, 2, 0, 4]` | 0.383 m | 0.4294 m | 37.35% |
| 7 m/s | 1/5 | 0/5 | `[5, 0, 0, 4, 2]` | 0.409 m | 0.4420 m | 54.34% |

The preliminary v7 gate in `step23` also completed in 76.08 s with no contact
and 0.375 m minimum clearance. It is excluded from the predeclared v7 five-run
cohort; counting every executed v7 run gives 2/6 completion and 0/6 contact.

Result files:

- `results/step23_guard_speed_v4_v7_seed6_single.csv`
- `results/step24_guard_speed_v7_seed6_n5.csv`
- `results/step25_guard_speed_v4_seed6_n4_additional.csv`
- corresponding `*_artifacts/` directories contain monitor JSON and stack logs.

## Failure classification

Neither speed produced a contact in these samples. The primary failure is
liveness, not collision:

- v4 had three early 0-waypoint stops. The other runs reached 2 and 4
  waypoints before timeout.
- v7 had two early 0-waypoint stops, one 2-waypoint timeout/stall, and one
  4-waypoint timeout; one run completed.
- The repeated rejection was overwhelmingly `CLEARANCE_MARGIN`, not stale-map
  or version-race status. Across the formal cohorts, v4 logged 1,250
  `CLEARANCE_MARGIN` rejections (plus one `VERSION_CHANGED`); v7 logged 944.
- The adaptive inflated-corridor retry repeatedly generated another candidate
  rejected at essentially the same local geometry. Lower maximum velocity did
  not remove that corridor/guard conflict.

The v4 4-waypoint run traveled 202.4 m and the v7 4-waypoint run traveled
208.1 m, so those two failures include a timeout-budget component. Extending
the timeout could change their completion labels, but it would not explain or
fix the 0-waypoint deadlocks.

## Conclusion

Reducing v10 to v4 or v7 eliminated observed contacts in this small seed6
sample, but neither speed passes the required 5/5 completion, zero-contact
gate. v7 is the better of the two tested settings for progress, but 1/5 formal
completion is not planner-ready and does not justify a 50-run campaign.

The next change should target recovery from repeated geometric guard rejection:
the retry must alter the candidate topology/corridor or select a certified
stop-and-reroute behavior, rather than resubmitting near-identical EXP
trajectories. Any such change should be re-gated at a fixed common speed and
with a timeout reported separately from geometric deadlock. These results are
descriptive only; no McNemar or other significance test was performed.
