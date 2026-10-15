# v7 topology change and certified stop-and-reroute (2026-08-14)

> [!IMPORTANT]
> **2026-08-15 continuation:** the pre-commit viability/speed-governor guard
> this doc's conclusion recommended was implemented, plus two bugs it exposed
> were found and fixed (a corridor-inflation-vs-physical-radius mismatch, and
> topology-reroute avoidance zones never reaching CIRI/MINCO). Best result so
> far: seed6 5-run gate 4/5 (still not the required 5/5), 0/5 contact. Read
> `docs/viability_guard_ciri_avoidance_2026-08-15.md` before citing this
> doc's numbers as current.

## Decision and scope

The new experimental mode is `full_guard_reroute_v7`. It keeps 7 m/s as the
upper cruise-speed basis, leaves `full_guard_v7` unchanged, and replaces the
old same-candidate recovery loop with a stopped topology change.

This is an experimental SUPER-derived planner mode. It is not an upstream
SUPER result and it has not passed the required safety/liveness gate.

## Implemented behavior

### Topology-changing recovery

After a `PlanFromRest` candidate is rejected with `CLEARANCE_MARGIN` in EXP,
appended backup, or the EXP-to-backup stitch, the planner:

1. requires the vehicle to be stopped (`speed <= 0.2 m/s`);
2. creates or grows a temporary avoidance sphere around the rejected point;
3. reruns A* with that sphere as an obstacle;
4. permits an initial monotonic escape only when the current vehicle position
   lies inside the newly created sphere;
5. retains at most four zones, with radii from 0.8 m to 1.8 m;
6. clears the zones after a successful trajectory commit or a goal change.

The relevant logs are `TRAJ_GUARD_REROUTE_ARM` and
`TRAJ_GUARD_REROUTE_SEARCH`.

### Stop certification correction

Contact forensics showed that the old emergency brake was started only after
`map_age` crossed 0.75 s, then checked against that same stale snapshot and
logged as `path_status=SAFE`. That was not a valid freshness-qualified
certificate.

The implementation now supports a separate
`brake_trigger_map_age_s`. The reroute profile uses 0.55 s while retaining a
0.75 s absolute map-certificate limit. Brake publication additionally requires
the map version before and after validation to match and the snapshot to remain
within the absolute age limit. Brake logs now include the certified map version
and age.

An optional raw-cloud KD-tree guard was also implemented behind
`fsm/trajectory_guard/raw_cloud`. It is disabled in the selected profile. The
experiment showed that raw-cloud staleness cannot itself be a hard stop trigger
at the measured simulator frame rate, and a fresh raw hazard can still arrive
after the certified-brake set has become empty.

## Results

All rows use seed6 and `loop24.txt`. `Contact runs` counts runs with one or more
live-cloud contacts.

| Step | Variant | Runs | Completion | Contact runs | Key observation |
|---:|---|---:|---:|---:|---|
| 26 | first topology reroute, 95.71 s | 1 | 4/5 WP | 0/1 | reroute armed 31 times; timeout |
| 28 | all guarded segments, 120 s | 1 | 5/5 | 0/1 | 72.20 s success |
| 29 | topology reroute, 120 s | 5 | 4/5 runs | 2/5 | three total contacts; gate failed |
| 30 | proactive stop at 0.45 s | 1 | 4/5 WP | 0/1 | 50 brakes; 0.46 m short at timeout |
| 31 | proactive stop at 0.55 s | 1 | 5/5 | 0/1 | 97.31 s; 29 brakes |
| 32 | proactive stop at 0.55 s | 5 | 1/5 runs | 1/5 | one total contact; gate failed |
| 33 | raw-cloud staleness as hard gate | 1 | 0/5 WP | 0/1 | only 54 raw frames in 120 s; unusable |
| 34 | only fresh raw hazards are hard | 1 | 2/5 WP | 0/1 | one hazard found, but all brakes rejected |

Result files and full artifacts are:

- `results/step26_guard_topology_reroute_v7_seed6_single.csv`
- `results/step28_guard_reroute_v7_recovery120_seed6_single.csv`
- `results/step29_guard_reroute_v7_recovery120_seed6_n5.csv`
- `results/step30_guard_reroute_v7_freshbrake045_seed6_single.csv`
- `results/step31_guard_reroute_v7_freshbrake055_seed6_single.csv`
- `results/step32_guard_reroute_v7_freshbrake055_seed6_n5.csv`
- `results/step33_guard_reroute_v7_rawcloud_seed6_single.csv`
- `results/step34_guard_reroute_v7_rawhazard_seed6_single.csv`

Each has a corresponding `_artifacts/` directory containing monitor JSON and
stack logs.

## Contact forensics

All four contacts in the two formal n=5 cohorts occurred while
`trajectory_flag=3`, namely during the guard's emergency brake, not while a
newly committed reroute trajectory was executing.

In step29 the brake triggers were at `map_age=0.750–0.757 s`. One contact
occurred after the vehicle had reached its terminal hold. In step32 the contact
occurred 0.626 s after a brake certified at `map_age=0.552 s`; speed was still
1.90 m/s and no newer planner map version had become available. The independent
monitor had already received a newer live cloud.

Step34 then demonstrated the other half of the problem. A fresh raw cloud
reported an intersection at age 0.009 s while speed was 6.98 m/s, but every
dynamically admissible stop candidate was rejected (`CLEARANCE_MARGIN`). A
fresh hazard signal alone therefore does not establish a certified recovery.

## Conclusion

Topology change is useful for liveness: it can escape repeated geometric
rejections that an identical-candidate retry cannot. It does not establish the
safety invariant needed at v=7.

The remaining architectural requirement is an always-available recovery set:
before publishing motion, every reachable command state must retain a
freshness-qualified, dynamically feasible stop or alternate route. In practice
this means either:

- validating and carrying a contingency trajectory along the whole committed
  trajectory (viability / invariant-backup policy), or
- treating 7 m/s as an upper cruise limit and reducing local speed whenever
  sensing latency, occlusion, clearance, or curvature makes that contingency
  set empty.

Further tuning of the 0.45/0.55/0.75 s threshold cannot satisfy both the 120 s
liveness gate and zero-contact safety with the measured sensor cadence. A
timeout increase can relabel near-complete runs but cannot repair the empty
certified-brake case.

## Verification

- `colcon build --packages-select super_planner --symlink-install`: passed.
- `pytest -q scripts/native_campaign/test_*.py`: passed (12 tests).
- `git diff --check`: passed at the implementation checkpoint.

